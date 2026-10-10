#!/usr/bin/env python3
"""Verifie la syntaxe d'un fichier Pine via l'API officielle de TradingView.

Appelle l'outil check_syntax du serveur MCP `pinescript-syntax-checker` en
direct (JSON-RPC sur stdio), sans passer par le chargement MCP de la session.
Renvoie du JSON : success, errors[] et warnings[] avec code, ligne et colonne.

Pourquoi ce script existe : le serveur MCP est enregistre (claude mcp list le
montre Connected) mais un serveur ajoute APRES le demarrage d'une session n'y
est pas charge. Ce script contourne ca et marche depuis n'importe ou.

Prerequis : uv installe dans ~/.local/bin. L'epinglage `--with mcp<2` est
OBLIGATOIRE : le paquet est ecrit pour mcp 1.x et uv resout mcp 2.x, ou
FastMCP a ete renomme MCPServer.

Usage : python3 tools/pinecheck.py <fichier.pine>
"""
import json, subprocess, sys, threading, queue
def check(code, timeout=240):
    p = subprocess.Popen(["/Users/jeremk/.local/bin/uvx","--with","mcp<2","pinescript-syntax-checker"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, bufsize=1)
    q = queue.Queue()
    def rd():
        for line in p.stdout:
            q.put(line)
    threading.Thread(target=rd, daemon=True).start()
    def send(m): p.stdin.write(json.dumps(m)+"\n"); p.stdin.flush()
    send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"c","version":"1"}}})
    send({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
    send({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{
        "name":"check_syntax","arguments":{"pine_code":code}}})
    out=None
    try:
        import time; t0=time.time()
        while time.time()-t0 < timeout:
            try: line=q.get(timeout=5)
            except queue.Empty: continue
            try: m=json.loads(line)
            except Exception: continue
            if m.get("id")==2: out=m; break
    finally:
        try: p.kill()
        except Exception: pass
    return out
if __name__=="__main__":
    code=open(sys.argv[1]).read()
    r=check(code)
    if r is None: print("TIMEOUT / pas de reponse"); sys.exit(2)
    c=r.get("result",{}).get("content",[])
    txt="\n".join(x.get("text","") for x in c) if c else json.dumps(r,ensure_ascii=False)
    print(txt)
