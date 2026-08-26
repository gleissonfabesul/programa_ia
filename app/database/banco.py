from sqlalchemy import create_engine

from urllib.parse import quote_plus

from app.configs.config import config


connection_string = quote_plus(
    config.DSN
)

DATABASE_URL = (
    f"mssql+pyodbc:///?odbc_connect={connection_string}"
)

engine = create_engine(

    DATABASE_URL,

    pool_pre_ping=True,

    pool_size=10,

    max_overflow=20,

    echo=False
)