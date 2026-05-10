# TodayHIT QQ Bot 设计文档

> 日期: 2026-05-10
> 状态: 待审核

## 1. 项目概述

为哈尔滨工业大学"今日哈工大"（today.hit.edu.cn）构建一个 QQ 机器人，提供公告推送、关键词搜索、分类订阅和关键词提醒功能。

### 1.1 目标

- 自动抓取"今日哈工大"网站的最新公告和新闻
- 按分类和关键词推送到 QQ 群和私聊
- 支持用户主动搜索和订阅管理
- 以标题 + 链接形式呈现，不获取文章完整正文

### 1.2 约束

- 数据源仅使用公开可访问的页面（RSS、分类列表、搜索页），不依赖 CAS 认证
- 单机部署，使用 conda 环境
- 推送频率：每 3-4 小时一次

## 2. 目标网站分析

| 数据源 | 路径 | 需认证 | 内容 |
|--------|------|--------|------|
| RSS 订阅 | `/rss.xml` | 否 | 最新 10 条，含标题、正文 HTML、作者、发布时间 |
| 分类列表 | `/category/10`（公告）、`/category/11`（快讯） | 否 | 文章列表 + 分页，含标题、部门、日期 |
| 搜索页 | `/search?keyword=xxx` | 否 | 关键词搜索结果 + 摘要，约 5 万条 |
| 文章详情 | `/article/YYYY/MM/DD/{id}` | 是 (CAS) | 完整正文，本项目不使用 |
| 首页 | `/` | 否 | 推荐、公告、快讯、活动、热门标签 |
| 活动日历 | `/calendar/month` | 否 | 院系活动预告 |

网站基于 Drupal 8 构建，无公开 JSON API。RSS 是最佳数据入口。

## 3. 架构设计

### 3.1 方案选择：NoneBot2 单体应用

```
┌─────────────────────────────────────┐
│         NoneBot2 应用                │
│  ┌──────────┐  ┌──────────────────┐ │
│  │ 命令插件  │  │ APScheduler 定时 │ │
│  │ 搜索/订阅 │  │ 爬取 + 推送逻辑  │ │
│  └────┬─────┘  └───────┬──────────┘ │
│       │                │            │
│  ┌────┴────────────────┴──────────┐ │
│  │        数据层 (SQLite)          │ │
│  │  文章记录 / 订阅关系 / 推送状态  │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
        ↕ OneBot v11 协议 (WebSocket)
   ┌──────────┐
   │  NapCat   │
   └──────────┘
```

选择理由：
- YAGNI — 项目规模不需要分布式架构
- KISS — 单进程部署，conda 一条命令启动
- NoneBot2 自带 APScheduler 插件，定时任务天然集成
- SQLite 单文件数据库，备份迁移方便

### 3.2 项目结构

```
TodayHIT/
├── bot.py                  # NoneBot2 入口
├── pyproject.toml          # 项目配置 + NoneBot 插件声明
├── .env.prod               # 生产环境变量
│
├── plugins/
│   ├── today_scraper/      # 核心插件
│   │   ├── __init__.py     # 插件入口，注册命令/定时任务
│   │   ├── scraper.py      # 爬虫：RSS + 分类页 + 搜索页
│   │   ├── models.py       # SQLite ORM (peewee)
│   │   ├── pusher.py       # 推送逻辑：匹配订阅 → 构建消息
│   │   ├── commands.py     # 用户命令：搜索/订阅/退订/列表
│   │   └── config.py       # 插件配置模型
│   └── today_help/         # 帮助信息插件
│       └── __init__.py
│
└── data/
    └── todayhit.db         # SQLite 数据库文件
```

## 4. 数据模型

### 4.1 articles — 文章记录

```sql
CREATE TABLE articles (
    id          INTEGER PRIMARY KEY,  -- 站点原始 ID（如 129723）
    title       TEXT NOT NULL,
    url         TEXT NOT NULL,
    source_dept TEXT,                 -- 来源部门（如"能源学院"）
    category    TEXT,                 -- 分类：公告公示 / 新闻快讯
    published_at DATETIME,
    scraped_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    summary     TEXT                  -- 摘要（搜索页获取时才有）
);
```

### 4.2 subscriptions — 订阅关系

```sql
CREATE TABLE subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL,        -- "group" / "private"
    target_id   TEXT NOT NULL,        -- QQ群号 / QQ号
    sub_type    TEXT NOT NULL,        -- "category" / "keyword"
    sub_value   TEXT NOT NULL,        -- 分类名 或 关键词
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_type, target_id, sub_type, sub_value)
);
```

### 4.3 push_records — 推送记录

```sql
CREATE TABLE push_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  INTEGER NOT NULL REFERENCES articles(id),
    target_type TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    pushed_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, target_type, target_id)
);
```

### 4.4 scraper_state — 爬虫状态

```sql
CREATE TABLE scraper_state (
    key       TEXT PRIMARY KEY,
    value     TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 5. 数据采集策略

### 5.1 三层采集

**① RSS 源（主入口）**
- 端点：`https://today.hit.edu.cn/rss.xml`
- 返回最新 10 条，含完整标题、正文 HTML、作者、发布时间
- RSS 不包含分类字段，category 初始为 NULL
- 每次定时任务首先拉取
- 对比 `scraper_state["last_rss_id"]`，发现新文章则写入
- `last_rss_id` 存储最大的数字文章 ID（从 RSS GUID 如 "129723 at ..." 中提取）

**② 分类列表页（补充 + 分类标注）**
- 端点：`/category/10`（公告公示）、`/category/11`（新闻快讯）
- 每页 20 条，支持分页
- 当 RSS 新文章 < 10 时触发，防止漏抓
- 提取 `/article/YYYY/MM/DD/{id}` 链接中的文章 ID
- 通过来源 URL 可确定文章分类：`/category/10` → "公告公示"，`/category/11` → "新闻快讯"
- 对已存在但 category 为 NULL 的文章，补充分类信息（UPDATE）

**③ 搜索页（用户查询专用）**
- 端点：`/search?keyword=xxx&page=N`
- 实时调用，不入库，直接返回结果给用户
- 每页 20 条，含摘要

### 5.2 增量采集流程

```
定时任务触发（每 3-4 小时）
  │
  ├─ 拉取 /rss.xml
  │    解析 <item> 列表
  │    对比 scraper_state["last_rss_id"]
  │    新文章 → INSERT INTO articles（INSERT OR IGNORE）
  │    更新 last_rss_id
  │
  ├─ 拉取 /category/10 和 /category/11 首页
  │    提取所有 /article/YYYY/MM/DD/{id} 链接
  │    已存在的跳过，新发现的 INSERT
  │
  └─ 触发推送匹配
```

### 5.3 反爬策略

- 请求间隔 ≥ 2 秒
- 设置正常 User-Agent（模拟浏览器）
- 单次最多翻 3 页（60 条），避免高频访问
- RSS 是 XML，服务端无压力

## 6. 订阅推送逻辑

### 6.1 推送匹配流程

```
定时任务触发推送
  │
  ├─ 查询本次新增的 articles（自上次推送后）
  │
  ├─ 对每条新文章，匹配订阅：
  │    │
  │    ├─ 分类订阅：article.category 匹配 sub_value
  │    │    → 推送给该 target
  │    │
  │    ├─ 关键词订阅：article.title 包含 sub_value
  │    │    → 推送给该 target
  │    │
  │    └─ 全量推送（默认）：如果 target 没有任何订阅
  │         → 推送所有新公告
  │
  ├─ 检查 push_records 防重复
  │
  └─ 构建消息发送
```

### 6.2 消息格式

**推送消息**：
```
📢 今日哈工大 · 新公告
━━━━━━━━━━━━━━━━━━━
📌 [标题]
   能源学院 · 3 小时前
   https://today.hit.edu.cn/article/...

📌 [标题]
   学工处 · 1 天前
   https://today.hit.edu.cn/article/...
━━━━━━━━━━━━━━━━━━━
共 5 条新公告 | /today help 查看命令
```

**搜索结果**：
```
🔍 搜索"创新大赛" - 第 1 页（共 12 条）
━━━━━━━━━━━━━━━━━━━
1. 关于举办中国国际大学生创新大赛(2026)...
   本科生院 · 2026-05-08
   https://today.hit.edu.cn/article/...

2. ...
━━━━━━━━━━━━━━━━━━━
/today search 创新大赛 2  → 下一页
```

### 6.3 用户命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/today` | 查看最新公告 | `/today` |
| `/today search <关键词>` | 搜索文章 | `/today search 创新大赛` |
| `/today search <关键词> <页码>` | 搜索翻页 | `/today search 招聘 2` |
| `/today sub category <分类>` | 订阅分类（可选：公告公示、新闻快讯） | `/today sub category 公告公示` |
| `/today sub keyword <词>` | 订阅关键词 | `/today sub keyword 招聘` |
| `/today unsub <序号>` | 取消订阅 | `/today unsub 1` |
| `/today list` | 查看我的订阅 | `/today list` |
| `/today help` | 帮助信息 | `/today help` |

## 7. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| Bot 框架 | NoneBot2 | Python，异步，插件化 |
| QQ 协议 | NapCat | OneBot v11 协议，WebSocket |
| 适配器 | nonebot-adapter-onebot | 官方 OneBot 适配器 |
| 定时任务 | nonebot-plugin-apscheduler | APScheduler 定时插件 |
| HTTP 请求 | httpx | 异步 HTTP 客户端 |
| HTML 解析 | BeautifulSoup4 + lxml | 解析 RSS XML 和 HTML |
| 数据库 | SQLite + peewee | 轻量 ORM，单文件 |
| 环境管理 | conda | 用户已有环境 |

## 8. 异常处理

| 异常场景 | 处理策略 |
|----------|----------|
| 网站不可达 | 跳过本次采集，记录日志，下次重试 |
| RSS 解析失败 | 降级到分类页采集 |
| 单条消息推送失败 | 记录失败日志，不阻塞其他推送 |
| 数据库写入冲突 | INSERT OR IGNORE 天然幂等 |
| NapCat 断连 | NoneBot2 内置重连机制 |
| 文章 ID 冲突 | INSERT OR IGNORE，已存在则跳过 |

## 9. 配置项

```bash
# .env.prod
DRIVER=~fastapi
ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
SUPERUSERS=["your_qq_id"]

# 插件配置
TODAYHIT_DB_PATH=./data/todayhit.db
TODAYHIT_SCRAPE_INTERVAL=14400   # 秒，4 小时
TODAYHIT_MAX_PUSH_PER_ROUND=10
TODAYHIT_REQUEST_DELAY=2         # 秒，请求间隔
```

## 10. 未来扩展（不在本次范围）

- 接入 CAS 认证获取完整文章正文
- 支持活动日历订阅
- 接入 DeepWiki/GPT 做文章摘要
- 微信公众号同步推送
