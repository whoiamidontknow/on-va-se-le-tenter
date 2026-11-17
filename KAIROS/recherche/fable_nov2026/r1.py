import pickle, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
S=pickle.load(open("rech.pkl","rb")); SF=pickle.load(open("sf.pkl","rb"))
PV={"MNQ1!":2.0,"MES1!":5.0}
def out(b,T,sym):
    com=2.5/(b.sl*PV[sym])            # commission aller-retour par contrat, en R
    return np.where(b.mfeR>=T, T-com, b.R)
print("clés sf:",list(SF))
for sym in ("MNQ1!","MES1!"):
    b=S[(sym,"15 minutes","R16")].copy(); b["r"]=out(b,2/3,sym)
    f=b[(b.b1>0)&(b.b4>0)&(b.e.round(1)<=0.6)]
    g=f[(f.b1>=0.025)&(f.b4>=0.025)]
    ref=SF[(sym,"15 minutes","b")]; rg=ref[ref.god]
    print(f"\n{sym} 15 min — reconstitution du 56 mode b à partir de R16")
    print(f"  reconstitué : tous n={len(f)} réussite {100*(f.r>0).mean():.1f} % R {f.r.mean():+.3f} | GODLIKE n={len(g)} réussite {100*(g.r>0).mean():.1f} % R {g.r.mean():+.3f} total$ {(g.r*g.sl*PV[sym]).sum():.0f}")
    print(f"  export réel : tous n={len(ref)} réussite {100*(ref.pm>0).mean():.1f} % | GODLIKE n={len(rg)} réussite {100*(rg.pm>0).mean():.1f} % total$/micro {rg.pm.sum():.0f}")
    m=set(ref.t_in)&set(f.t_in); print(f"  trades de l'export réel retrouvés (même heure d'entrée) : {len(m)}/{len(ref)} ; GODLIKE {len(set(rg.t_in)&set(g.t_in))}/{len(rg)}")
    # mode a
    fa=b[(b.a1>0)&(b.a4>0)&(b.e.round(1)<=0.6)]; ga=fa[(fa.a1>=0.025)&(fa.a4>=0.025)]
    ra=SF[(sym,"15 minutes","a")]; rga=ra[ra.god]
    print(f"  mode a reconstitué : GODLIKE n={len(ga)} réussite {100*(ga.r>0).mean():.1f} % R {ga.r.mean():+.3f} | export réel n={len(rga)} réussite {100*(rga.pm>0).mean():.1f} %")
print("\nBase sans filtre, R moyen selon l'objectif (R16) :")
for k,b in S.items():
    if k[2]!="R16": continue
    print(k, " ".join(f"T{T:.2f}:{out(b,T,k[0]).mean():+.3f}" for T in (0.33,0.5,0.667,1,1.5,2,4)), f"n={len(b)}")
