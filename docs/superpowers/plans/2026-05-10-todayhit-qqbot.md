# TodayHIT QQ Bot 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 NoneBot2 的 QQ 机器人，自动抓取"今日哈工大"网站内容，提供公告推送、关键词搜索、分类订阅和关键词提醒功能。

**Architecture:** NoneBot2 单体应用，SQLite 存储，APScheduler 定时任务，通过 RSS + 分类页 + 搜索页三层数据采集。NapCat 作为 QQ 协议端，OneBot v11 协议通信。

**Tech Stack:** Python 3.12, NoneBot2, nonebot-adapter-onebot (v11), nonebot-plugin-apscheduler, httpx, BeautifulSoup4, lxml, peewee, SQLite

**Spec:** `docs/superpowers/specs/2026-05-10-todayhit-qqbot-design.md`

---

## 文件结构总览

```
TodayHIT/
├── bot.py                          # NoneBot2 入口
├── pyproject.toml                  # 项目配置 + 依赖 + NoneBot 插件声明
├── .env.prod                       # 生产环境变量
├── .gitignore
│
├── plugins/
│   ├── today_scraper/              # 核心插件
│   │   ├── __init__.py             # 插件入口，加载子模块，注册定时任务
│   │   ├── config.py               # Pydantic 配置模型
│   │   ├── models.py               # peewee ORM 数据模型
│   │   ├── scraper.py              # 爬虫：RSS / 分类页 / 搜索页
│   │   ├── pusher.py               # 推送逻辑：订阅匹配 + 消息构建
│   │   └── commands.py             # 用户命令处理器
│   └── today_help/
│       └── __init__.py             # 帮助信息插件
│
├── tests/
│   ├── __init__.py
│   ├── test_models.py              # 数据模型测试
│   ├── test_scraper.py             # 爬虫逻辑测试
│   └── test_pusher.py              # 推送逻辑测试
│
└── data/                           # 运行时生成
    └── todayhit.db                 # SQLite 数据库
```

---

### Task 1: 项目脚手架与环境搭建

**Files:**
- Create: `pyproject.toml`
- Create: `.env.prod`
- Create: `.gitignore`
- Create: `bot.py`
- Create: `plugins/today_scraper/__init__.py`（空文件）
- Create: `plugins/today_help/__init__.py`（空文件）
- Create: `tests/__init__.py`（空文件）
- Create: `data/.gitkeep`

- [ ] **Step 1: 创建 conda 环境并安装依赖**

```bash
conda create -n todayhit python=3.12 -y
conda activate todayhit
pip install nonebot2 nonebot-adapter-onebot nonebot-plugin-apscheduler httpx beautifulsoup4 lxml peewee pytest pytest-asyncio
```

- [ ] **Step 2: 创建 pyproject.toml**

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

- [ ] **Step 3: 创建 .env.prod**

```bash
DRIVER=~fastapi
ONEBOT_WS_URLS=["ws://127.0.0.1:3001/onebot/v11/ws"]
SUPERUSERS=["YOUR_QQ_ID"]
COMMAND_START=["/"]
COMMAND_SEP=[" "]

TODAYHIT_DB_PATH=./data/todayhit.db
TODAYHIT_SCRAPE_INTERVAL=14400
TODAYHIT_MAX_PUSH_PER_ROUND=10
TODAYHIT_REQUEST_DELAY=2
```

- [ ] **Step 4: 创建 .gitignore**

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
```

- [ ] **Step 5: 创建 bot.py**

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

- [ ] **Step 6: 创建目录和空文件**

```bash
mkdir -p plugins/today_scraper plugins/today_help tests data
touch plugins/today_scraper/__init__.py plugins/today_help/__init__.py tests/__init__.py data/.gitkeep
```

- [ ] **Step 7: 验证环境**

```bash
conda activate todayhit
python -c "import nonebot; import httpx; import bs4; import peewee; print('All imports OK')"
```

Expected: `All imports OK`

- [ ] **Step 8: Commit**

```bash
git init
git add pyproject.toml .gitignore bot.py plugins/ tests/ data/.gitkeep
git commit -m "feat: project scaffolding with NoneBot2 + conda env"
```

---

### Task 2: 数据模型（peewee ORM）

**Files:**
- Create: `plugins/today_scraper/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: 编写数据模型测试**

```python
# tests/test_models.py
import pytest
from plugins.today_scraper.models import db, Article, Subscription, PushRecord, ScraperState, init_db


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
    # 重复插入应不报错（INSERT OR IGNORE）
    Article.insert(id=1, title="b", url="https://example.com/1b").on_conflict_ignore().execute()
    assert Article.select().count() == 1


def test_subscription_create_and_unique():
    Subscription.create(
        target_type="group", target_id="123456",
        sub_type="keyword", sub_value="招聘",
    )
    # 重复订阅应触发唯一约束
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
conda activate todayhit && cd c:/Users/wfy/Desktop/TodayHIT
pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'plugins.today_scraper.models'`

- [ ] **Step 3: 实现 models.py**

```python
# plugins/today_scraper/models.py
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
    id = IntegerField(primary_key=True)
    title = TextField(null=False)
    url = TextField(null=False)
    source_dept = TextField(null=True)
    category = TextField(null=True)
    published_at = DateTimeField(null=True)
    scraped_at = DateTimeField(default=datetime.now)
    summary = TextField(null=True)

    class Meta:
        table_name = "articles"


class Subscription(BaseModel):
    id = AutoField()
    target_type = TextField(null=False)  # "group" / "private"
    target_id = TextField(null=False)    # QQ群号 / QQ号
    sub_type = TextField(null=False)     # "category" / "keyword"
    sub_value = TextField(null=False)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "subscriptions"
        indexes = ((("target_type", "target_id", "sub_type", "sub_value"), True),)


class PushRecord(BaseModel):
    id = AutoField()
    article_id = IntegerField(null=False)
    target_type = TextField(null=False)
    target_id = TextField(null=False)
    pushed_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "push_records"
        indexes = ((("article_id", "target_type", "target_id"), True),)


class ScraperState(BaseModel):
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
    db.create_tables([Article, Subscription, PushRecord, ScraperState])
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_models.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/today_scraper/models.py tests/test_models.py
git commit -m "feat: add peewee ORM models for articles, subscriptions, push records, scraper state"
```

---

### Task 3: 插件配置

**Files:**
- Create: `plugins/today_scraper/config.py`

- [ ] **Step 1: 实现配置模型**

```python
# plugins/today_scraper/config.py
from pydantic import BaseModel


class TodayHITConfig(BaseModel):
    todayhit_db_path: str = "./data/todayhit.db"
    todayhit_scrape_interval: int = 14400  # 秒，4小时
    todayhit_max_push_per_round: int = 10
    todayhit_request_delay: float = 2.0  # 秒
    todayhit_base_url: str = "https://today.hit.edu.cn"
```

- [ ] **Step 2: Commit**

```bash
git add plugins/today_scraper/config.py
git commit -m "feat: add plugin pydantic config model"
```

---

### Task 4: RSS 爬虫

**Files:**
- Create: `plugins/today_scraper/scraper.py`
- Create: `tests/test_scraper.py`

- [ ] **Step 1: 编写 RSS 爬虫测试**

```python
# tests/test_scraper.py
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
    articles = parse_category_page(CATEGORY_HTML, "https://today.hit.edu.cn")
    assert len(articles) == 2
    assert articles[0]["id"] == 129723
    assert articles[0]["source_dept"] == "能源学院"


def test_parse_search_page_extracts_results():
    results = parse_search_page(SEARCH_HTML, "https://today.hit.edu.cn")
    assert len(results) == 1
    assert results[0]["title"] == "关于创新大赛的通知"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_scraper.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 scraper.py**

```python
# plugins/today_scraper/scraper.py
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
        items.append(
            {
                "id": article_id,
                "title": title,
                "url": link,
                "published_at": pub_date,
                "source_dept": None,
                "category": None,
            }
        )
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
        match = re.search(r"/article/\d{4}/\d{2}/\d{2}/(\d+)", href)
        if not match:
            continue
        article_id = int(match.group(1))
        title = link_tag.get_text(strip=True)
        dept_tag = row.select_one(".field--name-field-department, .views-field-field-department")
        source_dept = dept_tag.get_text(strip=True) if dept_tag else None
        url = base_url + href if href.startswith("/") else href
        articles.append(
            {
                "id": article_id,
                "title": title,
                "url": url,
                "source_dept": source_dept,
                "category": None,
                "published_at": None,
            }
        )
    return articles


def parse_search_page(html: str, base_url: str) -> list[dict[str, Any]]:
    """解析搜索结果页，提取标题、链接和摘要。"""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict[str, Any]] = []
    # 尝试多种选择器适配 Drupal 搜索结果
    for item in soup.select(".search-result, .search-results-item, li.search-result"):
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
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        resp = await client.get(f"{base_url}/rss.xml")
        resp.raise_for_status()
        return resp.text


async def fetch_category_page(base_url: str, category_id: int, page: int = 0) -> str:
    """异步拉取分类列表页。"""
    url = f"{base_url}/category/{category_id}"
    if page > 0:
        url += f"?page={page}"
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def fetch_search_page(base_url: str, keyword: str, page: int = 0) -> str:
    """异步拉取搜索结果页。"""
    url = f"{base_url}/search"
    params = {"keyword": keyword}
    if page > 0:
        params["page"] = str(page)
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.text
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_scraper.py -v
```

Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/today_scraper/scraper.py tests/test_scraper.py
git commit -m "feat: add RSS/category/search scraper with parsing tests"
```

---

### Task 5: 推送逻辑（订阅匹配 + 消息构建）

**Files:**
- Create: `plugins/today_scraper/pusher.py`
- Create: `tests/test_pusher.py`

- [ ] **Step 1: 编写推送逻辑测试**

```python
# tests/test_pusher.py
import pytest
from datetime import datetime
from plugins.today_scraper.models import db, Article, Subscription, PushRecord, init_db
from plugins.today_scraper.pusher import match_subscriptions, build_push_message, build_search_message


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
    Subscription.create(target_type="group", target_id="111", sub_type="category", sub_value="公告公示")
    targets = match_subscriptions(Article.get_by_id(1))
    assert ("group", "111") in targets


def test_match_keyword_subscription():
    _make_article(2, "关于招聘实验员的通知")
    Subscription.create(target_type="group", target_id="222", sub_type="keyword", sub_value="招聘")
    targets = match_subscriptions(Article.get_by_id(2))
    assert ("group", "222") in targets


def test_no_match_returns_all_subscribers_with_no_subs():
    """无任何订阅的 target 应收到所有新文章（全量推送）。"""
    _make_article(3, "某公告")
    # 没有任何订阅，但有 target 在系统中 — 此时应返回空（无订阅 = 不推送）
    targets = match_subscriptions(Article.get_by_id(3))
    assert targets == []


def test_build_push_message():
    articles = [
        {"title": "公告一", "source_dept": "能源学院", "url": "https://today.hit.edu.cn/article/2026/05/10/1"},
        {"title": "公告二", "source_dept": None, "url": "https://today.hit.edu.cn/article/2026/05/10/2"},
    ]
    msg = build_push_message(articles)
    assert "公告一" in msg
    assert "能源学院" in msg
    assert "公告二" in msg
    assert "today.hit.edu.cn" in msg


def test_build_push_message_empty():
    msg = build_push_message([])
    assert "暂无新公告" in msg or msg == ""


def test_build_search_message():
    results = [
        {"title": "创新大赛通知", "url": "https://today.hit.edu.cn/article/2026/05/08/100", "summary": "关于举办..."},
    ]
    msg = build_search_message("创新大赛", results, page=1, total=15)
    assert "创新大赛" in msg
    assert "创新大赛通知" in msg
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_pusher.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 pusher.py**

```python
# plugins/today_scraper/pusher.py
from __future__ import annotations

from typing import Any

from .models import Article, PushRecord, Subscription


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
    articles = (
        Article.select()
        .where(Article.id.not_in(pushed_ids) if pushed_ids else True)
        .order_by(Article.published_at.desc())
        .limit(limit)
    )
    return list(articles)


def mark_pushed(article_id: int, target_type: str, target_id: str) -> None:
    """记录已推送。"""
    PushRecord.insert(
        article_id=article_id,
        target_type=target_type,
        target_id=target_id,
    ).on_conflict_ignore().execute()


def build_push_message(articles: list[dict[str, Any]]) -> str:
    """构建推送消息文本。"""
    if not articles:
        return "暂无新公告"

    lines = ["📢 今日哈工大 · 新公告", "━" * 18]
    for i, a in enumerate(articles, 1):
        dept = a.get("source_dept") or "未知"
        lines.append(f"📌 {a['title']}")
        lines.append(f"   {dept}")
        lines.append(f"   {a['url']}")
        if i < len(articles):
            lines.append("")
    lines.append("━" * 18)
    lines.append(f"共 {len(articles)} 条新公告 | /today help 查看命令")
    return "\n".join(lines)


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

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_pusher.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/today_scraper/pusher.py tests/test_pusher.py
git commit -m "feat: add pusher with subscription matching and message formatting"
```

---

### Task 6: 用户命令处理器

**Files:**
- Create: `plugins/today_scraper/commands.py`

- [ ] **Step 1: 实现 commands.py**

```python
# plugins/today_scraper/commands.py
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
        items = [{"title": a.title, "source_dept": a.source_dept, "url": a.url} for a in articles]
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
        page = int(parts[1]) - 1

    try:
        html = await fetch_search_page("https://today.hit.edu.cn", keyword, page)
        results = parse_search_page(html, "https://today.hit.edu.cn")
    except Exception:
        await matcher.finish("搜索失败，请稍后重试。")
        return

    msg = build_search_message(keyword, results, page, total=len(results) * 10)  # 粗略估算
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
        Subscription.create(
            target_type=target_type, target_id=target_id,
            sub_type="category", sub_value=value,
        )
        await matcher.finish(f"已订阅分类: {value}")

    elif sub_type == "keyword":
        value = parts[1] if len(parts) > 1 else ""
        if not value:
            await matcher.finish("请输入要订阅的关键词")
        Subscription.create(
            target_type=target_type, target_id=target_id,
            sub_type="keyword", sub_value=value,
        )
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
        .where(Subscription.target_type == target_type, Subscription.target_id == target_id)
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
        .where(Subscription.target_type == target_type, Subscription.target_id == target_id)
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
```

- [ ] **Step 2: Commit**

```bash
git add plugins/today_scraper/commands.py
git commit -m "feat: add user command handlers for search/subscribe/unsubscribe/list"
```

---

### Task 7: 插件入口与定时任务

**Files:**
- Modify: `plugins/today_scraper/__init__.py`

- [ ] **Step 1: 实现插件入口**

```python
# plugins/today_scraper/__init__.py
import asyncio
from datetime import datetime

import nonebot
from nonebot import get_plugin_config, on_startup, require

from .config import TodayHITConfig
from .models import Article, ScraperState, Subscription, init_db
from .pusher import build_push_message, get_unpushed_articles, mark_pushed, match_subscriptions
from .scraper import fetch_category_page, fetch_rss, parse_category_page, parse_rss

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

# 加载命令模块（触发命令注册）
from . import commands  # noqa: F401

config = get_plugin_config(TodayHITConfig)

CATEGORY_MAP = {10: "公告公示", 11: "新闻快讯"}


@on_startup
async def startup():
    init_db(config.todayhit_db_path)


async def scrape_and_push():
    """核心定时任务：采集 + 推送。"""
    base_url = config.todayhit_base_url
    delay = config.todayhit_request_delay
    max_push = config.todayhit_max_push_per_round

    # 1. 采集 RSS
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

    # 2. 分类页补充采集
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
                ).on_conflict_ignore().execute()
                # 补充已有文章的分类
                Article.update(category=cat_name).where(
                    Article.id == a["id"], Article.category.is_null()
                ).execute()
        except Exception as e:
            nonebot.logger.warning(f"分类页 {cat_name} 采集失败: {e}")

    # 3. 推送
    unpushed = get_unpushed_articles(max_push)
    if not unpushed:
        nonebot.logger.info("无新文章需推送")
        return

    bots = nonebot.get_bots()
    if not bots:
        nonebot.logger.warning("无可用 Bot，跳过推送")
        return
    bot = next(iter(bots.values()))

    # 为每个 target 收集待推送文章
    target_articles: dict[tuple[str, str], list[dict]] = {}
    for article in unpushed:
        targets = match_subscriptions(article)
        if not targets:
            # 无订阅则不推（避免打扰）
            mark_pushed(article.id, "none", "none")
            continue
        for target_type, target_id in targets:
            key = (target_type, target_id)
            if key not in target_articles:
                target_articles[key] = []
            target_articles[key].append(
                {"title": article.title, "source_dept": article.source_dept, "url": article.url}
            )
            mark_pushed(article.id, target_type, target_id)

    # 发送消息
    for (target_type, target_id), articles in target_articles.items():
        msg = build_push_message(articles)
        try:
            if target_type == "group":
                await bot.send_group_msg(group_id=int(target_id), message=msg)
            else:
                await bot.send_private_msg(user_id=int(target_id), message=msg)
            await asyncio.sleep(3)  # 推送间隔
        except Exception as e:
            nonebot.logger.warning(f"推送到 {target_type}:{target_id} 失败: {e}")


# 注册定时任务
scheduler.add_job(
    scrape_and_push,
    "interval",
    seconds=config.todayhit_scrape_interval,
    id="todayhit_scrape",
    replace_existing=True,
)
```

- [ ] **Step 2: Commit**

```bash
git add plugins/today_scraper/__init__.py
git commit -m "feat: add plugin entry with scheduler and scrape-and-push logic"
```

---

### Task 8: 帮助插件

**Files:**
- Modify: `plugins/today_help/__init__.py`

- [ ] **Step 1: 实现帮助插件**

```python
# plugins/today_help/__init__.py
from nonebot import on_command
from nonebot.adapters.onebot.v11 import MessageEvent

help_cmd = on_command("todayhelp", aliases={"today帮助"}, priority=1, block=True)


@help_cmd.handle()
async def handle_help(event: MessageEvent):
    await help_cmd.finish(
        "📖 TodayHIT QQ Bot 使用指南\n"
        "━" * 20 + "\n\n"
        "🔔 功能概览\n"
        "  • 定时抓取今日哈工大最新公告\n"
        "  • 按分类/关键词订阅推送\n"
        "  • 在线搜索站内文章\n\n"
        "📝 命令列表\n"
        "  /today — 查看最新公告\n"
        "  /today search <关键词> — 搜索文章\n"
        "  /today sub category <分类> — 订阅分类\n"
        "  /today sub keyword <词> — 订阅关键词\n"
        "  /today unsub <序号> — 取消订阅\n"
        "  /today list — 查看我的订阅\n"
        "  /today help — 命令帮助\n\n"
        "📌 订阅分类可选: 公告公示、新闻快讯\n"
        "⏰ 推送频率: 每 4 小时自动检查"
    )
```

- [ ] **Step 2: Commit**

```bash
git add plugins/today_help/__init__.py
git commit -m "feat: add help plugin with usage guide"
```

---

### Task 9: 端到端验证

**Files:** 无新文件

- [ ] **Step 1: 运行全部测试**

```bash
conda activate todayhit && cd c:/Users/wfy/Desktop/TodayHIT
pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 2: 验证爬虫可连接真实网站**

```bash
python -c "
import asyncio
from plugins.today_scraper.scraper import fetch_rss, parse_rss
async def test():
    xml = await fetch_rss('https://today.hit.edu.cn')
    items = parse_rss(xml)
    print(f'RSS items: {len(items)}')
    for i in items[:3]:
        print(f'  - [{i[\"id\"]}] {i[\"title\"]}')
asyncio.run(test())
"
```

Expected: 输出 3 条最新文章标题

- [ ] **Step 3: 验证数据库初始化**

```bash
python -c "
from plugins.today_scraper.models import init_db, Article
init_db(':memory:')
print('DB init OK')
print(f'Articles: {Article.select().count()}')
"
```

Expected: `DB init OK` + `Articles: 0`

- [ ] **Step 4: Commit（如果有修复）**

```bash
git add -A
git commit -m "fix: end-to-end verification fixes"
```

---

## 部署检查清单

完成所有 Task 后，按以下步骤部署：

1. **NapCat 配置**：确保 NapCat 运行并开启 WebSocket 反向连接到 `ws://127.0.0.1:3001/onebot/v11/ws`
2. **修改 .env.prod**：填入你的 QQ 号作为 `SUPERUSERS`
3. **启动 Bot**：
   ```bash
   conda activate todayhit
   cd c:/Users/wfy/Desktop/TodayHIT
   python bot.py
   ```
4. **测试命令**：在 QQ 中发送 `/today help`
5. **手动触发采集**：首次启动后等待定时任务，或临时将 `TODAYHIT_SCRAPE_INTERVAL` 设小
6. **添加订阅**：`/today sub category 公告公示` 或 `/today sub keyword 招聘`
