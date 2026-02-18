#!/usr/bin/env python3
import json
import datetime as dt
import numpy as np
import pandas as pd
import yfinance as yf

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
RSI_MIN, RSI_MAX = 55, 65
RELVOL_MIN = 1.2
MAX_STRETCH = 15.0

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def fetch_sp500():
    df = pd.read_html(WIKI_SP500)[0]
    df = df.rename(columns={"Symbol":"Ticker","Security":"Company","GICS Sector":"Sector"})
    df["Ticker"] = df["Ticker"].str.replace(".", "-", regex=False)
    return df[["Ticker","Company","Sector"]]

def momentum_score(rsi14, p_vs_ma50, ret3m, relvol):
    s_rsi = max(0, min(1, 1 - abs(rsi14 - 60)/10)) if np.isfinite(rsi14) else 0
    if not np.isfinite(p_vs_ma50): s_ma = 0
    elif p_vs_ma50 < 0: s_ma = 0
    elif p_vs_ma50 <= 8: s_ma = 1
    elif p_vs_ma50 <= 15: s_ma = (15 - p_vs_ma50)/7
    else: s_ma = 0
    s_3m = max(0, min(1, ret3m/30)) if np.isfinite(ret3m) else 0
    s_rv = max(0, min(1, (relvol - 1))) if np.isfinite(relvol) else 0  # 1..2 -> 0..1 approx
    return round(100*(0.30*s_rsi + 0.25*s_ma + 0.25*s_3m + 0.20*s_rv), 0)

def main():
    base = fetch_sp500()
    tickers = base["Ticker"].tolist()
    start = (dt.date.today() - dt.timedelta(days=420)).isoformat()
    end = dt.date.today().isoformat()

    hist = yf.download(tickers, start=start, end=end, group_by="ticker", threads=True, progress=False, auto_adjust=False)

    rows = []
    D1M, D3M, D6M, D1Y = 21, 63, 126, 252

    for tk, company, sector in base.itertuples(index=False):
        try:
            h = hist[tk] if isinstance(hist.columns, pd.MultiIndex) else hist
            if h.empty: 
                continue
            close = h["Close"].dropna()
            vol = h["Volume"].dropna()
            if len(close) < 210 or len(vol) < 40:
                continue

            price = float(close.iloc[-1])
            ma50 = float(close.rolling(50).mean().iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1])
            rsi14 = float(rsi(close, 14).iloc[-1])

            def ret(days):
                if len(close) <= days: return np.nan
                return float((close.iloc[-1]/close.iloc[-(days+1)] - 1)*100)

            ret1m = ret(D1M)
            ret3m = ret(D3M)
            ret6m = ret(D6M)
            ret1y = ret(D1Y)

            v_today = float(vol.iloc[-1])
            v_avg20 = float(vol.rolling(20).mean().iloc[-1])
            relvol = float(v_today / v_avg20) if v_avg20 else np.nan

            p_vs_ma50 = float((price/ma50 - 1)*100) if ma50 else np.nan
            p_vs_ma200 = float((price/ma200 - 1)*100) if ma200 else np.nan

            pass_flag = (
                (RSI_MIN <= rsi14 <= RSI_MAX) and
                (price > ma50) and
                (relvol >= RELVOL_MIN) and
                (ret3m > 0) and
                (p_vs_ma50 <= MAX_STRETCH)
            )

            score = momentum_score(rsi14, p_vs_ma50, ret3m, relvol)

            rows.append({
                "ticker": tk,
                "company": company,
                "sector": sector,
                "price": round(price, 2),
                "rsi": round(rsi14, 2),
                "ma50": round(ma50, 2),
                "ma200": round(ma200, 2),
                "p_vs_ma50": round(p_vs_ma50, 2),
                "p_vs_ma200": round(p_vs_ma200, 2),
                "ret1m": round(ret1m, 2) if np.isfinite(ret1m) else None,
                "ret3m": round(ret3m, 2) if np.isfinite(ret3m) else None,
                "ret6m": round(ret6m, 2) if np.isfinite(ret6m) else None,
                "ret1y": round(ret1y, 2) if np.isfinite(ret1y) else None,
                "relvol": round(relvol, 2) if np.isfinite(relvol) else None,
                "score": score,
                "pass": bool(pass_flag)
            })
        except Exception:
            continue

    rows.sort(key=lambda x: (x["score"] if x["score"] is not None else -1), reverse=True)

    payload = {"updated_at": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "rows": rows}
    out_path = "frontend/data/sp500_momentum.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",",":"))

    print(f"Wrote {len(rows)} rows -> {out_path}")

if __name__ == "__main__":
    main()
