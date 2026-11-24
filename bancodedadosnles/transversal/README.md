# Transversal — o que não pertence a um formato só

Esta pasta documenta o conhecimento que **atravessa** os formatos: a tradução de uma NLE para
outra. É a visão que o RELINKER persegue — **"o app é um tradutor entre NLEs"**, não um copiador.

## Por que existe uma camada transversal

Cada NLE tem **sua própria biblioteca de efeitos** e **ignora** o que não é dela. O importador de
AAF do próprio Resolve **descarta** os transforms do Avid (3D Warp, SMPTE Wipe) — só velocidade
sobrevive. Logo, dar saída fiel para outra NLE é **escrever o efeito nativo do destino**
(autoração), traduzindo a **intenção** do efeito de origem — não passar bytes adiante.

A ponte é um **modelo neutro** (idioma comum, independente de NLE):

```
AAF (Avid) ─parse─► effects[] ─tradutor─► modelo NEUTRO ─writer─► DRT/OTIO (Resolve) ou .prproj (Premiere)
```

## Conteúdo

| arquivo | conteúdo |
|---|---|
| ⭐⭐⭐ [matriz-de-plataforma.md](matriz-de-plataforma.md) | **Regra master.** Windows ⇄ macOS variável por variável: pastas, PATH, discos, Unicode, sombras `._`, atributos, portas, diálogos, Media Composer — os dois lados, a armadilha e a confiança |
| [matriz-de-plataforma.json](matriz-de-plataforma.json) | As mesmas 55 variáveis consumíveis, com a regex de busca de cada uma para revisar um repositório |
| [modelo-neutro-efeitos.md](modelo-neutro-efeitos.md) | As três camadas (intenção/convenção/codec); primitivas universais; fórmulas medidas de posição/escala/rotação/crop/opacidade nas 3 NLEs |
| [modelo-neutro-efeitos.json](modelo-neutro-efeitos.json) | Fórmulas de conversão consumíveis (Avid↔Resolve↔Premiere) |
| [tempo-e-timecode.md](tempo-e-timecode.md) | Unidades de tempo de cada formato e conversões; velocidade/rampa entre NLEs |
| [tamanho-de-arquivo-de-nle.md](tamanho-de-arquivo-de-nle.md) | Projeto inteiro (prproj/drp) × várias timelines (avb) × uma timeline (AAF/XML/FCPXML/DRT/OTIO); memória para abrir (~3,6× o descompactado); bomba de compressão |
| ⭐ [caminhos-e-storage-producao.md](caminhos-e-storage-producao.md) | Do projeto até o **arquivo original em disco**: as 5 formas de URL que o Avid grava, o layout real do storage de produção, nome de fita = nome de pasta, identidade de volume, e o que funciona para linkar sem copiar |
| [caminhos-e-storage-producao.json](caminhos-e-storage-producao.json) | Os mesmos fatos consumíveis (padrões de caminho, marcadores de mídia gerenciada, matriz de mecanismos de link) |
| ⭐ [ambiente-media-composer-windows.md](ambiente-media-composer-windows.md) | O **runtime em volta do NLE**: antivírus travando o splash, o bridge QuickTime de 32 bits que o AMA exige, sidecars AppleDouble envenenando o autodetect, e as mensagens de console que parecem erro e não são |
| [ambiente-media-composer-windows.json](ambiente-media-composer-windows.json) | Triagem sintoma→causa, códigos de erro AMA em hex, mapa extensão→plugin, exclusões de antivírus |

## As três camadas (resumo) — "preciso remapear cada efeito?" → não

1. **Intenção (modelo neutro):** mapeada **uma vez por primitiva** (position/scale/rotation/
   anchor/crop/opacity). 3D Warp, Resize, PiP, Pan & Zoom do Avid são as MESMAS primitivas.
2. **Convenção (unidade/origem/âncora/ordem):** mapeada **uma vez por NLE**.
3. **Codec (ler/escrever os bytes):** **possivelmente por efeito** — única camada que pode exigir
   amostra por efeito (a maioria dos geométricos do Avid compartilha o esquema de param-ID).

## Fidelidade por família (gerencia expectativa)

| família | tratamento |
|---|---|
| Transform (pos/scale/rot/crop/opacity) | **fiel** — fazer primeiro |
| Time (velocidade) | **fiel** (linear adaptativo) — feito |
| Color | **só-informar** (ciência de cor difere; refeito no finishing) |
| Keying | **aproximado/refazer** |
| Stabilize | **não-suportado** (re-analisar no destino) |
| Transições wipe/3D | **não-suportado/aprox** (proprietário) |

## Princípio de validação
Toda célula nasce **"a validar"** e só vira **"fiel"** depois de **medir** (mesmo método que
destravou a rampa: criar o efeito nas duas NLEs, exportar e diffar — contador/grade queimada +
diff de imagem). Medir, não adivinhar.


---

## Fora da tradução entre NLEs

- ⭐⭐⭐ **[matriz de plataforma Windows ⇄ macOS](matriz-de-plataforma.md)** — a **regra master**.
  Nasceu de um padrão, não de uma sessão: cinco portes entre os dois sistemas e os mesmos erros de
  caminho voltando, com o conhecimento já registrado — mas em narrativa, organizado por sessão.
  A matriz é o índice por variável; [desenvolvimento-cross-platform.md](desenvolvimento-cross-platform.md)
  e [ambiente-media-composer-windows.md](ambiente-media-composer-windows.md) seguem sendo a fonte.

- ⭐ **[analisar o executável do concorrente](analise-de-executaveis.md)** — engenharia reversa de
  **aplicativo**, não de formato. Entrou aqui por ser método que serve a qualquer NLE e a qualquer
  formato: quando a documentação não existe ou o SDK é fechado, o produto do concorrente é a
  documentação que falta. Traz a ordem de ataque, as receitas de extração sem instalar, a régua de
  até onde ir, e a calibração do que a técnica acerta e erra.

- ⭐ **[ambiente do Media Composer no Windows](ambiente-media-composer-windows.md)** — o **runtime**,
  não o binário nem o formato. Entrou aqui porque um app pode gerar `.avb`/`.aaf` perfeitos e ainda
  colher "não funciona" da estação do editor — e nos quatro casos medidos (2026-08-19) o sintoma
  relatado **aponta para o lugar errado**. ⚠️⚠️ A armadilha de método mais cara: **import table só
  enxerga link estático no mesmo processo** — ela responde "dependências OK" com confiança total
  para uma dependência que mora num helper de 32 bits carregado em runtime.

- **[medir sync contra gabarito](medir-sync-contra-gabarito.md)** — a bin do editor como INSTRUMENTO de medição. A matriz `acertou/errou × sinalizou/calado`, as três armadilhas da extração, e o custo medido de não ter régua (três consertos revertidos numa sessão só).

- 🆕 ⭐⭐ **[decupagem por transcrição](decupagem-por-transcricao.md)** — **o roteiro escrito NÃO é a verdade** (novo em 2026-08-31). Como separar as falas de uma cena entre várias tomadas com ASR + roteiro. ⛔ Medido: em **4 de 6** falas o ator diverge do escrito ("Boa noite"→"Boa tarde"), e um motor que trate o roteiro como verdade **descarta material dito** — o improviso vira órfão (0,67 a 3,96 s perdidos, em 7 de 11 tomadas) e o aparo guiado por roteiro **corta dentro da palavra**. ⭐ A espinha é o material; o roteiro só semeia. ⭐ O respiro: o vão pode reduzir, **nunca zerar** (alvo 8 frames, piso 5, calibrado). ⭐ O gabarito sai da bin que o editor **aparou**. ⭐⭐ **Ampliado em 2026-09-01:** o **tempo do `whisper.cpp` não é o tempo da voz** (128,4 s de legenda no ar sem ninguém falando numa tomada; *"Boa tarde."* segurada 24,92 s), `-ojf` não serve com `--vad` (relógio comprimido), a rota por palavra é `-ml 1 -sow`, e **o VAD já sabe onde é a voz — o `whisper.cpp` descarta as fronteiras dele** (`whisper-vad-speech-segments`, 1,5 s/tomada). Energia diz DE QUEM, o VAD diz SE É FALA. ⭐ E a linha do roteiro também não é a fronteira da fala (§9). 🆕 ⭐⭐ **Ampliado em 2026-09-12:** §8.6 — **23,6% das fronteiras do `faster-whisper` são vão `0,000` (artefato do motor)**, e o clamp no vizinho zerava o respiro de **24,2% das falas**; e §12 — **conferir o mapa de corte de um LLM**, onde a escrituração sozinha aprova a montagem ruim, a âncora no material separa take certo (100%) de take errado (9%), e **validar "a fala está aqui" premia o degenerado** (16 cortes colapsados num plano aberto, aprovados).

- 🆕 ⭐ **[busca visual no acervo](busca-visual-no-acervo.md)** — *"onde mais eu tenho um plano assim?"*, medido em 2026-09-11. **pHash 93% com 0 MB; MobileNetV2 em ONNX 99% com 14 MB**, contra 38% ao acaso — **não é preciso CLIP de 350 MB**, e nenhum dos dois exige torch. ⛔⛔ E a armadilha do INSTRUMENTO, que invalida a medida inteira: deixando os quadros do PRÓPRIO take no conjunto, qualquer motor marca 100% — inclusive um que comparasse o tamanho em bytes. ⚠️ Medido em cena fechada: *"ache a Personagem F em outra cena"* continua por medir. 🆕 **2026-09-13:** "não é preciso CLIP" vale para **imagem → imagem**; o MobileNetV2 não tem codificador de texto, então buscar por FRASE sobre material não decupado é operação que ele não tem — o buraco que um par CLIP/SigLIP fecha.

- 🆕 ⭐⭐ **[a IA que o Premiere e o Resolve embarcam](ia-embarcada-nos-nles.md)** — (2026-09-13; Premiere 26.0.2, Resolve Studio 21.1 b14). **Nenhum dos dois usa LLM grande para olhar vídeo**: modelos pequenos, locais, busca por vetor (padrão CLIP no Premiere; UniIR no Resolve), Whisper large-v3-turbo na transcrição do Resolve, e o IntelliScript deixando strings de **semelhança de frase + melhor caminho em grafo**. Os pesos são criptografados: a identificação vem de nome de pacote, log e classe — sob a régua de [analisar o executável](analise-de-executaveis.md), sem extração de modelo.

- 🆕 ⭐⭐ **[o CLI do modelo como motor](cli-do-modelo-como-motor.md)** — o contrato operacional de embarcar o **CLI que o editor já tem logado** em vez de chave de API ou LLM local (novo em 2026-09-12, Claude Code 2.1.267→2.1.269). ⛔⛔ **O custo é o CONTEXTO, não o payload:** a mesma tarefa numa conversa de dois dias atrás leu **6.574.840 tokens em 12 chamadas**; depois de limpar, **690.727 em 13** — **10,8×** — e a saída de TODAS as ferramentas foi 0,5% do que foi lido. ⛔⛔ **`compact_boundary`: 70 segundos sem uma palavra na tela** (582.570 → 108.239 tokens, 474 mil descartados, ~121 mil queimados) quando a conversa não cabe na janela do modelo — o evento existe no stream e é fácil descartar. ⛔ **Teto de saída de ferramenta:** acima do limite a resposta volta como **erro com caminho de arquivo**, e o nome do arquivo carrega **timestamp, não a identidade da chamada** — com chamadas paralelas o modelo perde o mapeamento (medido: 12 de 14 estouraram, e a recuperação por grep custou mais que as transcrições). Bracketing: 20.201 chars passaram, 55.844 estouraram. ⭐ **`--effort` existe e NÃO é alavanca de custo:** ~70% da SAÍDA é pensamento, mas a saída é **0,3% dos tokens totais**. ⛔ **`--restricted` bloqueia as skills do próprio CLI** — quem expõe chat ao cliente tem de transportar o ofício para uma ferramenta MCP. ⛔⛔ **`--session-id` num id existente NÃO dá erro** (descarta o fio em silêncio) e **o id do fio tem de ser PERSISTIDO, não derivado** — limpar só na memória faz o "limpar" virar no-op depois de reiniciar, e o turno seguinte retoma com `--resume` o que o editor achava ter jogado fora. ⚠️ **A soma do `result` não é ocupação da janela** (medido 267.873 contra 23.360 reais, 11×) e **o transcript grava a mesma mensagem 2,6–3,2×** — deduplicar por `message.id` ou a conta triplica. 🆕 ⭐⭐ **§10 (2026-09-13), modelo local via Ollama:** estação de edição com GPU de laptop **não hospeda** modelo local (51% CPU / 49% GPU, 600 s estourados, telas azuis com o MC aberto); o Ollama 0.33.3 **fala `/v1/messages`** (o CLI por cima: `pendente`); contexto padrão **4096** contra 6.229 tokens de seis quadros; e o VLM pequeno copia o placeholder e descreve quadro a quadro.

- ⭐ **[modelo de execução de agente](modelo-de-execucao-de-agente.md)** — **como a decisão de um LLM
  chega na timeline**. É transversal pelo mesmo motivo que o modelo neutro de efeitos: a fronteira
  certa é um **plano de ações NLE-neutro**, com um executor por NLE. Cinco modelos medidos em quatro
  concorrentes e na nossa própria implementação, com o custo de cada um em ida-e-volta, atomicidade e
  undo — e a razão de, no Avid, autorarmos a timeline em vez de comandá-la ser **restrição de
  plataforma medida**, não preferência.

- ⭐⭐⭐ **[operacoes-de-nle.md](operacoes-de-nle.md)** — **comece por aqui.** O mapa por MECÂNICA (mover, inserir, remover, trilha, bin, metadado, seleção, efeito, estado, tempo, eventos), com uma coluna por NLE e o **mapa dos buracos** que dirige a exploração. Mecânica nova entra ali; o documento do produto vira fonte.
