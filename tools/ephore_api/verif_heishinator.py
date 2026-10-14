"""Compare la couleur des bougies (formule exacte EMA(ohlc4,4)>EMA(ohlc4,32) et ancienne
0.42/0.44 vs EMA33) a l etat Heishinator de l API du terminal web.
Usage : python3 verif_heishinator.py api_vitrine_instantane.json api_vitrine_20261012.json"""
import json, sys
def ema(xs, n):
    a = 2/(n+1); out=[]; e=None
    for i, x in enumerate(xs):
        if i < n - 1: out.append(None); continue
        e = sum(xs[:n])/n if e is None else a*x+(1-a)*e   # graine SMA comme ta.ema
        out.append(e)
    return out
CHAUFFE = 200
for fic in sys.argv[1:]:
    d = json.load(open(fic))
    for tf, u in d['unites'].items():
        B = u['bougies']
        cb = [i for i in u['indicateurs'] if i.get('type') == 'couleur_bougies'][0]
        etat = {p['t']*1000: p['etat'] for p in cb['points']}
        o4 = [(b['o']+b['h']+b['l']+b['c'])/4 for b in B]
        f, s = ema(o4, 4), ema(o4, 32)
        c = [b['c'] for b in B]; e33 = ema(c, 33)
        alpha = 0.42 if tf in ('2m', '15m') else 0.44
        sha = []; x = None
        for v in o4:
            x = v if x is None else alpha*v + (1-alpha)*x; sha.append(x)
        n = okN = okO = 0; zero = 0
        for i, b in enumerate(B):
            if i < CHAUFFE: continue
            ref = etat.get(b['t'])
            if ref is None: continue
            if ref == 0: zero += 1; continue
            n += 1
            okN += (f[i] > s[i]) == (ref == 1)
            okO += (sha[i] > e33[i]) == (ref == 1)
        print(f"{fic.split('/')[-1]:28} {tf:4} bougies comparées {n:5} | exacte EMA4/32 : {okN}/{n} ({100*okN/n:.2f} %) | ancienne : {okO}/{n} ({100*okO/n:.2f} %) | état 0 ignoré : {zero}")
