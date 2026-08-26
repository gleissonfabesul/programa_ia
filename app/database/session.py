from sqlalchemy.orm import sessionmaker

from app.database.database import engine


SessaoLocal = sessionmaker(

    autocommit=False,

    autoflush=False,

    bind=engine
)