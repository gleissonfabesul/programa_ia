import os
from dotenv import load_dotenv

load_dotenv()

class Configuracoes:

    DB_SERVER = os.getenv("DB_SERVER")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    ODBC_DRIVER = "ODBC Driver 17 for SQL Server"

    DSN = (
        f"Driver={{{ODBC_DRIVER}}};"
        f"Server={DB_SERVER};"
        f"Database={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"TrustServerCertificate=yes;"
    )

config = Configuracoes()