# Guia rápido para administradores: Vidalia Demo Analyzer

## A regra de ouro

**O Vidalia não decide quem é cheater. Você decide, assistindo a demo.**
O programa só aponta *onde olhar*. Um banimento deve se basear no que você viu na demo,
de preferência confirmado por um segundo administrador.

## Como ler o resultado

| Resultado | O que fazer |
|---|---|
| **Suspeito** | Prioridade de revisão. Assista todos os momentos listados. |
| **Atenção** | Vale assistir, mas é comum em jogadores limpos e habilidosos. |
| **Normal** | Nada fora do padrão foi medido. *Não* garante que o jogador é limpo. |
| **Sem dados** | O detector não teve informação suficiente (demo curta, sem inimigos, mapa .bsp ausente). |

**Vários detectores diferentes** alertando na mesma demo pesam mais que um único alerta isolado.
A **pontuação (0–100)** já faz essa conta: soma os alertas com mais peso para os detectores calibrados.
Em 75 demos limpas de teste, nenhuma passou de 50. **40+** vale revisar; **70+** é alta prioridade.
**O mesmo padrão em várias demos** do mesmo jogador pesa mais que uma demo só.

## O que cada detector significa e como conferir

### Triggerbot
O jogador atira exatamente no frame em que a mira encosta no inimigo, repetidas vezes.
- **Jogadores limpos:** cerca de 17% dos disparos. **Triggerbot:** cerca de 60%.
- **Conferir:** em câmera lenta, a mira "esperando" parada e o tiro saindo no instante em que o inimigo cruza, sem nenhum atraso.
- **Falso alarme comum:** jogador segurando um ângulo e atirando por reflexo. Precisa de muitas amostras (30+).

### Aimbot
Giro brusco da mira terminando travado no alvo logo antes da kill.
- **Conferir:** a mira "pula" para a cabeça e para exatamente nela, sem passar do ponto nem corrigir.
- **Falso alarme comum:** flick de AWP de jogador habilidoso. Olhe o padrão ao longo de várias kills.

### Silent aim
A bala sai numa direção bem diferente de onde a mira está apontando.
- **Conferir:** kills com a mira visivelmente fora do inimigo.

### No recoil (experimental)
Rajadas longas sem o recuo normal da arma.
- **Conferir:** a mira não sobe durante a rajada de AK/M4.

### Wallhack (experimental, exige o mapa)
A mira acompanha um inimigo que está andando atrás de uma parede, sem que o jogador o tenha visto há pelo menos 1 segundo.
- O relatório diz se foi **RASTREAMENTO ATIVO** (inimigo andando e mira seguindo) ou **pré-mira estática** (mira parada num ângulo comum, o que é normal).
- **Conferir:** a mira "grudada" no inimigo através da parede, acompanhando o movimento dele.
- **Falsos alarmes comuns:** pré-mira em ângulos conhecidos; passos ouvidos; portas, caixas e fumaça (o programa não as enxerga).

### Bunny hop script
Sequências de pulos perfeitos, todos no primeiro frame em solo.
- **Scripts:** 84–93% de pulos perfeitos. **Humanos, mesmo com a rodinha do mouse:** até 60%.

### Speedhack
O relógio do jogador anda mais rápido que o do servidor, ou há **rajadas** de velocidade (speedhack ligado por tecla).
- **Limpos:** 1,00× (rajadas de até 1,5×). **Speedhack:** 2,9× a 30×. Um pico isolado pode ser lag; vários seguidos, não.

### Anti-aim / spinbot
Ângulos de visão impossíveis (olhando além do limite do jogo) ou giro contínuo.

### Aimbot de 1 frame
No frame do disparo a mira salta para o alvo e, no frame seguinte, volta exatamente para onde estava.
- **Limpos:** no máximo 2 disparos assim. **Aimbots testados:** 4 a 149.
- **Conferir:** em câmera lenta (`demo_timescale 0.1`), a mira "pisca" no inimigo no instante do tiro.

### Autofire (autopistol)
Pistola disparando no ritmo máximo da arma, com intervalos idênticos, por 16+ tiros seguidos.
- **Falso alarme possível:** scroll do mouse bindado no ataque. Pergunte ao jogador e confira o som dos tiros.

### Strafe automático
- **Troca de lado de um frame para o outro:** o movimento lateral passa de esquerda para direita sem nenhum frame neutro.
  Em 75 demos limpas isso aconteceu no máximo 4 vezes; nos strafes com cheat, de 10 a 407 vezes → **Suspeito**.
- **Sincronia perfeita:** o strafe acompanha o mouse em 95%+ de 300+ frames no ar → **Atenção**.
- **Conferir:** ganho de velocidade no ar anormal, com a mira fazendo zigue-zague curto e regular.

### Script de agachamento
Agachar e sair do chão no primeiro frame em solo, repetidas vezes (ground strafe / SGS / DDRun por script).
- **Limpos:** até 36% dos agachamentos com timing perfeito. **Scripts:** 69% a 100%.
- **Conferir:** sequência longa de "pulinhos agachados" com ritmo idêntico.

### Fake lag (experimental)
O jogo segue rodando, mas o jogador fica 100+ ms sem enviar pacotes, várias vezes.
- **Conferir:** os outros jogadores veem o suspeito "teleportando". Na demo dele, isso é pouco visível; peça a demo de outro jogador/HLTV.
- **Falso alarme possível:** conexão muito instável. Compare com outras demos do mesmo jogador.

### No flash (experimental)
Com a tela totalmente branca pela flashbang, o jogador acompanha um inimigo em movimento ou faz abates.
- **Falso alarme comum:** spray às cegas num ângulo conhecido. O acompanhamento repetido de alvo em movimento pesa mais.

### No smoke (experimental)
A mira acompanha um inimigo em movimento atrás do centro de uma fumaça.
- **Falso alarme comum:** spray na fumaça ou inimigo visível pela borda (a fumaça é aproximada por uma esfera).

### Assinaturas no console
Comandos gravados na demo contendo nomes de cheats (ex.: `hpp`, `oxware`) ou termos como `aimbot`/`wallhack`.
- Nome de cheat → **Suspeito**; termo genérico → **Atenção**. Chat e troca de nome são ignorados.
- **Ausência não inocenta:** a maioria dos cheats não deixa comandos na demo.

## Chat da partida

A aba **Chat** mostra tudo o que o jogador que gravou a demo recebeu no chat: falas de todos (inclusive mortos e
espectadores), rádio, trocas de nome e avisos do servidor/admin. Use **Destaques** para ver só as mensagens com
palavras como *cheat, wh, aim, ban, demo*, e **Buscar** para achar um nome ou assunto.
- Útil para ver **quando** outros jogadores começaram a desconfiar, se o suspeito **trocou de nome** e o que os admins avisaram.
- O chat do time adversário só aparece se o servidor o enviar para o gravador. A demo guarda o que **ele** recebeu.

## Como ir até o momento indicado na demo

Cada evidência traz **tempo (mm:ss)** e **frame**, contados a partir do início da gravação.

1. Copie a demo para a pasta `cstrike` do seu CS 1.6.
2. Abra o console (tecla `'`) e digite: `viewdemo nome_da_demo`
   Isso abre o reprodutor com barra de progresso, pausa e velocidade.
3. Avance até alguns segundos antes do tempo indicado.
4. Para câmera lenta, digite no console: `demo_timescale 0.25` (para voltar ao normal: `demo_timescale 1`).
5. Assista ao trecho várias vezes, em velocidade normal e em câmera lenta.

> O tempo pode variar alguns segundos em relação à barra do reprodutor. Comece um pouco antes.

## Boas práticas

- **Analise várias demos** do mesmo jogador: use **Pasta de demos** e veja o `vidalia_resumo.html`.
- **Informe a pasta `cstrike\maps`** para habilitar o detector de wallhack.
- **Guarde as demos** dos casos confirmados (cheat ou limpo). Elas ajudam a melhorar o programa.
- **Privacidade:** os relatórios contêm nomes e SteamIDs. Não publique para expor jogadores.
- **Em caso de dúvida, não bana.** Peça uma segunda opinião ou mais demos.
