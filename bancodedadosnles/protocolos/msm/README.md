# MSM — bancos de mídia do Avid (.mdb, .pmr) e AMA Management

Os arquivos que o Media Composer usa para **localizar e relinkar** essência: os bancos do MSM
(Media Stream Manager) dentro de cada pasta `Avid MediaFiles/MXF/<n>/`, e o AMA Management
(para mídia *linkada* fora do MediaFiles). Aqui está o lado "onde está o arquivo"; o lado
"o que tem na timeline" é o [../avb/](../avb/README.md) (bin) e o [../aaf/](../aaf/README.md).

## As três peças

| arquivo | papel | contêiner | confiança |
|---|---|---|---|
| `msmMMOB.mdb` | banco de **objetos de mídia** (metadados completos por clip) | **Bento/OMFI** | leitura **confirmada e validada** (nome do clip + MobID + path AMA), via `tools/mdb_read.py` |
| `msmFMID.pmr` | índice **File Media ID**: arquivo ⇄ MobID ⇄ tape ⇄ timestamp | binário próprio (registros) | inferido |
| `Managed AMA Media Folders.xml` + `AMA Metadata Folders/` | mapa de pastas AMA-linkadas → metadados | XML + pastas com `.aaf` e `amaFMID.pmr` | confirmado |

## Como o MC resolve uma mídia (visão de conjunto)

```
bin (.avb) / AAF  →  SourceMob com MobID + MSMLocator
        │
        ▼  (procura nas pastas Avid MediaFiles/MXF/<n>/)
   msmMMOB.mdb  (metadados do clip)  +  msmFMID.pmr  (MobID → nome do .mxf)
        │
        ▼
   arquivo .mxf físico (Op-Atom) na mesma pasta
```

Para **mídia AMA** (linkada, não copiada para o MediaFiles) o caminho é outro: o MC guarda, por
pasta de mídia externa, uma *AMA Metadata Folder* contendo **um `.aaf` por arquivo** (o descriptor
do AMA-link — formato que já dominamos com pyaaf2, ver [../aaf/escrita.md](../aaf/escrita.md) §AMA)
e um `amaFMID.pmr`. O `Managed AMA Media Folders.xml` lista os pares
`media_pathname → metadata_pathname`.

## Mapa das peças (índice deste protocolo)

| arquivo | conteúdo |
|---|---|
| [mdb-bento.md](mdb-bento.md) | `.mdb` é container Bento/OMFI; label, TOC, valor, dicionário, MobID (32 e 12 bytes), colunas de bin e cadeia de origem |
| [dados/bento-toc.json](dados/bento-toc.json) | estrutura do registro TOC, flags de valor, dicionário e conversão de MobID |
| [dados/mdb-clip-fields.json](dados/mdb-clip-fields.json) | colunas de bin (Name/Start/Duration/Tape/Video), cadeia de origem OMFI, descritores |
| [pmr-fmid.md](pmr-fmid.md) | layout dos registros do `.pmr` (longo/curto, MobID, tape, timestamp) |
| [ama-management.md](ama-management.md) | XML, AMA Metadata Folders, o `.aaf` por mídia, e como a casa contorna hoje |
| [dados/bento-label.json](dados/bento-label.json) | label Bento de 24 bytes (offset/tamanho da TOC) |
| [dados/pmr-record.json](dados/pmr-record.json) | campos dos registros do `.pmr` |
| [fontes.md](fontes.md) | rastreabilidade |

## 🆕 "Esta mídia gerenciada está online?" — o `.pmr` responde pelo MobID do MASTER — `confirmado` (2026-10-13)

A bin não diz se um master de mídia gerenciada está online (comentário em `avb_bin/masters.classificar`); o índice
diz: `msmFMID.pmr` de cada `Avid MediaFiles/MXF/<n>` → `{MobID do master: [.mxf]}` (o registro SHORT; ver
`pmr-fmid.md`), e online = algum `.mxf` listado existe. Medido no notebook Windows (3 volumes, 26 índices, 394
masters, ~1 s): 80/119 masters de bins do "DLPC LAB 23.976" e **87/99 masters do AAF do PRODUCAO-A** casaram pelo
`chave_mob` do MobID (a URN do AAF e a do pyavb dão a mesma chave). Uso no De Lá Pra Cá (`ja_online.py`): o master
que não casou com as pastas mas está na Avid MediaFiles (ou num link AMA online do projeto) aparece como "já online"
e não vai à vista na bin entregue — a `DJI_0317` do PRODUCAO-A era um desses, dada antes como "sem mídia".

## Por que isso importa

Hoje a casa **contorna** o AMA Management em vez de escrever nele. Se mapearmos `.mdb`/`.pmr` e o
trio AMA, abrem-se: relink programático sem reimportar, criação de mídia "já reconhecida", e
geração de AMA-link em lote (já que a parte `.aaf` é território conhecido).

## Sincronizar `Avid MediaFiles` entre máquinas: a pasta `1` e as pastas numéricas (MC SINC → MSYNC, 2026-05/06)

> Registrado pelo zelador do SSD em 2026-10-06, ao arquivar a família de apps de sincronização P2P
> (MC SINC, MC SYNC, MSYNC), a partir das memórias do Claude desses projetos.

- **O MC sempre grava a mídia nova em `Avid MediaFiles/MXF/1` da máquina.** Sincronizar a `1`
  diretamente entre editores sobrescreve mídia e **corrompe o `msmMMOB.mdb`**. O Avid Nexis
  resolve dando uma `1` por ilha; o MSYNC simula: cada máquina mantém a SUA `1` intocada e a `1` do
  outro chega como `MXF/1 - <apelido do remetente>`. Só a `1` é especial (`10`, `12` não). Validado
  pelo autor em 2026-06-21 (a mídia recebida caiu em `1 - <remetente>`). — `confirmado` (comportamento
  do app); a corrupção em si é relato do autor, não medida.
- **O MC só CRIA/atualiza `msmMMOB.mdb` e `msmFMID.pmr` em pasta de nome puramente numérico**
  (`1`, `2`, `3`…). Numa pasta com sufixo (`1-<remetente>`) ele **só lê** os índices que já estiverem
  lá; sem eles, os `.mxf` estão no disco e o MC não os enxerga (MC SINC, 2026-05-18, relato do
  autor) — `inferido`. Consequência de projeto: transportar `.mdb`/`.pmr` **junto** com os `.mxf`,
  a pasta inteira como unidade (o `.mdb` indexa todos os arquivos dela), e re-hashear o `.mdb`
  quando o mtime mudar (o `.mxf` é imutável, o `.mdb` não).
- 🆕 **Reafirmado e completado pelo autor (2026-10-11, De Lá Pra Cá, ao montar o laboratório do MC):** o MC só cria o
  `msmMMOB.mdb` e o `msmFMID.pmr` numa pasta de nome **puramente numérico** (sem letra nem caractere especial). Depois
  que os índices existem, a pasta pode ser renomeada à vontade: o MC LÊ o conteúdo, só não escreve mais nela. A pasta
  `1` é onde o MC grava o que ELE cria (import, render de efeito) — não confundir com o ExportFile, que vai para onde o
  usuário escolhe. **Mudou o conteúdo de uma pasta que não é a `1` → apagar o `.mdb` e o `.pmr` dela** para o MC
  recriar: pode ser com o MC aberto, mas SEM o foco nele — ao ganhar o foco ele varre as mudanças e recria os índices.
  Se não varrer sozinho, reiniciar o MC do zero. ⛔ Este banco já registrava a regra da pasta numérica (`inferido`) e a
  sessão criou `MXF/DLPC_LAB` sem consultar — corrigido para `MXF/3572` ("DLPC" no teclado do telefone). — relato do
  autor (`confirmado` como prática; a varredura ao ganhar foco ainda a medir pela bancada).
  ✅ **Medido pela bancada (2026-10-11, MC 25.6 Windows):** 3 `.mxf` movidos para a `MXF\3572` com o MC aberto e SEM o
  foco, `.mdb`/`.pmr` da pasta tirados do caminho → ao ganhar o foco (no 2º ciclo de foco, ~20 s) o MC recriou os dois.
  ⛔⛔ **É o GANHO de foco, não o tempo em foco** (2026-11-01, MC 2024.6 Win, Ciclo Assist pelo chat): com o MC JÁ na
  frente (o piloto tinha acabado de criar o projeto), "tirar e pôr o foco" alternava MC com MC — nenhum ganho — e a
  pasta nova de som não indexou em 60 s; refeito com o foco vindo de fora, indexou em 17,2 s (ciclo de 15 s = o 2º
  ganho). Tirar o foco para uma janela que NÃO é do MC e devolver; ciclo curto (5 s) dá o ganho mais cedo.
  `cicloassist/avid/importar_opatom.py::_janela_de_fora`.
  ⛔ MAS o master que já estava na bin continuou preso ao caminho antigo NA MEMÓRIA: `ExportFile` = "AMA Export failed"
  até REINICIAR o MC; depois de reiniciar, export e DRT acharam a mídia na pasta nova. ⇒ mover mídia já usada = reiniciar.
  ⛔ **Terceira vez (2026-10-31):** o Ciclo Assist propôs `MXF\9999_CICLO_SPIKE` sem consultar esta linha. Quem vai
  criar pasta na `Avid MediaFiles`: **só dígitos, sempre**.
- ⭐ **A convenção do autor para a diária** (2026-10-31, prática da casa, não regra do MC): o número da pasta sai da
  **data de gravação** (do caminho onde a mídia vive); a diária de VÍDEO termina em **0** e a de ÁUDIO, com o mesmo
  número, em **1** (ex. ilustrativo: `202610290` vídeo, `202610291` áudio — o formato da data é do editor). Alternativa: o áudio na MESMA pasta do vídeo — aí
  `.mdb`/`.pmr` daquela pasta têm de ser tirados para o MC reindexar (regra acima). É escolha do editor: um app
  deve PERGUNTAR (ou ler da receita), não impor.
- ⚠️ **Não re-varrer a mídia a cada arquivo recebido**: cada `.mxf` disparava uma varredura de
  disco lendo cabeçalhos — lento e "piscando" em NAS/Wi-Fi. Lembrar o que foi recebido em memória e
  recalcular a diferença sem tocar o disco (MSYNC, 2026-06-21) — `confirmado`.

## ⭐ Consolidar o som direto injetado, e a pasta do áudio (`confirmado`, MC 2024.6 / Windows 11, 2026-10-31)

Não há RPC de Consolidate na API (proto 2024/2025): é **Clip → Consolidate/Transcode…**, com o master selecionado
(clique no ÍCONE). O que o autor usa e foi medido no ensaio do Ciclo Assist:

- **Consolidate**, destino `SSD (D:)`, ⭐ **"Delete original media files when done" LIGADO** (regra do autor).
  Apesar do nome, com master AMA **não apaga nada do disco** — medido: o WAV original continuou lá. Ela troca o elo da
  bin: o master passa a usar a mídia consolidada. **Desligada**, o MC pergunta ("Copying Media Files": manter o master
  no original e criar `….new` no destino, ou religar) — é o diálogo a não deixar aparecer.
- O MC grava os OP-Atom de áudio em **`MXF`** (4 arquivos `A01…A04` para um WAV de 4 canais), em ~1 s.
- **A pasta do áudio:** movidos para `MXF610311` (a diária de vídeo é `202610310`; áudio = mesmo nome terminando
  em 1, convenção do autor), o MC criou `msmMMOB.mdb`/`msmFMID.pmr` ali ao voltar o foco, e o master seguiu online
  (carregado no Source: 08:00, A1–A4). Pasta só de dígitos, como sempre.
- ✅ **Repetido em 2026-11-01 (MC 2024.6, Win11), medido passo a passo para virar ferramenta do Ciclo Assist:**
  4 masters AMA de WAV estéreo 24 bits (a bin `OP6 SOM TESTE`, autorada pelo DLPC) → Consolidate → **8 OP-Atom
  (`A01`/`A02` por clipe) em `MXF` em 1,4 s**, sem diálogo, `.mdb`/`.pmr` criados na hora. O ícone dos masters passa
  de link AMA a master gerenciado. **Renomear `MXF` → `MXF611011` com o MC aberto (sem foco) funcionou** (sem
  trava de arquivo); depois de 2 ciclos de foco, `GetMobInfo(only_visible_columns=False)` dá `Offline: ''`,
  `Drive: SSD (D:)`, `Audio File Format: PCM` nos 4 (`inferido` que `Offline` vazio = online: não visto com
  um offline de verdade).
- ⛔ **O estado padrão do diálogo** (24.6, esta máquina): Consolidate marcado, NENHUM disco escolhido (o botão
  Consolidate cinza até escolher), **"Delete original media files when done" DESMARCADO** — tem de ser marcado a cada
  vez. "Skip native media files already on the target drive" vem marcado. Janela própria, título
  `Consolidate/Transcode`, 826×766.
- ⛔⛔ **O menu só habilita Consolidate com a seleção ATIVA da bin**, e a API não a cria:
  `SelectMobsInBin` seleciona (lido de volta: 4 de 4) mas com o realce CINZA `(113,113,113)` de seleção inativa, e
  Clip → Consolidate/Transcode fica cinza. Clicar na aba da bin, ou num vazio da bin e reaplicar a seleção pela API,
  NÃO resolve; `CloseBin` + `OpenBin` também não ativa a bin (e esvazia o Source). O que habilita: **clique no ÍCONE
  de um clipe + Ctrl+A** (realce AZUL `(54,101,142)`). `MakeActiveWindow` e `GetListOfWindows`: UNIMPLEMENTED no
  24.6. ⚠️ O cinza `(113,113,113)` NÃO é exclusivo da bin (aparece em vários painéis): não serve para localizá-la.

