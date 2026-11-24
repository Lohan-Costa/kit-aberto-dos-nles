# .avb — formato binário (AObjDoc)

Descoberto lendo `pyavb 1.4.0` (`avb/file.py`) **e** conferindo byte a byte contra
`ARQUIVOS PARA ANALISAR/BIN/AUDIO-MAR (2).avb`. Os fatos estruturados estão em
[dados/avb-header.json](dados/avb-header.json). Confiança: **confirmado**.

## Endianness e o truque do fourcc invertido

Os 2 primeiros bytes do arquivo são a marca de byte order: `06 00` = little-endian (o usual),
`00 06` = big-endian. **Em little-endian todos os fourcc de classe são gravados invertidos.** Por
isso o início do arquivo lê `DomainDJBO`:

```
06 00            byte order (LE)
44 6f 6d 61 69 6e   "Domain"  (magic)
44 4a 42 4f         "DJBO"    = fourcc OBJD invertido
```

E é por isso que o sentinela de endianness aparece como `IIII` (`0x49494949`) em LE e seria
`MMMM` (`0x4D4D4D4D`) em BE. Strings são sempre `u16 (tamanho) + bytes` em macroman.

## Cabeçalho (na ordem)

```
[2]   byte_order            06 00 (LE) | 00 06 (BE)
[6]   magic                 "Domain"
[4]   fourcc OBJD           (no disco: "DJBO")
[str] "AObjDoc"
[u8]  doc_version           0x04
[str] last_save_str         "YYYY/MM/DD HH:MM:SS"
[u32] num_objects
[u32] root_index            (1-based; aponta para o Bin/ABIN)
[u32] endian_sentinel       0x49494949 "IIII" (LE) | 0x4D4D4D4D (BE)
[dt]  last_save_dt          (mesma data, binário)
[4]   skip                  00 00 00 00
[4]   fourcc "ATob"
[4]   fourcc "ATve"
[str] creator_version       u16=30 + 30 bytes (macroman), padding 0x20 até 32
[16]  reserved              zeros
```

Confere com o hexdump real:
`06 00 | Domain | DJBO | 07 00 "AObjDoc" | 04 | 13 00 "2023/09/17 19:05:07" | ...num_objects... | IIII`.

## Tabela de objetos

Logo após o cabeçalho vêm `num_objects` registros sequenciais. Cada registro:

```
[4]   class_id    (fourcc, invertido em LE)
[u32] size        (bytes do payload)
[size] data       (serialização da classe)
```

O parser percorre uma vez gravando `object_positions[i+1] = posição`, depois resolve a árvore a
partir de `root_index` sob demanda (lazy). Índice 0 = raiz/`None`. A classe de cada chunk vem da
tabela [dados/avb-classes.json](dados/avb-classes.json) (66 classes; `ABIN`→Bin, `CMPO`→Composition,
`SEQU`→Sequence, `SCLP`→SourceClip, `TRKG`→TrackGroup, `ATTR`→Attributes, etc.).

> **Atenção** — o `.avb` (AObjDoc) usa o vocabulário acima (`CMPO` para Composition). O `.mdb`
> usa **outro** vocabulário (OMFI/Bento: `MOBJ`, `TRAK`, `CLSD`). São dialetos diferentes do mesmo
> modelo conceitual. Ver [../msm/mdb-bento.md](../msm/mdb-bento.md).

## Escrita

`pyavb` reescreve o cabeçalho em `write_header` espelhando exatamente o acima
(`creator_version` truncado em 30 bytes, padding `0x20`, 16 bytes zerados). O round-trip
**dentro do pyavb** fecha; falta o teste decisivo: **abrir um `.avb` gerado no Media Composer**
(há acesso ao MC — é o próximo passo).
