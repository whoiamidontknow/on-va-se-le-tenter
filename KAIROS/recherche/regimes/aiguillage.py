"""Aiguillage état de marché -> setup (ou pas de trade), évalué en walk-forward strict.

    ~/venv-quant/bin/python aiguillage.py                     # source cache (défaut), résultats dans ce dossier
    ~/venv-quant/bin/python aiguillage.py --source dataset    # DATASET.pine (dès que les exports sont là)
    ~/venv-quant/bin/python aiguillage.py --registre          # + lignes dans registre/registre_tests.csv

Étapes :
 1. balayage : chaque setup du catalogue (setups.py, 9 déclencheurs x 3 sens x 6 filtres x 4 sorties = 648) est
    rejoué sur chaque série (développement seulement) ; chaque trade est étiqueté par l'état de sa barre signal
    dans chaque partition (etats.py) -> balayage_trades.pkl / balayage_setups.csv.
 2. walk-forward ANCRÉ sur le calendrier commun des séries : jours coupés en RATIO + K blocs ; pli p :
    apprentissage = blocs [0, p + RATIO), test = bloc p + RATIO. Sur l'apprentissage SEULEMENT, pour chaque état :
    setup au meilleur t (R moyen / erreur type, n >= NMIN) ; trader seulement si ce t >= T_MIN, sinon « pas de
    trade ». Appliqué tel quel au pli de test : rejeu EXACT (signaux masqués à l'état et aux jours de test, une
    position à la fois par série, la gestion propre à chaque setup).
 3. références : (a) partition UNIQUE = meilleur setup unique choisi de la même façon ; (b) entrées au hasard
    (moteur.reference_hasard : même heure, même sens, même gestion, mêmes jours de test) ; (c) développement
    (apprentissage) contre pli suivant = mesure du surapprentissage.
 4. propfirm : Tradeify Select Flex, Monte-Carlo par blocs de 5 jours sur les jours de TEST mis bout à bout,
    risque fixe RISQUE_USD par trade (micros), même règle pour l'aiguillage, l'unique et le hasard.
"""
from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import donnees  # noqa: E402  (pose sys.path vers moteur / dataset / propfirm)
import etats as E  # noqa: E402
import setups as SU  # noqa: E402
import moteur as M  # noqa: E402
import registre as RG  # noqa: E402
import simulateur as PF  # noqa: E402

K, RATIO = 5, 3
T_MINS = (0.0, 1.5, 2.5)
VARIANTE_PF = 'tradeify_50k_select_flex'
SER: list = []          # séries préparées (globale partagée avec les processus fils, fork)
BAL: pd.DataFrame | None = None
PLIS: list = []
OPT: argparse.Namespace | None = None


# ════════════════════════════════════ préparation ════════════════════════════════════
def jour_cme(idx: pd.DatetimeIndex) -> np.ndarray:
    t = idx.tz_convert('America/Chicago').tz_localize(None)
    return (t + pd.Timedelta(hours=7)).normalize().to_numpy()


def preparer(source):
    ser = donnees.charger_series(source)
    for s in ser:
        d = E.briques(s['df'])
        s['d'] = d
        s['lab'] = E.etiquettes(d)
        s['D'] = SU.declencheurs(d)
        s['F'] = SU.filtres(d)
        s['jour'] = jour_cme(d.index)
    return ser


def _tag(T: pd.DataFrame, s, setup) -> pd.DataFrame:
    pos = s['d'].index.get_indexer(pd.DatetimeIndex(T['entree_t'])) - 1
    out = pd.DataFrame(dict(setup=SU.nom_setup(setup), serie=s['nom'], instrument=s['instrument'],
                            jour=s['jour'][pos], entree_t=T['entree_t'].to_numpy(), r=T['r'].to_numpy(float),
                            pnl_usd=T['pnl_usd'].to_numpy(float)))
    for P in s['lab']:
        out[P] = s['lab'][P].to_numpy()[pos]
    return out


def _balayer(setups):
    rows = []
    for setup in setups:
        for s in SER:
            L, S = SU.signaux(setup, s['D'], s['F'])
            if not (L.any() or S.any()):
                continue
            T = M.backtest(s['d'], L, S, SU.gestion(setup[3], s['instrument'], s['d']))
            if len(T):
                rows.append(_tag(T, s, setup))
    return pd.concat(rows, ignore_index=True) if rows else None


def plis_communs(ser):
    jours = np.unique(np.concatenate([s['jour'] for s in ser]))
    nb = RATIO + K
    b = np.linspace(0, len(jours), nb + 1).round().astype(int)
    blocs = [jours[b[q]:b[q + 1]] for q in range(nb)]
    return [(np.concatenate(blocs[:p + RATIO]), blocs[p + RATIO]) for p in range(K)]


# ════════════════════════════════════ choix sur le passé ════════════════════════════════════
def stats_groupes(T: pd.DataFrame, cles) -> pd.DataFrame:
    g = T.groupby(cles)['r']
    st = g.agg(n='count', moy='mean', sd='std', somme='sum').reset_index()
    st['t'] = st['moy'] / (st['sd'] / np.sqrt(st['n']))
    st.loc[~np.isfinite(st['t']), 't'] = np.nan
    return st


def choisir(Ttrain: pd.DataFrame, P: str, tmin: float, nmin: int) -> dict:
    """état -> dict(setup, n, moy, t) du meilleur setup appris, ou None (« pas de trade »)."""
    st = stats_groupes(Ttrain, [P, 'setup'])
    st = st[(st['n'] >= nmin) & st['t'].notna()]
    out = {}
    for e in range(len(E.PARTITIONS[P][1])):
        c = st[st[P] == e]
        if not len(c):
            out[e] = None
            continue
        b = c.loc[c['t'].idxmax()]
        out[e] = (dict(setup=b['setup'], n=int(b['n']), moy=float(b['moy']), t=float(b['t']))
                  if b['t'] >= tmin and b['moy'] > 0 else None)
    return out


def _setup_tuple(nom):
    return tuple(nom.split('|'))


def _fusion(trs: list[pd.DataFrame]) -> pd.DataFrame:
    """Une position à la fois par série : on garde les trades dans l'ordre d'entrée, sans chevauchement."""
    trs = [t for t in trs if t is not None and len(t)]
    if not trs:
        return pd.DataFrame(columns=M.COLONNES_TRADES + ['serie', 'instrument', 'etat', 'setup'])
    T = pd.concat(trs, ignore_index=True).sort_values('entree_t')
    garde = []
    fin = {}
    for i, row in zip(T.index, T[['serie', 'entree_t', 'sortie_t']].itertuples(index=False)):
        if row.serie in fin and row.entree_t < fin[row.serie]:
            continue
        garde.append(i)
        fin[row.serie] = row.sortie_t
    return T.loc[garde].reset_index(drop=True)


def rejouer(choix: dict, P: str, jours_test, n_ref=0, graine=0):
    """Rejeu exact de l'aiguillage sur les jours de test ; + n_ref tirages au hasard (même gestion)."""
    trs, refs = [], [[] for _ in range(n_ref)]
    for si, s in enumerate(SER):
        m = np.isin(s['jour'], jours_test)
        if not m.any():
            continue
        dt = s['d'][m]
        lab = s['lab'][P].to_numpy()[m]
        for e, c in choix.items():
            if c is None:
                continue
            setup = _setup_tuple(c['setup'])
            L, S = SU.signaux(setup, s['D'], s['F'])
            L = L[m] & (lab == e); S = S[m] & (lab == e)
            if not (L.any() or S.any()):
                continue
            g = SU.gestion(setup[3], s['instrument'], dt)
            T = M.backtest(dt, L, S, g)
            extra = dict(serie=s['nom'], instrument=s['instrument'], etat=E.PARTITIONS[P][1][e], setup=c['setup'])
            trs.append(T.assign(**extra))
            if n_ref:
                _, tirs = M.reference_hasard(dt, n_ref, g, graine=graine + 1000 * si + e, long=L, short=S,
                                             garder_trades=True)
                for j, t in enumerate(tirs):
                    refs[j].append(t.assign(**extra))
    return _fusion(trs), [_fusion(r) for r in refs]


def evaluer(args):
    """Une variante (partition, T_MIN) sur tous les plis."""
    P, tmin = args
    oos, refs, choix_plis, is_rows = [], [[] for _ in range(OPT.nref)], [], []
    for p, (jtr, jte) in enumerate(PLIS):
        Ttr = BAL[np.isin(BAL['jour'], jtr)]
        ch = choisir(Ttr, P, tmin, OPT.nmin)
        # développement : performance, sur l'apprentissage, des couples (état, setup) choisis (en-échantillon)
        for e, c in ch.items():
            if c is not None:
                x = Ttr[(Ttr[P] == e) & (Ttr['setup'] == c['setup'])]
                is_rows.append(x.assign(pli=p))
            choix_plis.append(dict(pli=p, etat=E.PARTITIONS[P][1][e], setup=c['setup'] if c else 'PAS DE TRADE',
                                   n_app=c['n'] if c else 0, r_app=c['moy'] if c else np.nan,
                                   t_app=c['t'] if c else np.nan))
        T, R = rejouer(ch, P, jte, OPT.nref, graine=17 * p + int(10 * tmin))
        oos.append(T.assign(pli=p))
        for j, t in enumerate(R):
            refs[j].append(t)
    oos = pd.concat(oos, ignore_index=True)
    refs = [pd.concat(r, ignore_index=True) for r in refs]
    IS = pd.concat(is_rows, ignore_index=True) if is_rows else pd.DataFrame(columns=['r', 'jour', 'pli'])
    return dict(P=P, tmin=tmin, oos=oos, refs=refs, choix=pd.DataFrame(choix_plis), IS=IS)


# ════════════════════════════════════ propfirm ════════════════════════════════════
def compacter(T: pd.DataFrame, jours_test: np.ndarray) -> pd.DataFrame:
    """Met les jours de test bout à bout (calendrier fictif de jours ouvrés) pour que le Monte-Carlo ne compte pas
    l'été sans données comme des journées vides. Trades intrajournée : décalage d'un nombre entier de jours."""
    jt = np.unique(jours_test)
    faux = pd.bdate_range('2030-01-07', periods=len(jt)).to_numpy()
    dec = pd.Series(faux - jt, index=jt)
    if not len(T):
        return T
    T = T.copy()
    j = jour_cme(pd.DatetimeIndex(T['entree_t']))
    d = dec.reindex(j).to_numpy()
    T['entree_t'] = pd.DatetimeIndex(T['entree_t']) + pd.to_timedelta(d)
    T['sortie_t'] = pd.DatetimeIndex(T['sortie_t']) + pd.to_timedelta(d)
    return T


def note_pf(T, refs, jours_test, regles):
    fin = str(pd.bdate_range('2030-01-07', periods=len(np.unique(jours_test)))[-1].date())
    kw = dict(risque_usd=OPT.risque, instrument='micro', n_sim=OPT.nsim, debut='2030-01-07', fin=fin)
    out = {}
    if len(T):
        r = PF.monte_carlo(compacter(T, jours_test), regles, **kw)
        out.update(p_reussite=r['p_reussite'], p_payout=r['p_1er_payout'], ve=r['valeur_esperee_usd'])
    else:
        out.update(p_reussite=0.0, p_payout=0.0, ve=np.nan)
    rr = [compacter(t, jours_test) for t in refs if len(t)]
    if rr:
        a = PF.analyse_reference(rr, regles, **kw)
        out.update(p_reussite_hasard=a.get('p_reussite', np.nan), ve_hasard=a.get('valeur_esperee_usd', np.nan))
    return out


# ════════════════════════════════════ résumé ════════════════════════════════════
def r_jour(T):
    if not len(T):
        return pd.Series(dtype=float)
    return T.assign(j=jour_cme(pd.DatetimeIndex(T['entree_t']))).groupby('j')['r'].sum()


def resume_variante(res, jours_test, regles):
    T, refs, IS = res['oos'], res['refs'], res['IS']
    m = M.metriques(T, n_boot=500) if len(T) else dict(n=0)
    ref_moy = [t['r'].mean() for t in refs if len(t)]
    p_h = float((1 + sum(v >= m.get('r_moyen', np.nan) for v in ref_moy)) / (1 + len(ref_moy))) if ref_moy and m['n'] else np.nan
    pf = note_pf(T, refs, jours_test, regles)
    return dict(partition=res['P'], t_min=res['tmin'], n_etats=len(E.PARTITIONS[res['P']][1]),
                n_oos=m['n'], r_oos=m.get('r_moyen', np.nan),
                r_oos_ic=('[%+.2f ; %+.2f]' % m['r_ic95']) if m['n'] else '',
                pf_oos=m.get('pf', np.nan), net_oos=m.get('gain_net_usd', 0.0),
                somme_r_oos=float(T['r'].sum()) if len(T) else 0.0,
                n_dev=len(IS), r_dev=float(IS['r'].mean()) if len(IS) else np.nan,
                r_hasard=float(np.mean(ref_moy)) if ref_moy else np.nan, p_hasard=p_h,
                etats_trades_pct=float((res['choix']['setup'] != 'PAS DE TRADE').mean()), **pf)


def diff_bootstrap(Ta, Tb, jours_test, n=4000, graine=0):
    """Différence de somme de R par jour de test (a - b), bootstrap par jour : moyenne et IC95."""
    jt = np.unique(jours_test)
    a = r_jour(Ta).reindex(jt, fill_value=0.0).to_numpy()
    b = r_jour(Tb).reindex(jt, fill_value=0.0).to_numpy()
    d = a - b
    rng = np.random.default_rng(graine)
    bm = d[rng.integers(0, len(d), size=(n, len(d)))].mean(1)
    return float(d.mean()), float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5)), float((bm <= 0).mean())


def table_finale(P, tmin):
    """Aiguillage appris sur TOUT le développement (table état -> setup à livrer)."""
    ch = choisir(BAL, P, tmin, OPT.nmin)
    rows = []
    st_all = stats_groupes(BAL, [P])
    for e, nom in enumerate(E.PARTITIONS[P][1]):
        c = ch[e]
        nb = sum(int((s['lab'][P] == e).sum()) for s in SER)
        rows.append(dict(partition=P, t_min=tmin, etat=nom, barres=nb,
                         setup=c['setup'] if c else 'PAS DE TRADE', n_dev=c['n'] if c else 0,
                         r_dev=round(c['moy'], 3) if c else np.nan, t_dev=round(c['t'], 2) if c else np.nan))
    return pd.DataFrame(rows)


def fmt(x, k=3, pct=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return '—'
    return ('%.1f %%' % (100 * x)) if pct else (('%+.' + str(k) + 'f') % x)


# ════════════════════════════════════ principal ════════════════════════════════════
def main():
    global SER, BAL, PLIS, OPT
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    ap.add_argument('--nmin', type=int, default=10, help='trades minimum par (état, setup) en apprentissage')
    ap.add_argument('--nref', type=int, default=20, help='tirages au hasard par variante')
    ap.add_argument('--nsim', type=int, default=2000)
    ap.add_argument('--risque', type=float, default=200.0, help='risque $ par trade (taille en micros)')
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--registre', action='store_true')
    ap.add_argument('--note', default='', help='texte ajouté au verdict des lignes du registre')
    OPT = ap.parse_args()
    t0 = time.time()
    src = OPT.source or os.environ.get('REG_SOURCE', donnees.SOURCE_DEFAUT)
    ech = 'dev_dataset' if src == 'dataset' else 'dev_cache'
    SER = preparer(src)
    print('séries :', [(s['nom'], len(s['d'])) for s in SER], '%.0f s' % (time.time() - t0), flush=True)

    # 1. balayage
    cat = SU.catalogue()
    ctx = mp.get_context('fork')
    morceaux = [cat[i::OPT.jobs * 4] for i in range(OPT.jobs * 4)]
    with ctx.Pool(OPT.jobs) as pool:
        parts = pool.map(_balayer, morceaux)
    BAL = pd.concat([p for p in parts if p is not None], ignore_index=True)
    BAL.to_pickle(os.path.join(ICI, 'balayage_trades.pkl'))
    st = stats_groupes(BAL, ['setup']).sort_values('t', ascending=False)
    st.to_csv(os.path.join(ICI, 'balayage_setups.csv'), index=False, float_format='%.4f')
    print('balayage : %d setups, %d trades, %.0f s' % (len(cat), len(BAL), time.time() - t0), flush=True)

    # 2. walk-forward
    PLIS = plis_communs(SER)
    jours_test = np.concatenate([b for _, b in PLIS])
    print('plis :', [(str(pd.Timestamp(a[0]).date()), str(pd.Timestamp(b[0]).date()), str(pd.Timestamp(b[-1]).date()), len(b))
                     for a, b in PLIS], flush=True)
    variantes = [(P, t) for P in E.PARTITIONS for t in T_MINS]
    with ctx.Pool(OPT.jobs) as pool:
        RES = pool.map(evaluer, variantes)
    print('walk-forward : %.0f s' % (time.time() - t0), flush=True)
    regles = PF.charge_regles()[VARIANTE_PF]
    lignes = []
    for res in RES:
        lignes.append(resume_variante(res, jours_test, regles))
        print('  %-14s T_MIN %.1f : n %3d  R oos %s  R dev %s  hasard %s  p %.2f  P(réussite) %s / hasard %s'
              % (res['P'], res['tmin'], lignes[-1]['n_oos'], fmt(lignes[-1]['r_oos']), fmt(lignes[-1]['r_dev']),
                 fmt(lignes[-1]['r_hasard']), lignes[-1]['p_hasard'] if lignes[-1]['p_hasard'] == lignes[-1]['p_hasard'] else -1,
                 fmt(lignes[-1].get('p_reussite'), pct=True), fmt(lignes[-1].get('p_reussite_hasard'), pct=True)), flush=True)
    TAB = pd.DataFrame(lignes)
    TAB.to_csv(os.path.join(ICI, 'walk_forward_variantes.csv'), index=False, float_format='%.4f')
    pd.concat([r['choix'].assign(partition=r['P'], t_min=r['tmin']) for r in RES]).to_csv(
        os.path.join(ICI, 'choix_par_pli.csv'), index=False, float_format='%.3f')
    pd.concat([r['oos'].assign(partition=r['P'], t_min=r['tmin']) for r in RES]).to_csv(
        os.path.join(ICI, 'trades_oos_toutes_variantes.csv'), index=False, float_format='%.4f')
    with open(os.path.join(ICI, 'resultats_bruts.pkl'), 'wb') as fh:
        pickle.dump(dict(TAB=TAB, RES=[{k: v for k, v in r.items() if k != 'refs'} for r in RES], PLIS=PLIS), fh)

    # 3. comparaisons aiguillage vs unique (même T_MIN), tables finales
    comp = []
    byk = {(r['P'], r['tmin']): r for r in RES}
    for (P, t), r in byk.items():
        if P == 'UNIQUE':
            continue
        d, lo, hi, p = diff_bootstrap(r['oos'], byk[('UNIQUE', t)]['oos'], jours_test)
        comp.append(dict(partition=P, t_min=t, diff_r_par_jour=d, ic_bas=lo, ic_haut=hi, p_unilat=p))
    COMP = pd.DataFrame(comp)
    COMP.to_csv(os.path.join(ICI, 'aiguillage_vs_unique.csv'), index=False, float_format='%.4f')
    tables = pd.concat([table_finale(P, t) for P in E.PARTITIONS for t in T_MINS], ignore_index=True)
    tables.to_csv(os.path.join(ICI, 'table_etat_setup.csv'), index=False)

    ecrire_resultats(TAB, COMP, tables, byk, jours_test, src, time.time() - t0)
    if OPT.registre:
        inscrire(TAB, byk, ech)
    print('fini en %.0f s' % (time.time() - t0))


def ecrire_resultats(TAB, COMP, tables, byk, jours_test, src, duree):
    cols = ['partition', 't_min', 'n_etats', 'n_oos', 'r_oos', 'r_oos_ic', 'pf_oos', 'r_dev', 'r_hasard', 'p_hasard',
            'p_reussite', 'p_reussite_hasard', 've', 've_hasard', 'etats_trades_pct']
    T = TAB[cols].sort_values(['t_min', 'r_oos'], ascending=[True, False])
    try:
        md = T.to_markdown(index=False, floatfmt='.3f')
    except ImportError:
        md = T.to_string(index=False, float_format=lambda v: '%.3f' % v)
    with open(os.path.join(ICI, 'resultats_auto.md'), 'w') as fh:
        fh.write('# Résultats automatiques (source %s, %d jours de test, %.0f s)\n\n' % (src, len(np.unique(jours_test)), duree))
        fh.write(md + '\n\n## Aiguillage - unique (somme de R par jour de test)\n\n')
        fh.write(COMP.to_string(index=False, float_format=lambda v: '%.3f' % v) + '\n\n## Tables état -> setup (tout le développement)\n\n')
        fh.write(tables.to_string(index=False) + '\n')


def inscrire(TAB, byk, ech):
    """Une ligne par recette retenue : meilleur aiguillage (R hors échantillon), COMPOSITE (partition principale
    définie à l'avance) et meilleur setup unique ; leurs trades hors échantillon sont écrits par ajouter_test."""
    nvar = len(TAB)
    a = TAB[TAB.partition != 'UNIQUE'].sort_values('r_oos', ascending=False).iloc[0]
    u = TAB[TAB.partition == 'UNIQUE'].sort_values('r_oos', ascending=False).iloc[0]
    c = TAB[(TAB.partition == 'COMPOSITE')].sort_values('r_oos', ascending=False).iloc[0]
    for row, fam in ((a, 'aiguillage (meilleur hors échantillon)'), (c, 'aiguillage COMPOSITE'), (u, 'setup unique')):
        r = byk[(row.partition, row.t_min)]
        T = r['oos'][M.COLONNES_TRADES].copy() if len(r['oos']) else r['oos']
        verdict = ('walk-forward ancré %d plis : R hors éch. %+.3f (dév. %+.3f), hasard %+.3f p=%.2f ; P(réussite) %.1f %% '
                   'vs hasard %.1f %% ; VE %+.0f $ ; %d variantes d\'aiguillage comparées -> non concluant (2 mois)'
                   % (K, row.r_oos, row.r_dev, row.r_hasard, row.p_hasard, 100 * row.p_reussite,
                      100 * row.get('p_reussite_hasard', np.nan), row.ve, nvar)) + (' ; ' + OPT.note if OPT.note else '')
        RG.ajouter_test(dict(agent='regimes', famille=fam,
                             recette='%s, T_MIN %.1f (état -> setup appris sur le passé ; risque %d $/trade)'
                                     % (row.partition, row.t_min, OPT.risque),
                             marche='MES+MNQ', ut_signal='15', ut_entree='15', echantillon=ech,
                             n_variantes_testees=nvar * len(SU.catalogue()), p_tradeify=row.p_reussite,
                             p_ref_hasard=row.get('p_reussite_hasard', np.nan), verdict=verdict, trades=T),
                        prefixe='REG')


if __name__ == '__main__':
    main()
