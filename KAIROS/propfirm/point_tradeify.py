#!/usr/bin/env python3
"""point_tradeify.py — point hebdomadaire sur le compte Tradeify Select 50k.

Lancé le samedi, avec le comparatif des fantômes.

Les règles viennent de regles.toml, bloc [tradeify_50k_select_flex], relevé le
16/10 sur le centre d'aide Tradeify. La règle de CONSISTANCE est celle qu'on
oublie : on peut atteindre l'objectif et ne pas valider.

    # rapide, juste le solde
    python3 point_tradeify.py --solde 51200

    # complet, avec le détail par jour (date,pnl — export CSV depuis Numbers)
    python3 point_tradeify.py --jours jours.csv
"""
import argparse
import csv
import pathlib
import sys

DEPART = 50_000
OBJECTIF = 3_000          # objectif_eval_usd
DD = 2_000                # drawdown_usd, EOD trailing
JOURS_MIN = 3             # jours_min_eval
CONSISTANCE = 40          # consistance_eval_pct — aucune journée > 40 % du profit
PLAFOND_DD = 50_100       # le plancher se fige ici...
DECLENCHEUR = 52_100      # ...quand le solde atteint ça
MICROS = 2                # la méthode : 2 micros fixes (max 40)


def barre(x, total, n=22):
    r = max(0.0, min(1.0, x / total))
    return "█" * round(n * r) + "·" * (n - round(n * r))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--solde", type=float, help="solde actuel du compte")
    a.add_argument("--jours", help="CSV date,pnl — une ligne par journée tradée")
    args = a.parse_args()

    jours = []
    if args.jours:
        p = pathlib.Path(args.jours)
        if not p.exists():
            sys.exit(f"introuvable : {p}")
        for r in csv.reader(p.open()):
            if len(r) < 2:
                continue
            try:
                jours.append((r[0].strip(), float(str(r[1]).replace(",", "."))))
            except ValueError:
                continue

    profit = (args.solde - DEPART) if args.solde is not None else sum(p for _, p in jours)
    solde = args.solde if args.solde is not None else DEPART + profit

    print("═" * 60)
    print("  TRADEIFY SELECT 50k — point hebdomadaire")
    print("═" * 60)
    print(f"\n  Solde      {solde:>12,.0f} $")
    print(f"  Profit     {profit:>+12,.0f} $\n")

    # 1 — objectif
    print(f"  Objectif   {barre(profit, OBJECTIF)}  "
          f"{profit:+,.0f} / {OBJECTIF:,} $")
    if profit >= OBJECTIF:
        print("             ✓ atteint")
    else:
        print(f"             il reste {OBJECTIF - profit:,.0f} $")

    # 2 — plancher de liquidation (EOD trailing)
    pic = max(DEPART, solde)
    if args.jours and jours:
        c = DEPART
        pic = DEPART
        for _, p in jours:
            c += p
            pic = max(pic, c)
    plancher = min(pic - DD, PLAFOND_DD) if pic >= DECLENCHEUR else pic - DD
    marge = solde - plancher
    print(f"\n  Plancher   {plancher:>12,.0f} $   (EOD trailing, {DD:,} $ sous le pic)")
    print(f"  Marge      {marge:>12,.0f} $"
          + ("   ⚠ moins d'un stop de marge" if marge < 400 else ""))
    if pic >= DECLENCHEUR:
        print(f"             plancher figé à {PLAFOND_DD:,} $ (pic ≥ {DECLENCHEUR:,})")

    # 3 — jours tradés
    if jours:
        print(f"\n  Jours      {len(jours)} / {JOURS_MIN} minimum"
              + ("   ✓" if len(jours) >= JOURS_MIN else
                 f"   il en manque {JOURS_MIN - len(jours)}"))

    # 4 — LA RÈGLE QU'ON OUBLIE
    print(f"\n  ── Consistance ({CONSISTANCE} % max par journée) ──")
    if not jours:
        print("     non calculable : relancer avec --jours")
        print("     C'est la règle qui bloque une éval pourtant réussie.")
    else:
        gains = [(d, p) for d, p in jours if p > 0]
        total = sum(p for _, p in gains)
        if total <= 0:
            print("     aucun jour gagnant")
        else:
            d, meilleur = max(gains, key=lambda x: x[1])
            part = 100 * meilleur / total
            print(f"     meilleure journée : {d}  {meilleur:+,.0f} $  "
                  f"= {part:.0f} % du profit brut")
            if part > CONSISTANCE:
                besoin = meilleur / (CONSISTANCE / 100) - total
                print(f"     ✗ DÉPASSE. Il faut {besoin:,.0f} $ de profit ailleurs")
                print(f"       pour repasser sous {CONSISTANCE} %.")
            else:
                marge_c = meilleur / (CONSISTANCE / 100) - total
                print(f"     ✓ sous la limite (marge {-marge_c:,.0f} $ "
                      f"avant de la franchir)")

    print(f"\n  Taille     {MICROS} micros fixes (méthode) — max 40")
    print("\n" + "═" * 60)
    print("  Rappels : pas de perte journalière max en Select Flex.")
    print("  Payout : 5 jours tradés minimum, 250 $ mini, 50 % du profit,")
    print("  plafonné à 2 500 $ par demande. Une demande fige le plancher.")
    print("═" * 60)


if __name__ == "__main__":
    main()
