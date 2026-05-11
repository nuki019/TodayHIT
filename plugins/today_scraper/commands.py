from datetime import datetime

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.params import CommandArg

from .models import Article, Subscription
from .scraper import fetch_search_page, parse_search_page

VALID_CATEGORIES = {"公告公示", "新闻快讯"}


def _get_target(event: MessageEvent) -> tuple[str, str]:
    if isinstance(event, GroupMessageEvent):
        return "group", str(event.group_id)
    return "private", str(event.user_id)


def _format_time(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def _format_articles(articles: list, title: str) -> str:
    """格式化文章列表。"""
    if not articles:
        return f"{title}\n━━━━━━━━━━\n暂无数据"
    lines = [title, "━" * 16]
    for i, a in enumerate(articles, 1):
        dept = a.source_dept or "未知"
        time_str = _format_time(a.published_at) or ""
        lines.append(f"{i}. {a.title}")
        lines.append(f"   {dept} | {time_str}")
        lines.append(f"   {a.url}")
    lines.append("━" * 16)
    lines.append(f"共 {len(articles)} 条")
    return "\n".join(lines)


cmd_today = on_command("today", priority=10, block=True)


@cmd_today.handle()
async def handle_today(event: MessageEvent, args: Message = CommandArg()):
    arg_text = args.extract_plain_text().strip()

    if not arg_text:
        articles = list(
            Article.select()
            .where(Article.published_at.is_null(False))
            .order_by(Article.published_at.desc())
            .limit(10)
        )
        if not articles:
            articles = list(Article.select().order_by(Article.id.desc()).limit(10))
        if not articles:
            await cmd_today.finish("暂无公告数据，请等待定时采集完成。")
        await cmd_today.finish(_format_articles(articles, "📢 最新公告"))
        return

    parts = arg_text.split(maxsplit=1)
    subcmd = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if subcmd == "search":
        await _handle_search(cmd_today, rest)
    elif subcmd == "dept":
        await _handle_dept(cmd_today, rest)
    elif subcmd == "sub":
        await _handle_subscribe(cmd_today, event, rest)
    elif subcmd == "unsub":
        await _handle_unsubscribe(cmd_today, event, rest)
    elif subcmd == "list":
        await _handle_list(cmd_today, event)
    elif subcmd == "stat":
        await _handle_stat(cmd_today)
    elif subcmd == "help":
        await _handle_help(cmd_today)
    else:
        await _handle_help(cmd_today)


async def _handle_search(matcher, arg_text: str):
    """在本地数据库搜索标题。"""
    if not arg_text:
        await matcher.finish("用法: /today search <关键词>")

    keyword = arg_text.strip()
    articles = list(
        Article.select()
        .where(Article.title.contains(keyword))
        .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
        .limit(10)
    )

    if not articles:
        await matcher.finish(f'搜索"{keyword}" - 无结果\n试试其他关键词？')

    await matcher.finish(_format_articles(articles, f'🔍 搜索"{keyword}"'))


async def _handle_dept(matcher, arg_text: str):
    """按部门筛选。"""
    if not arg_text:
        # 显示所有部门列表
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

    dept_name = arg_text.strip()
    articles = list(
        Article.select()
        .where(Article.source_dept.contains(dept_name))
        .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
        .limit(10)
    )

    if not articles:
        await matcher.finish(f'部门"{dept_name}" - 无结果\n使用 /today dept 查看所有部门')

    await matcher.finish(_format_articles(articles, f'📌 {dept_name} 相关公告'))


async def _handle_stat(matcher):
    """显示数据库统计。"""
    total = Article.select().count()
    with_dept = Article.select().where(Article.source_dept.is_null(False), Article.source_dept != "").count()
    with_cat = Article.select().where(Article.category.is_null(False)).count()
    await matcher.finish(
        f"📊 数据库统计\n"
        f"━" * 16 + "\n"
        f"总文章数: {total}\n"
        f"有部门信息: {with_dept}\n"
        f"有分类信息: {with_cat}\n"
        f"━" * 16
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


async def _handle_help(matcher):
    await matcher.finish(
        "📖 TodayHIT 命令帮助\n"
        "━" * 16 + "\n"
        "/today — 最新公告（按时间排序）\n"
        "/today search <关键词> — 标题搜索\n"
        "/today dept — 查看所有部门\n"
        "/today dept <部门名> — 按部门筛选\n"
        "/today stat — 数据库统计\n"
        "/today sub category <分类> — 订阅分类\n"
        "/today sub keyword <词> — 订阅关键词\n"
        "/today unsub <序号> — 取消订阅\n"
        "/today list — 我的订阅\n"
        "/today help — 此帮助"
    )
