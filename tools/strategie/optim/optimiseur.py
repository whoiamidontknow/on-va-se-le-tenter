"""Évaluation des réglages (avec caches) et walk-forward glissant avec sélection d'une ZONE STABLE.

Caches :
  - paires (barre signal, sens) de TOUS les déclencheurs, une fois ;
  - simulation d'une configuration de trade (entrée+stop+sortie) sur toutes les paires, une fois ;
  - trades d'un réglage complet (déclencheur + filtres + trade, une position à la fois), une fois sur
    tout l'historique ; une fenêtre (apprentissage ou test) n'est qu'une tranche de ces trades.
Un trade d'apprentissage doit être ENTRÉ ET SORTI dans la fenêtre d'apprentissage (aucune information du
test ne sert au choix). Les trades de test sont ceux ENTRÉS dans la fenêtre de test.
"""
import time
import numpy as np
import moteur
import robustesse as RB
from espace import SIG_FILTER_KEYS, TRADE_KEYS, KEYS


class Evaluateur:
    def __init__(self, U, esp, cfg, log=print):
        self.U, self.esp, self.cfg, self.log = U, esp, cfg, log
        A = U.A
        keys = {}
        for dec in esp.E['declencheur']:
            e = A['E_' + dec]
            idx = np.nonzero((e != 0) & A['ok'])[0]
            keys[dec] = idx * 2 + (e[idx] > 0)
        allk = np.unique(np.concatenate(list(keys.values()))) if keys else np.zeros(0, np.int64)
        self.Pg = allk // 2
        self.Pd = np.where(allk % 2 == 1, 1, -1)
        self.trig = {k: np.searchsorted(allk, v) for k, v in keys.items()}
        fx = cfg['stop_fixe_points']
        self.fixes = {r: np.array([fx.get(rc, [10.0, 20.0])[r] for rc in U.racine]) for r in (0, 1)}
        self.sim = {}; self.comb = {}; self.mcache = {}; self.cand = {}
        ex = cfg['execution']
        self.rempl, self.hmode, self.plafond = ex['remplissage'], ex['heishi_sortie'], ex['plafond_barres']
        self.rank_of = lambda j: np.searchsorted(U.jours, j)
        self.t_sim = 0.0

    def simul(self, c):
        k = tuple(c[x] for x in TRADE_KEYS)
        if k not in self.sim:
            t0 = time.time()
            tc = self.esp.trade_cfg(c)
            self.sim[k] = moteur.simuler(self.U, self.Pg, self.Pd, tc, self.rempl, self.hmode, self.plafond,
                                         self.fixes[int(c['x_fixPts'])])
            self.t_sim += time.time() - t0
        return self.sim[k]

    def candidats(self, c):
        k = tuple(c[x] for x in SIG_FILTER_KEYS)
        if k not in self.cand:
            pos = self.trig[c['declencheur']]
            m = self.esp.masque(self.U, self.Pg[pos], self.Pd[pos], c, self.mcache)
            self.cand[k] = pos[m]
        return self.cand[k]

    def trades(self, c):
        key = self.esp.cle(c)
        if key in self.comb:
            return self.comb[key]
        A = self.U.A
        res = self.simul(c)
        sel = moteur.selection(self.candidats(c), self.Pg, res, int(c['f_maxJour']), A['paris_date'], A['sid'])
        g = self.Pg[sel]
        T = dict(p=sel, g=g, d=self.Pd[sel], R=res['R'][sel], usd=res['usd'][sel], why=res['why'][sel],
                 re=self.rank_of(A['jour'][g]), rx=self.rank_of(A['jour'][res['xbar'][sel]]),
                 sid=A['sid'][g], t=A['t'][g], nbar=res['nbar'][sel])
        self.comb[key] = T
        return T

    # ------------------------------------------------------------------ score sur une fenêtre
    def score(self, T, a, b, mode='appr'):
        m = (T['re'] >= a) & (T['re'] <= b)
        if mode == 'appr':
            m &= T['rx'] <= b
        R = T['R'][m]
        n = len(R)
        if n < self.cfg['recherche']['min_trades_apprentissage']:
            return -np.inf, n
        obj = self.cfg['recherche']['objectif']
        if obj == 'moyR':
            return R.mean(), n
        if obj == 'pf':
            l = -R[R <= 0].sum()
            return (R[R > 0].sum() / l if l > 0 else 10.0), n
        sd = R.std(ddof=1)
        return (R.mean() / sd * np.sqrt(n) if sd > 0 else -np.inf), n

    def choisir(self, pool, a, b):
        """pool : dict clé -> réglage. Évalue tout le pool sur [a,b], puis les voisins des K meilleurs, et
        renvoie le réglage au meilleur score de PLATEAU (quantile du score sur lui + ses voisins)."""
        R = self.cfg['recherche']
        sc = {}
        for k, c in pool.items():
            sc[k] = self.score(self.trades(c), a, b)[0]
        ordre = sorted((k for k in sc if np.isfinite(sc[k])), key=lambda k: -sc[k])[:R['top_k_plateau']]
        best = None
        details = []
        for k in ordre:
            c = pool[k]
            vs = self.esp.voisins(c)
            if len(vs) < R['min_voisins']:
                continue
            svs = []
            for v in vs:
                kv = self.esp.cle(v)
                pool.setdefault(kv, v)
                svs.append(self.score(self.trades(v), a, b)[0])
            allv = np.array([sc[k]] + svs)
            q = np.quantile(np.where(np.isfinite(allv), allv, -1e9), R['quantile_plateau'])
            med_v = float(np.median(np.where(np.isfinite(svs), svs, np.nan))) if np.isfinite(svs).any() else np.nan
            details.append((q, sc[k], med_v, len(vs), k))
            if best is None or (q, sc[k]) > (best[0], best[1]):
                best = (q, sc[k], med_v, len(vs), k)
        details.sort(key=lambda x: -x[0])
        return best, details, sc


def fenetres(D, L, T, ancre=False, auto=True):
    note = ''
    if auto and D < L + 2 * T:
        L2, T2 = max(4, int(0.5 * D)), max(2, int(0.12 * D))
        note = ('données courtes (%d jours de bourse) : fenêtres ramenées de %d/%d à %d/%d jours'
                % (D, L, T, L2, T2))
        L, T = L2, T2
    out = []
    a = 0
    while a + L <= D - 1:
        tr0 = 0 if ancre else a
        t0, t1 = a + L, min(a + L + T - 1, D - 1)
        out.append((tr0, a + L - 1, t0, t1))
        a += T
    return out, L, T, note


def walk_forward(ev, pool, log=print):
    cfg = ev.cfg
    W = cfg['walkforward']
    D = len(ev.U.jours)
    folds, L, T, note = fenetres(D, W['apprentissage_jours'], W['test_jours'], W['ancre'], W.get('auto', True))
    if note:
        log('  ' + note)
    oos = []
    choix = []
    for f, (a, b, c0, c1) in enumerate(folds):
        t0 = time.time()
        best, details, sc = ev.choisir(pool, a, b)
        if best is None:
            choix.append(dict(fold=f, a=a, b=b, c0=c0, c1=c1, cle=None, plateau=np.nan, score=np.nan, n_appr=0, n_test=0))
            log('  pli %d : apprentissage %s -> %s, test %s -> %s : AUCUN réglage éligible' % (
                f + 1, jour_txt(ev, a), jour_txt(ev, b), jour_txt(ev, c0), jour_txt(ev, c1)))
            continue
        q, s, medv, nv, k = best
        Tt = ev.trades(pool[k])
        m = (Tt['re'] >= c0) & (Tt['re'] <= c1)
        n_appr = ev.score(Tt, a, b)[1]
        for i in np.nonzero(m)[0]:
            oos.append(dict(fold=f, t=Tt['t'][i], R=Tt['R'][i], usd=Tt['usd'][i], jour=ev.U.jours[Tt['re'][i]],
                            sid=Tt['sid'][i], d=Tt['d'][i], why=Tt['why'][i]))
        st_test = RB.resume(Tt['R'][m])
        choix.append(dict(fold=f, a=a, b=b, c0=c0, c1=c1, cle=k, plateau=q, score=s, med_voisins=medv, n_voisins=nv,
                          n_appr=n_appr, n_test=int(m.sum()), moy_test=st_test['moy']))
        log('  pli %d : appr. %s -> %s, test %s -> %s | plateau %.2f (score %.2f, %d voisins) | test n=%d moyR %+.3f | %.0fs'
            % (f + 1, jour_txt(ev, a), jour_txt(ev, b), jour_txt(ev, c0), jour_txt(ev, c1), q, s, nv, m.sum(),
               st_test['moy'] if m.sum() else np.nan, time.time() - t0))
    return oos, choix, (L, T, note, folds)


def jour_txt(ev, r):
    import datetime
    return datetime.date.fromordinal(int(ev.U.jours[min(r, len(ev.U.jours) - 1)])).strftime('%d/%m/%y')
