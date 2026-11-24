# Histórico de versões

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
