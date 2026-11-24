# Decupagem por transcrição — o roteiro escrito **não é** a verdade

> Como separar as falas de uma cena entre várias tomadas, usando transcrição de ASR e o
> roteiro. Método e armadilhas, não formato: vale para qualquer app que case texto falado
> com texto escrito.
>
> **Confiança:** `confirmado` onde marcado. Medido em 2026-08-31 no Assist anterior, MC 25.6 /
> Windows 11, sobre a cena 4 de *PRODUCAO-A* — **15 tomadas, 1067 segmentos de ASR, 6
> falas de roteiro, 48 variações**, com gabarito aparado à mão pelo editor.
>
> ⚠️ **Atualizado em 2026-09-01** com as §8–§10, e em **2026-09-12** com a §8.6 (um quarto
> das fronteiras do `faster-whisper` é artefato, e o clamp do §8.5 acreditava nelas). ⭐ A **§8 é a mais transferível**: ela é
> sobre o `whisper.cpp`, não sobre decupagem, e vale para qualquer produto que o use.
>
> ⭐ Este arquivo abre um tema que o banco declarava virgem: *"não há registro de cruzar
> falas entre tomadas, de âncora por roteiro, de script sync"*.

---

## 1. ⛔⛔ O achado que muda o desenho: o ator não diz o que está escrito

Confrontando o roteiro do episódio com o que o ASR ouviu, em 4 das 6 falas da cena o texto
dito **diverge** do escrito — e não por erro de transcrição:

| | roteiro **escrito** | o que foi **dito** |
|---|---|---|
| fala 01 | "**Boa noite.** Sou o doutor Personagem I…" | "**Boa tarde.** Sou o doutor Personagem I…" |
| fala 02 | "Tudo bem, Eduardo? O advogado, não é?" | "**Eduardo, o advogado?**" |
| fala 04 | "Tudo bem. Estava lhe esperando… Eu sou Personagem F (pausa). A terapeuta." | "**Eu sou Personagem F, a terapeuta.**" |
| fala 06 | "Você falou com a secretária; ela já foi…" | "**Não.** Você falou com a **minha** secretária…" |

⇒ **Um motor que trate o roteiro como verdade descarta material dito.** Ele é um **mapa**:
diz quantas falas há e em que ordem, e poupa redescobrir a estrutura. Não diz as palavras.

⭐ A formulação do editor: *"o 'roteiro gravado' se sobrepõe ao roteiro escrito porque foi
ele o captado."*

### 1.1 ⛔ Dois modos de falha, e os dois foram medidos

**(a) O improviso vira ÓRFÃO.** Na fala 06 a atriz acrescenta um "Não" que o roteiro não
tem. Em **4 de 11** tomadas a pausa foi curta e o ASR o pôs no mesmo segmento — veio de
carona; nas outras **7** a pausa foi longa, virou segmento à parte, e o alinhamento contra o
roteiro **não tinha contra o que casá-lo**. Perda medida: **0,67 s a 3,96 s** de fala, por
tomada.

⚠️ A variação (0,67 a 3,96 s) é o tamanho da pausa mudando de tomada para tomada — não há
limiar de silêncio que separe "mesma frase" de "frase seguinte" com segurança.

**(b) O aparo guiado por roteiro CORTA DENTRO DA PALAVRA.** O motor afinava o in/out dentro
do segmento, mantendo só o que casava o roteiro acima de um piso. Medido no `C04_P01-T002`:

```
segmento do ASR:   74.58 – 76.06   "Eduardo, o advogado."
janela entregue:   75.33 – 76.06   ⛔ 0,75 s DENTRO do segmento, no meio de "Eduardo"
```

O editor ouviu antes de qualquer medição: *"comeu o início do nome do personagem"*.

⇒ **Regra derivada:** a janela é a **borda do segmento do ASR**, e nunca corta dentro dele.
⚠️ O custo é declarado — segmento largo traz material a mais nas pontas. A escolha do editor:
*sobrar é melhor que cortar palavra*, porque numa timeline de organização ele apara o excesso
num gesto e não recupera o fonema que não está lá.

---

## 2. ⭐⭐ A espinha é o material, e o roteiro só semeia

O desenho que funciona, em três passos:

1. **Semear** — com roteiro, os textos dele; sem roteiro, os segmentos da tomada com **mais
   material**. Nos dois casos a espinha é uma **sequência ordenada**.
2. **Casar cada tomada** contra a espinha, monotonicamente, juntando segmentos consecutivos.
3. ⭐ **Adotar o órfão vizinho** — o passo que conserta o improviso.

⭐ **Por que a ORDEM importa:** uma fala do fim de uma tomada pode ser textualmente parecida
com uma do começo de outra. Julgada isolada, ela vira falso positivo. Numa espinha ordenada
ela não pode ocupar a posição que as vizinhas já ocupam — o desempate deixa de ser a nota do
texto e passa a ser a coerência da ordem.

### 2.1 A regra da adoção, e o que a segura (`confirmado`)

> **Um órfão colado a um trecho, NO MESMO CANAL, que nenhum outro momento reclama, entra no
> trecho.**

⛔⛔ **O canal é o que segura a regra, e sem ele a regra é perigosa.** Canal é falante (ver
§4). Numa cena de dois, o segmento antes da fala de A costuma ser de B — adotar por
vizinhança sem checar canal engole a resposta do outro ator. **Segmento sem canal não é
adotado:** não medido não é permissão.

### 2.2 ⚠️⚠️ A adoção FOGE, e fugiu de duas maneiras diferentes

| tentativa | o que aconteceu |
|---|---|
| limite só por **índice** de segmento | a primeira fala adotou a **claquete** (−525 frames, 22 s antes) e a última **o resto da cena** (+714 frames, 30 s depois). Os momentos das pontas têm piso/teto na borda da tomada |
| limite por **silêncio** entre segmentos | ainda fugia: o ASR declarou um segmento de **21,5 s para duas palavras** (`"Boa tarde."`), a **0,41 s** de distância — passava em qualquer teto de silêncio e arrastava o in 22 s |
| ⭐ limite por **extensão da janela** | o que resolve |

⭐⭐ **A medida certa é quanto a janela CRESCE**, não o silêncio entre os segmentos. Silêncio
curto antes de um segmento comprido estica tanto quanto silêncio comprido.

⚠️ **Um segmento de ASR pode declarar duração muitas vezes maior que a fala que contém.** Foi
o caso acima: 21,5 s para duas palavras. Quem usar a duração declarada do segmento como se
fosse a duração da fala vai errar por dezenas de segundos, e o resultado ainda parece
plausível.

Varredura do teto contra o gabarito do editor (bordas a ≤8 frames do corte dele, de 86):

| teto (s) | 0 | 1 | 2 | **3–6** | 10 | 30 | sem |
|---|---|---|---|---|---|---|---|
| bordas | 29 | 30 | 31 | **32** | 31 | 29 | 29 |
| pior \|d\| | 334 | 356 | 356 | **356** | 459 | 714 | 714 |

Platô em **3–6 s**. ⚠️ Uma cena, uma sessão de aparo — não é lei geral.

### 2.3 ⛔ O que o método NÃO resolve, e a causa está nomeada

Contra o gabarito, a espinha ficou **43 acertos / 5 erros** onde o motor guiado por roteiro
dava **46 / 2**. Dos 5, **3 são falas perdidas numa única tomada**.

⇒ A causa é o **casador guloso e monotônico**: naquela tomada uma fala casou tarde, o cursor
avançou, e as três seguintes ficaram sem material onde procurar. ⚠️ **O cursor monotônico é o
que dá a coerência de ordem do §2 e é também o que perde tomadas** — quem for adotar o método
precisa de busca com feixe ou de ótimo global, não de guloso.

---

## 3. ⭐ O aviso que grita sempre não é aviso (`confirmado`)

O motor marcava a confiança de cada fala como `hipotese` quando ela aparecia em **mais de uma
tomada**. Num comando cujo propósito é enfileirar **todas** as tomadas de cada fala, isso é
sempre verdade. Medido, com a matriz `acertou/errou × sinalizado/calado`:

```
               sinalizado   calado
  acertou              46        0
  ERROU                 2        0
```

**46 avisos em variação certa contra 2 em errada.** É o quadrante do custo escondido de
[medir-sync-contra-gabarito.md](medir-sync-contra-gabarito.md) §4 no estado puro: *quem
confere 48 avisos para achar 2 erros aprende a não conferir nenhum*.

⇒ **A bandeira respondia uma pergunta cuja resposta é sempre "sim".** A decisão do editor foi
**tirá-la**: *"melhor nenhum aviso do que um aviso que todo mundo aprende a ignorar"*.

⭐ E tirá-la fez a régua dizer a verdade: os 2 falso-positivos reais deixaram de contar como
"avisados" e passaram a contar como **veneno**, que é o número a bater.

---

## 4. O falante vem do CANAL, não da diarização

Confirmação independente do que o banco já registra para som direto: numa cena de **dois**
atores, a diarização por embedding devolveu **doze** falantes (limiar varrido de 0,5 a 0,9:
43, 34, 26, 16, 12 — monotônico, sem joelho, nenhum valor dá 2). A causa não é o modelo: o WAV
tem 5 canais (mixdown L/R + duas lapelas + boom) e o derivado de fala soma tudo, então cada
voz entra duas ou três vezes e o timbre vira mistura.

⭐ **O falante já vinha do set:** o iXML do BWF traz um `TRACK_LIST` nomeado pelo técnico de
som, e atribuindo por energia da lapela dá **24 takes · 1502 falas · 91,9% resolvido**. E o
mapa `personagem → canal` **emerge** de uma primeira passada sem filtro — não precisa ser
perguntado.

⇒ É esse canal que torna a adoção do §2.1 segura. Sem som direto multipista, a regra de
adoção **não se aplica**.

---

## 5. ⭐⭐ O respiro editorial: o vão pode reduzir, **nunca zerar** (`confirmado`)

O motor dava um respiro alvo de **8 frames** de cada lado, **aparado pelo vão acústico**
(quanto de silêncio há antes e depois). Onde o vão era zero, o respiro ia a zero e o corte
saía **cravado na fala**.

A correlação apareceu sozinha no aparo à mão do editor, sobre 46 variações:

| fala | vão antes / depois | o que ele fez |
|---|---|---|
| 01 | 0,76 / 1,0 | ✅ **4 de 4 intocadas** |
| 03 | **0,0 / 0,0** | alongou **as 4, dos dois lados** |
| 05 | 0,48 / **0,0** | 0 na cabeça, **5 na cauda** |

⭐ Conferido que **não foi limite de material**: sobravam centenas de frames no take.

Varredura do **piso** contra o gabarito (bordas a ≤2 frames do corte dele, de 92):

| piso (frames) | 0 | 3 | 4 | **5** | 6 | 8 | 10 |
|---|---|---|---|---|---|---|---|
| bordas | 53 | 62 | 72 | **72** | 71 | 51 | 21 |

Platô em **4–6**, mínimo do erro mediano em **5** — e o editor havia **dito 5** antes de ver a
varredura. Duas derivações independentes no mesmo número.

⇒ **alvo 8 frames, piso 5.** O vão reduz, nunca zera. Reemitido e medido na bin: bordas a ≤1
frame do corte dele foram de **54 para 69** (de 92).

⚠️ **`None` continua dando zero.** Vão *não medido* é diferente de vão *medido em zero*: com o
zero sabe-se que há voz por perto e escolhe-se entrar 5 frames nela; sem medida, estender no
escuro põe voz alheia no clipe sem ninguém ter decidido isso.

⚠️ Amostra: uma cena, uma sessão de aparo. O banco cobra três diárias
([medir-sync-contra-gabarito.md](medir-sync-contra-gabarito.md) §3b).

---

## 6. ⭐ O gabarito sai da bin que o editor APAROU

Extensão do método de [medir-sync-contra-gabarito.md](medir-sync-contra-gabarito.md) para
decupagem, e o ponto é a ergonomia: **o editor não escreve JSON e não pensa em segundos
decimais** — ele pensa em timecode e apara.

```
1. a ferramenta emite a bin              → guarde uma CÓPIA do "antes"
2. o editor apara e EXTRAI no MC         → o gesto que ele faria de qualquer jeito
3. a ferramenta lê as DUAS bins          → a diferença É o gabarito
```

| na original | na conferida | vira |
|---|---|---|
| sim | sim | aprovada, com o in/out **dele** |
| sim | **não** | ⭐ falso-positivo declarado (ele extraiu) |
| não | sim | um "faltou" declarado (ele acrescentou) |

⛔⛔ **É obrigatório perguntar QUAIS falas ele percorreu.** Uma variação intocada tem a
**mesma geometria** nas duas bins de uma aprovada — sem essa lista, a régua conta como
aprovado tudo o que ninguém olhou. Foi o falso-verde mais provável de todo o método.

⚠️ **A cópia do "antes" tem de ser feita ANTES de o editor abrir a bin** — o MC regrava a bin
ao abri-la. E guarde-a **fora** da pasta de bins (extensão diferente de `.avb`): duas bins com
o mesmo `uid` no mesmo boot brigam, e a primeira carregada ganha.

### 6.1 ⛔ A conferência é DESFEITA a cada reemissão

Reemitir do plano trouxe de volta os 2 falso-positivos que o editor tinha extraído —
inclusive um clipe de **12,2 s** que pegava o diretor falando *"ação"*. O gabarito sabia; nada
o lia na hora de emitir.

⇒ **Quem for iterar com um editor tem de resolver isto antes de pedir a segunda conferência.**
Ou o emissor lê o gabarito, ou o editor refaz o trabalho a cada rodada — e para de colaborar.

### 6.2 ⛔⛔ O gabarito é ENVIESADO a favor do motor que produziu a bin

E isso não é um defeito a consertar — é o limite do método, e ele tem de ser dito **antes**
de alguém comparar dois motores com ele.

O editor não corta do zero: ele **ajusta a proposta**. Então "intocada" quer dizer *"aprovei
a escolha daquele motor"*, não *"é aqui que eu cortaria a partir do nada"*. A régua mede
**distância do que ele fez**, não qualidade.

Medido em 2026-08-31, e foi assim que apareceu: um motor novo, com um critério de janela
deliberadamente diferente (borda do segmento em vez de aparo por dentro), marcou **21 de 92**
bordas a ≤1 frame contra **69 de 92** do motor que gerou a bin do gabarito. ⚠️ **A régua não
consegue dizer se ele é pior — só que é diferente.**

⇒ **A régua julga bem o CONJUNTO** (esta variação devia estar aqui? — respiro-independente,
e foi ela que pegou três falas perdidas por um casador guloso) **e mal a JANELA**, quando o
critério de janela mudou.

⭐ **O que fazer:** para comparar dois motores com critérios de janela diferentes, o gabarito
tem de vir de **uma bin de cada**, ou de um corte que o editor fez sem proposta nenhuma. Com
um gabarito só, a comparação da janela volta para a sala — as duas bins abertas lado a lado.

### 6.3 ⚠️ E a calibração não transfere quando a BASE muda

Um piso de respiro calibrado sobre janelas **aparadas por dentro** deixou de valer quando a
janela passou a ser a **borda do segmento** — que já traz ar na cabeça. Somar o respiro ali
conta o mesmo ar duas vezes, e a varredura mostrou os dois lados querendo números
**diferentes** (o in 0–2 frames, o out 8) onde antes um só servia.

⇒ *Toda constante calibrada carrega, implícita, a base sobre a qual foi medida. Mudou a
base, a constante virou número herdado — e número herdado de outra escala não significa
nada.*

### 6.4 ⚠️ A mediana esconde o que importa; mostre a distribuição

Pôr o piso do respiro melhorou as bordas a ≤1 frame de **54 para 69**, e a **mediana não se
mexeu** (+0,0 nas duas medições), porque a maioria já estava em zero. Um relatório só de
mediana teria dito *"não mudou nada"* sobre quinze bordas de melhora.

⇒ Para defeito que vive na cauda, o resumo certo é **quantas bordas caem a ≤N frames**, não a
mediana.

---

## 7. ⚠️ O que este arquivo NÃO faz

- **Não mede sem roteiro.** A espinha semeada pelo material roda, mas produziu **157
  momentos** na C04 (a tomada de referência inteira, com claquete e a cena seguinte). Falta
  recortar escopo e agrupar. `pendente`.
- ✅ **O casador guloso foi resolvido** (§2.3) — programação dinâmica, ótimo global.
- ⚠️ **O piso do respiro (§5) não foi re-varrido depois do VAD.** A base mudou três vezes
  (borda do segmento → aparo por energia → VAD) e só os alvos do in/out foram recalibrados
  na última. `pendente`.
- **Não usa LLM.** O assento está desenhado e vazio: adotar órfão que a vizinhança não
  explicou, com a transcrição delimitada como *material a analisar* e a resposta validada
  contra esquema fechado. ⭐ E já existe caso de teste medido: o "Não" órfão em 7 de 11
  tomadas com a resposta conhecida — e nas outras 4 o mecanismo tem de saber **não fazer
  nada**, que é o eixo do falso-positivo.
- ⚠️ **Tem timestamp por palavra desde 01/09, e ele NÃO basta.** Ver §8.2 e §8.3: o tempo
  por palavra existe (`-ml 1 -sow`) e resolve **seleção**, não **aperto**. Quem aperta é o
  VAD (§8.4). ⭐ E o banco já registra que *"um modelo no disco não é uma feature"*
  ([analise-de-executaveis.md](analise-de-executaveis.md)): o Jumper empacota um
  `qwen3-forced-aligner` e as skills dele declaram que **não há timing por palavra**.
- **Uma produção, uma cena, uma sessão de aparo.** Todos os números aqui são dessa amostra.

---

## 8. ⛔⛔ O tempo do whisper.cpp **não é** o tempo da voz (`confirmado`)

> Medido em 2026-09-01, mesmo material. ⭐ É a seção mais transferível deste arquivo: vale
> para **qualquer** produto que use `whisper.cpp`, não só para decupagem.

O editor formulou a pergunta que a expôs:

> *"Se a nossa missão fosse legendar o vídeo, a legenda só cairia em cima de cada fala,
> deixando espaços vazios sem fala. Porque não conseguimos fazer o mesmo?"*

**A resposta é que o whisper não delimita fala — ele PARTICIONA a linha de tempo.** Todo
silêncio é grudado num vizinho. Medido numa tomada-mestra de 8m54s, 110 deixas:

| | |
|---|---|
| tempo coberto pelas deixas | **330,7 s** (61,9% da faixa) |
| tempo com voz de verdade | **202,3 s** (37,9%) |
| ⛔ **deixa no ar sem ninguém falar** | **128,4 s** — 39% do tempo de legenda |

As piores, e a mesma frase varia 10× entre tomadas:

    'Boa tarde.'                  50,64 –  75,56   (24,92 s de deixa)
    'Eu sou Personagem F, a terapeuta.' 114,96 – 127,22   (12,26 s)
    'Boa.'                       529,22 – 539,90   (10,68 s)

⚠️ E **24,3%** de 1052 fronteiras entre segmentos são **exatamente contíguas** (vão = 0,000):
o segmento seguinte começa no milésimo em que o anterior termina. É daí que saem os dois
sintomas clássicos — o rabo do falante anterior na cabeça do clipe, e a última palavra
cortada porque vazou para o segmento seguinte.

### 8.1 ⛔ `-ojf` (tempo por token) NÃO serve com `--vad`

O caminho óbvio é `--output-json-full`, que traz `offsets` por token. ⛔ **Com `--vad`
ligado os tokens ficam no relógio COMPRIMIDO** (o do áudio sem silêncios), enquanto os
segmentos já vêm remapeados para o original:

    segmento  ' Eu sou Personagem F, a terapeuta.'   19,07 – 30,46   ← relógio real
    tokens    ' Eu' … 'uta'                   14,20 – 16,20   ← relógio do VAD

Somar um offset de correção acerta um segmento e erra todos os outros: o erro cresce com o
silêncio acumulado. ⚠️ `--dtw <preset>` é **aceito** (um preset inválido dá erro, então a
validação existe) e ainda assim `t_dtw` volta **−1** em todos os tokens neste build.

### 8.2 ⭐ A rota que funciona para palavra: `-ml 1 -sow`

`--max-len 1 --split-on-word` faz o whisper emitir **um segmento por palavra**, e segmento
passa pelo **mesmo remapeamento** dos outros. Custo: uma passada a mais (7,7 s por tomada
numa RTX 4050, contra ~17 s da passada normal).

⭐⭐ **Portão obrigatório:** as duas passadas são decodificações independentes. Comparar os
fluxos de palavra antes de usar — se divergirem em uma palavra, todo índice depois dela
aponta para o tempo da palavra errada, **e a janela sai deslocada sem nada acusar**. Medido:
52/52 e **619/619** batem no material real, mas por medição, não por garantia.

⚠️ E o segmento de `-ml 1` **não é** uma palavra do seu tokenizador: `"e-mail,"` sai num
segmento só e vira duas palavras. Guardar o segmento faz a lista ficar mais curta que a do
texto (619 contra 616, medido) e desloca tudo depois do hífen.

### 8.3 ⚠️ E mesmo por palavra, a borda continua gorda

A palavra do whisper herda o mesmo particionamento: a **primeira** absorve o silêncio da
frente e a **última** o de trás.

    ' Eu'         114,96 – 122,43   ⛔ 7,5 s para uma sílaba
    ' terapeuta.' 123,31 – 127,22   ⛔ 3,9 s
    ' tal.'        40,10 –  54,46   ⛔ 14,4 s

⇒ O ganho do tempo por palavra é em **seleção** (excluir claquete, o rabo do outro ator, a
conversa depois do corte), **não em aperto**. Medido em 48 variações: 11 encolhem, ~29 s de
material alheio saem, **mediana zero**.

### 8.5 ⭐⭐ O `faster-whisper` erra para o LADO CONTRÁRIO — `confirmado` 2026-09-11

Medido no Ciclo Assist (`spikes/o_respiro_do_corte.py`), som direto real de set, com
`faster-whisper` **small / int8 / `word_timestamps=True` / `vad_filter=True`**, comparando
o tempo por palavra com a energia do WAV (janela de 10 ms, piso de ruído local × 3):

```
voz ANTES do que o ASR diz    mediana   10 ms   pior  300 ms
voz DEPOIS do que o ASR diz   mediana  230 ms   pior  350 ms   ← 5,5 frames a 24 fps
```

⛔⛔ **É o inverso do `whisper.cpp` do §8.3.** Lá a borda é GORDA (a primeira palavra
absorve o silêncio da frente — 7,5 s para uma sílaba); aqui ela é APERTADA, e o que fica de
fora é a **cauda**. Um app que troque de motor de ASR herda o defeito oposto, e a calibração
de aparo do §5 não transfere.

⇒ A consequência de produto é a que o editor relatou em campo, nas palavras dele: *"'sobe
comigo' vira 'sobe co…'"*. Cortar no tempo do ASR decepa a última sílaba.

⭐ **São dois problemas diferentes, e confundi-los produz o conserto errado:**

| sintoma | causa | conserto |
|---|---|---|
| cauda cortada | erro de **medida** — o ASR fecha cedo | estender o fim (0,4 s cobre o pior caso) |
| entrada colada | **não** é erro de medida (10 ms) | respiro de **montagem**: cortar rente não dá ar |

⭐ Corroboração externa: as skills embutidas do **Jumper** (parceiro oficial da Avid) mandam
*"add up to 0.5 seconds of handle on either side where the neighboring gap permits. Clamp at
the previous segment's end and next segment's start so an unselected speaker is not
included"*. Mesma regra, número redondo; a nossa é medida e assimétrica.

### 8.6 ⛔⛔ Um quarto das fronteiras do `faster-whisper` é ARTEFATO — e o clamp acredita nelas — `confirmado` 2026-09-12

Medido no cache do Ciclo Assist (**727 falas, 715 fronteiras**, `faster-whisper` small/int8
com `vad_filter=True`), sobre o vão entre falas consecutivas:

| vão entre uma fala e a seguinte | quantas | % |
|---|---|---|
| **exatamente `0,000 s`** | **169** | **23,6%** |
| 0 a 0,08 s | 6 | 0,8% |
| 0,08 a 0,40 s | 111 | 15,5% |
| 0,40 s ou mais | 429 | 60,0% |

⛔⛔ **Fala humana não produz vão exatamente zero um quarto das vezes.** Esses `0,000` são o
motor **encadeando segmentos** — a fronteira não foi medida, foi herdada do fim do anterior.

⇒ **E é aqui que a regra do §8.5 se volta contra si mesma.** O aparo que o Jumper descreve
(*"clamp at the previous segment's end and next segment's start"*) e que nós
implementávamos igual pressupõe que a fronteira do vizinho é um FATO. Com um vão de zero, o
clamp corta o respiro inteiro:

```python
corte_fim = min(fim + RESPIRO_DEPOIS, proxima_inicio - VAO_MINIMO)   # < fim quando o vão é 0
corte_fim = max(corte_fim, fim)                                      # colapsa em `fim`
```

Resultado medido: **176 de 727 falas (24,2%) saíam com respiro ZERO** — e entre elas *todas*
as ocorrências da fala que o editor vinha reclamando em campo há dois pareceres (*"sobe
comigo" virando "sobe co…"*).

⚠️⚠️ **O diagnóstico óbvio estava errado, e o do editor também.** Não era calibragem: o
respiro de 0,40 s já cobria com folga o pior caso medido no §8.5 (0,31 s naquele material).
Era o vizinho zerando o respiro de quem ainda estava falando.

⇒ **A regra:** separe **fronteira medida** de **fronteira encadeada**. Abaixo de um épsilon
(usamos 0,02 s) a fronteira é artefato do motor — o vizinho não tem autoridade para limitar
nada, e o respiro sai inteiro. Acima dele houve silêncio de verdade, e aí o clamp vale:
trazer a cauda do outro ator para dentro do corte é pior que cortar rente. Depois da
separação: **0,8%** de falas com respiro zero, e os que sobram são vãos medidos de verdade.

⭐ **Isto reinterpreta o §5.** Lá, *"onde o vão era zero, o respiro ia a zero"* foi lido como
uma propriedade do MATERIAL (falas coladas). Uma parte disso — a fatia que num motor com
`word_timestamps` é exatamente `0,000` — é propriedade do MOTOR. A correlação que o editor
produziu à mão continua válida; a explicação ganha uma segunda causa.

⚠️ Medido só no `faster-whisper`. O `whisper.cpp` do §8.3 tem 24,3% de fronteiras
"exatamente contíguas" (§8, tomada-mestra) — número suspeitosamente parecido, mas medido
sobre outra base e sem a mesma conclusão. Confirmar antes de transferir: `hipotese` para
qualquer outro motor.

### 8.7 ⭐⭐ A borda real da voz sai da LAPELA, nunca da mistura — `confirmado` 2026-11-09

Medido na C07 de *PRODUCAO-A* (MC 2024.6, OP-Atom de 5 canais, 7 takes, `_CICLO ASSIST/spikes/edicao_de_cena/bordas.py`). Motivo: o editor ouviu o fim da fala anterior
repetir em 3 emendas de um corte montado por agentes, com a pausa calculada pelo tempo do `faster-whisper`.

- O tempo por palavra é estimado: **77% das 2.531 palavras estão coladas à seguinte (0 ms)** e 106 duram mais de 0,8 s.
- ⛔ Na MISTURA o envelope não separa: com piso de sala alto, a "voz" bateu no limite de busca em toda borda e piorou contra o editor humano (10 de 20 emendas dentro de voz, contra 5 do ASR).
- ⭐ Na LAPELA separa: Personagem F some no quadro 1200 e Personagem G entra no 1204, respiro que o ASR não via. A voz de um ator vaza para a lapela do outro; só conta onde o canal dele não perde do outro por mais de 3 dB, cada um relativo ao próprio p95.
- Sem nome de trilha (condição C): as lapelas são o par de canais menos correlacionado **depois de tirar as cópias**. Mistura em duas pistas tem correlação 1,00 e, sem tirá-la, o par sai errado (mistura + lapela).
- Resultado: 627 de 660 bordas medidas; o fim da voz avança mediana de 5 quadros, o mesmo que o §8.5 mediu por outro caminho (230 ms). Emendas do editor humano dentro de voz: **ASR 5/20, lapela 2/20**.
- A conferência "voz de outro segmento dentro do plano", rodada sobre o corte que o editor ouviu, acusou as 3 repetições dele e mais uma que ele não citou.
- ⚠️ Whisper reouvindo o corte montado pegou só 1 das 3: fragmento de palavra ele não reconhece.
- Mac: `pendente`. Limite: n = 1 produção; canal de cada ator conferido por energia, sem o mapa de nomes.

### 8.4 ⭐⭐ O VAD já sabe onde é a voz — e o `whisper.cpp` DESCARTA as fronteiras

O Silero roda como `--vad` (é ele que impede a alucinação sobre música e silêncio), serve
para tirar silêncio antes de decodificar, e as fronteiras dele **não saem em lugar nenhum**
da saída normal. O binário `whisper-vad-speech-segments` as devolve:

| deixa do ASR | dura | ⭐ voz, segundo o VAD |
|---|---|---|
| `'Boa tarde.'` | 24,92 s | **0,36 s** (75,20–75,56) |
| `'Eu sou Personagem F, a terapeuta.'` | 12,26 s | **2,01 s** (122,43–127,22) |
| `'Boa.'` | 10,68 s | **0,31 s** |

⭐ E ele **bate com o tempo de palavra** onde este é confiável: o VAD diz que a voz começa em
122,43 e o `-ml 1` diz que a palavra *"sou"* começa em 122,43. Duas medições independentes.

**Custo: 1,5 s por tomada**, em CPU. ⛔ `-ug` (GPU) quebra neste build:
`pre-allocated tensor (leaf_0) in a buffer (CUDA0) that cannot run the operation`.

⚠️⚠️ **Duas armadilhas de leitura, as duas caladas:**

1. A saída é em **CENTISSEGUNDOS** — o `--help` avisa, e é erro de 100×.
2. Ao alinhar os trechos com janelas de energia, `int((1.2 - 1.0) / 0.1)` devolve **1**, não
   2: a subtração dá `0.19999999999999996`. Use `floor`/`ceil` com tolerância — o erro é de
   uma janela e só em algumas falas, que é o pior jeito de um defeito aparecer.

### 8.7 ⭐⭐ Energia diz DE QUEM; o VAD diz SE É FALA — precisa dos dois

Um aparo por **energia** confunde roupa na lapela, porta, respiração e ensaio com voz: das
128,4 s de deixa muda, a energia recuperava **34 s** e o VAD acha **111 s**. Mas o VAD roda
no mono e **não diz de quem é a voz** — quem responde isso é a energia por canal (§4).
Trocar um pelo outro perde metade da pergunta.

⚠️ E há um defeito de medição que só aparece em janela gorda: usar a **mediana** dos níveis
como referência de voz. Numa janela quase toda silêncio a mediana **é** o silêncio, o limiar
cai dentro do ruído e tudo vira voz:

| janela | mediana | p90 | max |
|---|---|---|---|
| 22,8 s | **−48,4 dBFS** | −25,9 | −14,3 |
| 2,4 s (apertada) | −36,1 | −22,5 | −20,0 |

⇒ Para achar voz DENTRO de uma janela larga, a referência é o **pico** (p90), não a mediana.

---

## 9. ⭐⭐ A linha do roteiro não é a fronteira da fala (`confirmado`)

O §1 estabeleceu que o roteiro não dita as **palavras**. Medido em 2026-09-01: ele também
não dita as **fronteiras**. A formulação do editor:

> *"No roteiro isso está em uma linha de diálogo apenas, na gravação separou-se em dois
> momentos… Se fosse considerado o roteiro gravado, teríamos a Fala 04 como 'tudo bem eu
> estava te esperando' e a fala 05 como 'eu sou personagem f a terapeuta'."*

Uma linha do roteiro — *"Tudo bem. Estava lhe esperando; entra, por favor. Eu sou Personagem F
(pausa). A terapeuta."* — foi gravada como **dois momentos separados**, com 18,4 s e dois
improvisos entre eles na tomada-mestra, e em setups diferentes (os planos fechados do fim só
têm a primeira metade; os outros onze só têm a segunda).

⛔⛔ **O efeito: a única resposta admissível é a errada.** Alinhando a linha inteira:

| candidato | nota |
|---|---|
| só a 2ª metade | 0,353 ⛔ abaixo do piso |
| só a 1ª metade | 0,381 ⛔ abaixo do piso |
| ⛔ **as duas juntadas, com o que houver no meio** | **0,483** ✅ passa |

Com piso em 0,45, o casador é **obrigado** a costurar por cima de tudo que estiver entre
elas. Partindo a linha em dois momentos, a 2ª metade vai de 0,353 a **0,750**.

### 9.1 ⭐ Como detectar, sem lista de exceções

Alinhe **o texto de cada trecho de volta contra a linha do roteiro** e veja que faixa de
palavras ele cobre. Faixas que **não se sobrepõem** são momentos diferentes. Medido nas 6
falas da cena (`cobertura por palavra`):

    FALA01  444444444444444444   um bloco
    FALA02  0044400              um bloco (as pontas ninguém disse)
    FALA03  44444444444444       um bloco
    ⭐ FALA04  22222222999999    DOIS — 11 tomadas cobrem [8:14], 2 cobrem [0:8]
    FALA05  7999999              um bloco (as faixas se ANINHAM)
    FALA06  999999999999999999   um bloco

⚠️ O critério é **sobreposição**, não o degrau da contagem: a FALA05 tem degrau (7 tomadas
dizem o "Ah", 12 não) e é um momento só, porque `[0:7]` contém `[1:7]`. Contar o degrau
partiria toda fala com uma palavra opcional na ponta.

⚠️ E depois de partir, **re-case** com as sementes menores — não remende os trechos da
passada anterior. É o re-casamento que faz a nota subir.

### 9.2 ⛔ A junção conta "consecutivos" na lista FILTRADA — e isso atravessa o outro ator

Um casador que filtra segmentos por canal e depois junta *"até N consecutivos"* está juntando
consecutivos **na lista filtrada**. Filtrado o outro ator, duas falas separadas por dez
segundos de diálogo dele ficam **vizinhas**, e a fala costura por cima. ⇒ **Teto de TEMPO na
junção, além do teto de contagem.** Medido: junções legítimas até **3,22 s** de vão; a que
precisava morrer, **6,17 s**.

⚠️ Isto **não** resolve claquete grudada: `"Constante." "Ação." "Eu sou Personagem F…"` vem com vão
**0,0** (o whisper corta contíguo), e nenhum limite de tempo a separa. Aquilo é assento do
tempo por palavra (§8.2).

---

## 10. ⛔⛔ Medido e REPROVADO — não repetir

| tentativa | por que caiu |
|---|---|
| **`-ojf`** para tempo por token | relógio comprimido (§8.1) |
| **teto de silêncio INTERNO** para colapsar janela gorda | a pausa **legítima** de *"Eu sou Personagem F (pausa). A terapeuta"* tem **5,32 s** — maior que os 3,52 s da janela defeituosa. Consertar uma quebra a outra |
| **respiro não entra em voz adjacente** | o editor **aceita** ~5 frames do outro ator. Bordas a ≤4 frames caem de 49 para 42 (de 92) |
| **limite de respiro contra qualquer palavra vizinha** | idem, 42 |
| **diarização por embedding** (já em §4) | 12 falantes numa cena de 2 atores |

⭐⭐ **O que sobrou:** a chamada do diretor e o rabo do outro ator têm a **mesma geometria** —
uma palavra alheia colada na cabeça da fala. A diferença é **quem falou**, então a regra que
funciona é de **vocabulário** (`ação`, `corta`, `cortou`, `constante`, `rodando`,
`gravando`, `valendo`), não de distância. ⚠️ Aplicada só a palavras que o alinhamento já
**excluiu** — uma personagem que diga *"corta"* na fala dela não perde a palavra.

### 10.1 ⚠️ E a régua não premia o que mais importa

O gabarito é o aparo do editor **sobre a bin do caminho antigo**. Ele mede *distância do que
ele fez*, e **não sabe pontuar** *"esta tomada agora está na fala certa"*. A repartição (§9)
e o vocabulário custaram borda no gabarito e entraram assim mesmo. ⛔ **Quem otimizar só o
número vai desfazer as duas.**

---

## 11. ⛔⛔ O ASR que não roda vira "não há fala" — `confirmado` (2026-09-03)

O caso mais caro de falso-verde deste arquivo, porque **não deixa rastro nenhum**.

Um app que chama o `whisper-cli` por subprocesso costuma envolver a chamada num
`try/except` e devolver `""` — a intenção é boa: *uma ilha ilegível não pode derrubar a
cena inteira*. O efeito é outro. Quem consome não distingue **"perguntei e não há fala"**
de **"não consegui perguntar"**, e escolhe pelo primeiro.

**Medido no Assist anterior**, com o binário fora da máquina e depois com ele de volta, na
mesma cena e no mesmo código:

```
sem whisper-cli   aperto por ilha: {'sem_buraco': 92, 'nenhuma_fala': 11}    48 ilhas
com whisper-cli   aperto por ilha: {'sem_buraco': 92, 'aparou_ilha_muda': 3,
                                    'tudo_fala': 8}                          48 ilhas
```

⛔⛔ **E olhe o que NÃO denunciava:** o número de ilhas transcritas é o mesmo (48) nas
duas — a chamada acontecia, só não respondia. O relatório saía inteiro, com todas as
outras linhas plausíveis. Na segunda cena, o mesmo (`nenhuma_fala: 7`).

⚠️ **O dano não é só o número errado no relatório.** O consumidor usava a resposta para
*decidir onde cortar*: "esta ilha é muda" apara a ponta da janela. ⇒ com o ASR mudo, o app
estava **cortando material apostando** que o não medido era silêncio.

### A regra

> **`""` e `None` são coisas diferentes.** `""` é *perguntei e a resposta é nada*; `None`
> é *não houve medida*. Um `except` que devolve o valor neutro do tipo apaga essa
> diferença, e o resto do sistema nunca mais a recupera.

Três coisas, e as três se pagaram:

1. o adaptador devolve **`None`** na exceção, nunca o valor neutro;
2. quem decide tem um **rótulo próprio** para *não medido* — o número aparece no relatório
   em vez de se somar ao de silêncio;
3. ⭐ e a decisão é **conservadora**: sem medida, **não corta**. Uma medida faltando basta
   para segurar a janela — decidir onde a fala termina usando um trecho que ninguém olhou
   é a mesma aposta pela metade.

⚠️ Isso **não** contradiz *"erro não bloqueia o processo"*. O trabalho segue; o que muda é
que a falha ganha nome em vez de se disfarçar de resultado.

⭐ **A parte transferível, e ela é maior que o ASR:** vale para toda ponte com binário
externo — `ffprobe` que não roda vira duração `0`, um VAD ausente vira "não há voz", um
`ffmpeg` que falha vira arquivo de zero byte que a próxima rodada reaproveita. Ver o mesmo
padrão em [desenvolvimento-cross-platform.md](desenvolvimento-cross-platform.md) (o `XSym`:
**existir não é estar**) e em [../seguranca/README.md](../seguranca/README.md) §12.

⛔ **E a guarda de "o motor está pronto?" precisa conferir os EXECUTÁVEIS, não só os
modelos.** No mesmo dia, a checagem do app respondia `pronto: True` numa máquina sem
`whisper-cli`, porque só olhava os arquivos de modelo — e a pasta de binários que ela mesma
anunciava não existia.

---

## Ver também

- [medir-sync-contra-gabarito.md](medir-sync-contra-gabarito.md) — a matriz
  `acertou/errou × sinalizado/calado`, de onde o §3 e o §6 saem.
- [../protocolos/avb/escrita.md](../protocolos/avb/escrita.md) — escrever a bin de saída.
- [../protocolos/avb/sincronizacao-e-subclipes.md](../protocolos/avb/sincronizacao-e-subclipes.md)
  — som direto × som de câmera, e a anatomia da bin sincronizada.
- [analise-de-executaveis.md](analise-de-executaveis.md) — o que os concorrentes fazem de ASR
  (todos remotos, exceto o Jumper).

---

## 12. ⛔⛔ Conferir o mapa de corte — e por que conferir o TEXTO não basta — `confirmado` 2026-09-12

Quando o casamento roteiro↔material passa a ser feito por um **LLM** (e não por um casador
determinístico), nasce uma pergunta nova: *como saber que o plano que ele escreveu está
certo, antes de escrever bin nenhuma?* Três achados, em ordem de quanto doeram.

### 12.1 ⛔ Regra que ninguém confere não é regra, é conselho

O método da casa tinha regra escrita para os quatro sintomas que o editor nomeou — ordem do
roteiro, fala repetida, corte no meio de fala, corte em L/J. Medido: o modelo **consultou o
método 16 segundos depois de o turno abrir**, leu as quatro, e entregou uma cena que o
editor descreveu como *"horrível"*, com os quatro defeitos.

⇒ Prosa no prompt não é verificação. O que fecha é **escrituração no serviço**: o modelo
julga o casamento semântico (*"Sinceramente? Não!"* é a mesma fala que *"Sinceramente,
não."*), o código conta.

⚠️ E a regra de ordem **não é "cada fala uma vez"**. Três coisas parecem erro e não são:
**N→1** (duas falas seguidas do mesmo take viram um corte só), **1→N** (fala longa coberta
por dois ângulos colados) e **1→0** (fala sacrificada, desde que DITA). ⇒ A regra que
sobrevive às três é: a sequência de números de fala tem de ser **não-decrescente**, com as
ocorrências de cada número **contíguas**.

### 12.2 ⛔⛔ A escrituração sozinha APROVA a montagem ruim

Rodada contra os 15 cortes reais que o editor reprovou, a conferência de ordem e repetição
**passa**: as falas declaradas estavam em ordem, **15 de 16**, sem uma repetição.

O defeito não estava no que o modelo **disse** — estava no que ele **apontou**. Ele declarava
a fala certa e escrevia o timecode de outro take (*"Sinceramente, não."* está em 18,12 s no
P02-T002 e em 26,72 s no P02-T003; ele usou 18,12 no P02-T003). Na tela isso vira fala
repetida e diálogo fora de ordem, **enquanto o mapa parece impecável**.

⇒ **A âncora que pega:** confrontar o texto do roteiro com o que a transcrição diz *naquele
take, naquele intervalo*. Os dois textos já estão na casa e a conta é determinística —
sobreposição de palavras do roteiro encontradas no falado, ignorando palavras de ≤2 letras.

```
take certo ......................... 100%
take certo, com improviso do ator ... 90%   ("paciente" → "personagem")
TAKE ERRADO .......................... 9%
```

⭐ O piso (usamos 30%) cai num **abismo**, não numa borda — e tem de ser generoso, porque o
§1 deste arquivo já mediu que o ator não diz o que está escrito.

### 12.3 ⛔⛔ Validar *"a fala está mesmo aqui"* PREMIA o degenerado

E aqui a conferência se volta contra si mesma. Um modelo fraco (Haiku 4.5) mandou 16 cortes
em 5 takes, levou **duas reprovações legítimas** da âncora (parecença 12% e 15%), reenviou o
mapa **idêntico**, e então **colapsou os 16 cortes num take só** — o plano aberto que cobre a
cena inteira, onde **toda** fala bate 100%. O checker aprovou.

⇒ Um master que contém a cena inteira satisfaz *"a fala está mesmo aqui"* para todas as
falas. A conferência tinha transformado *"não aponte material errado"* em **"aponte tudo
para o take que sempre passa"** — e um modelo fraco achou o atalho em dois lances.

⭐ **A regra que fecha NÃO é cota de cobertura** — ritmo é ofício, e é do editor. É que
**cortar de um plano para ele mesmo é jump cut**: dezesseis emendas invisíveis são o take
tocado de ponta a ponta com as pausas tiradas. Plano-sequência legítimo se monta com **um**
corte, e esse passa. Junto vem a conferência de **trechos sobrepostos** do mesmo take (dois
cortes começando no mesmo frame), que a validação de esquema não pega.

⚠️ E a reprova tem de ser **curta**: a primeira versão devolvia **21 linhas** para esse mapa,
e num turno que já deu errado cada linha é contexto que o editor paga.

> ⇒ A lição geral, que vale para qualquer portão automático em cima de um LLM: **toda
> verificação define um gradiente, e o modelo desce por ele.** Antes de escrever a regra,
> pergunte qual é a saída mais barata que a satisfaz — porque é nela que o modelo vai cair
> quando a tarefa ficar difícil.

### 12.4 ⭐ O Resolve resolve o mesmo problema ESCOLHENDO, não conferindo — adicionado 2026-09-13

O IntelliScript do DaVinci Resolve 21.1 (monta o corte a partir do roteiro) deixa no binário
`invalid sentence similarity data`, `Invalid graph for obtaining best sequence` e `Failed to
find matching transcript sentences for script sentences` — ver
[ia-embarcada-nos-nles.md](ia-embarcada-nos-nles.md) §3.4. A técnica provável (`hipotese`,
pelos nomes) é **vetor de frase** roteiro × transcrição e **melhor caminho num grafo**.

⇒ A diferença de desenho importa mais que o motor:

| | quem propõe | quem garante a ordem e a não-repetição |
|---|---|---|
| conferir (§12.1–12.3) | o LLM escreve o mapa | a regra aprova ou reprova **um** mapa — e o modelo desce pelo gradiente dela |
| escolher (grafo) | o algoritmo | o próprio **caminho**: fora de ordem e repetição simplesmente não são arestas |

⭐ Um caminho ótimo num grafo **não tem saída barata para descer**: a sequência degenerada
da §12.3 só aparece se ela for, de fato, a de maior pontuação. ⚠️ O que o grafo não sabe é
ofício — ritmo, reação, o take que o editor prefere —, e é isso que continuaria com o modelo:
**escolher entre caminhos bons**, não montar a sequência do zero. `hipotese`, por medir contra
o gabarito da C07.
