"""27/11/2026 — taux réel des alertes : pour chaque indice × unité, trades alertés depuis le 20/10, objectifs, stops,
sorties au temps (résultat inconnu si le message n'a pas de P&L). Lit tous les journaux TradingView de KAIROS-data,
n'écrit aucun texte de message (le journal contient un jeton en clair).    python3 -I taux_alertes.py"""
import csv,glob,re,collections,os
from datetime import datetime
os.chdir(os.path.expanduser("~/ERGON/KAIROS-data"))
rows={}
for f in glob.glob("**/TradingView_Alerts_Log*.csv",recursive=True)+["Dim15nov/Alerts_data.csv"]:
    for x in csv.DictReader(open(f,encoding="utf-8-sig")):
        if "Ticker" not in x: break
        rows[(x["ID de l'alerte"],x["Heure"],x["Description"])]=x
R=sorted([x for x in rows.values() if x["Ticker"].startswith("CME_MINI:M")],key=lambda x:x["Heure"])
def pnl(d):
    m=re.search(r"P&L ≈? ?(-?[\d.,   ]+)\s*\$",d)
    return float(re.sub(r"[,   ]","",m.group(1))) if m else None
T=[];ouv={}
for x in R:
    d=x["Description"];k=x["ID de l'alerte"];tk=x["Ticker"].split(":")[1]
    if "au marché maintenant" in d:
        if k in ouv: ouv[k]["res"]="sans sortie"
        ouv[k]=dict(tk=tk,t=x["Heure"],etiq="GODLIKE" if "GODLIKE" in d else "56 seul",res=None,pnl=None)
        T.append(ouv[k])
    elif ("trade terminé" in d or "FERMER" in d) and k in ouv:
        o=ouv.pop(k); o["pnl"]=pnl(d)
        o["res"]="objectif" if "OBJECTIF" in d else "stop" if "STOP" in d else "temps"
for o in ouv.values(): o["res"]="en cours/sans sortie"
T=[o for o in T if o["t"]>="2026-10-20"]
g=collections.defaultdict(list)
for o in T: g[o["tk"]].append(o)
def ligne(nom,L):
    n=len(L);w=sum(o["res"]=="objectif" for o in L);l=sum(o["res"]=="stop" for o in L)
    tp=[o for o in L if o["res"]=="temps"];tpp=sum(1 for o in tp if (o["pnl"] or 0)>0);tpn=sum(1 for o in tp if o["pnl"] is not None and o["pnl"]<=0)
    tpi=len(tp)-tpp-tpn;sx=n-w-l-len(tp)
    print(f"{nom:<16}{n:>4} | obj {w:>3} ({w/n:5.0%}) | stop {l:>3} ({l/n:5.0%}) | temps {len(tp):>3} ({len(tp)/n:4.0%}) [+{tpp} −{tpn} ?{tpi}] | sans sortie {sx} | obj/(obj+stop) {w/(w+l) if w+l else 0:4.0%} | {L[0]['t'][:10]}→{L[-1]['t'][:10]}")
order=["MNQ1!, 15m","MES1!, 15m","MNQ1!, 5m","MES1!, 5m","MNQ1!, 2m","MES1!, 2m"]
for k in order:
    if g[k]: ligne(k,g[k])
print()
ligne("TOTAL",T)
for e in ("GODLIKE","56 seul"): ligne(e,[o for o in T if o["etiq"]==e])
print()
for o in T:
    if o["t"]>="2026-11-21": print(o["tk"],o["t"],o["etiq"],o["res"],o["pnl"])
print()
for k in order+["TOTAL"]:
    L=T if k=="TOTAL" else g[k]
    s=[o["pnl"] for o in L if o["res"] in("objectif","stop") and o["pnl"] is not None]
    m=[o for o in L if o["res"] in("objectif","stop") and o["pnl"] is None]
    print(f"{k:<12} P&L obj+stop connus {sum(s):>8.0f} $ sur {len(s)} trades ({len(m)} sans montant) ; moy obj {sum(p for p in s if p>0)/max(1,sum(p>0 for p in s)):.0f} moy stop {sum(p for p in s if p<0)/max(1,sum(p<0 for p in s)):.0f}")
