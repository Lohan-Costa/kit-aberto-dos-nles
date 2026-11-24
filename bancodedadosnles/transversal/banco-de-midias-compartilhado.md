# Banco de mídias compartilhado — cache de casamento entre apps e entre pessoas

> Como construir um índice de mídia que vive na rede, é alimentado por vários editores e
> acelera o relink sem nunca decidir errado. Medido no **De Lá Pra Cá** (MC 25.6 /
> Windows 11, 2026-08-16); as lições são de arquitetura e valem para RELINKER, Órbita e
> qualquer app que case timeline com acervo.

Este banco não tinha **nada** sobre índice compartilhado, escrita concorrente ou
invalidação de cache em rede. Esta página abre o tema.

---

## 1. ⚠️⚠️ A chave NÃO pode ser o `mob_id` — e o erro seria silencioso

`confirmado`, 2026-08-16.

A chave óbvia para "este master ↔ este arquivo" é o `mob_id` do master. **Ela nunca
acertaria na segunda vez.** Em mídia **AMA** o Avid casa por arquivo e o `mob_id` é
**gerado fresco a cada link** — medido: **83 de 118 masters ganharam `mob_id` novo**
depois de um relink (ver `protocolos/avb/escrita.md`). Como quase toda mídia de câmera
num fluxo moderno é AMA, o cache teria 0% de acerto **e nenhum erro visível**: só nunca
serviria para nada.

⭐ **A chave estável é o NOME NORMALIZADO do master** (sufixos do Avid removidos, caixa e
acento normalizados). Ele atravessa projetos e episódios, e é o critério que resolve o
acervo na prática — *dos 101 casamentos por nome de uma medição real, 100 foram exatos*.

`mob_id` e `material_package_umid` entram como pistas **secundárias**: valem para mídia
**gerenciada**, onde o UMID é a identidade de verdade.

### ⚠️ RESSALVA (2026-08-20) — depende de o ARQUIVO ter UMID

A regra acima continua valendo, mas o *porquê* era mais estreito do que parecia: o `mob_id`
não é "gerado fresco a cada link" **sempre** — ele é gerado quando o arquivo **não tem um
UMID para copiar**.

Medido num **MXF profissional** (Sony VENICE, ProRes 4444), linkando o mesmo arquivo por
**dois motores diferentes** do Avid (`MSP_MXF` e UME): os **três MobIDs saíram
byte-idênticos**, porque o Avid **copia os UMIDs de dentro do arquivo** em vez de gerar:

```
ffprobe  material_package_umid  →  MasterMob.mob_id
ffprobe  file_package_umid      →  SourceMob.mob_id
```

Ou seja:

| mídia | `mob_id` é… | serve de chave? |
|---|---|---|
| MXF profissional (Sony/ARRI/XDCAM… com UMID SMPTE) | **cópia do UMID do arquivo** | ✔ **sim, é estável** |
| BRAW, WAV, MOV/QuickTime, imagem | gerado no link | ✘ não |
| mídia gerenciada (Op-Atom) | o UMID do MSM | ✔ sim |

Os **83 de 118 que trocaram** eram, quase certamente, os do segundo grupo. Vale reconferir
naquela amostra: se os que trocaram forem os BRAW e os que ficaram forem os MXF, a regra
refinada explica os dois números de uma vez.

⭐ **O que muda na prática:** a chave primária continua sendo o **nome normalizado** — ela
cobre os dois grupos. Mas para acervo majoritariamente MXF de câmera, o `mob_id` deixa de
ser pista secundária e vira **desempate forte**, melhor que a duração. Detalhe e medição em
[../protocolos/mxf/dados/xocn-sony.json](../protocolos/mxf/dados/xocn-sony.json)
(`mobid_vem_do_arquivo`).

## 2. ⚠️ Nome colide — e o desempate é a DURAÇÃO

Cartão reaproveitado entre diárias, `Take 1.wav`, clipe reexportado noutra pasta. Um
cache que guarde **uma** entrada por nome deixa a última gravada apagar a anterior, e o
master legítimo do outro episódio herda o arquivo errado, calado.

**Guarde todas as entradas de um nome** e desempate por duração, **com a mesma régua que
o matcher já usa** — duas réguas para a mesma pergunta é o cache discordando da varredura
em silêncio. Ordem de severidade que funcionou:

1. **espécie** (áudio × vídeo) — grátis, corta o erro grosseiro;
2. **duração**, tri-estado: `True` aprova, `False` reprova, `None` é neutro. ⭐ Havendo
   algum candidato com prova (`True`), os neutros são descartados — palpite não compete
   com medição;
3. **revalidação 1:1** do arquivo: existe? `tamanho` e `mtime` batem?

⭐ **Sobrando mais de um, o cache tem de SE CALAR** (`ambiguo`) e deixar a varredura
decidir. Um acelerador que chuta deixa de ser acelerador.

⚠️ **A comparação de duração é diferente nos dois lados:**

| pergunta | compara | uma diferença significa |
|---|---|---|
| matcher: "é este o arquivo?" | master × **arquivo** | pode ser mídia consolidada — normal |
| cache: "é este o master?" | master × master guardado | é **outro master** — prova |

Por isso o cache usa régua **simétrica** e o matcher pode precisar da **assimétrica** (o
arquivo nunca mais curto que o master, mas podendo ser bem mais longo — a lógica do
`PMM_INSUFFICIENT_MEDIA`).

## 3. ⭐⭐ Como MEDIR o ganho — e por que a medição óbvia mente

`confirmado`, 2026-08-16. **Esta é a lição mais transferível da página.**

Primeira medição, as duas rodadas no mesmo processo: o cache saiu **15% mais LENTO**.
Segunda medição, cada rodada em processo novo: **21% mais rápido**.

A causa é o **cache de metadado em memória do indexer** (`_META_CACHE`, `path → (mtime,
size, metadata)`), que vive no PROCESSO:

```
index.meta  →  7957 ms na 1ª rodada   |   1 ms na 2ª   |   2 ms na 3ª
```

Como o sidecar/serviço é um processo longo, **o segundo relink da mesma sessão já era
rápido antes de qualquer cache persistente existir**.

⚠️ **"Rodei duas vezes e ficou mais rápido" NÃO mede o cache — mede o processo.** E se as
rodadas forem no mesmo processo, o cache persistente só **acrescenta** custo.

**O protocolo honesto:**

1. rodada de aquecimento descartada (o cache do SISTEMA DE ARQUIVOS fica quente para
   todos);
2. cada rodada num **processo novo** (o cache em memória nasce frio);
3. a rodada **sem** o cache por **último** — a posição mais favorável a ela;
4. conferir que o cache não resolveu **menos** que a varredura: ganho às custas de acerto
   não é ganho.

**Régua de expectativa** (acervo pequeno; a economia cresce com o número de arquivos,
porque o que se corta é metadado por arquivo, ~61 ms cada):

| situação | efeito |
|---|---|
| cache de metadado quente (relinks seguidos na mesma sessão) | o banco **custa** ~230 ms |
| cache frio (serviço reiniciado, outro dia, outra máquina, outro editor) | **economiza** ~580 ms de 2729 ms |

O caso frio é o do fluxo diário de novela/série. A troca é favorável — mas só depois de
saber qual dos dois se está medindo.

## 4. Escrita concorrente em pasta de rede, sem trava

`inferido do confirmado` (o padrão vem do `_PRODUCAO-V/decupador`, aqui aplicado e
exercitado).

Em SMB **lock não é confiável**. O desenho que dispensa trava:

```
<pasta do banco>/
  banco.json                      cabeçalho: esquema, produção, raízes
  fragmentos/<host>-<user>.jsonl  cada máquina escreve SÓ o seu (append-only)
  mapa.json                       consolidado de leitura, regravado a partir deles
```

- **Um escritor por arquivo** — ninguém escreve no arquivo de outra máquina, então não há
  o que travar. A leitura junta tudo, e o **carimbo mais novo vence**.
- **Leitura defensiva** — linha de JSONL que não parseia é **pulada**: a última pode estar
  sendo escrita neste instante, e um fragmento vindo da rede é entrada não confiável.
- **Consolidar NUNCA apaga fragmento.** Se a troca falhar, nada se perde; o pior caso é o
  consolidado ficar velho, e ele é só um atalho.
- ⚠️ **`os.replace` só é atômico dentro do mesmo volume** — o temporário vai na pasta do
  banco, nunca na pasta de trabalho do app (que pode estar noutro disco). Nome do
  temporário com o **PID**, senão dois processos consolidando disputam o mesmo arquivo.

⚠️ **`mtime` em segundos INTEIROS.** exFAT e SMB divergem no sub-segundo; comparar
nanossegundo entre máquinas invalidaria o cache inteiro a cada leitura.

⚠️ **Versione o esquema — e bumpe também ao consertar um EXTRATOR.** Sem isso o metadado
errado sobrevive ao conserto e o defeito volta calado na leitura do cache.

## 5. Caminhos entre máquinas

- Guarde **as duas formas**: `raiz + relativo` (portátil) e o absoluto observado. A raiz é
  o **rótulo do volume** — a mesma identidade que o Avid usa na coluna `Drive`, e a que
  sobrevive a montar o acervo com outra letra.
- ⚠️ **Caminho vindo do banco é ENTRADA DE REDE**, não dado seu: uma URL disfarçada de
  caminho chegando ao ffmpeg ou ao MediaInfo é SSRF (ver `seguranca/README.md`). Valide
  antes de qualquer uso.

## 6. Onde a configuração vive

⭐ **Na pasta do PROJETO, não na máquina** — só o CAMINHO do banco, nunca o banco. Daí
saem de graça três comportamentos que ninguém precisa programar: abrir o projeto já traz
o banco; **trocar de projeto desconecta**; e a equipe que compartilha a pasta do projeto
compartilha o banco. Guardar na máquina daria o efeito errado — o banco de uma produção
seguiria o EDITOR para dentro do projeto de outro cliente.

## 8. 🆕 ⭐⭐ Casar o ORIGINAL com a mídia CONVERTIDA dele — `confirmado` 2026-09-17

(Numerada 8 por ter chegado depois; vem antes da §7 porque a §7 fecha a página.)

O caso do Ciclo Assist no Premiere: o Avid processou o OP-Atom convertido (chave = UMID do
master); o Premiere aponta o arquivo original — outro arquivo, outro codec, outro UMID.
Medido com `_CICLO ASSIST/spikes/o_convertido_casa.py`, dois pares reais desta máquina:

| par | original | convertido |
|---|---|---|
| A | `20240531_PANA2774.mov` (ProRes) | OP-Atom MPEG-2 do **transcode do Media Composer** |
| B | `A001_03170214_C001.mp4` (H.264) | OP-Atom DNxHD gerado pelo **DaVinci Resolve** |

**Candidato (metadado):** nome da fonte normalizado (o `reel_name` do OP-Atom × o nome do
arquivo; sem extensão, sem `.new.NN`, sem caixa) + TC de início + taxa (`avg_frame_rate`) +
nº de quadros (±1). Os dois pares verdadeiros bateram nos quatro; os impostores (o take vizinho
da mesma câmera) em nenhum.

**Confirmação (conteúdo):** 5 quadros nas mesmas posições do primeiro minuto, 32×32 cinza,
correlação de Pearson (indiferente ao nível e ao ganho que o transcode muda):

| | corr. mínima | corr. média |
|---|---|---|
| A verdadeiro | **1,000** | 1,000 |
| A impostor | −0,071 | 0,227 |
| B verdadeiro | **0,992** | 0,996 |
| B impostor | 0,523 | 0,692 |

⇒ piso **0,95**. ⛔⛔ **O embedding NÃO serve para isto:** o MobileNetV2 do produto deu cosseno
**0,909 ao impostor B** e 0,63 ao verdadeiro A. Ele mede "parecido" (mesma pessoa, mesmo
cenário), e o impostor mais difícil é justamente parecido. "É o MESMO quadro?" é pergunta de pixel.

⛔ **E a comparação só vale com o quadro certo:** no OP-Atom MPEG-2 a busca rápida do ffmpeg cai
no quadro N/2 ([`../protocolos/mxf/README.md`](../protocolos/mxf/README.md)), e a primeira rodada
reprovou o par verdadeiro A por isso. Decodificar em ordem (`select` + `-vsync 0`).

⭐ **Desenho:** nome + TC + duração continuam **só candidato** (§2); quem decide é o conteúdo, e o
resultado é um **vínculo** com procedência (`fonte: visual`, `medida: corr`), não uma identidade —
original e convertido continuam sendo duas mídias.

## 8b. 🆕 ⭐⭐ E o SOM direto tem três formas que a imagem não tem — `confirmado` 2026-09-21

A §8 foi medida em **dois pares de IMAGEM**. Levando a mesma régua para um projeto de
Premiere com **203 arquivos** (118 `.mp4` + 85 `.wav` convertidos) contra o cache que um
Media Composer tinha montado do mesmo material, **23 não casaram** — e as três causas eram
todas do som direto de cena, que é justamente a camada que mais se aproveita (transcrição).

### a) O `reel_name` do som traz o ROLO grudado no fim

```
OP-Atom : PRODUCAO-A - 05-04 C14 P1-T010.WAV:2023-04-06
arquivo : PRODUCAO-A - 05-04 C14 P1-T010.WAV
```

O `:AAAA-MM-DD` é a data do rolo de som. Como o `.wav` deixa de ser o FIM do nome, quem
tira a extensão pelo sufixo não a tira, os dois nomes divergem e o par **nem vira
candidato** — com as durações idênticas (146,146 s). ⇒ Tirar o `:<qualificador>` final
ANTES da extensão. **36 de 332 mídias** daquele cache têm essa forma; nenhuma de imagem tem.

### b) ⛔⛔ A MISTURA dos dois lados não prova nada quando o som é multipista

O WAV do gravador é **uma pista com 5 canais**; o Avid guarda o mesmo material como
**5 OP-Atom de uma pista cada**. Somando os cinco de cada lado: **0,876** — abaixo de
qualquer piso razoável, logo "não é o mesmo material". Canal a canal (Pearson, o pico da
correlação cruzada):

```
       A01    A02    A03    A04    A05
ch1  +0,044 +0,044 +0,037 +0,054 +0,998
ch2  +1,000 +1,000 +0,807 +0,592 +0,043
ch3  +0,807 +0,807 +1,000 +0,072 +0,037
ch4  +0,592 +0,592 +0,072 +1,000 +0,053
ch5  +0,043 +0,043 +0,037 +0,053 +1,000
```

É o MESMO som **em outra ordem e com uma pista duplicada** (A01 = A02 = ch2; o mixdown do
gravador está em ch1/ch5 e em A05). Somar lados que trazem as mesmas pistas em proporções
diferentes dá um sinal diferente.

⇒ **Toda pista de um dos lados acha a sua no outro; o veredito é o pior desses pares**, e
vale o melhor dos dois sentidos — porque os dois recortes acontecem: o editor importa 2 das
8 pistas do gravador, ou aponta um WAV mono que é uma das 5 pistas que o Avid tem.

| | medida |
|---|---|
| verdadeiro, 5 canais × 5 pistas | **1,000** (era 0,876 pela mistura) |
| verdadeiro contra só 2 das 5 pistas | **1,000** |
| impostor (take vizinho, mesma cena, mesmo gravador) | **0,024** |

⚠️ **Pista não é canal**, e é a armadilha de implementação: o `ffprobe` conta *streams*, e
o WAV de 5 canais é UM stream. Quem contar streams acha 1 contra 5.

### c) O editor RENOMEIA o take na bin, e o filtro barato de nome cega

```
arquivo : PRODUCAO-A - 05-04 C14 P1-T010.WAV
bin     : PRODUCAO-A - 05-04 C14 P1/010
```

Mesmo material, `reel_name` certo nos OP-Atom, duração idêntica — mas quem pré-filtrar o
cache pelo nome da BIN não acha. ⇒ Quando o filtro barato não achar NADA, refazer a busca
pelo nome que está DENTRO do arquivo. Custa uma sondagem por mídia (ffprobe, guardável):
**10 s na primeira vez num cache de 332, 0,2 s depois** — contra ~1 min de reprocesso.

### d) ⚠️ E um de imagem: clipe mais curto que o número de posições

`B001_03150154_C017`, de **4 quadros** (0,23 s). Pedir 5 posições num clipe de 4 gera
posição repetida, e o `select` do ffmpeg entrega cada quadro **uma vez só**: voltam menos
quadros que posições e a conferência devolve "não consegui comparar" — que se lê como "não
é o mesmo material". Sem repetição: **0,998** (impostor 0,526).

### O placar, no mesmo projeto

| | casaram |
|---|---|
| só pela chave/apelido (sem ler conteúdo) | 1 de 203 |
| régua da §8 (imagem) | 180 de 203 |
| \+ (a) rolo no nome, (b) som por canal, (d) clipe curto | 182 |
| \+ (c) busca pelo nome de dentro do arquivo | **202 de 203** |

O único que sobra é honesto: o cache tem **outro** material com o mesmo nome (46,7 s contra
108,1 s, correlação 0,018) — recusado, como deve ser.

⭐ Dos 202, o Avid já tinha **194 transcrições, 118 conjuntos de quadros e 118 vetores**
prontos: zero reprocesso. A primeira passada custou **51 s** para os 203; a segunda, **2 s**
(o vínculo fica guardado).

### e) 🆕 A OP-Atom solta numa pasta de CONVERTIDOS, e o WAV que carrega o UMID do master — `confirmado` (2026-11-12, Mac)

Medido na D01 da PRODUCAO-A pela Carta Aberta (Ciclo Assist `cicloassist/carta/anexar.py`, `spikes/carta_aberta_c1_d01.py`):
- `CONVERTIDOS/D01_230403/02_SOM-DIRETO/SD01` tem, ao lado de cada `…-T001.WAV`, três `…-T001_A01/A02/A03.mxf`: são
  **OP-Atom** (`operational_pattern_ul` `060e2b34.04010102.0d010201.10030000`), um por canal, de OUTRO master do Avid
  (UMID `…6505F576…`, nome `…-T001`) — não a versão de trabalho. Casando arquivo a arquivo, os quatro passam na régua
  (nome + duração) e a mídia dá EMPATE de 4. ⇒ agrupar os arquivos de uma OP-Atom pelo UMID de material ANTES de
  casar (um candidato, N arquivos), e separar pela forma: o MXF OP-Atom só conta como forma Avid; o OP1a de câmera
  (Sony, ARRI) é mídia inteira. Depois: 5 WAV → trabalho, 5 OP-Atom → avid, zero empates.
- ⛔ **CORRIGIDO no mesmo dia:** registrei que o WAV dessa pasta trazia o UMID dos masters da `MXF/0102304031` — **errado**:
  li a saída de DOIS laços do `ffprobe` como uma (as linhas com `…2B6B9922…` eram das OP-Atom). Conferido direto: o WAV
  não tem UMID nenhum (só `time_reference`), e a OP-Atom dos convertidos tem OUTRO (`…6505F576…`). Na D01 os WAV casam
  pela régua (nome + duração). O UMID igual continua sendo prova onde existir (cópia da mesma OP-Atom; o MXF de câmera
  visto pelos dois NLEs); UMID diferente não reprova nada (o AMA ganha MobID novo a cada link).
- O nome na bin (`…PRAIA 03-04/001`, o take renomeado) ≠ o nome de dentro da OP-Atom e do WAV (`…PRAIA 03-04-T001.WAV`):
  a identidade sai da SONDA do arquivo, nunca do nome da bin (o defeito c acima, de novo).

### f) ⚠️ O limite conhecido da régua de som: UM canal igual e outro trocado passa como a mesma mídia — `hipotese` (só em SINTÉTICO, 2026-11-12, Mac)

- O WAV `G01_CANAIS` do laboratório (Ciclo Assist, Carta Aberta) tem o canal L IDÊNTICO ao som do G01 (**+1,000**) e o R
  trocado por um tom (**−0,005**). Pela régua da casa (**o MELHOR par de canais decide**, feita para o BRAW cujo transcode
  processou só um canal: 0,789 × 1,000), ele é ACEITO como a mesma mídia.
- ✅ **Decisão do autor (2026-11-12): a régua NÃO muda.** O caso foi FEITO por nós (para provar o enxerto de canais); no
  mundo real a variante de canal é a mesma tomada, e exigir TODOS os canais acima de um piso daria falso negativo no
  material convertido (mixdown, canal mudo ou só ruído, compressão, canais em outra ordem).
- ⭐⭐ **Regra:** piso de identidade só se calibra com material REAL; o laboratório prova a MECÂNICA, não o piso.
- ⭐ E quando o conteúdo DISCORDA de uma referência que a régua de metadado achou (o homônimo: mesmo nome e duração), a
  Carta Aberta **não decide sozinha**: é empate, do editor, com a medida dita (`anexar._referencia`). Discordar não prova
  outra mídia — burn-in e LUT no convertido nunca foram medidos contra o piso (§8).

## 7. A regra que atravessa tudo

⭐⭐ **O cache é GUIA, nunca regra.** Ele entrega um candidato já confirmado por um humano,
que passa por revalidação antes de valer; o que ele não souber segue o caminho completo,
exatamente como antes de ele existir. **Não pode haver rota em que o cache IMPEÇA uma
descoberta** — e falhar ao ler ou gravar o cache jamais pode derrubar o trabalho.
