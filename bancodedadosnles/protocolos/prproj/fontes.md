# PRPROJ — Fontes e rastreabilidade

| tema | app / arquivo de origem | amostra | confiança |
|---|---|---|---|
| Formato, grafo de objetos, ticks, ClassIDs, cadeia de referência, Sequence, posição, merged, áudio adaptativo — **Premiere Pro 2024/2025** | `DRAMASYNC/docs/reverse-engineering/premiere-multicam-prproj.md` | `midias-projetos-exemplo/projeto premier/PROJETO_MULTICAM_TEMPLATE.prproj` (Premiere 2024/2025) | inferido |
| **Regras de ESCRITA** — InUse, referência circular do merged, Link por tempo, entrada na bin, label colors, constantes de infra → [escrita.md](escrita.md) | `DRAMASYNC/src-python/prproj/builder.py` | mídia real: `MIDIA MULTCAM` (13 câmeras + WAV) e a diária `PRODUCAO-A/D02` (24 tomadas) | **confirmado** (Premiere 25.6.5, macOS) |
| Gerador de Multicam Source Sequence | `DRAMASYNC/src-python/prproj/` | — | **confirmado** — o arquivo gerado do zero abre no Premiere real |
| **Relink e geometria** — semântica do `Scale`, `DefaultMotion`, campos específicos de R3D, `InPoint` base 0, `AlternateStart` × 1001/1000 → [relink-e-geometria.md](relink-e-geometria.md) | `RELINK_PRODUCAO-G/relink_prproj.py` + `verificar.py` — **Premiere Pro 2026 (26.0.2, macOS)** | `PRODUCAO-G/.../docdelacordillera2_1_downgraded2_1_COR_Beta_1.prproj` (64 min, 7 sequências, 1.094 itens de vídeo) + acervo `BRUTO_PROXY_2026` (5.819 arquivos) | **confirmado** (medido; falta a conferência no Premiere aberto) |
| Layout do projeto multicam (bins, merged, multicam seq, edit seq) | `MULTCAM-PREMIERE/GUIDELINE.md` | `ARQUIVOS TESTE/PROJETO PREMIERE/multcam - tester.prproj` (Premiere 2025) | inferido → ver [projeto-multicam.md](projeto-multicam.md) |

## Notas

- O PRPROJ de referência foi criado **manualmente** no Premiere com 4 variantes (com/sem merged,
  com/sem gap) — base para diff entre estruturas.
- **Ler um template não basta.** As regras de [escrita.md](escrita.md) são exatamente as que um
  template *não* revela: só aparecem quando você gera o arquivo do zero e o Premiere se recusa a
  abri-lo (ou o abre defeituoso, em silêncio). Cada uma custou uma sessão de bisecção. Um app novo
  deve ler `escrita.md` **antes** de escrever a primeira linha do builder.

## Promoções de confiança

- **2026-07-11 → `confirmado`.** A geração de PRPROJ do zero passa a abrir no Premiere 25.6.5
  (macOS). Causa raiz do crash `AR::AudioPrefetch` identificada — referência circular no `SubClip`
  de vídeo do merged clip — e corrigida. Stress test com 13 câmeras + WAV: 217 `ObjectUID` únicos,
  28 entradas de bin, 16 Links, zero link de vídeo solo.
- **2026-07-12 → `confirmado`.** Sequência de uma diária real (24 tomadas, um som direto por tomada)
  aberta no Premiere pelo usuário: *"está perfeito, sync está no ponto certo"*. A precisão foi
  verificada por três caminhos independentes (correlação com PCM cru; os frames da claquete; o
  Premiere). Também validado `MZ.ZeroPoint` / fps / TC de projeto (start TC 01:00:00:00, 13 câmeras).
- **2026-07-18 (Órbita, ex-DRAMASYNC).** Multicanal adaptativo (>2 canais) decodificado da multicam
  NATIVA do Premiere (*Create Multi-Camera Source Sequence*, som de 5 canais) → [audio-adaptativo.md](audio-adaptativo.md):
  master `ChannelType=3` + 32 discretos, panner `StereoTo16ChannelPanProcessor` com matriz por PAR,
  tracks de ângulo de câmera não-targeted, padrão de targeting. O "canais 2..5 mudos" era ROTEAMENTO
  (resolvido). **Continua `pendente`:** a multicam GERADA é lida como "0 Channel" (nativa:
  "Multichannel") e fica muda como FONTE, mesmo reproduzindo tudo o que dá para comparar. Sequência
  NORMAL sincronizada (sem multicam) funciona — é o que o Órbita entrega no Alpha.

- **2026-09-03/04 (RELINK_PRODUCAO-G, Premiere Pro 26.0.2).** Primeira EDIÇÃO de um PRPROJ existente (até aqui o banco só
  cobria geração do zero). Confirmado por medida: `Motion > Scale` é relativo aos pixels nativos
  da fonte, então trocar a mídia por uma menor exige `scale × largura_antiga/largura_nova`;
  `<DefaultMotion>true</DefaultMotion>` é o Motion **ausente** (= 100% nativo) e precisa ser
  materializado; `InPoint`/`OutPoint` são relativos ao arquivo, então mexer em
  `Start`/`AlternateStart` não desloca corte. 662 itens reescritos com o produto
  `largura × scale/100` idêntico antes e depois — 0 divergências, 0 referências quebradas.
  **Validado 2026-09-03 no Premiere pelo usuário:** o projeto relinkado abre com a mídia online.
  O caminho até lá deu três achados que valem mais que o resultado: o container gzip com campo
  `FNAME` é recusado antes do XML; `<OfflineReason>` é o flag de offline (correlação 711/711); e
  o **oráculo** — um `Media` que o próprio montador relinkou pela UI dentro do projeto — desmentiu
  três hipóteses nossas sobre o que remover num R3D. **Pendente:** conferir o enquadramento no
  Program Monitor, em especial os 75 itens que estavam em `<DefaultMotion>true</DefaultMotion>`.

## A integrar

- **Bug "0 Channel" da multicam adaptativa** (`pendente`, prioridade alta): a multicam GERADA é lida
  como `"0 Channel mapped to N Mono"` (nativa: "Multichannel") e fica muda como FONTE/nest. Master/
  inlet/master-clip/matrizes/props já reproduzidos exatos. Próximo passo: diffar o
  `AudioSequenceSource`/`AudioStream`/`AudioSettings` da sequência-fonte. Ver a seção do bug em
  [audio-adaptativo.md](audio-adaptativo.md).
- Enum de `MZ.Sequence.VideoTimeDisplayFormat` para fps além de 23,976 (hoje fixo em `110`).
- Detalhe XML da sequência de **edição** (`EDIT`) que aninha a multicam — estrutura-alvo descrita
  em [projeto-multicam.md](projeto-multicam.md), falta o mapa de objetos (instâncias da multicam +
  cortes). Quando o DRAMASYNC/MULTCAM-PREMIERE gerar e validar, consolidar aqui.

- 2026-10-02 — `PRODB_FINALIZACAO.prproj` (Premiere 26.0.2), leitura para o relink proxy→ARRIRAW no Resolve: `ScaleToFramePolicy`, `PlaybackSpeed`, multicam de uma câmera como subclipe (relink-e-geometria.md §10).
- 2026-10-03 — `03 CASOS/DU exemplos especificos.prproj` (autor: recortes do PRODB para isolar
  casos) — máscara `AEMask2` (contorno, invertida), crop em take aninhado, Basic 3D (Swivel/Tilt 20
  para calibrar — aguarda export do Premiere). §10.5–10.6.
- 2026-10-03 — PRODB inteiro: levantamento das máscaras (3 usos, todos fixos) e Gaussian Blur com máscara calibrado pela imagem no Resolve 21.1 (relink-e-geometria.md §10.7).
- 2026-10-03 — caso `03 CASOS/REAL/R02 PRODB EXEMPLOS` (cópia organizada do projeto de casos do autor + export do Basic 3D 20/20): Basic 3D medido por homografia, traduzido por CornerPositioner (relink-e-geometria.md §10.8).
- 2026-10-04 — áudio do PRODB: canal por SecondaryContentItem, Level linear com 1,0 = +15 dB, campos escapados (audio-adaptativo.md).
- 2026-10-03 — keyframes do Level (formato, contagem no filme), PlaybackSpeed do áudio (só constantes) e caminhos com `..` no FilePath (audio-adaptativo.md), PRODB lido no Windows.
- 2026-10-04 — título do Premiere conferido pela imagem: corpo padrão 100 px, entrelinha 120%, corpo ≠ padrão no FlatBuffers do Source Text, Graphic Group em volta da própria âncora (relink-e-geometria.md §10.5).
- 2026-10-06 — acrescentar trilha de áudio num `.prproj` existente (escrita.md §11e), da memória do Claude do `BRINGBACKMIC` (2026-06-07, validado no Premiere pelo autor); e o `xmeml` v4 como mapa de cortes (projeto-multicam.md), do `FLATFILE-MULTCAM/src/multicam_rebuild/cutmap/`. Registrados pelo zelador do SSD ao arquivar os projetos.
- 2026-10-09 — relink com montagens (nest, adjustment layer, Transform, Motion, Crop) e a adjustment layer no arquivo (relink-e-geometria.md §6.2): laboratório B13_MONTAGENS no Premiere 23.2.0 Windows, `laboratorio-de-midia/lab/bancadas/premiere_montagens.py`, quadros pelo `exportFramePNG` e correlação após desfoque de 2 px.
- 2026-10-09 — caso real R04 (PRODUCAO-C): o raster da montagem não está no projeto; a regra "menor versão que enche" e a ambiguidade em Scale 100 (relink-e-geometria.md §6.2), medido no Premiere 23.2 Windows contra o vídeo de referência.
- 2026-10-10 — Lumetri: LUT embutida `ITX3` (formato, ordem R-G-B, vários blobs) e a intensidade misturada em gama (estruturas.md), medido pela imagem no Premiere 23.2 Windows, caso real R04.
- 2026-10-10 — Motion: "Scale"/"Scale Height" e o StartKeyframe × CurrentValue (estruturas.md), caso real R04, medido pela API do Premiere 23.2 e pela imagem.
- 2026-10-10 — Time Remapping do Premiere (formato, curva 6/7→8, PlaybackSpeed ignorada, keyframe de efeito no tempo da fonte) — estruturas.md; caso real R04, conferido pela imagem no Premiere 23.2 e no Resolve 19.
- 2026-10-10 — CORRIGE o Time Remapping (PlaybackSpeed CONTA; tipo 7 com influência = Bézier na velocidade) e o encaixe do in do clipe SOLTO pelo piso — estruturas.md; R04, cada quadro da referência exportada (ProRes do autor) casado com o quadro da MÍDIA original por correlação de bordas a 192×108 (ffmpeg n = quadro do Premiere, conferido num clipe de fração zero).
- 2026-10-10 — efeito desligado (`Bypass`) não existe na imagem — estruturas.md; R04, render do Premiere 23.2 pela ponte com só a V2 ligada (cópia do projeto ISOLADO), contra a mesma trilha isolada no Resolve 19.
- 2026-10-10 — máscara de opacidade AEMask (22/23, formato 2cin) e o exportFramePNG sem máscara (estruturas.md), caso real R04, conferido contra o vídeo de referência.
- 2026-10-22 — subida 23.6 → 26.5.2 do `WSP-DLPC.prproj` (PRODUCAO-C, Windows): versões, AEMask → AEMask2, pré-visualizações gravadas como `Media` + `PreviewMediaSerializer` (CORRIGE no mesmo dia: existem desde o 22.4 — vinham do render do autor, não da versão); o De Lá Pra Cá lê os dois igual (escrita.md §11b).
| 2026-11-20 | Lumetri: curvas RGB (eixo de vídeo, spline natural; a mestra preserva o matiz, R/G/B independentes) e Saturation (luminância linear); ProcAmp Saturation (Y' BT.601) — o CC do MC no Premiere | lab B24_COR_MC `resultados/B24_COR_MC/PREMIERE.md`, `lab/bancadas/premiere_cor_mc.py` | confirmado (Windows, 26.5.2) |
| 2026-11-20 | Premiere 2027 (27.0.0) oficial: formato Project 46/VideoStream 24; a página Color = árvore de CompoundComponent (classe 250b3605) com Color And Contrast/Color Shift/Color Texture/Unsharp Mask2, opaca para a API; a cor do MC (ProcAmp + Lumetri) idêntica ao 26.5 | lab B24_COR_MC (27.0.0 Windows), piloto na página Color, inventário API_PREMIERE/premiere-27.0.0-win32.json | confirmado (Windows) |
| 2026-11-20 | Página Color do 2027: o modelo exato do Color And Contrast (fonte do kernel em PTX\CL\ColorAndContrast.clz + Frida no cuMemcpyHtoD: os valores do host) | lab B24_COR_MC, `premiere_pagina_cor.color_and_contrast`, 29 casos | confirmado (Windows, 27.0.0) |
| 2026-11-20 | A máscara do 26.5/2027 é o mesmo AEMask2 do 26.0 (35 parâmetros: o refino da borda); a feather do retângulo é simétrica (10–90 % = 0,935 × Feather); o Gradient do Resolve = retângulo com aresta a 0,53·L e Feather 0,60·L (0,3 % de diferença média) | LAB MASCARA LUMETRI 26 (26.5.2 Win, máscara do autor) + `lab/bancadas/premiere_mascara_lumetri.py` (Premiere 27.0.0 Mac) × JANELAS_BORDA (Resolve 19.1.4) | confirmado (27.0.0 Mac) |
| 2026-11-21 | O Input Sizing do Resolve vira um Transform separado (Position normalizada = 0,5 + Pan/W, 0,5 − Tilt/H; Scale; Rotation; Flip por efeito), o encaixe no Motion: ≤ 0,15 px contra o Resolve, inclusive combinado e com fonte 4K | `lab/bancadas/premiere_sizing.py` (Premiere 27.0.0 Mac) × LAB COR SIZING (Resolve 21.1) | confirmado (27.0.0 Mac) |
