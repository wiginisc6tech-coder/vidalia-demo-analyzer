"""Video real dos momentos: abre o CS 1.6 do usuario na demo e grava o trecho apontado.

Como funciona (sem cortar a demo):
1. Copia a demo para <CS>/<mod>/vidalia/ inserindo comandos de console nos tempos certos
   (veja demo_edit.py): avanco rapido ate pouco antes do trecho, velocidade normal, `startmovie`
   no inicio do trecho, `endmovie` + `quit` no fim.
2. Abre o hl.exe em janela com `+playdemo`.
3. Quando o jogo fecha, junta os quadros que o `startmovie` gravou (BMP/TGA), converte para PNG
   (o Tkinter abre PNG sem bibliotecas extras) e guarda ao lado da demo, para abrir na hora da proxima vez.
4. Se o ffmpeg estiver instalado, tambem gera um MP4.

Nada aqui altera a demo original.
"""
import glob
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import zlib

from .bsp import default_map_folders
from .demo_edit import inject_commands
from .i18n import _config_path, load_setting, save_setting
from .replay import ANTES, DEPOIS

FPS = 30
WIDTH, HEIGHT = 1280, 720
FF_RATE = 0.2          # host_framerate do avanco rapido (segundos de demo por quadro renderizado)
SLOW_BEFORE = 1.5      # volta a velocidade normal este tanto antes de comecar a gravar
TIMEOUT = 15 * 60      # tempo maximo esperando o jogo


class GameError(Exception):
    pass


# ---------------------------------------------------------------- localizar o jogo
def _exe_in(folder):
    for name in ("hl.exe", "cstrike.exe", "hl_linux", "hl.sh"):
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            return p
    return None


def find_game(demo_path=None):
    """Caminho do executavel do Half-Life/CS 1.6 (configurado ou procurado nas pastas padrao)."""
    saved = load_setting("hl_exe")
    if saved and os.path.isfile(saved):
        return saved
    for folder in default_map_folders(demo_path):
        # default_map_folders devolve pastas .../cstrike; o executavel fica uma pasta acima
        for cand in (os.path.dirname(folder.rstrip("\\/")), folder):
            exe = _exe_in(cand) if cand and os.path.isdir(cand) else None
            if exe:
                return exe
    return None


def set_game(path):
    save_setting("hl_exe", path)


def set_ffmpeg(path):
    save_setting("ffmpeg", path)


def find_ffmpeg():
    saved = load_setting("ffmpeg")
    if saved and os.path.isfile(saved):
        return saved
    here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    for cand in (os.path.join(here, "ffmpeg.exe"), os.path.join(here, "ffmpeg")):
        if os.path.isfile(cand):
            return cand
    return shutil.which("ffmpeg")


def map_installed(exe, mod, mapa):
    root = os.path.dirname(exe)
    for d in (mod, mod + "_downloads", "cstrike", "cstrike_downloads", "valve"):
        if os.path.isfile(os.path.join(root, d, "maps", mapa + ".bsp")):
            return True
    return False


# ---------------------------------------------------------------- cache do video
def video_dir(rp, m):
    base = os.path.splitext(rp.demo)[0] + "_vidalia_videos"
    return os.path.join(base, "frame_%d" % m.frame)


def load_video(rp, m):
    """Metadados do video ja gravado deste momento (ou None)."""
    d = video_dir(rp, m)
    try:
        with open(os.path.join(d, "video.json"), encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:  # noqa: BLE001
        return None
    meta["dir"] = d
    meta["frames"] = sorted(glob.glob(os.path.join(d, "f*.png")))
    if not meta["frames"]:
        return None
    mp4 = os.path.join(d, "video.mp4")
    meta["mp4"] = mp4 if os.path.isfile(mp4) else None
    wav = os.path.join(d, "audio.wav")
    meta["audio"] = wav if os.path.isfile(wav) else None
    return meta


# ---------------------------------------------------------------- preparar e abrir
def window_of(rp, m):
    """(inicio, alvo, fim) do trecho em tempo absoluto da demo."""
    alvo = rp.t0 + m.tempo_s
    return max(rp.t0, alvo - ANTES), alvo, alvo + DEPOIS


def prepare(rp, m, exe, record):
    """Gera a copia da demo com os comandos. Devolve (nome_para_playdemo, prefixo_do_movie)."""
    if not rp.demo or not os.path.isfile(rp.demo):
        raise GameError("demo_missing")
    root = os.path.dirname(exe)
    mod = rp.jogo or "cstrike"
    outdir = os.path.join(root, mod, "vidalia")
    try:
        os.makedirs(outdir, exist_ok=True)
    except OSError as e:
        raise GameError("no_write:%s" % e)
    start, alvo, end = window_of(rp, m)
    log("demo %s  momento %s (frame %d)  trecho %.2f-%.2f  mod %s  jogo %s" % (
        rp.demo, m.tempo, m.frame, start, end, mod, exe))
    tag = "vdl%d" % (m.frame % 100000)
    name = "%s_%s" % (tag, "rec" if record else "ver")
    cmds = [(0.0, "host_framerate %g" % FF_RATE)]
    if record:
        cmds += [(start - SLOW_BEFORE, "host_framerate 0"),
                 (start, "startmovie %s %d" % (tag, FPS)),
                 (end, "endmovie"),
                 (end + 0.05, "quit")]
    else:
        cmds += [(start - SLOW_BEFORE, "host_framerate 0")]
    try:
        inject_commands(rp.demo, os.path.join(outdir, name + ".dem"), cmds)
    except OSError as e:
        raise GameError("no_write:%s" % e)
    return "vidalia/" + name, tag


# ---------------------------------------------------------------- registro (para diagnostico)
def log_path():
    return os.path.join(os.path.dirname(_config_path()), "jogo.log")


def log(msg):
    try:
        p = log_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if os.path.exists(p) and os.path.getsize(p) > 512 * 1024:
            os.remove(p)
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:  # noqa: BLE001
        pass


_NO_WINDOW = 0x08000000


def _quiet_kw():
    """Sem janela de console e sem herdar stdin/stdout (o .exe --windowed nao tem console)."""
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if sys.platform == "win32":
        kw["creationflags"] = _NO_WINDOW
    return kw


def process_running(image):
    """True se existe um processo com esse nome (Windows: tasklist)."""
    if sys.platform != "win32":
        return False
    try:
        kw = _quiet_kw()
        kw["stdout"] = subprocess.PIPE
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq %s" % image, "/NH"], timeout=10, **kw)
        return image.lower() in r.stdout.decode("latin-1", "replace").lower()
    except Exception:  # noqa: BLE001
        return False


def find_steam(exe):
    """steam.exe, se o jogo for da Steam (pasta steamapps)."""
    if "steamapps" not in exe.lower().replace("\\", "/"):
        return None
    d = os.path.dirname(exe)
    for _ in range(6):
        cand = os.path.join(d, "steam.exe")
        if os.path.isfile(cand):
            return cand
        d = os.path.dirname(d)
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                cand = winreg.QueryValueEx(k, "SteamExe")[0]
                if cand and os.path.isfile(cand):
                    return cand
        except OSError:
            pass
    return None


class GameProcess:
    """O jogo em execucao. Pela Steam o lancador termina na hora e o jogo continua em outro processo,
    entao acompanhamos tambem pelo nome do executavel (hl.exe)."""
    START_WAIT = 60.0

    def __init__(self, proc, image):
        self.proc, self.image = proc, image
        self.t0 = time.time()
        self.seen = False

    def running(self):
        if self.proc.poll() is None:
            return True
        if self.exit_t is None:
            self.exit_t = time.time()
            log("processo iniciado terminou (codigo %s) apos %.1f s" % (self.proc.returncode, self.exit_t - self.t0))
        if process_running(self.image):
            self.seen = True
            return True
        # lancador (Steam) ou hl.exe que se reabriu pela Steam: espera o jogo aparecer
        relaunch = sys.platform == "win32" and (self.via_launcher or self.exit_t - self.t0 < 10.0)
        if relaunch and not self.seen and time.time() - self.t0 < self.START_WAIT:
            return True
        return False

    via_launcher = False
    exit_t = None

    def terminate(self):
        try:
            self.proc.terminate()
        except Exception:  # noqa: BLE001
            pass
        if self.seen and sys.platform == "win32":
            subprocess.run(["taskkill", "/IM", self.image, "/F"], timeout=10, **_quiet_kw())

    def wait(self):
        while self.running():
            time.sleep(1.0)


def launch(exe, mod, demo_rel, record):
    image = os.path.basename(exe)
    if process_running(image):
        log("jogo ja aberto: %s" % image)
        raise GameError("game_running")
    game_args = ["-game", mod, "-novid", "-nojoy", "-window", "-w", str(WIDTH), "-h", str(HEIGHT),
                 "+playdemo", demo_rel]
    steam = find_steam(exe)
    if steam and load_setting("usar_steam", True):
        args = [steam, "-applaunch", "10"] + game_args
    else:
        args = [exe] + game_args
    log("abrindo: %s  (pasta %s)" % (subprocess.list2cmdline(args), os.path.dirname(exe)))
    try:
        proc = subprocess.Popen(args, cwd=os.path.dirname(exe), **_quiet_kw())
    except OSError as e:
        log("falha ao abrir: %r" % e)
        raise GameError("launch:%s" % e)
    gp = GameProcess(proc, image)
    gp.via_launcher = bool(steam and args[0] == steam)
    return gp


# ---------------------------------------------------------------- preserva as configuracoes de video do usuario
# -window/-w/-h podem ficar salvos como preferencia do jogo; guardamos e restauramos depois.
_REG_KEY = r"Software\Valve\Half-Life\Settings"
_REG_VALUES = ("ScreenWidth", "ScreenHeight", "ScreenWindowed", "ScreenBPP", "EngineD3D")


def snapshot_settings(exe, mod):
    snap = {"files": {}, "reg": None}
    root = os.path.dirname(exe)
    for p in (os.path.join(root, "video.txt"), os.path.join(root, mod, "video.txt")):
        try:
            with open(p, "rb") as f:
                snap["files"][p] = f.read()
        except OSError:
            pass
    if sys.platform == "win32":
        try:
            import winreg
            vals = {}
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as k:
                for name in _REG_VALUES:
                    try:
                        vals[name] = winreg.QueryValueEx(k, name)
                    except OSError:
                        pass
            snap["reg"] = vals
        except OSError:
            pass
    return snap


def restore_settings(snap):
    for p, data in snap["files"].items():
        try:
            with open(p, "rb") as f:
                if f.read() == data:
                    continue
        except OSError:
            pass
        try:
            with open(p, "wb") as f:
                f.write(data)
        except OSError:
            pass
    if snap.get("reg") and sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE) as k:
                for name, (val, typ) in snap["reg"].items():
                    winreg.SetValueEx(k, name, 0, typ, val)
        except OSError:
            pass


def record(rp, m, exe, progress=None, cancel=None):
    """Grava o trecho e devolve os metadados do video (bloqueia ate o jogo fechar)."""
    mod = rp.jogo or "cstrike"
    root = os.path.dirname(exe)
    demo_rel, tag = prepare(rp, m, exe, record=True)
    for old in _movie_files(root, mod, tag) + _movie_audio(root, mod, tag):
        _rm(old)
    t_launch = time.time()
    snap = snapshot_settings(exe, mod)
    try:
        proc = launch(exe, mod, demo_rel, record=True)
        if progress:
            progress("game")
        while proc.running():
            if cancel and cancel():
                proc.terminate()
                raise GameError("cancelled")
            if time.time() - t_launch > TIMEOUT:
                proc.terminate()
                raise GameError("timeout")
            time.sleep(0.5)
        # alguns lancadores (Steam) devolvem logo: espera os quadros pararem de crescer
        files = _wait_movie(root, mod, tag, t_launch, cancel)
    finally:
        restore_settings(snap)
    log("quadros encontrados: %d" % len(files))
    if not files:
        raise GameError("no_frames")
    if progress:
        progress("convert")
    start, alvo, end = window_of(rp, m)
    d = video_dir(rp, m)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    w = h = 0
    for k, src in enumerate(files):
        if cancel and cancel():
            raise GameError("cancelled")
        w, h, rgb = read_image(src)
        write_png(os.path.join(d, "f%05d.png" % k), w, h, rgb)
        if progress and k % 10 == 0:
            progress("convert", k / len(files))
    for f in files:
        _rm(f)
    wavs = _movie_audio(root, mod, tag)
    if wavs:
        try:
            shutil.move(wavs[0], os.path.join(d, "audio.wav"))
        except OSError:
            pass
        for f in wavs[1:]:
            _rm(f)
    meta = dict(fps=FPS, t_inicio=round(start - rp.t0, 4), t_alvo=round(alvo - rp.t0, 4), quadros=len(files),
                largura=w, altura=h, gravado_em=time.strftime("%Y-%m-%d %H:%M:%S"))
    with open(os.path.join(d, "video.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    ff = find_ffmpeg()
    if ff:
        if progress:
            progress("mp4")
        try:
            export_mp4(ff, d)
        except Exception:  # noqa: BLE001  (o MP4 e um extra; os PNG ja bastam)
            pass
    _rm(os.path.join(root, mod, demo_rel.replace("/", os.sep) + ".dem"))
    return load_video(rp, m)


def watch(rp, m, exe):
    """Abre o jogo no momento, sem gravar (o usuario assiste e fecha quando quiser).
    Bloqueia ate o jogo fechar e restaura as configuracoes de video."""
    mod = rp.jogo or "cstrike"
    demo_rel, _ = prepare(rp, m, exe, record=False)
    snap = snapshot_settings(exe, mod)
    try:
        proc = launch(exe, mod, demo_rel, record=False)
        proc.wait()
        log("jogo fechado")
    finally:
        restore_settings(snap)
        _rm(os.path.join(os.path.dirname(exe), mod, demo_rel.replace("/", os.sep) + ".dem"))


def export_mp4(ffmpeg, d, out=None, speed=1.0, mark=None, audio=True):
    """Gera um MP4 com os quadros de `d`.

    speed: 1.0 normal, 0.5 = camera lenta. mark: segundos (no video original) do apontamento,
    destacado com uma borda vermelha. audio: inclui o audio.wav gravado pelo jogo, se existir."""
    out = out or os.path.join(d, "video.mp4")
    wav = os.path.join(d, "audio.wav")
    use_audio = audio and os.path.isfile(wav) and os.path.getsize(wav) > 44
    vf = ["scale=trunc(iw/2)*2:trunc(ih/2)*2"]
    if speed != 1.0:
        vf.append("setpts=PTS/%g" % speed)
    if mark is not None:
        a = max(0.0, mark - 0.5 / FPS) / speed
        b = (mark + 0.35) / speed
        vf.append("drawbox=x=0:y=0:w=iw:h=ih:color=red@0.9:t=12:enable='between(t,%.3f,%.3f)'" % (a, b))
    base = [ffmpeg, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "f%05d.png")]
    if use_audio:
        base += ["-i", wav]
    base += ["-vf", ",".join(vf)]
    if use_audio:
        tempo, af = speed, []
        while tempo < 0.5:
            af.append("atempo=0.5")
            tempo /= 0.5
        af.append("atempo=%g" % tempo)
        base += ["-af", ",".join(af), "-c:a", "aac", "-b:a", "160k", "-shortest"]
    tail = ["-r", str(FPS), "-movflags", "+faststart", out]
    last = None
    for codec in (["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium"],
                  ["-c:v", "mpeg4", "-q:v", "3", "-pix_fmt", "yuv420p"]):
        kw = _quiet_kw()
        kw["stderr"] = subprocess.PIPE
        r = subprocess.run(base + codec + tail, timeout=600, **kw)
        if r.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 0:
            log("mp4 gerado: %s" % out)
            return out
        last = r.stderr.decode("utf-8", "replace").strip()[-400:]
        log("ffmpeg falhou (%s): %s" % (codec[1], last))
    raise GameError("ffmpeg:%s" % (last or "?"))


def _movie_audio(root, mod, tag):
    out = []
    for folder in (os.path.join(root, mod), root):
        out += glob.glob(os.path.join(folder, glob.escape(tag) + "*.wav"))
    return sorted(set(out))


def _movie_files(root, mod, tag):
    out = []
    for folder in (os.path.join(root, mod), root, os.path.join(root, mod, "vidalia")):
        for ext in ("bmp", "tga", "BMP", "TGA"):
            out += glob.glob(os.path.join(folder, glob.escape(tag) + "*." + ext))
    seen, res = set(), []
    for f in out:
        k = os.path.normcase(os.path.abspath(f))
        if k not in seen:
            seen.add(k)
            res.append(f)

    def num(p):
        s = os.path.splitext(os.path.basename(p))[0][len(tag):]
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else -1
    return sorted(res, key=num)


def _wait_movie(root, mod, tag, since, cancel=None, quiet=4.0, limit=TIMEOUT):
    last, stable_since = None, None
    t0 = time.time()
    while time.time() - t0 < limit:
        if cancel and cancel():
            raise GameError("cancelled")
        files = [f for f in _movie_files(root, mod, tag) if os.path.getmtime(f) >= since - 2]
        sig = (len(files), sum(os.path.getsize(f) for f in files))
        if sig != last:
            last, stable_since = sig, time.time()
        elif time.time() - stable_since >= quiet:
            return files
        time.sleep(0.5)
    return _movie_files(root, mod, tag)


def _rm(p):
    try:
        os.remove(p)
    except OSError:
        pass


# ---------------------------------------------------------------- imagens (sem bibliotecas extras)
def read_image(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] == b"BM":
        return read_bmp(data)
    return read_tga(data)


def read_bmp(data):
    """BMP 8/24/32 bits -> (largura, altura, RGB de cima para baixo)."""
    off = struct.unpack_from("<I", data, 10)[0]
    hsize = struct.unpack_from("<I", data, 14)[0]
    w, h = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    comp = struct.unpack_from("<I", data, 30)[0]
    if comp not in (0, 3):
        raise ValueError("BMP comprimido nao suportado")
    top_down = h < 0
    h = abs(h)
    stride = ((w * bpp + 31) // 32) * 4
    rows = []
    if bpp == 8:
        ncol = struct.unpack_from("<I", data, 46)[0] or 256
        pal = data[14 + hsize:14 + hsize + 4 * ncol]
        lut = [bytes((pal[4 * i + 2], pal[4 * i + 1], pal[4 * i])) for i in range(ncol)]
        for y in range(h):
            r = data[off + y * stride: off + y * stride + w]
            rows.append(b"".join(lut[i] for i in r))
    elif bpp in (24, 32):
        n = bpp // 8
        for y in range(h):
            r = data[off + y * stride: off + y * stride + w * n]
            rows.append(_bgr_to_rgb(r, n, w))
    else:
        raise ValueError("BMP de %d bits nao suportado" % bpp)
    if not top_down:
        rows.reverse()
    return w, h, b"".join(rows)


def read_tga(data):
    """TGA sem compressao ou RLE, 24/32 bits -> (largura, altura, RGB de cima para baixo)."""
    idlen, cmap, itype = data[0], data[1], data[2]
    w, h, bpp, desc = struct.unpack_from("<HHBB", data, 12)
    if itype not in (2, 10) or bpp not in (24, 32) or cmap:
        raise ValueError("TGA nao suportado (tipo %d, %d bits)" % (itype, bpp))
    n = bpp // 8
    p = 18 + idlen
    if itype == 2:
        px = data[p:p + w * h * n]
    else:
        out = bytearray()
        total = w * h * n
        while len(out) < total:
            c = data[p]
            p += 1
            cnt = (c & 0x7F) + 1
            if c & 0x80:
                out += data[p:p + n] * cnt
                p += n
            else:
                out += data[p:p + n * cnt]
                p += n * cnt
        px = bytes(out[:total])
    rows = [_bgr_to_rgb(px[y * w * n:(y + 1) * w * n], n, w) for y in range(h)]
    if not desc & 0x20:   # origem embaixo
        rows.reverse()
    return w, h, b"".join(rows)


def _bgr_to_rgb(row, n, w):
    out = bytearray(w * 3)
    out[0::3] = row[2::n]
    out[1::3] = row[1::n]
    out[2::3] = row[0::n]
    return bytes(out)


def write_png(path, w, h, rgb):
    def chunk(tag, body):
        c = tag + body
        return struct.pack(">I", len(body)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    stride = w * 3
    raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(h))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(raw, 3)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
