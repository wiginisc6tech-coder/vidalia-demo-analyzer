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
O relógio do jogador anda mais rápido que o do servidor.
- **Limpos:** 1,00×. **Speedhack:** 5–6×. Um pico isolado pode ser lag; vários seguidos, não.

### Anti-aim / spinbot
Ângulos de visão impossíveis (olhando além do limite do jogo) ou giro contínuo.

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
