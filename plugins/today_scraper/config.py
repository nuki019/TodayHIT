from pydantic import BaseModel


class TodayHITConfig(BaseModel):
    todayhit_db_path: str = "./data/todayhit.db"
    todayhit_scrape_interval: int = 14400
    todayhit_max_push_per_round: int = 10
    todayhit_request_delay: float = 2.0
    todayhit_base_url: str = "https://today.hit.edu.cn"
    todayhit_admin_qqs: list[int] = [2990056153]
