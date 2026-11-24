# Transcrição por palavra: como os NLEs acham a borda de cada palavra, e o que isso vale em português

> **Medido em:** DaVinci Resolve Studio **21.1.0 build 79** (DVIP `fe6d4a6b`), macOS 15 (Mac mini M), 2026-11-11.
> Comparado com o ASR do Ciclo Assist (`faster-whisper 1.2.1` `small` int8, `word_timestamps=True`, VAD 500 ms).
> Premiere Pro 2026 (26.0.2) medido em §5b. Premiere Beta 27.1 em §5c. Media Composer: **pendente** (ver §6).
> Spike: `_CICLO ASSIST/spikes/transcricao_por_palavra/` (gerar o gabarito, ler o `Project.db`, comparar).

## 1. O pipeline do Resolve (`confirmado` pelos símbolos; a ordem é `inferido`)

Lido com `strings` no binário `Resolve` (1 GB) — `DaVinciIP/SpeechRecognition/*.cpp`:

```
VAD (VAD.cpp)  →  Whisper large-v3-turbo próprio (SpeechAnalyzer: Encoder/Decoder/KV-cache, Metal)
               →  tempo por token (ComputeTokenTimestamps / …Accurate; "Use fallback method to get word timings")
               →  ⭐ ALINHADOR FORÇADO Kaldi (ASRForcedAligner.cpp + KaldiASR.cpp)
                    rede acústica com i-vector, léxico (words.txt, phones.txt, L_disambig.fst, word_boundary.int),
                    HCLG montado na hora com um n-grama do TEXTO que o Whisper escreveu ("realign")
```

- Não é whisper.cpp (o `libggml` do pacote é de outra coisa): é implementação própria (`DVIP::SpeechRecognitionImp`).
- O alinhador só roda se `IsForcedAlignmentRequested && IsSupportedTranscriptionLanguage`
  (`[SpeechAnalyzer::ProcessChunk] Forced alignment skipped: …`). Os modelos ficam em `Contents/Resources/<md5>.bin`,
  cifrados — não decifrados (régua de [analise-de-executaveis.md](analise-de-executaveis.md)).
- O log normal (`logs/davinci_resolve.log`) não traz as mensagens do `SpeechAnalyzer`; traz só
  `Audio Transcription: Transcribe clip N from frame A to frame B, fps 24.0` — o pedido é feito em QUADROS.

## 2. ⭐⭐ O alinhador forçado só vale para INGLÊS — medido contra gabarito exato

Gabarito sintético: cada palavra falada à parte pelo `say` do macOS (voz Eddy pt_BR e en_US), aparada pela energia e
colada — dentro da frase com vão 0, 60 ou 150 ms, entre frases pausas de 0,25 a 3 s. A borda de cada palavra é
conhecida à amostra. 10 frases por idioma (53 palavras PT, 62 EN). `confirmado`, n pequeno, fala sintética.

| | começa a ≤ 1 quadro (42 ms) | termina a ≤ 1 quadro | coladas na seguinte | fim de frase que CORTA a voz (> 1 q) |
|---|---|---|---|---|
| **Resolve, inglês** (alinhador ligado) | **97 %** (\|p90\| 35 ms) | **76 %** (\|p90\| 68 ms) | 12 / 61 | **0 de 10** (mediana +40 ms: sobra, nunca falta) |
| Resolve, português (sem alinhador) | 30 % (\|p90\| 245 ms) | 25 % | 45 / 54 | **8 de 10** (mediana −123 ms) |
| Ciclo Assist, português (faster-whisper small) | 6 % (\|p90\| 286 ms) | 6 % | 41 / 52 | **9 de 10** (mediana −187 ms) |

⇒ **A precisão que se vê no Resolve é do alinhador, e em PT ele não existe.** Em português o Resolve é Whisper puro,
um pouco melhor que o nosso `small` (o dele é o large-v3-turbo), com os mesmos defeitos: palavra colada na seguinte
(o fim é o início da próxima, não o fim da voz) e fim de frase cortando a voz.

Material real confirma (take `PRODUCAO-A - 05-04 C4 P1-T001.WAV`, 9 min, 5 canais): Resolve PT × nosso, palavras
casadas pelo texto (584): diferença mediana ~30 ms, \|p90\| 219 ms no início; Resolve com **1067 de 1071** entradas
coladas na seguinte (um alinhador deixaria vão); e os mesmos artefatos de Whisper nos dois (um "Eu" de 1,5 s que
engole a pausa antes dele, no Resolve; palavras de duração zero, no nosso).

- ⚠️ O nosso `small` sai **~126 ms adiantado** em início E fim no sintético (o áudio mixado não está deslocado:
  conferido por correlação). Não foi medido em fala real contra gabarito.
- ⚠️ O idioma do projeto MANDA: com `transcriptionLanguage = pt`, o clipe em inglês saiu **traduzido** para português
  ("I think we should…" → "Eu acho que nós devemos…"). Para o alinhador rodar, o idioma tem de ser `en` antes de
  transcrever (`project.SetSetting('transcriptionLanguage','en')` + `ClearTranscription` + `TranscribeAudio`).

## 3. Onde o Resolve guarda a transcrição (`confirmado`)

- No `Project.db` (SQLite) do projeto, tabela `BtLockableBlob`, coluna `FieldsBlob`: cabeçalho UTF-16 `BlobData`,
  depois **zstd** (`28 b5 2f fd`) → protobuf `Sm2ItemLockableBlobProto`, campo 6 `transcriptSegments` repetido,
  campo 8 o idioma (`pt`).
- `TranscriptSegmentProto`: 1 `starttime` e 2 `endtime` (**float32, segundos REAIS desde a meia-noite do TC** —
  o início do arquivo é `quadros_do_TC × 1001/24000` a 23,976), 3 `text`, 4 `isdisabled`, 5 `speakerid` (−1 sem
  falante). Campo zerado é omitido (o primeiro silêncio, em 0 s, vem sem o campo 1).
- **Não há segmento gravado**: é UMA lista plana de palavras, silêncios `(...)` (com duração) e quebras `"\n"`
  (duração zero). A "frase" da janela e da API é montada a partir das `"\n"`.
- Resolução interna: múltiplos de **1/256 s** (3,9 ms) num TC das 11 h — é o float32; às 23 h vira 7,8 ms.
- Sem `zstandard` no Python: `zstd -d -c` (Homebrew) descomprime.

## 4. A API arredonda para BAIXO (`confirmado`, 756 de 772 nos dois lados)

`MediaPoolItem.GetTranscription()` → `segments[].words[]` com `start`/`end` em **TC de quadro** =
`floor(segundos × fps)` no início **e no fim** (os 16 casos fora disso são borda do float32). ⇒ o Out de uma palavra
pela API cai até 1 quadro ANTES do fim dela. `(...)` é palavra com tempo, e aparece também no MEIO de um segmento
("Sobe comigo, agora!(...) A câmera…").
### ⭐⭐ A seleção na janela AI Transcription → In/Out no Source (`confirmado`, 2 seleções, 2026-11-11)

Selecionar texto na janela marca In/Out no monitor Source do clipe (`MediaPoolItem.GetMarkInOut()` → `audio.in/out`, em
quadros desde o início do clipe). Regra medida contra o tempo interno (§3):

| seleção | palavra(s), em quadros | In / Out |
|---|---|---|
| "com … tal." (arrasto do autor) | 3175,40 → 3289,48 | **3175 / 3288** |
| "Não." (duplo clique, piloto) | 3130,82 → 3136,53 | **3130 / 3135** (arredondar daria In 3131) |

⇒ **In = piso(início × fps); Out = piso(fim × fps) − 1**, e o Out do Resolve é INCLUSIVO: a seleção cobre
`[piso(início), piso(fim))`. A cabeça ganha até 1 quadro antes da palavra (seguro); a CAUDA perde a fração do último
quadro (20 e 22 ms medidos — até 41 ms a 23,976). Num corte colado ao fim da palavra, é aí que "vaza para dentro": o
último fonema pode ser cortado. A linha da janela usa o mesmo piso (`[11:26:42:21 - 11:26:48:01]`: o fim é o piso do
fim do "tal.").
- ⚠️ A janela (título "Auto Caption", `AXUnknown`, camada 3 — flutuante) só aparece com o Resolve em FOCO; com outro
  app na frente ela some (autor, 2026-11-11). Para pilotá-la: trazer o Resolve à frente e agir no mesmo comando.
- Duplo clique numa palavra seleciona a palavra (sem o espaço) e já marca o In/Out.

## 5b. ⭐⭐ Premiere Pro 2026 (26.0.2, Mac, 2026-11-11) — o melhor em português, e a seleção com FOLGA

Mesmo gabarito sintético, transcrição pelo painel Texto ("Transcrever origem", sem rotular oradores; o autor
transcreveu, o piloto mediu). Motor PRÓPRIO da Adobe (pacotes `SpeechESL` em `/Library/Application Support/Adobe/
Premiere Pro/26.0/`); **sem Whisper** no 26 — o Beta 27.1 traz `WhisperTokenizer/whisper-large-v3-turbo` e
`whisper-base` (⬜ não medido).

| contra o gabarito | começa a ≤ 1 q | termina a ≤ 1 q | coladas | fim de frase que corta a voz |
|---|---|---|---|---|
| **Premiere 26, português** | **75 %** (\|p90\| 68 ms) | 49 % (\|p90\| 85 ms) | 24 / 53 | 5 de 10 |
| Premiere 26, inglês | 52 % (\|p90\| 86 ms) | 52 % | 32 / 61 | 6 de 10 |

- ⭐ Em PT ele é de longe o mais preciso dos medidos (Resolve PT 30 %, nosso 6 %); o mesmo desempenho nos dois idiomas
  ⇒ o alinhamento não depende de idioma. Erro SISTEMÁTICO: tudo uns **26–41 ms adiantado** (início e fim) — por isso
  metade das frases termina cortando a voz. Corrigível somando ~40 ms (não testado).
- Palavras NÃO coladas por padrão: deixa vão real entre elas (só ~45 % coladas, contra 80–98 % do Whisper).

### Onde ele guarda (`confirmado`)

`.prproj` (gzip XML) → `<ExternallyProvidedTranscriptDocument>` com `<TranscriptProvider>` (GUID
`9a139944-f00d-4f74-ac45-751e998bb5dc`, o mesmo nos dois clipes) e `<TranscriptData Encoding="base64">` = **FlatBuffers**.
Por palavra, uma tabela: **início e duração em `int64` de ticks** (254 016 000 000 por segundo; valores em passos de
10 ms), o texto, a **confiança** (`float`, 0,62–1,0) e, na última palavra da frase, dois campos a mais (`pendente`).
Idioma dentro do blob: `pt-pt` (a opção escolhida na lista) e `en-us`; orador `Orador 1`. O silêncio aparece na tela como
`[···]`, sem entrada própria encontrada (`pendente`). ⭐ O nome `ExternallyProvided…` sugere que o formato aceita
transcrição feita fora — caminho para o autor levar a NOSSA transcrição para o Premiere (`hipotese`, futuro).
As marcas do clipe: `<InPoint>`/`<OutPoint>` em ticks no `<Clip>` do master (só aparecem depois de SALVAR).

### ⭐⭐ Seleção no painel Texto → In/Out (`confirmado`, 3 seleções, 6 bordas)

| seleção | palavras | vão antes / depois | In / Out |
|---|---|---|---|
| "But … understand" (autor) | 12,780 → 15,780 | 0,45 s / 0,09 s | 12,740 / 15,825 |
| "what" | 15,870 → 16,290 | 0,09 s / 0,03 s | 15,825 / 16,305 |
| "doubt it." | 11,490 → 12,330 | 0 / 0,45 s | 11,490 / 12,370 − 1 amostra |

⇒ **cada borda avança até a METADE do vão para a palavra vizinha, com teto de 40 ms** (In = início − min(vão/2, 40 ms);
Out = fim + min(vão/2, 40 ms)). Em tempo de amostra, não de quadro. É o oposto do Resolve (que corta para dentro):
o Premiere protege a cauda e a cabeça, sem invadir a palavra vizinha. Como os tempos dele vêm ~35 ms adiantados, a
folga de 40 ms quase só compensa isso no fim.
- ⛔ Duplo clique numa palavra **entra na edição do TEXTO da transcrição** (caixa azul) e limpa as marcas — Esc sai sem
  mudar nada. A seleção é por ARRASTO.
- ⚠️ Com o painel Texto e o Source no mesmo grupo, um esconde o outro; lado a lado (layout do autor) os dois ficam.

## 5c. Premiere **Beta 27.1** (Mac, 2026-11-11) — Whisper, pelo MCP, sem um clique

`importFiles` → `createTranscript` (`language` `pt-br`/`en-us`, `diarization: none`; fila, pronta em ~5 s para 40 s de
áudio) → `getTranscript` com `detail: "words"` → `{startTime, endTime, text}` em segundos (passos de 10 ms). O projeto
precisa estar aberto (criar projeto não tem ação no MCP; foi pela tela).

| contra o gabarito | começa a ≤ 1 q | coladas | fim de frase |
|---|---|---|---|
| Beta, português | 4 % (desvio fixo −106 ms) | 17 / 49 | corta a voz 5 de 10 |
| Beta, inglês | 72 % | 24 / 61 | **engole silêncio 10 de 10** (mediana +265 ms) |

- ⛔ Em PT ele **perdeu palavras** ("Eu", "Vamos") e devolveu 4 entradas **sem `text`** (só tempo) — quem lê tem de
  aguentar a chave ausente. O 2026 (motor próprio) acertou todas.
- ⭐ Separando o DESVIO FIXO (todas as palavras deslocadas igual — corrigível somando um valor) do ESPALHAMENTO:

| (sem o desvio fixo) | desvio fixo | começa a ≤ 1 q | \|p90\| início |
|---|---|---|---|
| Resolve EN (alinhador) | +1 ms | 97 % | 36 ms |
| **Premiere 26 PT** | −26 ms | **89 %** | 42 ms |
| Premiere Beta PT | −106 ms | 71 % | 60 ms |
| Ciclo Assist PT (small) | −126 ms | 34 % | 160 ms |
| Resolve PT | −76 ms | 30 % | 176 ms |

  ⇒ o nosso ASR erra por ESPALHAMENTO, não só por desvio: somar uma constante não o salva. ⚠️ O desvio fixo foi
  medido com UMA voz sintética; em fala real ele pode mudar (⬜).
- ⬜ A seleção no painel Texto do Beta → In/Out (não medida; o `getInOutPoints` do MCP lê as marcas sem salvar).
- Saídas (palavras de cada motor em JSON): `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_CICLO ASSIST/2026-11-11 TRANSCRICAO POR PALAVRA/`.

## 5. O que isto muda para quem constrói (Ciclo Assist e família)

1. **Trocar o Whisper não resolve a borda.** O modelo maior melhora o texto e pouco a borda (30 % contra 6 % a
   ≤ 1 quadro); o salto para 97 % é do **alinhador forçado**. A peça que falta em PT é um alinhador.
2. Caminhos sem torch para PT (a decidir, nada medido): CTC wav2vec2/MMS em ONNX com Viterbi em numpy (o texto do
   Whisper como transcrição dada); ou a borda pela ENERGIA da lapela de quem fala (`edicao_de_cena/bordas.py`, sem
   modelo, só nas bordas de frase). ⛔ Na MISTURA de canais a energia não serve de juiz (o piso alto faz a voz
   "continuar" sempre) — medido de novo aqui: com "algum canal acima do piso" todas as bordas batem no limite.
3. Guardar o tempo em **segundos** e converter para quadro só na saída; ao converter um **Out**, arredondar
   para CIMA (o Resolve arredonda para baixo e corta até 1 quadro do fim da palavra).
4. Ter o silêncio como entrada explícita da lista (o `(...)` do Resolve) é o que deixa a janela oferecer "selecionar
   a pausa" — e, num corte, "tirar a pausa".

## 6. Pendente

- ⬜ Media Composer (`faster_whisper` embarcado, PhraseFind AI / ScriptSync AI): mesmo gabarito — precisa do
  Ultimate (trial; autor, 2026-11-11).
- ⬜ Gabarito com fala HUMANA (o sintético não tem coarticulação nem respiração): o laboratório de mídia pode gerar
  com a lapela gravada à parte, ou marcar à mão um take curto.
- ⬜ Que idiomas o alinhador do Resolve suporta além do inglês (só EN e PT medidos).

## 7. ⭐⭐ Um alinhador CTC para PT, sem torch (fase L0 do Ciclo Assist, Mac mini, 2026-11-11)

Spike: `_CICLO ASSIST/spikes/transcricao_por_palavra/alinhar_l0.py` (Viterbi CTC em numpy, ~40 linhas; ONNX no onnxruntime 1.30)
+ `medir_l0.py` (gabarito sintético) + `medir_real.py` (fala humana × Premiere 2026). Plano: `_CICLO ASSIST/docs/plano/2026-11-11-alinhador-por-palavra.md`.

**Modelos medidos** (todos 16 kHz; `confirmado` nesta máquina):

| modelo | onde se acha | passo | int8 | resultado |
|---|---|---|---|---|
| `jonatasgrosman/wav2vec2-large-xlsr-53-portuguese` | HF `onnx-community/…-ONNX` (só fp32/q4); int8 gerado com `quantize_dynamic(MatMul)` | 20 ms | 355 MB | ⭐ bom; int8 = fp32 na régua |
| Omnilingual ASR 300M CTC v2 (Meta, 1600 línguas) | release `asr-models` do sherpa-onnx | 20 ms | 290 MB | ⭐ igual ao de cima em PT; um modelo para todas |
| NeMo `stt_pt_fastconformer_hybrid_large_pc` (ramo CTC) | idem | **80 ms** | ~100 MB | ⛔ o único pequeno; o CTC dele erra ~300 ms (p90), nem a energia salva |

- ⚠️ Não há CTC pequeno (≤ ~100 MB) e bom em PT com passo de 20 ms (busca no HF e no sherpa, 2026-11-11). Todo wav2vec2 PT é `large` (300 M).
- Omnilingual: entrada = onda crua normalizada (média 0, var 1), branco = id 0 (`<s>`), espaço = `|`, letras minúsculas.
  wav2vec2 HF: idem, branco = `<pad>` (0), espaço = `|` (4). NeMo: log-mel 80 (pré-ênfase 0,97, janela 400 em n_fft 512, passo 160,
  Slaney, log + 2⁻²⁴, normalização por banda), subpalavras (`▁`), branco = último id.
- ⚠️ numpy 2: `int + int8` dá int8 (NEP 50) — o backtrace do Viterbi com ponteiros int8 estoura sem `int(...)`.

**⭐⭐ O CTC acerta o INÍCIO e erra o FIM** (`confirmado`, sintético e take real): a última letra é emitida cedo — fim mediano
**−134 ms**, espalhado de −11 a −212 ms, 9 de 10 fins de frase cortando a voz. O início tem desvio quase FIXO: **+36 ms** no sintético,
**+41 ms** no take real contra o Premiere (sem o desvio: 91 % e 84 %). Fricativa inicial ("sala", "cena") atrasa mais (+100 a +170 ms).

**⭐⭐ A energia conserta a borda** (camada 3): a partir da borda do CTC, andar até a energia cair abaixo de
`max(piso + 15 dB, pico da palavra − 30 dB)` (envelope de 10 ms, passo 5 ms); entre palavras COLADAS, a borda vai ao vale de energia entre
elas. Oclusiva final (/t/ /k/ /p/: "it", "doubt", "kept") tem um SILÊNCIO dentro da palavra: atravessar silêncio de até 120 ms, mas
**só antes de pausa** (≥ 350 ms até a próxima) — dentro da frase isso confunde com o vão entre palavras (medido: 96 % → 83 %).

| sintético (gabarito à amostra) | início ≤ 1 q | fim ≤ 1 q | fins de frase cortando a voz |
|---|---|---|---|
| nosso `small` hoje | 6 % | 6 % | 9/10 |
| Premiere 2026 | 75 % | 49 % | 5/10 |
| Whisper + energia (sem modelo) | 49 % | 49 % | **0/10** |
| CTC (w2v PT int8 ou Omnilingual) + energia, PT | **96 %** | **96 %** | **0/10** |
| Omnilingual + energia, EN | 74 % | 69 % | 0/10 (o resto: oclusivas DENTRO da frase) |

⇒ "Não cortar a voz na pausa" sai só da energia; "selecionar a palavra no meio da frase" precisa do CTC.
⚠️ O sintético favorece a energia (silêncio digital entre palavras, gabarito recortado por energia).

**⛔⛔ Fala real de set: a energia da MISTURA não cai na pausa** (take `05-04 C4 P1-T001`, 9 min, 5 canais, Premiere 2026 de
referência, 547 palavras casadas): o fim antes de pausa ficou **+417 ms** (mediana; p90 1,4 s) depois do Premiere. Na lapela DOMINANTE
de cada palavra (canais isolados 2–4; os canais 0–1 são a mixagem L/R do Zoom F8, `TRL/TRR` no iXML), o limiar decide:

| limiar (abaixo do pico / acima do piso) | fim na pausa ≤ 1 q do Premiere | antes dele | depois dele |
|---|---|---|---|
| só o CTC | 45 % | 47 % | 9 % |
| 40 / 10 | 17 % | 3 % | 79 % |
| 30 / 15 | 32 % | 9 % | 59 % |
| 25 / 20 (no sintético já corta 1 ataque) | 48 % | 16 % | 36 % |

⚠️ Aqui a régua acaba: o Premiere NÃO é gabarito (no sintético ele mesmo corta a voz em 5 de 10). A fronteira fala × pausa em som de
set precisa de juiz humano — `pendente`.

**Custo** (Mac mini M, take de 9 min, 91 falas, uma janela por fala do Whisper ± 0,5 s): **~22–25 s** (4,5 % da duração).
Memória do onnxruntime: a sessão sobe ~2× o arquivo (prepack dos pesos; `session.disable_prepacking=1` → 543 MB para o w2v int8 de
355 MB), e cada segundo de janela soma **~30 MB** (15 s = +450 MB). Com janela ≤ 6 s e sem prepack/arena: **~800–900 MB** de pico; ≤ 3 s:
~600 MB. ⇒ não cabe no notebook com o MC aberto (o SigLIP caiu com 169 MB livres). `pendente`: Windows.

### ⭐⭐ O juiz de OUVIDO (o autor, 18 bordas de pausa cegas A/B, take C4 P1-T001, 2026-11-11)

Bordas onde o alinhador (lapela 30/15) e o Premiere 2026 discordavam (> 1 q e < 1,5 s). Ouvidas na sequência `OUVIR PAUSAS C4 P1-T001`
(`…/TRANSCRICAO POR PALAVRA v3.prproj`); chave em `…/2026-11-11 TRANSCRICAO POR PALAVRA/bordas_para_ouvir_CHAVE.json`.

- Placar cego: **Premiere 10, nosso 7**, 1 nula (a "palavra" era voz de equipe longe e embolada: o ASR transcreveu "ser" onde ninguém
  do elenco falou ⇒ palavra sem energia na lapela dominante é candidata a "fala distante", não diálogo — `hipotese`).
- **FIM:** o nosso ganhou as 5 em que ficou DEPOIS do Premiere (ele cortou a cauda: +55 a +530 ms); perdeu 2 cortando a voz (a energia
  não estendeu: −90 e −45 ms) e 2 passando da conta (+120, +275).
- **INÍCIO:** a energia andou para trás demais (sobra: −70, −185, e −280 no "num apoio", ver abaixo) ou não corrigiu o atraso do CTC
  (+55 a +80 ms, cortando o ataque).
- ⭐⭐ **Regra que sai daí (não ajustada nestes dados, só a trava):** início = **CTC − 41 ms** (o desvio fixo medido antes, +36 sintético /
  +41 take); fim = **max(energia na lapela, fim do CTC + 60 ms)**. ⇒ **13 de 17 a ≤ 1 quadro do ouvido, 0 cortando a voz**; Premiere 10 de 17;
  CTC cru 5; lapela nos dois lados 7. ⚠️ n = 17, e só bordas de discordância: confirmar num segundo take.
- Restam: fricativa inicial ("Senta", +96 ms) e um início adiantado (+80 ms). E a CONTRAÇÃO: "num apoio" — o editor quer a palavra
  ("apoio"), sem o "num" embolado antes; a borda certa depende do TEXTO que se quer, não só do som.
- O autor prefere errar para o lado CONSERVADOR (um quadro a mais antes da palavra a cortar o ataque).

### A energia sem o CTC, em fala REAL (L2 do Ciclo Assist, `midia/voz.py`, 2026-11-11)

As mesmas 17 bordas de ouvido, com a borda da lapela partindo do tempo do faster-whisper `small` (sem alinhador): **4/17 a ≤ 1 q**,
cortando voz/ataque em **3** (o Whisper cru: 0/17 e 9). ⚠️ Em fala real o Whisper erra a palavra em até **~1 s** (no sintético, ~130 ms),
e a busca de energia parte do lugar errado — o resultado de 49 % / 0 cortes do sintético NÃO se transfere. ⇒ energia é refinamento de
uma borda já boa (a do CTC), não substituto dela. ⚠️ Voz de equipe distante entra igual nas duas lapelas e passa da regra "10 dB acima
do piso + não perde por 3 dB": "fala distante" precisa de outra regra (`pendente`).

### O alinhador no PRODUTO, em fala real (L1 do Ciclo Assist, `midia/alinhamento.py`, Mac mini, 2026-11-11)

Omnilingual 300M CTC int8 + a regra do juiz (início = CTC − 41 ms; fim = max(voz na lapela, CTC + 60 ms)), take C4 P1-T001 × Premiere
2026: **início ≤ 1 quadro em 86 %** (faster-whisper `small` cru: 43 %); fim antes de pausa **antes** do Premiere em 1 % (Whisper cru: 75 %),
depois dele em 74 %. 33 s e 1,35 GB de pico para 9 min (`confirmado`).
- ⛔ **Janela que pega a fala vizinha:** o Whisper erra onde a próxima fala começa, e a janela de uma fala pode conter o começo da outra.
  Contexto (2 palavras de cada vizinha, alinhadas e descartadas) é a defesa clássica — mas **com teto de tempo** (1 s): sem ele o
  contexto atravessou silêncios longos e o custo foi de 26 s / 1,3 GB a 100 s / 2,8 GB. ⚠️ Nos 2 casos medidos o contexto NÃO encurtou o
  fim esticado ("secretária." +650 ms, "toda." +120 ms além do ouvido): a causa é outra (`pendente`).
- ⚠️ As duas réguas de energia não concordam no fim: a de borda do `voz.py` (10 dB acima do percentil 20 da lapela, sem perder da outra
  por 3 dB) encerra a voz 130–300 ms ANTES da 30/15 da L0 em 2 de 9 fins julgados. Qual vale é um segundo juiz de ouvido (`pendente`).
- ⚠️ Lição de método: o juiz de ouvido de 11/11 não teve os vereditos gravados; reconstruí-los pelo resumo é circular (a régua que gerou
  o candidato vencedor leva o crédito). Veredito de ouvido vai para ARQUIVO, ao lado da chave cega.

### ⭐⭐ O 2º juiz de ouvido: a lapela alonga o fim (take C4 P1-T001, 2026-11-11)

**2º juiz de ouvido (autor, 2026-11-11, cego, L1 × Premiere, 19 de 20 respondidas; vereditos em `vereditos_L1.json`):**
  **Premiere 14, L1 5.** Inícios: Premiere 4 de 5 (a L1 erra por 42–80 ms nos dois sentidos). ⛔⛔ **Fins: o que alonga é a LAPELA,
  não o CTC** — nos 7 fins que a L1 perdeu por +120 a +680 ms, o CTC+60 sozinho ficava a −88…+71 ms do Premiere (02 +46, 05 +45,
  10 +18, 14 +71, 15 +26; 07 −61, 16 −88); a voz na lapela (`voz.py`, 10 dB sobre o percentil 20, tolerância 3 dB) estende até
  +400…+680 ms. A lapela acertou em 2 (09 "e" +260 contra CTC +95; 20 "você" +500 contra CTC −104) e o CTC estica sozinho em 2
  (11 "um" +531, 17 "Personagem F." +320). ⇒ a regra `fim = max(voz, CTC+60)` está REPROVADA pelo ouvido; o fim conservador da lapela
  passa da conta na maioria. ⬜ Decisão do autor: fim = CTC+60 (e a lapela só onde o CTC não mediu?), ou investigar por que a máscara
  segue a voz depois do fim (respiro, vazamento do outro).
  Sequência `OUVIR PAUSAS L1 C4 P1-T001` em `…/TRANSCRICAO POR PALAVRA v4.prproj`; chave `bordas_para_ouvir_L1_CHAVE.json`. `confirmado` (ouvido, n=19).
- **Por que a lapela alonga o fim (2026-11-11, o sinal dos 14 fins julgados):** a palavra acaba num TOMBO (de +15…+27 dB sobre o
  limiar para −1…+9) e a máscara (piso global +10 dB, buraco de 120 ms preenchido, alcance 0,6 s) segue acesa nesse RESTO FRACO — sala,
  respiro, ou a OUTRA lapela (no `medir_l1.py` a fala vai sem dono e o fim procura em qualquer lapela). Onde a L1 acertou ("e", "você")
  a voz segue FORTE (+13…+19) até o fim marcado. ⛔ E o fim chegava a passar do início da palavra seguinte ("apartamento," "de").
  ⭐ **Régua candidata — a QUEDA:** na lapela mais forte NA palavra, o fim é onde o nível fica 10 dB abaixo do pico dos últimos 300 ms
  por 50 ms; teto 0,6 s e 30 ms antes da próxima palavra; piso CTC+60. ⇒ **10 de 14 fins com o ouvido** (a L1 de hoje: 4; D de 10 a
  20 dB dá o mesmo placar, 10 é o que não erra "apartamento"). Os 4 que sobram: "um" e "Personagem F." (o CTC estica a palavra: +531, +320),
  "ler?" (o piso +60 passa do Premiere) e "telefone." (por 1 quadro). ⚠️ AJUSTADA nos mesmos 14 casos ⇒ `hipotese` até um 2º take.
  Scripts: `spikes/transcricao_por_palavra/olhar_fins.py`, `regua_da_queda.py`.
- **A QUEDA no produto (2026-11-11):** `voz.niveis` + `voz.queda`; `medir(..., nv)` usa a queda no fim de palavra ALINHADA (fala e
  palavra antes de pausa), limitada a 0,6 s e a 30 ms antes da palavra seguinte, piso CTC+60; sem nível, a máscara de antes.
  `voz.json` v3 (a queda na assinatura: o cache velho refaz sozinho). Conferido pelo `medir_l1.py`: **10 de 14 fins** com o ouvido
  (eram 4); inícios iguais. Suíte Mac 1949/38. ⬜ Conferir num 2º take (rodada curta de ouvido, vereditos em arquivo); ⬜ o CTC que
  estica a palavra ("um", "Personagem F."); ⬜ os inícios (Premiere 4 de 5).
