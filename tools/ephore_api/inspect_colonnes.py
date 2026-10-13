#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inventaire sans a priori des colonnes de TOUS les CSV d'export TradingView.

Pour chaque fichier : chaque colonne (chaque OCCURRENCE separement, car les
en-tetes sont dupliques), avec le nombre de cellules non vides et non nulles.
Test numerique : float(x) != 0  (et NON bool(x), car bool("0") == True).
"""
import csv, os, sys, glob, math

ROOTS = [
    "/Users/jeremk/Ephore/Base 10:10/Ajustements",
    "/Users/jeremk/Ephore/Base 10:10/base",
    "/Users/jeremk/Ephore/Lun12:10",
    "/Users/jeremk/Ephore/Singal",
    "/Users/jeremk/Ephore/Filtres",
    "/Users/jeremk/Ephore/Trendlinehelper",
    "/Users/jeremk/Ephore",
]

def files():
    seen = set()
    out = []
    for r in ROOTS:
        for p in sorted(glob.glob(os.path.join(r, "*.csv"))):
            rp = os.path.realpath(p)
            if rp in seen:
                continue
            seen.add(rp)
            out.append(p)
    return out

def stats(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        try:
            hdr = next(rd)
        except StopIteration:
            return None, [], 0
        n = len(hdr)
        nonempty = [0]*n
        nonzero  = [0]*n
        numeric  = [0]*n
        mn = [None]*n
        mx = [None]*n
        distinct = [set() for _ in range(n)]
        rows = 0
        for row in rd:
            rows += 1
            for i in range(min(n, len(row))):
                v = row[i].strip()
                if v == "":
                    continue
                nonempty[i] += 1
                if len(distinct[i]) < 12:
                    distinct[i].add(v)
                try:
                    x = float(v.replace(",", "."))
                except ValueError:
                    nonzero[i] += 1   # texte non vide = donnee
                    continue
                if math.isnan(x):
                    continue
                numeric[i] += 1
                if x != 0.0:
                    nonzero[i] += 1
                mn[i] = x if mn[i] is None else min(mn[i], x)
                mx[i] = x if mx[i] is None else max(mx[i], x)
        cols = []
        for i in range(n):
            cols.append(dict(idx=i, name=hdr[i], nonempty=nonempty[i],
                             nonzero=nonzero[i], numeric=numeric[i],
                             mn=mn[i], mx=mx[i],
                             sample=sorted(distinct[i])[:6]))
        return hdr, cols, rows

KEYS = ["range","rangeator","cassure","break","median","mediane","haut","bas",
        "equilib","top","bottom","plot","equi","box","zone","mid","borne",
        "sup","inf","high","low"]

def main():
    only_hits = "--hits" in sys.argv
    for p in files():
        hdr, cols, rows = stats(p)
        if hdr is None:
            continue
        print("="*100)
        print(f"FICHIER {p}   ({rows} lignes, {len(hdr)} colonnes)")
        # comptage des doublons d'en-tete
        from collections import Counter
        c = Counter(hdr)
        dup = {k:v for k,v in c.items() if v > 1}
        if dup:
            print(f"  en-tetes dupliques : {sorted(dup.items(), key=lambda t:-t[1])[:14]}")
        for col in cols:
            nm = col["name"]
            hit = any(k in nm.lower() for k in KEYS)
            if only_hits and not hit and col["nonzero"] > 0:
                pass
            flag = " <<<" if hit else ""
            rng = ""
            if col["mn"] is not None:
                rng = f" [{col['mn']:.6g} .. {col['mx']:.6g}]"
            print(f"  #{col['idx']:>3} {nm!r:<46} nonvide={col['nonempty']:>6} "
                  f"nonzero={col['nonzero']:>6}{rng}{flag}")
        sys.stdout.flush()

main()
