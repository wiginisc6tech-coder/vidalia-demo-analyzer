"""Interface grafica (Tkinter) do Vidalia Demo Analyzer."""
import glob
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .detectors import ATENCAO, OK, SEM_DADOS, SUSPEITO
from .report import analyze, save_batch, save_csv, save_html, save_json

BG, CARD, FG, MUT, ACC = "#0f172a", "#111c33", "#e2e8f0", "#94a3b8", "#60a5fa"
COL = {SUSPEITO: "#dc2626", ATENCAO: "#d97706", OK: "#16a34a", SEM_DADOS: "#6b7280"}
LEVEL = {SEM_DADOS: -1, OK: 0, ATENCAO: 1, SUSPEITO: 2}
FILTERS = ["Todas as evidencias", "Somente Atencao e Suspeito", "Somente Suspeito"]


class App:
    def __init__(self, root):
        self.root = root
        root.title("Vidalia Demo Analyzer %s" % __version__)
        root.geometry("1060x720")
        root.minsize(860, 580)
        root.configure(bg=BG)
        self.q = queue.Queue()
        self.demo = tk.StringVar()
        self.maps = tk.StringVar()
        self.status = tk.StringVar(value="Selecione uma demo (.dem) ou uma pasta de demos para iniciar.")
        self.f_sev = tk.StringVar(value=FILTERS[1])
        self.f_det = tk.StringVar(value="Todos os detectores")
        self.last_html = None
        self.results = []   # [(caminho, relatorio)]

        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        st.configure("Mut.TLabel", background=BG, foreground=MUT, font=("Segoe UI", 9))
        st.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI", 22, "bold"))
        st.configure("Sub.TLabel", background=BG, foreground=ACC, font=("Segoe UI", 10))
        st.configure("TButton", font=("Segoe UI", 10), padding=6)
        st.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=FG, rowheight=26, font=("Segoe UI", 10))
        st.configure("Treeview.Heading", background="#1e293b", foreground=FG, font=("Segoe UI", 10, "bold"))
        st.map("Treeview", background=[("selected", "#1d4ed8")])
        st.configure("Horizontal.TProgressbar", troughcolor=CARD, background=ACC)

        top = ttk.Frame(root, padding=(18, 14, 18, 4))
        top.pack(fill="x")
        ttk.Label(top, text="VIDALIA", style="Title.TLabel").pack(anchor="w")
        ttk.Label(top, text="DEMO ANALYZER  ·  %s  ·  triagem de demos CS 1.6 (GoldSrc)" % __version__,
                  style="Sub.TLabel").pack(anchor="w")

        form = ttk.Frame(root, padding=(18, 8))
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Demo ou pasta:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.demo).grid(row=0, column=1, sticky="ew", padx=8)
        bx = ttk.Frame(form)
        bx.grid(row=0, column=2)
        ttk.Button(bx, text="Demo...", command=self.pick_demo).pack(side="left")
        ttk.Button(bx, text="Pasta de demos...", command=self.pick_folder).pack(side="left", padx=(6, 0))
        ttk.Label(form, text="Mapas (opcional):").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.maps).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(form, text="Pasta...", command=self.pick_maps).grid(row=1, column=2, sticky="w")
        ttk.Label(form, text="Informe a pasta cstrike\\maps para habilitar a analise de wallhack.",
                  style="Mut.TLabel").grid(row=2, column=1, sticky="w", padx=8)

        bar = ttk.Frame(root, padding=(18, 6))
        bar.pack(fill="x")
        self.btn = ttk.Button(bar, text="Analisar", style="Accent.TButton", command=self.start)
        self.btn.pack(side="left")
        self.btn_html = ttk.Button(bar, text="Abrir relatorio completo", command=self.open_html, state="disabled")
        self.btn_html.pack(side="left", padx=8)
        self.pb = ttk.Progressbar(bar, mode="determinate", maximum=100, length=220)
        self.pb.pack(side="right")

        flt = ttk.Frame(root, padding=(18, 2))
        flt.pack(fill="x")
        ttk.Label(flt, text="Mostrar:").pack(side="left")
        cb1 = ttk.Combobox(flt, textvariable=self.f_sev, values=FILTERS, state="readonly", width=28)
        cb1.pack(side="left", padx=6)
        self.cb_det = ttk.Combobox(flt, textvariable=self.f_det, values=["Todos os detectores"], state="readonly", width=40)
        self.cb_det.pack(side="left", padx=6)
        cb1.bind("<<ComboboxSelected>>", lambda e: self.render())
        self.cb_det.bind("<<ComboboxSelected>>", lambda e: self.render())

        self.verdict = tk.Label(root, text="", bg=BG, fg=FG, font=("Segoe UI", 14, "bold"), anchor="w", padx=18)
        self.verdict.pack(fill="x", pady=(6, 0))

        body = ttk.Frame(root, padding=(18, 6, 18, 6))
        body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(body, columns=("status", "resumo"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Demo / detector")
        self.tree.heading("status", text="Status")
        self.tree.heading("resumo", text="Resumo / evidencia")
        self.tree.column("#0", width=300, stretch=False)
        self.tree.column("status", width=100, stretch=False, anchor="center")
        self.tree.column("resumo", width=600)
        for k, c in COL.items():
            self.tree.tag_configure(k, foreground=c)
        self.tree.tag_configure("demo", font=("Segoe UI", 10, "bold"))
        sb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        foot = ttk.Frame(root, padding=(18, 4, 18, 12))
        foot.pack(fill="x")
        ttk.Label(foot, textvariable=self.status, style="Mut.TLabel").pack(anchor="w")
        ttk.Label(foot, text="Resultado de triagem: nao comprova trapaca. Revise a demo nos momentos indicados.",
                  style="Mut.TLabel").pack(anchor="w")
        root.after(100, self.poll)

    # ------------------------------------------------------------ selecao
    def pick_demo(self):
        p = filedialog.askopenfilename(title="Selecionar demo", filetypes=[("Demo GoldSrc", "*.dem"), ("Todos", "*.*")])
        if p:
            self.demo.set(p)

    def pick_folder(self):
        p = filedialog.askdirectory(title="Pasta com demos (.dem)")
        if p:
            self.demo.set(p)

    def pick_maps(self):
        p = filedialog.askdirectory(title="Pasta de mapas (cstrike\\maps)")
        if p:
            self.maps.set(p)

    # ------------------------------------------------------------ analise
    def start(self):
        path = self.demo.get().strip()
        if os.path.isdir(path):
            demos = sorted(glob.glob(os.path.join(path, "*.dem")))
            if not demos:
                messagebox.showwarning("Vidalia", "Nenhum arquivo .dem nessa pasta.")
                return
        elif os.path.isfile(path):
            demos = [path]
        else:
            messagebox.showwarning("Vidalia", "Selecione um arquivo .dem ou uma pasta com demos.")
            return
        self.btn.configure(state="disabled")
        self.btn_html.configure(state="disabled")
        self.results = []
        self.tree.delete(*self.tree.get_children())
        self.verdict.configure(text="")
        self.pb["value"] = 0
        self.status.set("Analisando %d demo(s)..." % len(demos))
        folder = path if os.path.isdir(path) else None
        threading.Thread(target=self.work, args=(demos, self.maps.get().strip() or None, folder), daemon=True).start()

    def work(self, demos, maps, folder):
        n = len(demos)
        done = []
        for k, d in enumerate(demos):
            try:
                rep = analyze(d, maps, progress=lambda f, k=k: self.q.put(("p", (k + f) / n)))
                base = os.path.splitext(d)[0] + "_vidalia"
                save_json(rep, base + ".json")
                save_csv(rep, base + "_evidencias.csv")
                save_html(rep, base + ".html")
                done.append((d, rep))
                self.q.put(("one", (d, rep, base)))
            except Exception as e:  # noqa: BLE001
                self.q.put(("fail", (d, str(e))))
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
                    self.pb["value"] = val * 100
                elif kind == "one":
                    d, rep, base = val
                    rep["_base"] = base
                    self.results.append((d, rep))
                    self.last_html = base + ".html"
                    self.render()
                elif kind == "fail":
                    d, err = val
                    self.tree.insert("", "end", text=os.path.basename(d), values=("Erro", err), tags=(SUSPEITO,))
                elif kind == "done":
                    self.finish(val)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def finish(self, summary):
        self.btn.configure(state="normal")
        self.pb["value"] = 100
        if summary:
            self.last_html = summary
        if self.last_html:
            self.btn_html.configure(state="normal")
        dets = sorted({r["detector"] for _, rep in self.results for r in rep["detectores"]})
        self.cb_det.configure(values=["Todos os detectores"] + dets)
        if len(self.results) == 1:
            rep = self.results[0][1]
            g = rep["gravador"]
            self.verdict.configure(
                text="Triagem: %s   ·   %s  (%d kills, %d HS, %d mortes)   ·   mapa %s"
                % (rep["veredito"].upper(), g["nome"], g["kills"], g["headshots"], g["mortes"], rep["demo"]["mapa"]),
                fg=COL[rep["veredito"]])
            self.status.set("Relatorios salvos em %s.(html/json) e _evidencias.csv  ·  rede decodificada: %s%%"
                            % (rep["_base"], rep["decodificacao"].get("cobertura_rede", 0)))
        else:
            worst = max((LEVEL[r["veredito"]] for _, r in self.results), default=-1)
            v = {2: SUSPEITO, 1: ATENCAO, 0: OK}.get(worst, SEM_DADOS)
            cnt = {k: sum(1 for _, r in self.results if r["veredito"] == k) for k in (SUSPEITO, ATENCAO, OK)}
            self.verdict.configure(text="%d demos: %d Suspeito · %d Atencao · %d Normal"
                                   % (len(self.results), cnt[SUSPEITO], cnt[ATENCAO], cnt[OK]), fg=COL[v])
            self.status.set("Relatorio de resumo: %s" % (summary or "-"))
        self.render()

    # ------------------------------------------------------------ exibicao
    def render(self):
        self.tree.delete(*self.tree.get_children())
        sev = self.f_sev.get()
        det = self.f_det.get()
        min_lvl = {FILTERS[0]: -1, FILTERS[1]: 1, FILTERS[2]: 2}[sev]
        multi = len(self.results) > 1
        for path, rep in self.results:
            parent = ""
            if multi:
                g = rep["gravador"]
                parent = self.tree.insert("", "end", iid="demo:%s" % path, text=os.path.basename(path),
                                          values=(rep["veredito"], "%s · %d kills · mapa %s" % (g["nome"], g["kills"], rep["demo"]["mapa"])),
                                          tags=(rep["veredito"], "demo"), open=LEVEL[rep["veredito"]] >= 1)
            for r in rep["detectores"]:
                if det != "Todos os detectores" and r["detector"] != det:
                    continue
                if min_lvl > -1 and LEVEL[r["status"]] < min_lvl and det == "Todos os detectores":
                    continue
                node = self.tree.insert(parent, "end", text=r["detector"], values=(r["status"], r["resumo"]),
                                        tags=(r["status"],), open=LEVEL[r["status"]] >= 1)
                for e in r["evidencias"][:300]:
                    g = e.get("gravidade", "")
                    if LEVEL.get(g, 0) < min_lvl:
                        continue
                    self.tree.insert(node, "end", text="  %s" % e.get("tempo", ""),
                                     values=(g, e.get("descricao", "")), tags=(g,))

    def on_select(self, _e):
        sel = self.tree.selection()
        if sel and sel[0].startswith("demo:"):
            path = sel[0][5:]
            for p, rep in self.results:
                if p == path:
                    self.last_html = rep["_base"] + ".html"
                    self.btn_html.configure(state="normal", text="Abrir relatorio de %s" % os.path.basename(p)[:30])

    def open_html(self):
        if self.last_html and os.path.exists(self.last_html):
            webbrowser.open("file:///" + os.path.abspath(self.last_html).replace("\\", "/"))


def run():
    root = tk.Tk()
    App(root)
    root.mainloop()
