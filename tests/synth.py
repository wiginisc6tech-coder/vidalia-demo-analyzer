"""Gerador de demos GoldSrc sinteticas para testes (escrita inversa do parser)."""
import math
import struct

from vidalia.delta import (DT_ANGLE, DT_FLOAT, DT_INTEGER, DT_SIGNED, DT_STRING, META, Field)
from vidalia.demo import EVENT_FRAME, NETINFO_SIZE, REF_FMT, USERCMD


class BitWriter:
    def __init__(self):
        self.bits = []

    def write(self, v, n):
        for i in range(n):
            self.bits.append((v >> i) & 1)

    def sbits(self, v, n):
        self.write(1 if v < 0 else 0, 1)
        self.write(abs(int(v)), n - 1)

    def string(self, s):
        for c in s.encode() + b"\0":
            self.write(c, 8)

    def tobytes(self):
        out = bytearray()
        for i in range(0, len(self.bits), 8):
            b = 0
            for j, bit in enumerate(self.bits[i:i + 8]):
                b |= bit << j
            out.append(b)
        return bytes(out)


def write_field(bw, f, v):
    t = f.type & ~DT_SIGNED
    signed = bool(f.type & DT_SIGNED)
    if t == DT_STRING:
        bw.string(v)
    elif t == DT_ANGLE:
        bw.write(int(round(v / (360.0 / (1 << f.bits)))) & ((1 << f.bits) - 1), f.bits)
    else:
        iv = int(round(v * f.pre / f.post))
        if signed:
            bw.sbits(iv, f.bits)
        else:
            bw.write(iv, f.bits)


def write_delta(bw, desc, values):
    mask = 0
    for i, f in enumerate(desc):
        if f.name in values:
            mask |= 1 << i
    nbytes = (mask.bit_length() + 7) // 8
    bw.write(nbytes, 3)
    for i in range(nbytes):
        bw.write((mask >> (8 * i)) & 0xFF, 8)
    for i, f in enumerate(desc):
        if f.name in values:
            write_field(bw, f, values[f.name])


def b_string(s):
    return s.encode() + b"\0"


DESCS = {
    "event_t": [Field("entindex", DT_INTEGER, 11), Field("angles[0]", DT_FLOAT | DT_SIGNED, 26, 8192.0),
                Field("angles[1]", DT_FLOAT | DT_SIGNED, 26, 8192.0), Field("origin[0]", DT_FLOAT | DT_SIGNED, 21, 8.0),
                Field("origin[1]", DT_FLOAT | DT_SIGNED, 21, 8.0), Field("origin[2]", DT_FLOAT | DT_SIGNED, 21, 8.0)],
    "clientdata_t": [Field("origin[0]", DT_FLOAT | DT_SIGNED, 21, 128.0), Field("health", DT_FLOAT | DT_SIGNED, 10)],
    "weapon_data_t": [Field("m_iId", DT_INTEGER, 5), Field("m_iClip", DT_INTEGER | DT_SIGNED, 10)],
    "entity_state_t": [Field("origin[0]", DT_FLOAT | DT_SIGNED, 16, 8.0), Field("origin[1]", DT_FLOAT | DT_SIGNED, 16, 8.0),
                       Field("origin[2]", DT_FLOAT | DT_SIGNED, 16, 8.0), Field("modelindex", DT_INTEGER, 10)],
    "entity_state_player_t": [Field("origin[0]", DT_FLOAT | DT_SIGNED, 24, 32.0),
                              Field("origin[1]", DT_FLOAT | DT_SIGNED, 24, 32.0),
                              Field("origin[2]", DT_FLOAT | DT_SIGNED, 24, 32.0),
                              Field("angles[1]", DT_ANGLE, 16)],
    "custom_entity_state_t": [Field("rendermode", DT_INTEGER, 8)],
}


def msg_deltadesc(name, desc):
    bw = BitWriter()
    for f in desc:
        write_delta(bw, META, {"fieldType": f.type, "fieldName": f.name, "significant_bits": f.bits,
                               "premultiply": f.pre, "postmultiply": f.post})
    return bytes([14]) + b_string(name) + struct.pack("<H", len(desc)) + bw.tobytes()


def msg_serverinfo(playernum):
    return (bytes([11]) + struct.pack("<iii", 48, 1, 0) + b"\0" * 16 + bytes([16, playernum - 1, 1]) +
            b_string("cstrike") + b_string("Servidor Teste") + b_string("maps/de_teste.bsp") + b_string("") + b"\0")


def msg_userinfo(slot, name, sid):
    return bytes([13, slot - 1]) + struct.pack("<i", slot) + b_string("\\name\\%s\\*sid\\%s\\model\\gign" % (name, sid)) + b"\0" * 16


def msg_newusermsg(idx, name, size):
    return bytes([39, idx, size]) + name.encode().ljust(16, b"\0")


def msg_resourcelist(events):
    bw = BitWriter()
    bw.write(len(events), 12)
    for idx, name in events:
        bw.write(5, 4); bw.string(name); bw.write(idx, 12); bw.write(100, 24); bw.write(0, 3); bw.write(0, 1)
    bw.write(0, 1)
    return bytes([43]) + bw.tobytes()


def msg_spawnbaseline():
    bw = BitWriter()
    bw.write((1 << 11) - 1, 11)
    bw.write(0x1F, 5)
    bw.write(0, 6)
    return bytes([22]) + bw.tobytes()


def msg_packetentities(players):
    """players: dict num -> (x,y,z) ; pacote completo."""
    bw = BitWriter()
    bw.write(len(players), 16)
    last = 0
    for num in sorted(players):
        d = num - last
        if d == 1:
            bw.write(1, 1)
        else:
            bw.write(0, 1)
            if d <= 0 or d >= 64:
                bw.write(1, 1); bw.write(num, 11)
            else:
                bw.write(0, 1); bw.write(d, 6)
        last = num
        bw.write(0, 1)  # custom
        bw.write(0, 1)  # offset
        x, y, z = players[num]
        write_delta(bw, DESCS["entity_state_player_t"], {"origin[0]": x, "origin[1]": y, "origin[2]": z})
    bw.write(0, 16)
    return bytes([40]) + bw.tobytes()


def msg_clientdata():
    bw = BitWriter()
    bw.write(0, 1)
    write_delta(bw, DESCS["clientdata_t"], {"health": 100})
    bw.write(1, 1); bw.write(28, 6); write_delta(bw, DESCS["weapon_data_t"], {"m_iId": 28, "m_iClip": 30})
    bw.write(0, 1)
    return bytes([15]) + bw.tobytes()


def msg_time(t):
    return bytes([7]) + struct.pack("<f", t)


def um(idx, body, variable=False):
    return bytes([idx]) + (bytes([len(body)]) if variable else b"") + body


def frame_net(kind, t, fr, angles, view_angles, eye, buttons, onground, punch, msg, msec=10, playernum=0, seq=0,
              fwd=0.0, side=0.0):
    ref = [0.0] * 58
    ref[0:3] = list(eye)
    assert len(ref) == 58
    ref[3:6] = (view_angles[0], view_angles[1], 0.0)
    ref[15] = 0.01
    ref[16] = t
    ref[20] = onground
    ref[32:35] = (view_angles[0], view_angles[1], 0.0)
    ref[35] = 100
    ref[40:43] = punch
    ref[45] = playernum
    for i in (17, 18, 19, 20, 21, 35, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57):
        ref[i] = int(ref[i])
    info = struct.pack("<f", t) + REF_FMT.pack(*ref)
    info += USERCMD.pack(0, msec, angles[0], angles[1], 0.0, fwd, side, 0.0, 0, buttons, 0, 0, 0, 0.0, 0.0, 0.0)
    info += b"\0" * 132 + b"\0" * 16
    assert len(info) == NETINFO_SIZE
    return struct.pack("<Bfi", kind, t, fr) + info + struct.pack("<7i", seq, seq, 0, 0, seq, 0, 0) + struct.pack("<i", len(msg)) + msg


def frame_event(t, fr, index, entindex, angles):
    return struct.pack("<Bfi", 6, t, fr) + EVENT_FRAME.pack(0, index, 0.0, 0, entindex, 0, 0, 0, angles[0], angles[1], 0,
                                                            0, 0, 0, 0, 0.0, 0.0, 0, 0, 0, 0)


def build_demo(path, aimbot=True, bhop_script=True, silent=False, norecoil=False, speed=False, duplicate=False):
    me, enemy, mate = 3, 5, 4
    load = b"".join([
        msg_serverinfo(me),
        *[msg_deltadesc(n, d) for n, d in DESCS.items()],
        msg_userinfo(me, "Suspeito", "STEAM_0:1:111"),
        msg_userinfo(enemy, "Inimigo", "STEAM_0:0:222"),
        msg_userinfo(mate, "Aliado", "STEAM_0:0:333"),
        msg_newusermsg(70, "DeathMsg", 255),
        msg_newusermsg(71, "TeamInfo", 255),
        msg_newusermsg(72, "CurWeapon", 3),
        msg_resourcelist([(1, "events/ak47.sc"), (2, "events/knife.sc")]),
        msg_spawnbaseline(),
    ])
    seg0 = frame_net(0, 0.0, 0, (0, 0), (0, 0), (0, 0, 0), 0, 1, (0, 0, 0), load, playernum=me - 1) + struct.pack("<Bfi", 5, 0.0, 0)
    frames = []
    t = 0.0
    fr = 0
    eye = (0.0, 0.0, 64.0)
    enemy_pos = [500.0, 0.0, 64.0 - 8.5]  # inimigo a 0 graus
    yaw = 90.0
    pitch = 0.0
    on = 1
    jump_cycle = 0
    kills = 0
    seq = 0
    for i in range(6000):
        t = i * 0.01
        fr += 1
        seq += 1
        parts = [msg_time(t / 1.4 if speed else t), msg_clientdata()]
        if i == 1:
            parts.append(um(71, bytes([me]) + b_string("TERRORIST"), True))
            parts.append(um(71, bytes([enemy]) + b_string("CT"), True))
            parts.append(um(71, bytes([mate]) + b_string("TERRORIST"), True))
            parts.append(um(72, bytes([1, 28, 30])))
        buttons = 0
        view_yaw, view_pitch = yaw, pitch
        punch = (0.0, 0.0, 0.0)
        # ciclos de 3 s: mira longe, flick de 90 graus em 2 frames e disparo
        c = i % 300
        if aimbot:
            if c < 200:
                yaw = 90.0 + 5 * math.sin(i / 20.0)
            elif c in (200, 201):
                yaw = 45.0 if c == 200 else 0.0
            if c in (201, 202):
                buttons |= 1
        else:
            yaw = 90.0 * max(0.0, 1 - (c - 100) / 120.0) if c >= 100 else 90.0
            if c in (240, 241):
                buttons |= 1
        if norecoil and 3000 <= i < 3040:
            buttons |= 1
            punch = (0.0, 0.0, 0.0)
        elif 3000 <= i < 3040:
            buttons |= 1
            punch = (-(i - 3000) * 0.1, 0.0, 0.0)
        if silent and buttons & 1:
            view_yaw = yaw + 8.0
        # bhop
        if bhop_script and 4000 <= i < 5000:
            jump_cycle = (i - 4000) % 40
            on = 1 if jump_cycle == 0 else 0
            if jump_cycle == 0:
                buttons |= 2
        else:
            on = 1
        if c == 210 and aimbot or c == 250 and not aimbot:
            parts.append(um(70, bytes([me, enemy, 1]) + b_string("ak47"), True))
            kills += 1
        if i % 2 == 0:
            parts.append(msg_packetentities({mate: (-300.0, 50.0, 55.5), enemy: tuple(enemy_pos)}))
        msec = 13 if speed else 10
        if duplicate:  # frame extra da demo repetindo o mesmo comando (mesmo outgoing_sequence)
            frames.append(frame_net(1, t, fr, (pitch, yaw), (view_pitch, view_yaw), eye, buttons, on, punch,
                                    msg_time(t), msec=msec, playernum=me - 1, seq=seq))
        frames.append(frame_net(1, t, fr, (pitch, yaw), (view_pitch, view_yaw), eye, buttons, on, punch,
                                b"".join(parts), msec=msec, playernum=me - 1, seq=seq))
        if 3000 <= i < 3040 and i % 4 == 0:
            frames.append(frame_event(t, fr, 1, me, (pitch, view_yaw)))
        if buttons & 1 and (c in (201,) or (not aimbot and c == 240)):
            frames.append(frame_event(t, fr, 1, me, (pitch, view_yaw)))
    seg1 = b"".join(frames) + struct.pack("<Bfi", 5, t, fr)
    off0 = 544
    off1 = off0 + len(seg0)
    dir_off = off1 + len(seg1)
    hdr = b"HLDEMO\0\0" + struct.pack("<ii", 5, 48) + b"de_teste".ljust(260, b"\0") + b"cstrike".ljust(260, b"\0") + struct.pack("<Ii", 0, dir_off)
    d = struct.pack("<i", 2)
    d += struct.pack("<i64siifiii", 0, b"LOADING", 0, 0, 0.0, 1, off0, len(seg0))
    d += struct.pack("<i64siifiii", 1, b"Playback", 0, 0, t, fr, off1, len(seg1))
    with open(path, "wb") as f:
        f.write(hdr + seg0 + seg1 + d)
    return kills


def build_bsp(path):
    """BSP v30 minimo: parede solida entre x=200 e x=300."""
    planes = struct.pack("<4fi", 1, 0, 0, 200, 0) + struct.pack("<4fi", 1, 0, 0, 300, 0)
    # no 0: plano x=200 -> frente: no 1, tras: folha 0 (vazia)
    # no 1: plano x=300 -> frente: folha 0, tras: folha 1 (solida)
    nodes = struct.pack("<ihh6hHH", 0, 1, -1, 0, 0, 0, 0, 0, 0, 0, 0)
    nodes += struct.pack("<ihh6hHH", 1, -1, -2, 0, 0, 0, 0, 0, 0, 0, 0)
    leafs = struct.pack("<ii6hHH4B", -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    leafs += struct.pack("<ii6hHH4B", -2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    models = struct.pack("<9f4i3i", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0)
    lumps = {1: planes, 5: nodes, 10: leafs, 14: models}
    off = 4 + 15 * 8
    hdr = struct.pack("<i", 30)
    body = b""
    for i in range(15):
        data = lumps.get(i, b"")
        hdr += struct.pack("<ii", off + len(body), len(data))
        body += data
    with open(path, "wb") as f:
        f.write(hdr + body)


# ------------------------------------------------------------------ cenarios das funcoes de multihack (ECD)
def msg_event(idx, origin):
    bw = BitWriter()
    bw.write(1, 5); bw.write(idx, 10)
    bw.write(1, 1); bw.write(0, 11)
    bw.write(1, 1)
    write_delta(bw, DESCS["event_t"], {"origin[0]": origin[0], "origin[1]": origin[1], "origin[2]": origin[2]})
    bw.write(0, 1)
    return bytes([3]) + bw.tobytes()


def frame_console(t, fr, cmd):
    return struct.pack("<Bfi", 3, t, fr) + cmd.encode().ljust(64, b"\0")[:64]


def build_ecd_demo(path, strafe=None, duck_script=False, fakelag=False, noflash=False, nosmoke=False, console=False):
    """60 s a 100 fps. strafe: None (humano), "alt" (troca a cada frame) ou "sync" (sincronia perfeita).
    Flash (35 s) e fumaca (42 s) acontecem em todas as variantes; so o cheat mira no inimigo durante elas."""
    me, enemy = 3, 5
    load = b"".join([
        msg_serverinfo(me),
        *[msg_deltadesc(n, d) for n, d in DESCS.items()],
        msg_userinfo(me, "Suspeito", "STEAM_0:1:111"),
        msg_userinfo(enemy, "Inimigo", "STEAM_0:0:222"),
        msg_newusermsg(70, "DeathMsg", 255),
        msg_newusermsg(71, "TeamInfo", 255),
        msg_newusermsg(72, "CurWeapon", 3),
        msg_newusermsg(73, "ScreenFade", 10),
        msg_newusermsg(74, "SayText", 255),
        msg_newusermsg(75, "TextMsg", 255),
        msg_resourcelist([(1, "events/ak47.sc"), (3, "events/createsmoke.sc")]),
        msg_spawnbaseline(),
    ])
    seg0 = frame_net(0, 0.0, 0, (0, 0), (0, 0), (0, 0, 0), 0, 1, (0, 0, 0), load, playernum=me - 1) + struct.pack("<Bfi", 5, 0.0, 0)
    frames = []
    eye = (0.0, 0.0, 64.0)
    seq = 0
    hold = 0
    lag_side = [0.0] * 6
    prev_side = 0.0
    t = 0.0
    fr = 0
    for i in range(6000):
        t = i * 0.01
        fr += 1
        ey = 150.0 * math.sin(t * 1.3)
        epos = (600.0, ey, 47.0)
        parts = [msg_time(t), msg_clientdata()]
        if i == 1:
            parts.append(um(71, bytes([me]) + b_string("TERRORIST"), True))
            parts.append(um(71, bytes([enemy]) + b_string("CT"), True))
            parts.append(um(72, bytes([1, 28, 30])))
        if i % 2 == 0:
            parts.append(msg_packetentities({enemy: epos}))
        if i == 200:   # chat padrao do CS, chat de plugin com cor, mensagem de admin e radio
            parts.append(um(74, bytes([enemy]) + b_string("#Cstrike_Chat_All") + b_string("") + b_string("esse cara ta de wh"), True))
        if i == 300:
            parts.append(um(74, bytes([me]) + b_string("\x04[VIP] \x03Suspeito\x01 : boa tarde"), True))
        if i == 400:
            parts.append(um(75, bytes([3]) + b_string("ADMIN: grava a demo ai"), True))
        if i == 500:
            parts.append(um(75, bytes([5]) + b_string("#Game_radio") + b_string("Inimigo") + b_string("#Fire_in_the_hole"), True))
        yaw, pitch, buttons, on, side = 90.0, 0.0, 0, 1, 0.0
        # 0-20 s: saltos (80 frames: 20 em solo + 60 no ar) com strafe
        if i < 2000:
            c = i % 80
            on = 1 if c < 20 else 0
            if c == 19:
                buttons |= IN_JUMP_BIT
            yaw = 90.0 + 15.0 * math.sin(2 * math.pi * t / 0.4)
            if not on:
                dy = yaw - (90.0 + 15.0 * math.sin(2 * math.pi * (t - 0.01) / 0.4))
                ideal = -400.0 if dy > 0 else 400.0
                if strafe == "alt":
                    side = 400.0 if i % 2 else -400.0
                elif strafe == "sync":
                    side = ideal
                else:   # humano: reage ~6 frames depois, solta a tecla as vezes e passa por 0 ao trocar de lado
                    lag_side.append(ideal if (i // 7) % 5 else 0.0)
                    side = lag_side.pop(0)
                    if side and prev_side and (side > 0) != (prev_side > 0):
                        side = 0.0
            prev_side = side
        # 20-30 s: agachamentos
        elif i < 3000:
            c = (i - 2000) % (11 if duck_script else 16)
            on = 1 if c < (1 if duck_script else 6) else 0
            if c == 0:
                buttons |= IN_DUCK_BIT
        # flash total aos 35 s (hold 3 s) e fumaca aos 42 s
        if i == 3500:
            parts.append(um(73, struct.pack("<HHH", int(0.5 * 4096), int(3.0 * 4096), 0) + bytes([255, 255, 255, 255])))
        if i == 4200:
            parts.append(msg_event(3, (300.0, 0.0, 0.0)))
        tracking = (noflash and (3500 <= i < 3590 or 3620 <= i < 3750)) or \
                   (nosmoke and (4400 <= i < 4550 or 4600 <= i < 4750 or 4800 <= i < 4950))
        if tracking:
            yaw = math.degrees(math.atan2(ey, 600.0))
            pitch = 0.0
        if noflash and i in (3640, 3720):
            parts.append(um(70, bytes([me, enemy, 1]) + b_string("ak47"), True))
        # fake lag: segura 14 frames a cada 30
        if fakelag and i % 30 < 14 and i > 0:
            hold += 1
        else:
            seq += 1
        frames.append(frame_net(1, t, fr, (pitch, yaw), (pitch, yaw), eye, buttons, on, (0.0, 0.0, 0.0),
                                b"".join(parts), playernum=me - 1, seq=seq, side=side))
        if i == 100:
            frames.append(frame_console(t, fr, "hpp_menu" if console else "weapon_ak47"))
    seg1 = b"".join(frames) + struct.pack("<Bfi", 5, t, fr)
    off0 = 544
    off1 = off0 + len(seg0)
    dir_off = off1 + len(seg1)
    hdr = b"HLDEMO\0\0" + struct.pack("<ii", 5, 48) + b"de_teste".ljust(260, b"\0") + b"cstrike".ljust(260, b"\0") + struct.pack("<Ii", 0, dir_off)
    d = struct.pack("<i", 2)
    d += struct.pack("<i64siifiii", 0, b"LOADING", 0, 0, 0.0, 1, off0, len(seg0))
    d += struct.pack("<i64siifiii", 1, b"Playback", 0, 0, t, fr, off1, len(seg1))
    with open(path, "wb") as f:
        f.write(hdr + seg0 + seg1 + d)


IN_JUMP_BIT, IN_DUCK_BIT = 2, 4
