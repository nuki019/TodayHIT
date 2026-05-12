# TodayHIT QQ Bot（缇安版）

今日哈工大（today.hit.edu.cn）QQ 机器人「缇安」，提供公告推送、关键词搜索、分类订阅功能。

数据库已爬取约 **48,000+** 条历史公告，支持按时间、标题、部门查询。

## 快速开始

### 一键启动

```powershell
start.bat
```

自动启动 NapCat（QQ 协议端）→ 等待 5 秒 → 启动 Bot。

### 手动启动

```powershell
# 终端 1：启动 NapCat
cd NapCat.Shell
launcher.bat

# 终端 2：启动 Bot（等 NapCat 登录成功后再启动）
cd c:\Users\wfy\Desktop\TodayHIT
C:\Users\wfy\.conda\envs\todayhit\python.exe bot.py
```

## QQ 命令（缇安）

所有查询结果以**合并转发消息卡片**形式输出，每条包含标题、时间、部门、链接，单次最多 50 条。

详细命令参考见 [docs/qq-commands.md](docs/qq-commands.md)

| 命令 | 说明 |
|------|------|
| 缇安 | 最新公告（转发卡片） |
| 缇安 搜索 关键词 | 精确优先搜索 |
| 缇安 搜索 机电 学院 | 同时含两词 |
| 缇安 搜索 奖学金/评优 | 含任意一词 |
| 缇安 搜索 正则:表达式 | 正则搜索 |
| 缇安 搜索 奖学金 时间 24.01.01~24.12.31 | 搜索 + 时间过滤 |
| 缇安 时间 24.04.01~24.04.30 | 按时间筛选 |
| 缇安 部门列表 | 查看所有部门 |
| 缇安 部门 名称 | 按部门筛选 |
| 缇安 统计 | 数据库统计 |
| 缇安 爬取 | 手动爬取最新文章 |
| 缇安 订阅 分类 公告公示 | 订阅分类 |
| 缇安 订阅 关键词 招聘 | 订阅关键词 |
| 缇安 取消订阅 序号 | 取消订阅 |
| 缇安 我的订阅 | 查看我的订阅 |
| 缇安 帮助 | 帮助信息 |

## 配置

### Bot 配置 (.env.prod)

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

### NapCat 配置

配置文件：`NapCat.Shell/config/onebot11_<QQ号>.json`

当前架构：NapCat 作为 WebSocket **客户端**连接 Bot（反向连接）。

## 项目结构

```
TodayHIT/
├── start.bat                       # 一键启动脚本
├── bot.py                          # NoneBot2 入口
├── pyproject.toml                  # 依赖配置
├── .env.prod                       # 环境变量
├── plugins/
│   ├── today_scraper/              # 核心插件
│   │   ├── __init__.py             # 插件入口 + 定时任务 + 启动爬取
│   │   ├── config.py               # Pydantic 配置
│   │   ├── models.py               # SQLite ORM (peewee) + REGEXP 支持
│   │   ├── scraper.py              # RSS/分类页/搜索页爬虫（URL 日期提取）
│   │   ├── search.py               # 搜索引擎（精确优先/AND/OR/正则/时间过滤）
│   │   ├── pusher.py               # 订阅匹配 + 转发节点构建
│   │   └── commands.py             # 缇安命令系统 + 合并转发输出
│   └── today_help/
│       └── __init__.py             # 帮助信息
├── scripts/
│   └── full_scrape.py              # 全量历史数据爬取脚本
├── tests/                          # 测试（30 个）
├── docs/
│   └── qq-commands.md              # 缇安命令参考文档
├── data/
│   └── todayhit.db                 # SQLite 数据库（~48K 条记录）
└── NapCat.Shell/                   # QQ 协议端
    └── launcher.bat                # NapCat 启动脚本
```

## 数据来源

| 来源 | 路径 | 说明 |
|------|------|------|
| RSS | `/rss.xml` | 最新 10 条，定时自动抓取 |
| 分类页 | `/category/10`, `/category/11` | 公告公示、新闻快讯全量爬取 |
| 搜索页 | `/search?keyword=xxx` | 备用搜索入口 |

URL 中的 `/article/YYYY/MM/DD/ID` 日期自动提取为 `published_at`。

## 技术栈

- NoneBot2 2.5.0 + OneBot V11 适配器
- NapCat 4.18.1（QQ 协议端）
- peewee + SQLite（数据存储，48K+ 条记录）
- httpx + BeautifulSoup4（爬虫）
- APScheduler（定时任务，每 4 小时自动采集）

## 运行测试

```powershell
conda activate todayhit
cd c:/Users/wfy/Desktop/TodayHIT
pytest tests/ -v
```

## 重新爬取历史数据

```powershell
C:\Users\wfy\.conda\envs\todayhit\python.exe scripts/full_scrape.py
```
