"""Uso: python -m vidalia [demo.dem] [--mapas PASTA] [--saida PASTA]
Sem argumentos abre a interface grafica."""
import argparse
import os
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vidalia", description="Vidalia Demo Analyzer")
    ap.add_argument("demos", nargs="*", help="arquivos .dem")
    ap.add_argument("--mapas", help="pasta cstrike/maps (habilita analise de wallhack)")
    ap.add_argument("--saida", help="pasta dos relatorios (padrao: ao lado da demo)")
    a = ap.parse_args(argv)
    if not a.demos:
        from .gui import run
        run()
        return 0
    from .report import analyze, save_batch, save_chat_txt, save_csv, save_html, save_json
    code = 0
    done = []
    for d in a.demos:
        try:
            rep = analyze(d, a.mapas)
        except Exception as e:  # noqa: BLE001
            print("ERRO %s: %s" % (d, e), file=sys.stderr)
            code = 1
            continue
        out = a.saida or os.path.dirname(os.path.abspath(d))
        os.makedirs(out, exist_ok=True)
        base = os.path.join(out, os.path.splitext(os.path.basename(d))[0] + "_vidalia")
        save_json(rep, base + ".json")
        save_csv(rep, base + "_evidencias.csv")
        save_html(rep, base + ".html")
        save_chat_txt(rep, base + "_chat.txt")
        done.append((d, rep))
        print("%s -> %s [%s]" % (d, base + ".html", rep["veredito"]))
        for r in rep["detectores"]:
            print("  %-45s %-10s %s" % (r["detector"], r["status"], r["resumo"]))
        st = rep["decodificacao"]
        print("  rede: %s%% dos pacotes decodificados; erros: %s" % (st["cobertura_rede"], st["erros"] or "nenhum"))
    if len(done) > 1:
        out = a.saida or os.path.dirname(os.path.abspath(done[0][0]))
        print("Resumo:", save_batch(done, os.path.join(out, "vidalia_resumo")))
    return code


if __name__ == "__main__":
    sys.exit(main())
