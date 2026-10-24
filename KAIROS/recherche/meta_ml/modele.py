"""Walk-forward purgé, modèles (boosting + logistique régularisée), calibration, politique, importance.

Tout est fixé À L'AVANCE (aucun réglage des hyperparamètres sur le hors-échantillon) :
- HGB : HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=30,
  l2_regularization=1.0) ;
- logistique : imputation médiane + indicateurs de manque, standardisation, L2 C=0.05.
- Plis : jours CME triés ; 40 % premiers jours = apprentissage initial ; le reste en K=5 blocs de test
  consécutifs ; apprentissage croissant (tout ce qui précède), PURGE des candidats dont la sortie (pire cas des
  3 gestions) dépasse le début du test, EMBARGO d'une journée CME avant le test.
- Calibration (Platt) et seuil de la politique : choisis sur des prédictions hors-échantillon INTERNES à
  l'apprentissage (3 sous-plis chronologiques), jamais sur le test.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

GESTIONS = ['A15R2', 'A1R1', 'NIV']
FRACTIONS = [0.2, 0.33, 0.5, 0.67, 1.0]
META = {'i', 'sens', 't_signal', 'serie', 'instrument', 'jour'}


def colonnes_variables(T):
    cols = [c for c in T.columns if c not in META and not c.startswith(('r_', 'pnl_', 'sortie_', 'risque_'))]
    return [c for c in cols if T[c].notna().any() and T[c].nunique(dropna=True) > 1]


def fabrique(nom, graine=0):
    if nom == 'hgb':
        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150, min_samples_leaf=30,
                                              l2_regularization=1.0, random_state=graine)
    if nom == 'logit':
        return make_pipeline(SimpleImputer(strategy='median', add_indicator=True), StandardScaler(),
                             LogisticRegression(C=0.05, max_iter=2000))
    raise ValueError(nom)


def _fin_pire(T):
    s = [pd.to_datetime(T['sortie_' + g]) for g in GESTIONS if 'sortie_' + g in T]
    return pd.concat(s, axis=1).max(axis=1).fillna(pd.to_datetime(T['t_signal']))


def plis(T, k=5, part_init=0.4):
    """[(idx_app, idx_test)] (indices de T), purge + embargo 1 jour."""
    jours = np.sort(T['jour'].unique())
    n0 = int(round(part_init * len(jours)))
    bornes = np.linspace(n0, len(jours), k + 1).round().astype(int)
    fin = _fin_pire(T)
    out = []
    for p in range(k):
        jt = jours[bornes[p]:bornes[p + 1]]
        if not len(jt):
            continue
        test = np.flatnonzero(T['jour'].isin(jt).to_numpy())
        t0 = T['t_signal'].iloc[test].min()
        j_embargo = jours[max(bornes[p] - 1, 0)]
        app = np.flatnonzero((T['jour'] < jt[0]).to_numpy() & (T['jour'] != j_embargo).to_numpy()
                             & (fin < t0).to_numpy())
        out.append((app, test))
    return out


def _sous_plis(T, app, k=3):
    """Sous-plis chronologiques internes à l'apprentissage (croissants, purgés)."""
    sub = T.iloc[app]
    jours = np.sort(sub['jour'].unique())
    bornes = np.linspace(0, len(jours), k + 2).round().astype(int)
    fin = _fin_pire(sub)
    out = []
    for q in range(1, k + 1):
        jt = jours[bornes[q]:bornes[q + 1]]
        if not len(jt):
            continue
        te = np.flatnonzero(sub['jour'].isin(jt).to_numpy())
        t0 = sub['t_signal'].iloc[te].min()
        tr = np.flatnonzero((sub['jour'] < jt[0]).to_numpy() & (fin < t0).to_numpy())
        if len(tr) >= 40 and len(te):
            out.append((app[tr], app[te]))
    return out


def _platt(p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    z = np.log(p / (1 - p)).reshape(-1, 1)
    if len(np.unique(y)) < 2:
        return lambda q: np.full(len(q), y.mean() if len(y) else 0.5)
    lr = LogisticRegression(C=1.0).fit(z, y)
    return lambda q: lr.predict_proba(np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4))).reshape(-1, 1))[:, 1]


class _Modele:
    """Ne garde que les colonnes renseignées et variables dans l'apprentissage (petits plis, séries sans volume)."""
    def __init__(self, nom):
        self.nom = nom

    def fit(self, X, y):
        fin = np.isfinite(X)
        self.cols = np.flatnonzero((fin.sum(0) >= 5) & (np.nanstd(np.where(fin, X, np.nan), 0) > 0))
        self.m = fabrique(self.nom).fit(X[:, self.cols], y)
        return self

    def predict_proba(self, X):
        return self.m.predict_proba(X[:, self.cols])


def _ajuste(nom, X, y):
    if len(np.unique(y)) < 2 or len(y) < 20:
        return None
    return _Modele(nom).fit(X, y)


def _predit(m, X, defaut):
    return np.full(len(X), defaut) if m is None else m.predict_proba(X)[:, 1]


def _choisit_fraction(score, r, groupes):
    """Fraction q (prise des q meilleurs scores, seuil par sous-pli) qui maximise le R moyen interne."""
    best = (1.0, -np.inf)
    for q in FRACTIONS:
        pris = []
        for g in np.unique(groupes):
            m = groupes == g
            s = score[m]
            thr = np.quantile(s, 1 - q) if q < 1 else -np.inf
            pris.append(r[m][s >= thr])
        pris = np.concatenate(pris) if pris else np.array([])
        if len(pris) >= 20 and pris.mean() > best[1] + 1e-9:
            best = (q, pris.mean())
    return best[0]


def walk_forward(T, cols, nom_modele, gestion, folds):
    """Prédictions hors-échantillon calibrées + décision de la politique « seuil » pour une gestion.
    Renvoie DataFrame (index T) : p_brut, p, seuil, pris, pli ; et la liste des modèles par pli."""
    X = T[cols].to_numpy(float)
    rcol = 'r_' + gestion
    ok = T[rcol].notna().to_numpy()
    y = (T[rcol] > 0).to_numpy().astype(int)
    r = T[rcol].to_numpy(float)
    res = pd.DataFrame(index=T.index, columns=['p_brut', 'p', 'seuil', 'pris', 'pli', 'q'], dtype=float)
    modeles = []
    for f, (app, test) in enumerate(folds):
        app = app[ok[app]]; test_ok = test[ok[test]]
        # prédictions internes
        sp = _sous_plis(T, app)
        ps, ys, rs, gs = [], [], [], []
        for s, (tr, te) in enumerate(sp):
            tr = tr[ok[tr]]; te = te[ok[te]]
            m = _ajuste(nom_modele, X[tr], y[tr])
            ps.append(_predit(m, X[te], y[tr].mean())); ys.append(y[te]); rs.append(r[te]); gs.append(np.full(len(te), s))
        m = _ajuste(nom_modele, X[app], y[app])
        modeles.append(m)
        pb = _predit(m, X[test_ok], y[app].mean())
        if ps:
            ps, ys, rs, gs = map(np.concatenate, (ps, ys, rs, gs))
            cal = _platt(ps, ys)
            pc_int = cal(ps)
            q = _choisit_fraction(pc_int, rs, gs)
            seuil = np.quantile(pc_int, 1 - q) if q < 1 else -np.inf
            pc = cal(pb)
        else:
            q, seuil, pc = 1.0, -np.inf, pb
        res.loc[T.index[test_ok], 'p_brut'] = pb
        res.loc[T.index[test_ok], 'p'] = pc
        res.loc[T.index[test_ok], 'seuil'] = seuil
        res.loc[T.index[test_ok], 'q'] = q
        res.loc[T.index[test_ok], 'pris'] = (pc >= seuil).astype(float)
        res.loc[T.index[test_ok], 'pli'] = f
    return res, modeles


def _auc_intra(y, p, g):
    """Moyenne des AUC par pli, pondérée par la taille (l'AUC poolée mélange des niveaux de probabilité
    différents d'un pli à l'autre et peut être trompeuse)."""
    tot = w = 0.0
    for f in np.unique(g):
        k = g == f
        if len(np.unique(y[k])) > 1:
            tot += roc_auc_score(y[k], p[k]) * k.sum(); w += k.sum()
    return tot / w if w else np.nan


def auc_test(y, p, plis_, n_perm=2000, graine=0):
    """AUC intra-pli (moyenne pondérée) + p-valeur par permutation des prédictions DANS chaque pli,
    + AUC poolée (pour information) + AUC par pli."""
    m = np.isfinite(p)
    y, p, g = y[m], p[m], plis_[m]
    if len(np.unique(y)) < 2:
        return np.nan, np.nan, [], np.nan
    obs = _auc_intra(y, p, g)
    rng = np.random.default_rng(graine)
    idx = [np.flatnonzero(g == f) for f in np.unique(g)]
    nul = np.empty(n_perm)
    for b in range(n_perm):
        pp = p.copy()
        for k in idx:
            pp[k] = pp[rng.permutation(k)]
        nul[b] = _auc_intra(y, pp, g)
    par_pli = [roc_auc_score(y[k], p[k]) if len(np.unique(y[k])) > 1 else np.nan for k in idx]
    return obs, float((1 + (nul >= obs).sum()) / (1 + n_perm)), par_pli, roc_auc_score(y, p)


def selection_au_hasard(r, pris, plis_, n=5000, graine=0):
    """Référence « même nombre de candidats tirés au hasard dans chaque pli » : p-valeur du R moyen."""
    m = np.isfinite(r)
    r, pris, g = r[m], pris[m].astype(bool), plis_[m]
    obs = r[pris].mean() if pris.any() else np.nan
    rng = np.random.default_rng(graine)
    nul = np.empty(n)
    groupes = [(np.flatnonzero(g == f), int(pris[g == f].sum())) for f in np.unique(g)]
    for b in range(n):
        tot = []
        for k, c in groupes:
            if c:
                tot.append(r[rng.choice(k, c, replace=False)])
        nul[b] = np.concatenate(tot).mean() if tot else np.nan
    return obs, float((1 + (nul >= obs).sum()) / (1 + n)), float(np.nanmean(nul))


def importance_permutation(T, cols, groupes, nom_modele, gestion, folds, modeles, n_rep=10, graine=0):
    """Baisse d'AUC hors-échantillon quand on permute un groupe de variables (ou une variable) dans le test."""
    X = T[cols].to_numpy(float)
    rcol = 'r_' + gestion
    ok = T[rcol].notna().to_numpy()
    y = (T[rcol] > 0).to_numpy().astype(int)
    rng = np.random.default_rng(graine)
    blocs = {}
    for j, c in enumerate(cols):
        blocs.setdefault('G:' + groupes.get(c, c), []).append(j)
        blocs['V:' + c] = [j]
    lignes = []
    for f, ((app, test), m) in enumerate(zip(folds, modeles)):
        te = test[ok[test]]
        if m is None or len(np.unique(y[te])) < 2:
            continue
        base = roc_auc_score(y[te], m.predict_proba(X[te])[:, 1])
        for nom, js in blocs.items():
            baisses = []
            for _ in range(n_rep):
                Xp = X[te].copy()
                perm = rng.permutation(len(te))
                Xp[:, js] = Xp[perm][:, js]
                baisses.append(base - roc_auc_score(y[te], m.predict_proba(Xp)[:, 1]))
            lignes.append(dict(pli=f, bloc=nom, baisse_auc=float(np.mean(baisses))))
    D = pd.DataFrame(lignes)
    if not len(D):
        return D
    A = D.groupby('bloc')['baisse_auc'].agg(['mean', 'min', 'max', 'count']).reset_index()
    A['type'] = np.where(A['bloc'].str.startswith('G:'), 'groupe', 'variable')
    A['bloc'] = A['bloc'].str[2:]
    return A.sort_values('mean', ascending=False)
