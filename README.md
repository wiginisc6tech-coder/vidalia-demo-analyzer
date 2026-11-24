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

Confira o **SHA-256** e o link do **VirusTotal** publicados em cada versão.

> **Aviso do Windows/antivírus:** programas novos sem assinatura digital costumam ser bloqueados pelo
> SmartScreen ("O Windows protegeu o computador"). Clique em **Mais informações → Executar assim mesmo**.
> Alguns antivírus acusam falso positivo em executáveis gerados com PyInstaller. Se preferir, rode
> direto pelo código-fonte (veja abaixo).

## Como usar

1. Abra o `VidaliaDemoAnalyzer.exe`.
2. Em **Demo ou pasta**, escolha um arquivo `.dem` ou uma **pasta inteira** de demos.
3. (Opcional) Em **Mapas**, escolha a pasta `cstrike\maps` do seu CS: isso habilita a análise de wallhack.
4. Clique em **Analisar**.
5. Use os filtros **Mostrar** para ver só *Atenção/Suspeito* ou um detector específico.
6. Clique em **Abrir relatório completo** para ver o relatório no navegador.

Os relatórios são salvos ao lado da demo:

| Arquivo | Conteúdo |
|---|---|
| `<demo>_vidalia.html` | Relatório visual com detectores, gráfico da mira, mortes e jogadores |
| `<demo>_vidalia.json` | Dados técnicos completos |
| `<demo>_vidalia_evidencias.csv` | Lista de evidências (tempo, frame, descrição), abre no Excel |
| `vidalia_resumo.html` / `.csv` | Resumo de todas as demos, ao analisar uma pasta |

Veja também o **[Guia para administradores](GUIA_ADMINISTRADORES.md)**: como interpretar e conferir os alertas.

## O que é analisado

O Vidalia analisa o **jogador que gravou a demo** (demo POV, gravada com `record`).

| Detector | O que procura | Situação |
|---|---|---|
| Aimbot | Giro brusco da mira seguido de travamento preciso no alvo antes da kill | Experimental |
| Triggerbot | Disparo no mesmo frame em que a mira entra no inimigo | Calibrado |
| Silent aim | Disparo saindo muito fora da direção da mira | Calibrado |
| No recoil | Rajadas sem recuo ou com compensação perfeita | Experimental (máx. Atenção) |
| Wallhack | Mira acompanhando inimigo escondido atrás de parede (requer o `.bsp`) | Experimental (máx. Atenção) |
| Bunny hop script | Sequências de pulos com timing perfeito de 1 frame | Calibrado |
| Speedhack | Relógio do cliente mais rápido que o do servidor | Calibrado |
| Anti-aim / spinbot | Ângulos impossíveis e giro contínuo | Básico |

**Resultados possíveis:** `Normal`, `Atenção` (vale assistir), `Suspeito` (prioridade de revisão), `Sem dados`.

## Precisão atual (versão 1.4)

Medida com 55 demos públicas, do repositório de testes do [UnrealDemoScanner](https://github.com/UnrealKaraulov/UnrealDemoScanner),
e partidas reais de jogadores limpos:

| | Demos | Marcadas "Suspeito" | Marcadas "Atenção" | Sem alerta |
|---|---|---|---|---|
| Com cheat | 28 | 10 | 3 | 15 |
| Limpas | 27 | **0** | 1 | 26 |

Muitas demos com cheat não detectadas são clipes de poucos segundos ou cheats ainda não cobertos
(autofire, no spread). **Esses números vêm das mesmas demos usadas para ajustar os detectores**;
uma validação independente está planejada para a próxima versão.

O leitor de demos decodificou **100% dos pacotes de rede** de todas as demos testadas, incluindo uma
partida real de 29 minutos (158 mil pacotes).

## Limitações conhecidas

- Analisa apenas o jogador que gravou a demo; demos HLTV ainda não são suportadas.
- Wallhack considera só a geometria sólida do mapa: portas, caixas móveis e fumaça não entram.
- Cheats modernos e "humanizados" podem não ser detectados.
- Clipes muito curtos (poucos segundos) não têm dados suficientes.
- A precisão ainda não foi validada em um conjunto independente de demos.

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

A regressão com demos reais roda definindo `VIDALIA_DEMOS` para uma pasta com `cheat\`, `clean\` e `pro\`
(lista em `tests/data/demos_publicas.txt`).

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
