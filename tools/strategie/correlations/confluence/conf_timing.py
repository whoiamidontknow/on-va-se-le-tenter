"""2. TIMING DE L'ENTRÉE pour les meilleurs déclencheurs : immédiat / confirmation / repli.
Même sortie pour toutes les variantes (préréglage du déclencheur, puis sortie commune stop 1,5 ATR obj 2R).
R mesuré au risque réellement pris (stop_k x ATR du signal depuis le prix d'entrée), coûts engine inclus.
« par signal » = somme des R / nombre de signaux (pénalise les replis qui ratent les meilleurs départs)."""
import numpy as np
import conf_common as C
import conf_build as B

L = C.load()
GROUPS = {
    'sep-oct CSV moitié1': lambda S: S['set'] in ('MES', 'NQ'),
    'sep-oct CSV moitié2': lambda S: S['set'] in ('MES', 'NQ'),
    'MES avr-jul 15m': lambda S: S['set'] == 'MES1',
    'API 15m+2m vrais prix': lambda S: S['set'] in ('API15', 'API2'),
}


def lv_sess(S, i, d, j):
    """niveau de session cassé au signal i (haut si long, bas si court)."""
    for k in ('AS', 'LD', 'US'):
        a = S['SL'][k][i]
        if a is None: continue
        if d == 1 and S['c'][i] > a[0] >= S['c'][i - 1]: return a[0]
        if d == -1 and S['c'][i] < a[1] <= S['c'][i - 1]: return a[1]
    return None


def lv_clx50(S, i, d, j):
    return (S['rh'][i] + S['rl'][i]) / 2


VARIANTS = {
    'immédiat': lambda S, sg: C.fills_immediate(S, sg),
    'confirm. 2e bougie HA': lambda S, sg: C.fills_confirm(S, sg),
    'confirm. 2e vraie bougie': lambda S, sg: C.fills_confirm(S, sg, real=True),
    'repli EMA50 (8 b.)': lambda S, sg: C.fills_limit(S, sg, C.lv_ema50, 8),
    'repli 0.5 ATR (8 b.)': lambda S, sg: C.fills_limit(S, sg, C.lv_half_atr, 8),
    'repli 0.5 ATR (3 b.)': lambda S, sg: C.fills_limit(S, sg, C.lv_half_atr, 3),
    'repli milieu bougie signal (4 b.)': lambda S, sg: C.fills_limit(S, sg, C.lv_mid_bar, 4),
    'repli droite cassée (8 b.)': lambda S, sg: C.fills_limit(S, sg, C.lv_tl, 8),
    'repli niveau cassé (8 b.)': lambda S, sg: C.fills_limit(S, sg, lv_sess, 8),
}
ONLY = {'repli droite cassée (8 b.)': ('tl',), 'repli niveau cassé (8 b.)': ('sess',)}


def go(trig, exit_kw, filt):
    print('\n=== %s | sortie %s' % (trig, exit_kw['label']))
    kw = {k: v for k, v in exit_kw.items() if k != 'label'}
    for vn, fv in VARIANTS.items():
        if vn in ONLY and trig not in ONLY[vn]: continue
        cells = []
        for gn, gf in GROUPS.items():
            R = []; nsig = 0
            for S in L:
                if not gf(S): continue
                sg = C.apply_filter(S, C.trig(S, trig), filt)
                if 'moitié' in gn:
                    h2 = gn.endswith('2'); sg = [(i, d) for i, d in sg if (i >= S['n'] // 2) == h2]
                nsig += len(sg)
                R += [t['R'] for t in C.sim(S, fv(S, sg), **kw)]
            s = C.stats_R(R)
            cells.append('%s n%3d/%3d %+.2f (t%+.1f) /sig %+.2f' % (gn[:14], s['n'], nsig, s['m'] if s['n'] else 0,
                                                                  s['t'] if s['n'] > 1 else 0, sum(R) / nsig if nsig else 0))
        print('  %-34s' % vn, ' | '.join(cells))


import strat as T
for trig in ('tl', 'clxL', 'sigF', 'sess'):
    k, tg, x, f = C.PRESET[trig]
    go(trig, dict(label='préréglage', stop_k=k, target=tg, exit_on=x), f)
    if trig != 'tl' and trig != 'sess':
        go(trig, dict(label='stop1.5 obj2R', stop_k=1.5, target=2), f)
