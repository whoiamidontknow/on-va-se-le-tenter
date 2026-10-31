"""V9 candidate : V8 + clause de taille de bougie (range >= 0.5 * ATR14).

Verification sur les TROIS jeux de donnees independants :
  A) 14 exports 'Base 10:10/Ajustements' , groupe 4 (verite terrain principale)
  B) ~/ERGON/Singal (filtre OFF) et ~/ERGON/Filtres (filtre ON)
  C) l'API publique du terminal web (copie du 02/10), 15m et 2m

Usage : PYTHONPATH=. python3 sim_signator_conviction_v9.py
"""
import sys, glob, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_signator_conviction import pool, v8ref, volok
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import signator_sim as S

CPOS_TH = 0.67   # position de la cloture dans la bougie (constante du CQF)
RNG_TH = 0.5   # range de la bougie >= RNG_TH * ATR14

# ---------- A) Ajustements groupe 4, bout en bout ----------
def A(truth_ma=True):
    P = pool()
    out = {}
    def v9(e):
        if not v8ref(e): return False
        return (e['rngatr'] is not None and e['rngatr'] >= RNG_TH) or (e['cpos'] is not None and e['cpos'] >= CPOS_TH)
    for nom, conv in (('V8', v8ref), ('V9', v9)):
        tp = fp = fn = 0; err = []
        for e in P:
            p = bool(conv(e))
            if p and e['truth']: tp += 1
            elif p: fp += 1; err.append(('TROP', e))
            elif e['truth']: fn += 1; err.append(('MANQ', e))
        out[nom] = (tp, fp, fn, err)
    return out

# ---------- B/C) regle reimplementee avec la clause en option ----------
def simulate(d, use_filter, rng_th=None):
    N = len(d['c']); O,H,L,C,V,T = d['o'],d['h'],d['l'],d['c'],d['v'],d['t']
    tf = S.tf_seconds(T)
    o4 = [(O[i]+H[i]+L[i]+C[i])/4 for i in range(N)]
    bull = [a > b for a, b in zip(S.ema(o4,4), S.ema(o4,32))]
    run = [1]*N
    for i in range(1,N): run[i] = run[i-1]+1 if bull[i]==bull[i-1] else 1
    tr = [H[0]-L[0]] + [max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1])) for i in range(1,N)]
    up = [0] + [max(H[i]-H[i-1],0) if H[i]-H[i-1] > L[i-1]-L[i] else 0 for i in range(1,N)]
    dn = [0] + [max(L[i-1]-L[i],0) if L[i-1]-L[i] > H[i]-H[i-1] else 0 for i in range(1,N)]
    atr, pu, pdn = S.rma(tr,14), S.rma(up,14), S.rma(dn,14)
    dx = [None if pu[i] is None else (abs(pu[i]-pdn[i])/(pu[i]+pdn[i])*100 if pu[i]+pdn[i] > 0 else 0) for i in range(N)]
    adx = S.rma(dx,14)
    m1, m2 = d.get('m1') or [], d.get('m2') or []
    ok = (len(m1) == N and sum(1 for v in m1 if v and not math.isnan(v)) > N*0.9)
    if ok:
        e50 = [v if v and not math.isnan(v) else None for v in m1]
        e60 = [v if v and not math.isnan(v) else None for v in m2]
    else:
        e50, e60 = S.ema(C,50), S.ema(C,60)
    vma = S.sma_n(V,20)
    def news(i):
        if not use_filter: return False
        for hh,mm in S.NEWS_HHMM:
            tn = T[i].replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if 0 <= (tn - T[i]).total_seconds() < tf: return True
        return False
    tp = fp = fn = 0; err = []
    for i in range(S.WARMUP, N):
        b = bull[i]; ours = False
        if (run[i] == 2 and adx[i] is not None and adx[i] >= 18
                and e50[i] is not None and e60[i] is not None
                and ((C[i] > e50[i]) if b else (C[i] < e50[i])) and not news(i)):
            db = ((C[i]-max(e50[i],e60[i])) if b else (min(e50[i],e60[i])-C[i]))/atr[i]
            ours = db >= 0.3 or (vma[i] is not None and V[i] >= vma[i])
            if ours and rng_th is not None:
                ours = (H[i]-L[i]) >= rng_th*atr[i]
            if CPOS_TH is not None and rng_th is not None and not ours:
                rg = max(H[i]-L[i], 1e-12)
                cp = (C[i]-L[i])/rg if b else (H[i]-C[i])/rg
                ours = (db >= 0.3 or (vma[i] is not None and V[i] >= vma[i])) and cp >= CPOS_TH
        orig = d['oL'][i] or d['oS'][i] or d['oLM'][i] or d['oSM'][i]
        if ours and orig: tp += 1
        elif ours: fp += 1; err.append(('TROP', T[i].isoformat()[:16]))
        elif orig: fn += 1; err.append(('MANQ', T[i].isoformat()[:16]))
    return tp, fp, fn, err

def B(folder, use_filter):
    tot = {None: [0,0,0,[]], RNG_TH: [0,0,0,[]]}
    for f in sorted(glob.glob(os.path.join(os.path.expanduser(folder), '*.csv'))):
        d = S.load(f)
        if d is None: continue
        for k in tot:
            tp,fp,fn,err = simulate(d, use_filter, k)
            tot[k][0]+=tp; tot[k][1]+=fp; tot[k][2]+=fn
            tot[k][3] += [(a, os.path.basename(f).split('_')[0], b) for a,b in err]
    return tot

# ---------- C) API ----------
def Capi(rng_th=None):
    d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_vitrine_instantane.json')))
    res = {}
    for tf in ('15m','2m'):
        U = d['unites'][tf]; Bg = U['bougies']; N = len(Bg)
        T=[b['t']//1000 for b in Bg]; O=[b['o'] for b in Bg]; H=[b['h'] for b in Bg]
        L=[b['l'] for b in Bg]; C=[b['c'] for b in Bg]; V=[b['v'] for b in Bg]
        o4=[(O[i]+H[i]+L[i]+C[i])/4 for i in range(N)]
        bull=[a>b for a,b in zip(S.ema(o4,4), S.ema(o4,32))]
        run=[1]*N
        for i in range(1,N): run[i]=run[i-1]+1 if bull[i]==bull[i-1] else 1
        tr=[H[0]-L[0]]+[max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1])) for i in range(1,N)]
        up=[0]+[max(H[i]-H[i-1],0) if H[i]-H[i-1]>L[i-1]-L[i] else 0 for i in range(1,N)]
        dn=[0]+[max(L[i-1]-L[i],0) if L[i-1]-L[i]>H[i]-H[i-1] else 0 for i in range(1,N)]
        atr=S.rma(tr,14); pu=S.rma(up,14); pdn=S.rma(dn,14)
        dx=[None if pu[i] is None else (abs(pu[i]-pdn[i])/(pu[i]+pdn[i])*100 if pu[i]+pdn[i]>0 else 0) for i in range(N)]
        adx=S.rma(dx,14); e50=S.ema(C,50); e60=S.ema(C,60)
        vma=[sum(V[i-19:i+1])/20 if i>=19 else None for i in range(N)]
        sig=set()
        for x in U['indicateurs']:
            if x.get('type')=='marqueur_prix' and str(x.get('id','')).startswith(('sig_lf','sig_sf')):
                sig.add(x['t'])
        tp=fp=fn=0; err=[]
        for i in range(300,N):
            b=bull[i]; u=False
            if run[i]==2 and adx[i] and adx[i]>=18 and ((C[i]>e50[i]) if b else (C[i]<e50[i])):
                db=((C[i]-max(e50[i],e60[i])) if b else (min(e50[i],e60[i])-C[i]))/atr[i]
                base = db>=0.3 or V[i]>=vma[i]
                u = base
                if u and rng_th is not None: u = (H[i]-L[i]) >= rng_th*atr[i]
                if CPOS_TH is not None and rng_th is not None and not u and base:
                    rg=max(H[i]-L[i],1e-12); cp=(C[i]-L[i])/rg if b else (H[i]-C[i])/rg
                    u = cp>=CPOS_TH
            o = T[i] in sig
            if u and o: tp+=1
            elif u: fp+=1; err.append(('TROP',T[i]))
            elif o: fn+=1; err.append(('MANQ',T[i]))
        res[tf]=(tp,fp,fn,err)
    return res

if __name__ == '__main__':
    print('=== A) Ajustements groupe 4 (14 fichiers, ~9000 barres, warmup 100) ===')
    a = A()
    for k in ('V8','V9'):
        tp,fp,fn,err = a[k]
        print('  %s : %d exactes / %d en trop / %d manquees'%(k,tp,fp,fn))
    print('  ecarts V9 :')
    for tag,e in a['V9'][3]:
        print('    %s %s %s %s  dB %.2f  rng/ATR %.3f  adx %.1f'%(tag,e['inst'],e['tf'],e['t'],e['dband'],e['rngatr'],e['adx']))
    print()
    print('=== B) jeux externes (derniere paire de colonnes, cf. signator_sim) ===')
    for folder, uf in (('~/ERGON/Singal', False), ('~/ERGON/Filtres', True)):
        t = B(folder, uf)
        print('  %-18s V8 %d/%d/%d   V9 %d/%d/%d'%(folder, *t[None][:3], *t[RNG_TH][:3]))
        for tag,f,ts in t[RNG_TH][3][:8]: print('      V9 %s %s %s'%(tag,f,ts))
    print()
    print('=== C) API du terminal web (copie 02/10) ===')
    r8, r9 = Capi(None), Capi(RNG_TH)
    for tf in ('15m','2m'):
        print('  %s : V8 %d/%d/%d   V9 %d/%d/%d'%(tf, *r8[tf][:3], *r9[tf][:3]))
