#!/usr/bin/env python3
"""maj_suivi.py — régénère suivi_trades.numbers depuis les exports TradingView.

POURQUOI CE SCRIPT EXISTE
Jusqu'ici le suivi était reconstruit à la main chaque samedi. C'est lent, et
surtout ça perd les colonnes que Jeremy remplit lui-même (« Pris ? », « Mon
entrée », « Remarque »…) dès qu'on se trompe d'une ligne.

Le script sépare donc nettement deux choses :
  - les colonnes 1 à 8, calculées depuis les exports, toujours réécrites ;
  - les colonnes 9 à 15, saisies par Jeremy, RECOPIÉES depuis l'ancien fichier
    en appariant sur (symbole, date, heure). Elles ne sont jamais inventées.

Un trade qui disparaît d'un export emporte ses annotations : c'est voulu, on ne
garde pas de lignes orphelines. Mais on les affiche avant d'écrire.

    python3 KAIROS/suivi/maj_suivi.py KAIROS-data/Backtest/07nov
"""
import datetime as dt
import glob
import os
import re
import shutil
import sys
import zoneinfo

import openpyxl
from numbers_parser import Document

PARIS = zoneinfo.ZoneInfo("Europe/Paris")
CIBLE = "/Users/jeremk/ERGON/KAIROS-data/suivi_trades.numbers"
SECOURS = "/Users/jeremk/ERGON/KAIROS-data/.recuperation_annotations.tsv"
BACKUPS_MAX = 2          # consigne de Jeremy du 05/11

COLS = ["Symbole", "Date", "Heure", "Sens", "Étiquette", "Résultat",
        "P&L alerte $", "Fantôme ?", "Pris ?", "Si non, pourquoi",
        "Mon entrée", "Ma sortie", "Mon P&L $", "P&L FTMO $", "Remarque"]
# Le même instrument n'a pas le même nom partout : le suivi dit « BTCUSD »,
# l'export TradingView dit « BTC1! ». On apparie sur les deux.
ALIAS = {"BTC1!": ("BTCUSD",), "BTCUSD": ("BTC1!",)}

AUTO = 8                 # les 8 premières sont recalculées, le reste est à lui

# Quel export alimente quel onglet. Le 5 min est le terrain du bot : il a son
# propre onglet pour ne pas se mélanger au test manuel des 30 trades en 15 min.
ONGLETS = [
    ("MNQ",              "MNQ1!",  "15"),
    ("MES",              "MES1!",  "15"),
    ("BTC",              "BTC1!",  "15"),
    ("MNQ 5 min (bot)",  "MNQ1!",  "5"),
]


def unite(chemin):
    """5 ou 15 minutes, déduit des minutes d'entrée réellement présentes."""
    wb = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    rows = list(wb["Trades"].iter_rows(values_only=True))
    wb.close()
    iD = rows[0].index("Date et heure")
    mins = {d.minute for d in (r[iD] for r in rows[1:])
            if isinstance(d, dt.datetime)}
    return "15" if mins and all(m % 15 == 0 for m in mins) else "5"


def lire_export(chemin):
    """Les trades d'un export, appariés entrée/sortie par numéro de trade."""
    wb = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    rows = list(wb["Trades"].iter_rows(values_only=True))
    wb.close()
    h = rows[0]
    iN, iT, iD = h.index("Numéro de trade"), h.index("Type"), h.index("Date et heure")
    iS, iP = h.index("Signal"), h.index("P&L net USD")

    paires = {}
    for r in rows[1:]:
        num, typ = r[iN], str(r[iT] or "")
        if not isinstance(r[iD], dt.datetime):
            continue                      # « Ouverture » : trade encore en cours
        d = paires.setdefault(num, {})
        if typ.startswith("Entrer"):
            d["date"], d["sig"], d["pnl"] = r[iD], str(r[iS] or ""), r[iP]
        elif typ.startswith("Sortir"):
            d["sortie"] = str(r[iS] or "")

    out = []
    for num, d in sorted(paires.items()):
        if "date" not in d:
            continue
        sig = d["sig"]
        out.append({
            "dt":    d["date"],
            "sens":  "long" if sig.startswith("L") else "short",
            # « L 2 · GODLIKE |SP0 » -> « GODLIKE »
            "label": re.sub(r"^[LS] \d+ · ", "", sig).split(" |")[0].strip(),
            "res":   sortie_fr(d.get("sortie", "")),
            "pnl":   d.get("pnl"),
        })
    return out


def sortie_fr(s):
    """« Obj L » -> « objectif ». Le libellé brut ne dit rien à la lecture."""
    s = s.lower()
    if "obj" in s:
        return "objectif"
    if "stop" in s:
        return "stop"
    if "temps" in s or "time" in s:
        return "temps"
    if "fin" in s or "flat" in s:
        return "fin de fenêtre"
    return s or "—"


def lire_alertes(chemin):
    """Les instants d'alerte par symbole, en heure de Paris.

    Le journal est en UTC ; les exports sont en heure locale. Sans conversion
    l'écart vaut une ou deux heures selon la date, et TOUT paraît fantôme.
    """
    import csv
    par_sym = {}
    with open(chemin, newline="", encoding="utf-8") as fh:
        for l in csv.DictReader(fh):
            tick, heure = l.get("Ticker", ""), l.get("Heure", "")
            desc = l.get("Description", "")
            if not heure or "FERMER" in desc:
                continue
            m = re.search(r":([A-Z0-9!.]+), *(\d+)m", tick)
            if not m:
                continue                 # unités en h ou en jours : pas nos bots
            try:
                u = dt.datetime.fromisoformat(heure.replace("Z", "+00:00"))
            except ValueError:
                continue
            par_sym.setdefault((m.group(1), m.group(2)), set()).add(
                u.astimezone(PARIS).replace(tzinfo=None))
    return par_sym


def main():
    dossier = sys.argv[1] if len(sys.argv) > 1 else "."
    xlsx = glob.glob(os.path.join(dossier, "*.xlsx"))
    csvs = glob.glob(os.path.join(dossier, "*Alerts_Log*.csv"))
    if not xlsx:
        sys.exit(f"aucun .xlsx dans {dossier}")

    # ranger les exports par (symbole, unité)
    sources = {}
    for f in xlsx:
        m = re.search(r"CME(?:_MINI)?_([A-Z0-9!]+)_", f)
        if m:
            sources[(m.group(1), unite(f))] = f

    alertes = lire_alertes(csvs[0]) if csvs else {}
    print(f"  {len(sources)} exports, "
          f"{sum(len(v) for v in alertes.values())} alertes\n")

    # --- annotations existantes, à ne jamais perdre -----------------------
    # On lit TOUTES les sources, pas seulement la plus récente.
    #
    # Le 07/11 une passe fautive a écrit un fichier amputé de 12 annotations,
    # puis la rotation a supprimé l'original — seule copie qui les contenait.
    # Lire « la dernière sauvegarde » suffit tant que la dernière est bonne ;
    # c'est précisément l'hypothèse qui a sauté. On fusionne donc le courant,
    # toutes les sauvegardes et le filet TSV, et pour chaque trade on retient
    # la version la PLUS RENSEIGNÉE. Une annotation ne peut plus disparaître
    # par écrasement : il faudrait qu'elle disparaisse de partout à la fois.
    anciennes, orphelines, lignes_av = {}, {}, 0

    def richesse(cells):
        return sum(1 for x in cells if x not in (None, "", "—", "None"))

    copies = [CIBLE] + sorted(glob.glob(f"{CIBLE[:-8]}_backup_*.numbers"))
    for src in copies:
        if not os.path.exists(src):
            continue
        for sh in Document(src).sheets:
            for t in sh.tables:
                for r in t.rows(values_only=True)[1:]:
                    if not r or not r[0]:
                        continue
                    lignes_av += 1
                    cle = (str(r[0]), str(r[1]), str(r[2]))
                    manuel = list(r[AUTO:])
                    if richesse(manuel) >= richesse(anciennes.get(cle, [])):
                        anciennes[cle] = manuel
                    if richesse(manuel):
                        orphelines[cle] = (sh.name, list(r))

    # filet : lignes reconstituées depuis les transcriptions de session
    if os.path.exists(SECOURS):
        n = 0
        for ligne in open(SECOURS, encoding="utf-8"):
            c = ligne.rstrip("\n").split("\t")
            if len(c) < 15:
                continue
            cle = (c[0], c[1], c[2])
            if richesse(c[AUTO:]) > richesse(anciennes.get(cle, [])):
                anciennes[cle] = c[AUTO:]
                n += 1
            if richesse(c[AUTO:]):
                onglet = {"MNQ1!": "MNQ", "MES1!": "MES"}.get(c[0], "BTC")
                orphelines.setdefault(cle, (onglet, c))
        print(f"  filet de secours : {n} annotation(s) plus complètes reprises")

    # --- construire chaque onglet -----------------------------------------
    tables, reutil = {}, 0
    for nom, sym, tf in ONGLETS:
        f = sources.get((sym, tf))
        if not f:
            print(f"  « {nom} » : aucun export {sym} {tf} min — onglet ignoré")
            continue
        corps = []
        for t in lire_export(f):
            d, hh = t["dt"].strftime("%d/%m/%Y"), t["dt"].strftime("%H:%M")
            # fantôme : un trade que le testeur montre et dont aucune alerte
            # ne porte la trace, à la barre près.
            proches = alertes.get((sym, tf), set())
            if not proches or t["dt"] < min(proches) - dt.timedelta(minutes=int(tf)):
                fant = "—"               # aucune alerte ne couvrait cet instant
            else:
                vu = any(abs((a - t["dt"]).total_seconds()) <= int(tf) * 60
                         for a in proches)
                fant = "non" if vu else "OUI"
            manuel = anciennes.get((sym, d, hh))
            for autre in ALIAS.get(sym, ()):
                manuel = manuel or anciennes.get((autre, d, hh))
            if manuel:
                reutil += 1
            for k in [(sym, d, hh)] + [(a, d, hh) for a in ALIAS.get(sym, ())]:
                orphelines.pop(k, None)
            corps.append([sym, d, hh, t["sens"], t["label"], t["res"],
                          t["pnl"], fant] + (manuel or [None] * (len(COLS) - AUTO)))
        tables[nom] = [COLS] + corps
        g = sum(1 for r in corps if isinstance(r[6], (int, float)) and r[6] > 0)
        pnl = sum(r[6] for r in corps if isinstance(r[6], (int, float)))
        fant = sum(1 for r in corps if r[7] == "OUI")
        print(f"  « {nom:<16} » {len(corps):>3} trades   "
              f"{100*g/len(corps) if corps else 0:>5.1f} % réussite   "
              f"{pnl:>+9,.0f} $   {fant} fantôme(s)")

    print(f"\n  {reutil} ligne(s) d'annotations reprises sur {lignes_av}")

    # reverser les annotées orphelines dans leur onglet d'origine
    if orphelines:
        print(f"  {len(orphelines)} ligne(s) annotée(s) hors export, conservées :")
        for (sy, d, hh), (onglet, ligne) in sorted(
                orphelines.items(), key=lambda x: x[1][0]):
            if onglet not in tables:
                onglet = next(iter(tables))
            ligne = list(ligne)
            ligne[7] = "hors export"      # ni fantôme ni vu : plus dans la fenêtre
            tables[onglet].append(ligne)
            print(f"      {sy:<8} {d} {hh}  -> onglet « {onglet} »")
        for nom in tables:                # retrier par date
            corps = tables[nom][1:]
            corps.sort(key=lambda r: (str(r[1])[6:10], str(r[1])[3:5],
                                      str(r[1])[0:2], str(r[2])))
            tables[nom] = [tables[nom][0]] + corps

    # --- rotation des sauvegardes (2 au maximum) --------------------------
    if os.path.exists(CIBLE):
        hor = dt.datetime.now().strftime("%Y-%m-%d")
        dest = f"{CIBLE[:-8]}_backup_{hor}.numbers"
        if not os.path.exists(dest):      # la 1re passe du jour fait foi
            shutil.copy2(CIBLE, dest)
        vieux = sorted(glob.glob(f"{CIBLE[:-8]}_backup_*.numbers"))
        for v in vieux[:-BACKUPS_MAX]:
            os.remove(v)
            print(f"  sauvegarde supprimée : {os.path.basename(v)}")

    # --- écriture ----------------------------------------------------------
    doc = Document()
    for i, (nom, data) in enumerate(tables.items()):
        if i == 0:
            doc.sheets[0].name = nom
            t = doc.sheets[0].tables[0]
            t.name = "Trades"
        else:
            doc.add_sheet(nom, "Trades")
            t = doc.sheets[nom].tables[0]
        for ri, ligne in enumerate(data):
            for ci, val in enumerate(ligne):
                t.write(ri, ci, "" if val is None else val)
    doc.save(CIBLE)
    print(f"\n  écrit : {CIBLE}")


if __name__ == "__main__":
    main()
