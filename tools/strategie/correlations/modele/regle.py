"""Extraction d'une règle simple (arbre de profondeur 2-3) et test hors échantillon avec engine.py.

Pour chaque pli walk-forward : l'arbre est appris UNIQUEMENT sur les barres dont la cible est résolue avant
le pli (il choisit lui-même ses variables) ; on garde la meilleure feuille (>= 300 barres d'entraînement) si
son taux de réussite dépasse la base de +3 points ; on trade ses barres dans le pli suivant.
Exécution : engine.run, coûts inclus, stop 1,5 ATR, objectif 2R, sortie au changement Heishinator.
Référence : mêmes réglages, entrée sur TOUTES les barres du pli (une position à la fois) dans le même sens.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sklearn.tree import DecisionTreeClassifier
import dataset, build_all, engine as E, strat as ST
import models as M

SER = {}
for S in build_all.load():
    if S['tfm'] not in (5, 15, 30, 60): continue
    if S['sym'] == 'MES1' and not (S['tfm'] == 15 and S['T'][0].month < 8): continue
    SER['%s_%s_%s' % (S['sym'], S['tf'], S['T'][0].strftime('%m%d'))] = S
KW = dict(stop=('atr', 1.5), target=2, exit_on=ST.x_heishi)


def leaf_rules(tree, cols):
    t = tree.tree_; out = []
    def rec(node, conds):
        if t.children_left[node] == -1:
            v = t.value[node][0]; out.append((conds, v[1] / v.sum(), int(t.n_node_samples[node]))); return
        f, th = cols[t.feature[node]], t.threshold[node]
        rec(t.children_left[node], conds + [(f, '<=', th)]); rec(t.children_right[node], conds + [(f, '>', th)])
    rec(0, []); return out


def apply(conds, df):
    m = np.ones(len(df), bool)
    for f, op, th in conds:
        x = df[f].values
        m &= (x <= th) if op == '<=' else (x > th)   # NaN -> faux
    return m


def run_side(side, depth):
    yk = 'y' + side; d = 1 if side == 'L' else -1; trades = []; base = []
    print('\n== %s profondeur %d' % ('LONG' if side == 'L' else 'SHORT', depth))
    for k, (a, b) in enumerate(M.folds()):
        tr = M.CSV[(M.CSV['t_res' + side] < a) & M.CSV[yk].notna()]
        X = tr[M.FEATS].fillna(-999).values
        tree = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=300, random_state=0).fit(X, tr[yk].values)
        rules = [r for r in leaf_rules(tree, M.FEATS) if r[2] >= 300]
        p0 = tr[yk].mean(); best = max(rules, key=lambda r: r[1])
        te = M.CSV[(M.CSV.t >= a) & (M.CSV.t < b)]
        txt = ' ET '.join('%s %s %.3g' % c for c in best[0])
        if best[1] < p0 + 0.03:
            print('  pli %d : aucune feuille > base+3 pts (base %.3f, meilleure %.3f) -> pas de trade' % (k + 1, p0, best[1])); continue
        # la valeur -999 (manquant) est traitée comme « petite » par l'arbre ; on reproduit ce choix
        hit = apply(best[0], te.fillna(-999))
        yy = te.loc[hit, yk].dropna()
        ftr = []; fb = []
        for sn, g in te.groupby('serie'):
            S = SER[sn]; ii = g.i.values; h = hit[te.serie.values == sn]
            ftr += E.run(S, [(int(i), d) for i in ii[h]], **KW)
            fb += E.run(S, [(int(i), d) for i in ii], **KW)
        trades += ftr; base += fb
        st = E.stats(ftr); sb = E.stats(fb)
        print('  pli %d : SI %s  (train %.3f vs base %.3f, n=%d) | cible OOS %.3f vs %.3f (n=%d)' % (
            k + 1, txt, best[1], p0, best[2], yy.mean() if len(yy) else np.nan, te[yk].mean(), len(yy)))
        print('          règle   %s' % E.fmt(st)); print('          réf.    %s' % E.fmt(sb))
    for name, tt in (('RÈGLE', trades), ('RÉFÉRENCE (toutes barres)', base)):
        if not tt: print('  %s : aucun trade' % name); continue
        R = np.array([t['R'] for t in tt]); tstat = R.mean() / (R.std(ddof=1) / np.sqrt(len(R))) if len(R) > 1 else np.nan
        print('  TOTAL OOS %-26s %s  t=%.2f' % (name, E.fmt(E.stats(tt)), tstat))
        by = {}
        for t in tt: by.setdefault(t['sym'] + ' ' + t['tf'], []).append(t['R'])
        print('     par série :', ', '.join('%s n%d %+.2f' % (kk, len(v), np.mean(v)) for kk, v in sorted(by.items())))


if __name__ == '__main__':
    for side in ('L', 'S'):
        for depth in (2, 3):
            run_side(side, depth)
