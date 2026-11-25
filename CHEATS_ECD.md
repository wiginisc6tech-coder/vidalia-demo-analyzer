# Cheats detectados pelo ECD × detectores do Vidalia

Este documento resume os cheats que aparecem nos relatórios públicos do **ECD (Easy Cheats Detector)**,
em [fungun.top/ecd/list](https://fungun.top/ecd/list/), e mostra o que o Vidalia consegue (e não consegue) detectar a partir de uma demo.

## Como os dois funcionam (e por que são complementares)

| | ECD | Vidalia |
|---|---|---|
| **O que examina** | O computador do jogador: memória do jogo, processos, drivers, arquivos, registro e histórico de downloads | A demo (`.dem`) gravada pelo jogador |
| **Como detecta** | Por assinatura: compara com um banco de cheats conhecidos | Por comportamento: mira, movimento, rede e disparos impossíveis ou anormais |
| **Pega cheat novo ou privado?** | Só depois que entra no banco | Sim, se o comportamento aparecer na demo |
| **Pega cheat instalado mas sem uso?** | Sim | Não |

Ou seja, o Vidalia **não identifica o nome do cheat** (a demo não contém processos nem DLLs). Ele identifica
**as funções** do cheat sendo usadas: aimbot, strafe automático, fake lag etc.

## Amostra analisada

Em 25/11/2026 foram lidos os nomes de cheats de cerca de 50 relatórios com resultado **"Cheats detected"**
e 50 com resultado **"Suspicious"**, a página mais recente de cada filtro. Apenas o nome e o tipo do cheat
foram registrados, sem dados dos jogadores. A contagem abaixo é de ocorrências nessa amostra, não do banco inteiro do ECD.

### 1. Multihacks de CS 1.6 (injetados no jogo): os que importam para o Vidalia

| Cheat (como aparece no ECD) | Ocorrências |
|---|---|
| Alternative Hack / Alternative GigNight Hack | 19 |
| Furion Hack | 14 (+8 só instalados) |
| HPP Hack / HPP DATA | 18 |
| Oxware Hack | 8 (+4 suspeitos) |
| Evol hack | 6 |
| MIDNIGHT HACK | 5 |
| Python Hack, BlueMonday Hack | 4 cada |
| Nash Hack | 3 |
| Zemon, R-AimBot, tobys dk cheats | 2 cada |
| NorAdrenaline, Memsense, Visual Hack, AdvHack, Enhanced hack, MPH Hack, hack-strikeru, Private Aim, Catlean client, tcheats, Crystal, TapWare, Evelion | 1 a 4 cada |

Multihacks de CS 1.6 costumam reunir: **aimbot / silent aim**, **triggerbot**, **ESP / wallhack**,
**no recoil / no spread**, **funções de movimento** (bhop, auto-strafe, ground strafe), **speedhack**,
**anti-aim** e **fake lag**. Cada cheat ativa um subconjunto, conforme a configuração do jogador.

### 2. Hooks de OpenGL e cheats simples de CS 1.6

`[CS16] opengl32.dll hooked` (7), `Opengl32 multihack`, `No smoke` (3), `Norecoil`, `AimBot`,
`ESP + Strafe hack`, `Bloo's cheat script`.
Esses atuam na renderização (wallhack, **no smoke**, **no flash**) ou em uma única função.

### 3. Fora do alcance de uma demo de CS 1.6

- **Cheats de CS2 / CS:GO:** Osiris, AIMWARE, Interium, Onetap, ExHack, Enigma, ExtrimHack, GOESP, XONE (no relatório aberto, injetado no CS2), Midnight (versão CS2), nixware, undetek.
- **Loaders, drivers e ferramentas:** ExLoader (o item mais frequente da amostra), Hack Driver Inject, Cheat Driver Loader,
  "Active cheat injection", "Injected console", assinaturas de biblioteca ImGui, "FPS booster".
- **Bypass do próprio scanner:** Renegat1337 WG/ECD Bypass.
- **Downloads e sites:** UnknownCheats, EZCheats, AIMCOOP, 100cheats, hackvshack.

Esses itens só podem ser vistos por um scanner no PC, como o ECD. O Vidalia só detecta o que eles
fazem dentro de uma partida de CS 1.6.

## Função do cheat → detector do Vidalia

| Função | Cheats da lista que normalmente a oferecem | Detector do Vidalia | Desde |
|---|---|---|---|
| Aimbot | multihacks (HPP, Alternative, Oxware...), "AimBot", R-AimBot, Private Aim | **Aimbot** | 1.0 |
| Silent aim / psilent | multihacks | **Silent aim** | 1.0 |
| Triggerbot | multihacks | **Triggerbot** | 1.0 |
| No recoil | multihacks, "Norecoil" | **No recoil** | 1.0 |
| Wallhack / ESP | multihacks, opengl32 hooks, "ESP + Strafe hack" | **Wallhack** (exige o `.bsp`) | 1.2 |
| Bunny hop | multihacks, scripts | **Bunny hop script** | 1.0 |
| Speedhack | multihacks | **Speedhack** | 1.0 |
| Anti-aim / spinbot | multihacks | **Anti-aim / spinbot** | 1.0 |
| Auto-strafe / strafe helper | multihacks, "ESP + Strafe hack" | **Strafe automático** | **novo** |
| Ground strafe / SGS / DDRun | multihacks, scripts | **Script de agachamento** | **novo** |
| Fake lag | multihacks | **Fake lag** | **novo** |
| No flash | multihacks, opengl32 hooks | **No flash** | **novo** |
| No smoke | "No smoke", opengl32 hooks | **No smoke** | **novo** |
| Comandos/nomes do cheat | qualquer um que registre comandos | **Assinaturas no console** | **novo** |
| Aimbot que "pisca" no alvo no tiro | multihacks (HPP, "aimpack", "Zero") | **Aimbot de 1 frame** | 1.5 |
| Autopistol / autofire | multihacks (HPP, "Zero") | **Autofire** | 1.5 |

### Como os detectores novos funcionam

- **Strafe automático:** no ar, verifica se o movimento lateral troca de lado **a cada frame** ("silent strafe"),
  o que é impossível no teclado e pode resultar em **Suspeito**. Também mede a sincronia entre o lado do strafe e
  o giro do mouse; ~100% salto após salto resulta em **Atenção**.
- **Script de agachamento:** mesma lógica, já calibrada, do detector de bhop, aplicada ao `+duck`: agachar sempre
  no primeiro frame em solo.
- **Fake lag:** frames seguidos com o mesmo número de pacote de saída (`outgoing_sequence`) por 100+ ms, enquanto
  o jogo roda normalmente. Travadas do PC são descartadas.
- **No flash:** lê a mensagem `ScreenFade` da flashbang. Durante o cegamento total, procura mira acompanhando inimigo
  em movimento e abates.
- **No smoke:** lê o evento `createsmoke` (posição da fumaça). Procura mira acompanhando inimigo cuja linha de visão
  atravessa o núcleo da fumaça, aproximado por uma esfera de 110 unidades entre 1,5 s e 16 s após a detonação.
- **Assinaturas no console:** procura nos comandos gravados na demo os nomes de cheats acima (`hpp`, `oxware`,
  `midnight`...) e termos como `aimbot`, `wallhack`, `fakelag`. Chat (`say`) e troca de nome são ignorados.

## Limitações

- **Strafe automático e script de agachamento foram calibrados** com demos reais de HPP, Evol, Midnight, Interium e
  "Zero" (veja [CALIBRACAO.md](CALIBRACAO.md)). **Fake lag, no flash e no smoke continuam experimentais**, limitados a
  **Atenção**, porque o acervo público não tem demos reais dessas funções. Demos de jogadores pegos pelo ECD seriam
  ideais para calibrá-los: abra uma *issue*.
- **Ainda não coberto:** *perfect silent* (não deixa rastro na demo), *no spread*, *backtrack/fake latency*,
  *knifebot* e ESP sem nenhuma reação visível do jogador.
- Um cheat bem configurado ("legit") pode não produzir nenhum padrão mensurável. **"Normal" não inocenta.**
  Use o Vidalia junto com o ECD e a revisão humana da demo.
