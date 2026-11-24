# Magic Mask do Fusion no DRT/DRP — o tracking NÃO viaja

> Medido no **DaVinci Resolve Studio 21.1.0.0014, macOS** (Mac mini, banco local), 2026-10-07.
> Clipe: `laboratorio-de-midia/saida/base/B10_ROTO/B10_ROTO_MOV-PRORES.mov` (1920×1080 25p, 300 quadros),
> máscara de verdade `B10_ROTO_MASCARA_MOV-PRORES.mov`. Projeto do autor "MAGIC MASC" (1 MagicMask no Fusion,
> modo Better, 4 traços positivos no quadro 80).
> Origem: uma produção relatou que o Magic Mask "se perdia" quando a timeline ia de uma equipe para outra.

## 1. O que a composição guarda (confirmado)

O nó `MagicMask` grava na composição só a RECEITA, não o resultado:

| campo | exemplo | viaja no DRT/DRP |
|---|---|---|
| traços (`MagicMask1Strokes` = `BezierSpline` com `MagicMaskStrokes { PosStrokes = {…} }` no quadro de referência) | 4 pontos normalizados 0–1 no quadro 80 | ✅ |
| `ReferenceTime`, `ProcessedFramesLow/High`, `Mode`, `UseLegacyMagicMask`, `AlgoVersion` | 80 / 0 / 299 / Better / 0 / 1 | ✅ |
| `CachePath` — **caminho ABSOLUTO** do cache na máquina que fez | `/Users/<usuário>/Movies/CacheClip/<banco>/<projeto>/<timeline?>/Fusion/MagicMaskCache/MagicMask1-<uuid>/0/Cache000000.raw` | só o TEXTO do caminho |
| a máscara calculada, quadro a quadro | a pasta do cache (5 subpastas; 602 arquivos, **95 MB** para 300 quadros) | ❌ |

Cache (`RAWI` no cabeçalho, 1920×1080): `0/` um arquivo por quadro (~66 KB), `1/` o quadro de referência,
`2/` um por quadro (~131 KB), `3/` e `4/` um `Cache.raw` de 3 MB cada (inferido: estado do modelo). Formato
`pendente`.

No DRT/DRP a composição mora no `Sm2TiCompositionTable.CompositionBA` do clipe: 4 bytes BE (tamanho aberto) +
zlib → bloco UTF-16 com `0_name`/`0_data`; o `0_data` é o texto `Composition { … Compressed = true, }` (layout,
`CurrentTime`, `Prefs.Comp.Paths.Map["ResolveCaches:"]`) + `\0` + uint32 LE (tamanho) + **zlib das ferramentas**
(onde estão o MagicMask, os traços e o `CachePath`). O FCPXML não leva nada do Fusion.

## 2. O que acontece do outro lado (confirmado, 3 reproduções, 1 delas só pela interface)

| teste | situação | resultado |
|---|---|---|
| T0 | projeto original, cache presente | IoU médio **0,988** contra a verdade |
| A | DRT importado num projeto novo, MESMA sessão, cache presente | lê o cache do projeto ORIGINAL pelo caminho absoluto → idêntico (0,988) |
| A2 | o mesmo projeto A FECHADO E REABERTO | ignora o cache original e **recalcula num cache próprio** (pasta do projeto A) |
| B / B2 / B3 | DRT importado com o cache original ausente (simula outra máquina) | recalcula sozinho do quadro de referência (80) **até o `CurrentTime` em que a composição foi salva (201)**, ~2 quadros/s, com a tela bloqueada — e depois **TRAVA o Resolve** (B por script com render, B2 por script com `SaveProject`, **B3 pelo autor, só importando pela tela**) |
| A2 render | render do projeto reaberto (cache refeito só 80–201) | o render completa o tracking (85 s contra 4 s), quadros **0–201 idênticos** ao original (o recálculo é determinístico), mas **205–278 SAEM SEM MÁSCARA** com a pessoa em cena → IoU 0,769 |

A trava: a linha principal fica em `Fusion::FusionApp::SyncProjectSettings → Fusion::RenderTask::ObtainRenderLock`
(`usleep` em laço), CPU ~6%, sem responder nem à API. Só sai forçando o encerramento.

**Conclusão (confirmado no 21.1 Mac):** quem recebe o DRT/DRP recebe os traços e um endereço que não existe na
máquina dele. O Resolve tenta refazer o tracking, o que é lento, pode travar a importação e entrega uma máscara
parcial no render. É o "o tracking se perde" que a produção relatou.

## 3. Como contornar (em teste)

- `hipotese` — **"Render Magic Mask in place as an external matte"** (novo no 21, página Color): vira um arquivo
  de matte, que viaja como mídia. Precisa de um Magic Mask na página Color para medir.
- `confirmado` (21.1 Mac) — **matte do clipe viaja no DRT/DRP**: anexado com `MediaStorage.AddClipMattesToMediaPool(item,[arquivo])`,
  ele vai no `MpFolder.xml` → `MatteVec` → `BtVideoInfo` com `<Type>MATTE_CLIP</Type>`; o `<Clip>` (0x81 + zstd) leva pasta,
  nome do arquivo, data e id — referência de mídia comum (religável). Importado num projeto novo, o clipe volta com o matte
  (`MediaPool.GetClipMatteList`). Teste "LAB MM - E" / "E2", com o render T0 (ProRes 4444 + alfa) como matte.
  ⇒ Caminho de troca: ASSAR a máscara em arquivo e mandar o arquivo junto com a mídia; o DRT liga sozinho.
  ⏳ Falta: medir o "Render Magic Mask in place" da página Color (inferido: grava esse mesmo matte do clipe) e usar o
  matte recebido como chave na página Color do outro lado.
- `hipotese` — renderizar o matte para arquivo (ProRes 4444 com alfa / EXR) e usá-lo como fonte do outro lado.
  O render T0 com `ExportAlpha` já é esse matte (IoU 0,988).
- `inferido` — copiar a pasta do cache junto só funciona se cair no MESMO caminho absoluto (mesmo usuário e
  mesmos ids de banco/projeto), e A2 mostra que nem o mesmo Mac reaproveita depois de reabrir: não serve.
- ⚠️ Mudar o `CurrentTime` pela API (`comp.CurrentTime = 80`) e salvar não ficou gravado (o DRT saiu com 0).

Scripts (scratchpad da sessão de 2026-10-07): medição `iou.py` (alfa do render × máscara do B10), abertura do
`CompositionBA` `comp_ba.py` + `inner.py`. Vale virar `laboratorio-de-midia/lab/bancadas/`.

## 4. Magic Mask da página COLOR e o "Render Magic Mask in place" (confirmado, 21.1 Mac, 2026-10-07)

Projeto do autor "magic mask na color" (mesmo clipe B10, nó "AI Magic Mask", traços no quadro 77).

**Antes do clique:** o cache fica em `~/Movies/CacheClip/<id do projeto>/AlgoCache/1000/<…>/1/` — `0/` 300 `.dvcc`
(598 MB), `256/` 299 `.dvcc` (42 MB), `StateBlob/{fw,bw}.dvcc` (6 MB), `KeyframeBlob/0000000077.dvcc` = **646 MB para
12 s**. O DRT não cita esse cache (só leva a correção no `LmVersion.Body`) → mesmo problema do Fusion.

**O clique "Render Magic Mask in place":**
- grava `~/DaVinci Resolve Media/<projeto>/Magic Mask/<clipe><sufixo>.mov` — ProRes 4444 (`ap4h`, yuva444p12le),
  máscara na luma E no alfa, 300 quadros, 16 MB (40× menor que o cache). ⚠️ Cabeçalho **24 fps e TC 00:00:00:00**
  com a fonte em 25p TC 01:00:00:00 — dentro do Resolve casou quadro a quadro (deslocamento 0); fora dele, cuidado.
- anexa o arquivo como **matte do clipe** (`GetClipMatteList`) e TROCA o nó: "AI Magic Mask" → **External Key**
  alimentado por um nó de matte com o nome do arquivo.
- IoU do matte contra a verdade: **0,988** (igual ao Magic Mask vivo), nenhum quadro perdido.

**A troca (outro projeto, outra "equipe"):**
| teste | situação | resultado |
|---|---|---|
| F | DRT importado num projeto novo, matte no lugar | External Key + matte chegam; a chave sai **idêntica ao matte (IoU 1,000)**, 0,980 contra a verdade (sem os pixels já escuros) |
| G | matte AUSENTE no caminho gravado | o render **FALHA com aviso** ("Full resolution media not found for …325AC.mov") — não sai errado calado |
| G2 | religado ao arquivo entregue em outra pasta (`DeleteClipMattes` + `AddClipMattesToMediaPool`) | render **idêntico** ao F (0 pixel diferente) |

**Protocolo para a troca entre equipes (Resolve → Resolve):** quem faz o Magic Mask clica em "Render Magic Mask in
place" ANTES de exportar; entrega o DRT/DRP **+ a pasta `Magic Mask/`** de `~/DaVinci Resolve Media/<projeto>/` junto
com a mídia; quem recebe importa e, se o matte ficar offline, religa. Não depende de cache nem de tracking.
⏳ Religar o MATTE pela interface (Relink do media pool) — não medido; Windows/Resolve 19 — pendente.

## 5. O CACHE POR DENTRO — leitura bruta (21.1 Mac, 2026-10-07)

Leitores: `laboratorio-de-midia/lab/bancadas/resolve_magic_mask/` (`dvcc.py`, `exrhdr.py`, `rawi.py`).

**É o mesmo modelo nas duas páginas** (estilo SAM: referência + memória + máscara grossa + máscara final); os arquivos
têm os mesmos tamanhos e os mesmos números de quadro, só a embalagem muda:

| papel | Fusion (`MagicMaskCache/…/N/`) | Color (`AlgoCache/1000/<id>/<id>/<id>/1/…`) | estado |
|---|---|---|---|
| máscara FINAL por quadro | `0/CacheNNNNNN.raw` (RAWI, ver abaixo) | `0/NNNNNNNNNN.dvcc` | Color `confirmado`; Fusion `parcial` |
| máscara GROSSA por quadro | `2/CacheNNNNNN.raw` | `256/NNNNNNNNNN.dvcc` | `confirmado` (Fusion) |
| quadro de referência (características) | `1/Cache<ref>.raw` (524 804 B, u32 quadro + halfs) | `KeyframeBlob/<ref>.dvcc` | `inferido` |
| memória do tracking | `3/Cache.raw`, `4/Cache.raw` (3 148 824 B, u32 quadro + halfs) | `StateBlob/fw.dvcc`, `bw.dvcc` | `inferido` |

**Máscara GROSSA** (`confirmado`): u32 LE = nº do quadro + **256×256 float16 LE** = logit (> 0 = objeto), esticado no
quadro inteiro (não quadrado), linhas de cima para baixo. A caixa bate com a verdade; ampliada por vizinho, IoU **0,938**
(299 quadros; o de referência não tem). Na Color o mesmo bloco vai dentro de um EXR "de mentira" de 32769×1 UINT.

**`.dvcc` (Color)** (`confirmado`): cabeçalho TLV (u32 1, u32 4, `DVCC`, depois etiquetas `d` = largura/altura u32,
`f`, `e`, `k`, `n` = timecode texto "00:00:00:00", `exr_zip`…), zeros até **8192**, etiqueta `g` (u32 tamanho), e a partir
do byte 8192 um **OpenEXR comum** (versão 2, scanline). Máscara final: EXR **960×540, um canal "A" UINT, ZIP** (blocos
de 16 linhas; bloco com tamanho = bruto vem sem compressão); os 2 073 600 bytes, lidos em ordem, são a máscara **1920×1080
de 8 bits, 0/255** (binária), linhas de cima para baixo. Os 300 quadros saem **idênticos** ao matte do "Render Magic Mask in
place" (IoU 1,000; 0,988 contra a verdade). `KeyframeBlob`/`StateBlob`: depois do `g`, array cru (sem EXR).

**`RAWI` (Fusion)** (`parcial`): cabeçalho de 1536 bytes — `RAWI`, u32 1207, 1015, **1536 (início dos dados)**, **tamanho
dos dados**, largura, altura, **passo 3840** (2 bytes/px, 1 canal half), tipo 2, janela de dados, região de definição
±1 000 000, aspecto 1.0 (double). Dados: **PackBits em palavras de 16 bits** (controle = byte baixo: < 0x80 copia c+1
palavras; ≥ 0x80 repete a próxima (c−127) vezes) — fecha exatamente 1920×1080 nos quadros testados. **Linhas de BAIXO para
cima.** Os valores são RESÍDUOS de um preditor ainda não identificado (esquerda-só acerta a borda esquerda e deriva; testados
cima, média, Paeth, MED, a+b−c, por byte). O Loader do Fusion abre o `.raw` como "RawFormat" mas NÃO o decodifica
(serve de nada como juiz). ⏳ achar o preditor.

### Para traduzir uma máscara do Premiere (.prmf) para o Resolve
- Escrever um `.dvcc` de máscara final é simples (TLV + EXR UINT ZIP de bytes 0/255) e o `.prmf` já vira máscara 1920×1080.
  ⏳ Não testado: se o Resolve USA um cache forjado sem refazer o tracking — o caminho tem ids (`<id>/<id>/<id>`) e há a
  memória/referência; e o A2 mostrou que o Resolve não reaproveita cache antigo ao reabrir.
- Caminho já provado: matte do clipe + External Key (§3–4).
- Caminho nativo: gerar TRAÇOS a partir da máscara do Premiere e deixar o Resolve fazer o Magic Mask (Fusion: `PosStrokes`
  normalizados no texto da composição, §1).

## 6. INJEÇÃO: o Resolve aceita um cache que ele não fez (confirmado, 21.1 Mac, 2026-10-07)

Projeto "LAB MM - I injecao": DRT de antes do "Render in place" (nó AI Magic Mask, página Color) importado num projeto
novo; `TimelineItem.RegenerateMagicMask()` com a página Color aberta fez o tracking (~4 q/s; o script estoura 60 s mas o
tracking segue). Cache em `~/Movies/CacheClip/<id do PROJETO>/AlgoCache/1000/<?>/<ID DO CLIPE NA TIMELINE
(TimelineItem.GetUniqueId)>/<?>/1/`.

Gravador `dvcc.escrever_dvcc(modelo, mascara_u8, destino)` (bancada `resolve_magic_mask/`): copia o cabeçalho DVCC e o do
EXR do modelo, grava os blocos SEM compressão (como o Resolve, apesar do "ZIP" no cabeçalho), atualiza a etiqueta `g`
(tamanho do EXR) e completa até múltiplo de **8192** → sai **byte a byte igual** ao do Resolve (4/4 quadros).

| teste | resultado |
|---|---|
| quadros 100–199 trocados pela máscara deslocada 400 px, render na MESMA sessão | o render segue a INJETADA (IoU 1,000); o resto, a original |
| projeto fechado e reaberto | o Resolve NÃO regrava o cache; o render continua com a injetada (IoU 1,000) |
| **os 300 quadros trocados pela máscara de OBJETO do PREMIERE** (`.prmf` → `prmf.alfa_quadro_inteiro`, limiar 128, as 2 passadas do autor: 7–57 e 50–278) | o render segue a do Premiere (IoU **0,999**, 231/300 quadros ≥ 0,999); contra a verdade **0,950** (= a máscara grossa do `.prmf`, 0,954) |

⇒ **Tradução Premiere → Resolve possível pela Color:** precisa de um nó AI Magic Mask já rastreado no destino (para existir o
caminho e as peças `256/`, `KeyframeBlob`, `StateBlob`); trocamos só a pasta `0/`. ⚠️ Se o colorista refizer o tracking ou
mexer nos traços, o Resolve sobrescreve. ⏳ Falta: criar o cache do ZERO (decifrar os 2 ids `<?>` do caminho e testar sem
`256/`/`StateBlob`), Windows/Resolve 19, e o Fusion (preditor do RAWI).
⚠️ Ambiente: o render de teste em ProRes 4444 (434 MB por 12 s) encheu o disco do Mac e saiu CORTADO com status
"Complete" (sem moov) — medir em ProRes 422 LT.

## 7. CACHE DO ZERO — receita completa (confirmado, 21.1 Mac, banco LOCAL em disco, 2026-10-08)

**O caminho** `~/Movies/CacheClip/<Project.GetUniqueId()>/AlgoCache/1000/<Sm2Sequence>/<Sm2TiItem>/<LmVersion ativa>/1/`
— confirmado em 2 projetos. `Sm2TiItem` = `TimelineItem.GetUniqueId()`; `Sm2Sequence` = coluna `Sequence` de `Sm2Timeline`
(≠ `Timeline.GetUniqueId()`); `LmVersion` = `pActive` de `ListMgt::LmVersionTable` com o `Sm2TiItem_id` do clipe. Os dois
últimos só no `Project.db` (SQLite): `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Resolve Project
Library/Resolve Projects/Users/guest/Projects/<projeto>/Project.db`. `1000` e `1`: `inferido` (tipo de algoritmo; nó?).

**Por que o Resolve recalculava** (Z, Z2, Z4b, Z5 — mesmo com o cache completo e as peças de outro projeto): o banco diz
se a máscara está "em dia". O tracking muda DUAS coisas no banco (diferença do banco inteiro antes × depois):
1. **`ListMgt::LmVersion.Body`** (0x81 + zstd + protobuf): APAGA os campos **12** (varint) em `1.7` (o nó), `1.12` e `3.12` —
   números de série de modificação ("mudou desde o último tracking"). O DRT exportado JÁ os traz e a importação os regrava.
   Tirar o 12 do Body importado dá o Body rastreado BYTE A BYTE. ⛔ Tirar o 12 DENTRO DO DRT faz a importação DESCARTAR o
   Magic Mask (o nó perde a ferramenta) → editar no banco, não no DRT.
2. **`Sm2TiItem.RenderCacheBA`** (u32 BE tamanho + zlib, 178 bytes) — o RECIBO: estrutura fixa com o id da LmVersion em
   ASCII (offset 0x24), a faixa (0x12c = 300 quadros, 0x12b = último) e dois u32 BE de série em **0x4c** e **0x96**
   (I: 0x0fca4160/…63; Z: 0x08871f1e/0x0ae7710d). Gravar com série alta (0x7ffffff0 / +3) basta.

**⚠️ zstd do Body:** um quadro com o TAMANHO do conteúdo e SEM soma de verificação (cabeçalho `28b52ffd 60…`), igual ao do
Resolve; o `zstd` lendo da entrada padrão grava `04…` (sem tamanho, com soma) e o Resolve NÃO lê o nó (ferramentas `None`,
sem efeito). `zst.comprimir()` usa arquivo + `--no-check`; recomprimir o Body original reproduz o cabeçalho do Resolve.

**Receita** (bancada `resolve_magic_mask/`): importar a timeline com o nó AI Magic Mask (DRT) → salvar → **trocar de projeto**
(o banco fica fechado) → `editar_banco.py` (tira o 12) → `recibo.py` (grava o `RenderCacheBA`) → `montar_cache.py` (só a
pasta `0/`, de `masks.npy`; peças opcionais) → abrir o projeto e renderizar.

| teste | o que tinha | resultado |
|---|---|---|
| Z | só `0/` | recalculou e sobrescreveu 272/300 |
| Z2 | `0/` + peças de outro projeto | recalculou |
| Z3 | DRT sem o 12 | importação descartou o Magic Mask |
| Z4 | banco sem o 12, zstd errado | nó ilegível, sem efeito |
| Z4b / Z5 | banco sem o 12 (zstd certo), sem recibo | recalculou no render |
| **Z6** | banco sem o 12 + **recibo** + `0/` + peças emprestadas | **aceitou**: render = máscara do Premiere (IoU 0,999), nada recalculado |
| **Z7** | banco sem o 12 + **recibo** + **só `0/`** | **aceitou** (0,999; 0,950 contra a verdade) |

⇒ **A máscara de objeto do Premiere vira Magic Mask da Color SEM o Resolve rastrear nada.** As peças `256/`, `KeyframeBlob`
e `StateBlob` não são lidas no render (só para refinar/continuar o tracking — `inferido`).
⚠️ Exige editar o `Project.db` com o projeto FECHADO (cópia de segurança antes); só banco LOCAL em disco (PostgreSQL / nuvem:
`pendente`). ⏳ Windows/Resolve 19; o Fusion (RAWI); o que acontece se o colorista mexer nos traços depois (esperado: recalcula).

## 8. A FERRAMENTA: `lab/prmf_para_resolve.py` (confirmado, 21.1 Mac, 2026-10-08)

`python3 -m lab.prmf_para_resolve "<projeto> Masks"/*.prmf --clipe "<clipe na timeline aberta>"` — com o Resolve aberto no
projeto (API externa, Python do sistema). Módulo `lab/resolve_mascara.py` (sem numpy; precisa do `zstd`), moldes em
`lab/moldes/resolve/`, testes `tests/test_resolve_mascara.py` (7/7, 0 pulados).

Passos: copia o nó AI Magic Mask de um molde (`ImportTimelineFromFile` do DRT do molde → `TimelineItem.CopyGrades` → apaga a
timeline e o clipe que o molde trouxe) → salva → abre um projeto TEMPORÁRIO → cópia do `Project.db` em
`~/Movies/prmf_para_resolve/copias/` → tira os campos 12 + grava o recibo → escreve os `.dvcc` (com taxa e TC no cabeçalho,
como o Resolve) → reabre o projeto e apaga o temporário.

| prova (projeto LABORATORIO/"PRMF PARA RESOLVE - B10", B10 25p) | resultado |
|---|---|
| tempo | **6 s** |
| render × máscara do Premiere | IoU **0,9987** (225/300 ≥ 0,999); × verdade 0,950 |
| correção de cor no nó DEPOIS (`SetCDL`) | NÃO faz o Resolve recalcular |
| salvar + trocar de projeto + reabrir + renderizar | idêntico (0 pixel diferente), cache intocado |

`CopyGrades` leva o nó AI Magic Mask entre clipes (confirmado). O DRT do molde reaproveita o clipe do pool quando a mídia é a
mesma (nada a apagar). ⏳ clipe aparado (o nº do quadro do cache conta da mídia ou do clipe?), outras resoluções do `.prmf`,
Windows/Resolve 19, banco em rede, traços do molde ≠ objeto (se rastrear de novo, o Resolve segue os traços do molde).

### 8.1 Clipe aparado (confirmado, 21.1 Mac, 2026-10-08)
- O próprio Resolve, rastreando um B10 aparado 50→298: grava `0/0000000050.dvcc … 0000000298.dvcc` — **quadros da MÍDIA, só a
  faixa do clipe**; `KeyframeBlob/0000000077` (a referência, em quadro da mídia); TC do cabeçalho do quadro 50 = `00:00:02:00`
  (da mídia), taxa 25,0.
- O RECIBO leva a faixa (u32 BE, quadros da mídia): **0x86 = primeiro, 0x8E = quantidade, 0xA6 = primeiro, 0xAE = último**
  (inteiro: 0/300/0/299; aparado: 50/249/50/298). `resolve_mascara.recibo(versao, primeiro, ultimo)`.
- A ferramenta num clipe aparado 100→298, com a referência dos traços do molde (77) FORA do clipe: render × Premiere
  IoU **0,999** (150/199 ≥ 0,999), × verdade 0,942; nada recalculado. Faixa = `GetSourceStartFrame()` …
  `+ GetDuration() − 1`. ⚠️ `GetNodeGraph().GetToolsInNode(1)` voltou `None` logo depois da ferramenta reabrir o projeto, com
  o efeito funcionando — não usar essa leitura como prova.

### 8.2 DRP e o cache da Color (confirmado, 21.1 Mac, 2026-10-08)
- O DRP exportado (`ExportProject`) LEVA, em texto, os ids do caminho: `Sm2Sequence` (MpFolder e SeqContainer), `Sm2TiItem` e a
  `LmVersion` (SeqContainer) — ao contrário do DRT.
- MAS o `ImportProject` gera ids NOVOS (o clipe `432a18d4…` virou `3024fc39…`) e o recibo sai VAZIO (`<RenderCacheBA/>`).
  ⇒ Nem pelo DRP o cache coletado cai no lugar sozinho, e o Resolve do outro lado não o reconhece: recalcula. Só a reinjeção
  (`lab/prmf_para_resolve.py` / `resolve_mascara`, que lê os ids NOVOS do banco de quem recebe) ou o matte (modo simples).
