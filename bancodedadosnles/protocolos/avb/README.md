# AVB — Avid Bin (formato AObjDoc)

Bin nativo do Avid Media Composer (`.avb`): o contêiner onde vivem clips, subclips, sequências,
efeitos, master/source mobs e as configurações de visualização do bin. **Não é AAF** (aquele é o
intercâmbio OLE; ver [../aaf/](../aaf/README.md)) e **não é o mesmo contêiner do `.mdb`** (aquele é
Bento/OMFI; ver [../msm/](../msm/README.md)). O `.avb` é o formato proprietário **AObjDoc**.

## ⛔⛔ Regra da casa: a timeline sai do Avid LENDO a bin — nunca por `ExportFile` (2026-09-24)

Qualquer app da família que precise **extrair uma timeline de dentro do Media Composer**
(exportar para outro NLE, analisar, converter) lê a `CompositionMob` direto do `.avb` com
`pyavb`. **`ExportFile`/AAF exportado pelo MC não é caminho, nem fallback** — decisão do
usuário, por riscos já vividos pelo time. Não propor de novo.

- Leitor de referência: `_DeLaPraCa/motor/avb_bin/segmentos.py` (produz a lista linear no
  formato de `aaf/parser.py::Segment.to_dict()`, que os writers de DRT/OTIO já consomem).
  Antes dele **não existia** leitor `.avb → segmentos` em nenhum app — só fingerprint de
  regressão (`RELINKER/src-python/avb_export/nle_model.py`) e edição in-place (Ciclo Assist).
- Decisão registrada no app: `_DeLaPraCa/docs/adr/0015-export-le-a-bin-nunca-chama-exportfile.md`.

## Container e ferramentas

- **Container:** formato binário próprio "AObjDoc". Assinatura no disco: `\x06\x00Domain` +
  `DJBO` (que é o fourcc `OBJD` gravado **invertido** em little-endian) + `AObjDoc`.
- **Biblioteca de referência:** **`pyavb`** (Mark Reid, mesmo autor do `pyaaf2`). Instala via
  `pip install pyavb`, importa como `import avb`. **Lê e escreve** `.avb`. Versão usada: 1.4.0.
  - Abertura: `with avb.open(path) as f: f.content` → objeto `Bin`.
  - Mobs do bin: `f.content.mobs` (lista de `Composition`).
- **Estratégia (decisão da casa):** híbrido — usar `pyavb` para ler/escrever rápido, mas
  documentar o formato por dentro aqui (este protocolo) para não ficar refém da lib.

### ⚠️⚠️ `pyavb` é PREGUIÇOSO — e isso morde fora do `with` — `confirmado` 2026-09-11

As propriedades são lidas do arquivo **no momento em que se toca nelas**, não na abertura.
Guardar um mob (ou uma lista deles) para inspecionar depois do bloco dá:

```
ValueError: seek of closed file
   ...  avb/file.py, read_object → f.seek(object_pos)
```

⛔ O traceback **não menciona o `with`**, então parece defeito da biblioteca ou arquivo
corrompido. A regra é simples: **tudo que interessa vira dado seu ainda dentro do bloco.**

⭐ E o custo de ler é desprezível, o que torna o erro fácil de evitar: medido em 2026-09-11
(MC 25.6/Windows), **5.524 mobs em 42 bins de um projeto real = 0,4 s**, sendo 907
MasterMobs. Ler `.avb` é barato; o que custa é a API do Media Composer (~500 ms por
chamada).

### ⛔ `avb.open(caminho)` deixa o arquivo ABERTO quando a abertura falha — `confirmado` 2026-09-25

O `AVBFile.__init__` (pyavb 1.4.0) abre o arquivo e lê o cabeçalho **no construtor**. Se a
leitura falha ali (`ValueError: not a avb file`, `AssertionError` de bin truncada), a exceção
sai **sem fechar**: o `with` nunca chegou a existir para chamar o `close()`. O arquivo só se
fecha quando o coletor de lixo passar. **No Windows isso TRANCA a `.avb`** (WinError 32 para
quem tentar apagar ou regravar), e num serviço que fica ligado a tranca dura até ele cair. Se
a bin for do projeto, o Media Composer pode não conseguir salvá-la. No macOS não há tranca
obrigatória, mas o descritor vaza do mesmo jeito (`inferido`).

- **Como apareceu:** no De Lá Pra Cá, o teste do "Abrir arquivo…" dá ao serviço uma `.avb`
  inválida de 1 byte. O `TemporaryDirectory` não conseguiu apagá-la no fim: *"The process
  cannot access the file because it is being used by another process"*.
- **Solução:** abrir o arquivo por conta própria, passar o objeto, e fechá-lo se o construtor
  falhar. O `close()` do pyavb fecha também o objeto de arquivo passado (`if self.f:
  self.f.close()`), então o caminho normal não muda. Implementado em
  `_DeLaPraCa/motor/avb_export/reader.py::topen`:

```python
fh = io.open(path, "rb", buffering=io.DEFAULT_BUFFER_SIZE)
try:
    return avb.open(fh)
except BaseException:
    fh.close()
    raise
```

### Listar os masterclipes de uma bin — `confirmado` 2026-09-11

```python
with avb.open(caminho) as f:
    for mob in f.content.mobs:
        if getattr(mob, "mob_type", "") != "MasterMob":
            continue
        mob.mob_id                                   # urn:smpte:umid:… (a chave)
        mob.name                                     # o nome COMO O EDITOR VÊ e edita
        [t.component.media_kind for t in mob.tracks] # 'picture' / 'sound'
```

Numa bin de cena real, os `mob_type`/`usage` encontrados foram: `SourceMob` (94),
`MasterMob`/`mastermob` (19), `CompositionMob`/`subclip` (10) e `CompositionMob` sem usage
(1 — a sequência).

⭐ O `mob_id` do MasterMob é a **mesma identidade** do `material_package_umid` que o
`ffprobe` lê do OP-Atom (ver [mxf](../mxf/README.md)) — é o que permite cruzar "o que está
na bin" com "o que está no disco" sem banco central.

⛔ **A pasta `Trash` do projeto é lixeira, e conta como "não está no projeto".** Medido:
varrendo-a junto, **33 de 36** clipes listados como "na bin e sem arquivo" eram material
que o editor já tinha jogado fora — e apareciam como se fossem mídia offline a recuperar.
Ignorar junto com `Attic`, `Render Files`, `WaveformCache`, `SearchData` e `Statistics`.

## O modelo de objetos (o coração do .avb)

Um `.avb` é um **grafo de objetos serializados**. Cabeçalho → tabela de N objetos (cada um é um
chunk `fourcc + u32 size + data`) → o objeto raiz é o `Bin` (`ABIN`), que referencia os mobs.

A taxonomia dos mobs é **a mesma do AAF** (vocês já a dominam): `Composition` com `mob_type` em
`{MasterMob, SourceMob, CompositionMob}` e `usage` em `{mastermob, subclip, precompute,
precompute_file, ...}`. Por isso todo o conhecimento de cadeia de mobs do AAF
([../aaf/estruturas.md](../aaf/estruturas.md)) **transfere direto** — muda só a serialização.

Exemplo real (bin `03_OC_EDIT VALENDO.avb`, 1200 mobs):

| contagem | mob_type | usage |
|---|---|---|
| 484 | SourceMob | (none) |
| 184 | MasterMob | precompute |
| 184 | SourceMob | precompute_file |
| 101 | MasterMob | mastermob |
| 44  | CompositionMob | subclip |
| 18  | MasterMob | (none) |
| 1   | CompositionMob | (none) → a **sequência editada** (`PRODA_CORTE.02`, 29 tracks) |

MobID é UMID SMPTE, idêntico ao do AAF/MXF/.pmr:
`urn:smpte:umid:060a2b34.01010101.01010f00.13000000.<material>`.

## Mapa das peças (índice deste protocolo)

| arquivo | conteúdo |
|---|---|
| [formato-binario.md](formato-binario.md) | Layout byte a byte do cabeçalho e da tabela de objetos; endianness; fourcc invertido |
| [estruturas.md](estruturas.md) | Modelo de objetos, taxonomia de mobs, AMA-link (caminho na bin), BinViewSetting, ponte com o AAF |
| [escrita.md](escrita.md) | Relink por byte-patch (caminho AMA), limites do pyavb writer, criação por clonagem |
| [dados/avb-header.json](dados/avb-header.json) | Campos do cabeçalho AObjDoc (consumível) |
| [dados/avb-classes.json](dados/avb-classes.json) | As 66 classes (fourcc → classe pyavb) |
| [color-correction.md](color-correction.md) | ⭐ O Color Correction na bin (UUIDs, as 3 bandeiras do HSL sem as quais o MC ignora o efeito) e a CONTA de cada controle do Base HSL Master no pixel, medida com carta sintética (MC 24.6, 2026-11-20) |
| [dados/efeitos-na-bin.json](dados/efeitos-na-bin.json) | ⭐ Parâmetros de efeito lidos da bin com os nomes do AAF (`avb.parameter_uuids`): a tradução de efeitos sem ExportFile (2026-09-27) |
| [dados/ama-online.json](dados/ama-online.json) | Regra completa do "AMA online" (path + mtime + size + handler GUID) e GUIDs conhecidos |
| [dados/codec-templates.json](dados/codec-templates.json) | Tabela de controle: templates AMA por codec/container (criação por clonagem) — o que temos e o que falta |
| [fontes.md](fontes.md) | Rastreabilidade |

## Estado da engenharia reversa

- **`confirmado`:** cabeçalho AObjDoc (byte-exato vs. amostra), leitura completa do grafo via
  `pyavb` (os 3 bins de amostra abriram sem erro), taxonomia de mobs, tabela de 66 classes.
- **`pendente`:** escrita/round-trip validado **no próprio Media Composer** (o pyavb salva, mas
  ainda não confirmamos abrir o bin gerado no MC — é o próximo teste, já que há acesso ao MC).

## Apps que implementam / validaram

- Ainda nenhum app da casa. Candidato natural: "BIN AVID" (geração/comparação). Hoje quem mais
  chega perto é o AAF-TOOL (gera AAF, não `.avb`).
