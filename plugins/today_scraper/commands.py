import random

import nonebot
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, MessageSegment

from .config import TodayHITConfig
from .models import Article, GroupMessage, Subscription
from .search import MAX_RESULTS, build_forward_nodes, build_query, parse_search_args

VALID_CATEGORIES = {"公告公示", "新闻快讯"}

try:
    _config = nonebot.get_plugin_config(TodayHITConfig)
    _ADMIN_QQS = set(_config.todayhit_admin_qqs)
except Exception:
    _ADMIN_QQS = {2990056153}


def _is_admin(event: MessageEvent) -> bool:
    return int(event.user_id) in _ADMIN_QQS

# ── helpers ─────────────────────────────────────────────

def _get_target(event: MessageEvent) -> tuple[str, str]:
    if isinstance(event, GroupMessageEvent):
        return "group", str(event.group_id)
    return "private", str(event.user_id)


async def _send_forward(bot, event: MessageEvent, nodes: list[dict]):
    """发送合并转发消息（群/私聊自适应）。"""
    if not nodes:
        await bot.send(event, "暂无数据")
        return
    target_type, target_id = _get_target(event)
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
    except Exception as e:
        nonebot.logger.warning(f"合并转发失败: {e}")
        lines = []
        for n in nodes:
            for seg in n.get("data", {}).get("content", []):
                if seg.get("type") == "text":
                    lines.append(seg["data"]["text"])
        await bot.send(event, "\n---\n".join(lines))


def _parse_args(text: str) -> tuple[str, str]:
    """拆分子命令和剩余参数。返回 (subcmd, rest)。"""
    text = text.strip()
    if not text:
        return "", ""
    parts = text.split(maxsplit=1)
    return parts[0], parts[1] if len(parts) > 1 else ""


# ── 命令注册 ────────────────────────────────────────────

matcher = on_keyword("缇安", priority=10, block=True)


@matcher.handle()
async def handle_tian(event: MessageEvent):
    # 提取"缇安"之后的文本
    raw = event.get_plaintext()
    idx = raw.find("缇安")
    if idx == -1:
        return
    arg_text = raw[idx + len("缇安"):].strip()

    # ── 无参数：最新公告 ──
    if not arg_text:
        articles = list(
            Article.select()
            .where(Article.published_at.is_null(False))
            .order_by(Article.published_at.desc())
            .limit(MAX_RESULTS)
        )
        if not articles:
            articles = list(Article.select().order_by(Article.id.desc()).limit(MAX_RESULTS))
        if not articles:
            await matcher.finish("🥺 缇安还没爬到任何公告呢～稍后再试试吧！")
        bot = nonebot.get_bot()
        nodes = build_forward_nodes(articles, int(event.self_id))
        # 在转发卡片前发送前缀消息
        await matcher.send("💫 缇安开门找到最新公告啦！")
        await _send_forward(bot, event, nodes)
        return

    subcmd, rest = _parse_args(arg_text)

    # ── 搜索 ──
    if subcmd == "搜索":
        await _handle_search(event, rest)

    # ── 时间 ──
    elif subcmd == "时间":
        await _handle_time(event, rest)

    # ── 部门列表 ──
    elif subcmd == "部门列表":
        await _handle_dept_list()

    # ── 部门 ──
    elif subcmd == "部门":
        await _handle_dept(event, rest)

    # ── 订阅 ──
    elif subcmd == "订阅":
        await _handle_subscribe(event, rest)

    # ── 取消订阅 ──
    elif subcmd == "取消订阅":
        await _handle_unsubscribe(event, rest)

    # ── 我的订阅 ──
    elif subcmd == "我的订阅":
        await _handle_list(event)

    # ── 统计 ──
    elif subcmd == "统计":
        await _handle_stat()

    # ── 找群友 ──
    elif subcmd == "找群友":
        await _handle_find_member(event)

    # ── 强制推送（管理员） ──
    elif subcmd == "强制推送":
        if not _is_admin(event):
            await matcher.send("🔒 这个指令只有缇安的管理员才能用哦～")
            return
        await _handle_force_push()

    # ── 强制爬取（管理员） ──
    elif subcmd == "强制爬取":
        if not _is_admin(event):
            await matcher.send("🔒 这个指令只有缇安的管理员才能用哦～")
            return
        await _handle_force_scrape()

    # ── 帮助 ──
    elif subcmd == "帮助":
        await _handle_help()

    else:
        await matcher.send("😵 缇安没听懂这个指令哦～输入「缇安 帮助」看看所有用法吧！")


# ── 子命令实现 ──────────────────────────────────────────

async def _handle_search(event: MessageEvent, arg_text: str):
    if not arg_text:
        await matcher.send("😵 缇安没听懂这个指令哦～试试：缇安 搜索 奖学金")
        return

    keyword, time_range = parse_search_args(arg_text)
    if not keyword and not time_range:
        await matcher.send("🥺 缇安需要关键词才能搜索哦～")
        return

    articles = build_query(keyword, time_range)

    if not articles:
        await matcher.send("🥺 缇安翻遍了所有百界门，都没找到符合条件的公告呢～换个关键词试试吧！")
        return

    bot = nonebot.get_bot()
    nodes = build_forward_nodes(articles, int(event.self_id))

    # 根据搜索类型发送不同前缀
    if time_range and keyword:
        await matcher.send("🎡 缇安帮你锁定相关公告啦～")
    elif keyword.startswith("正则:"):
        await matcher.send("🔍 缇安用魔法正则帮你筛出符合条件公告咯～")
    elif "/" in keyword:
        await matcher.send("🌸 缇安挖到含任意一词的公告啦～")
    elif len(keyword.split()) > 1:
        await matcher.send("🎐 缇安精准锁定同时含这两个词的公告哦～")
    else:
        await matcher.send("🎀 缇安翻遍百界门找到相关公告啦～")

    await _send_forward(bot, event, nodes)


async def _handle_time(event: MessageEvent, arg_text: str):
    keyword, time_range = parse_search_args("时间 " + arg_text)
    if not time_range:
        await matcher.send("😵 时间格式不对哦～试试：缇安 时间 24.04.01~24.04.30")
        return

    articles = build_query("", time_range)
    if not articles:
        await matcher.send("🥺 缇安翻遍了所有百界门，该时间段没有公告呢～换个时间试试吧！")
        return

    bot = nonebot.get_bot()
    nodes = build_forward_nodes(articles, int(event.self_id))
    await matcher.send("✨ 缇安帮你筛选出该时间段公告咯～")
    await _send_forward(bot, event, nodes)


async def _handle_dept_list():
    depts = (
        Article.select(Article.source_dept)
        .where(Article.source_dept.is_null(False), Article.source_dept != "")
        .group_by(Article.source_dept)
        .order_by(Article.source_dept)
    )
    dept_list = [d.source_dept for d in depts if d.source_dept]
    if not dept_list:
        await matcher.send("🥺 缇安还没收集到部门数据呢～")
        return
    lines = ["📋 缇安整理好的部门列表来啦～", "━" * 16]
    for d in dept_list[:30]:
        cnt = Article.select().where(Article.source_dept == d).count()
        lines.append(f"  {d} ({cnt})")
    if len(dept_list) > 30:
        lines.append(f"  ... 共 {len(dept_list)} 个部门")
    lines.append("━" * 16)
    lines.append("输入「缇安 部门 名称」查看该部门公告")
    await matcher.send("\n".join(lines))


async def _handle_dept(event: MessageEvent, arg_text: str):
    if not arg_text:
        await matcher.send("😵 缇安需要部门名称哦～试试：缇安 部门 机电学院")
        return

    keyword, time_range = parse_search_args(arg_text)
    dept_name = keyword.strip()

    query = (
        Article.select()
        .where(Article.source_dept.contains(dept_name))
        .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
        .limit(MAX_RESULTS)
    )
    if time_range:
        start, end = time_range
        query = query.where(Article.published_at.between(start, end))

    articles = list(query)
    if not articles:
        await matcher.send("🤔 缇安没找到这个部门哦～输入「缇安 部门列表」看看所有部门名称吧！")
        return

    bot = nonebot.get_bot()
    nodes = build_forward_nodes(articles, int(event.self_id))

    if time_range:
        await matcher.send("💝 缇安筛出该时段该部门公告啦～")
    else:
        await matcher.send("💌 缇安为你搬来该部门最新公告～")

    await _send_forward(bot, event, nodes)


async def _handle_subscribe(event: MessageEvent, arg_text: str):
    if not arg_text:
        await matcher.send("😵 用法：缇安 订阅 分类 公告公示\n或：缇安 订阅 关键词 招聘")
        return

    parts = arg_text.split(maxsplit=1)
    sub_type = parts[0]
    value = parts[1] if len(parts) > 1 else ""
    target_type, target_id = _get_target(event)

    if sub_type == "分类":
        if value not in VALID_CATEGORIES:
            await matcher.send(f"😵 可选分类: {', '.join(VALID_CATEGORIES)}")
            return
        Subscription.insert(
            target_type=target_type,
            target_id=target_id,
            sub_type="category",
            sub_value=value,
        ).on_conflict_ignore().execute()
        await matcher.send("💖 缇安已帮你订阅！新消息第一时间敲你门哦～")

    elif sub_type == "关键词":
        if not value:
            await matcher.send("😵 缇安需要关键词哦～试试：缇安 订阅 关键词 招聘")
            return
        Subscription.insert(
            target_type=target_type,
            target_id=target_id,
            sub_type="keyword",
            sub_value=value,
        ).on_conflict_ignore().execute()
        await matcher.send("💓 缇安已帮你订阅关键词！有新公告立刻喊你～")

    else:
        await matcher.send("😵 订阅类型只能是「分类」或「关键词」哦～")


async def _handle_unsubscribe(event: MessageEvent, arg_text: str):
    if not arg_text or not arg_text.strip().isdigit():
        await matcher.send("😣 用法：缇安 取消订阅 序号\n输入「缇安 我的订阅」查看序号")
        return

    idx = int(arg_text.strip())
    target_type, target_id = _get_target(event)
    subs = list(
        Subscription.select()
        .where(
            Subscription.target_type == target_type,
            Subscription.target_id == target_id,
        )
        .order_by(Subscription.id)
    )
    if idx < 1 or idx > len(subs):
        await matcher.send("😣 这个订阅序号不对哦～输入「缇安 我的订阅」看看正确的序号吧！")
        return

    sub = subs[idx - 1]
    sub.delete_instance()
    await matcher.send(f"💔 缇安已帮你取消订阅 #{idx} [{sub.sub_value}]～后悔了随时再找我哦！")


async def _handle_list(event: MessageEvent):
    target_type, target_id = _get_target(event)
    subs = list(
        Subscription.select()
        .where(
            Subscription.target_type == target_type,
            Subscription.target_id == target_id,
        )
        .order_by(Subscription.id)
    )
    if not subs:
        await matcher.send("📋 缇安还没帮你记任何订阅哦～输入「缇安 订阅」开始吧！")
        return

    lines = ["📋 缇安帮你记的订阅清单哦～", "━" * 16]
    for i, s in enumerate(subs, 1):
        type_label = "分类" if s.sub_type == "category" else "关键词"
        lines.append(f"  {i}. [{type_label}] {s.sub_value}")
    lines.append("━" * 16)
    lines.append("输入「缇安 取消订阅 序号」取消")
    await matcher.send("\n".join(lines))


async def _handle_stat():
    total = Article.select().count()
    with_dept = Article.select().where(
        Article.source_dept.is_null(False), Article.source_dept != ""
    ).count()
    with_cat = Article.select().where(Article.category.is_null(False)).count()
    with_time = Article.select().where(Article.published_at.is_null(False)).count()
    sep = "━" * 16
    await matcher.send(
        f"📊 缇安整理的数据库小报告来啦～\n{sep}\n"
        f"总文章数: {total}\n"
        f"有部门信息: {with_dept}\n"
        f"有分类信息: {with_cat}\n"
        f"有时间信息: {with_time}\n{sep}"
    )


async def _handle_find_member(event: MessageEvent):
    """找群友：按发言次数加权随机抽取群成员。"""
    if not isinstance(event, GroupMessageEvent):
        await matcher.send("😵 缇安只能在群里找群友哦～")
        return

    group_id = str(event.group_id)
    records = list(
        GroupMessage.select()
        .where(GroupMessage.group_id == group_id, GroupMessage.message_count > 0)
    )
    if not records:
        await matcher.send("🥺 缇安还没记录到群友的发言呢～让大家多聊聊天吧！")
        return

    weights = [r.message_count for r in records]
    chosen = random.choices(records, weights=weights, k=1)[0]

    display_name = chosen.last_nickname or f"QQ:{chosen.user_id}"
    avatar_url = f"https://q.qlogo.cn/headimg_dl?dst_uin={chosen.user_id}&spec=2&img_type=jpg"

    bot = nonebot.get_bot()
    try:
        await bot.send(event, f"🌀 缇安为你开启百界门找到了 {display_name}！")
        await bot.send(event, MessageSegment.image(avatar_url))
    except Exception:
        await bot.send(event, f"🌀 缇安为你开启百界门找到了 {display_name}！(头像加载失败)")


async def _handle_force_push():
    """管理员强制推送：爬取 + 广播所有群 + 私聊订阅。"""
    await matcher.send("🚀 缇安开始强制推送！")
    try:
        from . import admin_force_push
        await admin_force_push()
        total = Article.select().count()
        await matcher.send(f"✅ 强制推送完成！数据库共 {total} 条文章。")
    except Exception as e:
        await matcher.send(f"😣 强制推送出错: {e}")


async def _handle_force_scrape():
    """管理员强制爬取：仅爬取不推送。"""
    await matcher.send("🚀 缇安冲去爬最新文章啦！")
    try:
        from . import admin_force_scrape
        count = await admin_force_scrape()
        total = Article.select().count()
        await matcher.send(f"✅ 爬取完成！新增 {count} 条，数据库共 {total} 条文章。")
    except Exception as e:
        await matcher.send(f"😣 爬取出错了: {e}")


async def _handle_help():
    sep = "━" * 16
    await matcher.send(
        f"💡 缇安把所有用法都写在这里啦～随时问我哦！\n{sep}\n"
        "缇安 — 最新公告\n"
        "缇安 时间 24.04.01~24.04.30 — 按时间筛选\n"
        "缇安 搜索 关键词 — 搜索（精确优先）\n"
        "缇安 搜索 机电 学院 — 同时含两词\n"
        "缇安 搜索 奖学金/评优 — 含任意一词\n"
        "缇安 搜索 正则:表达式 — 正则搜索\n"
        "缇安 搜索 奖学金 时间 24.01.01~24.12.31\n"
        "缇安 部门列表 — 查看所有部门\n"
        "缇安 部门 名称 — 按部门筛选\n"
        "缇安 找群友 — 随机抽群友\n"
        "缇安 统计 — 数据库统计\n"
        "缇安 订阅 分类 公告公示 — 订阅分类\n"
        "缇安 订阅 关键词 招聘 — 订阅关键词\n"
        "缇安 取消订阅 序号 — 取消订阅\n"
        "缇安 我的订阅 — 查看订阅\n"
        "缇安 帮助 — 此帮助\n"
        f"{sep}\n"
        "管理员专属:\n"
        "缇安 强制推送 — 爬取并广播所有群\n"
        "缇安 强制爬取 — 仅爬取不推送"
    )
