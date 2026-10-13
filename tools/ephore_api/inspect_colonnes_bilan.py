#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bilan global : pour chaque NOM de colonne, et pour chaque RANG d'occurrence
de ce nom dans le fichier (1er groupe, 2e groupe...), le total de cellules
porteuses de donnee sur tout le corpus.  Test : float(x) != 0, jamais bool(x).
"""
import csv, os, glob, collections, math

ROOTS = ["/Users/jeremk/Ephore/Base 10:10/Ajustements",
         "/Users/jeremk/Ephore/Base 10:10/base",
         "/Users/jeremk/Ephore/Lun12:10", "/Users/jeremk/Ephore/Singal",
         "/Users/jeremk/Ephore/Filtres", "/Users/jeremk/Ephore/Trendlinehelper",
         "/Users/jeremk/Ephore"]
SKIP = ("trades_",)

ne = collections.Counter(); nz = collections.Counter(); fi = collections.Counter()
seen = set()
for r in ROOTS:
    for p in sorted(glob.glob(os.path.join(r, "*.csv"))):
        rp = os.path.realpath(p)
        if rp in seen or any(s in os.path.basename(p) for s in SKIP): continue
        seen.add(rp)
        with open(p, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            try: hdr = next(rd)
            except StopIteration: continue
            rank = collections.Counter(); keys = []
            for h in hdr:
                rank[h] += 1
                keys.append((h, rank[h]))
            for k in set(keys): fi[k] += 1
            for row in rd:
                for i, k in enumerate(keys):
                    if i >= len(row): continue
                    v = row[i].strip()
                    if v == "": continue
                    ne[k] += 1
                    try: x = float(v.replace(",", "."))
                    except ValueError: nz[k] += 1; continue
                    if not math.isnan(x) and x != 0.0: nz[k] += 1

print(f"{'colonne':<34} {'occ#':>4} {'fichiers':>8} {'nonvide':>9} {'nonzero':>9}")
for k in sorted(ne, key=lambda k: (k[0], k[1])):
    print(f"{k[0]:<34} {k[1]:>4} {fi[k]:>8} {ne[k]:>9} {nz[k]:>9}")
