export const NOM = "i18n_cockpit";

const BALISES_MUETTES = new Set([ "SCRIPT", "STYLE", "NOSCRIPT", "TEXTAREA", "CODE", "PRE", "SVG", "CANVAS" ]);

const ATTRS = [ "title", "placeholder", "aria-label", "alt" ];

export function normaliser(texte) {
return String(texte === null || texte === undefined ? "" : texte).replace(/\s+/g, " ").trim();
}

export function traduire_par_regles(brut, regles) {
if (!Array.isArray(regles)) return null;
const s = String(brut === null || brut === undefined ? "" : brut);
const clef = normaliser(s);
if (!clef) return null;
for (const r of regles) {
if (!r || !(r.motif instanceof RegExp)) continue;
const m = clef.match(r.motif);
if (!m || m[0] !== clef) continue;
let sortie = String(r.en);
for (let i = 1; i < m.length; i += 1) {
sortie = sortie.split("$" + i).join(m[i] === undefined ? "" : m[i]);
}
const avant = s.match(/^\s*/)[0];
const apres = s.match(/\s*$/)[0];
return avant + sortie + apres;
}
return null;
}

export function traduire_texte(brut, dico) {
const s = String(brut === null || brut === undefined ? "" : brut);
const clef = normaliser(s);
if (!clef) return null;
if (!dico || !Object.prototype.hasOwnProperty.call(dico, clef)) return null;
const traduit = dico[clef];
if (typeof traduit !== "string" || !traduit) return null;
const avant = s.match(/^\s*/)[0];
const apres = s.match(/\s*$/)[0];
return avant + traduit + apres;
}

export function texte_traduisible(brut) {
const s = normaliser(brut);
if (!s) return false;
if (!/[A-Za-zÀ-ÿ]{2}/.test(s)) return false;
return true;
}

export function appliquer(racine, dico, document_) {
if (!racine || !dico) return 0;
const doc = document_ || (racine.ownerDocument || racine);
if (!doc || typeof doc.createTreeWalker !== "function") return 0;
let faits = 0;
const marcheur = doc.createTreeWalker(racine, 4, {
acceptNode(n) {
const parent = n.parentNode;
if (!parent || BALISES_MUETTES.has(parent.nodeName)) return 2;
if (parent.isContentEditable) return 2;
return texte_traduisible(n.nodeValue) ? 1 : 2;
}
});
const aTraiter = [];
let n = marcheur.nextNode();
while (n) {
aTraiter.push(n);
n = marcheur.nextNode();
}
const regles = dico && dico.__regles__ || null;
for (const noeud of aTraiter) {
let t = traduire_texte(noeud.nodeValue, dico);
if (t === null) t = traduire_par_regles(noeud.nodeValue, regles);
if (t !== null && t !== noeud.nodeValue) {
noeud.nodeValue = t;
faits += 1;
}
}
let elements;
try {
elements = racine.querySelectorAll("[title],[placeholder],[aria-label],[alt]");
} catch (e) {
elements = [];
}
for (const el of elements) {
for (const a of ATTRS) {
let v;
try {
v = el.getAttribute(a);
} catch (e) {
v = null;
}
if (v === null || v === undefined || !texte_traduisible(v)) continue;
let t = traduire_texte(v, dico);
if (t === null) t = traduire_par_regles(v, regles);
if (t !== null && t !== v) {
el.setAttribute(a, t);
faits += 1;
}
}
}
return faits;
}

export function surveiller(racine, dico, fenetre) {
const f = fenetre || (typeof globalThis !== "undefined" ? globalThis : null);
if (!f || typeof f.MutationObserver !== "function") return function() {};
let enAttente = false;
const obs = new f.MutationObserver(function() {
if (enAttente) return;
enAttente = true;
const plusTard = typeof f.requestAnimationFrame === "function" ? f.requestAnimationFrame : function(fn) {
return f.setTimeout(fn, 0);
};
plusTard(function() {
enAttente = false;
try {
appliquer(racine, dico);
} catch (e) {}
});
});
obs.observe(racine, {
childList: true,
subtree: true,
characterData: true,
attributes: true,
attributeFilter: ATTRS.slice()
});
return function() {
try {
obs.disconnect();
} catch (e) {}
};
}
