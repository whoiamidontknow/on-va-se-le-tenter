"""Rapport Markdown (français) + courbe des gains hors échantillon (PNG si matplotlib, sinon texte)."""
import os, re, datetime
import numpy as np
from espace import bloc_pine, decrire

_MOT = re.compile('e' + 'phore', re.I)
SURF, INK, INK2, GRID, BLUE = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df', '#2a78d6'


def propre(s):
    return _MOT.sub('…', s)


def f2(x, fmt='%+.2f'):
    return '—' if x is None or (isinstance(x, float) and not np.isfinite(x)) else fmt % x


def ic(t, fmt='%+.2f'):
    return '[%s ; %s]' % (f2(t[0], fmt), f2(t[1], fmt)) if t else '—'


def courbe_png(path, oos, folds_dates):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        return False
    t = [datetime.datetime.fromtimestamp(o['t']) for o in oos]
    eqR = np.cumsum([o['R'] for o in oos]); eqU = np.cumsum([o['usd'] for o in oos])
    fig, ax = plt.subplots(2, 1, figsize=(9, 5.6), sharex=False, facecolor=SURF)
    for a_, y, lab in ((ax[0], eqR, 'Gain cumulé hors échantillon (R)'), (ax[1], eqU, 'Gain cumulé hors échantillon ($, 1 contrat, coûts inclus)')):
        a_.set_facecolor(SURF)
        x = np.arange(1, len(y) + 1)
        a_.plot(x, y, color=BLUE, lw=2)
        a_.axhline(0, color=INK2, lw=0.8)
        a_.grid(axis='y', color=GRID, lw=0.6)
        for s in ('top', 'right'):
            a_.spines[s].set_visible(False)
        for s in ('left', 'bottom'):
            a_.spines[s].set_color(GRID)
        a_.tick_params(colors=INK2, labelsize=8)
        a_.set_title(lab, loc='left', color=INK, fontsize=10)
        # changements de pli
        prev = None
        for k, o in enumerate(oos):
            if prev is not None and o['fold'] != prev:
                a_.axvline(k + 0.5, color=GRID, lw=1, ls='--')
            prev = o['fold']
        if len(y):
            a_.annotate('%+.1f' % y[-1], (x[-1], y[-1]), textcoords='offset points', xytext=(4, 0), color=INK, fontsize=8, va='center')
    ax[1].set_xlabel('trades hors échantillon, dans l\'ordre (pointillés = changement de pli)', color=INK2, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURF)
    plt.close(fig)
    return True


def courbe_texte(oos, largeur=60, hauteur=10):
    y = np.cumsum([o['R'] for o in oos])
    if len(y) < 2:
        return '(pas assez de trades)'
    xs = np.linspace(0, len(y) - 1, min(largeur, len(y))).astype(int)
    v = y[xs]; lo, hi = min(v.min(), 0), max(v.max(), 0)
    rows = []
    for r in range(hauteur, -1, -1):
        lvl = lo + (hi - lo) * r / hauteur
        line = ''.join('█' if (vv >= lvl if lvl >= 0 else vv <= lvl) and (lvl != 0) else ('─' if abs(lvl) < (hi - lo) / hauteur / 2 else ' ') for vv in v)
        rows.append('%+7.1f │%s' % (lvl, line))
    return '\n'.join(rows)


def ecrire(dossier, ctx):
    os.makedirs(dossier, exist_ok=True)
    L = []
    w = L.append
    V = ctx['verdict']
    w('# Optimiseur conjoint entrée × stop × sortie — rapport')
    w('')
    w('*Généré le %s — unité %s min — symboles %s — %s*' % (ctx['date'], ctx['tf'], ', '.join(ctx['racines']), ctx['source_txt']))
    w('')
    w('## Verdict : %s' % V['titre'])
    w('')
    for x in V['raisons']:
        w('- ' + x)
    w('')
    w('## Données')
    w('')
    for x in ctx['univers']:
        w('- ' + x)
    w('- %d jours de bourse au total. Chauffe coupée : %d barres par série.' % (ctx['D'], ctx['warmup']))
    w('- Coûts : %d tick de glissement par côté + %.2f $ par contrat et par côté ; valeur du point : %s.'
      % (ctx['slip'], ctx['comm'], ', '.join('%s %g $' % (r, p) for r, p in ctx['points'])))
    w('')
    w('## Méthode')
    w('')
    w('- Recherche : %d réglages tirés au hasard (+ grille réduite par déclencheur) puis, à chaque pli, tous les '
      'voisins des %d meilleurs : **%d réglages distincts évalués**, %d configurations de trade simulées.'
      % (ctx['n_alea'], ctx['topk'], ctx['N'], ctx['n_sim']))
    w('- Walk-forward glissant : %d jours d\'apprentissage, %d jours de test, %d plis. %s'
      % (ctx['L'], ctx['T'], len(ctx['choix']), ctx['note_wf']))
    w('- Sélection d\'une **zone stable** : score = quantile %.0f %% du score (%s) sur le réglage et ses voisins '
      '(une valeur voisine de chaque paramètre ordonné) ; au moins %d trades en apprentissage.'
      % (100 * ctx['qplat'], ctx['objectif'], ctx['min_app']))
    w('- Biais de sélection : Deflated Sharpe Ratio (N = essais distincts) et Reality Check de White / SPA de Hansen '
      '(bootstrap stationnaire par jour, %d tirages).' % ctx['spa_B'])
    w('- Intervalles de confiance : bootstrap par JOUR (%d tirages) ; ruine : Monte Carlo, %g %% de risque par trade, '
      'ruine = -%g %% du capital, horizon %d trades.' % (ctx['B'], ctx['risque'], ctx['ruine_pct'], ctx['horizon']))
    w('')
    w('## Résultat hors échantillon (plis de test concaténés)')
    w('')
    o = ctx['oos_stats']; b = ctx['oos_boot']; r = ctx['oos_ruine']
    w('| Mesure | Valeur | IC 95 % (bootstrap par jour) |')
    w('|---|---|---|')
    w('| Trades | %d | minimum exigé : %d |' % (o['n'], ctx['min_trades']))
    w('| R moyen par trade | %s | %s |' % (f2(o['moy'], '%+.3f'), ic(b.get('moy'), '%+.3f')))
    w('| Profit factor | %s | %s |' % (f2(o['pf'], '%.2f'), ic(b.get('pf'), '%.2f')))
    w('| Gagnants | %s | %s |' % (f2(100 * o['gain'] if o['n'] else np.nan, '%.0f %%'), ic(tuple(100 * x for x in b['gain']) if b.get('gain') else None, '%.0f %%')))
    w('| Drawdown max (R) | %s | %s |' % (f2(o['dd'], '%.1f'), ic(b.get('dd'), '%.1f')))
    w('| Total (R) | %s | %s |' % (f2(o['tot'], '%+.1f'), ic(b.get('tot'), '%+.1f')))
    w('| Total ($, 1 contrat) | %s | |' % f2(ctx['oos_usd'], '%+.0f'))
    w('| P(R moyen > 0) | %s | |' % f2(b.get('p_moy_pos', np.nan), '%.2f'))
    w('| Probabilistic Sharpe (journalier, vs 0) | %s | |' % f2(ctx['psr_oos'], '%.2f'))
    w('| Probabilité de ruine (Monte Carlo) | %s | drawdown médian %s, 95e centile %s |' % (
        f2(100 * r['p_ruine'], '%.1f %%'), f2(100 * r.get('dd_med', np.nan), '%.0f %%'), f2(100 * r.get('dd_p95', np.nan), '%.0f %%')))
    w('')
    if ctx.get('png'):
        w('![Courbe des gains hors échantillon](%s)' % os.path.basename(ctx['png']))
    else:
        w('```')
        w(courbe_texte(ctx['oos']))
        w('```')
    w('')
    w('### Choix de chaque pli')
    w('')
    w('| Pli | Apprentissage | Test | Réglage choisi | Plateau | Trades appr. | Trades test | R moyen test |')
    w('|---|---|---|---|---|---|---|---|')
    for c in ctx['choix']:
        w('| %d | %s | %s | %s | %s | %d | %d | %s |' % (c['fold'] + 1, c['appr_txt'], c['test_txt'],
                                                     decrire(c['reglage']) if c.get('reglage') else 'aucun',
                                                     f2(c['plateau']), c['n_appr'], c['n_test'], f2(c.get('moy_test', np.nan), '%+.3f')))
    w('')
    w('Stabilité : %s' % ctx['stabilite'])
    w('')
    w('## Biais de sélection (échantillon complet)')
    w('')
    w('- Reality Check de White : p = %s ; SPA de Hansen : p = %s (H0 : aucun des %d réglages ne bat « ne rien faire »).'
      % (f2(ctx['p_rc'], '%.3f'), f2(ctx['p_spa'], '%.3f'), ctx['K_spa']))
    w('- Deflated Sharpe du réglage retenu : %s (Sharpe journalier %s ; Sharpe attendu du meilleur de %d essais '
      'distincts sans talent : %s ; %d réglages évalués, dont %d aux rendements distincts avec assez de trades).'
      % (f2(ctx['dsr'], '%.2f'), f2(ctx['sr_final'], '%.3f'), ctx['N_eff'], f2(ctx['sr0'], '%.3f'), ctx['N'], ctx['N_eff']))
    w('')
    w('## Meilleurs réglages sur tout l\'historique (zone stable, EN ÉCHANTILLON)')
    w('')
    w('Classés par score de plateau. Ces chiffres sont mesurés sur les données qui ont servi au choix : ils sont '
      'optimistes par construction. Seul le résultat hors échantillon ci-dessus fait foi.')
    w('')
    w('| # | Réglage | Pine ? | Plateau | Trades | R moyen [IC 95 %] | PF [IC 95 %] | DD max R | Médiane voisins |')
    w('|---|---|---|---|---|---|---|---|---|')
    for i, t in enumerate(ctx['top']):
        w('| %d | %s | %s | %s | %d | %s %s | %s %s | %s | %s |' % (
            i + 1, decrire(t['reglage']), 'oui' if t['pine'] else 'non', f2(t['plateau']), t['st']['n'],
            f2(t['st']['moy'], '%+.3f'), ic(t['boot'].get('moy'), '%+.3f'), f2(t['st']['pf'], '%.2f'),
            ic(t['boot'].get('pf'), '%.2f'), f2(t['st']['dd'], '%.1f'), f2(t['med_v'])))
    w('')
    w('## Réglages à recopier dans STRATEGIE_V1.pine')
    w('')
    if V['retenue']:
        w('Réglage RETENU (validé hors échantillon) :')
    else:
        w('**Aucun réglage n\'est validé.** Le bloc ci-dessous est seulement le meilleur plateau sur l\'historique '
          'complet, à tester au testeur de TradingView sur un historique long — PAS à trader.')
    w('')
    for titre, c in ctx['blocs']:
        w('*%s* — %s' % (titre, decrire(c)))
        w('')
        w('```pine')
        w('// Onglet Paramètres de « Stratégie V1 », ou défauts des input.* dans STRATEGIE_V1.pine')
        for x in bloc_pine(c, ctx['cfg'], ctx['racines']):
            w(x)
        w('```')
        w('')
    w('## Limites')
    w('')
    for x in ctx['limites']:
        w('- ' + x)
    w('')
    w('*Temps de calcul : %s.*' % ctx['temps'])
    txt = propre('\n'.join(L) + '\n')
    p = os.path.join(dossier, 'rapport.md')
    open(p, 'w').write(txt)
    return p
