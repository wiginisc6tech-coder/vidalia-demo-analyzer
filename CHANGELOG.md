# Histórico de versões

## 1.7.3
- **Perfil Steam:** botão na faixa do resultado que abre o perfil Steam do jogador analisado
  (com várias demos, o da demo selecionada). Também no clique direito de uma mensagem na aba Chat.
- **Scans ECD:** abre a lista de scans do fungun.top com a SteamID do jogador já copiada (formato STEAM_0:X:Y);
  o site não aceita busca pelo link, então basta colar (Ctrl+V) no campo Search.
- SteamIDs inválidas (servidor não-Steam, LAN, bot, HLTV) são identificadas e avisadas.

## 1.7.2
- **Exportar MP4:** botão **💾 Exportar MP4...** no vídeo real de cada momento. Escolha a velocidade (normal,
  0,5x ou 0,25x), se quer a **borda vermelha no frame do apontamento** e o som do jogo (quando gravado), e onde
  salvar. Usa o ffmpeg (gratuito): se ele não for encontrado, o Vidalia explica como baixar e pede o `ffmpeg.exe`
  uma única vez (ou basta deixá-lo ao lado do `VidaliaDemoAnalyzer.exe`).
- O som gravado pelo `startmovie` (.wav), quando existir, é guardado junto com o vídeo.

## 1.7.1
- **Ver no jogo / Gravar vídeo real:** corrigido o jogo que não abria pelo executável (.exe sem console);
  CS da Steam aberto pela Steam (`-applaunch 10`) e acompanhado pelo processo `hl.exe`; aviso quando o CS
  já está aberto; mensagens de erro em janela e registro em `%APPDATA%\Vidalia\jogo.log`.

## 1.7.0
- **Aba Momentos:** lista todos os apontamentos de Atenção/Suspeito e mostra um **replay do momento**, parando
  no frame exato do apontamento. O replay é reconstruído a partir dos dados da demo (não precisa do jogo):
  - **Visão do jogador** em 3D simples, com as paredes do mapa `.bsp` (quando encontrado), os jogadores
    (inimigos em vermelho, aliados em azul, inimigos **atrás da parede** tracejados em laranja), a mira e a
    **mira enviada ao servidor** (silent aim aparece como um círculo roxo fora da mira).
  - **Radar** visto de cima, girando com a mira, com rastros dos jogadores.
  - **Gráfico da mira:** velocidade da mira e distância ao inimigo, com tiros, mortes e o apontamento marcados;
    clique no gráfico para pular para qualquer ponto.
  - Controles: play/pausa, quadro a quadro (←/→), velocidade 0,1x a 2x, "Ir ao apontamento", repetir e
    janela ampliada (botão **Ampliar** ou duplo clique).
- Duplo clique em uma evidência na aba Detectores abre o momento na aba Momentos.
- **Vídeo real do momento (experimental):** com o CS 1.6 instalado, o botão **Gravar vídeo real** abre o jogo
  em janela, avança rápido até o trecho, grava com `startmovie`, fecha o jogo e mostra o vídeo na aba Momentos,
  sincronizado com o radar e o gráfico (botão *Reconstrução / Vídeo real*). O vídeo fica salvo ao lado da demo
  (`<demo>_vidalia_videos`) e, se o **ffmpeg** estiver instalado, também como MP4.
  **Ver no jogo** abre o CS já no momento, sem gravar. A demo original não é alterada: o Vidalia usa uma cópia
  com comandos de console inseridos. As configurações de vídeo do jogo (janela/resolução) são restauradas depois.

## 1.6.0
- **Idioma da interface:** Português, English, Español e Русский, escolhido no canto superior direito.
  A troca é imediata (inclusive durante uma análise) e fica salva; na primeira vez usa o idioma do Windows.
  As descrições detalhadas das evidências e o relatório HTML continuam em português.
- **Aba Chat:** todo o chat gravado na demo (geral, time, mortos, espectadores, rádio, trocas de nome e mensagens
  do servidor/admin/plugins), com filtros, busca e destaque de mensagens com "cheat", "wh", "aim", "ban", "demo"...
- Chat salvo junto com os relatórios (`<demo>_vidalia_chat.txt`) e incluído no relatório HTML e no JSON.
- Botão **Salvar chat** (.txt ou .csv para Excel), respeitando o filtro e a busca.
- Reconhece chat de plugins (VIP, patentes, `*DEAD*`), textos em cirílico (UTF-8 e cp1251) e rádio traduzido.

## 1.5.0
- **Calibração com 211 demos reais** (UnrealDemoScanner): demos com cheat marcadas "Suspeito" passaram de 18 para 39;
  demos limpas "Suspeito" de 2 para 0. Veja `CALIBRACAO.md`.
- **Pontuação 0–100** combinando os detectores por confiabilidade; resumo de pasta agrupado **por jogador**.
- **Novos detectores:** Aimbot de 1 frame (mira vai ao alvo no tiro e volta) e Autofire (autopistol).
- **Strafe automático** recalibrado (troca de lado frame a frame): 9 de 11 demos de strafe detectadas, 0 falsos alarmes.
- **Script de agachamento** recalibrado: 7 de 7 detectadas.
- **Speedhack:** detecta rajadas (speedhack por tecla) e não gera mais falso alarme em fps muito alto (1000+);
  um pico isolado de lag não gera mais "Atenção".
- **Anti-aim:** giro contínuo agora exige 1,5 s (giros rápidos de mouse geravam falso alarme).
- Mapa `.bsp` localizado automaticamente ao lado da demo e nas instalações padrão do CS 1.6.
- `python -m vidalia.calibrar`: ferramenta para medir o Vidalia em demos rotuladas.
- GitHub Actions gera o `.exe` (com SHA-256) a cada versão.

### Mudanças anteriores ainda não publicadas
- **6 novos detectores** cobrindo funções dos multihacks de CS 1.6 detectados pelo ECD (HPP, Alternative, Furion,
  Oxware, Evol, Midnight...): **Strafe automático**, **Script de agachamento (SGS/DDRun)**, **Fake lag**, **No flash**,
  **No smoke** e **Assinaturas de cheat no console**. Experimentais. Veja `CHEATS_ECD.md`.
- Leitor de demos: movimento lateral/frontal do usercmd, mensagem `ScreenFade` (flashbang) e evento `createsmoke`.
- **Interface:** porcentagem exibida ao lado da barra de progresso e na linha de status (com "demo X de N" em análise de pasta).
- **Interface:** botões **Pausar**, **Retomar** e **Cancelar**. A barra fica laranja enquanto pausada.
  Ao cancelar, as demos já concluídas e seus relatórios são mantidos; o resumo da pasta não é gerado.
- Progresso calculado pelos bytes lidos da demo (antes saltava por segmento) e avançando a cada detector.

## 1.4.2: primeira versão pública
- Novo nome: **Vidalia Demo Analyzer** (executável `VidaliaDemoAnalyzer.exe`).
- Licença MIT, README, guia para administradores.
- `Gerar_EXE.bat` exibe o SHA-256 do executável para publicação.

## 1.4.1
- Evidências de um detector com resultado Normal passam a ser só diagnósticas (sem "Atenção"/"Suspeito").
- Evidências duplicadas removidas.

## 1.4
- Calibração com 55 demos (28 com cheat, 19 limpas de teste, 8 partidas reais limpas).
- **Triggerbot:** novo critério, o disparo no mesmo frame em que a mira entra no inimigo (limpos 17,5%; HPP ~60%).
  O critério antigo (até 60 ms) foi abandonado: jogadores limpos ficam ~48% abaixo de 60 ms.
- **Silent aim:** tolera a defasagem de 1 frame na gravação (removeu falso positivo em partida limpa).
- **Interface:** análise de pasta inteira com resumo HTML/CSV e filtros por gravidade e detector.

## 1.3 / 1.3.1
- **Wallhack:** evidências detalhadas (inimigo, distância, percurso, acompanhamento da mira, última visualização).
  Separa rastreamento ativo de pré-mira estática; só conta inimigo não visto há 1+ s.

## 1.2 / 1.2.1
- Calibração com 47 demos públicas. Speedhack pelo relógio cliente × servidor; bhop por pulos de 1 frame;
  silent aim pelo ângulo real do disparo.
- Wallhack com leitura do mapa `.bsp` (experimental).

## 1.1
- Correções de falsos positivos apontadas na validação com uma partida real (speedhack, no recoil, triggerbot).

## 1.0
- Leitor completo do protocolo de rede GoldSrc 48, 8 detectores, interface gráfica, relatórios HTML/JSON/CSV.
