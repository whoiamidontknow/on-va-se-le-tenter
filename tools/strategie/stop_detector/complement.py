"""Compléments à etude.py (lit trades.pkl / respect.pkl, recharge les séries pour les placebos).

A. Placebo au niveau du trade : sur les trades où une zone est utilisable, on remplace la distance de la zone
   par celle d'un AUTRE trade utilisable (permutation, même déclencheur / unité / instrument / sens) :
   stop ATR « de même distance, placé au hasard ». Si la zone porte une information, le vrai stop Detector
   doit battre ce placebo (en R et en $). 200 permutations -> p unilatéral.
B. Tenue au niveau de la zone vs hasard : IC par bootstrap des JOURS de l'écart de tenue (ratio de sommes).
C. Synthèse par instrument (15 min, déclencheurs réunis hors aléatoire, et aléatoire) en R et en $.
Écrit complement.json et ajoute une section à resultats.md.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import regle, sim                  # noqa: E402
from core import boot_moyenne      # noqa: E402

M = 200
rng = np.random.default_rng(11)


def placebo(series, df):
    S_by = {id(S): S for S in series}
    out = {}
    base = df[(df['var'] == 'DET1.5') & df['zone']].copy()
    # id(S) a changé depuis etude.py : on rattache par (inst, tf, t)
    key = {(S['inst'], S['tfm'], S['T'][i].timestamp()): (S, i) for S in series for i in range(S['n'])}
    for sortie in ('cible', 'heishi'):
        for grp_nom, trigs in (('Declencheurs', ['Trendline', 'Climax BUY', 'Fleche Fort', 'Heishinator']),
                               ('Aleatoire', ['Aleatoire'])):
            for tf in (15, 5, 30, 60):
                for inst in ('MES', 'NQ'):
                    b = base[(base['sortie'] == sortie) & base['trig'].isin(trigs) & (base['tf'] == tf) & (base['inst'] == inst)]
                    if len(b) < 20: continue
                    SI = [key[(r.inst, r.tf, r.t)] for r in b.itertuples()]
                    d0 = b['dist_atr'].values; dd = b['d'].values; trg = b['trig'].values
                    obsR = b['R'].mean(); obsU = b['usd'].mean()
                    PR = np.zeros(M); PU = np.zeros(M)
                    for m in range(M):
                        perm = d0.copy()
                        for g in set(zip(trg, dd)):
                            k = np.where((trg == g[0]) & (dd == g[1]))[0]
                            perm[k] = d0[rng.permutation(k)]
                        Rs = []; Us = []
                        for (S, i), dist, d in zip(SI, perm, dd):
                            t = sim.trade(S, i, int(d), dist * S['ratr'][i], 2.0, sortie)
                            Rs.append(t['R']); Us.append(t['usd'])
                        PR[m] = np.mean(Rs); PU[m] = np.mean(Us)
                    out['%s|%s|%d|%s' % (sortie, grp_nom, tf, inst)] = dict(
                        n=len(b), R=float(obsR), R_placebo=float(PR.mean()), pR=float((1 + (PR >= obsR).sum()) / (M + 1)),
                        usd=float(obsU), usd_placebo=float(PU.mean()), pU=float((1 + (PU >= obsU).sum()) / (M + 1)))
                    print(sortie, grp_nom, tf, inst, out['%s|%s|%d|%s' % (sortie, grp_nom, tf, inst)], flush=True)
    return out


def tenue_boot(R, B=2000):
    out = {}
    for nom, m in (('15', R['tf'] == 15), ('15-60', R['tf'] >= 15), ('5', R['tf'] == 5),
                   ('15 MES', (R['tf'] == 15) & (R['inst'] == 'MES')), ('15 NQ', (R['tf'] == 15) & (R['inst'] == 'NQ'))):
        r = R[m]
        g = r.groupby('jour')
        A = pd.DataFrame(dict(near=g['near'].sum(), hold=g.apply(lambda x: (x['near'] & ~x['hit']).sum()),
                              nh=g['near_h'].sum(), hh=g['tenue_num_h'].sum()))
        v = A.values; G = len(v)
        W = rng.multinomial(G, np.full(G, 1 / G), size=B).astype(float)
        S = W @ v
        diff = S[:, 1] / S[:, 0] - S[:, 3] / S[:, 2]
        obs = v[:, 1].sum() / v[:, 0].sum() - v[:, 3].sum() / v[:, 2].sum()
        out[nom] = dict(n=int(len(r)), jours=G, ecart=float(obs), lo=float(np.quantile(diff, .025)),
                        hi=float(np.quantile(diff, .975)))
    return out


def synthese(df):
    out = {}
    k = ['trig', 'sid', 'i', 'd', 'sortie']
    for tf in (15, 5, 30, 60):
        for inst in ('MES', 'NQ'):
            for s in ('cible', 'heishi'):
                for nom, trg in (('Declencheurs', ['Trendline', 'Climax BUY', 'Fleche Fort', 'Heishinator']), ('Aleatoire', ['Aleatoire'])):
                    g = df[(df['tf'] == tf) & (df['inst'] == inst) & (df['sortie'] == s) & df['trig'].isin(trg)]
                    for v in ('ATR1.5', 'ATR2'):
                        A = g[g['var'] == ('DET1.5' if v == 'ATR1.5' else 'DET2')].set_index(k)
                        Bv = g[g['var'] == v].set_index(k)
                        j = A.join(Bv, lsuffix='_a', rsuffix='_b')
                        if len(j) == 0: continue
                        mU = boot_moyenne((j['usd_a'] - j['usd_b']).values, j['jour_a'].values)
                        mR = boot_moyenne((j['R_a'] - j['R_b']).values, j['jour_a'].values)
                        out['%d|%s|%s|%s|%s' % (tf, inst, s, nom, v)] = dict(
                            n=len(j), zone=float(j['zone_a'].mean()), stop_atr=float(j['stop_b'].mean()),
                            stop_det=float(j['stop_a'].mean()), R_atr=float(j['R_b'].mean()), R_det=float(j['R_a'].mean()),
                            usd_atr=float(j['usd_b'].mean()), usd_det=float(j['usd_a'].mean()),
                            dU=[float(x) for x in mU], dR=[float(x) for x in mR])
    return out


def main():
    df = pd.read_pickle(os.path.join(HERE, 'trades.pkl'))
    R = pd.read_pickle(os.path.join(HERE, 'respect.pkl'))
    series = regle.charger((5, 15, 30, 60))
    res = dict(synthese=synthese(df), tenue=tenue_boot(R), placebo=placebo(series, df))
    json.dump(res, open(os.path.join(HERE, 'complement.json'), 'w'), ensure_ascii=False, indent=1)
    L = ['', '## 4. Compléments', '', '### Synthèse par instrument (déclencheurs réunis hors aléatoire / aléatoire), Δ = DET - ATR même k, IC 95 % par jour', '',
         '| TF | inst | sortie | groupe | k | n | zone | stop ATR/DET | R ATR / DET | ΔR [IC] | $ ATR / DET | Δ$ [IC] |', '|' + '---|' * 12]
    for key, s in res['synthese'].items():
        tf, inst, so, nom, v = key.split('|')
        L.append('| %s | %s | %s | %s | %s | %d | %.0f%% | %.0f%% / %.0f%% | %+.3f / %+.3f | %+.3f [%+.3f ; %+.3f] | %+.1f / %+.1f | %+.1f [%+.1f ; %+.1f] |' % (
            tf, inst, so, nom, v, s['n'], 100 * s['zone'], 100 * s['stop_atr'], 100 * s['stop_det'], s['R_atr'], s['R_det'],
            *s['dR'], s['usd_atr'], s['usd_det'], *s['dU']))
    L += ['', '### Tenue (P(pas touché | prix venu à 0,25 ATR)) : zone - hasard même écart, IC par jour', '',
          '| TF | n | jours | écart tenue [IC 95 %] |', '|---|---|---|---|']
    for k_, s in res['tenue'].items():
        L.append('| %s | %d | %d | %+.1f [%+.1f ; %+.1f] pts |' % (k_, s['n'], s['jours'], 100 * s['ecart'], 100 * s['lo'], 100 * s['hi']))
    L += ['', '### Placebo : distance de zone permutée entre trades utilisables (même déclencheur, sens) — p = P(placebo >= réel)', '',
          '| sortie | groupe | TF | inst | n | R réel / placebo | p | $ réel / placebo | p |', '|' + '---|' * 9]
    for k_, s in res['placebo'].items():
        so, nom, tf, inst = k_.split('|')
        L.append('| %s | %s | %s | %s | %d | %+.3f / %+.3f | %.2f | %+.1f / %+.1f | %.2f |' % (
            so, nom, tf, inst, s['n'], s['R'], s['R_placebo'], s['pR'], s['usd'], s['usd_placebo'], s['pU']))
    with open(os.path.join(HERE, 'resultats.md'), 'a') as fh:
        fh.write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
