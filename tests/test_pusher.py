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


def test_no_match_returns_empty():
    _make_article(3, "某公告")
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
    assert "暂无" in msg


def test_build_search_message():
    results = [
        {"title": "创新大赛通知", "url": "https://today.hit.edu.cn/article/2026/05/08/100", "summary": "关于举办..."},
    ]
    msg = build_search_message("创新大赛", results, page=1, total=15)
    assert "创新大赛" in msg
    assert "创新大赛通知" in msg
