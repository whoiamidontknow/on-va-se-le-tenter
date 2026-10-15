"""Optimiseur conjoint entrée × filtres × stop × sortie, walk-forward, zone stable, biais de sélection corrigé.

Exemples :
  python tools/strategie/optim/run.py --data "/Users/jeremk/Jeu 15:10" --tf 15 --symboles NQ,MES
  python tools/strategie/optim/run.py --data DOSSIER1 DOSSIER2 --tf 15 --apprentissage 120 --test 20
  python tools/strategie/optim/run.py --data DOSSIER_API --tf 15            (JSON api_vitrine_*.json)
Le rapport (rapport.md + courbe_oos.png + trades_oos.csv + resultats.json) est écrit dans --sortie.
"""
import os, sys, time, json, argparse, datetime, copy
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import donnees, espace, univers, optimiseur, robustesse as RB, rapport


def main(argv=None):
    ap = argparse.ArgumentParser(description='Optimiseur walk-forward de STRATEGIE_V1')
    ap.add_argument('--data', nargs='+', required=True, help='dossier(s) d\'exports TradingView (récursif) ou fichiers')
    ap.add_argument('--tf', required=True, help='unité en minutes (15, 5, 60...) ou 1D')
    ap.add_argument('--symboles', default='', help='racines séparées par des virgules (NQ,MES). Vide = toutes')
    ap.add_argument('--config', default=os.path.join(HERE, 'config.toml'))
    ap.add_argument('--sortie', default=None, help='dossier du rapport (défaut : optim/resultats/<tf>_<symboles>_<date>)')
    ap.add_argument('--api', choices=['auto', 'oui', 'non'], default='auto',
                    help='lire aussi les JSON de l\'API (auto = seulement s\'il n\'y a aucun CSV)')
    ap.add_argument('--apprentissage', type=int, help='jours de bourse d\'apprentissage (remplace config)')
    ap.add_argument('--test', type=int, help='jours de bourse de test (remplace config)')
    ap.add_argument('--ancre', action='store_true', help='apprentissage ancré (fenêtre croissante)')
    ap.add_argument('--n-aleatoire', type=int, help='nombre de réglages tirés au hasard')
    ap.add_argument('--min-trades', type=int, help='trades hors échantillon minimum (défaut config : 100)')
    ap.add_argument('--min-trades-appr', type=int, help='trades minimum en apprentissage pour être éligible')
    ap.add_argument('--pine-seulement', action='store_true', help='n\'explorer que des réglages de STRATEGIE_V1')
    ap.add_argument('--graine', type=int)
    ap.add_argument('--rapide', action='store_true', help='démonstration : recherche et bootstraps réduits')
    a = ap.parse_args(argv)
    t00 = time.time()
    cfg = copy.deepcopy(espace.lire_config(a.config))
    W, R, RO = cfg['walkforward'], cfg['recherche'], cfg['robustesse']
    if a.apprentissage: W['apprentissage_jours'] = a.apprentissage
    if a.test: W['test_jours'] = a.test
    if a.ancre: W['ancre'] = True
    if a.n_aleatoire: R['n_aleatoire'] = a.n_aleatoire
    if a.min_trades: RO['min_trades'] = a.min_trades
    if a.min_trades_appr: R['min_trades_apprentissage'] = a.min_trades_appr
    if a.pine_seulement: R['pine_seulement'] = True
    if a.graine is not None: R['graine'] = a.graine
    if a.rapide:
        R['n_aleatoire'] = min(R['n_aleatoire'], 600); R['pool_entrees'] = min(R['pool_entrees'], 200)
        R['pool_sorties'] = min(R['pool_sorties'], 60); R['top_k_plateau'] = min(R['top_k_plateau'], 10)
        RO['bootstrap'] = min(RO['bootstrap'], 500); RO['spa_tirages'] = min(RO['spa_tirages'], 300)
    syms = [s.strip().upper() for s in a.symboles.split(',') if s.strip()] or None
    tf = a.tf.upper() if a.tf.upper().endswith('D') else a.tf
    log = lambda *x: print(*x, flush=True)

    # ------------------------------------------------------------------ données
    log('1. Données')
    S, journal = donnees.charger(a.data, tf, syms, cfg['instruments'], cfg['donnees']['min_barres_serie'],
                                 os.path.join(HERE, 'cache'), log, api={'auto': None, 'oui': True, 'non': False}[a.api])
    if not S:
        raise SystemExit('Aucune série exploitable (unité %s, symboles %s) dans %s' % (tf, syms, a.data))
    t0 = time.time()
    U = univers.Univers(S, cfg['instruments'], cfg['donnees']['unites_trend'], cfg['donnees']['warmup_barres'],
                        cfg['couts']['commission_par_cote'], cfg['couts']['glissement_ticks_par_cote'])
    for x in U.resume():
        log('   ' + rapport.propre(x))
    log('   %d jours de bourse, signaux calculés en %.1fs' % (len(U.jours), time.time() - t0))
    esp = espace.Espace(cfg, S[0]['tfm'])
    ev = optimiseur.Evaluateur(U, esp, cfg, log)
    log('   %d paires (barre signal, sens) candidates sur %d déclencheurs' % (len(ev.Pg), len(ev.trig)))

    # ------------------------------------------------------------------ recherche
    log('2. Tirage de l\'espace')
    rng = np.random.default_rng(R['graine'])
    pool = esp.tirer(rng, R['n_aleatoire'], R['pool_entrees'], R['pool_sorties'], R['grille_declencheurs'])
    t0 = time.time()
    for c in pool.values():
        ev.trades(c)
    log('   %d réglages évalués sur tout l\'historique en %.0fs (%d configurations de trade, simulation %.0fs)'
        % (len(pool), time.time() - t0, len(ev.sim), ev.t_sim))
    n_alea = len(pool)

    log('3. Walk-forward')
    oos, choix, (L, T, note, folds) = optimiseur.walk_forward(ev, pool, log)

    log('4. Sélection finale sur tout l\'historique')
    D = len(U.jours)
    best, details, sc = ev.choisir(pool, 0, D - 1)
    pine_pool = {k: c for k, c in pool.items() if esp.pine_ok(c)}
    best_p, details_p, _ = ev.choisir(pine_pool, 0, D - 1) if not R['pine_seulement'] else (best, details, sc)
    for k, c in pine_pool.items():
        pool.setdefault(k, c)

    # ------------------------------------------------------------------ statistiques
    log('5. Robustesse')
    N = len(ev.comb)
    oR = np.array([o['R'] for o in oos]); oJ = np.array([o['jour'] for o in oos], np.int64)
    ost = RB.resume(oR)
    oboot = RB.bootstrap_jour(oR, oJ, RO['bootstrap']) if len(oR) > 1 else {}
    oru = RB.ruine(oR, oJ, RO['risque_par_trade_pct'], RO['ruine_pct'], RO['horizon_trades']) if len(oR) else dict(p_ruine=np.nan)
    test_jours = np.unique(np.concatenate([U.jours[c0:c1 + 1] for (_, _, c0, c1) in folds])) if folds else np.zeros(0)
    psr_oos = RB.psr(RB.journalier(oR, oJ, test_jours))[0] if len(oR) > 2 else np.nan
    # matrice réglages x jours (échantillon complet) pour White/SPA et la variance des Sharpe (DSR)
    keys = [k for k, Tt in ev.comb.items() if len(Tt['R']) >= R['min_trades_apprentissage']]
    X = np.array([RB.journalier(ev.comb[k]['R'], U.jours[ev.comb[k]['re']], U.jours) for k in keys]) if keys else np.zeros((0, D))
    srs = X.mean(1) / np.where(X.std(1, ddof=1) > 0, X.std(1, ddof=1), np.inf) if len(X) else np.zeros(0)
    Vsr = float(np.var(srs[np.isfinite(srs)], ddof=1)) if len(srs) > 2 else 0.0
    p_rc, p_spa = RB.white_spa(X, RO['spa_tirages'], RO['bloc_moyen_jours']) if len(X) else (np.nan, np.nan)
    # essais réellement distincts : réglages aux rendements journaliers identiques comptés une fois
    N_eff = len(np.unique(np.round(X, 6), axis=0)) if len(X) else N
    final = pool[best[4]] if best else None
    if final:
        Tf = ev.trades(final)
        dsr, sr_f, sr0 = RB.dsr(RB.journalier(Tf['R'], U.jours[Tf['re']], U.jours), max(N_eff, 2), Vsr)
    else:
        dsr = sr_f = sr0 = np.nan
    top = []
    vus = set()
    for q, s, medv, nv, k in details:
        if len(top) >= 10: break
        Tt = ev.trades(pool[k])
        sig = (len(Tt['R']), round(float(Tt['R'].sum()), 6), tuple(Tt['g'][:5]))
        if sig in vus: continue          # même liste de trades qu'un réglage déjà affiché
        vus.add(sig)
        top.append(dict(reglage=pool[k], plateau=q, med_v=medv, pine=esp.pine_ok(pool[k]), st=RB.resume(Tt['R']),
                        boot=RB.bootstrap_jour(Tt['R'], Tt['re'], min(RO['bootstrap'], 1000))))

    # ------------------------------------------------------------------ verdict
    raisons = []
    min_tr = RO['min_trades']
    if ost['n'] < min_tr:
        titre = 'NON CONCLUANT'
        raisons.append('Seulement %d trades hors échantillon, moins que le minimum exigé (%d) : il faut un historique '
                       'plus long avant de conclure quoi que ce soit.' % (ost['n'], min_tr))
    crit = [
        (bool(oboot.get('moy')) and oboot['moy'][0] > 0, 'borne basse de l\'IC 95 %% du R moyen hors échantillon > 0 (%s)' % rapport.ic(oboot.get('moy'), '%+.3f')),
        (np.isfinite(psr_oos) and psr_oos >= 0.95, 'Probabilistic Sharpe hors échantillon >= 0,95 (%s)' % rapport.f2(psr_oos, '%.2f')),
        (np.isfinite(p_spa) and p_spa <= RO['seuil_p'], 'SPA de Hansen p <= %.2f (%s)' % (RO['seuil_p'], rapport.f2(p_spa, '%.3f'))),
        (np.isfinite(dsr) and dsr >= RO['seuil_dsr'], 'Deflated Sharpe >= %.2f (%s)' % (RO['seuil_dsr'], rapport.f2(dsr, '%.2f'))),
    ]
    for ok, txt in crit:
        raisons.append(('OK : ' if ok else 'ÉCHEC : ') + txt)
    retenue = ost['n'] >= min_tr and all(ok for ok, _ in crit)
    if ost['n'] >= min_tr:
        titre = 'STRATÉGIE RETENUE' if retenue else 'RIEN DE ROBUSTE'
    # stabilité des choix
    idx_final = esp.cle(final) if final else None
    vois_final = {esp.cle(v) for v in esp.voisins(final)} if final else set()
    same = sum(1 for c in choix if c['cle'] == idx_final); near = sum(1 for c in choix if c['cle'] in vois_final)
    decs = [pool[c['cle']]['declencheur'] for c in choix if c['cle']]
    stab = ('%d pli(s) sur %d ont choisi le réglage final, %d un de ses voisins ; déclencheurs choisis : %s.'
            % (same, len(choix), near, ', '.join('%s ×%d' % (d, decs.count(d)) for d in dict.fromkeys(decs)) or 'aucun'))
    for c in choix:
        c['reglage'] = pool[c['cle']] if c['cle'] else None
        c['appr_txt'] = '%s → %s' % (optimiseur.jour_txt(ev, c['a']), optimiseur.jour_txt(ev, c['b']))
        c['test_txt'] = '%s → %s' % (optimiseur.jour_txt(ev, c['c0']), optimiseur.jour_txt(ev, c['c1']))

    # ------------------------------------------------------------------ sortie
    racines = sorted({s['racine'] for s in U.series})
    if a.sortie:
        out = a.sortie
    else:
        out = os.path.join(HERE, 'resultats', '%s_%s_%s' % (tf, '-'.join(racines), datetime.datetime.now().strftime('%Y%m%d-%H%M')))
    os.makedirs(out, exist_ok=True)
    png = os.path.join(out, 'courbe_oos.png')
    png = png if (len(oos) and rapport.courbe_png(png, oos, None)) else None
    blocs = []
    if final:
        blocs.append(('Meilleure zone stable (espace complet)', final))
        if not esp.pine_ok(final) and best_p:
            blocs.append(('Meilleure zone stable 100 % transposable (réglages existants de STRATEGIE_V1)', pool[best_p[4]]))
    srcs = sorted({s['source'] for s in U.series})
    src_txt = {'CSV': 'vrais prix reconstitués depuis le Heiken Ashi', 'CSV+STD': 'vrais prix exacts (bougies standard)',
               'API': 'vrais prix exacts (API)'}
    limites = [
        'Une position à la fois par graphique, pas de renversement ; un trade encore ouvert en fin de série est abandonné.',
        'Remplissages prudents (objectif dépassé d\'un tick, stop et objectif dans la même barre = stop) : le testeur '
        'TradingView remplit un peu mieux les objectifs.',
        'Vrais prix reconstitués : fiables en 15 min (±0,1-0,2 R), PAS en 1-3 min. Fournir les bougies standard du '
        'même graphique (mode b) supprime cette erreur.',
        'Le Feu de Confluence n\'est qu\'un PROXY à 12 voix (le Pine en a 29) : désactivé par défaut.',
        'Swing (stop/suiveur) : pivots stricts des deux côtés (ta.pivotlow peut traiter les égalités autrement).',
        'Cassure de niveau (sessions/Monday) : dernier niveau terminé de chaque session (le Pine garde 2 jours).',
        'Les trades d\'un pli de test sont ceux du réglage choisi, joué en continu : une position ouverte par le réglage '
        'du pli précédent n\'est pas reportée.',
    ]
    if any(not s['hasv'] for s in U.series):
        limites.append('Séries sans volume : ni climax, ni Detector, flèches de l\'original exportées à la place du Signator.')
    if note:
        limites.append(note)
    temps = '%.0f s au total (simulation des trades %.0f s)' % (time.time() - t00, ev.t_sim)
    ctx = dict(date=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), tf=tf, racines=racines,
               source_txt=' + '.join(src_txt[s] for s in srcs), verdict=dict(titre=titre, raisons=raisons, retenue=retenue),
               univers=[rapport.propre(x) for x in U.resume()], D=D, warmup=cfg['donnees']['warmup_barres'],
               slip=cfg['couts']['glissement_ticks_par_cote'], comm=cfg['couts']['commission_par_cote'],
               points=[(r, cfg['instruments'].get(r, {}).get('point', np.nan)) for r in racines],
               n_alea=n_alea, topk=R['top_k_plateau'], N=N, n_sim=len(ev.sim), L=L, T=T, choix=choix, note_wf=note,
               qplat=R['quantile_plateau'], objectif=R['objectif'], min_app=R['min_trades_apprentissage'],
               spa_B=RO['spa_tirages'], B=RO['bootstrap'], risque=RO['risque_par_trade_pct'], ruine_pct=RO['ruine_pct'],
               horizon=RO['horizon_trades'], oos_stats=ost, oos_boot=oboot, oos_ruine=oru,
               oos_usd=float(np.sum([o['usd'] for o in oos])) if oos else 0.0, psr_oos=psr_oos, min_trades=min_tr,
               png=png, oos=oos, stabilite=stab, p_rc=p_rc, p_spa=p_spa, K_spa=len(X), N_eff=N_eff, dsr=dsr, sr_final=sr_f, sr0=sr0,
               top=top, blocs=blocs, cfg=cfg, limites=limites, temps=temps)
    p = rapport.ecrire(out, ctx)
    with open(os.path.join(out, 'trades_oos.csv'), 'w') as f:
        f.write('pli;date;symbole;sens;R;usd;sortie\n')
        for o in oos:
            f.write('%d;%s;%s;%d;%.4f;%.2f;%s\n' % (o['fold'] + 1, datetime.datetime.fromtimestamp(o['t']).strftime('%Y-%m-%d %H:%M'),
                                                     U.series[o['sid']]['racine'], o['d'], o['R'], o['usd'],
                                                     optimiseur.moteur.POURQUOI.get(int(o['why']), '?')))
    res = dict(verdict=titre, oos=dict(n=ost['n'], moyR=ost['moy'], pf=ost['pf'], dd=ost['dd'], ic_moy=oboot.get('moy'),
               p_ruine=oru.get('p_ruine'), psr=psr_oos), p_white=p_rc, p_spa=p_spa, dsr=dsr, n_reglages=N, n_essais_distincts=N_eff,
               reglage_final=final, reglage_pine=pool[best_p[4]] if best_p else None, choix=[
                   dict(pli=c['fold'] + 1, reglage=c['reglage'], n_test=c['n_test']) for c in choix], temps_s=time.time() - t00)
    json.dump(res, open(os.path.join(out, 'resultats.json'), 'w'), indent=1, ensure_ascii=False,
              default=lambda x: x.item() if hasattr(x, 'item') else str(x))
    log('6. Rapport : %s' % rapport.propre(p))
    log('   VERDICT : %s | OOS n=%d moyR %s IC %s | SPA p=%s | DSR %s | %s' % (
        titre, ost['n'], rapport.f2(ost['moy'], '%+.3f'), rapport.ic(oboot.get('moy'), '%+.3f'), rapport.f2(p_spa, '%.3f'),
        rapport.f2(dsr, '%.2f'), temps))
    return res


if __name__ == '__main__':
    main()
