import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.params import CommandArg

from .models import Article, Subscription
from .search import MAX_RESULTS, build_forward_nodes, build_query, parse_search_args

VALID_CATEGORIES = {"公告公示", "新闻快讯"}


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
        # 回退到纯文本
        lines = []
        for n in nodes:
            for seg in n.get("data", {}).get("content", []):
                if seg.get("type") == "text":
                    lines.append(seg["data"]["text"])
        await bot.send(event, "\n---\n".join(lines))


# ── 命令注册 ────────────────────────────────────────────

cmd_today = on_command("today", priority=10, block=True)


@cmd_today.handle()
async def handle_today(event: MessageEvent, args: Message = CommandArg()):
    arg_text = args.extract_plain_text().strip()

    if not arg_text:
        # 最新公告（转发消息）
        articles = list(
            Article.select()
            .where(Article.published_at.is_null(False))
            .order_by(Article.published_at.desc())
            .limit(MAX_RESULTS)
        )
        if not articles:
            articles = list(Article.select().order_by(Article.id.desc()).limit(MAX_RESULTS))
        if not articles:
            await cmd_today.finish("暂无公告数据，请等待定时采集完成。")
        bot = nonebot.get_bot()
        nodes = build_forward_nodes(articles, int(event.self_id))
        await _send_forward(bot, event, nodes)
        return

    parts = arg_text.split(maxsplit=1)
    subcmd = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if subcmd == "search":
        await _handle_search(cmd_today, event, rest)
    elif subcmd == "dept":
        await _handle_dept(cmd_today, event, rest)
    elif subcmd == "sub":
        await _handle_subscribe(cmd_today, event, rest)
    elif subcmd == "unsub":
        await _handle_unsubscribe(cmd_today, event, rest)
    elif subcmd == "list":
        await _handle_list(cmd_today, event)
    elif subcmd == "stat":
        await _handle_stat(cmd_today)
    elif subcmd == "scrape":
        await _handle_scrape(cmd_today, event)
    elif subcmd == "help":
        await _handle_help(cmd_today)
    else:
        # 尝试当作时间过滤的最新公告：/today --time 24.01.01~24.05.11
        keyword, time_range = parse_search_args(arg_text)
        if time_range and not keyword:
            articles = build_query("", time_range)
            if not articles:
                await cmd_today.finish("该时间范围内暂无公告。")
            bot = nonebot.get_bot()
            nodes = build_forward_nodes(articles, int(event.self_id))
            await _send_forward(bot, event, nodes)
            return
        await _handle_help(cmd_today)


async def _handle_search(matcher, event: MessageEvent, arg_text: str):
    """高级搜索：精确优先 + AND/OR/REGEX + 时间过滤。"""
    if not arg_text:
        await matcher.finish(
            "用法: /today search <关键词>\n"
            "多词AND: 机电 学院\n"
            "OR: 奖学金|评优\n"
            "正则: re:2024年.*评选\n"
            "时间: --time 24.01.01~24.12.31"
        )

    keyword, time_range = parse_search_args(arg_text)
    if not keyword and not time_range:
        await matcher.finish("请输入搜索关键词或时间范围。")

    articles = build_query(keyword, time_range)

    if not articles:
        hint = f'搜索"{keyword}"' if keyword else "该时间范围"
        await matcher.finish(f"{hint} - 无结果\n试试其他关键词？")

    bot = nonebot.get_bot()
    nodes = build_forward_nodes(articles, int(event.self_id))
    desc = f'搜索"{keyword}"' if keyword else "时间筛选"
    nonebot.logger.info(f"{desc}: {len(articles)} 条结果")
    await _send_forward(bot, event, nodes)


async def _handle_dept(matcher, event: MessageEvent, arg_text: str):
    """按部门筛选，输出转发消息。"""
    if not arg_text:
        depts = (
            Article.select(Article.source_dept)
            .where(Article.source_dept.is_null(False), Article.source_dept != "")
            .group_by(Article.source_dept)
            .order_by(Article.source_dept)
        )
        dept_list = [d.source_dept for d in depts if d.source_dept]
        if not dept_list:
            await matcher.finish("暂无部门数据")
        lines = ["📋 部门列表（部分）", "━" * 16]
        for d in dept_list[:30]:
            cnt = Article.select().where(Article.source_dept == d).count()
            lines.append(f"  {d} ({cnt})")
        if len(dept_list) > 30:
            lines.append(f"  ... 共 {len(dept_list)} 个部门")
        lines.append("━" * 16)
        lines.append("/today dept <部门名> 查看该部门公告")
        await matcher.finish("\n".join(lines))
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
        await matcher.finish(f'部门"{dept_name}" - 无结果\n使用 /today dept 查看所有部门')

    bot = nonebot.get_bot()
    nodes = build_forward_nodes(articles, int(event.self_id))
    await _send_forward(bot, event, nodes)


async def _handle_stat(matcher):
    """显示数据库统计。"""
    total = Article.select().count()
    with_dept = Article.select().where(
        Article.source_dept.is_null(False), Article.source_dept != ""
    ).count()
    with_cat = Article.select().where(Article.category.is_null(False)).count()
    with_time = Article.select().where(Article.published_at.is_null(False)).count()
    sep = "━" * 16
    await matcher.finish(
        f"📊 数据库统计\n{sep}\n"
        f"总文章数: {total}\n"
        f"有部门信息: {with_dept}\n"
        f"有分类信息: {with_cat}\n"
        f"有时间信息: {with_time}\n{sep}"
    )


async def _handle_subscribe(matcher, event: MessageEvent, arg_text: str):
    if not arg_text:
        await matcher.finish(
            "用法:\n"
            "  /today sub category 公告公示\n"
            "  /today sub keyword <关键词>"
        )

    parts = arg_text.split(maxsplit=1)
    sub_type = parts[0]
    target_type, target_id = _get_target(event)

    if sub_type == "category":
        value = parts[1] if len(parts) > 1 else ""
        if value not in VALID_CATEGORIES:
            await matcher.finish(f"可选分类: {', '.join(VALID_CATEGORIES)}")
        Subscription.insert(
            target_type=target_type,
            target_id=target_id,
            sub_type="category",
            sub_value=value,
        ).on_conflict_ignore().execute()
        await matcher.finish(f"已订阅分类: {value}")

    elif sub_type == "keyword":
        value = parts[1] if len(parts) > 1 else ""
        if not value:
            await matcher.finish("请输入要订阅的关键词")
        Subscription.insert(
            target_type=target_type,
            target_id=target_id,
            sub_type="keyword",
            sub_value=value,
        ).on_conflict_ignore().execute()
        await matcher.finish(f"已订阅关键词: {value}")

    else:
        await matcher.finish("订阅类型: category（分类）或 keyword（关键词）")


async def _handle_unsubscribe(matcher, event: MessageEvent, arg_text: str):
    if not arg_text or not arg_text.isdigit():
        await matcher.finish("用法: /today unsub <序号>\n使用 /today list 查看订阅列表")

    idx = int(arg_text)
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
        await matcher.finish(f"序号无效，共有 {len(subs)} 条订阅")

    sub = subs[idx - 1]
    sub.delete_instance()
    await matcher.finish(f"已取消订阅 #{idx}: [{sub.sub_type}] {sub.sub_value}")


async def _handle_list(matcher, event: MessageEvent):
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
        await matcher.finish("暂无订阅。使用 /today sub 添加订阅。")

    lines = ["📋 我的订阅列表", "━" * 16]
    for i, s in enumerate(subs, 1):
        type_label = "分类" if s.sub_type == "category" else "关键词"
        lines.append(f"  {i}. [{type_label}] {s.sub_value}")
    lines.append("━" * 16)
    lines.append("/today unsub <序号> 取消订阅")
    await matcher.finish("\n".join(lines))


async def _handle_scrape(matcher, event: MessageEvent):
    """手动触发爬取。"""
    await matcher.send("开始爬取最新文章...")
    try:
        from . import scrape_and_push
        await scrape_and_push()
        total = Article.select().count()
        await matcher.finish(f"爬取完成！数据库共 {total} 条文章。")
    except Exception as e:
        await matcher.finish(f"爬取出错: {e}")


async def _handle_help(matcher):
    sep = "━" * 16
    await matcher.finish(
        f"📖 TodayHIT 命令帮助\n{sep}\n"
        "/today — 最新公告（转发消息卡片）\n"
        "/today search <关键词> — 搜索（精确优先）\n"
        "/today search 机电 学院 — AND 搜索\n"
        "/today search 奖学金|评优 — OR 搜索\n"
        "/today search re:正则 — 正则搜索\n"
        "/today search XX --time 24.01.01~24.12.31\n"
        "/today dept — 查看所有部门\n"
        "/today dept <部门名> — 按部门筛选\n"
        "/today stat — 数据库统计\n"
        "/today scrape — 手动爬取最新文章\n"
        "/today sub category <分类> — 订阅分类\n"
        "/today sub keyword <词> — 订阅关键词\n"
        "/today unsub <序号> — 取消订阅\n"
        "/today list — 我的订阅\n"
        "/today help — 此帮助"
    )
