"""Bibliothèque d'entrées, de filtres et de sorties, toutes bâties sur les signaux HA de CompletV3."""
import features
HTF = {1: 5, 2: 10, 3: 15, 5: 30, 15: 60, 30: 120, 60: 240, 240: 1440}


def ensure_htf(S):
    if 'htf' not in S:
        m = HTF.get(S['tfm'])
        S['htf'] = features.resample_real(S, m) if m else [None] * S['n']
        S['htf2'] = features.resample_real(S, 4 * m) if m and 4 * m <= 1440 and S['n'] / (4 * m / S['tfm']) > 60 else [None] * S['n']
    return S


# ---------------- ENTRÉES : liste de (i, sens) connue à la clôture de i
def e_sigF(S):
    return [(i, x[1]) for i, x in enumerate(S['sig']) if x and x[0] == 'F' and i > 100]


def e_sigFM(S):
    return [(i, x[1]) for i, x in enumerate(S['sig']) if x and i > 100]


def e_api(S):
    return [(i, x) for i, x in enumerate(S['api_arrow']) if x and i > 100]


def e_heishi(S):
    return [(i, 1 if S['bull'][i] else -1) for i in range(101, S['n']) if S['run'][i] == 1 and not features.news(S['T'][i], S['tfm'])]


def e_heishi2(S):
    """2e bougie du nouvel état, sans les autres filtres du Signator."""
    return [(i, 1 if S['bull'][i] else -1) for i in range(101, S['n']) if S['run'][i] == 2 and not features.news(S['T'][i], S['tfm'])]


def e_tl(S):
    out = []
    for i in range(101, S['n']):
        if S['rB'][i]: out.append((i, 1))
        elif S['sB'][i]: out.append((i, -1))
    return out


def e_sess(S, keys=('AS', 'LD', 'US')):
    """Clôture HA au-delà du haut/bas de la dernière session terminée (première clôture au-delà)."""
    out = []; c = S['c']
    for i in range(101, S['n']):
        for k in keys:
            a, b = S['SL'][k][i], S['SL'][k][i - 1]
            if a is None or a != b: continue
            if c[i] > a[0] >= c[i - 1]: out.append((i, 1)); break
            if c[i] < a[1] <= c[i - 1]: out.append((i, -1)); break
    return out


def e_mhl(S):
    out = []; c = S['c']
    for i in range(101, S['n']):
        a, b = S['MHL'][i], S['MHL'][i - 1]
        if a is None or a != b: continue
        if c[i] > a[0] >= c[i - 1]: out.append((i, 1))
        elif c[i] < a[1] <= c[i - 1]: out.append((i, -1))
    return out


def e_det_rebond(S):
    """Mèche dans une zone Detector active et clôture HA hors de la zone, du bon côté."""
    out = []; h, l, c = S['h'], S['l'], S['c']
    for i in range(101, S['n']):
        hit = None
        for top, btm in S['Zb'][i - 1]:
            if l[i] <= top and l[i] >= btm and c[i] > top: hit = 1; break
        if hit is None:
            for top, btm in S['Zs'][i - 1]:
                if h[i] >= btm and h[i] <= top and c[i] < btm: hit = -1; break
        if hit: out.append((i, hit))
    return out


def e_det_cassure(S):
    out = []
    for i in range(101, S['n']):
        if S['mitB'][i]: out.append((i, -1))
        elif S['mitS'][i]: out.append((i, 1))
    return out


def e_clx(S):
    return [(i, S['clx'][i]) for i in range(101, S['n']) if S['clx'][i]]


ENTRIES = dict(sigF=e_sigF, sigFM=e_sigFM, heishi1=e_heishi, heishi2=e_heishi2, tl=e_tl, sess=e_sess, mhl=e_mhl,
               det_rebond=e_det_rebond, det_cassure=e_det_cassure, clx=e_clx)


# ---------------- FILTRES (S, i, d) -> bool
def f_trend(S, i, d):
    ensure_htf(S); x = S['htf'][i]
    return x is not None and (x['trend'] == (d == 1))


def f_trend2(S, i, d):
    ensure_htf(S); x = S['htf2'][i]
    return x is not None and (x['trend'] == (d == 1))


def f_moy(S, i, d):
    c, a, b = S['c'][i], S['e50'][i], S['e60'][i]
    return c > max(a, b) if d == 1 else c < min(a, b)


def f_heishi_htf(S, i, d):
    ensure_htf(S); x = S['htf'][i]
    return x is not None and (x['heishi'] == (d == 1))


def f_adx(th):
    return lambda S, i, d: S['adx'][i] is not None and S['adx'][i] >= th


def f_news(S, i, d):
    return not features.news(S['T'][i], S['tfm']) and not features.news(S['T'][min(i + 1, S['n'] - 1)], S['tfm'])


def f_bull(S, i, d):
    return S['bull'][i] == (d == 1)


def f_and(*fs):
    fs = [f for f in fs if f is not None]
    return (lambda S, i, d: all(f(S, i, d) for f in fs)) if fs else None


# ---------------- SORTIES sur signal (S, j, d) -> True = sortie à l'ouverture suivante
def x_heishi(S, j, d):
    return S['bull'][j] != (d == 1)


def x_arrow(S, j, d):
    x = S['sig'][j]
    return bool(x) and x[1] == -d


def x_moy(S, j, d):
    return (S['c'][j] < S['e50'][j]) if d == 1 else (S['c'][j] > S['e50'][j])


def e_base(S, k=4):
    """Référence : une entrée toutes les k barres, dans le sens de la bougie Heishinator (pas de signal)."""
    return [(i, 1 if S['bull'][i] else -1) for i in range(101, S['n'], k)]


def e_base_long(S, k=4):
    return [(i, 1) for i in range(101, S['n'], k)]


ENTRIES['base'] = e_base
ENTRIES['base_long'] = e_base_long


# ---------------- « Feu » simplifié (PROXY : l'original a 29 voix dont des données externes non exportées)
def ensure_feu(S):
    if 'feu' in S: return S
    ensure_htf(S)
    from impl_lab_core import ema_first as ema, rma
    n = S['n']; c = S['c']; h = S['h']; l = S['l']; o = S['o']
    # RSI 14
    up = [0.0] + [max(c[i] - c[i - 1], 0) for i in range(1, n)]; dn = [0.0] + [max(c[i - 1] - c[i], 0) for i in range(1, n)]
    au, ad = rma(up, 14), rma(dn, 14)
    rsi = [None if a is None else (100 if b == 0 else 100 - 100 / (1 + a / b)) for a, b in zip(au, ad)]
    m = [a - b for a, b in zip(ema(c, 12), ema(c, 26))]; sg = ema(m, 9)
    # SuperTrend(3,10) sur HA
    atr10 = rma([h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)], 10)
    stdir = [1] * n; ub = lb = None
    for i in range(n):
        if atr10[i] is None: continue
        hl = (h[i] + l[i]) / 2; u = hl + 3 * atr10[i]; d = hl - 3 * atr10[i]
        if ub is not None:
            u = u if (u < ub or c[i - 1] > ub) else ub
            d = d if (d > lb or c[i - 1] < lb) else lb
            stdir[i] = 1 if (stdir[i - 1] == -1 and c[i] > ub) else (-1 if (stdir[i - 1] == 1 and c[i] < lb) else stdir[i - 1])
        ub, lb = u, d
    feu = [None] * n
    for i in range(n):
        H, H2 = S['htf'][i], S['htf2'][i]
        if H is None or rsi[i] is None: continue
        v = [c[i] > o[i], S['bull'][i], c[i] > S['e50'][i], rsi[i] >= 50, m[i] > sg[i], stdir[i] == 1,
             H['dash'], H['trend'], H['heishi']]
        if H2 is not None: v += [H2['dash'], H2['trend'], H2['heishi']]
        feu[i] = sum(v) / len(v)   # part LONG ; part SHORT = 1 - part
    S['feu'] = feu
    return S


def f_feu(th=0.6):
    def f(S, i, d):
        ensure_feu(S); x = S['feu'][i]
        return x is not None and (x >= th if d == 1 else (1 - x) >= th)
    return f


def e_feu(S, th=0.6):
    ensure_feu(S); out = []; F = S['feu']; st = 0
    for i in range(101, S['n']):
        if F[i] is None: continue
        ns = 1 if F[i] >= th else (-1 if 1 - F[i] >= th else 0)
        if ns and ns != st: out.append((i, ns))
        st = ns if ns else st
    return out


ENTRIES['feu'] = e_feu
