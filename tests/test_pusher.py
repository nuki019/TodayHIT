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


def test_build_push_nodes():
    articles = [
        {"title": "公告一", "source_dept": "能源学院", "url": "https://today.hit.edu.cn/article/1", "published_at": datetime(2026, 5, 10, 12, 0)},
        {"title": "公告二", "source_dept": None, "url": "https://today.hit.edu.cn/article/2", "published_at": None},
    ]
    nodes = build_push_nodes(articles, bot_id=123456)
    assert len(nodes) == 2
    assert nodes[0]["type"] == "node"
    assert nodes[0]["data"]["user_id"] == "123456"
    assert nodes[0]["data"]["nickname"] == "今日哈工大"
    # content 中应包含标题
    content = nodes[0]["data"]["content"]
    assert any("公告一" in seg["data"]["text"] for seg in content if seg["type"] == "text")
    assert any("能源学院" in seg["data"]["text"] for seg in content if seg["type"] == "text")


def test_build_push_nodes_empty():
    nodes = build_push_nodes([], bot_id=123456)
    assert nodes == []
