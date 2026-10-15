"""Étude de corrélations : (A) chaque état vs la cible, (B) espérance par modalité, (C) toutes les paires
« entrée × filtre » et « filtre × filtre », (D) redondances entre modules.
Apprentissage = MES 1re moitié ; validation = MES 2e moitié, NQ (même période / période suivante), + jeux X.
Erreurs-types groupées par jour ; Benjamini-Hochberg sur l'apprentissage ; n >= 30 par case.
Sorties CSV dans ce dossier (res_univ.csv, res_modal.csv, res_paires.csv, res_redond.csv)."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import table, defs
from stats_util import cl_mean, cl_diff, cl_spearman, bh

NMIN = 30
TGT = ['ret4', 'ret8', 'ret16', 'L1', 'S1', 'L15', 'S15']
META = {'sid', 'i', 'sym', 'tf', 'group', 't', 'day', 'sess', 'cost'} | set(TGT)


def prep():
    df, S = table.load()
    SETS = defs.sets(df)
    df['set'] = None
    for k, m in SETS.items(): df.loc[m, 'set'] = k
    df = df[df.set.notna()].reset_index(drop=True)
    # dérive de chaque jeu (sym, unité) : pour mesurer l'apport AU-DELÀ de la tendance du marché
    for h in (4, 8, 16):
        df['drift%d' % h] = df.groupby(['set', 'sym', 'tf'])['ret%d' % h].transform('mean')
    return df, S


def univ(df):
    feats = [c for c in df.columns if c not in META and not c.startswith('drift') and c != 'set'
             and pd.api.types.is_numeric_dtype(df[c])]
    rows = []
    for st, d in df.groupby('set'):
        g = d.day.astype(str).values
        for f in feats:
            x = d[f].values.astype(float)
            if np.isnan(x).mean() > 0.9: continue
            for tg in TGT:
                r, t, p, n = cl_spearman(x, d[tg].values, g)
                rows.append(dict(feat=f, tgt=tg, set=st, rho=r, t=t, p=p, n=n))
    U = pd.DataFrame(rows)
    a = U.set == 'APPR_MES1'
    U.loc[a, 'q'] = bh(U.loc[a, 'p'].values)
    U.to_csv(os.path.join(HERE, 'res_univ.csv'), index=False)
    return U


def modal(df):
    """Espérance conditionnelle par modalité (quintiles fixés sur l'apprentissage)."""
    feats = [c for c in df.columns if c not in META and not c.startswith('drift') and c != 'set'
             and pd.api.types.is_numeric_dtype(df[c])]
    ap = df[df.set == 'APPR_MES1']; rows = []
    for f in feats:
        x = df[f].astype(float)
        if x.notna().mean() < 0.1: continue
        if x.nunique() <= 7:
            lab = x
        else:
            qs = np.unique(np.nanquantile(ap[f].astype(float), [.2, .4, .6, .8]))
            if len(qs) < 2: continue
            lab = pd.Series(np.digitize(x, qs), index=df.index).where(x.notna())
        for (st, m), d in df.assign(_m=lab).groupby(['set', '_m']):
            if len(d) < NMIN: continue
            g = d.day.astype(str).values
            m8, t8, p8, G = cl_mean(d.ret8.values - d.drift8.values, g)
            rows.append(dict(feat=f, mod=m, set=st, n=len(d), ret8=d.ret8.mean(), ex8=m8, t=t8, p=p8,
                             L1=d.L1.mean(), S1=d.S1.mean(), ret16=d.ret16.mean()))
    M = pd.DataFrame(rows); M.to_csv(os.path.join(HERE, 'res_modal.csv'), index=False)
    return M


def events(df):
    """Toutes les entrées (vraies + pseudo-entrées « chaque barre dans le sens de l'état X »)."""
    E = defs.entries(df)
    for k, fn in defs.DIR.items():
        s = np.asarray(fn(df), float)
        E['etat:' + k] = np.where(np.isnan(s), 0, np.sign(s))
    return E


def paires(df):
    E = events(df); rows = []
    for en, dv in E.items():
        m = dv != 0
        if m.sum() < NMIN: continue
        sub = df[m].reset_index(drop=True); d = dv[m]
        y8 = d * sub.ret8.values - sub.cost.values
        y4 = d * sub.ret4.values - sub.cost.values; y16 = d * sub.ret16.values - sub.cost.values
        x8 = d * (sub.ret8.values - sub.drift8.values)
        W1 = np.where(d > 0, sub.L1.values, sub.S1.values); W15 = np.where(d > 0, sub.L15.values, sub.S15.values)
        F = {'aucun': np.array(['tout'] * len(sub), dtype=object)}
        for k, fn in defs.DIR.items():
            if en == 'etat:' + k: continue
            F[k] = defs.dir_label(fn(sub), d)
        F.update(defs.nondir(sub, d))
        g_all = pd.factorize(sub.day)[0]; st_all = sub.set.values
        for fn_, lab in F.items():
            lab = np.asarray(lab, dtype=object)
            for st in np.unique(st_all):
                ms = st_all == st
                for L in pd.unique(lab[ms]):
                    if L is None or (isinstance(L, float) and np.isnan(L)): continue
                    c = ms & (lab == L)
                    n = int(c.sum())
                    if n < NMIN: continue
                    mu, t, p, G = cl_mean(y8[c], g_all[c])
                    cx = ms & (lab != L)
                    lift, lt, lp = cl_diff(y8[c], g_all[c], y8[cx], g_all[cx]) if cx.sum() >= NMIN and fn_ != 'aucun' else (np.nan,) * 3
                    xm, xt, xp, _ = cl_mean(x8[c], g_all[c])
                    dl = d[c] > 0
                    rows.append(dict(entree=en, filtre=fn_, mod=L, set=st, n=n, G=G, y8=mu, t=t, p=p,
                                     y4=np.nanmean(y4[c]), y16=np.nanmean(y16[c]), W1=np.nanmean(W1[c]), W15=np.nanmean(W15[c]),
                                     ex8=xm, ex_t=xt, ex_p=xp, lift=lift, lift_t=lt, lift_p=lp,
                                     part_long=dl.mean(), yL=np.nanmean(y8[c][dl]) if dl.any() else np.nan,
                                     yS=np.nanmean(y8[c][~dl]) if (~dl).any() else np.nan,
                                     cost=np.nanmean(sub.cost.values[c])))
        print(en, len(rows), flush=True)
    P = pd.DataFrame(rows)
    a = P.set == 'APPR_MES1'
    P.loc[a, 'q'] = bh(P.loc[a, 'p'].values)
    P.loc[a, 'ex_q'] = bh(P.loc[a, 'ex_p'].values)
    P.loc[a, 'lift_q'] = bh(P.loc[a, 'lift_p'].values)
    P.to_csv(os.path.join(HERE, 'res_paires.csv'), index=False)
    return P


def redond(df):
    d = df[df.set.isin(defs.SETS_MAIN)]
    cols = {k: np.asarray(fn(d), float) for k, fn in defs.DIR.items()}
    for k in ('moy_dist', 'moy_slope', 'rsi', 'cci', 'yoyo', 'adx', 'feu', 'heishi_age', 'sig_score', 'vol_rel', 'atr_rel'):
        cols['v:' + k] = d[k].values.astype(float)
    X = pd.DataFrame(cols)
    C = X.corr(method='spearman', min_periods=300)
    C.to_csv(os.path.join(HERE, 'res_redond.csv'))
    return C


if __name__ == '__main__':
    df, S = prep()
    print(df.groupby('set').size())
    U = univ(df); print('univ', len(U))
    M = modal(df); print('modal', len(M))
    C = redond(df); print('redond ok')
    P = paires(df); print('paires', len(P))
