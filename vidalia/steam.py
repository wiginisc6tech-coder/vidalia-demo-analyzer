"""SteamID: conversao entre formatos e links (perfil Steam, historico de scans do ECD)."""
import re

BASE = 76561197960265728          # SteamID64 da conta individual 0 (universo publico)
ECD_LIST = "https://fungun.top/ecd/list/"


def to_id64(sid):
    """SteamID64 (int) de uma conta Steam valida, ou None (LAN, BOT, HLTV, ids de servidor nao-Steam).

    Aceita 76561198..., STEAM_X:Y:Z e [U:1:N]."""
    s = str(sid or "").strip()
    if not s:
        return None
    m = re.fullmatch(r"STEAM_[0-5]:([01]):(\d+)", s, re.I)
    if m:
        return BASE + int(m.group(2)) * 2 + int(m.group(1))
    m = re.fullmatch(r"\[?U:1:(\d+)\]?", s, re.I)
    if m:
        return BASE + int(m.group(1))
    if s.isdigit():
        v = int(s)
        # conta individual, universo publico, instancia desktop: 0x01100001 nos 32 bits altos
        if v >> 32 == 0x01100001 and v > BASE:
            return v
    return None


def to_steam2(sid):
    """Formato STEAM_0:Y:Z (o que o CS 1.6 e o ECD usam), ou None."""
    v = to_id64(sid)
    if v is None:
        return None
    acc = v - BASE
    return "STEAM_0:%d:%d" % (acc & 1, acc >> 1)


def profile_url(sid):
    v = to_id64(sid)
    return "https://steamcommunity.com/profiles/%d" % v if v else None
