from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, DateTime, Integer, String, Text, Float
)
import dotenv
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, sessionmaker
)
dotenv.load_dotenv()

#DB CREATION _______________________________________________________________#
class Base(DeclarativeBase):
    pass
#Set db path and make sure it exists
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "Data" / "crypto_sentiment.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

#Set up the engine
engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)

#Use session
SessionLocal = sessionmaker(bind=engine)
def get_session():
    return SessionLocal()

class NewsSentiment(Base):
    __tablename__ = "news_sentiment"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Metadata
    source: Mapped[str] = mapped_column(String(100))        # e.g., 'CoinDesk'
    url: Mapped[str] = mapped_column(Text)                  # Store the article URL
    title: Mapped[str] = mapped_column(Text)                # Headline for fast lookup
    article_text: Mapped[str] = mapped_column(Text)         # Full scraped article content
    # Entities & Token Mentions
    crypto_mentioned: Mapped[str] = mapped_column(String(100))  # e.g., 'BTC, ETH' or just one
    # Time Info
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))  # When you scraped it
    # Sentiment Fields
    sentiment_score: Mapped[float] = mapped_column(Float)       # e.g., -1.0 to 1.0
    sentiment_label: Mapped[str] = mapped_column(String(20))    # 'Positive', 'Neutral', 'Negative'
    sentiment_model: Mapped[str] = mapped_column(String(50))    # e.g., 'VADER', 'BERT'


class PriceData(Base):
    __tablename__ = "price_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10))
    price_usd: Mapped[float] = mapped_column(Float)
    market_cap: Mapped[float] = mapped_column(Float)
    volume_24h: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String(100))
#_____________________________________________________________________#

if __name__ == "__main__":
    Base.metadata.create_all(engine)



