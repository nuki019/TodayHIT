from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import MessageEvent

help_cmd = on_keyword("缇安帮助", priority=1, block=True)


@help_cmd.handle()
async def handle_help(event: MessageEvent):
    sep = "━" * 20
    await help_cmd.finish(
        f"💡 缇安使用指南\n{sep}\n\n"
        "📌 功能概览\n"
        "  • 定时抓取今日哈工大最新公告\n"
        "  • 按分类/关键词订阅推送\n"
        "  • 在线搜索站内文章\n\n"
        "📝 命令列表\n"
        "  缇安 — 最新公告\n"
        "  缇安 搜索 关键词 — 搜索文章\n"
        "  缇安 部门 部门名 — 按部门筛选\n"
        "  缇安 订阅 分类/关键词 — 订阅\n"
        "  缇安 取消订阅 序号 — 取消\n"
        "  缇安 我的订阅 — 查看订阅\n"
        "  缇安 统计 — 数据统计\n"
        "  缇安 爬取 — 手动更新\n"
        "  缇安 帮助 — 详细帮助\n\n"
        "📌 订阅分类: 公告公示、新闻快讯\n"
        "⏰ 推送频率: 每 4 小时自动检查"
    )
