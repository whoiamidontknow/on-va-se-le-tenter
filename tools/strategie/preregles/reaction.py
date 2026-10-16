"""1. RÉACTION DU PRIX AUX NIVEAUX, contre des niveaux PLACEBO (même structure, décalés).

Événement « test » d'un niveau L (vrais prix reconstitués, ATR14 vrais prix de la barre précédente = a) :
  - armement : le close de i-1 est à au moins ARM x a du niveau, d'un côté (au-dessus -> test en support,
    en dessous -> test en résistance) ;
  - test : la barre i vient à TOL x a du niveau (mèche) ; on désarme jusqu'au prochain éloignement.
Issue sur H barres (premier franchissement) :
  - REBOND : le prix repart de UP x a du niveau du côté d'arrivée (compté à partir de i+1) ;
  - CASSURE : il traverse de BRK x a de l'autre côté (compté dès la barre i) ; les deux dans la même barre
    -> cassure (prudent) ; sinon CALÉ.
  - PÉNÉTRATION : plus grande avancée au-delà du niveau avant le rebond (en ATR) : P(pén. >= m) est la
    probabilité qu'un stop placé m ATR derrière le niveau soit touché avant que le prix ne reparte.
  - CASSURE FRANCHE : une clôture à 1 ATR au-delà du niveau dans les H barres.
Placebo : chaque niveau réel est recopié décalé de ±1,6 et ±2,7 x (ATR médian de la série) (ronds :
±30 % et ±70 % du pas), et suit exactement la même règle. Différence réel - placebo, IC 95 % par
bootstrap des JOURS. Jeux : MES (apprentissage) / NQ (validation), et 1re / 2e moitié dans le temps.
Sortie : reaction.json + reaction.md.
"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import pandas as pd
import niveaux as nv   # noqa: E402

ARM, TOL, UP, BRK, H = 0.5, 0.1, 1.0, 0.5, 16
PEN = (0.1, 0.25, 0.5, 1.0)
DELTAS = (-2.7, -1.6, 1.6, 2.7)


def jour(t):
    return int((t.timestamp() + 6 * 3600) // 86400)


def role(fam, sub):
    if fam.startswith('P'):
        r = 'P' if sub == 'P' else sub[0]
        return fam + ':' + r
    if fam in ('DB', 'DS'): return fam + ':' + sub
    if fam in ('AS', 'LD', 'US', 'MO'): return fam + ':' + sub
    return fam


def placebos(S, fam, sub, L, U):
    if fam in ('RD', 'RF'):
        st = 100.0 if fam == 'RD' else (50.0 if S['inst'] == 'NQ' else 25.0)
        return [L + st * f for f in (-0.7, -0.3, 0.3, 0.7)]
    return [L + d * U for d in DELTAS]


def evenements(S):
    n = S['n']; rh, rl, rc, a_ = S['rh'], S['rl'], S['rc'], S['ratr']
    U = float(np.nanmedian([x for x in S['ratr'] if x]))
    arm = {}; rows = []
    for i in range(102, n - H - 1):
        a = a_[i - 1]
        if not a or S['brk'][i]: continue
        cands = []
        for fam, sub, L in S['LV'][i - 1]:
            cands.append((fam, sub, L, False))
            for Lp in placebos(S, fam, sub, L, U):
                cands.append((fam, sub, Lp, True))
        for fam, sub, L, plc in cands:
            key = (fam, sub, round(L, 2), plc)
            dist = (rc[i - 1] - L) / a
            st = arm.get(key, 0)
            if dist >= ARM: st = 1
            elif dist <= -ARM: st = -1
            ev = 0
            if st == 1 and rl[i] <= L + TOL * a: ev = 1
            elif st == -1 and rh[i] >= L - TOL * a: ev = -1
            if ev == 0:
                arm[key] = st; continue
            arm[key] = 0
            s = ev
            # issue
            out = 'cale'; pen = 0.0; franche = False
            for k in range(i, min(n, i + H)):
                if k > i and S['brk'][k]: break
                adv = (L - rl[k]) / a if s == 1 else (rh[k] - L) / a
                brk = adv >= BRK
                reb = k > i and ((rh[k] - L) / a >= UP if s == 1 else (L - rl[k]) / a >= UP)
                if brk:
                    pen = max(pen, adv); out = 'cassure'
                    # pénétration : continuer jusqu'au rebond ou l'horizon
                    for k2 in range(k + 1, min(n, i + H)):
                        if (s == 1 and (rh[k2] - L) / a >= UP) or (s == -1 and (L - rl[k2]) / a >= UP): break
                        pen = max(pen, (L - rl[k2]) / a if s == 1 else (rh[k2] - L) / a)
                    break
                if reb:
                    out = 'rebond'; break
                pen = max(pen, adv)
            for k in range(i, min(n, i + H)):
                if (s == 1 and (L - rc[k]) / a >= 1.0) or (s == -1 and (rc[k] - L) / a >= 1.0):
                    franche = True; break
            rows.append((role(fam, sub), fam, s, plc, out == 'rebond', out == 'cassure', out == 'cale', pen, franche,
                         jour(S['T'][i]), S['T'][i].timestamp(), S['inst'], S['tfm']))
    return rows


COLS = ['role', 'fam', 's', 'placebo', 'rebond', 'cassure', 'cale', 'pen', 'franche', 'jour', 't', 'inst', 'tf']


def boot_diff(y_r, j_r, y_p, j_p, B=2000, seed=1):
    days = np.unique(np.concatenate([j_r, j_p]))
    ix = {d: k for k, d in enumerate(days)}; G = len(days)
    ir = np.array([ix[d] for d in j_r]); ip = np.array([ix[d] for d in j_p])
    Sr = np.bincount(ir, weights=y_r, minlength=G); Nr = np.bincount(ir, minlength=G)
    Sp = np.bincount(ip, weights=y_p, minlength=G); Np = np.bincount(ip, minlength=G)
    rng = np.random.default_rng(seed)
    W = rng.multinomial(G, np.full(G, 1 / G), size=B).astype(float)
    d = (W @ Sr) / np.maximum(W @ Nr, 1) - (W @ Sp) / np.maximum(W @ Np, 1)
    return float(y_r.mean() - y_p.mean()), float(np.quantile(d, .025)), float(np.quantile(d, .975))


def tableau(df, nmin=30):
    out = []
    df = df.copy()
    for m in PEN: df['pen%.2f' % m] = df['pen'] >= m
    for (rl_, s), g in df.groupby(['role', 's']):
        r = g[~g['placebo']]; p = g[g['placebo']]
        if len(r) < 10: continue
        rec = dict(role=rl_, s=int(s), n=len(r), jours=int(r['jour'].nunique()), n_plc=len(p))
        for v in ('rebond', 'cassure', 'cale', 'franche', 'pen0.25', 'pen0.50'):
            rec[v] = float(r[v].mean()); rec[v + '_plc'] = float(p[v].mean()) if len(p) else np.nan
        if len(r) >= nmin and len(p) >= nmin:
            for v in ('rebond', 'pen0.25', 'franche'):
                m, lo, hi = boot_diff(r[v].values.astype(float), r['jour'].values, p[v].values.astype(float), p['jour'].values)
                rec['d_' + v] = m; rec['d_' + v + '_lo'] = lo; rec['d_' + v + '_hi'] = hi
            for nm, mk in (('MES', 'MES'), ('NQ', 'NQ')):
                rr = r[r['inst'] == mk]; pp = p[p['inst'] == mk]
                rec['n_' + nm] = len(rr)
                rec['d_rebond_' + nm] = float(rr['rebond'].mean() - pp['rebond'].mean()) if len(rr) >= 15 and len(pp) else np.nan
                rec['d_pen_' + nm] = float(rr['pen0.25'].mean() - pp['pen0.25'].mean()) if len(rr) >= 15 and len(pp) else np.nan
            for nm, mk in (('T1', r['t1']), ('T2', ~r['t1'])):
                rr = r[mk]; pp = p[p['t1'] == (nm == 'T1')]
                rec['d_rebond_' + nm] = float(rr['rebond'].mean() - pp['rebond'].mean()) if len(rr) >= 15 and len(pp) else np.nan
        out.append(rec)
    return pd.DataFrame(out)


def familles(df):
    """Regroupement par grande famille (tous rôles et côtés réunis)."""
    def fam_g(f):
        if f.startswith('P'): return f[:2] + '_' + f.split('_')[1]
        return f
    d = df.copy(); d['role'] = d['fam'].map(fam_g); d['s'] = 0
    return tableau(d)


def principal(tfs=(15,), tag='15'):
    t0 = time.time()
    series = nv.charger(tfs)
    rows = []
    for S in series:
        r = evenements(S)
        print('  ', S['sym'], S['tf'], S['n'], 'événements', len(r), '%.0fs' % (time.time() - t0), flush=True)
        rows += r
    df = pd.DataFrame(rows, columns=COLS)
    # moitiés dans le temps, par instrument
    df['t1'] = False
    for inst, g in df.groupby('inst'):
        cut = np.median(np.unique(g['jour']))
        df.loc[g.index, 't1'] = g['jour'] < cut
    df.to_pickle(os.path.join(HERE, 'cache_reaction_%s.pkl' % tag))
    T = tableau(df); F = familles(df)
    T.to_csv(os.path.join(HERE, 'reaction_roles_%s.csv' % tag), index=False)
    F.to_csv(os.path.join(HERE, 'reaction_familles_%s.csv' % tag), index=False)
    print('fini %.0fs' % (time.time() - t0))
    return df, T, F


def fmt(T):
    cols = ['role', 's', 'n', 'jours', 'rebond', 'rebond_plc', 'd_rebond', 'd_rebond_lo', 'd_rebond_hi', 'd_rebond_MES',
            'd_rebond_NQ', 'd_rebond_T1', 'd_rebond_T2', 'cassure', 'cassure_plc', 'pen0.25', 'pen0.25_plc', 'd_pen0.25',
            'd_pen0.25_lo', 'd_pen0.25_hi', 'franche', 'franche_plc']
    cols = [c for c in cols if c in T.columns]
    return T[cols].to_string(index=False, float_format=lambda x: '%.3f' % x)


if __name__ == '__main__':
    tfs = tuple(int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else '15').split(','))
    tag = '-'.join(map(str, tfs))
    df, T, F = principal(tfs, tag)
    pd.set_option('display.width', 250)
    print(fmt(F)); print(); print(fmt(T))
