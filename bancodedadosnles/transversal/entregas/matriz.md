# Matriz de exigências de entrega — quem pede o quê (2026-10-04)

> ⚠️ **Manual é GUIA, não lei** (autor, 2026-10-04): pode estar errado, impreciso ou desatualizado; serve para
> direcionar a entrega e a conversa com a casa, e é maleável. Nada daqui vira requisito duro de app: no máximo
> opção, preset ou aviso que a pessoa ajusta — e sempre se combina com a casa da vez.

Consolidado das fichas (`fichas/`), lidas texto E prints. Siglas: **QC** CASA-POS-1 conform v1.5 · **QN** CASA-POS-1/Netflix
v8 · **CJ** casa-pos-2 · **TE** CASA-POS-3 · **NX** Netflix Pix v12 + Locked Cut · **NP** Netflix NPC SDR v1.0 ·
**DB** CASA-POS-4 (som) · **19** 1927 Audio (som) · **12** −12dB (som) · **NS** Netflix Studio Partner (site, 2026-10-04). Confiança: `documento` — é o que cada casa
PEDE, não engenharia reversa. ⚠️ = os fornecedores DIVERGEM (o projeto decide com a casa da vez).

## 1. A timeline que vai para a COR / CONFORM

| Exigência | Quem | Observação |
|---|---|---|
| Timeline limpa: sem mídia não usada, nada offline | QC QN | |
| Sem áudio na timeline de conform (ou só o da referência/uma mix) | QC QN CJ TE | QC aceita o som da referência |
| **Desfazer compound/nest e achatar multicam** | QC QN TE | ⚠️ o De Lá Pra Cá traduz o nest em compound POR PADRÃO (decisão do autor, caixa no painel); para estas casas, desmarcar |
| Sem subclips; sem efeito em filler, em trilha ou em "layer"; sem plugin/efeito avançado | TE CJ QN | |
| Zoom/crop/posição NO clipe, nunca em camada de ajuste | QC QN | |
| Remover cortes falsos (through edit) | QC QN | |
| **Trilhas por FUNÇÃO** | CJ TE QN QC | ⚠️ os nomes e a ordem variam: CJ `BASE·CONFORM·RETIME·MOTION·ÚTEIS`; TE `BASE·CONFORM·RETIME·PLATE·COMPOSITING·MOTION·ÚTEIS`; QN `OCF·RESIZE/RETIME·TO VFX·ARC·VFX`; QC `OCF·ARQUIVO·STILLS·ARTES` |
| Artes, letreiros, material de arquivo nas trilhas de cima | QC QN | |
| **Markers spanned (IN–OUT, o plano inteiro)** em resize (também animado), flip, crop, retime/Time Warp (com %), compositing, motion | CJ TE | QC: só os pertinentes ao colorista + estabilização, reenquadro, scale, cor feita na montagem; QN: só os do online (rampas, transições) |
| **Lista de markers em TXT e PDF** (Avid: Export Markers › Text; Print Markers) | CJ TE | colunas FRAMES, COMMENTS, TC IN, TC OUT, # |
| AAF/XML com Reel/Tape Name, Source TC, Source File Name, scale/position | QN | |
| Lista do corte em OTIO, AAF, XML (FCP/Premiere) ou EDL CMX 3600 | NS | ⚠️ o Conform Pull da mesma Netflix só lê EDL **File32/File129** (CMX3600, AAF e XML não) e pede a timeline SEM efeitos e transições |
| Nomes só com `a-z A-Z 0-9 . _ -`; estrutura de pastas e nomes originais na mídia de arquivo | NS | |
| **AAF do Avid para conform:** AAF Edit Protocol, Use Marks, Use Selected Tracks, só vídeo, Link to (Don't Export) Media, Render Video Effects | CJ TE | mesma janela nas duas casas |
| DRT (Resolve 17+) ou DRP | QN QC | QC pede Resolve ≤ 20.2.2 — ⛔ o autor manda ignorar versão de casa |
| ALE com metadados de câmera e LUT (só na coluna LUT USED); CDL em EDL | QN | |
| LMT: CDL no node 1, LUT no node 2, batendo com a referência | QC | |

## 2. Projeto, Media Management e cor (Resolve)

| Exigência | Quem | Observação |
|---|---|---|
| Media Management "Used media and trim keeping 10 frame handles", COPIAR, preservar hierarquia, Relink to new files; DRP relinkado à mídia consolidada | QC | |
| Master: resolução do maior delivery, taxa da montagem, PAR quadrado, sem drop/interlace | QC | |
| ACEScct · ACES 1.3 · ODT Rec.709 BT.1886 (resto dos campos na ficha) | QC | |
| Série: um DRP por episódio; longa: rolos de 25–45 min, Rolo 00 para vinhetas | QC QN | ⛔ divisão por rolos = pessoa (autor) |

## 3. TC, cabeça e bipes ⚠️ (o ponto de maior divergência)

| Esquema | Quem |
|---|---|
| Longa: **01:00:00:00** início · **bipe 01:00:06:00** (1 quadro) · **1º quadro 01:00:08:00** · bipe 2 s depois do último quadro | QC QN DB 19 |
| Rolo N: o mesmo esquema na hora N (R00 00:00:00:00, R01 01:…) | QC 19 |
| Rolo N: o **1º quadro de imagem** em N:00:00:00 (sem cabeça de 8 s) | CJ |
| **FFOA 01:00:00:00**, countdown e **bipe em 00:59:58:00** | 12 NX (2-pop) |
| Série Netflix: 00:00:00:00, programa em 00:00:01:00, 1 s de black/silêncio no fim | QN |
| Cortes no Pix: claquete 00:59:50:00, black 00:59:55:00, 2-pop 00:59:58:00, programa 01:00:01:00 | NX |
| NPC: 1 s black · pré-roll 1 min · 1 s · ident · 1 s · programa · 1 s | NP |
| Cartela de cabeça (01:00:00:00–01:00:05:00) com projeto, versão, data, duração, FPS, codec | DB (NX: a claquete) |

O app **respeita o TC que veio da origem** (regra do autor, 2026-10-04) e não monta cabeça nem bipes: a
estrutura de rolos é de pessoa. A matriz serve para o editor saber o que a casa da vez espera.

## 4. Vídeo de referência

| Exigência | Quem | Observação |
|---|---|---|
| Codec | QC QN: H.264, DNxHD ou ProRes Proxy · CJ TE: ProRes Proxy · DB: ProRes Proxy (DNxHD), **nunca H.264**, ≤ 1920×1080 · 19: ProRes Proxy > 10 Mbit/s · 12: ProRes Proxy com som · NX: H.264 ≤ 10 Mb/s, ≤ 6 GB · NP: ProRes 422 HQ | ⚠️ cor aceita H.264; som recusa |
| Mesmo TC e mesma taxa da timeline | QC QN | |
| Corte no Content Hub: H.264, ProRes 422 HQ/4444 (não XQ) ou DNxHD; lados múltiplos de 4; só progressivo, sem VFR; áudio embutido | NS | |
| Janela da entrega (ou tarjas) | QC QN | CJ: **sem** letterbox |
| Burn-in **Source File/Clip Name, Source TC, Rec TC, diária** | QC QN CJ TE | + Reel (QN), lente/LUT (QC QN), VFX shot, retime/scale, transições (QN) |
| Burn-in para som: projeto/ep/corte/data, ADR + fala, cena/plano/take, canais do áudio | 19 (12: sequência/take) | |
| TC aparente no topo direito | NX 12 | NP: **sem** TC nem marca d'água |
| Cópia da timeline LIMPA do AAF, sem multicam | CJ TE | |
| Nome com data AAAAMMDD; nunca "Versão Final" | DB NX NP | NX/NP têm convenção própria de nome |

## 5. Som (AAF, EDL, stems)

| Exigência | Quem | Observação |
|---|---|---|
| AAF **embedded** | DB | ⚠️ |
| AAF **não embedded** + pasta de áudio | 19 12 | ⚠️ (12 testa os dois no teste de workflow) |
| Handles | DB **150 quadros** · 19 **≥ 10 s** · 12 **5 s** | ⚠️ |
| WAV/BWF 48 kHz 24 bits; breakout to mono; trim | DB 19 12 | DB: a janela de AAF do Premiere inteira na ficha |
| **Manter fades, crossfades e keyframes de volume** | 12 | |
| Pistas por conteúdo (som direto · efeitos · música · VO/ADR), sem misturar | DB 19 | 19: canais 1–8 SD · 9–10 ADR/VO · 11–14 efeitos · 15–16 música |
| Todos os microfones do som direto conformados | 19 | |
| **EDL de vídeo** (CLIP NAME, FILE32/FILE129) | DB 19 12 | |
| **EDL de som e de diálogo** por rolo, com Sound Roll e File Name, na taxa do projeto, **sem bipes** | 12 (19: EDL de áudio com o source = pasta da diária) | |
| Stems/DME 2.0 (diálogo, música, efeitos) | NX (temporários) · 19 (por rolo) | |
| Loudness −27 LKFS ±2 LU, pico ≤ −2 dBTP | NP | |
| Som direto bruto + boletins + roteiro | DB 19 12 | |

## 6. VFX

| Exigência | Quem |
|---|---|
| Timeline SÓ de VFX (DRT ou AAF), mesmo TC e bipes da montagem | QC QN |
| VFX Pulls da Netflix: entrada EDL ou CSV (XML/OTIO não); saída EXR ACES AP0 | NS |
| Planilha/CSV: QC `EP/Rolo · TC Start · Seq # · Seq Name · Shot # (4 dígitos) · Nuke Proj Name · Descrição`; QN `VFX SHOT NAME · SOURCE NAME · RTC IN/OUT · STC IN/OUT` | QC QN |

## 7. Mudança de corte (reconform)

| Exigência | Quem |
|---|---|
| Referência NOVA e inteira + timeline/AAF só com o que mudou, mesmo start TC | QC CJ TE DB |
| Deslocamento da timeline inteira: só indicar os pontos | CJ TE |
| Som: AAF novo do som direto só com o material novo, nas mesmas referências de TC/cabeça/bipe; AAF de efeitos/música se entrou qualquer coisa | DB |
| Mov SONORIZADO como referência para reconform | 19 |
| Change List (locked cut → IMF) até 48 h antes | NX |

## 8. Material de arquivo, nomes, taxa

| Exigência | Quem |
|---|---|
| Sem espaços nem caracteres especiais; nunca renomear depois de entrar na timeline | QC QN |
| Estrutura de pastas da câmera e TC do original preservados; TC diferente = AAF novo | QC QN |
| A MESMA taxa do começo ao fim (definida com a finalização antes da pós de som) | DB 19 QC |
| Legenda: SRT UTF-8 com BOM (fonte, estilo, posição); DCP: XML SMPTE 428-7 | QN |

## 9. Fontes PÚBLICAS (2026-10-04): masters de TV, distribuição, som, conform e preservação

Siglas: **TA** estudio-o · **PW** ESTUDIO-N · **CB** Cinemateca (Portaria MinC 221/2025) · **EB** EBC NOR 704 · **CA**
CBC/Radio-Canada · **SV** SVT · **RT** RTÉ · **C4** Channel 4/DPP AS-11 · **AM** Amazon Prime Video · **AP** Apple TV
Channels · **DI** Discovery · **RM** EMPRESA-P (DCP) · **R128** EBU R 128 · **PB** PBS (TOS) · **PD** PBS Distribution ·
**PA** Paramount ANZ/Network 10 · **UK** UKTV · **TP** Telepacífico · **NS** site Netflix (varredura completa, 2026-10-04).

### 9.1 Onde começa o PROGRAMA (TC) ⚠️ — o mapa que o "TC de início" precisa respeitar

| Programa em | Cabeça antes | Quem |
|---|---|---|
| **00:00:00:00** | — (TC do programa começa no zero; legenda com offset −01:00:00:00 se o master vier em 01:00) | AP |
| **00:00:00:00** | 1 s de preto e silêncio (servicing turnover, NDF, sem barras/claquete/pop); legenda em hora 0 (erro de QC se vier em hora 1) | NS |
| **00:00:00:00** | claquete; conferir no MediaInfo que o TC exportado saiu em zero | TP |
| **01:00:00:00** | só 2 s de preto (00:59:58:00); ≥ 5 s de preto entre partes, ≥ 30 s no fim | PA |
| **01:00:00;00** DF | 00:59:45;00 preto/claquete ≥ 15 s + 2 s de preto | PB |
| **01:00:00;00 ou 10:00:00;00** | claquete 13 s em 00:59:45;00 + 2 s de preto; sem barras | PD |
| **01:00:00:00** | barras 00:59:38 · claquete 00:59:48 · black 00:59:58 | EB |
| **01:00:00:00** | nenhuma (TV: sem leader, barras nem black) | TA (TV) |
| **01:00:08:00** (FFOA) | leader de 01:00:00:00, pop 01:00:06:00 | TA (cinema) DB 19 QC QN |
| **10:00:00:00** | tons 09:59:30 · ID vocal 09:59:35 · sync 09:59:58:00 | CA |
| **10:00:00:00** | barras 09:58:00 (90 s) · relógio 09:59:30 · plop 09:59:57:06 | RT |
| **10:00:00:00** | barras 09:59:30 · relógio/slate 09:59:50 · tom+branco 09:59:57:06 · partes em arquivos = próxima hora | C4 |
| rolo N em N:00:00:00 | 2-pop 2 s antes (cinema/DCP) | RM CJ TA PW |
| só o programa (sem barras, slate, textless) | — | AM |

### 9.2 Outras exigências que as fichas trazem

| Exigência | Quem |
|---|---|
| EDL **File32/File16/red16** (CMX3600 corta o nome da fonte em 8 caracteres), sem efeitos, uma por trilha ou achatada | PW TA (File_32 ou CMX3600) |
| EDLs por GRUPO lógico (câmera, GoPro, VFX temp, títulos) + documento de "online notes" (CSV/PDF/XLSX) com cada efeito a refazer | PW |
| 3 AAFs de som separados (DX, FX, MX), embedded, handles 2 s, automação de keyframes | TA |
| AAF de som em link (nem embedded nem consolidado), DX 1–8 · FX 9–16 · MX 17–24, + AAF de sync com o áudio real | PW |
| Rolos ≤ 21 min, nome `SIGLA R3v5` (só rolos revistos sobem de versão; cor não conta) | TA |
| Loudness −23 LUFS (R 128; −1 dBTP falha no C4) · −24 LKFS (CA PB PD PA) · −27 LKFS dialog-gated (NP NS) · picos −20 a −10 dBFS (TP) | R128 C4 SV CA NP NS PB PD PA TP |
| EDL do Conform Pull: Tapename = nome completo do clipe sem extensão; achatada em 1 trilha; sem efeitos; Avid List Tool só CDL + Clip Names; Premiere só Optimize EDL + CDL + Clip Names + Source File Name | NS |
| Barras + tom + relógio OBRIGATÓRIOS na cabeça (UK) × PROIBIDOS (AM PD) | UK × AM PD |
| Textless: aberturas/créditos com texto DEPOIS do programa textless, 2 s de preto entre | PD (e NS: lista do que sai/fica) |
| Material não-HD ≤ 25 % da duração | UK |
| TV brasileira: XDCAM HD422 1080i 59,94 DF, Libras, CC EIA-708, audiodescrição | EB |
| TV europeia: 1080i/25 ou 1080p/25, AS-11 (AVC-Intra 100, MXF OP1a) | C4 SV |
| Legenda em língua estrangeira NÃO queimada | SV NX (IMF) CB |
| Mezanino: taxa nativa, sem telecine, sem VFR; HDR sempre com SDR de mesma conformação | AM |
| Recorte de área inativa por METADADO (crop), não na imagem | AP |
| Preservação: sequência TIFF/EXR/DPX + WAV (ou MKV/FFV1) sem compressão, legendas à parte, LTO-9; DCP sem KDM | CB |
| DCP: DSM DPX/TIFF/ProRes 4444, 24 fps, sem letterbox, 2-pop, BWAV por canal | RM |
