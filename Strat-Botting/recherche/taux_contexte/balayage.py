"""Étape 2 : balayage des CONTEXTES pour les géométries à fort taux de gagnants (stop 1,5 ATR ; objectif
0,5 / 0,75 / 1 R), tous déclencheurs, chaque contexte avec SON placebo (même géométrie, même heure, même sens,
même contexte), puis correction du biais de sélection (test du maximum sur les tirages placebo) et
walk-forward (choix du contexte sur le passé, test sur le bloc suivant).

    ~/venv-quant/bin/python balayage.py [--source dataset] [--n 500] [--proc 8]

Sorties (sorties/) : balayage_contextes.csv (une ligne par variante), stabilite_mois.csv,
walk_forward.csv + trades_wf_oos.csv, balayage.pkl (trades réels + placebo compacts de chaque variante).
"""
import argparse
import multiprocessing as mp
import os
import pickle
import time

import numpy as np
import pandas as pd

import commun as C
import moteur as M

ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, 'sorties')
GEOMS = ['A15R05', 'A15R075', 'A15R1']
PP = None


def variantes():
    """Liste (nom, geom, [(partition, état), ...]). Contextes seuls, puis croisés avec la nuit."""
    v = []
    for g in GEOMS:
        v.append(('tout|' + g, g, []))
        for part, (_, lab) in C.PARTITIONS.items():
            for e in lab:
                v.append(('%s=%s|%s' % (part, e, g), g, [(part, e)]))
        for part, (_, lab) in C.PARTITIONS.items():
            if part == 'seance':
                continue
            for e in lab:
                v.append(('seance=0+%s=%s|%s' % (part, e, g), g, [('seance', 0), (part, e)]))
    return v


def masques(P, conds):
    X = P['X']
    mL = np.ones(len(X), bool); mS = np.ones(len(X), bool)
    for part, e in conds:
        mL &= C.masque(X, part, e, 1)
        mS &= C.masque(X, part, e, -1)
    return mL, mS


def tourner(args):
    q, (nom, geom, conds), n, garder = args
    trs, comp, full = [], [], [[] for _ in range(n)] if garder else None
    for s, P in enumerate(PP):
        G = C.gestion(geom, P['instrument'])
        mL, mS = masques(P, conds)
        T = C.backtest_masque(P, G, mL, mS)
        trs.append(T)
        pl = C.placebo(P, G, mL, mS, n, graine=10_000 * q + s)
        for k, t in enumerate(pl):
            comp.append(C.compact(t, k).assign(serie=np.int8(s)))
            if garder:
                full[k].append(t)
    T = pd.concat(trs).sort_values('entree_t').reset_index(drop=True)
    pc = pd.concat(comp, ignore_index=True)
    if garder:
        full = [pd.concat(x).sort_values('entree_t').reset_index(drop=True) for x in full]
    return nom, T, pc, full


def stats(nom, geom, conds, T, pc, n):
    g = (T['pnl_usd'] > 0).to_numpy()
    by = pc.groupby('tirage')
    wr_pl = by['g'].mean().reindex(range(n)).to_numpy(float)
    r_pl = by['r'].mean().reindex(range(n)).to_numpy(float)
    m = M.metriques(T, n_boot=500) if len(T) else dict(n=0)
    wr = float(g.mean()) if len(T) else np.nan
    L = dict(variante=nom, geometrie=geom, contexte=' + '.join('%s=%s' % c for c in conds) or 'tout',
             n=len(T), pct_gagnants=wr, pct_placebo=float(np.nanmean(wr_pl)),
             ecart_pts=100 * (wr - np.nanmean(wr_pl)) if len(T) else np.nan,
             p_taux=float((1 + np.sum(wr_pl >= wr)) / (1 + np.isfinite(wr_pl).sum())) if len(T) else np.nan,
             z_taux=(wr - np.nanmean(wr_pl)) / np.nanstd(wr_pl) if len(T) and np.nanstd(wr_pl) > 0 else np.nan,
             r_moyen=m.get('r_moyen', np.nan), r_placebo=float(np.nanmean(r_pl)),
             p_r=float((1 + np.sum(r_pl >= m['r_moyen'])) / (1 + np.isfinite(r_pl).sum())) if len(T) else np.nan,
             z_r=(m['r_moyen'] - np.nanmean(r_pl)) / np.nanstd(r_pl) if len(T) and np.nanstd(r_pl) > 0 else np.nan,
             pf=m.get('pf', np.nan), net_usd=m.get('gain_net_usd', np.nan), ic95=m.get('r_ic95'))
    # stabilité par mois (écart de taux réel - placebo du même mois)
    mo = []
    if len(T):
        tm = pd.DatetimeIndex(T['entree_t']).tz_convert('Europe/Paris').strftime('%Y%m').astype(int).to_numpy()
        wpm = pc.groupby('mois')['g'].mean()
        for mm in sorted(set(tm)):
            k = tm == mm
            if k.sum() >= 8:
                mo.append(dict(variante=nom, mois=mm, n=int(k.sum()), pct_gagnants=float(g[k].mean()),
                               pct_placebo=float(wpm.get(mm, np.nan)),
                               ecart_pts=100 * (g[k].mean() - wpm.get(mm, np.nan)),
                               r_moyen=float(T['r'].to_numpy()[k].mean())))
    if mo:
        e = np.array([x['ecart_pts'] for x in mo])
        L['mois_n'] = len(mo); L['mois_positifs'] = int((e > 0).sum()); L['ecart_min_mois'] = float(e.min())
    else:
        L['mois_n'] = 0; L['mois_positifs'] = 0; L['ecart_min_mois'] = np.nan
    # par série
    for q, P in enumerate(PP):
        k = (T['serie'] == P['nom']).to_numpy() if len(T) else np.zeros(0, bool)
        L['n_%s' % P['nom'].split('_')[0]] = int(k.sum())
        L['ecart_%s' % P['nom'].split('_')[0]] = 100 * (g[k].mean() - pc.loc[pc.serie == q, 'g'].mean()) if k.sum() else np.nan
    return L, mo


def test_maximum(R, PCS, n, col='g'):
    """p ajustée « maxT » (Romano-Wolf en une étape) : pour chaque tirage k, max sur les variantes du z placebo."""
    zs = []
    for nom in R['variante']:
        pc = PCS[nom]
        if not len(pc):
            zs.append(np.full(n, np.nan)); continue
        x = pc.groupby('tirage')[col].mean().reindex(range(n)).to_numpy(float)
        zs.append((x - np.nanmean(x)) / (np.nanstd(x) or np.nan))
    Z = np.vstack(zs)
    mx = np.nanmax(Z, axis=0)
    zc = 'z_taux' if col == 'g' else 'z_r'
    return np.array([(1 + np.sum(mx >= z)) / (1 + n) if np.isfinite(z) else np.nan for z in R[zc]])


# ─────────────────────────────────────────── walk-forward
def blocs_jours(TR, PCS, nb=8):
    jours = set()
    for T in TR.values():
        jours |= set(C.jour_cme_trades(T).tolist())
    uj = np.array(sorted(jours))
    b = np.linspace(0, len(uj), nb + 1).round().astype(int)
    return [uj[b[q]:b[q + 1]] for q in range(nb)]


def walk_forward(R, TR, PCS, n, nmin=20, ratio=3):
    blocs = blocs_jours(TR, PCS)
    JT = {k: C.jour_cme_trades(T) for k, T in TR.items()}
    lignes, oos, oos_pl = [], [], [[] for _ in range(n)]
    for p in range(len(blocs) - ratio):
        app = np.concatenate(blocs[:p + ratio]); test = blocs[p + ratio]
        best, bsc = None, -np.inf
        for nom in R['variante']:
            T = TR[nom]
            if not len(T):
                continue
            k = np.isin(JT[nom], app)
            if k.sum() < nmin:
                continue
            g = (T['pnl_usd'].to_numpy()[k] > 0)
            wr, rm = g.mean(), T['r'].to_numpy()[k].mean()
            if not (0.60 <= wr <= 0.75 and rm > 0):
                continue
            pc = PCS[nom]
            wpl = pc.loc[pc['jour'].isin(app), 'g'].mean()
            sc = wr - wpl
            if sc > bsc:
                best, bsc, info = nom, sc, (int(k.sum()), wr, wpl, rm)
        L = dict(pli=p, app_debut=str(pd.Timestamp(app.min(), unit='D').date()), test_debut=str(pd.Timestamp(test.min(), unit='D').date()),
                 test_fin=str(pd.Timestamp(test.max(), unit='D').date()), choix=best)
        if best is not None:
            T = TR[best]; k = np.isin(JT[best], test)
            Tt = T[k]
            oos.append(Tt.assign(pli=p, variante=best))
            pc = PCS[best]; pct = pc[pc['jour'].isin(test)]
            for kk, grp in pct.groupby('tirage'):
                oos_pl[kk].append(grp)
            L.update(n_app=info[0], taux_app=info[1], placebo_app=info[2], r_app=info[3], n_test=len(Tt),
                     taux_test=float((Tt['pnl_usd'] > 0).mean()) if len(Tt) else np.nan,
                     placebo_test=float(pct['g'].mean()) if len(pct) else np.nan,
                     r_test=float(Tt['r'].mean()) if len(Tt) else np.nan)
        lignes.append(L)
    W = pd.DataFrame(lignes)
    O = pd.concat(oos).sort_values('entree_t').reset_index(drop=True) if oos else pd.DataFrame()
    res = dict(n=len(O))
    if len(O):
        wr_pl = np.array([pd.concat(x)['g'].mean() if x else np.nan for x in oos_pl])
        r_pl = np.array([pd.concat(x)['r'].mean() if x else np.nan for x in oos_pl])
        m = M.metriques(O)
        res.update(pct_gagnants=m['pct_gagnants'], pct_placebo=float(np.nanmean(wr_pl)),
                   ecart_pts=100 * (m['pct_gagnants'] - np.nanmean(wr_pl)),
                   p_taux=float((1 + np.sum(wr_pl >= m['pct_gagnants'])) / (1 + np.isfinite(wr_pl).sum())),
                   r_moyen=m['r_moyen'], r_ic95=m['r_ic95'], r_placebo=float(np.nanmean(r_pl)),
                   p_r=float((1 + np.sum(r_pl >= m['r_moyen'])) / (1 + np.isfinite(r_pl).sum())), pf=m['pf'])
    return W, O, res


def main():
    global PP
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None)
    ap.add_argument('--n', type=int, default=500)
    ap.add_argument('--proc', type=int, default=8)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    PP = [C.preparer(s) for s in C.charger_series(a.source)]
    V = variantes()
    print(time.strftime('%H:%M:%S'), len(V), 'variantes', flush=True)
    t0 = time.time()
    with mp.get_context('fork').Pool(a.proc) as pool:
        res = pool.map(tourner, [(q, v, a.n, False) for q, v in enumerate(V)], chunksize=2)
    print(time.strftime('%H:%M:%S'), 'balayage %.0f s' % (time.time() - t0), flush=True)
    TR = {nom: T for nom, T, _, _ in res}
    PCS = {nom: pc for nom, _, pc, _ in res}
    lignes, mois = [], []
    for (nom, geom, conds) in V:
        L, mo = stats(nom, geom, conds, TR[nom], PCS[nom], a.n)
        lignes.append(L); mois += mo
    R = pd.DataFrame(lignes)
    R['p_taux_ajustee'] = test_maximum(R, PCS, a.n, 'g')
    R['p_r_ajustee'] = test_maximum(R, PCS, a.n, 'r')
    R['n_variantes'] = len(R)
    R.to_csv(os.path.join(OUT, 'balayage_contextes.csv'), index=False)
    pd.DataFrame(mois).to_csv(os.path.join(OUT, 'stabilite_mois.csv'), index=False)
    pickle.dump(dict(V=V, TR=TR, PCS=PCS, n=a.n), open(os.path.join(OUT, 'balayage.pkl'), 'wb'))
    W, O, wres = walk_forward(R, TR, PCS, a.n)
    W.to_csv(os.path.join(OUT, 'walk_forward.csv'), index=False)
    if len(O):
        O.to_csv(os.path.join(OUT, 'trades_wf_oos.csv'), index=False)
    pd.Series(wres).to_json(os.path.join(OUT, 'walk_forward_resume.json'), indent=1, default_handler=str)
    print(W.to_string())
    print(wres)
    cols = ['variante', 'n', 'pct_gagnants', 'pct_placebo', 'ecart_pts', 'p_taux', 'p_taux_ajustee', 'r_moyen',
            'r_placebo', 'p_r', 'pf', 'mois_n', 'mois_positifs']
    ok = R[(R.n >= 60)].sort_values('z_taux', ascending=False)
    print(ok[cols].head(25).round(3).to_string())


if __name__ == '__main__':
    main()
