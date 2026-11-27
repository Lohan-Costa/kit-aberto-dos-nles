# Resolve 21.1.1 pela API: legenda SRT, legenda queimada, H.264 "Restrict to" e o crash do Python ao sair

- Programa e versão: DaVinci Resolve Studio 21.1.1.10 (API de script externa, Python 3.9.6 do sistema)
- Sistema: macOS 27.2.1, Apple Silicon (M2 Ultra)
- Confiança: `confirmado` nesta máquina para cada item marcado assim; o resto vem marcado como `inferido`
- Como reproduzir: os passos estão em cada item. Medido em material de trabalho real (um longa de ~107 min,
  timeline 1998×1080 24p começando em 01:00:00:00, três SRTs com ~1.200 a 1.400 legendas cada), **não** com mídia sintética do
  laboratório. A receita sintética ainda falta.

## O que se viu

### 1. SRT pela API cai no fim da timeline, e uma variação derrubou o Resolve (`confirmado`, uma ocorrência do crash)

- `MediaPool.ImportMedia([".srt"])` cria um item do tipo `Subtitle`.
- `MediaPool.AppendToTimeline([{"mediaPoolItem": srt}])` cria a trilha de legenda com todas as legendas, mas o bloco
  começa no **fim** do conteúdo da timeline, deslocado ainda pelo início do 1º evento do SRT.
- O mesmo append com `recordFrame` (e `trackIndex`) é ignorado e cai no mesmo lugar.
- Com `startFrame` + `endFrame` + `recordFrame`, o **Resolve fechou sozinho** ("quit unexpectedly").

**Contorno confirmado** (3 timelines, 3.885 legendas, zero diferenças de tempo contra os SRTs):

1. `CreateEmptyTimeline` e depois `SetStartTimecode`; ou `DuplicateTimeline` de uma timeline já estilizada, apagando todos os itens.
2. Append do SRT **primeiro**: ele cai no início da timeline + o 1º evento, ou seja, no lugar certo.
3. Depois vídeo e áudio com `recordFrame`, `startFrame`, `endFrame`, `trackIndex` e `mediaType` (1 vídeo, 2 áudio),
   que funcionam para clipes normais.

**Cuidado:** no `AppendToTimeline`, o `endFrame` é **exclusivo** (com `-1`, o clipe sai 1 quadro curto).

### 2. O estilo da trilha de legenda (`confirmado`)

- A API não lê nem escreve o estilo da trilha (fonte, tamanho, contorno, posição).
- `Project.DuplicateTimeline` leva o estilo junto: a timeline nova sai idêntica pixel a pixel numa legenda normal.
- Há preset, mas **só pela interface**. Com a trilha selecionada, o menu "…" do Inspector (canto de cima, aba Track) tem
  "Save Track as Preset…" e "Import Preset…". Cada preset salvo ganha um submenu com Load, Update, Export e Delete.
- O Export grava um arquivo `.preset` binário (208 bytes, cabeçalho de texto `PresetType: SubtitlePreset`).
- Pelo piloto, o "…" é um menu pop-up: no macOS precisou de controle de tela inteira, porque o clique em segundo plano é recusado.

### 3. `<i>` sem `<b>` no SRT perde o negrito da trilha (`confirmado`)

- Com a trilha em Arial **Bold**, a legenda marcada só com `<i>…</i>` sai em Arial **Italic de peso normal**, visivelmente mais fina.
  As legendas marcadas `<b>…</b>` saem em Bold.
- Com `<b><i>…</i></b>`, o itálico sai em Bold Italic, com o mesmo peso e tamanho das outras legendas (conferido por burn-in de quadro único).
- Contorno: uma cópia do SRT envolvendo em `<b>` toda legenda não vazia que ainda não esteja inteira em `<b>`
  (`negrito_srt.py`, nesta pasta). O SRT original fica intacto.

### 4. Legenda queimada no render (`confirmado`)

- `SetRenderSettings({"ExportSubtitle": True, "SubtitleFormat": "BurnIn"})` queima a legenda.
- Com `ExportSubtitle: False`, a mesma timeline sai limpa.
- Conferido num quadro de fala: as três versões legendadas diferem da limpa só na faixa da legenda (metade de cima com PSNR ~50 dB entre elas,
  e a faixa da legenda com ~22–28 dB).

### 5. H.264: `VideoQuality` numérico é "Restrict to" em Kb/s, um teto (`confirmado`)

- `SetRenderSettings({"VideoQuality": 10000})` aparece na interface como "Restrict to 10000 Kb/s".
- Sem multi-pass (encoder de hardware):
  - num trecho escuro de 60 s, a média deu **1,6 Mbps**;
  - no filme inteiro (~107 min, 1920×1080 24p), a média do vídeo deu **9,93 a 9,96 Mbps** em quatro renders.
  - O teto vale na média do filme, mas trecho escuro curto fica muito abaixo.
- Com `"MultiPassEncode": True`, o mesmo trecho de 60 s deu 10,0 Mbps, mas o render ficou bem mais lento (não medido no filme inteiro).
- Áudio AAC sem `AudioBitDepth`/bitrate definidos saiu a 320 kbps, 48 kHz (medido com ffprobe).
- Tempo sem multi-pass nesta máquina: ~45 min por arquivo de ~107 min (1080p, com ou sem legenda queimada).

### 6. A trilha de saída do áudio no render não é definida pela API (`confirmado`)

- Nenhuma chave de `SetRenderSettings` muda a "Output Track" do áudio (ex.: "Bus 1 (Stereo)" ou "All Timeline Tracks").
- Um job criado pela API herda a escolha **atual da interface** na página Deliver.
- Para um master com várias trilhas (2.0, M&E 2.0, 5.1, M&E 5.1), foi preciso escolher "All Timeline Tracks" na interface e dar "Update Job".
  Isso foi conferido com ffprobe: quatro trilhas no arquivo.

### 7. O script externo cai com SIGSEGV ao terminar (`confirmado`)

- O script faz todo o trabalho e, no fim do Python, morre com código 139. O macOS abre "Python quit unexpectedly".
- O relatório mostra `EXC_BAD_ACCESS` na thread `RemoteApp` de `fusionscript.so` (`Fusion::RemoteApp::FindLocalObject`),
  enquanto a thread principal roda os finalizadores (`__cxa_finalize_ranges`).
- Efeito: nenhum no Resolve nem no projeto, só o relatório de erro a cada execução.
- Contorno: terminar o script com `sys.stdout.flush(); os._exit(0)`. Todas as execuções seguintes (dezenas) saíram com 0, sem janela.

## O que se mediu (o número, o quadro)

- Tempos de cada legenda contra o SRT: 0 diferenças em 1.403 + 1.198 + 1.284 legendas.
- Quadros: os quatro renders H.264 com 154.466 quadros, igual à timeline; ProRes de referência com PSNR de 97 dB contra o master.
- Taxas, canais e quadros: ffprobe 9.0.2. Comparação de imagem: ffmpeg `psnr`.

## O que não se mediu

- Nada disso foi reproduzido com mídia sintética do laboratório; a receita ainda falta.
- O crash do item 1 aconteceu uma vez (não tentei repetir, para não perder trabalho).
- O "Load Preset" do item 2 numa timeline nova não foi testado.
- `legenda_na_timeline.py` é o esqueleto do contorno, reescrito sem nada do trabalho; nessa forma não foi executado.
  O `negrito_srt.py` é o mesmo que rodou, e foi testado de novo num SRT sintético.
- Windows e outras versões do Resolve (21.1.0, 21.2) não foram medidos.
- O item 7 com outro Python (3.11+ do Homebrew ou python.org) não foi testado.
