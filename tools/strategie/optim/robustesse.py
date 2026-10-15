"""Statistiques anti-sur-ajustement.

- bootstrap PAR JOUR des trades (les trades d'une même journée restent ensemble : ils ne sont pas
  indépendants) : IC 95 % du R moyen, du profit factor, du drawdown max, du total ;
- Monte Carlo de ruine : tirage de journées jusqu'à l'horizon (en trades), capital composé à risque
  fixe par trade ; ruine = capital sous (1 - ruine %) ;
- Probabilistic / Deflated Sharpe Ratio (Bailey & López de Prado 2012, 2014) sur rendements JOURNALIERS ;
- Reality Check de White (2000) et SPA de Hansen (2005) par bootstrap stationnaire (Politis-Romano) sur
  la matrice réglages x jours.
"""
import math
import numpy as np
from scipy import stats as ss

EULER = 0.5772156649015329


def resume(R):
    R = np.asarray(R, float)
    n = len(R)
    if n == 0:
        return dict(n=0, moy=np.nan, t=np.nan, pf=np.nan, gain=np.nan, dd=np.nan, tot=0.0)
    w = R[R > 0].sum(); l = -R[R <= 0].sum()
    sd = R.std(ddof=1) if n > 1 else np.nan
    eq = np.cumsum(R); dd = np.max(np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq])
    return dict(n=n, moy=R.mean(), t=R.mean() / sd * math.sqrt(n) if sd and sd > 0 else np.nan,
                pf=w / l if l > 0 else np.inf, gain=(R > 0).mean(), dd=dd, tot=R.sum())


def _groupes(jours):
    u, inv = np.unique(jours, return_inverse=True)
    idx = [np.nonzero(inv == k)[0] for k in range(len(u))]
    return idx


def bootstrap_jour(R, jours, B=2000, rng=None):
    rng = rng or np.random.default_rng(0)
    R = np.asarray(R, float)
    G = _groupes(jours)
    if len(G) < 2:
        return {}
    res = {k: [] for k in ('moy', 'pf', 'dd', 'tot', 'gain')}
    for _ in range(B):
        pick = rng.integers(len(G), size=len(G))
        x = np.concatenate([R[G[k]] for k in pick])
        s = resume(x)
        for k in res:
            res[k].append(s[k])
    out = {}
    for k, v in res.items():
        v = np.asarray(v, float); v = v[np.isfinite(v)] if k == 'pf' else v
        out[k] = (np.nanpercentile(v, 2.5), np.nanpercentile(v, 97.5)) if len(v) else (np.nan, np.nan)
    out['p_moy_pos'] = float(np.mean(np.asarray(res['moy']) > 0))
    return out


def ruine(R, jours, risque_pct=1.0, ruine_pct=30.0, horizon=250, M=2000, rng=None):
    rng = rng or np.random.default_rng(1)
    R = np.asarray(R, float)
    G = _groupes(jours)
    if not len(G):
        return dict(p_ruine=np.nan, mediane_finale=np.nan, dd_med=np.nan)
    r = risque_pct / 100.0; seuil = 1 - ruine_pct / 100.0
    nr = 0; fin = []; dds = []
    for _ in range(M):
        x = []
        while len(x) < horizon:
            x.extend(R[G[rng.integers(len(G))]].tolist())
        x = np.asarray(x[:horizon])
        eq = np.cumprod(1 + r * np.maximum(x, -1 / r + 1e-9))
        nr += eq.min() <= seuil
        fin.append(eq[-1]); dds.append(1 - (eq / np.maximum.accumulate(np.r_[1, eq])[1:]).min())
    return dict(p_ruine=nr / M, mediane_finale=float(np.median(fin)), dd_med=float(np.median(dds)),
                dd_p95=float(np.percentile(dds, 95)))


def journalier(R, jours, tous_jours):
    """Somme des R par journée de bourse (0 les jours sans trade)."""
    pos = np.searchsorted(tous_jours, jours)
    out = np.zeros(len(tous_jours))
    np.add.at(out, pos, R)
    return out


def psr(x, sr0=0.0):
    """Probabilistic Sharpe Ratio : P(SR vrai > sr0) (SR non annualisé, rendements x)."""
    x = np.asarray(x, float); T = len(x)
    if T < 3 or x.std(ddof=1) == 0:
        return np.nan, np.nan
    sr = x.mean() / x.std(ddof=1)
    g3 = ss.skew(x); g4 = ss.kurtosis(x, fisher=False)
    den = math.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))
    return float(ss.norm.cdf((sr - sr0) * math.sqrt(T - 1) / den)), sr


def sr0_deflate(N, V):
    """Sharpe maximal attendu sous H0 parmi N essais de variance V des Sharpe (Bailey & López de Prado)."""
    if N < 2 or V <= 0:
        return 0.0
    return math.sqrt(V) * ((1 - EULER) * ss.norm.ppf(1 - 1 / N) + EULER * ss.norm.ppf(1 - 1 / (N * math.e)))


def dsr(x, N, V):
    """Deflated Sharpe Ratio = PSR(SR0 = Sharpe attendu du meilleur de N essais sans talent)."""
    s0 = sr0_deflate(N, V)
    p, sr = psr(x, s0)
    return p, sr, s0


def _stationnaire(T, b, rng):
    p = 1.0 / b
    idx = np.empty(T, np.int64)
    idx[0] = rng.integers(T)
    nouv = rng.random(T) < p
    deb = rng.integers(T, size=T)
    for t in range(1, T):
        idx[t] = deb[t] if nouv[t] else (idx[t - 1] + 1) % T
    return idx


def white_spa(X, B=1000, bloc=5, rng=None):
    """X : matrice (réglages x jours) des rendements journaliers (référence = ne rien faire = 0).
    Renvoie (p du Reality Check de White, p du SPA « consistant » de Hansen)."""
    rng = rng or np.random.default_rng(2)
    X = np.asarray(X, float)
    K, T = X.shape
    if K == 0 or T < 10:
        return np.nan, np.nan
    m = X.mean(1)
    sd = X.std(1, ddof=1)
    om = np.where(sd > 0, sd, np.inf)
    V_rc = math.sqrt(T) * m.max()
    tstat = math.sqrt(T) * m / om
    V_spa = max(0.0, tstat.max())
    seuil = -om * math.sqrt(2 * math.log(math.log(T)) / T)
    mu_c = np.where(m >= seuil, m, 0.0)
    c_rc = c_spa = 0
    for _ in range(B):
        idx = _stationnaire(T, bloc, rng)
        mb = X[:, idx].mean(1)
        if math.sqrt(T) * (mb - m).max() >= V_rc:
            c_rc += 1
        if max(0.0, (math.sqrt(T) * (mb - mu_c) / om).max()) >= V_spa:
            c_spa += 1
    return c_rc / B, c_spa / B
