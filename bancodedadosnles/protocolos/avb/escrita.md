# .avb — escrita / relink

Técnicas para **modificar** um bin `.avb` de forma que o Media Composer aceite. Foco atual:
relink de AMA-link por edição de caminho. Confiança: **confirmado** (MC 25.12.0.58863, 2026-06-27).

## A regra completa do "AMA online" (confirmado)

Para um clipe AMA aparecer **online** ao importar a bin, a bin precisa casar com o arquivo em:

1. **Caminho** — `MacFileLocator.path_posix`/`path_utf8` = caminho POSIX do arquivo.
2. **Data de modificação** — atributo `_AMA_FILE_DATE_TIME` (no SourceMob) = **mtime do arquivo**
   em **Unix epoch (segundos)**. Validado: valor `1782514487` == mtime `2026-06-26 19:54:47` do
   original. Se não bater, fica **offline** mesmo com caminho e tamanho corretos.
3. **Tamanho** do arquivo (bateu na amostra; provável parte do check).
4. **Handler do plugin** — `_CONTAINER_HANDLER_GUID` (no MediaDescriptor) = GUID do plugin AMA que
   abre o tipo de arquivo. Conhecidos (ver [dados/ama-online.json](dados/ama-online.json)):
   - `.mov` → `73dc063c-7602-4c4c-ba3f-3f47120cd1e9` (UME/QuickTime)
   - `.wav` → `3711d3cc-62d0-49d7-b0ae-c118101d1a16` (WaveAiff)
   - mais o marcador `_IMPORTED_AMA = 1` no MasterMob e `mob_kind = 5` no MediaDescriptor.

Prova (2026-06-27, MC 25.12): cópia real de um `.mov` no caminho patchado ficou **offline** porque
o mtime da cópia (data da cópia) ≠ `_AMA_FILE_DATE_TIME`. Após `touch -r original copia` (alinhar
mtime), reimportou-se → **online**. O `birthtime` continuou diferente e **não** afetou → o check é
no **mtime**.

## Relink por byte-patch (caminho de mesmo comprimento)

A descoberta-chave (ver [estruturas.md](estruturas.md) §AMA): o caminho do arquivo AMA mora na
própria bin, no `MacFileLocator.path_posix`/`path_utf8` (string UTF-8/latin1). Para relinkar **sem
etapa manual no MC**, basta trocar essa string.

Quando o caminho novo tem **o mesmo número de bytes** do antigo, o patch é trivial e seguro: não
mexe em prefixos de tamanho, no `size` do chunk, nem nos offsets da tabela de objetos.

```python
d = open(bin_path, 'rb').read()
old = b"MIDIAS BRUTAS"      # trecho do caminho antigo
new = b"RELINK TESTE1"      # MESMO nº de bytes
assert len(old) == len(new)
patched = d.replace(old, new)         # troca todas as ocorrências (eram 22 na amostra)
assert len(patched) == len(d)
open(out_path, 'wb').write(patched)
```

Validação empírica (amostra `PORJETO LINK REPLICAR Bin.avb`, 3 mídias AMA):
1. Patch de `MIDIAS BRUTAS` → `RELINK TESTE1` (22 ocorrências; tamanho idêntico).
2. Criou-se a pasta `RELINK TESTE1/` (que não existia) com os arquivos.
3. Projeto novo → importou a bin patchada → **3 clipes ONLINE** lendo do caminho novo.
4. Controle: substituiu-se um item por **cópia real** (não symlink) → "Reveal File" no MC aponta
   para o caminho patchado, provando que o MC usa o `path_posix` que escrevemos.

> Symlink no caminho-alvo funciona (o MC/macOS resolve transparentemente), mas o "Reveal File"
> mostra o **alvo real** do symlink — não é erro, é resolução de link. Para conferir sem
> ambiguidade, use um arquivo real no caminho novo.

⚠️ **Apontar para um arquivo FÍSICO diferente** (cópia, transcode, mídia nova) exige, além do
caminho, casar o **mtime** com `_AMA_FILE_DATE_TIME` (ver "regra completa" acima): ou ajustar o
mtime do arquivo (`touch -r`/`os.utime`), ou patchar `_AMA_FILE_DATE_TIME` na bin = mtime do
arquivo. **Mover** o arquivo (`mv`) preserva o mtime → só o patch de caminho basta.

## Relink de comprimento DIFERENTE por byte-surgery (estrutural OK — 2026-06-27)

Funciona sem pyavb (imune ao bug do PCMA) porque **o `.avb` não tem tabela de offsets**: as
posições dos objetos são recalculadas no walk de leitura. Logo, mudar o tamanho de um chunk só
exige corrigir (a) os u16 das strings e (b) o u32 `size` do chunk; o resto desloca naturalmente.

Formato do chunk `FILE` (MacFileLocator), confirmado byte a byte (ver pyavb `misc.py` FileLocator):
```
... base AVBObject ...
0x02 0x02
path (legado):       u16 len + macroman      (normalmente u16=0, vazio)
ext 0x01 0x01 0x4C   path_posix: u16 len + macroman
ext 0x01 0x02 0x4C   path_utf8:  u16 (=2+len) + 0x00 0x00 + utf-8
0x03
```
(`read_string` = u16 LE + bytes; utf-8 leva prefixo `00 00`.) `MSMLocator` guarda
`last_known_volume` (macroman) + `_utf8` no mesmo esquema.

Algoritmo do relinker: para cada chunk `FILE` cujo path_posix está no mapa `{antigo: novo}`,
troca os blocos `01 01 4C|u16|posix` e `01 02 4C|u16|0000|utf8`, recalcula o `size` (u32 em
chunk_pos+4) por delta, e remonta os bytes (editar do fim p/ o começo se vários).

Ferramenta: `eng-rev-bin-e-mdb/tools/avb_relink.py` (100% stdlib, sem pyavb — imune ao bug do PCMA;
`list` e `relink --replace/--map [--sync-mtime]`). O patch de bytes em si está **correto**
(o pyavb/MC reabre, o caminho muda, estrutura íntegra).

### ⚠️ CORREÇÃO IMPORTANTE (2026-06-27): online ≠ só caminho; conform por identidade do arquivo

Vários "sucessos" de relink anteriores estavam **enganados por confound**: usavam symlink para o
arquivo original, ou o original seguia presente no caminho antigo — em ambos o MC resolvia para o
**mesmo arquivo físico (file ID)**, não para o nosso alvo.

Primeiro teste **limpo** (cópia byte-idêntica em caminho novo, original removido do caminho):
- mídia **H.264/mp4 (UME Link)**: ficou **online mas NÃO toca** —
  `APlayer::Play ... CreateContainerHolder.InitContainerHandler failed: CH Init failed: -1610612625`.
- Com o original presente (Test 1), o "Reveal File" abria o **original**, não a cópia da bin →
  o MC tem um caminho de resolução por **identidade do arquivo** além do path da bin.

**Causa raiz (v3, validada pelo usuário 2026-06-27):** a falha do mp4 NÃO era file ID / cópia. Era
uma **AMA Management leftover** referenciando a mesma mídia (apontando ao original, depois movido):
o MC **prioriza** a AMA Management sobre o `path_posix` da bin → "Reveal File" abria o original; com
o original sumido, o conform falhava (`InitContainerHandler failed`). A bin **resolve sozinha** pelo
`path_posix` (arquivo real) quando **não há** essa entrada conflitante — confirmado: AMA Management
vazia → import → ONLINE e tocando (cópia real inclusive), sem o MC recriar a AMA Management.

**Fluxo de relink confiável (AMA):**
1. `avb_relink.py relink ... [--sync-mtime]` — corrige `path_posix`/`path_utf8` p/ um **arquivo real**.
2. **Remover qualquer entrada conflitante na AMA Management** daquelas mídias (senão ela sequestra a
   resolução p/ o caminho antigo). Sem conflito, pular este passo.
3. Importar em projeto novo (MC relançado) → online.

Confiança: patch de caminho = **confirmado**; relink AMA ponta-a-ponta (sem AMA Mgmt conflitante) =
**confirmado pelo usuário** p/ caminho novo, inclusive cópia real. Em aberto: o MC parece **não
resolver via symlink** (uma bin relinkada p/ symlinks ficou offline com AMA Mgmt vazia) — confirmar
com alvo real. Refinamento futuro: limpeza **cirúrgica** da AMA Management (só os folders do relink)
em vez de apagar tudo — exige ler/editar a AMA Management (ver [../msm/](../msm/README.md)).

- **`_AMA_FILE_DATE_TIME`** ao apontar p/ arquivo físico diferente: setar = mtime do arquivo
  (u32/int, tamanho fixo, trivial). Com symlink/`mv` o mtime se preserva e não precisa.
- **`MSMLocator.last_known_volume`:** em mudança de volume pode precisar atualizar também
  (a confirmar; no Teste 1 o volume não mudou).

## O writer do pyavb: rejeitado para mob AMA MODIFICADO, aceito para o resto (confirmado 2026-06-28)

**Modificar** um mob AMA e salvar com o WRITER do pyavb (`f.write`) produz um bin que o MC traz
OFFLINE, mesmo com todos os campos corretos. Confirmado em ~5 iterações (v5..v9): MobID fresco AMA,
durações certas, `MSMLocator.mob_id` consistente — e offline. Trocando **só a via de escrita** por
byte-surgery (patch cru sobre o template), o **mesmo conteúdo lógico vem ONLINE**. Prova A/B (MC
25.12, 2026-06-28): bin com os 3 MobIDs do DJI_0012 trocados por material fresco **via byte-surgery**
→ online; a mesma troca via pyavb-write → offline.

⚠️ **REFINAMENTO (confirmado MC 2026-06-28, round-trip):** o problema é a **MODIFICAÇÃO** de mobs AMA
pelo pyavb, **não o writer em si**. Um **round-trip** (abrir uma bin Avid real só-vídeo e `f.write`
sem mudar nada — re-serializa 105k/109k bytes diferentes) reabriu no MC com a **timeline + clipes AMA
ONLINE e tocando**. Logo:
- **EDITAR mob existente (AMA): byte-surgery** (o pyavb-write da modificação quebra o online).
- **ADICIONAR objeto novo (ex.: uma CompositionMob/timeline): pyavb-write SERVE** — o MC aceita
  composição escrita pelo pyavb, e source mobs AMA não-modificados continuam online.

Isso abre o caminho de **autorar uma timeline dentro do `.avb`** (bin única, zero import): mídia online
por byte-surgery + **adicionar** a composição via pyavb, sem tocar nos source mobs. (pyavb tem
construtores `Composition(name,mob_type)`, `Sequence`/`SourceClip`/`Filler(edit_rate,media_kind)`,
`Track`.) NOTA: toda bin gerada deve **randomizar o UID** (`Bin.uid`) — senão o MC a confunde com a
bin de origem e não abre as duas juntas.

## ⛔⛔ CORRIGE (2026-09-12): o round-trip do pyavb NÃO é sempre aceito — o `WinFileLocator`

**Confiança:** `confirmado` · **Medido em:** MC **2025.6.58781** / Windows 11, projeto
`_ASSIST ANTERIOR`, bin de 96 itens montada à mão pelo editor · **Por:** Ciclo Assist
(`spikes/mover_entre_bins.py`)

A seção acima diz que um **round-trip** (abrir e `f.write` sem mudar nada) reabre no MC com
os clipes AMA online. Isso é verdade para a bin que foi medida em 2026-06-28 — e **falso
para uma bin que contenha `SourceMob` de fita com `locator = WinFileLocator`**. Ali o MC
não traz offline: ele **recusa a bin inteira** com `FILE_OPEN_FAILURE`.

**A medição, uma variável de cada vez, com todas as outras bins FECHADAS:**

| a bin escrita pelo pyavb | `OpenBin` |
|---|---|
| cópia **crua do arquivo** (nenhum pyavb no meio) | ✅ abre, 8 itens, nomes certos |
| resave completo, **uid novo** | ⛔ `FILE_OPEN_FAILURE` |
| resave completo, **uid PRESERVADO** | ⛔ `FILE_OPEN_FAILURE` |
| **só os 2** `SourceMob` com `WinFileLocator` | ⛔ `FILE_OPEN_FAILURE` |
| **os outros 94 itens** (as duas timelines inclusive) | ✅ abre |

⇒ **Um único mob desses condena o arquivo todo**, e a bisseção chega nele em 11 tentativas
(`spikes/mover_entre_bins.py`).

⚠️⚠️ **E `FILE_OPEN_FAILURE` agora tem TRÊS causas conhecidas**, todas com a mesma frase:

1. `Bin.uid` repetido com uma bin **aberta** na sessão (2026-08-16);
2. bin aberta no MC sendo reescrita por baixo (a matriz de 2026-08-16);
3. 🆕 **mob AMA com `WinFileLocator` passando pelo writer do pyavb.**

⇒ *Mensagem única para três causas é o pior caso de diagnóstico: a primeira hipótese que
alguém testar vai "explicar" o sintoma e parar a investigação. Foi o que aconteceu aqui —
gastei duas rodadas culpando o uid, e os uids estavam todos distintos desde o começo.*

### ⭐ Por que o produto nunca tropeçou nisto

`acrescentar_timeline` escreve na bin de cena do editor desde 2026-09-11, e ela tem **19
`SourceMob` de fita** — todos com `locator = None`, porque a mídia é **gerenciada**
(OP-Atom, `msmMMOB`). O locator só aparece em material **AMA**: na bin medida eram os dois
*sound rolls* `26Y06M29` dos WAV linkados.

| bin | mobs de fita | com `WinFileLocator` | pyavb `write()` |
|---|---|---|---|
| `CENAS/C07.avb` (a do produto) | 19 | **0** | ✅ |
| `BIN ORIGEM.avb` (montada à mão) | 14 | **2** | ⛔ |

⇒ **A pergunta a fazer ANTES de escrever numa bin do editor** é se ela tem mob AMA com
locator. Uma linha resolve:

```python
def tem_ama(f):
    return any(type(getattr(getattr(i.mob, "descriptor", None), "locator", None)).__name__
               == "WinFileLocator" for i in f.content.items)
```

⚠️ O que este spike **não** mediu: se a byte-surgery (a via que a seção de 2026-06-28
indica para mob AMA) preserva o `OpenBin` aqui, e se o defeito é do `TapeDescriptor` ou do
`WinFileLocator` isolado. Fica por medir.

## ⛔⛔ CORRIGE A SEÇÃO ACIMA (2026-09-13): não é o AMA, é a STRING NULA

**Confiança:** `confirmado` · **Medido em:** MC **2025.6.58781** / Windows 11, pyavb
**1.4.0**, projeto `_ASSIST ANTERIOR` · **Por:** Ciclo Assist (`spikes/a_bin_ama_regravada.py`)

A bisseção de 2026-09-12 achou os mobs certos e **nomeou a característica errada**. O que
condena a bin não é `SourceMob` com `WinFileLocator`: é um campo string **nulo** dentro dele.
⇒ A conferência `tem_ama` acima **não serve** — reprovaria bins AMA que regravam bem.

**Formato:** string de `.avb` é `u16 tamanho + bytes`. O tamanho **`0xFFFF` = o campo não
existe**, e é diferente de `0x0000` (existe e está vazio). O `read_string` do pyavb devolve
`""` para os dois (`ioctx.py`: `if size >= 65535: return u""`), e o `write_string` grava
`00 00`. Um ciclo de leitura e escrita troca "não existe" por "vazio".

**Onde apareceu:** os dois `WINF` da `BIN ORIGEM` (os *sound rolls* `26Y06M29` dos WAV
linkados) têm caminho principal vazio e caminho UTF-8 nulo:

```
original   02 02 | 00 00 | 01 02 4c ff ff | 03
pyavb      02 02 | 00 00 | 01 02 4c 00 00 | 03
```

**A prova, uma variável só, mesma bin, fixtures fechadas:**

| a `BIN ORIGEM` regravada pelo pyavb | `OpenBin` |
|---|---|
| como o pyavb grava | ⛔ `FILE_OPEN_FAILURE` |
| com o `0xFFFF` preservado | ✅ abre |
| com o `0xFFFF` preservado + timeline nova | ✅ abre |
| bin nova: timeline + 13 mobs de fecho copiados (`copy`) | ✅ abre |

**O contraexemplo que derruba a regra antiga:** duas bins AMA montadas pelo editor para o
teste (`BIN COM MIDIA AMA LINK`, `BIN COM SEQUENCIA AMA LINK`), com BRAW, MOV e WAV
linkados — **20 `WinFileLocator`**, todos com caminho preenchido, em `MediaDescriptor` e em
`TapeDescriptor`. `write()` cru do pyavb, com e sem timeline acrescentada: **abrem todas**.

**O que foi descartado no caminho**, medido nas mesmas bins:

- **Ordem dos objetos no arquivo:** o pyavb escreve na ordem do walk, o MC noutra. Um writer
  que preserva a ordem original reproduz a bin **idêntica byte a byte**; a ordem do pyavb
  abre igual. Não importa.
- **4 bytes do cabeçalho** entre a data de gravação e `ATob`, que o MC preenche
  (`cd dd c6 01`, `a8 4c c6 01`) e o pyavb zera. Não importa.
- Descontada a renumeração das referências, **574 de 574 objetos** da bin da sequência saem
  byte a byte iguais.
- Diferenças que sobram na `BIN ORIGEM` e são inofensivas (a bin abre com elas): o
  `PCMADescriptor` guarda a taxa como mantissa·10^expoente (`30 00 00 00 03 00` = 48·10³) e
  o pyavb regrava `80 bb 00 00 00 00` (48000·10⁰), mesmo valor; o `TrackGroup` sem tracks
  tem um ext `01 01` vazio que o pyavb não repete (`if self.tracks:`).

**O conserto** (Ciclo Assist, `cicloassist/avid/avb_fiel.py`): `read_string` devolve uma
subclasse de `str` vazia quando o tamanho é `0xFFFF`, e `write_string` a reconhece e grava
`ff ff`. Para o resto do código continua sendo `""`. Sobrevive a `AVBObject.copy` (medido:
a bin nova com o fecho da `BIN ORIGEM` abre).

⭐ **Onde a nula mora de verdade (De Lá Pra Cá, 2026-10-28, 523 bins do Mac):** no **nome de TODO parâmetro de
efeito** (`ParameterItem.name`) — 30 bins com efeito, de 1 a 3789 nulas cada. Essas o pyavb regravava `00 00` e o MC
abria igual (meses de relink provam): o campo que condena é o do `WinFileLocator`, que não apareceu em nenhuma bin
deste Mac. O De Lá Pra Cá passou a usar o mesmo conserto (`motor/avb_fiel.py`): a 'FASE 1 EFEITO' regravada saiu com o
mesmo tamanho e as 32 nulas, e abriu no MC 25.12 com a timeline na Record.

⇒ *Lição transferível: bisseção acha O QUE; só a comparação de bytes diz POR QUÊ. "Os 2 mobs
AMA sozinhos → recusa" era verdade e induzia a regra errada, porque aqueles dois eram os
únicos AMA **e** os únicos com campo nulo.*

✅ **E carregam — confirmado pelo editor na tela em 2026-09-13.** Todas as timelines desta
rodada, carregadas uma bin por vez na Record, com a mídia online e tocando:

| timeline | como foi escrita |
|---|---|
| `_AMA SEQ TL pyavb` | acrescentada à bin AMA da sequência, pyavb cru |
| `_AMA MID TL nova` | bin nova, timeline + fecho oculto (masters AMA) |
| `_AMA ORI TL nula` | acrescentada à `BIN ORIGEM` com a string nula preservada |
| `_AMA TL MASTERS NA BIN` | `montar_corte`: 3 masters AMA (MOV, WAV, BRAW) numa bin que NÃO tinha os masters, fecho levado junto |
| `_AMA TL MASTERS BIN NOVA` | `montar_corte`: os mesmos, em bin nova |
| 3 timelines de `_AMA TL GERENCIADO` | `montar_corte`: subclipe gerenciado da C07, master de câmera e master de som das diárias, acrescentadas em sequência à mesma bin nova |

⇒ Fica confirmado também, para AMA e para mídia gerenciada: **master e subclipe copiados
com `AVBObject.copy` para outra bin, ocultos (`user_placed=False`), resolvem ao carregar.**

---

## ⭐ Mover um item de uma bin para outra (2026-09-12)

**Confiança:** `confirmado` no nível do arquivo · **por confirmar** na tela do MC (o
veredito ficou bloqueado pelo `WinFileLocator` acima, que impede qualquer bin derivada
desta fixture de abrir).

Não há comando — ver `plugins/avid-panel-sdk/dados/docommand-comandos.md`. Por autoria, o
gesto tem três peças, e cada uma tinha uma dúvida:

**1. TIRAR** — `f.content.items.remove(item)`. `content.items` é lista comum e `add_mob` só
faz append; o writer anda pelas referências a partir do `content`, então o mob removido
simplesmente não é gravado. Medido: 96 → 95 itens, 8 → 7 visíveis, o MobID some do arquivo
e o resto relê intacto.

**2. COPIAR entre arquivos** — ⛔ `destino.content.add_mob(mob_de_outro_arquivo)` é
**recusado**, e a guarda está no **`write`**, não no `add_mob`:

```
ValueError: object is from different file: Attributes()      (avb/file.py:328)
```

⭐⭐ Graças a ela. Medido: **21 `instance_id`** da timeline colidem com os do destino, e o
writer indexa por `instance_id` com um `continue` em cima do repetido — sem a guarda, o
resultado seria uma bin plausível com referências trocadas.

⭐⭐ **E a saída já existe no pyavb: `AVBObject.copy(root)`** (`avb/core.py:206`) recria o
objeto no outro arquivo, recursivamente, com `instance_id` novo vindo do
`root.create.from_name`. É o *CAPTURE-REUSE* que este banco descrevia como mecanismo a
portar — não precisa ser portado. ⚠️ O `mob_id` não é objeto AVB, então o `copy` o preserva
por valor: a cópia é o **mesmo clipe morando noutra bin**, não um clipe novo parecido.
Medido: destino de 13 itens → 53, com o fecho inteiro e o item que já estava lá coerente.

**3. LEVAR O FECHO** — obrigatório, e é a parte que mata quem esquecer: a timeline medida
aponta **3 subclipes**, e subclipe não resolve fora da bin (§ *Timeline que referencia
SUBCLIPE*). ⚠️ `SourceClip` aponta por **MobID**, que é VALOR: o `walk_references` do pyavb
**não** atravessa isso. Quem não resolver o MobID à mão conclui que a timeline não depende
de nada.

⚠️ **Controle que todo verificador de integridade precisa:** o fecho de uma timeline SÃ já
contém um MobID de material number **todo zero**
(`…060e2b34.7f7f2a80.00000000.00000000`) — é o idioma AVB para "a cadeia acaba aqui".
Contá-lo como referência quebrada faz toda medição reprovar por um defeito que não existe.

### ⭐⭐ A ordem: TIRAR antes de PÔR

Com o mob ainda vivo na bin de origem **aberta**, o MC trata o que chega como cópia e
renomeia para `….AutoCopy.NN` — medido três vezes, em três bins diferentes. O editor pede
para mover uma timeline e recebe uma com outro nome.

⭐ Isso também **nomeia o mecanismo do `.AutoCopy`**: é **MobID visível repetido entre bins
ABERTAS**, não `Bin.uid` — os uids das bins medidas eram todos distintos.

🆕 **2026-10-12 (MC 25.6, De Lá Pra Cá — o relink pela bin):** abrir uma CÓPIA de uma bin (UID novo) com a original
aberta faz o MC duplicar **TODAS** as sequências da cópia — 92 de 92 ganharam **MobID novo** e o nome
`<nome>.AutoCopy.01` no arquivo que ele salvou. ⛔ Consequência para quem guarda o MobID de uma timeline antes de
abrir a bin de trabalho: depois do save ele **não existe mais** nela. O relink do app reencontra pela assinatura
(nome base com ou sem `.AutoCopy.NN` + nº de trilhas + comprimento; única ou recusa) e devolve o nome original
(`relink_avb._reencontrar`; amostra em `03 CASOS/ATUALIZAR/O02 BIN COM VARIAS TIMELINES`).

---

## Layout do MobID no disco (p/ byte-surgery — confirmado 2026-06-28)

O `.avb` é **não-comprimido**, mas o MobID **não é um blob contíguo** — vem serializado intercalado
com tags (por isso buscar pelo `bytes_le` cru dá 0). De `pyavb ioctx.read_mob_id`/`write_uuid`:
```
tag 0x41 + s32=12 + 12B SMPTELabel + (0x44 + u8)x4 [length, instHigh, instMid, instLow] + material
material (UUID) = 0x48 <time_low:4 LE> 0x46 <time_mid:2 LE> 0x46 <time_hi:2 LE> 0x41 08000000 <tail:8>
```
Os 16 bytes do material == `MobID.bytes_le[16:32]`. Em AMA os **16 bytes de prefixo são constantes**
(`060a2b34 01010100 01010f00 13000000`) e só o material varia → **MobID fresco = manter prefixo,
randomizar material**. A **região de 24 bytes do material** (com as tags) é única no arquivo →
trocar MobID = `data.replace(regiao_velha, regiao_nova)` global, size-neutral. Pega TODAS as refs de
uma vez (header do mob + `SourceClip.mob_id` + `MSMLocator.mob_id`), incluindo a auto-referência do
`MSMLocator` que dá offline se ficar com o id velho. Contagens (template vídeo-puro): essência 3x,
master 1x, arquivo 2x.

## TOC de objetos + scoping (p/ patchar duração/data sem colisão — confirmado 2026-06-28)

`AVBFile.object_positions[index]` é um **TOC** (`array`): offset do header de 8 bytes
(`4s class_id + u32 size`) de cada objeto; os dados começam em **+8** e **não são comprimidos**. Todo
objeto pyavb tem `.instance_id == index`. O clipe AMA vídeo-puro é uma cadeia de objetos `CMPO`
**separados** (não embutidos): os 3 mobs (Master/essência/arquivo), e referenciados por eles —
`mob.attributes` (objeto `ATTR`), cada `track.component` (Sequence) e seus `components[]` (SourceClip/
Filler), `descriptor`, `locator`. (Cuidado: `property_data` **não** alcança attributes/components —
use `m.attributes`, `m.tracks[].component` direto; e o `f.tell()` do pyavb é offset de um `BytesIO`
por objeto = base `object_positions[idx]+8` + tell, **não** offset do arquivo.)

Com o intervalo `[pos+8, pos+8+size)` de cada objeto do clipe, patcha-se **escopado**:
- **duração** = frame count (`nb_frames` ffprobe), `u32 LE`, nos objetos do clipe. Mora em ~5
  lugares (MasterMob + Seqs + SourceClips + `CDCIDescriptor.length`); o `Sequence.length` é
  computado; o SourceMob "de arquivo" tem `length` físico grande (~5178821) que **não** se mexe.
- **`_AMA_FILE_DATE_TIME`** = mtime do arquivo, `u32 LE`, escopado ao `ATTR` da essência (resolve a
  colisão quando dois clipes compartilham a mesma data).
- **nome + filename do path** = replace da string (size-neutral se o nome novo tiver o mesmo nº de
  bytes; senão, fixup de chunk-size como no relink).

Escopar ao objeto é necessário porque valores de duração colidem entre clipes (ex.: `len=580`
aparece 9x no arquivo, só 5 são do clipe).

## Criação de AMA-link por CLONAGEM (mídia nova — CONFIRMADO no MC 2026-06-28)

Ferramenta: `eng-rev-bin-e-mdb/tools/avb_clone.py` (pyavb **só leitura** + **ffprobe**; escrita
byte-surgery). Clona um clipe-template já AMA-linkado no MC para um **arquivo novo**, ajustando
MobID(fresco) + path + `_AMA_FILE_DATE_TIME` + nome + **duração** pelas técnicas acima. Validado:
clones `DJI_0004` (2434f) e `DJI_0005` (5884f) a partir do template `teste 10` (ProRes 1080p 29.97
vídeo-puro) ficaram **online e tocaram a duração inteira sem crash** — eliminando o
`VideoSampleFuture ... sequence failed` que a 1ª versão (duração herdada) causava.

Requisito: template por família (container+codec+resolução+layout) — ver
[dados/codec-templates.json](dados/codec-templates.json). Famílias com áudio PCM (PCMA) o pyavb não
lê → clonagem dessas precisa de byte-surgery na leitura também (a fazer).

### ⭐⭐ "Linka o primeiro, injeta os irmãos" — e o MOTOR viaja no molde (confirmado, MC 24.6.0 / Windows 11, 2026-10-18)

Medido em `_DeLaPraCa` (projeto "PROJETO - PILOTO LINK"). Método: para cada família, `LinkFile` de TODOS os
arquivos numa bin GOLDEN (a verdade do MC) + `LinkFile` de UM (o molde) numa bin só dele + `clone_generic` de
cada irmão numa bin nova + `OpenBin` + `GetMobInfo` do clone comparado coluna a coluna com o golden (36 colunas;
só `Creation Date`/`Modified Date` ignoradas) + quadro no Source × quadro 0 do ffmpeg.

| família | motor (coluna `Plug-in`) | resultado |
|---|---|---|
| MP4 H.264 1024×540 25p, sem áudio (PRODC) | `UME Link` | clone = golden; quadro certo |
| MOV H.264 1920×1080 25p, sem áudio (PRODC, 13 arquivos) | `UME Link` | **12/12 = golden**, TC incluído; quadro certo |
| BRAW 4096 e 3840, com áudio embutido (PRODUCAO-A) | `Blackmagic RAW` | **3/3 = golden**; quadro certo (claquete A09) |

⭐ **O motor de leitura vem do molde.** O clone herda `descriptor.uuid`, `wchar` e `_CONTAINER_HANDLER_GUID`
(ver [plugins-e-handlers.md](plugins-e-handlers.md)) e o MC o abre pelo MESMO plugin, de outro fabricante inclusive.
⇒ Para formato que o autodetect erra (X-OCN × MXF nativo, mesma extensão), o editor linka UM pelo Source Browser com
o `Link with` certo e os irmãos saem pelo motor escolhido — a API não precisa escolher (o `LinkFile` não tem campo
para isso: só `file_path`, `destination_bin`, `link_settings_name`). X-OCN em si: `pendente` (codec da Sony não
instalado nesta medição).

⭐ **A coluna `Plug-in` do `GetMobInfo` diz o motor** ("UME Link", "Blackmagic RAW") — a régua para conferir sem
abrir bin nenhuma.

Molde = UMA assinatura: (container, codec, perfil, raster, taxa, áudio). Raster diferente = outro molde (o BRAW
4096 e o 3840 são duas). 6 assinaturas cobrem os 47 vídeos do PRODC. Cada clone ≈ 0,3 s (o `LinkFile` com pausa
anti-rajada: ≥ 3 s).

O que o `clone_generic` não fazia e passou a fazer (as 5 medidas de hoje):

1. **`WinFileLocator`** (molde linkado no Windows): o caminho fica em `path` e `path_utf8` (este com prefixo
   `\0\0`), forma `D//A/B`, strings u16-prefixadas. O `relink.relink` só conhece `path_posix` (Mac) → o clone
   apontava para o arquivo do MOLDE, calado (colunas certas, `Source File` errado). Agora `_relink_win`.
2. **`Bin.uid`** — o clone copiava o do molde; com a bin do molde aberta: `FILE_OPEN_FAILURE` (a causa 1 desta
   página). O MC 24.6 grava o uid em DOIS objetos da bin; troca-se o u64 nos dois.
3. **TC de início**: o `−2` fixo do `_probe_start_tc` ("corpus H.264") NÃO vale para os MOV H.264 25p — o MC grava o
   TC do ffprobe sem desconto; os 12 clones saíram 2 quadros adiantados. Agora o desconto é CALIBRADO pelo molde
   (TC que o MC gravou − ffprobe do arquivo do molde); o −2 só sem o arquivo do molde.
4. **Material repetido (BRAW)**: o plugin da Blackmagic dá o MESMO material aos 3 mobs do clipe (master, fonte,
   MultiDescriptor; só o byte de instância muda: `13`, `13a1`, `13b1`). O `clone_one` caía em "region do MobID não
   encontrada" na 2ª volta. Agora troca o material uma vez (os três seguem juntos, como o plugin grava).
5. **`MultiDescriptor` (RAW com som)**: BRAW = `RGBADescriptor` (vídeo) + `PCMADescriptor` (AMOSTRAS, 48 kHz)
   dentro dele, e o caminho no `physical_media` do MultiDescriptor. O PCMA ganha as amostras do arquivo novo
   (ffprobe `nb_frames` do PCM: 319 quadros 23,976 → 638638 = 319 × 2002).
6. **Metadados da câmera** no `_USER` do master (BRAW: `Clip Number`, `Reel Name`, `Date Recorded` = as tags
   `clip_number`, `reel_name`, `date_recorded` do arquivo): clonados, ficavam os do molde. Agora troca a coluna cujo
   valor no molde é igual à tag do arquivo do molde, pelo par `<u16>chave<u16>valor` inteiro (o "2" do Reel solto
   casaria com outro campo).

#### As famílias com SOM embutido (mesmo dia, comparação PROFUNDA: colunas + cada descritor + cada componente)

As colunas da bin escondem diferenças: o MOV com PCM deu "5/5 iguais" nas colunas com o `PCMADescriptor` ainda
com as amostras do molde. A régua é comparar, mob a mob, `length`/`start_time` de cada SourceClip e de cada
descritor contra o golden. Com ela: **40/40 clones = golden** em 6 famílias (MP4 H.264 60p + AAC 19, MOV 1080p100 +
PCM 5, MOV 960×540 1, MOV 1080p25 12, BRAW 3).

| o que o MC grava | regra medida | n |
|---|---|---|
| duração do master (MP4 + AAC) | o stream MAIS LONGO: `max(quadros de vídeo, ⌈pacotes × 1024 / sr × taxa⌉)` — 981 para 979 quadros | 20/20 |
| `MPGADescriptor.length` (AAC) | `quadros × sr / taxa + 2112` (o *priming* do AAC) — o acréscimo sai do molde | 20/20 |
| `PCMADescriptor.length` (MOV PCM, BRAW) | as amostras do arquivo (`nb_frames` do PCM) | 8/8 |
| TC do MP4 sem `tmcd` | o `xmpDM:startTimecode` do XMP, na taxa de EDIÇÃO do componente Timecode (`edit_rate` 60; o `fps` dele também 60 — a coluna mostra 60p em base 30, com "." no ímpar) | 20/20 |
| início das essências (MP4 60p) | vídeo começa em **4** se o quadro 60 do TC é PAR, **3** se ÍMPAR; o áudio, 3 antes e 3 mais longo; o TC gravado = XMP − início do vídeo | 20/20 |
| geometria (MOV 960×540) | o MC grava 1920×1080 — recalcular pelo ffprobe estraga; mesma assinatura ⇒ a geometria do molde | 1/1 |

Tudo calibrado pelo MOLDE (o que o MC gravou para ele − o que o ffprobe lê dele), nunca por constante.
Código: `_DeLaPraCa/motor/avb_export/clone_generic.py` + `motor/avb_bin/video.py` (o "molde por assinatura" no relink).

#### ⛔ Armadilha paga (2026-10-18): mover `.avb` de bins ABERTAS para fora da pasta do projeto TRAVOU o MC

Para o teste de ponta a ponta não reaproveitar os links do laboratório, as bins `LAB*` foram movidas da pasta do
projeto com o MC aberto (o `bins_abertas()` do 24.6 devolveu vazio; quatro estavam em aba) e devolvidas minutos
depois. O MC 24.6 ficou **sem resposta** (`IsHungAppWindow`, 0 % de CPU, API sem resposta em 40 s) com uma janela
"AvidMediaComposer" 322×100 INVISÍVEL — e o `PrintWindow` dela também trava. ⇒ Nunca mexer nos arquivos de bin do
projeto com o MC aberto; para isolar um teste, use mídia em caminho novo (a cópia não casa com o que o projeto já
linkou) ou outro projeto.

⚠️ Correção de registro: o "5 `PRJ-0006-*.mov` recusados SEMPRE" (sessão de 2026-10-18 à tarde, projeto "DLPC
PRODUCAO-A 2024") **não é do arquivo**: no projeto novo os 13 linkaram pelo `LinkFile` (0,1 s cada) e os 13 clones
também abrem. A causa da recusa naquele projeto segue aberta (estado do projeto, não do formato).

## Entregar uma TIMELINE relinkada sem relink manual (rota AAF + bin de mídia — confirmado 2026-06-28)

Problema: o relinker exporta um AAF que, importado no Avid, entra **offline** → exige relink manual.
Objetivo: o relinker entregar algo que vem **online sozinho**.

**Regra de identidade do automatch do Avid** (confirmado em PRODUCAO-A, antes/depois do relink):
- **Mídia gerenciada (MXF)**: o Avid casa por **mob_id** (mob_id do clip ↔ MXF no banco
  `Avid MediaFiles/MXF/.../msmMMOB.mdb`). O mob_id É a identidade.
- **Mídia AMA**: o Avid casa por **arquivo** (path + `_AMA_FILE_DATE_TIME` + handler); o **mob_id é
  gerado fresco** no link e **não** é a chave (por isso clones AMA com mob_id aleatório vêm online).
- 🆕 ⭐ **E isso atravessa PROJETOS** — `confirmado` (2026-11-12, MC 25.12.0 Mac, Ciclo Assist
  `spikes/carta_aberta_bin_entre_projetos.py`): uma bin NOVA escrita pelo pyavb (UID novo) com os masters VISÍVEIS de uma
  bin do projeto A (`PRODUCAO-A-ENSAIO`) + o fecho deles OCULTO (os mobs de arquivo), gravada na pasta do projeto B
  (`LAB_ARRASTO_MAC`, que nunca teve esse material — conferido por `grep` nas `.avb`) com o MC FECHADO, aberta com o MC
  recém-iniciado (nenhum mob servido da sessão): 3 masters de vídeo (OP-Atom DNxHD LB do Resolve) e 1 de som
  gerenciado, todos **online** — a coluna `Drive` preenchida (`GetMobInfo`) e, no Source, o quadro certo (CAM 1,
  `10:00:05:00`) e a forma de onda de A1/A2. O `msmMMOB.mdb` é da PASTA `MXF/<n>`, não do projeto. ⚠️ O master que o MC
  cria tem `usage = mastermob`; o que o pyavb escreve do zero pode vir com `usage = None` — filtre master por
  `mob_type == "MasterMob"`.

**A identidade vive na BIN, não no AAF cru.** Diff antes/depois do relink de PRODUCAO-A: 83 de 118
masters ganharam mob_id NOVO (o Avid criou masters AMA novos p/ os vídeos). Um AAF "simples" do
relinker não carrega a identidade que o Avid casa → importa offline.

**Rota validada (mob_id matching AAF↔bin):** o Avid **casa o SourceClip de uma sequência de AAF a um
MasterMob AMA online presente numa bin já aberta, POR MOB_ID**, trazendo a sequência online sem relink
manual. Prova (MC 25.12, 2026-06-28): bin `MATCH MEDIA Bin.avb` (1 clip AMA online, MasterMob M) +
AAF `MATCH TEST.aaf` (sequence cujo SourceClip referencia M, via pyaaf2) → importou **online**.

Logo o relinker pode entregar **[bin de mídia: clipes AMA online com mob_ids escolhidos por ele] +
[AAF cujo sequence referencia esses mesmos mob_ids]** → timeline online no import. Ele controla os
dois lados, então alinhar o mob_id é escolha de engenharia. Equivale à opção do usuário "se a mídia
já está pré-linkada numa bin, o AAF acha". Construir a bin de mídia de áudio (PCMA) por byte-surgery
ainda é pendente; alternativa: usar uma bin já online e só LER os master mob_ids (o MasterMob mob_id
é legível sem tocar no descriptor PCMA que crasha o pyavb) e emitir o AAF alinhado.

Como autorar o AAF de teste (pyaaf2 1.7.1): `CompositionMob(usage=Usage_TopLevel)` →
`create_picture_slot(edit_rate)` → no `slot.segment` (Sequence) anexar `SourceClip(media_kind=...)`
com `.mob_id = MobID(bytes_le=<bytes_le do MasterMob no .avb>)`, `.slot_id`, `StartTime=0`, `Length`.

## Bin ÚNICA: timeline + mídia online numa só `.avb` (confirmado 2026-06-28)

Objetivo do relinker: entregar **uma `.avb`** já com o edit + as mídias online (em vez de AAF + pasta
de mídia p/ relink manual). Confirmado no MC (25.12) que dá pra produzir isso por **byte-surgery**:

**PoC (retarget de timeline-bin):** partindo de uma bin Avid real com timeline + masters AMA online
(`TESTE CORTE SIMPLES.avb`), o `avb_clone` retargeta os masters p/ **clipes novos/aleatórios** —
o **region-replace global do MobID atualiza as refs da composição sozinho** (o `SourceClip.mob_id` da
sequência casa com o `MasterMob` novo), o edit fica preservado, e os clipes novos só precisam ser
**longos o suficiente** p/ os alcances do edit (`SourceClip.start_time + length` ≤ frames do arquivo).
Resultado: uma bin única com a timeline + 3 drones aleatórios **online e tocando**. Generaliza p/
mídia nova (não é caso decorado).

⚠️ **UID da bin:** randomizar `Bin.uid` (u64 LE; aparece ~5x = auto-refs, trocar todas consistente),
senão o MC confunde a bin gerada com a de origem e não abre as duas juntas.

**Caminho de PRODUÇÃO — tradutor AAF→composição (núcleo CONFIRMADO 2026-06-28):** no real sempre há um
**AAF guia** com a timeline (edit feito com mídia convertida; o relinker faz o match p/ os originais).
Traduz-se **AAF → composição `.avb`** (não se autora do nada nem se reusa esqueleto fixo). Provado:
**pyaaf2 lê o edit** (comp `usage='Usage_TopLevel'`, `slot.segment.components`: SourceClip com
`.mob_id`/`.slot_id`/`['StartTime'].value`/`.length`, Filler com `.length`) e **pyavb autora a
CompositionMob do zero**, aceita pelo MC (validado lado a lado com a comp que o próprio Avid
materializa do mesmo AAF). Ferramenta `eng-rev-bin-e-mdb/tools/avb_translate_aaf.py`: **toda a Fase 1 de VÍDEO** validada no MC
(2026-06-28): cortes/gaps/in-points; **transições** (TransitionEffect dissolve/dip/fade, cutpoint=
alinhamento); **efeitos** (TrackEffect Resize/PIP/3DWarp, params casados por uuid, clip dentro do
efeito); **velocidade** (MotionEffect freeze/reverse/timewarp/trim-fill/**rampa** — control_points
Bézier + offset map integral); **multipista** (NestedScope -> N trilhas, ScopeReference=gap);
derivação automática de edit_rate (tabela 23.976/29.97/25/24). N trilhas de vídeo, UID novo.

MECANISMO "CAPTURE-REUSE" (núcleo do tradutor): efeitos têm objetos complexos (TransitionEffect/
TrackEffect/MotionEffect com EffectParamList, ParameterList/ControlPoints, tangentes). Em vez de
autorar campo-a-campo, CAPTURA-se o objeto do gabarito (deep-copy serialize->materialize entre
arquivos, tratando MobID/uuid.UUID/AVBRefList/Attributes) e REUSA-se variando só o que muda (length,
cutpoint, effect_id, params por uuid, speed). Gabarito p/ cada recurso: importar 1 AAF com ele no MC,
salvar, e diffar a composição que o Avid gera (em ARQUIVOS PARA ANALISAR/AMOSTRAS DE FASES/FASE 1/).
Convenção: a Sequence .avb começa/termina com Filler — add Filler(0) só se a ponta não for gap.

PENDENTE: Fase 2 = ÁUDIO (trilhas de som + PCMA, que o pyavb não lê -> precisa byte-surgery/parser).

**Autoria pyavb (mecânica):** `f.create.<Classe>(...)` cria objeto já com root (factory limpo).
Pegadinhas: `f.create.Composition(name,mob_type)` sobrescreve `name` com `mob_type` (setar `comp.name`
depois); `Sequence.length` é COMPUTADO (sem setter); `f.content.add_mob(comp)` registra no bin;
`f.content.uid = random` (UID novo). Estrutura mínima da CompositionMob aceita pelo MC: mob_id prefixo
`060a2b340101010501010f1013000000` (formato comp); `attributes` `_VERSION=2`+`SEQUERNCE_FORMAT_TYPE=22`
+`SEQUERNCE_FORMAT_STRING`+`_USER`+`_USER_POS`; `session_attrs` `_VIS_START`/`_VIS_END`; 3 tracks
(picture: Sequence `[Filler(0)+SourceClips/Fillers+Filler(0)]` + `filler_proxy=TrackRef(len=2147483647,
relative_track=-1)` + `session_attr` `_ENBLSTATE`/`_MONSTATE`; timecode: `Timecode(media_kind_id=3,
fps=30, start=108000)` + `session_attr`; DescriptiveMetadata: `Sequence[Filler]` + `filler_proxy`).
MÉTODO p/ cada recurso novo: importar 1 AAF com ele no MC, salvar, e DIFFAR a comp que o Avid gera.

### ⛔⛔ `SEQUERNCE_FORMAT_TYPE`: uma TABELA, e o valor errado DERRUBA o MC (2026-10-31, MC 2024.6 Win, `confirmado`)

O código de formato da sequência é lido pelo motor de compressão. Valor que não corresponde ao projeto = o MC cai ao
abrir/tocar (`FatalAbort Assertion failed: FALSE … CompressionMgr\CompressionManager.c, line 11276`, Source/monitor com
`CORE_CONSISTENCY_CHECK_FAILURE`). **Prova de causa e efeito** (ensaio M06, 1080p/25): a sequência do Órbita com **13**
derruba; a MESMA bin com SÓ esse campo trocado para **16** abre na Record e decodifica o quadro no lugar certo.

| projeto | código que o MC GRAVA (sequência feita no próprio MC) | fonte |
|---|---|---|
| 1080p/23,976 | 9 | dezenas de sequências do DLPC PRODUCAO-A / ORBITA DEMO / ASSIST TESTE |
| 1080p/24 | 7 | tabela da casa (`inferido`: não revarrido em 31/10) |
| **1080p/25** | **16** | `Untitled Sequence.01`, feita à mão no CICLO ENSAIO 25 (MC 2024.6) |
| 1080p/29,97 | 22 | tabela da casa + autoria acima |
| 1080p/50 | 24 | DLPC LAB ESTABILIZADOR 50P |

- ⛔ O **13** estava em QUATRO tabelas da família (Órbita `avid/writer.py`, DLPC `translate.py`/`nle_model.py`, Promo
  Entrega `autoria.py`, Assist anterior) e em dois testes que o CONGELAVAM — nenhuma medida no banco o sustentava.
  Consertado nos três ativos em 2026-10-31 (Órbita `1e236fa`, DLPC `c18d0b0`, Promo `3d858a3`). O que 13 é: `pendente`.
- ⇒ Código de formato só entra na tabela com uma sequência FEITA PELO MC naquele formato, lida do disco. Taxa nova =
  criar o projeto, fazer uma sequência à mão, ler o atributo. Teste que fixa o valor tem de citar essa medida.

### ⭐ `_MONSTATE` — a timeline abre MOSTRANDO imagem (confirmado 2026-08-09)

O `session_attr` da track não é decoração: **`_MONSTATE` é o botão de *monitoring*** da
timeline, o que mostra "desta track para baixo". Valores medidos numa bin que o próprio MC 25.12
salvou depois de o editor ligar o monitor na V2:

| media_kind | valor | significado |
|---|---|---|
| picture | `0` | sem monitor |
| picture | `1` | **MONITORADA** — uma só track de vídeo o tem |
| sound | `2` | outro eixo, **não** é "ligado" |

**Marque a track de vídeo de MAIOR índice.** O monitor do Avid é cumulativo PARA BAIXO: ligado na
V do topo, tudo abaixo aparece; ligado numa do meio, as câmeras acima somem do Composer.

⚠️ **Sem isto a bin abre com o Composer PRETO** e o editor liga na mão toda vez — e, como a
timeline está lá e correta, parece defeito do gerador, não configuração de sessão. Foi o que
acontecia com o Órbita até esta medição.

`_ENBLSTATE` fica ao lado (`0` em picture e timecode, `1` em sound) e **continua `inferido`**: são
os valores com que o Avid gravou uma timeline que ele abre, toca e salva — o que o campo controla
não foi determinado. Copiar; não chutar. Fatos em
[dados/track-session-attrs.json](dados/track-session-attrs.json).

## Fase 2 — ÁUDIO, TRANSIÇÕES, EFEITOS, TÍTULO (confirmado no MC 2026-07-10)

Toda a Fase 2 do tradutor `AAF→composição .avb` foi implementada no `RELINKER/src-python/avb_export/`
e **validada no MC** com a timeline real da PRODA (`PRODA_CORTE.02`, 1172 segmentos: 3 vídeo + 16 áudio,
23.976fps): abre + toca + navega/edita (Extract) + **SALVA** sem erro, com áudio sincronizado. O bug
recorrente que travava tudo era **`CM_INVALID_DUP`** ("Range specified for Dup is outside range of
component"), disparado no SAVE ou ao editar — sempre por um COMPRIMENTO INTERNO incoerente com o mob que
o referencia. Achado por comparação sistemática contra a **bin NATIVA do projeto** (o `.avb` do editor
original, antes do export AAF) = ground-truth. Cada peça abaixo é uma faceta desse invariante.

### Áudio — PCMADescriptor: samples ≠ frames (confirmado)
Um clipe de áudio tem DOIS comprimentos independentes que precisam ser coerentes entre si:
- **MASTER + tracks**: em **frames@edit_rate da timeline** (ex.: 407 @ 23.976).
- **`PCMADescriptor.length`**: em **SAMPLES@sample_rate** (ex.: 814815 @ 48000).
A conversão: `samples = ceil(frames / edit_rate * sample_rate)`. Se o descriptor ficar com samples de
OUTRA duração (ex.: clonado de um template e não reajustado), o Avid recusa no save. `sample_rate` do
descriptor precisa bater com o arquivo real: 44.1kHz clonado de template 48kHz → byte-patch de
`sample_rate`+`edit_rate`(mantissas exp10=s32le)+`average_bps`(=block_align×sr). O CLAMP do OUT (clipe
que referencia além do fim do master) evita `PMM_INSUFFICIENT_MEDIA` no corte — apara a duração ao que
a mídia tem + filler compensatório.

### Áudio embutido em vídeo — MPGADescriptor (confirmado)
Um `.mov/.mp4` de câmera com áudio AAC/MP2 embutido vira, na bin, um mob `MPGADescriptor` SEPARADO,
referenciado pelo MasterMob junto com o vídeo (CDCI). Ao clonar um vídeo, é preciso ajustar TAMBÉM a
duração da essência MPGA (a SourceClip da própria track do MPGA E o `descriptor.length`) para o frame-
count do arquivo real — o clone do MASTER sozinho não alcança o MPGA (os valores raramente coincidem,
ex.: master 5267 vs MPGA 5268). Sem isso: Dup-range ao editar (Extract) perto do fim do clipe.

### TRANSIÇÕES (dissolve) — a REGRA DO HANDLE (confirmado, o achado central)
Um `TransitionEffect` (áudio: `BLEND_AUDIO_DISSOLVE`; vídeo: `EFF2_BLEND_DISSOLVE`) numa Sequence fica
ENTRE dois componentes e causa OVERLAP: `tlen = Σ(não-trans) − Σ(trans)`. O objeto em si é simples e
IDÊNTICO ao que o Avid autora (mesmo `left_length`/`right_length`=15/15 SEMPRE — é constante, NÃO um
handle real; `left_bob`/`right_bob` são só CACHE de posição em disco, `None` é válido; `precomputed`
aponta pro mixdown renderizado, mas `None` também é válido — 2/141 reais são None). **A causa do
Dup-range NÃO é o objeto — é o HANDLE dos clipes vizinhos.** Regra medida na bin nativa (0 violações em
194 checagens; a nossa tinha 10 → Dup-range):
> Para uma transição de comprimento **L**, cutpoint **C**:
> - o clipe **ANTES** precisa de **(L − C)** frames de mídia DEPOIS do seu out (`handle_after ≥ L−C`);
> - o clipe **DEPOIS** precisa de **C** frames de mídia ANTES do seu in (`handle_before ≥ C`).

Na bin real os clipes de transição referenciam SUBCLIPES que carregam handle do master longo → sempre
têm folga. Masters ONLINE (arquivo de câmera) têm handle de sobra. Só os **OFFLINE** (mídia ausente,
autorada com comprimento = span exato) tinham ZERO handle → todas as violações eram offline. **Fix:**
mídia offline é sintética, então autora o master offline com **H frames de folga em CADA lado**
(`master_len += 2H`) e desloca os clipes offline **+H** (centraliza) → handle garantido. `H = maior
transição da timeline + margem`.

**Curva de blend interna:** o `param_list[N].control_track` da transição tem 2 control points `(0→0.0)`
e `(L→1.0)`; o offset do último ponto DEVE ser `L` (o comprimento real da transição), não o do template
capturado. O índice do param com a curva varia por effect_id (áudio=0, vídeo `EFF2_BLEND_DISSOLVE`=1).

**Cutpoint (corte seco):** desativando a transição (kill-switch), o corte não pode simplesmente sumir —
numa Sequence (concatenação linear) o clipe seguinte encostaria no FIM da transição, não no cutpoint.
Corte-seco correto: apara a cauda do clipe A em `(L−C)` e a cabeça do B em `C` (avança source_start) →
o corte cai exato no cutpoint. `Σ` de comprimento idêntico entre dissolve-ligado e corte-seco.

### FADES clipe↔silêncio (confirmado)
Transições com UM lado em Filler/gap são fades: **fade-in** `[Filler, Trans, Clip]` (surge do silêncio)
e **fade-out** `[Clip, Trans, Filler]` (some no silêncio). Estrutura idêntica a um dissolve, só que um
vizinho é silêncio (não precisa handle). Posição: fade-in estende o filler até `clip_tc_in + L` e recua
`pos −= L`; fade-out emite a transição após o clipe e o gap seguinte preenche.

### GANHO de áudio — Audio Gain → PanVolumeEffect (confirmado)
O `OperationGroup 'Audio Gain'` do AAF (parâmetro = `AAFRational`, `level = numerador/2^29`, 2^29=0dB)
vira um `PanVolumeEffect` na bin, embrulhando o clipe: `level`+`level_set=True`, `pan=16384`. O nº de
canais da trilha e o `_TRK_CLIP_G=1` na track marcam o clip-gain ativo. Unity (2^29) → não embrulha.
- ⭐ **Teto +12 dB (2026-10-29, Mac, MC 25.12):** o `level` é `int32` → máximo 2^31−1 = 4 × 2^29 = **+12,04 dB**
  (a régua do Audio Mixer para em +12). O Premiere vai a **+15**: gravar o valor cru estoura o `struct.pack` da bin.
  O De Lá Pra Cá manda +12 e CONTA na tela (`avb_export/do_prproj.ganho_de_clipe`). Medido pela rota Premiere → Avid
  (volume FIXO do clipe → `Audio Gain` → `PanVolumeEffect`): −40/−12/−6/+6/+12 aparecem idênticos na timeline e no
  mixer (modo Clip).
- ⭐⭐ **AUTOMAÇÃO DE VOLUME (keyframes) — confirmada (2026-10-29, MC 25.12 Mac).** O MC separa **ganho** (o `level`) de
  **volume** (a automação). A keyframe do Volume é uma **2ª trilha do `PanVolumeEffect`**, sem `index`, com
  `control_code 1000`, e dentro dela um `ControlClip` (`media_kind_id 10`, `attributes None`, `length` = o clipe,
  `interp_kind 3` = linear) com um `ControlPoint` por ponto: `offset [q, 1]` = quadros desde o **início do clipe na
  timeline** (não da mídia: clipe no quadro 48 da sequência com entrada 24 → os quadros 60/100/130 viraram 12/52/82),
  `time_scale 1`, `value [v, 1]` na MESMA escala do ganho (2^29 = 0 dB; teto int32 = +12 dB), `pp []`. A trilha da
  sequência ganha `_TRK_AUTO_G = 1` (o ganho é `_TRK_CLIP_G`). Clipe SEM ganho com automação: o MC cria o
  `PanVolumeEffect` com `level` 2^29 e `level_set False`. O `pyavb` lê e grava isso sem mudança (o campo
  `PanVolumeEffect.keyframes` fica vazio — não é ali). Gabaritos: bin `VOLUME FIXO` (3 pontos à mão, o autor) e
  `VOLUME KF` (DoCommand 6131 `Add Keyframe` após `SetPosition`), LAB_ARRASTO_MAC; a `VOLUME KF APP 2` montada pelo
  De Lá Pra Cá abre com a curva. ✅ **Nível conferido** (Audio Mixer em **Auto**, agulha por `SetPosition` e
  tocando por `StartPlay`): nos pontos −20,0 / 0,0 / +6,0 / −10,0 exatos; ⭐ **entre os pontos o Avid interpola LINEAR
  NA AMPLITUDE** (o `value`), não em dB — a ¼, ½ e ¾ de −20 → 0 deu −9,8 / −5,2 / −2,2 (amplitude: −9,76 / −5,19 /
  −2,21; em dB seria −15 / −10 / −5); 0 → +6 no meio = +3,5; +6 → −10 a 49 % = +1,4. É a MESMA regra do `Level` do
  Premiere: a curva vai ponto a ponto sem reamostrar. Tocando, o fader e o medidor da trilha seguem a curva (−20 →
  +5,6 em ~3 s). ✅ **MC 24.6.0 (Windows 11, 2026-10-29) — o piso abre igual**: a rota Premiere → Avid do De Lá Pra
  Cá com o .prproj REAL de 2023 do R04 (PRODC, `ISOLADO/MIDIA`; bin `DLPC WIN246 R04` no "projeto teste de plugin
  2021") — Audio Mixer (Clip) com os ganhos fixos **11.8 / 4.4 / 8.3** (o Premiere diz +11,76 / +4,39 / +8,34; A1 e
  A2 do mesmo par) e (Auto) a automação **0.0 → 12.0** na LOU_7237 (22:12 → 24:00) e **−4.7** na música OzCrias em
  A5/A6; a timeline desenha as curvas e escreve o ganho no clipe ("+4"). Agulha pelo clique na régua do Record
  (o 24.6 não tem `DoCommand`). ⏳ 25.6.
- ⭐ **Como o autor faz a keyframe de volume no MC** (o gesto, 2026-10-29): o Volume tem de estar LIGADO na trilha
  (Track Control Panel — a setinha ao lado do TC no canto superior esquerdo da timeline —, botão da trilha → None /
  Clip Gain / Volume / Pan; ou para todas: menu ☰ da timeline → Audio Data → Volume). `Add Keyframe` (6131) põe o ponto
  NA AGULHA, em toda trilha ATIVA com o Volume ligado — sem selecionar clipe; trilha desligada (Shift+Cmd+A) ou sem o
  Volume não recebe. Para mexer no ponto com o mouse, o botão **Audio Keyframe Mode** (penúltimo da barra da
  timeline, dois triângulos ligados por uma linha) precisa estar ativo. ⛔ Sem o Volume ligado o 6131 volta
  "Completed" e não grava NADA.

### TÍTULO — texto do Avid Titler+ (blob AVUP) (confirmado a extração; reconstrução AVB pendente)
Ver `dados/titler-texto.json`. O `OperationGroup 'Avid Titler+ Legacy'` (V3 = sub-seq 2 do NestedScope)
guarda o texto de cada caixa no parâmetro **`Text Box Text`** como blob **AVUP** (`'PUVA'` após um UUID
de 16B; `data` = string UTF-8 null-terminated). MESMO formato do SubCap. Acesso aos bytes crus:
`param['Value'].data` (o `.value` do pyaaf2 devolve `[]`). A EXTRAÇÃO do texto está feita
(`RELINKER/src-python/aaf/parser.py::_extract_title_params`); a RECONSTRUÇÃO do TrackEffect no AVB
(capture-reuse de um template neutralizado + override do blob) fica p/ uma sessão dedicada (gerar
timeline de variações estratégicas do Titler+, como se fez p/ transições/efeitos).

### TÍTULO — ESCRITA do Avid Titler+ ATUAL a partir do modelo neutro (2026-10-26, Mac; confirmado por ida-e-volta, render ao vivo pendente)
⛔ **MC 24.6.0 (Windows, 2026-10-29): o Titler+ sintetizado ABRE, mas a bin que o contém não passa pelo Save All Bins /
salvamento automático depois de editada** — `FatalExcpt "Range specified for Dup is outside range of component."`
(`Avid FatalErrorReports/APPEVENT.LOG`; o 1º veio sozinho, 15 min depois da montagem = o salvamento automático).
Bissecção com a rota .prproj → Avid do R04 (montar, `AddMarker` para sujar a bin, Save All): V1 só, V2, V3–V4, V2–V4
limpas; **V1 + V7 (um só título do Premiere, `TrackEffect E4EEBB07…` de 26 q) = o erro**. Fechar a bin pela API
(`CloseBin`) grava sem erro — a edição não se perde (o marcador chegou ao arquivo). O molde vem do 25.12 (Mac): é a
ficha B026. ✅ **CAUSA e conserto (mesmo dia, De Lá Pra Cá `a2f1499`):** a curva do parâmetro `8ba0916a` (um `ParamClip` 0 → 1) vinha no tamanho do título capturado (`length 24`, último ponto em 2304 = 24 × 96, `timescale 4`); reescalada na proporção do título, o R04 inteiro editado e salvo sem erro. A mesma classe da curva das transições.
⛔⛔ **E o 24.6 grava o Titler+ em OUTRO formato** (gabarito nativo criado à mão no 24.6: caso `03 CASOS/TITULOS/T02 TITLER PLUS 24.6 NATIVO`): `_EFFECT_PLUGIN_CACHE_INFO` "Version **0.0**", ~140 parâmetros, o texto puro em `80332d81…` e `48eec481…`, o estilo num XML **Deko** (`23101d3f…`, 47 KB, `deko_config version="2022.12.01"`), o fundo num JSON UTF-16 (`c6219ca9…`), SEM o MQP `67a614ac`; a curva `8ba0916a` com o último ponto em `length − 1`. O 25.x grava "Version **1.0**" (4 parâmetros, o MQP — o molde do app e as bins do T01). O 24.6 abre o 1.0 mas o título fica VAZIO (nem o sintetizado nem, por consequência, o que vem de um Avid 25.x). ⏳ o 25.6/25.12 abre o 0.0?
O sentido que leva ao Avid: um título do Premiere (ou de qualquer NLE) chega como o bloco `titulo`
da Carta (texto + fonte + corpo + cor + alinhamento + posição) e vira um **`TrackEffect` Avid
Titler+ ATUAL** (eid `E4EEBB07…`). Antes isso DROPAVA em gap (o `_title_entry` só reconstruía
quando a origem já trazia o `mqp_hex` pronto do AAF); por isso o "PRODUCAO-C" perdeu os
títulos no Avid. Agora o motor SINTETIZA o MQP (`_DeLaPraCa/motor/titulos/avid_escrita.py`, o
espelho de escrita do leitor `avid.py`), **editando o MQP do MOLDE** capturado (o template do
Title+ no `avb_export/templates.json`, texto "T01 BASE"), em vez de montar as ~324 chaves do zero:

- **texto:** reescreve a SEQUÊNCIA de `Character` do `Scene › Layer › Flow` (um `Character = { Name,
  PropList, UId, Code }` por glifo; espaço = `Code = { }`, nova linha = `Code = 0xA`; UId é ruído).
  ⭐ **É o `Character` que o MC renderiza, NÃO o `_TTEXT`** — provado no molde: os `Character`
  soletram "T01 BASE" enquanto o `_TTEXT` diz "TITLE" (= o nome do clipe na bin). O `_TTEXT` sai
  como `\x00\x00T+: <texto> \x00`, só para o nome do clipe.
- **estilo:** sobrescreve EM LUGAR o `Value` da entrada do `PropCache` que o leitor
  (`mqp.valor(lista, chave)`) resolve — `Text.Font.Name`/`Size`, `Material.Main.Base.{RGB}` na lista
  do caractere; `Transform.Position.{X,Y}` na lista da caixa. **Sem cirurgia de lista nem
  contadores** (o DB não tem `Count =`): troca só o texto do `Value`. Chave fora da lista cai no
  padrão (primeira ocorrência) — basta sobrescrever essa, porque há uma caixa e um estilo de
  caractere só.
- **alinhamento:** direto no `Paragraph.Info.Column.Justify` do `Flow` (Left/Center/Right).
- **posição:** o modelo neutro mede como o Avid (alturas de quadro a partir do centro, Y p/ cima).
  O título do Premiere chega só com `posicao_resolve` (coords do Resolve); a volta (inverso do
  `titulos/resolve.py`) é APROXIMADA → sai com aviso "conferir no Avid". Calibração fina = `pendente`
  (pede amostras iguais nos dois programas, como se fez p/ o Resolve).

**Confiança:** `confirmado` por IDA-E-VOLTA — o MQP sintetizado, relido pelo leitor JÁ MEDIDO
(`avid.py`/`mqp.py`), devolve texto/fonte/corpo/cor/alinhamento/posição iguais (teste
`_DeLaPraCa/tests/test_titulo_avid_escrita.py`, 21 casos; suíte 100 scripts). ⚠️ **Falta a prova de
que o MC RENDERIZA** o título sintetizado (pilotar o MC / o autor abrir o PRODC no Avid) — este domínio
falha em silêncio. **Contorno/sombra/fundo:** ainda NÃO escritos (o leitor do Premiere não os extrai;
quando o bloco neutro os trouxer, estender `avid_escrita.py`).
- **Os caracteres no `Code` (2026-10-28, medido em 574 bins desta máquina, Mac):** o MC grava ACENTO **cru em UTF-8**
  (é, ó, Ç, Ã, Ê, Ũ e o apóstrofo ’ — bins `TITLE EXEMPLOS`, `PROJ-X - RG_DIRECTO-BOARD_RELINK`, `TEST PRODC COM TEXT 1_SEQ`);
  espaço = `{ }`, nova linha = `Name 000a`/`Code 0xA`. O escritor manda caractere de CONTROLE (a tabulação) na mesma forma
  (`0x9`), nunca cru. ⏳ `{`, `}` e `=` dentro do texto: nenhuma amostra — `pendente` (medir com um título no MC).
  ✅ O render do título sintetizado no MC foi CONFIRMADO pelo autor em 2026-10-26 (PRODC; handoff do app).

### TÍTULO — ESCRITA do Titler+ Legacy: falta o GOLD (2026-10-26)
O autor pediu Title+ ATUAL **E** Legacy (compatibilidade com Avid antigo). O Legacy (eid
`8BA34E51…`) usaria o MESMO *capture-reuse*, mas **não há template dele** no `templates.json` (só o
do atual). Para escrevê-lo falta CAPTURAR um gold: uma bin com um título Titler+ Legacy (o autor tem
— o do PRODA_CORTE). Com o gold, o texto é um `CFUserParam` de string crua (ver `titler-texto.json`);
o estilo (XML "deko") segue `pendente`. Enquanto não houver gold, o motor escreve só o ATUAL (que
cobre todas as versões de MC que o PRODC mira hoje: 25.12 Mac, 24.6 Windows).

## ⚠️⚠️ O `topen` do pyavb é PREGUIÇOSO — nada pode reescrever o arquivo durante a sessão

Medido em 2026-08-16, e o preço foi bin corrompida + Media Composer fechando sozinho ao
abri-la. O sintoma foi `unpack requires a buffer of 8 bytes` — `struct` lendo lixo.

`avb.open()/topen()` **não carrega o arquivo inteiro**: mantém o handle e resolve objeto
por objeto, sob demanda, por offset. Qualquer coisa que reescreva o arquivo no meio disso
faz as leituras seguintes caírem em offsets que já não valem. **Duas fontes, e a segunda
é auto-infligida:**

1. **O NLE reescrevendo o mesmo arquivo.** Um `CloseBin` chamado de dentro da sessão do
   pyavb — fechar bin faz o Avid **regravar a bin**. → *Feche a bin ANTES de abrir o
   arquivo com o pyavb, nunca no meio.*
2. **O próprio `write()` no MESMO caminho que está aberto para leitura.** O writer pode
   ler um offset de um arquivo que ele acabou de truncar. → *Grave num arquivo AO LADO e
   troque com `os.replace` **depois** de fechar o handle.*

⭐ **A troca atômica não é preciosismo:** garante *ou a bin antiga, ou a nova* — nunca
meia bin, que é exatamente o que abre e derruba o Media Composer. ⚠️ `os.replace` só é
atômico **dentro do mesmo volume**: o temporário vai na pasta do projeto, não na pasta de
trabalho do app (que pode estar em outro disco). Use extensão fora de `.avb` para o NLE
não enxergar o arquivo enquanto ele existe.

⚠️ E depois de qualquer `Save`/`CloseBin`, **espere o arquivo estabilizar** (tamanho e
mtime parados) antes de lê-lo: os rpcs deste SDK não prometem ter terminado ao voltar.

⭐ **A regra geral, para qualquer NLE:** enquanto uma biblioteca preguiçosa tiver o
arquivo aberto, **ele é dela**. Um dono por vez, e o handshake com o NLE acontece **fora**
da sessão — antes de abrir, ou depois de fechar.

### ⚠️⚠️ A outra ponta da mesma preguiça: o mob NÃO sobrevive ao `close()` (2026-08-26)

Medido no Assist anterior. Um helper aparentemente inocente:

```python
def _masters(caminho):
    with topen(str(caminho)) as f:
        return [m for m in f.content.mobs if e_master(m)]      # ⚠️ ERRADO
```

Os mobs voltam, e **parecem** válidos. O primeiro acesso a `.tracks` estoura:

```
ValueError: seek of closed file
  avb/file.py:273  →  f.seek(object_pos)
```

⭐ **O que torna isto perigoso é que ele funciona pela metade.** `mob.name` **continua
respondendo** depois do `close()` — o nome já veio no índice de objetos, não precisa de
seek. Então testes que só leem nome passam, e o helper parece bom; quem estoura é o único
teste que **percorre a estrutura**. Foi exatamente esse o padrão observado: três testes
verdes e o quarto vermelho, com o defeito no helper que os quatro compartilhavam.

A forma certa é manter o percurso **dentro** da sessão:

```python
@contextlib.contextmanager
def _masters(caminho):
    with topen(str(caminho)) as f:
        yield [m for m in f.content.mobs if e_master(m)]       # ✅
```

⭐ Regra prática: **de uma sessão pyavb só saem dados puros** — números, strings, dataclasses
próprias. Objeto da biblioteca que cruza a fronteira do `with` é uma referência a um arquivo
que já não está aberto.

## Pendente / a mapear
- **Título Titler+ no AVB:** capturar+neutralizar um template do TrackEffect (142 params + 2 tracks
  internas) e sobrescrever o texto (AVUP). Mapear estilo (fonte/corpo/cor/posição — params homônimos
  ambíguos). Emissão de título nativo em DRT/OTIO (DaVinci/Premiere) usa o `text` já extraído.
- **Transição/dissolve com áudio renderizado:** o `precomputed` real é o mixdown já renderizado; hoje
  autoramos com `precomputed=None` (válido, o Avid re-renderiza). Idem AudioSuitePluginEffect (D-Verb).
- **Multicam (Selector):** o AAF flat-file já vem achatado p/ 1 câmera → não recuperável do AAF.
- **Formatos de áudio:** mono real interleaved, poly multi-mono (N source mobs), MPGA/mp3 standalone.
- **Retarget de volume / edit_rate ajustável / nome-caminho tam≠** (itens antigos, ver histórico git).

## ⭐⭐ ÁUDIO AMA AUTORADO POR FORA: ONLINE no MC, sem `LinkFile` (2026-08-16)

36 masters AMA de WAV **autorados por byte-surgery** vieram **ONLINE** no Media Composer
(25.6/Windows), sem uma única chamada de `LinkFile` e **sem nenhum diálogo**. Validado na
tela por um editor, junto de 44 BRAW linkados pelo MC, na mesma bin.

**Por que autorar o áudio e deixar o vídeo com o MC** (divisão proposta pelo usuário): o
áudio tem poucos formatos e o banco já os mapeou — medido neste acervo, **85/85 WAVs caem
em 5 combinações** `(coding_format, bits, canais)`, todas com template embarcado. O vídeo
tem dezenas de codecs. Autora-se o lado fechado e delega-se o aberto.

⭐⭐ **E o motivo maior não é driblar a janela.** O modal `Audio Start-Time Options` existe
porque o start do BWF é um número **sem base**; respondido na mão, ele **não deixa
rastro**. Autorado, vira valor explícito, gravado e testável.

### As QUATRO peças — todas necessárias, todas falhando em silêncio

| peça | valor certo | o que o clone fazia | sintoma |
|---|---|---|---|
| **forma do caminho** | `E//A/B/x.WAV` | `E:\A\B\x.WAV` | offline com `exists=True` e `mtime_ok=True` |
| **volume** | `V-001 (E:)` — rótulo **+** letra | `AVB-MEDIA` (do template) | `Drive` mostra o volume do template |
| **`_AMD_SOURCE_LENGTH`** | u64 LE = nº de samples | valor do template | — |
| **MobID** | fresco a cada build | reaproveitado | mede a rodada anterior (ver abaixo) |

⭐⭐ **A DECISIVA — a forma do caminho.** O Avid grava caminho de Windows como
**letra + `//` + barras normais**: `E//MIDIAS DE TESTES/.../x.WAV`. Golden-diff contra um
`LinkFile` oficial:

```
MC (online) : 01 02 4C  len=144  'E//MIDIAS DE TESTES/_PROJETOS EM ANDAMENTO/…/x.WAV'
nosso(offline): 01 01 4C len=142  'E:\MIDIAS DE TESTES\_PROJETOS EM ANDAMENTO\…\x.WAV'
```

O arquivo existia, o mtime batia, o descriptor era **idêntico ao do MC em todos os campos
comparados** — e ficava offline por causa de três caracteres. ⭐ **A causa é
cross-platform:** o clone nasceu e foi validado no macOS, onde o caminho POSIX já vem com
barra normal, e ninguém converteu ao portar. ⭐ A troca é **size-neutral** (`E:\`↔`E//` = 3
chars; `\`↔`/` = 1:1), então é byte-surgery sem correção de chunk.

⚠️ **`_AMD_SOURCE_LENGTH`** mora no `attributes` do PCMADescriptor, serializado como
`<u16 18>_AMD_SOURCE_LENGTH<u32 8><u64 LE samples>` — e vale o **mesmo** que
`descriptor.length`. O `clone_generic` patcha `length` por `scoped_replace_u32` e **não
alcança** esse u64. Também size-neutral.

⛔ **CORRIGE (2026-10-28, De Lá Pra Cá, B067 em `transversal/bugs-do-mundo-real`): o `scoped_replace_u32`
cru acerta campo alheio de mesmo valor — e o escopo por objeto não protege.** Medido nos 15 moldes embarcados,
trocando uma ocorrência por vez e relendo o objeto: 14 sem colisão, mas no `audio_1_24bit_1ch_semcena` (1 s) a
duração **25** é também a **referência da Sequence para o objeto 25** (referência de objeto é u32 LE como qualquer
campo), e as **48000** amostras são também o `sample_rate` e o `edit_rate` do PCMA e o
`_SAVED_AAF_AUDIO_RATE_NUM`. Um WAV sem cena de 7 s quebrava a bin ("bad index: 175"); com 1 s a referência
apontaria **calada** para outro objeto. Molde CURTO = números pequenos = colisão com referências. Agora
`clone.campos_provados` prova cada offset (troca um, relê, confere que mudou o campo pedido), uma vez por molde.
E a duração de um master de áudio sai da **taxa** do molde, não da razão quadros/amostras: o molde de 1 s tem 25
quadros a 23,976 (o MC conta um quadro de guarda) e a razão levava esse +4 % a todo WAV (7 s → 175 quadros; certo 168).

⚠️ **O volume: `rótulo + letra` na MESMA string.** O banco ensina que a coluna `Drive` é o
rótulo e **não** a letra — isso vale para **LER** (não monte `V-001:\`). O campo GRAVADO
carrega os dois: `V-001 (E:)`. Ele aparece em **duas variantes por arquivo**: `MSMLocator`
com prefixo `u16`, e uma variante utf8 `01 03 4C` cujo campo inclui **dois bytes nulos**
(`len=11` para 9 caracteres) — um `replace_field` que procure só a primeira troca metade.

⚠️⚠️ **ARMADILHA DE MEDIÇÃO, e foi a mais cara do dia: o MC serve mob por MobID a partir da
SESSÃO, não do arquivo.** Duas bins com o mesmo MobID no mesmo boot: a primeira carregada
ganha. Invalidou **três** medições — o `Drive` continuava `AVB-MEDIA` com **zero**
ocorrências da string no arquivo, e depois continuou `V-001` com o arquivo já gravando
`V-001 (E:)`. **Ou se reinicia o MC a cada iteração, ou se geram MobIDs novos** (reautorar
do zero é barato: `clone_generic` já randomiza).

### O que NÃO era necessário

⛔ **Entrada na AMA Management.** Medido: os 44 BRAW seguiram **online** com a AMA
Management **apagada** e nenhuma pasta registrada. Confirma o modelo v3 (opcional, mas
prioritária) — e vale para áudio também: os 36 WAVs vieram online sem nenhuma entrada.

### ⛔⛔ A TAXA DO PROJETO na cadeia inteira — 5 gabaritos do MC (`confirmado`, MC 2024.6 / Windows 11, 2026-10-31)

**O B001 no AVB de áudio** ([bugs-do-mundo-real](../../transversal/bugs-do-mundo-real.md)). O `fps` passado ao
`clone_generic` só entrava no START; a taxa dos componentes e a duração vinham do MOLDE — e os moldes embarcados são
todos de 23,976. Num projeto 1080p/25 o master injetado saía a **23,976 com 192 quadros** (o MC grava **25 com 200**),
calado. Achado no ensaio do Ciclo Assist (som direto injetado num projeto 25).

**Método:** o MESMO WAV (8 s, 4 canais 24 bits, sem cena/iXML, `time_reference` = 01:00:08:00) linkado pelo
`LinkFile` em 5 projetos, o diálogo "Audio Start-Time Options" respondido com o fps do projeto + OK to All, e a cadeia
lida campo a campo. Os 5 `.avb` são os gabaritos de `_DeLaPraCa/tests/dados/gabaritos_audio_mc/`.

| projeto | `edit_rate` (exp10 gravado) | start | master | `Timecode` da fonte de mídia | clipe da fonte |
|---|---|---|---|---|---|
| 1080p/23.976 | 23976e-3 | 86505 | **193** | fps 24, 10.800.000 | 4.143.250 |
| 1080p/24 | 24e0 | 86592 | 192 | fps 24, 10.800.000 | 4.147.392 |
| 1080p/25 | 25e0 | 90200 | 200 | fps 25, 10.800.000 | 4.320.200 |
| 1080i/59.94 NDF | 2997e-2 | **108131** | **241** | fps 30, flags 0 | 5.179.062 |
| 1080i/59.94 DF | 2997e-2 | 108131 | 241 | fps 30, **flags 1** | 5.179.062 |

As regras (todas conferidas nos 5):
- **`edit_rate` de TODO componente** (master, fonte de arquivo PCMA, fonte de mídia) = a do projeto.
- ⛔ **start = PISO** (TC nominal × taxa ÷ nominal), não arredondamento: 108131,87 → 108131. CORRIGE "a fórmula está
  certa" abaixo — o `round` só coincidia porque a 23,976 a fração era ,49. A mesma página já tinha a prova sem ler
  assim: 10:00:00 a 23,98 → `09:59:24:00` (863136,86 → piso).
- ⭐ **Duração do master = os quadros que o som TOCA**: teto(início exato + duração) − piso(início exato). 191,8 quadros
  a 23,976 dão **193** porque o início cai em ,49. ⏳ `hipotese`: é isto que explica o "ceil ou ceil+1" dos 56 masters
  abaixo — não conferido contra eles.
- **Fonte de MÍDIA** (WAV sem cena): `Timecode` com fps = nominal, duração fixa 10.800.000, `flags=1` só em DF; nas
  trilhas, clipe = arred(172.800 s × taxa) + master, e filler até 10.800.000. Drop-frame NÃO muda nenhum quadro.
- ⭐ **Fonte de TAPE (WAV com cena) — MEDIDA no mesmo dia** (WAV real de Sound Devices Mix664, 4 canais, 38 s,
  `sSCENE=53-54-3` `sTAKE=02` `sTAPE=24Y08M01`, iXML `TIMECODE_RATE 24/1 NDF`, TC 16:56:27:00, linkado num projeto
  **25**, diálogo respondido 25): o MC nomeia o master `53-54-3/02` (cena/take) e a fonte de tape `24Y08M01`.
  **Master e fonte de arquivo seguem o PROJETO** (25; 950 quadros; start 1.524.675 = 16:56:27 contado a 25) e têm a
  MESMA duração. ⭐⭐ **A fonte de TAPE segue o TC do GRAVADOR** (`TIMECODE_RATE`), não o projeto nem a resposta do
  diálogo: edit_rate 24, `Timecode` fps 24 com **120 h a 24** (10.368.000 — diferente da fonte de MÍDIA, fixa em
  10.800.000), e o clipe = 48 h a 24 + 912 (38 s × 24), filler até completar. Isso explica o tape a 30 do molde de
  cena (o gravador de origem estava a 30). Gabarito: `_DeLaPraCa/tests/dados/gabaritos_audio_mc/
  gabarito_mc_cena_tc24_projeto25.avb`. ⏳ **Falta no motor:** remendar o mob de TAPE por esta regra (hoje fica a do
  molde) e um molde de 4 canais com cena de nomes padronizados; TC de gravador 23,976/29,97 DF sem gabarito.
- ⛔ **Molde da variante ausente caía calado no outro:** não havia molde `semcena` de 4 canais e o WAV sem cena saía com
  fonte de TAPE (o MC faz de MÍDIA). Hoje o gabarito de 23,976 é esse molde, e o resultado diz `variante_trocada`.

⭐ **A prova roda em toda injeção** (`clone_generic.conferir_taxa_do_audio`): a bin gravada é relida e a cadeia tem de
seguir as regras acima, senão o arquivo vai para `pulados` com o motivo. ⚠️ Os offsets são do molde e a troca de nome
muda o tamanho: os remendos de taxa vão ANTES dela. ⚠️ O `fps` do `Timecode` é o ÚLTIMO u16 do objeto — os u16 de antes
são os tamanhos das strings do Component (`0xFFFF`).

✅ **No MC (mesmo dia):** o WAV injetado a 25 abriu na bin online, consolidou (abaixo) e tocou no Source, 08:00, A1–A4.

### O start do BWF: a fórmula está certa e é reprodutível

`clone_generic._probe_bwf_start(path, edit_rate)` converte `time_reference` (samples desde
a meia-noite) → TC no rate **nominal** (24) → pulldown NTSC **1000/1001 exato** (não o
`edit_rate` arredondado). ⭐ **Confirmação independente:** para `PRODUCAO-A - 05-04 C4
P1-T002.WAV` a fórmula deu `11:42:00:00`, **o mesmo TC que o diálogo do próprio MC
exibia** para esse arquivo, e o mesmo que o `LinkFile` oficial gravou.

⭐ **Desde 2026-10-28 o De Lá Pra Cá grava o start SEMPRE** (decisão do autor; antes só com `AVB_AUDIO_TC=1` e o
master ficava com o start do MOLDE — 09:59:24:00 num WAV sem TC). **WAV sem `time_reference` → start 0**: medido no
MC 25.12, um WAV sem bext ligado pelo próprio `LinkFile` sai com `Start 00:00:00:00` (e `Creation Date` = a hora do
link — o clone ainda leva a do molde). ⚠️ O start mora nos SourceClips do mob da ESSÊNCIA (o do `PCMADescriptor`);
dois moldes embarcados (WAV 24 bits estéreo, AIFF 16 bits) o têm ZERO ali — achar pelo mob, nunca por "start não-zero".
Conferência no MC: 42.120 s de relógio no BWF → 1009870 quadros → a coluna Start mostra `11:41:17:22` (o TC de 24 dos
quadros a 23,976), exatamente o que a fórmula manda.

⚠️ **Responder `fps da timeline` é o certo**, e há duas confirmações no dado: o master
offline carrega `_SAVED_AAF_AUDIO_RATE_NUM/DEN = 24000/1001`, e os masters que o MC autora
usam a mesma taxa. **Prefira COPIAR do master offline quando ele existir**; o fps do
projeto é o fallback.

⚠️ **Duas camadas de taxa, não confunda:** no **MasterMob** o áudio conta em **frames@
timeline** (23,976); `edit_rate == sample_rate` (48 kHz) vale no **descriptor/essência**.

### ⚠️⚠️ A DURAÇÃO DECLARADA DO MASTER: não há fórmula, use o que a timeline PEDE

Autorar o áudio com a duração "correta" do arquivo **não basta**, e o sintoma é fatal: um
único clipe que peça 1 frame além do fim do master faz o Media Composer recusar **a
timeline inteira** com `PMM_INSUFFICIENT_MEDIA`. Medido em 2026-08-16, num relink com 97
de 98 mídias online: **10 clipes, todos de som, todos estourando por exatamente 1 frame**.

⚠️ **O Avid não declara a duração do master por uma fórmula fixa.** Confrontando 56
masters de som de um projeto real contra o `ffprobe` dos arquivos:

| fórmula | casos que ela explica |
|---|---|
| `ceil(samples / sr × fps)` | 33 |
| nenhuma candidata testada | **16** |
| `ceil(...) + 1` | 4 |
| `ceil(real)` ou `ceil(nominal)` | 2 |

> ⚠️ **2026-09-17:** antes de atribuir um "+1" ao Avid, confira se a SUA conta não é
> `ceil(duration_ms/1000·fps)` sobre vídeo — ela mesma conta um frame a mais em parte dos
> arquivos (ver `protocolos/prproj/escrita.md` §11c). Use o `frame_count` do MediaInfo.

Ele às vezes conta um **frame de guarda**, preenchido com silêncio, e às vezes não —
`00;12;12 Piano e Cordas.wav` tem 32,000 s exatos (768 frames a 24) e o master declara
**769**. Perseguir a regra seria adivinhar.

⭐ **A saída é não precisar da fórmula:** num relink sabe-se o maior `start + length` que a
timeline pede de cada master, e o master é autorado com **pelo menos** isso. Não muda
**nenhum frame da edição** — start, duração e conteúdo de cada corte ficam idênticos; muda
só a duração DECLARADA do master, que passa a valer o que o master offline já declarava,
contra o qual o editor cortou.

⚠️⚠️ **A ORDEM não é a intuitiva:** medir só faz sentido **depois de achatar**, porque é o
achatamento que fixa o `start` final (`S + s`). Medir antes subestima e o master nasce
curto do mesmo jeito.

⛔ **NÃO se corrige recuando o `start_time` do clipe.** Isso não move o clipe no tempo,
mas troca **quais** frames entram — no áudio, joga aquele trecho 1 frame fora de sincronia
com o resto. Descaracteriza a edição, e foi vetado pelo usuário com razão.

⚠️ **Com trava:** diferença de **1–2 frames** é o arredondamento do Avid e se preenche;
acima disso o arquivo é **outro** (take errado, versão diferente) e a resposta certa é
**recusar aquele master e contar**, não preencher silêncio para esconder erro de acervo.

⚠️ **PENDÊNCIAS** — (a) `clone_generic` deriva o `edit_rate` do **template** (os 8
embarcados têm 23,976 gravado), não do projeto; num projeto a 25 ou 29,97 sai errado em
silêncio (o `clone_offline`, ao lado, já aceita `fps` do chamador — *"preferir sempre"*).
(b) O patch do start é travado por `AVB_AUDIO_TC=1`, com motivo legítimo (*proxies
re-carimbados têm TC ≠ do original*) — precisa virar decisão explícita, não variável de
ambiente. (c) Resíduo cosmético do template nas colunas `TapeID`/`Scene`.

### Modelo novo a partir de bin do WINDOWS: o locator é `WINF`, não `FILE` (2026-10-13, MC 25.6) — `confirmado` na leitura; injeção `pendente` no MC

Os modelos de áudio embarcados vieram de bins do Mac. A bin do Windows (WAV float 32 estéreo linkado pelo MC 25.6) tem a
mesma cadeia (master → mob do arquivo `MediaDescriptor` → mob `PCMADescriptor`), mas o locator do arquivo é outro chunk:

```
FILE (Mac)    : 02 02 | u16 0 "" | 01 01 4C u16 posix(macroman) | 01 02 4C u16 (00 00 + utf8) | 03
WINF (Windows): 02 02 | u16 n caminho "G//A/B/x.wav" | 01 02 4C u16 (00 00 + utf8) | 03
```

O `relink.relink` e o `clone_generic` só conhecem o `FILE` (procuram `path_posix`): com um modelo `WINF` o clone
manteria o caminho do modelo, CALADO. Remédio do De Lá Pra Cá (`tools/neutralizar_modelo_audio.py`): reescrever o chunk
como `FILE` com caminho neutro — os objetos da bin se acham pelo ÍNDICE, então trocar classe e tamanho do chunk é seguro
(a bin abre inteira no pyavb). O nome do arquivo aparece em 6 enquadramentos (u16, u32, com prefixo `00 00`, `fd ff`);
trocado por um nome neutro do MESMO tamanho, nenhum campo precisa de correção. Golden do clone (WAV real) × bin do MC:
formato, taxa, samples, `_AMD_SOURCE_LENGTH`, `_AMA_FILE_DATE_TIME` e caminho `G//…` iguais. ⏳ Falta ver online no MC.

---

## ⭐⭐ RELINK PELA BIN, sem AAF: CONFIRMADO no MC (2026-08-16)

Uma timeline offline volta a ficar **online, sem subclipes e com os efeitos intactos**,
editando a `.avb` do editor — **sem `ExportFile`, sem preset de export e sem
`ImportFile`**. Validado na tela por um editor (MC 25.6.0.58781, Windows 11; curta real:
timeline de 26'28", 1118 clipes, 877 SourceClips, 83 mobs referenciados, 44 subclipes,
80 masters; originais **BRAW** + WAV de som direto).

```
1. resave da bin do editor com Bin.uid NOVO          → bin de trabalho
2. OpenBin (o MC precisa conhecê-la para aceitá-la como destino)
3. LinkFile dos originais COM destination_bin = a bin de trabalho
4. DoCommand(1004 Save)
5. ler do disco: ACHATAR os subclipes, DEPOIS repontar os masters
6. resave com OUTRO Bin.uid novo                     → bin final
7. OpenBin
```

**Três condições, e cada uma foi um fracasso antes de virar regra:**

1. ⭐ **`Bin.uid` novo em toda gravação.** Sem isso, `FILE_OPEN_FAILURE` — ver a correção
   logo abaixo.
2. ⭐⭐ **Os masters AMA e a timeline têm de ficar na MESMA bin.** A 1ª tentativa deixou os
   masters numa bin e a composição repontada noutra, contando que o MC resolvesse pelo
   MobID no banco de mídia: **timeline 100% offline**, com o `LinkFile` reportando 44/44
   online e o `OpenBin` reportando OK. Isso vale para mídia **gerenciada**; num master
   **AMA** o caminho do arquivo mora na própria bin.
3. ⭐⭐ **Achatar os subclipes é OBRIGATÓRIO, e não só por causa do diálogo de conflito.**
   Repontar o master **dentro** do subclipe não basta: 60 SourceClips passaram a apontar
   para masters AMA comprovadamente online (o editor via imagem no Source monitor) e a
   timeline **continuou vermelha**. Só depois de desfazer os subclipes — o `SourceClip` da
   timeline apontando direto para o MasterMob — o vídeo veio online.

**O achatamento em AVB** (porte de `_DeLaPraCa/motor/aaf/denest.py`):

```
timeline: SourceClip → subclipe (track_id=T, start=S)
subclipe: track T    → SourceClip → master (track_id=t, start=s)
resultado: SourceClip → master, track_id=t, start = S + s
```

⭐ **Contagem cruzada como prova de porte:** o AVB deu **738 achatados / 44 subclipes**,
exatamente o mesmo que a rota AAF registra para a mesma timeline. Dois caminhos
independentes, o mesmo número.

⚠️⚠️ **`track_id` sozinho NÃO identifica a track do mob.** Um mob tem `index=1` de imagem
**e** `index=1` de som (medido: o subclipe `04-02-01` tem picture idx=1, sound idx=1 e
sound idx=2). Casar só pelo índice põe um SourceClip de SOM na track de IMAGEM, sem erro
nenhum. Case por `index` **+** `media_kind`, com o `media_kind` como desempate.

⭐⭐ **TODA BIN DO AVID É UM BANCO AUTOSSUFICIENTE** (ensinado pelo usuário, 2026-08-16, e
confirmado na leitura). Basta a timeline existir na bin para que **tudo que ela referencia
viva ali dentro**, oculto — visível em *Set Bin Display → mostrar itens referenciados*.
Arraste uma timeline para uma bin nova e as mídias vão junto; não é preciso ter as bins de
origem abertas. **Consequência para quem depura:** abrir ou fechar bin **não muda
resolução de mob nenhuma**. Uma hipótese de "o MC está resolvendo o subclipe por uma cópia
velha noutra bin aberta" é impossível — e o dado que a refutava estava no primeiro recon
(os 44 subclipes estavam entre os 648 mobs da própria bin). É também o que explica a
"bin com só a timeline" e o `Find in Bin` levando ao clipe na bin de origem.

**Escopo validado: ✅ CICLO COMPLETO — vídeo E áudio, na tela, sem nenhum diálogo**
(MC 25.6/Windows, 2026-08-16). 44 BRAW pelo `LinkFile` + 36 WAVs **autorados** + 738
subclipes achatados + 738 SourceClips repontados, tudo numa bin só, **sem
`PMM_INSUFFICIENT_MEDIA`** depois da correção da duração declarada do master (§ acima).
Drone (`.mov`/`.mp4`) não testado: a instalação de MC usada tem defeito de AMA para mp4.

⭐ **Levado a produto** no `_DeLaPraCa` (`motor/avb_bin/`, `servico/relink_avb.py`), com
165 casos de regressão que **não precisam do NLE aberto** — o percurso, o achatamento, o
repontamento, as conversões do áudio e a ordem "achatar antes de medir" estão travados.

⚠️ **Custo medido:** `LinkFile` para dentro de uma bin GRANDE custa **3887 ms** por arquivo
contra **454 ms** para uma bin vazia (171 s contra 20 s para os mesmos 44 BRAW) — 8,5×. O
MC parece reescrever a bin a cada link.

> ### ⚠️⚠️ CORRIGE (2026-08-17): o 8,5× NÃO se reproduz — e a medição original tinha viés
>
> Refeito com desenho balanceado (MC 25.6 / Windows 11, bin de origem de 1327 KB com a
> timeline inteira e 118 masters):
>
> ```
> bin VAZIA   352 ms/arquivo        bin GRANDE  359 ms/arquivo      →  1,02×
> ```
>
> **Praticamente idênticas.** Linkar numa bin vazia e mesclar depois **não compra nada**.
>
> ⭐ **O que a medição antiga provavelmente mediu foi CACHE, não tamanho de bin.** Uma
> primeira tentativa deste refazimento reproduziu o efeito ao contrário (a bin grande
> saindo 2× mais barata) — porque usava **os mesmos arquivos nas duas condições**, com a
> vazia primeiro: ela pagou a leitura fria (866 → 454 → 390 ms, aquecendo à vista) e a
> grande colheu o cache. Trocar a ordem inverte o "resultado".
>
> **O desenho que responde de verdade:** dois LOTES distintos de arquivos, e duas rodadas
> com os **papéis trocados** — assim cada condição pega um lote frio e um quente, e o
> viés se cancela. Sem isso, qualquer comparação entre duas leituras dos mesmos arquivos
> mede o cache do sistema operacional.
>
> ⭐⭐ Isto é a **terceira** vez que este banco registra a mesma armadilha em 24 h (a outra
> foi o cache de metadado do indexer, em `transversal/banco-de-midias-compartilhado.md`).
> **Em medição de I/O, a pergunta que vem antes de qualquer número é: o que estava quente
> quando eu medi?**
>
> ⭐ O que continua valendo da nota original: `LinkFile` custa **~350 ms por arquivo**, e
> esse é o piso — 44 BRAW são ~15 s. Quando o observado for muito acima disso, a causa
> está na LEITURA DA MÍDIA (arquivo frio, volume de rede), não no tamanho da bin.
>
> ⭐ E fica confirmado o outro lado: **um master criado pelo `LinkFile` SOBREVIVE à
> mescla para outra bin** (`serialize`/`materialize`), chegando com `_IMPORTED_AMA`
> presente — 3 de 3. O padrão que o áudio já usa vale para o vídeo; só não há motivo de
> desempenho para usá-lo.

⚠️ **Ao medir, nunca reescreva a bin de saída com o mesmo nome:** `OpenBin` numa bin já
aberta devolve `Completed` e **não relê o disco**; a rodada seguinte fica medindo a
anterior, e nada acusa.

---

## ⭐ CONFIRMADO (2026-09-11): acrescentar uma timeline numa bin ABERTA, com `CloseBin`

**Confiança:** `confirmado` · **Medido em:** Media Composer **2025.6.58781** / Windows 11,
projeto `_ASSIST ANTERIOR`, bin `CENAS/C07.avb` com 10 subclipes sincronizados ABERTA na
interface · **Por:** Ciclo Assist (`mcp/ferramentas/corte.py`)

A matriz de 2026-08-16 (abaixo) dizia o que NÃO fazer com a bin aberta. Faltava o caminho
que FUNCIONA, e ele é uma dança de três passos:

```
1. CloseBin (rpc)   →  o MC SALVA a bin e larga o arquivo
2. pyavb            →  abrir, montar a timeline nova, escrever AO LADO, fechar o handle,
                       os.replace  —  com o Bin.uid PRESERVADO
3. OpenBin (rpc)    →  o MC relê do disco e mostra o conteúdo antigo + o novo
```

**Resultado medido:** bin com uma timeline → duas; e, no teste de produto, a bin da cena
com 10 subclipes passou a enumerar 11 itens, **sem perder nada do que estava lá**. O
`GetListOfBinItems` depois do `OpenBin` lista o antigo e o novo.

⭐⭐ **O UID é PRESERVADO aqui, e isso é o oposto da regra do resave.** A regra "todo
`.avb` gerado randomiza o `Bin.uid`" vale para bin NOVA derivada de outra. Ao ATUALIZAR a
bin do editor, randomizar faria o MC tratá-la como bin distinta (sintoma conhecido: ele
renomeia o conteúdo para `….AutoCopy.NN`) — e o editor ganharia uma segunda bin em vez da
dele atualizada.

| o que se quer | UID | a bin precisa estar |
|---|---|---|
| bin NOVA a partir de outra | randomizar | tanto faz |
| ATUALIZAR a bin existente | **preservar** | **fechada** (use `CloseBin` antes) |

⚠️ **Não existe "refresh" de bin.** `OpenBin` numa bin **já aberta** devolve `Completed` e
**não relê o disco** (já registrado abaixo). Sem o `CloseBin`, escrever no arquivo não
muda a tela — e, pior, o MC salva por cima quando ele mesmo fechar a bin, desfazendo a
escrita **sem erro nenhum**.

⚠️ `CloseBin` é **operação de arquivo**: teto de dezenas de segundos, nunca o prazo de
consulta (ver `plugins/avid-panel-sdk/README.md`). `CloseBin` numa bin que já está fechada
devolve erro — é o caso normal, e quem chama deve ignorá-lo.

⚠️ Depois do `CloseBin`, o arquivo cresce: o MC grava na bin os mobs de mídia que ele
tinha em memória (na medição, 1 mob nomeado → 15). O `GetListOfBinItems` continua
enumerando só o que o editor vê.

---

## ⚠️⚠️ CORRIGE (2026-08-16): o `FILE_OPEN_FAILURE` NÃO é do writer — é do `Bin.uid`

**O fato abaixo estava `confirmado` e a ATRIBUIÇÃO está errada.** O resave cru do pyavb
**é aceito** pelo Media Composer. O que ele recusa é uma segunda bin com o **mesmo
`Bin.uid`** de uma bin já aberta na sessão — o problema clássico de troca de bins entre
editores, não um defeito do writer.

**Por que a leitura antiga enganava:** o experimento de 2026-08-08 mudou **duas
variáveis ao mesmo tempo**. O resave cru preserva o `Bin.uid` da origem; o `build_avb`,
que funcionava, **randomiza** (`f.content.uid = random.getrandbits(63)`). As duas causas
explicam o mesmo resultado, e a conclusão creditou ao writer o que era da identidade.
⭐ O aviso já estava neste mesmo arquivo, duas seções acima (§"randomizar o UID … senão o
MC a confunde com a de origem e **não abre as duas juntas**") — dois fatos do banco se
contradiziam sem que ninguém cruzasse.

**Matriz que separa as causas** (MC **25.6.0.58781**, Windows 11, `_DeLaPraCa`,
2026-08-16; bin real de 1,9 MB / 648 mobs / 119 masterclips + 1 sequence):

| | bin original ABERTA | bin original FECHADA |
|---|---|---|
| **UID preservado** | ❌ `FILE_OPEN_FAILURE` | ✅ abre |
| **UID randomizado** | ✅ abre | ✅ abre |

Três das quatro abrem, e o MC enumera o conteúdo completo (119 masterclips + 1 sequence)
nos dois arquivos gerados.

⭐ **A prova decisiva:** com o resave de mesmo UID aberto, **a bin ORIGINAL passou a ser
recusada** com o mesmo `FILE_OPEN_FAILURE` — o arquivo que o próprio Media Composer
escreveu. A recusa acompanha a **identidade**, não o arquivo. (Sinal correlato: o MC
renomeia a sequence da bin de UID novo para `….AutoCopy.NN`, isto é, ele a tratou como
bin distinta.)

**Consequência — o que volta a ser possível:** editar uma bin existente e regravar. O
"não dá para editar in-place" desta seção **cai**, e com ele a conclusão derivada de que
duplicar uma timeline e trocar o áudio exigiria re-autorar via `build_avb` (com Matte
Key/Titler dropando). **Regra prática: todo `.avb` gerado randomiza o `Bin.uid` — sempre,
inclusive num resave que não muda mais nada.**

**Validado em relink real** (mesma sessão): timeline offline de AAF (877 SourceClips → 83
subclipes → 80 MasterMobs), `LinkFile` de 44 BRAW originais (44/44 online, 454 ms cada),
patch dos MobID **dentro dos subclipes**, resave com UID novo → `OpenBin` aceito. ⚠️ O
patch desce até o MasterMob: trocar o MobID do **subclipe** é o erro silencioso conhecido.

⚠️ **Armadilha de biblioteca, medida no mesmo dia:** **no pyavb NÃO existe classe
`MasterMob`** — todo mob é `Composition`, e quem distingue é o atributo **`mob_type`**
(nesta bin: SourceMob 484, MasterMob 119, CompositionMob 45). No pyaaf2 são classes
distintas e `type(m).__name__ == "MasterMob"` funciona; portar o teste devolve **zero
masters sem erro nenhum** — a varredura roda inteira e reporta `0/0 casados`, como se o
acervo estivesse vazio.

⚠️ **Ao medir isto, não reescreva a bin de saída com o mesmo nome:** `OpenBin` numa bin
**já aberta** devolve `Completed` e **não relê o disco**. A segunda rodada fica medindo a
primeira, e nada acusa.

O texto original fica abaixo, como estava, porque a **observação** (resave cru recusado
naquela sessão) é verdadeira — o que estava errado é a causa atribuída a ela.

---

## GOTCHA: pyavb `f.write()` cru é rejeitado pelo MC 25.12 (FILE_OPEN_FAILURE) — 2026-08-08

**Achado (reproduzível, MC 25.12.0.58863):** um **resave cru** de uma `.avb` do próprio MC via pyavb
(`f=avb.open(bin); f.write(out)`, sem modificação) gera arquivo que o **MC recusa abrir**
(`OpenBin -> ErrorMessage "FILE_OPEN_FAILURE"`). O pyavb RELÊ o próprio output sem erro; o tamanho é
idêntico ao original — mas o MC rejeita. Testado com 2 bins diferentes (uma simples só com 1 master
WAV, uma complexa com Matte Keys): ambas falham no resave cru.

**Mas o caminho do `build_avb`/`_emit` FUNCIONA:** abrir a mesma bin, ADICIONAR um CompositionMob
fresco via `_emit` e `f.write(out)` → o MC ABRE normalmente (confirmado: `BUILDAVB_TEST.avb` da
`bounce.avb`, e o `MINIMO_RELINK.avb` do relink). O output do build_avb é ~maior (comp novo).

**Implicação:** NÃO dá para "editar uma bin existente e regravar" (ex.: duplicar timeline e trocar
áudio in-place) — o resave é recusado. Autoria só é aceita pelo caminho que **constrói um comp novo**
(build_avb). Consequência direta no experimento do "bounce" (painel de sonorização): copiar o vídeo
VERBATIM regravando a bin é inviável; teria de RE-AUTORAR o vídeo via segmentos (build_avb), o que
reintroduz a dependência de parsear a timeline + cobrir efeitos (Matte Key/Titler ainda dropados).

~~**A investigar (sessão dedicada):** por que o resave cru é rejeitado e o comp-novo é aceito — diff
byte/estrutura entre um output aceito (build_avb) e um recusado (resave). Provável: o MC 25.12 espera
algo no header/TOC/ordem que o writer do pyavb só produz corretamente quando há autoria via _emit, OU
o formato de bin do 25.12 divergiu do que o pyavb reproduz no passthrough. Chave para destravar
qualquer edição in-place de bins.~~

✅ **RESPONDIDO em 2026-08-16 — e nenhuma das duas hipóteses estava certa.** Não é header, TOC nem
divergência de formato: é o **`Bin.uid`**. O `build_avb` era aceito porque randomiza o UID; o resave
cru era recusado porque o preserva. Ver a correção no topo desta seção. ⭐ **Lição de método:** as
duas hipóteses levantadas aqui eram sobre o *arquivo*, e a causa era sobre a *sessão* — a variável que
ninguém listou foi a que decidiu. Antes de investigar um formato, pergunte o que mais mudou junto.

## Bin com SÓ A TIMELINE: os masters ficam nas bins do editor (confirmado no MC 2026-08-08)

O oposto da "bin única" acima, e a forma certa quando o editor **já tem o projeto**: a `.avb`
entregue contém **um único mob — a `CompositionMob`**. Nenhum master, nenhum SourceMob.

**Funciona, e é o que o fluxo de plugin quer.** O Avid resolve `SourceClip → mídia` pelo **MobID no
banco de mídia** (`msmMMOB.mdb`), não pela bin. Validado por um editor na GUI: a timeline abre
**online e tocando**, e um `Find in Bin` a partir dela leva ao clipe **na bin original dele** — que
é o comportamento esperado por quem trabalha no Avid.

Tamanho, no mesmo material (13 câmeras + som): **6 KB** contra **212 KB** da bin autossuficiente.

### ⚠️⚠️ A rede anti-"leak" APAGA a timeline neste modo

Um writer que troca `SourceClip` de mob AUSENTE por `Filler` — defesa correta quando a bin deveria
ser autossuficiente — **destrói a timeline inteira aqui**, onde o master está ausente por
definição. Observado: 15 clipes viraram buraco e a função reportou **sucesso**, com o número de
"leaks preenchidos" igual à contagem de clipes. A timeline abre vazia, sem erro nenhum.

**Regra:** modo autossuficiente e modo só-timeline precisam de checagens OPOSTAS. No segundo,
master fora da bin é o esperado; o que é erro é um clipe **sem MobID resolvido** — e isso tem de
falhar ANTES de escrever.

### `track_id` do SourceClip de som = o CANAL dentro do master (1-based)

Um mapa de canais derivado de um AAF não existe quando a origem **não é um AAF** (ex.: um app que
sincroniza arquivos e autora a composição direto). Um fallback que decrementa o slot colapsa o
**canal 2 no 1**: um estéreo toca o canal 1 nas DUAS trilhas, e uma câmera de 4 canais sai
`1,1,2,3` — o canal 4 nunca é ouvido.

⚠️ **Isso não se pega de ouvido.** Passou por uma validação humana. O que revelou foi um material
com **canais MUDOS**: a câmera tinha som em 1-2 e silêncio digital (−91 dB) em 3-4, e o padrão de
silêncio na timeline **discrimina** o mapeamento certo do errado (2 trilhas com som contra 3).
→ *Quando o teste de ouvido não distingue, procurar um canal mudo: a ausência é mais fácil de
verificar que a diferença.*

### O clamp do OUT não é caso de borda

O arquivo ORIGINAL costuma ser **1 frame mais longo** que o transcode do Avid (medido: `.mov` de
1237 frames → master de 1236). Um `SourceClip` que passe do fim do master faz o MC recusar a
timeline com **`PMM_INSUFFICIENT_MEDIA`**, num diálogo modal. Numa diária real, 5 de 14 masters
estouravam por exatamente 1 frame.

A duração do master vem do `GetMobInfo` da API (`Frame Count Duration`) ou, para OP-Atom, do
próprio arquivo. ⚠️ **Master de ÁUDIO OP-Atom não traz duração de vídeo** — quem depender só do
arquivo fica sem clamp justamente no som.

---

## ⭐⭐ Timeline que referencia SUBCLIPE: o que resolve pelo banco de mídia e o que não (confirmado no MC 25.6, 2026-08-30)

**Corrige e completa a seção *"Bin com SÓ A TIMELINE"* acima.** Lá está escrito que uma `.avb`
com **um único mob** funciona, porque o Avid resolve `SourceClip → mídia` pelo MobID no banco de
mídia (`msmMMOB.mdb`). Isso é verdade — **para `SourceClip` que aponta MASTER**.

⛔ **Não vale para `SourceClip` que aponta SUBCLIPE.** Um subclipe é uma `CompositionMob`
(`usage_code=2`): objeto de **bin**, não de mídia. Ele não está no `msmMMOB.mdb`, e não há por
onde resolvê-lo fora da bin. Entregando uma `.avb` só com as timelines, cujos `SourceClip`
apontam subclipes de outra bin, o Media Composer **derruba**:

```
Exception: Structured Exception, ExceptionCode:3221225477,
ExceptionString:ACCESS_VIOLATION, FaultAddress:0000000001DEA4CC
```

`3221225477` = `0xC0000005`. A bin **abre** e lista as timelines com as durações corretas; o
crash é ao **carregar** uma delas. Medido em `_ASSIST ANTERIOR`, 2026-08-30: bin de 64 KB com 7
timelines apontando 14 subclipes de uma bin de cena.

**A regra:**

| o `SourceClip` aponta | resolve fora da bin? | por quê |
|---|---|---|
| **MasterMob** | ✅ sim | está no `msmMMOB.mdb` — é mídia |
| **CompositionMob (subclipe)** | ⛔ **não** | é objeto de bin; não há registro de mídia para ele |

### As duas saídas, e a que o Órbita escolheu

**(a) Achatar para o master.** `SourceClip → master`, com `start = S + s` — a conta que
`avb_bin/denest.py` já faz. Aí a bin pode ser só a `CompositionMob` (6 KB), como a seção
anterior descreve. ⚠️ Custo: `matchframe`/`reveal` levam ao **master**, não ao subclipe.

**(b) Levar os mobs, INVISÍVEIS.** É o que o Órbita faz. Medido na `SYNC.avb` que ele escreveu:

```
299 itens no conteúdo da bin · user_placed=True em apenas UM (a sequência)
50 MasterMob + 248 SourceMob viajam ocultos · 549 KB
```

⭐⭐ **Não é o que a bin CONTÉM, é o que ela MOSTRA.** `f.content.add_mob(m)` devolve o item; o
campo é `item.user_placed`. Com `False`, o mob está na bin para a referência resolver e **não
aparece** na janela.

### ⭐ Por que ocultar é o comportamento CERTO, e não só cosmética

Toda bin do Media Composer é um **banco de dados independente**. Quando o editor dá `matchframe`
ou `reveal file` a partir da timeline, o Avid mostra o arquivo **na bin em que ele NÃO está
oculto** — ou seja, na bin de ORIGEM, onde o editor o organizou. Se o clipe estivesse visível
também na bin de edição, a navegação pararia ali.

→ *Ocultar o material que viaja junto é o que faz a navegação apontar para o lugar certo.*

### ✅ A saída (b) VALIDADA em produção — 2026-08-31, Assist anterior (`confirmado`)

O editor abriu no Media Composer uma bin de decupagem escrita por este caminho e **ela
funcionou**: as 6 timelines carregam, tocam, o `matchframe` volta à bin de origem e a V1
monitora. Medido depois, na bin entregue:

```
6 timelines de fala referenciam 14 SUBCLIPES
os 14 estão DENTRO da bin, ocultos, entre 188 itens
```

⭐ É a confirmação que faltava: a mitigação **(b)** não é só teoria — uma bin cujas timelines
referenciam **subclipes** (não masters) abre e reproduz, desde que os subclipes viajem junto e
invisíveis.

⚠️⚠️ **E a armadilha de processo que veio junto:** no mesmo app, a flag que traz os mobs era
**opcional**, e a suíte de teste de material real rodava **sem ela**, de propósito. Ou seja: o
que a suíte exercitava **não era** o que o editor abria. Um caminho que só existe em produção
não é um caminho testado — e o modo de falha dele é `ACCESS_VIOLATION` na mão do editor.

⇒ *Se o modo autossuficiente é o único que se pode entregar, ele não deve ser uma opção.*

### Onde isto foi implementado

`_ASSIST ANTERIOR/assist_anterior/modulos/assistir/emissor.py` — depois de montar as timelines:

```python
for item_da_bin in f.content.items:
    item_da_bin.user_placed = (str(item_da_bin.mob.mob_id) in emitidas)
```

Medido: 208 itens, **23 visíveis → 7 visíveis** (só as timelines emitidas).

---

## ⛔⛔ Toda track de `Sequence` tem de TERMINAR em `Filler` (confirmado no MC 25.6, 2026-08-29)

São **duas invariantes diferentes**, e confundi-las custa a bin inteira.

**A de DURAÇÃO** — toda track abrange o comprimento total do comp. Falhar aqui dá
`PMM_INSUFFICIENT_MEDIA` + assertion `GetVideoFrameOffset < GetGlobalDuration`, ao navegar além
do fim da track. Já registrada acima.

**A ESTRUTURAL** — o **último componente da lista** tem de ser literalmente um `Filler`, tenha a
soma fechado ou não:

```
Assertion failed: CompIsFiller(last) || TT_SOUND_MASTER==GetType()
File: …\coresw\ame\src\CompMan\ASequence.c, Line: 1549
```

⚠️ **Não é redundante com a primeira.** Um writer cujas entradas já somem o total pode concluir
que o trail seria "um `Filler(0)` inútil" e removê-lo — e aí a soma fecha, a duração está certa,
e o Media Composer recusa **todas** as timelines da bin. Aconteceu: 7 de 7 não abriram.

⭐ `avb_export/translate.py` (DeLaPraCá/Relinker, em produção) empilha o trail
**incondicionalmente**:

```python
seq.components.append(_filler(f, max(0, total - tlen(tr)), tkind))
```

⭐⭐ **Confirmação independente:** uma sequência escrita pelo PRÓPRIO Media Composer termina toda
track em `Filler`. Verificável em qualquer `.avb` de sync do projeto.

---

## Monitor da track de imagem: `translate.py` deixa a V1 povoada DESLIGADA (confirmado, 2026-08-30)

`avb_export/translate.py::build()` escreve:

| track | `session_attr` |
|---|---|
| som | `_MONSTATE=2, _ENBLSTATE=1` |
| **imagem POVOADA** | `_ENBLSTATE=0, _MONSTATE=0` |
| V1 **vazia** (comp só-áudio) | `_ENBLSTATE=1, _MONSTATE=1` |

⚠️ Na prática isso inverte: a timeline que **tem** vídeo nasce com o vídeo desligado, e a que
**não tem** nasce ligada. O editor precisa ligar a V1 na mão para ver imagem.

`MONSTATE` aparece **num lugar só** no DeLaPraCá inteiro — não há segundo mecanismo. Para uma
timeline que o editor abre para CONFERIR, escrever `_ENBLSTATE=1, _MONSTATE=1` na track de
imagem povoada é o que entrega imagem sem clique. Feito em
`_ASSIST ANTERIOR/assist_anterior/modulos/assistir/sequencia.py`.

⚠️ **Confiança:** `inferido` quanto a ser o valor universalmente certo — foi validado num caso
(corte de cena, MC 25.6). O `0/0` do `translate.py` pode ser deliberado para o caso de relink,
onde a timeline entra num projeto que já tem monitoração configurada.

---

## ⭐⭐ EDITAR a timeline do editor preservando TUDO: extrair, inserir, abrir gap (confirmado no MC 25.6, 2026-09-13)

**Confiança:** `confirmado` — arquivo provado por impressão digital E conferido na tela pelo
editor · **Medido em:** MC **2025.6.58781** / Windows 11, pyavb **1.4.0** · **Por:** Ciclo
Assist (`cicloassist/avid/edicao.py`, `spikes/extrair_da_timeline.py`,
`spikes/inserir_na_timeline.py`, `spikes/ler_a_timeline.py`)

**A fixture:** `TL EDITADA`, trecho real do curta com efeitos acrescentados — 4.277 objetos:
38 `TransitionEffect`, 11 `TrackEffect`, 40 `PanVolumeEffect`, 4 `MotionEffect`, 14
`Selector` (group clip), keyframes em 51 `ParamClip` / 4 `ControlClip`, 33 `DIDPosition`.

**1. O portão: o pyavb aguenta uma timeline trabalhada?** Lê os 4.277 objetos sem falha, e
a regravação sai com o **mesmo tamanho (826.504 bytes), mesma contagem, zero órfãos e zero
diferenças reais** byte a byte, descontada a renumeração (4.979 pares do walk).

**2. O gesto, três operações, cada uma numa CÓPIA da sequência na mesma bin** (MobID novo;
a original intacta), com `CloseBin` → gravar → `OpenBin` → `LoadMobsIntoViewer(Record)`:

| operação | resultado na tela |
|---|---|
| **extrair** `[01:02:33:11, 01:02:54:03)` de TODAS as trilhas (o Extract do Avid com IN/OUT) | ✅ o `07-02-02` da V1 colou no `07-03-01`; sobraram os 16 frames do áudio em L do take tirado; efeitos, dissolves, volume intactos |
| **inserir** 48 frames de um subclipe **oculto na bin** — imagem na V2, som em A1–A5 — empurrando tudo | ✅ em sync; V1 ganhou buraco de 48 (a imagem foi para outra trilha) |
| **abrir gap** de 48 frames antes do último segmento, em todas as trilhas | ✅ |

**3. A prova — é ela que sustenta "100% do que não devia mudar continua igual":**

- **Impressão digital estrutural** de cada objeto (hash dos campos e dos filhos, por valor):
  compara o mesmo segmento em arquivos diferentes.
- ⛔⛔ **O memo da impressão tem de segurar o OBJETO.** Com `id(obj)` sozinho de chave, a
  prova acusou TODOS os mobs da bin como mudados: o pyavb solta objetos lidos (cache fraco) e
  relê sob demanda, e um objeto novo herda o `id` de um coletado.
- Em cada trilha: todo segmento que no original está **inteiro** antes ou depois do trecho
  aparece **idêntico** na cópia; só pode faltar um **vazio** (estendido ou colado); a cópia
  pode ter uma sobra de cada lado (o que cruzava a fronteira). ⛔ A primeira versão tolerava
  "um diferente de cada lado" e **aprovava um clipe alterado encostado na emenda**.
- Fora das trilhas: todo campo da sequência e de cada `Track` igual; os mobs da bin inteira
  com a mesma impressão; e a impressão do resultado em memória = a relida do disco.

**4. O que o formato ensinou no caminho:**

- ⛔ **Uma sequência pode ter VÁRIAS trilhas de timecode**: aqui três — `86400 @ 24`, `86400
  @ 24` e `90000 @ 25`. O início é a **primeira**, e o `start` conta na taxa DELA (`fps`).
  Pegar a última pôs todo timecode 2 min 30 s adiantado.
- **9 das 28 trilhas não são de mídia:** 3 `Timecode`, 5 `CaptureMask`, 1 `Edgecode`, um
  componente só do tamanho da sequência. Numa edição, só o `length` delas muda.
- ⚠️ `Sequence.length` é **calculado** no pyavb (soma dos componentes) e recusa atribuição;
  `Composition.length`, `Timecode.length` etc. são gravados.
- ⚠️ `Selector.components` é **método** no pyavb, não lista.
- A `TransitionEffect` **não soma** posição: ela se sobrepõe aos vizinhos, e a posição volta
  `length` frames.
- ⚠️ O Media Composer **guarda dois `Filler` vizinhos** (visto na A10 da fixture) — mas a
  edição não deve criá-los: estender o vazio que já está ali.
- ⭐ **Mob oculto é material:** o subclipe inserido só existia oculto na bin da timeline, e
  resolveu normalmente. Pela API (`GetListOfBinItems`) ele não aparece; pelo arquivo, sim.

**5. O que ainda é RECUSADO** (`EdicaoRecusada`, antes de mexer em qualquer trilha): trecho
no meio de um clipe (seria partir), transição encostando no corte, keyframe num segmento
aparado (a curva teria de ser remapeada), group clip no trecho, efeito que não envolve um
clipe só.

**6. Adendo, 2026-09-13 (tarde) — MC 2025.6.58781, pyavb, só arquivo:**

- ⭐ **Aplicar várias edições da última posição para a primeira dá o mesmo resultado que o
  Avid em sequência.** "Abrir espaço antes do `DJI_0312`" + "inserir 48 f na V2/A1–A5",
  com ambos os pontos na timeline ORIGINAL e aplicados em ordem decrescente, saiu com
  impressão digital idêntica, trilha a trilha, à sequência gravada em sequência e conferida
  na tela. Confiança: **confirmado** (comparação estrutural; a variante decrescente ainda não
  foi carregada no MC). No empate de posição, extrair antes de inserir.
- ⚠️ **`CaptureMask` (trilha de `media_kind` timecode) ENVOLVE um `Timecode` próprio**,
  noutra taxa (aqui `fps 25`, `start 90000`), com `length` na taxa dele. Uma extração de 496 f
  a 23,976 que muda só o `length` do `CaptureMask` deixa o de dentro em 8.536; na cópia da
  mesma extração que o editor carregou e o MC regravou, o de dentro está em **8.020**
  (−516 = 496 × 25/24). Confiança: **hipótese** — o MC recalcula o timecode aninhado ao
  salvar. A versão com o de dentro desatualizado abriu, carregou e tocou.
- ⛔ **Ponto de inserção: a transição pode vir DEPOIS, na lista, do vazio que contém o
  ponto.** Quem para de varrer a trilha ao achar o segmento que contém o ponto não vê a
  transição que se sobrepõe a ele (medido: um dissolve de 40 f na V3 da `TL EDITADA`).

- ✅ **Clipe comum na V2 (e acima), escrito do zero** (2026-10-12, MC 25.6 Windows, laboratório
  `lab/bancadas/avid.py::montar_camadas`): a trilha de cima é a MESMA forma da V1 do montador do
  Ciclo Assist — `Sequence[Filler 0, SourceClip(track_id 1 do master), Filler de rabo]`, `Track.index`
  2, `_ENBLSTATE=1 _MONSTATE=1`, inserida logo depois da V1 (ordem V1, V2, TC…). A sequência
  `LAB_ANIMATTE` (B14_FUNDO na V1, B14_FRENTE na V2, 144 f) apareceu na bin, carregou e mostrou a V2
  por cima. Não há como fazer isso pela API: o `DoCommand` não escolhe trilha de destino (patching).
  Confiança: **confirmado** (carregada e vista na tela; sem efeito, sem som).


## ⭐⭐ PREMIERE → AVID: os canais, "tudo mono", e a IDA E VOLTA (2026-11-25, MC 25.12 Mac + Premiere 26.0.2) — `confirmado`

Decisão do autor: **tudo MONO no Avid** (nada de trilha estéreo: o Avid não mistura mono e estéreo numa trilha, e o
estéreo numa trilha mono derruba o MC — B065). Medido com a mídia sintética do laboratório (B03 a 23,976, um tom por
canal), pela rota do Conformar (`prproj.leitura` → `do_prproj` → `translate.build_avb`), aberto no MC sem queda:
- Cada trilha do Premiere vira tantas trilhas MONO quanto o clipe mais largo dela: o estéreo → L e R em trilhas vizinhas;
  o mono na mesma trilha fica na 1ª (a 2ª vazia naquele trecho); o WAV de 5 canais → 5 trilhas, canais 1…5.
- ⛔⛔ **Três defeitos achados e consertados**: (1) o leitor do `.prproj` ignorava o `StreamNumber` (o "N Mono" é uma mídia
  por canal, todas com `ChannelIndex 0`): os 5 canais liam o 1; (2) o `translate._chan` aplicava a regra do AAF ("slot
  − 1", o slot 1 do AAF costuma ser vídeo/TC) a quem não vem de AAF — o R do estéreo tocava o L e os 5 canais saíam
  1, 1, 2, 3, 4 (agora, `origem="premiere"`: canal = a trilha de som do master); (3) o som que está NO caminho do
  projeto entrava OFFLINE (só o "fora do lugar" era aproveitado).
- **A ida e volta Avid → Premiere → Avid** dá a MESMA bin (trilhas, arquivos e canais): o par A1/A2 vira um estéreo na
  A1 do Premiere com a A2 vazia (o lugar do R); na volta, a trilha inteiramente vazia logo abaixo de uma trilha larga
  é esse lugar e não ganha outra (antes: +1 trilha por estéreo). Efeito no projeto NATIVO do Premiere: uma trilha vazia
  logo abaixo de um estéreo também é absorvida (vazia não tem conteúdo; só a numeração das de baixo sobe uma).
- ⛔ A leitura da BIN numera o som 1000 + trilha (A1 = 1000, a convenção do DRT); quem usava "≥ 1000" para achar a
  trilha de REFERÊNCIA (a montagem do Premiere) tratava todo o som de uma bin como referência e sumia com a trilha vazia
  — a referência é pela marca `referencia`, não pelo número.
Provas: `Ciclo Assist spikes/ida_e_volta_canais.py` (+ a bancada `tools/bancada_avid/e2e_prproj_avid.py`); teste
`modulos/conformar/tests/test_canais_ida_e_volta.py` (os `.prproj` em `3 CONJUNTOS…/conformar/04 SINTETICOS/CANAIS IDA E VOLTA`).

- ⭐ **MOV com mais de um fluxo de som (pares estéreo), 2026-11-25, MC 25.12 Mac** — `confirmado`: o master do link
  (AMA) do MOV de 2 pares tem as trilhas de som MONO 1…4 (2 pares + 1 mono: 1…5) — a trilha N do master é o canal N do
  arquivo, e o `CHANMAP {i: i}` da rota do Premiere vale. Dois consertos da rota (Conformar `do_prproj`/`media_bin`):
  (1) o MOV/MXF usado SÓ como som ia ao molde de WAV e entrava OFFLINE estando no disco — vai pelo LINK, como o vídeo;
  (2) o master OFFLINE de som era sempre o molde de 2 canais: a sequência que usa o canal 3+ de um som ausente dava
  "Sequence refers to non-existent track in clip" ao abrir — o molde agora tem trilhas para o maior canal usado (há
  moldes de 1 a 5, 8 e 16 canais a 24 bits; acima de 16, o de 16).
- ⭐ **Moldes de som de 8 e 16 canais, 2026-11-25, MC 25.12 Mac** — `confirmado`: o WAV BWF de 8 e o de 16 canais
  (lab `B03_LAYOUTS_DE_AUDIO`, PCM 24 bits) linkados pelo `LinkFile` numa bin do projeto de lab ("Audio Start-Time
  Options" respondido com a taxa do projeto, 23.98, e OK) dão o master com 8 e 16 trilhas mono e o PCMA (1, 24, 8/16);
  neutralizados pelo `main_mac` do `tools/neutralizar_modelo_audio.py` (locator `FILE` → `/AVB_TEMPLATES/…`, volume →
  `AVB-MEDIA`, projeto/bin/`_USER` pelo mesmo tamanho). Provado nas DUAS pontas da rota Premiere → Avid, numa sequência
  que usa os canais 1 e 8 e 1 e 16: **online** — os dois WAV injetados pelo molde (antes: `sem_template` → offline),
  3/3 masters online; **offline** — masters de 8 e 16 trilhas, a sequência abre sem "non-existent track". O molde de
  16 serve a qualquer som de 9 a 16 canais (o offline só precisa de trilhas BASTANTES).
- ⛔⛔ **`filler_proxy` é SÓ da trilha de IMAGEM — na de SOM, o vazio TOCA outra trilha** (2026-11-25, MC 25.12 Mac,
  `confirmado` de ouvido). O writer do Conformar (`translate.build`) punha em TODA trilha o `TrackRef(relative_scope 0,
  relative_track −1)` — o "vazio mostra a de baixo" do vídeo. O MC não grava `filler_proxy` em trilha de som (0 de 390
  trilhas de som nas bins reais dos conjuntos de teste). Com ele, no export (e na reprodução) o VAZIO de uma trilha de
  som tocava a trilha de índice menor, em cadeia: o tom saía 3×, 6×, 9× mais alto (uma cópia por trilha vazia) e, no
  MOV de pares de 5 canais, as trilhas do L tocavam o R (o canal 1 e o 3 sumiam) — com o proxy tirado, as 9 trilhas
  certas e a −23 dB cada. Os masters estavam certos o tempo todo (exportados sozinhos, trilha a trilha). Método de
  OUVIR no MC (o export do preset do lab sai como a MISTURA em 2 trilhas mono iguais; uma trilha por vez = cópia da bin
  com só ela em `_ENBLSTATE 1`, o preset com `iUseEnabledTracks`): Ciclo Assist `spikes/ouvido_mc/`.
