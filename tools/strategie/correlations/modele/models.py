"""Modèles multivariés : logistique L1 et HistGradientBoosting, en walk-forward et en croisé MES <-> NQ.

- Walk-forward : 5 blocs de test consécutifs (15/09 -> 15/10) ; entraînement = toutes les barres dont la
  cible est RÉSOLUE avant le début du bloc (purge : aucune information future).
- Hasard : AUC nulle obtenue en décalant circulairement la cible dans chaque série (garde l'autocorrélation
  des issues qui se chevauchent ; un mélange barre à barre serait trop optimiste). 1000 décalages.
- Importance : permutation hors échantillon, par MODULE (variables d'un module permutées ensemble) et par variable.
- Contrôle reconstitution : l'API 15m a les VRAIS prix ; on y compare l'AUC cible recon vs cible vraie.
"""
import sys, os, json, warnings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
import dataset
warnings.filterwarnings('ignore')
RNG = np.random.default_rng(0)
HERE = os.path.dirname(os.path.abspath(__file__))
D = dataset.load()
FEATS = dataset.feat_cols(D)
CSV = D[D.sym != 'API'].copy()
APIX = D[D.sym == 'API'].copy()


def module(f):
    if f.startswith(('trend_', 'dash_', 'heishi_htf')): return 'TREND/Dashator multi-unites'
    for p, m in (('heishi_', 'Heishinator'), ('moy_', 'Moyenator'), ('sig_', 'Signator'), ('tl_', 'Trendlines'),
                 ('det_', 'Detector'), ('clx_', 'Climax'), ('sess_', 'Sessions+Monday'), ('monday_', 'Sessions+Monday'),
                 ('piv_', 'Pivots'), ('heure', 'Heure/seance/jour'), ('seance', 'Heure/seance/jour'), ('jour', 'Heure/seance/jour'),
                 ('vol_rel', 'Volume/ATR relatifs'), ('atr_', 'Volume/ATR relatifs'), ('ret', 'Prix recent HA'),
                 ('pos_range', 'Prix recent HA'), ('corps', 'Prix recent HA'), ('unite', 'Unite')):
        if f.startswith(p): return m
    if f in ('adx', 'di_diff'): return 'ADX'
    return 'SuperTrader (RSI/CCI/MACD/YoYo/Score/VIDYA)'


GROUPS = {}
for f in FEATS: GROUPS.setdefault(module(f), []).append(f)


def make(kind, p):
    if kind.startswith('logit'):
        return make_pipeline(SimpleImputer(strategy='median', add_indicator=True), StandardScaler(),
                             LogisticRegression(penalty='l1', solver='liblinear', C=p, max_iter=2000))
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.03, max_iter=p, min_samples_leaf=80,
                                          l2_regularization=1.0, early_stopping=False, random_state=0)


GRID = {'logit': [0.002, 0.005, 0.01, 0.03, 0.1], 'logit_fixe': [0.03], 'hgb': [40, 120, 300]}


class Wrap:
    """Colonnes entièrement vides à l'entraînement -> remplacées par 0 (l'arbre ne sait pas les découper)."""
    def __init__(self, kind, p, X):
        self.m = make(kind, p); self.dead = np.isnan(X).all(axis=0)
    def _x(self, X):
        X = X.copy(); X[:, self.dead] = 0.0; return X
    def fit(self, X, y):
        self.m.fit(self._x(X), y); return self
    def predict_proba(self, X):
        return self.m.predict_proba(self._x(X))


def fit(kind, Xtr, ytr, ttr):
    """Choix de l'hyperparamètre sur les 25 % les plus récents de l'entraînement, puis réentraînement complet."""
    cut = np.quantile(ttr, 0.75); a = ttr < cut; b = ~a; best = None
    if len(GRID[kind]) == 1: return Wrap(kind, GRID[kind][0], Xtr).fit(Xtr, ytr), GRID[kind][0]
    for p in GRID[kind]:
        try:
            m = Wrap(kind, p, Xtr[a]).fit(Xtr[a], ytr[a]); s = roc_auc_score(ytr[b], m.predict_proba(Xtr[b])[:, 1])
        except ValueError:
            continue
        if best is None or s > best[0]: best = (s, p)
    return Wrap(kind, best[1], Xtr).fit(Xtr, ytr), best[1]


def null_auc(y, p, groups, n=1000):
    """AUC sous l'hypothèse nulle : décalage circulaire de la cible dans chaque série."""
    out = np.empty(n); idx = [np.where(groups == g)[0] for g in np.unique(groups)]
    for k in range(n):
        ys = y.copy()
        for ii in idx:
            L = len(ii)
            if L > 2 * dataset.H_MAX: ys[ii] = np.roll(y[ii], RNG.integers(dataset.H_MAX, L - dataset.H_MAX))
        out[k] = roc_auc_score(ys, p)
    return out


def perm_importance(model, X, y, base, cols, n_rep=5):
    res = {}
    for name, fs in list(GROUPS.items()) + [(f, [f]) for f in cols]:
        j = [cols.index(f) for f in fs]; drops = []
        for _ in range(n_rep):
            Xp = X.copy(); perm = RNG.permutation(len(X)); Xp[:, j] = X[perm][:, j]
            drops.append(base - roc_auc_score(y, model.predict_proba(Xp)[:, 1]))
        res[name] = float(np.mean(drops))
    return res


def folds():
    t = CSV.t.values; t0 = pd.Timestamp('2026-09-15', tz='Europe/Paris').timestamp()
    q = np.quantile(t[t >= t0], np.linspace(0, 1, 6)); q[-1] += 1
    return list(zip(q[:-1], q[1:]))


def walk_forward(side, kind):
    yk = 'y' + side; tk = 't_res' + side; rows = []; allp = []; imps = []
    for k, (a, b) in enumerate(folds()):
        tr = CSV[(CSV[tk] < a) & CSV[yk].notna()]; te = CSV[(CSV.t >= a) & (CSV.t < b) & CSV[yk].notna()]
        m, p = fit(kind, tr[FEATS].values, tr[yk].values, tr.t.values)
        pr = m.predict_proba(te[FEATS].values)[:, 1]; y = te[yk].values
        auc = roc_auc_score(y, pr); nul = null_auc(y, pr, te.serie.values, 500)
        # contrôle API (vrais prix), même fenêtre
        ap = APIX[(APIX.t >= a) & (APIX.t < b) & APIX[yk].notna() & APIX[yk + '_vrai'].notna()]
        api_r = api_v = np.nan
        if len(ap) > 100:
            pa = m.predict_proba(ap[FEATS].values)[:, 1]
            api_r = roc_auc_score(ap[yk], pa); api_v = roc_auc_score(ap[yk + '_vrai'], pa)
        rows.append(dict(pli=k + 1, debut=pd.Timestamp(a, unit='s', tz='Europe/Paris').strftime('%m-%d'),
                         fin=pd.Timestamp(b, unit='s', tz='Europe/Paris').strftime('%m-%d'), n_tr=len(tr), n_te=len(te),
                         param=p, auc=auc, p_hasard=(1 + (nul >= auc).sum()) / (1 + len(nul)),
                         nul95=np.quantile(nul, 0.95), api_recon=api_r, api_vrai=api_v))
        allp.append(pd.DataFrame(dict(y=y, p=pr, serie=te.serie.values, tfm=te.tfm.values, sym=te.sym.values)))
        imps.append(perm_importance(m, te[FEATS].values, y, auc, FEATS, n_rep=3))
    P = pd.concat(allp, ignore_index=True)
    nul = null_auc(P.y.values, P.p.values, P.serie.values, 1000); auc = roc_auc_score(P.y, P.p)
    byu = {int(u): roc_auc_score(g.y, g.p) for u, g in P.groupby('tfm')}
    imp = pd.DataFrame(imps).mean().sort_values(ascending=False)
    imp_min = pd.DataFrame(imps).min()
    return pd.DataFrame(rows), dict(auc=auc, p=(1 + (nul >= auc).sum()) / 1001, nul95=np.quantile(nul, .95), par_unite=byu), imp, imp_min


def cross(side, kind):
    yk = 'y' + side; out = {}
    mes = CSV[(CSV.sym == 'MES') & CSV[yk].notna()]; nq = CSV[(CSV.sym == 'NQ') & CSV[yk].notna()]
    for name, tr, te in (('MES->NQ', mes, nq), ('NQ->MES', nq, mes)):
        m, p = fit(kind, tr[FEATS].values, tr[yk].values, tr.t.values)
        pr = m.predict_proba(te[FEATS].values)[:, 1]; auc = roc_auc_score(te[yk], pr)
        nul = null_auc(te[yk].values, pr, te.serie.values, 500)
        out[name] = dict(auc=auc, p=(1 + (nul >= auc).sum()) / 501, nul95=np.quantile(nul, .95))
    return out


def simple_baselines(side):
    yk = 'y' + side; a = folds()[0][0]; te = CSV[(CSV.t >= a) & CSV[yk].notna()]; out = {}
    for f in ('heishi_bull', 'trend_htf1', 'moy_dist50', 'ret5', 'rsi', 'sig_score', 'adx'):
        ok = te[f].notna()
        if ok.sum() > 100: out[f] = roc_auc_score(te[yk][ok], te[f][ok])
    return out


if __name__ == '__main__':
    print('lignes CSV', len(CSV), 'API', len(APIX), 'variables', len(FEATS))
    print('plis :', [(pd.Timestamp(a, unit='s', tz='Europe/Paris').strftime('%m-%d %H:%M'),
                      pd.Timestamp(b, unit='s', tz='Europe/Paris').strftime('%m-%d %H:%M')) for a, b in folds()])
    R = {}
    for side in ('L', 'S'):
        print('\n######## %s' % ('LONG' if side == 'L' else 'SHORT'))
        print('AUC variables seules (OOS, sens brut) :', {k: round(v, 3) for k, v in simple_baselines(side).items()})
        for kind in ('logit', 'logit_fixe', 'hgb'):
            tab, glob, imp, imp_min = walk_forward(side, kind); cr = cross(side, kind)
            print('\n== %s %s walk-forward' % (side, kind)); print(tab.round(3).to_string(index=False))
            print('poolé OOS : AUC %.3f  p_hasard %.3f  (95e centile hasard %.3f)  par unité %s' % (
                glob['auc'], glob['p'], glob['nul95'], {k: round(v, 3) for k, v in glob['par_unite'].items()}))
            print('croisé :', {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in cr.items()})
            mods = [k for k in imp.index if k in GROUPS]; feats_ = [k for k in imp.index if k not in GROUPS]
            print('importance par module (baisse AUC moyenne | min sur plis) :')
            for k in mods: print('   %-45s %+.4f | %+.4f' % (k, imp[k], imp_min[k]))
            print('top variables :', ', '.join('%s %+.4f (min %+.4f)' % (k, imp[k], imp_min[k]) for k in feats_[:10]))
            R['%s_%s' % (side, kind)] = dict(plis=tab.to_dict('records'), poole=glob, croise=cr,
                                             imp_modules={k: float(imp[k]) for k in mods},
                                             imp_vars={k: float(imp[k]) for k in feats_[:20]},
                                             imp_vars_min={k: float(imp_min[k]) for k in feats_[:20]})
    json.dump(R, open(os.path.join(HERE, 'resultats_modeles.json'), 'w'), indent=1, default=float)
