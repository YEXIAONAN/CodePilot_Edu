"""应用配置：所有敏感项均来自环境变量，不在代码中硬编码。"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "CodePilot Edu Backend"
    app_env: str = "development"
    api_prefix: str = "/api/v1"

    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    demo_token: str = ""

    # 主库只接受 MySQL + PyMySQL；缺少配置或写入 SQLite 时直接启动失败，
    # 避免任何环境下静默回退到本地文件库。
    database_url: str = ""
    test_database_url: str = ""

    # 连接池与超时（秒）
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout_seconds: int = 5
    db_pool_recycle_seconds: int = 1800
    db_connect_timeout_seconds: int = 5
    db_io_timeout_seconds: int = 10

    # 评测限制（单位见字段名）
    max_source_bytes: int = 16 * 1024
    judge_docker_bin: str = "docker"
    judge_image: str = "judge-c:latest"
    judge_timeout_seconds: int = 25
    judge_case_timeout_ms: int = 2000
    judge_max_output_bytes: int = 4096
    judge_max_cases: int = 8
    judge_max_concurrency: int = 2

    # AI 服务：AI_ENABLED=false 时全部走规则提示
    ai_enabled: bool = False
    ai_base_url: str = ""
    ai_api_key: str = Field(default="", repr=False)
    ai_model: str = ""
    ai_timeout: float = 15.0

    @field_validator("database_url")
    @classmethod
    def _require_mysql(cls, value: str) -> str:
        if not value:
            raise ValueError("DATABASE_URL 未配置（必须为 mysql+pymysql:// 连接串）")
        if not value.startswith("mysql+pymysql://"):
            raise ValueError(
                "DATABASE_URL 仅支持 mysql+pymysql://，禁止 SQLite 或内存库"
            )
        return value

    @field_validator("test_database_url")
    @classmethod
    def _test_database_must_be_mysql(cls, value: str) -> str:
        if value and not value.startswith("mysql+pymysql://"):
            raise ValueError("TEST_DATABASE_URL 仅支持 mysql+pymysql://")
        return value

    @field_validator("cors_origins")
    @classmethod
    def _no_wildcard_cors(cls, value: str) -> str:
        origins = [item.strip() for item in value.split(",") if item.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS 不允许通配符 *，请填写受控来源")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_enabled and self.ai_base_url and self.ai_api_key and self.ai_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
