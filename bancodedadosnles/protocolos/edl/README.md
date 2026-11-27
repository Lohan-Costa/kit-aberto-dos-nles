# EDL (CMX 3600 e as variantes File_32/File_129) — o que o Premiere e o Media Composer escrevem

> **Medido em 2026-11-25, macOS 15.6.1 (Mac mini):** Media Composer **25.12** (List Tool) e Premiere Pro **26.0.2**
> (Arquivo › Exportar › EDL…, interface em português). Comparação com uma EDL do Resolve **19.0.0b** (Windows) já
> existente. **Confiança: `confirmado`** para o que está nas EDLs (lido byte a byte); **`inferido`** onde a causa é
> deduzida (marcado). Uma sequência de cada lado (a mesma); outras versões = `hipotese` até remedir.
>
> Amostras e fotos: `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_CICLO ASSIST/2026-11-25 EDL PREMIERE MC/` (`PR01…PR03` do
> Premiere, `MC01 FILE129`, `MC02 CMX3600` do MC; `fotos/` com o diálogo do Premiere e as abas do List Tool;
> `DIARIO.md`). Mídia: receita `laboratorio-de-midia/receitas/base/B30_EDL.json` (cada fonte com TC próprio: A 01h,
> B 02h com 5 canais, nome de 51 caracteres 03h, `AÇÃO` 04h, 25 fps 05h, WAV de 4 canais 06h). A sequência foi montada
> no Premiere por script (`2 ATIVOS/_CICLO ASSIST/spikes/edl_premiere_mc/montar_premiere.py`) e levada ao MC pelo
> Conformar (Premiere → Avid), então o MC exportou a mesma montagem.

**Por que interessa:** a EDL é a lista que as casas de pós ainda pedem (Conform Pull e VFX Pull da Netflix só leem EDL
File32/File129 — [entregas/matriz.md](../../transversal/entregas/matriz.md)), e hoje **nenhum app nosso escreve nem lê
EDL** ([entregas/lacunas.md](../../transversal/entregas/lacunas.md)). Para escrever (ou ler) uma EDL que sirva aos dois
mundos é preciso saber em que cada NLE diverge.

## 1. Como se exporta

| | Premiere 26.0.2 | Media Composer 25.12 |
|---|---|---|
| onde | **Arquivo › Exportar › EDL…** (menu nativo do Mac; pelo nome: `click menu item "EDL…" of menu 1 of menu item "Exportar" of menu "Arquivo"`) | **Tools › List Tool** (o DoCommand 5075 existe; o 25.12 Mac LISTA o `DoCommand` na reflexão — não medido; ver o `SetPosition` que trava em `plugins/avid-panel-sdk/README.md`) |
| por script | ⛔ **não há**: o DOM tem `exportAAF`, `exportOMF`, `exportFinalCutProXML`, `exportTimeline(string)` (este é para plugin de *export controller* de terceiros) — nenhum EDL. Só pela interface | ⛔ não pela API do 25.12 (sem `DoCommand`); interface |
| formatos | **só CMX 3600** (o diálogo se chama "Configurações de exportação do EDL (CMX 3600)"; o salvar só oferece `CMX3600 EDL (*.edl)`) | **CMX_3600, CMX_DigitalCut, CMX_Transfer, Cuedos, File_16, File_32, File_129, Columnar, TabbedLists, XML** (Output Format) |
| trilhas | **1 de vídeo** (lista "Vídeo: Vídeo 1") e **4 canais de áudio** (Áudio 1–4, cada um = "Áudio N - Canal M" de uma trilha) | todas as escolhidas na aba Input (V1…, A1…A*n*); um evento por trilha |
| configurações | caixas: níveis de vídeo/áudio, nome do arquivo de origem, nome original do arquivo de vídeo/áudio, **nomes com 32 caracteres**, faixa principal, transições, rolagem de som/TC de som, ASC CDL e LUTs, marcadores de clipe, eventos em branco; "Processamento de áudio: O áudio segue o vídeo" | Active Setting com nome (salvo; muda para "Default EDL.1" quando se altera); abas **Input** (Load = a sequência do Record; trilhas), **List Options** (juntar trilhas de vídeo, Optimize EDL, handles, o que entra: Dissolves, Other/3rd Party Transitions, Black Edits, Spatial/Temporal Adapters, Title Text, Color Effects, CDL…), **Formatting** (Source TC, Record TC, **Reel ID Type = Source File/Tape**, Sort Mode A, Starting Event Number, **Tape or File name truncation = End**, converter fitas em números, tabela de fontes) |
| salvar | diálogo do Mac; as caixas FICAM marcadas para a próxima vez | **Save List › To one file / To several files** |

## 2. As diferenças, campo a campo (a mesma sequência)

| campo | Premiere 26.0.2 (CMX 3600) | MC 25.12 CMX_3600 | MC 25.12 File_129 |
|---|---|---|---|
| codificação | ⛔ **MacRoman** no Mac (`Ç` = 0x82, `Ã` = 0xCC), composto (o arquivo no disco era NFD) · CRLF | **UTF-8** composto no comentário (`C3 87 C3 83`) · CRLF | igual; ⛔ **no campo de REEL o acento vira `U+FFFD` (�)** — um por letra acentuada |
| `TITLE:` | `TITLE: B30 EDL LAB` | `TITLE:   B30 EDL LAB ` (**3 espaços** e espaço no fim) | igual |
| linha em branco entre eventos | **sim** | não | não |
| número do evento | 3 dígitos; **6 com "Nomes com 32 caracteres"** (a única mudança que essa caixa fez aqui) | 3 | **6** (`000001`) |
| **reel** | ⛔ **`AX` em todos** (os MOVs sem tape name); com "Usar nome do arquivo de origem" + "nome original" + 32 caracteres marcados: **continuou AX** (`inferido`: as caixas só agem com tape name ou com o nome do clipe diferente do arquivo — `pendente`) | **o nome da fonte cortado em 8** (`B30_A_MO`, `B30_NOME`): Reel ID = Source File/Tape, truncar no fim | **o nome inteiro**, campo de 129 colunas (preenchido com espaços); MOV **sem** extensão (`B30_A_MOV-PRORES` — o nome do clipe), WAV **com** extensão e em MAIÚSCULAS (`B30_SOM_WAV-BWF.WAV`) |
| canal | `V`, `AA` (o par), **`AA/V`** (vídeo e som juntos num evento só) | um evento por trilha: `V`, `A`, `A2`, …, **`A7`…`A10`** (passa do CMX clássico, que só tem A/A2/AA/B, mesmo no CMX_3600) | igual |
| comentário do nome | `* FROM CLIP NAME: <arquivo com extensão>` | `* FROM CLIP NAME:  <nome do clipe>` (2 espaços) | `*FROM CLIP NAME:  …` (**sem espaço depois do `*`**) |
| nível de áudio | `* AUDIO LEVEL AT <TC> IS -0.00 DB  (REEL AX A1)` em todo evento com som | não | não |
| **dissolve** (24 q centrado no corte A│B) | `C` de duração zero + **`W000 024`** (o *Cross Dissolve* novo vira **wipe 000**, `EFFECTS NAME IS W000`); o evento da transição cobre o clipe B INTEIRO (rec 01:00:02:12–01:00:06:00) | `C` zero + **`D 024`** cobrindo SÓ a transição (rec 02:12–03:12), e o resto do B num evento novo (014); `* BLEND, DISSOLVE` | igual, `*BLEND, DISSOLVE` |
| dissolve de som | `W001 024`, `EFFECTS NAME IS Constant Power` | `* BLEND, AUDIO DISSOLVE` num evento `C` (`inferido`: o FROM/TO saiu invertido, B → A — ver §4) | igual |
| buraco (vazio) | evento **`BL`** (fonte 00:00:00:00–00:00:01:00) | **nenhum** (List Options › Black Edits desmarcado no padrão) | igual |
| velocidade 50 % | `M2   AX       012.0                      03:00:02:00` no vídeo **e no som** | `M2   B30_NOME       012.0                03:00:02:00` só no vídeo (o som não tinha velocidade no MC — ver §4) | igual, reel longo |
| clipe de 25 fps numa sequência 23,976 | **sem M2**; fonte no TC de 25 (`05:00:01:24`–`05:00:04:24`, 75 q = 3 s) | vídeo com **`M2 … 025.0`** e fonte até `05:00:05:00` (76 q); o som no TC de 25 sem M2 | igual |
| ordem | por trilha (todo o V, depois o AA), com AA/V juntos | Sort Mode A (Record In): todas as trilhas misturadas em ordem de entrada | igual |
| fim do arquivo | sem quebra de linha na última linha | sem quebra | sem quebra |

## 3. Quem escreveu esta EDL? (corrige "EDL não tem origem")

CORRIGE (2026-11-25) a linha da EDL em [assinatura-de-origem.md](../../transversal/assinatura-de-origem.md): não há
marca DECLARADA, mas o desenho denuncia — **pista, não prova** (uma amostra de cada; o texto pode ter sido editado):

- **MC:** `TITLE:` com 3 espaços; nenhuma linha em branco entre eventos; `*FROM CLIP NAME:  ` (File_*) ou `* FROM CLIP
  NAME:  ` (2 espaços depois dos dois-pontos); canais `A3`…`A10`; `* BLEND, DISSOLVE`.
- **Premiere:** reel `AX`, linha em branco entre eventos, `* AUDIO LEVEL AT … (REEL AX A1)`, `EFFECTS NAME IS`,
  `AA/V`, um espaço no fim da linha do evento; MacRoman no Mac.
- **Resolve 19:** reel `AX`, linha em branco, `* FROM CLIP NAME: ` (1 espaço) — como o Premiere, mas **dois espaços** no
  fim da linha do evento e ASCII puro.

## 4. O que esta rodada achou FORA do formato (a tradução Premiere → Avid do Conformar)

- ✅ **O som do WAV entrou 1 quadro antes (2026-11-25, resolvido):** duas causas. (1) O PREMIERE: o script pediu 24 q
  (1,001 s); o clipe da bin ficou com 1,000 s e o item da timeline com 23 q — o Premiere posiciona o som pela grade
  dele, então a verdade lá é `06:00:00:23`. (2) O CONFORMAR: o master injetado no Avid começava em 518399 (05:59:59:23)
  em vez de 518400 — a conta do `time_reference` arredondava em 24 antes do pulldown (`protocolos/avb/escrita.md`, o
  CORRIGE do "start do BWF"; metade dos WAVs de gravador a 23,976). Com o conserto, a EDL do MC diz `06:00:00:23`.
- ⏳ **O dissolve de som `FROM B TO A`** na EDL do MC: a transição na bin é IDÊNTICA à que o MC grava (comparada campo a
  campo com as da PRODUCAO-A: `BLEND_AUDIO_DISSOLVE`, cutpoint no meio, os mesmos atributos) e o vídeo de mesma forma
  sai certo — ✅ **CONFIRMADO (2026-11-26, `MC04 FILE129 DISSOLVE A MAO.edl`): é o List Tool.** Um dissolve de som
  feito À MÃO no MC (Quick Transition, atalho `\`, 24 q centrado, A1/A2, no corte seco B → AÇÃO em 01:00:06:00) sai na
  MESMA forma: um evento `C` com a fonte do clipe que ENTRA (`04:00:01:12–04:00:02:12`) cobrindo só a transição (rec
  05:12–06:12), `*BLEND, AUDIO DISSOLVE`, **`*FROM CLIP NAME:` = o que ENTRA e `*TO CLIP NAME:` = o que SAI**; o resto
  de cada lado em eventos próprios (B até 05:12, AÇÃO de 06:12). No A2 o evento leva só o `FROM` (sem `TO`). O vídeo
  continua `C` zero + `D 024` com FROM/TO na ordem certa. ⇒ quem LÊ uma EDL do MC inverte FROM/TO no AUDIO DISSOLVE.
  O Conformar não tem defeito aqui.
- ✅ **Remedido no MC depois dos consertos (2026-11-26, `MC03 FILE129 CONSERTADO.edl` na pasta da rodada):** o WAV em
  `06:00:00:23` (A7–A10), o mesmo quadro do Premiere; e o som do LONGO com `M2 … 012.0` e fonte `03:00:02:00–03:00:03:12`
  nas DUAS trilhas (A, A2) — igual ao evento 011 do Premiere. O resto, byte a byte igual à MC01.
- ⛔ **Mas o MC TOCA o som do LONGO a 100 %** (export pela API + FFT, `spikes/ouvido_mc`): 3700/3800 Hz (a 50 % sem
  correção, 1850/1900) e as claques do lab a cada 24 quadros (408, 432; a 50 %, só a de 432). O Audio Warp escrito é o
  `EFF_TIMEWARP.AUDIO_TIME_WARP` com `_MIXMATCH_MOTIONADAPTER 2` — o ADAPTADOR DE TAXA MISTA: as ~600 ocorrências nas
  bins do SSD são TODAS ele (`speed_ratio` = razão das taxas: 1000/1001, 5/4, 960/1001, 2/5, 4/5); nenhuma é velocidade
  escolhida pelo editor. `hipotese`: com taxas iguais o MC ignora o `speed_ratio`. A EDL diz 50 %, o MC toca 100 %.
  ✅ RESPONDIDO abaixo: é o AudioSuite TIME SHIFT.
- ⭐ **O gesto do editor no MC para a velocidade do SOM é o AudioSuite TIME SHIFT** (autor, 2026-11-26, MC 25.12 Mac; o
  Time Compression Expansion também existe, mas é o Time Shift o certo): Speed 50 % e RENDER. `confirmado` de ouvido
  (export pela API + FFT): com o render, o tom FICA em 3700/3800 Hz e as claques do lab vêm a cada 2 s (0,000 e 1,993 s
  depois do corte) — 50 % mantendo o tom, como o Premiere com `MaintainAudioPitch` ligado. ⛔ SEM render o MC toca a
  100 % (o Time Shift escrito pelo Conformar, export idêntico ao do clipe sem efeito). Estrutura na bin e o chunk:
  `protocolos/avb/escrita.md` (Time Shift). ⛔ **A EDL do List Tool NÃO diz a velocidade do Time Shift** (2026-11-26,
  `MC04`, a B30 EDL 3 com o Time Shift 50 % RENDERIZADO no A1/A2 do LONGO): os eventos de som saem SEM `M2`, com a fonte
  a 100 % (`03:00:02:00–03:00:05:00`, 3 s para 3 s de gravação), enquanto o vídeo do mesmo clipe tem `M2 … 012.0`
  (`03:00:02:00–03:00:03:12`). O Audio Warp (MC03) dava `M2` no som, mas o MC o tocava a 100 %; o Time Shift toca certo e
  a EDL perde. ⇒ numa EDL do MC, som com velocidade = trecho errado da fonte, calado.
- ⬜ A velocidade de 50 % ficou só no VÍDEO no Avid (o som do mesmo clipe entrou a 100 %) — conferir se o Conformar
  passa velocidade ao som.
- ✅ O dissolve de som `AUDIO DISSOLVE` de B para A — é o List Tool (feito à mão, sai igual; ver acima).

## 5. O que a foto de uma lista File_129 de produção acrescentou (anonimizada)

Uma EDL de som de produção (File_129, setting de vídeo nomeada) mostrou: eventos acima de 13 000 (os 6 dígitos são
necessários), reel = o nome do WAV com extensão e `#NN` do take, `*FROM CLIP NAME:` repetindo o reel, um evento cujo
reel é só um número (`260608`, a data — `inferido`: a fita do som direto) e `*BLEND, AUDIO DISSOLVE`.

## 5b. EDL para o SOM: onde a lista sai certa e leva ao lugar errado (MC 25.12 Mac, rodada 2, 2026-11-25)

> Lab `B31_EDL_SOM` (CAM A/B/A2 + som direto BWF de 6 canais, iXML com sound roll `26Y11M25`, cena 12, takes 1/2), linkado
> no `LAB COR MC`; casos escritos por pyavb (Ciclo Assist `spikes/edl_som_mc/montar_casos.py`, que grava o `plano.json` =
> a verdade por evento e trilha); EDLs pelo List Tool (CMX_3600 e File_129, Reel ID Type `Source File/Tape`, Source TC
> `Start`); conferidas por `modulos/conformar/motor/edl/conferir.py` (teste `test_edl_conferir`, 18/18). Saídas e fotos:
> `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_CICLO ASSIST/2026-11-25 EDL SOM MC/`. `confirmado` (uma máquina, uma versão).

| caso | o que a EDL diz | veredito |
|---|---|---|
| S1 subclipe | reel/TC do MASTER (o In do subclipe somado); `FROM CLIP NAME` = o subclipe, em maiúsculas (`A001C003.SUB.01`) | certo |
| S6 AutoSync (`.sync.01`) | imagem com o reel da câmera; som com a TAPE do WAV e o TC do WAV; um evento por trilha, A1–A6 | certo (com o alerta do rolo) |
| S7 group (câmeras só imagem + som direto) | o ângulo ATIVO da imagem (CAM B) e o som direto, cada um com o seu reel; `FROM CLIP NAME` = o master do ângulo (`B001C007_MOV-PRORES`) | certo (com o alerta do rolo) |
| S8 troca de ângulo (botão direito no segmento › o ângulo) | CAM B → CAM A → CAM B evento a evento, o som direto contínuo, TCs exatos | certo (com o alerta do rolo) |
| S10 WAV de 6 usado em 2 canais | `A`/`A2` com o reel do rolo — **nada diz que são os canais 3/5 (e depois 4/6) do arquivo** | ⛔ errado calado |
| S11 dois takes do mesmo rolo | o MESMO reel (`26Y11M25`) nos dois; só o TC (14h × 15h) e o `FROM CLIP NAME` (`12/1` × `12/2`) separam | alerta |

- ⛔⛔ **O canal da EDL é a TRILHA, nunca o canal do arquivo.** Quem conforma lê `A2` como "canal 2 do arquivo" e põe o MIX R
  onde a montagem usou a LAPELA BETO — lista bem formada, som errado. Nem CMX_3600 nem File_129 têm onde dizer.
- ⛔⛔ **O List Tool LEMBRA as trilhas marcadas da sequência ANTERIOR** (Input › Tracks): carregada depois de uma de 2
  trilhas, a de 6 sai só com A1/A2, sem aviso (S6 e S7, CMX e File_129). Clear + Load NÃO repõe; o botão de trilha ALTERNA
  (vindo de uma de 6, clicar A3–A6 os DESLIGA). Conferir a fileira de trilhas antes de todo Preview.
- ⭐ **Reel do som = a TAPE quando o BWF a tem** (iXML `TAPE`/sound roll): o File_129 dá o nome do arquivo à IMAGEM
  (`A001C003_MOV-PRORES`, sem extensão) e a tape ao SOM; sem tape (rodada 1) é o nome do arquivo com extensão. Num dia de
  gravação o rolo é o mesmo para todos os takes: o reel não identifica o arquivo.
- ⭐ Com TC em jam (câmeras e gravador no mesmo relógio), o TC do som na EDL é IGUAL ao da imagem no mesmo instante — a
  EDL não mostra a diferença entre "sincronizado pelo TC" e "sincronizado por outra coisa". ⬜ Medir sem jam (sync por
  claquete/In), onde um NLE que trocasse o TC do som pelo da imagem apareceria.
- ⛔⛔ **O group NA TIMELINE é uma CÓPIA do `Selector` do grupo** (o grupo arrastado pelo autor, lido por pyavb): um
  `Selector` por segmento (`selected`, ganged), um ramo por ângulo apontando o mob de ALINHAMENTO (`.grp`), aparado no
  trecho. Um `SourceClip` apontando o grupo TOCA certo, mas o MC não o vê como group: sem o (g) no nome, sem a lista de
  ângulos, e o `FROM CLIP NAME` da EDL vira `…GRP`. (Ciclo Assist `spikes/edl_som_mc/montar_casos.py::_segmento_de_grupo`.)
- ⭐ **Timeline SÓ DE ÁUDIO (sem nenhum segmento de vídeo; V1 vazia) = a MESMA EDL de som** (pedido do autor: o AAF do
  Premiere com merged clip só sai certo sem vídeo na timeline). Medido no MC 25.12 Mac, File_129: S1, S6, S7 (group na
  forma do MC), S10, S11 — reel, TC, trilha e `FROM CLIP NAME` idênticos evento a evento aos da versão com vídeo. No MC o
  vídeo não muda o que vai anexado ao som. ⬜ O teste que importa é no PREMIERE (merged, multicâmera, nest).
- ⬜ Não medidos nesta rodada: S9 (collapse — adiado pelo autor), Reel ID Type `Source File`
  e `Tape`, as opções de Source TC para o som (Aux/Sound TC), a variante "1 vídeo + todo o áudio", o Premiere.

## 5c. EDL para o SOM no PREMIERE 26.0.2 Mac (rodada 2, B31, 2026-11-25) — com vídeo × SÓ ÁUDIO

> Projeto `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_CICLO ASSIST/2026-11-25 EDL SOM PREMIERE/B31 EDL SOM PREMIERE v02.prproj`;
> merged (Timecode e Pontos de entrada, "Remover áudio do clipe AV") e multicâmera (Timecode, uma única sequência, **Todas
> as câmeras** — o que o autor usa) pelo MENU pelo nome; nest = sequência com o merged por TC dentro; sequências pela
> ponte (Ciclo Assist `spikes/edl_som_premiere/`); EDL pilotando (Arquivo › Exportar › EDL…, diálogo como estava). A
> verdade de cada evento conferida no monitor Programa (o TC e o quadro queimados). Conferidor: 37/37 com o MC.

| caso | o que a EDL diz | veredito |
|---|---|---|
| subclipe | reel `AX`; TC certo (o do master); `FROM CLIP NAME` = o ARQUIVO (não o subclipe) | alerta (só o nome leva ao arquivo) |
| merged por TC | imagem `AX` + nome do MOV; som com a TAPE do iXML (`26Y11M25`) e o TC certo; `AA` + `NONE`/`AUD 3 4` | ⛔ os canais 5–6 SOMEM (4 canais por EDL) |
| merged por pontos de entrada | imagem certa; **som 1 quadro ANTES** (14:00:02:23 × 14:00:03:00) — a EDL é fiel ao merged, que desloca o som (o 240 → 239 já registrado) | ⛔ errado calado |
| multicâmera | reel `AX`, **TC da sequência multicâmera** (00:00:08:08), `FROM CLIP NAME` = a multicâmera | ⛔ errado calado — não leva a câmera nem som |
| nest | reel `AX`, **TC do nest** (00:00:01:00), `FROM CLIP NAME` = o nest; áudio do nest = uma trilha (a mistura) | ⛔ errado calado |

- ⭐⭐ **SÓ ÁUDIO = a MESMA EDL de som nos cinco** (pergunta do autor: o AAF do Premiere com merged só sai certo sem vídeo).
  Na EDL não: o erro vem do TIPO de clipe (multicâmera, nest, merged por In), com ou sem vídeo na timeline.
- ⭐ **"Usar timecode de áudio do clipe" (diálogo Mesclar clipes) NÃO muda a EDL** — S2C/S3C sem a opção (o jeito do
  autor) = S2/S3B com ela, linha a linha, com e sem vídeo: a EDL escreve o TC de CADA componente. A opção muda só o
  TC do PRÓPRIO merged (bin, Origem): por In, 14:00:02:00 (o da câmera) sem ela × 14:00:01:23 com ela (o do áudio,
  com o quadro a menos); por TC os dois começam em 13:59:58:00 (o merged abre no som, que começa antes). A origem
  interna do merged por TC é o começo do SOM nos dois casos.
- O canal: o Premiere escreve `AA` (A1+A2) e um evento `NONE` seguido de `AUD  3    4` para A3/A4 — o leitor do Ciclo
  Assist lê (`motor/edl/leitura.py`). O mapa do diálogo "Áudio N – Canal M" no padrão estéreo exportou as trilhas mono 1–4.
- ⚠️ API (26.0.2 Mac): `createSubClip` nasce na RAIZ e o `getInPoint()` do subclipe lê o master inteiro — o recorte vale
  na timeline; `overwriteClip` de um MERGED põe o ZERO do merged no tempo pedido (o trecho cai em posição + entrada) e na
  trilha de ÁUDIO traz o vídeo junto; `TrackItem.move()` move só aquele item; `importFiles` numa BIN não seleciona (na raiz
  sim); `ProjectItem.select()` substitui a seleção. ⛔⛔ **Merged e multicâmera estão em `app.project.sequences`:
  `deleteSequence` em "todas as sequências" APAGA os merged e as multicâmeras** (aconteceu; filtrar por nome e por
  `isMergedClip`/`isMulticamClip` do item).

## 6. Pendente

- DROP-FRAME (29,97) — não medido (o projeto de laboratório é 23,976).
- Título (Titler+ / gráfico essencial) — não entrou nesta rodada.
- Por que as caixas de nome do Premiere não mudaram nada (tape name gravado no MOV; clipe renomeado na bin).
- Windows: a codificação do Premiere lá (cp1252?) e do MC — `pendente` (matriz de plataforma).
- File_32 e File_16 do MC (só CMX_3600 e File_129 salvos).
