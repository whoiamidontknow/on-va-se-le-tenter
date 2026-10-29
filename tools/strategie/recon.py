"""Reconstitution des VRAIS prix (open/high/low/close) à partir des seules bougies Heiken Ashi.

Faits exacts :
  c_HA = (o+h+l+c)/4            -> o + h + l + c = K = 4*c_HA
  h_HA = max(h, o_HA)           -> si h_HA > o_HA + eps : h = h_HA exactement ; sinon h <= o_HA
  l_HA = min(l, o_HA)           -> si l_HA < o_HA - eps : l = l_HA exactement ; sinon l >= o_HA
  (c_HA <= h et c_HA >= l toujours)
Hypothèse de continuité : o_t = c_{t-1} ± g (g = 1 tick ; remise à zéro aux coupures de séance).
On propage un INTERVALLE pour le close, en avant puis en arrière (lissage), on prend le milieu
de l'intersection. o et c jouent des rôles symétriques dans les contraintes.
Validé sur l'API (vrais prix connus) : voir __main__.
"""


def _box(b, eps):
    oH, hH, lH, cH = b['o'], b['h'], b['l'], b['c']
    K = 4 * cH
    if hH > oH + eps:
        Hlo = Hhi = hH
    else:
        Hlo, Hhi = cH, oH
    if lH < oH - eps:
        Llo = Lhi = lH
    else:
        Llo, Lhi = oH, cH
    if Hhi < Hlo:
        Hhi = Hlo
    if Lhi < Llo:
        Lhi = Llo
    return K, Hlo, Hhi, Llo, Lhi


def _crange(o, K, Hlo, Hhi, Llo, Lhi):
    """Intervalle faisable de c pour un o donné (None si infaisable)."""
    h1 = max(Hlo, o, (K - o - Llo) / 2)
    if h1 > Hhi + 1e-9:
        return None
    cmax = K - o - Llo - h1
    l2 = min(Lhi, o, (K - o - Hhi) / 2)
    if l2 < Llo - 1e-9:
        return None
    cmin = K - o - Hhi - l2
    if cmin > cmax + 1e-9:
        return None
    return cmin, cmax


def _prop(lo, hi, box, n=24):
    """Pour o dans [lo,hi], union des c faisables (approx. par échantillonnage)."""
    K, Hlo, Hhi, Llo, Lhi = box
    best = None
    for k in range(n + 1):
        o = lo + (hi - lo) * k / n
        r = _crange(o, K, Hlo, Hhi, Llo, Lhi)
        if r is None:
            continue
        best = r if best is None else (min(best[0], r[0]), max(best[1], r[1]))
    return best


def _free(box):
    K, Hlo, Hhi, Llo, Lhi = box
    return _prop(Llo, Hhi, box, n=48)


def pos_dir(bars, i, a=0.3):
    """Position du close dans l'intervalle faisable : 0,5 + 0,3 x corps HA relatif (calé sur l'API,
    identique sur les 4 jeux 15m/2m) — supprime le biais « retour au milieu » qui rend optimistes
    les entrées après une bougie directionnelle."""
    b = bars[i]; rg = (b['h'] - b['l']) or 1.0
    return min(max(0.5 + a * (b['c'] - b['o']) / rg, 0.0), 1.0)


def reconstruct(bars, tick=0.25, g=None, breaks=None, eps=None, pos=pos_dir):
    """bars : liste de dict o,h,l,c (HA). breaks[i]=True si la bougie i suit une coupure.
    Renvoie liste de dict ro, rh, rl, rc (estimations des vrais prix) + hk/lk (high/low exacts ?)."""
    n = len(bars)
    g = tick if g is None else g
    eps = tick / 10 if eps is None else eps
    boxes = [_box(b, eps) for b in bars]
    breaks = breaks or [False] * n
    F = [None] * n
    for i in range(n):
        fr = _free(boxes[i]) or (bars[i]['l'], bars[i]['h'])
        if i == 0 or breaks[i] or F[i - 1] is None:
            F[i] = fr
            continue
        r = _prop(F[i - 1][0] - g, F[i - 1][1] + g, boxes[i])
        F[i] = r if r is not None else fr
    # passe arrière : intervalle de c_t compatible avec le futur
    Bk = [None] * n
    for i in range(n - 1, -1, -1):
        fr = _free(boxes[i]) or (bars[i]['l'], bars[i]['h'])
        if i == n - 1 or breaks[i + 1] or Bk[i + 1] is None:
            Bk[i] = fr
            continue
        # o_{i+1} faisable étant donné c_{i+1} dans Bk[i+1] (symétrie o<->c)
        oi = _prop(Bk[i + 1][0], Bk[i + 1][1], boxes[i + 1])
        if oi is None:
            Bk[i] = fr
            continue
        lo, hi = max(oi[0] - g, fr[0]), min(oi[1] + g, fr[1])
        Bk[i] = (lo, hi) if lo <= hi else fr
    out = []; ivs = []
    for i in range(n):
        lo, hi = max(F[i][0], Bk[i][0]), min(F[i][1], Bk[i][1])
        if lo > hi:
            lo, hi = F[i]
        ivs.append((lo, hi))
        p = 0.5 if pos is None else pos(bars, i)
        out.append(lo + p * (hi - lo))
    res = []
    for i in range(n):
        K, Hlo, Hhi, Llo, Lhi = boxes[i]
        c = out[i]
        o = out[i - 1] if (i > 0 and not breaks[i]) else None
        if o is None:
            o = K / 4  # à défaut
        hk, lk = Hlo == Hhi, Llo == Lhi
        h, l = Hlo, Llo
        if hk and lk:
            pass
        elif hk:  # l inconnu : l = K - o - c - h, borné
            l = min(max(K - o - c - h, Llo), min(Lhi, o, c))
        elif lk:
            h = max(min(K - o - c - l, Hhi), max(Hlo, o, c))
        else:
            rest = K - o - c
            h = max(min(rest / 2 + (Hhi - Lhi) / 4, Hhi), Hlo, o, c)
            l = min(max(rest - h, Llo), Lhi, o, c)
        o = min(max(o, l), h)
        c = min(max(c, l), h)
        res.append(dict(ro=o, rh=h, rl=l, rc=c, hk=hk, lk=lk, Hhi=Hhi, Llo=Llo, iv=ivs[i]))
    return res


if __name__ == '__main__':
    import json
    P = '/Users/jeremk/ERGON/on-va-se-le-tenter/tools/ephore_api/'
    q = lambda x, p: sorted(x)[int(p * (len(x) - 1))]
    for f in ['api_vitrine_instantane.json', 'api_vitrine_20261012.json']:
        A = json.load(open(P + f))
        for u in ['15m', '2m']:
            B = A['unites'][u]['bougies']
            bars = [dict(o=b['o'], h=b['h'], l=b['l'], c=b['c']) for b in B]
            for g in (1, 2, 3):
                R = reconstruct(bars, tick=1, g=g, eps=0.05)
                ec = [abs(R[i]['rc'] - B[i]['cr']) for i in range(50, len(B))]
                bias = sum(R[i]['rc'] - B[i]['cr'] for i in range(50, len(B))) / len(ec)
                eh = [abs(R[i]['rh'] - B[i]['hr']) for i in range(50, len(B))]
                el = [abs(R[i]['rl'] - B[i]['lr']) for i in range(50, len(B))]
                rng = sorted(b['hr'] - b['lr'] for b in B)[len(B) // 2]
                print(f[:22], u, 'g', g, 'range med', rng, '| close err med %.1f p90 %.1f p99 %.1f biais %.2f' % (
                    q(ec, .5), q(ec, .9), q(ec, .99), bias),
                      '| high err p90 %.1f p99 %.1f | low err p90 %.1f p99 %.1f' % (q(eh, .9), q(eh, .99), q(el, .9), q(el, .99)))
