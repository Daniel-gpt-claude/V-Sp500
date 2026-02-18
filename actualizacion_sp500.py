import yfinance as yf
import pandas as pd
import numpy as np
import json

# Lista S&P500 desde Wikipedia
sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
sp500_table = pd.read_html(sp500_url)[0]
tickers = sp500_table["Symbol"].tolist()

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

results = []

for ticker in tickers[:80]:  # límite para evitar timeouts
    try:
        data = yf.download(ticker, period="6mo", progress=False)
        if len(data) < 50:
            continue
