"""24/11 — question de Jeremy : différences entre périodes de range et périodes de tendance.
Relevé 5669 (décisions du 56, parcours) joint au Relevé complet 15 min (Directionnor dirC / dirM / dirH, ADX)
sur la bougie signal (t1 - 15 min). 2019-2024 seulement (scellé fermé). Lecture k (bougies 1 h / 4 h terminées)
pour le résultat ; fantômes = go56b sans go56 (o).
"""
import sys, os
sys.path[:0] = [os.path.expanduser("~/ERGON/on-va-se-le-tenter/KAIROS/dataset"), os.path.dirname(os.path.abspath(__file__))]
import numpy as np, pandas as pd
from releve import charger
import releve_complet
from simu56 import un_trade, ouvertures

def stat(g):
    n = len(g); 
    return pd.Series(dict(n=n, gagnant=(g.R > 0).mean(), R=g.R.mean(), err=g.R.std() / np.sqrt(n) if n > 1 else np.nan,
                          usd=g.pnl.sum()))

for ins in ("MNQ", "MES"):
    t = charger(ins); B = releve_complet.charger(ins)
    t = t[(t.t1 < "2025-01-01") & t.parcours].copy()
    t["ts"] = t.t1 - pd.Timedelta(minutes=15)
    B = B[["t", "dirC", "dirM", "dirH", "adx"]].rename(columns={"t": "ts", "adx": "adxC"})
    j = t.merge(B, on="ts", how="left")
    vp = t.attrs["val_point"]; opn = ouvertures(t)
    rows = []
    for s, d in (("L", 1), ("S", -1)):
        u = j[j[f"go56k_{s}"] == 1].copy(); u["d"] = d; rows.append(u)
    u = pd.concat(rows)
    out = [un_trade(r, r.d, opn)[0] for r in u.itertuples(index=False)]
    u["R"] = [(o["sortie"] - o["entree"]) * r / o["sl"] for o, r in zip(out, u.d)]
    u["pnl"] = [(o["sortie"] - o["entree"]) * r * 2 * vp - 5 for o, r in zip(out, u.d)]
    u["periode"] = np.where(u.t1 < "2023-01-01", "2019-22", "2023-24")
    for c in ("dirC", "dirM", "dirH"):
        u[c + "_rel"] = np.select([u[c] == 0, u[c] == u.d], ["range", "avec"], "contre")
    u["adx_reg"] = pd.cut(u.adxC, [0, 20, 25, 200], labels=["ADX<20 range", "20-25", "ADX>25 tendance"])
    print(f"\n===== {ins} — 56 lecture bougies terminées, 2019-2024 : {len(u)} trades, jointure {j.dirC.notna().mean():.0%}")
    for c in ("dirC_rel", "dirM_rel", "dirH_rel", "adx_reg"):
        print(f"-- {c}")
        print(u.groupby([c, "periode"], observed=True).apply(stat, include_groups=False).round(3).to_string())
    # fantômes par régime (toutes décisions o ou b)
    rows = []
    for s, d in (("L", 1), ("S", -1)):
        o, b = j[f"go56_{s}"] == 1, j[f"go56b_{s}"] == 1
        v = j[o | b].copy(); v["fant"] = (b & ~o)[o | b]; v["d"] = d; rows.append(v)
    v = pd.concat(rows)
    v["dirH_rel"] = np.select([v.dirH == 0, v.dirH == v.d], ["range", "avec"], "contre")
    v["adx_reg"] = pd.cut(v.adxC, [0, 20, 25, 200], labels=["ADX<20", "20-25", "ADX>25"])
    print("-- fantômes :", v.groupby("dirH_rel").fant.agg(["mean", "size"]).round(2).to_dict("index"),
          v.groupby("adx_reg", observed=True).fant.agg(["mean", "size"]).round(2).to_dict("index"))
