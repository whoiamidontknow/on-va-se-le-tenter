"""Étude du stop et de la sortie par MAE/MFE — ligne de commande.

Exemples :
  python tools/strategie/maemfe/run.py --tf 15
  python tools/strategie/maemfe/run.py --tf 5,15,30,60
  python tools/strategie/maemfe/run.py --data "/Users/jeremk/Jeu 15:10" --data <autre dossier> --tf 15
Sans --data : toutes les séries du projet (cache commun tools/strategie/cache_series.pkl).
Écrit un rapport Markdown (et un JSON des recommandations pour un optimiseur).

Depuis Python (sans ligne de commande) :
  sys.path.insert(0, '.../tools/strategie/maemfe'); import etude, donnees
  S = donnees.selectionner(donnees.charger_series(), (15,)); U = etude.univers(S)
  etude.recommander(U, ma_fonction_entrees)       # ma_fonction_entrees(S) -> [(i, sens)]
  etude.evaluer_plan(U, ma_fonction_entrees, stop=1.5, cible=2, hcap=16)
"""
import os, sys, json, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import numpy as np
import donnees, core, etude, rapport


def controle_api(H=48, h=16):
    """Erreur de la reconstitution sur MAE/MFE (ATR) : API 15 min, vrais prix vs prix reconstitués."""
    try:
        Sv = donnees.series_api('vrai'); Sr = donnees.series_api('recon')
    except Exception as e:  # pas de fichier API
        return 'indisponible (%s)' % e
    Uv, Ur = core.Univers(Sv, H=H), core.Univers(Sr, H=H)
    com = [k for k in Uv.index if k in Ur.index]
    rv = np.array([Uv.index[k] for k in com]); rr = np.array([Ur.index[k] for k in com])
    out = []
    for d in (1, -1):
        dv = np.full(len(rv), d)
        maeV, mfeV, _, _ = core.excursions(Uv, rv, dv, h); maeR, mfeR, _, _ = core.excursions(Ur, rr, dv, h)
        # Les deux en ATR des VRAIS prix pour isoler l'erreur de prix
        k = Ur.atr[rr] / Uv.atr[rv]
        ok = np.isfinite(maeV) & np.isfinite(maeR)
        out.append((np.abs(maeR * k - maeV)[ok], (maeR * k - maeV)[ok], np.abs(mfeR * k - mfeV)[ok], (mfeR * k - mfeV)[ok]))
    ae = np.concatenate([o[0] for o in out]); be = np.concatenate([o[1] for o in out])
    af = np.concatenate([o[2] for o in out]); bf = np.concatenate([o[3] for o in out])
    rng = np.random.default_rng(0); dd = rng.choice([1, -1], len(rv))
    Rv = core.simuler(Uv, rv, dd, 1.5, 2.0, hcap=h); Rr = core.simuler(Ur, rr, dd, 1.5, 2.0, hcap=h)
    return ('%d barres x 2 sens, horizon %d barres : erreur MAE médiane %.2f ATR (biais %+.2f), MFE médiane %.2f ATR '
            '(biais %+.2f) ; plan stop 1,5 ATR / objectif 2R : E[R] vrais prix %+.3f vs reconstitués %+.3f, '
            'même issue (gain/perte) dans %.0f %% des trades.' % (
                len(rv), h, np.median(ae), np.mean(be), np.median(af), np.mean(bf), np.mean(Rv), np.mean(Rr),
                100 * np.mean((Rv > 0) == (Rr > 0))))


def principal(argv=None):
    ap = argparse.ArgumentParser(description='Étude MAE/MFE du stop et de la sortie, par déclencheur.')
    ap.add_argument('--data', action='append', help='dossier(s) de CSV Heiken Ashi (répétable). Défaut : cache commun.')
    ap.add_argument('--tf', default='15', help='unité(s) en minutes, ex. 15 ou 5,15,30,60')
    ap.add_argument('--sortie', help='fichier Markdown (défaut : maemfe/rapport_tf<tf>.md)')
    ap.add_argument('--declencheurs', default=','.join(list(donnees.DECLENCHEURS) + [donnees.ALEA]))
    ap.add_argument('--href', type=int, default=16, help='horizon (barres) définissant gagnant/perdant')
    ap.add_argument('--garde', type=float, default=0.90, help='part des gagnants à conserver par le stop')
    ap.add_argument('--prudent', action='store_true', help='high/low incertains pris du côté défavorable')
    ap.add_argument('--tirages', type=int, default=1000)
    ap.add_argument('--sans-api', action='store_true', help='ne pas faire le contrôle de reconstitution sur l\'API')
    a = ap.parse_args(argv)
    tfs = tuple(int(x) for x in a.tf.split(','))
    t0 = time.time()
    S = donnees.selectionner(donnees.charger_series(a.data, verbose=True), tfs)
    if not S:
        sys.exit('aucune série pour les unités %s' % (tfs,))
    U = core.Univers(S, prudent=a.prudent)
    print('univers : %d séries, %d barres candidates (%.1fs)' % (len(S), U.N, time.time() - t0), flush=True)
    cfg = dict(h_ref=a.href, garde=a.garde, M=a.tirages)
    res = {}
    for nom in a.declencheurs.split(','):
        lib = 'Aléatoire (référence)' if nom == donnees.ALEA else donnees.DECLENCHEURS[nom][0]
        rows, d = etude.entrees_univers(U, lambda s, n=nom: donnees.entrees(s, n))
        if len(rows) == 0:
            print(lib, ': aucune entrée'); continue
        r = etude.etudier(U, rows, d, cfg)
        res[lib] = r
        v = r['res'].get('VAL', {})
        print('%-28s n=%4d plan=%s VAL E[R]=%s hasard=%s p=%s -> %s' % (
            lib, len(rows), {k: v2 for k, v2 in r['plan'].items()}, rapport.f(v.get('R'), 3, True),
            rapport.f(v.get('R_hasard'), 3, True), rapport.f(v.get('p'), 3), r['verdict']['texte']), flush=True)
    ctl = None if a.sans_api else controle_api(h=a.href)
    tag = '-'.join(map(str, tfs))
    sortie = a.sortie or os.path.join(HERE, 'rapport_tf%s.md' % tag)
    src = 'cache commun du projet' if not a.data else ', '.join('« %s »' % os.path.basename(os.path.normpath(x)) for x in a.data)
    rapport.ecrire(sortie, res, S, tfs, dict(etude.CFG, **cfg), ctl, src)
    js = {k: dict(plan={kk: (None if vv is None else float(vv)) for kk, vv in r['plan'].items()},
                  verdict=r['verdict'], val={kk: (float(vv) if isinstance(vv, (int, float, np.floating)) else vv)
                                             for kk, vv in r['res'].get('VAL', {}).items()},
                  appr={kk: (float(vv) if isinstance(vv, (int, float, np.floating)) else vv)
                        for kk, vv in r['res'].get('APPR', {}).items()})
          for k, r in res.items()}
    json.dump(js, open(os.path.splitext(sortie)[0] + '.json', 'w'), ensure_ascii=False, indent=1)
    print('rapport :', sortie, '(%.1fs)' % (time.time() - t0))
    if ctl: print('contrôle API :', ctl)
    return res


if __name__ == '__main__':
    principal()
