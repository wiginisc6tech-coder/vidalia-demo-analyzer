# Vidalia Demo Analyzer

**Triagem automática de demos de Counter-Strike 1.6 (GoldSrc) em busca de sinais de trapaça.**
Gratuito, de código aberto, funciona offline no Windows, sem precisar do jogo instalado.

> ⚠️ **O Vidalia faz triagem, não julgamento.** Ele aponta momentos suspeitos com tempo e frame
> para você conferir na demo. Um resultado "Suspeito" **não é prova** de cheat, e um "Normal" não
> garante que o jogador seja limpo. Nunca bana ninguém só com base no relatório.

---

## Download

Baixe a versão mais recente na página **[Releases](../../releases)**:

- **`VidaliaDemoAnalyzer.exe`**: é só abrir, sem instalar nada.
- **Código-fonte (.zip)**: para rodar com Python ou conferir o código.

Confira o **SHA-256** e o link do **VirusTotal** publicados em cada versão. O executável é gerado
automaticamente pelo GitHub Actions a partir do código de cada versão (veja `.github/workflows/build.yml`).

> **Aviso do Windows/antivírus:** programas novos sem assinatura digital costumam ser bloqueados pelo
> SmartScreen ("O Windows protegeu o computador"). Clique em **Mais informações → Executar assim mesmo**.
> Alguns antivírus acusam falso positivo em executáveis gerados com PyInstaller. Se preferir, rode
> direto pelo código-fonte (veja abaixo).

## Como usar

1. Abra o `VidaliaDemoAnalyzer.exe`. O idioma (Português, English, Español, Русский) pode ser trocado no canto superior direito.
2. Em **Demo ou pasta**, escolha um arquivo `.dem` ou uma **pasta inteira** de demos.
3. (Opcional) Em **Mapas**, escolha a pasta `cstrike\maps` do seu CS para a análise de wallhack. Se ficar vazio,
   o Vidalia procura o mapa sozinho ao lado da demo e nas instalações padrão do CS 1.6.
4. Clique em **Analisar**.
5. Use os filtros **Mostrar** para ver só *Atenção/Suspeito* ou um detector específico.
6. Clique em **Abrir relatório completo** para ver o relatório no navegador.
7. Na aba **Momentos**, clique em um apontamento para ver o replay do trecho (4 s antes e 2 s depois), que para
   no frame exato do alerta. Use ←/→ para andar quadro a quadro e **Ampliar** (ou duplo clique) para abrir em uma
   janela grande. O replay é desenhado com os dados da demo, não é a imagem do jogo. Com o `.bsp` do mapa, ele
   mostra as paredes e marca os inimigos escondidos atrás delas. Na aba Detectores, um duplo clique em uma
   evidência leva direto ao momento.
   Com o CS 1.6 instalado, **Gravar vídeo real** abre o jogo sozinho, grava o trecho e mostra o vídeo de verdade
   na mesma aba (experimental; o mapa da demo precisa estar instalado). **Ver no jogo** abre o CS já no momento.
   Depois de gravar, **💾 Exportar MP4...** salva o vídeo no seu PC (normal ou em câmera lenta, com borda vermelha
   no frame do apontamento). Para isso é preciso o [ffmpeg](https://ffmpeg.org/download.html) (gratuito).
8. Na aba **Chat**, veja tudo o que foi digitado na partida (jogadores, rádio, admin e servidor), com busca e
   destaque de mensagens que falam em cheat, wh, ban, demo etc. O botão **Salvar chat** exporta em .txt ou .csv.

Os relatórios são salvos ao lado da demo:

| Arquivo | Conteúdo |
|---|---|
| `<demo>_vidalia.html` | Relatório visual com detectores, gráfico da mira, mortes e jogadores |
| `<demo>_vidalia.json` | Dados técnicos completos |
| `<demo>_vidalia_evidencias.csv` | Lista de evidências (tempo, frame, descrição), abre no Excel |
| `<demo>_vidalia_chat.txt` | Chat da partida: jogadores, rádio, trocas de nome e mensagens do servidor/admin |
| `vidalia_resumo.html` / `.csv` | Resumo de todas as demos, ao analisar uma pasta |

Veja também o **[Guia para administradores](GUIA_ADMINISTRADORES.md)**: como interpretar e conferir os alertas.

## O que é analisado

O Vidalia analisa o **jogador que gravou a demo** (demo POV, gravada com `record`).

| Detector | O que procura | Situação |
|---|---|---|
| Aimbot | Giro brusco da mira seguido de travamento preciso no alvo antes da kill | Experimental |
| Aimbot de 1 frame | Mira que vai ao alvo só no frame do tiro e volta no seguinte | Calibrado |
| Triggerbot | Disparo no mesmo frame em que a mira entra no inimigo | Calibrado |
| Silent aim | Disparo saindo muito fora da direção da mira | Calibrado |
| No recoil | Rajadas sem recuo ou com compensação perfeita | Experimental (máx. Atenção) |
| Wallhack | Mira acompanhando inimigo escondido atrás de parede (requer o `.bsp`) | Experimental (máx. Atenção) |
| Bunny hop script | Sequências de pulos com timing perfeito de 1 frame | Calibrado |
| Strafe automático | Strafe trocando de lado de um frame para o outro, ou sincronia perfeita com o mouse | Calibrado |
| Script de agachamento | Ground strafe / SGS / DDRun com timing perfeito | Calibrado |
| Speedhack | Relógio do cliente mais rápido que o do servidor; rajadas de velocidade | Calibrado |
| Autofire | Muitos tiros seguidos de pistola no ritmo exato da arma | Calibrado (máx. Atenção) |
| Anti-aim / spinbot | Ângulos impossíveis e giro contínuo | Básico |
| Fake lag | Cliente retendo pacotes por 100+ ms com o jogo rodando normalmente | Experimental (máx. Atenção) |
| No flash | Mira acompanhando inimigos ou abates com a tela totalmente branca | Experimental (máx. Atenção) |
| No smoke | Mira acompanhando inimigos através do núcleo de uma fumaça | Experimental (máx. Atenção) |
| Assinaturas no console | Nomes/comandos de cheats (lista baseada no ECD) nos comandos gravados | Básico |

Vários deles cobrem funções dos multihacks de CS 1.6 detectados pelo ECD (HPP, Alternative, Furion,
Oxware, Evol, Midnight...). Veja **[Cheats do ECD × detectores do Vidalia](CHEATS_ECD.md)**.

**Pontuação (0–100):** combina todos os alertas, dando mais peso aos detectores calibrados.
40+ vale revisar; 70+ é alta prioridade. Na análise de pasta, o resumo também agrupa **por jogador**.

**Resultados possíveis:** `Normal`, `Atenção` (vale assistir), `Suspeito` (prioridade de revisão), `Sem dados`.

## Precisão atual (versão 1.5.0)

Medida com as **211 demos públicas** do [UnrealDemoScanner](https://github.com/UnrealKaraulov/UnrealDemoScanner):
134 com cheat (HPP, Furion, Evol, Midnight, Interium...) e 75 limpas, muitas delas testes de situações difíceis.

| | Demos | Marcadas "Suspeito" | Com algum alerta | Pontuação ≥ 50 |
|---|---|---|---|---|
| Com cheat | 134 | 39 | 53 | 39 |
| Limpas | 75 | **0** | 8 (só "Atenção") | **0** |

A maioria das demos com cheat são clipes curtos de uma única função, por isso muitas não têm o que detectar.
**Os limiares foram ajustados com essas mesmas demos**, então os números são otimistas. Detalhes, limiares e
o que *não* dá para detectar pela demo estão em **[CALIBRACAO.md](CALIBRACAO.md)**.

O leitor de demos decodificou **100% dos pacotes de rede** de todas as demos limpas testadas.

## Limitações conhecidas

- Analisa apenas o jogador que gravou a demo; demos HLTV ainda não são suportadas.
- Wallhack considera só a geometria sólida do mapa: portas, caixas móveis e fumaça não entram.
- Cheats modernos e "humanizados" podem não ser detectados.
- Clipes muito curtos (poucos segundos) não têm dados suficientes.
- "Perfect silent" (HPP/Furion) não deixa rastro mensurável na demo.
- A precisão ainda não foi validada em um conjunto independente de demos (veja [CALIBRACAO.md](CALIBRACAO.md)).

## Privacidade

Os relatórios mostram **nome e SteamID** dos jogadores da demo. Use-os apenas na administração do
seu servidor e não os publique para expor ou acusar jogadores. Todo o processamento é local:
nenhum dado é enviado para a internet.

## Rodar pelo código-fonte

Requer Python 3.10+ (sem bibliotecas extras).

```bat
:: interface gráfica
Iniciar.bat
:: ou linha de comando (várias demos geram também o resumo)
py -m vidalia demo1.dem demo2.dem --mapas "C:\...\cstrike\maps" --saida relatorios
```

Para gerar o executável: `Gerar_EXE.bat` (instala o PyInstaller e cria `dist\VidaliaDemoAnalyzer.exe`).

### Testes

```bat
py -m unittest discover tests
```

A regressão com demos reais roda definindo `VIDALIA_DEMOS` para a pasta do repositório
[UnrealDemoScanner](https://github.com/UnrealKaraulov/UnrealDemoScanner) (com `CheatDemos*` e `ClearDemos*`).

### Calibrar com as suas demos

```bat
py -m vidalia.calibrar C:\demos\cheat C:\demos\limpas --rotulos rotulos.csv --csv metricas.csv
```

Mostra, por detector, quantas demos com cheat foram detectadas e quantas limpas geraram alarme.
O formato do `rotulos.csv` está no início de `vidalia/calibrar.py`.

## Como contribuir

- **Demos são o que mais ajuda:** demos de jogadores banidos com cheat confirmado (diga qual cheat)
  e de jogadores confiáveis ajudam a calibrar os detectores. Abra uma *issue*.
- **Falso positivo?** Abra uma *issue* com o relatório JSON e, se possível, a demo.
- Correções e melhorias são bem-vindas via *pull request*.

## Créditos

Desenvolvido com a ajuda do **Claude (Anthropic)** e do **ChatGPT (OpenAI)**.
Demos de teste públicas: [UnrealDemoScanner](https://github.com/UnrealKaraulov/UnrealDemoScanner).

## Licença

[MIT](LICENSE): uso livre, inclusive comercial, mantendo o aviso de copyright.
