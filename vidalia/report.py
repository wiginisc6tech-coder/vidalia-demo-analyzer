"""Orquestracao da analise e geracao de relatorios (JSON, CSV e HTML)."""
import csv
import datetime
import html
import json
import os

from . import __version__
from .bsp import BSP, default_map_folders, find_bsp
from .detectors import LEVEL, SEM_DADOS, OK, ATENCAO, SUSPEITO, fmt_time, run_all
from .engine import LOAD_SHARE, load, player_name, weapon_name


# Confiabilidade de cada detector (quanto foi validado com demos reais) -> peso de Suspeito / Atencao.
# A pontuacao combina os alertas como probabilidades independentes: 100 * (1 - prod(1 - p)).
SCORE_WEIGHTS = {
    "alta": (0.70, 0.30),    # calibrado com demos publicas, separacao clara entre limpas e cheats
    "media": (0.50, 0.20),   # calibrado, mas com sobreposicao ou poucas amostras
    "baixa": (0.35, 0.12),   # experimental
}
DETECTOR_TIER = {
    "Speedhack": "alta", "Bunny hop script": "alta", "Triggerbot": "alta", "Silent aim": "alta",
    "Strafe automatico": "alta", "Script de agachamento": "alta", "Assinaturas de cheat": "alta",
    "Aimbot de 1 frame": "media", "Aimbot": "media", "Autofire": "media", "Anti-aim": "media",
}


# palavras que costumam aparecer quando alguem acusa/denuncia cheat ou um admin age (pt, en, es, ru)
CHAT_FLAGS = ("wh", "wall", "aim", "cheat", "hack", "xit", "xiter", "speed", "bhop", "trigger", "ban", "kick",
              "demo", "record", "gravar", "grava", "denunc", "report", "admin", "\u0447\u0438\u0442", "\u0432\u0445",
              "\u0430\u0438\u043c", "\u0431\u0430\u043d", "\u0434\u0435\u043c\u043e", "\u043a\u0438\u043a")
CHAT_LABELS = {"todos": "Todos", "time": "Time", "morto": "Morto", "espectador": "Espectador", "radio": "Radio",
               "nome": "Troca de nome", "servidor": "Servidor/Admin", "jogo": "Jogo"}


def _flag(text):
    import re
    low = text.lower()
    return any(re.search(r"(?<![a-z\u0430-\u044f])" + re.escape(w), low) for w in CHAT_FLAGS)


def build_chat(dd, t0):
    """Lista do chat da demo: jogadores, radio, mensagens do servidor/admin e trocas de nome."""
    out = []
    for e in dd.events:
        if e["tipo"] != "chat" or not e.get("texto"):
            continue
        p = dd.players.get(e.get("remetente")) or {}
        out.append(dict(tempo=fmt_time(e["tempo"], t0), tempo_s=round(e["tempo"] - t0, 3), categoria=e["categoria"],
                        tipo=CHAT_LABELS.get(e["categoria"], e["categoria"]), jogador=e.get("nome", ""),
                        steamid=p.get("steamid", "") if e.get("remetente") else "", texto=e["texto"],
                        destaque=_flag(e["texto"]) and e["categoria"] not in ("servidor", "jogo")))
    return out


def save_chat_txt(report, path):
    """Chat em texto simples, uma linha por mensagem."""
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("Chat da demo %s (Vidalia %s)\n\n" % (report["arquivo"], report["versao"]))
        for c in report.get("chat", []):
            who = ("%s: " % c["jogador"]) if c["jogador"] else ""
            f.write("[%s] (%s) %s%s\n" % (c["tempo"], c["tipo"], who, c["texto"]))


def score(results):
    """Pontuacao 0-100 combinando os detectores, com o detalhamento de cada contribuicao."""
    keep = 1.0
    parts = []
    for r in results:
        if r["status"] not in (SUSPEITO, ATENCAO):
            continue
        tier = next((t for k, t in DETECTOR_TIER.items() if r["detector"].startswith(k)), "baixa")
        p = SCORE_WEIGHTS[tier][0 if r["status"] == SUSPEITO else 1]
        keep *= 1.0 - p
        parts.append(dict(detector=r["detector"], status=r["status"], confiabilidade=tier, peso=round(p * 100)))
    return round(100 * (1.0 - keep)), parts


def score_label(sc):
    if sc >= 70:
        return "alta prioridade de revisao"
    if sc >= 40:
        return "vale revisar"
    if sc > 0:
        return "indicios fracos"
    return "sem indicios"


def analyze(path, maps_folder=None, cfg=None, progress=None):
    dd = load(path, progress)
    bsp = None
    bsp_note = ""
    map_name = os.path.splitext(os.path.basename(dd.header.map_name))[0]
    auto = not maps_folder
    folders = [maps_folder] if maps_folder else default_map_folders(path)
    if folders:
        bp = find_bsp(map_name, folders)
        if bp:
            try:
                bsp = BSP(bp)
                bsp_note = "Mapa carregado: %s" % bp
            except Exception as e:  # noqa: BLE001
                bsp_note = "Falha ao ler %s: %s" % (bp, e)
        elif not auto:
            bsp_note = "%s.bsp nao encontrado em %s" % (map_name, maps_folder)
        else:
            bsp_note = "%s.bsp nao encontrado automaticamente; informe a pasta cstrike/maps" % map_name
    results, speeds = run_all(dd, cfg, bsp, progress=progress, span=(LOAD_SHARE, 0.95))
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    worst = max((LEVEL[r["status"]] for r in results), default=-1)
    veredito = {2: SUSPEITO, 1: ATENCAO, 0: OK}.get(worst, SEM_DADOS)
    pontuacao, pontuacao_det = score(results)
    kills = [e for e in dd.events if e["tipo"] == "morte"]
    me = dd.local
    report = dict(
        software="Vidalia Demo Analyzer",
        versao=__version__,
        gerado_em=datetime.datetime.now().isoformat(timespec="seconds"),
        arquivo=os.path.basename(path),
        aviso="Resultado de triagem automatizada. Nao comprova uso de trapaca; toda evidencia exige revisao humana da demo.",
        demo=dict(
            protocolo_demo=dd.header.demo_protocol, protocolo_rede=dd.header.net_protocol,
            mapa=map_name, jogo=dd.header.game_dir, bytes=dd.header.file_size,
            duracao=fmt_time(tl.t[-1], t0) if tl.t else "00:00.000",
            frames_de_jogo=len(tl), servidor=dd.decoder.st.server.get("servidor", ""),
        ),
        gravador=dict(indice=me, nome=player_name(dd, me),
                      steamid=(dd.players.get(me) or {}).get("steamid", ""),
                      time=(dd.players.get(me) or {}).get("time", ""),
                      kills=sum(1 for k in kills if k["matador"] == me and k["vitima"] != me),
                      mortes=sum(1 for k in kills if k["vitima"] == me),
                      headshots=sum(1 for k in kills if k["matador"] == me and k.get("headshot")),
                      disparos=len(dd.shots)),
        veredito=veredito,
        pontuacao=pontuacao,
        pontuacao_detalhe=pontuacao_det,
        detectores=results,
        jogadores=[dict(indice=k, nome=v.get("nome", ""), steamid=v.get("steamid", ""), time=v.get("time", ""),
                        frags=v.get("frags"), mortes=v.get("mortes"))
                   for k, v in sorted(dd.players.items()) if v.get("nome")],
        mortes=[dict(tempo=fmt_time(k["tempo"], t0), matador=player_name(dd, k["matador"]) if k["matador"] else "mundo",
                     vitima=player_name(dd, k["vitima"]), arma=k.get("arma", ""), headshot=k.get("headshot", False))
                for k in kills],
        decodificacao=dd.stats,
        mapa_bsp=bsp_note,
        chat=build_chat(dd, t0),
        avisos=dd.warnings[:50],
    )
    report["_series"] = _series(dd, speeds)
    if progress:
        progress(1.0)
    return report


def _series(dd, speeds, max_points=1500):
    tl = dd.timeline
    n = len(tl)
    if not n:
        return dict(t=[], v=[], shots=[], kills=[])
    step = max(1, n // max_points)
    ts, vs = [], []
    for i in range(0, n, step):
        ts.append(round(tl.t[i] - tl.t[0], 3))
        vs.append(round(max(speeds[i:i + step]), 1))
    kills = [round(e["tempo"] - tl.t[0], 3) for e in dd.events if e["tipo"] == "morte" and e["matador"] == dd.local]
    return dict(t=ts, v=vs, kills=kills)


def save_json(report, path):
    data = {k: v for k, v in report.items() if not k.startswith("_")}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(report, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["detector", "gravidade", "tempo", "tempo_s", "frame", "descricao"])
        for r in report["detectores"]:
            for e in r["evidencias"]:
                w.writerow([r["detector"], e.get("gravidade", ""), e.get("tempo", ""), e.get("tempo_s", ""),
                            e.get("frame", ""), e.get("descricao", "")])


COLORS = {SUSPEITO: "#dc2626", ATENCAO: "#d97706", OK: "#16a34a", SEM_DADOS: "#6b7280"}
LABELS = {SUSPEITO: "Suspeito", ATENCAO: "Atencao", OK: "Normal", SEM_DADOS: "Sem dados"}


def _chart(series):
    t, v = series["t"], series["v"]
    if not t:
        return "<p>Sem dados.</p>"
    W, H = 1000, 220
    tmax = max(t[-1], 1e-6)
    vmax = max(2000.0, min(max(v), 6000.0))
    pts = " ".join("%.1f,%.1f" % (x / tmax * W, H - min(y, vmax) / vmax * (H - 10)) for x, y in zip(t, v))
    lines = "".join('<line x1="%.1f" x2="%.1f" y1="0" y2="%d" class="kill"/>' % (k / tmax * W, k / tmax * W, H)
                    for k in series.get("kills", []) if 0 <= k <= tmax)
    th = H - 1500 / vmax * (H - 10)
    return ('<svg viewBox="0 0 %d %d" preserveAspectRatio="none" class="chart" role="img" aria-label="Velocidade angular ao longo da demo">'
            '%s<line x1="0" x2="%d" y1="%.1f" y2="%.1f" class="thr"/><polyline points="%s" class="line"/></svg>'
            % (W, H, lines, W, th, th, pts))


def save_html(report, path):
    e = html.escape
    det = []
    for r in report["detectores"]:
        ev = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(str(x.get("tempo", ""))), e(str(x.get("frame", ""))), e(x.get("descricao", "")))
                     for x in r["evidencias"][:40])
        more = len(r["evidencias"]) - 40
        met = " · ".join("%s: <b>%s</b>" % (e(k.replace("_", " ")), e(str(v))) for k, v in r["metricas"].items())
        det.append(
            '<details class="det"%s><summary><span class="pill" style="background:%s">%s</span> <b>%s</b>'
            '<span class="sum">%s</span></summary><div class="body"><p class="met">%s</p>%s%s%s</div></details>'
            % (" open" if r["status"] in (SUSPEITO, ATENCAO) else "", COLORS[r["status"]], LABELS[r["status"]],
               e(r["detector"]), e(r["resumo"]), met,
               "<table><tr><th>Tempo</th><th>Frame</th><th>Evidencia</th></tr>%s</table>" % ev if ev else "",
               "<p class=note>+%d evidencias no CSV.</p>" % more if more > 0 else "",
               "<p class=note>%s</p>" % e(r["nota"]) if r["nota"] else ""))
    g = report["gravador"]
    d = report["demo"]
    kills = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        e(k["tempo"]), e(k["matador"]), e(k["vitima"]), e(k["arma"]), "HS" if k["headshot"] else "")
        for k in report["mortes"][:300])
    players = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
        e(str(p["indice"])), e(p["nome"]), e(p["steamid"]), e(p["time"] or "")) for p in report["jogadores"])
    st = report["decodificacao"]
    page = TEMPLATE.format(
        arquivo=e(report["arquivo"]), versao=e(report["versao"]), gerado=e(report["gerado_em"]),
        vcolor=COLORS[report["veredito"]], veredito=LABELS[report["veredito"]], aviso=e(report["aviso"]),
        pontuacao=report.get("pontuacao", 0), pontuacao_txt=e(score_label(report.get("pontuacao", 0))),
        pontuacao_det=e("Pontuacao = " + (" + ".join("%s (%s, confiabilidade %s)" % (p["detector"].split(" (")[0], p["status"], p["confiabilidade"])
                                                    for p in report.get("pontuacao_detalhe", [])) or "nenhum alerta")),
        mapa=e(d["mapa"]), duracao=e(d["duracao"]), servidor=e(d["servidor"]), frames=d["frames_de_jogo"],
        nome=e(g["nome"]), steamid=e(g["steamid"] or "-"), time=e(g["time"] or "-"), kills=g["kills"],
        mortes=g["mortes"], hs=g["headshots"], disparos=g["disparos"], cobertura=st.get("cobertura_rede", 0),
        detectores="".join(det), chart=_chart(report["_series"]), killrows=kills or "<tr><td colspan=5>Nenhuma morte decodificada.</td></tr>",
        players=players or "<tr><td colspan=4>Nenhum jogador decodificado.</td></tr>",
        nchat=len(report.get("chat", [])),
        chatrows="".join('<tr%s><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            ' style="background:#3b2a08"' if c["destaque"] else "", e(c["tempo"]), e(c["tipo"]), e(c["jogador"]), e(c["texto"]))
            for c in report.get("chat", [])[:5000]) or "<tr><td colspan=4>Nenhuma mensagem de chat na demo.</td></tr>",
        bsp=e(report.get("mapa_bsp") or "Nao fornecido"),
        avisos="".join("<li>%s</li>" % e(a) for a in report["avisos"]) or "<li>Nenhum</li>",
        erros="".join("<li>%s (%s)</li>" % (e(k), v) for k, v in st.get("erros", {}).items()) or "<li>Nenhum</li>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


TEMPLATE = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatorio Vidalia - {arquivo}</title><style>
:root{{--bg:#0f172a;--card:#111c33;--fg:#e2e8f0;--mut:#94a3b8;--line:#1e293b;--acc:#60a5fa}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 "Segoe UI",system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px}}h1{{margin:0;font-size:26px;letter-spacing:.5px}}h2{{font-size:18px;margin:28px 0 10px}}
.sub{{color:var(--acc);font-size:13px;letter-spacing:2px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}.k{{color:var(--mut);font-size:12px}}.v{{font-size:20px;font-weight:600}}
.verdict{{display:flex;gap:16px;align-items:center;flex-wrap:wrap}}.big{{font-size:22px;font-weight:700;padding:6px 14px;border-radius:8px;color:#fff}}
.warn{{color:var(--mut);font-size:13px}}.score{{display:flex;align-items:baseline;gap:6px}}.sv{{font-size:30px;font-weight:700}}.pill{{display:inline-block;min-width:84px;text-align:center;color:#fff;border-radius:999px;padding:1px 10px;font-size:12px}}
.det{{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:8px 0}}.det summary{{cursor:pointer;padding:12px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.sum{{color:var(--mut);font-size:13px;flex-basis:100%}}.body{{padding:0 14px 14px}}.met{{font-size:13px;color:var(--mut)}}.note{{font-size:12px;color:var(--mut);font-style:italic}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}}th{{color:var(--mut);font-weight:500}}
.tw{{overflow-x:auto}}.chart{{width:100%;height:220px;background:#0b1325;border-radius:8px}}.line{{fill:none;stroke:var(--acc);stroke-width:1}}.thr{{stroke:#d97706;stroke-dasharray:4 4}}.kill{{stroke:#dc2626;stroke-opacity:.45}}
footer{{color:var(--mut);font-size:12px;margin-top:30px}}
</style></head><body><main>
<h1>VIDALIA</h1><div class="sub">DEMO ANALYZER · {versao}</div>
<h2>Resultado da triagem</h2><div class="card verdict"><span class="big" style="background:{vcolor}">{veredito}</span><div class="score"><span class="sv">{pontuacao}</span><span class="k">/100 · {pontuacao_txt}</span></div><div><b>{arquivo}</b><div class="warn">{aviso}</div><div class="warn">{pontuacao_det}</div></div></div>
<h2>Demo e jogador gravador</h2><div class="grid">
<div class="card"><div class="k">Mapa</div><div class="v">{mapa}</div></div><div class="card"><div class="k">Duracao</div><div class="v">{duracao}</div></div>
<div class="card"><div class="k">Jogador</div><div class="v">{nome}</div><div class="k">{steamid} · {time}</div></div>
<div class="card"><div class="k">Kills / Mortes / HS</div><div class="v">{kills} / {mortes} / {hs}</div></div>
<div class="card"><div class="k">Disparos identificados</div><div class="v">{disparos}</div></div>
<div class="card"><div class="k">Cobertura da decodificacao de rede</div><div class="v">{cobertura}%</div></div></div>
<p class="warn">Servidor: {servidor} · {frames} frames de jogo</p>
<h2>Detectores</h2>{detectores}
<h2>Velocidade angular da mira</h2><div class="card">{chart}<p class="warn">Linha azul: graus/s · tracejado: 1500 graus/s · linhas vermelhas: kills do gravador.</p></div>
<h2>Mortes</h2><div class="card tw"><table><tr><th>Tempo</th><th>Matador</th><th>Vitima</th><th>Arma</th><th></th></tr>{killrows}</table></div>
<h2>Chat ({nchat} mensagens)</h2><div class="card tw"><p class="warn">Mensagens de jogadores, radio, trocas de nome e avisos do servidor/admin gravados na demo. Linhas destacadas contem palavras como cheat, wh, aim, ban, demo.</p><table><tr><th>Tempo</th><th>Tipo</th><th>Jogador</th><th>Mensagem</th></tr>{chatrows}</table></div>
<h2>Jogadores</h2><div class="card tw"><table><tr><th>#</th><th>Nome</th><th>SteamID</th><th>Time</th></tr>{players}</table></div>
<h2>Diagnostico tecnico</h2><div class="card"><p class="warn">Mapa BSP: {bsp}</p><b>Avisos</b><ul class="warn">{avisos}</ul><b>Erros de decodificacao (mensagens)</b><ul class="warn">{erros}</ul></div>
<footer>Gerado em {gerado} pelo Vidalia Demo Analyzer. Ferramenta de apoio a administradores; nao substitui a analise humana.</footer>
</main></body></html>"""


def players_summary(items):
    """Agrupa as demos por jogador gravador (SteamID ou nome)."""
    groups = {}
    for _, rep in items:
        g = rep["gravador"]
        key = g.get("steamid") or ("nome:" + (g.get("nome") or "?"))
        groups.setdefault(key, []).append(rep)
    out = []
    for key, reps in groups.items():
        sc = [r.get("pontuacao", 0) for r in reps]
        dets = sorted({d["detector"].split(" (")[0] for r in reps for d in r["detectores"] if d["status"] in (SUSPEITO, ATENCAO)})
        out.append(dict(nome=reps[0]["gravador"]["nome"], steamid=reps[0]["gravador"].get("steamid", ""), demos=len(reps),
                        max=max(sc), media=round(sum(sc) / len(sc)), alertas=sum(1 for x in sc if x >= 40),
                        detectores=", ".join(dets)))
    out.sort(key=lambda p: (-p["alertas"], -p["max"]))
    return out


def save_batch(items, base):
    """Resumo de varias demos: <base>.csv e <base>.html. Devolve o caminho do HTML."""
    e = html.escape
    names = []
    for _, rep in items:
        for r in rep["detectores"]:
            if r["detector"] not in names:
                names.append(r["detector"])
    with open(base + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["demo", "jogador", "steamid", "mapa", "kills", "veredito", "pontuacao"] + names)
        for path, rep in items:
            st = {r["detector"]: r["status"] for r in rep["detectores"]}
            g = rep["gravador"]
            w.writerow([os.path.basename(path), g["nome"], g["steamid"], rep["demo"]["mapa"], g["kills"], rep["veredito"],
                        rep.get("pontuacao", 0)] + [st.get(n, "") for n in names])
    order = sorted(items, key=lambda it: (-it[1].get("pontuacao", 0), -LEVEL[it[1]["veredito"]]))
    rows = []
    for path, rep in order:
        st = {r["detector"]: r["status"] for r in rep["detectores"]}
        g = rep["gravador"]
        rel = os.path.basename(os.path.splitext(path)[0] + "_vidalia.html")
        cells = "".join('<td><span class="pill" style="background:%s">%s</span></td>' % (COLORS[st[n]], LABELS[st[n]])
                        if n in st else "<td></td>" for n in names)
        rows.append('<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td><td>%d</td><td><span class="pill" style="background:%s">%s</span></td><td><b>%d</b></td>%s</tr>'
                    % (e(rel), e(os.path.basename(path)), e(g["nome"]), e(rep["demo"]["mapa"]), g["kills"],
                       COLORS[rep["veredito"]], LABELS[rep["veredito"]], rep.get("pontuacao", 0), cells))
    prow = "".join('<tr><td>%s</td><td>%s</td><td>%d</td><td><b>%d</b></td><td>%d</td><td>%d</td><td>%s</td></tr>'
                   % (e(p["nome"]), e(p["steamid"] or "-"), p["demos"], p["max"], p["media"], p["alertas"], e(p["detectores"]))
                   for p in players_summary(items))
    head = "".join("<th>%s</th>" % e(n.split(" (")[0]) for n in names)
    page = ("""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resumo Vidalia</title><style>body{margin:0;background:#0f172a;color:#e2e8f0;font:14px/1.5 "Segoe UI",system-ui,sans-serif}
main{max-width:1300px;margin:0 auto;padding:24px 16px}h1{margin:0}h2{font-size:17px;margin:26px 0 4px}.sub{color:#60a5fa;font-size:13px;letter-spacing:2px}
.tw{overflow-x:auto;background:#111c33;border:1px solid #1e293b;border-radius:10px;margin-top:18px}table{width:100%%;border-collapse:collapse}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid #1e293b;white-space:nowrap}th{color:#94a3b8;font-weight:500}
a{color:#93c5fd}.pill{display:inline-block;color:#fff;border-radius:999px;padding:1px 9px;font-size:12px}.warn{color:#94a3b8;font-size:13px}</style></head>
<body><main><h1>VIDALIA</h1><div class="sub">RESUMO DE %d DEMOS · %s</div>
<p class="warn">Triagem automatizada: nao comprova trapaca. Clique no nome da demo para abrir o relatorio individual.</p>
<h2>Por jogador</h2><p class="warn">O mesmo padrao em varias demos do mesmo jogador pesa mais que uma demo isolada.</p>
<div class="tw"><table><tr><th>Jogador</th><th>SteamID</th><th>Demos</th><th>Pontuacao maxima</th><th>Media</th><th>Demos com 40+</th><th>Detectores que alertaram</th></tr>%s</table></div>
<h2>Por demo</h2>
<div class="tw"><table><tr><th>Demo</th><th>Jogador</th><th>Mapa</th><th>Kills</th><th>Resultado</th><th>Pontuacao</th>%s</tr>%s</table></div></main></body></html>"""
            % (len(items), e(__version__), prow, head, "".join(rows)))
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(page)
    return base + ".html"
