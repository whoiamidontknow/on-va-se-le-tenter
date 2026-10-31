#!/usr/bin/env python3
"""Validation croisee de la regle Climax sur les CSV TradingView.

La regle vient de l'API (XYZ100 uniquement, cf. tools/ephore_api/NOTES_CLIMAX.md).
Ce script la confronte aux colonnes "Climax BUY/SELL (confirmed)" des exports
TradingView : autre instrument (MES, NQ), autre source, 7 unites de temps.

Resultat du 10/10 : rappel 454/500 = 90.8 %, precision 80.9 % sur 21 fichiers.

Usage : python3 tools/climax_csv_check.py
"""
import csv, glob, os

RULE = dict(buy_body=0.55, buy_vr=1.5, sell_body=0.65, sell_vr=2.0)


def load(p):
    rows = list(csv.reader(open(p, newline="")))
    hdr, data = rows[0], [r for r in rows[1:] if r and r[0]]
    idx = {n.strip(): i for i, n in enumerate(hdr)}
    if not all(k in idx for k in
               ("Volume", "Climax BUY (confirmed)", "Climax SELL (confirmed)")):
        return None
    def num(r, i, d=0.0):
        try: return float(r[i])
        except (ValueError, IndexError): return d
    return dict(
        o=[num(r, 1) for r in data], h=[num(r, 2) for r in data],
        l=[num(r, 3) for r in data], c=[num(r, 4) for r in data],
        v=[num(r, idx["Volume"]) for r in data],
        cb=[num(r, idx["Climax BUY (confirmed)"]) != 0 for r in data],
        cs=[num(r, idx["Climax SELL (confirmed)"]) != 0 for r in data])


def check(d):
    N = len(d["c"]); O, H, L, C, V = d["o"], d["h"], d["l"], d["c"], d["v"]
    vma = [sum(V[i - 19:i + 1]) / 20 if i >= 19 else None for i in range(N)]
    tp = fp = fn = 0
    for i in range(60, N):
        rg = H[i] - L[i]
        if rg <= 0 or not vma[i]:
            continue
        body = (C[i] - O[i]) / rg; vr = V[i] / vma[i]
        ours = ((O[i] == L[i] and body >= RULE["buy_body"] and vr >= RULE["buy_vr"])
                or (O[i] == H[i] and -body >= RULE["sell_body"] and vr >= RULE["sell_vr"]))
        orig = d["cb"][i] or d["cs"][i]
        if ours and orig: tp += 1
        elif ours: fp += 1
        elif orig: fn += 1
    return tp, fp, fn


def main():
    root = os.path.expanduser("~/ERGON")
    files = sorted(glob.glob(f"{root}/Singal/*.csv")) + sorted(glob.glob(f"{root}/Filtres/*.csv"))
    hdr = f"{'fichier':<30}{'barres':>7}{'orig B/S':>10}{'exact':>7}{'trop':>6}{'manq':>6}"
    print(hdr); print("-" * len(hdr))
    TP = FP = FN = 0
    for f in files:
        d = load(f)
        if not d:
            continue
        tp, fp, fn = check(d); TP += tp; FP += fp; FN += fn
        print(f"{os.path.basename(f)[:29]:<30}{len(d['c']):>7}"
              f"{f'{sum(d[chr(99)+chr(98)])}/{sum(d[chr(99)+chr(115)])}':>10}{tp:>7}{fp:>6}{fn:>6}")
    print("-" * len(hdr))
    print(f"{'TOTAL':<30}{'':>7}{'':>10}{TP:>7}{FP:>6}{FN:>6}")
    if TP + FN:
        print(f"\nrappel {TP}/{TP+FN} = {100*TP/(TP+FN):.1f} %   "
              f"precision {TP}/{TP+FP} = {100*TP/max(TP+FP,1):.1f} %")


if __name__ == "__main__":
    main()
