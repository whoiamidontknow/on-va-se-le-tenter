"""Compare chaque alerte d'entrée Strat5669 reçue en direct avec l'historique recalculé (export xlsx).

Usage : uv run --with pandas --with openpyxl python verif_fantomes.py <dossier Strat-Botting-data>
Cherche récursivement les TradingView_Alerts_Log*.csv et les exports Strat5669 / Stratégie 56 (15 min).
Pour chaque alerte : présente (même sens, même bougie), présente mais étiquette changée, ou ABSENTE (fantôme).
"""
import glob, os, re, sys
import pandas as pd

racine = sys.argv[1] if len(sys.argv) > 1 else "."
logs = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(glob.escape(racine), "**/TradingView_Alerts_Log*.csv"), recursive=True)])
logs = logs[logs["Description"].str.contains("au marché maintenant", na=False)
            & logs["Description"].str.contains("GODLIKE|56 seul", na=False)]
logs = logs.drop_duplicates(["Ticker", "Heure", "Description"])
logs["t"] = pd.to_datetime(logs["Heure"]).dt.tz_convert("Europe/Paris").dt.tz_localize(None)
logs["sym"] = logs["Ticker"].str.split(",").str[0].str.split(":").str[-1]
logs["tf"] = logs["Ticker"].str.split(", ").str[1]
logs["sens"] = logs["Description"].str.contains("ACHAT").map({True: "L", False: "S"})
logs["etiq"] = logs["Description"].str.contains("GODLIKE").map({True: "GODLIKE", False: "56 seul"})

exports = {}
for f in glob.glob(os.path.join(glob.escape(racine), "**/*.xlsx"), recursive=True):
    nom = os.path.basename(f)
    if not re.match(r"(Strat5669|Stratégie_56)_", nom) or os.sep + "5min" + os.sep in f:
        continue
    m = re.search(r"(MNQ1!|MES1!|BTCUSD)", nom)
    if not m:
        continue
    t = pd.read_excel(f, "Trades")
    t["Date et heure"] = pd.to_datetime(t["Date et heure"])
    e = t[t["Type"].str.startswith("Entrer")]
    exports.setdefault(m.group(1), []).append((t["Date et heure"].max(), e))

bilan = {}
for _, a in logs.sort_values("t").iterrows():
    couverts = [e for mx, e in exports.get(a.sym, []) if a.tf == "15m" and a.t <= mx]
    if not couverts:
        verdict = "pas encore dans un export"
    else:
        e = max(couverts, key=len)
        m = e[(e["Date et heure"] - a.t).abs() <= pd.Timedelta(minutes=15)]
        m = m[m["Signal"].str.startswith(a.sens)]
        if m.empty:
            verdict = "ABSENTE (fantôme)"
        else:
            etiq = "GODLIKE" if "GODLIKE" in m.iloc[0]["Signal"] else "56 seul"
            verdict = "présente" if etiq == a.etiq else f"présente, devenue « {etiq} »"
    bilan.setdefault((a.etiq, verdict.split(" (")[0]), []).append(1)
    print(f"{a.t:%d/%m %H:%M}  {a.sym:7} {a.sens} {a.etiq:8} → {verdict}")
print()
for (etiq, v), n in sorted(bilan.items()):
    print(f"{etiq:8} {v:28} {len(n)}")
