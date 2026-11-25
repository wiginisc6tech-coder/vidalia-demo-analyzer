"""Controle de execucao da analise: pausar, retomar e cancelar.

O controle e consultado nos pontos em que a analise reporta progresso
(a cada bloco de frames lidos e apos cada detector), entao a pausa e o
cancelamento acontecem em instantes seguros, sem corromper o estado.
"""
import threading


class Cancelled(Exception):
    """Levantada dentro da analise quando o usuario cancela."""


class AnalysisControl:
    def __init__(self):
        self._run = threading.Event()   # setado = executando; limpo = pausado
        self._run.set()
        self._cancel = threading.Event()

    # chamados pela interface ------------------------------------------
    def pause(self):
        self._run.clear()

    def resume(self):
        self._run.set()

    def cancel(self):
        self._cancel.set()
        self._run.set()   # libera uma analise que esteja pausada

    # consultados pela analise -----------------------------------------
    @property
    def paused(self):
        return not self._run.is_set()

    @property
    def cancelled(self):
        return self._cancel.is_set()

    def checkpoint(self):
        """Bloqueia enquanto pausado; levanta Cancelled se cancelado."""
        while not self._run.wait(0.2):
            pass
        if self._cancel.is_set():
            raise Cancelled()
