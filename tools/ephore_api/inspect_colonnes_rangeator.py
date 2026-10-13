#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contre-verification ciblee des colonnes Rangeator.

Deuxieme methode, independante de inspect_colonnes.py : aucun float() n'est
utilise pour decider si une cellule porte une donnee. On compte simplement
les valeurs brutes distinctes, OCCURRENCE PAR OCCURRENCE de l'en-tete.
"""
import csv, os, glob, collections

ROOTS = ["/Users/jeremk/Ephore/Base 10:10/Ajustements",
         "/Users/jeremk/Ephore/Base 10:10/base",
         "/Users/jeremk/Ephore/Lun12:10", "/Users/jeremk/Ephore/Singal",
         "/Users/jeremk/Ephore/Filtres", "/Users/jeremk/Ephore/Trendlinehelper",
         "/Users/jeremk/Ephore"]
PAT = ("rangeator", "cassure", "break", "median", "equilib")

tot = collections.Counter()
seen = set()
for r in ROOTS:
    for p in sorted(glob.glob(os.path.join(r, "*.csv"))):
        rp = os.path.realpath(p)
        if rp in seen: continue
        seen.add(rp)
        with open(p, newline="", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            try: hdr = next(rd)
            except StopIteration: continue
            idxs = [i for i,h in enumerate(hdr)
                    if any(k in h.lower() for k in PAT)]
            if not idxs: continue
            vals = {i: collections.Counter() for i in idxs}
            for row in rd:
                for i in idxs:
                    if i < len(row):
                        vals[i][row[i].strip()] += 1
            print(f"{p}")
            for i in idxs:
                c = vals[i]
                dist = dict(c.most_common(8))
                tot[hdr[i]] += sum(v for k,v in c.items()
                                   if k not in ("", "0", "NaN", "nan"))
                print(f"   col#{i:>3} {hdr[i]!r:<34} valeurs brutes distinctes = {dist}")
print("\n--- TOTAL cellules porteuses (hors vide/0/NaN), toutes occurrences, tous fichiers ---")
for k,v in tot.items():
    print(f"  {k!r:<34} {v}")
