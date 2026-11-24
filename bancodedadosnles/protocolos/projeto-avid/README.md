# Projeto Avid — o `.avp`, o projeto em rede e o binlock (`.lck`)

O que existe **em volta** das bins: o arquivo de projeto, a diferença entre um projeto local
e um compartilhado, e o arquivo de trava que o Media Composer usa para dizer aos outros
editores que uma bin está em uso.

Fatos consumíveis em [dados/avp-formato.json](dados/avp-formato.json) e
[dados/binlock.json](dados/binlock.json). Rastreabilidade em [fontes.md](fontes.md).

## O `.avp` é AObjDoc — o MESMO container da bin

O arquivo de projeto usa exatamente o cabeçalho de [../avb/](../avb/README.md):
`\x06\x00Domain` + `DJBO` + `AObjDoc`, seguido da tabela de objetos. A **única** diferença
estrutural está no campo 12 do cabeçalho:

```
.avb :  … IIII | dt | skip4 | ATob | ATve | "Media Composer 21.12.10" | 908 objetos
.avp :  … IIII | dt | skip4 | ATpj | ATve | "Media Composer 21.12.10" |   5 objetos
                                    ^^^^
```

⚠️ **Isto corrige um campo `confirmado`:** o
[dados/avb-header.json](../avb/dados/avb-header.json) documenta esse campo como
`"fourcc_ATob", "valor": "ATob"`, isto é, como constante. **Ele não é constante — é o
discriminador de tipo de documento:** `ATob` = bin, `ATpj` = projeto.

É exatamente por isso que o **pyavb recusa um `.avp`**: `file.py:162` faz
`assert ctx.read_fourcc(f) == b'ATob'`. Todo o resto — cabeçalho, tabela de chunks
(`fourcc + u32 size + data`), indexação — parseia idêntico. Um `.avp` está a **um `assert`**
de ser legível pela mesma biblioteca.

### O que tem dentro

Objeto raiz `Iprj`. Classes observadas:

| projeto | objetos | classes |
|---|---|---|
| teste, 1 bin | 5 | `ATTR`×3, `BLst`, **`Iprj`** |
| real, 68 bins | 39 | `WINF`×25, `ATTR`×4, `CATL`×3, `Decs`×2, `Bins`×2, `Tabs`, `BLst`, **`Iprj`** |

- Os `ATTR` carregam o **formato do projeto**: `_TGTFORMAT_*` (frame rate, tape rate, film
  rate, raster, geometria, color space, transfer, primaries, ACES) e `PRJ_*`
  (`PRJ_PROJ_TYPE`, `PRJ_COLOR_SPACE`, `PRJ_MATCHBACK`, `PRJ_STEREOSCOPIC_PROJECT_FORMAT`…).
- Os `WINF` são `WinFileLocator` — **os caminhos das bins**, na forma
  `letra + // + barras normais` (`Y//_Jobs/O PRODUCAO-A/…/OC-Corte_00.avb`), a mesma
  convenção documentada em [../avb/escrita.md](../avb/escrita.md).
- `BLst` guarda `BinsOpenOnProjectClose` e `BinLayout`.

### ⚠️ EOF não é fim de tabela

O `.avp` de 19.269 bytes do projeto real tem a **tabela de objetos terminando em 9.639**.
Os 9.630 bytes finais são **um save anterior que o Avid não truncou** — e contêm caminhos de
bins de quando o projeto morava noutro lugar (`D://01_PROJETO/…`, enquanto a tabela atual diz
`Y//_Jobs/…`).

⭐ **Um app que faça `grep` de caminhos num `.avp` — a abordagem óbvia — colhe caminhos-
fantasma de uma localização antiga.** A regra: `num_objects` termina a tabela; qualquer
coisa depois é lixo de gravação.

## 🆕 ⛔ Ler uma bin pela API pode TRAVÁ-LA para a equipe — `hipotese` (2026-08-23)

O MC cria o `<bin>.lck` **ao ABRIR a bin** (ver [dados/binlock.json](dados/binlock.json)).
O `OpenBin` do MCAPI tem **efeito visível** — ele abre a bin na tela do editor. Juntando as
duas medições: **um app que chame `OpenBin` num projeto compartilhado provavelmente toma o
lock daquela bin para o resto da equipe.**

⚠️ É `hipotese` de propósito: as duas metades são `confirmado` em separado, mas o `.lck`
nunca foi visto aparecendo *por causa de uma chamada de API* — falta ambiente compartilhado
em bancada.

⛔ **Por que isto merece destaque mesmo sem confirmação:** o sintoma aparece **para outra
pessoa**. Quem testou não vê nada de errado; um colega é que encontra a bin travada em nome
de uma estação que não está usando ela. E como o `.lck` não tem PID nem timestamp, o lock
que um app deixou é indistinguível de um lock vivo.

Quem for testar em ambiente compartilhado: o roteiro de verificação está no JSON, em
`consequencia_para_apps_que_usam_a_api.como_verificar`.

## Projeto em REDE × projeto LOCAL: a diferença é de pasta

| | rede (com binlock) | local |
|---|---|---|
| `<Projeto>.avp` na raiz | ✔ | ✔ |
| `<Projeto> Settings.xml` na raiz | ✔ | ✔ |
| `bin_background_color.json` | ✔ | ✔ |
| **pasta `<NOME-DA-ESTAÇÃO>/`** com cópia do `.avp` e do `Settings.xml` + `SearchData/` + `WaveformCache/` | ✔ | ✘ |
| `SearchData/` e `WaveformCache/` na raiz | ✘ (vivem na pasta da estação) | ✔ |
| `Statistics/` na raiz | ✔ | ✔ |
| `Trash/` | ✘ | ✔ |
| `<bin>.lck` e `<bin>.log` | ✔ | ✘ |

Dois pontos que mudam o desenho de um app:

1. **A cópia do `.avp` na pasta da estação é byte-idêntica à da raiz** (diff limpo, e o
   `Settings.xml` também). A subpasta não é "o projeto do usuário" — é o isolamento de
   cache/settings por máquina.
2. ⭐⭐ **Não existe flag de "projeto compartilhado".** Nem no `.avp` (só `_TGTFORMAT_*` e
   `PRJ_*`), nem no `Settings.xml`. **A colaboratividade se infere da estrutura de pastas** —
   existe uma subpasta com nome de estação contendo um `.avp` homônimo? — **e da presença de
   `.lck`/`.log`.** Um app não tem campo para perguntar.

> 🆕 ⚠️⚠️ **LEIA ANTES: o `.lck` NÃO é o único mecanismo de lock** (2026-08-24). Em Avid Shared
> Storage / NEXIS o lock é do **cliente de armazenamento**, chamado **`Flock`**, e é consultável
> por API (`ASIsFlockPresent`, `ASGetFlockList`, `ASGetFlockWSList`) — com *quem* e *qual
> workspace*. O `.lck` descrito abaixo é o mecanismo de **pasta compartilhada comum**, o caso
> degradado. Descoberto abrindo o Mimiq e o Osiris 2 →
> **[storage-como-integracao.md](storage-como-integracao.md)**.

## O binlock: `<nome da bin>.lck`

⛔ **Não existe lock no nível do projeto. Só por bin.**

### O formato

510 bytes = **`wchar_t[255]`**. Só o começo é escrito:

```
0x000 : "ESTACAO-01"  (UTF-16LE, terminada em NUL)   ← nome da ESTAÇÃO
0x01E : 478 bytes que NÃO são padding
```

Ler quem travou a bin é trivial: decodificar UTF-16LE até o primeiro NUL. Não precisa de
API do Avid. ⚠️ **Só o nome da máquina está lá** — o nome do usuário do SO **não** aparece
no `.lck` (aparece no `.log`).

⚠️⚠️ Os 478 bytes restantes são **memória de processo não inicializada** — ver
[../../seguranca/README.md](../../seguranca/README.md) §13.

### O ciclo de vida

`confirmado` pela prática (relato do usuário, 2026-08-20; não reproduzido em bancada por
falta de ambiente compartilhável):

1. O MC **cria** o `.lck` ao **abrir** a bin, e o **apaga** ao **fechar**.
2. Apagar o `.lck` à mão com a bin aberta **libera** a bin para os outros — que a abrem no
   **último estado salvo**.
3. ⚠️ **O caso comum na prática:** o MC fecha por erro e não dá tempo de apagar o `.lck`. O
   próprio usuário volta e encontra a bin travada **em nome dele mesmo**. A solução é apagar
   o `.lck` manualmente para retomar a posse.

⭐ **E o formato explica por que não há solução automática melhor:** o arquivo carrega
**apenas o nome da estação**. Não há PID, não há timestamp, não há sessão. **Não existe
como distinguir um lock vivo de um lock órfão pelo conteúdo** — só pela ausência do processo,
que o arquivo não registra. Um app que queira ajudar aqui só pode comparar o nome da estação
com o `COMPUTERNAME` local e oferecer a remoção.

### O `.log`

Texto puro ao lado da bin, uma linha por abertura, CRLF:

```
Wed Aug 19 17:07:35  Computer: ESTACAO-01 User: usuario-rede
Wed Aug 19 17:08:53  Computer: ESTACAO-01 User: usuario-rede
```

É o histórico de acesso da bin, e é onde o **nome do usuário** aparece.

## Ver também

- [../avb/README.md](../avb/README.md) — a bin, que usa o mesmo container.
- [../avb/plugins-e-handlers.md](../avb/plugins-e-handlers.md) — o que vive dentro da bin.
- [../../seguranca/README.md](../../seguranca/README.md) — o que o `.lck` e a `.avb` vazam.
- [fontes.md](fontes.md)

## Pendente

- Ler `.avp` com pyavb (falta destravar o `assert` e mapear `Iprj`/`Bins`/`CATL`/`Tabs`/`Decs`).
- Semântica dos 8 bytes entre o sentinela `IIII` e o fourcc do tipo (2 timestamps? checksum?).
- Estrutura do `Settings.xml` (346 KB de `AvProp`/`AvClass`, formato OMFI em XML).
- Uma bin com mídia realmente em volume de rede (as amostras tinham mídia em disco local).
