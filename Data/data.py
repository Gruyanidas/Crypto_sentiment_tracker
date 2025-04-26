from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import (create_engine, DateTime, String, Text, Float )
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
    source: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)                  # Store the article URL
    title: Mapped[str] = mapped_column(Text)
    article_text: Mapped[str] = mapped_column(Text)
    # Entities & Token Mentions
    crypto_mentioned: Mapped[str] = mapped_column(String(100))
    # Time Info
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Sentiment Fields
    sentiment_score: Mapped[float] = mapped_column(Float)
    sentiment_label: Mapped[str] = mapped_column(String(20))
    sentiment_model: Mapped[str] = mapped_column(String(50))

    def __repr__(self):
        return f"<NewsSentiment(title={self.title[:30]}..., sentiment={self.sentiment_label})>"

    def __str__(self):
        return (
            f"📰 {self.title[:60]}...\n"
            f"🔗 URL: {self.url}\n"
            f"🧠 Sentiment: {self.sentiment_label} ({self.sentiment_score})\n"
            f"🪙 Coins: {self.crypto_mentioned}\n"
            f"📅 Published: {self.published_at}, Scraped: {self.scraped_at}\n"
            f"📚 Source: {self.source}\n"
        )

class PriceData(Base):
    __tablename__ = "price_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    price_usd: Mapped[float] = mapped_column(Float)
    market_cap: Mapped[float] = mapped_column(Float)
    volume_24h: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(100))

    def __repr__(self):
        return f"<PriceData(symbol={self.symbol}, price_usd={self.price_usd}, timestamp={self.timestamp})>"

    def __str__(self):
        return (
            f"💰 {self.symbol.upper()} - ${self.price_usd:,.2f}\n"
            f"🏦 Market Cap: ${self.market_cap:,.0f}, Volume 24h: ${self.volume_24h:,.0f}\n"
            f"🕒 Timestamp: {self.timestamp} | Source: {self.source}"
        )
#_____________________________________________________________________#

if __name__ == "__main__":
    Base.metadata.create_all(engine)



