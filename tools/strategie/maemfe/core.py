"""Cœur MAE/MFE : chemins de prix après entrée, simulation vectorisée des sorties, bootstrap par jour.

Conventions (identiques à tools/strategie/engine.py, prudentes) :
- signal connu à la CLÔTURE de la barre i -> entrée à l'OUVERTURE (vraie) de i+1 ; pas d'entrée si la barre
  i+1 suit une coupure ;
- tout est exprimé en multiples de l'ATR14 des vrais prix connu à la clôture de i, dans le sens du trade
  (x > 0 = favorable) ;
- coûts : 1 tick de glissement par côté + 1,25 $/contrat/côté, retirés une fois par trade (en ATR) ;
- stop : rempli au niveau du stop, ou à l'ouverture si elle a sauté le stop ; objectif : ordre limite
  rempli seulement si le prix le DÉPASSE d'un tick ; stop ET objectif dans la même barre -> STOP ;
- break-even / stop suiveur : mis à jour à la clôture d'une barre, actifs à partir de la barre suivante ;
- sortie au temps : clôture de la barre « hcap » ; le chemin s'arrête à un trou de données > 12 h
  (week-end) : sortie forcée à la dernière clôture disponible.
Chaque signal est étudié isolément (des trades peuvent se chevaucher) : c'est une étude d'excursions,
pas un backtest à position unique.
"""
import numpy as np
from donnees import instrument, cout_points, SPEC  # noqa: F401

H = 48
WARM = 101
TROU_S = 12 * 3600


class Univers:
    """Toutes les barres candidates (une ligne = une entrée possible à l'ouverture de i+1), sens LONG.
    Le sens SHORT s'obtient par miroir (fav <-> adv, opn/cls -> opposés)."""

    def __init__(self, series, H=H, prudent=False):
        self.H = H
        cols = {k: [] for k in ('sid', 'i', 'tfm', 't', 'jour', 'atr', 'cout', 'tick', 'inst')}
        FAV, ADV, OPN, CLS = [], [], [], []
        self.series = series
        self.index = {}
        K = np.arange(1, H + 1)
        for sid, S in enumerate(series):
            n = S['n']
            ro = np.asarray(S['ro'], float); rh = np.asarray(S['rh'], float)
            rl = np.asarray(S['rl'], float); rc = np.asarray(S['rc'], float)
            if prudent and 'rhx' in S:          # côté défavorable au pire, favorable au moins bon
                rh_f, rl_f = np.asarray(S['rhn'], float), np.asarray(S['rln'], float)
                rh_a, rl_a = np.asarray(S['rhx'], float), np.asarray(S['rlx'], float)
            else:
                rh_f = rh_a = rh; rl_f = rl_a = rl
            atr = np.array([np.nan if x is None else x for x in S['ratr']], float)
            ts = np.array([t.timestamp() for t in S['T']])
            brk = np.asarray(S['brk'], bool)
            trou = np.r_[False, np.diff(ts) > TROU_S]
            ct = np.cumsum(trou)
            I = np.arange(WARM, n - 1)
            I = I[~brk[I + 1] & np.isfinite(atr[I]) & (atr[I] > 0)]
            if len(I) == 0: continue
            J = I[:, None] + K[None, :]
            ok = J < n
            Jc = np.minimum(J, n - 1)
            ok &= ct[Jc] == ct[I + 1][:, None]
            e = ro[I + 1][:, None]; a = atr[I][:, None]
            with np.errstate(invalid='ignore'):
                fav = np.where(ok, (rh_f[Jc] - e) / a, np.nan)
                adv = np.where(ok, (e - rl_a[Jc]) / a, np.nan)
                # côté short : favorable = baisse (low le moins bas plausible), défavorable = high le plus haut
                fav_s = np.where(ok, (e - rl_f[Jc]) / a, np.nan)
                adv_s = np.where(ok, (rh_a[Jc] - e) / a, np.nan)
                opn = np.where(ok, (ro[Jc] - e) / a, np.nan)
                cls = np.where(ok, (rc[Jc] - e) / a, np.nan)
            FAV.append(np.stack([fav, fav_s])); ADV.append(np.stack([adv, adv_s]))
            OPN.append(opn); CLS.append(cls)
            ins = instrument(S['sym']); pv, tick = SPEC.get(ins, (5.0, 0.25))
            for i in I:
                self.index[(sid, int(i))] = len(cols['sid'])
                cols['sid'].append(sid); cols['i'].append(int(i))
            cols['tfm'] += [S['tfm']] * len(I)
            cols['t'] += list(ts[I])
            # jour de marché (session CME qui commence à 18:00 New York ~ 00:00 Paris + 6 h de décalage)
            cols['jour'] += list(((ts[I] + 6 * 3600) // 86400).astype(int))
            cols['atr'] += list(atr[I])
            cols['cout'] += list(cout_points(ins) / atr[I])
            cols['tick'] += list(tick / atr[I])
            cols['inst'] += [ins] * len(I)
        for k, v in cols.items():
            setattr(self, k, np.asarray(v, dtype=object if k == 'inst' else float))
        self.sid = self.sid.astype(int); self.i = self.i.astype(int); self.jour = self.jour.astype(int)
        self.tfm = self.tfm.astype(int)
        self.fav2 = np.concatenate(FAV, axis=1)     # (2, N, H) : [long, short]
        self.adv2 = np.concatenate(ADV, axis=1)
        self.opn = np.concatenate(OPN); self.cls = np.concatenate(CLS)
        self.N = len(self.sid)
        self.L = np.isfinite(self.cls).sum(1)        # barres disponibles

    # -------------------------------------------------------------- chemins orientés
    def chemins(self, rows, d):
        """rows : indices de lignes ; d : sens (+1/-1). Renvoie fav, adv, opn, cls (M, H) orientés."""
        rows = np.asarray(rows, int); d = np.asarray(d, int)
        s = (d < 0).astype(int)
        fav = self.fav2[s, rows]; adv = self.adv2[s, rows]
        sg = d[:, None].astype(float)
        return fav, adv, sg * self.opn[rows], sg * self.cls[rows]

    def lignes(self, S_idx_entries):
        """[(sid, i, d)] -> (rows, d) pour les entrées présentes dans l'univers."""
        rows, ds = [], []
        for sid, i, d in S_idx_entries:
            r = self.index.get((sid, int(i)))
            if r is not None:
                rows.append(r); ds.append(d)
        return np.asarray(rows, int), np.asarray(ds, int)


# ------------------------------------------------------------------ mesures descriptives
def excursions(U, rows, d, k):
    """MAE et MFE (ATR, >= 0) sur les k premières barres, retour à la clôture de k, barre du MFE.
    Lignes sans k barres complètes -> NaN."""
    fav, adv, opn, cls = U.chemins(rows, d)
    ok = np.isfinite(cls[:, k - 1])
    mfe = np.where(ok, np.nanmax(np.maximum(fav[:, :k], 0), axis=1), np.nan)
    mae = np.where(ok, np.nanmax(np.maximum(adv[:, :k], 0), axis=1), np.nan)
    ret = cls[:, k - 1]
    tmfe = np.where(ok, np.nanargmax(np.where(np.isfinite(fav[:, :k]), fav[:, :k], -1e9), axis=1) + 1, np.nan)
    return mae, mfe, ret, tmfe


# ------------------------------------------------------------------ simulation d'un plan de sortie
def simuler(U, rows, d, stop, cible=None, be=None, suiveur=None, hcap=H, couts=True, detail=False):
    """Résultat net en R de chaque trade.
    stop : distance du stop initial en ATR (R = stop) ; cible : objectif en R (None = pas d'objectif) ;
    be : break-even (stop ramené à l'entrée + coûts) dès que le MFE atteint be R ;
    suiveur : stop suiveur à `suiveur` ATR du meilleur prix atteint ; hcap : sortie au temps (barres)."""
    fav, adv, opn, cls = U.chemins(rows, d)
    M = len(rows)
    cout = U.cout[rows] if couts else np.zeros(M)
    tick = U.tick[rows]
    niv = np.full(M, -float(stop))                # niveau du stop (en ATR, coordonnée favorable)
    tgt = np.full(M, np.inf) if cible is None else np.full(M, cible * stop)
    xout = np.full(M, np.nan); nb = np.zeros(M, int); why = np.zeros(M, int)   # 1 stop 2 objectif 3 temps
    best = np.full(M, -np.inf)
    actif = np.ones(M, bool)
    for k in range(min(hcap, U.H)):
        f, a, o, c = fav[:, k], adv[:, k], opn[:, k], cls[:, k]
        fin = actif & ~np.isfinite(c)             # chemin interrompu : sortie à la dernière clôture
        if k > 0 and fin.any():
            xout[fin] = cls[fin, k - 1]; why[fin] = 3; nb[fin] = k; actif &= ~fin
        elif k == 0 and fin.any():
            xout[fin] = 0.0; why[fin] = 3; actif &= ~fin
        st = actif & (-a <= niv)
        px = np.where(k == 0, niv, np.minimum(niv, o))
        xout[st] = px[st]; why[st] = 1; nb[st] = k + 1; actif &= ~st
        tg = actif & (f >= tgt + tick)
        xout[tg] = tgt[tg]; why[tg] = 2; nb[tg] = k + 1; actif &= ~tg
        best = np.where(actif, np.maximum(best, f), best)
        if be is not None:
            niv = np.where(actif & (best >= be * stop), np.maximum(niv, cout), niv)
        if suiveur is not None:
            niv = np.where(actif, np.maximum(niv, best - suiveur), niv)
    k = min(hcap, U.H) - 1
    xout[actif] = cls[actif, k]; why[actif] = 3; nb[actif] = k + 1
    R = (xout - cout) / stop
    if detail:
        return R, why, nb
    return R


# ------------------------------------------------------------------ statistiques
def boot_moyenne(y, jours, B=2000, graine=1, alpha=0.05):
    """Moyenne et IC à 95 % par bootstrap des JOURS (dépendance intra-journée et entre unités)."""
    y = np.asarray(y, float); ok = np.isfinite(y); y = y[ok]; g = np.asarray(jours)[ok]
    if len(y) == 0: return np.nan, np.nan, np.nan
    _, inv = np.unique(g, return_inverse=True); G = inv.max() + 1
    Sg = np.bincount(inv, weights=y, minlength=G); Ng = np.bincount(inv, minlength=G).astype(float)
    if G < 3: return y.mean(), np.nan, np.nan
    rng = np.random.default_rng(graine)
    W = rng.multinomial(G, np.full(G, 1.0 / G), size=B).astype(float)
    m = (W @ Sg) / np.maximum(W @ Ng, 1)
    return y.mean(), np.quantile(m, alpha / 2), np.quantile(m, 1 - alpha / 2)


def boot_p(y, jours, B=4000, graine=5):
    """p unilatéral (moyenne <= 0) par bootstrap des jours : part des moyennes rééchantillonnées <= 0."""
    y = np.asarray(y, float); ok = np.isfinite(y); y = y[ok]; g = np.asarray(jours)[ok]
    if len(y) < 3: return np.nan
    _, inv = np.unique(g, return_inverse=True); G = inv.max() + 1
    if G < 3: return np.nan
    Sg = np.bincount(inv, weights=y, minlength=G); Ng = np.bincount(inv, minlength=G).astype(float)
    rng = np.random.default_rng(graine)
    W = rng.multinomial(G, np.full(G, 1.0 / G), size=B).astype(float)
    m = (W @ Sg) / np.maximum(W @ Ng, 1)
    return float((1 + (m <= 0).sum()) / (B + 1))


def base_hasard(U, rows, d, VL, VS, masque):
    """Valeur moyenne d'une barre quelconque de la même série, même sens, même période (par trade)."""
    rows = np.asarray(rows, int); d = np.asarray(d, int)
    out = np.full(len(rows), np.nan)
    for sid in np.unique(U.sid[rows]):
        pool = (U.sid == sid) & masque
        for sens, V in ((1, VL), (-1, VS)):
            k = (U.sid[rows] == sid) & (d == sens)
            if k.any(): out[k] = np.nanmean(V[pool]) if pool.any() else np.nan
    return out


def tirages_hasard(U, rows, d, valeurs, M=1000, graine=3, masque=None):
    """Référence aléatoire APPARIÉE : pour chaque trade du déclencheur, une barre tirée au hasard dans la
    même série et la même période (masque), même sens. valeurs : liste de couples (V_long, V_short), valeurs
    par ligne de l'univers (ex. R d'un plan, MFE, MAE). Les MÊMES tirages servent pour toutes les valeurs.
    Renvoie, pour chaque couple, les M moyennes aléatoires."""
    rng = np.random.default_rng(graine)
    rows = np.asarray(rows, int); d = np.asarray(d, int)
    masque = np.ones(U.N, bool) if masque is None else masque
    tot = [np.zeros(M) for _ in valeurs]; cnt = 0
    for sid in np.unique(U.sid[rows]):
        for sens in (1, -1):
            k = int(((U.sid[rows] == sid) & (d == sens)).sum())
            if k == 0: continue
            ok = (U.sid == sid) & masque
            for VL, VS in valeurs:
                ok &= np.isfinite(VL if sens == 1 else VS)
            pool = np.where(ok)[0]
            if len(pool) == 0: continue
            idx = pool[rng.integers(0, len(pool), size=(M, k))]
            for j, (VL, VS) in enumerate(valeurs):
                tot[j] += (VL if sens == 1 else VS)[idx].sum(1)
            cnt += k
    return [t / max(cnt, 1) for t in tot]
