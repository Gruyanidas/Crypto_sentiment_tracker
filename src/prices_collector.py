import requests
from datetime import datetime
import os, dotenv
from news_collector import NewsViaAPI
from Data.data import get_session
from Data.data import PriceData
dotenv.load_dotenv()

class PriceCollector:

	def __init__(self):
		self.COINGECKO_ENDPOINT = os.getenv('COINGECKO_ENDPOINT')
		self.COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')

	def get_price_data(self):
		"""Fetches crypto prices for CoinGecko"""
		headers = {"accept": "application/json",
				   "x-cg-api-key": self.COINGECKO_API_KEY}
		params = {
			"vs_currency": "usd",
			"symbols": "btc,eth,bnb,xrp,xlm,usdt,usdc,sol,trx",
			"price_change_percentage": "24h",
			"precision": "2"}
		data = NewsViaAPI.perform_http_request(url=self.COINGECKO_ENDPOINT,
											   method='GET',
											   params=params,
											   headers=headers)
		return data

	@staticmethod
	def proces_coingecko_data(data:dict) -> None:
		"""Process data and writes them to db table"""
		with get_session() as session:
			for coin in data:
				symbol = coin.get("symbol")
				price_usd = coin.get("current_price")
				market_cap = coin.get("market_cap")
				volume_24h = coin.get("total_volume")
				timestamp = datetime.fromisoformat(coin["last_updated"].replace("Z", "+00:00"))
				source = "CoinGecko"
				try:
					new_entry = PriceData(
						symbol=symbol,
						price_usd=price_usd,
						market_cap=market_cap,
						volume_24h=volume_24h,
						timestamp=timestamp,
						source=source)
					session.add(new_entry)
					session.commit()
				except Exception as e:
					print(f"Error writing to db: {e}")
					continue

priceCol = PriceCollector()
data = priceCol.get_price_data()
priceCol.proces_coingecko_data(data)