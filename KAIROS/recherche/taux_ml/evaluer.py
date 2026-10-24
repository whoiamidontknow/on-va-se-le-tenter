"""Étape 2 (taux_ml) : classifieur « haute précision » P(objectif avant le stop), walk-forward purgé.

Pour chaque géométrie fixe (construire.GEOMETRIES) et chaque modèle (logistique, boosting, arbre de
profondeur 2), on apprend P(trade gagnant) en walk-forward (plis de recherche/meta_ml/modele.plis : jours
CME, apprentissage croissant, purge + embargo 1 jour). Le SEUIL est choisi sur le passé seulement
(prédictions hors échantillon internes à l'apprentissage, 3 sous-plis) pour viser une précision cible
(65 / 70 / 75 %). On mesure hors échantillon : précision, nombre de trades, écart au taux de base de la
même géométrie (placebo), R moyen ; courbe précision / nombre de trades ; correction multiple par
permutation conjointe (max-z, façon White / Romano-Wolf) ; moteur + référence au hasard (moteur) +
simulateur Tradeify pour les meilleures politiques.

    ~/venv-quant/bin/python evaluer.py                    # étapes A (modèles), B (politiques), C (moteur)
    ~/venv-quant/bin/python evaluer.py --etape B          # reprend depuis sorties/predictions.pkl
    ~/venv-quant/bin/python evaluer.py --source dataset --reconstruire
    ~/venv-quant/bin/python evaluer.py --registre         # + lignes WRM dans le registre
"""
import argparse
import json
import os
import pickle
import sys
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.metrics import roc_auc_score

ICI = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(os.path.dirname(ICI), 'meta_ml')
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
sys.path[:0] = [ICI, META, os.path.join(SB, 'moteur'), os.path.join(SB, 'propfirm')]
import moteur as M  # noqa: E402
import registre as RG  # noqa: E402
import simulateur as SIM  # noqa: E402
import modele as MD  # noqa: E402          (recherche/meta_ml)
import donnees  # noqa: E402               (recherche/meta_ml : point d'accès unique aux données)
import importlib.util  # noqa: E402
import construire as CO  # noqa: E402      (ce dossier ; importé AVANT meta_ml/evaluer qui modifie sys.path)
_spec = importlib.util.spec_from_file_location('evaluer_meta_ml', os.path.join(META, 'evaluer.py'))
EV_META = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(EV_META)   # signaux, simulateur
# La purge de meta_ml/modele.py (plis, _sous_plis) lit les sorties des gestions de MD.GESTIONS : on y met NOS
# géométries (réglage à l'exécution seulement ; le fichier meta_ml n'est pas modifié).
MD.GESTIONS = list(CO.GEOMETRIES)

warnings.filterwarnings('ignore')
OUT = os.path.join(ICI, 'sorties')
REGLE = 'tradeify_50k_select_flex'
MODELES = ('logit', 'hgb', 'arbre')
CIBLES = (0.65, 0.70, 0.75)
FRACTIONS = (0.05, 0.10, 0.20, 0.30, 0.50, 1.0)
N_HASARD = 500
N_PERM = 2000
N_MIN_INTERNE = 10


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def ecrire(df, nom):
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, nom), index=False)


# ════════════════════════════════════════════════════════════════════════ données / plis
def charger_table(source=None, reconstruire=False):
    if reconstruire or not os.path.exists(CO.CACHE):
        CO.construire(source)
    d = pickle.load(open(CO.CACHE, 'rb'))
    return d['table'], d['groupes']


def colonnes(T):
    return [c for c in MD.colonnes_variables(T) if not c.startswith('y_')]


def plis(T):
    """modele.plis de meta_ml. Tous les trades sont intrajournée (15:59 Chicago) : la purge par journée CME
    est exacte, l'embargo d'un jour s'ajoute."""
    return MD.plis(T)


# ════════════════════════════════════════════════════════════════════════ modèles
class Modele:
    def __init__(self, nom):
        self.nom = nom

    def fit(self, X, y):
        fin = np.isfinite(X)
        self.cols = np.flatnonzero((fin.sum(0) >= 5) & (np.nanstd(np.where(fin, X, np.nan), 0) > 0))
        if self.nom == 'arbre':
            self.m = DecisionTreeClassifier(max_depth=2, min_samples_leaf=40, random_state=0)
        else:
            self.m = MD.fabrique(self.nom)
        self.m.fit(X[:, self.cols], y)
        return self

    def predict_proba(self, X):
        return self.m.predict_proba(X[:, self.cols])


def ajuste(nom, X, y):
    if len(np.unique(y)) < 2 or len(y) < 40:
        return None
    return Modele(nom).fit(X, y)


def predit(m, X, defaut):
    return np.full(len(X), defaut) if m is None else m.predict_proba(X)[:, 1]


def walk_forward(T, cols, nom, geo, folds):
    """-> liste par pli : dict(test, p_test (calibrée), p_int, y_int, r_int, modele)."""
    X = T[cols].to_numpy(float)
    y = T['y_' + geo].to_numpy(float)
    ok = np.isfinite(y)
    out = []
    for app, test in folds:
        app = app[ok[app]]; te = test[ok[test]]
        ps, ys = [], []
        for tr, ti in MD._sous_plis(T, app):
            tr = tr[ok[tr]]; ti = ti[ok[ti]]
            m = ajuste(nom, X[tr], y[tr].astype(int))
            ps.append(predit(m, X[ti], y[tr].mean())); ys.append(y[ti])
        m = ajuste(nom, X[app], y[app].astype(int))
        pb = predit(m, X[te], y[app].mean())
        if ps:
            ps, ys = np.concatenate(ps), np.concatenate(ys)
            cal = MD._platt(ps, ys.astype(int))
            p_int, p_te = cal(ps), cal(pb)
        else:
            p_int, ys, p_te = np.array([]), np.array([]), pb
        out.append(dict(test=te, p_test=p_te, p_int=p_int, y_int=ys, modele=m, base_app=float(y[app].mean())))
    return out


# ════════════════════════════════════════════════════════════════════════ politiques
def seuil_precision(p_int, y_int, cible, n_min=N_MIN_INTERNE):
    """Plus grand top-k interne (k >= n_min) dont la précision >= cible -> seuil = score du k-ième ;
    +inf si aucun (on ne prend rien dans ce pli)."""
    if not len(p_int):
        return np.inf
    o = np.argsort(-p_int, kind='stable')
    prec = np.cumsum(y_int[o]) / np.arange(1, len(o) + 1)
    k = np.flatnonzero((np.arange(1, len(o) + 1) >= n_min) & (prec >= cible))
    return float(p_int[o][k.max()]) if len(k) else np.inf


def politiques(wf, n_total):
    """{nom_politique: masque booléen sur T (sélection hors échantillon)} pour une (géométrie, modèle)."""
    P = {}
    for c in CIBLES:
        for regle in ('topk', 'proba'):
            m = np.zeros(n_total, bool)
            for f in wf:
                s = seuil_precision(f['p_int'], f['y_int'], c) if regle == 'topk' else c
                m[f['test'][f['p_test'] >= s]] = True
            P['%s%.0f' % (regle, 100 * c)] = m
    for q in FRACTIONS:
        m = np.zeros(n_total, bool)
        for f in wf:
            s = np.quantile(f['p_int'], 1 - q) if (q < 1 and len(f['p_int'])) else -np.inf
            m[f['test'][f['p_test'] >= s]] = True
        P['frac%02.0f' % (100 * q)] = m
    return P


def stats_selection(T, geo, mask, test_mask):
    y = T['y_' + geo].to_numpy(float); r = T['r_' + geo].to_numpy(float)
    ok = np.isfinite(y)
    sel = mask & ok; base = test_mask & ok
    n = int(sel.sum()); b = float(y[base].mean())
    prec = float(y[sel].mean()) if n else np.nan
    z = (prec - b) / np.sqrt(b * (1 - b) / n) if n else np.nan
    return dict(n=n, precision=prec, taux_base=b, ecart_pts=100 * (prec - b) if n else np.nan, z=z,
                r_moyen=float(r[sel].mean()) if n else np.nan, r_moyen_base=float(r[base].mean()))


def permutation_conjointe(T, lignes, masques, folds, n_perm=N_PERM, graine=0, globale=None):
    """Nul : dans chaque pli de test, on permute les LIGNES d'issues (toutes géométries ensemble) entre
    candidats -> sélection au hasard du même nombre par pli. p brute par politique + p ajustée max-z
    (famille = toutes les politiques avec n >= 10)."""
    geos = list(CO.GEOMETRIES)
    Y = T[['y_' + g for g in geos]].to_numpy(float)
    gi = np.array([geos.index(l['geometrie']) for l in lignes])
    S = np.array(masques, float)                                  # politiques x candidats
    test = np.concatenate([t for _, t in folds])
    groupes = [t for _, t in folds]
    valide = np.array([l['n'] >= 10 for l in lignes])
    rng = np.random.default_rng(graine)
    Yz = np.nan_to_num(Y); Ok = np.isfinite(Y).astype(float)

    def z_de(Yp, Okp):
        num = (S @ Yp)[np.arange(len(gi)), gi]; den = (S @ Okp)[np.arange(len(gi)), gi]
        prec = num / np.maximum(den, 1)
        base = np.array([np.nanmean(Y[test, g]) for g in range(len(geos))])[gi]
        return (prec - base) / np.sqrt(base * (1 - base) / np.maximum(den, 1)), prec
    z_obs, _ = z_de(Yz, Ok)
    globale = np.zeros(len(lignes), bool) if globale is None else (np.asarray(globale) & valide)
    g_obs = np.nanmean(z_obs[globale]) if globale.any() else np.nan; g_ge = 0
    ge_brut = np.zeros(len(lignes)); ge_max = np.zeros(len(lignes)); maxz = np.empty(n_perm)
    for b in range(n_perm):
        perm = np.arange(len(T))
        for g in groupes:
            perm[g] = g[rng.permutation(len(g))]
        zp, _ = z_de(Yz[perm], Ok[perm])
        ge_brut += zp >= z_obs - 1e-12
        maxz[b] = np.nanmax(np.where(valide, zp, -np.inf))
        if globale.any():
            g_ge += np.nanmean(zp[globale]) >= g_obs - 1e-12
    for k in range(len(lignes)):
        ge_max[k] = (maxz >= z_obs[k] - 1e-12).sum()
    return (1 + ge_brut) / (1 + n_perm), (1 + ge_max) / (1 + n_perm), dict(
        z_moyen=float(g_obs), p=float((1 + g_ge) / (1 + n_perm)), n_politiques=int(globale.sum()))


# ════════════════════════════════════════════════════════════════════════ moteur
def series_par_nom(source):
    return {s['nom']: s for s in donnees.charger_series(source)}


def moteur(T, mask, geo, series):
    """Une position à la fois par série, gestion = géométrie."""
    idx = T.index[mask]
    tous = []
    for nom, s in series.items():
        L, S = EV_META.signaux(T, idx, [s])[nom]
        if L.any() or S.any():
            t = M.backtest(s['df'], L, S, CO.gestion(s['instrument'], geo))
            t['serie'] = nom; t['instrument'] = s['instrument']; tous.append(t)
    return pd.concat(tous).sort_values('entree_t').reset_index(drop=True) if tous else pd.DataFrame()


def hasard(T, mask, geo, series, n=N_HASARD, graine=11):
    par = [[] for _ in range(n)]
    idx = T.index[mask]
    for nom, s in series.items():
        L, S = EV_META.signaux(T, idx, [s])[nom]
        if not (L.any() or S.any()):
            continue
        _, trs = M.reference_hasard(s['df'], n, CO.gestion(s['instrument'], geo), graine=graine, long=L, short=S,
                                    garder_trades=True)
        for k, t in enumerate(trs):
            par[k].append(t)
    out = [pd.concat(x).sort_values('entree_t').reset_index(drop=True) for x in par if x]
    return [t for t in out if len(t)]


def evaluer_moteur(T, mask, geo, series, regles, nom):
    tr = moteur(T, mask, geo, series)
    if not len(tr):
        return None, tr
    m = M.metriques(tr)
    refs = hasard(T, mask, geo, series)
    pg = np.array([(t['pnl_usd'] > 0).mean() for t in refs]); rm = np.array([t['r'].mean() for t in refs])
    sim = EV_META.simulateur(tr, refs, regles)
    ligne = dict(politique=nom, geometrie=geo, n=m['n'], pct_gagnants=m['pct_gagnants'],
                 pct_gagnants_hasard=float(pg.mean()), ecart_pts=100 * (m['pct_gagnants'] - pg.mean()),
                 p_gagnants=float((1 + (pg >= m['pct_gagnants']).sum()) / (1 + len(pg))),
                 r_moyen=m['r_moyen'], r_moyen_hasard=float(rm.mean()),
                 p_r=float((1 + (rm >= m['r_moyen']).sum()) / (1 + len(rm))), pf=m['pf'], ic95=m['r_ic95'],
                 net_usd=m['gain_net_usd'], dd_max_usd=m['dd_max_usd'], n_tirages=len(refs), **sim)
    return ligne, tr


# ════════════════════════════════════════════════════════════════════════ principal
def etape_A(T, cols, folds):
    WF = {}
    for geo in CO.GEOMETRIES:
        for nom in MODELES:
            WF[(geo, nom)] = walk_forward(T, cols, nom, geo, folds)
            y = T['y_' + geo].to_numpy(float)
            aucs = [roc_auc_score(y[f['test']], f['p_test']) for f in WF[(geo, nom)]
                    if len(np.unique(y[f['test']])) > 1 and np.ptp(f['p_test']) > 0]
            log('A %-9s %-5s AUC par pli %s' % (geo, nom, np.round(aucs, 3)))
    pickle.dump(dict(WF={k: [{kk: vv for kk, vv in f.items() if kk != 'modele'} for f in v] for k, v in WF.items()},
                     arbres={k: [f['modele'] for f in v] for k, v in WF.items() if k[1] == 'arbre'}),
                open(os.path.join(OUT, 'predictions.pkl'), 'wb'))
    return WF


def etape_B(T, cols, folds, WF):
    test_mask = np.zeros(len(T), bool)
    for _, t in folds:
        test_mask[t] = True
    lignes, masques = [], []
    for (geo, nom), wf in WF.items():
        y = T['y_' + geo].to_numpy(float)
        pl = np.full(len(T), np.nan); pp = np.full(len(T), np.nan)
        for k, f in enumerate(wf):
            pl[f['test']] = k; pp[f['test']] = f['p_test']
        auc, p_auc, par_pli, _ = MD.auc_test(y, pp, pl, n_perm=500)
        for pol, mask in politiques(wf, len(T)).items():
            s = stats_selection(T, geo, mask, test_mask)
            lignes.append(dict(geometrie=geo, modele=nom, politique=pol, auc_oos=auc, p_auc=p_auc, **s))
            masques.append(mask)
    # règle FIXÉE À L'AVANCE (CONSIGNES_TAUX) : la nuit 0h-8h Paris, tous les candidats, aucun modèle
    nuit = T['seance_nuit'].to_numpy() == 1
    for geo in CO.GEOMETRIES:
        s = stats_selection(T, geo, nuit & test_mask, test_mask)
        lignes.append(dict(geometrie=geo, modele='regle', politique='nuit_0_8h', auc_oos=np.nan, p_auc=np.nan, **s))
        masques.append(nuit & test_mask)
    # test GLOBAL fixé avant de regarder : « le haut du classement (5 et 10 %) bat-il le taux de base, en
    # moyenne sur toutes les géométries et tous les modèles ? » (moyenne des z, même nul conjoint)
    haut = [l['politique'] in ('frac05', 'frac10') for l in lignes]
    p_brut, p_ajust, glob = permutation_conjointe(T, lignes, masques, folds, globale=haut)
    log('B test global haut 5-10 %% : z moyen %.2f, p %.4f (%d politiques)' % (glob['z_moyen'], glob['p'], glob['n_politiques']))
    json.dump(glob, open(os.path.join(OUT, 'test_global.json'), 'w'), indent=1)
    B = pd.DataFrame(lignes)
    B['p_brut'] = p_brut; B['p_ajuste_maxz'] = p_ajust
    B['n_variantes_famille'] = int((B['n'] >= 10).sum())
    ecrire(B, 'politiques.csv')
    pickle.dump(masques, open(os.path.join(OUT, 'masques.pkl'), 'wb'))
    # règle nuit sur TOUT l'échantillon de dev (elle n'apprend rien, elle peut être évaluée partout)
    tout = np.ones(len(T), bool)
    nl = [dict(geometrie=g, **{k + '_nuit': v for k, v in stats_selection(T, g, nuit, tout).items()},
               **{k + '_jour': v for k, v in stats_selection(T, g, ~nuit, tout).items()}) for g in CO.GEOMETRIES]
    ecrire(pd.DataFrame(nl), 'regle_nuit_tout_dev.csv')
    return B, masques, test_mask


def arbres_lisibles(T, cols, WF):
    """Arbres de profondeur 2 : premiers découpages par pli (stabilité) + arbre sur tout le dev (in-sample)."""
    txt = []
    for geo in CO.GEOMETRIES:
        y = T['y_' + geo].to_numpy(float); ok = np.isfinite(y)
        X = T[cols].to_numpy(float)
        m = Modele('arbre').fit(X[ok], y[ok].astype(int))
        noms = [cols[j] for j in m.cols]
        txt.append('=== %s : arbre profondeur 2 sur TOUT le dev (in-sample, taux de base %.3f) ===' % (geo, y[ok].mean()))
        txt.append(export_text(m.m, feature_names=noms, show_weights=True, decimals=3))
    open(os.path.join(OUT, 'arbres.txt'), 'w').write('\n'.join(txt))


def etape_C(T, B, masques, source, n_max=10):
    """Moteur + hasard moteur + simulateur : base (tous les candidats de test), règle nuit, et les meilleures
    politiques apprises (n >= 30, écart > 0, tri par p brute)."""
    series = series_par_nom(source)
    regles = SIM.charge_regles()[REGLE]
    choix = []
    for geo in CO.GEOMETRIES:
        choix.append(B.index[(B['geometrie'] == geo) & (B['modele'] == 'logit') & (B['politique'] == 'frac100')][0])
        choix.append(B.index[(B['geometrie'] == geo) & (B['politique'] == 'nuit_0_8h')][0])
    cand = B[(B['n'] >= 30) & (B['ecart_pts'] > 0) & (B['politique'] != 'frac100') & (B['modele'] != 'regle')]
    choix += list(cand.sort_values('p_brut').index[:n_max])
    res = []
    for k in dict.fromkeys(choix):
        l = B.loc[k]
        nom = '%s|%s|%s' % (l['geometrie'], l['modele'], l['politique'])
        ligne, tr = evaluer_moteur(T, masques[k], l['geometrie'], series, regles, nom)
        if ligne is None:
            continue
        ligne.update(modele=l['modele'], regle=l['politique'], p_brut_candidats=l['p_brut'],
                     p_ajuste_candidats=l['p_ajuste_maxz'])
        res.append(ligne)
        tr.to_csv(os.path.join(OUT, 'trades_%s.csv' % nom.replace('|', '_')), index=False)
        log('C', nom, {kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in ligne.items()
                       if kk in ('n', 'pct_gagnants', 'pct_gagnants_hasard', 'p_gagnants', 'r_moyen', 'p_r', 'pf',
                                 'p_reussite', 'ref_p_reussite')})
        ecrire(pd.DataFrame(res), 'moteur.csv')
    return pd.DataFrame(res)


RETENUES = {  # (politique moteur, libellé) : les 3 recettes du RESULTATS.md
    'S2R05|hgb|frac10': 'boosting, 10 % les mieux notés, stop 2 ATR / objectif 0,5R',
    'S2R05|regle|nuit_0_8h': 'règle nuit 0h-8h Paris (fixée à l\'avance), stop 2 ATR / objectif 0,5R',
    'S15R1_BE|logit|frac05': 'logistique, 5 % les mieux notés, stop 1,5 ATR / objectif 1R / BE 0,5R',
}


def ecrire_registre(source=None):
    C = pd.read_csv(os.path.join(OUT, 'moteur.csv'))
    B = pd.read_csv(os.path.join(OUT, 'politiques.csv'))
    n_var = int(len(B))
    echant = 'dev_dataset' if source == 'dataset' else 'dev_cache'
    for _, l in C[C['politique'].isin(list(RETENUES))].iterrows():
        tr = pd.read_csv(os.path.join(OUT, 'trades_%s.csv' % l['politique'].replace('|', '_')),
                         parse_dates=['entree_t', 'sortie_t'])
        verdict = ('%.1f %% gagnants vs placebo %.1f %% (écart %+.1f pts, p %.3f, %d tirages) ; R %+.3f, PF %.2f ; '
                   'p ajustée (max-z, %d politiques) %.3f -> %s' % (
                       100 * l['pct_gagnants'], 100 * l['pct_gagnants_hasard'], l['ecart_pts'], l['p_gagnants'],
                       l['n_tirages'], l['r_moyen'], l['pf'], n_var, l['p_ajuste_candidats'],
                       'survit à la correction mais n < 60 et précision < 60 %' if l['p_ajuste_candidats'] < 0.05
                       else 'ne survit PAS à la correction multiple : non probant'))
        RG.ajouter_test(dict(agent='taux_ml', famille='Taux de réussite / classifieur haute précision',
                             recette='%s (union des déclencheurs, walk-forward purgé 5 plis)' % RETENUES[l['politique']],
                             marche='MES+MNQ', ut_signal='15', ut_entree='15', echantillon=echant,
                             n_variantes_testees=n_var, p_tradeify=l.get('p_reussite'),
                             p_ref_hasard=l.get('ref_p_reussite'), verdict=verdict, trades=tr), prefixe='WRM')
    log('registre écrit')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    ap.add_argument('--reconstruire', action='store_true')
    ap.add_argument('--etape', default='A', choices=['A', 'B', 'C'])
    ap.add_argument('--registre', action='store_true', help='+ lignes WRM (après C)')
    ap.add_argument('--registre-seul', action='store_true')
    a = ap.parse_args()
    if a.registre_seul:
        return ecrire_registre(a.source)
    os.makedirs(OUT, exist_ok=True)
    T, groupes = charger_table(a.source, a.reconstruire)
    cols = colonnes(T)
    folds = plis(T)
    log('%d candidats, %d variables, plis %s' % (len(T), len(cols), [(len(x), len(y)) for x, y in folds]))
    if a.etape == 'A':
        WF = etape_A(T, cols, folds)
    else:
        WF = pickle.load(open(os.path.join(OUT, 'predictions.pkl'), 'rb'))['WF']
    if a.etape in ('A', 'B'):
        B, masques, _ = etape_B(T, cols, folds, WF)
        arbres_lisibles(T, cols, WF)
    else:
        B = pd.read_csv(os.path.join(OUT, 'politiques.csv'))
        masques = pickle.load(open(os.path.join(OUT, 'masques.pkl'), 'rb'))
    log('B fini : %d politiques' % len(B))
    etape_C(T, B, masques, a.source)
    if a.registre:
        ecrire_registre(a.source)


if __name__ == '__main__':
    main()
