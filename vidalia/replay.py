"""Recortes de replay dos momentos apontados pelos detectores.

Para cada evidencia de Atencao/Suspeito guarda alguns segundos da linha do tempo ao redor do frame
apontado (posicao e mira do gravador, posicao dos outros jogadores, tiros, mortes). A aba "Momentos"
da interface usa esses recortes para reconstruir a cena (visao do jogador, radar e grafico da mira)
sem precisar do jogo instalado.
"""
import bisect
from dataclasses import dataclass, field

from .demo import IN_ATTACK, IN_DUCK, IN_JUMP
from .engine import player_name, team_at, weapon_name

ANTES = 4.0      # segundos antes do frame apontado
DEPOIS = 2.0     # segundos depois
MAX_MOMENTOS = 300
GRAVES = ("Suspeito", "Atencao")
_ORDEM = {"Suspeito": 0, "Atencao": 1}


@dataclass
class Quadro:
    """Um frame de rede do gravador da demo."""
    t: float              # segundos desde o inicio da demo
    frame: int
    eye: tuple            # posicao do olho
    view: tuple           # (pitch, yaw) que o jogador via na tela
    cmd: tuple            # (pitch, yaw) enviados ao servidor (onde o tiro sai)
    punch: tuple
    atirando: bool
    pulando: bool
    agachado: bool
    no_chao: bool
    vida: float
    arma: str
    inimigos: dict        # num -> origem
    aliados: dict         # num -> origem


@dataclass
class Momento:
    detector: str
    gravidade: str
    tempo: str
    tempo_s: float
    frame: int
    descricao: str
    i0: int               # primeiro quadro do recorte (indice em Replay.quadros)
    i1: int               # ultimo quadro (inclusivo)
    alvo: int             # quadro do apontamento


@dataclass
class Replay:
    mapa: str
    demo: str = ""                                    # caminho da demo analisada
    jogo: str = "cstrike"                             # pasta do mod gravada na demo
    t0: float = 0.0                                   # tempo da demo correspondente a 00:00.000
    bsp: str = None                                   # caminho do .bsp usado (None = sem mapa)
    gravador: int = 0
    quadros: dict = field(default_factory=dict)       # indice da timeline -> Quadro
    momentos: list = field(default_factory=list)
    nomes: dict = field(default_factory=dict)         # num -> nome
    mortes: list = field(default_factory=list)        # dict(t, matador, vitima, hs, arma)
    tiros: list = field(default_factory=list)         # tempos (s) dos disparos do gravador

    def recorte(self, m):
        return [self.quadros[i] for i in range(m.i0, m.i1 + 1) if i in self.quadros]


def _index_of(tl, frames_idx, ev, t0):
    """Indice da timeline do frame apontado (pelo numero do frame; se nao achar, pelo tempo)."""
    fr = ev.get("frame")
    if fr is not None and fr in frames_idx:
        return frames_idx[fr]
    t = ev.get("tempo_s", 0.0) + t0
    k = bisect.bisect_right(tl.t, t) - 1
    return max(0, min(len(tl.t) - 1, k))


def _mortos_por_tempo(dd):
    """Lista ordenada de (tempo, num, morto?) para saber quem esta vivo a cada instante."""
    out = []
    for e in dd.events:
        if e["tipo"] == "morte" and e.get("vitima"):
            out.append((e["tempo"], e["vitima"], True))
        elif e["tipo"] == "inicio_round":
            out.append((e["tempo"], None, False))
    out.sort(key=lambda x: x[0])
    return out


def build(dd, results, t0, bsp_path=None, map_name="", demo_path=""):
    """Monta o Replay a partir da demo carregada e dos resultados dos detectores."""
    tl = dd.timeline
    rp = Replay(mapa=map_name, demo=demo_path, jogo=(dd.header.game_dir or "cstrike") if dd.header else "cstrike",
                t0=t0, bsp=bsp_path, gravador=dd.local or 0)
    n = len(tl)
    if not n:
        return rp
    frames_idx = {}
    for i, fr in enumerate(tl.frame):
        frames_idx.setdefault(fr, i)

    evs = []
    seen = set()
    for r in results:
        for e in r.get("evidencias", []):
            g = e.get("gravidade")
            if g not in GRAVES:
                continue
            key = (r["detector"], e.get("frame"), e.get("descricao"))
            if key in seen:
                continue
            seen.add(key)
            evs.append((r["detector"], e))
    evs.sort(key=lambda x: (_ORDEM[x[1]["gravidade"]], x[1].get("tempo_s", 0)))
    evs = evs[:MAX_MOMENTOS]

    for det, e in evs:
        i = _index_of(tl, frames_idx, e, t0)
        t = tl.t[i]
        a = bisect.bisect_left(tl.t, t - ANTES)
        b = min(n - 1, bisect.bisect_right(tl.t, t + DEPOIS) - 1)
        a = max(0, min(a, i))
        b = max(b, i)
        rp.momentos.append(Momento(det, e["gravidade"], e.get("tempo", ""), round(t - t0, 3), tl.frame[i],
                                   e.get("descricao", ""), a, b, i))
    rp.momentos.sort(key=lambda m: m.tempo_s)

    # quadros necessarios (uniao das janelas)
    need = set()
    for m in rp.momentos:
        need.update(range(m.i0, m.i1 + 1))
    if not need:
        return rp

    mortes = _mortos_por_tempo(dd)
    mt = [x[0] for x in mortes]
    me = dd.local
    for i in sorted(need):
        t = tl.t[i]
        # quem esta morto neste instante (mortes desde o ultimo inicio de round)
        k = bisect.bisect_right(mt, t)
        dead = set()
        for j in range(k - 1, -1, -1):
            tt, num, morto = mortes[j]
            if not morto:
                break
            dead.add(num)
        mine = team_at(dd, me, t)
        inim, ali = {}, {}
        for num, pos in (tl.players[i] or {}).items():
            if num == me or num in dead:
                continue
            tm = team_at(dd, num, t)
            if tm is None and mine is None:
                inim[num] = pos
            elif tm is None:
                continue  # espectador
            elif mine and tm == mine:
                ali[num] = pos
            else:
                inim[num] = pos
        b = tl.buttons[i]
        rp.quadros[i] = Quadro(
            t=round(t - t0, 4), frame=tl.frame[i], eye=tuple(tl.eye[i]),
            view=(tl.view_pitch[i], tl.view_yaw[i]), cmd=(tl.pitch[i], tl.yaw[i]), punch=tuple(tl.punch[i]),
            atirando=bool(b & IN_ATTACK), pulando=bool(b & IN_JUMP), agachado=bool(b & IN_DUCK),
            no_chao=bool(tl.onground[i]), vida=tl.health[i], arma=weapon_name(tl.weapon[i]),
            inimigos=inim, aliados=ali)

    for num in dd.players:
        rp.nomes[num] = player_name(dd, num)
    for e in dd.events:
        if e["tipo"] == "morte":
            rp.mortes.append(dict(t=round(e["tempo"] - t0, 3), matador=e.get("matador"), vitima=e.get("vitima"),
                                  hs=bool(e.get("headshot")), arma=e.get("arma", "")))
    rp.tiros = [round(s["t"] - t0, 4) for s in dd.shots]
    return rp
