"""Construit (et met en cache) les séries utilisées par l'étude CONFLUENCE / TIMING / CONTEXTE.

Réutilise features.build_series (signaux HA + vrais prix reconstitués), api.series (vrais prix API),
strat.ensure_htf (TREND/Dashator/Heishi 2 unités au-dessus). Ajoute :
  - RSI 14 et MACD(12,26,9) sur HA ;
  - la géométrie de la trendline au moment de sa cassure (pour le « repli vers la droite cassée ») ;
  - les votes de chaque module (+1 / -1 / 0) à la clôture de chaque barre.
Cache propre à ce dossier (cache_conf.pkl) pour ne pas se marcher dessus avec d'autres scripts.
"""
import sys, os, pickle, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..')))
import data, features, api, strat as T
from impl_lab_core import ema_first as ema, rma   # chemin ajouté par features

CACHE = os.path.join(HERE, 'cache_conf.pkl')
TFS = (5, 15, 30, 60)


def tl_geom(h, l, bars=10, buf=0.001, nT=3, newH=100):
    """Copie de features.trendline_breaks qui renvoie aussi la droite cassée : geo[i] = (X1, Y1, X2, Y2, côté)."""
    n = len(h)
    ph = features.pivots(h, bars); pl = features.pivots([-v for v in l], bars)
    geo = [None] * n
    for side in ('r', 's'):
        X = h if side == 'r' else [-v for v in l]
        P = ph if side == 'r' else pl
        ancH = ancB = lastH = lastB = None
        X1 = Y1 = X2 = Y2 = None; validAt = None; active = False
        for i in range(n):
            p = P[i]
            if p is not None and (ancH is None or p > ancH or i - ancB > newH):
                ancH, ancB = p, i - bars; lastH = lastB = None
            elif p is not None and i - bars > ancB and p < ancH:
                lastH, lastB = p, i - bars
            cH = cB = None
            if ancH is not None and lastB is not None and X[i] < ancH:
                cH, cB = lastH, lastB
            if cB is not None and i - ancB < 4900:
                tc = 0; ok = True
                for k in range(0, i - ancB + 1):
                    x = i - k
                    pv = ancH + (cH - ancH) / (cB - ancB) * (x - ancB)
                    if side == 'r':
                        if h[x] > pv * (1 + buf): ok = False; break
                        if h[x] >= pv * (1 - buf): tc += 1
                    else:
                        lv = -pv
                        if l[x] < lv * (1 - buf): ok = False; break
                        if l[x] <= lv * (1 + buf): tc += 1
                if ok and tc >= nT and (X1 is None or X1 != ancB or X2 != cB):
                    X1, Y1, X2, Y2 = ancB, ancH, cB, cH; validAt = i; active = True
            if active and X1 is not None and i > validAt:
                v = Y1 + (Y2 - Y1) / (X2 - X1) * (i - X1)
                if side == 'r' and h[i] > v * (1 + buf):
                    geo[i] = (X1, Y1, X2, Y2, 1); active = False
                if side == 's' and l[i] < (-v) * (1 - buf):
                    geo[i] = (X1, -Y1, X2, -Y2, -1); active = False
    return geo


def tl_value(g, j):
    X1, Y1, X2, Y2, _ = g
    return Y1 + (Y2 - Y1) / (X2 - X1) * (j - X1)


def add_extra(S):
    n = S['n']; c = S['c']
    up = [0.0] + [max(c[i] - c[i - 1], 0) for i in range(1, n)]
    dn = [0.0] + [max(c[i - 1] - c[i], 0) for i in range(1, n)]
    au, ad = rma(up, 14), rma(dn, 14)
    S['rsi'] = [None if a is None else (100 if b == 0 else 100 - 100 / (1 + a / b)) for a, b in zip(au, ad)]
    m = [a - b for a, b in zip(ema(c, 12), ema(c, 26))]
    S['macd'] = m; S['macds'] = ema(m, 9)
    S['tlg'] = tl_geom(S['h'], S['l'])
    T.ensure_htf(S)
    # EMA50 sur vrais prix (pour les replis exécutés sur vrais prix)
    S['re50'] = ema(S['rc'], 50)
    return S


def build():
    D = data.load(); out = []
    for (sym, tf), segs in sorted(D.items()):
        if tf not in features.TFMIN or features.TFMIN[tf] not in TFS: continue
        for seg in segs:
            if len(seg) < 300: continue
            t0 = time.time()
            S = features.build_series(seg, tf, sym)
            S['orig_arrow'] = [('F', 1) if r['oLF'] else ('F', -1) if r['oSF'] else ('M', 1) if r['oLM'] else
                               ('M', -1) if r['oSM'] else None for r in seg]
            S['set'] = ('MES1' if sym == 'MES1' and S['T'][0].month < 8 else ('MES' if sym in ('MES', 'MES1') else 'NQ'))
            add_extra(S); out.append(S)
            print(sym, tf, S['n'], S['set'], '%.1fs' % (time.time() - t0), flush=True)
    for u in ('15m', '2m'):
        for S in api.series(u, 'vrai'):
            S['set'] = 'API' + u[:-1]; S['orig_arrow'] = [None] * S['n']
            add_extra(S); out.append(S)
            print('API', u, S['n'], flush=True)
    pickle.dump(out, open(CACHE, 'wb'))
    return out


def load():
    return pickle.load(open(CACHE, 'rb')) if os.path.exists(CACHE) else build()


if __name__ == '__main__':
    if os.path.exists(CACHE): os.remove(CACHE)
    build()
