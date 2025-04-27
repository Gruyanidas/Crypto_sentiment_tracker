import pandas as pd
df = pd.read_csv('crypto_fundamental.csv')

mapping = {"positive": "Bullish",
           "negative": "Bearish",
           "neutral":  "Neutral"}

df["label"] = df["label"].map(mapping)
df.to_csv("../train_data/news_dataset_mapped.csv", index=False)