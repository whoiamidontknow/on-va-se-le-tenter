#!/usr/bin/env python3
"""genere_testfirewall.py — fabrique TESTFIREWALL.pine à partir de Strat5669.pine.

Pourquoi : Jeremy publie sa stratégie en invite-only pour un bêta-testeur. L'invite-only ne
cache que le code source ; le panneau de réglages, le texte des alertes, les commentaires
d'ordre (liste des trades) et les noms des tracés restent lisibles. Ce script en fait une
version qui donne les mêmes trades sans rien laisser lire de la méthode :

  1. chaque input.*() est remplacé par sa valeur, contrôlée contre la feuille « Propriétés »
     des exports réels de Jeremy (les valeurs qu'il utilise, pas seulement les défauts) ;
  2. le préréglage est figé (une seule ligne de clés, nom neutre) ;
  3. tous les commentaires du code disparaissent ;
  4. alertes, commentaires d'ordre, tracés, tableau : renommés ou retirés ;
  5. les mots qui trahissent la méthode sont effacés de toutes les chaînes restantes.

Strat5669.pine n'est jamais modifié : on régénère TESTFIREWALL.pine quand il change.

    uv run -q --with pandas --with openpyxl python KAIROS/firewall/genere_testfirewall.py \\
        Strat5669.pine ~/ERGON/KAIROS-data/Backtest/07nov TESTFIREWALL.pine
"""
import glob
import os
import re
import sys

import pandas as pd

SRC, EXPORTS, DST = sys.argv[1], os.path.expanduser(sys.argv[2]), sys.argv[3]
TITRE = "Firewall Test"
NOM_A, NOM_B = "GODLIKE", "56 seul"        # étiquettes gardées à la demande de Jeremy (09/11), sans leur explication
# posées APRÈS le nettoyage des chaînes (qui les effacerait), via ces marques provisoires
MARQUE_A, MARQUE_B = "\u00a7A\u00a7", "\u00a7B\u00a7"
PRESET_SOURCE = "56 · 48 avec sortie après 16 bougies (4 h)"

src = open(SRC, encoding="utf-8").read()


# --- outils : chaînes et parenthèses, en respectant les littéraux Pine ------------------------
def fin_chaine(t, i):
    """t[i] est un guillemet : indice juste après la chaîne fermante."""
    q, j = t[i], i + 1
    while j < len(t) and t[j] != q:
        j += 2 if t[j] == "\\" else 1
    return j + 1


def fin_appel(t, i):
    """t[i] == '(' : indice juste après la parenthèse fermante correspondante."""
    n, j = 0, i
    while j < len(t):
        c = t[j]
        if c in "\"'":
            j = fin_chaine(t, j)
            continue
        if c in "([":
            n += 1
        elif c in ")]":
            n -= 1
            if n == 0:
                return j + 1
        j += 1
    raise ValueError("parenthèse non fermée")


def args_haut_niveau(corps):
    """Arguments d'un appel, découpés aux virgules de premier niveau."""
    out, n, j, deb = [], 0, 0, 0
    while j < len(corps):
        c = corps[j]
        if c in "\"'":
            j = fin_chaine(corps, j)
            continue
        if c in "([":
            n += 1
        elif c in ")]":
            n -= 1
        elif c == "," and n == 0:
            out.append(corps[deb:j].strip())
            deb = j + 1
        j += 1
    out.append(corps[deb:].strip())
    return out


def sans_commentaires(t):
    lignes = []
    for ligne in t.split("\n"):
        if ligne.startswith("//@version"):
            lignes.append(ligne)
            continue
        j, coupe = 0, None
        while j < len(ligne):
            c = ligne[j]
            if c in "\"'":
                j = fin_chaine(ligne, j)
                continue
            if ligne.startswith("//", j):
                coupe = j
                break
            j += 1
        ligne = (ligne if coupe is None else ligne[:coupe]).rstrip()
        if ligne.strip() or (lignes and lignes[-1].strip()):
            lignes.append(ligne)
    return "\n".join(lignes)


def remplace_exact(t, ancien, nouveau, n=1):
    assert t.count(ancien) == n, f"{t.count(ancien)} occurrence(s) au lieu de {n} : {ancien[:80]!r}"
    return t.replace(ancien, nouveau)


# --- 1. valeurs réelles de Jeremy (Propriétés des exports) ------------------------------------
props = {}
for f in sorted(glob.glob(os.path.join(EXPORTS, "*.xlsx"))):
    p = pd.read_excel(f, "Propriétés", header=None)
    for k, v in zip(p[0], p[1]):
        props.setdefault(str(k).strip().lower(), set()).add(str(v).strip())


def norme(v):
    v = str(v).strip().strip('"').strip("'")
    v = {"true": "on", "false": "off"}.get(v, v.lower())
    v = re.sub(r"^(\d{2})(\d{2})-(\d{2})(\d{2})$", r"\1:\2 — \3:\4", v)   # session
    try:
        return str(float(v.replace(",", ".")))
    except ValueError:
        return v


# --- 2. préréglage figé -------------------------------------------------------------------------
m = re.search(r'nom == "' + re.escape(PRESET_SOURCE) + r'" \? ("[^"]*")', src)
cles = m.group(1)
deb = src.index("f_pr_def(string nom) =>")
fin = src.index('\n     ""', deb) + len('\n     ""')
src = src[:deb] + "f_pr_def(string nom) =>\n     " + cles + src[fin:]
src = remplace_exact(src, f'preset    = "{PRESET_SOURCE}"', 'preset    = "A"')

# --- 3. commentaires ----------------------------------------------------------------------------
src = sans_commentaires(src)

# --- 4. inputs → valeurs ------------------------------------------------------------------------
GARDES = {"al_on"}          # réécrits à la main plus bas (réglages cosmétiques)
ecarts, n_inputs, sans_titre = [], 0, 0
motif = re.compile(r"\binput\.(bool|int|float|string|session|timeframe|source|color|symbol|price|time|text_area)\(")
morceaux, pos = [], 0
for mm in motif.finditer(src):
    if mm.start() < pos:
        continue
    ouv = mm.end() - 1
    fermeture = fin_appel(src, ouv)
    args = args_haut_niveau(src[ouv + 1:fermeture - 1])
    defaut = args[0]
    titre = args[1] if len(args) > 1 and args[1][:1] in "\"'" else '""'
    titre = titre.strip("\"'")
    n_inputs += 1
    if titre:
        reel = props.get(titre.lower())
        if reel is None:
            ecarts.append(f"absent des Propriétés : {titre!r} (défaut {defaut})")
        elif norme(defaut) not in {norme(x) for x in reel}:
            ecarts.append(f"ÉCART : {titre!r} défaut {defaut} ≠ Jeremy {sorted(reel)}")
    else:
        sans_titre += 1
    morceaux.append(src[pos:mm.start()])
    morceaux.append(defaut)
    pos = fermeture
morceaux.append(src[pos:])
src = "".join(morceaux)

# --- 5. ce que le bêta-testeur voit -------------------------------------------------------------
src = remplace_exact(src, 'strategy("Strat5669 (alertes)", overlay=true,',
                     f'strategy("{TITRE}", shorttitle="{TITRE}", overlay=true,')
# capital des exports de Jeremy (Propriétés : « Capital initial 50000 »), pour que le testeur montre ses chiffres
src = remplace_exact(src, "initial_capital=25000,", "initial_capital=50000,")
# deux réglages cosmétiques, rien d'autre
src = re.sub(r"^al_on\s*=\s*true$",
             'al_on     = input.bool(true, "Alertes")\naff_fl    = input.bool(true, "Flèches")',
             src, count=1, flags=re.M)
assert "aff_fl" in src

# étiquette des trades
src = remplace_exact(src, '(d > 0 ? gd_L : gd_S) ? " · GODLIKE" : " · 56 seul"',
                     f'(d > 0 ? gd_L : gd_S) ? " · {MARQUE_A}" : " · {MARQUE_B}"')
src = remplace_exact(src, 'comment=(jr_on ? f_jr(1, dist) : "L " + str.tostring(q)) + f_gdTag(1) + ws_tag',
                     'comment="entrée" + f_gdTag(1)')
src = remplace_exact(src, 'comment=(jr_on ? f_jr(-1, dist) : "S " + str.tostring(q)) + f_gdTag(-1) + ws_tag',
                     'comment="entrée" + f_gdTag(-1)')

# alerte d'entrée : une ligne, sans diagnostic
deb = src.index('alert(syminfo.ticker + " · " + (d > 0 ? "ACHAT (long)" : "VENTE (short)")')
fin = src.index("alert.freq_once_per_bar_close)", deb) + len("alert.freq_once_per_bar_close)")
src = src[:deb] + (
    'alert(syminfo.ticker + " · " + (d > 0 ? "ACHAT (long)" : "VENTE (short)") + " · " + '
    f'((d > 0 ? gd_L : gd_S) ? "{MARQUE_A}" : "{MARQUE_B}") + '
    '" · Entrée ≈ " + f_px(e0) + '
    '" · Stop " + f_px(s0) + " (" + str.tostring(dist, "0.00") + " pts)" + '
    '" · Objectif " + (na(tp0) ? "aucun" : f_px(tp0) + " (" + str.tostring(math.abs(tp0 - e0), "0.00") + " pts)") + '
    '" · Sortie au plus tard " + str.format_time(tSort, "HH:mm", "Europe/Paris") + " (Paris)", '
    "alert.freq_once_per_bar_close)") + src[fin:]

# commentaires de sortie (liste des trades) et les tests qui les relisent
src = remplace_exact(src, 'comment="Stop dépassé"', 'comment="stop"')
src = remplace_exact(src, 'comment="Fin de séance"', 'comment="fin"')
src = remplace_exact(src, 'comment="Signal opposé"', 'comment="fin"', n=2)
src = remplace_exact(src, 'comment="Temps (" + str.tostring(x_tBar) + " bougies)"', 'comment="fin"')
src = remplace_exact(src, 'cl = lg ? "Stop L" : "Stop S"', 'cl = "stop"')
src = remplace_exact(src, 'cp = lg ? "Obj L" : "Obj S"', 'cp = "objectif"')
src = remplace_exact(src, 'str.startswith(strategy.closedtrades.exit_comment(kw), "Stop")',
                     'str.startswith(strategy.closedtrades.exit_comment(kw), "stop")')
src = remplace_exact(src, 'if str.startswith(cx, "Obj") or str.startswith(cx, "Stop")',
                     'if str.startswith(cx, "objectif") or str.startswith(cx, "stop")')
src = remplace_exact(src, '(str.startswith(cx, "Obj") ? "OBJECTIF touché" : "STOP touché")',
                     '(str.startswith(cx, "objectif") ? "OBJECTIF touché" : "STOP touché")')
src = remplace_exact(src, '" bougies écoulées (ni stop ni objectif)"', '" · heure limite atteinte"')
src = src.replace('syminfo.ticker + " · FERMER la position maintenant : " + str.tostring(x_tBar) + " · heure limite atteinte"',
                  'syminfo.ticker + " · FERMER la position maintenant : heure limite atteinte"')

# tracés : couleur des bougies, moyennes, diagnostics → retirés ; le reste → p1, p2…
src = re.sub(r"^barcolor\(.*\n", "", src, flags=re.M)
src = re.sub(r'^plot\(ema_m[12], .*\n', "", src, flags=re.M)
src = re.sub(r'^plot\([^\n]*"DIAG [^\n]*\n', "", src, flags=re.M)
src = re.sub(r'^plotshape\(a_sig and [^\n]*\n', "", src, flags=re.M)
src = remplace_exact(src, 'plotshape(entree_L, "Entrée long (signal)",', 'plotshape(aff_fl and entree_L, "p1",')
src = remplace_exact(src, 'plotshape(entree_S, "Entrée short (signal)",', 'plotshape(aff_fl and entree_S, "p2",')
src = remplace_exact(src, 'plotshape(sortie_marq, "Sortie sur signal",', 'plotshape(aff_fl and sortie_marq, "p3",')
for i, nom in enumerate(['"Entrée", ', '"SL",     ', '"TP",     ', '"TP 2",   '], 4):
    src = remplace_exact(src, nom, f'"p{i}", ')

# avertissement Heikin Ashi : nécessaire (les signaux en dépendent), sans explication
src = remplace_exact(src, '"⚠ Passe le graphique en Heiken Ashi\\n(tous les signaux sont calibrés dessus)"',
                     '"⚠ Utiliser des bougies Heikin Ashi"')

# tableau : résultats et position seulement
src = remplace_exact(src, "table.new(f_tb_pos(a_pos), 2, 12,", "table.new(f_tb_pos(a_pos), 2, 8,")
src = remplace_exact(src, 'enPos ? f_px(tr_stop) + (tr_stop != tr_stop0 ? " (déplacé)" : " · " + tr_slNom) : "—"',
                     'enPos ? f_px(tr_stop) : "—"')
src = remplace_exact(src, 'enPos and not na(tr_tp) ? f_px(tr_tp) + " · " + tr_tpNom : "—"',
                     'enPos and not na(tr_tp) ? f_px(tr_tp) : "—"')
src = re.sub(r"^    f_tb\((8|9|10|11), .*\n", "", src, flags=re.M)

# --- 6. mots qui trahissent la méthode, dans toutes les chaînes restantes (code mort compris) ---
# Remplacement uniforme : deux chaînes égales le restent, les comparaisons ne changent pas.
EFFACE = [("GODLIKE", "A"), ("Godlike", "A"), ("Dashator", "D"), ("Blackout", "F"), ("blackout", "f"), ("BLACKOUT", "F"), ("DASHATOR", "D"),
          ("Break-even", "BE"), ("break-even", "be"), ("ATR", "V"), ("Heishinator", "H"), ("Signator", "S"),
          ("Breakator", "K"), ("Moyenator", "M"), ("Rondator", "R"), ("Detector", "Z"), ("Climax", "X"),
          ("climax", "x"), ("Strat5669", "FT"), ("règle du 69", ""), ("56 seul", "B")]


def nettoie_chaine(s):
    for a, b in EFFACE:
        s = s.replace(a, b)   # sensible à la casse : x_prio est passé en minuscules puis comparé
    return re.sub(r"(?<!\d)(56|69)(?!\d)", "", s)


morceaux, j, deb = [], 0, 0
while j < len(src):
    if src[j] in "\"'":
        k = fin_chaine(src, j)
        morceaux.append(src[deb:j] + nettoie_chaine(src[j:k]))
        deb = j = k
        continue
    j += 1
morceaux.append(src[deb:])
src = "".join(morceaux)

src = src.replace(MARQUE_A, NOM_A).replace(MARQUE_B, NOM_B)

# hors chaînes, 56 ne survit que dans une couleur du tableau : 57, l'œil ne voit pas la différence
src = src.replace("color.rgb(56, 149, 255)", "color.rgb(57, 149, 255)")

open(DST, "w", encoding="utf-8").write(src.rstrip() + "\n")

print(f"{n_inputs} inputs remplacés par leur valeur ({sans_titre} sans titre, défaut gardé)")
print(f"{len(ecarts)} écart(s) avec les Propriétés de Jeremy")
for e in ecarts:
    print("  ", e)
controle = src.replace(f'"{NOM_A}"', "").replace(f'" · {NOM_A}"', "").replace(f'"{NOM_B}"', "").replace(f'" · {NOM_B}"', "")
restes = [w for w in ("GODLIKE", "Dashator", "Blackout", "break-even", "Break-even", "règle du 69")
          if w.lower() in controle.lower()]
nombres = sorted(set(re.findall(r"(?<![\d.])(?:56|69)(?![\d])", controle)))
print(f"étiquettes {NOM_A!r} / {NOM_B!r} : {src.count(NOM_A)} / {src.count(NOM_B)} occurrence(s)")
print("mots interdits restants :", restes or "aucun", "· nombres 56/69 restants :", nombres or "aucun")
print("input.* restants :", re.findall(r"input\.\w+\([^\n]*", src))
print(f"écrit : {DST} ({src.count(chr(10))} lignes)")
