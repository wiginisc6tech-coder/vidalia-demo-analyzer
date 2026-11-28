"""Player dos momentos apontados (aba "Momentos").

Reconstroi a cena a partir dos dados da demo, sem o jogo: visao do jogador em 3D simples (paredes do
.bsp + caixas dos jogadores), radar visto de cima e grafico da mira, com controle quadro a quadro.
Nao e a imagem real do jogo: e um desenho dos dados que a demo guarda.
"""
import bisect
import math
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import game
from .bsp import BSP, load_geometry
from .engine import angle_between, angles_to, wrap180
from .i18n import T, detector, status

BG = "#0b0a12"
SURF = "#14121e"
SURF2 = "#1d1a2b"
BORDER = "#2b2640"
FG = "#ece9f5"
MUT = "#8f89a6"
PURPLE = "#a855f7"
GREEN = "#a3e635"
AMBER = "#f59e0b"
RED = "#f43f5e"
BLUE = "#38bdf8"

NEAR = 2.0
VIEW_DIST = 2600.0     # alcance do desenho das paredes
HEAD_Z = 17.0          # olho acima da origem do jogador
SPEEDS = (0.1, 0.25, 0.5, 1.0, 2.0)
FFMPEG_URL = "https://ffmpeg.org/download.html"

# gravacao em andamento (uma por vez, compartilhada entre a aba e a janela ampliada)
_REC = {"busy": False, "cancel": False}

# ---------------------------------------------------------------- cache de mapas (compartilhado entre janelas)
_MAPS = {}
_MAPS_LOCK = threading.Lock()


def get_map(path):
    """(Geometry, BSP) do caminho, com cache. (None, None) se nao der para ler."""
    if not path:
        return None, None
    with _MAPS_LOCK:
        if path not in _MAPS:
            try:
                _MAPS[path] = (load_geometry(path), BSP(path))
            except Exception:  # noqa: BLE001
                _MAPS[path] = (None, None)
        return _MAPS[path]


# ---------------------------------------------------------------- matematica da camera
def basis(pitch, yaw):
    p, y = math.radians(pitch), math.radians(yaw)
    cp, sp, cy, sy = math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    f = (cp * cy, cp * sy, -sp)
    r = (sy, -cy, 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    return f, r, u


def _mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    t = max(0.0, min(1.0, t))
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _shade(rgb, k):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c * k))) for c in rgb)


WALL = (150, 142, 176)
FLOOR = (104, 92, 78)
CEIL = (70, 66, 88)
WATER = (60, 110, 160)
FOG = (11, 10, 18)
LIGHT = (0.45, 0.3, 0.84)


class Camera:
    def __init__(self, eye, pitch, yaw, w, h, fov=90.0):
        self.eye = eye
        self.f, self.r, self.u = basis(pitch, yaw)
        self.w, self.h = w, h
        self.focal = (w / 2.0) / math.tan(math.radians(fov) / 2.0)

    def to_cam(self, p):
        d0, d1, d2 = p[0] - self.eye[0], p[1] - self.eye[1], p[2] - self.eye[2]
        f, r, u = self.f, self.r, self.u
        return (d0 * r[0] + d1 * r[1] + d2 * r[2], d0 * u[0] + d1 * u[1] + d2 * u[2],
                d0 * f[0] + d1 * f[1] + d2 * f[2])

    def proj(self, c):
        return (self.w / 2.0 + c[0] / c[2] * self.focal, self.h / 2.0 - c[1] / c[2] * self.focal)

    def point(self, p):
        c = self.to_cam(p)
        if c[2] < NEAR:
            return None
        return self.proj(c)

    def direction(self, pitch, yaw):
        f, _, _ = basis(pitch, yaw)
        return self.point((self.eye[0] + f[0] * 4000, self.eye[1] + f[1] * 4000, self.eye[2] + f[2] * 4000))


def clip_near(cs):
    out = []
    n = len(cs)
    for k in range(n):
        a, b = cs[k], cs[(k + 1) % n]
        ia, ib = a[2] >= NEAR, b[2] >= NEAR
        if ia:
            out.append(a)
        if ia != ib:
            t = (NEAR - a[2]) / (b[2] - a[2])
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, NEAR))
    return out


# ---------------------------------------------------------------- o player
class ReplayViewer(tk.Frame):
    """Visao do jogador + radar + grafico da mira de um Momento."""

    def __init__(self, parent, font, on_expand=None, big=False):
        super().__init__(parent, bg=SURF)
        self.F = font
        self.rp = None
        self.m = None
        self.qs = []
        self.ts = []
        self.k = 0
        self.playing = False
        self.speed = tk.StringVar(value="0.5x")
        self.loop = tk.BooleanVar(value=True)
        self.stop_at = tk.BooleanVar(value=True)
        self._stopped_at_target = False
        self._last = None
        self._job = None
        self._los = {}
        self._walls2d = None
        self.geo = self.bsp = None
        self.on_expand = on_expand
        self.big = big
        self.mode = tk.StringVar(value="rec")
        self.video = None
        self._imgs = {}
        self._q = queue.Queue()
        self._build()
        self.after(150, self._poll)

    # ------------------------------------------------------------ interface
    def _build(self):
        F = self.F
        head = tk.Frame(self, bg=SURF)
        head.pack(fill="x", padx=10, pady=(8, 4))
        self.title = tk.Label(head, text=T("mv_pick"), bg=SURF, fg=FG, font=(F, 11, "bold"), anchor="w",
                              justify="left")
        self.title.pack(side="left", fill="x", expand=True)
        if self.on_expand:
            ttk.Button(head, text=T("mv_expand"), style="Ghost.TButton", command=self.on_expand).pack(side="right")
        self.desc = tk.Label(self, text="", bg=SURF, fg=MUT, font=(F, 9), anchor="w", justify="left")
        self.desc.pack(fill="x", padx=10)
        self.desc.bind("<Configure>", lambda e: self.desc.configure(wraplength=max(200, e.width - 10)))

        gbar = tk.Frame(self, bg=SURF)
        gbar.pack(fill="x", padx=10, pady=(6, 0))
        self.btn_watch = ttk.Button(gbar, text=T("mv_watch"), style="Ghost.TButton", command=self.watch_game)
        self.btn_watch.pack(side="left")
        self.btn_rec = ttk.Button(gbar, text=T("mv_record"), style="Danger.TButton", command=self.record_video)
        self.btn_rec.pack(side="left", padx=(6, 0))
        self.mode_box = tk.Frame(gbar, bg=SURF)
        for val, key in (("rec", "mv_mode_rec"), ("video", "mv_mode_video")):
            tk.Radiobutton(self.mode_box, text=T(key), value=val, variable=self.mode, command=self.draw, bg=SURF,
                           fg=FG, selectcolor=SURF2, activebackground=SURF, activeforeground=FG,
                           highlightthickness=0, font=(F, 9, "bold")).pack(side="left", padx=(8, 0))
        self.btn_export = ttk.Button(self.mode_box, text=T("mv_export"), style="Purple.TButton",
                                     command=self.export_dialog)
        self.btn_export.pack(side="left", padx=(10, 0))
        self.btn_mp4 = ttk.Button(self.mode_box, text=T("mv_open_mp4"), style="Ghost.TButton", command=self.open_mp4)
        self.game_lbl = tk.Label(gbar, text="", bg=SURF, fg=AMBER, font=(F, 9), anchor="w")
        self.game_lbl.pack(side="left", fill="x", expand=True, padx=(10, 0))

        tk.Label(self, text=T("mv_note"), bg=SURF, fg=MUT, font=(F, 8), anchor="w").pack(side="bottom", fill="x",
                                                                         padx=10, pady=(0, 6))
        ctl = tk.Frame(self, bg=SURF)
        ctl.pack(side="bottom", fill="x", padx=10, pady=6)
        b = dict(style="Ghost.TButton")
        ttk.Button(ctl, text="⏮", width=3, command=self.to_start, **b).pack(side="left")
        ttk.Button(ctl, text="◀", width=3, command=lambda: self.step(-1), **b).pack(side="left", padx=(4, 0))
        self.btn_play = ttk.Button(ctl, text="▶", width=4, command=self.toggle, style="Accent.TButton")
        self.btn_play.pack(side="left", padx=(4, 0))
        ttk.Button(ctl, text="▶|", width=3, command=lambda: self.step(1), **b).pack(side="left", padx=(4, 0))
        ttk.Button(ctl, text=T("mv_goto"), command=self.to_target, style="Purple.TButton").pack(side="left",
                                                                                              padx=(10, 0))
        tk.Label(ctl, text=T("mv_speed"), bg=SURF, fg=MUT, font=(F, 9)).pack(side="left", padx=(14, 4))
        ttk.Combobox(ctl, textvariable=self.speed, values=["%gx" % s for s in SPEEDS], state="readonly", width=6,
                     style="Dark.TCombobox").pack(side="left")
        for var, key in ((self.stop_at, "mv_stop_at"), (self.loop, "mv_loop")):
            tk.Checkbutton(ctl, text=T(key), variable=var, bg=SURF, fg=FG, selectcolor=SURF2, activebackground=SURF,
                           activeforeground=FG, highlightthickness=0, font=(F, 9)).pack(side="left", padx=(10, 0))
        self.pos_lbl = tk.Label(ctl, text="", bg=SURF, fg=GREEN, font=(F, 10, "bold"))
        self.pos_lbl.pack(side="right")
        self.graph = tk.Canvas(self, bg=BG, highlightthickness=1, highlightbackground=BORDER, bd=0,
                               height=110 if self.big else 78)
        self.graph.pack(side="bottom", fill="x", padx=10, pady=(6, 0))

        mid = tk.Frame(self, bg=SURF)
        mid.pack(fill="both", expand=True, padx=10, pady=(6, 0))
        self.view = tk.Canvas(mid, bg=BG, highlightthickness=1, highlightbackground=BORDER, bd=0)
        self.view.pack(side="left", fill="both", expand=True)
        self.radar = tk.Canvas(mid, bg=BG, highlightthickness=1, highlightbackground=BORDER, bd=0, width=300 if self.big else 220)
        self.radar.pack(side="right", fill="y", padx=(8, 0))
        for c in (self.view, self.radar, self.graph):
            c.bind("<Configure>", lambda e: self.draw())
        self.graph.bind("<Button-1>", self._seek_click)
        self.graph.bind("<B1-Motion>", self._seek_click)

    def bind_keys(self, widget):
        widget.bind("<space>", lambda e: (self.toggle(), "break")[1])
        widget.bind("<Left>", lambda e: (self.step(-1), "break")[1])
        widget.bind("<Right>", lambda e: (self.step(1), "break")[1])
        widget.bind("<Home>", lambda e: self.to_start())

    # ------------------------------------------------------------ dados
    def load(self, rp, m, autoplay=True):
        self.pause()
        self.rp, self.m = rp, m
        self.qs = rp.recorte(m) if (rp and m) else []
        self.ts = [q.t for q in self.qs]
        self._los = {}
        self._walls2d = None
        self._stopped_at_target = False
        if not self.qs:
            self.title.configure(text=T("mv_pick"))
            self.desc.configure(text="")
            self._set_video(None)
            self.draw()
            return
        self.geo, self.bsp = get_map(rp.bsp)
        self._set_video(game.load_video(rp, m))
        self.target_k = max(0, min(len(self.qs) - 1, bisect.bisect_left(self.ts, self.qs_target_t())))
        self.title.configure(text="%s  ·  %s  ·  %s  (frame %d)" % (
            m.tempo, detector(m.detector), status(m.gravidade).upper(), m.frame),
            fg=RED if m.gravidade == "Suspeito" else AMBER)
        extra = "" if self.geo else "   " + T("mv_no_map") % (rp.mapa or "?")
        self.desc.configure(text=m.descricao + extra)
        # comeca ~2 s antes do apontamento e para nele
        k0 = bisect.bisect_left(self.ts, self.ts[self.target_k] - 2.0)
        self.k = max(0, min(k0, self.target_k))
        self.draw()
        if autoplay:
            self.play()

    def qs_target_t(self):
        q = self.rp.quadros.get(self.m.alvo)
        return q.t if q else self.m.tempo_s

    # ------------------------------------------------------------ reproducao
    def _speed(self):
        try:
            return float(self.speed.get().rstrip("x"))
        except ValueError:
            return 0.5

    def toggle(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self):
        if not self.qs:
            return
        if self.k >= len(self.qs) - 1:
            self.k = 0
            self._stopped_at_target = False
        if self.k >= self.target_k:
            self._stopped_at_target = True
        self.playing = True
        self.btn_play.configure(text="❚❚")
        self._clock = self.ts[self.k]
        self._last = time.perf_counter()
        self._tick()

    def pause(self):
        self.playing = False
        if self._job:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        try:
            self.btn_play.configure(text="▶")
        except tk.TclError:
            pass

    def _tick(self):
        if not self.playing:
            return
        now = time.perf_counter()
        self._clock += (now - self._last) * self._speed()
        self._last = now
        k = max(self.k, bisect.bisect_right(self.ts, self._clock) - 1)
        if self.stop_at.get() and not self._stopped_at_target and k >= self.target_k:
            self.k = self.target_k
            self._stopped_at_target = True
            self.pause()
            self.draw()
            return
        if k >= len(self.qs) - 1:
            if self.loop.get():
                self.k = 0
                self._stopped_at_target = False
                self._clock = self.ts[0]
            else:
                self.k = len(self.qs) - 1
                self.pause()
                self.draw()
                return
        else:
            self.k = k
        self.draw()
        self._job = self.after(16, self._tick)

    def step(self, d):
        if not self.qs:
            return
        self.pause()
        self.k = max(0, min(len(self.qs) - 1, self.k + d))
        self.draw()

    def to_start(self):
        if self.qs:
            self.pause()
            self.k = 0
            self._stopped_at_target = False
            self.draw()

    def to_target(self):
        if self.qs:
            self.pause()
            self.k = self.target_k
            self._stopped_at_target = True
            self.draw()

    def _seek_click(self, e):
        if not self.qs:
            return
        w = max(1, self.graph.winfo_width())
        t0, t1 = self.ts[0], self.ts[-1]
        t = t0 + (t1 - t0) * max(0.0, min(1.0, (e.x - 40) / max(1, w - 50)))
        self.pause()
        self.k = max(0, min(len(self.qs) - 1, bisect.bisect_left(self.ts, t)))
        self._stopped_at_target = self.k >= self.target_k
        self.draw()

    # ------------------------------------------------------------ desenho
    def draw(self):
        try:
            self._draw_view()
            self._draw_radar()
            self._draw_graph()
        except tk.TclError:
            pass

    def _visible(self, i, num, pos, eye):
        key = (i, num)
        if key not in self._los:
            if not self.bsp:
                self._los[key] = None
            else:
                pts = ((pos[0], pos[1], pos[2] + HEAD_Z), (pos[0], pos[1], pos[2]), (pos[0], pos[1], pos[2] - 24))
                self._los[key] = any(self.bsp.visible(eye, p) for p in pts)
        return self._los[key]

    def _draw_view(self):
        c = self.view
        c.delete("all")
        W, H = max(50, c.winfo_width()), max(50, c.winfo_height())
        if not self.qs:
            c.create_text(W / 2, H / 2, text=T("mv_pick"), fill=MUT, font=(self.F, 11))
            return
        q = self.qs[self.k]
        if self.video and self.mode.get() == "video":
            self._draw_video(c, q, W, H)
            return
        cam = Camera(q.eye, q.view[0], q.view[1], W, H)
        # fundo: ceu/chao
        hz = cam.direction(0, q.view[1])
        hy = hz[1] if hz else H / 2
        hy = max(-5, min(H + 5, hy))
        c.create_rectangle(0, 0, W, hy, fill="#141226", outline="")
        c.create_rectangle(0, hy, W, H, fill="#1a1714", outline="")
        if self.geo:
            self._draw_world(c, cam, q)
        else:
            self._draw_grid(c, cam, q)
        self._draw_players(c, cam, q)
        self._draw_hud(c, cam, q, W, H)

    def _draw_world(self, c, cam, q):
        ex, ey, ez = q.eye
        polys = self.geo.polys
        items = []
        for idx in self.geo.near(ex, ey, VIEW_DIST):
            vs, n, zr, ctr, water = polys[idx]
            # face de costas para a camera
            if n[0] * (ex - ctr[0]) + n[1] * (ey - ctr[1]) + n[2] * (ez - ctr[2]) <= 0.0:
                continue
            dx, dy, dz = ctr[0] - ex, ctr[1] - ey, ctr[2] - ez
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist > VIEW_DIST + 512:
                continue
            cs = [cam.to_cam(v) for v in vs]
            if all(p[2] < NEAR for p in cs):
                continue
            cs = clip_near(cs)
            if len(cs) < 3:
                continue
            pts = [cam.proj(p) for p in cs]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            if max(xs) < 0 or min(xs) > cam.w or max(ys) < 0 or min(ys) > cam.h:
                continue
            depth = sum(p[2] for p in cs) / len(cs)
            if water:
                base = WATER
            elif n[2] > 0.7:
                base = FLOOR
            elif n[2] < -0.7:
                base = CEIL
            else:
                base = WALL
            lam = 0.55 + 0.45 * abs(n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2])
            fog = min(1.0, dist / VIEW_DIST) ** 1.3
            col = tuple(base[i] * lam * (1 - fog) + FOG[i] * fog for i in range(3))
            items.append((depth, pts, col))
        items.sort(key=lambda it: -it[0])
        for depth, pts, col in items:
            flat = [v for p in pts for v in p]
            c.create_polygon(flat, fill=_shade(col, 1.0), outline=_shade(col, 0.72), width=1)

    def _draw_grid(self, c, cam, q):
        ex, ey, ez = q.eye
        fz = ez - 53.0
        step, R = 128, 2048
        gx0, gy0 = int(ex // step) * step, int(ey // step) * step
        for k in range(-R // step, R // step + 1):
            for a, b in (((gx0 + k * step, gy0 - R, fz), (gx0 + k * step, gy0 + R, fz)),
                         ((gx0 - R, gy0 + k * step, fz), (gx0 + R, gy0 + k * step, fz))):
                ca, cb = cam.to_cam(a), cam.to_cam(b)
                if ca[2] < NEAR and cb[2] < NEAR:
                    continue
                if ca[2] < NEAR or cb[2] < NEAR:
                    t = (NEAR - ca[2]) / (cb[2] - ca[2])
                    m = tuple(ca[i] + (cb[i] - ca[i]) * t for i in range(3))
                    if ca[2] < NEAR:
                        ca = m
                    else:
                        cb = m
                pa, pb = cam.proj(ca), cam.proj(cb)
                c.create_line(pa[0], pa[1], pb[0], pb[1], fill="#2a2540")

    def _player_box(self, c, cam, pos, color, solid, label):
        x, y, z = pos
        corners = [(x + dx, y + dy, z + dz) for dz in (-36, 36) for dx in (-16, 16) for dy in (-16, 16)]
        pts = [cam.point(p) for p in corners]
        if any(p is None for p in pts):
            return None
        edges = ((0, 1), (0, 2), (1, 3), (2, 3), (4, 5), (4, 6), (5, 7), (6, 7), (0, 4), (1, 5), (2, 6), (3, 7))
        dash = () if solid else (4, 3)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if solid:
            c.create_rectangle(min(xs), min(ys), max(xs), max(ys), fill=color, outline="", stipple="gray25")
        for a, b in edges:
            c.create_line(pts[a][0], pts[a][1], pts[b][0], pts[b][1], fill=color, width=2 if solid else 1,
                          dash=dash)
        head = cam.point((x, y, z + 26))
        if head:
            r = max(2.0, abs(pts[4][0] - pts[5][0]) * 0.28 + 2)
            c.create_oval(head[0] - r, head[1] - r, head[0] + r, head[1] + r, outline=color, width=2,
                          dash=dash)
        c.create_text((min(xs) + max(xs)) / 2, min(ys) - 9, text=label, fill=color, font=(self.F, 9, "bold"))
        return pts

    def _draw_players(self, c, cam, q):
        i = self.m.i0 + self.k if self.m else 0
        names = self.rp.nomes
        order = []
        for num, pos in q.aliados.items():
            order.append((num, pos, False))
        for num, pos in q.inimigos.items():
            order.append((num, pos, True))
        # mais longe primeiro
        order.sort(key=lambda o: -((o[1][0] - q.eye[0]) ** 2 + (o[1][1] - q.eye[1]) ** 2))
        for num, pos, enemy in order:
            name = names.get(num, "#%d" % num)
            if not enemy:
                self._player_box(c, cam, pos, BLUE, True, name)
                continue
            vis = self._visible(i, num, pos, q.eye)
            if vis is False:
                self._player_box(c, cam, pos, AMBER, False, "%s · %s" % (name, T("mv_behind")))
            else:
                self._player_box(c, cam, pos, RED, True, name)

    def _draw_hud(self, c, cam, q, W, H):
        F = self.F
        cx, cy = W / 2, H / 2
        hot = abs(self.k - self.target_k) <= 1
        col = "#fde047" if q.atirando else GREEN
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            c.create_line(cx + dx * 4, cy + dy * 4, cx + dx * 13, cy + dy * 13, fill=col, width=2)
        # mira enviada ao servidor (cmd) - silent aim aparece aqui
        d = angle_between(q.view[0], q.view[1], q.cmd[0], q.cmd[1])
        if d > 1.0:
            p = cam.direction(q.cmd[0], q.cmd[1])
            if p and -50 < p[0] < W + 50 and -50 < p[1] < H + 50:
                c.create_oval(p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9, outline=PURPLE, width=2)
                c.create_line(cx, cy, p[0], p[1], fill=PURPLE, dash=(3, 3))
                c.create_text(p[0] + 12, p[1] - 12, text=T("mv_server_aim"), fill=PURPLE, anchor="w",
                              font=(F, 8, "bold"))
            else:
                c.create_text(cx, cy + 30, text="%s: %.0f°" % (T("mv_server_aim"), d), fill=PURPLE,
                              font=(F, 9, "bold"))
        # informacoes
        tag = []
        if q.atirando:
            tag.append(T("mv_shot"))
        if not q.no_chao:
            tag.append(T("mv_air"))
        if q.agachado:
            tag.append(T("mv_duck"))
        c.create_text(10, 10, anchor="nw", fill=FG, font=(F, 10, "bold"),
                      text="%s   frame %d   %s" % (_fmt(q.t), q.frame, "  ".join(tag)))
        c.create_text(10, H - 10, anchor="sw", fill=FG, font=(F, 10, "bold"),
                      text="%s %d   ·   %s" % (T("mv_hp"), max(0, int(q.vida)), q.arma))
        # kill feed (ultimos 2 s)
        y = 10
        for k in self.rp.mortes:
            if q.t - 2.0 <= k["t"] <= q.t:
                txt = "%s  ➜  %s%s" % (self.rp.nomes.get(k["matador"], "?"), self.rp.nomes.get(k["vitima"], "?"),
                                      "  (HS)" if k["hs"] else "")
                mine = k["matador"] == self.rp.gravador
                c.create_text(W - 10, y, anchor="ne", text=txt, fill=RED if mine else FG, font=(F, 9, "bold"))
                y += 16
        if hot:
            c.create_rectangle(2, 2, W - 2, H - 2, outline=RED, width=4)
            c.create_text(W / 2, 14, text="⚑ %s · %s" % (T("mv_flag"), detector(self.m.detector)), fill=RED,
                          font=(F, 11, "bold"))

    # ------------------------------------------------------------ video real (gravado no CS)
    def _set_video(self, meta):
        self.video = meta
        self._imgs = {}
        if meta:
            self.mode_box.pack(side="left", padx=(6, 0), before=self.game_lbl)
            if meta.get("mp4"):
                self.btn_mp4.pack(side="left", padx=(10, 0))
            else:
                self.btn_mp4.pack_forget()
            self.mode.set("video")
        else:
            self.mode_box.pack_forget()
            self.mode.set("rec")

    def _frame_img(self, k, W, H):
        v = self.video
        key = (k, W // 64, H // 64)
        img = self._imgs.get(key)
        if img is None:
            try:
                img = tk.PhotoImage(file=v["frames"][k])
            except tk.TclError:
                return None
            f = max(1, math.ceil(max(img.width() / max(1, W), img.height() / max(1, H))))
            if f > 1:
                img = img.subsample(f, f)
            else:
                z = int(min(W / max(1, img.width()), H / max(1, img.height())))
                if z >= 2:
                    img = img.zoom(z, z)
            if len(self._imgs) > 90:
                self._imgs.pop(next(iter(self._imgs)))
            self._imgs[key] = img
        return img

    def _draw_video(self, c, q, W, H):
        v = self.video
        k = int(round((q.t - v["t_inicio"]) * v["fps"]))
        if 0 <= k < len(v["frames"]):
            img = self._frame_img(k, W, H)
            if img is not None:
                c.create_image(W / 2, H / 2, image=img)
        else:
            c.create_text(W / 2, H / 2, text=T("g_outside"), fill=MUT, font=(self.F, 11))
        c.create_text(10, H - 10, anchor="sw", fill=FG, font=(self.F, 10, "bold"),
                      text="%s   frame %d   ·   %s" % (_fmt(q.t), q.frame, T("g_video_tag")))
        if abs(self.k - self.target_k) <= 1:
            c.create_rectangle(2, 2, W - 2, H - 2, outline=RED, width=4)
            c.create_text(W / 2, 14, text="⚑ %s · %s" % (T("mv_flag"), detector(self.m.detector)), fill=RED,
                          font=(self.F, 11, "bold"))

    # ------------------------------------------------------------ exportar MP4
    def export_dialog(self):
        if not self.video or not self.m:
            return
        v, m, rp = self.video, self.m, self.rp
        F = self.F
        dlg = tk.Toplevel(self)
        dlg.title(T("ex_title"))
        dlg.configure(bg=SURF)
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())
        box = tk.Frame(dlg, bg=SURF)
        box.pack(padx=18, pady=14)
        tk.Label(box, text=T("ex_title"), bg=SURF, fg=FG, font=(F, 12, "bold")).pack(anchor="w")
        tk.Label(box, text="%s · %s · %d %s" % (m.tempo, detector(m.detector), v["quadros"], T("ex_frames")),
                 bg=SURF, fg=MUT, font=(F, 9)).pack(anchor="w", pady=(2, 10))
        tk.Label(box, text=T("ex_speed"), bg=SURF, fg=MUT, font=(F, 9, "bold")).pack(anchor="w")
        speed = tk.DoubleVar(value=1.0)
        for val, label in zip((1.0, 0.5, 0.25), T("ex_speeds")):
            tk.Radiobutton(box, text=label, value=val, variable=speed, bg=SURF, fg=FG, selectcolor=SURF2,
                           activebackground=SURF, activeforeground=FG, highlightthickness=0,
                           font=(F, 10)).pack(anchor="w")
        mark = tk.BooleanVar(value=True)
        audio = tk.BooleanVar(value=bool(v.get("audio")))
        opts = [(mark, "ex_mark", True)]
        if v.get("audio"):
            opts.append((audio, "ex_audio", True))
        tk.Frame(box, bg=SURF, height=8).pack()
        for var, key, _ in opts:
            tk.Checkbutton(box, text=T(key), variable=var, bg=SURF, fg=FG, selectcolor=SURF2, activebackground=SURF,
                           activeforeground=FG, highlightthickness=0, font=(F, 10)).pack(anchor="w")
        bar = tk.Frame(box, bg=SURF)
        bar.pack(fill="x", pady=(14, 0))

        def go():
            sp, mk, au = speed.get(), mark.get(), audio.get()
            dlg.destroy()
            self._export(rp, m, v, sp, mk, au)
        ttk.Button(bar, text=T("ex_go"), style="Accent.TButton", command=go).pack(side="right")
        ttk.Button(bar, text=T("ex_cancel"), style="Ghost.TButton", command=dlg.destroy).pack(side="right",
                                                                                           padx=(0, 8))
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        _center(dlg, self)
        dlg.grab_set()
        dlg.focus_set()

    def _ffmpeg(self):
        ff = game.find_ffmpeg()
        if ff:
            return ff
        dlg = tk.Toplevel(self)
        dlg.title("ffmpeg")
        dlg.configure(bg=SURF)
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())
        res = {"path": None}
        box = tk.Frame(dlg, bg=SURF)
        box.pack(padx=18, pady=14)
        tk.Label(box, text=T("ex_need_ff"), bg=SURF, fg=FG, font=(self.F, 10), justify="left",
                 wraplength=460).pack(anchor="w")
        bar = tk.Frame(box, bg=SURF)
        bar.pack(fill="x", pady=(14, 0))

        def pick():
            p = filedialog.askopenfilename(parent=dlg, title=T("ex_pick_ff"),
                                           filetypes=[("ffmpeg.exe", "ffmpeg.exe"), ("*", "*")])
            if p:
                game.set_ffmpeg(p)
                res["path"] = p
                dlg.destroy()
        ttk.Button(bar, text=T("ex_pick_ff"), style="Accent.TButton", command=pick).pack(side="right")
        ttk.Button(bar, text=T("ex_download"), style="Ghost.TButton",
                   command=lambda: __import__("webbrowser").open(FFMPEG_URL)).pack(side="right", padx=(0, 8))
        ttk.Button(bar, text=T("ex_cancel"), style="Ghost.TButton", command=dlg.destroy).pack(side="right",
                                                                                           padx=(0, 8))
        _center(dlg, self)
        dlg.grab_set()
        self.wait_window(dlg)
        return res["path"]

    def _export(self, rp, m, v, speed, mark, audio):
        ff = self._ffmpeg()
        if not ff:
            return
        det = "_".join("".join(ch if ch.isalnum() else " " for ch in detector(m.detector)).split())[:30]
        name = "%s_%s_%s%s.mp4" % (os.path.splitext(os.path.basename(rp.demo))[0], m.tempo.replace(":", "m").replace(
            ".", "s"), det, "" if speed == 1.0 else "_%gx" % speed)
        out = filedialog.asksaveasfilename(parent=self, title=T("ex_save"), defaultextension=".mp4",
                                           initialdir=os.path.dirname(rp.demo), initialfile=name,
                                           filetypes=[("MP4", "*.mp4")])
        if not out:
            return
        mk = (v["t_alvo"] - v["t_inicio"]) if mark else None
        self.btn_export.configure(state="disabled")
        self.game_lbl.configure(text=T("ex_working"), fg=AMBER)

        def run():
            try:
                game.export_mp4(ff, v["dir"], out=out, speed=speed, mark=mk, audio=audio)
                self._q.put(("exported", out))
            except Exception as e:  # noqa: BLE001
                self._q.put(("export_err", e))
        threading.Thread(target=run, daemon=True).start()

    def open_mp4(self):
        if self.video and self.video.get("mp4"):
            _open_file(self.video["mp4"])

    def _game_exe(self):
        exe = game.find_game(self.rp.demo if self.rp else None)
        game.log("executavel do jogo: %s" % exe)
        if exe:
            return exe
        messagebox.showinfo("Vidalia", T("g_not_found"), parent=self)
        p = filedialog.askopenfilename(parent=self, title=T("g_pick_exe"),
                                       filetypes=[("hl.exe / cstrike.exe", "*.exe"), ("*", "*")])
        if not p:
            return None
        game.set_game(p)
        return p

    def _check(self):
        if not self.m:
            return None
        if _REC["busy"]:
            messagebox.showinfo("Vidalia", T("g_running"), parent=self)
            return None
        exe = self._game_exe()
        if not exe:
            return None
        if not game.map_installed(exe, self.rp.jogo or "cstrike", self.rp.mapa):
            if not messagebox.askyesno("Vidalia", T("g_no_map") % self.rp.mapa, parent=self):
                return None
        return exe

    def watch_game(self):
        exe = self._check()
        if not exe:
            return
        self.pause()
        rp, m = self.rp, self.m
        self.game_lbl.configure(text=T("g_watch_on") % m.tempo, fg=GREEN)

        def run():
            try:
                game.watch(rp, m, exe)
                self._q.put(("watch_end", None))
            except Exception as e:  # noqa: BLE001
                self._q.put(("err", e))
        threading.Thread(target=run, daemon=True).start()

    def record_video(self):
        if _REC["busy"]:
            _REC["cancel"] = True
            return
        exe = self._check()
        if not exe:
            return
        self.pause()
        rp, m = self.rp, self.m
        _REC.update(busy=True, cancel=False)
        self.btn_rec.configure(text=T("g_cancel"))
        self.btn_watch.configure(state="disabled")
        self.game_lbl.configure(text=T("g_game"), fg=AMBER)

        def prog(stage, frac=0.0):
            self._q.put(("prog", (stage, frac)))

        def run():
            try:
                meta = game.record(rp, m, exe, progress=prog, cancel=lambda: _REC["cancel"])
                self._q.put(("done", (rp, m, meta)))
            except Exception as e:  # noqa: BLE001
                self._q.put(("err", e))
        threading.Thread(target=run, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, val = self._q.get_nowait()
                if kind == "prog":
                    stage, frac = val
                    txt = {"game": T("g_game"), "convert": T("g_convert") % int(frac * 100),
                           "mp4": T("g_mp4")}.get(stage, "")
                    self.game_lbl.configure(text=txt, fg=AMBER)
                elif kind == "done":
                    rp, m, meta = val
                    self._rec_end()
                    self.game_lbl.configure(text=T("g_done") % (meta["quadros"] if meta else 0), fg=GREEN)
                    if self.m is m:
                        self._set_video(meta)
                        self.to_target()
                elif kind == "exported":
                    self.btn_export.configure(state="normal")
                    self.game_lbl.configure(text=T("ex_done") % os.path.basename(val), fg=GREEN)
                    if messagebox.askyesno("Vidalia", T("ex_open_folder") % val, parent=self):
                        _show_in_folder(val)
                elif kind == "export_err":
                    self.btn_export.configure(state="normal")
                    detail = str(val).partition(":")[2] if isinstance(val, game.GameError) else str(val)
                    txt = T("ex_err") % detail
                    self.game_lbl.configure(text=txt.splitlines()[0][:120], fg=RED)
                    messagebox.showerror("Vidalia", txt + "\n\n" + T("g_log") % game.log_path(), parent=self)
                elif kind == "watch_end":
                    self.game_lbl.configure(text="")
                elif kind == "err":
                    self._rec_end()
                    txt = _err_text(val)
                    game.log("erro: %r" % val)
                    self.game_lbl.configure(text=txt, fg=RED)
                    if not (isinstance(val, game.GameError) and str(val) == "cancelled"):
                        messagebox.showerror("Vidalia", txt + "\n\n" + T("g_log") % game.log_path(), parent=self)
        except queue.Empty:
            pass
        try:
            self.after(150, self._poll)
        except tk.TclError:
            pass

    def _rec_end(self):
        _REC.update(busy=False, cancel=False)
        try:
            self.btn_rec.configure(text=T("mv_record"))
            self.btn_watch.configure(state="normal")
        except tk.TclError:
            pass

    def _walls(self):
        if self._walls2d is None:
            segs = []
            if self.geo:
                for vs, n, zr, ctr, water in self.geo.polys:
                    if abs(n[2]) > 0.5:
                        continue
                    tx, ty = -n[1], n[0]
                    proj = [(v[0] * tx + v[1] * ty, v) for v in vs]
                    a = min(proj)[1]
                    b = max(proj)[1]
                    segs.append((a[0], a[1], b[0], b[1], zr[0], zr[1]))
            self._walls2d = segs
        return self._walls2d

    def _draw_radar(self):
        c = self.radar
        c.delete("all")
        W, H = max(50, c.winfo_width()), max(50, c.winfo_height())
        c.create_text(8, 6, anchor="nw", text=T("mv_radar"), fill=MUT, font=(self.F, 9, "bold"))
        if not self.qs:
            return
        q = self.qs[self.k]
        ex, ey, ez = q.eye
        R = 1100.0
        s = (min(W, H) / 2 - 12) / R
        cx, cy = W / 2, H / 2
        yaw = math.radians(q.view[1])
        # rotaciona para a mira apontar para cima
        ca, sa = math.cos(-yaw + math.pi / 2), math.sin(-yaw + math.pi / 2)

        def tr(x, y):
            dx, dy = x - ex, y - ey
            rx, ry = dx * ca - dy * sa, dx * sa + dy * ca
            return cx + rx * s, cy - ry * s

        for x0, y0, x1, y1, z0, z1 in self._walls():
            if z1 < ez - 70 or z0 > ez + 10:
                continue
            if min(abs(x0 - ex), abs(x1 - ex)) > R * 1.5 and min(abs(y0 - ey), abs(y1 - ey)) > R * 1.5:
                continue
            a, b = tr(x0, y0), tr(x1, y1)
            c.create_line(a[0], a[1], b[0], b[1], fill="#6d6590", width=2)
        # cone de visao
        L = R * 0.9 * s
        c.create_polygon(cx, cy, cx - L, cy - L, cx + L, cy - L, fill="#1f2a12", outline="", stipple="gray50")
        c.create_line(cx, cy, cx, cy - L, fill=GREEN, width=1)
        d = wrap180(q.cmd[1] - q.view[1])
        if abs(d) > 1.0:
            a = math.radians(90 + d)
            c.create_line(cx, cy, cx + math.cos(a) * L, cy - math.sin(a) * L, fill=PURPLE, width=2, dash=(4, 3))
        # rastros de 1 s
        i = self.m.i0 + self.k
        k0 = bisect.bisect_left(self.ts, q.t - 1.0)
        trails = {}
        for qq in self.qs[k0:self.k + 1]:
            for num, pos in list(qq.inimigos.items()) + list(qq.aliados.items()):
                trails.setdefault(num, []).extend(tr(pos[0], pos[1]))
        for num, pts in trails.items():
            if len(pts) >= 4:
                c.create_line(*pts, fill="#3a3352")
        for num, pos in q.aliados.items():
            x, y = tr(pos[0], pos[1])
            c.create_oval(x - 5, y - 5, x + 5, y + 5, fill=BLUE, outline="")
        for num, pos in q.inimigos.items():
            x, y = tr(pos[0], pos[1])
            vis = self._visible(i, num, pos, q.eye)
            col = AMBER if vis is False else RED
            c.create_oval(x - 6, y - 6, x + 6, y + 6, fill=col if vis is not False else "", outline=col, width=2)
            c.create_text(x + 8, y, anchor="w", text=self.rp.nomes.get(num, "#%d" % num)[:14], fill=col,
                          font=(self.F, 8))
        c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=GREEN, outline=BG, width=2)

    def _series(self):
        if getattr(self, "_ser_key", None) == id(self.qs):
            return self._ser
        sp, err = [0.0], []
        for k, q in enumerate(self.qs):
            if k:
                p = self.qs[k - 1]
                dt = q.t - p.t
                d = math.hypot(wrap180(q.cmd[1] - p.cmd[1]), q.cmd[0] - p.cmd[0])
                sp.append(d / dt if dt > 0.0005 else sp[-1])
            best = None
            for pos in q.inimigos.values():
                pp, yy, _ = angles_to(q.eye, (pos[0], pos[1], pos[2] + HEAD_Z))
                e = angle_between(q.cmd[0], q.cmd[1], pp, yy)
                best = e if best is None or e < best else best
            err.append(best)
        self._ser_key = id(self.qs)
        self._ser = (sp, err)
        return self._ser

    def _draw_graph(self):
        c = self.graph
        c.delete("all")
        W, H = max(80, c.winfo_width()), max(40, c.winfo_height())
        if not self.qs:
            return
        sp, err = self._series()
        t0, t1 = self.ts[0], self.ts[-1]
        span = max(1e-3, t1 - t0)
        x0, x1, y0, y1 = 40, W - 10, 8, H - 16

        def X(t):
            return x0 + (t - t0) / span * (x1 - x0)

        top = max(200.0, max(sp))
        c.create_text(4, y0, anchor="nw", text="%d°/s" % top, fill=GREEN, font=(self.F, 7))
        c.create_text(4, y1, anchor="sw", text="0", fill=MUT, font=(self.F, 7))
        # mortes e tiros
        for t in self.rp.tiros:
            if t0 <= t <= t1:
                c.create_line(X(t), y1, X(t), y1 + 6, fill="#fde047")
        for k in self.rp.mortes:
            if t0 <= k["t"] <= t1:
                c.create_text(X(k["t"]), y1 + 9, text="☠", fill=RED, font=(self.F, 8))
        pts = []
        for t, v in zip(self.ts, sp):
            pts += [X(t), y1 - (y1 - y0) * min(1.0, v / top)]
        if len(pts) >= 4:
            c.create_line(*pts, fill=GREEN, width=1)
        seg = []
        for t, e in zip(self.ts, err):
            if e is None:
                if len(seg) >= 4:
                    c.create_line(*seg, fill=AMBER, width=1)
                seg = []
                continue
            seg += [X(t), y1 - (y1 - y0) * min(1.0, e / 45.0)]
        if len(seg) >= 4:
            c.create_line(*seg, fill=AMBER, width=1)
        tx = X(self.ts[self.target_k])
        c.create_line(tx, y0 - 4, tx, y1 + 6, fill=RED, width=2)
        px = X(self.ts[self.k])
        c.create_line(px, 0, px, H, fill=FG, width=1)
        lg = c.create_text(x1, y0, anchor="ne", fill=AMBER, font=(self.F, 8), text="— " + T("mv_graph_err"))
        bx = c.bbox(lg)
        c.create_text((bx[0] if bx else x1) - 14, y0, anchor="ne", fill=GREEN, font=(self.F, 8),
                      text="— " + T("mv_graph_speed"))
        self.pos_lbl.configure(text="%+.3f s  ·  %d/%d" % (self.ts[self.k] - self.ts[self.target_k],
                                                            self.k + 1, len(self.qs)))


def _err_text(e):
    msg = str(e)
    if isinstance(e, game.GameError):
        code, _, extra = msg.partition(":")
        key = "g_err_" + code
        txt = T(key)
        if txt != key:
            return txt % extra if "%s" in txt else txt
    return T("g_err_other") % msg


def _open_file(path):
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)  # noqa: S606
        else:
            import subprocess
            subprocess.Popen(["xdg-open", path])
    except Exception:  # noqa: BLE001
        pass


def _center(dlg, over):
    try:
        dlg.update_idletasks()
        top = over.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - dlg.winfo_reqwidth()) // 2
        y = top.winfo_rooty() + (top.winfo_height() - dlg.winfo_reqheight()) // 3
        dlg.geometry("+%d+%d" % (max(0, x), max(0, y)))
    except tk.TclError:
        pass


def _show_in_folder(path):
    try:
        if os.name == "nt":
            import subprocess
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        else:
            _open_file(os.path.dirname(path))
    except Exception:  # noqa: BLE001
        pass


def _fmt(t):
    t = max(0.0, t)
    m = int(t // 60)
    return "%02d:%06.3f" % (m, t - 60 * m)
