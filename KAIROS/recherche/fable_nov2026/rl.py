# Chargeur des exports de recherche R16 / R48 (Strat5669_SANSFUITE, commit a8a1cbb)
# Commentaire d'entrée : d=FMH|a1=..|a4=..|b1=..|b4=..|e=..|ha=..|atr=..|sl=..|v=..|adx=..|tr=..|ds=a/b
import glob, os, pickle, warnings, openpyxl, pandas as pd, numpy as np
warnings.filterwarnings("ignore")
D = "/Users/jeremk/ERGON/KAIROS-data/SansFuite/1/"
PV = {"MNQ1!": 2.0, "MES1!": 5.0}
NUM = ["a1", "a4", "b1", "b4", "e", "ha", "atr", "sl", "v", "adx"]

def load(f):
    wb = openpyxl.load_workbook(f, read_only=True)
    p = {str(r[0]): r[1] for r in wb["Propriétés"].iter_rows(values_only=True)}
    rows = list(wb["Trades"].iter_rows(values_only=True))
    df = pd.DataFrame(rows[1:], columns=rows[0])
    ent = df[df["Type"].str.startswith("Entrer")].set_index("Numéro de trade")
    ex = df[df["Type"].str.startswith("Sortir")].set_index("Numéro de trade")
    b = pd.DataFrame({
        "t_in": ent["Date et heure"], "t_out": ex["Date et heure"],
        "dir": ent["Type"].map(lambda s: 1 if "long" in s else -1),
        "com": ent["Signal"], "exit": ex["Signal"], "p_in": ent["Prix USD"], "p_out": ex["Prix USD"],
        "pnl": ent["P&L net USD"].astype(float), "qty": ent["Taille (qté)"],
        "mfe": ent["Excursion favorable USD"].astype(float), "mae": ent["Excursion adverse USD"].astype(float),
        "bars": ent["Durée (barres)"]}).dropna(subset=["t_out"]).sort_values("t_in")
    return p, b

def parse(b, sym):
    kv = b.com.astype(str).map(lambda s: dict(x.split("=", 1) for x in s.split("|") if "=" in x))
    for k in NUM:
        b[k] = pd.to_numeric(kv.map(lambda d: d.get(k)), errors="coerce")
    b["d"] = kv.map(lambda d: d.get("d", "")); b["tr"] = kv.map(lambda d: d.get("tr")); b["ds"] = kv.map(lambda d: d.get("ds"))
    pv = PV[sym]
    risk = b.sl * pv * b.qty                      # risque en $ au stop
    b["R"] = b.pnl / risk                         # résultat net en R (commission comprise)
    b["mfeR"] = b.mfe / risk                      # excursion favorable en R
    b["maeR"] = b.mae.abs() / risk
    b["h"] = b.t_in.dt.hour + b.t_in.dt.minute / 60
    b["y"] = b.t_in.dt.year
    return b

if __name__ == "__main__":
    S = {}
    for f in sorted(glob.glob(D + "*.xlsx")):
        p, b = load(f)
        pr = next((str(v) for k, v in p.items() if k.startswith("Préréglage")), "")
        sym = p["Symbole"].split(":")[1]; tf = p["Plage temporelle"]
        if not pr.startswith("R"):
            continue
        b = parse(b, sym)
        key = (sym, tf, pr[:3])
        S[key] = b
        manq = b[NUM].isna().mean().round(3).to_dict()
        print(f"\n== {os.path.basename(f)[-12:]} | {key} | plage {p.get('Plage de trading')}")
        print(f"   n={len(b)} | qty {sorted(b.qty.unique())} | champs manquants {dict((k, v) for k, v in manq.items() if v)}")
        print(f"   commentaire type : {b.com.iloc[0]}  (longueur max {b.com.astype(str).str.len().max()})")
        print(f"   R moyen {b.R.mean():+.3f} | réussite {100*(b.R>0).mean():.1f} % | sorties {b.exit.str.replace(' [LS]$','',regex=True).value_counts().to_dict()}")
    pickle.dump(S, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rech.pkl"), "wb"))
    print("\nclés :", list(S))
