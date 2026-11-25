"""Leitor minimo de mapas BSP v30 (GoldSrc) para testes de linha de visao."""
import os
import struct

CONTENTS_SOLID = -2


class BSP:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        ver = struct.unpack_from("<i", data, 0)[0]
        if ver != 30:
            raise ValueError("BSP versao %d nao suportada" % ver)
        lumps = [struct.unpack_from("<ii", data, 4 + 8 * i) for i in range(15)]

        def lump(i):
            o, l = lumps[i]
            return data[o:o + l]

        pl = lump(1)
        self.planes = [struct.unpack_from("<4fi", pl, i) for i in range(0, len(pl) - 19, 20)]
        nd = lump(5)
        self.nodes = [struct.unpack_from("<ihh", nd, i) for i in range(0, len(nd) - 23, 24)]
        lf = lump(10)
        self.leafs = [struct.unpack_from("<i", lf, i)[0] for i in range(0, len(lf) - 27, 28)]
        md = lump(14)
        self.headnode = struct.unpack_from("<i", md, 36)[0]
        self.name = os.path.splitext(os.path.basename(path))[0]

    def _contents(self, node, p):
        while node >= 0:
            n = self.nodes[node]
            a, b, c, d, t = self.planes[n[0]]
            node = n[1] if a * p[0] + b * p[1] + c * p[2] - d >= 0 else n[2]
        return self.leafs[-node - 1]

    def visible(self, p1, p2):
        """True se o segmento p1->p2 nao atravessa solido do mundo (hull 0)."""
        stack = [(self.headnode, p1, p2)]
        while stack:
            node, a, b = stack.pop()
            if node < 0:
                if self.leafs[-node - 1] == CONTENTS_SOLID:
                    return False
                continue
            n = self.nodes[node]
            nx, ny, nz, dist, _ = self.planes[n[0]]
            d1 = nx * a[0] + ny * a[1] + nz * a[2] - dist
            d2 = nx * b[0] + ny * b[1] + nz * b[2] - dist
            if d1 >= 0 and d2 >= 0:
                stack.append((n[1], a, b))
            elif d1 < 0 and d2 < 0:
                stack.append((n[2], a, b))
            else:
                frac = d1 / (d1 - d2)
                mid = (a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac, a[2] + (b[2] - a[2]) * frac)
                near, far = (n[1], n[2]) if d1 >= 0 else (n[2], n[1])
                stack.append((far, mid, b))
                stack.append((near, a, mid))
        return True


def default_map_folders(demo_path=None):
    """Pastas onde o mapa costuma estar quando o usuario nao informa: ao lado da demo (demos ficam
    normalmente na pasta cstrike) e as instalacoes padrao do CS 1.6 (Steam e nao-Steam) no Windows."""
    out = []
    if demo_path:
        d = os.path.dirname(os.path.abspath(demo_path))
        out += [d, os.path.dirname(d)]
    for root in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), "C:\\Program Files (x86)",
                 "C:\\Program Files", "C:\\Games", "D:\\Games", "D:\\SteamLibrary", "E:\\SteamLibrary"):
        if not root:
            continue
        out += [os.path.join(root, "Steam", "steamapps", "common", "Half-Life", "cstrike"),
                os.path.join(root, "steamapps", "common", "Half-Life", "cstrike"),
                os.path.join(root, "Counter-Strike 1.6", "cstrike"),
                os.path.join(root, "Counter-Strike", "cstrike")]
    return out


def find_bsp(map_name, folders):
    for folder in folders:
        if not folder:
            continue
        for cand in (os.path.join(folder, map_name + ".bsp"),
                     os.path.join(folder, "maps", map_name + ".bsp"),
                     os.path.join(folder, "cstrike", "maps", map_name + ".bsp")):
            if os.path.isfile(cand):
                return cand
    return None
