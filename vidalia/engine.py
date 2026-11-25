"""Coleta de dados: percorre a demo, decodifica a rede e monta a linha do tempo."""
import bisect
import math
from collections import Counter

from .demo import (IN_ATTACK, ClientDataFrame, ConsoleFrame, EventFrame, NetFrame,
                   iter_frames, read_header)
from .netmsg import CS_WEAPONS, NetDecoder

FIRE_EXCLUDE = ("knife", "createexplo", "createsmoke", "decal", "c4", "hegrenade",
                "flashbang", "smokegrenade", "vehicle", "train")


class Timeline:
    """Amostras por frame de rede do gravador da demo."""

    def __init__(self):
        self.t = []
        self.frame = []
        self.pitch = []
        self.yaw = []
        self.view_pitch = []
        self.view_yaw = []
        self.buttons = []
        self.onground = []
        self.punch = []
        self.eye = []
        self.msec = []
        self.frametime = []
        self.weapon = []
        self.health = []
        self.outseq = []
        self.fwd = []       # forwardmove do usercmd
        self.side = []      # sidemove do usercmd (negativo = esquerda)
        self.srvtime = []
        self.players = []   # dict num -> origin (compartilhado entre frames sem mudanca)

    def __len__(self):
        return len(self.t)


class DemoData:
    def __init__(self):
        self.header = None
        self.timeline = Timeline()
        self.shots = []          # dict(t, idx_timeline, origem, angulos, arma, fonte)
        self.events = []         # eventos de alto nivel (mortes, armas, ...)
        self.players = {}
        self.local = None
        self.warnings = []
        self.stats = {}
        self.console = []
        self.decoder = None


def wrap180(a):
    a = (a + 180.0) % 360.0 - 180.0
    return a


def angle_between(p1, y1, p2, y2):
    """Distancia angular (graus) entre duas direcoes (pitch, yaw)."""
    v1 = forward(p1, y1)
    v2 = forward(p2, y2)
    d = max(-1.0, min(1.0, v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]))
    return math.degrees(math.acos(d))


def forward(pitch, yaw):
    p = math.radians(pitch)
    y = math.radians(yaw)
    cp = math.cos(p)
    return (cp * math.cos(y), cp * math.sin(y), -math.sin(p))


def angles_to(src, dst):
    dx, dy, dz = dst[0] - src[0], dst[1] - src[1], dst[2] - src[2]
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw, math.sqrt(dx * dx + dy * dy + dz * dz)


# Fracao da barra de progresso dedicada a leitura da demo (o restante vai para os detectores).
LOAD_SHARE = 0.6


def load(path, progress=None):
    dd = DemoData()
    warnings = dd.warnings
    hdr = read_header(path)
    dd.header = hdr
    dec = NetDecoder()
    dd.decoder = dec
    tl = dd.timeline
    st = dec.st
    kinds = Counter()
    last_players = {}
    attack_prev = False
    total = max(1, hdr.file_size)
    n = 0
    playback_started = False
    pos = [0]
    for fr in iter_frames(path, hdr, warnings, pos):
        n += 1
        if progress and n % 1000 == 0:
            # leitura = 0% a LOAD_SHARE do total, proporcional aos bytes ja lidos
            progress(min(LOAD_SHARE, pos[0] / total * LOAD_SHARE))
        if isinstance(fr, NetFrame):
            kinds["rede"] += 1
            dec.player_pos = None
            dec.feed(fr.msg, fr.time, fr.incoming_sequence)
            if dec.player_pos is not None:
                last_players = dec.player_pos
            if fr.segment == 0 and hdr.entries[0].type == 0:
                continue  # segmento LOADING: apenas estado
            playback_started = True
            if dd.local is None:
                dd.local = st.playernum or (fr.playernum + 1)
            tl.t.append(fr.time)
            tl.frame.append(fr.frame)
            tl.pitch.append(fr.cmd_angles[0])
            tl.yaw.append(fr.cmd_angles[1])
            tl.view_pitch.append(fr.cl_viewangles[0])
            tl.view_yaw.append(fr.cl_viewangles[1])
            tl.buttons.append(fr.buttons)
            tl.onground.append(fr.onground)
            tl.punch.append(fr.punchangle)
            tl.eye.append(fr.vieworg)
            tl.msec.append(fr.msec)
            tl.frametime.append(fr.frametime)
            tl.weapon.append(st.weapon_id)
            tl.health.append(fr.health)
            tl.outseq.append(fr.outgoing_sequence)
            tl.fwd.append(fr.forwardmove)
            tl.side.append(fr.sidemove)
            tl.srvtime.append(st.time)
            tl.players.append(last_players)
            attack_prev = bool(fr.buttons & IN_ATTACK)
        elif isinstance(fr, EventFrame):
            kinds["evento"] += 1
            if not playback_started:
                continue
            name = st.event_names.get(fr.index, "")
            local = dd.local or st.playernum
            if fr.entindex and local and fr.entindex != local:
                continue
            low = name.lower()
            if name and any(x in low for x in FIRE_EXCLUDE):
                continue
            dd.shots.append(dict(t=fr.time, i=max(0, len(tl) - 1), nome_evento=name or ("evento %d" % fr.index),
                                 angulos=fr.angles, origem=fr.origin, fonte="evento"))
        elif isinstance(fr, ConsoleFrame):
            kinds["console"] += 1
            dd.console.append(dict(t=fr.time, comando=fr.command))
        elif isinstance(fr, ClientDataFrame):
            kinds["clientdata"] += 1
    # Sem nomes de eventos (lista de recursos nao decodificada) - os eventos genericos
    # podem incluir coisas que nao sao disparos; nesse caso usamos tambem IN_ATTACK.
    if not dd.shots or not st.event_names:
        fallback = []
        prev = False
        for i, b in enumerate(tl.buttons):
            cur = bool(b & IN_ATTACK)
            if cur and not prev:
                fallback.append(dict(t=tl.t[i], i=i, nome_evento="+attack", angulos=None, origem=None, fonte="botao"))
            prev = cur
        if not dd.shots:
            dd.shots = fallback
            warnings.append("Disparos reais nao identificados; usando inicio de +attack como aproximacao.")
    dd.events = dec.events
    dd.players = st.players
    # historico de times (TeamInfo) para avaliar cada momento com o time da epoca
    dd.team_hist = {}
    for e in dd.events:
        if e["tipo"] == "time":
            dd.team_hist.setdefault(e["jogador"], []).append((e["tempo"], _norm_team(e["time"])))
    dd.stats = dict(
        frames=dict(kinds),
        pacotes=dec.packets,
        pacotes_decodificados=dec.packets_ok,
        cobertura_rede=round(100.0 * dec.packets_ok / dec.packets, 1) if dec.packets else 0.0,
        mensagens=dict(dec.counts.most_common()),
        erros=dict(dec.errors.most_common(15)),
        desconhecidas=dict(dec.unknown),
        descricoes_delta=sorted(st.deltas),
        user_messages=len(st.usermsgs),
        eventos_registrados=len(st.event_names),
    )
    if progress:
        progress(LOAD_SHARE)
    return dd


def _norm_team(t):
    t = (t or "").upper()
    if t.startswith("T"):
        return "T"
    if t.startswith("C"):
        return "CT"
    return None


def team_of(players, num):
    return _norm_team((players.get(num) or {}).get("time"))


def team_at(dd, num, t):
    """Time do jogador no instante t (historico de TeamInfo); None se desconhecido/espectador."""
    hist = getattr(dd, "team_hist", {}).get(num)
    if not hist:
        return team_of(dd.players, num)
    times = dd.__dict__.setdefault("_team_times", {}).get(num)
    if times is None:
        times = [h[0] for h in hist]
        dd._team_times[num] = times
    k = bisect.bisect_right(times, t) - 1
    return hist[max(k, 0)][1]


def enemies_at(dd, i):
    pl = dd.timeline.players[i] or {}
    t = dd.timeline.t[i]
    mine = team_at(dd, dd.local, t)
    out = {}
    for num, pos in pl.items():
        if num == dd.local:
            continue
        tm = team_at(dd, num, t)
        if mine and tm and tm == mine:
            continue
        out[num] = pos
    return out


def player_name(dd, num):
    p = dd.players.get(num) or {}
    return p.get("nome") or ("jogador #%s" % num)


def weapon_name(wid):
    return CS_WEAPONS.get(wid, "desconhecida") if wid else "desconhecida"
