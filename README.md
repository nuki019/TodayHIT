# TodayHIT QQ Bot

今日哈工大（today.hit.edu.cn）QQ 机器人，提供公告推送、关键词搜索、分类订阅功能。

数据库已爬取约 **48,000+** 条历史公告，支持按时间、标题、部门查询。

## 快速开始

### 一键启动

```powershell
start.bat
```

自动启动 NapCat（QQ 协议端）→ 等待 15 秒 → 启动 Bot。

### 手动启动

```powershell
# 终端 1：启动 NapCat
cd NapCat.Shell
launcher.bat

# 终端 2：启动 Bot（等 NapCat 登录成功后再启动）
cd c:\Users\wfy\Desktop\TodayHIT
C:\Users\wfy\.conda\envs\todayhit\python.exe bot.py
```

## QQ 命令

所有查询结果以**合并转发消息卡片**形式输出，每条包含标题、时间、部门、链接，单次最多 50 条。

| 命令 | 说明 |
|------|------|
| `/today` | 最新公告（按时间排序，转发卡片） |
| `/today search <关键词>` | 搜索（精确匹配优先，不够再模糊补） |
| `/today search 机电 学院` | AND 搜索（空格分隔，所有词都出现） |
| `/today search 奖学金\|评优` | OR 搜索（竖线分隔，任一词出现） |
| `/today search re:2024年.*评选` | 正则搜索（`re:` 前缀） |
| `/today search XX --time 24.01.01~24.12.31` | 关键词 + 时间范围过滤 |
| `/today --time 24.05.01~24.05.11` | 按时间范围浏览公告 |
| `/today dept` | 查看所有部门列表 |
| `/today dept <部门名>` | 按部门筛选（支持 `--time`） |
| `/today stat` | 数据库统计 |
| `/today scrape` | 手动爬取最新文章 |
| `/today sub category <分类>` | 订阅分类（公告公示/新闻快讯） |
| `/today sub keyword <词>` | 订阅关键词提醒 |
| `/today unsub <序号>` | 取消订阅 |
| `/today list` | 查看我的订阅 |
| `/today help` | 帮助信息 |

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
│   │   ├── scraper.py              # RSS/分类页/搜索页爬虫
│   │   ├── search.py               # 搜索引擎（精确优先/AND/OR/正则/时间过滤）
│   │   ├── pusher.py               # 订阅匹配 + 转发节点构建
│   │   └── commands.py             # 用户命令 + 合并转发输出
│   └── today_help/
│       └── __init__.py             # 帮助信息
├── scripts/
│   └── full_scrape.py              # 全量历史数据爬取脚本
├── tests/                          # 测试（16 个）
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
