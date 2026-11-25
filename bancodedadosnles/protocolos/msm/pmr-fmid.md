# msmFMID.pmr / amaFMID.pmr — índice File Media ID

> ⭐⭐ **ATUALIZAÇÃO 2026-08-22 — leia a última seção antes de agir por esta página.**
> O par LONG+SHORT foi decifrado: **o SHORT carrega o MobID do MASTER**, e com ele o
> `.pmr` RESOLVE master → arquivos sem abrir `.mxf` nenhum. A conclusão *"não basta"* mais
> abaixo vale só para quem precisa casar contra um NOME de câmera. ⚠ E não faça dele
> fundação: em storage de rede gerenciado ele não fica na pasta de mídia.

O `.pmr` (FMID = *File Media ID*) é o índice que liga cada **arquivo de essência** ao seu **MobID**,
**tape** e **timestamp**. Pequeno e de formato próprio (não Bento, não AObjDoc). Tudo
little-endian. Confiança: **confirmado para leitura** — parser genérico validado contra 4 amostras
heterogêneas (vídeo `.mxf` OP-Atom, `.wav`, `.aif`, `.mov` de pastas AMA), extraindo corretamente
MobID/UL + nome do tape + nome do arquivo em todos os casos (2026-07-08). Ainda **sem round-trip**
(gerar um `.pmr` do zero e o MC reconhecer). Fatos em [dados/pmr-record.json](dados/pmr-record.json).
Parser: [../../../eng-rev-bin-e-mdb/tools/pmr_read.py](../../../eng-rev-bin-e-mdb/tools/pmr_read.py).

Amostras: `ARQUIVOS PARA ANALISAR/1/msmFMID.pmr` (5 mídias, vídeo) e três `amaFMID.pmr` dentro de
`AMA Metadata Folders/` (áudio/vídeo AMA, tapes diferentes).

## Cabeçalho (12 bytes)

```
a9 07 00 00   magic/versão = 0x000007a9 (1961)
08 00 00 00   contador_a = 8     (papel exato a confirmar)
05 00 00 00   n_mídias  = 5      (bate com nº de .mxf únicos)
```

## Registro "longo" (com nome de arquivo) — REC0 byte a byte

```
06 0a 2b 34 01 01 01 05 01 01 0d 43   UL SMPTE de MobID Avid (material 0d 43)
13 00 00 00                           const = 0x13
af dd 26 65                           timestamp Unix LE = 0x6526ddaf (~out/2023)
25 04 00 00                           mob_instance (contador único do clip)
06 0e 2b 34 7f 7f 2a 80               label2 (2º UL Avid)
28 00                                 fname_len = 40
"PRODUCAO-A - 05-04 C11 P1-T002_A02.mxf"
0c 00                                 tape_len = 12
"PRODUCAO-A"
```

## Registro "curto" (intercalado)

Logo após o longo vem um registro sem strings: mesmo UL + `const 0x13` + timestamp + `mob_instance`
(ex.: `21 04 00 00`) + label2 + mais 4 bytes (`bb dd 26 65`, provável 2º timestamp). A leitura
mostra **pares longo+curto** por mídia — provavelmente o mob do arquivo e o mob fonte/físico
(análogo ao par MasterMob/SourceMob).

## Conexões importantes

- O **UL `06 0a 2b 34 ...`** e o MobID são os mesmos do AAF/MXF (ver [../mxf/README.md](../mxf/README.md)
  sobre UMID) e do `.avb` (ver [../avb/estruturas.md](../avb/estruturas.md)). É a chave de junção
  entre bin, banco de mídia e arquivo físico.
- `amaFMID.pmr` (dentro das AMA Metadata Folders) é, em tudo indica, **o mesmo formato** —
  confirmar em [ama-management.md](ama-management.md).

## Confirmado contra múltiplas amostras (2026-07-08)

Rodando um parser genérico (varre pares LONG/SHORT até bater `n_midias` do header, decidindo
LONG vs SHORT por heurística — "os 2 bytes em `fname_len` decodificam como um comprimento
plausível seguido de bytes ASCII imprimíveis?") contra 4 `.pmr` de origens bem diferentes:

- `msmMMOB`/vídeo Avid nativo (5 `.mxf`, tape `"PRODUCAO-A"`).
- `amaFMID` de áudio (`.wav`/`.aif`, 11 e 3 mídias, tape `"producao-a"` — note o hífen, difere do
  nativo).
- `amaFMID` de vídeo AMA (`.mov` do DJI/Panasonic, tape `"PORJETO LINK REPLICAR"` — inclui erro de
  digitação do usuário, prova que o tape é *texto livre*, não normalizado pelo MC).

Em todos: MobID (UL de 12 bytes) + nome do tape + nome do arquivo saem corretos. **Isso já resolve
a necessidade prática de leitura** (mapear reel/tape → arquivo físico) sem precisar decodificar o
`.mdb` (Bento) — ver [mdb-bento.md](mdb-bento.md) §Pendente sobre o tamanho desse esforço à parte.

Nuance nova: o campo que eu rotulava `const13` (4 bytes logo após o UL) **não é constante entre
LONG e SHORT** — no registro LONG ele mistura com o byte seguinte de forma diferente do SHORT
(nas amostras, LONG mostrou `0xb113`/`0x5010101` etc., SHORT mostrou `0x13` puro). Não travei a
semântica exata; o parser trata esse campo como opaco (só avança 4 bytes) porque não precisa dele
para extrair tape/fname. Ver código-fonte do parser para a heurística exata de LONG-vs-SHORT.

Achado novo: em pelo menos uma amostra (`msmFMID.pmr` de `ARQUIVOS PARA ANALISAR/1/`), depois dos
`n_midias` pares declarados no header, o arquivo **repete o mesmo conteúdo** (mesmos UL/fname/tape)
num bloco secundário prefixado por um mini-header `u32=16, u32=n_midias` — parece um índice/cópia
redundante. Não afeta a leitura do bloco principal; só ignorar o restante do arquivo após
`n_midias` pares é suficiente.

## ~~Não basta pra substituir a leitura de header MXF~~ (checado 2026-07-08 — **parcialmente SUPERADO**, ver a seção final)

Testei cruzado: comparei o que o `.pmr` diz sobre `1/PRODUCAO-A - 05-04 C11 P1-T002_A01.mxf`
contra o que `multicam_rebuild.mxf_inspect._read_mxf` lê de verdade do header desse mesmo arquivo
(projeto FLATFILE-MULTCAM, que faz exatamente esse tipo de resolução hoje via header MXF).

- `MaterialPackage.Name` real: `"PRODUCAO-A - 05-04 C11 P1-T002"`.
- `.pmr` `fname`: `"PRODUCAO-A - 05-04 C11 P1-T002_A01.mxf"` (nome físico, com sufixo de canal).
- `.pmr` `tape`: `"PRODUCAO-A"` (nome do reel/sessão — igual pra **todos** os arquivos do lote).

**Nenhum campo do `.pmr` equivale ao `MaterialPackage.Name`** que um resolver de câmera precisaria
pra casar contra um nome tipo `"CAM A"` — `tape` é grosso demais (não distingue câmeras do mesmo
lote) e `fname` carrega sufixos que a `Name` não tem.

Além disso, tentei reconstruir o UMID completo (32 bytes) a partir dos campos do `.pmr` e comparar
com o UMID real (`urn:smpte:umid:060a2b34.01010105.01010d43.13000000.6526ddaf.**04210000**.060e2b34.7f7f2a80`).
Os 12 bytes do label batem exatos, mas o grupo que eu rotulei `mob_instance` **não bateu byte a
byte** com o grupo correspondente do UMID real — indica desalinhamento não resolvido nesse trecho
do registro. Por isso: **não usar ainda** a reconstrução de MobID do `.pmr` como chave de
agrupamento vídeo+áudio (é o que `mxf_inspect` faz hoje via UMID real, de forma confiável).

**Conclusão prática:** o `.pmr` serve pra listar rápido "quais arquivos existem + nome do tape"
sem abrir cada MXF, mas **não substitui** a leitura de `MaterialPackage.Name` via header (que seguE
robusta, formato aberto, já funciona) — esse dado só mora no header do MXF ou no `.mdb` Bento
(não decodificado a fundo, ver [mdb-bento.md](mdb-bento.md)).

## Pendente

- Significado exato do campo de 4 bytes pós-UL (antes chamado `const13`) e de `header[1] = 8`.
- Fechar o alinhamento exato de `mob_instance`/`label2` (não bateu no teste cruzado acima).
- Confirmar a semântica do par longo/curto (file mob vs source mob) e do bloco secundário
  duplicado ao final do arquivo.
- Round-trip: gerar um `.pmr` e ver o MC reconhecer a mídia.

## ⭐⭐ RESOLVIDO (2026-08-22) — o SHORT é o MasterMob, e o grupo 6 são dois `u16`

`confirmado` contra 50 masters de uma diária real (projeto `ORBITA TESTE COM BASTANTE MIDIA`,
diária D02 de *PRODUCAO-A*, MC 25.6 / Windows 11), no DRAMASYNC/Órbita.

A seção acima deixou duas coisas em aberto e uma conclusão que **engana se lida fora do
contexto dela**. As três se resolvem juntas.

### 1. O par LONG+SHORT: quem é quem

O texto dizia *"provavelmente o mob do arquivo e o mob fonte/físico"*. Medido, é mais útil que
isso:

| registro | carrega |
|---|---|
| **LONG** | o mob **daquele ARQUIVO** (único por arquivo) + `fname` + `tape` |
| **SHORT** (logo em seguida) | o mob do **MASTER** — **o mesmo para todos os arquivos do clipe** |

A prova: os três arquivos de `a004_03170917_C003` (vídeo, `_A01`, `_A02`) têm `mob_instance`
**diferentes** no LONG (`471f`, `441f`, `461f`) e **idêntico** no SHORT (`431f`). E `431f0000`,
transformado como no item 2, é exatamente o MobID que o Media Composer reporta para aquele master
via `GetMobInfo`.

⭐ **Ou seja: o `.pmr` SIM resolve MobID-do-master → arquivos, sem abrir um `.mxf` sequer.**
Basta parear cada LONG (que tem o nome) com o SHORT seguinte (que tem o master).

### 2. A ordem de bytes que faltava

Cabeça de 32 bytes → hex na ordem do URN SMPTE, por grupos de 4:

| grupo | conteúdo | transformação |
|---|---|---|
| 1-4 | UL SMPTE (12 B) + `flags` | **crus** |
| 5 | timestamp | **`u32` little-endian** |
| 6 | `mob_instance` | ⭐ **dois `u16` little-endian** — não um `u32` |
| 7-8 | label2 | **crus** |

```python
g = [cab[i:i+4] for i in range(0, 32, 4)]
g[4] = g[4][::-1]                      # u32 LE
g[5] = g[5][1::-1] + g[5][3:1:-1]      # dois u16 LE
urn_hex = b"".join(g).hex()
```

### 3. Por que a tentativa de 2026-07-08 não bateu — e a prova está nos bytes desta própria página

A seção anterior comparou a reconstrução contra
`urn:...13000000.6526ddaf.**04210000**.060e2b34.7f7f2a80` e concluiu "desalinhamento não
resolvido". Eram **dois erros somados**, e o dump de REC0 publicado aqui em cima os denuncia:

- o REC0 (**LONG**) mostra `mob_instance = 25 04 00 00`, e o SHORT ao lado, `21 04 00 00`;
- pela regra do item 2, `21 04 00 00` → **`04210000`** — que é exatamente o grupo do UMID real
  contra o qual se comparava.

Ou seja: (a) comparava-se o **LONG** (mob do arquivo) contra o UMID do **master**, e (b) o grupo 6
estava sendo lido como `u32`. Corrigidos os dois, bate byte a byte. ⭐ **A resposta estava no dump
desta página desde julho** — faltava saber que os dois registros do par são mobs de níveis
diferentes.

### 4. A conclusão "não basta" continua válida — para a pergunta DELA

*"Nenhum campo do `.pmr` equivale ao `MaterialPackage.Name`"* segue verdadeiro, e quem precisa
casar contra um rótulo de câmera (`"CAM A"`) continua sem resposta aqui. **Mas quem já tem o
MobID do master** — qualquer app que leia a bin ou fale com a `mcapi` — não precisa de nome
nenhum, e para esse o `.pmr` resolve.

⚠️ Lição transferível: *"o índice não serve"* é sempre relativo à pergunta que se estava fazendo.
Vale registrar QUAL pergunta ficou sem resposta, senão a conclusão é reutilizada fora do escopo.

### 5. ⛔ Mas NÃO faça dele fundação — o ambiente de rede não o entrega

Medido pelo autor em produção (Emissora, 2026-08-22): **em storage gerenciado o `.pmr` e o `.mdb`
não ficam na pasta de mídia** como a documentação da Avid descreve — são geridos noutro lugar.
Um app que dependa deles não degrada, **falha**.

Some-se um limite estrutural: **cada `.pmr` indexa só a SUA pasta** (o de `0200230405` declara
`n = 198`, o número exato de arquivos daquela pasta). Num acervo espalhado é preciso achar e ler
todos, e um ausente ou desatualizado produz resultado **parcial e silencioso**.

⭐ **Desenho recomendado:** o `.pmr` entra como **ordenador da fila de candidatos**, e a
identidade é sempre confirmada pelo UMID lido do arquivo. Índice ausente, velho ou apontando para
arquivo que sumiu não quebra nada — a fila só fica pior ordenada. Mesma regra do
[`../../transversal/banco-de-midias-compartilhado.md`](../../transversal/banco-de-midias-compartilhado.md)
§7: **o cache é guia, nunca regra.**

⛔ **Medido de novo em 2026-11-24 (MC 25.12, Mac — o caso que custou):** a pasta `98_SFX - GRITOS - MOTO - BOZINA - LAB -
CHAVES` da PRODUCAO-A tem **84 MXF no disco e o `.pmr` dela lista 30** (55 de fora — ex.: lista o `_A02` de um efeito
e não o `_A01`). A `990123` idem. (CORRIGE 2026-11-24, mesma sessão: escrevi antes que o `.pmr` trazia identidades de
"versões antigas" — errado: o `…10ee…` que comparei é o do MASTER, e o `…10f1`/`…10f2` da bin são as ESSÊNCIAS de cada
canal; os dois batem com o `material_package_umid`/`file_package_umid` do MXF.) O MC mostra a timeline (`PRODA_CORTE.00.2`) **100% online** — ele lê os MXF —, e o
Conformar do Ciclo Assist, que usava o `.pmr` como fonte ÚNICA da mídia gerenciada, deixou **21 de 866 trechos offline**
(14 arquivos). Confiança: `confirmado` (contagem no disco × `pmr.ler`, e a leitura da bin). ⇒ quem monta a mídia
gerenciada tem de confirmar pelo UMID do MXF quando o `.pmr` não cobre a pasta — a regra deste §5.
✅ Feito no Conformar (`media/pmr.py::indice_de(completar=True)`): os `.mxf` da pasta que o `.pmr` não lista são lidos
pelo `ffprobe` (`file_package_umid` da essência, `material_package_umid` do master — tags de formato/stream). Medido:
`PRODA_CORTE.00.2` **866/866** online; 120 arquivos lidos do MXF, o índice inteiro em 0,8 s (era 0,4 s, só `.pmr`).

### 6. ⭐⭐ Ele revela mídia ESTACIONADA — e `MXF-<projeto>` NÃO deve ser varrida

Achado de brinde, e vale para **qualquer app que varra uma `Avid MediaFiles`**. O `.pmr`
reportou **396** arquivos para 50 masters onde a coluna `Tracks` do MC prevê **198**:

```
198 arquivos  E:\Avid MediaFiles\MXF0230405
198 arquivos  E:\Avid MediaFiles\MXF-producaoa-tbm0230405
```

Mesmos nomes, mesmos MobIDs, todos existindo. A primeira leitura foi *"mídia duplicada,
precisa de regra de desempate"* — **e estava errada.**

⭐⭐ **A explicação é de ofício, não de formato** (autor do Órbita, editor de Media
Composer, 2026-08-22): **o Avid só conhece `Avid MediaFiles/MXF` e `Avid MediaFiles/UME`**
(a segunda bem menos usada). Renomear `MXF` para `MXF-<PROJETO>` é a convenção com que
editores **guardam o material de um projeto para trabalhar noutro no mesmo disco** sem
misturar mídia, render e import — a pasta renomeada some para o Avid e volta a valer quando
é renomeada de volta para `MXF`.

Ou seja: **`MXF-<algo>` é mídia que o editor pôs OFFLINE de propósito.** Não há empate a
desempatar — há uma pasta que o MC enxerga e outra que ele não enxerga.

⛔ **Varrê-la é bug, e o mais silencioso possível: os MobIDs são os MESMOS nas duas
cópias.** O clipe "resolve", nada levanta erro, e o app entrega mídia que o Media Composer
trata como inexistente. Aconteceu no Órbita: um sync real saiu apontando para
`MXF-producaoa-tbm`, com 50/50 masters resolvidos e timeline montada — **o resultado
parecia certo**.

⭐ **Regra:** varra `<volume>/Avid MediaFiles/MXF` e `/UME` explicitamente. **Nunca** a base
com `rglob`. ⚠ E compare o nome da pasta **sem depender da caixa**: há disco em produção
com `Avid Mediafiles` (`f` minúsculo) enquanto a Avid documenta `Avid MediaFiles` — no
Windows e no exFAT não dói, num volume macOS sensível a maiúsculas some a mídia inteira.

Medido: 1984 → **1246** arquivos a varrer (**37% a menos**), e a varredura serial de ~106 s
para ~67 s **só por parar de ler o que não devia**.

⚠️ Sobra o caso menor e real: cópias entre as pastas NUMERADAS **de dentro** da `MXF`
(`MXF/1`, `MXF/2`) — essas são duplicatas de verdade, e aí sim vale "fica a primeira e
reporte as outras".

⭐ **Lição transferível:** um número estranho no acervo (396 ≠ 198) rendeu uma explicação
**plausível e errada**, porque os arquivos existiam mesmo, com os mesmos MobIDs. O que
faltava não era mais medição — era **saber como o ofício usa a ferramenta**. Antes de
escrever regra para um comportamento estranho do acervo, pergunte a quem monta se aquilo
tem nome.

### 7. Onde isto foi usado

Órbita/DRAMASYNC, 2026-08-22 — três estratégias medidas para ir de MobID → arquivos, num acervo
de 1984 `.mxf` em HD mecânico, alvo de 50 masters, **todas resolvendo 50/50**:

| estratégia | tempo | `ffprobe` |
|---|---|---|
| varredura completa (um `ffprobe` por arquivo do acervo) | 109,67 s | 1984 |
| filtro por nome (`Name`) + **parada antecipada** (`Tracks`) | 10,96 s | 198 |
| **índice `.pmr`** | **0,31 s** | 0 |

⭐ E a coluna **`Tracks`** do `GetMobInfo` (`V1 A1-2` → 3 arquivos; `A1-5` → 5) prevê o total
**exato** de arquivos a procurar — é o sinal de parada que torna a busca independente do tamanho
do acervo. Detalhe em
[`../../plugins/avid-panel-sdk/README.md`](../../plugins/avid-panel-sdk/README.md) §colunas.

### 8. ⭐ Segunda casa a usar, e o parser publicado aqui está INCOMPLETO (2026-09-02)

`confirmado` no **Assist anterior**, no mesmo acervo (*PRODUCAO-A*, `E:\Avid MediaFiles`), agora
do lado do painel dentro do Media Composer:

```
.pmr lidos: 12 · arquivos: 1404 · masters distintos: 358 · 0,56 s
28/28 UMIDs da bin CENAS/C07.avb resolvidos — zero ffprobe, zero .mxf aberto
```

⛔⛔ **O `tools/pmr_read.py` deste repositório só devolve os registros LONG** — e o LONG é o mob
do ARQUIVO. Quem usá-lo como está responde *"que arquivos existem"* e **não** *"de quem são"*:
o MobID do master está no **SHORT**, que o parser descarta no `else` (`off += 4`). Para resolver
master → arquivos é preciso **parear** cada LONG com o SHORT seguinte e aplicar a ordem de bytes
do §2 sobre a cabeça de 32 bytes do SHORT.

⚠️ A página dizia isso desde a atualização de 2026-08-22; o **código** não acompanhou. Quem
chegar pelo parser e não pela prosa reimplementa a metade errada — foi o que quase aconteceu.

⭐ E a guarda do §6 se paga sozinha: varrer só `Avid MediaFiles/MXF` e `/UME`, nunca a base com
`rglob`. No acervo medido isso é a diferença entre 12 `.pmr` úteis e um índice contaminado por
mídia que o editor pôs offline de propósito.

### 9. ⭐ TERCEIRA casa a usar, e as guardas §5 e §6 se PROVARAM em campo (2026-09-07)

`confirmado` no **Promo Entrega** (plugin do MC, Windows 11, MC 2025.6.58781), portando o
módulo do Assist anterior para a aba Bendito Field — que precisa do `.mxf` de **vídeo** de
cada corte para medir os campos.

```
27 .pmr lidos (3 volumes) · 365 masters · 4/4 MobIDs da bin resolvidos · 0,29 s · ZERO ffprobe
```

⭐ **A alternativa que ele substituiu está medida no mesmo disco:** `Avid MediaFiles` tem
**1404 `.mxf`** por volume e um `ffprobe` custa **40 ms** — **~56 s** para achar quatro
clipes, e **sem parada** quando um MobID não está lá (varre tudo e ainda assim não acha).

⭐⭐ **As duas guardas que a página descreve apareceram JUNTAS nesta máquina**, e nenhuma
era hipotética:

```
E:\Avid Mediafiles                       ← §6: "f" MINÚSCULO, exatamente o caso previsto
E:\Avid Mediafiles\MXF-producaoa-tbm   ← §6: a MESMA pasta do achado do Órbita, de pé
S:\Avid MediaFiles\MXF\1 - Mac-mini-…    ← §5: pasta de REDE, SEM .pmr
```

A primeira é a mais traiçoeira: no Windows o `glob` perdoa a caixa e o defeito não aparece,
mas quem comparar `== "Avid MediaFiles"` **perde o volume inteiro em silêncio** — e num
volume macOS sensível a maiúsculas some a mídia toda. A terceira é a prova de que o §5 não
é teórico: **num mesmo projeto convivem pastas com e sem índice**, então o fallback não é
zelo, é requisito.

⚠️ **A regra de ofício que decide a ORDEM dos ramos, dita pelo editor** (Lohan Costa, MC,
2026-09-07): ***"a mídia que vale é a gerenciada"***. Quando um clipe existe nas duas
formas, o `WinFileLocator` da bin aponta o **arquivo de ORIGEM do import** e o Media
Composer toca a **gerenciada** — medido lado a lado:

```
bin (WinFileLocator)  D:\MIDIAS DE TESTES\RABO DE VIDEO\ACERVO_CLIP_02….mxf
.pmr (gerenciada)     D:\Avid MediaFiles\MXF\BENTIDO-FIELD\V01.6A87F807….mxf   ← esta
```

⛔ **Para quem MEDE a essência (campo, loudness, cor), pegar o arquivo errado é um veredito
errado com aparência de certo:** se o original e o transcode diferirem em entrelaçamento, o
defeito aparece ou some sem que nada levante erro. Naquele material os dois deram o mesmo
número (`43,6 / 14,3` e `36,5 / 8,3`) — **sorte, não garantia**. Ordem correta:

    1. .pmr (gerenciada)  →  2. varredura dirigida (gerenciada)  →  3. locator da bin (AMA puro)

⭐ E um detalhe do consumo que não estava escrito: **um master tem 34 arquivos e só 2 são de
vídeo**. Quem quer imagem filtra `V*` **antes** de escolher — pegar `sorted(arquivos)[0]`
devolve um `A01…` e o ffmpeg mede nada com sucesso. Master sem `V*` não deve ser
"resolvido": cai para o ramo seguinte, senão a tela diz "não achei frame" quando o certo é
"este clipe não tem imagem".

### 10. ⭐⭐ O LONG é a ESSÊNCIA do arquivo — o `.mxf` EXATO de cada trilha (2026-09-24)

`confirmado` no **De Lá Pra Cá** (export para o Resolve), bin do curta *PRODUCAO-A* contra
`D:\Avid MediaFiles` desta máquina (12 `.pmr`, 1429 arquivos, **0,03 s**):

O filtro `V*` do §9 é CONVENÇÃO de nome e não serve ao áudio (qual `_A0n` é qual canal?). A
pergunta certa é *"qual arquivo é desta trilha"*, e o `.pmr` responde: **a cabeça do registro
LONG, com a mesma transformação de bytes do §2, é o MobID da ESSÊNCIA daquele arquivo** — o
mesmo `SourceMob` que a trilha do master aponta na bin (`master.tracks[i]` → `SourceClip.mob_id`).

```
B001_03150131_C011  picture 1 → B001_03150131_C011.mxf
                    sound   1 → B001_03150131_C011_A01.mxf
                    sound   2 → B001_03150131_C011_A02.mxf
290 de 290 trilhas do curta presentes no disco casaram (362 no total; o resto não está aqui)
```

Isto encerra a dúvida do §4/§3 ("não usar ainda o MobID do LONG como chave") **para esta
pergunta**: a chave LONG ↔ essência da bin é exata. Porte com o índice por arquivo:
`_DeLaPraCa/motor/media/pmr.py` (`ler_registros`, `Leitura.por_arquivo`).

⚠️ E o consumo que a medição exigiu: a `.mxf` de um canal é MONO — o clipe de som lê o canal
1 **dela**, não o canal N de um arquivo polifônico. E o TC de uma `.mxf` só de áudio mora nas
tags do **stream de áudio** (`11:42:00:00`), não no formato nem num stream de vídeo — quem pede
`-select_streams v:0` recebe vazio e o clipe cai em 00:00:00:00.

Resultado contra o DRT que o Resolve 19 montou do AAF da mesma timeline: vídeo 108/108 e o
som no MESMO take e TC em todos os 628 clipes que o nativo tinha online; os 140 que o nativo
deixou offline (música e efeitos fora da `Avid MediaFiles` daqui), o export também deixa.
