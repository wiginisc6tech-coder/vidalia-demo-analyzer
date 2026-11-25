"""Calibracao: roda o Vidalia num conjunto de demos ROTULADAS e mede acertos e falsos alarmes.

Uso:
    python -m vidalia.calibrar PASTA [PASTA ...] [--rotulos rotulos.csv] [--cache PASTA] [--csv saida.csv]

Rotulos (CSV com cabecalho `arquivo,rotulo,funcoes`):
    rotulo  = cheat | limpa | parcial
    funcoes = lista separada por ';' (aim, silent, trigger, bhop, strafe, duck, speed, recoil,
              fakelag, knifebot, autofire, ...)
Sem arquivo de rotulos, o rotulo vem do nome da pasta (CheatDemos* = cheat, ClearDemos* e
FalsePositive = limpa, Partially* = parcial) e as funcoes vem de palavras do nome do arquivo.

Boa pratica: separe as demos em AJUSTE e TESTE. Ajuste limiares olhando so o conjunto de ajuste e
publique a precisao medida no conjunto de teste (use --teste para sortear 30% fixos para teste).
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

# palavra no nome do arquivo -> funcao esperada
KEYWORDS = [
    ("knifebot", "knifebot"), ("autopistol", "autofire"), ("autofire", "autofire"), ("autoattack", "autofire"),
    ("psilent", "silent"), ("silent", "silent"), ("norecoil", "recoil"), ("recoil", "recoil"),
    ("gstrafe", "duck"), ("groundstrafe", "duck"), ("ground", "duck"),
    ("strafe", "strafe"), ("bhop", "bhop"), ("jumpbug", "bhop"), ("kz", "bhop"),
    ("speed", "speed"), ("fastrun", "speed"), ("fake_latency", "fakelag"), ("desync", "fakelag"),
    ("trigger", "trigger"), ("aim", "aim"), ("rage", "aim"), ("oneshot", "aim"), ("one_shoot", "aim"),
]
# funcao -> detectores que deveriam acusa-la (prefixo do nome do detector)
FUNC_DETECTORS = {
    "aim": ("Aimbot", "Silent aim", "Triggerbot"),   # inclui "Aimbot de 1 frame" "silent": ("Silent aim",), "trigger": ("Triggerbot",),
    "recoil": ("No recoil",), "bhop": ("Bunny hop",), "strafe": ("Strafe automatico",),
    "duck": ("Script de agachamento",), "speed": ("Speedhack",), "fakelag": ("Fake lag",),
    "knifebot": ("Knifebot",), "autofire": ("Autofire",),
}


def label_from_path(path):
    folder = os.path.basename(os.path.dirname(path)).lower()
    name = os.path.basename(path).lower()
    if folder.startswith("cheat"):
        rot = "cheat"
    elif folder.startswith("partially"):
        rot = "parcial"
    elif folder.startswith("clear") or folder.startswith("clean") or folder.startswith("false"):
        rot = "limpa"
    else:
        rot = "?"
    funcs = []
    for kw, f in KEYWORDS:
        if kw in name and f not in funcs:
            funcs.append(f)
            if kw in ("gstrafe", "groundstrafe"):
                break   # "gstrafe" nao implica strafe automatico
    return rot, funcs


def _key(path):
    st = os.stat(path)
    return hashlib.sha1(("%s|%d|%d" % (os.path.abspath(path), st.st_size, int(st.st_mtime))).encode()).hexdigest()[:16]


def _analyze_one(args):
    path, cache, maps = args
    cp = os.path.join(cache, _key(path) + ".json") if cache else None
    if cp and os.path.exists(cp):
        with open(cp) as f:
            return json.load(f)
    from .report import analyze
    t = time.time()
    try:
        rep = analyze(path, maps)
        out = dict(arquivo=path, ok=True, veredito=rep["veredito"], pontuacao=rep.get("pontuacao"),
                   segundos=round(time.time() - t, 1), duracao=rep["demo"]["duracao"],
                   detectores={r["detector"]: dict(status=r["status"], metricas=r["metricas"], n_ev=len(r["evidencias"]))
                               for r in rep["detectores"]})
    except Exception as e:  # noqa: BLE001
        out = dict(arquivo=path, ok=False, erro=str(e)[:200])
    if cp:
        with open(cp, "w") as f:
            json.dump(out, f, default=str)
    return out


def run(paths, cache=None, maps=None, workers=None, progress=True):
    if cache:
        os.makedirs(cache, exist_ok=True)
    jobs = [(p, cache, maps) for p in paths]
    res = []
    with Pool(workers or max(1, (os.cpu_count() or 2))) as pool:
        for k, r in enumerate(pool.imap_unordered(_analyze_one, jobs), 1):
            res.append(r)
            if progress:
                print("\r[%d/%d] %s" % (k, len(jobs), os.path.basename(r["arquivo"])[:50].ljust(50)), end="", file=sys.stderr)
    if progress:
        print(file=sys.stderr)
    return res


def is_test(path, frac=0.3):
    """Sorteio deterministico (pelo nome) do conjunto de teste."""
    h = int(hashlib.md5(os.path.basename(path).lower().encode()).hexdigest(), 16)
    return (h % 1000) < frac * 1000


def summarize(results, labels, only=None):
    """Tabelas de desempenho por detector, por funcao e do veredito final."""
    rows = [r for r in results if r.get("ok") and (only is None or only(r["arquivo"]))]
    lines = []
    dets = sorted({d for r in rows for d in r["detectores"]})
    lines.append("%-36s %22s %22s" % ("Detector", "Cheat: Susp/Aten/n", "Limpa: Susp/Aten/n"))
    for d in dets:
        c = [r["detectores"].get(d, {}).get("status") for r in rows if labels[r["arquivo"]][0] == "cheat"]
        l = [r["detectores"].get(d, {}).get("status") for r in rows if labels[r["arquivo"]][0] == "limpa"]
        lines.append("%-36s %22s %22s" % (d[:36], "%d/%d/%d" % (c.count("Suspeito"), c.count("Atencao"), len(c)),
                                          "%d/%d/%d" % (l.count("Suspeito"), l.count("Atencao"), len(l))))
    lines.append("")
    lines.append("%-12s %8s %s" % ("Funcao", "acerto", "(demos com a funcao no nome em que algum detector esperado alertou)"))
    for f, ds in FUNC_DETECTORS.items():
        tot = hit = 0
        miss = []
        for r in rows:
            rot, funcs = labels[r["arquivo"]]
            if rot != "cheat" or f not in funcs:
                continue
            tot += 1
            st = [v["status"] for k, v in r["detectores"].items() if k.startswith(ds)]
            if any(s in ("Suspeito", "Atencao") for s in st):
                hit += 1
            else:
                miss.append(os.path.basename(r["arquivo"]))
        if tot:
            lines.append("%-12s %5d/%-3d %s" % (f, hit, tot, ("nao detectadas: " + ", ".join(miss[:6])) if miss else ""))
    lines.append("")
    for rot in ("cheat", "limpa", "parcial"):
        v = [r["veredito"] for r in rows if labels[r["arquivo"]][0] == rot]
        if v:
            lines.append("Veredito %-7s n=%-3d Suspeito %-3d Atencao %-3d Normal/Sem dados %d"
                         % (rot, len(v), v.count("Suspeito"), v.count("Atencao"), len(v) - v.count("Suspeito") - v.count("Atencao")))
    sc = [(r.get("pontuacao"), labels[r["arquivo"]][0]) for r in rows if r.get("pontuacao") is not None]
    if sc:
        for thr in (30, 50, 70):
            cs = [s for s, l in sc if l == "cheat"]
            ls = [s for s, l in sc if l == "limpa"]
            lines.append("Pontuacao >= %d: %d/%d demos com cheat, %d/%d limpas"
                         % (thr, sum(s >= thr for s in cs), len(cs), sum(s >= thr for s in ls), len(ls)))
    return "\n".join(lines)


def false_alarms(results, labels):
    out = []
    for r in results:
        if not r.get("ok") or labels[r["arquivo"]][0] != "limpa":
            continue
        for d, v in r["detectores"].items():
            if v["status"] in ("Suspeito", "Atencao"):
                out.append("%-40s %-34s %s" % (os.path.basename(r["arquivo"])[:40], d[:34], v["status"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vidalia.calibrar", description="Mede o Vidalia em demos rotuladas")
    ap.add_argument("pastas", nargs="+")
    ap.add_argument("--rotulos")
    ap.add_argument("--cache", default=None, help="pasta para guardar resultados (reprocessa so demos novas)")
    ap.add_argument("--mapas")
    ap.add_argument("--csv", help="exporta metricas de todos os detectores")
    ap.add_argument("--teste", action="store_true", help="mostra tambem o resultado so do conjunto de teste (30%%)")
    ap.add_argument("--workers", type=int)
    a = ap.parse_args(argv)
    paths = []
    for p in a.pastas:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                paths += [os.path.join(root, f) for f in files if f.lower().endswith(".dem")]
        elif p.lower().endswith(".dem"):
            paths.append(p)
    paths = sorted(p for p in paths if os.path.getsize(p) > 1024)
    labels = {p: label_from_path(p) for p in paths}
    if a.rotulos:
        with open(a.rotulos, newline="", encoding="utf-8") as f:
            given = {row["arquivo"].lower(): row for row in csv.DictReader(f)}
        for p in paths:
            row = given.get(os.path.basename(p).lower())
            if row:
                labels[p] = (row["rotulo"].strip(), [x for x in row.get("funcoes", "").split(";") if x])
    res = run(paths, a.cache, a.mapas, a.workers)
    errs = [r for r in res if not r.get("ok")]
    print("Demos: %d (%d com erro)\n" % (len(res), len(errs)))
    print(summarize(res, labels))
    if a.teste:
        print("\n--- Somente conjunto de TESTE ---")
        print(summarize(res, labels, only=is_test))
    fa = false_alarms(res, labels)
    if fa:
        print("\nAlertas em demos limpas:")
        print("\n".join(fa))
    for r in errs:
        print("ERRO %s: %s" % (r["arquivo"], r["erro"]))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["arquivo", "rotulo", "funcoes", "teste", "veredito", "pontuacao", "detector", "status", "metrica", "valor"])
            for r in res:
                if not r.get("ok"):
                    continue
                rot, funcs = labels[r["arquivo"]]
                for d, v in r["detectores"].items():
                    for mk, mv in (v["metricas"] or {"-": ""}).items():
                        w.writerow([os.path.basename(r["arquivo"]), rot, ";".join(funcs), int(is_test(r["arquivo"])),
                                    r["veredito"], r.get("pontuacao"), d, v["status"], mk, json.dumps(mv) if isinstance(mv, (dict, list)) else mv])
    return 0


if __name__ == "__main__":
    sys.exit(main())
