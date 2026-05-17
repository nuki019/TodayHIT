import asyncio

import nonebot

from .config import TodayHITConfig
from .models import Article, GroupMessage, ScraperState, Subscription, init_db
from .pusher import build_push_nodes, get_unpushed_articles, mark_pushed, match_subscriptions
from .scraper import (
    fetch_category_page,
    fetch_rss,
    parse_category_page,
    parse_rss,
    scrape_all_departments,
    scrape_hit_main,
    scrape_hitcs,
    scrape_hoa_blog,
)

# 以下 nonebot 初始化仅在完整运行时执行，测试时跳过
try:
    from nonebot import get_plugin_config, on_message, require
    from nonebot.adapters.onebot.v11 import GroupMessageEvent

    require("nonebot_plugin_apscheduler")
    from nonebot_plugin_apscheduler import scheduler  # noqa: E402

    from . import commands  # noqa: F401

    config = get_plugin_config(TodayHITConfig)
    _NONEBOT_READY = True
except Exception:
    _NONEBOT_READY = False

CATEGORY_MAP = {10: "公告公示", 11: "新闻快讯"}

# 启动爬取完成标志，防止推送空数据
_startup_done = False


if _NONEBOT_READY:

    # ── 消息计数监听器 ──────────────────────────────────

    msg_counter = on_message(priority=0, block=False)


    @msg_counter.handle()
    async def count_group_message(event: GroupMessageEvent):
        """统计群消息条数（不存内容），用于找群友加权。"""
        nickname = getattr(event, "sender", None)
        name = ""
        if nickname:
            name = nickname.card or nickname.nickname or ""
        GroupMessage.increment(
            group_id=str(event.group_id),
            user_id=str(event.user_id),
            nickname=name,
        )

    # ── 启动钩子 ────────────────────────────────────────

    @nonebot.get_driver().on_startup
    async def startup():
        init_db(config.todayhit_db_path)
        asyncio.create_task(_startup_scrape())
        asyncio.create_task(_sync_group_members())

    async def _startup_scrape():
        """启动后延迟执行一次爬取。"""
        global _startup_done
        await asyncio.sleep(5)
        try:
            await scrape_only()
            nonebot.logger.info("启动爬取完成")
        except Exception as e:
            nonebot.logger.warning(f"启动爬取失败: {e}")
        finally:
            _startup_done = True

    async def _sync_group_members():
        """同步所有群成员昵称到 GroupMessage 表。"""
        await asyncio.sleep(10)
        try:
            bot = nonebot.get_bot()
            groups = await bot.call_api("get_group_list")
            for g in groups:
                gid = str(g["group_id"])
                members = await bot.call_api("get_group_member_list", group_id=int(gid))
                for m in members:
                    name = m.get("card") or m.get("nickname") or ""
                    GroupMessage.increment(gid, str(m["user_id"]), name)
            nonebot.logger.info(f"群成员同步完成，共 {len(groups)} 个群")
        except Exception as e:
            nonebot.logger.warning(f"群成员同步失败: {e}")

    # ── 核心采集 ────────────────────────────────────────

    async def scrape_only() -> int:
        """采集所有数据源，返回新增文章总数。"""
        new_count = 0
        new_count += await _scrape_todayhit()
        new_count += await _scrape_hit_main()
        new_count += await _scrape_hitcs()
        new_count += await _scrape_hoa_blog()
        new_count += await _scrape_departments()
        nonebot.logger.info(f"全源采集完成，新增 {new_count} 条")
        return new_count

    async def _scrape_todayhit() -> int:
        """原有 today.hit.edu.cn RSS + 分类页采集。"""
        base_url = config.todayhit_base_url
        delay = config.todayhit_request_delay

        # 1. RSS
        try:
            rss_text = await fetch_rss(base_url)
            items = parse_rss(rss_text)
        except Exception as e:
            nonebot.logger.warning(f"RSS 采集失败: {e}")
            items = []

        new_count = 0
        last_rss_id = int(ScraperState.get_value("last_rss_id", "0"))
        for item in items:
            if item["id"] > last_rss_id:
                Article.insert(
                    id=item["id"],
                    title=item["title"],
                    url=item["url"],
                    source="todayhit",
                    source_id=str(item["id"]),
                    published_at=item["published_at"],
                ).on_conflict_ignore().execute()
                new_count += 1

        if items:
            max_id = max(item["id"] for item in items)
            if max_id > last_rss_id:
                ScraperState.set("last_rss_id", str(max_id))

        # 2. 分类页
        for cat_id, cat_name in CATEGORY_MAP.items():
            try:
                await asyncio.sleep(delay)
                html = await fetch_category_page(base_url, cat_id)
                articles = parse_category_page(html, base_url)
                for a in articles:
                    Article.insert(
                        id=a["id"],
                        title=a["title"],
                        url=a["url"],
                        source="todayhit",
                        source_id=str(a["id"]),
                        source_dept=a.get("source_dept"),
                        category=cat_name,
                        published_at=a.get("published_at"),
                    ).on_conflict_ignore().execute()
                    Article.update(category=cat_name).where(
                        Article.id == a["id"], Article.category.is_null()
                    ).execute()
                    if a.get("published_at"):
                        Article.update(published_at=a["published_at"]).where(
                            Article.id == a["id"], Article.published_at.is_null()
                        ).execute()
            except Exception as e:
                nonebot.logger.warning(f"分类页 {cat_name} 采集失败: {e}")

        nonebot.logger.info(f"todayhit 采集完成，新增 {new_count} 条")
        return new_count

    async def _scrape_hit_main() -> int:
        """hit.edu.cn 主站工大要闻。"""
        try:
            items = await scrape_hit_main()
            new_count = 0
            for a in items:
                Article.insert(**a).on_conflict_ignore().execute()
                new_count += 1
            nonebot.logger.info(f"hit_main 采集完成，新增 {new_count} 条")
            return new_count
        except Exception as e:
            nonebot.logger.warning(f"hit_main 采集失败: {e}")
            return 0

    async def _scrape_hitcs() -> int:
        """HITCS GitHub 仓库提交。"""
        try:
            last_sha = ScraperState.get_value("last_hitcs_sha", "")
            items = await scrape_hitcs()
            new_count = 0
            for a in items:
                if a["source_id"] == last_sha:
                    break
                Article.insert(**a).on_conflict_ignore().execute()
                new_count += 1
            if items:
                ScraperState.set("last_hitcs_sha", items[0]["source_id"])
            nonebot.logger.info(f"hitcs 采集完成，新增 {new_count} 条")
            return new_count
        except Exception as e:
            nonebot.logger.warning(f"hitcs 采集失败: {e}")
            return 0

    async def _scrape_hoa_blog() -> int:
        """hoa.moe 博客。"""
        try:
            items = await scrape_hoa_blog()
            new_count = 0
            for a in items:
                Article.insert(**a).on_conflict_ignore().execute()
                new_count += 1
            nonebot.logger.info(f"hoa_blog 采集完成，新增 {new_count} 条")
            return new_count
        except Exception as e:
            nonebot.logger.warning(f"hoa_blog 采集失败: {e}")
            return 0

    async def _scrape_departments() -> int:
        """哈工大各子站点（学院/部处/直属单位）。"""
        try:
            items = await scrape_all_departments()
            new_count = 0
            for a in items:
                Article.insert(**a).on_conflict_ignore().execute()
                new_count += 1
            nonebot.logger.info(f"各部门站点采集完成，新增 {new_count} 条")
            return new_count
        except Exception as e:
            nonebot.logger.warning(f"部门站点采集失败: {e}")
            return 0

    # ── 订阅推送（原有逻辑） ────────────────────────────

    async def scrape_and_push():
        """采集 + 订阅推送。"""
        if not _startup_done:
            nonebot.logger.info("启动爬取尚未完成，跳过本次推送")
            return
        await scrape_only()

        max_push = config.todayhit_max_push_per_round
        unpushed = get_unpushed_articles(max_push)
        if not unpushed:
            nonebot.logger.info("无新文章需推送")
            return

        try:
            bot = nonebot.get_bot()
        except Exception:
            nonebot.logger.warning("无可用 Bot，跳过推送")
            return

        target_articles: dict[tuple[str, str], list[dict]] = {}
        for article in unpushed:
            targets = match_subscriptions(article)
            if not targets:
                mark_pushed(article.id, "none", "none")
                continue
            for target_type, target_id in targets:
                key = (target_type, target_id)
                if key not in target_articles:
                    target_articles[key] = []
                target_articles[key].append(
                    {
                        "title": article.title,
                        "source_dept": article.source_dept,
                        "url": article.url,
                        "published_at": article.published_at,
                        "source": getattr(article, "source", None) or "todayhit",
                    }
                )
                mark_pushed(article.id, target_type, target_id)

        bot_id = int(bot.self_id)
        for (target_type, target_id), articles in target_articles.items():
            nodes = build_push_nodes(articles, bot_id)
            if not nodes:
                continue
            try:
                if target_type == "group":
                    await bot.call_api(
                        "send_group_forward_msg",
                        group_id=int(target_id),
                        messages=nodes,
                    )
                else:
                    await bot.call_api(
                        "send_private_forward_msg",
                        user_id=int(target_id),
                        messages=nodes,
                    )
                await asyncio.sleep(3)
            except Exception as e:
                nonebot.logger.warning(f"推送到 {target_type}:{target_id} 失败: {e}")

    # ── 每日广播推送（7:30 cron） ──────────────────────

    async def daily_push():
        """每天 7:30：爬取 → 广播所有群 → 等 10s → 推送私聊订阅用户。"""
        if not _startup_done:
            nonebot.logger.info("启动爬取尚未完成，跳过每日推送")
            return
        await scrape_only()

        max_push = config.todayhit_max_push_per_round
        unpushed = get_unpushed_articles(max_push)
        if not unpushed:
            nonebot.logger.info("每日推送：无新文章")
            return

        try:
            bot = nonebot.get_bot()
        except Exception:
            nonebot.logger.warning("每日推送：无可用 Bot")
            return

        bot_id = int(bot.self_id)
        articles_dicts = [
            {
                "title": a.title,
                "source_dept": a.source_dept,
                "url": a.url,
                "published_at": a.published_at,
                "source": getattr(a, "source", None) or "todayhit",
            }
            for a in unpushed
        ]
        nodes = build_push_nodes(articles_dicts, bot_id)
        if not nodes:
            return

        # 1. 广播所有群
        try:
            groups = await bot.call_api("get_group_list")
            for g in groups:
                gid = g["group_id"]
                try:
                    await bot.call_api(
                        "send_group_forward_msg",
                        group_id=gid,
                        messages=nodes,
                    )
                    mark_pushed_batch(unpushed, "group", str(gid))
                except Exception as e:
                    nonebot.logger.warning(f"广播群 {gid} 失败: {e}")
                await asyncio.sleep(3)
        except Exception as e:
            nonebot.logger.warning(f"获取群列表失败: {e}")

        # 2. 等待 10 秒
        await asyncio.sleep(10)

        # 3. 推送私聊订阅用户
        private_subs = (
            Subscription.select(Subscription.target_id)
            .where(Subscription.target_type == "private")
            .distinct()
        )
        for sub in private_subs:
            try:
                await bot.call_api(
                    "send_private_forward_msg",
                    user_id=int(sub.target_id),
                    messages=nodes,
                )
                mark_pushed_batch(unpushed, "private", sub.target_id)
            except Exception as e:
                nonebot.logger.warning(f"推送私聊 {sub.target_id} 失败: {e}")
            await asyncio.sleep(3)

        nonebot.logger.info(f"每日推送完成：{len(groups) if 'groups' in dir() else 0} 个群 + 私聊订阅用户")

    def mark_pushed_batch(articles: list, target_type: str, target_id: str):
        """批量标记已推送。"""
        for a in articles:
            mark_pushed(a.id, target_type, target_id)

    # ── 管理员命令入口（供 commands.py 调用） ───────────

    async def admin_force_push():
        """管理员强制推送：爬取 + 广播。"""
        await daily_push()

    async def admin_force_scrape():
        """管理员强制爬取：仅爬取不推送。"""
        return await scrape_only()

    # ── 定时任务注册 ────────────────────────────────────

    # 每 4 小时：采集 + 订阅推送
    # misfire_grace_time=3600: 重启后超过 1 小时的错过的任务不再补执行
    scheduler.add_job(
        scrape_and_push,
        "interval",
        seconds=config.todayhit_scrape_interval,
        id="todayhit_scrape",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 每天 7:30：采集 + 广播所有群 + 私聊订阅
    scheduler.add_job(
        daily_push,
        "cron",
        hour=7,
        minute=30,
        id="todayhit_daily_push",
        replace_existing=True,
    )
