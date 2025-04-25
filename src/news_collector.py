import requests
from datetime import datetime, timezone
import os
import dotenv
from pprint import pprint
from transformers import pipeline
import transformers
import torch
from pathlib import Path
from Data.data import get_session, NewsSentiment
from Data.helper_data import COIN_KEYWORDS

dotenv.load_dotenv()

class NewsViaAPI:
	"""Fetches news from all available APIs"""
	#CONSTS
	COIN_DESK_API = os.getenv("COIN_DESK_API")
	COIN_DESK_URL = os.getenv("COIN_DESK_URL")
	def __init__(self):
		pass
		# model_path = Path(__file__).resolve().parent.parent / "gemma_financial_sentiment"
		# assert model_path.exists(), f"Model path not found: {model_path}"
		# self.sentiment_model = pipeline("text-classification",
        #     model=str(model_path),
        #     tokenizer=str(model_path),
        #     local_files_only=True)

	@staticmethod
	def perform_http_request(url: str, method=None, params=None, json=None, data=None, headers=None):
		"""Generic method to handle GET, POST, PUT"""
		try:
			method = method.upper()
			if method == "GET":
				response = requests.get(url=url, params=params, headers=headers, timeout=30)
			elif method == "POST":
				response = requests.post(url=url, json=json, data=data, headers=headers, timeout=30)
			elif method == "PUT":
				response = requests.put(url=url, json=json, headers=headers, timeout=30)
			elif method == "DELETE":
				response = requests.delete(url=url, headers=headers, timeout=30)
			else:
				raise ValueError(f"Unsupported HTTP method: {method}")

			response.raise_for_status()
			return response.json() if method == "GET" else response

		except requests.exceptions.Timeout:
			raise RuntimeError("Request timed out. Try again later.")
		except requests.exceptions.ConnectionError:
			raise RuntimeError("Network connection error. Check your internet.")
		except requests.exceptions.HTTPError as http_err:
			raise RuntimeError(f"HTTP error occurred: {http_err}")
		except requests.exceptions.RequestException as req_err:
			raise RuntimeError(f"Request failed: {req_err}")
		except json.JSONDecodeError:
			raise RuntimeError("Failed to parse JSON response.")

	@classmethod
	def get_coindesk_news(cls):
		params = {"lang": "EN", "limit": 10,
				  "categories": "BNB,BTC,ETH,SOL,XRP,XLM,TRX,USDT,USDC",
				  "api_key": cls.COIN_DESK_API}
		headers = {"Content-type": "application/json; charset=UTF-8"}
		data = NewsViaAPI.perform_http_request(url=cls.COIN_DESK_URL,
											   method="GET",params=params,
											   headers=headers)
		return data

	@staticmethod
	def extract_coins(text: str) -> str:
		"""Finds mentioned cryptocurrency from text news"""
		text_lower = text.lower()
		mentioned = set()

		for coin, aliases in COIN_KEYWORDS.items():
			if any(alias in text_lower for alias in aliases):
				mentioned.add(coin)

		return ",".join(sorted(mentioned)) if mentioned else "UNKNOWN"

	@staticmethod
	def unix_to_db_timestamp(unix_timestamp: int) -> datetime:
		"""Converts a Unix timestamp for DB storage"""
		return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)

	def analyze_sentiment(self, text):
		result = self.sentiment_model(text)
		return result[0]['label'], round(result[0]['score'], 3)

	def proces_coindesk_data(self, data:dict):
		"""Process data and writes it do db"""
		all_news_data = []
		with get_session() as session:
			source = "CoinDesk"
			for item in data['Data']:
				all_news_data.append((item.get("TITLE", "Unknown title"), item.get("AUTHORS", "Unknown authors"),
									  item.get("URL", "Unknown url"), item.get("BODY", "No data"),
									  item.get("KEYWORDS", "No keywords"), item.get("SENTIMENT", "No data"),
									  item.get("PUBLISHED_ON", "Unknown data")))
			for news in all_news_data:
				try:
					#check does the news exist in db, if yes, skip
					existing = session.query(NewsSentiment).filter_by(url=news[2]).first()
					if existing:
						continue
					label, sen_score = self.analyze_sentiment(news[3])
				except Exception as model_err:
					label, sen_score = "NEUTRAL", 0.0
					print(f"Sentiment fallback: {model_err}")
				try:
					new_entry = NewsSentiment(
						source=source,
						url=news[2],
						title=news[0],
						article_text=news[3],
						crypto_mentioned= NewsViaAPI.extract_coins(news[3]),
						published_at=NewsViaAPI.unix_to_db_timestamp(news[6]),
						scraped_at=datetime.now(timezone.utc),
						sentiment_label=label,
						sentiment_score=sen_score,
						sentiment_model="Gemma"
					)
					session.add(new_entry)
					session.commit()
				except Exception as db_err:
					session.rollback()
					raise db_err








