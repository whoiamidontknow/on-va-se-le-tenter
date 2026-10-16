"""4. Trades réels du testeur TradingView (préréglage A, 15 min, NQ1! et ES1!) face aux pivots.

LIMITE DE DONNÉES (mesurée ici) : les trades sont en NQ1!/ES1! ajustés (back-adjust). Nos seuls journaliers
longs sont ceux du contrat Z2026 (NQZ2026 depuis 2023, MESZ2026 depuis sept. 2025). Avant que le Z2026
ne traite vraiment (volume nul jusqu'en mai 2026), son historique ne colle pas au NQ1! ajusté (écart de
plusieurs centaines de points, variable dans le mois) : les pivots de 2023-2025 ne sont PAS reconstituables.
À partir de juin 2026, NQ1! ajusté = prix du Z2026 (à quelques points) : l'étude porte sur juin -> oct. 2026.
On le vérifie : part des prix d'entrée compris dans la bougie journalière du Z2026 du même jour.

Pour chaque trade (R = 2 ATR estimé par ../testeur_1er_jet/risque.py, MFE/MAE exacts du testeur) :
  (a) pivot (annuel/mensuel/weekly, HA ou REEL) situé SOUS l'entrée à moins de 1 R (là où on aurait pu
      mettre le stop derrière) : taux de stop et R moyen avec / sans ;
  (b) le plus bas atteint (MAE) s'est-il arrêté à ±0,1 R AU-DESSUS d'un pivot (le pivot a « tenu ») ?
  (c) le plus haut atteint (MFE) s'est-il arrêté à ±0,1 R SOUS un pivot (le pivot a « bloqué ») ?
  Contrôle placebo : mêmes trades, tous les niveaux décalés d'un même écart (±0,7 ; ±1,3 ; ±1,9 R moyen),
  ce qui garde la structure des niveaux et casse leur position.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'testeur_1er_jet'))
import numpy as np
import pandas as pd
import niveaux as nv          # noqa: E402
import charge, risque         # noqa: E402

DEBUT = pd.Timestamp('2026-06-01')
SRC = {'NQ': 'NQZ', 'ES': 'MES'}
SHIFTS = (-1.9, -1.3, -0.7, 0.7, 1.3, 1.9)


def niveaux_jour(daily):
    tabs = {k: nv.pivot_sets(daily, k, m) for k, m in (('Y', 150), ('M', 15), ('W', 4))}
    def f(d, bases=('HA', 'REEL'), kinds=('Y', 'M', 'W')):
        out = []
        for k in kinds:
            s = tabs[k].get(nv.pkey(d, k))
            if not s: continue
            for b in bases:
                if b in s: out += [(k + '_' + b, nm, v) for nm, v in s[b].items()]
        return out
    return f


def table(sym):
    out, _, _ = risque.estime_tous()
    d = out[sym].copy()
    d = d[d['entree_dt'] >= DEBUT]
    daily = nv.daily_hybrid(SRC[sym]); f = niveaux_jour(daily)
    rows = []
    for n_, r in d.iterrows():
        dt = r['entree_dt'].tz_localize(nv.PARIS)
        td = nv.tdate(dt.to_pydatetime())
        lv = f(td)
        if not lv or td not in daily: continue
        o, h, l, c = daily[td]
        rows.append(dict(n=n_, sym=sym, dt=r['entree_dt'], px=r['px_e'], R=r['R'], pnl=r['pnl'], stop=r['stop'],
                         mfe=r['mfe_pts'], mae=r['mae_pts'], pts=r['pts'], inside=(l - 1 <= r['px_e'] <= h + 1), lv=lv,
                         jour=td.toordinal()))
    return pd.DataFrame(rows)


def mesures(T, shift_R=0.0, kinds=('Y', 'M', 'W'), base=None):
    """Pour chaque trade : pivot proche sous l'entrée (<= 1 R), MAE arrêté sur un pivot, MFE arrêté sous un pivot."""
    Rm = T['R'].median()
    res = []
    for _, t in T.iterrows():
        L = np.array([v + shift_R * Rm for k, nm, v in t['lv'] if k[0] in kinds and (base is None or k.endswith(base))])
        if len(L) == 0: res.append((False, False, False)); continue
        z = (t['px'] - L) / t['R']
        sous = bool(((z > 0.05) & (z <= 1.0)).any())
        low = t['px'] - t['mae']; high = t['px'] + t['mfe']
        zl = (low - L) / t['R']; zh = (L - high) / t['R']
        mae_tenu = bool(((zl >= -0.02) & (zl <= 0.10) & (L < t['px'])).any())
        mfe_bloque = bool(((zh >= -0.02) & (zh <= 0.10) & (L > t['px'])).any())
        res.append((sous, mae_tenu, mfe_bloque))
    a = np.array(res)
    return a[:, 0], a[:, 1], a[:, 2]


def resume(T, kinds, base):
    sous, mt, mb = mesures(T, 0.0, kinds, base)
    plc = [mesures(T, s, kinds, base) for s in SHIFTS]
    rec = dict(niveaux='+'.join(kinds) + ' ' + (base or 'HA+REEL'), n=len(T),
               part_sous=sous.mean(), part_sous_plc=np.mean([p[0].mean() for p in plc]))
    Rr = (T['pnl'] / (T['R'] * np.where(T['sym'] == 'NQ', 20, 50))).values
    st = T['stop'].values.astype(float)
    if sous.sum() >= 10 and (~sous).sum() >= 10:
        rec.update(stop_avec=st[sous].mean(), stop_sans=st[~sous].mean(), R_avec=Rr[sous].mean(), R_sans=Rr[~sous].mean())
        dp = [st[p[0]].mean() - st[~p[0]].mean() for p in plc if p[0].sum() >= 10 and (~p[0]).sum() >= 10]
        rec['d_stop'] = rec['stop_avec'] - rec['stop_sans']; rec['d_stop_plc'] = float(np.mean(dp)) if dp else np.nan
        rec['d_stop_plc_min'] = float(np.min(dp)) if dp else np.nan; rec['d_stop_plc_max'] = float(np.max(dp)) if dp else np.nan
    rec['mae_tenu'] = mt.mean(); rec['mae_tenu_plc'] = np.mean([p[1].mean() for p in plc])
    rec['mae_tenu_plc_max'] = np.max([p[1].mean() for p in plc])
    rec['mfe_bloque'] = mb.mean(); rec['mfe_bloque_plc'] = np.mean([p[2].mean() for p in plc])
    rec['mfe_bloque_plc_max'] = np.max([p[2].mean() for p in plc])
    # binomiale approximative contre le placebo moyen
    for k in ('mae_tenu', 'mfe_bloque'):
        p0 = rec[k + '_plc']; nobs = len(T)
        rec['z_' + k] = (rec[k] - p0) / np.sqrt(max(p0 * (1 - p0), 1e-9) / nobs)
    return rec


if __name__ == '__main__':
    pd.set_option('display.width', 250)
    Ts = []
    for sym in ('NQ', 'ES'):
        T = table(sym)
        print(sym, 'trades depuis', DEBUT.date(), ':', len(T), '| entrée dans la bougie 1D du Z2026 :', '%.0f %%' % (100 * T['inside'].mean()))
        Ts.append(T)
    T = pd.concat(Ts, ignore_index=True)
    T = T[T['inside']]
    print('gardés (entrée cohérente avec le journalier) :', len(T), T.groupby('sym').size().to_dict())
    rows = []
    for kinds in (('Y', 'M', 'W'), ('Y', 'M'), ('W',), ('M',), ('Y',)):
        for base in (None, 'HA', 'REEL'):
            rows.append(resume(T, kinds, base))
    R = pd.DataFrame(rows)
    print(R.to_string(index=False, float_format=lambda x: '%.3f' % x))
    R.to_csv(os.path.join(HERE, 'trades_reels.csv'), index=False)
