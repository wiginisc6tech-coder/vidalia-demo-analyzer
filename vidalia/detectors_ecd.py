"""Detectores comportamentais para funcoes de multihacks de CS 1.6.

Referencia: familias de cheats listadas nos relatorios do ECD (Easy Cheats Detector,
fungun.top/ecd), por exemplo HPP, Alternative, Furion, Oxware, Evol, Midnight,
"opengl32 multihack", "No smoke" e "ESP + Strafe hack". O ECD detecta essas ferramentas
por assinatura no computador do jogador; a demo nao contem processos nem DLLs, entao aqui
detectamos o EFEITO das funcoes no jogo (movimento, rede, mira em condicoes impossiveis).

Todos estes detectores sao EXPERIMENTAIS: nao foram calibrados com demos reais e, salvo
onde indicado, ficam limitados a "Atencao". Nenhum deles comprova trapaca.
"""
import math
import re

from .demo import IN_ATTACK, IN_DUCK, IN_JUMP
from .detectors import ATENCAO, OK, SEM_DADOS, SUSPEITO, _err_to, _idx_at, _result, fmt_time
from .engine import enemies_at, player_name, wrap180

EXPERIMENTAL = "EXPERIMENTAL (nao calibrado com demos reais): trate como indicio para revisao."


def _ev(tl, i, t0, desc, grav=ATENCAO):
    return dict(tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
                descricao=desc, gravidade=grav)


def _grounded(tl):
    minus = any(v == -1 for v in tl.onground)
    return [(v != -1) if minus else bool(v) for v in tl.onground]


def _air_segments(tl, grounded):
    """Lista de (inicio, fim_exclusivo) de cada periodo no ar."""
    segs, s = [], None
    for i, g in enumerate(grounded):
        if not g and s is None:
            s = i
        elif g and s is not None:
            segs.append((s, i))
            s = None
    if s is not None:
        segs.append((s, len(grounded)))
    return segs


# ------------------------------------------------------------ STRAFE HELPER
def detect_strafe(dd, cfg):
    """Auto-strafe / strafe helper / strafe optimizer.

    1) Troca de lado frame a frame: o sidemove inverte o sinal (esquerda <-> direita) de um frame
       para o seguinte. Calibrado com 211 demos publicas: limpas tiveram no maximo 4 trocas
       (0,2% dos pares de frames no ar); strafes de HPP, Evol, Midnight, Zero e "strafe optimizer"
       tiveram de 10 a 407 trocas (3,5% a 67%).
    2) Sincronia perfeita: o lado do strafe acompanha o giro do mouse em 95%+ de 300+ frames
       (limpas: no maximo 42% com essa quantidade de frames).
    """
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if len(tl) < 50 or not tl.side:
        return _result("Strafe automatico", SEM_DADOS, "Sem frames.")
    grounded = _grounded(tl)
    segs = [s for s in _air_segments(tl, grounded) if s[1] - s[0] >= 8]
    air = sum(b - a for a, b in segs)
    if air < 100:
        return _result("Strafe automatico", OK if segs else SEM_DADOS, "Pouco tempo no ar (%d frames)." % air,
                       dict(frames_no_ar=air))
    ev = []
    flips = pairs = 0
    js = jt = 0
    for a, b in segs:
        seg_flips = 0
        for i in range(a + 1, b):
            s0, s1 = tl.side[i - 1], tl.side[i]
            dt = tl.t[i] - tl.t[i - 1]
            if s0 and s1 and 0 < dt < 0.1:
                pairs += 1
                if (s0 > 0) != (s1 > 0):
                    flips += 1
                    seg_flips += 1
            dy = wrap180(tl.yaw[i] - tl.yaw[i - 1])
            if abs(dy) >= 0.3 and s1:
                jt += 1
                if (dy > 0 and s1 < 0) or (dy < 0 and s1 > 0):   # girando p/ esquerda + moveleft (e vice-versa)
                    js += 1
        if seg_flips >= 3 and len(ev) < 60:
            ev.append(_ev(tl, a, t0, "Salto com %d trocas de lado (esquerda/direita) de um frame para o seguinte" % seg_flips,
                          SUSPEITO if seg_flips >= 6 else ATENCAO))
    rate = flips / pairs if pairs else 0.0
    sync = js / jt if jt else 0.0
    if flips >= 20 and rate >= 0.03:
        status = SUSPEITO
    elif (flips >= 8 and rate >= 0.02) or (jt >= 300 and sync >= 0.95):
        status = ATENCAO
    else:
        status = OK
    if jt >= 300 and sync >= 0.95:
        ev.insert(0, _ev(tl, segs[0][0], t0, "Strafe acompanhou o giro do mouse em %.1f%% de %d frames no ar" % (sync * 100, jt)))
    return _result("Strafe automatico", status,
                   "%d trocas de lado frame a frame (%.1f%% dos frames no ar); sincronia strafe x mouse %.0f%% em %d frames."
                   % (flips, rate * 100, sync * 100, jt),
                   dict(frames_no_ar=air, saltos=len(segs), trocas_por_frame=flips, taxa_trocas_percent=round(rate * 100, 2),
                        sincronia_percent=round(sync * 100, 1), frames_sincronia=jt), ev,
                   "Calibrado com 211 demos publicas (UnrealDemoScanner): limpas <= 4 trocas; strafe automatico de "
                   "HPP/Evol/Midnight/Zero: 10 a 407. Sincronia de 95%+ em 300+ frames so apareceu com cheat.")


# ---------------------------------------------------- SCRIPTS DE AGACHAMENTO
def detect_duck_script(dd, cfg):
    """Ground strafe / SGS / DDRun por script: agachar e sair do chao no primeiro frame em solo,
    de forma repetida. Calibrado com 211 demos publicas: limpas ate 36% com 1 frame em solo
    (ate 67% com ate 2 frames); scripts de HPP/Evol/Midnight/Interium 69-100% com 1 frame;
    "Zero" 91-98% com 2 frames."""
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if len(tl) < 50:
        return _result("Script de agachamento (SGS/DDRun)", SEM_DADOS, "Sem frames.")
    grounded = _grounded(tl)
    hops = []   # (indice_saida_do_chao, frames_em_solo)
    run = 0
    duck = jump = False
    for i in range(len(tl)):
        if grounded[i]:
            run += 1
            duck = duck or bool(tl.buttons[i] & IN_DUCK)
            jump = jump or bool(tl.buttons[i] & IN_JUMP)
            continue
        if run and duck and not jump and not (tl.buttons[i] & IN_JUMP):
            hops.append((i, run))
        run = 0
        duck = jump = False
    if len(hops) < 6:
        return _result("Script de agachamento (SGS/DDRun)", OK if hops else SEM_DADOS,
                       "Apenas %d saidas do chao por agachamento." % len(hops), dict(duck_hops=len(hops)))
    perfect = sum(1 for _, g in hops if g == 1)
    ratio = perfect / len(hops)
    ratio2 = sum(1 for _, g in hops if g <= 2) / len(hops)
    best = cur = 0
    ev = []
    start = None
    for k, (i, g) in enumerate(hops):
        if g == 1 and (cur == 0 or tl.t[i] - tl.t[hops[k - 1][0]] < 1.0):
            start = i if cur == 0 else start
            cur += 1
        else:
            if cur >= 6 and len(ev) < 40:
                ev.append(_ev(tl, start, t0, "Sequencia de %d agachamentos com timing perfeito (1 frame em solo)" % cur))
            best = max(best, cur)
            cur = 1 if g == 1 else 0
            start = i
    if cur >= 6:
        ev.append(_ev(tl, start, t0, "Sequencia de %d agachamentos com timing perfeito (1 frame em solo)" % cur))
    best = max(best, cur)
    if ratio >= 0.80 and perfect >= 8:
        status = SUSPEITO
    elif (ratio >= 0.55 and perfect >= 5) or (ratio2 >= 0.85 and len(hops) >= 15):
        status = ATENCAO
    else:
        status = OK
    if status != OK and not ev:
        ev.append(_ev(tl, hops[0][0], t0, "%.0f%% dos agachamentos com 1 frame em solo (%.0f%% com ate 2)" % (ratio * 100, ratio2 * 100)))
    return _result("Script de agachamento (SGS/DDRun)", status,
                   "%d saidas do chao por agachamento: %.0f%% com 1 frame em solo, %.0f%% com ate 2; maior sequencia: %d."
                   % (len(hops), ratio * 100, ratio2 * 100, best),
                   dict(duck_hops=len(hops), perfeitos_percent=round(ratio * 100, 1), ate_2_frames_percent=round(ratio2 * 100, 1),
                        maior_sequencia=best), ev,
                   "Ground strafe/SGS/DDRun por script. Calibrado com demos publicas: limpas <= 36% com 1 frame "
                   "(<= 67% com 2); cheats 69-100%.")


# ---------------------------------------------------------------- FAKE LAG
def detect_fakelag(dd, cfg):
    """Fake lag: o cliente segura (choke) seus pacotes por varios frames e envia em lote.
    Na demo isso aparece como varios frames seguidos com o mesmo outgoing_sequence enquanto
    o jogo roda normalmente (frames curtos). Travadas do PC (frames longos) sao ignoradas."""
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if len(tl) < 200:
        return _result("Fake lag (choke de pacotes)", SEM_DADOS, "Sem frames.")
    changes = sum(1 for i in range(1, len(tl)) if tl.outseq[i] != tl.outseq[i - 1])
    if changes < len(tl) * 0.1:
        return _result("Fake lag (choke de pacotes)", SEM_DADOS, "Sequencia de pacotes do cliente indisponivel na demo.")
    runs = []   # (inicio, fim, duracao)
    s = 0
    for i in range(1, len(tl) + 1):
        if i < len(tl) and tl.outseq[i] == tl.outseq[s]:
            continue
        e = i - 1
        if e - s >= 3:
            dts = [tl.t[k] - tl.t[k - 1] for k in range(s + 1, e + 1)]
            if dts and max(dts) < 0.04 and min(dts) > 0:
                runs.append((s, e, tl.t[e] - tl.t[s]))
        s = i
    total = max(1e-6, tl.t[-1] - tl.t[0])
    long_runs = [r for r in runs if r[2] >= 0.1]
    choked = sum(r[2] for r in long_runs)
    frac = choked / total
    ev = [_ev(tl, a, t0, "Cliente ficou %d ms sem enviar pacotes (%d frames retidos)" % (round(d * 1000), b - a + 1))
          for a, b, d in long_runs[:60]]
    status = ATENCAO if len(long_runs) >= 10 and frac >= 0.03 else OK
    return _result("Fake lag (choke de pacotes)", status,
                   "%d periodos de 100+ ms sem envio de pacotes com o jogo rodando normalmente (%.1f%% do tempo)."
                   % (len(long_runs), frac * 100),
                   dict(periodos_retidos=len(long_runs), tempo_retido_percent=round(frac * 100, 2),
                        maior_retencao_ms=round(max((r[2] for r in runs), default=0) * 1000)), ev,
                   "Funcao 'fake lag' de multihacks: faz o jogador 'teleportar' para os outros. " + EXPERIMENTAL)


# --------------------------------------------------- mira em condicao impossivel
def _tracking_episodes(dd, idxs, blocked, min_dur=0.4, max_err=2.5, min_move=40.0):
    """Episodios em que a mira acompanha um inimigo em movimento enquanto `blocked(i, pos)`
    diz que o jogador nao deveria enxerga-lo. Retorna [(i_inicio, i_fim, num_inimigo)]."""
    tl = dd.timeline
    out = []
    cur = None   # (inicio, num, pos_inicial)
    last = None
    for i in idxs:
        hit = None
        for num, pos in enemies_at(dd, i).items():
            e, dist = _err_to(tl, i, pos)
            if e <= max_err and dist > 100 and blocked(i, pos):
                hit = (num, pos)
                break
        contiguous = last is not None and i == last + 1
        if hit and cur and contiguous and hit[0] == cur[1]:
            pass
        else:
            if cur:
                _close(tl, cur, last, out, min_dur, min_move, dd)
            cur = (i, hit[0], hit[1]) if hit else None
        last = i
    if cur:
        _close(tl, cur, last, out, min_dur, min_move, dd)
    return out


def _close(tl, cur, end, out, min_dur, min_move, dd):
    a, num, p0 = cur
    if tl.t[end] - tl.t[a] < min_dur:
        return
    # deslocamento maximo do inimigo durante o episodio (ele pode ir e voltar)
    moved = 0.0
    for k in range(a, end + 1, 5):
        p = (tl.players[k] or {}).get(num)
        if p:
            moved = max(moved, math.dist(p0, p))
    if moved >= min_move:
        out.append((a, end, num))


def _kills_by_me(dd):
    me = dd.local
    return [k for k in dd.events if k["tipo"] == "morte" and k["matador"] == me and k["vitima"] != me]


# ---------------------------------------------------------------- NO FLASH
def detect_noflash(dd, cfg):
    """No flash: com a tela totalmente branca (ScreenFade da flashbang), o jogador continua
    acompanhando inimigos em movimento com precisao ou abatendo-os."""
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    flashes = [e for e in dd.events if e["tipo"] == "flash" and e.get("alfa", 0) >= 250 and e.get("hold", 0) >= 0.3]
    if not tl.t or not flashes:
        return _result("No flash", SEM_DADOS, "Nenhum cegamento total por flashbang registrado na demo.")
    wins = [(f["tempo"], f["tempo"] + f["hold"]) for f in flashes]
    idxs = []
    for a, b in wins:
        i = _idx_at(tl, a)
        while i < len(tl) and tl.t[i] <= b:
            if tl.health[i] > 0:
                idxs.append(i)
            i += 1
    idxs = sorted(set(idxs))
    trk = _tracking_episodes(dd, idxs, lambda i, pos: True)
    kills = [k for k in _kills_by_me(dd) if any(a <= k["tempo"] <= b for a, b in wins)]
    ev = []
    for a, b, num in trk[:40]:
        ev.append(_ev(tl, a, t0, "Cego pela flash, acompanhou %s em movimento por %.1f s com a mira"
                      % (player_name(dd, num), tl.t[b] - tl.t[a])))
    for k in kills[:40]:
        i = _idx_at(tl, k["tempo"])
        ev.append(_ev(tl, i, t0, "Abateu %s%s com a tela totalmente branca (flash)"
                      % (player_name(dd, k["vitima"]), " (HS)" if k.get("headshot") else "")))
    ev.sort(key=lambda e: e["tempo_s"])
    status = ATENCAO if len(trk) >= 2 or len(kills) >= 2 or (trk and kills) else OK
    return _result("No flash", status,
                   "%d cegamentos totais; %d acompanhamentos de inimigo e %d abates durante o cegamento."
                   % (len(flashes), len(trk), len(kills)),
                   dict(cegamentos=len(flashes), acompanhamentos=len(trk), abates_cego=len(kills)), ev,
                   "Funcao 'no flash' de multihacks e opengl32 hooks. Abates cegos por spray acontecem; "
                   "acompanhamento repetido de alvo em movimento e mais indicativo. " + EXPERIMENTAL)


# ---------------------------------------------------------------- NO SMOKE
SMOKE_RADIUS = 110.0       # nucleo denso da fumaca (unidades)
SMOKE_START, SMOKE_END = 1.5, 16.0   # janela (s) apos a detonacao em que a fumaca e densa


def _seg_sphere(p0, p1, c, r):
    dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    L2 = dx * dx + dy * dy + dz * dz
    if L2 <= 0:
        return False
    t = max(0.0, min(1.0, ((c[0] - p0[0]) * dx + (c[1] - p0[1]) * dy + (c[2] - p0[2]) * dz) / L2))
    q = (p0[0] + t * dx, p0[1] + t * dy, p0[2] + t * dz)
    return math.dist(q, c) < r


def detect_nosmoke(dd, cfg):
    """No smoke: a mira acompanha inimigos em movimento atraves do nucleo de uma fumaca."""
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    smokes = []
    for e in dd.events:
        if e["tipo"] != "fumaca":
            continue
        if any(abs(e["tempo"] - s[0]) < 3 and math.dist(e["origem"], s[1]) < 64 for s in smokes):
            continue
        c = e["origem"]
        smokes.append((e["tempo"], (c[0], c[1], c[2] + 32.0)))
    if not tl.t or not smokes:
        return _result("No smoke", SEM_DADOS, "Nenhuma granada de fumaca registrada na demo.")

    def active(t):
        return [c for ts, c in smokes if ts + SMOKE_START <= t <= ts + SMOKE_END]

    def blocked(i, pos):
        eye = tl.eye[i]
        head = (pos[0], pos[1], pos[2] + 17.0)
        return any(_seg_sphere(eye, head, c, SMOKE_RADIUS) for c in active(tl.t[i]))

    idxs = [i for i in range(len(tl)) if tl.health[i] > 0 and active(tl.t[i])]
    trk = _tracking_episodes(dd, idxs, blocked)
    kills = []
    for k in _kills_by_me(dd):
        if not active(k["tempo"]):
            continue
        i = _idx_at(tl, k["tempo"])
        pos = (tl.players[i] or {}).get(k["vitima"])
        if pos and blocked(i, pos):
            kills.append((i, k))
    ev = [_ev(tl, a, t0, "Mira acompanhou %s atraves da fumaca por %.1f s" % (player_name(dd, num), tl.t[b] - tl.t[a]))
          for a, b, num in trk[:40]]
    ev += [_ev(tl, i, t0, "Abateu %s com a linha de visao passando pelo centro de uma fumaca" % player_name(dd, k["vitima"]))
           for i, k in kills[:40]]
    ev.sort(key=lambda e: e["tempo_s"])
    status = ATENCAO if len(trk) >= 2 or (trk and len(kills) >= 2) else OK
    return _result("No smoke", status,
                   "%d fumacas; %d acompanhamentos de inimigo e %d abates atraves do nucleo da fumaca."
                   % (len(smokes), len(trk), len(kills)),
                   dict(fumacas=len(smokes), acompanhamentos=len(trk), abates_pela_fumaca=len(kills)), ev,
                   "Funcao 'no smoke' (listada pelo ECD em multihacks/opengl32). A fumaca e aproximada por uma esfera de "
                   "%d unidades; spray em fumaca e jogada comum, por isso so acompanhamento repetido conta. " % SMOKE_RADIUS
                   + EXPERIMENTAL)


# ------------------------------------------------------ AIMBOT DE 1 FRAME (VAI E VOLTA)
def detect_snap(dd, cfg):
    """Aimbot que vira a mira para o alvo apenas no frame do disparo e a devolve no frame seguinte
    (a mira 'pisca' no alvo). Calibrado com 211 demos publicas: limpas no maximo 2 disparos com esse
    padrao (3,4%); aim_type_4, aimpack5, HPP_ALL_FEATURES e zero_test2: 4 a 149 (10% a 73%).
    Obs.: o "perfect silent" do HPP/Furion nao deixa nem este rastro na demo."""
    from .engine import angle_between
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    n = len(tl)
    shots = sorted({s["i"] for s in dd.shots if s.get("fonte") == "evento"})
    if len(shots) < 3 or n < 50:
        return _result("Aimbot de 1 frame (vai e volta)", SEM_DADOS, "Poucos disparos reais (%d)." % len(shots))

    def spike(i):
        if i < 1 or i + 1 >= n:
            return 0.0
        d1 = angle_between(tl.pitch[i - 1], tl.yaw[i - 1], tl.pitch[i], tl.yaw[i])
        d2 = angle_between(tl.pitch[i], tl.yaw[i], tl.pitch[i + 1], tl.yaw[i + 1])
        d3 = angle_between(tl.pitch[i - 1], tl.yaw[i - 1], tl.pitch[i + 1], tl.yaw[i + 1])
        return min(d1, d2) if d1 > 2.0 and d2 > 2.0 and d3 < 0.25 * min(d1, d2) else 0.0

    ev = []
    hits = 0
    for i in shots:
        d = max(spike(j) for j in (i - 1, i, i + 1))
        if d:
            hits += 1
            if len(ev) < 60:
                ev.append(_ev(tl, i, t0, "No disparo a mira saltou %.1f graus e voltou ao ponto anterior no frame seguinte" % d,
                              SUSPEITO))
    rate = hits / len(shots)
    if hits >= 8 or (hits >= 4 and rate >= 0.2):
        status = SUSPEITO
    elif hits >= 4 and rate >= 0.08:
        status = ATENCAO
    else:
        status = OK
    return _result("Aimbot de 1 frame (vai e volta)", status,
                   "%d de %d disparos com a mira saltando e voltando em 1 frame (%.1f%%)." % (hits, len(shots), rate * 100),
                   dict(disparos=len(shots), picos=hits, taxa_percent=round(rate * 100, 1)), ev,
                   "Calibrado com demos publicas: limpas <= 2 disparos (3,4%); aimbots 4-149 (10-73%).")


# ---------------------------------------------------------------- AUTOFIRE
SEMI_AUTO_SKIP = {5}   # xm1014 (escopeta automatica); as demais automaticas vem de AUTO_WEAPONS


def detect_autofire(dd, cfg):
    """Autopistol / autofire: armas semiautomaticas disparando no ritmo exato da arma
    (intervalos iguais com tolerancia de 8 ms) por muitos tiros seguidos.
    Calibrado com 211 demos publicas: limpas ate 12 tiros seguidos nesse ritmo
    (scroll do mouse/clique rapido); autopistol de HPP/Zero/"rage" 16 a 30."""
    from .detectors import AUTO_WEAPONS
    from .engine import weapon_name
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    sh = [s for s in dd.shots if s.get("fonte") == "evento"]
    skip = AUTO_WEAPONS | SEMI_AUTO_SKIP
    semi = [s for s in sh if tl.weapon[s["i"]] not in skip]
    if len(semi) < 6:
        return _result("Autofire (autopistol)", SEM_DADOS if not semi else OK,
                       "Apenas %d disparos com armas semiautomaticas." % len(semi), dict(disparos_semi=len(semi)))
    chains = []   # (inicio_idx_shot, tamanho, ciclo, arma)
    run = 0
    start = 0
    prev = None
    for k in range(1, len(sh)):
        a, b = sh[k - 1], sh[k]
        w = tl.weapon[b["i"]]
        dt = b["t"] - a["t"]
        valid = w not in skip and w == tl.weapon[a["i"]] and 0.05 < dt < 0.3
        if valid and prev is not None and abs(dt - prev) <= 0.008:
            run += 1
        else:
            if run >= 1:
                chains.append((start, run + 1, prev, tl.weapon[sh[start]["i"]]))
            run = 1 if valid else 0
            start = k - 1
        prev = dt if valid else None
    if run >= 1:
        chains.append((start, run + 1, prev, tl.weapon[sh[start]["i"]]))
    best = max((c[1] for c in chains), default=0)
    long_chains = [c for c in chains if c[1] >= 16]
    ev = [_ev(tl, sh[c[0]]["i"], t0, "%d tiros seguidos de %s a cada %.0f ms exatos (ritmo maximo da arma)"
              % (c[1], weapon_name(c[3]), c[2] * 1000)) for c in long_chains[:40]]
    status = ATENCAO if long_chains else OK
    return _result("Autofire (autopistol)", status,
                   "%d disparos com armas semiautomaticas; maior sequencia no ritmo exato da arma: %d tiros." % (len(semi), best),
                   dict(disparos_semi=len(semi), maior_sequencia=best, sequencias_16_mais=len(long_chains)), ev,
                   "Calibrado com demos publicas: limpas <= 12 tiros seguidos no ritmo exato; autopistol 16-30. "
                   "Autopistol com poucos tiros seguidos nao e detectado. Scroll do mouse bindado no ataque pode "
                   "gerar sequencias longas: confira a demo.")


# ------------------------------------------------------- ASSINATURAS NO CONSOLE
# Nomes de cheats de CS 1.6 vistos nos relatorios do ECD e termos tipicos de comandos de cheat.
CHEAT_NAMES = ["hpp", "alternative", "furion", "oxware", "evol", "midnight", "xone", "noradrenaline",
               "memsense", "bluemonday", "nash", "zemon", "catlean", "advhack", "tcheats", "crystal",
               "tapware", "evelion", "renegat", "exloader", "gignight", "r-aimbot", "shark"]
CHEAT_TERMS = ["aimbot", "aim_bot", "triggerbot", "trigger_bot", "wallhack", "esp_", "norecoil", "no_recoil",
               "nospread", "no_spread", "nosmoke", "noflash", "speedhack", "autostrafe", "strafe_helper",
               "fakelag", "fake_lag", "antiaim", "anti_aim", "spinbot", "cheat"]
_RX = re.compile(r"(?<![a-z0-9_])(?:%s)" % "|".join(
    "(%s)" % re.escape(x) if x.endswith("_") else r"(%s)s?(?![a-z])" % re.escape(x) for x in CHEAT_NAMES + CHEAT_TERMS), re.I)
# chat e troca de nome carregam texto livre (ex.: "say ele ta de hpp"): nao sao comandos do jogador
_SKIP = ("say", "say_team", "name", "setinfo", "messagemode", "echo")


def detect_console(dd, cfg):
    """Procura nomes/comandos de cheat nos comandos de console gravados na demo."""
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if not dd.console:
        return _result("Assinaturas de cheat no console", SEM_DADOS, "A demo nao gravou comandos de console.",
                       dict(comandos=0))
    ev = []
    names = set()
    for c in dd.console:
        cmd = (c.get("comando") or "").strip()
        if cmd.split(" ", 1)[0].lower() in _SKIP:
            continue
        m = _RX.search(cmd)
        if not m:
            continue
        word = next(g for g in m.groups() if g).lower()
        brand = word in CHEAT_NAMES
        names.add(word)
        if len(ev) < 60:
            ev.append(dict(tempo=fmt_time(c["t"], t0), tempo_s=round(c["t"] - t0, 3), frame=None,
                           descricao="Comando de console '%s' contem '%s'%s" % (cmd[:80], word, " (nome de cheat)" if brand else ""),
                           gravidade=SUSPEITO if brand else ATENCAO))
    status = SUSPEITO if any(e["gravidade"] == SUSPEITO for e in ev) else (ATENCAO if ev else OK)
    return _result("Assinaturas de cheat no console", status,
                   "%d comandos de console analisados; %d com termos de cheat%s."
                   % (len(dd.console), len(ev), (" (" + ", ".join(sorted(names)) + ")") if names else ""),
                   dict(comandos=len(dd.console), ocorrencias=len(ev), termos=sorted(names)), ev,
                   "Lista de nomes baseada em cheats de CS 1.6 detectados pelo ECD. A maioria dos cheats nao deixa "
                   "comandos na demo: ausencia de ocorrencias nao inocenta ninguem.")


ECD_DETECTORS = [detect_snap, detect_strafe, detect_duck_script, detect_fakelag, detect_noflash, detect_nosmoke, detect_autofire,
                 detect_console]
