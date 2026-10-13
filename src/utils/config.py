from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    # 大模型
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    llm_temperature: float = 0.0

    # 路径
    db_path: Path = ROOT_DIR / "data" / "shop.db"
    output_dir: Path = ROOT_DIR / "output"
    log_dir: Path = ROOT_DIR / "logs"
    mcp_server_path: Path = ROOT_DIR / "src" / "mcp_servers" / "ecomdb_server.py"

    # 异常判断阈值（改这里就能调报警灵敏度，不用翻业务代码）
    bad_review_threshold: float = 15.0       # 差评率>=15%报警
    bad_review_high: float = 30.0            # 差评率>=30%为high级
    refund_threshold: float = 10.0           # 退款率>=10%报警
    gmv_drop_ratio: float = 0.30             # GMV环比跌>=30%
    store_bad_review_jump: float = 8.0       # 全店差评率环比上升>=8个百分点
    store_refund_jump: float = 5.0            # 全店退款率环比上升>=5个百分点

    # 日期窗口（天）
    recent_days: int = 7
    compare_days: int = 14

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
