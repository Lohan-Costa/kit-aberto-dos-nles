# MSM — fontes / rastreabilidade

| data | o quê | como / amostra | confiança |
|---|---|---|---|
| 2026-06-27 | `.mdb` é Bento/OMFI | label de 24 bytes em `ARQUIVOS PARA ANALISAR/1/msmMMOB.mdb`; magic `A4 43 4D A5 48 64 72 D7`; `toc_off+toc_size+24 == filesize` (29584+90336+24=119944) | confirmado (externo) |
| 2026-06-27 | vocabulário OMFI no `.mdb` | tokens `MOBJ/SEQU/SCLP/TRAK/CLSD/ATTR/MDES/MSML`, props `OMFI:...`; zero `OBJD` | confirmado |
| 2026-06-27 | TOC interna do `.mdb` | — | pendente |
| 2026-06-27 | `.pmr` header + REC0 | parse byte a byte de `msmFMID.pmr` (1270 B, 5 mídias) | inferido |
| 2026-06-27 | `.pmr` pares longo/curto, timestamps Unix | leitura dos registros (0x6526ddaf etc.) | inferido |
| 2026-06-27 | AMA XML (`Managed AMA Media Folders.xml`) | 56 `<OneFolder>`, 9 pastas únicas; pares media/metadata | confirmado |
| 2026-06-27 | AMA Metadata Folder = N×`.aaf` + `amaFMID.pmr` + `amaMMOB.mdb` | conteúdo de `MIXADAS14109323/` e `MIDIAS BRUae8ba35c/` | confirmado |
| 2026-06-27 | **bin é autossuficiente p/ AMA**: importar bin com AMA Management VAZIA → 3 clipes ONLINE | teste `PARA RECRIAR/` em MC 25.12.0.58863; controle negativo + varredura de disco sem cache | confirmado |
| 2026-06-27 | caminho do arquivo na bin: `MacFileLocator.path_posix`/`path_utf8` (legado `path` vazio) | pyavb em `PORJETO LINK REPLICAR Bin.avb` (3 AMA source mobs com path_posix) | confirmado |
| 2026-06-27 | `.aaf` (AAF-em-KLV/MXF), `.mdb`, `.pmr`, XML são dispensáveis p/ import de bin | testes incrementais removendo cada peça | confirmado |
| 2026-06-27 | bug pyavb 1.4.0: `PCMADescriptor` → `unknown ext tag 0x02` em alguns mobs | leitura de `PORJETO LINK REPLICAR Bin.avb` | confirmado |
| — | autorar `.avb` por pyavb e abrir no MC; limites de escrita do pyavb | caminho de criação/relink | pendente |
| 2026-07-08 | `.pmr` leitura confirmada (MobID+tape+fname) contra 4 amostras heterogêneas | `tools/pmr_read.py`; `1/msmFMID.pmr` (vídeo Avid) + 3 `amaFMID.pmr` (áudio/vídeo AMA) | confirmado (leitura; sem round-trip) |
| 2026-07-08 | `.mdb` TOC interna: registros fixos de 24 bytes (objID+propID+typeID+valor inline-ou-offset/length) | dissecação byte a byte de `1/msmMMOB.mdb` (3764 registros) | confirmado (estrutura de registro); vocabulário de tipos/props ainda pendente |
| 2026-07-10 | `.mdb` **decodificado por completo (leitura)**: valor = offset+length+flag (`0x1`=ref, `0x10001`=imediato); dicionário auto-descritivo (propID 23=nome de tipo, 24=nome de propriedade) resolve todo o vocabulário da própria TOC; mob = `OMFI:ObjID=='MOBJ'` → `OMFI:CPNT:Name` + `OMFI:MOBJ:MobID`; MobID em GUID little-endian (inverter Data1/2/3 → SMPTE) | `tools/mdb_read.py` + `tests/test_mdb.py`; **cruzamento airtight**: name+MobID do `.mdb` == header do `1/…_A01.mxf` (pyaaf2); generaliza p/ amostra AMA (`SD01…`), que traz ainda `OMFI:FL:POSIXPathName` | confirmado (leitura; sem round-trip de escrita) |
| 2026-07-10 | `.mdb` **colunas de bin** (Name/Start/Duration/Tape/Video) via cadeia de composição OMFI (`Tracks→TRAK→SEQU→SCLP→SourceID`, `PhysicalMedia→CDCI/PCMA`); UsageCode `0x07`=master clip; grafo gravado em **DUAS cópias** (dedup por MobID); edit rate `23976/1000` | `tools/mdb_read.py::bin_clips`; **porte Rust** em `LEITOR DE MDB/…/mdb.rs` varreu a `Avid MediaFiles` real inteira (6 bins) e bateu com a bin do Media Composer (screenshots) | confirmado (leitura) |
| 2026-07-10 | `.mdb` **MobID de 12 bytes** (OMFI legado, `3×u32`) coexiste com o de 32 (SMPTE) — mídia antiga (`MXF/009/` real, MPEG-2); leitor que aceite só 32 deixa a bin vazia | `format_mobid` (32→UMID, 12→hex); bug real corrigido no app | confirmado |
| 2026-09-02 | `.pmr` usado por um SEGUNDO app (Assist anterior, painel dentro do MC): 12 `.pmr` → 358 masters em **0,56 s**, e **28/28** UMIDs de `CENAS/C07.avb` resolvidos sem abrir `.mxf`. ⛔ E o `tools/pmr_read.py` deste repo **descarta o registro SHORT**, que é onde está o MobID do MASTER — quem usar o parser como está responde *que arquivos existem*, não *de quem são* | varredura de `E:\Avid MediaFiles` + `CENAS/C07.avb` | confirmado (leitura) |

Amostras: `eng-rev-bin-e-mdb/ARQUIVOS PARA ANALISAR/1/` (mdb+pmr+mxf) e `.../AMA MANAGMENT/`.
Ferramentas: análise binária própria (Python stdlib). Sem lib dedicada para `.mdb`/`.pmr`.
Ponte com AAF: [../aaf/escrita.md](../aaf/escrita.md) §AMA.
| 2026-09-24 | O registro LONG do `.pmr` é a ESSÊNCIA do arquivo: `.mxf` exato de cada trilha do master (imagem, `_A01`, `_A02`…); TC da `.mxf` de áudio nas tags do stream de áudio — ver `pmr-fmid.md` §10 | bin do curta × `D:\Avid MediaFiles` (12 `.pmr`, 1429 arquivos): 290/290 trilhas presentes casaram; DRT gerado comparado ao nativo do Resolve 19 | confirmado |
| 2026-10-06 | Sincronizar `Avid MediaFiles` entre máquinas: `MXF/1` por ilha, `.mdb`/`.pmr` só criados em pasta numérica, não re-varrer a cada arquivo (README.md) | memórias do Claude do MC SINC (2026-05-18) e do MSYNC (2026-06-21), registradas pelo zelador do SSD ao arquivar | confirmado (app) / inferido (MC) |
