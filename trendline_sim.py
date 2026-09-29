#!/usr/bin/env python3
"""Simulateur de la logique TRENDLINES V2 (cf. trendlinediag.md).

But : verifier le comportement de l'algo et choisir les reglages sans passer par
TradingView. Pas de verite terrain necessaire — on mesure si les droites produites
sont plausibles : combien, combien de temps, quelle couverture.

Usage:
    python3 trendline_sim.py "CME_MINI_MES1!, 15_bb0d6.csv"
"""
import csv
import sys
from dataclasses import dataclass

BARS_PER_DAY = 92  # MES 15 min, session ~23h


def load(path):
    o, h, l, c = [], [], [], []
    with open(path, newline="") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            if len(row) < 5 or not row[1]:
                continue
            o.append(float(row[1]))
            h.append(float(row[2]))
            l.append(float(row[3]))
            c.append(float(row[4]))
    return o, h, l, c


def pivots(src, L, high=True):
    """Retourne {bar_de_confirmation: (bar_du_pivot, valeur)}.

    Equivalent de ta.pivothigh/pivotlow(src, L, L) : le pivot est en i, confirme
    en i+L. Strict a gauche, tolerant a droite (comme Pine).
    """
    out = {}
    n = len(src)
    for i in range(L, n - L):
        v = src[i]
        left = src[i - L:i]
        right = src[i + 1:i + L + 1]
        if high:
            if v > max(left) and v >= max(right):
                out[i + L] = (i, v)
        else:
            if v < min(left) and v <= min(right):
                out[i + L] = (i, v)
    return out


@dataclass
class Line:
    x1: int
    y1: float
    sl: float
    tc: int
    born: int


def best_line(pp, pb, is_res, lb, viol_buf, touch_buf, min_sep, min_touch,
              px_ref, bar_index, pair_cap=12, hull_cap=30):
    """Port fidele de f_best_line, avec buffers de violation et de touche separes."""
    sz = len(pp)
    if sz < 2:
        return None
    cap = min(sz - 1, pair_cap - 1)
    hcap = min(sz - 1, hull_cap - 1)
    best = None
    b_tc, b_span, b_dist = 0, 0, 1e12

    for i in range(0, cap):
        for j in range(i + 1, cap + 1):
            xa, ya = pb[i], pp[i]   # plus recent
            xb, yb = pb[j], pp[j]   # plus ancien = ancrage
            if not (xa > xb and (xa - xb) >= min_sep and (bar_index - xb) <= lb):
                continue
            sl = (ya - yb) / (xa - xb)
            if is_res and sl > 0:
                continue
            if not is_res and sl < 0:
                continue
            now_y = yb + sl * (bar_index - xb)
            if is_res and not now_y > px_ref:
                continue
            if not is_res and not now_y < px_ref:
                continue

            viol = False
            tc = 0
            for k in range(0, hcap + 1):
                xk, yk = pb[k], pp[k]
                if xk < xb or (bar_index - xk) > lb:
                    continue
                ly = yb + sl * (xk - xb)
                vbf = abs(ly) * viol_buf / 100.0
                tbf = abs(ly) * touch_buf / 100.0
                if is_res and yk > ly + vbf:
                    viol = True
                if (not is_res) and yk < ly - vbf:
                    viol = True
                if abs(yk - ly) <= tbf:
                    tc += 1
            if viol or tc < min_touch:
                continue

            span = xa - xb
            dist = abs(px_ref - now_y) / px_ref * 100.0
            better = (tc > b_tc
                      or (tc == b_tc and span > b_span)
                      or (tc == b_tc and span == b_span and dist < b_dist))
            if better:
                b_tc, b_span, b_dist = tc, span, dist
                best = Line(xb, yb, sl, tc, bar_index)
    return best


def run_side(h_or_l, close, is_res, piv_len, lb, viol_buf, touch_buf,
             min_span, min_touch):
    piv = pivots(h_or_l, piv_len, high=is_res)
    pp, pb = [], []          # newest first, cap 50
    active = None
    adopted, breaks, lifetimes, active_bars = 0, 0, [], 0
    min_sep = min_span * piv_len

    for bi in range(len(close)):
        if bi in piv:
            pbar, pval = piv[bi]
            pp.insert(0, pval)
            pb.insert(0, pbar)
            if len(pp) > 50:
                pp.pop()
                pb.pop()

        broke = False
        if active is not None:
            now_y = active.y1 + active.sl * (bi - active.x1)
            bf = abs(now_y) * viol_buf / 100.0
            if (is_res and close[bi] > now_y + bf) or \
               ((not is_res) and close[bi] < now_y - bf):
                broke = True
                breaks += 1
                lifetimes.append(bi - active.born)
                active = None

        if active is None and (bi in piv or broke):
            cand = best_line(pp, pb, is_res, lb, viol_buf, touch_buf,
                             min_sep, min_touch, close[bi], bi)
            if cand is not None:
                active = cand
                adopted += 1

        if active is not None:
            active_bars += 1

    n = len(close)
    days = n / BARS_PER_DAY
    return {
        "adopted": adopted,
        "breaks": breaks,
        "per_day": adopted / days,
        "coverage": 100.0 * active_bars / n,
        "mean_life": sum(lifetimes) / len(lifetimes) if lifetimes else 0.0,
    }


def main():
    path = sys.argv[1]
    o, h, l, c = load(path)
    print(f"{path} — {len(c)} barres ({len(c)/BARS_PER_DAY:.0f} jours)\n")

    viol_buf, touch_buf = 0.04, 0.20
    min_span, min_touch = 2, 3
    lb_res, lb_sup = 250, 150

    hdr = (f"{'piv':>4} | {'res/j':>6} {'res cov%':>9} {'res vie':>8} "
           f"{'res cass':>9} | {'sup/j':>6} {'sup cov%':>9} {'sup vie':>8} {'sup cass':>9}")
    print(hdr)
    print("-" * len(hdr))
    for piv_len in (5, 8, 10, 13, 16, 20):
        r = run_side(h, c, True,  piv_len, lb_res, viol_buf, touch_buf, min_span, min_touch)
        s = run_side(l, c, False, piv_len, lb_sup, viol_buf, touch_buf, min_span, min_touch)
        print(f"{piv_len:>4} | {r['per_day']:>6.2f} {r['coverage']:>9.1f} "
              f"{r['mean_life']:>8.1f} {r['breaks']:>9} | "
              f"{s['per_day']:>6.2f} {s['coverage']:>9.1f} "
              f"{s['mean_life']:>8.1f} {s['breaks']:>9}")

    print(f"\n(viol_buf={viol_buf}%  touch_buf={touch_buf}%  "
          f"min_span={min_span}x  min_touch={min_touch})")

    print("\n— Sensibilite min_touch (piv_len=10) —")
    for mt in (2, 3, 4):
        r = run_side(h, c, True,  10, lb_res, viol_buf, touch_buf, min_span, mt)
        s = run_side(l, c, False, 10, lb_sup, viol_buf, touch_buf, min_span, mt)
        print(f"  min_touch={mt} : res {r['per_day']:.2f}/j cov {r['coverage']:.0f}% "
              f"| sup {s['per_day']:.2f}/j cov {s['coverage']:.0f}%")

    print("\n— Sensibilite viol_buf (piv_len=10, min_touch=3) —")
    for vb in (0.02, 0.04, 0.08, 0.15):
        r = run_side(h, c, True,  10, lb_res, vb, touch_buf, min_span, min_touch)
        s = run_side(l, c, False, 10, lb_sup, vb, touch_buf, min_span, min_touch)
        print(f"  viol_buf={vb:.2f}% : res {r['per_day']:.2f}/j cov {r['coverage']:.0f}% "
              f"vie {r['mean_life']:.0f} | sup {s['per_day']:.2f}/j cov {s['coverage']:.0f}% "
              f"vie {s['mean_life']:.0f}")


if __name__ == "__main__":
    main()
