"""Analyse du balayage E2M : ce que l'affinage apporte, classement, contrôle du biais de sélection (White),
walk-forward, puis pour les 3 meilleures recettes : référence au hasard, simulateur propfirm Tradeify
Select Flex, lignes du registre.

    ~/venv-quant/bin/python analyse.py                 # tableaux -> resultats/synthese_auto.md
    ~/venv-quant/bin/python analyse.py --registre      # + hasard, propfirm et lignes du registre
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI, os.path.join(ICI, '..', '..', 'propfirm')]
import affinage as A   # noqa: E402
import balayage as B   # noqa: E402
import donnees as D    # noqa: E402

M = A.M
RES = B.SORTIE
ECHANTILLON = 'dev_cache' if D.SOURCE == 'cache' else 'dev_dataset'
NMIN = 8 if D.SOURCE == 'cache' else 100           # trades minimum pour être classé
VARIANTE = 'tradeify_50k_select_flex'


def md(df, flt='%.3f'):
    """DataFrame -> tableau Markdown (sans dépendance)."""
    cols = list(df.columns)
    out = ['| ' + ' | '.join(map(str, cols)) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        cel = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cel.append('' if v != v else (flt % v))
            else:
                cel.append(str(v))
        out.append('| ' + ' | '.join(cel) + ' |')
    return '\n'.join(out)


def charger_balayages():
    dfs = [pd.read_csv(f) for f in sorted(glob.glob(os.path.join(RES, 'balayage_*.csv')))]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def charger_trades(marche, us, ux):
    f = os.path.join(RES, 'trades_%s_%s_%s.pkl' % (marche, us, ux))
    return pickle.load(open(f, 'rb')) if os.path.exists(f) else pd.DataFrame()


# ─────────────────────────────── ce que l'affinage apporte ───────────────────────────────
def apport(bal):
    """Chaque variante affinée comparée à la variante DIRECTE de même famille / filtre / objectif :
    - réf. 15m  = direct + stop 2 ATR S (« entrer à l'ouverture de la bougie S suivante », gestion classique)
    - réf. même stop = direct + même stop (isole l'effet du moment d'entrée)."""
    cle = ['marche', 'us', 'ux', 'famille', 'filtre', 'obj']
    d = bal[bal.entree == 'direct']
    ref15 = d[d.stop == 'atrS2'].set_index(cle)[['n', 'r_moyen', 'r_fixe', 'net_fixe']].add_suffix('_ref15')
    refst = d.set_index(cle + ['stop'])[['n', 'r_moyen', 'r_fixe']].add_suffix('_refst')
    x = bal.join(ref15, on=cle).join(refst, on=cle + ['stop'])
    x['taux_vs_ref'] = x['n'] / x['n_ref15'].replace(0, np.nan)
    x['d_rfixe_vs_ref15'] = x['r_fixe'] - x['r_fixe_ref15']
    x['d_rfixe_vs_memestop'] = x['r_fixe'] - x['r_fixe_refst']
    x['d_netfixe_vs_ref15'] = x['net_fixe'] - x['net_fixe_ref15']
    return x


def table_entrees(x, marche, us, ux):
    s = x[(x.marche == marche) & (x.us == us) & (x.ux == ux)]
    g = s.groupby(['entree', 'W_min'])
    t = pd.DataFrame({
        'variantes': g.size(),
        'taux_trades_vs_direct': g['taux_vs_ref'].mean(),
        'gain_entree_pts': g['gain_entree_pts'].mean(),
        'gain_entree_ATR_S': g['gain_entree_atrS'].mean(),
        'stop_pts': g['stop_pts'].mean(),
        'micros_a_200$': g['micros'].mean(),
        'cout_R': g['cout_R'].mean(),
        'R_moyen_1ct': g['r_moyen'].mean(),
        'R_risque_fixe': g['r_fixe'].mean(),
        'dR_vs_ref15': g['d_rfixe_vs_ref15'].mean(),
        'part_variantes_mieux_que_ref15': g['d_rfixe_vs_ref15'].apply(lambda v: (v > 0).mean()),
    }).reset_index()
    return t


def table_stops(x, marche, us, ux):
    s = x[(x.marche == marche) & (x.us == us) & (x.ux == ux)]
    g = s.groupby(['stop'])
    return pd.DataFrame({'variantes': g.size(), 'stop_pts': g['stop_pts'].mean(), 'micros_a_200$': g['micros'].mean(),
                         'cout_R': g['cout_R'].mean(), 'pct_gagnants': g['pct_g'].mean(),
                         'R_risque_fixe': g['r_fixe'].mean()}).reset_index()


def manques(marche, us, ux, bal):
    """Au niveau des signaux : R (réf. 15m) des signaux que l'affinage PREND vs ceux qu'il MANQUE."""
    T = charger_trades(marche, us, ux)
    if not len(T):
        return pd.DataFrame()
    T = T.copy()
    p = T['vid'].str.split('|', expand=True)
    T['fam'], T['filt'], T['ent'], T['W'], T['stop'], T['obj'] = p[0], p[1], p[2], p[3], p[4], p[5]
    k3 = ['fam', 'filt', 'obj']
    ref = T[(T.ent == 'direct') & (T.stop == 'atrS2')][k3 + ['evt', 'r']].drop_duplicates(k3 + ['evt'])
    if not len(ref):
        return pd.DataFrame()
    tot = ref.groupby(k3)['r'].agg(['sum', 'size']).rename(columns={'sum': 'S_ref', 'size': 'N_ref'})
    var = T[T.ent != 'direct'][k3 + ['ent', 'W', 'stop', 'evt']].drop_duplicates()
    pr = var.merge(ref.rename(columns={'r': 'r_ref'}), on=k3 + ['evt'], how='inner')
    g6 = k3 + ['ent', 'W', 'stop']
    pg = pr.groupby(g6)['r_ref'].agg(['sum', 'size']).rename(columns={'sum': 'S_p', 'size': 'N_p'}).reset_index()
    pg = pg.join(tot, on=k3)
    pg['r_ref_pris'] = pg.S_p / pg.N_p
    pg['N_m'] = pg.N_ref - pg.N_p
    pg['r_ref_manques'] = (pg.S_ref - pg.S_p) / pg.N_m.replace(0, np.nan)
    pg['W_min'] = pg['W'].astype(int)
    g = pg.groupby(['ent', 'W_min'])
    out = pd.DataFrame({'R_ref15_signaux_pris': g['r_ref_pris'].mean(), 'R_ref15_signaux_manques': g['r_ref_manques'].mean(),
                        'n_pris': g['N_p'].sum(), 'n_manques': g['N_m'].sum()}).reset_index()
    return out.rename(columns={'ent': 'entree'})


# ─────────────────────────────── biais de sélection, walk-forward ───────────────────────────────
def jours_cme(t):
    return M._jour_cme_serie(t)


def matrice_jours(T, vids):
    """Somme quotidienne des R à risque fixe (pnl_fixe / 200 $) par variante (lignes = jours CME)."""
    T = T[T.vid.isin(vids)].copy()
    nf, pfx = A.a_risque_fixe(T)
    T['rf'] = pfx / A.RISQUE_FIXE
    T['jour'] = jours_cme(T['sortie_t'])
    X = T.pivot_table(index='jour', columns='vid', values='rf', aggfunc='sum').fillna(0.0)
    tous = pd.bdate_range(X.index.min(), X.index.max())
    return X.reindex(tous, fill_value=0.0)


def white(X, n_boot=2000, bloc=3, graine=0):
    """Reality check de White (bootstrap par blocs de jours) : p-valeur du meilleur R quotidien moyen."""
    if X.shape[0] < 3:
        return np.nan
    rng = np.random.default_rng(graine)
    mu = X.mean(0).to_numpy()
    V = X.to_numpy() - mu
    nj = len(X)
    stat = np.sqrt(nj) * mu.max()
    cnt = 0
    for _ in range(n_boot):
        deb = rng.integers(0, nj, size=int(np.ceil(nj / bloc)))
        idx = (deb[:, None] + np.arange(bloc)[None, :]).ravel()[:nj] % nj
        cnt += np.sqrt(nj) * V[idx].mean(0).max() >= stat
    return (1 + cnt) / (1 + n_boot)


def walk_forward(T, bal_s, k=None, ratio=None):
    """Sélection sur l'apprentissage (meilleur R à risque fixe, n >= NMIN/2), évaluation sur le bloc suivant."""
    jours = np.sort(jours_cme(T['entree_t']).unique())
    nj = len(jours)
    if k is None:
        k, ratio = (5, 3) if nj >= 40 else (2, 1)
    nb = ratio + k
    bornes = np.linspace(0, nj, nb + 1).round().astype(int)
    blocs = [jours[bornes[q]:bornes[q + 1]] for q in range(nb)]
    T = T.copy()
    nf, pfx = A.a_risque_fixe(T)
    T['rf'] = pfx / A.RISQUE_FIXE
    T['ok'] = nf > 0
    T['jour'] = jours_cme(T['entree_t']).to_numpy()
    oos = []
    for p in range(k):
        app = np.concatenate(blocs[p:p + ratio]); tst = blocs[p + ratio]
        a = T[T.jour.isin(app) & T.ok].groupby('vid')['rf'].agg(['mean', 'size'])
        a = a[a['size'] >= max(3, NMIN // 2)]
        if not len(a):
            continue
        best = a['mean'].idxmax()
        t = T[T.jour.isin(tst) & T.ok & (T.vid == best)]
        oos.append(dict(pli=p, choisi=best, r_app=a.loc[best, 'mean'], n_test=len(t),
                        r_test=t['rf'].mean() if len(t) else np.nan))
    return pd.DataFrame(oos)


# ─────────────────────────────── propfirm ───────────────────────────────
def propfirm(T, regles, risques=(100, 200, 300), n_sim=1000):
    import simulateur as SIM
    best = None
    for rq in risques:
        if not (T['risque_usd'] <= rq).any():
            continue                      # aucun micro possible à ce risque
        r = SIM.monte_carlo(T, regles, risque_usd=rq, n_sim=n_sim, graine=1)
        if r.get('taille_autorisee') and (best is None or r['valeur_esperee_usd'] > best['valeur_esperee_usd']):
            best = dict(r, risque=rq)
    return best


def propfirm_ref(trs, regles, risque, n_sim=1000):
    import simulateur as SIM
    trs = [t for t in trs if len(t) and (t['risque_usd'] <= risque).any()]
    return SIM.analyse_reference(trs, regles, risque_usd=risque, n_sim=n_sim) if trs else {}


def decrire(vid, us, ux):
    fam, filt, ent, W, stop, obj = vid.split('|')
    nom_ent = {'direct': 'entrée directe (ouverture de la bougie %sm suivante)' % us,
               'hei_flip': 'flip Heishinator %sm' % ux, 'hei_aligne': 'Heishinator %sm dans le sens' % ux,
               'cassure': 'clôture %sm au-delà du plus haut/bas précédent' % ux, 'sigX': 'Signator %sm' % ux,
               'rejet_ema': 'rejet de l\'EMA50 %sm' % ux, 'lim_milieu': 'limite au milieu de la bougie %sm' % us,
               'lim_ema50': 'limite sur l\'EMA50 %sm' % ux, 'lim_atr': 'limite à clôture %sm - 0,25 ATR' % us}[ent]
    nom_st = {'swing': 'stop swing %sm (5 barres)' % ux, 'bougieS': 'stop extrême bougie %sm' % us,
              'atrS2': 'stop 2 ATR %sm' % us, 'atrX2': 'stop 2 ATR %sm' % ux}[stop]
    nom_ob = {'R2': 'objectif 2R', 'R3': 'objectif 3R', 'heiS': 'sortie flip Heishinator %sm' % us}.get(obj, obj)
    f = fam + (' + TREND au-dessus' if filt == 'trend' else '')
    w = '' if ent == 'direct' else ', fenêtre %s min' % W
    return '%s %sm ; %s%s ; %s ; %s' % (f, us, nom_ent, w, nom_st, nom_ob)


def main(registre=False):
    bal = charger_balayages()
    if not len(bal):
        print('aucun balayage'); return
    n_var = len(bal)
    x = apport(bal)
    x.to_csv(os.path.join(RES, 'apport_par_variante.csv'), index=False)
    L = ['# Synthèse automatique E2M (%s, %d variantes au total)\n' % (ECHANTILLON, n_var),
         'Risque fixe = %d $ par trade, micros = floor(%d / risque d\'un micro), plafonné à %d.\n'
         % (A.RISQUE_FIXE, A.RISQUE_FIXE, A.MICROS_MAX)]
    synth = {}
    for (m, us, ux), _ in bal.groupby(['marche', 'us', 'ux']):
        meta_f = os.path.join(RES, 'meta_%s_%s_%s.pkl' % (m, us, ux))
        meta = pickle.load(open(meta_f, 'rb')) if os.path.exists(meta_f) else {}
        L.append('\n## %s — signal %sm -> entrée %sm (%s -> %s)\n' % (m, us, ux, meta.get('debut', '?')[:16],
                                                                       meta.get('fin', '?')[:16]))
        te = table_entrees(x, m, us, ux)
        mq = manques(m, us, ux, bal)
        if len(mq):
            te = te.merge(mq, on=['entree', 'W_min'], how='left')
        L.append(md(te))
        L.append('\n\nPar stop :\n')
        L.append(md(table_stops(x, m, us, ux)))
        s = x[(x.marche == m) & (x.us == us) & (x.ux == ux)]
        top = s[s.n_fixe >= NMIN].sort_values('r_fixe', ascending=False).head(8)
        L.append('\n\nMeilleures variantes (n >= %d) :\n' % NMIN)
        L.append(md(top[['vid', 'n', 'pct_g', 'r_moyen', 'r_fixe', 'net_fixe', 'micros', 'cout_R', 'r_fixe_ref15']]))
        T = charger_trades(m, us, ux)
        if len(T):
            X = matrice_jours(T, s.vid)
            pw = white(X)
            wf = walk_forward(T, s)
            L.append('\n\nWhite reality check (%d variantes, %d jours) : p = %.3f\n' % (X.shape[1], X.shape[0], pw))
            if len(wf):
                L.append('\nWalk-forward (sélection sur l\'apprentissage, test sur le bloc suivant) :\n')
                L.append(md(wf))
            synth['%s_%s_%s' % (m, us, ux)] = dict(white=pw, n_jours=int(X.shape[0]),
                                                  wf_r_test=float(wf['r_test'].mean()) if len(wf) else None)
        synth.setdefault('%s_%s_%s' % (m, us, ux), {})['entrees'] = te.to_dict('records')
    open(os.path.join(RES, 'synthese_auto.md'), 'w').write('\n'.join(L) + '\n')
    json.dump(synth, open(os.path.join(RES, 'synthese_auto.json'), 'w'), default=float, indent=1)
    print('synthèse écrite (%d variantes)' % n_var)
    if registre:
        recettes(x, n_var)


def recettes(x, n_var, n_top=3, n_hasard=200):
    """3 meilleures recettes affinées 15m -> 2m (familles / entrées distinctes) + leur référence directe."""
    import simulateur as SIM
    import registre as RG
    regles = SIM.charge_regles()[VARIANTE]
    s = x[(x.us == 15) & (x.ux == 2) & (x.entree != 'direct') & (x.n_fixe >= NMIN)]
    s = s.sort_values('r_fixe', ascending=False)
    choix, vus = [], set()
    for _, r in s.iterrows():
        k = (r.famille, r.entree)
        if k in vus:
            continue
        vus.add(k); choix.append(r)
        if len(choix) >= n_top:
            break
    lignes = []
    for r in choix:
        m = r.marche
        ctx = B.preparer(m, 15, 2)
        fam, filt, ent, W, stop, obj = r.vid.split('|')
        Wb = max(1, int(round(int(W) / ctx.bx.ut)))
        L_, S_ = A.signaux_S(ctx.dfS, fam, '' if filt == '-' else filt)
        ev = ctx.evenements(L_, S_)
        res = {}
        for nom, (e_, w_, st_) in dict(recette=(ent, Wb, stop), ref15=('direct', 1, 'atrS2')).items():
            T, cons, av, g = A.lancer(ctx, ev, e_, w_, st_, obj, sortie_S=ctx.sortie_heiS())
            T = A.enrichir(ctx, ev, T)
            Tm = T[M.COLONNES_TRADES]
            mt = M.metriques(Tm)
            R, trs = A.hasard(ctx, cons, e_, av, g, n_tirages=n_hasard, graine=7, garder=True)
            p_r = M.p_hasard(R, mt['r_moyen'])
            p_f = M.p_hasard(R, r.r_fixe if nom == 'recette' else r.r_fixe_ref15, col='r_fixe')
            pf = propfirm(Tm, regles)
            ref = propfirm_ref(trs[:20], regles, pf['risque']) if pf else {}
            res[nom] = dict(T=T, m=mt, p_r=p_r, p_f=p_f, pf=pf, ref=ref, R=R)
        rec = res['recette']; rf = res['ref15']
        verdict = ('%s ; n=%d (%s) ; R risque fixe %+.2f vs réf. directe %+.2f ; p hasard (R) %.2f ; '
                   'Tradeify P %.2f (risque %d $) vs hasard %.2f vs réf. directe %.2f ; données ~%d jours : '
                   'NON CONCLUANT, à relancer sur le DATASET'
                   % (r.vid, rec['m']['n'], m, r.r_fixe, r.r_fixe_ref15 if r.r_fixe_ref15 == r.r_fixe_ref15 else np.nan,
                      rec['p_r'], rec['pf']['p_reussite'] if rec['pf'] else np.nan, rec['pf']['risque'] if rec['pf'] else 0,
                      rec['ref'].get('p_reussite', np.nan), rf['pf']['p_reussite'] if rf['pf'] else np.nan,
                      len(np.unique(jours_cme(rec['T']['entree_t'])))))
        T_reg = rec['T'][M.COLONNES_TRADES]
        id_ = RG.ajouter_test(dict(agent='E2M', famille='Entrée 15m->2m', recette=decrire(r.vid, 15, 2),
                                   marche=m, ut_signal='15', ut_entree='2', echantillon=ECHANTILLON,
                                   n_variantes_testees=n_var,
                                   p_tradeify=rec['pf']['p_reussite'] if rec['pf'] else None,
                                   p_ref_hasard=rec['ref'].get('p_reussite'), verdict=verdict, trades=T_reg),
                              prefixe='E2M')
        lignes.append(dict(id=id_, vid=r.vid, marche=m, n=rec['m']['n'], r_moyen=rec['m']['r_moyen'],
                           r_fixe=r.r_fixe, r_fixe_ref15=r.r_fixe_ref15, p_hasard_r=rec['p_r'],
                           p_hasard_rfixe=rec['p_f'],
                           P_tradeify=rec['pf']['p_reussite'] if rec['pf'] else np.nan,
                           VE=rec['pf']['valeur_esperee_usd'] if rec['pf'] else np.nan,
                           risque=rec['pf']['risque'] if rec['pf'] else np.nan,
                           P_hasard=rec['ref'].get('p_reussite', np.nan),
                           P_ref15=rf['pf']['p_reussite'] if rf['pf'] else np.nan,
                           VE_ref15=rf['pf']['valeur_esperee_usd'] if rf['pf'] else np.nan,
                           n_ref15=rf['m']['n'], r_moyen_ref15=rf['m']['r_moyen']))
        print(lignes[-1], flush=True)
    t = pd.DataFrame(lignes)
    t.to_csv(os.path.join(RES, 'recettes_retenues.csv'), index=False)
    with open(os.path.join(RES, 'synthese_auto.md'), 'a') as fh:
        fh.write('\n## Recettes retenues (registre) et Tradeify Select Flex\n\n' + md(t) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--registre', action='store_true')
    a = ap.parse_args()
    main(a.registre)
