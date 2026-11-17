import glob, os, pickle, pandas as pd, numpy as np, openpyxl, warnings; warnings.filterwarnings("ignore")
D="/Users/jeremk/ERGON/KAIROS-data/SansFuite/"
def load(f):
    wb=openpyxl.load_workbook(f, read_only=True)
    p={str(r[0]):r[1] for r in wb["Propriétés"].iter_rows(values_only=True)}
    rows=list(wb["Trades"].iter_rows(values_only=True)); df=pd.DataFrame(rows[1:],columns=rows[0])
    ent=df[df["Type"].str.startswith("Entrer")].set_index("Numéro de trade"); ex=df[df["Type"].str.startswith("Sortir")].set_index("Numéro de trade")
    b=pd.DataFrame({"t_in":ent["Date et heure"],"t_out":ex["Date et heure"],"dir":ent["Type"].map(lambda s:"L" if "long" in s else "S"),"label":ent["Signal"],"exit":ex["Signal"],"p_in":ent["Prix USD"],"pnl":ent["P&L net USD"].astype(float),"qty":ent["Taille (qté)"]}).dropna(subset=["t_out"]).sort_values("t_in")
    b["pm"]=b.pnl/b.qty; b["god"]=b.label.str.contains("GODLIKE"); b["ex"]=b.exit.str.replace(" [LS]$","",regex=True)
    return p,b
S={}
for f in sorted(glob.glob(D+"*.xlsx")):
    p,b=load(f); mode=str(p.get("Données multi-unités")); sym=p["Symbole"].split(":")[1]; tf=p["Plage temporelle"]
    S[(sym,tf,mode[:1] if mode[:1] in "ab" else "ancien")]=b
    print(f"\n== {os.path.basename(f)[-12:]} | {sym} {tf} | mode : {mode} | plage {p.get('Plage de trading')} | qty {sorted(b.qty.unique())}")
    def st(t): 
        return "n=0" if not len(t) else f"n={len(t):4d} | réussite {100*(t.pm>0).mean():4.1f} % | {t.pm.mean():6.1f} $/trade/micro | total/micro {t.pm.sum():7.0f}"
    print("   TOUS    :",st(b)); print("   GODLIKE :",st(b[b.god])); print("   56 seul :",st(b[~b.god]))
    g=b[b.god]
    for y,u in g.groupby(g.t_in.dt.year): print(f"      GODLIKE {y}: {st(u)}")
    u=g[g.t_in>="2025-11-09"]; print("   GODLIKE 12 derniers mois :",st(u),f"| {len(u)/12:.0f} trades/mois")
    print("   sorties GODLIKE :",g.groupby("ex").pm.agg(n="size",moy="mean").round(1).to_dict("index"))
pickle.dump(S,open("sf.pkl","wb"))
