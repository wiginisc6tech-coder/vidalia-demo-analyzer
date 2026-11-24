import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vidalia.bitreader import BitReader, ByteReader
from vidalia.netmsg import NetDecoder
from vidalia.report import analyze, save_csv, save_html, save_json
import synth

HERE = os.path.dirname(os.path.abspath(__file__))


class TestBits(unittest.TestCase):
    def test_roundtrip(self):
        bw = synth.BitWriter()
        bw.write(5, 3); bw.sbits(-77, 12); bw.string("abc"); bw.write(0x1234, 16)
        br = BitReader(bw.tobytes())
        self.assertEqual(br.read(3), 5)
        self.assertEqual(br.sbits(12), -77)
        self.assertEqual(br.string(), "abc")
        self.assertEqual(br.read(16), 0x1234)


@unittest.skipUnless(os.path.exists(os.path.join(HERE, "data", "mtt_loading_6000.hex")), "amostra real nao incluida")
class TestRealData(unittest.TestCase):
    """Bytes reais do segmento LOADING da mtt.dem (fornecidos pelo ChatGPT)."""

    def test_mtt_loading(self):
        with open(os.path.join(HERE, "data", "mtt_loading_6000.hex")) as f:
            d = bytes.fromhex(f.read().strip())
        import struct
        q = 9 + 436
        msg = d[q + 32:]
        dec = NetDecoder()
        r = ByteReader(msg)
        # processa ate onde a amostra permite (o restante foi truncado em 6000 bytes)
        while r.remaining():
            s = r.u8()
            try:
                dec.HANDLERS[s](dec, r)
            except Exception:
                break
        st = dec.st
        self.assertEqual(st.server["protocolo"], 48)
        self.assertEqual(st.server["mapa"], "maps/de_dust2.bsp")
        self.assertEqual(st.playernum, 11)
        for name in ("event_t", "weapon_data_t", "usercmd_t", "custom_entity_state_t",
                     "entity_state_player_t", "entity_state_t"):
            self.assertIn(name, st.deltas)
        names = [f.name for f in st.deltas["entity_state_player_t"]]
        self.assertIn("origin[0]", names)
        self.assertEqual(len(st.deltas["entity_state_t"]), 52)
        o = [f for f in st.deltas["entity_state_player_t"] if f.name == "origin[0]"][0]
        self.assertEqual((o.bits, o.pre), (24, 32.0))


class TestSynthetic(unittest.TestCase):
    def run_demo(self, **kw):
        tmp = tempfile.mkdtemp()
        p = os.path.join(tmp, "teste.dem")
        kills = synth.build_demo(p, **kw)
        rep = analyze(p)
        save_json(rep, p + ".json"); save_csv(rep, p + ".csv"); save_html(rep, p + ".html")
        return rep, kills, {r["detector"].split(" ")[0]: r for r in rep["detectores"]}

    def test_cheater(self):
        rep, kills, det = self.run_demo(aimbot=True, bhop_script=True, silent=True, norecoil=True)
        self.assertEqual(rep["decodificacao"]["cobertura_rede"], 100.0, rep["decodificacao"]["erros"])
        self.assertEqual(rep["gravador"]["nome"], "Suspeito")
        self.assertEqual(rep["gravador"]["kills"], kills)
        self.assertEqual(det["Aimbot"]["status"], "Suspeito")
        self.assertEqual(det["Bunny"]["status"], "Suspeito")
        self.assertEqual(det["Silent"]["status"], "Suspeito")
        self.assertIn(det["No"]["status"], ("Atencao", "Suspeito"))
        self.assertEqual(rep["veredito"], "Suspeito")

    def test_clean(self):
        rep, kills, det = self.run_demo(aimbot=False, bhop_script=False, silent=False, norecoil=False)
        self.assertEqual(rep["decodificacao"]["cobertura_rede"], 100.0)
        for k in ("Aimbot", "Bunny", "Silent", "Speedhack", "Anti-aim"):
            self.assertIn(det[k]["status"], ("Normal", "Sem dados"), (k, det[k]))


if __name__ == "__main__":
    unittest.main()


class TestSpeed(unittest.TestCase):
    def _speed(self, **kw):
        p = os.path.join(tempfile.mkdtemp(), "s.dem")
        synth.build_demo(p, aimbot=False, bhop_script=False, **kw)
        return [r for r in analyze(p)["detectores"] if r["detector"] == "Speedhack"][0]

    def test_duplicated_commands_not_flagged(self):
        r = self._speed(duplicate=True)
        self.assertEqual(r["status"], "Normal", r)
        self.assertAlmostEqual(r["metricas"]["mediana_razao"], 1.0, delta=0.05)

    def test_speedhack_whole_demo(self):
        r = self._speed(speed=True)
        self.assertNotEqual(r["status"], "Normal", r)


class TestBSP(unittest.TestCase):
    def test_visibility(self):
        from vidalia.bsp import BSP
        p = os.path.join(tempfile.mkdtemp(), "de_teste.bsp")
        synth.build_bsp(p)
        b = BSP(p)
        self.assertFalse(b.visible((0, 0, 64), (500, 0, 64)))
        self.assertTrue(b.visible((0, 0, 64), (150, 300, 64)))
        self.assertTrue(b.visible((350, 0, 0), (900, 50, 0)))

    def test_wallhack_pipeline(self):
        tmp = tempfile.mkdtemp()
        synth.build_bsp(os.path.join(tmp, "de_teste.bsp"))
        p = os.path.join(tmp, "wh.dem")
        synth.build_demo(p, aimbot=True)
        rep = analyze(p, tmp)
        wh = [r for r in rep["detectores"] if r["detector"].startswith("Wallhack")][0]
        self.assertNotEqual(wh["status"], "Sem dados", wh)


PUBLIC = os.environ.get("VIDALIA_DEMOS")  # pasta com cheat/ e clean/ (demos publicas do UnrealDemoScanner)


@unittest.skipUnless(PUBLIC and os.path.isdir(PUBLIC or ""), "defina VIDALIA_DEMOS para rodar a regressao com demos reais")
class TestPublicDemos(unittest.TestCase):
    EXPECT = {  # arquivo -> (detector, status minimo)
        "cheat/Speedhack.dem": ("Speedhack", "Suspeito"),
        "cheat/speedhackmax.dem": ("Speedhack", "Suspeito"),
        "cheat/testbhop.dem": ("Bunny", "Suspeito"),
        "cheat/hpp_bhop2.dem": ("Bunny", "Suspeito"),
        "cheat/aim_type_4.dem": ("Silent", "Suspeito"),
    }

    def test_cheats_detected(self):
        for f, (det, want) in self.EXPECT.items():
            r = {d["detector"].split(" ")[0]: d for d in analyze(os.path.join(PUBLIC, f))["detectores"]}
            self.assertEqual(r[det]["status"], want, (f, r[det]))

    def test_clean_not_suspect(self):
        import glob
        for f in glob.glob(os.path.join(PUBLIC, "clean", "*.dem")) + glob.glob(os.path.join(PUBLIC, "pro", "*.dem")):
            rep = analyze(f)
            self.assertEqual(rep["decodificacao"]["cobertura_rede"], 100.0, f)
            for d in rep["detectores"]:
                self.assertNotEqual(d["status"], "Suspeito", (f, d["detector"], d["resumo"]))


class TestWallhackScenarios(unittest.TestCase):
    """Cenarios sinteticos com parede solida entre x=200 e x=300 (synth.build_bsp)."""

    @classmethod
    def setUpClass(cls):
        from vidalia.bsp import BSP
        p = os.path.join(tempfile.mkdtemp(), "de_teste.bsp")
        synth.build_bsp(p)
        cls.bsp = BSP(p)

    def make(self, segments):
        """segments: lista de (duracao_s, funcao(t_rel) -> (posicao_inimigo, yaw_mira))."""
        import math
        from vidalia.engine import DemoData
        dd = DemoData()
        dd.local = 1
        dd.players = {1: {"nome": "Gravador", "time": "TERRORIST"}, 2: {"nome": "Alvo", "time": "CT"}}
        dd.team_hist = {}
        tl = dd.timeline
        t = 0.0
        fr = 0
        for dur, fn in segments:
            n = int(dur / 0.01)
            for k in range(n):
                pos, yaw = fn(k * 0.01)
                tl.t.append(t); tl.frame.append(fr); tl.pitch.append(0.0); tl.yaw.append(yaw)
                tl.eye.append((0.0, 0.0, 64.0)); tl.players.append({2: pos} if pos else {}); tl.weapon.append(28)
                t += 0.01
                fr += 1
        return dd

    @staticmethod
    def bearing(pos):
        import math
        return math.degrees(math.atan2(pos[1], pos[0]))

    def run_wh(self, dd):
        from vidalia.detectors import DEFAULTS, detect_wallhack
        return detect_wallhack(dd, DEFAULTS, self.bsp)

    def moving(self, x=500.0):
        return lambda tr: (x, -150.0 + 150.0 * tr, 47.5)

    def test_blind_tracking_is_flagged(self):
        mv = self.moving()
        follow = lambda tr: (mv(tr), self.bearing(mv(tr)))
        gap = lambda tr: (None, 90.0)
        r = self.run_wh(self.make([(2.0, follow), (1.0, gap), (2.0, follow)]))
        self.assertEqual(r["metricas"]["ativos_sem_visao_recente"], 2, r)
        self.assertEqual(r["status"], "Atencao")

    def test_static_preaim_not_flagged(self):
        mv = self.moving()
        static = lambda tr: (mv(tr), self.bearing(mv(1.0)))   # mira parada no meio do caminho
        r = self.run_wh(self.make([(2.0, static), (2.0, static)]))
        self.assertEqual(r["metricas"]["episodios_ativos"], 0, r)
        self.assertEqual(r["status"], "Normal")

    def test_recently_seen_is_not_blind(self):
        visible = lambda tr: ((150.0, -150.0, 47.5), self.bearing((150.0, -150.0)))  # na frente da parede
        mv = self.moving()
        follow = lambda tr: (mv(tr), self.bearing(mv(tr)))
        r = self.run_wh(self.make([(0.5, visible), (2.0, follow)]))
        self.assertEqual(r["metricas"]["episodios_ativos"], 1, r)
        self.assertEqual(r["metricas"]["ativos_sem_visao_recente"], 0, r)
        self.assertIn("visto pela ultima vez 0.0 s antes", r["evidencias"][0]["descricao"])
        self.assertEqual(r["status"], "Normal")

    def test_since_never_negative(self):
        mv = self.moving()
        follow = lambda tr: (mv(tr), self.bearing(mv(tr)))
        visible = lambda tr: ((150.0, 0.0, 47.5), 0.0)
        r = self.run_wh(self.make([(1.5, follow), (0.5, visible), (1.5, follow)]))
        for e in r["evidencias"]:
            self.assertNotIn("-", e["descricao"].split("visto pela ultima vez")[-1][:3], e)


class TestBatch(unittest.TestCase):
    def test_batch_summary(self):
        from vidalia.report import save_batch
        tmp = tempfile.mkdtemp()
        items = []
        for k, kw in enumerate([dict(aimbot=True), dict(aimbot=False, bhop_script=False)]):
            p = os.path.join(tmp, "d%d.dem" % k)
            synth.build_demo(p, **kw)
            items.append((p, analyze(p)))
        out = save_batch(items, os.path.join(tmp, "vidalia_resumo"))
        with open(out, encoding="utf-8") as f:
            txt = f.read()
        self.assertIn("RESUMO DE 2 DEMOS", txt)
        self.assertTrue(os.path.exists(os.path.join(tmp, "vidalia_resumo.csv")))


class TestEvidenceConsistency(unittest.TestCase):
    def test_normal_detector_has_no_suspect_evidence_and_no_duplicates(self):
        p = os.path.join(tempfile.mkdtemp(), "c.dem")
        synth.build_demo(p, aimbot=False, bhop_script=False)
        for r in analyze(p)["detectores"]:
            keys = [(e.get("frame"), e.get("descricao")) for e in r["evidencias"]]
            self.assertEqual(len(keys), len(set(keys)), r["detector"])
            if r["status"] in ("Normal", "Sem dados"):
                for e in r["evidencias"]:
                    self.assertNotIn(e.get("gravidade"), ("Atencao", "Suspeito"), (r["detector"], e))
