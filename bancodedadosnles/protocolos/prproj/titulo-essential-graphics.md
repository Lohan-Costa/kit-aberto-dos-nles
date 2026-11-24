# O título do Essential Graphics (Basic Title) — o mapa do `Source Text`, controle a controle

> **Medido no Premiere 23.6.0 (macOS)**, `MZ.BuildVersion.Modified` = `23.6.0x65`, `Project Version="41"`, 2026-11-15.
> Método: o PILOTO mexeu num controle por vez do painel Essential Graphics (aba Edit, camada de texto), com valores
> inconfundíveis (corpo 137, tracking 23, cor C83214…); cada passo foi salvo e o blob comparado com o anterior.
> Os 38 passos (`.prproj`) e as ferramentas de leitura (`fb.py`, `estilo.py`, `diff.py`) estão em
> `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_CICLO ASSIST/2026-11-15 TITULO NO PREMIERE 2023/`.
> Todo o mapa é `inferido`: lido de arquivos reais com uma variável por vez, mas **ainda não escrito e reaberto**.
> ⬜ A 2ª metade: o **25/26/27** (o painel mudou para "Properties"). ✅ **O blob é o mesmo no 26.5.2 (Windows),
> 2026-11-20** — ver "No Premiere 26.5" no fim; falta só confirmar cada controle do painel Properties.

Para quê: levar o título do Avid (Titler+, `modulos/conformar/motor/titulos/avid.py`) para um Basic Title do Premiere
— a frente 2 do plano `_CICLO ASSIST/docs/plano/2026-11-15-completar-a-troca.md`. O que já se sabia está em
[relink-e-geometria.md §10.5](relink-e-geometria.md) (corpo, alinhamento, posição, Graphic Group).

## Onde está cada coisa

| camada | onde | lê pela API do 23.6? |
|---|---|---|
| texto, fonte, corpo, cores, contorno, fundo, sombra… | param 0 do componente `AE.ADBE Text` ("Source Text"), `StartKeyframeValue` em base64 | ⛔ **não**: `getValue()` devolve 1 caractere (o blob cortado no 1º byte nulo) |
| posição, escala, rotação, opacidade e âncora da CAMADA de texto (o bloco "Align and Transform") | params 2–8 do mesmo `AE.ADBE Text` | ✅ sim (`getValue`: `Position` e `Anchor Point` NORMALIZADOS ao quadro — 812/1920 = 0,4229) |
| a transformação do gráfico inteiro | `AE.ADBE Graphic Group` ("Vector Motion") e `AE.ADBE Motion` | ✅ sim |

`Sequence.importMGT(Basic Title.mogrt, ticks, trilhaV, trilhaA)` põe o título (o `.mogrt` fica em
`Adobe Premiere Pro 2023.app/Contents/Essential Graphics/Basic Title.mogrt`).

## O blob

12 bytes de cabeçalho (`u32` = tamanho do resto do blob · `00000000` · `44332211`) e um FlatBuffers. Ausente = o padrão
(o FlatBuffers não grava o padrão). Leitura: `raiz → campo 0 = DOCUMENTO`; `documento.0` = vetor de TRECHOS;
`trecho.0` = o texto (string UTF-8), `trecho.1` = o ESTILO do trecho. **Cor** = tabela de 3 bytes
`{0: R, 1: G, 2: B}` (u8 cada; **cada componente tem padrão 255** e só é gravado quando difere — branco = tabela vazia; FFD200 grava só G = D2 e B = 00).

### ESTILO do trecho (o que é por caractere)

| campo | controle do painel | tipo | padrão |
|---|---|---|---|
| 0 | a FONTE: índice no vetor `documento.1` (`hipotese`: só houve uma fonte no título) | u32 | 0 |
| 1 | corpo (Font Size) | f32 | 100 |
| 2 | cor do Fill | cor | branco |
| 4 | cor do Stroke (o 1º) | cor | branco |
| 5 | Stroke ligado | bool | não |
| 6 | espessura do Stroke | f32 | 1,0 |
| 8 | Tracking | f32 | 0 |
| 9 | Tsume (17 → 0,17) | f32 fração | 0 |
| 10 | Baseline Shift | f32 | 0 |
| 12 | 2 = All Caps, 1 = Small Caps | u32 | 0 |
| 13 | 1 = Superscript, 2 = Subscript | u32 | 0 |
| 14 | Faux Bold | bool | não |
| 15 | Faux Italic | bool | não |
| 16 | Underline | bool | não |
| 17 | os Strokes EXTRAS ("+"): vetor de tabelas `{0: cor, 1: ligado, 2: espessura f32, 5: tipo}` — o extra nasce cinza, 7,5, Outer | vetor | — |
| 21, 23 | sub-tabelas (`pendente`; o fill sólido mexe na 21 — gradiente?) | | |
| 24 | tipo do Stroke: 2 Outer, 1 Inner, ausente = Center | u32 | 2 no Basic Title |

### DOCUMENTO (o que é do parágrafo / da camada)

| campo | controle do painel | tipo | padrão |
|---|---|---|---|
| 1 | as FONTES: vetor de **STRINGS** (CORRIGE 2026-11-20: não de tabelas — lido byte a byte e escrito) com o nome **PostScript** (`MyriadPro-Regular`, `ArialMT`, `Arial-BoldItalicMT`). O menu de estilo (Regular/Italic/Bold/Bold Italic) só troca o nome — não há campo de estilo | vetor | |
| 4 | alinhamento: 0 esquerda, 1 direita, 2 centro (já `confirmado` no 23.2 em §10.5) | u32 | 0 |
| 5 | alinhamento vertical: ausente topo, 1 centro, 2 baixo | u32 | topo |
| 6 | Leading | f32 | 0 (automático = 120 %) |
| 7 | Tab Width | f32 | 400 |
| 10 | cor da Shadow | cor | preto |
| 11 | Shadow ligada | bool | não |
| 12 | opacidade da Shadow (%) | f32 | 100 |
| 13 | ângulo da Shadow (°) | f32 | 135 |
| 14 | distância da Shadow | f32 | 10 |
| 15 | tamanho da Shadow | f32 | 0 |
| 16 | desfoque da Shadow | f32 | 0 |
| 17 | cor do Background | cor | 3F3F3F |
| 18 | Background ligado | bool | não |
| 19 | opacidade do Background (%) | f32 | 75 |
| 20 | tamanho do Background | f32 | 0 |
| 21 | Mask with Text | bool | não |
| 26, 27, 38 | direção: RTL liga 26 e 27 e tira o 38; voltar a LTR deixou 26 = 1 e não devolveu o 38 (`pendente`) | | |
| 34 | cantos arredondados do Background | f32 | 0 |
| 37 | as Shadows EXTRAS ("+"): vetor de tabelas `{0: cor, 1: ligada, …}` — a extra nasce com 75 % e 135° | vetor | — |

- Os quatro botões de JUSTIFICAR ficam cinza no texto de ponto (só valem em caixa de parágrafo).
- Kerning fica cinza sem texto selecionado.
- ⬜ `pendente`: Fill em gradiente (o menu "Fill Options" do seletor não abriu com o clique sintético), o
  "Pin To" do Responsive Design (params 9–21 do `AE.ADBE Text`?), texto de várias linhas e trechos com estilos
  diferentes, os campos 0/1/10/14/40/43/44 vistos no documento do Basic Title sem controle associado.

## Pilotar o painel (Premiere 23.6, Mac) — o que custou caro

- O campo numérico "arrastável" REPOSICIONA o cursor ao entrar em edição (~18 px): o freio do mouse do piloto
  acusa o autor. Clicar, esperar ~1 s, conferir que a caixa abriu (fundo claro), Cmd+A, digitar, Enter. Com pausas
  curtas (0,6 s) o texto não entra.
- ⛔ **CORRIGE (mesmo dia):** o Color Picker "fechando sozinho" (ao perder o foco, ~1 s depois do campo hexa, "Tab
  confirma") NÃO era do Premiere: era o **vigia de diálogos do laboratório** (`lab/bancadas/vigia_dialogos.py`), que
  o `premiere.esperar_ponte()` LIGA SOZINHO e que ficou rodando a manhã inteira, apertando Return em todo "modal sem
  título" do Premiere — o Color Picker (512×374) é um deles: ~30 Returns registrados em `saida/bancadas/vigia/vigia.jsonl`.
  O comportamento real do seletor está por medir de novo, SEM o vigia. Ele leva de 1 a 4 s para aparecer.
- O seletor do Background é mais curto (sem o menu Solid/gradiente): a posição do campo hexa muda — medir na foto da
  abertura, não reaproveitar.
- A roda do mouse rola o painel com o ponteiro dentro dele (no piloto: `rolar(x, y, n)` com n POSITIVO desce).
- Tecla com o seletor já fechado vai para a TIMELINE (Cmd+A seleciona tudo, letras trocam a ferramenta).

## Um gráfico, VÁRIAS camadas (Premiere 23.6, 2026-11-15 — `inferido`)

O gráfico é UM clipe (mídia sintética "Graphic") cuja `VideoComponentChain` leva um componente por camada, **na ordem
do painel (a de cima primeiro)**; o `InstanceName` do componente é o nome da camada ("Shape 04", "New Text Layer",
"CLAQ_CANAL-K_2021"). Camadas vêm do botão "New Layer" do painel (Text, Vertical Text, Rectangle, Ellipse, Polygon,
From File…) ou DESENHADAS no monitor de programa com a ferramenta de retângulo/elipse/polígono (o menu escondido do
retângulo) ou com a Caneta, com o gráfico selecionado — as duas vias gravam igual.

| camada | componente | o que guarda |
|---|---|---|
| Text | `AE.ADBE Text` | o blob acima |
| Vertical Text | `AE.ADBE Text` | o mesmo blob com `documento.9` = 1 |
| Rectangle / Ellipse / Polygon / Caneta | `AE.ADBE Shape` | param 0 **Path**, param 1 **Appearance**, params 2–17 a transformação (`Position` e `Anchor Point` normalizados ao quadro) |
| From File (imagem, PSD…) | `VideoClipComponent` | `InstanceName` = nome do arquivo e `ChildClip` → o clipe da mídia (14 params de transformação) |

⚠️ O Basic Title importado (`importMGT`) traz um `AE.ADBE Graphic Group` ("Vector Motion") por cima; o gráfico real
da EVENTO-T, feito com a ferramenta de texto no 23.6.9, NÃO tem.

### O Path (forma)

`u32 2` · `u32 N` (vértices) · N × { `u32 tipo` (0 canto, 1 curva) · ponto x,y · tangente de entrada x,y · de saída
x,y } em f32 · `u8 1` (fechado). Coordenadas em pixels da própria forma (o retângulo de 401 × 221 vai de 0,0 a
401,221; a âncora padrão é o centro). Elipse = 4 vértices tipo 1 com tangentes Bézier; polígono = os N vértices já
calculados (o triângulo, 3); Caneta = os pontos clicados, e o ponto ARRASTADO vira tipo 1 com tangentes simétricas.
⭐ **O canto arredondado não é um número**: com 23 o retângulo passa a 8 vértices, tangente 12,7 (= 0,552 × 23, o
quarto de círculo em Bézier), e NADA mais muda (Appearance e params iguais) — o painel volta a mostrar 23, então ele
o reconhece da geometria. O "número de lados" do polígono deve ser igual (`hipotese`, não mudado).

### A Appearance (forma)

Mesmo cabeçalho do texto (u32 tamanho do resto · 0 · `44332211`) e um FlatBuffers: `raiz.0` = a tabela:

| campo | controle | padrão |
|---|---|---|
| 0 | cor do Fill | 7F7F7F |
| 2 | cor do Stroke | branco |
| 3 | Stroke ligado | não |
| 4 | espessura do Stroke | 4,0 |
| 5 | cor da Shadow | 3F3F3F |
| 6 | Shadow ligada | não |
| 7 | opacidade da Shadow | 75 (a do TEXTO nasce 100) |
| 8 | ângulo da Shadow | 135 |
| 9 | distância da Shadow | 7 |
| 10 | tamanho da Shadow | 0 |
| 12 | Mask with Shape | não |
| 20, 28, 30 | sub-tabelas do Fill, do Stroke e da Shadow (aparecem quando a cor passa pelo seletor; a geometria de gradiente? `pendente`) | |
| 23 | o TIPO da forma: 1 retângulo, 3 polígono (elipse 2? caneta? `pendente`) | |
| 24, 25 | W e H (f32) — mudar o W recalcula o Path | |
| 26, 31, 34 | `pendente` | |

- **Número de lados do polígono = o número de vértices do Path** (5 lados → 5 vértices); não há campo. Como o canto
  arredondado, é geometria.
- A Shadow da forma nasce com 75 %, 135°, distância 7.
- ✅ **Fill em GRADIENTE** (refeito SEM o vigia: o menu "Solid / Linear Gradient / Radial Gradient" abre com um clique
  sintético normal; quem o fechava era o vigia). Na Appearance da forma: **campo 19 = tipo do Fill** (1 = linear;
  ausente = sólido; radial `hipotese` 2). A sub-tabela **20** (a do Fill) guarda: 0,1 = ponto inicial e 2,3 = ponto
  final da linha do gradiente (px da forma: (100,2; 110,5) → (300,8; 110,5) num retângulo de 401 × 221); **6 = paradas
  de COR**, vetor de `{0: cor, 1: posição f32 (0–1, padrão 0), 2: ponto médio f32 (0,5)}` — medido FF0000 em 0 e
  0000FF em 1; **7 = paradas de OPACIDADE**, `{1: posição, 2: ponto médio}` (opacidade 100 % = padrão, não gravada).
  As sub-tabelas 28 e 30 (Stroke e Shadow) têm a mesma forma. No seletor: paradas de cor embaixo da barra, de
  opacidade em cima, losango = ponto médio, "Location" em %. O Fill do TEXTO em gradiente: mesma via, `pendente`.

### A camada From File (pilotada, `ARTE_FROM_FILE.png`)

"New Layer › From File…" abre o diálogo "Import" (do macOS) e IMPORTA o arquivo no projeto como item comum (ele
aparece no painel de projeto). A camada é um `VideoClipComponent`: `InstanceName` = o nome do arquivo SEM extensão,
`ChildClip` → um `SubClip` daquele item (→ `VideoClip` → `Media` com o caminho; e o `MasterClip` "ARTE_FROM_FILE.png").
14 params: Position e Anchor Point normalizados (0,5:0,5 = centro), Scale, Horizontal Scale, Uniform Scale, Rotation,
Opacity, Left/Top/Right/Bottom (os pinos do Responsive Design), Parent Width/Height/Rotation. Igual à claquete real.

### O caso real: a claquete da EVENTO-T (Premiere 23.6.9, projeto de trabalho, cópia em `real_evento-t/`)

Um gráfico com **6 camadas de texto** (GaleanaCondensed-Black: "CANAL-K", "30…", "2026", "EDITOR",
"NOME_DA_CHAMADA_ID" e uma vazia) e **uma From File** (`CLAQ_CANAL-K_2021.psd`, o fundo do CANAL-K) por baixo.

## Estilo POR TRECHO: parte de uma frase com outra cor/corpo (a base da legenda "karaokê") — 2026-11-15, `inferido`

Selecionar parte do texto e mudar um atributo PARTE o vetor de trechos (`documento.0`): medido em "New Text Layer"
com "Text" selecionado → **3 trechos**, cada um `{0: texto, 1: estilo}` com uma CÓPIA COMPLETA do estilo:
`"New "` (corpo 137, cor C83214) · `"Text"` (corpo 90, cor FFD200) · `" Layer"` (corpo 137, cor C83214). O que é do
documento (alinhamento, sombra, fundo…) continua um só. Para gerar legenda animada que destaca a palavra falada: um
trecho por palavra (ou o trecho da palavra da vez com o estilo de destaque), e keyframes do `Source Text` (abaixo).

### O gesto (Premiere 23.6, Mac) — o que o autor ensinou e o que foi medido
- **Duplo clique no texto, no monitor de programa, com a ferramenta de SELEÇÃO ativa** → entra na edição com TUDO
  selecionado. Com a ferramenta de **TEXTO** ativa, o duplo clique só põe a barra de texto (sem seleção) — observação
  do autor. Selecionar uma camada de texto no painel às vezes troca a ferramenta para Texto: conferir antes.
- Clique simples (ferramenta de Texto) = posiciona a barra; **arrastar sobre letras = seleção** (✅ pelo piloto: o
  realce escuro aparece só sobre o trecho).
- Setas movem a barra (✅); **Shift+seta sintético NÃO seleciona** (CGEvent, com e sem as marcas Fn/NumericPad das
  setas) — pelo piloto, use o arrasto. À mão, Shift+setas funciona (autor).
- Com só a BARRA (sem seleção), mudar o corpo no painel não muda o texto existente — vale para o que for digitado ali.
- Com a seleção feita, os atributos do painel (corpo, cor do Fill pelo seletor) mudam SÓ a seleção, e ela sobrevive
  ao seletor de cor aberto e fechado.
- ⚠️ O "Desfazer" do menu Edit fica vazio a sessão inteira com as mudanças do Essential Graphics: não serve para
  conferir se algo foi editado.

## O `Source Text` ANIMADO (keyframes) — 2026-11-15, `inferido`

Pilotado no Effect Controls (o gráfico lista um componente por camada; "Text (Your Title Here)" › cronômetro do
`Source Text` = "Toggle animation"; mudar um atributo noutro tempo cria o keyframe seguinte). No `.prproj` o param
ganha `<Keyframes>` (o `StartKeyframeValue` continua lá):

```
<Keyframes>914958106776000,<blob base64>;915212122776000,<blob base64>;</Keyframes>
```

- Cada keyframe = `tempo,blob;` e o blob é o **`Source Text` COMPLETO** daquele instante (o mesmo formato acima:
  texto, trechos e estilos) — medido: corpo 137 no 1º, 60 no 2º. Sem interpolação: texto troca em degrau (hold).
- O tempo é em ticks (254 016 000 000 por segundo) no relógio da MÍDIA do clipe do gráfico, como os keyframes do
  Motion ([relink-e-geometria.md §10.5](relink-e-geometria.md)): InPoint 914 450 328 792 000; os keyframes caíram a
  +2,0 s e +3,0 s dele = 3,0 s e 4,0 s na sequência (o clipe começa em 1,0 s).
- ⭐ Para a legenda karaokê: um keyframe por palavra falada, cada um com o blob inteiro em que só o trecho da palavra
  da vez tem o estilo de destaque.

## No Premiere 26.5 (Windows 11, `26.5.2`, 2026-11-20) — o blob é o MESMO; o `importMGT` do Basic Title vem VAZIO

Projeto de teste: `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_CICLO ASSIST/2026-11-20 TITULO NO PREMIERE 2026 WINDOWS/`
(`passos/00_new_text_layer.prproj`; o de trabalho, em NTFS, `Documents/CICLO TITULO 2026/`).

- ⛔⛔ **`Sequence.importMGT("…/Basic Title.mogrt")` põe um gráfico SEM CAMADA nenhuma no 26.5** (`confirmado`, 1 de 1):
  o clipe "Graphic" entra na trilha, `isMGT()` = true, mas os componentes são só Opacity, Motion e `AE.ADBE Graphic
  Group`; o painel Properties mostra "Graphic" com a lista de camadas vazia, o monitor não desenha texto, e o `.prproj`
  salvo tem a `VideoComponentChain` vazia. O `.mogrt` é o mesmo de 2018 (`project.prgraphic`) que no 23.6 trazia o
  `AE.ADBE Text`. ⇒ No 26 o molde do título NÃO vem do `importMGT`.
- ✅ **O que funciona: Graphics and Titles › New Layer › Text** (menu nativo por id, `maos.comando_menu`, id 21801
  nesta instalação) com o gráfico selecionado: acrescenta a camada "New Text Layer" ao gráfico (Lucida Console, 100).
  Sem gráfico selecionado, `pendente` (deve criar um gráfico novo no playhead).
- ✅ **O `Source Text` é o MESMO formato** (`inferido`, lido): o mesmo nome de param, os 12 bytes de cabeçalho
  (`u32` tamanho · `00000000` · `44332211`) e o FlatBuffers com os MESMOS números de campo — documento `0` (trechos),
  `1` (fontes, nome PostScript: `LucidaConsole`), `26`, `40`, `43`, `44`; estilo `6`, `21`, `23`, `24`. ⇒ O mapa do
  23.6 acima vale como ponto de partida para o 26; a camada nova traz padrões diferentes do Basic Title do 23.6:
  contorno com espessura **4,0** (estilo `6`), `documento.26 = 1` sem o `38` (a combinação que no 23.6 se via depois
  de RTL→LTR — ⇒ o `26`/`38` não é direção pura; `pendente`), sem alinhamento gravado (esquerda).
- ✅ **ESCRITO, REABERTO E REGRAVADO** (26.5.2 Windows, 2026-11-20 — `confirmado`): `cicloassist/carta/titulo_prproj.py`
  (leitor/escritor com esquema; ida e volta sem perda nos 164 blobs reais do 23.6 e do 26.5) e
  `spikes/titulo_escrito_no_premiere.py`. Um blob com 22 valores inconfundíveis na camada do 26.5, reaberto: o monitor
  desenhou "PRODUCAO-A" e o painel Properties mostrou CADA um — texto, fonte `ArialMT` → "Arial", corpo 137, Fill
  C83214 e Stroke 1E5AA0 (o pixel da amostra, exato), stroke ligado 7,0 Outer, tracking 23, All Caps (o texto escrito
  em minúsculas aparece MAIÚSCULO), Faux Italic, centro, Background ligado 45 / 9,0 / cantos 6 (verde), Shadow ligada
  60 / 200° / 12,0 / 3,0 / 27 (roxa). Salvo pelo Premiere, o blob voltou com 472 bytes e **zero diferença** na
  árvore. ⇒ Os campos do estilo 1, 2, 4, 5, 6, 8, 12, 15, 24 e do documento 1, 4, 10–20, 34 estão `confirmado` no 26.5.
  - O `BinaryHash` do valor: 12 bytes ALEATÓRIOS + `u32` BE (tamanho + 12) basta — o 26.5 abre e, ao salvar, troca
    pelo dele (como o 23, banco `escrita.md`).
  - ⭐ Escrevem-se os três componentes da cor mesmo os de valor 255 (o Premiere omite o padrão; ele lê os dois).
  - ⬜ Ainda não escritos: vertical (doc 5), leading (6), tab (7), Tsume (9), baseline (10), Small Caps/super/sub,
    Faux Bold, underline, Mask with Text, os extras (estilo 17, doc 37), vários trechos e keyframes.

### O aviso "Project Modified" a cada salvamento (26.5.2 Windows) — é da SESSÃO

"The project file has been modified since last save. Do you wish to continue?" (OK/Cancel, `#32770` 613×321) a CADA
salvamento — `app.project.save()`, File › Save pelo menu, e o `closeDocument(1, …)` — num projeto criado por
`app.newProject(caminho)` e depois gravado com `saveAs` noutro caminho. Segura a resposta da ponte até alguém
responder; o OK grava de fato. Não é o disco (igual em exFAT e NTFS). **Fechado e reaberto (`app.openDocument`), o
mesmo arquivo salva sem aviso** (1 de 1). ⇒ Na bancada: criar o projeto e REABRIR antes de uma rodada de salvamentos.
Causa: não medida (o 1º `newProject` caiu num caminho errado — a barra entre pasta e nome se perdeu no ExtendScript
passado como `"…\…"`; com `/` não acontece).

### O título do Avid levado ao 26.5 por MOLDE (2026-11-20, `confirmado` na tela)

- O "Importar para o Premiere" da Carta (`_CICLO ASSIST`, `carta/entrega_prproj._escrever_titulo`) clona um gráfico de
  texto feito pelo Premiere (o molde do app) e escreve o blob: a PRODA_CORTE.00.2 entrou com "PRODUCAO-A" na V3
  (735–934) e os dois dissolves de 40 quadros, desenhado no monitor. Cada título leva MasterClip e Media sintética
  NOVOS (ObjectUID), como o Premiere faz ao criar um gráfico; a duração vai no `OutPoint` do VideoClip do gráfico.
- ⛔ **A camada nova (New Layer › Text) HERDA o último estilo usado na sessão** — o molde feito logo depois de um título
  de teste saiu com fundo, sombra, itálico, caixa alta e corpo 137. Quem clona uma camada tem de ZERAR os campos do
  painel antes de escrever.
- ⚠️ Num projeto IMPORTADO noutro (`importFiles` de um `.prproj`), o gráfico chega com a cadeia só com o `AE.ADBE Text`
  (o "Vector Motion" / `AE.ADBE Graphic Group` some) — e funciona igual.
- ⛔ `qe.project.newSequence(nome, preset)` no Windows: o caminho do `.sqpreset` com `/` devolve `false` e não cria
  nada; com `\` cria (26.5.2). Preset: `Settings\SequencePresets\HD 1080p\HD 1080p 23.976 fps.sqpreset`.
- ⚠️ "Project Modified" (a cada salvamento) NÃO aconteceu num `newProject` salvo direto, sem `saveAs` — reforça que vem
  do `saveAs` depois do `newProject`.
