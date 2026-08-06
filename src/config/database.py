from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL

from src.config.config import DB


def get_engine() -> Engine:
    """
    Create and return a SQLAlchemy PostgreSQL engine.
    """

    required_settings = {
        "host": DB.get("host"),
        "port": DB.get("port"),
        "database": DB.get("database"),
        "user": DB.get("user"),
        "password": DB.get("password"),
    }

    missing = [
        key
        for key, value in required_settings.items()
        if value is None or str(value).strip() == ""
    ]

    if missing:
        raise ValueError(
            "Missing database settings in .env: "
            + ", ".join(missing)
        )

    database_url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB["user"],
        password=DB["password"],
        host=DB["host"],
        port=int(DB["port"]),
        database=DB["database"],
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )