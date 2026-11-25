# Histórico de versões

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
