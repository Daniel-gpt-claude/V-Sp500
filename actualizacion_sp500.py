import json
import math
from datetime import datetime, timezone

import pandas as pd
import requests
import numpy as np

# =========================
# Configuración
# =========================

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

headers = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()

tables = pd.read_html(response.text, flavor="html5lib")

df = tables[0]


# Filtros (los mismos que tu UI muestra arriba)
RSI_MIN = 55
RSI_MAX = 65
REL_VOL_MIN = 1.2
RET_3M_MIN = 0.0
PCT_VS_MA50_MAX = 15.0  # % arriba de MA50 permitido
LOOKBACK_DAYS = 260     # ~1 año bursátil para calcular retornos y MA50
RSI_PERIOD = 14
MA_PERIOD = 50
VOL_PERIOD = 20

OUT_FILE_ROOT = "sp500.json"
...
df.to_json(OUT_FILE_ROOT, orient="records")


# =========================
# Utilidades
# =========================

def safe_float(x):
  try:
    if x is None:
      return None
    if isinstance(x, (np.floating, np.integer)):
      return float(x)
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
      return None
    return float(x)
  except Exception:
    return None


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
  # RSI clásico (Wilder)
  delta = close.diff()
  gain = delta.clip(lower=0)
  loss = -delta.clip(upper=0)

  avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
  avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

  rs = avg_gain / avg_loss.replace(0, np.nan)
  rsi = 100 - (100 / (1 + rs))
  return rsi


def pct_change_over(close: pd.Series, days: int) -> float | None:
  if close is None or len(close) < days + 1:
    return None
  a = close.iloc[-(days+1)]
  b = close.iloc[-1]
  if pd.isna(a) or pd.isna(b) or a == 0:
    return None
  return float((b / a) - 1.0)


def get_sp500_constituents():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }

    r = requests.get(SP500_WIKI_URL, headers=headers, timeout=30)
    print("WIKI status:", r.status_code)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")

    # La tabla correcta en Wikipedia suele tener id="constituents"
    table = soup.find("table", {"id": "constituents"})
    if table is None:
        # fallback: primera tabla con clase wikitable sortable
        table = soup.find("table", {"class": "wikitable"})
    if table is None:
        raise RuntimeError("No encontré la tabla de constituyentes en Wikipedia.")

    df = pd.read_html(str(table))[0]

    df = df.rename(columns={
        "Symbol": "ticker",
        "Security": "company",
        "GICS Sector": "sector",
    })

    return df[["ticker", "company", "sector"]]



def score_row(rsi, price_vs_ma50, relvol, ret1m, ret3m, ret1y):
  # Score simple (técnico) para ordenar “lo más atractivo” dentro del filtro.
  # Pesos ajustables.
  score = 0.0

  # RSI cerca de 60 es “sweet spot”
  if rsi is not None:
    score += max(0, 10 - abs(rsi - 60))

  # Premia estar arriba de MA50 pero sin estar demasiado extendido
  if price_vs_ma50 is not None:
    score += max(0, 10 - (price_vs_ma50 / 2))

  # Volumen relativo
  if relvol is not None:
    score += min(10, (relvol - 1) * 10)

  # Retornos
  for v, w in [(ret1m, 8), (ret3m, 10), (ret1y, 6)]:
    if v is not None:
      score += w * max(-1, min(1, v))  # recorta extremos

  return float(score)


# =========================
# Main
# =========================

def main():
  meta = get_sp500_constituents()

  tickers = meta["ticker"].tolist()

  # Descargamos precios en bloques (yfinance)
  # group_by='ticker' para columnas multiindex
  data = yf.download(
    tickers=tickers,
    period=f"{LOOKBACK_DAYS}d",
    interval="1d",
    group_by="ticker",
    auto_adjust=False,
    threads=True,
    progress=False,
  )

  rows = []
  now_iso = datetime.now(timezone.utc).isoformat()

  for _, m in meta.iterrows():
    t = m["ticker"]
    company = m["company"]
    sector = m["sector"]

    try:
      if isinstance(data.columns, pd.MultiIndex):
        if t not in data.columns.get_level_values(0):
          continue
        df = data[t].dropna(how="any")
      else:
        # si viene simple (cuando es 1 ticker)
        df = data.dropna(how="any")

      if df is None or df.empty:
        continue

      close = df["Close"].dropna()
      vol = df["Volume"].dropna()

      if len(close) < max(MA_PERIOD, RSI_PERIOD, VOL_PERIOD) + 5:
        continue

      ma50 = close.rolling(MA_PERIOD).mean()
      rsi = compute_rsi(close, RSI_PERIOD)

      # Últimos valores
      last_price = close.iloc[-1]
      last_ma50 = ma50.iloc[-1]
      last_rsi = rsi.iloc[-1]

      # Volumen relativo: vol actual vs media 20
      vol_ma20 = vol.rolling(VOL_PERIOD).mean()
      last_relvol = None
      if not pd.isna(vol_ma20.iloc[-1]) and vol_ma20.iloc[-1] != 0:
        last_relvol = float(vol.iloc[-1] / vol_ma20.iloc[-1])

      # % vs MA50
      p_vs_ma50 = None
      if not pd.isna(last_ma50) and last_ma50 != 0:
        p_vs_ma50 = float((last_price / last_ma50 - 1.0) * 100)

      # Retornos aproximados (21d ~ 1m, 63d ~ 3m, 252d ~ 1y)
      ret1m = pct_change_over(close, 21)
      ret3m = pct_change_over(close, 63)
      ret1y = pct_change_over(close, 252)

      # Limpieza
      last_price = safe_float(last_price)
      last_ma50 = safe_float(last_ma50)
      last_rsi = safe_float(last_rsi)
      last_relvol = safe_float(last_relvol)
      p_vs_ma50 = safe_float(p_vs_ma50)

      # Filtro momentum (como tu UI)
      passes = True
      if last_rsi is None or not (RSI_MIN <= last_rsi <= RSI_MAX):
        passes = False
      if p_vs_ma50 is None or p_vs_ma50 < 0:
        passes = False
      if p_vs_ma50 is not None and p_vs_ma50 > PCT_VS_MA50_MAX:
        passes = False
      if last_relvol is None or last_relvol < REL_VOL_MIN:
        passes = False
      if ret3m is None or ret3m < RET_3M_MIN:
        passes = False

      score = score_row(last_rsi, p_vs_ma50, last_relvol, ret1m, ret3m, ret1y)

      rows.append({
        "ticker": t,
        "company": company,
        "sector": sector,
        "price": last_price,
        "rsi": last_rsi,
        "ma50": last_ma50,
        "p_vs_ma50": p_vs_ma50,     # %
        "relvol": last_relvol,
        "ret1m": safe_float(ret1m),
        "ret3m": safe_float(ret3m),
        "ret1y": safe_float(ret1y),
        "score": safe_float(score),
        "passes": bool(passes),
      })

    except Exception:
      # Si un ticker truena, seguimos
      continue

  # Orden: primero los que pasan filtro, luego por score desc
  df_rows = pd.DataFrame(rows)
  if not df_rows.empty:
    df_rows["passes_int"] = df_rows["passes"].astype(int)
    df_rows = df_rows.sort_values(
      by=["passes_int", "score"],
      ascending=[False, False],
      kind="mergesort"
    ).drop(columns=["passes_int"])

  payload = {
    "generated_at": now_iso,
    "source": "Yahoo Finance via yfinance",
    "filters": {
      "rsi_min": RSI_MIN,
      "rsi_max": RSI_MAX,
      "relvol_min": REL_VOL_MIN,
      "ret3m_min": RET_3M_MIN,
      "pct_vs_ma50_max": PCT_VS_MA50_MAX,
      "price_above_ma50": True
    },
    "rows": df_rows.to_dict(orient="records") if not df_rows.empty else []
  }

  with open(OUT_FILE_ROOT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)

  print(f"OK: wrote {OUT_FILE_ROOT} with {len(payload['rows'])} rows at {now_iso}")


if __name__ == "__main__":
  main()
