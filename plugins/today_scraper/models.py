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
    target_type = TextField(null=False)
    target_id = TextField(null=False)
    sub_type = TextField(null=False)
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
