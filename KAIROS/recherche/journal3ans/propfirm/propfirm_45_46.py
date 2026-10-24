"""Préréglages 45 / 46 (exports testeur TradingView 3 ans) au simulateur propfirm. 17/10/2026."""
import glob, os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'propfirm'))
import simulateur as S

DOSSIER = os.path.expanduser('~/Ephore/Strat-Botting-data/45*46')
VARIANTES = ['tradeify_50k_select_flex', 'tradeify_50k_growth', 'lucid_50k_flex_sans_dll', 'apex_50k_eod']
TAILLES = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
KW = dict(max_jours_eval=250, max_jours_funded=250, max_payouts=5, bloc_jours=5, n_sim=1000, ordre='heuristique')


def charge(f):
    x = pd.ExcelFile(f)
    P = dict(zip(*[x.parse('Propriétés')[c].astype(str) for c in ('name', 'value')]))
    T = x.parse('Trades')
    en = T[T['Type'].str.startswith('Entrer')].set_index('Numéro de trade')
    ex = T[T['Type'].str.startswith('Sortir')].set_index('Numéro de trade')
    q = ex['Taille (qté)'].astype(float)          # micros par trade dans l'export
    tz = lambda s: pd.to_datetime(s).dt.tz_localize('Europe/Paris', ambiguous='NaT', nonexistent='shift_forward')
    t = pd.DataFrame({'entree_t': tz(en['Date et heure']), 'sortie_t': tz(ex['Date et heure']),
                      'sens': ['long' if 'long' in s else 'short' for s in ex['Type']],
                      'pnl_usd': ex['P&L net USD'] / q, 'mae_usd': ex['Excursion adverse USD'] / q,
                      'mfe_usd': ex['Excursion favorable USD'] / q}).dropna().reset_index(drop=True)
    return P.get('Symbole', '').split(':')[-1], P.get('Préréglage', '')[:2], t


R = S.charge_regles()
lignes = []
for f in sorted(glob.glob(os.path.join(glob.escape(DOSSIER), '*.xlsx'))):
    sym, pre, t = charge(f)
    if not sym.startswith(('MNQ', 'MES')) or pre not in ('45', '46'):
        continue
    for v in VARIANTES:
        df, best = S.optimise_taille(t, R[v], TAILLES, **KW)
        ch = S.monte_carlo(t, R[v], int(best['contrats']), methode='chronologique',
                           **{k: KW[k] for k in ('max_jours_eval', 'max_jours_funded', 'max_payouts', 'ordre')})
        lignes.append(dict(symbole=sym, prereglage=pre, variante=v, micros=int(best['contrats']),
                           p_reussite=best['p_reussite'], p_chrono=ch['p_reussite'],
                           delai_j=best['delai_median_jours'], p_1er_payout=best['p_1er_payout'],
                           p_3_payouts=best.get('p_3_payouts', float('nan')),
                           valeur_esperee=best.get('valeur_esperee_usd', float('nan')),
                           gain_payouts=best.get('payouts_nets_moyens_usd', float('nan'))))
        print(lignes[-1], flush=True)
out = pd.DataFrame(lignes)
out.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resultats_propfirm.csv'), index=False)
print(out.to_string(index=False))
