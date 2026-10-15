"""Stop « Zone Detector la plus proche » contre stop ATR x 1,5 / x 2 — étude INDICATIVE (≈ 2 mois de données).

1. Comparaison appariée (même entrée, même sortie) par déclencheur, unité, instrument :
   stops ATR1.5, ATR2, DET1.5 (zone, repli ATR x 1,5), DET2 (zone, repli ATR x 2) ;
   sorties : objectif 2R (+ stop) ou changement Heishinator (+ stop). Coûts : 1 tick/côté + 1,25 $/côté.
   Chaque signal est un trade isolé (chevauchements permis) -> comparaison strictement appariée.
   Contrôle réaliste : préréglages C et A en position unique (comme le Pine).
2. « La zone apporte-t-elle une information ? » sur TOUTES les barres (long et short) où une zone est
   utilisable : taux de stop touché en H barres au niveau de la zone, contre (a) le même écart en ATR
   pris sur des barres tirées au hasard (même série, même sens), (b) des niveaux décalés de ±0,25/±0,5 ATR
   sur la même barre (profil de « tenue » : P(pas touché | le prix est venu à 0,25 ATR du niveau)).
3. Jeux : MES 1re moitié (apprentissage) / MES 2e moitié / NQ 1re / NQ 2e ; bootstrap par jour (IC 95 %).
Sortie : resultats.json + resultats.md dans ce dossier.
"""
import os, sys, json, time
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import regle, sim                         # noqa: E402
import strat, features                     # noqa: E402
from core import boot_moyenne              # maemfe/core.py  # noqa: E402

TFS = (5, 15, 30, 60)
H_RESPECT = 16
PROCHE = 0.25
RNG = np.random.default_rng(7)
VARIANTES = {'ATR1.5': ('atr', 1.5), 'ATR2': ('atr', 2.0), 'DET1.5': ('det', 1.5), 'DET2': ('det', 2.0)}


def jour(t):
    return int((t.timestamp() + 6 * 3600) // 86400)


def hors_londres(S, i):
    d = S['T'][i].astimezone(features.PARIS); m = d.hour * 60 + d.minute
    return not (480 <= m < 870)


def declencheurs(S):
    strat.ensure_htf(S)
    r = np.random.default_rng(S['n'] * 31 + S['tfm'])
    alea = [(i, int(r.choice((1, -1)))) for i in range(101, S['n'] - 1)]
    nn = lambda S, i: not features.news(S['T'][i], S['tfm'])
    return {
        'Trendline': strat.e_tl(S),
        'Climax BUY': [(i, d) for i, d in strat.e_clx(S) if d == 1],
        'Fleche Fort': strat.e_sigF(S),
        'Heishinator': strat.e_heishi(S),
        'Aleatoire': alea,
        'Preset C': [(i, d) for i, d in strat.e_tl(S) if hors_londres(S, i) and nn(S, i)],
        'Preset A': [(i, d) for i, d in strat.e_clx(S) if d == 1 and strat.f_trend(S, i, d) and nn(S, i)],
    }


def coupures(series):
    """Coupure temporelle par unité : milieu de la période commune MES / NQ."""
    cut = {}
    for tf in TFS:
        ss = [s for s in series if s['tfm'] == tf]
        if not ss: continue
        a = max(min(s['T'][0] for s in ss if s['inst'] == ins) for ins in {s['inst'] for s in ss})
        b = min(max(s['T'][-1] for s in ss if s['inst'] == ins) for ins in {s['inst'] for s in ss})
        cut[tf] = a + (b - a) / 2
    return cut


def jeu(S, i, cut):
    return S['inst'] + ('_1' if S['T'][i] < cut[S['tfm']] else '_2')


# ------------------------------------------------------------------ 1. comparaison appariée
def comparer(series, cut):
    rows = []
    for S in series:
        for trig, E in declencheurs(S).items():
            if trig == 'Aleatoire' and S['tfm'] == 5: pass
            for i, d in E:
                a = S['ratr'][i]
                if not a or i + 1 >= S['n']: continue
                base = dict(trig=trig, inst=S['inst'], tf=S['tfm'], sid=id(S), i=i, d=d, jour=jour(S['T'][i]),
                            jeu=jeu(S, i, cut), t=S['T'][i].timestamp(), atr=a)
                for v, (mode, k) in VARIANTES.items():
                    dist, z = regle.distance_stop(S, i, d, mode, k)
                    for sortie in ('cible', 'heishi'):
                        tr = sim.trade(S, i, d, dist, 2.0, sortie)
                        if tr is None: continue
                        rows.append(dict(base, var=v, sortie=sortie, zone=z, dist_atr=dist / a, R=tr['R'],
                                         usd=tr['usd'], stop=tr['why'] == 'stop', nb=tr['nb']))
    return pd.DataFrame(rows)


def pf(x):
    g = x[x > 0].sum(); l_ = -x[x <= 0].sum()
    return g / l_ if l_ > 0 else np.inf


def resume(df, var):
    x = df[df['var'] == var]
    if len(x) == 0: return None
    return dict(n=len(x), zone=float(x['zone'].mean()), dist=float(x['dist_atr'].mean()), stop=float(x['stop'].mean()),
                R=float(x['R'].mean()), pf=float(pf(x['usd'].values)), usd=float(x['usd'].mean()))


def delta(df, a, b, champ='usd'):
    """Écart apparié a - b (même trade) : moyenne et IC bootstrap par jour."""
    k = ['trig', 'sid', 'i', 'd', 'sortie']
    A = df[df['var'] == a].set_index(k); B = df[df['var'] == b].set_index(k)
    j = A.join(B, lsuffix='_a', rsuffix='_b', how='inner')
    if len(j) == 0: return dict(n=0)
    y = (j[champ + '_a'] - j[champ + '_b']).values
    m, lo, hi = boot_moyenne(y, j['jour_a'].values, B=2000)
    return dict(n=len(y), m=float(m), lo=float(lo), hi=float(hi))


# ------------------------------------------------------------------ 2. la zone retient-elle le prix ?
def mae_chemins(S, H):
    """MAE en ATR depuis le vrai close de i (référence du Pine), sur les barres i+1..i+H, long et short."""
    n = S['n']; rh = np.asarray(S['rh']); rl = np.asarray(S['rl']); rc = np.asarray(S['rc'])
    a = np.array([np.nan if x is None else x for x in S['ratr']])
    ts = np.array([t.timestamp() for t in S['T']])
    I = np.arange(101, n - H)
    J = I[:, None] + np.arange(1, H + 1)[None, :]
    ok = ~(np.diff(ts)[J[:, :1] - 1].ravel() > 6 * 3600)        # pas d'entrée juste après un trou
    gap = (ts[J[:, -1]] - ts[I]) > 3 * H * S['tfm'] * 60        # pas de week-end dans la fenêtre
    maeL = (rc[I] - rl[J].min(1)) / a[I]
    maeS = (rh[J].max(1) - rc[I]) / a[I]
    v = ok & ~gap & np.isfinite(a[I])
    return I[v], maeL[v], maeS[v]


def respect(series, cut, H=H_RESPECT, M=400):
    recs = []
    for S in series:
        I, mL, mS = mae_chemins(S, H)
        for d, mae in ((1, mL), (-1, mS)):
            for k, i in enumerate(I):
                cand = regle.niveau_detector(S, i, d)
                if cand is None: continue
                a = S['ratr'][i]; d0 = abs(S['rc'][i] - cand) / a
                if not (regle.DMIN <= d0 <= regle.DMAX): continue
                recs.append(dict(sid=id(S), tf=S['tfm'], inst=S['inst'], d=d, k=k, d0=d0, mae=mae[k],
                                 jour=jour(S['T'][i]), jeu=jeu(S, i, cut)))
        S['_mae'] = (mL, mS)
    R = pd.DataFrame(recs)
    if len(R) == 0: return R, {}
    R['hit'] = R['mae'] >= R['d0']
    R['near'] = R['mae'] >= R['d0'] - PROCHE
    # (a) même écart, barre tirée au hasard dans la même série et le même sens
    pools = {}
    for S in series:
        mL, mS = S['_mae']; pools[(id(S), 1)] = mL; pools[(id(S), -1)] = mS
    hitR = np.zeros((M, len(R))); nearR = np.zeros((M, len(R)))
    for (sid, d), g in R.groupby(['sid', 'd']):
        P = pools[(sid, d)]; idx = g.index.values
        draw = P[RNG.integers(0, len(P), size=(M, len(idx)))]
        hitR[:, idx] = draw >= g['d0'].values[None, :]
        nearR[:, idx] = draw >= (g['d0'].values - PROCHE)[None, :]
    R['hit_hasard'] = hitR.mean(0)                 # probabilité attendue, par instance
    R['tenue_num_h'] = (nearR - hitR).mean(0); R['near_h'] = nearR.mean(0)
    # (b) même barre, niveau décalé
    for dl in (-0.5, -0.25, 0.25, 0.5):
        L = R['d0'] + dl
        R['hit%+.2f' % dl] = R['mae'] >= L
        R['near%+.2f' % dl] = R['mae'] >= L - PROCHE
    return R, dict(hitR=hitR, nearR=nearR)


def stats_respect(R, D, masque):
    r = R[masque]; idx = np.where(masque.values)[0]
    if len(r) < 30: return None
    obs_hit = r['hit'].mean(); obs_tenue = 1 - r['hit'].sum() / max(r['near'].sum(), 1)
    hz = D['hitR'][:, idx].mean(1)
    tz = 1 - D['hitR'][:, idx].sum(1) / np.maximum(D['nearR'][:, idx].sum(1), 1)
    m, lo, hi = boot_moyenne((r['hit'] - r['hit_hasard']).values.astype(float), r['jour'].values)
    prof = {}
    for dl in (-0.5, -0.25, 0.0, 0.25, 0.5):
        h = r['hit'] if dl == 0 else r['hit%+.2f' % dl]; nr = r['near'] if dl == 0 else r['near%+.2f' % dl]
        prof['%+.2f' % dl] = float(1 - h.sum() / max(nr.sum(), 1))
    return dict(n=len(r), jours=int(r['jour'].nunique()), d0=float(r['d0'].mean()), hit=float(obs_hit),
                hit_hasard=float(hz.mean()), p_hit=float((1 + (hz <= obs_hit).sum()) / (len(hz) + 1)),
                ecart=float(m), ecart_lo=float(lo), ecart_hi=float(hi),
                tenue=float(obs_tenue), tenue_hasard=float(tz.mean()),
                p_tenue=float((1 + (tz >= obs_tenue).sum()) / (len(tz) + 1)), profil=prof)


# ------------------------------------------------------------------ 3. position unique (comme le Pine)
def sequentiel(series, cut):
    out = []
    for S in series:
        if S['tfm'] != 15: continue
        T = declencheurs(S)
        for preset, sortie, k in (('Preset C', 'cible', 1.5), ('Preset A', 'heishi', 2.0)):
            for v in ('ATR', 'DET'):
                fn = (lambda S, i, d, v=v, k=k: regle.distance_stop(S, i, d, 'det' if v == 'DET' else 'atr', k))
                for i, d, t in sim.sequentiel_gen(S, T[preset], fn, 2.0, sortie):
                    out.append(dict(preset=preset, var=v, inst=S['inst'], jeu=jeu(S, i, cut), jour=jour(S['T'][i]),
                                    R=t['R'], usd=t['usd'], zone=t['zone'], stop=t['why'] == 'stop'))
    return pd.DataFrame(out)


def principal():
    t0 = time.time()
    series = regle.charger(TFS)
    cut = coupures(series)
    print('séries :', [(s['inst'], s['tfm'], s['n']) for s in series], 'coupures', {k: str(v)[:16] for k, v in cut.items()})
    df = comparer(series, cut)
    df.to_pickle(os.path.join(HERE, 'trades.pkl'))
    print('trades simulés : %d (%.0fs)' % (len(df), time.time() - t0), flush=True)
    res = dict(coupures={k: str(v) for k, v in cut.items()}, comparaison={}, respect={}, sequentiel={})
    # --- 1. comparaison
    for (trig, tf, sortie), g in df.groupby(['trig', 'tf', 'sortie']):
        for nom, m in (('TOUT', slice(None)), ('MES_1', g['jeu'] == 'MES_1'), ('MES_2', g['jeu'] == 'MES_2'),
                       ('NQ_1', g['jeu'] == 'NQ_1'), ('NQ_2', g['jeu'] == 'NQ_2'), ('NQ', g['inst'] == 'NQ'),
                       ('VAL', g['jeu'].isin(['MES_2', 'NQ_2']))):
            x = g[m]
            if len(x) == 0: continue
            key = '%s|%s|%s|%s' % (trig, tf, sortie, nom)
            zx = x[(x['var'] == 'DET1.5') & x['zone']][['sid', 'i', 'd']]
            xz = x.merge(zx, on=['sid', 'i', 'd'])            # trades où une zone est utilisable
            res['comparaison'][key] = dict(
                **{v: resume(x, v) for v in VARIANTES},
                d15=delta(x, 'DET1.5', 'ATR1.5'), d2=delta(x, 'DET2', 'ATR2'),
                d15R=delta(x, 'DET1.5', 'ATR1.5', 'R'),
                zone_seul={v: resume(xz, v) for v in VARIANTES},
                zone_d15=delta(xz, 'DET1.5', 'ATR1.5'), zone_d2=delta(xz, 'DET1.5', 'ATR2'))
    # --- 2. respect
    R, D = respect(series, cut)
    R.drop(columns=[]).to_pickle(os.path.join(HERE, 'respect.pkl'))
    for tf in TFS:
        for nom, m in (('TOUT', R['tf'] == tf), ('MES_1', (R['tf'] == tf) & (R['jeu'] == 'MES_1')),
                       ('MES_2', (R['tf'] == tf) & (R['jeu'] == 'MES_2')), ('NQ', (R['tf'] == tf) & (R['inst'] == 'NQ')),
                       ('LONG', (R['tf'] == tf) & (R['d'] == 1)), ('SHORT', (R['tf'] == tf) & (R['d'] == -1))):
            s = stats_respect(R, D, m)
            if s: res['respect']['%d|%s' % (tf, nom)] = s
    s = stats_respect(R, D, R['tf'] >= 15)
    if s: res['respect']['15-60|TOUT'] = s
    # --- 3. séquentiel
    Q = sequentiel(series, cut)
    for (p, inst, v), g in Q.groupby(['preset', 'inst', 'var']):
        res['sequentiel']['%s|%s|%s' % (p, inst, v)] = dict(n=len(g), zone=float(g['zone'].mean()),
                                                           stop=float(g['stop'].mean()), R=float(g['R'].mean()),
                                                           pf=float(pf(g['usd'].values)), usd=float(g['usd'].mean()),
                                                           tot=float(g['usd'].sum()))
    json.dump(res, open(os.path.join(HERE, 'resultats.json'), 'w'), ensure_ascii=False, indent=1, default=float)
    print('fini (%.0fs)' % (time.time() - t0))
    return res


if __name__ == '__main__':
    principal()
