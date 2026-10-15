"""Chargement des exports du testeur TradingView (préréglage A, 15 min, 3 ans).

Une ligne par trade : entrée/sortie, prix, P&L net, MFE/MAE (USD et points),
durée, type de sortie. Heure du fichier conservée telle quelle (voir etude.py
pour la déduction du fuseau).
"""
import pandas as pd

DOSSIER = "/Users/jeremk/Stratégie /1er jet/"
FICHIERS = {
    "NQ": DOSSIER + "Stratégie_V1_CME_MINI_NQ1!_2026-10-15_2b13f.xlsx",
    "ES": DOSSIER + "Stratégie_V1_CME_MINI_ES1!_2026-10-15_2f924.xlsx",
}
VALEUR_POINT = {"NQ": 20.0, "ES": 50.0}
TICK = {"NQ": 0.25, "ES": 0.25}
COMMISSION_AR = 2.5  # 1,25 $ par côté


def charge(sym):
    t = pd.read_excel(FICHIERS[sym], sheet_name="Trades")
    t = t.rename(columns={
        "Numéro de trade": "n", "Date et heure": "dt", "Prix USD": "prix",
        "P&L net USD": "pnl", "Excursion favorable USD": "mfe_usd",
        "Excursion adverse USD": "mae_usd", "Durée (barres)": "barres",
    })
    e = t[t["Type"].str.startswith("Entrer")].set_index("n")
    s = t[t["Type"].str.startswith("Sortir")].set_index("n")
    d = pd.DataFrame({
        "entree_dt": pd.to_datetime(e["dt"]),
        "sortie_dt": pd.to_datetime(s["dt"]),
        "px_e": e["prix"], "px_s": s["prix"],
        "pnl": e["pnl"], "mfe_usd": e["mfe_usd"], "mae_usd": e["mae_usd"].abs(),
        "barres": e["barres"], "sortie": s["Signal"], "qte": e["Taille (qté)"],
    }).sort_index()
    vp = VALEUR_POINT[sym]
    d["pts"] = (d["px_s"] - d["px_e"])            # brut en points (long seul)
    # Les excursions du testeur incluent la commission d'entrée (1,25 $) :
    # MFE = pts×vp − 1,25 ; MAE = pts×vp + 1,25. On la retire pour avoir des points.
    d["mfe_pts"] = (d["mfe_usd"] + COMMISSION_AR / 2) / vp
    d["mae_pts"] = ((d["mae_usd"] - COMMISSION_AR / 2) / vp).clip(lower=0)
    d["stop"] = d["sortie"].str.startswith("Stop")
    d["sym"] = sym
    return d


if __name__ == "__main__":
    for s in FICHIERS:
        d = charge(s)
        print(s, len(d), d["pnl"].sum(), d["sortie"].value_counts().to_dict())
        print(d.head(3).to_string())
