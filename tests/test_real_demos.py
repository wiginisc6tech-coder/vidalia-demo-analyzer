"""Regressao com demos reais (opcional).

Defina VIDALIA_DEMOS com a pasta do repositorio UnrealDemoScanner (com CheatDemos*, ClearDemos*...)
para rodar. Garante que as melhorias nao voltem a gerar "Suspeito" em demos limpas e que a deteccao
nao piore em relacao a calibracao publicada (veja CALIBRACAO.md).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.environ.get("VIDALIA_DEMOS")


@unittest.skipUnless(ROOT and os.path.isdir(ROOT), "defina VIDALIA_DEMOS para rodar com demos reais")
class TestRealDemos(unittest.TestCase):
    def test_calibracao(self):
        from vidalia.calibrar import label_from_path, run
        paths = []
        for d in sorted(os.listdir(ROOT)):
            full = os.path.join(ROOT, d)
            if os.path.isdir(full) and d.lower().startswith(("cheat", "clear", "false")):
                paths += [os.path.join(full, f) for f in sorted(os.listdir(full))
                          if f.lower().endswith(".dem") and os.path.getsize(os.path.join(full, f)) > 1024]
        res = [r for r in run(paths, progress=False) if r.get("ok")]
        lab = {p: label_from_path(p)[0] for p in paths}
        clean = [r for r in res if lab[r["arquivo"]] == "limpa"]
        cheat = [r for r in res if lab[r["arquivo"]] == "cheat"]
        self.assertEqual([os.path.basename(r["arquivo"]) for r in clean if r["veredito"] == "Suspeito"], [])
        self.assertEqual([os.path.basename(r["arquivo"]) for r in clean if r["pontuacao"] >= 50], [])
        self.assertGreaterEqual(sum(1 for r in cheat if r["veredito"] == "Suspeito"), 39)


if __name__ == "__main__":
    unittest.main()
