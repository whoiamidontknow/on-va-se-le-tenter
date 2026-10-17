import numpy as np, etude as E
NOMS = ['A_clx_trend', 'hei', 'sigF', 'tl', 'union']
def declencheurs(df):
    D = E.declencheurs(df)
    n = len(df); z = np.zeros(n, bool)
    L = z.copy(); S = z.copy()
    for k in ('sigF', 'clx_buy', 'clx_sell', 'hei', 'tl', 'orb', 'mon'):
        if k in D:
            L |= D[k][0]; S |= D[k][1]
    S &= ~L
    D['union'] = (L, S)
    return {k: D[k] for k in NOMS if k in D}
