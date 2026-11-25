"""25/11 — programme EFFETS DOCUMENTÉS D1-D6 (HYPOTHESES.md, commit 01a94da). MNQ / MES 5 min, heures ET.

Grille par jour de bourse ET : créneaux de 5 min de 8:00 à 15:55 (96 créneaux ; 9:30 = 18, 15:55 = 95). Sortie « x » =
ouverture du créneau x, ou clôture de 15:55-16:00 si x = 96. Hasard « mêmes heures, autres jours » vectorisé.

    uv run --with pandas --with openpyxl python effets.py
"""
import os
import sys

import numpy as np
import pandas as pd

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [ICI]
from objectifs import prep, AN  # noqa: E402
from seuils import MILIEU  # noqa: E402

TICK, COMM, QTY, N_TIR, MIN_TRADES = 0.25, 1.25, 2, 2000, 30
NS = 96
S930, S1555 = 18, 95


def slot(h, m):
    return (h * 60 + m - 480) // 5


class Grille:
    def __init__(self, ins):
        B = prep(ins, 5)
        self.vp = B.attrs["val_point"]
        et = B.t.dt.tz_localize("Europe/Paris", ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("America/New_York")
        mn = (et.dt.hour * 60 + et.dt.minute).values
        ok = (mn >= 480) & (mn < 960) & (mn % 5 == 0) & et.notna().values
        jours = pd.Index(sorted(set(et[ok].dt.date)))
        # jours de bourse = jours avec au moins 70 créneaux de séance (9:30-16:00) présents
        d_i = jours.get_indexer(et[ok].dt.date)
        s_i = (mn[ok] - 480) // 5
        shape = (len(jours), NS)
        self.O, self.H, self.L, self.C, self.K4 = (np.full(shape, np.nan) for _ in range(5))
        for arr, col in ((self.O, "o"), (self.H, "h"), (self.L, "l"), (self.C, "c"), (self.K4, "k4")):
            arr[d_i, s_i] = B[col].values[ok]
        seance = np.isfinite(self.O[:, S930:]).sum(axis=1)
        garde = seance >= 70
        self.jours = pd.to_datetime(jours[garde])
        for nom in ("O", "H", "L", "C", "K4"):
            setattr(self, nom, getattr(self, nom)[garde])
        self.n = len(self.jours)
        self.cprev = np.r_[np.nan, self.C[:-1, S1555]]
        hd = np.nanmax(self.H[:, S930:], axis=1)
        ld = np.nanmin(self.L[:, S930:], axis=1)
        tr = np.maximum(hd, self.cprev) - np.minimum(ld, self.cprev)
        tr[0] = hd[0] - ld[0]
        self.atrd = pd.Series(tr).rolling(14).mean().shift(1).values
        self.h1 = np.asarray(self.jours < MILIEU)

    def pnl(self, d, se, x, sens, stop=None, obj=None):
        """Vectorisé : d, sens, stop, obj (distances en points depuis le prix d'entrée, nan = aucun) de même longueur,
        se / x scalaires. Rend le P&L par contrat (nan si une bougie manque)."""
        d = np.asarray(d)
        sens = np.asarray(sens, dtype=float)
        n = len(d)
        stop = np.full(n, np.nan) if stop is None else np.asarray(stop, dtype=float)
        obj = np.full(n, np.nan) if obj is None else np.asarray(obj, dtype=float)
        fill = self.O[d, se] + sens * TICK
        out = np.full(n, np.nan)
        ouvert = np.isfinite(fill)
        sl = fill - sens * stop
        tp = fill + sens * obj
        for s in range(se, min(x, NS)):
            h, l = self.H[d, s], self.L[d, s]
            touche_s = ouvert & np.isfinite(sl) & np.where(sens > 0, l <= sl, h >= sl)
            out[touche_s] = ((sl - sens * TICK - fill) * sens)[touche_s]
            ouvert &= ~touche_s
            touche_o = ouvert & np.isfinite(tp) & np.where(sens > 0, h >= tp, l <= tp)
            out[touche_o] = ((tp - fill) * sens)[touche_o]
            ouvert &= ~touche_o
        px = self.C[d, S1555] if x >= NS else self.O[d, x]
        out[ouvert] = ((px - sens * TICK - fill) * sens)[ouvert]
        return out * self.vp - 2 * COMM


# ------------------------------------------------------------------ règles : liste de trades (d, se, x, sens, stop, obj)
def trades(G, regle, **p):
    D, SE, X, SENS, ST, OB = [], [], [], [], [], []

    def ajoute(d, se, x, s, st=np.nan, ob=np.nan):
        D.append(d); SE.append(se); X.append(x); SENS.append(s); ST.append(st); OB.append(ob)

    O, C, H, L = G.O, G.C, G.H, G.L
    for d in range(1, G.n):
        if regle == "D1":
            fin_sig = slot(*p.get("fin_sig", (10, 0))) - 1          # clôture de la bougie qui finit à fin_sig
            ref = G.cprev[d] if p["var"] == "a" else O[d, S930]
            r = C[d, fin_sig] - ref
            if np.isfinite(r) and r != 0:
                ajoute(d, slot(*p.get("entree", (15, 30))), 96, np.sign(r))
        elif regle == "D2":
            nr = p["range"] // 5
            hi, lo = np.nanmax(H[d, S930:S930 + nr]), np.nanmin(L[d, S930:S930 + nr])
            for s in range(S930 + nr, slot(15, 0)):
                c = C[d, s]
                if not np.isfinite(c):
                    continue
                sens = 1 if c > hi else -1 if c < lo else 0
                if sens:
                    if p["filtre"] == "k4" and not ((G.K4[d, s] > 0) if sens > 0 else (G.K4[d, s] <= 0)):
                        break
                    fill = O[d, s + 1] + sens * TICK
                    st = (fill - lo) if sens > 0 else (hi - fill)
                    if st > 0:
                        ajoute(d, s + 1, p.get("sortie", S1555), sens, st, st * p.get("R", np.nan))
                    break
        elif regle == "D3":
            g = O[d, S930] - G.cprev[d]
            if np.isfinite(g) and np.isfinite(G.atrd[d]) and abs(g) > p["x"] * G.atrd[d]:
                s = -np.sign(g)
                fill = O[d, S930] + s * TICK
                ajoute(d, S930, slot(*p.get("sortie", (11, 0))), s, np.nan, abs(G.cprev[d] - fill))
        elif regle == "D4":
            jour = G.jours[d].date()
            for hh, mm in p["annonces"].get(jour, []):
                s0 = slot(hh, mm)
                attente = p.get("attente", 15) // 5
                r = C[d, s0 + attente - 1] - O[d, s0]
                if np.isfinite(r) and r != 0:
                    ajoute(d, s0 + attente, p.get("sortie", S1555), np.sign(r))
                    break                                   # une position à la fois : CPI et FOMC le même jour → le 1er
        elif regle == "D5":
            if d in p["tom"]:
                ajoute(d, slot(*p.get("entree", (9, 30))), S1555, 1)
        elif regle == "D6":
            e = slot(*p.get("entree", (15, 0)))
            r = C[d, e - 1] - O[d, S930]
            if np.isfinite(r) and r != 0:
                ajoute(d, e, p.get("sortie", S1555), np.sign(r))
    return pd.DataFrame(dict(d=D, se=SE, x=X, sens=SENS, stop=ST, obj=OB))


def jours_tom(G, apres=3):
    m = G.jours.to_period("M")
    tom = set()
    for i in range(G.n - 1):
        if m[i] != m[i + 1]:                     # i = dernier jour du mois
            tom.update(range(i, min(i + 1 + apres, G.n)))
    return tom


def evaluer(G, T):
    """P&L par trade (2 contrats) ; l'ordre des trades suit les jours (un par jour, sauf D4 regroupé)."""
    if T.empty:
        return np.array([])
    p = np.full(len(T), np.nan)
    for (se, x), g in T.groupby(["se", "x"]):
        p[g.index] = G.pnl(g.d.values, se, x, g.sens.values, g.stop.values, g.obj.values)
    return p * QTY


def mesure(G, T, p, masque_jours):
    m = masque_jours[T.d.values] & np.isfinite(p)
    x = p[m]
    if len(x) == 0:
        return dict(n=0, pnl=0.0, rc=np.nan, gain=np.nan)
    c = np.cumsum(x)
    dd = float(np.max(np.maximum.accumulate(np.r_[0, c])[1:] - c))
    jours = G.jours[masque_jours]
    ans = max((jours.max() - jours.min()).days, 1) / AN
    return dict(n=len(x), pnl=float(x.sum()), rc=(x.sum() / ans) / dd if dd > 0 else np.nan, gain=float((x > 0).mean()))


def hasard(G, T, p, masque_jours, ref, rng, n_tir=N_TIR):
    """Pour chaque trade de la période : n_tir autres jours de la même période, mêmes créneaux, même stop / objectif en
    ATR journalier ; sens au hasard (A, même part de longs) ou long (L). Rend les sommes de P&L par tirage."""
    m = masque_jours[T.d.values] & np.isfinite(p)
    Tm = T[m]
    cand = np.flatnonzero(masque_jours & np.isfinite(G.atrd))
    p_long = (Tm.sens > 0).mean() if len(Tm) else 0.5
    tot = np.zeros(n_tir)
    for r in Tm.itertuples():
        dd = rng.choice(cand, n_tir)
        k = G.atrd[dd] / G.atrd[r.d] if np.isfinite(G.atrd[r.d]) else np.ones(n_tir)
        sens = np.ones(n_tir) if ref == "L" else np.where(rng.random(n_tir) < p_long, 1.0, -1.0)
        x = G.pnl(dd, r.se, r.x, sens, r.stop * k, r.obj * k) * QTY
        tot += np.nan_to_num(x)
    return tot


def regles(G, annonces):
    tom = jours_tom(G)
    R = [("D1a", "D1", dict(var="a")), ("D1b", "D1", dict(var="b"))]
    for rg in (15, 30):
        for f in ("aucun", "k4"):
            R.append((f"D2-{rg}-{f}", "D2", dict(range=rg, filtre=f)))
    R += [("D3-0.5", "D3", dict(x=0.5)), ("D3-1", "D3", dict(x=1.0))]
    if annonces:
        R.append(("D4", "D4", dict(annonces=annonces)))
    R += [("D5", "D5", dict(tom=tom)), ("D6", "D6", dict())]
    return R


def plateau(G, nom, regle, p, annonces, h2):
    v = []
    if regle == "D1":
        v = [dict(p, fin_sig=f, entree=e) for f in ((9, 55), (10, 0), (10, 5)) for e in ((15, 25), (15, 30), (15, 35))]
        mini = 6
    elif regle == "D2":
        v = [dict(p, range=p["range"] + dr, sortie=S1555, R=R) for dr in (-5, 0, 5) for R in (np.nan, 1.0, 2.0)]
        mini = 6
    elif regle == "D3":
        v = [dict(p, x=p["x"] + dx, sortie=s) for dx in (-0.25, 0, 0.25) for s in ((10, 30), (11, 0), (11, 30))]
        mini = 6
    elif regle == "D4":
        v = [dict(p, attente=a, sortie=s) for a in (10, 15, 20) for s in (slot(15, 0), S1555)]
        mini = 4
    elif regle == "D5":
        v = [dict(p, tom=jours_tom(G, a), entree=e) for a in (2, 3, 4) for e in ((9, 30), (9, 45))]
        mini = 4
    elif regle == "D6":
        v = [dict(p, entree=e, sortie=s) for e in ((14, 45), (15, 0), (15, 15)) for s in (slot(15, 50), S1555)]
        mini = 4
    res = []
    for q in v:
        T = trades(G, regle, **q)
        res.append(mesure(G, T, evaluer(G, T), h2))
    pos = sum(r["pnl"] > 0 for r in res)
    return pos >= mini and np.nanmedian([r["rc"] for r in res]) > 0, f"{pos}/{len(res)}"


def charger_annonces():
    f = os.path.join(ICI, "calendrier_annonces.csv")
    if not os.path.exists(f):
        return None
    a = pd.read_csv(f)
    out = {}
    for r in a.itertuples():
        hh, mm = map(int, str(r.heure_et).split(":"))
        out.setdefault(pd.Timestamp(r.date).date(), []).append((hh, mm))
    return out


def main():
    annonces = charger_annonces()
    print(f"Calendrier des annonces : {'présent, ' + str(sum(len(v) for v in annonces.values())) + ' annonces' if annonces else 'ABSENT : D4 non testé'}")
    n_tests = 22
    lignes, cand = [], []
    for ins in ("MNQ", "MES"):
        G = Grille(ins)
        h1, h2 = G.h1, ~G.h1
        print(f"{ins} : {G.n} jours de bourse, {G.jours.min():%d/%m/%Y} → {G.jours.max():%d/%m/%Y}", flush=True)
        for nom, regle, p in regles(G, annonces):
            T = trades(G, regle, **p)
            pn = evaluer(G, T)
            r = mesure(G, T, pn, h1)
            refs = ("L",) if regle == "D5" else ("A", "L")
            pv = {}
            for ref in refs:
                pv[ref] = np.nan
                if r["n"] >= MIN_TRADES and r["pnl"] > 0:
                    tot = hasard(G, T, pn, h1, ref, np.random.default_rng(5669))
                    pv[ref] = (np.sum(tot >= r["pnl"]) + 1) / (N_TIR + 1)
            s = 0.05 / n_tests
            ok = r["n"] >= MIN_TRADES and r["pnl"] > 0 and all(pv[x] < s for x in refs)
            d = dict(ins=ins, regle=nom, H1_n=r["n"], H1_pnl=r["pnl"], H1_gain=r["gain"], H1_rc=r["rc"],
                     H1_pA=pv.get("A", np.nan), H1_pL=pv["L"], candidat=ok)
            lignes.append(d)
            print(f"  {ins} {nom:<12} H1 : {r['n']:4d} tr {r['gain'] if r['n'] else 0:.0%} {r['pnl']:>9,.0f} $ R/C {r['rc']:.2f}"
                  f" p_A {pv.get('A', np.nan):.4f} p_L {pv['L']:.4f}" + ("  ← candidat" if ok else ""), flush=True)
            if ok:
                cand.append((ins, nom, regle, p))
    T_ = pd.DataFrame(lignes)
    print(f"\nCandidats H1 : {len(cand)} sur {len(T_)}")
    for ins, nom, regle, p in cand:
        G = Grille(ins)
        h2 = ~G.h1
        T = trades(G, regle, **p)
        pn = evaluer(G, T)
        r = mesure(G, T, pn, h2)
        refs = ("L",) if regle == "D5" else ("A", "L")
        pv = {ref: (np.sum(hasard(G, T, pn, h2, ref, np.random.default_rng(5669)) >= r["pnl"]) + 1) / (N_TIR + 1) for ref in refs}
        pl, txt = plateau(G, nom, regle, p, annonces, h2)
        s = 0.05 / len(cand)
        passe = r["pnl"] > 0 and all(pv[x] < s for x in refs) and pl
        i = T_.index[(T_.ins == ins) & (T_.regle == nom)][0]
        T_.loc[i, ["H2_n", "H2_pnl", "H2_rc", "H2_pA", "H2_pL", "plateau", "passe"]] = \
            [r["n"], r["pnl"], r["rc"], pv.get("A", np.nan), pv["L"], txt, passe]
        print(f"  H2 {ins} {nom} : {r['n']} tr {r['pnl']:+,.0f} $ R/C {r['rc']:.2f} p_A {pv.get('A', np.nan):.4f} p_L {pv['L']:.4f}"
              f" (seuil {s:.4f}) ; plateau {txt} → {'PASSE' if passe else 'non'}", flush=True)
        if passe:
            m = h2[T.d.values] & np.isfinite(pn)
            X = T[m].assign(jour=G.jours[T[m].d.values].date, pnl_2_contrats=pn[m])
            X.to_csv(os.path.join(ICI, f"effets_trades_H2_{ins}_{nom}.csv"), index=False)
    T_.to_csv(os.path.join(ICI, "effets_resultats.csv"), index=False)


if __name__ == "__main__":
    main()
