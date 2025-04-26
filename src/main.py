from pathlib import Path
from news_collector import NewsViaAPI

# Ensure the /Data directory exists
data_dir = Path(__file__).resolve().parent / "Data"


#TEST BASED MAIN ATM
news_collector = NewsViaAPI()
data = news_collector.get_coindesk_news()
print(news_collector.extract_coins(data['Data'][0]["BODY"]))