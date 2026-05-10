import asyncio
from datetime import datetime

import nonebot
from nonebot import get_plugin_config, on_startup, require

from .config import TodayHITConfig
from .models import Article, ScraperState, init_db
from .pusher import build_push_message, get_unpushed_articles, mark_pushed, match_subscriptions
from .scraper import fetch_category_page, fetch_rss, parse_category_page, parse_rss

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

# 加载命令模块（触发命令注册）
from . import commands  # noqa: F401

config = get_plugin_config(TodayHITConfig)

CATEGORY_MAP = {10: "公告公示", 11: "新闻快讯"}


@on_startup
async def startup():
    init_db(config.todayhit_db_path)


async def scrape_and_push():
    """核心定时任务：采集 + 推送。"""
    base_url = config.todayhit_base_url
    delay = config.todayhit_request_delay
    max_push = config.todayhit_max_push_per_round

    # 1. 采集 RSS
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
                published_at=item["published_at"],
            ).on_conflict_ignore().execute()
            new_count += 1

    if items:
        max_id = max(item["id"] for item in items)
        if max_id > last_rss_id:
            ScraperState.set("last_rss_id", str(max_id))

    # 2. 分类页补充采集
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
                    source_dept=a.get("source_dept"),
                    category=cat_name,
                ).on_conflict_ignore().execute()
                # 补充已有文章的分类
                Article.update(category=cat_name).where(
                    Article.id == a["id"], Article.category.is_null()
                ).execute()
        except Exception as e:
            nonebot.logger.warning(f"分类页 {cat_name} 采集失败: {e}")

    nonebot.logger.info(f"采集完成，新增 {new_count} 条 RSS 文章")

    # 3. 推送
    unpushed = get_unpushed_articles(max_push)
    if not unpushed:
        nonebot.logger.info("无新文章需推送")
        return

    bots = nonebot.get_bots()
    if not bots:
        nonebot.logger.warning("无可用 Bot，跳过推送")
        return
    bot = next(iter(bots.values()))

    # 为每个 target 收集待推送文章
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
                }
            )
            mark_pushed(article.id, target_type, target_id)

    # 发送消息
    for (target_type, target_id), articles in target_articles.items():
        msg = build_push_message(articles)
        try:
            if target_type == "group":
                await bot.send_group_msg(group_id=int(target_id), message=msg)
            else:
                await bot.send_private_msg(user_id=int(target_id), message=msg)
            await asyncio.sleep(3)
        except Exception as e:
            nonebot.logger.warning(f"推送到 {target_type}:{target_id} 失败: {e}")


# 注册定时任务
scheduler.add_job(
    scrape_and_push,
    "interval",
    seconds=config.todayhit_scrape_interval,
    id="todayhit_scrape",
    replace_existing=True,
)
