# CLAUDE.md — Laboratório de Mídia

Ferramenta **da família** (serve a todos os apps). Antes de tudo, a regra da família:
`../CLAUDE.md` (o `PROGRAMAS COM CLAUDE/CLAUDE.md`) e a skill `ciclo-media-dev` — consultar o banco
(`bancodedadosnles`, ache subindo de pasta) ANTES de investigar, registrar nele DEPOIS de descobrir.

O autor é o Lohan, editor de vídeo, não programador. Português do Brasil, linguagem de editor, gestos
(duplo clique, "pode seguir") em vez de comandos.

## ⭐⭐⭐ "Execute o roteiro de demonstração" (autor, 2026-10-22)

Quando o autor disser isso (ou "roda a demo", "mostra o roteiro"), é uma APRESENTAÇÃO ao vivo: assuma o teste
inteiro sozinho, sem perguntar nada, sem ler o handoff e sem investigar. Vale como "pode pilotar" (skill `/piloto`:
leia as regras dela antes do primeiro gesto). Uma linha curta por passo, em linguagem de editor, para quem assiste.
O teste é o multicam de quatro câmeras pelo **Órbita standalone** (janela "Órbita", à direita, botão **Sincronizar** no rodapé) no **Premiere 2026** (o 2023 quebrou em 22/10)
(`lab/bancadas/demo_multicam.py`; o cabeçalho explica cada peça). Rode com `PYTHONIOENCODING=utf-8`.

1. Diga em uma linha o que vai acontecer e que o freio é o **F12**.
2. `python -m lab.bancadas.demo_multicam preparar` (~3 min): gera a mídia, fecha o Ciclo Assist se estiver aberto,
   abre o Órbita e o Premiere com um projeto novo, importa tudo na bin `DEMO 4 CAMERAS` e põe as janelas lado a lado
   (Premiere à esquerda, Órbita à direita). Enquanto gera, mostre o `mosaico.png` da rodada (Read): o mesmo instante
   nas quatro câmeras, e a CAM 4 sem timecode marcando outro relógio.
3. `foto antes "o Premiere com a bin importada"` e LEIA a foto: meça o **ícone** da bin `DEMO 4 CAMERAS` no painel
   Project do Premiere (selecionada, à esquerda) e o meio da janela do Órbita (à direita). No ensaio (1920×1080):
   ícone em (110, 271), meio do Órbita em (1640, 600). A bin já vem SELECIONADA pela API: arraste SEM clicar antes
   (clique + arrasto = duplo clique, skill do piloto).
4. `arrastar X0 Y0 X1 Y1` — a bancada fotografa antes, no meio do gesto e depois. Leia a foto "solto": o Órbita tem de
   mostrar as fontes (CAM A–D com "2 clipes · CAM n" e SOM DIRETO). No meio do gesto o Órbita mostra o contorno
   tracejado de "solte aqui". Não mostrou as fontes = foto e pare (nunca repetir o gesto às cegas).
5. Meça o botão **Sincronizar** (rodapé do Órbita; no ensaio, (1640, 947)) na foto e `clicar X Y "Sincronizar"`;
   confira na foto que o sync começou (o botão vira "sincronizando…" e aparece a barra no topo).
6. `esperar` (prazo de 6 min, foto a cada minuto) → `conferir`.
7. Publique o `relatorio.html` da rodada (a pasta está em `saida/bancadas/demo_multicam/ATUAL.txt`) com o Artifact
   tool, `icon: "chart"`, e dê o link. Diga em duas linhas o veredito e o que os gráficos mostram.

**Se algo falhar ao vivo:** diga em uma linha o que a foto mostra, NÃO depure, e ofereça o relatório do ensaio
(plano B: https://claude.ai/artifact/RKsnr24C1PrevGBcQ8b64M). Diálogo desconhecido = foto e pare.

**Ensaio de 2026-10-22 21h31 (Premiere 26.5, Órbita 0.4.0):** `preparar` 1 min 41 s (mídia 76 s; o 2026 CRIA o
projeto pela API), arrasto 5 s, do clique à sequência 38 s, régua ≤ 1 quadro nos 10 arquivos (CAM 4 sem TC exata;
CAM 3 T01 −1 quadro). Tudo em ~3 min 30 s, mais o tempo da sessão olhando as fotos.

## O que é

Mídia **sintética**, gerada pelo ffmpeg a partir de **receitas** (JSON), que diz em cada quadro e em cada
canal o que é. Cada caso gera um `verdade.json`; os testes e os validadores dos apps comparam com ele.

**Plano aprovado pelo autor em 2026-10-06:** `docs/organograma-2026-10-06.html`
(publicado em https://claude.ai/artifact/Xgo3sGcNLSDX8yn4M6muwW). Resumo e decisões em `README.md`.
Estado do trabalho: `.dev/HANDOFF.md` — leia ao começar, atualize ao terminar.

## Quem opera: o Claude

"O laboratório é feito para você operar, a menos que não seja possível" (autor, 2026-10-06). O autor dá a missão;
o Claude cria os projetos nos NLEs, importa, mede, tira prints e registra — sem devolver passos ao autor. Só o
que a máquina não alcança (um diálogo que só a mão fecha, uma licença) volta para ele.

- **Bancadas** (`lab/bancadas/`): a metade que roda DENTRO do NLE (`resolve.py`, pelo MCP do Resolve com
  `run_script_unsafe`, em passos de < 60 s) grava `saida/bancadas/<nle>/<caso>/<nle>.json` + stills + renders;
  `python3 -m lab.bancadas.conferir <trabalho> <caso>` lê tudo contra a verdade e grava
  `resultados/<caso>/<nle>-<versão>-<plataforma>.json` (no Git) — e o `resultados/<caso>/<NLE>.md` conta em
  linguagem de editor. Projetos do Resolve: pasta `LABORATORIO` do Project Manager, um projeto por caso.
- **Premiere:** a PONTE (`lab/bancadas/premiere.py` + a extensão CEP invisível `lab/bancadas/premiere/ponte-cep/`)
  executa ExtendScript recebido em 127.0.0.1 com token — autorizada pelo autor ("ponte livre", 2026-10-06), mas é uma
  porta de execução de código. **Nesta máquina (ambiente de teste) ela FICA instalada** — decisão do autor (2026-10-06:
  "a ponte do premiere não precisa ser excluída e retornada toda hora"); `remover()` só se o autor pedir ou numa
  máquina de produção. Instala por
  CÓPIA (o symlink do `com.orbita.sonda` quebrou quando o Órbita mudou de pasta). O Premiere só lê a extensão ao ABRIR
  (`reabrir_premiere(ano)`). Diálogo do Premiere trava a ponte: o **VIGIA DE DIÁLOGOS** (`lab/bancadas/vigia_dialogos.py`,
  sobe sozinho no `esperar_ponte`) fecha os CONHECIDOS pela acessibilidade do macOS — Return no diálogo do Premiere em foco
  com título conhecido, OK no "Relatório de Problemas", fecha o relatório de erro da Adobe — e registra cada um com print em
  `saida/bancadas/vigia/`; o desconhecido ele NÃO clica (print + registro). Se o Premiere cair, `premiere.retomar(ano, f)`
  reabre e refaz. O autor não precisa acompanhar (2026-10-07: "eu não posso ficar acompanhando esse processo sempre").
  Diálogo novo que se repete = regra nova em `REGRAS`. Arquivo recusado entra na lista `recusados` e não volta.
- ⭐ **100 % autônomo, com as liberdades do laboratório** (autor, 2026-10-11): o objetivo é rodar TODO teste sem o
  autor. Função que a API/script não alcança mas que aceita **tecla de atalho** → um **teclado personalizado só do
  laboratório**, por NLE (o Avid é o mais personalizável; o Premiere e o Resolve têm o seu leque), com as teclas que a
  bancada aperta. E **presets/configurações de usuário valem aqui** (ex.: preset de EXPORT do Avid para o render de
  referência): o autor os barra no APP porque são do usuário e fora do nosso controle — no laboratório podemos, e isso
  **não vira regra do app**. Tecla só vai com o NLE em primeiro plano (conferir antes, `servico/teclado.py` do De Lá
  Pra Cá); cada teclado/preset do laboratório fica descrito em `lab/bancadas/<nle>/` para ser reinstalado.
- ⭐ **Media Composer — o FOCO dispara coisas** (autor, 2026-10-11): ao abrir, o MC perde o foco, e janelas como a do
  layout de teclado só aparecem quando ele GANHA o foco; a varredura da MediaFiles (recriar `.mdb`/`.pmr`) também.
  Regra: antes e depois de toda ação no MC, conferir onde está o foco, trazer o MC para a frente e VARRER os diálogos
  (`vigia_windows.varrer` com o catálogo de `lab/bancadas/avid/dialogos/`). O catálogo reconhece pela FOTO (o diálogo
  Qt não tem texto acessível e o título pode ser genérico) e diz o botão; desconhecido = foto + parar. Perfil de usuário
  do laboratório: **DLPC_LAB** (de fábrica, criado pelo autor; em `Avid Users\CICLO MEDIA`); projetos em
  `Documents\Avid Projects\DLPC LAB\`, um por taxa; mídia escrita pelo laboratório em `D:\Avid MediaFiles\MXF\3572`.
- ⭐ **Cão de guarda: nenhuma espera sem prazo** (autor, 2026-10-11: "eu encontrei você esperando por algo que nunca
  chegaria"). Toda ação num NLE roda em `vigia_windows.com_prazo`: prazo + checagem periódica (processo vivo, janela
  respondendo, queda nova no EVENTLOG do MC, diálogos). Travou, caiu ou estourou → `Travado` com a foto da tela, e a
  sessão decide (reabrir, repetir, registrar) — nunca ficar esperando.
- **Beta 27.1** (`"Beta"` no lugar do ano): não sai pelo `app.quit()`/AppleScript — fechar o projeto e esperar; não usar
  `kill` à toa (gera relatório de falha).
- Cada rodada do Premiere guarda o `.prproj` e a impressão digital da estrutura em `resultados/<caso>/prproj/`
  (`lab/prproj_estrutura.py`) — o insumo do estudo de DOWNGRADE (uma rodada por versão: 2023, 2025, 2026).
- Print da tela: `osascript -e 'tell application "DaVinci Resolve" to activate'` + `screencapture -x` (Mac).
  Vai para `saida/…/prints`; a cópia em JPEG que conta a história vai para `resultados/<caso>/prints/`.

## Regras deste projeto

- **Laboratório ≠ mídia de teste.** Aqui é o mundo controlado. Material real de produção mora em
  `MIDIAS DE TESTES/1 PRODUCOES`; arquivos reais de câmera (a "coleta") em
  `MIDIAS DE TESTES/2 FORMATOS E CAMERAS/<formato>/`. No Git daqui ficam só as **fichas** (`fichas/`).
- **Receita, não arquivo.** No Git: o gerador (`lab/`), as receitas, os testes, as fichas.
  Fora do Git: `saida/` (pode apagar e refazer, em qualquer máquina).
- **Windows e Mac, do mesmo SSD (exFAT).** Só biblioteca padrão do Python + ffmpeg/ffprobe: sem venv,
  sem pip. O ffmpeg é achado por `lab/ffmpeg.py` (PATH + onde os instaladores põem; nunca `shutil.which`).
  ⛔ **Nada de `drawtext`**: o ffmpeg do Homebrew não tem (2026-10-06) — texto é `drawbox`
  (`lab/fonte_pixel.py`, dígitos de 7 segmentos em `lab/video.py`). Conferir a matriz de plataforma do banco
  antes de mexer em caminho, subprocesso ou encoding. Sem symlinks.
- **Quadro por posição: nunca `-ss`.** `select=eq(n,N)` + `-fps_mode passthrough` (a busca do MPEG-2 cai no
  quadro errado — banco, `protocolos/mxf/README.md`).
- **Teste que pula não prova nada:** a suíte avisa `PULADO — sem ffmpeg`; conte os pulados antes de dizer que passou.
- **Verificar fecha o laço:** nenhum arquivo gerado vale antes de o `verificar` conferir (ffprobe +
  leitura do código de barras) que tem a taxa, o TC, a duração, os canais e o código pedidos.
- **"Esperado" é hipótese** até a medição: nas fichas e no `verdade.json`, separar o que a receita pede
  do que um NLE de fato mostrou (`confirmado` / `inferido` / `hipótese`, com versão do NLE e data).
- O `gerar_taxas.py` do De Lá Pra Cá (`MIDIAS DE TESTES/3 CONJUNTOS DOS APPS/_DeLaPraCa/04 SINTETICOS/
  GERADORES`) **continua onde está**; o laboratório reaproveita o código de barras dele e o substitui aos poucos.
- Mover ou renomear esta pasta é com o zelador (sessão na raiz do SSD).

## ⛔ Freio de mão das bancadas (autor, 2026-10-11)

**F12** (a bancada nunca usa) ou o arquivo **`saida/PARAR`** param qualquer bancada que clique ou tecle
(`lab/bancadas/interface_win.py::checar_freio`, chamado em todo `_enviar`). O sinal (`Parado`) deriva de
`KeyboardInterrupt`: os laços que registram erro e seguem (`except Exception`) não o engolem. Toda automação nova de
mouse/teclado passa pelo `interface_win` — nunca um `SendInput` por fora.
