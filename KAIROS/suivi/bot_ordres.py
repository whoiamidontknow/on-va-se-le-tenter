"""bot_ordres.py — ordres réels Tradovate du bot, appariés en trades, rapprochés des alertes TradingView.

Juger le bot sur Tradovate, jamais sur la Liste des trades (audit du 15/11). Ce script lit l'export « Orders » de
Tradovate, reconstitue les trades (entrée au marché, sortie objectif / stop / clôture au marché), donne le P&L brut
par jour, et retrouve pour chaque entrée le message JSON envoyé à PickMyTrade (même symbole, même sens, ±1 min).

Le journal d'alertes contient le jeton PickMyTrade en clair : on ne lit que les champs utiles du JSON, rien n'est
recopié.

    uv run --with pandas python bot_ordres.py <Orders.csv> <TradingView_Alerts_Log.csv>
"""
import json
import sys

import pandas as pd

VAL_POINT = {"MNQ": 2.0, "MES": 5.0}

o = pd.read_csv(sys.argv[1])
o = o[o["Status"].str.strip() == "Filled"].copy()
o["t"] = pd.to_datetime(o["Fill Time"])
o["sens"] = o["B/S"].str.strip().map({"Buy": 1, "Sell": -1})
o = o.sort_values("t")

# --- trades : position nette par contrat, une entrée puis la sortie qui ramène à plat ----------------------------
trades, ouvert = [], {}
for r in o.itertuples():
    c, q = r.Contract, r.sens * r.filledQty
    if c not in ouvert:
        ouvert[c] = dict(contrat=c, produit=r.Product, entree=r.t, sens="long" if q > 0 else "short",
                         qte=abs(q), px_e=r.avgPrice)
        continue
    e = ouvert.pop(c)
    typ = r.Type.strip()
    e.update(sortie=r.t, px_s=r.avgPrice,
             raison={"Limit": "objectif", "Stop": "stop"}.get(typ, "clôture au marché"))
    e["brut"] = (e["px_s"] - e["px_e"]) * (1 if e["sens"] == "long" else -1) * e["qte"] * VAL_POINT[e["produit"]]
    trades.append(e)
T = pd.DataFrame(trades)

# --- alertes JSON du bot (PickMyTrade) --------------------------------------------------------------------------
a = pd.read_csv(sys.argv[2])
a = a[a["Description"].str.lstrip().str.startswith("{")]
js = []
for d in a["Description"]:
    try:
        j = json.loads(d)
    except ValueError:
        continue
    if j.get("data") in ("long", "short"):
        js.append(dict(sym=j["symbol"].rstrip("1!"), sens=j["data"], px=float(j["price"]),
                       t=pd.Timestamp(j["date"]).tz_convert("Europe/Paris").tz_localize(None)))
J = pd.DataFrame(js)

print("TRADES RÉELS DU BOT (Tradovate)\n")
for r in T.itertuples():
    m = J[(J.sym == r.produit) & (J.sens == r.sens) & ((J.t - r.entree).abs() <= pd.Timedelta(minutes=1))]
    al = f"alerte {m.t.iloc[0]:%H:%M} @ {m.px.iloc[0]:.2f}" if len(m) else "AUCUNE ALERTE"
    print(f"{r.entree:%d/%m %H:%M} {r.produit} {r.sens:5} {r.qte:.0f} @ {r.px_e:<9.2f} → {r.raison:17} "
          f"{r.sortie:%H:%M} @ {r.px_s:<9.2f} {r.brut:+8.2f} $   {al}")
print("\nP&L BRUT PAR JOUR (hors commissions)")
print(T.groupby(T.entree.dt.date)["brut"].agg(["count", "sum"]).to_string())
print(f"\nTotal : {len(T)} trades, {T.brut.sum():+.2f} $ brut")
