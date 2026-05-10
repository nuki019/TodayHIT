from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent

help_cmd = on_command("todayhelp", aliases={"today帮助"}, priority=1, block=True)


@help_cmd.handle()
async def handle_help(event: MessageEvent):
    await help_cmd.finish(
        "\U0001f4d6 TodayHIT QQ Bot 使用指南\n"
        "━" * 20
        + "\n\n"
        "\U0001f514 功能概览\n"
        "  • 定时抓取今日哈工大最新公告\n"
        "  • 按分类/关键词订阅推送\n"
        "  • 在线搜索站内文章\n\n"
        "\U0001f4dd 命令列表\n"
        "  /today — 查看最新公告\n"
        "  /today search <关键词> — 搜索文章\n"
        "  /today sub category <分类> — 订阅分类\n"
        "  /today sub keyword <词> — 订阅关键词\n"
        "  /today unsub <序号> — 取消订阅\n"
        "  /today list — 查看我的订阅\n"
        "  /today help — 命令帮助\n\n"
        "\U0001f4cc 订阅分类可选: 公告公示、新闻快讯\n"
        "⏰ 推送频率: 每 4 小时自动检查"
    )
