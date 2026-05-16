import pytest
from plugins.today_scraper.scraper import parse_rss, parse_category_page, parse_search_page, _url_hash, _source_label, scrape_hoa_blog


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


# ── 多源爬取工具函数测试 ──────────────────────────────


def test_url_hash_deterministic():
    h1 = _url_hash("https://example.com/article/1")
    h2 = _url_hash("https://example.com/article/1")
    assert h1 == h2
    assert isinstance(h1, int)
    assert h1 > 0


def test_url_hash_different_urls():
    h1 = _url_hash("https://example.com/a")
    h2 = _url_hash("https://example.com/b")
    assert h1 != h2


def test_source_label_known():
    assert _source_label("todayhit") == "今日哈工大"
    assert _source_label("hit_main") == "工大官网"
    assert _source_label("hitcs") == "课程资料"
    assert _source_label("hoa_blog") == "HOA博客"


def test_source_label_unknown():
    assert _source_label("unknown") == "unknown"


# ── Article 多源去重测试 ─────────────────────────────


def test_article_source_dedup():
    from plugins.today_scraper.models import db, Article, init_db
    init_db(":memory:")
    try:
        Article.create(id=100, title="a", url="https://a.com", source="hit_main", source_id="abc")
        Article.insert(id=100, title="b", url="https://a.com", source="hit_main", source_id="abc").on_conflict_ignore().execute()
        assert Article.select().count() == 1
    finally:
        db.close()


def test_article_different_source_same_url():
    from plugins.today_scraper.models import db, Article, init_db
    init_db(":memory:")
    try:
        # Same URL, different source → different records (different ids)
        id1 = _url_hash("https://example.com/x")
        id2 = _url_hash("https://example.com/x")  # same hash
        Article.create(id=id1, title="a", url="https://example.com/x", source="hit_main", source_id="aaa")
        # Different source_id allows different record (if id differs)
        Article.create(id=id1 + 99999, title="b", url="https://example.com/x", source="todayhit", source_id="bbb")
        assert Article.select().count() == 2
    finally:
        db.close()
