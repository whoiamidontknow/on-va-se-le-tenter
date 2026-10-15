"""Statistiques robustes à la dépendance intra-journée : erreurs-types groupées par JOUR (toutes unités
confondues : une même journée vue en 5, 15, 30 et 60 min ne compte qu'une fois en information)."""
import numpy as np
from scipy import stats


def cl_mean(y, g):
    """moyenne, t groupé par jour, p bilatéral (loi de Student à G-1 ddl), G."""
    y = np.asarray(y, float); g = np.asarray(g)
    ok = ~np.isnan(y); y, g = y[ok], g[ok]
    n = len(y)
    if n < 2: return np.nan, np.nan, np.nan, 0
    m = y.mean()
    _, inv = np.unique(g, return_inverse=True)
    G = inv.max() + 1
    if G < 5: return m, np.nan, np.nan, G
    s = np.bincount(inv, weights=y - m)
    var = (s ** 2).sum() / n ** 2 * G / (G - 1)
    if var <= 0: return m, np.nan, np.nan, G
    t = m / np.sqrt(var)
    return m, t, 2 * stats.t.sf(abs(t), G - 1), G


def cl_diff(y1, g1, y2, g2):
    """différence de moyennes (cellule - complément), t groupé approximatif."""
    m1, t1, _, G1 = cl_mean(y1, g1); m2, t2, _, G2 = cl_mean(y2, g2)
    if any(np.isnan([m1, m2, t1, t2])) or t1 == 0 or t2 == 0: return np.nan, np.nan, np.nan
    se = np.sqrt((m1 / t1) ** 2 + (m2 / t2) ** 2)
    t = (m1 - m2) / se
    return m1 - m2, t, 2 * stats.t.sf(abs(t), max(min(G1, G2) - 1, 1))


def cl_spearman(x, y, g):
    """rho de Spearman + t/p groupés (régression des rangs standardisés, sandwich par jour)."""
    x = np.asarray(x, float); y = np.asarray(y, float); g = np.asarray(g)
    ok = ~np.isnan(x) & ~np.isnan(y); x, y, g = x[ok], y[ok], g[ok]
    n = len(x)
    if n < 30 or np.std(x) == 0: return np.nan, np.nan, np.nan, n
    zx = stats.rankdata(x); zy = stats.rankdata(y)
    zx = (zx - zx.mean()) / zx.std(); zy = (zy - zy.mean()) / zy.std()
    b = (zx * zy).mean()
    e = zy - b * zx
    _, inv = np.unique(g, return_inverse=True); G = inv.max() + 1
    if G < 5: return b, np.nan, np.nan, n
    s = np.bincount(inv, weights=zx * e)
    var = (s ** 2).sum() / (zx ** 2).sum() ** 2 * G / (G - 1)
    t = b / np.sqrt(var)
    return b, t, 2 * stats.t.sf(abs(t), G - 1), n


def bh(p):
    """q-valeurs de Benjamini-Hochberg (NaN ignorés)."""
    p = np.asarray(p, float); q = np.full(len(p), np.nan)
    ok = ~np.isnan(p); pv = p[ok]; m = len(pv)
    if m == 0: return q
    o = np.argsort(pv); r = pv[o] * m / np.arange(1, m + 1)
    r = np.minimum.accumulate(r[::-1])[::-1]
    qq = np.empty(m); qq[o] = np.minimum(r, 1)
    q[ok] = qq
    return q
