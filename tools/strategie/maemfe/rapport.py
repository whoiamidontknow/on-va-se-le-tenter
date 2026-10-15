"""Rapport Markdown (français) de l'étude MAE/MFE."""
import datetime
import numpy as np
from zoneinfo import ZoneInfo
import etude, donnees

PARIS = ZoneInfo('Europe/Paris')


def f(x, nd=2, sg=False):
    if x is None: return '-'
    try:
        if not np.isfinite(x): return '-'
    except TypeError:
        return str(x)
    return ('%+.' + str(nd) + 'f' if sg else '%.' + str(nd) + 'f') % x


def pct(x):
    return '-' if x is None or not np.isfinite(x) else '%.0f %%' % (100 * x)


def nflag(n):
    return '%d' % n if n >= etude.NMIN else '%d (n<%d)' % (n, etude.NMIN)


def cible_txt(T):
    return 'aucun (temps)' if T is None else '%gR' % T


def date(ts):
    return datetime.datetime.fromtimestamp(ts, PARIS).strftime('%Y-%m-%d')


def gestion_txt(r):
    p = r['plan']; ch = r['choix']; out = []
    for nom, lib in (('be', 'BE'), ('suiveur', 'suiveur')):
        x = ch.get(nom)
        if not x: continue
        unite = 'R' if nom == 'be' else ' ATR'
        if p.get(nom) is not None:
            etat = 'utile (confirmé en validation)' if x['confirme'] else 'adopté en APPR, NON confirmé en validation'
        else:
            etat = 'inutile'
        out.append('%s %g%s : %s' % (lib, x['valeur'], unite, etat))
    return ' ; '.join(out)


def synthese_ligne(nom, r):
    p = r['plan']; v = r['res'].get('VAL', {}); a = r['res'].get('APPR', {})
    G = r['jeux']['APPR']['garde'].get(p['stop'], (np.nan, np.nan))
    be = '-' if p.get('be') is None else '%gR' % p['be']
    tr = '-' if p.get('suiveur') is None else '%g ATR' % p['suiveur']
    conf_bs = []
    for k in ('be', 'suiveur'):
        x = r['choix'].get(k)
        if x and p.get(k) is not None:
            conf_bs.append('oui' if x['confirme'] else 'non confirmé')
    return '| %s | %s / %s | %g (garde %s) | %s | %s / %s %s | %d | %s | %s [%s ; %s] | %s | %s | %s / %s | %s, %s |' % (
        nom, nflag(a.get('n', 0)), nflag(v.get('n', 0)), p['stop'], pct(G[0]), cible_txt(p['cible']), be, tr,
        ('(' + ', '.join(conf_bs) + ')') if conf_bs else '', p['hcap'], f(a.get('R'), 2, True),
        f(v.get('R'), 2, True), f(v.get('lo'), 2, True), f(v.get('hi'), 2, True), f(v.get('R_hasard'), 2, True),
        f(v.get('p'), 3), f(v.get('eratio')), f(v.get('eratio_hasard')), r['verdict']['texte'], r['verdict']['conf'])


def detail(nom, r, h_ref):
    L = []
    J = r['jeux']; p = r['plan']
    L.append('### %s\n' % nom)
    L.append('Coupure APPR/validation : %s (médiane des entrées %s). n : %s.\n' % (
        date(r['coupure']), r['inst_appr'],
        ', '.join('%s %d (%d j)' % (k, J[k]['n'], J[k]['jours']) for k in ('APPR', 'VAL_T', 'VAL_NQ', 'NQ_avant'))))
    # MAE/MFE par horizon
    L.append('**MAE / MFE moyens (ATR) par horizon** — e-ratio = MFE/MAE (1 = hasard symétrique) ; ret = clôture nette de coûts.\n')
    L.append('| Horizon | APPR MAE | APPR MFE | APPR e-ratio | APPR ret | VAL MAE | VAL MFE | VAL e-ratio | VAL ret |')
    L.append('|---|---|---|---|---|---|---|---|---|')
    for hz in etude.HORIZONS:
        a = J['APPR']['horizons'][hz]; v = J['VAL']['horizons'][hz]
        er = lambda x: x['mfe'] / x['mae'] if x['mae'] and np.isfinite(x['mae']) else np.nan
        L.append('| %d | %s | %s | %s | %s | %s | %s | %s | %s |' % (hz, f(a['mae']), f(a['mfe']), f(er(a)), f(a['ret'], 2, True),
                                                                f(v['mae']), f(v['mfe']), f(er(v)), f(v['ret'], 2, True)))
    tA, tV = J['APPR'].get('t_mfe'), J['VAL'].get('t_mfe')
    if tA or tV:
        s = lambda t: '-' if not t else 'médiane %g barres (q25 %g, q75 %g) ; atteint avant 8 barres : %s, avant 16 : %s' % (
            t['med'], t['q25'], t['q75'], pct(t['le8']), pct(t['le16']))
        L.append('\n**Instant du MFE sur 48 barres** — APPR : %s. VAL : %s.\n' % (s(tA), s(tV)))
    # gagnants / perdants
    L.append('**MAE (ATR) des gagnants vs perdants à %d barres** (quantiles 50/75/90/95 %%)\n' % h_ref)
    L.append('| Jeu | gagnants n | MAE gagnants | perdants n | MAE perdants |')
    L.append('|---|---|---|---|---|')
    for k in ('APPR', 'VAL_T', 'VAL_NQ', 'VAL'):
        g, pe = J[k]['gagnants'], J[k]['perdants']
        L.append('| %s | %d | %s | %d | %s |' % (k, g['n'], ' / '.join(f(x) for x in g['mae_q']), pe['n'],
                                              ' / '.join(f(x) for x in pe['mae_q'])))
    # courbe garde
    L.append('\n**% de gagnants conservés vs taille du stop** (et % de perdants que le stop laisse vivre)\n')
    L.append('| Stop (ATR) | APPR gagnants gardés | APPR perdants gardés | VAL gagnants gardés |')
    L.append('|---|---|---|---|')
    for s in etude.STOPS:
        a = J['APPR']['garde'][s]; v = J['VAL']['garde'][s]
        mark = ' <- retenu' if s == p['stop'] else ''
        L.append('| %g%s | %s | %s | %s |' % (s, mark, pct(a[0]), pct(a[1]), pct(v[0])))
    # courbe stop
    L.append('\n**Espérance vs taille du stop** (objectif %s, %d barres max) : en R, et en ATR par trade (= R x stop, comparable entre stops à 1 contrat)\n' % (cible_txt(p['cible']), p['hcap']))
    L.append('| Stop (ATR) | APPR R | VAL R | APPR ATR | VAL ATR |')
    L.append('|---|---|---|---|---|')
    for s_, x in r['courbe_stop'].items():
        mark = ' <- retenu' if s_ == p['stop'] else ''
        L.append('| %g%s | %s | %s | %s | %s |' % (s_, mark, f(x['APPR'], 3, True), f(x['VAL'], 3, True),
                                              f(x['APPR'] * s_, 3, True), f(x['VAL'] * s_, 3, True)))
    # courbe cible
    L.append('\n**Espérance (R nets) vs objectif**, stop %g ATR, sortie au temps à %d barres\n' % (p['stop'], r['cfg']['hcap_courbe']))
    L.append('| Objectif | APPR | VAL |')
    L.append('|---|---|---|')
    for T, x in r['courbe_cible'].items():
        mark = ' <- retenu' if T == p['cible'] else ''
        L.append('| %s%s | %s | %s |' % (cible_txt(T), mark, f(x['APPR'], 3, True), f(x['VAL'], 3, True)))
    L.append('\n**Espérance vs durée maximale de détention** (stop %g ATR, objectif %s)\n' % (p['stop'], cible_txt(p['cible'])))
    L.append('| Barres | APPR | VAL |')
    L.append('|---|---|---|')
    for hc, x in r['courbe_h'].items():
        mark = ' <- retenu' if hc == p['hcap'] else ''
        L.append('| %d%s | %s | %s |' % (hc, mark, f(x['APPR'], 3, True), f(x['VAL'], 3, True)))
    # BE / suiveur
    L.append('\n**Break-even et stop suiveur** : gain en R par trade par rapport au plan de base (même trades), IC 95 % bootstrap par jour\n')
    L.append('| Gestion | APPR delta [IC] | VAL delta [IC] |')
    L.append('|---|---|---|')
    for (nom2, val), x in r['options'].items():
        lib = 'break-even à +%gR' % val if nom2 == 'be' else 'suiveur %g ATR' % val
        L.append('| %s | %s [%s ; %s] | %s [%s ; %s] |' % (lib, f(x['APPR'][0], 3, True), f(x['APPR'][1], 2, True), f(x['APPR'][2], 2, True),
                                                       f(x['VAL'][0], 3, True), f(x['VAL'][1], 2, True), f(x['VAL'][2], 2, True)))
    L.append('\nGestion retenue : %s.\n' % (gestion_txt(r) or 'aucune'))
    # plan final
    pl = 'stop %g ATR, objectif %s, BE %s, suiveur %s, sortie au temps %d barres' % (
        p['stop'], cible_txt(p['cible']), '-' if p.get('be') is None else '%gR' % p['be'],
        '-' if p.get('suiveur') is None else '%g ATR' % p['suiveur'], p['hcap'])
    L.append('**Plan final (%s) vs hasard apparié** (même série, même période, même sens ; %d tirages)\n' % (pl, r['cfg']['M']))
    L.append('| Jeu | n | jours | E[R] net [IC 95 %%] | %% gagnants | E[R] hasard | excès sur hasard [IC 95 %%] | p | e-ratio %d | e-ratio hasard | p e-ratio |' % h_ref)
    L.append('|---|---|---|---|---|---|---|---|---|---|---|')
    for k in ('APPR', 'VAL_T', 'VAL_NQ', 'NQ_avant', 'VAL'):
        x = r['res'].get(k, {})
        if not x.get('n'):
            L.append('| %s | 0 | | | | | | | | | |' % k); continue
        L.append('| %s | %s | %d | %s [%s ; %s] | %s | %s | %s [%s ; %s] | %s | %s | %s | %s |' % (
            k, nflag(x['n']), x['jours'], f(x['R'], 3, True), f(x['lo'], 2, True), f(x['hi'], 2, True), pct(x['gain']),
            f(x['R_hasard'], 3, True), f(x['exces'], 3, True), f(x['exces_lo'], 2, True), f(x['exces_hi'], 2, True), f(x['p'], 3), f(x['eratio']), f(x['eratio_hasard']), f(x['p_er'], 3)))
    L.append('\nVerdict : **%s** — confiance %s.\n' % (r['verdict']['texte'], r['verdict']['conf']))
    return '\n'.join(L)


def ecrire(chemin, resultats, series, tfs, cfg, controle=None, sources='cache commun'):
    L = ['# Étude du stop et de la sortie par MAE/MFE\n']
    L.append('Généré le %s. Unités : %s min. Sources : %s.\n' % (
        datetime.datetime.now(PARIS).strftime('%Y-%m-%d %H:%M'), ', '.join(map(str, tfs)), sources))
    L.append('## Méthode\n')
    L.append('- Signaux calculés sur les bougies Heiken Ashi (comme l\'indicateur), **excursions mesurées aux vrais prix** '
             'reconstitués depuis le HA (`recon.py`, fiable en 15 min) ; tout en multiples de l\'ATR14 des vrais prix connu au signal.')
    L.append('- Entrée à l\'ouverture de la barre qui suit le signal. MAE = pire excursion contre le trade, MFE = meilleure '
             'excursion en faveur, sur 4 à 48 barres. Chaque signal est étudié isolément (chevauchements possibles).')
    L.append('- Coûts : 1 tick de glissement par côté + 1,25 $/contrat/côté (MES 5 $/pt, NQ 20 $/pt), retirés de chaque trade. '
             'Stop et objectif dans la même barre : stop. Objectif rempli seulement s\'il est dépassé d\'un tick.')
    L.append('- Jeux : coupure à la date médiane des entrées MES du déclencheur. **APPR** = MES avant (tous les choix y sont '
             'faits) ; **VAL_T** = MES après ; **VAL_NQ** = NQ après (instrument ET temps) ; NQ_avant = mêmes journées '
             'que APPR (pas indépendant, affiché pour info) ; **VAL** = VAL_T + VAL_NQ (verdict).')
    L.append('- Stop recommandé = plus petit stop qui garde >= %d %% des gagnants d\'APPR (gagnant = clôture nette > 0 à %d barres). '
             'Objectif et durée = meilleure espérance en APPR. Break-even / suiveur adoptés s\'ils améliorent APPR, '
             '« confirmés » s\'ils améliorent aussi VAL.' % (round(100 * cfg['garde']), cfg['h_ref']))
    L.append('- Référence aléatoire **appariée** : pour chaque trade, une barre tirée au hasard dans la même série, la même '
             'période et le même sens, gérée avec le même plan (%d tirages). p = le plus prudent de (a) la part des tirages '
             'au moins aussi bons et (b) le bootstrap par jour de l\'excès trade par trade sur la moyenne du hasard apparié '
             '(tient compte des signaux groupés le même jour). '
             'IC 95 %% par bootstrap des journées (une journée vue en 5, 15, 30 et 60 min ne compte qu\'une fois). '
             'Cases à n < %d signalées « (n<%d) » : pas de conclusion.' % (cfg['M'], etude.NMIN, etude.NMIN))
    L.append('- Verdict : « bat le hasard » si p < 0,05 sur VAL et si VAL_T et VAL_NQ sont chacun au-dessus du hasard '
             '(confiance élevée) ; p < 0,10 = fragile ; sinon non.\n')
    L.append('**Séries utilisées**\n')
    L.append('| Instrument | Unité | Du | Au | Barres |')
    L.append('|---|---|---|---|---|')
    for s in series:
        L.append('| %s | %s | %s | %s | %d |' % (donnees.instrument(s['sym']) + ('' if s['hasv'] else ' (sans volume : ni climax ni Detector)'),
                                             s['tf'], s['T'][0].strftime('%Y-%m-%d'), s['T'][-1].strftime('%Y-%m-%d'), s['n']))
    if controle:
        L.append('\n**Contrôle de la reconstitution des vrais prix (API 15 min, vrais prix connus)** : %s\n' % controle)
    L.append('\n## Synthèse\n')
    L.append('| Déclencheur | n APPR / VAL | Stop (ATR) | Objectif | BE / suiveur | Durée (barres) | E[R] APPR | E[R] VAL [IC 95 %] | Hasard VAL | p | e-ratio VAL / hasard | Verdict |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for nom, r in resultats.items():
        L.append(synthese_ligne(nom, r))
    L.append('\nLa ligne « Aléatoire » est la référence elle-même (son p ne mesure que le bruit des tirages).')
    L.append('\nE[R] = espérance nette de coûts par trade, en R (R = distance du stop). e-ratio = MFE/MAE moyens à %d barres.\n' % cfg['h_ref'])
    L.append('## Détail par déclencheur\n')
    for nom, r in resultats.items():
        L.append(detail(nom, r, cfg['h_ref']))
    open(chemin, 'w').write('\n'.join(L) + '\n')
