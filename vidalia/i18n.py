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
        "tab_moments": "Momentos", "tab_moments_n": "Momentos (%d)", "moments_title": "Momentos para conferir",
        "moments_filters": ["Atenção e Suspeito", "Somente Suspeito"],
        "moments_none": "Nenhum momento de Atenção ou Suspeito.", "col_detector": "Detector",
        "dbl_hint": "Clique duas vezes em uma evidência para ver o momento na aba Momentos.",
        "mv_pick": "Selecione um momento na lista para ver o replay.", "mv_expand": "⤢  Ampliar",
        "mv_goto": "⚑  Ir ao apontamento", "mv_speed": "Velocidade", "mv_loop": "Repetir",
        "mv_stop_at": "Pausar no apontamento", "mv_window": "Momento: %s",
        "mv_no_map": "(Mapa %s.bsp não encontrado: paredes não desenhadas. Informe a pasta de mapas e analise de novo.)",
        "mv_hp": "Vida", "mv_shot": "TIRO", "mv_air": "NO AR", "mv_duck": "AGACHADO",
        "mv_behind": "atrás da parede", "mv_radar": "RADAR", "mv_server_aim": "mira enviada ao servidor",
        "mv_graph_speed": "velocidade da mira", "mv_graph_err": "distância da mira ao inimigo (0–45°)",
        "mv_flag": "APONTAMENTO",
        "mv_note": "Reconstrução feita com os dados da demo, não é a imagem do jogo. Portas, caixas móveis e fumaça não aparecem. Espaço = play/pausa, ←/→ = frame a frame, duplo clique = ampliar.",
        "mv_watch": "🎮  Ver no jogo", "mv_record": "●  Gravar vídeo real", "mv_mode_rec": "Reconstrução",
        "mv_mode_video": "Vídeo real", "mv_open_mp4": "Abrir MP4", "g_cancel": "■  Cancelar gravação",
        "g_pick_exe": "Selecione o hl.exe do seu CS 1.6", "g_video_tag": "VÍDEO REAL (CS 1.6)",
        "g_not_found": "Não achei o CS 1.6 neste computador. Selecione o hl.exe (fica na pasta do Half-Life).",
        "g_no_map": "O mapa %s não está instalado no seu CS. Sem ele o jogo não consegue abrir a demo.\n\nContinuar mesmo assim?",
        "g_game": "Gravando no CS 1.6: o jogo abre em janela, avança até o momento e fecha sozinho. Não mexa nele.",
        "g_convert": "Convertendo os quadros do vídeo... %d%%", "g_mp4": "Gerando o MP4...",
        "g_done": "Vídeo real gravado (%d quadros).", "g_watch_on": "CS aberto no momento %s. Feche o jogo quando terminar.",
        "g_running": "Já existe uma gravação em andamento.", "g_outside": "Fora do trecho gravado",
        "g_err_no_frames": "O jogo fechou, mas nenhum quadro foi gravado. Confira se a demo abriu no jogo (mapa instalado?) e tente de novo.",
        "g_err_no_write": "Sem permissão para escrever na pasta do CS (%s). Rode o Vidalia como administrador.",
        "g_err_timeout": "O jogo demorou demais e foi fechado.", "g_err_demo_missing": "A demo original não foi encontrada.",
        "g_err_cancelled": "Gravação cancelada.", "btn_steam": "👤  Perfil Steam", "btn_steam_na": "👤  Sem SteamID", "btn_ecd": "🔎  Scans ECD",
        "steam_none": "sem SteamID",
        "steam_invalid": "%s não tem uma SteamID válida (%s).\n\nIsso acontece em servidores não-Steam, LAN, bots e HLTV: não há perfil Steam nem como buscar no ECD.",
        "ecd_copied": "SteamID %s copiada. No fungun.top, cole (Ctrl+V) no campo Search.",
        "ecd_tip": "A lista de scans do ECD foi aberta no navegador.\n\nO site não aceita busca pelo link, então a SteamID %s foi copiada: é só clicar no campo \"Search\" e colar (Ctrl+V).", "mv_export": "💾  Exportar MP4...", "ex_title": "Exportar vídeo MP4", "ex_frames": "quadros",
        "ex_speed": "VELOCIDADE", "ex_speeds": ["Normal (1x)", "Câmera lenta (0,5x)", "Câmera bem lenta (0,25x)"],
        "ex_mark": "Destacar o apontamento com uma borda vermelha", "ex_audio": "Incluir o som do jogo",
        "ex_go": "Exportar", "ex_cancel": "Cancelar", "ex_save": "Salvar vídeo como", "ex_working": "Gerando o MP4...",
        "ex_need_ff": "Para gerar o MP4 o Vidalia usa o ffmpeg (gratuito), que não foi encontrado neste computador.\n\n1. Baixe o ffmpeg para Windows (versão \"essentials\").\n2. Extraia o arquivo.\n3. Clique em \"Selecionar ffmpeg.exe\" e escolha o ffmpeg.exe (fica na pasta bin).\n\nOu coloque o ffmpeg.exe na mesma pasta do VidaliaDemoAnalyzer.exe.",
        "ex_pick_ff": "Selecionar ffmpeg.exe", "ex_download": "Abrir página de download",
        "ex_done": "MP4 salvo em %s", "ex_open_folder": "MP4 salvo em:\n%s\n\nAbrir a pasta?", "ex_err": "Erro ao gerar o MP4: %s", "g_err_game_running": "O CS já está aberto. Feche o jogo e tente de novo.", "g_err_launch": "Não consegui abrir o jogo: %s", "g_log": "Detalhes em: %s", "g_err_other": "Erro ao abrir o jogo: %s",
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
        "tab_moments": "Moments", "tab_moments_n": "Moments (%d)", "moments_title": "Moments to review",
        "moments_filters": ["Attention and Suspect", "Suspect only"],
        "moments_none": "No Attention or Suspect moments.", "col_detector": "Detector",
        "dbl_hint": "Double-click an evidence row to watch the moment in the Moments tab.",
        "mv_pick": "Select a moment in the list to watch the replay.", "mv_expand": "⤢  Enlarge",
        "mv_goto": "⚑  Go to flagged frame", "mv_speed": "Speed", "mv_loop": "Loop",
        "mv_stop_at": "Pause at flagged frame", "mv_window": "Moment: %s",
        "mv_no_map": "(Map %s.bsp not found: walls are not drawn. Set the maps folder and analyze again.)",
        "mv_hp": "HP", "mv_shot": "SHOT", "mv_air": "IN AIR", "mv_duck": "DUCKING",
        "mv_behind": "behind wall", "mv_radar": "RADAR", "mv_server_aim": "aim sent to server",
        "mv_graph_speed": "aim speed", "mv_graph_err": "aim distance to enemy (0–45°)",
        "mv_flag": "FLAGGED",
        "mv_note": "Reconstructed from demo data, not the actual game image. Doors, moving boxes and smoke are not shown. Space = play/pause, ←/→ = frame by frame, double-click = enlarge.",
        "mv_watch": "🎮  Watch in game", "mv_record": "●  Record real video", "mv_mode_rec": "Reconstruction",
        "mv_mode_video": "Real video", "mv_open_mp4": "Open MP4", "g_cancel": "■  Cancel recording",
        "g_pick_exe": "Select the hl.exe of your CS 1.6", "g_video_tag": "REAL VIDEO (CS 1.6)",
        "g_not_found": "CS 1.6 was not found on this computer. Select hl.exe (in the Half-Life folder).",
        "g_no_map": "Map %s is not installed in your CS. Without it the game cannot open the demo.\n\nContinue anyway?",
        "g_game": "Recording in CS 1.6: the game opens in a window, fast-forwards to the moment and closes by itself. Don't touch it.",
        "g_convert": "Converting video frames... %d%%", "g_mp4": "Creating the MP4...",
        "g_done": "Real video recorded (%d frames).", "g_watch_on": "CS opened at %s. Close the game when you are done.",
        "g_running": "A recording is already in progress.", "g_outside": "Outside the recorded clip",
        "g_err_no_frames": "The game closed but no frames were recorded. Check that the demo opened in the game (map installed?) and try again.",
        "g_err_no_write": "No permission to write to the CS folder (%s). Run Vidalia as administrator.",
        "g_err_timeout": "The game took too long and was closed.", "g_err_demo_missing": "The original demo was not found.",
        "g_err_cancelled": "Recording cancelled.", "btn_steam": "👤  Steam profile", "btn_steam_na": "👤  No SteamID", "btn_ecd": "🔎  ECD scans",
        "steam_none": "no SteamID",
        "steam_invalid": "%s has no valid SteamID (%s).\n\nThis happens on non-Steam servers, LAN, bots and HLTV: there is no Steam profile and no way to search ECD.",
        "ecd_copied": "SteamID %s copied. On fungun.top, paste it (Ctrl+V) into the Search field.",
        "ecd_tip": "The ECD scan list was opened in your browser.\n\nThe site does not accept searches through the link, so SteamID %s was copied: click the \"Search\" field and paste (Ctrl+V).", "mv_export": "💾  Export MP4...", "ex_title": "Export MP4 video", "ex_frames": "frames",
        "ex_speed": "SPEED", "ex_speeds": ["Normal (1x)", "Slow motion (0.5x)", "Very slow (0.25x)"],
        "ex_mark": "Highlight the flagged frame with a red border", "ex_audio": "Include game sound",
        "ex_go": "Export", "ex_cancel": "Cancel", "ex_save": "Save video as", "ex_working": "Creating the MP4...",
        "ex_need_ff": "Vidalia uses ffmpeg (free) to create the MP4, and it was not found on this computer.\n\n1. Download ffmpeg for Windows (\"essentials\" build).\n2. Extract it.\n3. Click \"Select ffmpeg.exe\" and choose ffmpeg.exe (in the bin folder).\n\nOr put ffmpeg.exe in the same folder as VidaliaDemoAnalyzer.exe.",
        "ex_pick_ff": "Select ffmpeg.exe", "ex_download": "Open download page",
        "ex_done": "MP4 saved to %s", "ex_open_folder": "MP4 saved to:\n%s\n\nOpen the folder?", "ex_err": "Error creating the MP4: %s", "g_err_game_running": "CS is already running. Close the game and try again.", "g_err_launch": "Could not start the game: %s", "g_log": "Details in: %s", "g_err_other": "Error opening the game: %s",
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
        "tab_moments": "Momentos", "tab_moments_n": "Momentos (%d)", "moments_title": "Momentos para revisar",
        "moments_filters": ["Atención y Sospechoso", "Solo Sospechoso"],
        "moments_none": "Ningún momento de Atención o Sospechoso.", "col_detector": "Detector",
        "dbl_hint": "Haz doble clic en una evidencia para ver el momento en la pestaña Momentos.",
        "mv_pick": "Selecciona un momento de la lista para ver el replay.", "mv_expand": "⤢  Ampliar",
        "mv_goto": "⚑  Ir al momento marcado", "mv_speed": "Velocidad", "mv_loop": "Repetir",
        "mv_stop_at": "Pausar en el momento marcado", "mv_window": "Momento: %s",
        "mv_no_map": "(Mapa %s.bsp no encontrado: no se dibujan las paredes. Indica la carpeta de mapas y analiza de nuevo.)",
        "mv_hp": "Vida", "mv_shot": "DISPARO", "mv_air": "EN EL AIRE", "mv_duck": "AGACHADO",
        "mv_behind": "detrás de la pared", "mv_radar": "RADAR", "mv_server_aim": "mira enviada al servidor",
        "mv_graph_speed": "velocidad de la mira", "mv_graph_err": "distancia de la mira al enemigo (0–45°)",
        "mv_flag": "MARCADO",
        "mv_note": "Reconstrucción con los datos de la demo, no es la imagen del juego. Puertas, cajas móviles y humo no aparecen. Espacio = play/pausa, ←/→ = cuadro a cuadro, doble clic = ampliar.",
        "mv_watch": "🎮  Ver en el juego", "mv_record": "●  Grabar video real", "mv_mode_rec": "Reconstrucción",
        "mv_mode_video": "Video real", "mv_open_mp4": "Abrir MP4", "g_cancel": "■  Cancelar grabación",
        "g_pick_exe": "Selecciona el hl.exe de tu CS 1.6", "g_video_tag": "VIDEO REAL (CS 1.6)",
        "g_not_found": "No encontré CS 1.6 en este equipo. Selecciona hl.exe (en la carpeta de Half-Life).",
        "g_no_map": "El mapa %s no está instalado en tu CS. Sin él el juego no puede abrir la demo.\n\n¿Continuar de todos modos?",
        "g_game": "Grabando en CS 1.6: el juego se abre en ventana, avanza hasta el momento y se cierra solo. No lo toques.",
        "g_convert": "Convirtiendo los cuadros del video... %d%%", "g_mp4": "Generando el MP4...",
        "g_done": "Video real grabado (%d cuadros).", "g_watch_on": "CS abierto en %s. Cierra el juego cuando termines.",
        "g_running": "Ya hay una grabación en curso.", "g_outside": "Fuera del tramo grabado",
        "g_err_no_frames": "El juego se cerró, pero no se grabó ningún cuadro. Comprueba que la demo abrió en el juego (¿mapa instalado?) e inténtalo de nuevo.",
        "g_err_no_write": "Sin permiso para escribir en la carpeta de CS (%s). Ejecuta Vidalia como administrador.",
        "g_err_timeout": "El juego tardó demasiado y se cerró.", "g_err_demo_missing": "No se encontró la demo original.",
        "g_err_cancelled": "Grabación cancelada.", "btn_steam": "👤  Perfil de Steam", "btn_steam_na": "👤  Sin SteamID", "btn_ecd": "🔎  Scans ECD",
        "steam_none": "sin SteamID",
        "steam_invalid": "%s no tiene una SteamID válida (%s).\n\nOcurre en servidores no-Steam, LAN, bots y HLTV: no hay perfil de Steam ni forma de buscar en ECD.",
        "ecd_copied": "SteamID %s copiada. En fungun.top, pégala (Ctrl+V) en el campo Search.",
        "ecd_tip": "La lista de scans de ECD se abrió en el navegador.\n\nEl sitio no acepta búsquedas por el enlace, así que se copió la SteamID %s: haz clic en el campo \"Search\" y pega (Ctrl+V).", "mv_export": "💾  Exportar MP4...", "ex_title": "Exportar video MP4", "ex_frames": "cuadros",
        "ex_speed": "VELOCIDAD", "ex_speeds": ["Normal (1x)", "Cámara lenta (0,5x)", "Muy lenta (0,25x)"],
        "ex_mark": "Resaltar el momento marcado con un borde rojo", "ex_audio": "Incluir el sonido del juego",
        "ex_go": "Exportar", "ex_cancel": "Cancelar", "ex_save": "Guardar video como", "ex_working": "Generando el MP4...",
        "ex_need_ff": "Vidalia usa ffmpeg (gratuito) para generar el MP4 y no se encontró en este equipo.\n\n1. Descarga ffmpeg para Windows (versión \"essentials\").\n2. Extráelo.\n3. Haz clic en \"Seleccionar ffmpeg.exe\" y elige ffmpeg.exe (en la carpeta bin).\n\nO coloca ffmpeg.exe en la misma carpeta que VidaliaDemoAnalyzer.exe.",
        "ex_pick_ff": "Seleccionar ffmpeg.exe", "ex_download": "Abrir página de descarga",
        "ex_done": "MP4 guardado en %s", "ex_open_folder": "MP4 guardado en:\n%s\n\n¿Abrir la carpeta?", "ex_err": "Error al generar el MP4: %s", "g_err_game_running": "CS ya está abierto. Cierra el juego e inténtalo de nuevo.", "g_err_launch": "No pude abrir el juego: %s", "g_log": "Detalles en: %s", "g_err_other": "Error al abrir el juego: %s",
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
        "tab_moments": "Моменты", "tab_moments_n": "Моменты (%d)", "moments_title": "Моменты для проверки",
        "moments_filters": ["Внимание и Подозрительно", "Только Подозрительно"],
        "moments_none": "Нет моментов «Внимание» или «Подозрительно».", "col_detector": "Детектор",
        "dbl_hint": "Дважды щёлкните по улике, чтобы посмотреть момент на вкладке «Моменты».",
        "mv_pick": "Выберите момент в списке, чтобы посмотреть повтор.", "mv_expand": "⤢  Увеличить",
        "mv_goto": "⚑  К отмеченному кадру", "mv_speed": "Скорость", "mv_loop": "Повтор",
        "mv_stop_at": "Пауза на отмеченном кадре", "mv_window": "Момент: %s",
        "mv_no_map": "(Карта %s.bsp не найдена: стены не рисуются. Укажите папку карт и запустите анализ снова.)",
        "mv_hp": "HP", "mv_shot": "ВЫСТРЕЛ", "mv_air": "В ВОЗДУХЕ", "mv_duck": "ПРИСЕД",
        "mv_behind": "за стеной", "mv_radar": "РАДАР", "mv_server_aim": "прицел, отправленный серверу",
        "mv_graph_speed": "скорость прицела", "mv_graph_err": "расстояние прицела до врага (0–45°)",
        "mv_flag": "ОТМЕЧЕНО",
        "mv_note": "Реконструкция по данным демо, а не изображение из игры. Двери, движущиеся ящики и дым не показаны. Пробел = пуск/пауза, ←/→ = по кадрам, двойной щелчок = увеличить.",
        "mv_watch": "🎮  Смотреть в игре", "mv_record": "●  Записать реальное видео", "mv_mode_rec": "Реконструкция",
        "mv_mode_video": "Реальное видео", "mv_open_mp4": "Открыть MP4", "g_cancel": "■  Отменить запись",
        "g_pick_exe": "Выберите hl.exe вашего CS 1.6", "g_video_tag": "РЕАЛЬНОЕ ВИДЕО (CS 1.6)",
        "g_not_found": "CS 1.6 не найден на этом компьютере. Выберите hl.exe (в папке Half-Life).",
        "g_no_map": "Карта %s не установлена в вашем CS. Без неё игра не сможет открыть демо.\n\nПродолжить всё равно?",
        "g_game": "Запись в CS 1.6: игра откроется в окне, перемотает до момента и закроется сама. Не трогайте её.",
        "g_convert": "Преобразование кадров видео... %d%%", "g_mp4": "Создание MP4...",
        "g_done": "Реальное видео записано (%d кадров).", "g_watch_on": "CS открыт на %s. Закройте игру, когда закончите.",
        "g_running": "Запись уже идёт.", "g_outside": "Вне записанного фрагмента",
        "g_err_no_frames": "Игра закрылась, но кадры не записаны. Проверьте, что демо открылось в игре (карта установлена?), и попробуйте снова.",
        "g_err_no_write": "Нет прав на запись в папку CS (%s). Запустите Vidalia от имени администратора.",
        "g_err_timeout": "Игра работала слишком долго и была закрыта.", "g_err_demo_missing": "Исходное демо не найдено.",
        "g_err_cancelled": "Запись отменена.", "btn_steam": "👤  Профиль Steam", "btn_steam_na": "👤  Нет SteamID", "btn_ecd": "🔎  Сканы ECD",
        "steam_none": "нет SteamID",
        "steam_invalid": "У игрока %s нет действительного SteamID (%s).\n\nТак бывает на non-Steam серверах, в LAN, у ботов и HLTV: профиля Steam нет, и искать в ECD нечего.",
        "ecd_copied": "SteamID %s скопирован. На fungun.top вставьте его (Ctrl+V) в поле Search.",
        "ecd_tip": "Список сканов ECD открыт в браузере.\n\nСайт не принимает поиск через ссылку, поэтому SteamID %s скопирован: нажмите на поле «Search» и вставьте (Ctrl+V).", "mv_export": "💾  Экспорт MP4...", "ex_title": "Экспорт видео MP4", "ex_frames": "кадров",
        "ex_speed": "СКОРОСТЬ", "ex_speeds": ["Обычная (1x)", "Замедленно (0,5x)", "Очень медленно (0,25x)"],
        "ex_mark": "Выделить отмеченный кадр красной рамкой", "ex_audio": "Добавить звук игры",
        "ex_go": "Экспорт", "ex_cancel": "Отмена", "ex_save": "Сохранить видео как", "ex_working": "Создание MP4...",
        "ex_need_ff": "Для создания MP4 Vidalia использует ffmpeg (бесплатно), но он не найден на этом компьютере.\n\n1. Скачайте ffmpeg для Windows (сборка «essentials»).\n2. Распакуйте архив.\n3. Нажмите «Выбрать ffmpeg.exe» и укажите ffmpeg.exe (в папке bin).\n\nИли положите ffmpeg.exe в папку с VidaliaDemoAnalyzer.exe.",
        "ex_pick_ff": "Выбрать ffmpeg.exe", "ex_download": "Открыть страницу загрузки",
        "ex_done": "MP4 сохранён: %s", "ex_open_folder": "MP4 сохранён:\n%s\n\nОткрыть папку?", "ex_err": "Ошибка создания MP4: %s", "g_err_game_running": "CS уже запущен. Закройте игру и попробуйте снова.", "g_err_launch": "Не удалось запустить игру: %s", "g_log": "Подробности: %s", "g_err_other": "Ошибка запуска игры: %s",
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


def load_setting(key, default=None):
    """Preferencia salva no config.json (ex.: caminho do hl.exe)."""
    try:
        with open(_config_path(), encoding="utf-8") as f:
            return json.load(f).get(key, default)
    except Exception:  # noqa: BLE001
        return default


def save_setting(key, value):
    p = _config_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        data = {}
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        data[key] = value
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass
