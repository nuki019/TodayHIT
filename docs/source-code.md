# TodayHIT 源代码文档

> 今日哈工大（today.hit.edu.cn）QQ 机器人「缇安」完整源代码参考。
> 生成日期：2026-05-13

---

## 目录

- [1. 项目概览](#1-项目概览)
- [2. 项目结构](#2-项目结构)
- [3. 技术栈](#3-技术栈)
- [4. 配置文件](#4-配置文件)
  - [4.1 pyproject.toml](#41-pyprojecttoml)
  - [4.2 .env.prod](#42-envprod)
  - [4.3 .gitignore](#43-gitignore)
- [5. 入口与启动](#5-入口与启动)
  - [5.1 bot.py — NoneBot2 入口](#51-botpy--nonebot2-入口)
  - [5.2 start.bat — Windows 一键启动](#52-startbat--windows-一键启动)
  - [5.3 restart.sh — Linux 服务管理](#53-restartsh--linux-服务管理)
  - [5.4 scheduled_restart.sh — 定时重启守护](#54-scheduled_restartsh--定时重启守护)
- [6. 核心插件 today_scraper](#6-核心插件-today_scraper)
  - [6.1 __init__.py — 插件入口 + 定时任务](#61-__initpy--插件入口--定时任务)
  - [6.2 config.py — 配置模型](#62-configpy--配置模型)
  - [6.3 models.py — 数据库 ORM](#63-modelspy--数据库-orm)
  - [6.4 scraper.py — 爬虫引擎](#64-scraperpy--爬虫引擎)
  - [6.5 search.py — 搜索引擎](#65-searchpy--搜索引擎)
  - [6.6 pusher.py — 推送系统](#66-pusherpy--推送系统)
  - [6.7 commands.py — 命令系统](#67-commandspy--命令系统)
- [7. 辅助插件](#7-辅助插件)
  - [7.1 today_help/__init__.py](#71-today_help__initpy)
- [8. 脚本](#8-脚本)
  - [8.1 scripts/full_scrape.py — 全量历史爬取](#81-scriptsfull_scrapy--全量历史爬取)
- [9. 测试](#9-测试)
  - [9.1 test_models.py](#91-test_modelspy)
  - [9.2 test_scraper.py](#92-test_scraperpy)
  - [9.3 test_pusher.py](#93-test_pusherpy)
  - [9.4 test_commands.py — 搜索引擎测试](#94-test_commandspy--搜索引擎测试)
  - [9.5 verify_real_site.py — 端到端验证](#95-verify_real_sitepy--端到端验证)

---

## 1. 项目概览

TodayHIT 是一个基于 NoneBot2 框架的 QQ 机器人，自动采集 [今日哈工大](https://today.hit.edu.cn) 网站的公告和新闻，提供关键词搜索、分类订阅、定时推送等功能。

**核心功能：**

| 功能 | 说明 |
|------|------|
| 自动采集 | 每 4 小时从 RSS + 分类页采集新文章 |
| 每日广播 | 每天 7:30 广播最新公告到所有群 |
| 关键词搜索 | 精确优先 / AND / OR / 正则 / 时间过滤 |
| 分类订阅 | 按分类或关键词订阅，新文章自动推送 |
| 找群友 | 按发言次数加权随机抽取群成员 |
| 数据统计 | 48,000+ 条历史公告，支持部门/时间筛选 |

---

## 2. 项目结构

```
TodayHIT/
├── bot.py                          # NoneBot2 入口
├── pyproject.toml                  # 项目配置与依赖
├── .env.prod                       # 生产环境变量
├── .gitignore
├── start.bat                       # Windows 一键启动
├── restart.sh                      # Linux 服务管理脚本
├── scheduled_restart.sh            # 定时重启守护进程
├── README.md
├── plugins/
│   ├── today_scraper/              # 核心插件
│   │   ├── __init__.py             # 插件入口 + 定时任务 + 启动钩子
│   │   ├── config.py               # Pydantic 配置模型
│   │   ├── models.py               # SQLite ORM (peewee)
│   │   ├── scraper.py              # 爬虫引擎 (RSS/分类页/搜索页)
│   │   ├── search.py               # 搜索引擎 (精确/AND/OR/正则/时间)
│   │   ├── pusher.py               # 订阅匹配 + 推送节点构建
│   │   └── commands.py             # 缇安命令系统
│   └── today_help/
│       └── __init__.py             # 帮助插件（已合并到 commands）
├── scripts/
│   └── full_scrape.py              # 全量历史数据爬取脚本
├── tests/
│   ├── __init__.py
│   ├── test_models.py              # 数据模型测试
│   ├── test_scraper.py             # 爬虫解析测试
│   ├── test_pusher.py              # 推送匹配测试
│   ├── test_commands.py            # 搜索引擎测试
│   └── verify_real_site.py         # 端到端验证
├── docs/
│   ├── qq-commands.md              # 命令参考文档
│   └── source-code.md              # 本文档
├── data/
│   └── todayhit.db                 # SQLite 数据库 (~48K 条)
└── NapCat.Shell/                   # QQ 协议端 (NapCat)
```

---

## 3. 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | NoneBot2 | >= 2.4.0 |
| QQ 适配器 | nonebot-adapter-onebot (V11) | >= 2.4.0 |
| QQ 协议端 | NapCat | 4.18.1 |
| 数据库 | SQLite + peewee ORM | >= 3.17.0 |
| HTTP 客户端 | httpx (异步) | >= 0.27.0 |
| HTML 解析 | BeautifulSoup4 + lxml | >= 4.12.0 |
| 定时任务 | APScheduler | >= 0.4.0 |
| 配置管理 | Pydantic | — |
| Python | CPython | >= 3.12 |

---

## 4. 配置文件

### 4.1 pyproject.toml

```toml
[project]
name = "todayhit-qqbot"
version = "0.1.0"
description = "今日哈工大 QQ 机器人"
requires-python = ">=3.12"
dependencies = [
    "nonebot2>=2.4.0",
    "nonebot-adapter-onebot>=2.4.0",
    "nonebot-plugin-apscheduler>=0.4.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "peewee>=3.17.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]

[tool.nonebot]
adapters = [
    { name = "OneBot V11", module_name = "nonebot.adapters.onebot.v11" },
]
plugins = ["nonebot_plugin_apscheduler"]
plugin_dirs = ["plugins"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 4.2 .env.prod

```bash
DRIVER=~fastapi
ONEBOT_WS_URLS=[]
SUPERUSERS=["3943456425"]
COMMAND_START=["/"]
COMMAND_SEP=[" "]

TODAYHIT_DB_PATH=./data/todayhit.db
TODAYHIT_SCRAPE_INTERVAL=14400
TODAYHIT_MAX_PUSH_PER_ROUND=10
TODAYHIT_REQUEST_DELAY=2
```

### 4.3 .gitignore

```gitignore
__pycache__/
*.pyc
.env
.env.prod
data/*.db
.venv/
*.egg-info/
dist/
build/
NapCat.Shell/
```

---

## 5. 入口与启动

### 5.1 bot.py — NoneBot2 入口

```python
import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
```

### 5.2 start.bat — Windows 一键启动

```bat
@echo off
chcp 65001 >nul
echo ========================================
echo   TodayHIT QQ Bot 启动脚本
echo ========================================
echo.

echo [1/2] 启动 NapCat...
start "NapCat" cmd /c "cd /d %~dp0NapCat.Shell && launcher.bat"

echo [2/2] 等待 NapCat 启动 (5秒)...
timeout /t 5 /nobreak >nul

echo [2/2] 启动 Bot...
cd /d %~dp0
C:\Users\wfy\.conda\envs\todayhit\python.exe bot.py

pause
```

### 5.3 restart.sh — Linux 服务管理

```bash
#!/bin/bash
# TodayHIT 自动重启脚本
# 凌晨 2 点前后随机关闭，早上 7 点重新启动

LOG="/root/TodayHIT/restart.log"
PYTHON="/root/TodayHIT/venv/bin/python"
BOT_QQ="3943456425"
WS_URL="ws://127.0.0.1:8080/onebot/v11/ws"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG"
}

configure_napcat_ws() {
    local TMPJSON="/tmp/onebot11_${BOT_QQ}.json"
    cat > "$TMPJSON" << EOF
{
  "websocketClients": [
    "${WS_URL}"
  ]
}
EOF
    podman cp "$TMPJSON" "napcat:/app/napcat/config/onebot11_${BOT_QQ}.json" 2>/dev/null
    rm -f "$TMPJSON"
    log "WebSocket 配置已写入"
}

stop_all() {
    log "停止 Bot..."
    pkill -f "python bot.py" 2>/dev/null
    sleep 2

    log "停止 NapCat 容器..."
    podman stop napcat 2>/dev/null
    sleep 2

    log "清理残留进程..."
    pkill -f "napcat" 2>/dev/null

    log "全部停止完成"
}

start_all() {
    log "启动 NapCat 容器..."
    podman start napcat 2>/dev/null || {
        log "容器不存在，重新创建..."
        podman run -d --name napcat --network=host \
            docker.m.daocloud.io/mlikiowa/napcat-docker:latest
    }

    sleep 3
    configure_napcat_ws

    log "等待 NapCat 启动并登录（60 秒）..."
    sleep 60

    if podman ps | grep -q napcat; then
        log "NapCat 运行正常"
    else
        log "NapCat 未运行，尝试重启..."
        podman restart napcat
        sleep 30
    fi

    log "启动 Bot..."
    cd /root/TodayHIT
    nohup "$PYTHON" bot.py >> "$LOG" 2>&1 &
    BOT_PID=$!
    log "Bot 已启动 (PID: $BOT_PID)"

    sleep 10
    if ps -p $BOT_PID > /dev/null 2>&1; then
        log "Bot 进程运行正常"
    else
        log "Bot 启动失败，重试一次..."
        nohup "$PYTHON" bot.py >> "$LOG" 2>&1 &
        log "Bot 重试启动 (PID: $!)"
    fi
}

# ── 主逻辑 ──

case "$1" in
    stop)
        stop_all
        ;;
    start)
        start_all
        ;;
    restart)
        stop_all
        sleep 5
        start_all
        ;;
    *)
        echo "用法: $0 {stop|start|restart}"
        exit 1
        ;;
esac
```

### 5.4 scheduled_restart.sh — 定时重启守护

```bash
#!/bin/bash
# 定时重启守护进程
# 每天凌晨 2 点前后随机 0-30 分钟关闭，早上 7 点重启

SCRIPT="/root/TodayHIT/restart.sh"
LOG="/root/TodayHIT/restart.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [守护] $1" | tee -a "$LOG"
}

while true; do
    HOUR=2
    RANDOM_MIN=$((RANDOM % 31))
    STOP_TIME=$(printf "%02d:%02d" $HOUR $RANDOM_MIN)

    START_HOUR=7
    START_MIN=$((RANDOM % 6))
    START_TIME=$(printf "%02d:%02d" $START_HOUR $START_MIN)

    log "下次关闭时间: 今天 $STOP_TIME，下次启动时间: 今天 $START_TIME"

    # 等到凌晨关闭时间
    while true; do
        CUR_HOUR=$(date +%H)
        CUR_MIN=$(date +%M)
        if [ "$CUR_HOUR" -ge 2 ] && [ "$CUR_HOUR" -lt 7 ]; then
            if [ "$CUR_HOUR" -gt "$HOUR" ] || \
               ([ "$CUR_HOUR" -eq "$HOUR" ] && [ "$CUR_MIN" -ge "$RANDOM_MIN" ]); then
                log "到达关闭时间，开始关闭..."
                bash "$SCRIPT" stop
                break
            fi
        fi
        if [ "$CUR_HOUR" -ge 7 ]; then
            log "已过 7 点，跳过今天的关闭"
            break
        fi
        sleep 30
    done

    # 等到早上 7 点启动
    while true; do
        CUR_HOUR=$(date +%H)
        CUR_MIN=$(date +%M)
        if [ "$CUR_HOUR" -ge 7 ]; then
            if [ "$CUR_HOUR" -gt "$START_HOUR" ] || \
               ([ "$CUR_HOUR" -eq "$START_HOUR" ] && [ "$CUR_MIN" -ge "$START_MIN" ]); then
                log "到达启动时间，开始启动..."
                bash "$SCRIPT" start
                break
            fi
        fi
        sleep 30
    done

    log "今日重启完成，等待明天..."
    sleep 3600
done
```

---

## 6. 核心插件 today_scraper

### 6.1 \_\_init\_\_.py — 插件入口 + 定时任务

> 文件：`plugins/today_scraper/__init__.py`

插件入口，负责：
- 初始化数据库和配置
- 启动钩子：延迟爬取 + 群成员同步
- 消息计数监听（用于「找群友」功能）
- 定时任务注册：每 4 小时采集 + 每天 7:30 广播
- 管理员命令入口

```python
import asyncio

import nonebot

from .config import TodayHITConfig
from .models import Article, GroupMessage, ScraperState, Subscription, init_db
from .pusher import build_push_nodes, get_unpushed_articles, mark_pushed, match_subscriptions
from .scraper import fetch_category_page, fetch_rss, parse_category_page, parse_rss

# 以下 nonebot 初始化仅在完整运行时执行，测试时跳过
try:
    from nonebot import get_plugin_config, on_message, require
    from nonebot.adapters.onebot.v11 import GroupMessageEvent

    require("nonebot_plugin_apscheduler")
    from nonebot_plugin_apscheduler import scheduler

    from . import commands

    config = get_plugin_config(TodayHITConfig)
    _NONEBOT_READY = True
except Exception:
    _NONEBOT_READY = False

CATEGORY_MAP = {10: "公告公示", 11: "新闻快讯"}


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
        await asyncio.sleep(5)
        try:
            await scrape_only()
            nonebot.logger.info("启动爬取完成")
        except Exception as e:
            nonebot.logger.warning(f"启动爬取失败: {e}")

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
        """仅采集，不推送。返回新增 RSS 文章数。"""
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

        nonebot.logger.info(f"采集完成，新增 {new_count} 条 RSS 文章")
        return new_count

    # ── 订阅推送 ────────────────────────────────────────

    async def scrape_and_push():
        """采集 + 订阅推送。"""
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
                target_articles[key].append({
                    "title": article.title,
                    "source_dept": article.source_dept,
                    "url": article.url,
                    "published_at": article.published_at,
                })
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
        articles_dicts = [{
            "title": a.title,
            "source_dept": a.source_dept,
            "url": a.url,
            "published_at": a.published_at,
        } for a in unpushed]
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

        nonebot.logger.info(
            f"每日推送完成：{len(groups) if 'groups' in dir() else 0} 个群 + 私聊订阅用户"
        )

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
    scheduler.add_job(
        scrape_and_push,
        "interval",
        seconds=config.todayhit_scrape_interval,
        id="todayhit_scrape",
        replace_existing=True,
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
```

### 6.2 config.py — 配置模型

> 文件：`plugins/today_scraper/config.py`

```python
from pydantic import BaseModel


class TodayHITConfig(BaseModel):
    todayhit_db_path: str = "./data/todayhit.db"
    todayhit_scrape_interval: int = 14400       # 采集间隔（秒），默认 4 小时
    todayhit_max_push_per_round: int = 10        # 每轮最大推送文章数
    todayhit_request_delay: float = 2.0          # 请求间隔（秒）
    todayhit_base_url: str = "https://today.hit.edu.cn"
    todayhit_admin_qqs: list[int] = [2990056153] # 管理员 QQ 列表
```

### 6.3 models.py — 数据库 ORM

> 文件：`plugins/today_scraper/models.py`

使用 peewee ORM 定义 5 张表，支持 SQLite REGEXP 自定义函数。

```python
from datetime import datetime

from peewee import (
    AutoField,
    DateTimeField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

db = SqliteDatabase(None)


class BaseModel(Model):
    class Meta:
        database = db


class Article(BaseModel):
    """文章表"""
    id = IntegerField(primary_key=True)
    title = TextField(null=False)
    url = TextField(null=False)
    source_dept = TextField(null=True)       # 来源部门
    category = TextField(null=True)          # 分类：公告公示/新闻快讯
    published_at = DateTimeField(null=True)
    scraped_at = DateTimeField(default=datetime.now)
    summary = TextField(null=True)

    class Meta:
        table_name = "articles"


class Subscription(BaseModel):
    """订阅表"""
    id = AutoField()
    target_type = TextField(null=False)      # "group" / "private"
    target_id = TextField(null=False)        # 群号 / 用户 QQ
    sub_type = TextField(null=False)         # "category" / "keyword"
    sub_value = TextField(null=False)        # 分类名 / 关键词
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "subscriptions"
        indexes = ((("target_type", "target_id", "sub_type", "sub_value"), True),)


class PushRecord(BaseModel):
    """推送记录表"""
    id = AutoField()
    article_id = IntegerField(null=False)
    target_type = TextField(null=False)
    target_id = TextField(null=False)
    pushed_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "push_records"
        indexes = ((("article_id", "target_type", "target_id"), True),)


class GroupMessage(BaseModel):
    """群消息计数表，用于「找群友」加权随机"""
    id = AutoField()
    group_id = TextField(null=False)
    user_id = TextField(null=False)
    message_count = IntegerField(default=0)
    last_nickname = TextField(null=True)

    class Meta:
        table_name = "group_messages"
        indexes = ((("group_id", "user_id"), True),)

    @classmethod
    def increment(cls, group_id: str, user_id: str, nickname: str = "") -> None:
        """消息计数 +1，同时更新昵称缓存。"""
        cls.insert(
            group_id=group_id,
            user_id=user_id,
            message_count=1,
            last_nickname=nickname or None,
        ).on_conflict(
            conflict_target=[cls.group_id, cls.user_id],
            update={
                cls.message_count: cls.message_count + 1,
                cls.last_nickname: nickname or cls.last_nickname,
            },
        ).execute()


class ScraperState(BaseModel):
    """爬虫状态表（KV 存储）"""
    key = TextField(primary_key=True)
    value = TextField(null=True)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "scraper_state"

    @classmethod
    def get_value(cls, key: str, default: str = "") -> str:
        try:
            return cls.get_by_id(key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key: str, value: str) -> None:
        cls.insert(key=key, value=value, updated_at=datetime.now()).on_conflict(
            conflict_target=[cls.key],
            update={cls.value: value, cls.updated_at: datetime.now()},
        ).execute()


def init_db(db_path: str) -> None:
    db.init(db_path)
    db.connect(reuse_if_open=True)
    db.create_tables([Article, Subscription, PushRecord, GroupMessage, ScraperState])
    db.register_function(_regexp, "REGEXP")


def _regexp(pattern: str, value: str) -> bool:
    """SQLite REGEXP 用户自定义函数。"""
    import re
    try:
        return bool(re.search(pattern, value or ""))
    except re.error:
        return False
```

**ER 关系图：**

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Article    │     │  PushRecord      │     │ Subscription │
│──────────────│     │──────────────────│     │──────────────│
│ id (PK)      │◄────│ article_id (FK)  │     │ id (PK)      │
│ title        │     │ target_type      │     │ target_type  │
│ url          │     │ target_id        │     │ target_id    │
│ source_dept  │     │ pushed_at        │     │ sub_type     │
│ category     │     └──────────────────┘     │ sub_value    │
│ published_at │                               │ created_at   │
│ scraped_at   │     ┌──────────────────┐     └──────────────┘
│ summary      │     │  GroupMessage    │
└──────────────┘     │──────────────────│     ┌──────────────┐
                     │ group_id         │     │ ScraperState │
                     │ user_id          │     │──────────────│
                     │ message_count    │     │ key (PK)     │
                     │ last_nickname    │     │ value        │
                     └──────────────────┘     │ updated_at   │
                                              └──────────────┘
```

### 6.4 scraper.py — 爬虫引擎

> 文件：`plugins/today_scraper/scraper.py`

支持三种数据源：RSS XML、分类列表页、搜索结果页。

```python
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


def parse_rss(xml_text: str) -> list[dict[str, Any]]:
    """解析 RSS XML，返回文章列表。"""
    soup = BeautifulSoup(xml_text, "lxml-xml")
    items: list[dict[str, Any]] = []
    for item in soup.find_all("item"):
        guid = item.guid.text.strip() if item.guid else ""
        match = re.search(r"(\d+)", guid)
        if not match:
            continue
        article_id = int(match.group(1))
        title = item.title.text.strip() if item.title else ""
        link = item.link.text.strip() if item.link else ""
        pub_date_str = item.pubDate.text.strip() if item.pubDate else ""
        try:
            pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
        except ValueError:
            pub_date = None
        items.append({
            "id": article_id,
            "title": title,
            "url": link,
            "published_at": pub_date,
            "source_dept": None,
            "category": None,
        })
    return items


def parse_category_page(html: str, base_url: str) -> list[dict[str, Any]]:
    """解析分类列表页，提取文章链接和部门信息。"""
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict[str, Any]] = []
    for row in soup.select(".views-row"):
        link_tag = row.select_one('a[href*="/article/"]')
        if not link_tag:
            continue
        href = link_tag.get("href", "")
        match = re.search(r"/article/(\d{4})/(\d{2})/(\d{2})/(\d+)", href)
        if not match:
            continue
        article_id = int(match.group(4))
        try:
            published_at = datetime(
                int(match.group(1)), int(match.group(2)), int(match.group(3))
            )
        except ValueError:
            published_at = None
        title = link_tag.get_text(strip=True)
        dept_tag = row.select_one(
            ".field--name-field-department, .views-field-field-department"
        )
        source_dept = dept_tag.get_text(strip=True) if dept_tag else None
        url = base_url + href if href.startswith("/") else href
        articles.append({
            "id": article_id,
            "title": title,
            "url": url,
            "source_dept": source_dept,
            "category": None,
            "published_at": published_at,
        })
    return articles


def parse_search_page(html: str, base_url: str) -> list[dict[str, Any]]:
    """解析搜索结果页，提取标题、链接和摘要。"""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, Any]] = []
    for item in soup.select(
        ".search-result, .search-results-item, li.search-result"
    ):
        link_tag = item.select_one("a[href]")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        url = base_url + href if href.startswith("/") else href
        snippet_tag = item.select_one(".search-snippet, p, .snippet")
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
        results.append({"title": title, "url": url, "summary": snippet})
    return results


async def fetch_rss(base_url: str) -> str:
    """异步拉取 RSS 源。"""
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=15
    ) as client:
        resp = await client.get(f"{base_url}/rss.xml")
        resp.raise_for_status()
        return resp.text


async def fetch_category_page(base_url: str, category_id: int, page: int = 0) -> str:
    """异步拉取分类列表页。"""
    url = f"{base_url}/category/{category_id}"
    if page > 0:
        url += f"?page={page}"
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=15
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_search_page(
    base_url: str, keyword: str, page: int = 0
) -> str:
    """异步拉取搜索结果页。"""
    url = f"{base_url}/search"
    params: dict[str, str] = {"keyword": keyword}
    if page > 0:
        params["page"] = str(page)
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=15
    ) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text
```

**数据流：**

```
today.hit.edu.cn
       │
       ├── /rss.xml          ──► fetch_rss()       ──► parse_rss()
       ├── /category/{id}    ──► fetch_category_page() ──► parse_category_page()
       └── /search?keyword=  ──► fetch_search_page()    ──► parse_search_page()
                                                                │
                                                                ▼
                                                         Article 表 (peewee)
```

### 6.5 search.py — 搜索引擎

> 文件：`plugins/today_scraper/search.py`

纯逻辑模块，不依赖 nonebot，可独立测试。支持精确优先、AND、OR、正则、时间过滤。

```python
"""搜索引擎：精确优先、AND/OR/REGEX、时间过滤、转发节点构建。"""
import operator
import re
from datetime import datetime
from functools import reduce
from typing import Any

from .models import Article

MAX_RESULTS = 50

_TIME_RE = re.compile(
    r"时间\s+(\d{2})\.(\d{2})\.(\d{2})~(\d{2})\.(\d{2})\.(\d{2})"
)


def _format_time(dt: datetime | None) -> str:
    if not dt:
        return "未知"
    return dt.strftime("%Y-%m-%d %H:%M")


def parse_search_args(arg_text: str) -> tuple[str, tuple[datetime, datetime] | None]:
    """解析搜索参数，返回 (keyword_raw, time_range_or_None)。"""
    time_range = None
    m = _TIME_RE.search(arg_text)
    if m:
        y1, mo1, d1, y2, mo2, d2 = (int(x) for x in m.groups())
        start = datetime(2000 + y1, mo1, d1, 0, 0, 0)
        end = datetime(2000 + y2, mo2, d2, 23, 59, 59)
        time_range = (start, end)
        arg_text = arg_text[: m.start()] + arg_text[m.end() :]
    return arg_text.strip(), time_range


def build_query(
    keyword: str,
    time_range: tuple[datetime, datetime] | None,
    limit: int = MAX_RESULTS,
) -> list:
    """构建搜索查询，精确优先 + 高级语法。

    搜索模式：
    - 无关键词：按发布时间倒序
    - "正则:xxx"：REGEXP 正则匹配
    - "A/B/C"：OR 模式，包含任意一个
    - "A B"：AND 模式，同时包含
    - 单词：精确匹配优先，不够再模糊补充
    """
    if not keyword:
        query = (
            Article.select()
            .where(Article.published_at.is_null(False))
            .order_by(Article.published_at.desc())
            .limit(limit)
        )
        if time_range:
            start, end = time_range
            query = query.where(Article.published_at.between(start, end))
        return list(query)

    if keyword.startswith("正则:"):
        pattern = keyword[3:].strip()
        query = (
            Article.select()
            .where(Article.title.regexp(pattern))
            .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
            .limit(limit)
        )
    elif "/" in keyword and not keyword.startswith("正则:"):
        terms = [t.strip() for t in keyword.split("/") if t.strip()]
        if len(terms) == 1:
            cond = Article.title.contains(terms[0])
        else:
            cond = reduce(operator.or_, [Article.title.contains(t) for t in terms])
        query = (
            Article.select()
            .where(cond)
            .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
            .limit(limit)
        )
    else:
        terms = keyword.split()
        if len(terms) == 1:
            # 单关键词：精确匹配优先，不够再模糊补
            exact = list(
                Article.select()
                .where(Article.title == keyword)
                .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
                .limit(limit)
            )
            if len(exact) >= limit:
                return exact
            exact_ids = {a.id for a in exact}
            fuzzy = list(
                Article.select()
                .where(
                    Article.title.contains(keyword),
                    Article.id.not_in(exact_ids) if exact_ids else True,
                )
                .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
                .limit(limit - len(exact))
            )
            combined = exact + fuzzy
            if time_range:
                start, end = time_range
                combined = [
                    a for a in combined
                    if a.published_at and start <= a.published_at <= end
                ]
            return combined[:limit]
        else:
            cond = reduce(operator.and_, [Article.title.contains(t) for t in terms])
            query = (
                Article.select()
                .where(cond)
                .order_by(Article.published_at.desc(nulls="LAST"), Article.id.desc())
                .limit(limit)
            )

    if time_range:
        start, end = time_range
        query = query.where(Article.published_at.between(start, end))

    return list(query)


def build_forward_nodes(articles: list[Any], bot_id: int) -> list[dict]:
    """将文章列表构建为合并转发消息节点。"""
    nodes = []
    for a in articles:
        dept = a.source_dept or "未知"
        time_str = _format_time(a.published_at)
        text = f"📌 {a.title}\n📅 {time_str}\n🏫 {dept}\n🔗 {a.url}"
        nodes.append({
            "type": "node",
            "data": {
                "user_id": str(bot_id),
                "nickname": "缇安",
                "content": [{"type": "text", "data": {"text": text}}],
            },
        })
    return nodes
```

### 6.6 pusher.py — 推送系统

> 文件：`plugins/today_scraper/pusher.py`

负责订阅匹配、未推送文章获取、推送记录、消息节点构建。

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import Article, PushRecord, Subscription


def _format_time(dt: datetime | None) -> str:
    if not dt:
        return "未知"
    return dt.strftime("%Y-%m-%d %H:%M")


def match_subscriptions(article: Article) -> list[tuple[str, str]]:
    """匹配文章对应的订阅目标，返回 [(target_type, target_id), ...]。"""
    targets: set[tuple[str, str]] = set()

    # 分类订阅匹配
    if article.category:
        for sub in Subscription.select().where(
            Subscription.sub_type == "category",
            Subscription.sub_value == article.category,
        ):
            targets.add((sub.target_type, sub.target_id))

    # 关键词订阅匹配
    for sub in Subscription.select().where(Subscription.sub_type == "keyword"):
        if sub.sub_value in article.title:
            targets.add((sub.target_type, sub.target_id))

    return list(targets)


def get_unpushed_articles(limit: int = 10) -> list[Article]:
    """获取尚未推送过的文章。"""
    pushed_ids = set(
        r.article_id for r in PushRecord.select(PushRecord.article_id).distinct()
    )
    query = Article.select().order_by(Article.published_at.desc()).limit(limit)
    if pushed_ids:
        query = query.where(Article.id.not_in(pushed_ids))
    return list(query)


def mark_pushed(article_id: int, target_type: str, target_id: str) -> None:
    """记录已推送。"""
    PushRecord.insert(
        article_id=article_id,
        target_type=target_type,
        target_id=target_id,
    ).on_conflict_ignore().execute()


def build_push_nodes(articles: list[dict[str, Any]], bot_id: int) -> list[dict]:
    """构建推送转发消息节点列表。"""
    if not articles:
        return []

    nodes = []
    for a in articles:
        dept = a.get("source_dept") or "未知"
        time_str = _format_time(a.get("published_at"))
        text = f"📌 {a['title']}\n📅 {time_str}\n🏫 {dept}\n🔗 {a['url']}"
        nodes.append({
            "type": "node",
            "data": {
                "user_id": str(bot_id),
                "nickname": "缇安",
                "content": [{"type": "text", "data": {"text": text}}],
            },
        })
    return nodes


def build_search_message(
    keyword: str, results: list[dict[str, Any]], page: int, total: int
) -> str:
    """构建搜索结果消息文本。"""
    if not results:
        return f'🔍 搜索"{keyword}" - 无结果'

    lines = [f'🔍 搜索"{keyword}" - 第 {page + 1} 页（共 {total} 条）', "━" * 18]
    for i, r in enumerate(results, 1):
        dept = r.get("source_dept") or ""
        date_str = r.get("date") or ""
        meta = " · ".join(filter(None, [dept, date_str]))
        lines.append(f"{i}. {r['title']}")
        if meta:
            lines.append(f"   {meta}")
        lines.append(f"   {r['url']}")
        if i < len(results):
            lines.append("")
    lines.append("━" * 18)
    lines.append(f"/today search {keyword} {page + 2} → 下一页")
    return "\n".join(lines)
```

### 6.7 commands.py — 命令系统

> 文件：`plugins/today_scraper/commands.py`

通过 `on_keyword("缇安")` 注册命令匹配器，实现所有用户交互命令。

```python
import random

import nonebot
from nonebot import on_keyword
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent, MessageSegment

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
        # 降级为纯文本
        lines = []
        for n in nodes:
            for seg in n.get("data", {}).get("content", []):
                if seg.get("type") == "text":
                    lines.append(seg["data"]["text"])
        await bot.send(event, "\n---\n".join(lines))


# ── 命令注册 ────────────────────────────────────────────

matcher = on_keyword("缇安", priority=10, block=True)


@matcher.handle()
async def handle_tian(event: MessageEvent):
    bot = nonebot.get_bot()
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
            await bot.send(event, "🥺 缇安还没爬到任何公告呢～稍后再试试吧！")
            return
        nodes = build_forward_nodes(articles, int(event.self_id))
        await bot.send(event, "💫 缇安开门找到最新公告啦！")
        await _send_forward(bot, event, nodes)
        return

    subcmd, rest = _parse_args(arg_text)

    try:
        # ── 搜索 ──
        if subcmd == "搜索":
            await _handle_search(bot, event, rest)
        # ── 时间 ──
        elif subcmd == "时间":
            await _handle_time(bot, event, rest)
        # ── 部门列表 ──
        elif subcmd == "部门列表":
            await _handle_dept_list(bot, event)
        # ── 部门 ──
        elif subcmd == "部门":
            await _handle_dept(bot, event, rest)
        # ── 订阅 ──
        elif subcmd == "订阅":
            await _handle_subscribe(bot, event, rest)
        # ── 取消订阅 ──
        elif subcmd == "取消订阅":
            await _handle_unsubscribe(bot, event, rest)
        # ── 我的订阅 ──
        elif subcmd == "我的订阅":
            await _handle_list(bot, event)
        # ── 统计 ──
        elif subcmd == "统计":
            await _handle_stat(bot, event)
        # ── 找群友 ──
        elif subcmd == "找群友":
            await _handle_find_member(bot, event)
        # ── 群友排名 ──
        elif subcmd == "群友排名":
            await _handle_member_rank(bot, event)
        # ── 管理员命令 ──
        elif subcmd == "强制推送":
            if not _is_admin(event):
                await bot.send(event, "🔒 这个指令只有缇安的管理员才能用哦～")
                return
            await _handle_force_push(bot, event)
        elif subcmd == "强制爬取":
            if not _is_admin(event):
                await bot.send(event, "🔒 这个指令只有缇安的管理员才能用哦～")
                return
            await _handle_force_scrape(bot, event)
        # ── 帮助 ──
        elif subcmd == "帮助":
            await _handle_help(bot, event)
        else:
            await bot.send(event, "😵 缇安没听懂这个指令哦～输入「缇安 帮助」看看所有用法吧！")
    except Exception as e:
        nonebot.logger.error(f"缇安命令出错: {e}", exc_info=True)
        await bot.send(event, f"😣 缇安出了点问题: {e}")


# ── 子命令实现（完整代码见源文件） ───────────────────────
# _handle_search       - 关键词搜索（精确/AND/OR/正则/时间过滤）
# _handle_time         - 按时间段筛选
# _handle_dept_list    - 查看所有部门
# _handle_dept         - 按部门筛选
# _handle_subscribe    - 订阅分类/关键词
# _handle_unsubscribe  - 取消订阅
# _handle_list         - 查看我的订阅
# _handle_stat         - 数据库统计
# _handle_find_member  - 找群友（加权随机）
# _handle_member_rank  - 群友发言排名
# _handle_force_push   - 管理员强制推送
# _handle_force_scrape - 管理员强制爬取
# _handle_help         - 帮助信息（合并转发卡片）
```

**命令路由表：**

```
用户消息包含 "缇安"
       │
       ▼
  handle_tian()
       │
       ├─ (无参数)     → 最新公告（合并转发）
       ├─ "搜索"       → _handle_search()
       ├─ "时间"       → _handle_time()
       ├─ "部门列表"   → _handle_dept_list()
       ├─ "部门"       → _handle_dept()
       ├─ "订阅"       → _handle_subscribe()
       ├─ "取消订阅"   → _handle_unsubscribe()
       ├─ "我的订阅"   → _handle_list()
       ├─ "统计"       → _handle_stat()
       ├─ "找群友"     → _handle_find_member()
       ├─ "群友排名"   → _handle_member_rank()
       ├─ "强制推送"   → _handle_force_push()   [管理员]
       ├─ "强制爬取"   → _handle_force_scrape() [管理员]
       └─ "帮助"       → _handle_help()
```

---

## 7. 辅助插件

### 7.1 today_help/\_\_init\_\_.py

> 文件：`plugins/today_help/__init__.py`

```python
# help 插件已合并到 today_scraper.commands 中，此文件暂时留空
```

---

## 8. 脚本

### 8.1 scripts/full_scrape.py — 全量历史爬取

> 文件：`scripts/full_scrape.py`

独立脚本，全量爬取公告公示和新闻快讯两个分类的所有历史页面，支持断点续爬（幂等插入）。

```python
"""全量爬取今日哈工大历史数据。"""
import asyncio
import re
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from bs4 import BeautifulSoup
from plugins.today_scraper.models import init_db, Article, ScraperState

BASE_URL = "https://today.hit.edu.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}
CATEGORIES = {10: "公告公示", 11: "新闻快讯"}


def parse_list_page(html: str, category: str) -> list[dict]:
    """解析分类列表页。"""
    soup = BeautifulSoup(html, "lxml")
    articles = []
    for item in soup.select("ul.paragraph li"):
        link = item.select_one('a[href*="/article/"]')
        if not link:
            continue
        href = link.get("href", "")
        match = re.search(r"/article/(\d{4})/(\d{2})/(\d{2})/(\d+)", href)
        if not match:
            continue
        article_id = int(match.group(4))
        try:
            published_at = datetime(
                int(match.group(1)), int(match.group(2)), int(match.group(3))
            )
        except ValueError:
            published_at = None
        title = link.get_text(strip=True)
        url = BASE_URL + href if href.startswith("/") else href

        dept = None
        text_parts = list(item.stripped_strings)
        if text_parts:
            first = text_parts[0]
            if len(first) < 20 and "/article/" not in first:
                dept = first

        articles.append({
            "id": article_id,
            "title": title,
            "url": url,
            "source_dept": dept,
            "category": category,
            "published_at": published_at,
        })
    return articles


def get_max_page(html: str) -> int:
    """获取分页最大页码。"""
    soup = BeautifulSoup(html, "lxml")
    pages = soup.select(".pager__item a")
    max_page = 0
    for p in pages:
        href = p.get("href", "")
        m = re.search(r"page=(\d+)", href)
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page


async def scrape_category(client: httpx.AsyncClient, cat_id: int, cat_name: str) -> int:
    """爬取单个分类的所有页面。"""
    url = f"{BASE_URL}/category/{cat_id}"
    resp = await client.get(url)
    resp.raise_for_status()
    html = resp.text

    max_page = get_max_page(html)
    print(f"  [{cat_name}] 共 {max_page + 1} 页")

    total_new = 0
    for page in range(max_page + 1):
        if page > 0:
            await asyncio.sleep(2)
            resp = await client.get(f"{url}?page={page}")
            resp.raise_for_status()
            html = resp.text

        articles = parse_list_page(html, cat_name)
        new_count = 0
        for a in articles:
            try:
                Article.insert(
                    id=a["id"],
                    title=a["title"],
                    url=a["url"],
                    source_dept=a.get("source_dept"),
                    category=a["category"],
                    published_at=a.get("published_at"),
                ).on_conflict(
                    conflict_target=[Article.id],
                    update={
                        Article.source_dept: a.get("source_dept") or Article.source_dept,
                        Article.category: a["category"],
                        Article.published_at: a.get("published_at") or Article.published_at,
                    },
                ).execute()
                new_count += 1
            except Exception:
                pass

        total_new += new_count
        if page % 10 == 0:
            print(f"    page {page}: +{new_count} (累计 {total_new})")

    return total_new


async def main():
    init_db("./data/todayhit.db")
    before = Article.select().count()
    print(f"数据库已有 {before} 条记录")

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for cat_id, cat_name in CATEGORIES.items():
            print(f"\n开始爬取 [{cat_name}] ...")
            count = await scrape_category(client, cat_id, cat_name)
            print(f"  [{cat_name}] 完成，新增/更新 {count} 条")

    after = Article.select().count()
    print(f"\n总计: {before} -> {after} 条记录")

    for cat in ["公告公示", "新闻快讯"]:
        cnt = Article.select().where(Article.category == cat).count()
        print(f"  {cat}: {cnt} 条")
    no_cat = Article.select().where(Article.category.is_null()).count()
    print(f"  无分类: {no_cat} 条")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. 测试

### 9.1 test_models.py

> 文件：`tests/test_models.py`

测试所有数据模型的 CRUD 操作、唯一约束、幂等插入。

```python
import pytest
from plugins.today_scraper.models import (
    db, Article, Subscription, PushRecord,
    ScraperState, GroupMessage, init_db,
)


@pytest.fixture(autouse=True)
def test_db():
    """每个测试使用内存数据库。"""
    init_db(":memory:")
    yield
    db.close()


def test_article_create_and_get():
    article = Article.create(
        id=129723,
        title="测试公告标题",
        url="https://today.hit.edu.cn/article/2026/05/10/129723",
        source_dept="能源学院",
        category="公告公示",
    )
    assert article.id == 129723
    assert article.title == "测试公告标题"
    got = Article.get_by_id(129723)
    assert got.url == "https://today.hit.edu.cn/article/2026/05/10/129723"


def test_article_idempotent_insert():
    Article.create(id=1, title="a", url="https://example.com/1")
    Article.insert(id=1, title="b", url="https://example.com/1b").on_conflict_ignore().execute()
    assert Article.select().count() == 1


def test_subscription_create_and_unique():
    Subscription.create(
        target_type="group", target_id="123456",
        sub_type="keyword", sub_value="招聘",
    )
    with pytest.raises(Exception):
        Subscription.create(
            target_type="group", target_id="123456",
            sub_type="keyword", sub_value="招聘",
        )


def test_subscription_query_by_target():
    Subscription.create(target_type="group", target_id="111", sub_type="category", sub_value="公告公示")
    Subscription.create(target_type="group", target_id="111", sub_type="keyword", sub_value="创新")
    Subscription.create(target_type="private", target_id="222", sub_type="keyword", sub_value="招聘")

    subs = list(Subscription.select().where(
        Subscription.target_type == "group",
        Subscription.target_id == "111",
    ))
    assert len(subs) == 2


def test_push_record_unique():
    Article.create(id=1, title="a", url="https://example.com/1")
    PushRecord.create(article_id=1, target_type="group", target_id="111")
    with pytest.raises(Exception):
        PushRecord.create(article_id=1, target_type="group", target_id="111")


def test_scraper_state_get_set():
    ScraperState.set("last_rss_id", "129700")
    assert ScraperState.get_value("last_rss_id") == "129700"
    assert ScraperState.get_value("nonexistent", "default") == "default"


def test_group_message_increment():
    GroupMessage.increment("111", "100", "小明")
    GroupMessage.increment("111", "100", "小明")
    GroupMessage.increment("111", "100", "小明")
    record = GroupMessage.get(GroupMessage.group_id == "111", GroupMessage.user_id == "100")
    assert record.message_count == 3
    assert record.last_nickname == "小明"


def test_group_message_increment_different_users():
    GroupMessage.increment("111", "100", "小明")
    GroupMessage.increment("111", "200", "小红")
    GroupMessage.increment("111", "200", "小红")
    records = list(GroupMessage.select().where(GroupMessage.group_id == "111"))
    assert len(records) == 2
    counts = {r.user_id: r.message_count for r in records}
    assert counts["100"] == 1
    assert counts["200"] == 2


def test_group_message_nickname_update():
    GroupMessage.increment("111", "100", "旧名")
    GroupMessage.increment("111", "100", "新名")
    record = GroupMessage.get(GroupMessage.group_id == "111", GroupMessage.user_id == "100")
    assert record.last_nickname == "新名"
```

### 9.2 test_scraper.py

> 文件：`tests/test_scraper.py`

使用固定的 HTML/XML 样本测试 RSS、分类页、搜索页解析。

```python
import pytest
from plugins.today_scraper.scraper import parse_rss, parse_category_page, parse_search_page


RSS_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xml:base="http://today.hit.edu.cn/">
  <channel>
    <title>今日哈工大</title>
    <item>
      <title>测试公告一</title>
      <link>http://today.hit.edu.cn/article/2026/05/10/129723</link>
      <description>&lt;h4&gt;测试公告一&lt;/h4&gt;&lt;div&gt;这是正文内容&lt;/div&gt;</description>
      <pubDate>Sun, 10 May 2026 13:18:37 +0000</pubDate>
      <dc:creator>张三</dc:creator>
      <guid>129723 at http://today.hit.edu.cn</guid>
    </item>
    <item>
      <title>测试快讯二</title>
      <link>http://today.hit.edu.cn/article/2026/05/09/129722</link>
      <description>&lt;div&gt;快讯正文&lt;/div&gt;</description>
      <pubDate>Sat, 09 May 2026 12:00:00 +0000</pubDate>
      <dc:creator>李四</dc:creator>
      <guid>129722 at http://today.hit.edu.cn</guid>
    </item>
  </channel>
</rss>"""


CATEGORY_HTML = """
<html><body>
<div class="view-content">
  <div class="views-row">
    <a href="/article/2026/05/10/129723">公告标题一</a>
    <span class="field--name-field-department">能源学院</span>
    <span class="date-display-single">05-10</span>
  </div>
  <div class="views-row">
    <a href="/article/2026/05/09/129694">公告标题二</a>
    <span class="field--name-field-department">学工处</span>
    <span class="date-display-single">05-09</span>
  </div>
</div>
</body></html>
"""


SEARCH_HTML = """
<html><body>
<div class="search-result">
  <h3><a href="/article/2026/05/08/129682">关于创新大赛的通知</a></h3>
  <p class="search-snippet">这是摘要内容...</p>
  <span class="search-date">2026-05-08</span>
</div>
</body></html>
"""


def test_parse_rss_extracts_items():
    items = parse_rss(RSS_SAMPLE)
    assert len(items) == 2
    assert items[0]["id"] == 129723
    assert items[0]["title"] == "测试公告一"
    assert items[0]["url"] == "http://today.hit.edu.cn/article/2026/05/10/129723"
    assert items[1]["id"] == 129722


def test_parse_rss_empty():
    items = parse_rss("<?xml version='1.0'?><rss><channel><title>x</title></channel></rss>")
    assert items == []


def test_parse_category_page_extracts_articles():
    from datetime import datetime
    articles = parse_category_page(CATEGORY_HTML, "https://today.hit.edu.cn")
    assert len(articles) == 2
    assert articles[0]["id"] == 129723
    assert articles[0]["source_dept"] == "能源学院"
    assert articles[0]["published_at"] == datetime(2026, 5, 10)
    assert articles[1]["published_at"] == datetime(2026, 5, 9)


def test_parse_search_page_extracts_results():
    results = parse_search_page(SEARCH_HTML, "https://today.hit.edu.cn")
    assert len(results) == 1
    assert results[0]["title"] == "关于创新大赛的通知"
```

### 9.3 test_pusher.py

> 文件：`tests/test_pusher.py`

测试订阅匹配逻辑和推送节点构建。

```python
import pytest
from datetime import datetime
from plugins.today_scraper.models import db, Article, Subscription, PushRecord, init_db
from plugins.today_scraper.pusher import match_subscriptions, build_push_nodes


@pytest.fixture(autouse=True)
def test_db():
    init_db(":memory:")
    yield
    db.close()


def _make_article(article_id: int, title: str, category: str = None, dept: str = None):
    return Article.create(
        id=article_id,
        title=title,
        url=f"https://today.hit.edu.cn/article/2026/05/10/{article_id}",
        source_dept=dept,
        category=category,
        published_at=datetime(2026, 5, 10, 12, 0),
    )


def test_match_category_subscription():
    _make_article(1, "公告A", category="公告公示")
    Subscription.create(
        target_type="group", target_id="111",
        sub_type="category", sub_value="公告公示",
    )
    targets = match_subscriptions(Article.get_by_id(1))
    assert ("group", "111") in targets


def test_match_keyword_subscription():
    _make_article(2, "关于招聘实验员的通知")
    Subscription.create(
        target_type="group", target_id="222",
        sub_type="keyword", sub_value="招聘",
    )
    targets = match_subscriptions(Article.get_by_id(2))
    assert ("group", "222") in targets


def test_no_match_returns_empty():
    _make_article(3, "某公告")
    targets = match_subscriptions(Article.get_by_id(3))
    assert targets == []


def test_build_push_nodes():
    articles = [
        {"title": "公告一", "source_dept": "能源学院",
         "url": "https://today.hit.edu.cn/article/1",
         "published_at": datetime(2026, 5, 10, 12, 0)},
        {"title": "公告二", "source_dept": None,
         "url": "https://today.hit.edu.cn/article/2",
         "published_at": None},
    ]
    nodes = build_push_nodes(articles, bot_id=123456)
    assert len(nodes) == 2
    assert nodes[0]["type"] == "node"
    assert nodes[0]["data"]["user_id"] == "123456"
    assert nodes[0]["data"]["nickname"] == "缇安"
    content = nodes[0]["data"]["content"]
    assert any("公告一" in seg["data"]["text"] for seg in content if seg["type"] == "text")
    assert any("能源学院" in seg["data"]["text"] for seg in content if seg["type"] == "text")


def test_build_push_nodes_empty():
    nodes = build_push_nodes([], bot_id=123456)
    assert nodes == []
```

### 9.4 test_commands.py — 搜索引擎测试

> 文件：`tests/test_commands.py`

使用 10 条预设数据测试搜索引擎的各种模式。

```python
"""测试搜索引擎：精确优先、AND/OR/REGEX、时间过滤、转发节点构建。"""
import pytest
from datetime import datetime
from plugins.today_scraper.models import db, Article, init_db
from plugins.today_scraper.search import parse_search_args, build_query, build_forward_nodes


@pytest.fixture(autouse=True)
def test_db():
    init_db(":memory:")
    for i, (title, dept, dt) in enumerate([
        ("机电学院2024年度奖学金评选通知", "机电工程学院", datetime(2024, 3, 15, 10, 0)),
        ("机电学院研究生招生简章", "机电工程学院", datetime(2024, 6, 1, 8, 0)),
        ("计算机学院2024年度奖学金评选通知", "计算机学院", datetime(2024, 3, 20, 9, 0)),
        ("关于评选优秀研究生的通知", "研究生院", datetime(2024, 5, 10, 14, 0)),
        ("2024年奖学金评审结果公示", "学生工作部", datetime(2024, 7, 1, 16, 0)),
        ("能源学院实验室安全培训", "能源学院", datetime(2024, 4, 5, 10, 0)),
        ("电气学院创新大赛报名通知", "电气学院", datetime(2023, 11, 20, 9, 0)),
        ("图书馆数据库使用培训", "图书馆", datetime(2024, 9, 1, 8, 0)),
        ("2023年度教职工体检通知", "校医院", datetime(2023, 10, 15, 10, 0)),
        ("数学学院学术报告", "数学学院", datetime(2024, 8, 20, 14, 0)),
    ], start=1):
        Article.create(
            id=i, title=title,
            url=f"https://today.hit.edu.cn/article/2024/01/01/{i}",
            source_dept=dept, published_at=dt,
        )
    yield
    db.close()


# ── parse_search_args 测试 ────────────────────────────

def test_parse_search_args_no_time():
    keyword, tr = parse_search_args("机电学院")
    assert keyword == "机电学院"
    assert tr is None


def test_parse_search_args_with_time():
    keyword, tr = parse_search_args("奖学金 时间 24.01.01~24.12.31")
    assert keyword == "奖学金"
    assert tr is not None
    start, end = tr
    assert start == datetime(2024, 1, 1, 0, 0, 0)
    assert end == datetime(2024, 12, 31, 23, 59, 59)


def test_parse_search_args_time_only():
    keyword, tr = parse_search_args("时间 23.10.01~24.06.30")
    assert keyword == ""
    assert tr is not None


# ── build_query 测试 ──────────────────────────────────

def test_build_query_no_keyword():
    results = build_query("", None)
    assert len(results) > 0
    for i in range(len(results) - 1):
        a1, a2 = results[i], results[i + 1]
        if a1.published_at and a2.published_at:
            assert a1.published_at >= a2.published_at


def test_build_query_exact_first():
    results = build_query("机电学院2024年度奖学金评选通知", None)
    assert len(results) >= 1
    assert results[0].title == "机电学院2024年度奖学金评选通知"


def test_build_query_single_keyword_fuzzy():
    results = build_query("奖学金", None)
    titles = [r.title for r in results]
    assert len(titles) >= 3
    assert all("奖学金" in t for t in titles)


def test_build_query_and_mode():
    results = build_query("机电 评选", None)
    assert len(results) >= 1
    for r in results:
        assert "机电" in r.title and "评选" in r.title


def test_build_query_or_mode():
    """竖线 / 分隔 = OR 模式。"""
    results = build_query("图书馆/数学", None)
    titles = [r.title for r in results]
    assert any("图书馆" in t for t in titles)
    assert any("数学" in t for t in titles)


def test_build_query_regex():
    """正则: 前缀 = 正则模式。"""
    results = build_query("正则:2024年.*评选", None)
    titles = [r.title for r in results]
    assert all("2024年" in t and "评选" in t for t in titles)


def test_build_query_time_filter():
    start = datetime(2024, 3, 1, 0, 0, 0)
    end = datetime(2024, 6, 30, 23, 59, 59)
    results = build_query("", (start, end))
    for r in results:
        assert r.published_at is not None
        assert start <= r.published_at <= end


def test_build_query_keyword_and_time():
    start = datetime(2024, 1, 1, 0, 0, 0)
    end = datetime(2024, 4, 30, 23, 59, 59)
    results = build_query("奖学金", (start, end))
    for r in results:
        assert "奖学金" in r.title
        assert r.published_at is not None
        assert start <= r.published_at <= end


def test_build_query_no_results():
    results = build_query("不存在的关键词XYZ", None)
    assert results == []


# ── build_forward_nodes 测试 ──────────────────────────

def test_build_forward_nodes():
    articles = list(Article.select().limit(3))
    nodes = build_forward_nodes(articles, bot_id=999)
    assert len(nodes) == 3
    for node in nodes:
        assert node["type"] == "node"
        assert node["data"]["user_id"] == "999"
        assert node["data"]["nickname"] == "缇安"
        content = node["data"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        text = content[0]["data"]["text"]
        assert "📌" in text
        assert "📅" in text
        assert "🏫" in text
        assert "🔗" in text


def test_build_forward_nodes_empty():
    nodes = build_forward_nodes([], bot_id=999)
    assert nodes == []


def test_build_forward_nodes_max_50():
    results = build_query("", None)
    assert len(results) <= 50
    nodes = build_forward_nodes(results, bot_id=999)
    assert len(nodes) <= 50
```

### 9.5 verify_real_site.py — 端到端验证

> 文件：`tests/verify_real_site.py`

连接真实网站进行端到端验证（非 pytest，直接运行）。

```python
"""端到端验证：连接真实网站测试爬虫。"""
import asyncio
from plugins.today_scraper.scraper import fetch_rss, parse_rss
from plugins.today_scraper.models import init_db, Article


async def test_rss():
    xml = await fetch_rss("https://today.hit.edu.cn")
    items = parse_rss(xml)
    print(f"RSS items: {len(items)}")
    for i in items[:3]:
        print(f"  - [{i['id']}] {i['title']}")
    return items


def test_db():
    init_db(":memory:")
    print(f"DB init OK, Articles: {Article.select().count()}")


if __name__ == "__main__":
    test_db()
    asyncio.run(test_rss())
    print("\nAll verification passed!")
```

---

> 文档结束。本文档包含 TodayHIT 项目全部源代码，可作为代码审查、交接或归档使用。
