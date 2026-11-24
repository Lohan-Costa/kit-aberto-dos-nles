# Netflix — Studio Partner Help Center / Knowledge Hub (site público, lido em 2026-10-04)

Fonte: https://studiopartner.netflix.net/studio/ (versão em INGLÊS — mais completa; o site é um app em JavaScript:
só abre num navegador de verdade, lido pelo Chrome do autor). Substitui, para produção e pós, o antigo
`partnerhelp.netflixstudios.com` (este hoje só tem dublagem, legendas, entrega de arquivos e QC — 474 artigos).
Confiança: `documento` — e é GUIA (memória `manual-e-guia-nao-lei`): **o próprio site se contradiz** (abaixo).

## O mapa (o que existe e interessa à família de apps)
- **Branded Production & Post › Delivering to Netflix › Delivery Specifications & Requirements:**
  `editorial-cut-turnover-specification` ⭐, `spec-image-sound-mps`, `screenings-and-reviews`,
  `branded-titles-and-graphics-requirements`, IMF, DCP, M&E, áudio de arquivo, NAM.
- **› Delivery Best Practices:** `editorial-media-folder-structure-file-naming` ⭐, `textless-delivery-guidelines`,
  `prerelease-servicing-turnovers`, `archival-folder-file-naming`, nomes de projetos de cor.
- **› Imaging › Post & Color Workflows** (18): ACES no Resolve e no Baselight, AMF, enquadramento e resolução de
  trabalho (calculadora), framing charts, blow-up, dailies, acervo/found footage, relação de aspecto, títulos e
  gráficos, idents/logos, crédito Netflix, Dolby Vision, fotossensibilidade.
- **› Sound** (gravação, M&E, mix e entrega) · **› VFX & Virtual Production** · **Branded QC**.
- **Tools › Media Production Suite (MPS):** Footage Ingest, **Conform Pulls** ⭐, **VFX Pulls** ⭐, MPS Dailies,
  Media Downloader, Post Services.

## Editorial Cut Turnover (o corte que sobe ao Content Hub)
- **Lista de edição**, do mesmo corte do vídeo: **OpenTimelineIO (.otio) · Avid AAF · XML de Final Cut ou Premiere ·
  EDL CMX 3600**.
- **Vídeo com áudio embutido** (sem ele, falha de encode). H.264 (Closed GOP; sem cmov/elst; MP4 ou MOV; 10 Mb/s+ HD,
  25 Mb/s+ UHD; 8 bits) · **ProRes 422 HQ ou 4444 (não XQ)** em MOV, 10 bits · **DNxHD 36–440** em MOV.
  1920×1080 a 3840×2160, **lados múltiplos de 4** (preencher com preto), PAR 1:1, imagem ativa dentro do container
  (ex. 1920×800 para 2.4), BT.709/D65/BT.1886, 23,976 a 60 fps, **só progressivo, sem VFR**.
- **Áudio:** MP4/MOV com AAC (1 trilha, 5.1 ou 2.0 intercalado) ou MOV com LPCM 48 kHz 16/24 bits em 1, 2, 3, 7 ou 8
  trilhas — os mapas de canal de 5.1+2.0 estão na página (L R C LFE Ls Rs + Stereo L R).
- Changelog: 2024-06-13 (só progressivo; Rec.601 e xvYCC saíram).

## Mídia editorial para arquivo
- Caracteres legais nos nomes: `a-z A-Z 0-9 . _ -` (espaço e qualquer outro símbolo: ilegal).
- Manter a estrutura de pastas original (dailies/sistema editorial) e os MESMOS nomes do projeto (para religar depois);
  incluir o material que não é dailies (GoPro, stills, licenciado); sem zip; até 250.000 arquivos por upload.

## Conform Pulls (a Netflix busca o OCF na nuvem a partir da lista) — o vizinho mais próximo do De Lá Pra Cá
- **Entrada: só EDL File32 ou File129.** ⚠️ O FAQ diz que **CMX3600 NÃO**, e **AAF e XML NÃO** — o oposto da página
  de turnover editorial, que aceita CMX 3600, AAF, XML e OTIO (o primeiro é a lista do CORTE, o segundo a do PULL).
  OTIO e XML: "Q4 2025" (sem confirmação de que saiu).
- **Tirar efeitos e transições antes de exportar a EDL** ("não garantimos os quadros exatos" com efeito).
- Faz: transwrap e trim do OCF (RED, ARRI, Sony, ProRes…; formato que não corta = arquivo inteiro), **junta segmentos
  do mesmo clipe**, handles IGUAIS para todos (por plano: não), nome por **cor de locator** (black, blue, cyan, green,
  magenta, orange, pink, purple), pela coluna Name da EDL ou pelo nome do OCF, filtro por locator.
- Controle de qualidade: avisa plano que não conforma; deixa corrigir Tape e TC e tentar de novo; **casamento "fuzzy"
  do campo Tape**; avisa **"multimatch"** (vários arquivos para o mesmo evento) e nome de saída repetido; avisa IDT
  faltando. **"Perceptual conform" (pela imagem): TBD** — não existe.
- Recomendação: quem submete é o ASSISTENTE DE MONTAGEM (é a ele que voltam as dúvidas da EDL).

## VFX Pulls
- Entrada: **EDL ou CSV** (ShotGrid, XML e OTIO: não). Saída: EXR ACES 2065-1 (AP0) e referência ProRes/H.264
  Rec.709 em MOV (sem DNx, sem MXF, **sem burn-in**). Configurável: compressão, handles, start frame, nome por plano,
  enquadramento (FDL), cor por plano (AMF; CDL embutido na EDL também vale; ALE não).

## Títulos e gráficos (requisitos)
- Canvas de pelo menos UHD (3840 de largura) no aspecto final; EXR 16 bits (sem LOG) ou TIFF 16 bits; DPX só tela
  cheia; ProRes 4444 só em não ficção/animação. Title safe 90%, action safe 93% (SMPTE). Entregar projeto, versões
  textless e um "toolkit" (fundos limpos, camada de fonte editável, lista de plugins e de fontes).

## Varredura completa (2026-10-04, pela API pública — ver `../netflix-site-mapa.md`)
O site inteiro foi lido pela API que o próprio app usa (`/api/v2/subsites/studio/page/<slug>`, JSON do
Contentful, inglês, sem login). Texto de cada página em `MANUAIS ENTREGA/PUBLICOS/NETFLIX (site)/paginas/`.
O que a varredura acrescentou ao que já estava acima:

### TC de início: a Netflix é "hora zero"
- **Servicing Turnover** (ProRes 422 HQ SDR, textless, 4444 XQ Dolby Vision, H.264): `START TIMECODE 00:00:00:00`,
  NDF, sem barras/claquete/2-pop, **1 s de preto e silêncio na cabeça e na cauda**. Áudio 8 trilhas
  (5.1 L R C LFE Ls Rs + Stereo L R), 48 kHz/24 bits; o textless leva D/M/E 2.0 em 6 trilhas.
- Legenda (QC automático `TimedText-MaximumOffset`): erro típico é TC "hora 1" (01:00:00:00) em vez de hora 0.
- DCP: o `StartTime` do Timed Text é 00:00:00:00 em todo rolo (sem deslocamento por hora de rolo).
- Exceção: gravação de diálogo de animação começa a sessão em 00:59:50:00, nada gravado antes de 01:00:00:00.
- ⚠️ Isso contrasta com as casas brasileiras e o broadcast (01:00:00:00 / 10:00:00:00 — `../matriz.md` §9.1):
  reforça a decisão do autor de **respeitar o TC da origem** e não impor um valor.

### Dailies MPS (o que o assistente de montagem recebe)
- Avid: MXF OP-Atom DNxHD/DNxHR + **.avb gerados pelo sistema** + ALE + relatório de laboratório (sem .pmr/.mdb:
  o Avid os cria no scan). Premiere/outros: MOV ProRes + ALE (sem bins).
- Nome do ARQUIVO só em 3 formas (nome do OCF; `_Cena-Take`; `_Cena-Slate-Take`); a coluna Name é configurável.
- Burn-in: TC de vídeo e de som, rolo, nome do arquivo; **nunca cena/take** (são corrigíveis; queimar é permanente).
- Enquadramento só por **ASC-FDL** (por formato de câmera ou por plano); um único punch-in por vez.
- Falta de insumo (AMF, FDL, som): o projeto escolhe "segurar o dia", "entregar o que está certo" ou "entregar
  tudo com aviso" — o mesmo dilema da nossa trava de prontidão, resolvido como OPÇÃO do projeto.

### Conform Pulls (detalhe — `conform-pulls-user-guide`, `-faq`, `-feature-support`, `-settings`)
- **Tapename + TC da EDL = nome COMPLETO do clipe de câmera, sem extensão nem numeração de quadro.**
- **Achatar em UMA trilha** (ou uma EDL por trilha); tirar dissolve, wipe, retime e filtro temporal. Se o master
  precisa da transição, ESTICAR o clipe no corte para que os quadros extras já estejam no in/out de origem da EDL.
- Exportar a EDL: **Avid List Tool** — só "Color Decision List" e "Clip Names"; **Premiere** — só "Optimize EDL",
  "Color Decision List", "Clip Names" e "Source File Name". O resto desmarcado.
- Mais de uma taxa no projeto: falar com a Netflix (não há regra automática).
- O sistema limpa caracteres ilegais e pode descartar eventos que não são vídeo (slug etc.).
- Settings: handles iguais cabeça/cauda; nome de saída = **Source FileName** (o recomendado para conform);
  **Merge Segments** junta usos do mesmo arquivo se a distância for ≤ 10 min; filtro por locator.
- Pacote baixado: pasta com o nome da EDL; `Attached_Files/` com a EDL original + CSV evento a evento; uma pasta
  por formato de câmera.
- Feature support (tabela do site, com previsões "Q4 2025" que podem já ter vencido): XML, CSV e iniciar do NLE —
  não; OTIO — Q4 2025; handles por plano — não; enquadramento/normalização por FDL — Q4 2025.

### VFX Pulls (detalhe)
- Entrada EDL ou CSV; **CDL embutido na EDL é aceito** sem AMF; ALE não. ShotGrid/XML/OTIO: não.
- Taxa: o projeto tem uma taxa só; clipe em outra taxa exige **new master** (mezzanine) na taxa do projeto ou
  render na taxa de origem — senão o TC do material de montagem não bate com o OCF e o pull erra os quadros.
  Recomendam **loop test** (ida e volta com a finalização) a cada formato de câmera novo.
- Saída sempre ACES 2065-1 EXR; referência ProRes/H.264 MOV Rec.709, sem burn-in; filtro de resize Adaptive
  (FilmLight); estrutura de pastas fixa.

### Textless (o que sai e o que fica no master sem texto)
- Sai e vira insert textless: créditos iniciais e texto sobre imagem, créditos finais sobre cor/animação, título
  principal, carimbos de tempo/lugar, lower thirds (com o grafismo junto), infográficos, texto animado sobre imagem.
- Fica: créditos finais sobre preto/branco 100%, logos de produtora, texto dentro de comp de VFX/animação, texto
  diegético, marcas na cena, grafismo de tela cheia.

### Som (mix e entrega)
- Near field: **−27 LKFS ±2 LU dialog-gated (BS.1770-1)**, true peak −2 dBTP; abaixo de 15 % de diálogo, mede o
  programa inteiro (−24 LKFS). LRA de diálogo ≤ 10 LU. Lo/Ro preferido. Stems D/M/E que somam o mix.
- Teatral: 85 dB SPL, sem exigência de LKFS, pico 0 dBTP — e é um segundo conjunto completo de entregas.
- Áudio na taxa nativa do projeto; sessão Pro Tools ou, de outro DAW, AAF/OMF junto.

## Para os apps (ver `../lacunas.md`)
- TC: o site confirma que "o certo" depende do destino (Netflix hora 0; broadcast hora 1 ou 10) — opção, não regra.
- Nome de arquivo do dailies Netflix = nome do OCF (+ cena/take): o casamento por nome do relink cobre.
- A Netflix aceita **OTIO, AAF, XML e EDL** como lista do corte, mas os PULLS automáticos só leem **EDL File32/129
  limpa** (ou CSV): um app que gere EDL File32/129 sem efeitos + CSV de VFX a partir da timeline encaixa direto.
- O conform deles não confere pela IMAGEM nem resolve efeito: a conferência pela imagem do De Lá Pra Cá e a tradução
  de efeitos são justamente o que falta lá.
