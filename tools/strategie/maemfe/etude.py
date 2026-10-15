"""Étude du stop et de la sortie d'un déclencheur par MAE/MFE, avec référence aléatoire appariée.

Protocole (pour chaque déclencheur) :
  coupure = date médiane des entrées du déclencheur sur l'instrument d'apprentissage (MES par défaut) ;
  APPR = MES avant la coupure (tous les choix y sont faits) ;
  VAL_T = MES après (validation dans le temps) ; VAL_NQ = NQ après (validation instrument ET temps) ;
  NQ_avant = NQ avant la coupure (instrument seul : mêmes journées que APPR, pas indépendant) ;
  VAL = VAL_T + VAL_NQ (sert au verdict).
Choix faits sur APPR : stop = plus petit stop gardant >= 90 % des gagnants (gagnant = clôture nette > 0
à h_ref barres) ; objectif = meilleure espérance ; durée = meilleure espérance ; break-even / suiveur adoptés
s'ils améliorent APPR. Tout est ensuite mesuré tel quel sur les jeux de validation.
"""
import numpy as np
import core
from core import simuler, excursions, boot_moyenne, tirages_hasard, boot_p, base_hasard

STOPS = [round(x, 2) for x in np.arange(0.25, 4.01, 0.25)]
CIBLES = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, None]
HCAPS = [2, 4, 8, 12, 16, 24, 32, 48]
BES = [0.5, 1.0, 1.5]
SUIVEURS = [0.5, 1.0, 1.5, 2.0, 3.0]
HORIZONS = [4, 8, 12, 16, 24, 32, 48]
NMIN = 50

CFG = dict(h_ref=16, garde=0.90, inst_appr='MES', B=2000, M=1000, hcap_courbe=48)


def jeux(U, rows, inst_appr='MES'):
    """Masques (sur l'univers entier) des jeux, coupure à la médiane des entrées d'apprentissage."""
    insts = sorted(set(U.inst[rows])) if len(rows) else []
    if inst_appr not in insts and insts:
        inst_appr = max(insts, key=lambda x: (U.inst[rows] == x).sum())
    tA = U.t[rows][U.inst[rows] == inst_appr]
    cut = np.median(tA) if len(tA) else np.median(U.t[rows]) if len(rows) else np.median(U.t)
    A = U.inst == inst_appr; early = U.t < cut
    J = {'APPR': A & early, 'VAL_T': A & ~early, 'VAL_NQ': ~A & ~early, 'NQ_avant': ~A & early}
    J['VAL'] = J['VAL_T'] | J['VAL_NQ']
    return J, cut, inst_appr


def _sel(rows, d, masque):
    k = masque[rows]
    return rows[k], d[k]


def _plan_R(U, rows, d, plan):
    return simuler(U, rows, d, plan['stop'], plan['cible'], plan.get('be'), plan.get('suiveur'), plan['hcap'])


def etudier(U, rows, d, cfg=None, verbose=False):
    """rows, d : entrées du déclencheur dans l'univers U. Renvoie un dict complet (voir rapport.py)."""
    c = dict(CFG); c.update(cfg or {})
    h = c['h_ref']
    rows = np.asarray(rows, int); d = np.asarray(d, int)
    J, cut, inst_appr = jeux(U, rows, c['inst_appr'])
    out = dict(n_total=len(rows), coupure=cut, inst_appr=inst_appr, jeux={}, cfg=c)
    sets = ['APPR', 'VAL_T', 'VAL_NQ', 'NQ_avant', 'VAL']
    sub = {k: _sel(rows, d, J[k]) for k in sets}

    # ---------- 1. description MAE / MFE par horizon et instant du MFE
    for k in sets:
        r, dd = sub[k]
        D = dict(n=len(r), part_long=float((dd > 0).mean()) if len(r) else np.nan,
                 jours=int(len(np.unique(U.jour[r]))) if len(r) else 0, horizons={})
        for hz in HORIZONS:
            mae, mfe, ret, tm = excursions(U, r, dd, hz)
            ok = np.isfinite(mae)
            D['horizons'][hz] = dict(n=int(ok.sum()), mae=np.nanmean(mae) if ok.any() else np.nan,
                                     mfe=np.nanmean(mfe) if ok.any() else np.nan,
                                     mae_med=np.nanmedian(mae) if ok.any() else np.nan,
                                     mfe_med=np.nanmedian(mfe) if ok.any() else np.nan,
                                     ret=np.nanmean(ret - U.cout[r]) if ok.any() else np.nan)
            if hz == 48 and ok.any():
                tt = tm[ok]
                D['t_mfe'] = dict(q25=np.percentile(tt, 25), med=np.median(tt), q75=np.percentile(tt, 75),
                                  le8=float((tt <= 8).mean()), le16=float((tt <= 16).mean()))
        # gagnants / perdants à h_ref
        mae, mfe, ret, _ = excursions(U, r, dd, h)
        ok = np.isfinite(ret); net = ret - U.cout[r]
        w = ok & (net > 0); l_ = ok & (net <= 0)
        q = lambda x: [float(np.percentile(x, p)) if len(x) else np.nan for p in (50, 75, 90, 95)]
        D['gagnants'] = dict(n=int(w.sum()), mae_q=q(mae[w]), part=float(w.sum() / max(ok.sum(), 1)))
        D['perdants'] = dict(n=int(l_.sum()), mae_q=q(mae[l_]))
        D['garde'] = {s: (float((mae[w] < s).mean()) if w.any() else np.nan,
                          float((mae[l_] < s).mean()) if l_.any() else np.nan) for s in STOPS}
        out['jeux'][k] = D

    # ---------- 2. choix sur APPR
    rA, dA = sub['APPR']
    G = out['jeux']['APPR']['garde']
    stop = next((s for s in STOPS if np.isfinite(G[s][0]) and G[s][0] >= c['garde']), STOPS[-1])
    courbe_cible = {}
    for T in CIBLES:
        courbe_cible[T] = {k: (np.nanmean(simuler(U, *sub[k], stop, T, hcap=c['hcap_courbe'])) if len(sub[k][0]) else np.nan)
                           for k in ('APPR', 'VAL')}
    okT = [T for T in CIBLES if np.isfinite(courbe_cible[T]['APPR'])]
    cible = max(okT, key=lambda T: courbe_cible[T]['APPR']) if okT else None
    courbe_h = {}
    for hc in HCAPS:
        courbe_h[hc] = {k: (np.nanmean(simuler(U, *sub[k], stop, cible, hcap=hc)) if len(sub[k][0]) else np.nan)
                        for k in ('APPR', 'VAL')}
    okH = [x for x in HCAPS if np.isfinite(courbe_h[x]['APPR'])]
    hcap = max(okH, key=lambda x: courbe_h[x]['APPR']) if okH else 48
    base = dict(stop=stop, cible=cible, hcap=hcap)
    courbe_stop = {s_: {k: (np.nanmean(simuler(U, *sub[k], s_, cible, hcap=hcap)) if len(sub[k][0]) else np.nan)
                        for k in ('APPR', 'VAL')} for s_ in STOPS}

    # ---------- 3. break-even et stop suiveur (différences appariées)
    opts = {}
    R0 = {k: _plan_R(U, *sub[k], base) if len(sub[k][0]) else np.array([]) for k in ('APPR', 'VAL')}
    for nom, kw in [('be', dict(be=b)) for b in BES] + [('suiveur', dict(suiveur=t)) for t in SUIVEURS]:
        p = dict(base, **kw); key = (nom, list(kw.values())[0])
        res = {}
        for k in ('APPR', 'VAL'):
            r, dd = sub[k]
            if not len(r): res[k] = (np.nan, np.nan, np.nan); continue
            diff = _plan_R(U, r, dd, p) - R0[k]
            res[k] = boot_moyenne(diff, U.jour[r], B=c['B'])
        opts[key] = res
    choix = {}
    for nom in ('be', 'suiveur'):
        cand = [(k, v) for k, v in opts.items() if k[0] == nom and np.isfinite(v['APPR'][0])]
        if not cand: choix[nom] = None; continue
        k, v = max(cand, key=lambda kv: kv[1]['APPR'][0])
        choix[nom] = dict(valeur=k[1], appr=v['APPR'], val=v['VAL'], adopte=v['APPR'][0] > 0,
                          confirme=v['APPR'][0] > 0 and np.isfinite(v['VAL'][0]) and v['VAL'][0] > 0,
                          ic_val_pos=np.isfinite(v['VAL'][1]) and v['VAL'][1] > 0)
    plan = dict(base)
    # on garde au plus UNE gestion (celle qui améliore le plus APPR)
    adopt = [(nom, x) for nom, x in choix.items() if x and x['adopte']]
    if adopt:
        nom, x = max(adopt, key=lambda t: t[1]['appr'][0])
        plan[nom] = x['valeur']

    # ---------- 4. plan final mesuré sur chaque jeu + comparaison au hasard apparié
    RL = simuler(U, np.arange(U.N), np.ones(U.N, int), plan['stop'], plan['cible'], plan.get('be'), plan.get('suiveur'), plan['hcap'])
    RS = simuler(U, np.arange(U.N), -np.ones(U.N, int), plan['stop'], plan['cible'], plan.get('be'), plan.get('suiveur'), plan['hcap'])
    maeL, mfeL, _, _ = excursions(U, np.arange(U.N), np.ones(U.N, int), h)
    maeS, mfeS, _, _ = excursions(U, np.arange(U.N), -np.ones(U.N, int), h)
    res = {}
    for k in sets:
        r, dd = sub[k]
        if not len(r):
            res[k] = dict(n=0); continue
        R = _plan_R(U, r, dd, plan)
        m, lo, hi = boot_moyenne(R, U.jour[r], B=c['B'])
        mae, mfe, _, _ = excursions(U, r, dd, h)
        er = np.nanmean(mfe) / np.nanmean(mae) if np.isfinite(mae).any() else np.nan
        rand_R, rand_mfe, rand_mae = tirages_hasard(U, r, dd, [(RL, RS), (mfeL, mfeS), (maeL, maeS)], M=c['M'], masque=J[k])
        rer = rand_mfe / rand_mae
        win = R > 0
        exc = R - base_hasard(U, r, dd, RL, RS, J[k])          # excès sur le hasard apparié, trade par trade
        mx, xlo, xhi = boot_moyenne(exc, U.jour[r], B=c['B'])
        p_cl = boot_p(exc, U.jour[r]); p_cl_inv = boot_p(-exc, U.jour[r])
        res[k] = dict(n=len(r), jours=int(len(np.unique(U.jour[r]))), R=m, lo=lo, hi=hi, gain=float(win.mean()),
                      R_hasard=float(np.mean(rand_R)), p_R=float((1 + (rand_R >= m).sum()) / (len(rand_R) + 1)),
                      exces=mx, exces_lo=xlo, exces_hi=xhi, p_cl=p_cl, p_cl_inv=p_cl_inv,
                      p=max(float((1 + (rand_R >= m).sum()) / (len(rand_R) + 1)), p_cl),
                      p_inv=max(float((1 + (rand_R <= m).sum()) / (len(rand_R) + 1)), p_cl_inv),
                      eratio=er, eratio_hasard=float(np.nanmean(rer)),
                      p_er=float((1 + (rer >= er).sum()) / (len(rer) + 1)) if np.isfinite(er) else np.nan)
    out.update(plan=plan, courbe_stop=courbe_stop, courbe_cible=courbe_cible, courbe_h=courbe_h, options=opts, choix=choix, res=res)
    out['verdict'] = verdict(res)
    return out


def verdict(res):
    v = res.get('VAL', {})
    if v.get('n', 0) < NMIN:
        return dict(code='indetermine', texte='indéterminé (n validation %d < %d)' % (v.get('n', 0), NMIN), conf='-')
    p = v['p']; pe = v['p_er']
    coh = all(res[k].get('n', 0) == 0 or res[k]['R'] >= res[k]['R_hasard'] for k in ('VAL_T', 'VAL_NQ'))
    a = res.get('APPR', {})
    if p < 0.10 and not (a.get('n', 0) and a.get('exces', np.nan) > 0):
        return dict(code='non', texte='non concluant (VAL > hasard mais APPR < hasard : effet de régime)',
                    conf='faible (p VAL=%.3f)' % p)
    if p < 0.05 and coh:
        return dict(code='bat', texte='bat le hasard', conf='élevée (p=%.3f)' % p)
    if p < 0.10:
        return dict(code='probable', texte='bat le hasard (fragile)', conf='moyenne (p=%.3f)' % p)
    if v['p_inv'] < 0.05:
        return dict(code='pire', texte='PIRE que le hasard', conf='élevée (p=%.3f)' % v['p_inv'])
    return dict(code='non', texte='ne bat pas le hasard', conf='p=%.2f (profil MFE/MAE p=%.2f)' % (p, pe))


# ------------------------------------------------------------------ API simple pour un autre module (optimiseur)
def univers(series, H=core.H, prudent=False):
    """Construit l'univers (chemins de prix) une fois ; à réutiliser pour plusieurs déclencheurs."""
    return core.Univers(series, H=H, prudent=prudent)


def entrees_univers(U, f):
    """f(S) -> [(i, sens)] appliquée à chaque série de l'univers -> (rows, d)."""
    trip = []
    for sid, S in enumerate(U.series):
        trip += [(sid, i, dd) for i, dd in f(S)]
    return U.lignes(trip)


def profil(series_ou_U, f, cfg=None):
    """Étude complète d'un générateur d'entrées f(S) -> [(i, sens)]. Renvoie le dict de etudier()."""
    U = series_ou_U if isinstance(series_ou_U, core.Univers) else univers(series_ou_U)
    rows, d = entrees_univers(U, f)
    return etudier(U, rows, d, cfg)


def recommander(series_ou_U, f, cfg=None):
    """Version courte pour un optimiseur : stop (ATR), objectif (R), be, suiveur, durée (barres), verdict."""
    r = profil(series_ou_U, f, cfg)
    p = r['plan']; v = r['res'].get('VAL', {})
    return dict(stop_atr=p['stop'], cible_R=p['cible'], be_R=p.get('be'), suiveur_atr=p.get('suiveur'),
                hcap_barres=p['hcap'], R_val=v.get('R'), ic_val=(v.get('lo'), v.get('hi')), n_val=v.get('n', 0),
                R_hasard_val=v.get('R_hasard'), p_hasard=v.get('p'), verdict=r['verdict']['texte'])


def evaluer_plan(series_ou_U, f, stop, cible=None, be=None, suiveur=None, hcap=core.H):
    """R net par trade d'un plan de sortie donné (sans optimisation). Renvoie (R, U.t des entrées, sens)."""
    U = series_ou_U if isinstance(series_ou_U, core.Univers) else univers(series_ou_U)
    rows, d = entrees_univers(U, f)
    return simuler(U, rows, d, stop, cible, be, suiveur, hcap), U.t[rows], d
