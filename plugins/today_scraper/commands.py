from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message

from .models import Article, Subscription
from .pusher import build_push_message, build_search_message
from .scraper import fetch_search_page, parse_search_page

VALID_CATEGORIES = {"公告公示", "新闻快讯"}


def _get_target(event: MessageEvent) -> tuple[str, str]:
    if isinstance(event, GroupMessageEvent):
        return "group", str(event.group_id)
    return "private", str(event.user_id)


# /today — 查看最新公告
cmd_today = on_command("today", priority=10, block=True)


@cmd_today.handle()
async def handle_today(event: MessageEvent, args: Message = CommandArg()):
    arg_text = args.extract_plain_text().strip()

    if not arg_text:
        # 显示最新公告
        articles = list(Article.select().order_by(Article.published_at.desc()).limit(10))
        if not articles:
            await cmd_today.finish("暂无公告数据，请等待定时采集完成。")
        items = [
            {"title": a.title, "source_dept": a.source_dept, "url": a.url}
            for a in articles
        ]
        await cmd_today.finish(build_push_message(items))
        return

    parts = arg_text.split(maxsplit=1)
    subcmd = parts[0]

    if subcmd == "search":
        await _handle_search(cmd_today, event, parts[1] if len(parts) > 1 else "")
    elif subcmd == "sub":
        await _handle_subscribe(cmd_today, event, parts[1] if len(parts) > 1 else "")
    elif subcmd == "unsub":
        await _handle_unsubscribe(cmd_today, event, parts[1] if len(parts) > 1 else "")
    elif subcmd == "list":
        await _handle_list(cmd_today, event)
    elif subcmd == "help":
        await _handle_help(cmd_today)


async def _handle_search(matcher, event: MessageEvent, arg_text: str):
    if not arg_text:
        await matcher.finish("用法: /today search <关键词> [页码]")

    parts = arg_text.rsplit(maxsplit=1)
    keyword = parts[0]
    page = 0
    if len(parts) > 1 and parts[1].isdigit():
        page = int(parts[1]) - 1  # user-facing is 1-based, internal is 0-based

    try:
        html = await fetch_search_page("https://today.hit.edu.cn", keyword, page)
        results = parse_search_page(html, "https://today.hit.edu.cn")
    except Exception:
        await matcher.finish("搜索失败，请稍后重试。")
        return

    msg = build_search_message(keyword, results, page, total=len(results) * 10)
    await matcher.finish(msg)


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

    lines = ["📋 我的订阅列表", "━" * 18]
    for i, s in enumerate(subs, 1):
        type_label = "分类" if s.sub_type == "category" else "关键词"
        lines.append(f"  {i}. [{type_label}] {s.sub_value}")
    lines.append("━" * 18)
    lines.append("/today unsub <序号> 取消订阅")
    await matcher.finish("\n".join(lines))


async def _handle_help(matcher):
    await matcher.finish(
        "📖 TodayHIT 命令帮助\n"
        "━" * 18 + "\n"
        "/today — 查看最新公告\n"
        "/today search <关键词> [页码] — 搜索文章\n"
        "/today sub category <分类> — 订阅分类\n"
        "  可选: 公告公示、新闻快讯\n"
        "/today sub keyword <词> — 订阅关键词\n"
        "/today unsub <序号> — 取消订阅\n"
        "/today list — 查看我的订阅\n"
        "/today help — 显示此帮助"
    )
