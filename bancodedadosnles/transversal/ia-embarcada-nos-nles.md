# A IA que o Premiere e o Resolve embarcam — e o que isso ensina a quem constrói plugin

> **Medido em 2026-09-12/13**, Mac mini M4 16 GB, macOS 15.6.1, em modo leitura.
> **Adobe Premiere Pro 26.0.2** (2026) com o pacote Media Intelligence ·
> **DaVinci Resolve Studio 21.1 build 14** com todos os pacotes de IA baixados.
> Fonte: relatório "IA local e técnicas dos editores" (sessão do editor no Mac, 2026-09-13),
> registrado aqui pelo Ciclo Assist. ⚠️ **Não reconferido por nós no binário** — os níveis
> abaixo são os do relatório, traduzidos: ✅ → `confirmado`, 🟡 → `inferido`, ⚪ → `hipotese`.

⛔ **Todos os pesos estão criptografados** (CoreML `.mlem` na Adobe; `.bin` com cabeçalho
FlatBuffers no Resolve). Toda identificação vem de nome de arquivo, identificador de pacote,
mensagem de log e nome de classe — e **não houve nem haverá extração de modelo**, pela régua de
[analise-de-executaveis.md](analise-de-executaveis.md).

---

## 1. ⭐⭐ O achado que dá forma a tudo: nenhum dos dois usa LLM grande para olhar vídeo

Os dois usam **modelos pequenos e especializados, rodando na máquina**, e a busca visual é
**vetor**, não texto escrito por um modelo. `inferido` (padrão arquitetural consistente nos dois).

| | CLIP / vetores | LLM com visão (VLM) |
|---|---|---|
| responde | "o que se parece com esta frase/imagem" | qualquer pergunta, com julgamento |
| acha o que **ninguém descreveu** | ✅ | ⛔ só busca no que ele escreveu |
| lê texto (claquete, placa), conta, nega | ruim | bom |
| alucina | não | pode |
| memória | centenas de MB | 5–8 GB (7–12B) |

⭐ **O padrão da indústria é *retrieve then rerank*:** o vetor filtra o acervo inteiro em
milissegundos, e só o top-N vai para o modelo caro. É o que o modo *Better* do Resolve parece
fazer (§3).

---

## 2. Premiere Pro 26.0.2 — Media Intelligence

`/Library/Application Support/Adobe/Premiere Pro/26.0/<guid>/MediaIntelligence` — 529 MB,
instalado depois do app (`ccd-deferred`), pacote `MLModels/AdobeOne`.

| arquivo (`module/CoreML/v6/`) | tamanho | leitura | confiança |
|---|---|---|---|
| `A1V-B16BV-FP16` | 173 MB | codificador de **imagem**, ViT-B/16, FP16 | `inferido` |
| `A1T-B16BV-FP16` | 127 MB | codificador de **texto**, par do anterior — **padrão CLIP** | `inferido` |
| `audioclip_p16_audio` / `_text` | 63 / 180 MB | par imagem-texto para **som** | `inferido` |
| `nanoBERT-V2-float16`, `engClass_nanoBERT-fp16` | ~5,6 MB | classificadores da frase de busca | `inferido` |
| `animal`, `human` | 5 KB | classificadores por cima do vetor | `hipotese` |

- Motor: **CoreML** no Mac; o app também traz `libonnxruntime.1.19.0` (provável Windows,
  `hipotese`).
- ⭐ **Nenhum modelo gera texto.** Tudo é vetor e classificação. `confirmado` pela lista.
- A Adobe declara que a análise é local e não treina com o material. `confirmado` (doc oficial).

---

## 3. DaVinci Resolve Studio 21.1 build 14

### 3.1 Motores embutidos — `confirmado` (`otool -L`)

`libllama.0` + `libggml*.0` v0.9.4 (**llama.cpp**, o motor do Ollama) · `libonnxruntime.1.13.1`
· `libopencv_ml.409` · Metal / MPSGraph.

### 3.2 Pacotes baixáveis (`/Library/Application Support/Blackmagic Design/DaVinci Resolve/Extras/`)

| pacote | tamanho | técnica | confiança |
|---|---|---|---|
| AI IntelliSearch – Faster | 1,0 GB | vetores **UniIR** (CLIP + BLIP, TIGER-Lab/Waterloo) + vetor de **cor** | `inferido` |
| AI IntelliSearch – Better | 4,1 GB | Faster + várias consultas + nota por candidato (*rerank*) | `inferido`; uso de LLM `hipotese` |
| Transcrição + Extended Language Support 2 | 1,8 GB | **Whisper large-v3-turbo** (`ai/speech-recognition,2.0,large-v3-turbo`) | `inferido`; + alinhador forçado Kaldi só em inglês → [transcricao-por-palavra.md](transcricao-por-palavra.md) |
| AI Voice Training | 672 MB | **RVC** (VITS + NSF-HiFiGAN), PyInstaller + libtorch | `inferido` |
| AI Slate ID | 5,3 GB | leitura de claquete | `hipotese` |

### 3.3 IntelliSearch — as mensagens de log (`DaVinciIP/IntelliEdit/MediaSearcher.cpp`)

```
[MediaSearcher::QueryByText]: Color Query '%s', Color Embedding Results = %zu UniIR Encoding Results = %zu
[MediaSearcher::QueryByText]: Query '%s', numTokens %d, isLongQuery %s, isColorQuery %s
[MediaSearcher::GetSingletonQuery]: Query without filler words '%s'
[MediaSearcher::BetterMode]: converting to %zu queries
[MediaSearcher::BetterMode]: retrieved candidate %zu with score %.3f
[MediaSearcher::QueryByImage]
```

Pipeline deduzido (`inferido`): limpar a frase → detectar se é busca de cor → vetores UniIR e/ou
de cor → combinar e aplicar limiar → no *Better*, expandir em várias consultas e dar nota.

### 3.4 ⭐⭐ IntelliScript — montar a partir do roteiro

```
invalid sentence similarity data
Invalid graph for obtaining best sequence
Failed to find matching transcript sentences for script sentences
```

Técnica provável (`hipotese`, pelos nomes): **vetores de frase** roteiro × transcrição para a
semelhança, e **melhor caminho num grafo** para escolher a sequência e descartar repetições.
É o mesmo problema de [decupagem-por-transcricao.md](decupagem-por-transcricao.md) §12 — ver lá
a diferença entre **escolher** e **conferir**.

---

## 3b. Media Composer 25.6.0 — PhraseFind AI e ScriptSync AI (2026-09-13)

`medido` na instalação (`C:\Program Files\Avid\Avid Media Composer\PythonModules\`): o MC traz um
Python embarcado com **`faster_whisper` + `ctranslate2`** (58,9 MB), **`onnxruntime`** (com
provider CUDA de 450 MB e TensorRT), `tokenizers`, `kaldi_native_fbank` e `pythainlp`, com as
licenças em `LicenseFiles\Third_Party\PythonModules\`. ⇒ o PhraseFind AI é **busca em
transcrição Whisper**, não indexação fonética. `inferido` (pelos módulos; o código não foi lido).

`medido` na ajuda (`Help\Content\Editing_Guide\PhraseFind_AI.htm` e `Search_Tips_…`):
- escopo: *"audible dialogue throughout bins in a single project"* — as BINS do projeto, não o
  disco;
- sem diferença de maiúscula e pontuação; números têm de ser buscados como algarismos ("42", não
  "quarenta e dois") — sintoma típico de busca no TEXTO que o Whisper escreveu;
- transcrição gerenciada por bin, com identificação de falante e dica de idioma; 21 idiomas.

⚠️ O PhraseFind **antigo** (licença da Nexidia) indexava fonemas, e por isso achava nome próprio
que nenhum dicionário conhece. `hipotese` aqui — de memória, não conferido neste banco. A troca
tem custo: busca em transcrição só acha o que o ASR escreveu certo.

---

## 3c. ⭐⭐ Ler a CLAQUETE com um modelo de visão — MEDIDO (2026-09-22)

O equivalente nosso do "AI Slate ID" do Resolve (§3.2, `hipotese`). Medido no Ciclo Assist
(`motor/decupador.py`), acervo "PRODUCAO-A" (Blackmagic 4K convertido para 1080p), com o
`qwen3-vl:8b-instruct` no Ollama e gabarito lido à mão:

- ⛔ **Quem amostra quadros "longe das pontas" nunca vê a claquete** — e isso costuma ser
  proposital (a ponta descreve o que o take NÃO é). Ler claquete é um pedido SEPARADO, com
  quadros da CABEÇA (usamos 1 s e 3 s).
- ⚠️ **Resolução:** a 768 px, claquete que enche o quadro é legível; segurada longe num plano
  aberto vira mancha. A 1568 px lê-se rolo, cena e plano (o take num quadrinho vermelho
  ficou no limite).
- ⭐ **Formato real desta claquete brasileira:** ROLO · CENA · PLANO · **TOMADA** (não
  "take"), rolo = câmera + cartão (`A02`), e anotações à mão no campo (`PICKUP`). A
  americana pode ter só cena/take, com o plano na cena (`01-2`, `12A`) — relato do editor,
  `pendente` de material.
- ⛔⛔ **O modelo local COPIA o exemplo da instrução.** Com `"marcas": ["PICKUP"]` no exemplo,
  marcou PICKUP em 4 de 4 takes; na claquete pequena, devolveu o exemplo INTEIRO
  (`A02 · 4 · 6 · 2`) em vez de "ilegível". E um campo que não está na LISTA de campos da
  resposta ("exatamente estes campos") não é respondido: fora dela, `null` em 4 de 4.
- ⭐ **Conferência que não depende do modelo:** o nome do arquivo de câmera traz o rolo
  (`A009_…`, `A001C003`, `A001_C003`). Rolo lido que não bate → leitura inteira `hipotese`.
  Pegou o chute acima.
- Resultado final (8 imagens por pedido, 92–97 s por mídia no Mac): **3 de 3 claquetes
  legíveis certas**, 1 chute pego pela conferência. ⚠️ Claude (Haiku) **não medido**.
- **CORRIGE (2026-09-22, mesmo dia):** o exemplo da instrução era `A02 · 4 · 6 · 2` — a
  claquete REAL de um dos 3 takes medidos (A002_C002). Ali "leu certo" e "copiou o exemplo"
  davam o mesmo número: aquela 1 das 3 não provava nada. ⛔ **Regra: o exemplo de um prompt
  de extração nunca pode ser um valor do material de teste.** Refeito com `X07 · 31 · 8 · 5`
  (que não existe no acervo), na decupagem MICRO (quadros da cabeça no trecho inicial): as 3
  cabeças conferidas certas (A02·4·6·2, A01·4·4·1, A05·11·3·03) — e um trecho do MEIO do take,
  sem claquete, "leu" `31 · 8 · 5`, o exemplo novo. ⇒ Só o trecho da cabeça lê claquete.

### ⛔⛔ AMPLIADO em 2026-09-23: ele não lê mal — ele INVENTA na ausência

A §3c media 4 takes COM claquete. A primeira fila grande (Ciclo Assist, 537 mídias em
cache, 100 leituras de claquete gravadas) mostrou o outro lado, e ele é maior:

- **30 de 50 mídias com decupagem micro feita devolveram a cena/plano/take do EXEMPLO**
  (`31 · 8 · 5`) como se as tivesse lido — com o exemplo já trocado por um valor que NÃO
  existe no acervo, que era o conserto de 2026-09-22.
- ⭐⭐ **E a causa não é leitura ruim: é resposta onde não havia pergunta.** Abrindo os
  quadros da cabeça das quatro primeiras COM OS OLHOS: **não há claquete nenhuma** (plano
  de sala, ninguém com prancheta). As quatro de controle, essas com a claquete enchendo o
  quadro, foram lidas **certas 4 de 4**. ⇒ O modelo lê bem o que está lá; o que ele não faz
  é dizer *"não há"*. A instrução dizia `Sem claquete, omita. Nunca chute.` — não bastou.
- ⛔ **`texto` é o campo mais contaminado de todos:** o exemplo trazia `"texto": "como
  está"`, e as leituras devolveram a string `"como está"` — **inclusive as 4 CERTAS**.
  Quem usar esse campo como evidência do que foi lido está lendo o prompt de volta.
- ⛔⛔ **E o eco não se limita ao bloco de exemplo JSON.** Trocando os valores por
  `‹cena›`/`‹plano›` (impreenchíveis), o eco de `31 · 8 · 5` foi a **zero** e nenhum `‹…›`
  voltou — mas em **3 de 4** o modelo passou a devolver `rolo ["01-2"] · cena 01 · plano 2`,
  que é a FRASE SEGUINTE da instrução (`"01-2"/"12A" = cena 01 plano 2`), escrita ali como
  explicação de notação. ⇒ **Todo literal do prompt é material de cópia**, não só o exemplo.

⚠️⚠️ **A conferência do rolo (§3c) é necessária e INSUFICIENTE.** Ela compara o rolo lido
com o do nome do arquivo e pegou o chute de 2026-09-22 — mas medido em escala, **8 notas de
4 mídias** passaram por ela: o modelo leu o rolo CERTO (`A002_…` → `A002`, que ele vê no
burn-in ou deduz) e copiou só cena/plano/take. Uma segunda conferência, que não depende do
material, é comparar a resposta com o próprio texto da instrução.

⭐⭐ **A instrução que sobrou, medida em três rodadas** (8 mídias: 4 com claquete, 4 sem):

| instrução | eco do prompt | inventou onde não há | leitura perdida |
|---|---|---|---|
| exemplo com valores plausíveis (`X07 · 31 · 8 · 5`) | **7** | 4 de 4 | 0 |
| sem exemplo nenhum, campos descritos em PROSA | 0 | 3 de 4 | ⛔ **4 de 4** |
| `‹cena›` no lugar do valor, sem literal na prosa | **0** | 4 de 4 | **0** |

- ⛔⛔ **Os campos não podem sair da estrutura JSON.** Descrevendo-os em prosa ("copie o
  texto e dele tire rolo, cena…"), as 4 claquetes legíveis voltaram VAZIAS — e não por não
  ver: o `texto` trouxe a claquete inteira e certa (produção, `A01 ROLO 4 CENA 2 PLANO 2
  TOMADA`, cameraman e data), com **nenhum campo preenchido**. É o mesmo fato do §3c
  ("campo fora da LISTA não é respondido"), e ele derruba a solução mais óbvia.
- ⭐ **O que funciona é o LUGAR do valor** (`"cena": "‹cena›"`) dentro da estrutura
  completa, **e nenhum literal na prosa** — os dois juntos. Só o primeiro deixa o modelo
  copiar a frase de notação seguinte.
- ⭐ Efeito colateral bom: o campo de transcrição deixa de vir com o placeholder e traz a
  claquete escrita — o que abre uma conferência de coerência (o número lido tem de aparecer
  no texto transcrito) que ainda **não foi calibrada**.
- ⚠️⚠️ **Nada disso faz o modelo dizer "não há claquete"**: ele continuou respondendo nas
  4 mídias sem claquete. O que muda é a natureza do erro — de um mesmo valor plausível
  repetido em dezenas de mídias para chute aleatório, que a conferência do rolo pega. ⇒ A
  rede é a conferência; o prompt só decide se o chute é sistemático ou não.

### ⭐⭐ Um SEGUNDO acervo, e o que ele quebrou (2026-09-23, *PRODUCAO-F*)

Claquete de outra produção, no mesmo pipeline: **digital, com timecode em LED** e os campos
impressos **em inglês** — `ROLL # A02 · SCENE 25 · SHOT 6 · TAKE 5`, mais PROD/DIR/DOP/DATE.
Com luz boa, o modelo leu **os quatro campos exatos**. O que quebrou foi tudo em volta:

- ⛔⛔ **O nome do arquivo não casava com o padrão de rolo conhecido** (`A_0002C016_260629_
  125302_h1DF4` contra `A009_…`/`A001C003`). E isso é pior do que parece: sem referência no
  nome, a conferência do rolo **não tem com que comparar e aprova o que vier** — o acervo
  novo chega justamente desprotegido. ⇒ o padrão precisa cobrir `letra + separador opcional
  + 3 a 4 dígitos`.
- ⛔⛔ **O rolo da CLAQUETE não é o cartão do ARQUIVO.** Medido no mesmo dia de filmagem:
  `A_0002C002` (cartão 0002) tem claquete `ROLL # A01`, e `A_0002C016` (mesmo cartão) tem
  `ROLL # A02`. A claquete conta o ROLO da produção, que o assistente vira por outro
  critério. ⇒ conferir "rolo lido × rolo do nome" é um SINAL forte quando bate, e uma
  dúvida legítima quando não bate — não é prova de erro. `hipotese`, com 2 pares medidos.
- ⛔⛔ **Na claquete ilegível ele devolve o NOME DO ARQUIVO repartido nos campos.** Numa
  cena noturna em que só o timecode em LED estava aceso, o texto trouxe o TC certo
  (`08:30:08:12`) e os campos vieram `cena 260629 · plano 083016 · take h1DF4` — data, hora
  e sufixo do arquivo. ⇒ **O nome vai no cabeçalho do pedido, então ele é material de cópia
  como o prompt**, e a conferência tem de olhá-lo. ⚠️ Por TOKEN inteiro: a cena `4` de um
  take real está "dentro" de `03170345` como substring. ⛔ E **o campo do rolo fica de
  fora** dessa comparação — ele coincide com o nome por definição, e um OP-Atom ainda traz
  o sufixo de trilha `_A01`/`_A02`, que é o formato de um rolo.
- ⚠️ **Rótulo impresso vira valor:** `"cena": "CENA 1"`, `"plano": "SHOT 6"`. O rótulo está
  escrito embaixo de cada campo da prancheta, e ele lê o que vê.
- ⚠️ **Caligrafia:** `A01` escrito à mão vira `AO1` (o zero parece O) e `A05` vira `AuS`.
  Desfazer `O`→`0` na comparação recupera leitura certa; desfazer `U`→`0` **não** — medido,
  aprovaria uma leitura cujos números estavam errados (leu `4 · 4 · 4` onde a claquete diz
  `11 · 1 · 1`).

⚠️ Com claquete nítida: **leitura exata**. Em contraluz: **colunas deslocadas** (leu o SHOT
no lugar da cena). No escuro: **invenção**. A dificuldade do quadro prediz o erro melhor do
que qualquer outra variável observada aqui.

⭐ **A régua de produto que saiu disto** (Ciclo Assist, `motor/decupador.py`): o que a
conferência reprova continua GRAVADO e visível, marcado `hipotese` com o motivo, mas não
empresta valor a campo nenhum que alimente busca, filtro ou ordenação — e a promoção mora
DENTRO da conferência, para que um caminho que esqueça de conferir perca a promoção em vez
de ganhar um fato.

## 3d. Premiere 27.0 (Beta, Windows) — "Aprimorar áudio", créditos e o índice `.prin` (2026-11-05, piloto)

`hipotese` onde não diz medido. Material: `laboratorio-de-midia/referencias/sync-com-fala/producao-a` (WAV 5 canais, 92 s).

- **Os comandos** (menu nativo, ids estáveis — matriz §F): Clipe ▸ Aprimorar áudio ▸ Habilitar aprimoramento de áudio
  (11551), ▸ Dividir em clipes… (11552), Clipe ▸ Separar falas sobrepostas (11575). Medido: com item no PAINEL Projeto
  os três ficam cinza; com o clipe selecionado na TIMELINE só o 11551 acende. 11552 e 11575 ficaram cinza o tempo todo
  (inclusive depois de ligar o aprimoramento) — a condição deles NÃO foi achada.
- **O diálogo** "Aprimorar áudio" (`#32770`): *"Faça o diálogo soar como uma gravação profissional e divida-o em música,
  ambiente e efeitos sonoros para reequilibrar cada camada"* — **"Usa 16 créditos"** (92 s) [Cancelar] [Aprimorar].
  É o aprimoramento + SEPARAÇÃO EM CAMADAS (stems), cobrado em créditos generativos.
- **Duas fases, medidas por fora** (I/O do processo, `netstat`, CPU):
  1. "Aprimorar": conexões a `ec2-…us-west-2` e `ec2-…compute-1` (AWS, :443), ~5 MB escritos e 330 MB lidos em 6 s,
     depois quase nada por ~75 s; no `.prproj` nasce um CLIPE COMPOSTO (`MZ.EnhanceAudioCompoundClip=true`,
     `MZ.EnhanceAudioOriginalMasterClipNodeID`), `EnhanceSpeechModel=1` e uma `EnhanceAudioAcknowledgedRenderSignature`
     (GUID) por canal. Nenhum arquivo de mídia novo no disco. ⇒ ao que tudo indica, autorização/cobrança na nuvem.
  2. Ligar o interruptor da seção "Aprimoramento de áudio" (painel Propriedades): **"Preparando"**, ZERO rede, 668 MB
     lidos, ~1 núcleo de CPU contínuo (pico de 4) por mais de 5 min sem terminar ⇒ a inferência é LOCAL.
     ⚠️ O autor fechou o Premiere antes do fim: o RESULTADO (as camadas) não foi visto.
- **A pilha local** (instalação do Beta): ONNX Runtime com provedores TensorRT RTX (NVIDIA), OpenVINO (NPU Intel) e
  Vitis AI (`vaiml.dll`, NPU AMD), mais o `DVAML` da Adobe (`DVAMLTestAssets/*.onnx` são de teste). Nenhum modelo
  > 40 MB fora dos binários (o exe tem 950 MB) — os modelos parecem EMBUTIDOS. Nesta máquina a RTX 4050 não respondeu
  ao `nvidia-smi` (modo híbrido?) ⇒ provável CPU, o que explicaria a lentidão. ⬜ medir com a GPU ativa.
- ⭐ **O `.prin`** (gravado AO LADO do `.prproj` ao salvar; 906 KB aqui): gzip de um índice binário
  `LinearFeatureVectorIndex:AudioClipAudioFP16-20250912Temporal:1.0.0` — EMBEDDINGS de áudio em FP16, temporais,
  calculados localmente para a busca por conteúdo do Premiere. A mesma ideia da aba Busca do Ciclo Assist. ⬜ ler o
  formato (dimensão, passo no tempo) e ver se há o de vídeo.
- ⛔⛔ **Autor, 2026-11-05: o notebook NÃO aguenta IA local** (a mesma regra do Ciclo Assist: telas azuis com o MC aberto).
  Como a inferência do Aprimorar é LOCAL apesar dos créditos, NÃO ligar o aprimoramento neste notebook — testar no Mac
  mini ou numa máquina com GPU ativa.
- ⬜ Falta: ver o resultado (camadas, o que entra no projeto, onde o render fica), o custo real debitado (o saldo de
  créditos antes e depois), e a condição de "Separar falas sobrepostas" / "Dividir em clipes".

## 3e. Premiere 27.1 (Beta) no MAC mini M4 — o "Aprimorar áudio" visto até o fim (2026-11-06, piloto)

Medido (Ciclo Assist, sessão de 06/11; projeto descartável, a sequência montada pela ponte CEP). Material: o WAV de 5
canais do `sync-com-fala/producao-a` (92,09 s), que o `createNewSequenceFromClips` pôs em **5 trilhas mono**.

- **Custo:** com SÓ o clipe do Canal 1 selecionado (92 s, mono) o diálogo disse **"Usa 4 créditos"** — no Windows, o
  WAV de 5 canais num clipe só deu 16. ⇒ ao que tudo indica, por canal/tempo (`hipotese`: uma medida de cada). Com as
  5 trilhas selecionadas as Propriedades dizem "Vários clipes selecionados": selecionar UMA antes (custo × trilhas).
  ⬜ O saldo antes/depois não foi lido (onde a conta mostra os créditos: não achado).
- **O menu no Mac** (Clipe): "Habilitar Aprimorar fala" (cinza) · "Aprimorar áudio ▸ Habilitar aprimoramento de áudio"
  (acende com clipe na TIMELINE) · "Separar falas sobrepostas". Clicado pelo NOME (System Events) ✅. O diálogo
  "Aprimorar áudio" NÃO aparece na acessibilidade (`window "Aprimorar áudio"` = -1728) e o 1º clique sintético só
  ativou o Premiere; **Enter entregue com ele na frente** (o Aprimorar é o padrão) ✅.
- ⭐⭐ **A condição de "Dividir em clipes…" e "Separar falas sobrepostas" ACHADA:** os dois acendem DEPOIS do
  aprimoramento feito, com o clipe aprimorado selecionado (o botão "Separar falas sobrepostas" aparece também no rodapé
  das Propriedades). ⬜ Não acionados (custo/efeito ainda não pedidos).
- ⭐⭐ **Rede, não só local — corrige a leitura do Windows (§3d):** nos primeiros 30 s o processo ENVIOU 8,97 MB e
  RECEBEU 8,47 MB (`nettop`), ≈ 92 s mono 48 kHz 16 bits (8,84 MB). CPU subiu a 77 % e voltou a ~3 %; o Separando 0 % →
  pronto em **~1 min** (no Windows, "Preparando" > 5 min sem rede). ⇒ no Mac ao menos parte da separação é na NUVEM
  (o áudio sobe e volta); o caminho local do Windows pode ser outra rota (sem NPU/GPU usável). `hipotese` até medir a
  rede no Windows com a mesma régua.
- **Onde o render mora:** `<pasta do .prproj>/Adobe Premiere Pro (Beta) Captured and Generated/<projeto>/<clipe>-<guid>/`
  - `Enhance Speech V2 Sample 0-<amostras>.wav` — mono 16 bits 48 kHz: a FALA aprimorada;
  - `Sound Lift Sample 0-<amostras>.wav` — **5 canais** 16 bits: a decomposição. A soma dos 5 = o original
    (correlação **0,981**); **canal 0 = diálogo** (0,615 com a fala aprimorada; os outros ≈ 0). Canais 1–4 = ambiente,
    música, efeitos e um quinto (resíduo/reverb?) — `hipotese`, a ordem não foi ouvida.
  - No projeto: um item novo `<clipe> (Aprimorado)` (tipo 8, clipe composto: `MZ.EnhanceAudioCompoundClip`,
    `…OriginalMasterClipNodeID`, `EnhanceAudioAcknowledgedRenderSignature`), que SUBSTITUI o clipe na timeline, com o
    componente "Aprimoramento de áudio" (matchName `e8685c92-4799-4799-42b1-dbc3df3e3b2d`). Painel: Diálogo (volume +
    dois controles em 50 %), Som ambiente, Música, Efeitos sonoros — os volumes são o remix das camadas.
- ⭐⭐ **O `.prin` tem TRÊS índices** (FlatBuffers dentro do gzip; 906 KB com 2 clipes): `LinearFeatureVectorIndex:
  AudioClipAudioFP16-20250912Temporal:1.0.0` (offsets de 0x88C = 2.188 B por registro — ~1.024 dimensões FP16,
  `hipotese`), **`LinearFeatureVectorIndex:AdobeOneVisualB16-20240625:1.0.4`** (`VisualEmbeddingPayload`: o par
  imagem-texto da busca do painel) e **`FaceFeatureVectorIndex:RetinaFace-20221010+FaceNet-20260226:1.0.0`** —
  detecção e EMBEDDING DE ROSTO. ⇒ o Premiere indexa rosto localmente; o Ciclo Assist não faz reconhecimento facial.
  ⬜ Dimensão e passo no tempo de cada um.

- ⭐⭐ **"Separar falas sobrepostas" acionado** (mesma sessão; o clipe aprimorado do Canal 1, 92 s):
  1. 1ª vez na conta: diálogo **"Recursos de voz baseados na nuvem"** — consentimento de processamento BIOMÉTRICO
     (incorporações de voz) e declaração de que se tem a permissão das pessoas no material. ⛔ É do AUTOR clicar em
     "Concordo" (o piloto parou ali; o autor aceitou em 06/11).
  2. Diálogo "Separar falas sobrepostas" — *"Atribua uma faixa própria a cada voz"* — **"Utiliza 92 créditos"** = **1
     crédito por SEGUNDO** (o Aprimorar do mesmo clipe: 4). Enter = Separar ✅; o próprio diálogo mostra "Fazendo
     upload… N%". ⇒ Autor: *"não parece pensada para material bruto, e sim pequenos segmentos durante a montagem"* —
     5 mil créditos/mês não pagam 1 h de som (3.600 por canal).
  3. Rede: ~16 MB SUBIDOS, ~27 MB descidos; pronto em < 1 min. É NA NUVEM (o aviso diz).
  4. Resultado, na mesma `…Captured and Generated/<projeto>/`: `<clipe> (Aprimorado).falante_1.wav`, `.falante_2.wav`,
     `.plano de fundo.wav` (mono 16 bits 48 kHz, a duração inteira; soma dos três ≈ o original, 0,97). No projeto: uma
     bin `<clipe> (Aprimorado) - Separar falas sobrepostas` com os três e **3 trilhas NOVAS** (A6–A8) alinhadas; o
     original fica. Atividade: f1 24 % do take, f2 12 %, os dois juntos 4 %.
  5. ⭐⭐ **As vozes que ela separa são as LAPELAS que o som direto já tinha separado.** O iXML do take: interleave
     1–2 sem nome (a mixagem L/R), **3 = MIC2, 4 = MIC3, 5 = BOOM**. Com cada canal normalizado pelo próprio p95
     (janelas de 200 ms com fala): onde a MIC2 lidera, o `falante_2` domina **97 %**; onde a MIC3 lidera, o
     `falante_1` domina **88 %** (o boom liderando: f1 93 %). ⇒ falante_2 = ator da MIC2, falante_1 = ator da MIC3
     (n = 1 take; ⚠️ a 1ª conta desta seção nomeou os canais pela posição e trocou TrR/Tr3 por lapelas — corrigida).
     ⇒ em ficção com som direto multipista, "quem fala" já vem POR CANAL de graça (`metadado-de-canal-do-som-direto.md`); a separação paga
     serve ao que tem UMA pista (câmera, entrevista com um microfone, mix).
  - Nasceu também um modelo CoreML compilado no temporário (`/var/folders/…/T/<guid>.mlmodelc`) e
    `Analyzer Cache Files/*____Embedings.mfdc` — inferência local de apoio (o índice de busca?) — não investigado.

## 3f. ⭐⭐⭐ Premiere 27.1 (Beta) — o **AI Assistant** por dentro: um agente MCP com skills (2026-11-06, leitura estática)

Medido no Mac mini, Premiere Pro (Beta) **27.1.0.7**, só lendo o pacote instalado (nenhum prompt enviado, nenhum
crédito gasto). `confirmado` = está escrito no pacote; o comportamento em uso é `pendente`.

- **O painel é UXP** (`Contents/UXP/plugins/com.adobe.dva.creative-copilot`, 5 MB, React num webview, JS legível;
  commit `5ed094fd…`). Hosts declarados: **Premiere, After Effects e Media Encoder** — o mesmo agente nos três.
  Entradas: painel "AI Assistant (beta)", a barra "Composer" e o comando `cmd.aiassistant.delegate.task` ("Run
  delegated task"). `confirmado`.
- **O modelo não está no cliente.** O padrão é o **"Drover"**: `https://drover-chat-harness.adobe.io/api/v1` (e
  `adobe-chat-harness-va6.adobe.io`), com token IMS do client `ppro-dva-copilot` — o "chat harness" da Adobe decide o
  modelo no servidor. ⭐ Há uma tela de configuração (**"Debug config (internal)"**) que aceita modelo **"OpenAI
  compatible"** (endpoint + chave; padrão `gpt-4o` em `api.openai.com/v1`) e um "Mock server" de snapshots — ao que
  tudo indica só interna (`hipotese`: não vista na tela).
- ⭐⭐⭐ **As ferramentas são um servidor MCP NATIVO do Premiere** (classes `mcp::…Tool` no executável). São DOIS:
  | servidor | porta / caminho | quem usa |
  |---|---|---|
  | `assistant` | `[::1]:3111` `premiere/assistant/mcp`, token Bearer **novo a cada abertura** | o painel (medido: a porta responde `401` sem token) |
  | `user` | `localhost:3000` `premiere/mcp` (porta configurável), token opcional | **clientes de FORA** (Claude, etc.): Preferências ▸ **Agents** ▸ "Enable MCP server" + "Copy MCP Configuration" |
  ⛔⛔ **O `user` está TRANCADO numa beta feature da Adobe** (medido 2026-11-06, conta externa logada): a aba
  **Agents NÃO aparece** em Ajustes (o painel `DLG::AgentsPrefsPanel` existe no executável, escondido) e a porta 3000
  fica fechada. A bandeira é `PPro.MCP.EnableMCPServer` (ao lado de `PPro.AIAssistant`, `…SupportsSubAgents`,
  `…SkillsWindow`, `…ComposerBar`), do sistema `dvaappsupport::feature::BetaFeature`: liga para conta INTERNA
  (`@adobe.com`) ou por liberação remota (Floodgate), com "override" pelo Debug Database (`InitializeDebugDatabase
  Overrides`). As preferências são `HSL.Prefs.McpEnabled/McpPort/McpServer/McpPath/McpAuthenticationEnabled/
  McpAccessToken` (token no keychain, `PremierePro.MCP`). `listMCPTools(endpoint)`/`callMCPTool` existem, mas em
  módulos UXP INTERNOS (`require("uxp").hSLScripting.MCP`, liberados ao painel da Adobe pelas `dependencies` privadas
  do manifesto) — plugin de terceiro não os recebe (`hipotese`, não tentado). ⇒ Hoje não há porta oficial para nós;
  quando a Adobe liberar a bandeira, a aba Agents aparece. Ligar pelo override do Debug Database é decisão do autor
  (é abrir recurso que a Adobe ainda não liberou a contas externas).
- ⭐⭐⭐ **DESTRANCADO e MEDIDO (2026-11-06, autor autorizou; Mac, 27.1.0 build 7, conta externa):**
  1. Caminho: Cmd+F12 abre o **Console** (vista "Debug Database View"; a chave da bandeira NÃO aparece lá) ▸ menu ☰
     ▸ **"Open Test Host Plugin"** — executor de testes JS da própria Adobe (`com.adobe.dva.test.hostplugin`, roda
     `*.test.ts` com acesso aos módulos internos; 1ª vez pede a pasta de testes e a de assets; ⚠️ sem
     `outputDirectory` em `~/Documents/Adobe/test-host-plugin/config.yaml` a UI quebra calada ao rodar — "Cannot read
     properties of undefined (reading 'props')" no `UXPLogs_*.log` — e só volta reiniciando o Premiere). Os tipos
     embutidos (`@dva/types`) estão VELHOS (`listMCPTools()` sem argumento): usar `any`.
  2. No script: `require("uxp").dvaappsupport.BetaFeature.setFeatureFlagOverride("PPro.MCP.EnableMCPServer",
     FEATURE_FLAG_OVERRIDE_ON)` → `true` (o `isFeatureEnabled` só muda depois de REABRIR) e
     `require("uxp").hSLScripting.MCP.setPreferences({enabled: true, authenticationMode: 1})`. Antes: `interno=false`,
     `PPro.AIAssistant`/`SupportsSubAgents`/`SkillsWindow` = true, `ComposerBar` e `EnableMCPServer` = false.
  3. Fica GRAVADO: `~/Library/Preferences/Adobe/Premiere Pro (Beta)/27.0/Debug Database.txt` ganha
     `dvaappsupport.feature.PPro.MCP.EnableMCPServer	1` (desfazer: 0 ou apagar a linha, com o Premiere fechado);
     as prefs `HSL.Prefs.Mcp*` vão para o `Adobe Premiere Pro (Beta) Prefs` do perfil (o token também, e no keychain).
  4. Reaberto: **`[::1]:3000` escutando**. Protocolo: MCP Streamable HTTP (`POST /premiere/mcp`, resposta em SSE,
     `mcp-session-id`, `Authorization: Bearer <token>`), `protocolVersion 2025-06-18`, `serverInfo` "Premiere MCP
     Server" 0.0.2, capacidades tools/resources/prompts com `listChanged`. **`getOpenProjects` em 0,03 s**;
     `getProjectItems` lista bins/clipes/sequências com `itemId` e caminho.
  5. ⭐ `listMCPTools("assistant")` e o `tools/list` do `user` devolvem **as MESMAS 60 ferramentas** (esquema JSON
     completo, `annotations`, `_meta.keywords`). O `user` não serve as skills (0 resources, 0 prompts). Das 67 classes
     do executável, 7 não estão no catálogo (ao que tudo indica as de `MCP.EnableExperimentalTools`: som —
     `analyzeAudioQuality`, `classifyAudioClips`, `setAudioType`, Essential Sound — e `createSyntheticMedia`).
     O catálogo bruto fica FORA do banco (texto da Adobe): `~/ciclo_mcp/tools_assistant.json` no Mac mini.
  - **leitura (25):** `browseDirectory` `getAppliedEffects` `getAppliedTransitions` `getAvailableEffects` `getClipMetadata` `getColorClipMetadata` `getColorEffect` `getColorManagementSettings` `getEditingContext` `getEffectParams` `getExportPresets` `getInOutPoints` `getMarkers` `getMasks` `getOpenProjects` `getProgress` `getProjectInfo` `getProjectItems` `getSequenceStructure` `getTrackItemProperties` `getTranscript` `getTypeScriptDefinitions` `readTextDataFromFile` `renderFrame` `universalSearch`
  - **escrita (35; todas `destructiveHint` menos `editMask`):** `addEffects` `addTracksToSequence` `addTransitions` `autoReframe` `copyTrackItemAttributes` `createBins` `createMask` `createSequences` `createSubClips` `createTranscript` `deleteProjectItems` `deleteTrackItems` `deleteTracks` `editColorEffect` `editMask` `executeMCPScript` `exportMedia` `importAfterEffectsProject` `importFiles` `insertClipsToSequence` `interpretFootage` `manageMarkers` `moveOrCopyProjectItems` `moveOrCopyTrackItems` `razorTrackItems` `removeEffects` `removeTransitions` `renameProjectItems` `setColorManagementSettings` `setEffectParameters` `setInOutPoints` `setLabelColors` `setTrackItemProperties` `trackMask` `writeTextDataToFile`
  - Toda escrita declara "uma ação desfazível" (lote atômico). `writeTextDataToFile` só escreve na subpasta Assistant
    do scratch "Captured and Generated"; `deleteProjectItems` não apaga mídia do disco.
  - Debug Database depois do painel carregar: `Assistant.ModelOverride`, `Assistant.ToolDiscoveryMode`,
    `Assistant.ApplicationContext` (⬜ não investigados).
  - ⬜ Windows: mesmo caminho, não medido. ⬜ Se a Adobe liberar a bandeira por Floodgate, o override vira redundante.
- ⭐⭐⭐ **As ações MEDIDAS pelo MCP "user"** (2026-11-06, Mac mini M4, 27.1.0 b7; projeto descartável com 1 `.mp4`
  23,976 de 81 s, o WAV de 5 canais de 92 s do `sync-com-fala/producao-a` e 2 sequências; Ciclo Assist
  `spikes/o_mcp_do_premiere.py`, cliente stdlib). **23 de 23 etapas responderam.**
  | ação | tempo | o que se viu |
  |---|---:|---|
  | `getOpenProjects` · `getProjectItems` · `getSequenceStructure` · `getClipMetadata` | 1–9 ms | ids estáveis (`agentProjectId`, `itemId`, `nodeId`), tempos em segundos; `getClipMetadata` dá duração, `start`, fps, codec, canais, caminho; `mode: discover` lista os campos XMP que existem |
  | `getEditingContext` | 35 ms | monitor ativo, sequência ativa, agulha, in/out, seleção da timeline, item no Source |
  | `renderFrame` (clipe ou sequência) | 40–90 ms | PNG sem perda, cor CERTA (o mp4 conferido a olho), teto 1568 px (pedido 1568 → 1185×667 mantendo o aspecto) |
  | `createTranscript` (fila) → pronto | 1 s + **18 s** p/ 92 s | "Transcrevendo no dispositivo" (LOCAL); `getProgress` acompanha. Texto bom em PT ("Cena quatro. Plano quatro. Tomada três.", "Eu sou Personagem F, A terapeuta") |
  | `getTranscript` segments / words | 2 ms | segmentos LONGOS (7 em 92 s, até 18 s cada); palavras com início/fim. ⚠️ `diarization: "channel"` no WAV de 5 canais deu `speaker: "Desconhecido"` em tudo |
  | `universalSearch` | 30–50 ms (1ª: 2,3 s) | ver abaixo |
  | `executeMCPScript` (2 chamadas encadeadas) | 4 ms | funciona sem carregar skill nenhuma |
  | `getTypeScriptDefinitions` | 6 ms | 54 mil caracteres de tipos TS de todas as ferramentas |
  | `createSequences` (de um clipe) | 55 ms | sequência casada com o clipe, ativada |
  | `insertClipsToSequence` 3 pontos, `append` | 3 ms | V e A ligados; ⚠️ pedido 2–8 s entrou **1,96–7,966 s**: o tempo é arredondado PARA BAIXO no quadro (23,976) — mandar segundos de quadro exato (`n/fps`) |
  - ⭐ **Toda escrita é UM passo do Desfazer nativo**: Editar ▸ Desfazer tirou a inserção (a sequência voltou a 81,373 s).
  - ⭐⭐ **`universalSearch`**: o agente de **transcrição** acha em PORTUGUÊS e devolve o ponto exato da palavra
    (`FILTER` → `HSL.UniversalSearchAgentTranscript`: "Personagem F" em 26,58 s com a frase inteira em `previewText` e os
    limites do destaque; o Ciclo Assist acha a mesma fala em 26,04 s no som). ⛔ Os agentes **visual** e de **áudio
    semântico** só aceitam INGLÊS ("As pesquisas visual e de áudio são compatíveis apenas com o inglês") e o de áudio
    é RUÍDO: "woman sitting" → 43 resultados de áudio, "man" → 141, "office" → 104. ⇒ O TEXT sem filtro é inútil num
    acervo em PT; usar `FILTER` por agente. `analysisCoverage` diz por projeto se a análise visual/áudio está
    `complete`/`incomplete` (é a mesma dúvida de alcance que a aba Busca do Ciclo Assist põe na tela).
- ⭐⭐⭐ **F0 — o que faltava, MEDIDO** (2026-11-06, Mac, 27.1.0 b7; `spikes/o_mcp_do_premiere_f0.py`; clipes sintéticos
  com o nº do quadro em 12 barras binárias, lido na IMAGEM do `renderFrame`):
  1. **Quadro exato:** tempo mandado como `n/fps` exato erra 1 em 6 em 23,976 e 29,97 DF (o float cai um tiquinho
     abaixo e o Premiere arredonda PARA BAIXO); com **+1 µs ou meio quadro (`(n+½)/fps`) acerta 6/6 nas três taxas**,
     conferido na imagem. Vale também para o `renderFrame` (pedido 48 → viu 47 em 23,976). ⇒ mandar `(n+½)/fps`.
  2. **Subclipe:** `getClipMetadata` do subclipe dá a janela DIRETO (`start` 2 s, `end` 4 s = quadros 50–100 do
     arquivo; `duration` é a do master) — sem a conta "SubclipStart − TC do arquivo" da CEP. Na timeline, no
     `renderFrame` e no 3 pontos o tempo é RELATIVO ao subclipe (pedido 0,5 s → quadro 62 = 50 + 12).
  3. **Timecode:** `start` de arquivo é 0 (não é TC). O TC vem do XMP: `xmpDM:altTimecode` (vídeo) /
     `xmpDM:startTimecode` (WAV) com `timeFormat` (`23976Timecode`, `25Timecode`, `2997DropTimecode`) e
     `premierePrivateProjectMetaData:Column.Intrinsic.SoundTimeCode`. O WAV traz também `iXML:trackList` (nomes das
     lapelas) e `bext:*`. `mode: discover` lista ~60 campos por clipe.
  4. ⛔⛔ **Áudio multicanal: `insertClipsToSequence` põe UMA trilha de áudio por clipe** — e o canal que vai NÃO é
     o 1º: WAV sintético 5.0 com um tom por canal (100…500 Hz), inserido em sequência estéreo ou multicanal → o
     export tem SÓ o 200 Hz. O mesmo com um merged clip de 2 trilhas de áudio (entrou uma). ⭐ **Caminho completo:**
     `createSequences` a partir do clipe (traz 5 trilhas mono, os 5 tons no export) + `moveOrCopyTrackItems`
     (`copy: true`, `targetAudioTrack` por item) para a sequência de destino → **os 5 tons no export**. ⬜ aparar
     depois de copiar (`trimTrackItems`) não medido.
  5. **Merged clip** vem como `type: "sequence"` no `getProjectItems`; `getSequenceStructure` dele mostra os
     componentes com o deslocamento de cada um (imagem em 0 s, som em 236,695 s); `getClipMetadata` não dá
     `filePath`/`duration`. Inserção de 3 pontos de um merged funciona (V + uma trilha de A — item 4).
  6. **Concorrência:** `getProjectItems` ~1 ms sozinho, ~1,1 ms com 4 sessões em paralelo, ~1,6 ms com a ponte CEP
     trabalhando (`/vetores?nle=premiere` 0,08–0,3 s) — um não atrapalha o outro.
  7. **Escala** (cópia convertida de um projeto real do Windows, mídia offline): **613 itens em 24 ms** (4 páginas);
     `getClipMetadata` de 583 clipes em **225 ms** (12 páginas). Offline, `filePath` mantém o caminho de ORIGEM
     (`D:\MIDIAS DE TESTES\…`).
  8. **Token no Keychain:** `security find-generic-password -s PremierePro.MCP -w` abre o SecurityAgent pedindo a
     **senha de login do Mac** (Permitir Sempre · Negar · Permitir); negado → saída 128. ⚠️ "Permitir Sempre" põe o
     binário `security` na lista do item — qualquer processo que use o `security` passa a ler o token.
  8b. **Sem senha (máquina de DESENVOLVIMENTO, decisão do autor):** `hSLScripting.MCP.setPreferences({enabled: true,
     authenticationMode: 0})` pelo Test Host Plugin vale NA HORA (sem reiniciar: `initialize` sem token → 200) e
     só vai para o arquivo de prefs ao SAIR do Premiere (`HSL.Prefs.McpAuthenticationEnabled` 1 → 0); reaberto,
     200 sem token em 6 s. O servidor escuta só em `[::1]:3000` (IPv6 de loopback; pelo IP da rede não conecta) —
     cliente usa `http://[::1]:3000/…` ou `localhost` que resolva para `::1`.
  8c. **Usado pelo produto** (Ciclo Assist F1, 2026-11-06): projeto aberto, taxa da sequência ativa e a lista de
     mídias do projeto pelo MCP, com queda para a CEP. No Premiere real a lista é IGUAL à da CEP (nome, arquivo,
     bins) e a rota `/vetores?nle=premiere` foi de 53 ms (CEP) para 8 ms (MCP), com o Premiere ocioso. ⛔ Os ids
     do MCP (`itemId`, base64) NÃO são o `nodeId` do ExtendScript: não misturar as duas vias numa mesma operação
     que devolve id para a outra.
  8d. ⭐⭐ **Montar e editar pelo MCP, medido (Ciclo Assist F2–F4, 2026-11-06):** `trimTrackItems` NÃO está
     no catálogo; aparar = `razorTrackItems` + copiar/apagar. ⛔ A navalha NÃO encaixa no SOM: em
     `(n+½)/fps` cortou o áudio em n+½ (precisão de amostra) e a imagem em n+1; com `n/fps + 1 µs` os dois
     caem no quadro n. Caminho completo com todos os canais: sequência a partir do take + navalha + 
     `moveOrCopyTrackItems` (`copy`, `linked: false`, trilha por item) — corte em J e WAV de 5 canais
     conferidos na imagem e no export. Edição de uma CÓPIA (`moveOrCopyProjectItems copy`): extrair =
     navalha + `deleteTrackItems` + `timeOffset` negativo; abrir espaço = navalha + `timeOffset`. Merged
     clip reconhecível: todos os pedaços da estrutura dele levam o nome dele. `getEditingContext` dá a
     seleção do painel de projeto (`projectPanelSelection`). `moveOrCopyProjectItems` exige `parentId`:
     mover para a RAIZ não tem id. `renderFrame` devolve o PNG só no `content` (não no
     `structuredContent`). O id de preset (`getExportPresets`) muda a cada abertura do Premiere.
  8f. ⭐⭐ **Windows (Ciclo Assist F5, 2026-11-18, Win 11, Premiere 27.1.0 Beta):** `confirmado`.
     - **Ligar SEM o Test Host Plugin** (Premiere FECHADO): a linha
       `dvaappsupport.feature.PPro.MCP.EnableMCPServer<TAB>1<TAB>-1` no `%APPDATA%\Adobe\Premiere Pro (Beta)\27.0\
       Debug Database.txt` é lida (aparece em azul no Console; `isFeatureEnabled` = true), e nas prefs do perfil
       (`Documentos\Adobe\Premiere Pro (Beta)\27.0\Profile-<u>\… Prefs`) `<HSL.Prefs.McpEnabled>true</…>` +
       `<HSL.Prefs.McpAuthenticationEnabled>0</…>`. ⛔ `McpEnabled` com `1` não liga (o servidor ficou desligado até o
       `setPreferences`; ao sair o Premiere gravou `true`). `McpAuthenticationEnabled` aceita `0`.
     - Porta 3000 em `127.0.0.1` **e** `[::1]` (no Mac só `[::1]`). `getOpenProjects` 16–18 ms, `getProjectItems` 1 ms,
       `executeMCPScript` 23 ms. ⛔ o `path` do projeto vem `\\?\D:\…` (prefixo de caminho longo; o `filePath` dos
       clipes não) — matriz de plataforma, seção C.
     - Pelo código do Ciclo Assist (sem modelo): montar 2 pedaços 0,67 s (6/6 itens conferidos por quadro), ler a
       timeline 0,08 s, editar numa cópia 0,24 s com a prova (3 pedaços intocados iguais).
     - O Test Host no Windows CHECA O TIPO: `__dirname` sem declaração = TS2304 e nada roda; sem `__dirname` em
       tempo de execução o `fs.writeFileSync("./x")` vai para a pasta de onde o Premiere foi lançado.
     - `universalSearch` igual ao Mac: o agente de áudio responde "Future: Broken Promise"; uma busca foi cancelada
       em 12 s.
  8e. **Versões:** o servidor MCP só existe no **27.1 (Beta)** — 25.6.5 e 26.0.2 (Mac) não têm
     `PPro.MCP.EnableMCPServer`, `premiere/mcp` nem classe `mcp::*Tool`; o UXP "Assistant" deles é a geração
     anterior, sem MCP. `confirmado` (strings dos executáveis, 2026-11-06). Pelo CHAT do Ciclo Assist (Sonnet
     5.5) as ações de montar/separar/editar pelo MCP rodaram de ponta a ponta com cartão aprovado.
  9. `insertClipsToSequence` aceita um clipe em vários formatos de sequência; `exportMedia` (`direct`) de 2–6 s
     de áudio volta "complete" na hora — serve de instrumento de medida.
  - ⚠️ Armadilha do piloto (Mac): depois de um Cmd+Shift+G sintético no diálogo de arquivo, a reabertura seguinte do
    Premiere mostrou "Opções de redefinição" (o diálogo de modificadora apertada na partida) — "Cancelar" segue sem
    redefinir nada.
- **As 67 ferramentas** (nome MCP): projeto — `getProjectInfo` `getOpenProjects` `getProjectItems` `importFiles`
  `createBins` `moveOrCopyProjectItems` `renameProjectItems` `deleteProjectItems` `setLabelColors` `interpretFootage`
  `getClipMetadata` `createSubClips` `importAfterEffectsProject`; sequência — `createSequences` `getSequenceStructure`
  `insertClipsToSequence` `moveOrCopyTrackItems` `razorTrackItems` `trimTrackItems` `deleteTrackItems`
  `addTracksToSequence` `deleteTracks` `get/setTrackItemProperties` `copyTrackItemAttributes` `get/setInOutPoints`
  `getMarkers` `manageMarkers` `getEditingContext` (monitor ativo, sequência, item no Source, marcas); efeito e cor —
  `getAvailableEffects` `addEffects` `removeEffects` `getAppliedEffects` `getEffectParams` `setEffectParameters`
  `addTransitions` `removeTransitions` `getAppliedTransitions` `get/editColorEffect` `getColorClipMetadata`
  `get/setColorManagementSettings` `autoReframe`; máscara — `createMask` `editMask` `getMasks` `trackMask`; som —
  `analyzeAudioQuality` `classifyAudioClips` (até 200 por vez) `setAudioType` `get/setEssentialSound…`;
  fala — `createTranscript` (diarização `none|speaker|speakerChange|channel`, canal escolhível) `getTranscript`;
  ver — **`renderFrame`** (PNG até 1568 px de um item no tempo pedido — o modelo OLHA quadros); achar —
  **`universalSearch`** (consulta JSON aninhável TEXT/FIELD/FILTER/JOIN/MERGE sobre "agentes": metadado, transcrição,
  marcadores, visual semântico `AdobeOneVisual`, áudio semântico); disco — `browseDirectory` `readTextDataFromFile`
  `writeTextDataToFile` `exportMedia` `getExportPresets`; geração — `createSyntheticMedia`; e
  **`executeMCPScript`** + `getTypeScriptDefinitions`: o modelo escreve uma função JS async que chama as ferramentas
  em laço (o "programmatic tool calling"). `getProgress` acompanha jobs longos. `confirmado` (nomes); descrições
  parciais lidas.
- **Skills, como as do Claude Code:** 9 de fábrica em `Contents/Resources/AgenticSkills/<nome>/SKILL.md` —
  `media-search` `find-and-organize-media` `edit-and-review-sequences` `prepare-source-media` `color-grading`
  `masking` `mix-audio-with-essential-sound` `working-with-after-effects` `programmatic-tool-calling` — ⛔ **CIFRADAS**
  (`AGENC1.…`, até a descrição; servidas ao agente por `skill://premiere/` e `load_skill`). Não foram decifradas
  (régua de [analise-de-executaveis.md](analise-de-executaveis.md)). ⭐ **Skills do usuário, em texto aberto:**
  `~/Documents/Adobe/Common/Assets/Assistant Skills/Premiere/<nome>/SKILL.md` (existe e está vazia aqui), com as regras
  do Claude Code: cabeçalho `---` com `name` (minúsculas, números, hífen; = nome da pasta) e `description`, UTF-8.
- **Permissão** (o seletor do compositor): *Always ask* · **Only ask before disk and generative actions** · *Never
  ask*. Cartões: "I'd like to run the action …" [Proceed · Always proceed · Deny]; disco: *"…will get access to your
  local disk"*; crédito: *"…permission to run @0. This uses @1 generative credits"* [Approve · Decline]. Perguntas ao
  editor com opções ("@0 of @1", Skip/Next/Submit). Mensagens podem ser ENFILEIRADAS; tarefa continua no fundo ao
  abrir chat novo. `confirmado` (textos).
- **Desfazer por resposta:** cada resposta guarda um `checkpoint` do projeto; "Undo" desfaz aquela resposta E as
  seguintes, da última para a primeira; recusa com *"edits unrelated to the assistant have been performed"* se o
  editor mexeu à mão (`non_mcp_actions`). `confirmado` (código).
- **Custo:** créditos generativos por resposta ("Used @0 credits"), cotas diária/semanal, paywall do Firefly,
  bloqueio por administrador. ⬜ Quanto custa um chat comum (não gerativo) — medir.
- **Anexos e referência:** até N arquivos, "copie e cole da timeline e da bin para referenciar", e um **pincel de
  anotação** (vermelho/verde/azul) para desenhar sobre o monitor e mostrar ao modelo onde.
- **Os exemplos de prompt** (o que a Adobe acha que vende): organizar por diária, renomear em lote por transcrição e
  metadado, montar um corte de 60 s "fazendo perguntas de profissional", **"Create a line-by-line sequence"** (todos
  os takes de cada fala agrupados com um marcador — o `separar_falas` do Ciclo Assist), **"Detect and mark slates"**
  (marcador no ponto da claquete), **"Organize speakers onto separate tracks"**, máscara e blur de rostos com
  tracking, auto-reframe 9:16, exportar em lote, limpar duplicados, converter alta taxa para 24.

⬜ **Pendente (dinâmico):** ligar o MCP `user` e ler o catálogo com esquemas/annotations; rodar 2–3 exemplos num
projeto de teste olhando rede e créditos; ver se o `universalSearch` usa o `.prin` (§3e) e se o `renderFrame` é o que
o modelo usa para "ver". REA (bundle do webview, Frida no processo) só se o estático e o `tools/list` não bastarem.

## 4. O que isto muda para quem constrói plugin

1. **Busca por frase não precisa de LLM, e não precisa de ninguém ter olhado antes.** Um
   par CLIP/SigLIP responde "praia ao pôr do sol" sobre acervo não decupado. ⚠️ Um
   classificador usado como extrator (o MobileNetV2 de
   [busca-visual-no-acervo.md](busca-visual-no-acervo.md)) **não faz isso**: não tem codificador
   de texto.
2. **A descrição escrita por modelo é a camada de cima, não a de baixo.** VLM para explicar o
   top-N; vetor para achar os N.
3. **Transcrição boa é Whisper grande.** O Resolve embarca large-v3-turbo; o Media Composer 2025
   embarca `small` (ver [decupagem-por-transcricao.md](decupagem-por-transcricao.md) §8).
4. **Equivalentes abertos existem para tudo** (verificar licença): SigLIP 2 / OpenCLIP /
   MobileCLIP (imagem-texto) · CLAP (som) · whisper.cpp / mlx-whisper · bge-m3 /
   multilingual-e5 (frase, bom em PT) · PySceneDetect (troca de plano) · sqlite-vec / LanceDB.

---

## 5. Como repetir

```bash
find "<App>.app" -iname "*.onnx" -o -iname "*.mlmodelc" -o -iname "*.gguf"
otool -L "DaVinci Resolve.app/Contents/MacOS/Resolve" | grep -iE "onnx|ggml|llama"
xxd -l 32 arquivo.bin                     # GGUF? FlatBuffers? criptografado?
strings Resolve | grep -E "MediaSearcher|IntelliScript|^ai/"
```

⚠️ Os nomes de pacote e os caminhos mudam entre versões — conferir a versão antes de citar.

## Fontes

Ciclo Assist, fila de decupagem no cache real (537 mídias, 100 leituras de claquete) e `spikes/o_exemplo_que_o_modelo_copia.py`, 2026-09-23, qwen3-vl:8b-instruct no Ollama 0.33.3; relatório do editor (2026-09-13); [Adobe — Media intelligence and Search panel](https://helpx.adobe.com/uk/premiere-pro/using/media-intelligence-and-search-panel.html) e
[FAQ](https://helpx.adobe.com/premiere-pro/using/media-intelligence-and-search-panel-faq.html);
Puget Systems (2025-02-27); Larry Jordan, *IntelliSearch in DaVinci Resolve 21*; Digital
Production (2026-07-29); repositórios TIGER-AI-Lab/UniIR, RVC-Project, openai/whisper.
