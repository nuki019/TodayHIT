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
