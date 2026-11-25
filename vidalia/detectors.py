"""Detectores heuristicos. Cada um devolve evidencias para revisao humana.

Nenhum detector comprova trapaca; os limiares sao conservadores e configuraveis.
"""
import math
import statistics

from .demo import IN_ATTACK, IN_JUMP
from .engine import (angle_between, angles_to, enemies_at, player_name, weapon_name, wrap180)

OK, ATENCAO, SUSPEITO, SEM_DADOS = "Normal", "Atencao", "Suspeito", "Sem dados"
LEVEL = {SEM_DADOS: -1, OK: 0, ATENCAO: 1, SUSPEITO: 2}

AUTO_WEAPONS = {7, 8, 12, 13, 14, 15, 19, 20, 22, 23, 24, 27, 28, 30}
HEAD_Z = 17.0      # olho/cabeca acima da origem (em pe)
BODY_RADIUS = 16.0

DEFAULTS = dict(
    flick_graus=30.0,          # rotacao minima considerada "flick"
    flick_janela=0.10,         # s
    flick_erro_alvo=1.5,       # graus ate o alvo no disparo
    reacao_trigger=0.060,      # s
    silent_graus=1.5,
    bhop_cadeia=10,
    speed_razao=1.25,
)


def fmt_time(t, t0=0.0):
    t = max(0.0, t - t0)
    m = int(t // 60)
    return "%02d:%06.3f" % (m, t - 60 * m)


def _result(nome, status, resumo, metricas=None, evidencias=None, nota=None):
    return dict(detector=nome, status=status, resumo=resumo, metricas=metricas or {},
                evidencias=evidencias or [], nota=nota or "")


def _idx_at(tl, t, lo=0):
    """Indice do ultimo frame com tempo <= t (busca binaria)."""
    a, b = lo, len(tl.t) - 1
    if b < 0:
        return 0
    while a < b:
        m = (a + b + 1) // 2
        if tl.t[m] <= t:
            a = m
        else:
            b = m - 1
    return a


def _err_to(tl, i, pos):
    eye = tl.eye[i]
    p, y, dist = angles_to(eye, (pos[0], pos[1], pos[2] + HEAD_Z))
    return angle_between(tl.pitch[i], tl.yaw[i], p, y), dist


def _nearest_enemy(dd, i):
    best = None
    for num, pos in enemies_at(dd, i).items():
        e, dist = _err_to(dd.timeline, i, pos)
        if best is None or e < best[1]:
            best = (num, e, dist, pos)
    return best


def angular_speeds(tl):
    out = [0.0]
    for i in range(1, len(tl)):
        dt = tl.t[i] - tl.t[i - 1]
        if dt <= 0.0005:
            out.append(0.0)
            continue
        d = math.hypot(wrap180(tl.yaw[i] - tl.yaw[i - 1]), tl.pitch[i] - tl.pitch[i - 1])
        out.append(d / dt)
    return out


# ------------------------------------------------------------------ AIMBOT
def detect_aimbot(dd, cfg, speeds):
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    ev = []
    kills = [e for e in dd.events if e["tipo"] == "morte" and e["matador"] == dd.local and e["vitima"] != dd.local]
    shot_times = [s["t"] for s in dd.shots]
    suspicious = 0
    errs = []
    flicks_total = 0
    for k in kills:
        # ultimo disparo antes da morte (ate 1 s)
        st = [t for t in shot_times if k["tempo"] - 1.0 <= t <= k["tempo"] + 0.02]
        ts = st[-1] if st else k["tempo"]
        i = _idx_at(tl, ts)
        j0 = _idx_at(tl, ts - cfg["flick_janela"])
        rot = 0.0
        for j in range(j0 + 1, i + 1):
            rot += math.hypot(wrap180(tl.yaw[j] - tl.yaw[j - 1]), tl.pitch[j] - tl.pitch[j - 1])
        peak = max(speeds[j0:i + 1] or [0.0])
        victim_pos = (tl.players[i] or {}).get(k["vitima"])
        err = dist = None
        if victim_pos:
            err, dist = _err_to(tl, i, victim_pos)
            errs.append(err)
        flick = rot >= cfg["flick_graus"]
        flicks_total += flick
        susp = flick and err is not None and err <= cfg["flick_erro_alvo"] + math.degrees(math.atan2(BODY_RADIUS * 0.3, max(dist or 1, 1)))
        if flick and err is None:
            susp = peak > 1500
        if susp:
            suspicious += 1
        if flick or susp:
            ev.append(dict(
                tempo=fmt_time(ts, t0), tempo_s=round(ts - t0, 3), frame=tl.frame[i],
                descricao="Kill em %s (%s%s): rotacao de %.1f graus em %d ms antes do disparo, pico %.0f graus/s%s"
                % (player_name(dd, k["vitima"]), k.get("arma") or "?", ", HS" if k.get("headshot") else "",
                   rot, cfg["flick_janela"] * 1000, peak,
                   ", erro ao alvo %.2f graus" % err if err is not None else ""),
                gravidade=SUSPEITO if susp else ATENCAO))
    # flicks sem kill (anomalias angulares isoladas)
    isolated = sum(1 for s in speeds if s > 1500)
    if not kills:
        status = SEM_DADOS if not tl.t else (ATENCAO if isolated > 30 else OK)
        resumo = "Nenhuma kill do gravador identificada; %d amostras acima de 1500 graus/s." % isolated
    else:
        ratio = suspicious / len(kills)
        status = SUSPEITO if suspicious >= 3 and ratio >= 0.3 else (ATENCAO if suspicious >= 1 else OK)
        resumo = "%d kills analisadas, %d com flick, %d com flick + travamento preciso no alvo." % (
            len(kills), flicks_total, suspicious)
    return _result("Aimbot (flick + travamento)", status, resumo, dict(
        kills=len(kills), kills_com_flick=flicks_total, kills_suspeitas=suspicious,
        erro_medio_alvo=round(statistics.mean(errs), 2) if errs else None,
        amostras_acima_1500_graus_s=isolated), ev,
        "Flicks rapidos tambem ocorrem em jogadores habilidosos; avalie o padrao ao longo de varias kills.")


# --------------------------------------------------------------- TRIGGERBOT
def detect_triggerbot(dd, cfg):
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if not any(tl.players):
        return _result("Triggerbot", SEM_DADOS, "Posicoes dos inimigos indisponiveis (entidades nao decodificadas).")
    reactions = []
    ev = []
    prev_press = False
    on_since = None
    for i in range(len(tl)):
        best = _nearest_enemy(dd, i)
        on = False
        if best:
            num, err, dist, _ = best
            radius = math.degrees(math.atan2(BODY_RADIUS * 0.6, max(dist, 1.0)))
            on = err <= radius
        if on and on_since is None:
            on_since = tl.t[i]
        elif not on:
            on_since = None
        press = bool(tl.buttons[i] & IN_ATTACK)
        if press and not prev_press and on_since is not None and tl.weapon[i] not in (29, 4, 9, 25, 6):
            r = tl.t[i] - on_since
            reactions.append(r)
            if r <= 0.0001:
                ev.append(dict(tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
                               descricao="Disparo no mesmo frame em que a mira entrou no corpo de %s (%s)"
                               % (player_name(dd, best[0]), weapon_name(tl.weapon[i])),
                               gravidade=ATENCAO, _zero=True))
        prev_press = press
    if len(reactions) < 15:
        return _result("Triggerbot", SEM_DADOS if not reactions else OK,
                       "Apenas %d disparos iniciados com a mira sobre um inimigo (minimo 15)." % len(reactions),
                       dict(amostras=len(reactions)), [])
    n = len(reactions)
    same = sum(1 for r in reactions if r <= 0.0001)
    fast = sum(1 for r in reactions if r <= cfg["reacao_trigger"])
    same_frac = same / n
    if n >= 30:
        status = SUSPEITO if same_frac >= 0.45 else (ATENCAO if same_frac >= 0.30 else OK)
    else:
        status = ATENCAO if same_frac >= 0.45 else OK
    ev = [e for e in ev if e.get("_zero")] if status != OK else []
    for e in ev:
        e.pop("_zero", None)
    return _result("Triggerbot", status,
                   "%d de %d disparos (%.0f%%) sairam no MESMO frame em que a mira entrou no inimigo; %.0f%% em ate %d ms."
                   % (same, n, 100 * same_frac, 100 * fast / n, cfg["reacao_trigger"] * 1000),
                   dict(amostras=n, disparos_mesmo_frame=same, mesmo_frame_percent=round(100 * same_frac, 1),
                        reacoes_ate_60ms=fast, mediana_reacao_ms=round(statistics.median(reactions) * 1000, 1)), ev[:50],
                   "Calibrado com partidas reais: jogadores limpos 17,5% no mesmo frame (e ~48% em ate 60 ms, por isso esse "
                   "criterio antigo foi abandonado); triggerbot HPP ~60%. Suspeito exige 30+ amostras.")


# ------------------------------------------------------------- SILENT AIM
def detect_silent(dd, cfg):
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if not tl.t:
        return _result("Silent aim", SEM_DADOS, "Sem frames.")
    diffs_fire, diffs_idle = [], []
    ev = []
    for i in range(len(tl)):
        d = math.hypot(wrap180(tl.yaw[i] - tl.view_yaw[i]), tl.pitch[i] - tl.view_pitch[i])
        if tl.buttons[i] & IN_ATTACK:
            diffs_fire.append(d)
            if d >= cfg["silent_graus"] and len(ev) < 100:
                ev.append(dict(tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
                               descricao="Angulo enviado ao servidor difere %.2f graus da visao do jogador durante ataque" % d,
                               gravidade=SUSPEITO))
        else:
            diffs_idle.append(d)
    # disparo real (evento) em direcao diferente de mira + recuo (calibrado: evento = comando + 1x punch)
    ev_mismatch = 0
    n_ev = 0
    for sh in dd.shots:
        if sh.get("fonte") == "evento" and sh.get("angulos") and any(sh["angulos"]):
            n_ev += 1
            i = sh["i"]
            # o evento pode estar gravado 1 frame antes da atualizacao da mira: usa o menor desvio entre i e i+1
            d = min(angle_between(sh["angulos"][0], sh["angulos"][1], tl.pitch[j] + tl.punch[j][0], tl.yaw[j] + tl.punch[j][1])
                    for j in (i, min(i + 1, len(tl) - 1)))
            if d >= 15.0:
                ev_mismatch += 1
                if len(ev) < 100:
                    ev.append(dict(tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
                                   descricao="Disparo saiu %.1f graus fora da direcao da mira (+recuo)" % d,
                                   gravidade=SUSPEITO))
    n_bad = sum(1 for d in diffs_fire if d >= cfg["silent_graus"])
    n_idle_bad = sum(1 for d in diffs_idle if d >= cfg["silent_graus"])
    base = n_idle_bad / max(1, len(diffs_idle))
    rate = n_bad / max(1, len(diffs_fire))
    status = OK
    ev_rate = ev_mismatch / n_ev if n_ev else 0.0
    if (n_bad >= 5 and rate > max(0.02, base * 5)) or (ev_mismatch >= 3 and ev_rate >= 0.2):
        status = SUSPEITO
    elif (n_bad >= 2 and rate > base * 3) or (ev_mismatch >= 2 and ev_rate >= 0.05):
        status = ATENCAO
    return _result("Silent aim", status,
                   "%d de %d disparos reais sairam 15+ graus fora da mira; %d frames de ataque com comando divergente da visao (base %.2f%%)."
                   % (ev_mismatch, n_ev, n_bad, base * 100),
                   dict(frames_ataque=len(diffs_fire), divergentes=n_bad, disparos_reais=n_ev, eventos_divergentes=ev_mismatch,
                        taxa_base_percent=round(base * 100, 3)), ev,
                   "Compara cl_viewangles (visao) com os angulos do usercmd. Divergencias concentradas nos disparos sao caracteristicas de silent aim.")


# --------------------------------------------------------------- NO RECOIL
def detect_norecoil(dd, cfg):
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    sprays = []
    cur = []
    for i in range(len(tl)):
        if (tl.buttons[i] & IN_ATTACK) and tl.weapon[i] in AUTO_WEAPONS:
            cur.append(i)
        else:
            if len(cur) >= 15:
                sprays.append(cur)
            cur = []
    if len(cur) >= 15:
        sprays.append(cur)
    if not sprays:
        return _result("No recoil", SEM_DADOS, "Nenhuma rajada longa com arma automatica identificada.")
    shot_t = sorted(x["t"] for x in dd.shots if x.get("fonte") == "evento")
    if shot_t:
        import bisect as _b
        real = []
        for sp in sprays:
            n = _b.bisect_right(shot_t, tl.t[sp[-1]] + 0.02) - _b.bisect_left(shot_t, tl.t[sp[0]] - 0.02)
            if n >= 5:
                real.append(sp)
        ignored = len(sprays) - len(real)
        sprays = real
    else:
        ignored = 0
    if not sprays:
        return _result("No recoil", SEM_DADOS, "Nenhuma rajada com 5+ disparos reais (%d descartadas sem disparo)." % ignored)
    zero_punch = 0
    ratios = []
    per_weapon = {}
    ev = []
    for sp in sprays:
        punch = [abs(tl.punch[i][0]) + abs(tl.punch[i][1]) for i in sp]
        if max(punch) < 0.05:
            zero_punch += 1
            ev.append(dict(tempo=fmt_time(tl.t[sp[0]], t0), tempo_s=round(tl.t[sp[0]], 3), frame=tl.frame[sp[0]],
                           descricao="Rajada de %.2f s com %s sem nenhum punchangle (recuo zerado)"
                           % (tl.t[sp[-1]] - tl.t[sp[0]], weapon_name(tl.weapon[sp[0]])), gravidade=SUSPEITO))
            continue
        dpunch = tl.punch[sp[-1]][0] - tl.punch[sp[0]][0]
        dpitch = tl.pitch[sp[-1]] - tl.pitch[sp[0]]
        if abs(dpunch) > 0.5:
            ratios.append(-dpitch / dpunch)
            per_weapon.setdefault(weapon_name(tl.weapon[sp[0]]), []).append(-dpitch / dpunch)
    perfect = [r for r in ratios if 1.85 <= r <= 2.15]
    status = OK
    zero_frac = zero_punch / len(sprays)
    if zero_punch >= 3 and zero_frac >= 0.5:
        status = ATENCAO
    elif ratios and len(ratios) >= 5 and len(perfect) / len(ratios) >= 0.8 and statistics.pstdev(ratios) < 0.1:
        status = ATENCAO
    elif zero_punch >= 1:
        status = ATENCAO
    return _result("No recoil", status,
                   "%d rajadas com disparos reais (%d descartadas sem disparo); %d sem recuo; compensacao media %s (2.0 = total)."
                   % (len(sprays), ignored, zero_punch, "%.2f" % statistics.mean(ratios) if ratios else "-"),
                   dict(rajadas=len(sprays), descartadas_sem_disparo=ignored, sem_punch=zero_punch,
                        compensacao_por_arma={k: round(statistics.mean(v), 2) for k, v in per_weapon.items()},
                        compensacao_media=round(statistics.mean(ratios), 3) if ratios else None,
                        compensacao_desvio=round(statistics.pstdev(ratios), 3) if len(ratios) > 1 else None), ev,
                   "EXPERIMENTAL (maximo: Atencao): as demos publicas de teste nao permitiram calibrar este detector.")


# ------------------------------------------------------------------- BHOP
def detect_bhop(dd, cfg):
    """Pulo perfeito = decolagem apos exatamente 1 frame em solo com o pulo acionado.
    Calibrado com demos publicas: scripts 84-93%; humanos (inclusive scroll do mouse) <= 60%."""
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if not tl.t:
        return _result("Bunny hop script", SEM_DADOS, "Sem frames.")
    minus = any(v == -1 for v in tl.onground)
    grounded = [(v != -1) if minus else bool(v) for v in tl.onground]
    jumps = []   # (indice_decolagem, frames_em_solo)
    run = 0
    jump_in_run = False
    for i in range(len(tl)):
        if grounded[i]:
            run += 1
            jump_in_run = jump_in_run or bool(tl.buttons[i] & IN_JUMP)
            continue
        if run:
            if jump_in_run or (tl.buttons[i] & IN_JUMP):
                jumps.append((i, run))
            run = 0
            jump_in_run = False
    if len(jumps) < 6:
        return _result("Bunny hop script", OK if jumps else SEM_DADOS, "Apenas %d pulos." % len(jumps),
                       dict(pulos=len(jumps)))
    perfect = [g == 1 for _, g in jumps]
    ratio = sum(perfect) / len(perfect)
    best = cur = 0
    start = None
    ev = []
    for k, (i, g) in enumerate(jumps):
        if g == 1 and (k == 0 or tl.t[i] - tl.t[jumps[k - 1][0]] < 1.5 or cur == 0):
            if cur == 0:
                start = i
            cur += 1
        else:
            if cur >= 5:
                ev.append(dict(tempo=fmt_time(tl.t[start], t0), tempo_s=round(tl.t[start] - t0, 3), frame=tl.frame[start],
                               descricao="Sequencia de %d pulos perfeitos consecutivos" % cur, gravidade=ATENCAO))
            best = max(best, cur)
            cur = 1 if g == 1 else 0
            start = i
    if cur >= 5:
        ev.append(dict(tempo=fmt_time(tl.t[start], t0), tempo_s=round(tl.t[start] - t0, 3), frame=tl.frame[start],
                       descricao="Sequencia de %d pulos perfeitos consecutivos" % cur, gravidade=ATENCAO))
    best = max(best, cur)
    if ratio >= 0.80 and len(jumps) >= 8:
        status = SUSPEITO
    elif ratio >= 0.70 or (ratio >= 0.80 and len(jumps) >= 6):
        status = ATENCAO
    else:
        status = OK
    return _result("Bunny hop script", status,
                   "%d pulos, %.0f%% com timing perfeito (1 frame em solo), maior sequencia perfeita: %d."
                   % (len(jumps), ratio * 100, best),
                   dict(pulos=len(jumps), perfeitos_percent=round(ratio * 100, 1), maior_sequencia=best), ev,
                   "Calibrado com demos publicas: scripts 84-93%; humanos, inclusive com scroll do mouse, ate 60%.")


# --------------------------------------------------------------- SPEEDHACK
def detect_speed(dd, cfg):
    """Compara o relogio do cliente (tempo da demo, acelerado por speedhack) com o relogio
    do servidor (svc_time), que o cheat nao controla. Calibrado com demos publicas:
    limpas ~1.00; speedhack 5-6x."""
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if len(tl) < 100 or sum(1 for x in tl.srvtime if x) < len(tl) * 0.5:
        return _result("Speedhack", SEM_DADOS, "Relogio do servidor indisponivel.")
    windows = []
    ws = 0
    for i in range(1, len(tl)):
        dsrv = tl.srvtime[i] - tl.srvtime[i - 1]
        dcl = tl.t[i] - tl.t[i - 1]
        if dsrv < -0.5 or dsrv > 5 or dcl > 5 or dcl < 0:   # troca de mapa, reconexao, pausa
            ws = i
            continue
        span_srv = tl.srvtime[i] - tl.srvtime[ws]
        if span_srv >= 5.0:
            windows.append((ws, (tl.t[i] - tl.t[ws]) / span_srv))
            ws = i
    if len(windows) < 2:
        return _result("Speedhack", SEM_DADOS, "Janelas validas insuficientes (%d)." % len(windows))
    ratios = sorted(r for _, r in windows)
    med = ratios[len(ratios) // 2]
    thr = cfg["speed_razao"]
    ev = []
    flagged = 0
    for i, r in windows:
        if r >= thr:
            flagged += 1
            if len(ev) < 50:
                ev.append(dict(tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
                               descricao="Relogio do cliente %.2fx mais rapido que o do servidor (janela de 5 s)" % r,
                               gravidade=SUSPEITO))
    frac = flagged / len(windows)
    # 2a medida: duracao declarada dos comandos (msec) vs tempo real, somada em janelas de 0,5 s.
    # Frame a frame o msec inteiro distorce a razao em fps muito alto (ex.: 1000+ fps -> falso 1,3x);
    # cada frame da demo pode carregar varios comandos (delta do outgoing_sequence).
    fr_r = []
    bursts = []   # (indice, razao) de janelas com rajada de velocidade
    acc_ms = acc_dt = 0.0
    for i in range(1, len(tl)):
        dt = tl.t[i] - tl.t[i - 1]
        if not (0.0005 < dt < 0.5) or tl.frame[i] == tl.frame[i - 1]:
            acc_ms = acc_dt = 0.0
            continue
        dseq = tl.outseq[i] - tl.outseq[i - 1]
        acc_ms += tl.msec[i] * (dseq if 1 <= dseq <= 10 else 1)
        acc_dt += dt
        if acc_dt >= 0.5:
            r = acc_ms / 1000.0 / acc_dt
            fr_r.append(r)
            if r >= 2.5:
                bursts.append((i, r))
            acc_ms = acc_dt = 0.0
    fr_r.sort()
    # rajadas: speedhack ligado por tecla (Furion, Interium...). Calibrado com 211 demos publicas:
    # limpas no maximo 1,48x numa janela de 0,5 s; cheats 2,9x a 30x.
    for i, r in bursts[:30]:
        ev.append(dict(tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
                       descricao="Rajada de velocidade: comandos somando %.1fx o tempo real em 0,5 s" % r, gravidade=SUSPEITO))
    max_burst = max((r for _, r in bursts), default=0.0)
    fmed = fr_r[len(fr_r) // 2] if fr_r else 0.0
    ffrac = sum(1 for x in fr_r if x > 1.3) / len(fr_r) if fr_r else 0.0
    if fmed >= 1.5 or ffrac >= 0.3:
        ev.insert(0, dict(tempo=fmt_time(t0, t0), tempo_s=round(t0, 3), frame=tl.frame[0],
                          descricao="Duracao declarada dos frames %.1fx maior que o tempo real (%.0f%% dos frames acima de 1.3x)"
                          % (fmed, ffrac * 100), gravidade=SUSPEITO))
    if med >= thr or (flagged >= 3 and frac >= 0.05) or fmed >= 1.5 or ffrac >= 0.3 or len(bursts) >= 2 or max_burst >= 5:
        status = SUSPEITO
    elif bursts:
        status = ATENCAO
    elif flagged >= 2 or ffrac >= 0.15:   # um pico isolado de uma janela e tipico de lag (clean_lags_test.dem)
        status = ATENCAO
    else:
        status = OK
    return _result("Speedhack", status,
                   "Relogio cliente/servidor: mediana %.2f, pior %.2f (%d de %d janelas acima de %.2f); msec/tempo real: mediana %.2f."
                   % (med, ratios[-1], flagged, len(windows), thr, fmed),
                   dict(janelas=len(windows), janelas_suspeitas=flagged, mediana_razao=round(med, 3),
                        pior_razao=round(ratios[-1], 3), msec_por_tempo_real=round(fmed, 3),
                        frames_acima_1_3x_percent=round(ffrac * 100, 1), rajadas=len(bursts),
                        maior_rajada=round(max_burst, 2)), ev,
                   "Calibrado com demos publicas: limpas = 1.00 (rajadas ate 1,48x); speedhack 2,9x a 30x. "
                   "Engasgos de rede causam picos isolados no relogio do servidor.")


# ---------------------------------------------------------------- WALLHACK
def detect_wallhack(dd, cfg, bsp):
    """Episodios em que a mira fica sobre um inimigo oculto pela geometria do mapa.
    Separa RASTREAMENTO ATIVO (inimigo se move e a mira o acompanha) de PRE-MIRA
    ESTATICA (mira parada num angulo comum). So rastreamento ativo conta para o status."""
    NAME = "Wallhack (rastreamento atraves de paredes)"
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if bsp is None:
        return _result(NAME, SEM_DADOS, "Mapa .bsp nao fornecido; selecione a pasta cstrike/maps para habilitar esta analise.")
    if not any(tl.players):
        return _result(NAME, SEM_DADOS, "Posicoes dos inimigos indisponiveis.")
    step = 2
    hidden_total = 0.0
    hidden_track = 0.0
    cache_vis = {}
    last_vis = {}      # inimigo -> ultimo instante visivel
    open_ep = {}       # inimigo -> lista de amostras (i, dt, erro, dist, pos)
    episodes = []

    ep_since = {}      # inimigo -> segundos desde a ultima visualizacao, medido NA ABERTURA do episodio

    def close(num):
        smp = open_ep.pop(num, None)
        since = ep_since.pop(num, None)
        if not smp:
            return
        dur = sum(x[1] for x in smp)
        if dur < 1.0:
            return
        # percurso acumulado do inimigo e da direcao-alvo; rotacao acumulada da mira
        path = 0.0
        tgt_rot = 0.0
        view_rot = 0.0
        follow = 0.0
        for a, b in zip(smp, smp[1:]):
            path += math.dist(a[4][:2], b[4][:2])
            ty = wrap180(b[5] - a[5])                 # variacao do azimute do alvo
            vy = wrap180(tl.yaw[b[0]] - tl.yaw[a[0]])  # variacao do yaw da mira
            tgt_rot += abs(ty)
            view_rot += abs(vy)
            if ty * vy > 0:
                follow += min(abs(ty), abs(vy))
        follow_ratio = follow / tgt_rot if tgt_rot > 0.5 else 0.0
        active = path >= 96.0 and view_rot >= 3.0 and follow_ratio >= 0.6
        episodes.append(dict(i=smp[0][0], dur=dur, num=num, active=active, moved=path, rot=view_rot,
                             follow=follow_ratio, err=statistics.mean(x[2] for x in smp),
                             dist=statistics.mean(x[3] for x in smp), since=since))

    for i in range(0, len(tl), step):
        dt = tl.t[min(i + step, len(tl) - 1)] - tl.t[i]
        if dt <= 0 or dt > 0.5:
            for n in list(open_ep):
                close(n)
            continue
        eye = tl.eye[i]
        any_hidden = False
        tracked_now = set()
        for num, pos in enemies_at(dd, i).items():
            head = (pos[0], pos[1], pos[2] + HEAD_Z)
            key = (round(eye[0] / 8), round(eye[1] / 8), round(eye[2] / 8), round(pos[0] / 8), round(pos[1] / 8), round(pos[2] / 8))
            vis = cache_vis.get(key)
            if vis is None:
                vis = bsp.visible(eye, head) or bsp.visible(eye, pos)
                cache_vis[key] = vis
            if vis:
                last_vis[num] = tl.t[i]
                if num in open_ep:
                    close(num)
                continue
            any_hidden = True
            p, y, dist = angles_to(eye, (pos[0], pos[1], pos[2] + HEAD_Z * 0.5))
            err = angle_between(tl.pitch[i], tl.yaw[i], p, y)
            if dist > 120 and err <= 4.0:
                tracked_now.add(num)
                if num not in open_ep:
                    lv = last_vis.get(num)
                    ep_since[num] = (tl.t[i] - lv) if lv is not None else None
                open_ep.setdefault(num, []).append((i, dt, err, dist, pos, y))
        for n in list(open_ep):
            if n not in tracked_now:
                close(n)
        if any_hidden:
            hidden_total += dt
        if tracked_now:
            hidden_track += dt
    for n in list(open_ep):
        close(n)
    episodes.sort(key=lambda e: e["i"])
    active = [e for e in episodes if e["active"]]
    blind = [e for e in active if e["since"] is None or e["since"] >= 1.0]   # sem informacao visual recente
    ev = []
    for e in episodes[:60]:
        i = e["i"]
        since = ("visto pela ultima vez %.1f s antes" % e["since"]) if e["since"] is not None else "ainda nao tinha sido visto"
        ev.append(dict(
            tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
            descricao="%s: mira em %s oculto por parede durante %.1f s (dist. %.0f, erro medio %.1f graus, inimigo percorreu %.0f u, mira girou %.0f graus, acompanhamento %.0f%%, %s, arma %s)"
            % ("RASTREAMENTO ATIVO" if e["active"] else "Pre-mira estatica", player_name(dd, e["num"]), e["dur"], e["dist"],
               e["err"], e["moved"], e["rot"], e["follow"] * 100, since, weapon_name(tl.weapon[i])),
            gravidade=ATENCAO if (e["active"] and (e["since"] is None or e["since"] >= 1.0)) else OK))
    ratio = hidden_track / hidden_total if hidden_total else 0.0
    # EXPERIMENTAL: sem demos de calibracao, o maximo e Atencao
    status = ATENCAO if len(blind) >= 2 else OK
    return _result(NAME, status,
                   "%d episodios de rastreamento ATIVO de inimigos ocultos (>= 1 s), %d deles sem ver o inimigo ha 1+ s; %d de pre-mira estatica; mira sobre ocultos em %.1f%% do tempo com inimigos ocultos."
                   % (len(active), len(blind), len(episodes) - len(active), ratio * 100),
                   dict(tempo_inimigos_ocultos_s=round(hidden_total, 1), tempo_rastreando_ocultos_s=round(hidden_track, 1),
                        episodios=len(episodes), episodios_ativos=len(active), ativos_sem_visao_recente=len(blind),
                        maior_episodio_s=round(max((e["dur"] for e in episodes), default=0.0), 2)), ev,
                   "EXPERIMENTAL (maximo: Atencao). So conta para o status o rastreamento ativo (inimigo andando 96+ u, mira girando no mesmo sentido em 60%+ do movimento) de inimigo nao visto ha 1+ s. "
                   "Considera apenas a geometria solida do mapa: portas, caixas moveis e fumaca nao entram. O jogador pode ter ouvido passos. "
                   "Tempos (tempo/tempo_s) sao contados a partir do inicio da gravacao.")


# ---------------------------------------------------------------- SPINBOT
def detect_antiaim(dd, cfg, speeds):
    tl = dd.timeline
    t0 = tl.t[0] if tl.t else 0.0
    if not tl.t:
        return _result("Anti-aim / spinbot", SEM_DADOS, "Sem frames.")
    bad_pitch = [i for i in range(len(tl)) if abs(tl.pitch[i]) > 89.5 and abs(wrap180(tl.pitch[i])) > 89.5]
    # giro continuo acima de 2000 graus/s por 1,5 s+ (giros rapidos de mouse duram ~0,5 s:
    # demo_bad_positive.dem e sensitivity100.dem, limpas, tinham giros de 30 frames)
    spin = 0
    run_t = 0.0
    counted = False
    for i, s in enumerate(speeds):
        if s > 2000 and i > 0:
            run_t += tl.t[i] - tl.t[i - 1]
            if run_t >= 1.5 and not counted:
                spin += 1
                counted = True
        else:
            run_t = 0.0
            counted = False
    ev = []
    if bad_pitch:
        i = bad_pitch[0]
        ev.append(dict(tempo=fmt_time(tl.t[i], t0), tempo_s=round(tl.t[i] - t0, 3), frame=tl.frame[i],
                       descricao="Pitch fora do limite do jogo (%.1f graus) em %d frames" % (tl.pitch[i], len(bad_pitch)),
                       gravidade=SUSPEITO))
    status = SUSPEITO if (len(bad_pitch) > 10 or spin >= 2) else (ATENCAO if bad_pitch or spin else OK)
    return _result("Anti-aim / spinbot", status, "%d frames com pitch invalido; %d sequencias de giro continuo." % (len(bad_pitch), spin),
                   dict(pitch_invalido=len(bad_pitch), giros=spin), ev)


BASE_DETECTORS = 8   # detectores deste modulo; os de detectors_ecd sao somados em detector_count()


def detector_count():
    from .detectors_ecd import ECD_DETECTORS
    return BASE_DETECTORS + len(ECD_DETECTORS)


def run_all(dd, cfg=None, bsp=None, progress=None, span=(0.0, 1.0)):
    """Executa todos os detectores. `progress(f)` e chamado apos cada detector,
    com f distribuido linearmente no intervalo `span`."""
    c = dict(DEFAULTS)
    c.update(cfg or {})
    speeds = angular_speeds(dd.timeline)
    steps = [
        lambda: detect_aimbot(dd, c, speeds),
        lambda: detect_triggerbot(dd, c),
        lambda: detect_silent(dd, c),
        lambda: detect_norecoil(dd, c),
        lambda: detect_wallhack(dd, c, bsp),
        lambda: detect_bhop(dd, c),
        lambda: detect_speed(dd, c),
        lambda: detect_antiaim(dd, c, speeds),
    ]
    from .detectors_ecd import ECD_DETECTORS   # import tardio: o modulo importa deste
    steps += [(lambda f=f: f(dd, c)) for f in ECD_DETECTORS]
    lo, hi = span
    results = []
    for k, step in enumerate(steps):
        results.append(step())
        if progress:
            progress(lo + (hi - lo) * (k + 1) / len(steps))
    # Coerencia: evidencias de um detector Normal/Sem dados sao apenas diagnosticas; sem duplicatas.
    for r in results:
        seen = set()
        clean = []
        for e in r["evidencias"]:
            key = (e.get("frame"), e.get("descricao"))
            if key in seen:
                continue
            seen.add(key)
            if r["status"] in (OK, SEM_DADOS) and e.get("gravidade") in (ATENCAO, SUSPEITO):
                e["gravidade"] = OK
            clean.append(e)
        r["evidencias"] = clean
    return results, speeds
