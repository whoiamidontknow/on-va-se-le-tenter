"""Exploration de la FORME de la clause de conviction des fleches Signator.

Reduit le probleme : la base (run==2 du nouvel etat Heishinator EMA(ohlc4,4)/EMA(ohlc4,32),
ADX(14,14)>=18, cloture du bon cote de l'EMA50) est figee et validee. Tous les ecarts
restants sont des ecarts de CONVICTION. On extrait donc le "pool" des barres qui passent
la base, avec un jeu de descripteurs riche, puis on evalue n'importe quelle forme de
conviction sur ce pool (exactes / en trop / manquees, par instrument et par unite de temps).

Verite terrain = groupe 4 des colonnes Signal Long/Short Fort|Moyen (cols 31-34, 0-based 30-33).
Warmup 100 barres. Moyenator 1/2 de l'original utilises comme EMA50/60 exactes.
"""
import math, statistics
from sim_signator_g4 import all_data, ema, rma, sma

WARM = 100

def sma_n(x, p):
    return [None if i < p-1 or any(y is None for y in x[i-p+1:i+1]) else sum(x[i-p+1:i+1])/p
            for i in range(len(x))]

def med_n(x, p):
    out=[None]*len(x)
    for i in range(p-1, len(x)):
        w=[y for y in x[i-p+1:i+1] if y is not None]
        if len(w)==p: out[i]=statistics.median(w)
    return out

def rsi(c, p=14):
    n=len(c); up=[0.0]*n; dn=[0.0]*n
    for i in range(1,n):
        ch=c[i]-c[i-1]; up[i]=max(ch,0.0); dn[i]=max(-ch,0.0)
    u=rma(up,p); d=rma(dn,p)
    return [None if a is None or b is None else (100.0 if b==0 else 100-100/(1+a/b)) for a,b in zip(u,d)]

def extra(d):
    """Ajoute les descripteurs candidats au dict issu de feats()."""
    o,h,l,c,v = d['o'],d['h'],d['l'],d['c'],d['v']
    n=len(c); atr=d['atr']; e50=d['e50']; e60=d['e60']; bull=d['bull']
    tick = 0.25 if d['inst']=='MES' else 0.25
    rng=[h[i]-l[i] for i in range(n)]
    o4=[(o[i]+h[i]+l[i]+c[i])/4 for i in range(n)]
    f4=ema(o4,4); f32=ema(o4,32)
    d['rng']=rng
    d['rng10']=sma_n(rng,10); d['rng20']=sma_n(rng,20); d['rng50']=sma_n(rng,50)
    d['atr50']=rma([None]+[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(1,n)],50)
    d['vmed20']=med_n(v,20); d['vmed10']=med_n(v,10); d['vma10']=sma_n(v,10); d['vma50']=sma_n(v,50)
    d['rsi']=rsi(c,14)
    sd20=[None]*n
    s20=sma_n(c,20)
    for i in range(19,n):
        m=s20[i]; sd20[i]=math.sqrt(sum((c[j]-m)**2 for j in range(i-19,i+1))/20)
    d['sd20']=sd20
    # rang percentile du volume sur N barres (volume nul = inconnu)
    for N in (20,50):
        pr=[None]*n
        for i in range(N,n):
            w=[v[j] for j in range(i-N,i) if v[j]]
            if v[i] and len(w)>=N//2: pr[i]=sum(1 for y in w if y<=v[i])/len(w)
        d['vpct%d'%N]=pr
    d['d50']=[None if not atr[i] else ((c[i]-e50[i]) if bull[i] else (e50[i]-c[i]))/atr[i] for i in range(n)]
    d['dfar']=[None if not atr[i] else ((c[i]-min(e50[i],e60[i])) if bull[i] else (max(e50[i],e60[i])-c[i]))/atr[i] for i in range(n)]
    d['dbt']=[None if not atr[i] else ((c[i]-max(e50[i],e60[i])) if bull[i] else (min(e50[i],e60[i])-c[i]))/tick for i in range(n)]
    d['dbr']=[None if not rng[i] else ((c[i]-max(e50[i],e60[i])) if bull[i] else (min(e50[i],e60[i])-c[i]))/rng[i] for i in range(n)]
    d['bandw']=[None if not atr[i] else abs(e50[i]-e60[i])/atr[i] for i in range(n)]
    d['mom']=[None if not atr[i] else (f4[i]-f32[i])/atr[i] if bull[i] else (f32[i]-f4[i])/atr[i] for i in range(n)]
    d['rngatr']=[None if not atr[i] else rng[i]/atr[i] for i in range(n)]
    d['body']=[None if not rng[i] else abs(c[i]-o[i])/rng[i] for i in range(n)]
    d['cpos']=[None if not rng[i] else ((c[i]-l[i]) if bull[i] else (h[i]-c[i]))/rng[i] for i in range(n)]
    d['atrreg']=[None if not d['atr50'][i] else atr[i]/d['atr50'][i] for i in range(n)]
    return d

def pool(warm=WARM, adx_th=18.0, truth_ma=True):
    """Liste de dicts : une entree par barre qui passe la base figee."""
    P=[]
    for d in all_data(truth_ma):
        extra(d)
        for i in range(warm, len(d['c'])):
            if d['adx'][i] is None or d['atr'][i] is None or d['dband'][i] is None: continue
            b=d['bull'][i]
            if d['run'][i]!=2: continue
            if d['adx'][i] < adx_th: continue
            if not (d['c'][i] > d['e50'][i] if b else d['c'][i] < d['e50'][i]): continue
            truth = bool(d['LF'][i] or d['SF'][i] or d['LM'][i] or d['SM'][i])
            vok = bool(d['v'][i])            # volume renseigne ?
            e=dict(inst=d['inst'], tf=d['tf'], t=d['t'][i][:16], bull=b, truth=truth,
                   dband=d['dband'][i], adx=d['adx'][i], has_vol=vok,
                   vr = (d['v'][i]/d['vma'][i]) if (vok and d['vma'][i]) else None,
                   vrmed = (d['v'][i]/d['vmed20'][i]) if (vok and d['vmed20'][i]) else None,
                   vrmed10 = (d['v'][i]/d['vmed10'][i]) if (vok and d['vmed10'][i]) else None,
                   vr10 = (d['v'][i]/d['vma10'][i]) if (vok and d['vma10'][i]) else None,
                   vr50 = (d['v'][i]/d['vma50'][i]) if (vok and d['vma50'][i]) else None,
                   vpct20=d['vpct20'][i], vpct50=d['vpct50'][i])
            for k in ('d50','dfar','dbt','dbr','bandw','mom','rngatr','body','cpos','atrreg','rsi','sc'):
                e[k]=d[k][i]
            e['dbrng10'] = None if not d['rng10'][i] else (d['dband'][i]*d['atr'][i])/d['rng10'][i]
            e['dbrng20'] = None if not d['rng20'][i] else (d['dband'][i]*d['atr'][i])/d['rng20'][i]
            e['dbsd20']  = None if not d['sd20'][i] else (d['dband'][i]*d['atr'][i])/d['sd20'][i]
            e['dbatr50'] = None if not d['atr50'][i] else (d['dband'][i]*d['atr'][i])/d['atr50'][i]
            # --- descripteurs decales / cumules sur les 2 bougies du nouvel etat
            j=i-1
            e['dband_p']=d['dband'][j]; e['d50_p']=d['d50'][j]
            e['dband_max2']=max(d['dband'][i],d['dband'][j]) if d['dband'][j] is not None else d['dband'][i]
            e['dband_min2']=min(d['dband'][i],d['dband'][j]) if d['dband'][j] is not None else d['dband'][i]
            e['dband_sum2']=(d['dband'][i]+d['dband'][j]) if d['dband'][j] is not None else None
            vj=d['v'][j]; vm=d['vma'][i]
            e['vr_p']=(vj/d['vma'][j]) if (vj and d['vma'][j]) else None
            e['vr_max2']=max(x for x in (e['vr'],e['vr_p']) if x is not None) if (e['vr'] is not None or e['vr_p'] is not None) else None
            e['vr_sum2']=((d['v'][i]+vj)/(2*vm)) if (d['v'][i] and vj and vm) else None
            e['rngsum2']=((d['rng'][i]+d['rng'][j])/d['atr'][i]) if d['atr'][i] else None
            e['dmove2']=((d['c'][i]-d['c'][j-1]) if b else (d['c'][j-1]-d['c'][i]))/d['atr'][i] if d['atr'][i] else None
            e['adx_p']=d['adx'][j]
            e['dadx']=(d['adx'][i]-d['adx'][j]) if (d['adx'][i] is not None and d['adx'][j] is not None) else None
            P.append(e)
    return P

def score(P, conv):
    """conv(e)->bool. Renvoie (tp,fp,fn) global + par instrument + par tf."""
    g=[0,0,0]; byi={}; bytf={}
    for e in P:
        p=bool(conv(e)); t=e['truth']
        k=0 if (p and t) else (1 if (p and not t) else (2 if t else None))
        if k is None: continue
        g[k]+=1
        byi.setdefault(e['inst'],[0,0,0])[k]+=1
        bytf.setdefault(e['tf'],[0,0,0])[k]+=1
    return tuple(g), byi, bytf

def v8conv(e, db=0.3, vk=1.0):
    return (e['dband'] is not None and e['dband']>=db) or (e['vr'] is not None and e['vr']>=vk)

if __name__=='__main__':
    P=pool()
    print('pool', len(P), 'vraies', sum(1 for e in P if e['truth']))
    print('sans volume dans le pool', sum(1 for e in P if not e['has_vol']),
          'dont vraies', sum(1 for e in P if not e['has_vol'] and e['truth']))
    g,byi,bytf=score(P, v8conv)
    print('V8 (ref) tp/fp/fn', g); print(' par instr', byi); print(' par tf', bytf)

# ---- semantique nz() de Pine : sur une barre sans volume, volume=0 et sma20=0,
# ---- donc 0>=0 est VRAI : la clause volume passe toujours. C'est ce que fait la V8.
def volok(e, k=1.0):
    if not e['has_vol']: return True
    return e['vr'] is not None and e['vr'] >= k

def v8ref(e):
    return (e['dband'] >= 0.3) or volok(e, 1.0)
