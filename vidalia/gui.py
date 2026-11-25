"""Interface grafica (Tkinter) do Vidalia Demo Analyzer."""
import glob
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from . import __version__
from .control import AnalysisControl, Cancelled
from .detectors import ATENCAO, OK, SEM_DADOS, SUSPEITO, detector_count
from .i18n import (LANGS, T, chat_type, detector, get_lang, load_lang, save_lang, score_text, set_lang, status)
from .report import analyze, save_batch, save_chat_txt, save_csv, save_html, save_json

# ---------------------------------------------------------------- identidade visual
BG = "#0b0a12"        # fundo da janela
SURF = "#14121e"      # cartoes
SURF2 = "#1d1a2b"     # campos / botoes secundarios
HOVER = "#272338"
BORDER = "#2b2640"
FG = "#ece9f5"
MUT = "#8f89a6"
PURPLE = "#a855f7"
PURPLE_D = "#7e22ce"
GREEN = "#a3e635"
GREEN_D = "#84cc16"
AMBER = "#f59e0b"
RED = "#f43f5e"
COL = {SUSPEITO: RED, ATENCAO: AMBER, OK: "#4ade80", SEM_DADOS: "#6b7280"}
LEVEL = {SEM_DADOS: -1, OK: 0, ATENCAO: 1, SUSPEITO: 2}
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def asset(name):
    """Caminho de um recurso (funciona no codigo-fonte e no .exe do PyInstaller)."""
    for base in (ASSETS, os.path.join(getattr(sys, "_MEIPASS", ""), "vidalia", "assets")):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def pick_font(root):
    fams = set(tkfont.families(root))
    for f in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Ubuntu", "DejaVu Sans"):
        if f in fams:
            return f
    return "TkDefaultFont"


def set_app_icon(root):
    """Icone da janela e da barra de tarefas."""
    if sys.platform == "win32":
        try:  # faz o Windows agrupar a janela com o icone do Vidalia (e nao do python.exe)
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Vidalia.DemoAnalyzer")
        except Exception:  # noqa: BLE001
            pass
        ico = asset("vidalia.ico")
        if ico:
            try:
                root.iconbitmap(default=ico)
            except tk.TclError:
                pass
    imgs = []
    for s in (16, 32, 64, 128):
        p = asset("icon_%d.png" % s)
        if p:
            try:
                imgs.append(tk.PhotoImage(file=p))
            except tk.TclError:
                pass
    if imgs:
        root.iconphoto(True, *imgs)
    return imgs


class App:
    def __init__(self, root):
        self.root = root
        root.title("Vidalia Demo Analyzer %s" % __version__)
        root.geometry("1100x780")
        root.minsize(900, 640)
        root.configure(bg=BG)
        self._icons = set_app_icon(root)
        self.q = queue.Queue()
        self.demo = tk.StringVar()
        self.maps = tk.StringVar()
        self.status = tk.StringVar(value="")
        self.f_sev = tk.StringVar()
        self.f_det = tk.StringVar()
        self.last_html = None
        self.results = []   # [(caminho, relatorio)]
        self.ctl = None     # AnalysisControl da analise em andamento
        self.pct = tk.StringVar(value="")
        self.cur = None     # (indice, total, nome) da demo em analise
        self.running = False
        self.sev_idx = 1          # filtro de gravidade (indice em T("filters"))
        self.det_filter = None    # nome interno do detector filtrado (None = todos)
        self.chat_idx = 1         # filtro do chat (indice em T("chat_filters"))
        self._pv = 0.0            # valor atual da barra de progresso
        set_lang(load_lang())
        self.F = pick_font(root)
        self._build_ui()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self.poll)

    def _build_ui(self):
        root = self.root
        F = self.F
        self._style(F)

        # ---------------------------------------------------------- cabecalho
        head = tk.Frame(root, bg=BG)
        head.pack(fill="x", padx=14, pady=(10, 0))
        self._logo = None
        lp = asset("logo_header.png")
        if lp:
            try:
                self._logo = tk.PhotoImage(file=lp)
            except tk.TclError:
                self._logo = None
        if self._logo:
            tk.Label(head, image=self._logo, bg=BG, bd=0).pack(side="left")
        else:
            tk.Label(head, text="VIDALIA", bg=BG, fg=FG, font=(F, 30, "bold")).pack(side="left", padx=8)
        txt = tk.Frame(head, bg=BG)
        txt.pack(side="left", padx=(10, 0), fill="y")
        tk.Frame(txt, bg=BG).pack(expand=True)
        tk.Label(txt, text="DEMO ANALYZER", bg=BG, fg=FG, font=(F, 24, "bold")).pack(anchor="w")
        tk.Label(txt, text=T("subtitle"), bg=BG, fg=MUT,
                 font=(F, 11)).pack(anchor="w")
        pills = tk.Frame(txt, bg=BG)
        pills.pack(anchor="w", pady=(8, 0))
        self._pill(pills, "v%s" % __version__, PURPLE_D, "#ffffff")
        self._pill(pills, T("pill_detectors") % detector_count(), SURF2, GREEN)
        self._pill(pills, T("pill_free"), SURF2, MUT)
        tk.Frame(txt, bg=BG).pack(expand=True)
        lang = tk.Frame(head, bg=BG)
        lang.pack(side="right", anchor="n", padx=(0, 4), pady=(6, 0))
        tk.Label(lang, text="\U0001F310  " + T("language"), bg=BG, fg=MUT, font=(F, 9, "bold")).pack(anchor="e")
        self.lang_var = tk.StringVar(value=dict(LANGS)[get_lang()])
        cbl = ttk.Combobox(lang, textvariable=self.lang_var, values=[n for _, n in LANGS], state="readonly", width=16,
                           style="Dark.TCombobox")
        cbl.pack(anchor="e", pady=(4, 0))
        cbl.bind("<<ComboboxSelected>>", lambda e: self.change_lang())

        self.grad = tk.Canvas(root, height=3, bg=BG, highlightthickness=0, bd=0)
        self.grad.pack(fill="x", padx=18, pady=(10, 12))
        self.grad.bind("<Configure>", self._draw_gradient)

        # ---------------------------------------------------------- entrada
        card = self._card(root)
        card.pack(fill="x", padx=18)
        inner = tk.Frame(card, bg=SURF)
        inner.pack(fill="x", padx=16, pady=12)
        inner.columnconfigure(1, weight=1)
        self._caption(inner, T("demo_or_folder")).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(inner, textvariable=self.demo, style="Dark.TEntry").grid(row=0, column=1, sticky="ew", padx=12, ipady=4)
        bx = tk.Frame(inner, bg=SURF)
        bx.grid(row=0, column=2, sticky="e")
        ttk.Button(bx, text=T("btn_demo"), style="Ghost.TButton", command=self.pick_demo).pack(side="left")
        ttk.Button(bx, text=T("btn_folder"), style="Ghost.TButton", command=self.pick_folder).pack(side="left", padx=(6, 0))
        self._caption(inner, T("maps_optional")).grid(row=1, column=0, sticky="w", pady=(8, 4))
        ttk.Entry(inner, textvariable=self.maps, style="Dark.TEntry").grid(row=1, column=1, sticky="ew", padx=12,
                                                                            pady=(8, 0), ipady=4)
        ttk.Button(inner, text=T("btn_maps"), style="Ghost.TButton", command=self.pick_maps).grid(
            row=1, column=2, sticky="w", pady=(8, 0))
        tk.Label(inner, text=T("maps_hint"),
                 bg=SURF, fg=MUT, font=(F, 9)).grid(row=2, column=1, sticky="w", padx=12, pady=(4, 0))

        # ---------------------------------------------------------- acoes
        bar = tk.Frame(root, bg=BG)
        bar.pack(fill="x", padx=18, pady=(14, 8))
        self.btn = ttk.Button(bar, text=T("btn_analyze"), style="Accent.TButton", command=self.start)
        self.btn.pack(side="left")
        self.btn_pause = ttk.Button(bar, text=T("btn_pause"), style="Ghost.TButton", command=self.pause, state="disabled")
        self.btn_pause.pack(side="left", padx=(10, 0))
        self.btn_resume = ttk.Button(bar, text=T("btn_resume"), style="Ghost.TButton", command=self.resume, state="disabled")
        self.btn_resume.pack(side="left", padx=(6, 0))
        self.btn_cancel = ttk.Button(bar, text=T("btn_cancel"), style="Danger.TButton", command=self.cancel, state="disabled")
        self.btn_cancel.pack(side="left", padx=(6, 0))
        self.btn_html = ttk.Button(bar, text=T("btn_report"), style="Purple.TButton",
                                   command=self.open_html, state="disabled")
        self.btn_html.pack(side="right")

        prog = tk.Frame(root, bg=BG)
        prog.pack(fill="x", padx=18, pady=(2, 8))
        self.pb = ttk.Progressbar(prog, mode="determinate", maximum=100, style="Run.Horizontal.TProgressbar")
        self.pb.pack(side="left", fill="x", expand=True)
        self.pct_lbl = tk.Label(prog, textvariable=self.pct, bg=BG, fg=GREEN, font=(F, 11, "bold"), width=5, anchor="e")
        self.pct_lbl.pack(side="right", padx=(10, 0))

        # ---------------------------------------------------------- veredito
        self.vbox = self._card(root)
        self.vstripe = tk.Frame(self.vbox, bg=MUT, width=5)
        self.vstripe.pack(side="left", fill="y")
        self.verdict = tk.Label(self.vbox, text="", bg=SURF, fg=FG, font=(F, 13, "bold"), anchor="w",
                                padx=14, pady=10)
        self.verdict.pack(side="left", fill="x", expand=True)
        self.vanchor = tk.Frame(root, bg=BG, height=0)
        self.vanchor.pack(fill="x")

        # ---------------------------------------------------------- rodape (fixo embaixo)
        foot = tk.Frame(root, bg=BG)
        foot.pack(side="bottom", fill="x", padx=18, pady=(8, 12))
        tk.Label(foot, textvariable=self.status, bg=BG, fg=FG, font=(F, 9), anchor="w").pack(fill="x")
        tk.Label(foot, text=T("disclaimer") + ("  " + T("evidence_note") if T("evidence_note") else ""),
                 bg=BG, fg=MUT, font=(F, 9), anchor="w").pack(fill="x")

        # ---------------------------------------------------------- resultados (abas)
        res = self._card(root)
        res.pack(fill="both", expand=True, padx=18, pady=(6, 0))
        self.nb = ttk.Notebook(res, style="Dark.TNotebook")
        self.nb.pack(fill="both", expand=True)
        tab_det = tk.Frame(self.nb, bg=SURF)
        self.tab_chat = tk.Frame(self.nb, bg=SURF)
        self.nb.add(tab_det, text="  %s  " % T("tab_detectors"))
        self.nb.add(self.tab_chat, text="  %s  " % T("tab_chat"))
        self._build_chat_tab(self.tab_chat)
        rh = tk.Frame(tab_det, bg=SURF)
        rh.pack(fill="x", padx=14, pady=(10, 8))
        tk.Label(rh, text=T("results_title"), bg=SURF, fg=FG, font=(F, 12, "bold")).pack(side="left")
        self.cb_det = ttk.Combobox(rh, textvariable=self.f_det, values=[T("all_detectors")], state="readonly",
                                   width=30, style="Dark.TCombobox")
        self.cb_det.pack(side="right")
        cb1 = ttk.Combobox(rh, textvariable=self.f_sev, values=T("filters"), state="readonly", width=30,
                           style="Dark.TCombobox")
        cb1.pack(side="right", padx=8)
        tk.Label(rh, text=T("show"), bg=SURF, fg=MUT, font=(F, 10)).pack(side="right")
        cb1.bind("<<ComboboxSelected>>", lambda e: self._on_filter())
        self.cb_det.bind("<<ComboboxSelected>>", lambda e: self._on_filter())
        self.f_sev.set(T("filters")[self.sev_idx])
        tk.Frame(tab_det, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(tab_det, bg=SURF)
        body.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        self.tree = ttk.Treeview(body, columns=("status", "resumo"), show="tree headings", selectmode="browse",
                                 style="Dark.Treeview", height=8)
        self.tree.heading("#0", text=T("col_demo_detector"), anchor="w")
        self.tree.heading("status", text=T("col_status"))
        self.tree.heading("resumo", text=T("col_summary"), anchor="w")
        self.tree.column("#0", width=300, stretch=False)
        self.tree.column("status", width=140, stretch=False, anchor="center")
        self.tree.column("resumo", width=600)
        for k, c in COL.items():
            self.tree.tag_configure(k, foreground=c)
        self.tree.tag_configure("demo", font=(F, 10, "bold"))
        sb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview, style="Dark.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self._fill_det_filter()
        if not self.status.get():
            self._say("status_start")


    # ------------------------------------------------------------ chat
    # indice do filtro -> categorias (0 = tudo, 4 = destaques)
    CHAT_SETS = {1: {"todos", "time", "morto", "espectador", "nome"},
                 2: {"todos", "time", "morto", "espectador", "nome", "radio"},
                 3: {"servidor", "jogo"}}

    def _build_chat_tab(self, parent):
        F = self.F
        self.chat_f = tk.StringVar(value=T("chat_filters")[self.chat_idx])
        self.chat_q = getattr(self, "chat_q", None) or tk.StringVar()
        top = tk.Frame(parent, bg=SURF)
        top.pack(fill="x", padx=14, pady=(10, 8))
        tk.Label(top, text=T("chat_title"), bg=SURF, fg=FG, font=(F, 12, "bold")).pack(side="left")
        ttk.Button(top, text=T("btn_save_chat"), style="Ghost.TButton", command=self.save_chat).pack(side="right")
        ent = ttk.Entry(top, textvariable=self.chat_q, style="Dark.TEntry", width=22)
        ent.pack(side="right", padx=(0, 10))
        tk.Label(top, text=T("search"), bg=SURF, fg=MUT, font=(F, 10)).pack(side="right", padx=(10, 6))
        cb = ttk.Combobox(top, textvariable=self.chat_f, values=T("chat_filters"), state="readonly", width=30,
                          style="Dark.TCombobox")
        cb.pack(side="right")
        tk.Label(top, text=T("show"), bg=SURF, fg=MUT, font=(F, 10)).pack(side="right", padx=(0, 8))
        cb.bind("<<ComboboxSelected>>", lambda e: (setattr(self, "chat_idx", T("chat_filters").index(self.chat_f.get())),
                                                   self.render_chat()))
        if not getattr(self, "_chat_traced", False):
            self.chat_q.trace_add("write", lambda *a: self.render_chat())
            self._chat_traced = True
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
        body = tk.Frame(parent, bg=SURF)
        body.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        cols = ("demo", "tempo", "tipo", "jogador", "texto")
        self.chat_tree = ttk.Treeview(body, columns=cols, show="headings", style="Dark.Treeview", height=8)
        for c, t, w, st in (("demo", T("col_demo"), 160, False), ("tempo", T("col_time"), 80, False),
                            ("tipo", T("col_type"), 120, False), ("jogador", T("col_player"), 190, False),
                            ("texto", T("col_message"), 520, True)):
            self.chat_tree.heading(c, text=t, anchor="w")
            self.chat_tree.column(c, width=w, stretch=st, anchor="w")
        self.chat_tree.tag_configure("destaque", background="#3b2a08", foreground="#fcd34d")
        self.chat_tree.tag_configure("servidor", foreground=MUT)
        self.chat_tree.tag_configure("jogo", foreground=MUT)
        self.chat_tree.tag_configure("radio", foreground="#c4b5fd")
        self.chat_tree.tag_configure("morto", foreground="#9ca3af")
        self.chat_tree.tag_configure("nome", foreground=GREEN)
        sb = ttk.Scrollbar(body, orient="vertical", command=self.chat_tree.yview, style="Dark.Vertical.TScrollbar")
        self.chat_tree.configure(yscrollcommand=sb.set)
        self.chat_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.chat_rows = []

    def _chat_visible(self):
        sel = self.chat_idx
        q = self.chat_q.get().strip().lower()
        allowed = self.CHAT_SETS.get(sel)
        out = []
        for path, rep in self.results:
            for c in rep.get("chat", []):
                if allowed is not None and c["categoria"] not in allowed:
                    continue
                if sel == 4 and not c.get("destaque"):
                    continue
                if q and q not in (c["texto"] + " " + c["jogador"]).lower():
                    continue
                out.append((path, c))
        return out

    def render_chat(self):
        if not hasattr(self, "chat_tree"):
            return
        self.chat_tree.delete(*self.chat_tree.get_children())
        multi = len(self.results) > 1
        self.chat_tree.configure(displaycolumns=("demo", "tempo", "tipo", "jogador", "texto") if multi
                                 else ("tempo", "tipo", "jogador", "texto"))
        rows = self._chat_visible()
        for path, c in rows[:20000]:
            tags = ("destaque",) if c.get("destaque") else (c["categoria"],)
            self.chat_tree.insert("", "end", values=(os.path.basename(path), c["tempo"], chat_type(c["categoria"]),
                                                     c["jogador"], c["texto"]),
                                  tags=tags)
        total = sum(len(rep.get("chat", [])) for _, rep in self.results)
        self.nb.tab(self.tab_chat, text="  %s  " % (T("tab_chat_n") % total if total else T("tab_chat")))
        self.chat_rows = rows

    def save_chat(self):
        if not self.chat_rows:
            messagebox.showinfo("Vidalia", T("chat_none"))
            return
        p = filedialog.asksaveasfilename(title=T("save_chat_title"), defaultextension=".txt",
                                         filetypes=[("Texto", "*.txt"), ("CSV (Excel)", "*.csv")],
                                         initialfile="chat_vidalia.txt")
        if not p:
            return
        import csv as _csv
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            if p.lower().endswith(".csv"):
                w = _csv.writer(f, delimiter=";")
                w.writerow([T("col_demo"), T("col_time"), T("col_type"), T("col_player"), "SteamID", T("col_message")])
                for path, c in self.chat_rows:
                    w.writerow([os.path.basename(path), c["tempo"], chat_type(c["categoria"]), c["jogador"],
                                c.get("steamid", ""), c["texto"]])
            else:
                for path, c in self.chat_rows:
                    who = ("%s: " % c["jogador"]) if c["jogador"] else ""
                    pre = ("%s  " % os.path.basename(path)) if len(self.results) > 1 else ""
                    f.write("%s[%s] (%s) %s%s\n" % (pre, c["tempo"], chat_type(c["categoria"]), who, c["texto"]))
        self._say("chat_saved", p)

    # ------------------------------------------------------------ estilo
    def _style(self, F):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure(".", background=BG, foreground=FG, font=(F, 10), bordercolor=BORDER,
                     lightcolor=BORDER, darkcolor=BORDER, troughcolor=SURF2, focuscolor=PURPLE)

        def button(name, bg, fg, hover, press, border=None, bold=False):
            st.configure(name, background=bg, foreground=fg, bordercolor=border or bg, lightcolor=bg, darkcolor=bg,
                         focuscolor=bg, relief="flat", padding=(14, 7), font=(F, 10, "bold" if bold else "normal"))
            st.map(name,
                   background=[("disabled", SURF), ("pressed", press), ("active", hover)],
                   foreground=[("disabled", "#4b4660")],
                   bordercolor=[("disabled", BORDER), ("active", border or hover)],
                   lightcolor=[("disabled", SURF), ("pressed", press), ("active", hover)],
                   darkcolor=[("disabled", SURF), ("pressed", press), ("active", hover)])

        button("Accent.TButton", GREEN, "#10140a", "#bef264", GREEN_D, bold=True)
        button("Purple.TButton", PURPLE_D, "#ffffff", "#9333ea", "#6b21a8", bold=True)
        button("Ghost.TButton", SURF2, FG, HOVER, BORDER, border=BORDER)
        button("Danger.TButton", SURF2, RED, "#3a1622", "#4c1d2b", border="#5b2133")

        st.configure("Dark.TEntry", fieldbackground=SURF2, foreground=FG, insertcolor=FG, bordercolor=BORDER,
                     lightcolor=SURF2, darkcolor=SURF2, padding=6)
        st.map("Dark.TEntry", bordercolor=[("focus", PURPLE)], lightcolor=[("focus", PURPLE)])
        st.configure("Dark.TCombobox", fieldbackground=SURF2, background=SURF2, foreground=FG, arrowcolor=GREEN,
                     bordercolor=BORDER, lightcolor=SURF2, darkcolor=SURF2, padding=5)
        st.map("Dark.TCombobox", fieldbackground=[("readonly", SURF2)], foreground=[("readonly", FG)],
               selectbackground=[("readonly", SURF2)], selectforeground=[("readonly", FG)],
               background=[("active", HOVER)], bordercolor=[("focus", PURPLE), ("active", PURPLE)])
        self.root.option_add("*TCombobox*Listbox.background", SURF2)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", PURPLE_D)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", (F, 10))

        for name, color in (("Run", GREEN), ("Paused", AMBER)):
            st.configure("%s.Horizontal.TProgressbar" % name, troughcolor=SURF2, background=color,
                         bordercolor=SURF2, lightcolor=color, darkcolor=color, thickness=10)

        st.configure("Dark.Treeview", background=SURF, fieldbackground=SURF, foreground=FG, rowheight=28,
                     font=(F, 10), borderwidth=0, relief="flat")
        st.layout("Dark.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.map("Dark.Treeview", background=[("selected", "#3b1d5e")], foreground=[("selected", "#ffffff")])
        st.configure("Dark.Treeview.Heading", background=SURF2, foreground=MUT, font=(F, 9, "bold"),
                     relief="flat", bordercolor=BORDER, lightcolor=SURF2, darkcolor=SURF2, padding=(8, 6))
        st.map("Dark.Treeview.Heading", background=[("active", HOVER)])
        st.configure("Dark.TNotebook", background=SURF, borderwidth=0, tabmargins=(10, 8, 10, 0))
        st.configure("Dark.TNotebook.Tab", background=SURF2, foreground=MUT, padding=(16, 7), font=(F, 10, "bold"),
                     bordercolor=BORDER, lightcolor=SURF2, darkcolor=SURF2, focuscolor=SURF)
        st.map("Dark.TNotebook.Tab", background=[("selected", SURF), ("active", HOVER)],
               foreground=[("selected", GREEN), ("active", FG)],
               lightcolor=[("selected", SURF)], darkcolor=[("selected", SURF)], bordercolor=[("selected", PURPLE)])
        st.configure("Dark.Vertical.TScrollbar", background=SURF2, troughcolor=SURF, bordercolor=SURF,
                     lightcolor=SURF2, darkcolor=SURF2, arrowcolor=MUT, gripcount=0)
        st.map("Dark.Vertical.TScrollbar", background=[("active", PURPLE_D)])

    def _card(self, parent):
        return tk.Frame(parent, bg=SURF, highlightbackground=BORDER, highlightcolor=BORDER, highlightthickness=1)

    def _caption(self, parent, text):
        return tk.Label(parent, text=text, bg=SURF, fg=MUT, font=(self.F, 9, "bold"))

    def _pill(self, parent, text, bg, fg):
        tk.Label(parent, text=text, bg=bg, fg=fg, font=(self.F, 9, "bold"), padx=10, pady=2).pack(side="left", padx=(0, 6))

    def _draw_gradient(self, e):
        c = self.grad
        c.delete("all")
        w = max(1, e.width)
        a = tuple(int(PURPLE[i:i + 2], 16) for i in (1, 3, 5))
        b = tuple(int(GREEN[i:i + 2], 16) for i in (1, 3, 5))
        step = 4
        for x in range(0, w, step):
            t = x / w
            col = "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
            c.create_rectangle(x, 0, x + step, 3, fill=col, outline="")

    def set_verdict(self, text, color=None):
        if not text:
            self.vbox.pack_forget()
            return
        self.verdict.configure(text=text, fg=color or FG)
        self.vstripe.configure(bg=color or MUT)
        self.vbox.pack(fill="x", padx=18, pady=(4, 6), before=self.vanchor)

    # ------------------------------------------------------------ selecao
    def pick_demo(self):
        p = filedialog.askopenfilename(title=T("pick_demo"), filetypes=[("Demo GoldSrc", "*.dem"), (T("all_files"), "*.*")])
        if p:
            self.demo.set(p)

    def pick_folder(self):
        p = filedialog.askdirectory(title=T("pick_folder"))
        if p:
            self.demo.set(p)

    def pick_maps(self):
        p = filedialog.askdirectory(title=T("pick_maps"))
        if p:
            self.maps.set(p)

    # ------------------------------------------------------------ analise
    def start(self):
        path = self.demo.get().strip()
        if os.path.isdir(path):
            demos = sorted(glob.glob(os.path.join(path, "*.dem")))
            if not demos:
                messagebox.showwarning("Vidalia", T("no_dem_in_folder"))
                return
        elif os.path.isfile(path):
            demos = [path]
        else:
            messagebox.showwarning("Vidalia", T("select_demo"))
            return
        self.btn.configure(state="disabled")
        self.btn_html.configure(state="disabled", text=T("btn_report"))
        self.results = []
        self.last_html = None
        self.tree.delete(*self.tree.get_children())
        self.set_verdict("")
        self.render_chat()
        self.set_progress(0)
        self.pb.configure(style="Run.Horizontal.TProgressbar")
        self.ctl = AnalysisControl()
        self.running = True
        self.cur = (0, len(demos), os.path.basename(demos[0]))
        self.update_buttons()
        self.update_status()
        folder = path if os.path.isdir(path) else None
        threading.Thread(target=self.work, args=(demos, self.maps.get().strip() or None, folder, self.ctl),
                         daemon=True).start()

    def work(self, demos, maps, folder, ctl):
        n = len(demos)
        done = []

        def progress(k, f):
            ctl.checkpoint()   # pausa aqui enquanto pausado; levanta Cancelled se cancelado
            self.q.put(("p", (k, n, f)))

        try:
            for k, d in enumerate(demos):
                ctl.checkpoint()
                self.q.put(("start", (k, n, d)))
                try:
                    rep = analyze(d, maps, progress=lambda f, k=k: progress(k, f))
                    base = os.path.splitext(d)[0] + "_vidalia"
                    save_json(rep, base + ".json")
                    save_csv(rep, base + "_evidencias.csv")
                    save_html(rep, base + ".html")
                    save_chat_txt(rep, base + "_chat.txt")
                    done.append((d, rep))
                    self.q.put(("one", (d, rep, base)))
                except Cancelled:
                    raise
                except Exception as e:  # noqa: BLE001
                    self.q.put(("fail", (d, str(e))))
        except Cancelled:
            self.q.put(("cancelled", (len(done), n)))
            return
        summary = None
        if folder and n > 1:
            try:
                summary = save_batch(done, os.path.join(folder, "vidalia_resumo"))
            except Exception as e:  # noqa: BLE001
                self.q.put(("fail", (folder, "resumo: %s" % e)))
        self.q.put(("done", summary))

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "p":
                    k, n, f = val
                    self.set_progress((k + f) / n * 100)
                    self.update_status()
                elif kind == "start":
                    k, n, d = val
                    self.cur = (k, n, os.path.basename(d))
                    self.set_progress(k / n * 100)
                    self.update_status()
                elif kind == "one":
                    d, rep, base = val
                    rep["_base"] = base
                    self.results.append((d, rep))
                    self.last_html = base + ".html"
                    self.render()
                elif kind == "fail":
                    d, err = val
                    self.tree.insert("", "end", text=os.path.basename(d), values=(T("error"), err), tags=(SUSPEITO,))
                elif kind == "done":
                    self.finish(val)
                elif kind == "cancelled":
                    self.finish(None, cancelled=val)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def finish(self, summary, cancelled=None):
        self.running = False
        self.ctl = None
        self.update_buttons()
        self.pb.configure(style="Run.Horizontal.TProgressbar")
        self.pct_lbl.configure(fg=GREEN)
        if not cancelled:
            self.set_progress(100)
        if summary:
            self.last_html = summary
        if self.last_html:
            self.btn_html.configure(state="normal")
        self._fill_det_filter()
        self._refresh_verdict()
        if len(self.results) == 1:
            rep = self.results[0][1]
            self._say("saved_single", rep["_base"], rep["decodificacao"].get("cobertura_rede", 0))
        elif self.results:
            self._say("saved_summary", summary or "-")
        if cancelled:
            ok, n = cancelled
            self._say("cancelled", self.pct.get() or "0%", ok, n, suffix_key=None if n == 1 else "no_summary")
        self.render()

    def _say(self, key, *args, suffix_key=None):
        """Mensagem de status guardada como (chave, argumentos) para ser retraduzida ao trocar de idioma."""
        self._last_status = (key, args, suffix_key)
        self.status.set((T(key) % args if args else T(key)) + (T(suffix_key) if suffix_key else ""))

    def _refresh_verdict(self):
        """Faixa de veredito a partir dos resultados (no idioma atual)."""
        if not self.results:
            self.set_verdict("")
            return
        if len(self.results) == 1:
            rep = self.results[0][1]
            g = rep["gravador"]
            self.set_verdict(T("verdict_single") % (
                status(rep["veredito"]).upper(), rep.get("pontuacao", 0), score_text(rep.get("pontuacao", 0)),
                g["nome"], g["kills"], g["headshots"], rep["demo"]["mapa"]), COL[rep["veredito"]])
            return
        worst = max((LEVEL[r["veredito"]] for _, r in self.results), default=-1)
        v = {2: SUSPEITO, 1: ATENCAO, 0: OK}.get(worst, SEM_DADOS)
        cnt = {k: sum(1 for _, r in self.results if r["veredito"] == k) for k in (SUSPEITO, ATENCAO, OK)}
        self.set_verdict(T("verdict_multi") % (len(self.results), cnt[SUSPEITO], cnt[ATENCAO], cnt[OK]), COL[v])

    def _fill_det_filter(self):
        raw = sorted({r["detector"] for _, rep in self.results for r in rep["detectores"]})
        self._det_map = {detector(d): d for d in raw}
        self.cb_det.configure(values=[T("all_detectors")] + list(self._det_map))
        inv = {v: k for k, v in self._det_map.items()}
        self.f_det.set(inv.get(self.det_filter, T("all_detectors")))

    def _on_filter(self):
        vals = T("filters")
        self.sev_idx = vals.index(self.f_sev.get()) if self.f_sev.get() in vals else 1
        self.det_filter = getattr(self, "_det_map", {}).get(self.f_det.get())
        self.render()

    def change_lang(self):
        code = next((c for c, n in LANGS if n == self.lang_var.get()), "pt")
        if code == get_lang():
            return
        set_lang(code)
        save_lang(code)
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        # restaura o estado da tela no novo idioma
        self.set_progress(self._pv)
        self.update_buttons()
        if self.running and self.ctl and self.ctl.paused:
            self.pb.configure(style="Paused.Horizontal.TProgressbar")
            self.pct_lbl.configure(fg=AMBER)
        if self.last_html and not self.running:
            self.btn_html.configure(state="normal")
        self._fill_det_filter()
        if self.running:
            self.update_status()
        else:
            self._refresh_verdict()
            last = getattr(self, "_last_status", None)
            if last:
                self._say(last[0], *last[1], suffix_key=last[2])
        self.render()

    # ------------------------------------------------------------ controle
    def set_progress(self, value):
        value = max(0.0, min(100.0, value))
        self._pv = value
        self.pb["value"] = value
        self.pct.set("%d%%" % int(value))

    def update_status(self):
        if not self.running or not self.cur:
            return
        k, n, name = self.cur
        paused = bool(self.ctl and self.ctl.paused)
        if n > 1:
            what = T("paused_n" if paused else "analyzing_n") % (k + 1, n, name)
        else:
            what = "%s %s" % (T("paused") if paused else T("analyzing"), name)
        self.status.set("%s  ·  %s" % (what, self.pct.get()))

    def update_buttons(self):
        run = self.running
        paused = bool(run and self.ctl and self.ctl.paused)
        self.btn.configure(state="disabled" if run else "normal")
        self.btn_pause.configure(state="normal" if run and not paused else "disabled")
        self.btn_resume.configure(state="normal" if paused else "disabled")
        self.btn_cancel.configure(state="normal" if run else "disabled")

    def pause(self):
        if self.running and self.ctl:
            self.ctl.pause()
            self.pb.configure(style="Paused.Horizontal.TProgressbar")
            self.pct_lbl.configure(fg=AMBER)
            self.update_buttons()
            self.update_status()

    def resume(self):
        if self.running and self.ctl:
            self.ctl.resume()
            self.pb.configure(style="Run.Horizontal.TProgressbar")
            self.pct_lbl.configure(fg=GREEN)
            self.update_buttons()
            self.update_status()

    def cancel(self):
        if not (self.running and self.ctl):
            return
        if not messagebox.askyesno("Vidalia", T("cancel_q")):
            return
        if self.ctl:
            self.ctl.cancel()
            self.btn_pause.configure(state="disabled")
            self.btn_resume.configure(state="disabled")
            self.btn_cancel.configure(state="disabled")
            self._say("cancelling")

    def on_close(self):
        if self.ctl:
            self.ctl.cancel()
        self.root.destroy()

    # ------------------------------------------------------------ exibicao
    def render(self):
        self.tree.delete(*self.tree.get_children())
        det = self.det_filter
        min_lvl = {0: -1, 1: 1, 2: 2}[self.sev_idx]
        multi = len(self.results) > 1
        items = sorted(self.results, key=lambda pr: -pr[1].get("pontuacao", 0)) if multi else self.results
        for path, rep in items:
            parent = ""
            if multi:
                g = rep["gravador"]
                parent = self.tree.insert("", "end", iid="demo:%s" % path, text=os.path.basename(path),
                                          values=(status(rep["veredito"]), T("demo_row")
                                                  % (rep.get("pontuacao", 0), g["nome"], g["kills"], rep["demo"]["mapa"])),
                                          tags=(rep["veredito"], "demo"), open=LEVEL[rep["veredito"]] >= 1)
            for r in rep["detectores"]:
                if det and r["detector"] != det:
                    continue
                if min_lvl > -1 and LEVEL[r["status"]] < min_lvl and not det:
                    continue
                node = self.tree.insert(parent, "end", text=detector(r["detector"]), values=(status(r["status"]), r["resumo"]),
                                        tags=(r["status"],), open=LEVEL[r["status"]] >= 1)
                for e in r["evidencias"][:300]:
                    g = e.get("gravidade", "")
                    if LEVEL.get(g, 0) < min_lvl:
                        continue
                    self.tree.insert(node, "end", text="  %s" % e.get("tempo", ""),
                                     values=(status(g), e.get("descricao", "")), tags=(g,))

        self.render_chat()

    def on_select(self, _e):
        sel = self.tree.selection()
        if sel and sel[0].startswith("demo:"):
            path = sel[0][5:]
            for p, rep in self.results:
                if p == path:
                    self.last_html = rep["_base"] + ".html"
                    self.btn_html.configure(state="normal", text=T("btn_report_of") % os.path.basename(p)[:30])

    def open_html(self):
        if self.last_html and os.path.exists(self.last_html):
            webbrowser.open("file:///" + os.path.abspath(self.last_html).replace("\\", "/"))


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
