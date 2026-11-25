"""Decodificador das mensagens de rede svc_* do GoldSrc (protocolo 48).

Mantem o estado do jogo (jogadores, entidades, descricoes delta, user messages)
e emite eventos de alto nivel (mortes, arma atual, times, etc.).
"""
import struct
from collections import Counter

from .bitreader import BitReader, ByteReader, ParseError
from .delta import read_delta, read_description

SVC_NAMES = {
    0: "svc_bad", 1: "svc_nop", 2: "svc_disconnect", 3: "svc_event", 4: "svc_version",
    5: "svc_setview", 6: "svc_sound", 7: "svc_time", 8: "svc_print", 9: "svc_stufftext",
    10: "svc_setangle", 11: "svc_serverinfo", 12: "svc_lightstyle", 13: "svc_updateuserinfo",
    14: "svc_deltadescription", 15: "svc_clientdata", 16: "svc_stopsound", 17: "svc_pings",
    18: "svc_particle", 19: "svc_damage", 20: "svc_spawnstatic", 21: "svc_event_reliable",
    22: "svc_spawnbaseline", 23: "svc_tempentity", 24: "svc_setpause", 25: "svc_signonnum",
    26: "svc_centerprint", 27: "svc_killedmonster", 28: "svc_foundsecret",
    29: "svc_spawnstaticsound", 30: "svc_intermission", 31: "svc_finale", 32: "svc_cdtrack",
    33: "svc_restore", 34: "svc_cutscene", 35: "svc_weaponanim", 36: "svc_decalname",
    37: "svc_roomtype", 38: "svc_addangle", 39: "svc_newusermsg", 40: "svc_packetentities",
    41: "svc_deltapacketentities", 42: "svc_choke", 43: "svc_resourcelist",
    44: "svc_newmovevars", 45: "svc_resourcerequest", 46: "svc_customization",
    47: "svc_crosshairangle", 48: "svc_soundfade", 49: "svc_filetxferfailed", 50: "svc_hltv",
    51: "svc_director", 52: "svc_voiceinit", 53: "svc_voicedata", 54: "svc_sendextrainfo",
    55: "svc_timescale", 56: "svc_resourcelocation", 57: "svc_sendcvarvalue",
    58: "svc_sendcvarvalue2",
}

# Tamanho fixo (bytes apos o tipo) das svc_tempentity mais comuns.
TE_SIZES = {
    0: 24, 1: 20, 2: 6, 3: 11, 4: 6, 5: 10, 6: 12, 7: 17, 8: 16, 9: 6, 10: 6, 11: 6,
    12: 8, 14: 9, 15: 19, 17: 10, 18: 16, 19: 24, 20: 24, 21: 24, 22: 10, 23: 11, 24: 16,
    25: 19, 27: 12, 28: 16, 30: 17, 31: 17, 99: 2, 100: 10, 101: 14, 102: 12, 103: 14,
    104: 9, 105: 5, 106: 17, 107: 13, 108: 24, 109: 9, 110: 17, 111: 7, 112: 10, 113: 19,
    114: 19, 115: 12, 116: 7, 117: 7, 118: 9, 119: 16, 120: 18, 121: 5, 122: 10, 123: 9,
    124: 7, 125: 1, 126: 18, 127: 15,
}

CS_WEAPONS = {
    1: "p228", 3: "scout", 4: "hegrenade", 5: "xm1014", 6: "c4", 7: "mac10", 8: "aug",
    9: "smokegrenade", 10: "elite", 11: "fiveseven", 12: "ump45", 13: "sg550", 14: "galil",
    15: "famas", 16: "usp", 17: "glock18", 18: "awp", 19: "mp5navy", 20: "m249", 21: "m3",
    22: "m4a1", 23: "tmp", 24: "g3sg1", 25: "flashbang", 26: "deagle", 27: "sg552",
    28: "ak47", 29: "knife", 30: "p90",
}


def parse_userinfo(s):
    parts = s.split("\\")
    if parts and parts[0] == "":
        parts = parts[1:]
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


# ------------------------------------------------------------------ chat
CHAT_FORMATS = {
    "#Cstrike_Chat_All": "todos", "#Cstrike_Chat_AllDead": "morto", "#Cstrike_Chat_AllSpec": "espectador",
    "#Cstrike_Chat_T": "time", "#Cstrike_Chat_CT": "time", "#Cstrike_Chat_T_Dead": "morto",
    "#Cstrike_Chat_CT_Dead": "morto", "#Cstrike_Chat_Spec": "espectador",
}
RADIO = {
    "#Cover_me": "Me dê cobertura!", "#You_take_the_point": "Assuma a frente.", "#Hold_this_position": "Segure essa posição.",
    "#Regroup_team": "Reagrupar, time.", "#Follow_me": "Siga-me.", "#Taking_fire": "Estou sob fogo, preciso de ajuda!",
    "#Go_go_go": "Vai, vai, vai!", "#Team_fall_back": "Time, recuar!", "#Stick_together_team": "Fiquem juntos, time.",
    "#Get_in_position_and_wait": "Posicionem-se e aguardem.", "#Storm_the_front": "Avançar pela frente!",
    "#Report_in_team": "Time, reportem.", "#Affirmative": "Afirmativo.", "#Roger_that": "Entendido.",
    "#Enemy_spotted": "Inimigo avistado.", "#Need_backup": "Preciso de reforço.", "#Sector_clear": "Setor limpo.",
    "#In_position": "Em posição.", "#Reporting_in": "Reportando.", "#Get_out_of_there": "Saiam daí, vai explodir!",
    "#Negative": "Negativo.", "#Enemy_down": "Inimigo abatido.", "#Fire_in_the_hole": "Granada!",
}
GAME_MSGS = {
    "#Game_teammate_attack": "Atacou um companheiro de time", "#Killed_Teammate": "Matou um companheiro de time!",
    "#Game_join_terrorist": "Entrou nos Terroristas", "#Game_join_ct": "Entrou nos Contra-Terroristas",
    "#Game_scoring": "Placar", "#Game_connected": "Conectou", "#Game_disconnected": "Desconectou",
    "#Cannot_Be_Spectator": "Não pode ser espectador",
}


def _chat_str(b):
    """String terminada em zero; tenta UTF-8 e cai para cp1251 (servidores russos antigos)."""
    i = b.data.find(b"\0", b.pos, b.end)
    raw = b.data[b.pos:(i if i >= 0 else b.end)]
    b.pos = (i + 1) if i >= 0 else b.end
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1251", "replace")


def _clean(s):
    """Remove codigos de cor (\\x01-\\x04), quebras de linha e espacos extras."""
    s = "".join(ch for ch in s if ch >= " " or ch == "\t")
    return " ".join(s.split())


class GameState:
    def __init__(self):
        self.maxclients = 32
        self.playernum = None          # indice de entidade (1..maxclients) do gravador
        self.server = {}
        self.deltas = {}               # nome -> [Field]
        self.usermsgs = {}             # id -> (nome, tamanho)
        self.resources = {}            # (tipo, indice) -> nome
        self.event_names = {}          # indice de evento -> nome (events/ak47.sc)
        self.players = {}              # slot(1..) -> dict(name, steamid, team, userid)
        self.baselines = {}
        self.instanced_baselines = 0
        self.entities = {}             # numero -> estado atual
        self.frames = {}               # seq & 255 -> snapshot de entidades
        self.clientdata = {}
        self.weapon_id = None
        self.time = 0.0


class NetDecoder:
    """Decodifica o buffer de mensagens de cada frame de rede."""

    def __init__(self, state=None):
        self.st = state or GameState()
        self.counts = Counter()
        self.unknown = Counter()
        self.errors = Counter()
        self.packets = 0
        self.packets_ok = 0
        self.events = []      # eventos de alto nivel gerados
        self.cur_time = 0.0
        self.cur_seq = 0

    # ------------------------------------------------------------------ API
    def feed(self, msg, demo_time, incoming_sequence=0):
        self.cur_time = demo_time
        self.cur_seq = incoming_sequence
        if not msg:
            return True
        self.packets += 1
        r = ByteReader(msg)
        while r.remaining() > 0:
            start = r.pos
            svc = r.u8()
            try:
                if svc >= 64:
                    self._usermsg(svc, r)
                else:
                    h = self.HANDLERS.get(svc)
                    if h is None:
                        self.unknown[svc] += 1
                        return False
                    h(self, r)
                self.counts[SVC_NAMES.get(svc) or self._umname(svc)] += 1
            except (ParseError, struct.error, KeyError, IndexError, ValueError) as e:
                name = SVC_NAMES.get(svc) or self._umname(svc)
                self.errors["%s: %s" % (name, str(e)[:80])] += 1
                return False
        self.packets_ok += 1
        if self.cur_seq is not None:
            self.st.frames[self.cur_seq & 255] = self.st.entities
        return True

    def _umname(self, svc):
        um = self.st.usermsgs.get(svc)
        return um[0] if um else "usermsg_%d" % svc

    def _emit(self, kind, **kw):
        kw["tipo"] = kind
        kw["tempo"] = round(self.cur_time, 4)
        self.events.append(kw)

    # ------------------------------------------------------- mensagens simples
    def _nop(self, r): pass
    def _string(self, r): r.string()
    def _long(self, r): r.skip(4)
    def _short(self, r): r.skip(2)
    def _byte(self, r): r.skip(1)

    def _time(self, r):
        self.st.time = r.f32()

    def _print(self, r):
        s = r.string()
        self._emit("print", texto=s.strip())

    def _stufftext(self, r):
        s = r.string()
        self._emit("stufftext", texto=s.strip())

    def _setangle(self, r):
        a = [r.s16() * (360.0 / 65536.0) for _ in range(3)]
        self._emit("setangle", angulos=a)

    def _serverinfo(self, r):
        proto = r.s32()
        spawncount = r.s32()
        crc = r.s32()
        r.skip(16)
        maxc = r.u8()
        pnum = r.u8()
        r.u8()
        gamedir = r.string()
        host = r.string()
        mapn = r.string()
        r.string()  # mapcycle
        r.u8()      # VAC / extra
        self.st.maxclients = maxc
        self.st.playernum = pnum + 1
        self.st.server = dict(protocolo=proto, spawncount=spawncount, maxclients=maxc,
                              jogador_gravador=pnum + 1, gamedir=gamedir, servidor=host, mapa=mapn)
        self._emit("serverinfo", **self.st.server)

    def _lightstyle(self, r):
        r.u8(); r.string()

    def _updateuserinfo(self, r):
        slot = r.u8()
        uid = r.s32()
        info = parse_userinfo(r.string())
        r.skip(16)
        p = self.st.players.setdefault(slot + 1, {})
        if info:
            p.update(userid=uid, nome=info.get("name", p.get("nome", "")),
                     steamid=info.get("*sid", p.get("steamid", "")),
                     modelo=info.get("model", ""), hltv=info.get("*hltv", ""))
            self._emit("userinfo", slot=slot + 1, nome=p["nome"], steamid=p["steamid"])

    def _deltadescription(self, r):
        name = r.string()
        n = r.u16()
        br = BitReader(r.data, r.pos, r.end)
        self.st.deltas[name] = read_description(br, n)
        r.pos = br.byte_pos()

    def _bits_begin(self, r):
        return BitReader(r.data, r.pos, r.end)

    def _clientdata(self, r):
        br = self._bits_begin(r)
        if br.read(1):
            br.read(8)
        d = self.st.deltas.get("clientdata_t")
        if d is None:
            raise ParseError("clientdata_t ainda nao recebido")
        self.st.clientdata = read_delta(br, d, self.st.clientdata)
        wd = self.st.deltas.get("weapon_data_t")
        while br.read(1):
            br.read(6)
            read_delta(br, wd)
        r.pos = br.byte_pos()

    def _pings(self, r):
        br = self._bits_begin(r)
        while br.read(1):
            br.read(5); br.read(12); br.read(7)
        r.pos = br.byte_pos()

    def _particle(self, r): r.skip(11)

    def _spawnstatic(self, r):
        r.skip(2 + 1 + 1 + 2 + 1 + 9)
        if r.u8():
            r.skip(5)

    def _event(self, r):
        br = self._bits_begin(r)
        n = br.read(5)
        d = self.st.deltas.get("event_t")
        for _ in range(n):
            idx = br.read(10)
            args = None
            if br.read(1):
                br.read(11)
                if br.read(1):
                    args = read_delta(br, d)
            if br.read(1):
                br.read(16)
            self._net_event(idx, args)
        r.pos = br.byte_pos()

    def _event_reliable(self, r):
        br = self._bits_begin(r)
        idx = br.read(10)
        args = read_delta(br, self.st.deltas.get("event_t"))
        if br.read(1):
            br.read(16)
        self._net_event(idx, args)
        r.pos = br.byte_pos()

    def _net_event(self, idx, args):
        name = self.st.event_names.get(idx, "")
        if args is not None and "createsmoke" in name.lower():
            org = (args.get("origin[0]", 0.0), args.get("origin[1]", 0.0), args.get("origin[2]", 0.0))
            if any(org):
                self._emit("fumaca", origem=tuple(float(v) for v in org))
        if args is not None and args.get("entindex"):
            self._emit("evento_rede", indice=idx, nome=name, entidade=int(args.get("entindex", 0)))

    def _sound(self, r):
        br = self._bits_begin(r)
        fl = br.read(9)
        if fl & 1: br.read(8)
        if fl & 2: br.read(8)
        br.read(3)
        br.read(11)
        br.read(16 if fl & 4 else 8)
        br.vec3coord()
        if fl & 8: br.read(8)
        r.pos = br.byte_pos()

    def _spawnbaseline(self, r):
        br = self._bits_begin(r)
        st = self.st
        while True:
            idx = br.read(11)
            if idx == (1 << 11) - 1:
                break
            typ = br.read(2)
            if typ & 1:
                name = "entity_state_player_t" if 0 < idx <= st.maxclients else "entity_state_t"
            else:
                name = "custom_entity_state_t"
            st.baselines[idx] = read_delta(br, st.deltas[name])
        br.read(5)
        st.instanced_baselines = br.read(6)
        for _ in range(st.instanced_baselines):
            read_delta(br, st.deltas["entity_state_t"])
        r.pos = br.byte_pos()

    def _tempentity(self, r):
        t = r.u8()
        if t == 13:  # TE_BSPDECAL
            r.skip(8)
            if r.s16():
                r.skip(2)
        elif t == 29:  # TE_TEXTMESSAGE
            r.skip(5)
            eff = r.u8()
            r.skip(14)
            if eff == 2:
                r.skip(2)
            r.string()
        elif t in TE_SIZES:
            r.skip(TE_SIZES[t])
        else:
            raise ParseError("tempentity desconhecida %d" % t)

    def _spawnstaticsound(self, r): r.skip(14)
    def _cdtrack(self, r): r.skip(2)

    def _restore(self, r):
        r.string()
        for _ in range(r.u8()):
            r.string()

    def _decalname(self, r):
        r.u8(); r.string()

    def _newusermsg(self, r):
        idx = r.u8()
        size = r.u8()
        name = r.raw(16).split(b"\0", 1)[0].decode("latin-1")
        self.st.usermsgs[idx] = (name, 255 if size == 255 else size)

    def _packetentities(self, r, delta=False):
        st = self.st
        br = self._bits_begin(r)
        br.read(16)  # quantidade de entidades
        if delta:
            dseq = br.read(8)
            old = st.frames.get(dseq, st.entities)
            new = dict(old)
        else:
            old = {}
            new = {}
        num = 0
        decoded = []
        while True:
            if br.peek(16) == 0:
                br.read(16)
                break
            if delta:
                remove = br.read(1)
                if br.read(1):
                    num = br.read(11)
                else:
                    num += br.read(6)
            else:
                remove = 0
                if br.read(1):
                    num += 1
                elif br.read(1):
                    num = br.read(11)
                else:
                    num += br.read(6)
            if remove:
                new.pop(num, None)
                continue
            custom = br.read(1)
            base = None
            if st.instanced_baselines:
                if br.read(1):
                    br.read(6)
            if not delta:
                if br.read(1):
                    off = br.read(6)
                    if 0 < off <= len(decoded):
                        base = decoded[-off]
            if 0 < num <= st.maxclients:
                dname = "entity_state_player_t"
            elif custom:
                dname = "custom_entity_state_t"
            else:
                dname = "entity_state_t"
            if base is None:
                base = old.get(num) if delta and num in old else st.baselines.get(num)
            ent = read_delta(br, st.deltas[dname], base)
            new[num] = ent
            decoded.append(ent)
        st.entities = new
        r.pos = br.byte_pos()
        self._player_positions()

    def _deltapacketentities(self, r):
        self._packetentities(r, delta=True)

    def _player_positions(self):
        st = self.st
        pos = {}
        for num, e in st.entities.items():
            if 0 < num <= st.maxclients and "origin[0]" in e:
                pos[num] = (e.get("origin[0]", 0.0), e.get("origin[1]", 0.0), e.get("origin[2]", 0.0))
        self.player_pos = pos

    def _resourcelist(self, r):
        br = self._bits_begin(r)
        n = br.read(12)
        for _ in range(n):
            typ = br.read(4)
            name = br.string()
            idx = br.read(12)
            br.read(24)
            fl = br.read(3)
            if fl & 4:
                for _ in range(16):
                    br.read(8)
            if br.read(1):
                for _ in range(32):
                    br.read(8)
            self.st.resources[(typ, idx)] = name
            if typ == 5:  # t_eventscript
                self.st.event_names[idx] = name
        if br.read(1):
            while br.read(1):
                if br.read(1):
                    br.read(5)
                else:
                    br.read(10)
        r.pos = br.byte_pos()

    def _newmovevars(self, r):
        r.skip(64 + 1 + 32)
        r.string()

    def _resourcerequest(self, r): r.skip(8)

    def _customization(self, r):
        r.u8(); r.u8(); r.string(); r.u16(); r.s32()
        if r.u8() & 4:
            r.skip(16)

    def _hltv(self, r):
        if r.u8() == 2:
            r.skip(8)

    def _director(self, r):
        r.skip(r.u8())

    def _voiceinit(self, r):
        r.string(); r.u8()

    def _voicedata(self, r):
        r.u8()
        r.skip(r.u16())

    def _sendextrainfo(self, r):
        r.string(); r.u8()

    def _sendcvarvalue2(self, r):
        r.skip(4); r.string()

    # ---------------------------------------------------------- user messages
    def _usermsg(self, svc, r):
        um = self.st.usermsgs.get(svc)
        if um is None:
            raise ParseError("user message %d nao registrada" % svc)
        name, size = um
        if size == 255:
            size = r.u8()
        body = ByteReader(r.raw(size))
        h = self.USERMSG_HANDLERS.get(name)
        if h:
            try:
                h(self, body)
            except ParseError:
                pass

    def _um_deathmsg(self, b):
        killer = b.u8(); victim = b.u8(); hs = b.u8()
        weapon = b.string() if b.remaining() else ""
        self._emit("morte", matador=killer, vitima=victim, headshot=bool(hs), arma=weapon)

    def _um_curweapon(self, b):
        active = b.u8(); wid = b.u8(); clip = b.s8()
        if active and wid:
            if wid != self.st.weapon_id:
                self._emit("arma", id=wid, arma=CS_WEAPONS.get(wid, str(wid)))
            self.st.weapon_id = wid

    def _um_teaminfo(self, b):
        idx = b.u8(); team = b.string()
        p = self.st.players.setdefault(idx, {})
        if p.get("time") != team:
            p["time"] = team
            self._emit("time", jogador=idx, time=team)

    def _um_scoreinfo(self, b):
        idx = b.u8(); frags = b.s16(); deaths = b.s16()
        p = self.st.players.setdefault(idx, {})
        p["frags"] = frags; p["mortes"] = deaths

    def _um_damage(self, b):
        armor = b.u8(); dmg = b.u8()
        self._emit("dano_recebido", dano=dmg, armadura=armor)

    def _um_textmsg(self, b):
        dest = b.u8()
        s = _chat_str(b)
        if s.startswith("#") and ("Win" in s or "Round_Draw" in s or "Game_Commencing" in s or "Restart" in s):
            self._emit("fim_round", texto=s)
        params = []
        while b.remaining() > 0 and len(params) < 4:
            params.append(_chat_str(b))
        if s == "#Game_radio" and len(params) >= 2:      # radio: (nome) "#Fire_in_the_hole"
            self._emit("chat", categoria="radio", remetente=0, nome=_clean(params[0]),
                       texto=RADIO.get(params[1], params[1].lstrip("#").replace("_", " ")))
        elif dest == 3 and s:                             # HUD_PRINTTALK: mensagens de chat do servidor/admin/plugins
            if s.startswith("#"):
                txt = GAME_MSGS.get(s, s.lstrip("#").replace("_", " "))
                if params:
                    txt += " (" + ", ".join(_clean(x) for x in params if x) + ")"
                self._emit("chat", categoria="jogo", remetente=0, nome="", texto=txt)
            else:
                txt = _clean(s)
                for k, v in enumerate(params, 1):
                    txt = txt.replace("%%s%d" % k, _clean(v))
                self._emit("chat", categoria="servidor", remetente=0, nome="", texto=txt)

    def _um_saytext(self, b):
        sender = b.u8()
        fmt = _chat_str(b)
        params = []
        while b.remaining() > 0 and len(params) < 3:
            params.append(_chat_str(b))
        p = self.st.players.get(sender) or {}
        nome = p.get("nome", "")
        if fmt.startswith("#Cstrike_Name_Change") and len(params) >= 2:
            self._emit("chat", categoria="nome", remetente=sender, nome=_clean(params[0]),
                       texto="mudou o nome para %s" % _clean(params[1]))
            return
        if fmt.startswith("#Cstrike_Chat"):
            cat = CHAT_FORMATS.get(fmt, "todos")
            msg = params[1] if len(params) >= 2 else (params[0] if params else "")
            if len(params) >= 2 and params[0]:
                nome = _clean(params[0]) or nome
            self._emit("chat", categoria=cat, remetente=sender, nome=nome, texto=_clean(msg))
            return
        if fmt.startswith("#"):
            return   # textos internos do HUD (ex.: #Spec_PlayerItem)
        # formato livre (plugins AMXX / ColorChat): "[VIP][Patente] Nome : mensagem", radio ou anuncio do servidor
        txt = _clean(fmt)
        low = txt.lower()
        for mark in ("(radio)", "(\u0440\u0430\u0434\u0438\u043e)"):
            k = low.find(mark)
            if k >= 0:
                body = txt[k + len(mark):].lstrip(" :")
                self._emit("chat", categoria="radio", remetente=0, nome=txt[:k].strip(), texto=body or txt)
                return
        nm = _clean(nome)
        idx = txt.find(nm) if (sender and nm) else -1
        rest = txt[idx + len(nm):] if idx >= 0 else ""
        if not (idx >= 0 and ":" in rest[:40]):
            # plugins de chat (patentes, VIP...) podem mandar o remetente errado: procura o nome de
            # qualquer jogador conhecido logo antes do ":" ("[VIP][Patente] Nome : mensagem")
            sep = txt.find(" : ")
            sep = sep if sep >= 0 else txt.find(": ")
            head = txt[:sep] if sep > 0 else ""
            best = None
            for num, pl in self.st.players.items():
                cand = _clean(pl.get("nome", ""))
                if len(cand) >= 2 and head.endswith(cand) and (best is None or len(cand) > len(best[1])):
                    best = (num, cand)
            if best:
                sender, nm = best
                idx = len(head) - len(nm)
                rest = txt[idx + len(nm):]
        if idx >= 0 and ":" in rest[:40]:
            prefix = txt[:idx].lower()
            msg = rest.split(":", 1)[1].strip()
            if any(k in prefix for k in ("dead", "\u043c\u0435\u0440\u0442\u0432", "morto", "\u0442\u0440\u0443\u043f")):
                cat = "morto"
            elif any(k in prefix for k in ("team", "(t)", "(ct)", "time", "terror", "counter", "\u043a\u043e\u043c\u0430\u043d\u0434",
                                           "\u0442\u0435\u0440\u0440\u043e\u0440", "\u0441\u043f\u0435\u0446\u043d\u0430\u0437")):
                cat = "time"
            elif "spec" in prefix:
                cat = "espectador"
            else:
                cat = "todos"
            self._emit("chat", categoria=cat, remetente=sender, nome=nm, texto=msg)
            return
        self._emit("chat", categoria="servidor", remetente=0, nome="", texto=txt)

    def _um_resethud(self, b):
        self._emit("inicio_round")

    def _um_screenfade(self, b):
        # duracao e hold em segundos * 4096 (ponto fixo 4.12); flashbang = branco com alfa alto
        dur = b.u16() / 4096.0; hold = b.u16() / 4096.0; flags = b.u16()
        r, g, bl, a = b.u8(), b.u8(), b.u8(), b.u8()
        # flags: 0x1 = FFADE_OUT (escurecendo), 0x2 = FFADE_MODULATE; a flashbang usa FFADE_IN (0)
        if flags & 0x0003 == 0 and r >= 240 and g >= 240 and bl >= 240 and a >= 200:
            self._emit("flash", duracao=round(dur, 3), hold=round(hold, 3), alfa=a)

    HANDLERS = {
        0: _nop, 1: _nop, 2: _string, 3: _event, 4: _long, 5: _short, 6: _sound, 7: _time,
        8: _print, 9: _stufftext, 10: _setangle, 11: _serverinfo, 12: _lightstyle,
        13: _updateuserinfo, 14: _deltadescription, 15: _clientdata, 16: _short, 17: _pings,
        18: _particle, 20: _spawnstatic, 21: _event_reliable, 22: _spawnbaseline,
        23: _tempentity, 24: _byte, 25: _byte, 26: _string, 27: _nop, 28: _nop,
        29: _spawnstaticsound, 30: _nop, 31: _string, 32: _cdtrack, 33: _restore,
        34: _string, 35: _cdtrack, 36: _decalname, 37: _short, 38: _short, 39: _newusermsg,
        40: _packetentities, 41: _deltapacketentities, 42: _nop, 43: _resourcelist,
        44: _newmovevars, 45: _resourcerequest, 46: _customization, 47: _cdtrack,
        48: _long, 49: _string, 50: _hltv, 51: _director, 52: _voiceinit, 53: _voicedata,
        54: _sendextrainfo, 55: _long, 56: _string, 57: _string, 58: _sendcvarvalue2,
    }

    USERMSG_HANDLERS = {
        "DeathMsg": _um_deathmsg, "CurWeapon": _um_curweapon, "TeamInfo": _um_teaminfo,
        "ScoreInfo": _um_scoreinfo, "Damage": _um_damage, "TextMsg": _um_textmsg,
        "ResetHUD": _um_resethud, "ScreenFade": _um_screenfade, "SayText": _um_saytext,
    }
