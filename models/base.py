import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DATABASE_USER', 'postgres')}"
    f":{os.getenv('DATABASE_PASSWORD', 'Salimata')}"
    f"@{os.getenv('DATABASE_HOST', '127.0.0.1')}"
    f":{os.getenv('DATABASE_PORT', '5433')}"
    f"/{os.getenv('DATABASE_NAME', 'regbot')}"
)

engine       = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()
