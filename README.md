# TodayHIT QQ Bot

今日哈工大（today.hit.edu.cn）QQ 机器人，提供公告推送、关键词搜索、分类订阅功能。

## 快速开始

### 1. 环境

```powershell
conda activate todayhit
```

### 2. 配置 NapCat

NapCat 是 QQ 协议端，需要先启动并配置 WebSocket 服务器。

配置文件位置：`NapCat.Shell/config/onebot11_<QQ号>.json`

关键配置（websocketServers 部分）：
```json
{
  "enable": true,
  "host": "127.0.0.1",
  "port": 3001,
  "messagePostFormat": "array",
  "token": "<你的token>"
}
```

### 3. 配置 Bot

编辑 `.env.prod`：

```bash
# NapCat WebSocket 地址（带 token）
ONEBOT_WS_URLS=["ws://127.0.0.1:3001/onebot/v11/ws?token=<你的token>"]

# 你的 QQ 号（超级管理员）
SUPERUSERS=["你的QQ号"]
```

### 4. 启动

```powershell
# 先启动 NapCat，登录 QQ
# 再启动 Bot
C:\Users\wfy\.conda\envs\todayhit\python.exe bot.py
```

## QQ 命令

| 命令 | 说明 |
|------|------|
| `/today` | 查看最新公告 |
| `/today search <关键词>` | 搜索文章 |
| `/today search <关键词> <页码>` | 搜索翻页 |
| `/today sub category 公告公示` | 订阅分类 |
| `/today sub keyword <词>` | 订阅关键词 |
| `/today unsub <序号>` | 取消订阅 |
| `/today list` | 查看我的订阅 |
| `/today help` | 帮助信息 |

## 项目结构

```
TodayHIT/
├── bot.py                      # NoneBot2 入口
├── pyproject.toml              # 依赖配置
├── .env.prod                   # 环境变量
├── plugins/
│   ├── today_scraper/          # 核心插件
│   │   ├── __init__.py         # 插件入口 + 定时任务
│   │   ├── config.py           # Pydantic 配置
│   │   ├── models.py           # SQLite ORM (peewee)
│   │   ├── scraper.py          # RSS/分类页/搜索页爬虫
│   │   ├── pusher.py           # 订阅匹配 + 消息构建
│   │   └── commands.py         # 用户命令
│   └── today_help/
│       └── __init__.py         # 帮助信息
├── tests/                      # 测试（16 个）
└── data/
    └── todayhit.db             # SQLite 数据库（运行时生成）
```

## 数据来源

| 来源 | 路径 | 说明 |
|------|------|------|
| RSS | `/rss.xml` | 最新 10 条，含标题和正文 |
| 分类页 | `/category/10`, `/category/11` | 公告公示、新闻快讯列表 |
| 搜索页 | `/search?keyword=xxx` | 关键词搜索结果 |

## 技术栈

- NoneBot2 2.5.0 + OneBot V11 适配器
- NapCat 4.18.1（QQ 协议端）
- peewee + SQLite（数据存储）
- httpx + BeautifulSoup4（爬虫）
- APScheduler（定时任务，每 4 小时）

## 已知问题

### WebSocket 连接断开 (code 1005)

Bot 启动后反复报 `WebSocketClosed(code=1005)`。可能原因：
1. NapCat WebSocket 服务器未正确启动
2. token 不匹配
3. NapCat 版本兼容性问题

待排查：确认 NapCat 日志中是否有连接记录，以及连接后是否有握手错误。

## 运行测试

```powershell
conda activate todayhit
cd c:/Users/wfy/Desktop/TodayHIT
pytest tests/ -v
```
