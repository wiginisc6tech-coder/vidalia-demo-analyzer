# Calibração com demos reais

## Conjunto de demos

As **211 demos públicas** do repositório [UnrealDemoScanner](https://github.com/UnrealKaraulov/UnrealDemoScanner)
(pastas `CheatDemos`, `CheatDemos1`, `CheatDemos2`, `ClearDemos`, `ClearDemos_2`, `FalsePositive`, `PartiallyCheatDemos`):

| Rótulo | Demos | Conteúdo |
|---|---|---|
| Com cheat | 134 | HPP, Furion, Evol, Midnight, Interium, Alternative, "Zero" e outros, quase sempre uma função por demo (nome do arquivo: `strafe_hpp`, `midnight_groundstrafe`, `hpp_autopistol`...) |
| Limpas | 75 | Jogo normal, testes de sensibilidade, fps alto/baixo, rate ruim, lag, agachamentos, pulos com scroll do mouse, e 2 demos conhecidas por gerar falso positivo |
| Parciais | 2 | "fps hack" |

As demos não fazem parte deste repositório. Para reproduzir a medição, baixe o repositório acima e rode:

```
python -m vidalia.calibrar CAMINHO/UnrealDemoScanner/CheatDemos CAMINHO/UnrealDemoScanner/ClearDemos ... --teste --csv metricas.csv
```

O teste `tests/test_real_demos.py` roda a mesma verificação quando a variável `VIDALIA_DEMOS` aponta para essa pasta.

## Resultado (versão 1.5.0, todas as 211 demos)

| | Antes (1.4.2 + detectores ECD sem calibrar) | Depois (1.5.0) |
|---|---|---|
| Demos com cheat marcadas **Suspeito** | 18 de 134 | **39 de 134** |
| Demos com cheat com algum alerta | 37 de 134 | **53 de 134** |
| Demos limpas marcadas **Suspeito** | 2 de 75 | **0 de 75** |
| Demos limpas com **pontuação ≥ 50** | – | **0 de 75** |
| Demos limpas com **Atenção** | 7 de 75 | 8 de 75 |

### Por função (demos cujo nome indica a função)

| Função | Antes | Depois | Observação |
|---|---|---|---|
| Strafe automático | 2/11 | **9/11** | Os 2 restantes (`zero_only_strafe*`) usam outra técnica |
| Ground strafe / SGS | 4/7 | **7/7** | |
| Speedhack | 4/6* | 4/6 (8 demos no total, contra 4) | *Antes havia 1 falso "Suspeito" em demo limpa a 1160 fps. Agora detecta rajadas (speedhack por tecla). Os 2 não detectados são "fastrun"/"speedrun" (truques de movimento) |
| Bunny hop | 9/25 | 9/25 | Inalterado |
| Aimbot (todas as formas) | 2/16 | 2/16 + novo detector "vai e volta" (4 demos de aimbot sem "aim" no nome) | |
| Autofire / autopistol | 0/6 | 0/6 (2 outras demos detectadas) | Ver limitações |

## Limiares calibrados (o que separa limpas de cheats)

| Detector | Demos limpas (pior caso) | Demos com cheat |
|---|---|---|
| Strafe automático: trocas de lado de um frame para o outro | ≤ 4 (0,2% dos frames no ar) | 10 a 407 (3,5% a 67%) |
| Strafe automático: sincronia com o mouse em 300+ frames | ≤ 42% | 93% a 100% |
| Script de agachamento: saídas do chão com 1 frame em solo | ≤ 36% | 69% a 100% ("Zero": 91–98% com 2 frames) |
| Aimbot de 1 frame (mira vai ao alvo no tiro e volta) | ≤ 2 disparos (3,4%) | 4 a 149 disparos (10% a 73%) |
| Autofire: tiros seguidos no ritmo exato da arma | ≤ 12 | 7 a 30 (alerta a partir de 16) |
| Anti-aim: giro contínuo acima de 2000°/s | ≤ 0,5 s (giros de mouse) | exige 1,5 s |
| Speedhack: pico de msec declarado / tempo real em 0,5 s | ≤ 1,48× | 2,9× a 30× (Furion, Interium, speedhackmax, HPP) |

## Honestidade sobre os números

- **Os limiares foram escolhidos olhando todas as 211 demos.** A opção `--teste` separa 30% das demos por sorteio fixo
  (no teste: 12 de 43 demos com cheat marcadas Suspeito, 0 de 21 limpas), mas, como os limiares foram decididos vendo o
  conjunto inteiro, isso **não é uma validação independente**. A medição honesta exige demos novas, de partidas reais.
- A maioria das demos com cheat são **clipes curtos de uma única função**, muitas sem inimigos. Por isso detectores de
  mira (aimbot, triggerbot, wallhack) aparecem pouco nesses números.
- Demos limpas do acervo são, em boa parte, **testes de situações difíceis** (sensibilidade extrema, lag, fps
  extremo), justamente para provocar falsos positivos. É uma boa amostra de "pior caso", mas pequena.

## O que os dados mostraram que **não** dá para detectar pela demo

- **"Perfect silent" (HPP/Furion):** a demo grava o ângulo já alterado e não há nenhuma divergência nem salto de mira.
  Nenhum dos 6 exemplos deixa rastro mensurável.
- **Fake lag / fake latency:** cada frame da demo corresponde a um pacote *recebido*, e não a um frame do jogo. O padrão de
  envio depende muito da configuração de fps/rate do jogador (uma demo limpa teve 26% de frames sem envio). O detector
  de fake lag teve 0 falsos alarmes, mas não há demos reais de fake lag para validá-lo.
- **Knifebot:** só 3 exemplos e nenhuma demo limpa com uso de faca suficiente para comparar.
- **Autopistol com poucos tiros seguidos:** humanos rápidos (ou scroll do mouse) chegam a 12 tiros no ritmo da arma.

## Como ajudar

Demos de **partidas reais** de jogadores **comprovadamente** pegos (por exemplo, pelo ECD) e de jogadores
**comprovadamente limpos** são o que mais melhora a precisão. Rode `python -m vidalia.calibrar` na sua pasta de demos
(com um `rotulos.csv`) e compartilhe o resumo e o CSV de métricas, sem as demos, se houver dados pessoais.
