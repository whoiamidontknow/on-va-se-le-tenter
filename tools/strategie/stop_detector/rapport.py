"""Tableaux lisibles (resultats.md) à partir de resultats.json."""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
TRIGS = ['Trendline', 'Preset C', 'Climax BUY', 'Preset A', 'Fleche Fort', 'Heishinator', 'Aleatoire']


def f(x, n=2, s=False):
    if x is None: return '-'
    return ('%+.' + str(n) + 'f' if s else '%.' + str(n) + 'f') % x


def ic(d):
    if not d or d.get('n', 0) == 0: return '-'
    return '%+.1f [%+.1f ; %+.1f]' % (d['m'], d['lo'], d['hi'])


def main():
    R = json.load(open(os.path.join(HERE, 'resultats.json')))
    L = ['# Stop Zone Detector vs stop ATR — résultats bruts (indicatifs)', '',
         'Coupures temps (1re/2e moitié) : ' + ', '.join('%s min : %s' % (k, v[:16]) for k, v in R['coupures'].items()), '',
         '## 1. Comparaison appariée (chaque signal = un trade isolé, 1 contrat, coûts inclus)', '',
         'zone = part des trades avec zone utilisable ; dist = stop moyen (ATR) ; stop = part sortie au stop ; '
         '$ = espérance par trade (1 contrat) ; Δ$ = DET - ATR même k, apparié, IC 95 % bootstrap par jour.', '']
    for sortie in ('cible', 'heishi'):
        L += ['### Sortie : %s' % ('objectif 2R' if sortie == 'cible' else 'changement Heishinator'), '',
              '| déclencheur | TF | jeu | n | zone | dist DET1.5 | stop ATR1.5 / DET1.5 | R ATR1.5 / DET1.5 | PF ATR1.5 / DET1.5 | $ ATR1.5 / DET1.5 / ATR2 / DET2 | Δ$ DET1.5-ATR1.5 | Δ$ DET2-ATR2 | Δ$ zone seule DET-ATR1.5 |',
              '|' + '---|' * 13]
        for trig in TRIGS:
            for tf in ('15', '5', '30', '60'):
                for jeu in ('TOUT', 'MES_1', 'MES_2', 'NQ_1', 'NQ_2'):
                    c = R['comparaison'].get('%s|%s|%s|%s' % (trig, tf, sortie, jeu))
                    if not c or not c['ATR1.5']: continue
                    if tf != '15' and jeu != 'TOUT': continue
                    a, b, a2, b2 = c['ATR1.5'], c['DET1.5'], c['ATR2'], c['DET2']
                    L.append('| %s | %s | %s | %d | %.0f%% | %.2f | %.0f%% / %.0f%% | %s / %s | %s / %s | %s / %s / %s / %s | %s | %s | %s |' % (
                        trig, tf, jeu, a['n'], 100 * b['zone'], b['dist'], 100 * a['stop'], 100 * b['stop'],
                        f(a['R'], 3, True), f(b['R'], 3, True), f(min(a['pf'], 99)), f(min(b['pf'], 99)),
                        f(a['usd'], 1, True), f(b['usd'], 1, True), f(a2['usd'], 1, True), f(b2['usd'], 1, True),
                        ic(c['d15']), ic(c['d2']), ic(c['zone_d15'])))
        L.append('')
    L += ['## 2. La zone retient-elle le prix ? (toutes les barres, long et short, zone utilisable, %s barres)' % 16, '',
          'hit = stop au niveau de la zone touché ; hasard = même écart (ATR) sur une barre tirée au hasard, même série/sens ; '
          'tenue = P(pas touché | prix venu à 0,25 ATR du niveau) ; profil = tenue pour un niveau décalé de δ ATR (même barre).', '',
          '| TF | jeu | n | jours | écart moy (ATR) | hit zone | hit hasard | Δhit [IC] | p | tenue zone | tenue hasard | p | profil -0.5/-0.25/0/+0.25/+0.5 |',
          '|' + '---|' * 13]
    for k, s in R['respect'].items():
        tf, jeu = k.split('|')
        pr = '/'.join('%.2f' % s['profil'][x] for x in ('-0.50', '-0.25', '+0.00', '+0.25', '+0.50'))
        L.append('| %s | %s | %d | %d | %.2f | %.1f%% | %.1f%% | %+.1f [%+.1f ; %+.1f] pts | %.3f | %.1f%% | %.1f%% | %.3f | %s |' % (
            tf, jeu, s['n'], s['jours'], s['d0'], 100 * s['hit'], 100 * s['hit_hasard'], 100 * s['ecart'],
            100 * s['ecart_lo'], 100 * s['ecart_hi'], s['p_hit'], 100 * s['tenue'], 100 * s['tenue_hasard'], s['p_tenue'], pr))
    L += ['', '## 3. Position unique (comme le Pine), 15 min', '', '| préréglage | instrument | stop | n | zone | stop touché | R | PF | $/trade | total $ |',
          '|' + '---|' * 10]
    for k, s in R['sequentiel'].items():
        p, inst, v = k.split('|')
        L.append('| %s | %s | %s | %d | %.0f%% | %.0f%% | %+.3f | %.2f | %+.1f | %+.0f |' % (
            p, inst, v, s['n'], 100 * s['zone'], 100 * s['stop'], s['R'], min(s['pf'], 99), s['usd'], s['tot']))
    open(os.path.join(HERE, 'resultats.md'), 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
