"""Règles d'entrée complètes candidates, chiffrées sur chaque jeu (coûts engine inclus), mode normal et prudent,
avec t « grappé par jour ». Le seuil de volatilité est appris sur sep-oct moitié 1 seulement.
Aussi : le score de confluence aligné ajoute-t-il quelque chose AUX déclencheurs ? (k choisi sur moitié 1)."""
import numpy as np, pandas as pd
from scipy import stats as st
import conf_common as C
import strat as T

L = C.load()
LD = 'LONDRES 08-14:30'
JEUX = {'sep-oct moitié1': lambda S, i: S['set'] in ('MES', 'NQ') and i < S['n'] // 2,
        'sep-oct moitié2': lambda S, i: S['set'] in ('MES', 'NQ') and i >= S['n'] // 2,
        'MES avr-jul 15m': lambda S, i: S['set'] == 'MES1',
        'API 15m': lambda S, i: S['set'] == 'API15', 'API 2m': lambda S, i: S['set'] == 'API2'}

# seuil de volatilité relative : tiers bas des barres de sep-oct moitié 1
v = [C.atr_rel(S, i) for S in L if S['set'] in ('MES', 'NQ') for i in range(101, S['n'] // 2)]
VQ = float(np.nanquantile([x for x in v if x], 1 / 3))
print('seuil ATR relatif appris (sep-oct moitié 1, tiers bas) = %.2f' % VQ)


def hors_ld(S, i, d): return C.session5(S['T'][i]) != LD
def vol_ok(S, i, d):
    a = C.atr_rel(S, i); return a is not None and a >= VQ
def long_(S, i, d): return d == 1


RULES = {
    'R1 Signator Fort + TREND HTF, hors Londres, ATRrel>=seuil ; stop 1 ATR, sortie Heishi':
        ('sigF', T.f_and(T.f_trend, hors_ld, vol_ok), 'imm', dict(stop_k=1.0, exit_on=T.x_heishi)),
    'R1b idem sans filtre de volatilité (= préréglage B)':
        ('sigF', T.f_and(T.f_trend, hors_ld), 'imm', dict(stop_k=1.0, exit_on=T.x_heishi)),
    'R2 Climax BUY + TREND HTF, limite au milieu de la bougie climax (4 b.) ; stop 1.5 ATR obj 2R':
        ('clxL', T.f_trend, 'mid', dict(stop_k=1.5, target=2)),
    'R2b Climax BUY + TREND HTF, limite milieu (4 b.) ; stop 2 ATR sortie Heishi':
        ('clxL', T.f_trend, 'mid', dict(stop_k=2.0, exit_on=T.x_heishi)),
    'R2c Climax BUY + TREND HTF immédiat ; stop 1.5 ATR obj 2R (référence)':
        ('clxL', T.f_trend, 'imm', dict(stop_k=1.5, target=2)),
    'R3 Cassure trendline hors Londres ; stop 1.5 ATR obj 2R (= préréglage C)':
        ('tl', hors_ld, 'imm', dict(stop_k=1.5, target=2)),
}


def run_rule(trig, filt, entry, kw, jeu, prudent=False):
    tr = []
    for S in L:
        sg = [(i, d) for i, d in C.apply_filter(S, C.trig(S, trig), filt) if JEUX[jeu](S, i)]
        f = C.fills_immediate(S, sg) if entry == 'imm' else C.fills_limit(S, sg, C.lv_mid_bar, 4)
        tr += C.sim(S, f, prudent=prudent, **kw)
    return tr


def line(tr):
    if not tr: return 'n=0'
    R = np.array([t['R'] for t in tr]); s = C.stats_R(R)
    d = pd.Series(R, index=[t['t'].astimezone(C.PARIS).date() for t in tr]).groupby(level=0).mean()
    tj = st.ttest_1samp(d, 0)[0] if len(d) > 2 else np.nan
    srt = np.sort(R); sans = srt[:-1].mean() if len(R) > 1 else np.nan
    return 'n%3d moy %+.2f méd %+.2f PF %.2f t_jour %+.1f sans le meilleur %+.2f' % (
        len(R), R.mean(), np.median(R), min(s['pf'], 99), tj, sans)


for name, (trig, filt, entry, kw) in RULES.items():
    print('\n==', name)
    for jeu in JEUX:
        tr = run_rule(trig, filt, entry, kw, jeu); trp = run_rule(trig, filt, entry, kw, jeu, prudent=True)
        print('   %-16s %s | prudent moy %+.2f' % (jeu, line(tr), np.mean([t['R'] for t in trp]) if trp else np.nan))

# ---------------- le score de confluence comme FILTRE des déclencheurs
print('\n== Filtre « score aligné >= k » sur les déclencheurs (préréglages, entrée immédiate)')
for trig in ('tl', 'clxL', 'sigF', 'sess'):
    k0, tg, x, f = C.PRESET[trig]
    res = {}
    for k in (-99, 0, 3, 5, 7, 9):
        filt = T.f_and(f, lambda S, i, d, k=k: S['score'][i] * d >= k)
        row = []
        for jeu in ('sep-oct moitié1', 'sep-oct moitié2', 'MES avr-jul 15m', 'API 15m'):
            tr = run_rule(trig, filt, 'imm', dict(stop_k=k0, target=tg, exit_on=x), jeu)
            R = [t['R'] for t in tr]
            row.append('%s n%3d %+.2f' % (jeu[:11], len(R), np.mean(R) if R else 0))
        print('  %-5s k=%3s ' % (trig, 'aucun' if k == -99 else k), ' | '.join(row))
