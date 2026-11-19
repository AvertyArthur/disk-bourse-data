"""Récupère les cours via OpenBB (fournisseur gratuit yfinance) et calcule les indicateurs
pour l'appli Mon Desk Bourse. Résultat : data/marche.json"""
import json, math, sys, datetime as dt
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "symbols.json").read_text(encoding="utf-8"))
START = (dt.date.today() - dt.timedelta(days=430)).isoformat()

try:
    from openbb import obb
    obb.user.preferences.output_type = "dataframe"
    SOURCE = "OpenBB (yfinance)"
except Exception as e:  # OpenBB indisponible : on passe directement par yfinance
    print("OpenBB indisponible, repli sur yfinance :", e)
    obb = None
    SOURCE = "yfinance"


def history(ticker: str) -> pd.DataFrame:
    df = None
    if obb is not None:
        try:
            df = obb.equity.price.historical(ticker, start_date=START, provider="yfinance")
        except Exception as e:
            print(f"  OpenBB a échoué pour {ticker} : {e}")
    if df is None or len(df) == 0:
        import yfinance as yf
        df = yf.download(ticker, start=START, progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index).tz_localize(None) if getattr(pd.to_datetime(df.index), "tz", None) else pd.to_datetime(df.index)
    df = df[["open", "high", "low", "close"]].dropna(subset=["close"]).sort_index()
    return df


def rsi(close: pd.Series, n: int = 14) -> float | None:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, math.nan)
    v = 100 - 100 / (1 + rs)
    v = v.iloc[-1]
    return None if pd.isna(v) else round(float(v), 1)


def r(x, n=4):
    return None if x is None or pd.isna(x) else round(float(x), n)


def pct(a, b):
    return None if a is None or b is None or b == 0 or pd.isna(a) or pd.isna(b) else round((a / b - 1) * 100, 2)


def analyse(item: dict, keep_closes: bool = True) -> dict:
    df = history(item["ticker"])
    if len(df) < 2:
        raise ValueError("pas assez de données")
    c = df["close"]
    last = float(c.iloc[-1])
    sma = {n: (float(c.tail(n).mean()) if len(c) >= n else None) for n in (20, 50, 200)}
    sma50_prev = float(c.iloc[-60:-10].mean()) if len(c) >= 60 else None  # moyenne 50 j il y a 10 séances
    tail20 = df.tail(20)
    tail252 = df.tail(252)
    tend = "neutre"
    pente = None if sma50_prev is None or sma[50] is None else (1 if sma[50] > sma50_prev else -1)
    if sma[50] and sma[200]:
        # haussière : cours au-dessus des deux moyennes et moyenne 50 j qui monte ; baissière : l'inverse
        if last > sma[50] and last > sma[200] and pente != -1:
            tend = "haussiere"
        elif last < sma[50] and last < sma[200] and pente != 1:
            tend = "baissiere"
    elif sma[50]:
        tend = "haussiere" if last > sma[50] * 1.02 else "baissiere" if last < sma[50] * 0.98 else "neutre"

    def back(n):
        return float(c.iloc[-1 - n]) if len(c) > n else None

    out = {
        "sym": item["sym"], "nom": item["nom"], "ticker": item["ticker"],
        "date": df.index[-1].strftime("%Y-%m-%d"),
        "prix": r(last), "var1j": pct(last, back(1)), "var1s": pct(last, back(5)),
        "var1m": pct(last, back(21)), "var3m": pct(last, back(63)), "var1a": pct(last, back(252)),
        "sma20": r(sma[20]), "sma50": r(sma[50]), "sma200": r(sma[200]),
        "rsi": rsi(c), "tendance": tend,
        "support": r(tail20["low"].min()), "resistance": r(tail20["high"].max()),
        "plusBas52s": r(tail252["low"].min()), "plusHaut52s": r(tail252["high"].max()),
        "volatilite20j": r(c.pct_change().tail(20).std() * math.sqrt(252) * 100, 1),
    }
    if sma[50] is not None and sma50_prev is not None:
        out["sma50Pente"] = "monte" if sma[50] > sma50_prev else "baisse"
    if keep_closes:
        out["closes"] = [[d.strftime("%Y-%m-%d"), r(v)] for d, v in c.tail(300).items()]
    return out


def main():
    res = {"majLe": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "source": SOURCE,
           "valeurs": {}, "indices": {}, "erreurs": {}}
    for group, key in (("valeurs", "valeurs"), ("indices", "indices")):
        for item in CFG.get(group, []):
            print(f"{item['sym']} ({item['ticker']})…")
            try:
                res[key][item["sym"]] = analyse(item, keep_closes=(group == "valeurs"))
            except Exception as e:
                print("  erreur :", e)
                res["erreurs"][item["sym"]] = str(e)[:200]
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "marche.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = len(res["valeurs"]) + len(res["indices"])
    print(f"Terminé : {ok} séries, {len(res['erreurs'])} erreur(s).")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
