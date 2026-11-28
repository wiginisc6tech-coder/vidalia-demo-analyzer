"""Replay dos momentos (aba Momentos): recortes, geometria do mapa e camera."""
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vidalia.bsp import BSP, load_geometry
from vidalia.replay import ANTES, DEPOIS
from vidalia.report import analyze, save_json
import synth


class TestReplay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_momentos_da_demo(self):
        p = os.path.join(self.tmp, "a.dem")
        synth.build_demo(p)
        rep = analyze(p)
        rp = rep["_replay"]
        graves = {(r["detector"], e["frame"], e["descricao"]) for r in rep["detectores"] for e in r["evidencias"]
                  if e["gravidade"] in ("Atencao", "Suspeito")}
        self.assertTrue(graves)
        self.assertEqual(len(rp.momentos), len(graves))
        for m in rp.momentos:
            qs = rp.recorte(m)
            self.assertTrue(qs)
            alvo = rp.quadros[m.alvo]
            self.assertEqual(alvo.frame, m.frame)           # o frame exato do apontamento esta no recorte
            self.assertLessEqual(qs[0].t, alvo.t)
            self.assertGreaterEqual(qs[-1].t, alvo.t)
            self.assertLessEqual(alvo.t - qs[0].t, ANTES + 0.05)
            self.assertLessEqual(qs[-1].t - alvo.t, DEPOIS + 0.05)
        # o replay nao vai para o JSON
        save_json(rep, os.path.join(self.tmp, "a.json"))
        with open(os.path.join(self.tmp, "a.json"), encoding="utf-8") as f:
            self.assertNotIn("_replay", f.read())

    def test_geometria_e_visao(self):
        p = os.path.join(self.tmp, "m.bsp")
        synth.build_box_bsp(p, [((-100, -100, -100), (100, 100, 100)), ((300, -50, 0), (350, 50, 50))])
        g = load_geometry(p)
        self.assertEqual(len(g.polys), 12)
        # normais para fora da caixa
        for vs, n, zr, ctr, water in g.polys[:6]:   # caixa centrada na origem
            self.assertGreater(n[0] * ctr[0] + n[1] * ctr[1] + n[2] * ctr[2], 0)
        self.assertTrue(g.near(0, 0, 10))
        b = BSP(p)
        self.assertFalse(b.visible((-200, 0, 0), (200, 0, 0)))
        self.assertTrue(b.visible((-200, 200, 0), (200, 200, 0)))


class TestCamera(unittest.TestCase):
    def test_projecao(self):
        try:
            from vidalia.replay_view import Camera
        except ImportError:  # tkinter ausente
            self.skipTest("tkinter indisponivel")
        cam = Camera((0, 0, 0), 0, 0, 800, 600)
        x, y = cam.point((100, 0, 0))
        self.assertAlmostEqual(x, 400)
        self.assertAlmostEqual(y, 300)
        self.assertLess(cam.point((100, 50, 0))[0], 400)    # +y fica a esquerda com yaw 0
        self.assertLess(cam.point((100, 0, 50))[1], 300)    # +z fica acima
        self.assertIsNone(cam.point((-100, 0, 0)))          # atras da camera
        cam = Camera((0, 0, 0), 0, 90, 800, 600)
        self.assertAlmostEqual(cam.point((0, 100, 0))[0], 400)
        cam = Camera((0, 0, 0), 89, 0, 800, 600)            # olhando para baixo
        self.assertAlmostEqual(cam.point((1, 0, -100))[0], 400, places=0)


if __name__ == "__main__":
    unittest.main()


class TestVideoReal(unittest.TestCase):
    """Fluxo do botao 'Gravar video real' com um CS falso (tests/fake_hl.py)."""

    def test_injecao_preserva_demo(self):
        from vidalia.demo import ConsoleFrame, iter_frames
        from vidalia.demo_edit import inject_commands
        from vidalia.engine import load
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "a.dem")
        synth.build_demo(src)
        a = load(src)
        t = a.timeline.t[len(a.timeline.t) // 2]
        dst = os.path.join(tmp, "b.dem")
        inject_commands(src, dst, [(0, "host_framerate 0.2"), (t, "startmovie x 30; echo " + "a" * 40 + "; echo " + "b" * 40),
                                   (t + 1, "endmovie; quit")])
        w = []
        b = load(dst)
        self.assertEqual(b.timeline.t, a.timeline.t)
        self.assertEqual(b.timeline.yaw, a.timeline.yaw)
        self.assertEqual(len(b.events), len(a.events))
        cmds = [(f.time, f.command) for f in iter_frames(dst, warnings=w) if isinstance(f, ConsoleFrame)]
        self.assertFalse(w)
        self.assertEqual(len(cmds), 4)                         # o comando longo foi dividido em 2 frames
        self.assertTrue(all(len(c) < 64 for _, c in cmds))
        tm = dict((c.split(";")[0], tt) for tt, c in cmds)
        self.assertAlmostEqual(tm["startmovie x 30"], t, places=3)
        self.assertAlmostEqual(tm["endmovie"], t + 1, delta=0.05)

    def test_imagens(self):
        from vidalia.game import read_image, read_tga, write_png
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import fake_hl
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "x.bmp")
        fake_hl.bmp(p, 5, 3, 1)
        w, h, rgb = read_image(p)
        self.assertEqual((w, h, len(rgb)), (5, 3, 45))
        self.assertEqual(rgb[0:3], bytes((170, 7, 0)))         # topo = ultima linha gravada no BMP
        tga = bytes([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0]) + struct.pack("<HHBB", 2, 1, 24, 0) + bytes([1, 2, 3, 4, 5, 6])
        self.assertEqual(read_tga(tga), (2, 1, bytes([3, 2, 1, 6, 5, 4])))
        write_png(os.path.join(tmp, "x.png"), w, h, rgb)
        with open(os.path.join(tmp, "x.png"), "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")

    @unittest.skipIf(sys.platform == "win32", "o CS falso usa shebang")
    def test_gravacao_com_cs_falso(self):
        import shutil
        import stat
        from vidalia import game
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "demos", "a.dem")
        os.makedirs(os.path.dirname(p))
        synth.build_demo(p)
        rp = analyze(p)["_replay"]
        m = rp.momentos[len(rp.momentos) // 2]
        cs = os.path.join(tmp, "Half-Life")
        os.makedirs(os.path.join(cs, "cstrike", "maps"))
        exe = os.path.join(cs, "hl_linux")
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_hl.py")) as f:
            body = f.read()
        with open(exe, "w") as f:
            f.write("#!%s\n" % sys.executable + body.replace(
                'os.environ.get("VIDALIA_SRC", os.path.dirname(HERE))',
                repr(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
        with open(os.path.join(cs, "video.txt"), "w") as f:
            f.write("original")
        old_wait = game._wait_movie
        game._wait_movie = lambda *a, **k: old_wait(*a, quiet=0.2, **{x: y for x, y in k.items() if x != "quiet"})
        try:
            meta = game.record(rp, m, exe)
        finally:
            game._wait_movie = old_wait
        start, alvo, end = game.window_of(rp, m)
        self.assertAlmostEqual(meta["quadros"], (end - start) * game.FPS, delta=1)
        self.assertEqual(len(meta["frames"]), meta["quadros"])
        self.assertAlmostEqual(meta["t_alvo"], m.tempo_s, places=3)
        self.assertEqual(game.load_video(rp, m)["quadros"], meta["quadros"])
        # limpa os BMP, a demo temporaria e restaura as configuracoes de video
        self.assertFalse([f for f in os.listdir(os.path.join(cs, "cstrike")) if f.endswith(".bmp")])
        self.assertFalse(os.listdir(os.path.join(cs, "cstrike", "vidalia")))
        with open(os.path.join(cs, "video.txt")) as f:
            self.assertEqual(f.read(), "original")
        self.assertTrue(game.map_installed(exe, "cstrike", "de_teste") is False)
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(__import__("shutil").which("ffmpeg"), "ffmpeg nao instalado")
class TestExportMp4(unittest.TestCase):
    def test_exporta(self):
        import json
        import shutil
        import struct as st
        from vidalia import game
        tmp = tempfile.mkdtemp()
        w, h = 64, 36
        for k in range(30):
            game.write_png(os.path.join(tmp, "f%05d.png" % k), w, h, bytes([k * 8 % 256, 0, 0]) * (w * h))
        # wav de 1 s (silencio) como o startmovie gravaria
        n = 22050
        wav = (b"RIFF" + st.pack("<I", 36 + n * 2) + b"WAVEfmt " + st.pack("<IHHIIHH", 16, 1, 1, 22050, 44100, 2, 16)
               + b"data" + st.pack("<I", n * 2) + b"\0" * (n * 2))
        with open(os.path.join(tmp, "audio.wav"), "wb") as f:
            f.write(wav)
        ff = shutil.which("ffmpeg")
        a = game.export_mp4(ff, tmp, out=os.path.join(tmp, "a.mp4"))
        b = game.export_mp4(ff, tmp, out=os.path.join(tmp, "b.mp4"), speed=0.25, mark=0.5)
        probe = shutil.which("ffprobe")
        if probe:
            import subprocess
            def dur(p):
                r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "json", p],
                                   capture_output=True)
                return float(json.loads(r.stdout)["format"]["duration"])
            self.assertAlmostEqual(dur(a), 1.0, delta=0.15)
            self.assertAlmostEqual(dur(b), 4.0, delta=0.3)       # 0,25x = 4 vezes mais longo
        self.assertGreater(os.path.getsize(b), 0)
        shutil.rmtree(tmp, ignore_errors=True)


class TestSteamId(unittest.TestCase):
    def test_conversoes(self):
        from vidalia import steam
        # par conferido no proprio fungun.top (relatorio 490845)
        self.assertEqual(steam.to_steam2("76561199816595690"), "STEAM_0:0:928164981")
        self.assertEqual(steam.to_id64("STEAM_0:0:928164981"), 76561199816595690)
        self.assertEqual(steam.to_id64("STEAM_1:0:928164981"), 76561199816595690)
        self.assertEqual(steam.to_id64("[U:1:1856329962]"), 76561199816595690)
        self.assertEqual(steam.profile_url("STEAM_0:1:46748090"),
                         "https://steamcommunity.com/profiles/%d" % (76561197960265728 + 93496181))
        for bad in ("", "BOT", "HLTV", "STEAM_ID_LAN", "VALVE_ID_PENDING", "90071996842377222", "12345"):
            self.assertIsNone(steam.to_id64(bad), bad)
