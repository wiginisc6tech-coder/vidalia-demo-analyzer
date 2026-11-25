"""Traducoes da interface (pt, en, es, ru) e preferencia de idioma do usuario."""
import json
import locale
import os
import sys

LANGS = [("pt", "Português (BR)"), ("en", "English"), ("es", "Español"), ("ru", "Русский")]

S = {
    "pt": {
        "subtitle": "Triagem de demos de Counter-Strike 1.6 (GoldSrc)",
        "pill_detectors": "%d detectores", "pill_free": "gratuito · MIT", "language": "Idioma",
        "demo_or_folder": "DEMO OU PASTA", "maps_optional": "MAPAS (OPCIONAL)",
        "btn_demo": "Demo...", "btn_folder": "Pasta de demos...", "btn_maps": "Pasta...",
        "maps_hint": "Para o wallhack: se vazio, o mapa é procurado ao lado da demo e na instalação do CS.",
        "btn_analyze": "▶  Analisar", "btn_pause": "❚❚  Pausar", "btn_resume": "▶  Retomar", "btn_cancel": "✕  Cancelar",
        "btn_report": "Abrir relatório completo", "btn_report_of": "Abrir relatório: %s",
        "disclaimer": "Resultado de triagem: não comprova trapaça. Revise a demo nos momentos indicados.",
        "status_start": "Selecione uma demo (.dem) ou uma pasta de demos para iniciar.",
        "tab_detectors": "Detectores", "tab_chat": "Chat", "tab_chat_n": "Chat (%d)",
        "results_title": "Resultados dos detectores", "show": "Mostrar",
        "filters": ["Todas as evidências", "Somente Atenção e Suspeito", "Somente Suspeito"],
        "all_detectors": "Todos os detectores",
        "col_demo_detector": "Demo / detector", "col_status": "Status", "col_summary": "Resumo / evidência",
        "chat_title": "Chat da partida", "search": "Buscar", "btn_save_chat": "Salvar chat...",
        "chat_filters": ["Tudo", "Somente jogadores", "Jogadores e rádio", "Servidor e admin",
                         "Destaques (cheat, ban, demo...)"],
        "col_demo": "Demo", "col_time": "Tempo", "col_type": "Tipo", "col_player": "Jogador", "col_message": "Mensagem",
        "chat_none": "Nenhuma mensagem de chat para salvar (verifique o filtro).",
        "chat_saved": "Chat salvo em %s", "save_chat_title": "Salvar chat",
        "pick_demo": "Selecionar demo", "pick_folder": "Pasta com demos (.dem)", "pick_maps": "Pasta de mapas (cstrike\\maps)",
        "all_files": "Todos", "no_dem_in_folder": "Nenhum arquivo .dem nessa pasta.",
        "select_demo": "Selecione um arquivo .dem ou uma pasta com demos.",
        "error": "Erro", "analyzing": "Analisando", "paused": "Pausado:",
        "analyzing_n": "Analisando demo %d de %d (%s)", "paused_n": "Pausado na demo %d de %d (%s)",
        "cancel_q": "Cancelar a análise?\n\nAs demos já concluídas e seus relatórios serão mantidos.",
        "cancelling": "Cancelando...",
        "cancelled": "Análise cancelada em %s. %d de %d demo(s) concluída(s) e salva(s).",
        "no_summary": " Resumo da pasta não gerado.",
        "saved_single": "Relatórios salvos em %s.(html/json), _evidencias.csv e _chat.txt  ·  rede decodificada: %s%%",
        "saved_summary": "Relatório de resumo: %s",
        "verdict_single": "Triagem: %s  ·  pontuação %d/100 (%s)   ·   %s  (%d kills, %d HS)   ·   mapa %s",
        "verdict_multi": "%d demos: %d Suspeito · %d Atenção · %d Normal",
        "demo_row": "Pontuação %d/100 · %s · %d kills · mapa %s",
        "score_high": "alta prioridade de revisão", "score_review": "vale revisar", "score_weak": "indícios fracos",
        "score_none": "sem indícios",
        "evidence_note": "",
    },
    "en": {
        "subtitle": "Counter-Strike 1.6 (GoldSrc) demo screening",
        "pill_detectors": "%d detectors", "pill_free": "free · MIT", "language": "Language",
        "demo_or_folder": "DEMO OR FOLDER", "maps_optional": "MAPS (OPTIONAL)",
        "btn_demo": "Demo...", "btn_folder": "Demo folder...", "btn_maps": "Folder...",
        "maps_hint": "For wallhack: if empty, the map is searched next to the demo and in the CS install folder.",
        "btn_analyze": "▶  Analyze", "btn_pause": "❚❚  Pause", "btn_resume": "▶  Resume", "btn_cancel": "✕  Cancel",
        "btn_report": "Open full report", "btn_report_of": "Open report: %s",
        "disclaimer": "Screening result: it does not prove cheating. Review the demo at the times shown.",
        "status_start": "Select a demo (.dem) or a folder of demos to start.",
        "tab_detectors": "Detectors", "tab_chat": "Chat", "tab_chat_n": "Chat (%d)",
        "results_title": "Detector results", "show": "Show",
        "filters": ["All evidence", "Attention and Suspect only", "Suspect only"],
        "all_detectors": "All detectors",
        "col_demo_detector": "Demo / detector", "col_status": "Status", "col_summary": "Summary / evidence",
        "chat_title": "Match chat", "search": "Search", "btn_save_chat": "Save chat...",
        "chat_filters": ["Everything", "Players only", "Players and radio", "Server and admin",
                         "Highlights (cheat, ban, demo...)"],
        "col_demo": "Demo", "col_time": "Time", "col_type": "Type", "col_player": "Player", "col_message": "Message",
        "chat_none": "No chat messages to save (check the filter).",
        "chat_saved": "Chat saved to %s", "save_chat_title": "Save chat",
        "pick_demo": "Select demo", "pick_folder": "Folder with demos (.dem)", "pick_maps": "Maps folder (cstrike\\maps)",
        "all_files": "All", "no_dem_in_folder": "No .dem files in this folder.",
        "select_demo": "Select a .dem file or a folder with demos.",
        "error": "Error", "analyzing": "Analyzing", "paused": "Paused:",
        "analyzing_n": "Analyzing demo %d of %d (%s)", "paused_n": "Paused at demo %d of %d (%s)",
        "cancel_q": "Cancel the analysis?\n\nDemos already finished and their reports will be kept.",
        "cancelling": "Cancelling...",
        "cancelled": "Analysis cancelled at %s. %d of %d demo(s) finished and saved.",
        "no_summary": " Folder summary not created.",
        "saved_single": "Reports saved to %s.(html/json), _evidencias.csv and _chat.txt  ·  network decoded: %s%%",
        "saved_summary": "Summary report: %s",
        "verdict_single": "Screening: %s  ·  score %d/100 (%s)   ·   %s  (%d kills, %d HS)   ·   map %s",
        "verdict_multi": "%d demos: %d Suspect · %d Attention · %d Normal",
        "demo_row": "Score %d/100 · %s · %d kills · map %s",
        "score_high": "high review priority", "score_review": "worth reviewing", "score_weak": "weak signs",
        "score_none": "no signs",
        "evidence_note": "Evidence details and the HTML report are in Portuguese.",
    },
    "es": {
        "subtitle": "Análisis de demos de Counter-Strike 1.6 (GoldSrc)",
        "pill_detectors": "%d detectores", "pill_free": "gratis · MIT", "language": "Idioma",
        "demo_or_folder": "DEMO O CARPETA", "maps_optional": "MAPAS (OPCIONAL)",
        "btn_demo": "Demo...", "btn_folder": "Carpeta de demos...", "btn_maps": "Carpeta...",
        "maps_hint": "Para el wallhack: si está vacío, el mapa se busca junto a la demo y en la instalación del CS.",
        "btn_analyze": "▶  Analizar", "btn_pause": "❚❚  Pausar", "btn_resume": "▶  Reanudar", "btn_cancel": "✕  Cancelar",
        "btn_report": "Abrir informe completo", "btn_report_of": "Abrir informe: %s",
        "disclaimer": "Resultado de análisis: no prueba trampa. Revisa la demo en los momentos indicados.",
        "status_start": "Selecciona una demo (.dem) o una carpeta de demos para empezar.",
        "tab_detectors": "Detectores", "tab_chat": "Chat", "tab_chat_n": "Chat (%d)",
        "results_title": "Resultados de los detectores", "show": "Mostrar",
        "filters": ["Todas las evidencias", "Solo Atención y Sospechoso", "Solo Sospechoso"],
        "all_detectors": "Todos los detectores",
        "col_demo_detector": "Demo / detector", "col_status": "Estado", "col_summary": "Resumen / evidencia",
        "chat_title": "Chat de la partida", "search": "Buscar", "btn_save_chat": "Guardar chat...",
        "chat_filters": ["Todo", "Solo jugadores", "Jugadores y radio", "Servidor y admin",
                         "Destacados (cheat, ban, demo...)"],
        "col_demo": "Demo", "col_time": "Tiempo", "col_type": "Tipo", "col_player": "Jugador", "col_message": "Mensaje",
        "chat_none": "No hay mensajes de chat para guardar (revisa el filtro).",
        "chat_saved": "Chat guardado en %s", "save_chat_title": "Guardar chat",
        "pick_demo": "Seleccionar demo", "pick_folder": "Carpeta con demos (.dem)", "pick_maps": "Carpeta de mapas (cstrike\\maps)",
        "all_files": "Todos", "no_dem_in_folder": "No hay archivos .dem en esta carpeta.",
        "select_demo": "Selecciona un archivo .dem o una carpeta con demos.",
        "error": "Error", "analyzing": "Analizando", "paused": "En pausa:",
        "analyzing_n": "Analizando demo %d de %d (%s)", "paused_n": "En pausa en la demo %d de %d (%s)",
        "cancel_q": "¿Cancelar el análisis?\n\nSe conservarán las demos ya terminadas y sus informes.",
        "cancelling": "Cancelando...",
        "cancelled": "Análisis cancelado en %s. %d de %d demo(s) terminada(s) y guardada(s).",
        "no_summary": " No se generó el resumen de la carpeta.",
        "saved_single": "Informes guardados en %s.(html/json), _evidencias.csv y _chat.txt  ·  red decodificada: %s%%",
        "saved_summary": "Informe resumen: %s",
        "verdict_single": "Análisis: %s  ·  puntuación %d/100 (%s)   ·   %s  (%d kills, %d HS)   ·   mapa %s",
        "verdict_multi": "%d demos: %d Sospechoso · %d Atención · %d Normal",
        "demo_row": "Puntuación %d/100 · %s · %d kills · mapa %s",
        "score_high": "alta prioridad de revisión", "score_review": "vale la pena revisar", "score_weak": "indicios débiles",
        "score_none": "sin indicios",
        "evidence_note": "Los detalles de las evidencias y el informe HTML están en portugués.",
    },
    "ru": {
        "subtitle": "Проверка демо Counter-Strike 1.6 (GoldSrc)",
        "pill_detectors": "детекторов: %d", "pill_free": "бесплатно · MIT", "language": "Язык",
        "demo_or_folder": "ДЕМО ИЛИ ПАПКА", "maps_optional": "КАРТЫ (НЕОБЯЗАТЕЛЬНО)",
        "btn_demo": "Демо...", "btn_folder": "Папка с демо...", "btn_maps": "Папка...",
        "maps_hint": "Для проверки на WH: если пусто, карта ищется рядом с демо и в папке установки CS.",
        "btn_analyze": "▶  Проверить", "btn_pause": "❚❚  Пауза", "btn_resume": "▶  Продолжить", "btn_cancel": "✕  Отмена",
        "btn_report": "Открыть полный отчёт", "btn_report_of": "Открыть отчёт: %s",
        "disclaimer": "Результат проверки не доказывает использование читов. Просмотрите демо в указанные моменты.",
        "status_start": "Выберите демо (.dem) или папку с демо, чтобы начать.",
        "tab_detectors": "Детекторы", "tab_chat": "Чат", "tab_chat_n": "Чат (%d)",
        "results_title": "Результаты детекторов", "show": "Показать",
        "filters": ["Все улики", "Только Внимание и Подозрительно", "Только Подозрительно"],
        "all_detectors": "Все детекторы",
        "col_demo_detector": "Демо / детектор", "col_status": "Статус", "col_summary": "Итог / улика",
        "chat_title": "Чат матча", "search": "Поиск", "btn_save_chat": "Сохранить чат...",
        "chat_filters": ["Всё", "Только игроки", "Игроки и радио", "Сервер и админ",
                         "Важное (чит, бан, демо...)"],
        "col_demo": "Демо", "col_time": "Время", "col_type": "Тип", "col_player": "Игрок", "col_message": "Сообщение",
        "chat_none": "Нет сообщений чата для сохранения (проверьте фильтр).",
        "chat_saved": "Чат сохранён в %s", "save_chat_title": "Сохранить чат",
        "pick_demo": "Выбрать демо", "pick_folder": "Папка с демо (.dem)", "pick_maps": "Папка карт (cstrike\\maps)",
        "all_files": "Все", "no_dem_in_folder": "В этой папке нет файлов .dem.",
        "select_demo": "Выберите файл .dem или папку с демо.",
        "error": "Ошибка", "analyzing": "Проверка", "paused": "Пауза:",
        "analyzing_n": "Проверка демо %d из %d (%s)", "paused_n": "Пауза на демо %d из %d (%s)",
        "cancel_q": "Отменить проверку?\n\nУже проверенные демо и их отчёты сохранятся.",
        "cancelling": "Отмена...",
        "cancelled": "Проверка отменена на %s. Готово и сохранено демо: %d из %d.",
        "no_summary": " Сводка по папке не создана.",
        "saved_single": "Отчёты сохранены: %s.(html/json), _evidencias.csv и _chat.txt  ·  сеть декодирована: %s%%",
        "saved_summary": "Сводный отчёт: %s",
        "verdict_single": "Итог: %s  ·  оценка %d/100 (%s)   ·   %s  (%d убийств, %d HS)   ·   карта %s",
        "verdict_multi": "Демо: %d · Подозрительно %d · Внимание %d · Норма %d",
        "demo_row": "Оценка %d/100 · %s · убийств %d · карта %s",
        "score_high": "проверить в первую очередь", "score_review": "стоит проверить", "score_weak": "слабые признаки",
        "score_none": "признаков нет",
        "evidence_note": "Подробности улик и HTML-отчёт на португальском языке.",
    },
}

# status interno -> texto exibido
STATUS = {
    "pt": {"Normal": "Normal", "Atencao": "Atenção", "Suspeito": "Suspeito", "Sem dados": "Sem dados", "Erro": "Erro"},
    "en": {"Normal": "Normal", "Atencao": "Attention", "Suspeito": "Suspect", "Sem dados": "No data", "Erro": "Error"},
    "es": {"Normal": "Normal", "Atencao": "Atención", "Suspeito": "Sospechoso", "Sem dados": "Sin datos", "Erro": "Error"},
    "ru": {"Normal": "Норма", "Atencao": "Внимание", "Suspeito": "Подозрительно", "Sem dados": "Нет данных", "Erro": "Ошибка"},
}

# nome do detector (prefixo, em portugues) -> nome exibido
DETECTORS = {
    "en": {"Aimbot de 1 frame": "1-frame aimbot (snap and return)", "Aimbot": "Aimbot (flick + lock)",
           "Triggerbot": "Triggerbot", "Silent aim": "Silent aim", "No recoil": "No recoil",
           "Wallhack": "Wallhack (tracking through walls)", "Bunny hop script": "Bunny hop script",
           "Speedhack": "Speedhack", "Anti-aim": "Anti-aim / spinbot", "Strafe automatico": "Auto strafe",
           "Script de agachamento": "Duck script (SGS/DDRun)", "Fake lag": "Fake lag (packet choke)",
           "No flash": "No flash", "No smoke": "No smoke", "Autofire": "Autofire (autopistol)",
           "Assinaturas de cheat": "Cheat signatures in console"},
    "es": {"Aimbot de 1 frame": "Aimbot de 1 frame (va y vuelve)", "Aimbot": "Aimbot (flick + fijación)",
           "Triggerbot": "Triggerbot", "Silent aim": "Silent aim", "No recoil": "No recoil",
           "Wallhack": "Wallhack (seguimiento a través de paredes)", "Bunny hop script": "Script de bunny hop",
           "Speedhack": "Speedhack", "Anti-aim": "Anti-aim / spinbot", "Strafe automatico": "Strafe automático",
           "Script de agachamento": "Script de agacharse (SGS/DDRun)", "Fake lag": "Fake lag (retención de paquetes)",
           "No flash": "No flash", "No smoke": "No smoke", "Autofire": "Autofire (autopistola)",
           "Assinaturas de cheat": "Firmas de cheat en la consola"},
    "ru": {"Aimbot de 1 frame": "Аимбот за 1 кадр (рывок и возврат)", "Aimbot": "Аимбот (рывок + фиксация)",
           "Triggerbot": "Триггербот", "Silent aim": "Сайлент аим", "No recoil": "Без отдачи (no recoil)",
           "Wallhack": "WH (слежение сквозь стены)", "Bunny hop script": "Скрипт банихопа",
           "Speedhack": "Спидхак", "Anti-aim": "Анти-аим / спинбот", "Strafe automatico": "Автострейф",
           "Script de agachamento": "Скрипт приседаний (SGS/DDRun)", "Fake lag": "Фейк-лаг (задержка пакетов)",
           "No flash": "Анти-флеш", "No smoke": "Анти-смок", "Autofire": "Автострельба (автопистолет)",
           "Assinaturas de cheat": "Сигнатуры читов в консоли"},
}

CHAT_TYPES = {
    "pt": {"todos": "Todos", "time": "Time", "morto": "Morto", "espectador": "Espectador", "radio": "Rádio",
           "nome": "Troca de nome", "servidor": "Servidor/Admin", "jogo": "Jogo"},
    "en": {"todos": "All", "time": "Team", "morto": "Dead", "espectador": "Spectator", "radio": "Radio",
           "nome": "Name change", "servidor": "Server/Admin", "jogo": "Game"},
    "es": {"todos": "Todos", "time": "Equipo", "morto": "Muerto", "espectador": "Espectador", "radio": "Radio",
           "nome": "Cambio de nombre", "servidor": "Servidor/Admin", "jogo": "Juego"},
    "ru": {"todos": "Всем", "time": "Команде", "morto": "Мёртвый", "espectador": "Зритель", "radio": "Радио",
           "nome": "Смена ника", "servidor": "Сервер/Админ", "jogo": "Игра"},
}

_lang = "pt"


def set_lang(code):
    global _lang
    _lang = code if code in S else "pt"


def get_lang():
    return _lang


def T(key):
    return S[_lang].get(key, S["pt"].get(key, key))


def status(st):
    return STATUS[_lang].get(st, st)


def detector(name):
    table = DETECTORS.get(_lang)
    if not table:
        return name
    for k in sorted(table, key=len, reverse=True):
        if name.startswith(k):
            return table[k]
    return name


def chat_type(cat):
    return CHAT_TYPES[_lang].get(cat, cat)


def score_text(sc):
    if sc >= 70:
        return T("score_high")
    if sc >= 40:
        return T("score_review")
    if sc > 0:
        return T("score_weak")
    return T("score_none")


# ------------------------------------------------------------------ preferencia salva
def _config_path():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "Vidalia", "config.json")
    return os.path.join(os.path.expanduser("~"), ".config", "vidalia", "config.json")


def system_lang():
    """Idioma do sistema operacional, se for um dos suportados (senao ingles)."""
    code = ""
    try:
        if sys.platform == "win32":
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            code = locale.windows_locale.get(lcid, "")
        if not code:
            code = locale.getlocale()[0] or os.environ.get("LANG", "")
    except Exception:  # noqa: BLE001
        code = os.environ.get("LANG", "")
    code = (code or "").lower()
    for c in ("pt", "es", "ru", "en"):
        if code.startswith(c):
            return c
    return "en" if code else "pt"


def load_lang():
    try:
        with open(_config_path(), encoding="utf-8") as f:
            code = json.load(f).get("idioma")
        if code in S:
            return code
    except Exception:  # noqa: BLE001
        pass
    return system_lang()


def save_lang(code):
    p = _config_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        data = {}
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        data["idioma"] = code
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass
