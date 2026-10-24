"""Gestion adaptative (spec : recherche/GESTION_ADAPTATIVE.md + précisions du coordinateur du 17/10).
Tout est calculé à la clôture de la bougie signal. Sorties : tableaux de PRIX (stop, objectif) par barre et par
sens, branchés sur le moteur via stop/objectif en mode 'niveau' (stop et objectif fixés par trade).
Écart assumé avec le Pine : l'objectif est un prix fixé à partir de la clôture du signal ; le moteur entre à
l'ouverture suivante (+ glissement), donc le R réel diffère un peu du R planifié.
Accès aux données : UNE fonction, charger_dev()."""
from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(ICI, '..', '..'))
RACINE = os.path.abspath(os.path.join(SB, '..'))
for p in (os.path.join(SB, 'recherche', 'sorties'), os.path.join(SB, 'moteur'), os.path.join(SB, 'propfirm'),
          os.path.join(SB, 'recherche', 'meta_ml')):
    if p not in sys.path:
        sys.path.insert(0, p)
import moteur as M  # noqa: E402

TICK = 0.25
MARGE = 4 * TICK
PLAGES = [('08:00', '22:00')]
DEFAUT = dict(adFeu=60, adAdx=25, adK=2.0, adKbas=2.5, adKhaut=1.5, adR1=1.0, adR2=1.5, adR3=2.0,
              adNiv=0, adSaute=1, slMin=1.0, slMax=3.0)
FAM_STOP = ['PYR', 'PMR', 'DET', 'PWR', 'MON', 'SES']      # priorité annuel > mensuel > detector > weekly > monday > session
FAM_OBST = ['PYR', 'PMR', 'PWR', 'DET', 'MON', 'SES']


def charger_dev():
    """POINT D'ACCÈS UNIQUE : séries 15m (développement seulement, 75 %) + colonnes feu (proxy), adx, dip, dim."""
    import donnees_sor as DN
    sys.path[:0] = [DN.STRAT, os.path.join(DN.STRAT, 'preregles'), os.path.join(DN.RACINE, 'tools', 'ephore_api')]
    out = []
    if DN.SOURCE == 'cache':
        import niveaux as nv, strat
        brut = nv.charger((DN.UT,))
    for k, s in enumerate(DN.charger_series(DN.UT)):
        df = s['df'].copy()
        if DN.SOURCE == 'cache':
            S = brut[k]; strat.ensure_feu(S)
            f = lambda x: np.array([np.nan if v is None else v for v in x], float)
            df['feu'] = f(S['feu']); df['adx'] = f(S['adx']); df['dip'] = f(S['dip']); df['dim'] = f(S['dim'])
        dev = M.charger_recherche(df)
        out.append(dict(nom=s['nom'], instrument=s['instrument'], df=dev))
    return out


def _niv(df, fam):
    cols = [c for c in df.columns if c.startswith('lv_%s_' % fam)]
    return df[cols].to_numpy(float) if cols else np.full((len(df), 1), np.nan)


def adaptatif(df, prm=None):
    """-> dict(stop_l, stop_s, obj_l, obj_s, C_l, C_s, typ_l, typ_s) tableaux par barre (NaN = trade sauté)."""
    P = dict(DEFAUT); P.update(prm or {})
    n = len(df)
    e = df['c'].to_numpy(float); a = df['atr'].to_numpy(float)
    sma = pd.Series(a).rolling(96, min_periods=48).mean().to_numpy()
    vr = a / sma
    k = np.where(vr < 0.8, P['adKbas'], np.where(vr > 1.3, P['adKhaut'], P['adK']))
    k = np.where(np.isfinite(vr), k, P['adK'])
    tr = df['trend_60'].to_numpy(bool)
    feu = df['feu'].to_numpy(float) if 'feu' in df else np.full(n, np.nan)
    adx, dip, dim = (df[x].to_numpy(float) if x in df else np.full(n, np.nan) for x in ('adx', 'dip', 'dim'))
    NS = {f: _niv(df, f) for f in set(FAM_STOP) | set(FAM_OBST)}
    res = {}
    rnd = lambda x: np.round(x / TICK) * TICK
    for d, suf in ((1, 'l'), (-1, 's')):
        C = ((tr if d == 1 else ~tr).astype(int)
             + (np.nan_to_num((feu if d == 1 else 1 - feu), nan=0) * 100 >= P['adFeu']).astype(int)
             + ((adx >= P['adAdx']) & ((dip > dim) if d == 1 else (dim > dip))).astype(int))
        stop = rnd(e - d * k * a)
        if P['adNiv']:
            fait = np.zeros(n, bool); sn = stop.copy()
            for f in FAM_STOP:
                M_ = NS[f]
                cand = rnd(M_ - d * MARGE)
                dist = d * (e[:, None] - cand)            # >0 : niveau derrière l'entrée
                ok = np.isfinite(dist) & (dist >= P['slMin'] * a[:, None]) & (dist <= P['slMax'] * a[:, None])
                dd = np.where(ok, dist, np.inf)
                j = dd.argmin(1); best = dd[np.arange(n), j]
                use = np.isfinite(best) & ~fait
                sn = np.where(use, cand[np.arange(n), j], sn); fait |= use
            stop = sn
        R = d * (e - stop)
        base = np.where(C <= 1, P['adR1'], np.where(C == 2, P['adR2'], P['adR3']))
        # obstacle : niveau adverse le plus proche devant le prix, moins 4 ticks
        D = np.full(n, np.inf)
        for f in FAM_OBST:
            M_ = NS[f]
            dev_ = d * (M_ - e[:, None])                  # >0 : devant
            dev_ = np.where(dev_ > 0, dev_, np.inf)
            D = np.minimum(D, dev_.min(1) - MARGE)
        Rr = np.where(R > 0, R, np.nan)
        Dr = D / Rr                                       # obstacle en R (inf si aucun)
        skip = Dr < 1.0
        if P['adSaute']:
            ok = ~skip
        else:
            ok = np.ones(n, bool)
        objR = np.where(Dr >= base, base, np.where(Dr >= 1.0, Dr, 1.0))
        typ = np.where(Dr >= base, np.where(base == P['adR1'], 'R1', np.where(base == P['adR2'], 'R2', 'R3')),
                       np.where(Dr >= 1.0, 'obstacle', 'plancher1R'))
        obj = rnd(e + d * objR * Rr)
        valide = ok & np.isfinite(a) & (a > 0) & np.isfinite(Rr) & (R > 0) & np.isfinite(sma[:] * 0 + 1)
        res['stop_' + suf] = np.where(valide, stop, np.nan)
        res['obj_' + suf] = np.where(valide, obj, np.nan)
        res['C_' + suf] = C; res['typ_' + suf] = typ; res['skip_' + suf] = skip; res['ok_' + suf] = np.isfinite(Rr)
    return res


def gestion_adaptative(df, A, instrument):
    return dict(instrument=instrument, plages_autorisees=PLAGES,
                stop={'mode': 'niveau', 'long': {'s': A['stop_l']}, 'short': {'s': A['stop_s']},
                      'marge_ticks': 0, 'min_atr': None, 'max_atr': None, 'sauter': True},
                objectif={'mode': 'niveau', 'long': {'o': A['obj_l']}, 'short': {'o': A['obj_s']},
                          'ratio_min': 0.0, 'si_absent': 'sauter'})


def gestion_fixe(instrument, R, k=2.0):
    return dict(instrument=instrument, plages_autorisees=PLAGES, stop={'mode': 'atr', 'k': k},
                objectif={'mode': 'R', 'k': R})
