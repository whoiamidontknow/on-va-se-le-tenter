"""Tableaux de synthèse des étapes A à E (lus dans resultats/*.csv) -> resultats/rapport.md

    ~/venv-quant/bin/python rapport.py
"""
import os

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ICI, 'resultats')
REELS = lambda df: df[df['decl'] != 'hasard']


def lire(nom):
    f = os.path.join(OUT, nom)
    return pd.read_csv(f) if os.path.exists(f) else None


def md(df, flt='%.3f'):
    if df is None or not len(df):
        return '_(vide)_\n'
    cols = list(df.columns)
    out = ['| ' + ' | '.join(map(str, cols)) + ' |', '|' + '---|' * len(cols)]
    for _, r in df.iterrows():
        cel = []
        for c in cols:
            v = r[c]
            cel.append(flt % v if isinstance(v, (float, np.floating)) and v == v else ('' if v != v else str(v)))
        out.append('| ' + ' | '.join(cel) + ' |')
    return '\n'.join(out) + '\n'


def section_A():
    A, P = lire('A_stops.csv'), lire('A_placebo.csv')
    if A is None:
        return ''
    s = ['## A. Stops\n']
    A = A[A['n'] >= 5]
    ref = A[A.stop == 'atr2'][['decl', 'sortie', 'r_moyen']].rename(columns={'r_moyen': 'r_atr2'})
    X = A.merge(ref, on=['decl', 'sortie'])
    X['delta'] = X['r_moyen'] - X['r_atr2']
    R = REELS(X)
    g = R.groupby('stop').agg(n_decl=('decl', 'nunique'), n_trades=('n', 'sum'), r_moyen=('r_moyen', 'mean'),
                              delta_vs_atr2=('delta', 'mean'), pct_decl_mieux=('delta', lambda d: (d > 0).mean()),
                              pct_stop=('pct_stop', 'mean'), dist_atr=('dist_atr', 'mean'),
                              pct_niveau=('pct_niveau', 'mean')).reset_index()
    g = g[g['n_decl'] >= 4]
    s.append('Panel des déclencheurs réels (moyenne par déclencheur, sorties Heishinator et 2R confondues), '
             '%d stops testés.\n\n**ATR fixes**\n' % A['stop'].nunique())
    s.append(md(g[g.stop.str.startswith('atr')].sort_values('stop')))
    s.append('\n**15 meilleurs stops sur niveau**\n')
    s.append(md(g[g.stop.str.startswith('niv')].sort_values('r_moyen', ascending=False).head(15)))
    s.append('\n**15 moins bons**\n')
    s.append(md(g[g.stop.str.startswith('niv')].sort_values('r_moyen').head(15)))
    # par famille (configuration centrale)
    if P is not None and len(P):
        P = P.copy()
        P['ecart_placebo'] = P['r_moyen'] - P['placebo_moy']
        P['fam'] = P['stop'].str.split(':').str[1]
        P['repli'] = P['stop'].str.split(':').str[4]
        PR = REELS(P)
        t = PR.groupby(['fam', 'repli']).agg(n_cas=('decl', 'size'), r_reel=('r_moyen', 'mean'),
                                             r_placebo=('placebo_moy', 'mean'), ecart=('ecart_placebo', 'mean'),
                                             pct_reel_mieux=('ecart_placebo', lambda d: (d > 0).mean()),
                                             n_p_inf_5pc=('p_placebo', lambda p: int((p <= 0.05).sum())),
                                             n_p_sup_95pc=('p_placebo', lambda p: int((p >= 0.95).sum()))).reset_index()
        s.append('\n**Niveau contre placebo** (marge 0,1 ATR, fourchette 0,5-3 ATR ; un « cas » = un déclencheur × '
                 'une sortie ; placebo = mêmes signaux, distance du stop permutée entre signaux, %s tirages)\n'
                 % '20')
        s.append(md(t.sort_values('ecart', ascending=False)))
        H = P[P['decl'] == 'hasard']
        if len(H):
            th = H.groupby(['fam', 'repli']).agg(r_reel=('r_moyen', 'mean'), r_placebo=('placebo_moy', 'mean'),
                                                 ecart=('ecart_placebo', 'mean')).reset_index()
            s.append('\nTémoin (entrées au hasard) :\n')
            s.append(md(th.sort_values('ecart', ascending=False)))
    T = lire('A_placebo_top.csv')
    if T is not None and len(T):
        T = T.copy(); T['ecart'] = T['r_moyen'] - T['placebo_moy']
        t = REELS(T).groupby('stop').agg(n_cas=('decl', 'size'), n_trades=('n', 'sum'), r_reel=('r_moyen', 'mean'),
                                          r_placebo=('placebo_moy', 'mean'), ecart=('ecart', 'mean'),
                                          pct_reel_mieux=('ecart', lambda d: (d > 0).mean()),
                                          n_p_inf_5pc=('p_placebo', lambda p: int((p <= 0.05).sum())),
                                          n_p_sup_95pc=('p_placebo', lambda p: int((p >= 0.95).sum()))).reset_index()
        s.append('\n**Meilleurs stops sur niveau du classement brut, contre leur placebo**\n')
        s.append(md(t.sort_values('ecart', ascending=False)))
    return '\n'.join(s)


def section_B():
    B, P = lire('B_sorties.csv'), lire('B_placebo.csv')
    if B is None:
        return ''
    s = ['\n## B. Objectifs et gestion\n']
    B = B[B['n'] >= 5]
    ref = B[(B.stop == 'atr2') & (B.sortie == 'hei')][['decl', 'r_moyen']].rename(columns={'r_moyen': 'r_ref'})
    X = REELS(B.merge(ref, on='decl'))
    X['delta'] = X['r_moyen'] - X['r_ref']
    g = X.groupby(['stop', 'sortie']).agg(n_decl=('decl', 'nunique'), n_trades=('n', 'sum'), r_moyen=('r_moyen', 'mean'),
                                          delta_vs_atr2_hei=('delta', 'mean'),
                                          pct_decl_mieux=('delta', lambda d: (d > 0).mean()),
                                          pct_gagnants=('pct_gagnants', 'mean')).reset_index()
    g = g[g.n_decl >= 4]
    s.append('Référence : stop 2 ATR + sortie Heishinator. %d gestions.\n\n**Stop 2 ATR, toutes les sorties**\n'
             % len(g))
    s.append(md(g[g.stop == 'atr2'].sort_values('r_moyen', ascending=False)))
    s.append('\n**20 meilleures gestions (tous stops)**\n')
    s.append(md(g.sort_values('r_moyen', ascending=False).head(20)))
    if P is not None and len(P):
        P = P.copy()
        P['ecart'] = P['r_moyen'] - P['placebo_moy']
        t = REELS(P).groupby('sortie').agg(n_decl=('decl', 'size'), r_reel=('r_moyen', 'mean'),
                                           r_placebo=('placebo_moy', 'mean'), ecart=('ecart', 'mean'),
                                           pct_reel_mieux=('ecart', lambda d: (d > 0).mean()),
                                           n_p_inf_5pc=('p_placebo', lambda p: int((p <= 0.05).sum()))).reset_index()
        s.append('\n**Objectif sur niveau contre placebo** (stop 2 ATR ; placebo = multiple de R permuté entre signaux)\n')
        s.append(md(t.sort_values('ecart', ascending=False)))
    return '\n'.join(s)


def section_C():
    C = lire('C_propfirm.csv')
    if C is None:
        return ''
    s = ['\n## C. Propfirm (Tradeify Select Flex, risque fixe en $)\n']
    b = C[C['meilleur']].copy()
    base = b[(b.stop == 'atr2') & (b.sortie == 'hei')][['decl', 've', 'p_reussite', 'risque_usd']].rename(
        columns={'ve': 've_base', 'p_reussite': 'p_base', 'risque_usd': 'risque_base'})
    top = b.sort_values('ve', ascending=False).groupby('decl').head(1)
    top = top.merge(base, on='decl', how='left')
    s.append(md(top[['decl', 'stop', 'sortie', 'risque_usd', 'n', 'n_pris', 'r_moyen', 'p_reussite', 'p_1er_payout', 've',
                     'risque_base', 'p_base', 've_base']].sort_values('ve', ascending=False), '%.2f'))
    # taille : VE en fonction du risque pour la gestion de référence, panel
    t = C.groupby('risque_usd').agg(ve_moy=('ve', 'mean'), p_moy=('p_reussite', 'mean'),
                                    pris=('n_pris', 'sum'), n=('n', 'sum')).reset_index()
    t['pct_pris'] = t['pris'] / t['n']
    s.append('\n**Effet du risque par trade** (moyenne sur toutes les gestions évaluées)\n')
    s.append(md(t[['risque_usd', 've_moy', 'p_moy', 'pct_pris']], '%.3f'))
    return '\n'.join(s)


def section_D():
    CH = lire('D_choix.csv')
    if CH is None:
        return ''
    return '\n## D. Situations (choix sur les 2/3 anciens, vérification sur le 1/3 récent)\n\n' + md(CH)


def section_E():
    R, W = lire('E_recettes.csv'), lire('E_white.csv')
    s = ['\n## E. Biais de sélection et référence au hasard\n']
    if W is not None:
        s.append('**White (panel, gain en R par signal contre 2 ATR + Heishinator), 10 meilleures**\n')
        s.append(md(W.head(10)))
    if R is not None:
        s.append('\n**Recettes retenues (meilleure VE par déclencheur) et référence au hasard**\n')
        s.append(md(R, '%.3f'))
    return '\n'.join(s)


def section_F():
    F = lire('F_panel_propfirm.csv')
    if F is None:
        return ''
    s = ['\n## F. Panel propfirm (Tradeify Select Flex) : gestions et placebo\n']
    F = REELS(F)
    R = F[F.placebo == -1]
    # meilleure taille par (déclencheur, gestion)
    b = R.sort_values('ve', ascending=False).groupby(['decl', 'stop', 'sortie']).head(1)
    ref = b[(b.stop == 'atr2') & (b.sortie == 'hei')][['decl', 've']].rename(columns={'ve': 've_ref'})
    b = b.merge(ref, on='decl')
    t = b.groupby(['stop', 'sortie']).agg(n_decl=('decl', 'size'), ve_moy=('ve', 'mean'), ve_med=('ve', 'median'),
                                          p_reussite=('p_reussite', 'mean'), p_payout=('p_1er_payout', 'mean'),
                                          risque_moy=('risque_usd', 'mean'),
                                          pct_decl_mieux_que_ref=('ve', lambda v: np.nan)).reset_index()
    mieux = b.assign(m=b['ve'] > b['ve_ref']).groupby(['stop', 'sortie'])['m'].mean().reset_index()
    t = t.drop(columns='pct_decl_mieux_que_ref').merge(mieux.rename(columns={'m': 'pct_decl_mieux_que_ref'}),
                                                       on=['stop', 'sortie'])
    s.append('Chaque déclencheur réel à SA meilleure taille (risque fixe en $) ; VE = valeur espérée $ par tentative.\n')
    s.append(md(t.sort_values('ve_moy', ascending=False), '%.2f'))
    # placebo, à risque égal (200 $) et à la meilleure taille
    P = F[F.placebo >= 0]
    if len(P):
        rows = []
        for (st, so), g in P.groupby(['stop', 'sortie']):
            for rq in (150, 200, 300):
                r_ = R[(R.stop == st) & (R.sortie == so) & (R.risque_usd == rq)]
                p_ = g[g.risque_usd == rq].groupby('decl')[['ve', 'p_reussite', 'r_moyen']].mean()
                m = r_.set_index('decl')[['ve', 'p_reussite', 'r_moyen']].join(p_, rsuffix='_plac').dropna()
                if len(m):
                    rows.append(dict(stop=st, sortie=so, risque_usd=rq, n_decl=len(m), ve_reel=m['ve'].mean(),
                                     ve_placebo=m['ve_plac'].mean(), p_reel=m['p_reussite'].mean(),
                                     p_placebo=m['p_reussite_plac'].mean(), r_reel=m['r_moyen'].mean(),
                                     r_placebo=m['r_moyen_plac'].mean(),
                                     pct_decl_reel_mieux=float((m['ve'] > m['ve_plac']).mean())))
        s.append('\n**Niveaux contre placebo en métriques propfirm** (même risque fixe ; placebo = 5 tirages)\n')
        s.append(md(pd.DataFrame(rows), '%.3f'))
    # taille
    t2 = R[(R.stop == 'atr2') & (R.sortie == 'hei')].groupby('risque_usd').agg(
        ve_moy=('ve', 'mean'), p_reussite=('p_reussite', 'mean'), p_payout=('p_1er_payout', 'mean'),
        pris=('n_pris', 'sum'), n=('n', 'sum')).reset_index()
    t2['pct_trades_pris'] = t2['pris'] / t2['n']
    s.append('\n**Taille : risque fixe par trade (stop 2 ATR + Heishinator, moyenne des déclencheurs)**\n')
    s.append(md(t2[['risque_usd', 've_moy', 'p_reussite', 'p_payout', 'pct_trades_pris']], '%.3f'))
    return '\n'.join(s)


def section_G():
    G = lire('G_entrees_agents.csv')
    if G is None or not len(G):
        return ''
    s = ['\n## G. Entrées publiées par les autres agents, rejouées avec chaque gestion\n']
    s.append(md(G[['id', 'stop', 'sortie', 'n', 'r_moyen', 'pct_gagnants', 'risque_usd', 'p_reussite', 'p_1er_payout', 've']], '%.2f'))
    return '\n'.join(s)


if __name__ == '__main__':
    txt = '# Rapport chiffré SOR (généré par rapport.py)\n\n' + section_A() + section_B() + section_C() + section_D() + section_E() + section_F() + section_G()
    open(os.path.join(OUT, 'rapport.md'), 'w').write(txt)
    print(txt)
