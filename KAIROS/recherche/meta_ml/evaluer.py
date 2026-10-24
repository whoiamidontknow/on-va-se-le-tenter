"""Étape 2 : walk-forward des modèles, politiques, moteur, simulateur Tradeify, importance des variables.

    ~/venv-quant/bin/python evaluer.py                 # sur cache/candidats.pkl (construire.py d'abord)
    ~/venv-quant/bin/python evaluer.py --reconstruire --source dataset   # passage au DATASET
    ~/venv-quant/bin/python evaluer.py --registre      # + lignes ML-xxxx dans le registre (une seule fois)
    ~/venv-quant/bin/python evaluer.py --registre-seul # lignes registre depuis sorties/, sans recalcul

Sorties (dossier sorties/) : balayage.csv (toutes les variantes), politiques_moteur.csv (moteur + simulateur),
importance_*.csv, predictions.csv, resultats.json ; trades des politiques dans sorties/trades_*.csv.
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

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
sys.path[:0] = [ICI, os.path.join(SB, 'moteur'), os.path.join(SB, 'propfirm')]
import moteur as M  # noqa: E402
import registre as RG  # noqa: E402
import simulateur as SIM  # noqa: E402
import candidats as CD  # noqa: E402
import donnees  # noqa: E402
import modele as MD  # noqa: E402

warnings.filterwarnings('ignore')
OUT = os.path.join(ICI, 'sorties')
REGLE = 'tradeify_50k_select_flex'
TAILLES = [1, 2, 3, 5, 8]
N_SIM = 1000
N_HASARD = 1000       # 100 lors du run du 16/10 (sauf « tous les candidats A15R2 », relancé à 1000)


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def ecrire(df, nom):
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(os.path.join(OUT, nom), index=False)


# ─────────────────────────────────────────────── moteur
def signaux(T, choix_idx, series):
    """{nom_serie: (long_bool, short_bool)} à partir des lignes choisies de T."""
    out = {}
    for s in series:
        n = len(s['df'])
        L = np.zeros(n, bool); S = np.zeros(n, bool)
        sub = T.loc[choix_idx]
        sub = sub[sub['serie'] == s['nom']]
        L[sub.loc[sub['sens'] == 1, 'i'].to_numpy(int)] = True
        S[sub.loc[sub['sens'] == -1, 'i'].to_numpy(int)] = True
        out[s['nom']] = (L, S)
    return out


def moteur_politique(T, choix_par_gestion, series):
    """choix_par_gestion : {gestion: index de T}. Une position à la fois PAR SÉRIE ; si plusieurs gestions,
    les trades qui chevauchent un trade antérieur de la même série sont retirés."""
    tous = []
    for s in series:
        G = CD.gestions(s['df'], s['instrument'])
        px = s['df']
        tr = []
        for g, idx in choix_par_gestion.items():
            L, S = signaux(T, idx, [s])[s['nom']]
            if L.any() or S.any():
                t = M.backtest(px, L, S, G[g]); t['gestion'] = g; tr.append(t)
        if not tr:
            continue
        t = pd.concat(tr).sort_values('entree_t').reset_index(drop=True)
        garde, fin = [], None
        for k, row in t.iterrows():
            if fin is None or row['entree_t'] >= fin:
                garde.append(k); fin = row['sortie_t']
        t = t.loc[garde]; t['serie'] = s['nom']; t['instrument'] = s['instrument']
        tous.append(t)
    return pd.concat(tous).sort_values('entree_t').reset_index(drop=True) if tous else pd.DataFrame()


def hasard_moteur(T, idx, gestion, series, n=N_HASARD):
    """moteur.reference_hasard série par série (mêmes heures, même sens, même fréquence), tirages combinés."""
    par_tirage = [[] for _ in range(n)]
    for s in series:
        L, S = signaux(T, idx, [s])[s['nom']]
        if not (L.any() or S.any()):
            continue
        G = CD.gestions(s['df'], s['instrument'])[gestion]
        _, trs = M.reference_hasard(s['df'], n, G, graine=7, long=L, short=S, garder_trades=True)
        for k, t in enumerate(trs):
            par_tirage[k].append(t)
    out = [pd.concat(x).sort_values('entree_t').reset_index(drop=True) for x in par_tirage if x]
    return [t for t in out if len(t)]


def simulateur(trades, refs, regles):
    if not len(trades):
        return {}
    tab, best = SIM.optimise_taille(trades, regles, TAILLES, n_sim=N_SIM, ordre='prudent', bloc_jours=5)
    c = int(best['contrats'])
    ref = SIM.analyse_reference(refs[:30], regles, c, n_sim=N_SIM, ordre='prudent', bloc_jours=5) if refs else {}
    return dict(contrats=c, p_reussite=best['p_reussite'], p_1er_payout=best.get('p_1er_payout'),
                ve_usd=best.get('valeur_esperee_usd'), ref_p_reussite=ref.get('p_reussite'),
                ref_p_1er_payout=ref.get('p_1er_payout'), ref_ve_usd=ref.get('valeur_esperee_usd'))


# ─────────────────────────────────────────────── principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reconstruire', action='store_true')
    ap.add_argument('--source', default=None)
    ap.add_argument('--registre', action='store_true')
    ap.add_argument('--rapide', action='store_true', help='sans moteur/simulateur/importance')
    ap.add_argument('--registre-seul', action='store_true', help='registre depuis sorties/, sans recalcul')
    a = ap.parse_args()
    if a.registre_seul:
        return registre_seul(a.source)
    if a.reconstruire or not os.path.exists(os.path.join(ICI, 'cache', 'candidats.pkl')):
        import construire
        construire.construire(a.source)
    d = pickle.load(open(os.path.join(ICI, 'cache', 'candidats.pkl'), 'rb'))
    T, groupes = d['table'], d['groupes']
    series = donnees.charger_series(a.source)
    cols = MD.colonnes_variables(T)
    folds = MD.plis(T)
    log('%d candidats, %d variables, %d plis : %s' % (len(T), len(cols), len(folds),
        [(len(x), len(y), str(T['jour'].iloc[y].min())[:10], str(T['jour'].iloc[y].max())[:10]) for x, y in folds]))
    test_idx = np.concatenate([y for _, y in folds])
    pli = np.full(len(T), np.nan)
    for f, (_, y) in enumerate(folds):
        pli[y] = f
    R = dict(n_candidats=len(T), n_variables=len(cols), variables=cols,
             plis=[dict(n_app=len(x), n_test=len(y), debut=str(T['jour'].iloc[y].min())[:10],
                        fin=str(T['jour'].iloc[y].max())[:10]) for x, y in folds])

    # ── 1. modèles × gestions
    P = {}; MODS = {}; bal = []
    for nom in ('hgb', 'logit'):
        for g in MD.GESTIONS:
            res, mods = MD.walk_forward(T, cols, nom, g, folds)
            P[(nom, g)] = res; MODS[(nom, g)] = mods
            r = T['r_' + g].to_numpy(float); y = (r > 0).astype(int)
            p = res['p'].to_numpy(float)
            auc, pval, par_pli, auc_pool = MD.auc_test(y, p, pli)
            pris = res['pris'].to_numpy(float) == 1
            obs, p_sel, nul = MD.selection_au_hasard(r, pris, pli)
            m = np.isfinite(p) & np.isfinite(r)
            brier = float(np.mean((p[m] - y[m]) ** 2)); brier0 = float(np.mean((y[m].mean() - y[m]) ** 2))
            ligne = dict(modele=nom, gestion=g, auc_oos=auc, p_auc=pval, auc_poolee=auc_pool, auc_par_pli=[round(x, 3) for x in par_pli],
                         brier=brier, brier_constante=brier0, n_test=int(m.sum()), n_pris=int(pris.sum()),
                         r_moyen_pris=obs, r_moyen_tous_test=float(np.nanmean(r[test_idx])),
                         r_moyen_hasard_meme_nb=nul, p_selection=p_sel,
                         fractions_choisies=sorted(res['q'].dropna().unique().tolist()))
            bal.append(ligne)
            log(nom, g, 'AUC %.3f (p %.3f) plis %s | pris %d R %.3f vs tous %.3f, hasard %.3f (p %.3f) | Brier %.4f/%.4f'
                % (auc, pval, ligne['auc_par_pli'], pris.sum(), obs, ligne['r_moyen_tous_test'], nul, p_sel, brier, brier0))
    # politique « choix de la gestion » : E[R_g] = p_g W_g - (1 - p_g) L_g (W, L moyens des gagnants/perdants
    # de l'apprentissage du pli), on prend la meilleure gestion si E > 0 (seuil fixé à l'avance).
    CHOIX = {}
    for nom in ('hgb', 'logit'):
        E = pd.DataFrame(index=T.index, columns=MD.GESTIONS, dtype=float)
        for g in MD.GESTIONS:
            p = P[(nom, g)]['p'].astype(float)
            for f, (app, test) in enumerate(folds):
                ra = T['r_' + g].iloc[app]
                W = ra[ra > 0].mean(); Lm = -ra[ra <= 0].mean()
                E.iloc[test, E.columns.get_loc(g)] = (p.iloc[test] * W - (1 - p.iloc[test]) * Lm).to_numpy()
        best = E.fillna(-np.inf).idxmax(axis=1)
        emax = E.max(axis=1)
        prend = (emax > 0) & emax.notna()
        r_ch = np.array([T.at[i, 'r_' + best[i]] if prend[i] else np.nan for i in T.index], float)
        CHOIX[nom] = (best, prend)
        # référence : même nombre, même gestion choisie au hasard parmi les candidats du pli
        obs = np.nanmean(r_ch[prend.to_numpy()])
        rng = np.random.default_rng(1); nul = []
        for _ in range(3000):
            tot = []
            for f in range(len(folds)):
                k = np.flatnonzero((pli == f))
                c = int(prend.to_numpy()[k].sum())
                if c:
                    pick = rng.choice(k, c, replace=False)
                    gg = rng.choice(MD.GESTIONS, c)
                    tot.append([T['r_' + x].iloc[j] for j, x in zip(pick, gg)])
            nul.append(np.nanmean(np.concatenate(tot)))
        nul = np.array(nul)
        ligne = dict(modele=nom, gestion='CHOIX', n_pris=int(prend.sum()), r_moyen_pris=float(obs),
                     r_moyen_hasard_meme_nb=float(nul.mean()), p_selection=float((1 + (nul >= obs).sum()) / (1 + len(nul))),
                     repartition=best[prend].value_counts().to_dict())
        bal.append(ligne)
        log(nom, 'CHOIX', ligne)
    B = pd.DataFrame(bal)
    ecrire(B, 'balayage.csv')
    R['balayage'] = B.to_dict('records')
    pred = T[['t_signal', 'serie', 'sens', 'jour'] + ['r_' + g for g in MD.GESTIONS]].copy()
    pred['pli'] = pli
    for (nom, g), res in P.items():
        pred['p_%s_%s' % (nom, g)] = res['p']; pred['pris_%s_%s' % (nom, g)] = res['pris']
    ecrire(pred, 'predictions.csv')

    # ── 2. canari : une variable qui contient l'issue doit être détectée (contrôle de la machine)
    Tc = T.copy(); rng = np.random.default_rng(3)
    Tc['canari'] = (Tc['r_A15R2'] > 0).astype(float) + rng.normal(0, 1.0, len(Tc))
    resc, _ = MD.walk_forward(Tc, cols + ['canari'], 'hgb', 'A15R2', folds)
    yc = (Tc['r_A15R2'] > 0).to_numpy(int)
    R['canari_auc'] = MD.auc_test(yc, resc['p'].to_numpy(float), pli, n_perm=200)[0]
    log('canari (issue + bruit) AUC %.3f' % R['canari_auc'])
    json.dump(R, open(os.path.join(OUT, 'resultats.json'), 'w'), indent=1, default=str)
    if a.rapide:
        return

    # ── 3. importance par permutation
    for nom, g in (('hgb', 'A15R2'), ('logit', 'A15R2'), ('hgb', 'A1R1'), ('hgb', 'NIV')):
        A = MD.importance_permutation(T, cols, groupes, nom, g, folds, MODS[(nom, g)])
        ecrire(A, 'importance_%s_%s.csv' % (nom, g))
        log('importance', nom, g, A[A['type'] == 'groupe'].head(6)[['bloc', 'mean', 'min']].round(4).to_dict('records'))

    # ── 4. moteur + simulateur
    regles = SIM.charge_regles()[REGLE]
    pol = []
    idx_test = T.index[test_idx]
    cas = []
    for g in MD.GESTIONS:
        cas.append(('tous_les_candidats', g, {g: idx_test}))
    for nom in ('hgb', 'logit'):
        for g in MD.GESTIONS:
            res = P[(nom, g)]
            cas.append(('%s_seuil' % nom, g, {g: res.index[res['pris'] == 1]}))
        best, prend = CHOIX[nom]
        cas.append(('%s_choix' % nom, 'CHOIX', {g: T.index[prend & (best == g)] for g in MD.GESTIONS}))
    for nom_cas, g, choix in cas:
        tr = moteur_politique(T, choix, series)
        if not len(tr):
            continue
        m = M.metriques(tr)
        g_ref = g if g != 'CHOIX' else max(choix, key=lambda k: len(choix[k]))
        idx_all = np.concatenate([np.asarray(v) for v in choix.values()])
        refs = hasard_moteur(T, idx_all, g_ref, series)
        rm = [t['r'].mean() for t in refs]
        p_h = float((1 + sum(x >= m['r_moyen'] for x in rm)) / (1 + len(rm)))
        sim = simulateur(tr, refs, regles)
        ligne = dict(politique=nom_cas, gestion=g, n=m['n'], r_moyen=m['r_moyen'], ic95=m.get('r_ic95'),
                     pf=m['pf'], pct_gagnants=m['pct_gagnants'], net_usd=m['gain_net_usd'], dd_max_usd=m['dd_max_usd'],
                     r_moyen_hasard=float(np.mean(rm)), p_hasard=p_h, **sim)
        pol.append(ligne)
        tr.to_csv(os.path.join(OUT, 'trades_%s_%s.csv' % (nom_cas, g)), index=False)
        log('MOTEUR', nom_cas, g, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in ligne.items()})
        ecrire(pd.DataFrame(pol), 'politiques_moteur.csv')
    R['politiques'] = pol
    json.dump(R, open(os.path.join(OUT, 'resultats.json'), 'w'), indent=1, default=str)

    # ── 5. registre (lignes retenues seulement)
    if a.registre:
        ecrire_registre(pol, len(cols), a.source)


RETENUES = {('tous_les_candidats', 'A15R2'), ('hgb_seuil', 'A15R2'), ('logit_seuil', 'A15R2'),
            ('hgb_choix', 'CHOIX'), ('logit_choix', 'CHOIX')}


def ecrire_registre(pol, n_cols, source=None):
    """Une ligne ML-xxxx par politique retenue, à partir des lignes moteur+simulateur (pol)."""
    n_var = 8 + 3        # 2 modèles × (3 gestions + choix) + 3 « tous les candidats » ; fractions choisies sur le passé
    echant = 'dev_dataset' if (source == 'dataset') else 'dev_cache'
    for ligne in pol:
        if (ligne['politique'], ligne['gestion']) not in RETENUES:
            continue
        tr = pd.read_csv(os.path.join(OUT, 'trades_%s_%s.csv' % (ligne['politique'], ligne['gestion'])),
                         parse_dates=['entree_t', 'sortie_t'])
        bat = ligne['p_hasard'] < 0.05 / n_var
        verdict = ('%s ; R moyen %.3f vs hasard %.3f (p %.3f, seuil Bonferroni %.4f) ; P(réussite) %.3f vs réf. hasard %.3f — %s' % (
            ligne['politique'], ligne['r_moyen'], ligne['r_moyen_hasard'], ligne['p_hasard'], 0.05 / n_var,
            ligne.get('p_reussite', np.nan), ligne.get('ref_p_reussite', np.nan) or np.nan,
            'bat le hasard (à confirmer sur le DATASET)' if bat else
            ('mieux que le hasard sans correction, PAS après correction multiple' if ligne['p_hasard'] < 0.05
             else 'ne bat pas le hasard hors échantillon')))
        RG.ajouter_test(dict(agent='meta_ml', famille='Méta-modèle ML',
                             recette='%s, gestion %s, walk-forward purgé 5 plis (union des déclencheurs, %d variables)'
                             % (ligne['politique'], ligne['gestion'], n_cols),
                             marche='MES+MNQ', ut_signal='15', ut_entree='15', echantillon=echant,
                             n_variantes_testees=n_var, p_tradeify=ligne.get('p_reussite'),
                             p_ref_hasard=ligne.get('ref_p_reussite'), verdict=verdict, trades=tr), prefixe='ML')
    log('registre écrit')


def registre_seul(source=None):
    """Écrit le registre depuis sorties/politiques_moteur.csv sans rien recalculer."""
    pol = pd.read_csv(os.path.join(OUT, 'politiques_moteur.csv')).to_dict('records')
    n_cols = json.load(open(os.path.join(OUT, 'resultats.json')))['n_variables']
    ecrire_registre(pol, n_cols, source)

if __name__ == '__main__':
    main()
