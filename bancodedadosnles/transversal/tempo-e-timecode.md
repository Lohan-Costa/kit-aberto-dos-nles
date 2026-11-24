# Tempo e timecode entre formatos

Cada NLE mede tempo de um jeito. Traduzir timeline entre elas exige converter a unidade **e** a
convenção (drop/non-drop, nominal/real). Fatos consumíveis em
[tempo-e-timecode.json](tempo-e-timecode.json). Confiança `confirmado`.

## Unidade por formato

| formato | unidade | detalhe |
|---|---|---|
| **AAF** (Avid) | **frames** | `edit_rate` como Fraction; fps típico `24000/1001`. `SourceClip.start` em frames — cuidado com Selector (offset em `reconstructed.N`, não na fonte). |
| **PRPROJ** (Premiere) | **ticks** | `254.016.000.000 ticks/s` (exato). Frame 23.976 = `10.594.584.000` ticks; sample 48k = `5.292.000` ticks. |
| **DRT/DRP** (Resolve) | **segundos** (blobs) e **frames nominais** (timeline) | Convenção da timeline: NOMINAL = `round(fps)`, non-drop. |
| **OTIO** | **RationalTime** (valor+rate) | frames nominais. |

## Conversões

```python
secs   = frames / fps
ticks  = round(secs * 254_016_000_000)        # → Premiere
frames = ticks / ticks_por_frame              # ← Premiere
# AAF offset map → curva do Resolve:
X = tl_frame / fps                            # tempo de saída (seg)
Y = (source_start + src_frame) / fps          # tempo de fonte (seg)
```

## Convenção de TC (armadilha)

- **23.976 drop vs non-drop:** o AAF do Avid costuma ser `24000/1001`. Ao escrever DRT/OTIO, a
  convenção corrigida no RELINKER é **NOMINAL** (`round(fps)`, non-drop) — evita o bug de TC de
  projeto. Anotar sempre se o número é nominal ou real.
- **Dropframe é só rótulo:** internamente, mantenha **frames contínuos non-drop**; DF entra só na
  exibição/input (29.97/59.94, separador `;`). Vale para qualquer fps non-drop
  (23.976/24/25/29.97ND/30/50/59.94ND/60). Ver [../protocolos/aaf/estruturas.md](../protocolos/aaf/estruturas.md) §FPS.
- ⛔ **Comparar contagem com RÓTULO** (2026-11-21, `confirmado`, Conformar `media/matcher_masters`, lab Baselight
  2997DF): o `Timecode.start` do AVB/AAF é CONTÍNUO; o TC do arquivo pelo ffprobe chega como rótulo DF (`14:59:50;00`).
  Converter o rótulo com `;` (base 30/60) para contínuo ANTES de comparar — lido como NDF, às 15h a diferença é de
  1620 quadros (54 s) e o arquivo certo parece outro. ⚠️ Décimos minutos (15:00, 15:10) não pulam: mídia de teste
  de DF tem de atravessar um minuto que pula (15:01:00;02), senão o pulo não é medido.
- **`MZ.ZeroPoint` (Premiere):** TC exibido na posição 0 da timeline, em ticks. Multicam usa
  `min(alternate_start)` entre câmeras.

## Um timecode não é um número: é um número MAIS a base em que ele conta — `confirmado` (2026-08-14)

`10:01:38:21` não vale nada sozinho. A mesma string vira **36 098,84 s** se conta a 25 e
**36 134,97 s** se conta a 23,976 — **36 s de diferença**, que é a deriva de 0,1 % do NTSC
acumulada em 10 h (`10 × 3600 × 0,001`).

O erro de método é tratar a base como propriedade do PROJETO ou do ARQUIVO. Ela é do
**aparelho que gravou**: o gravador de som tem relógio próprio e ninguém promete que ele
conta na base da câmera. Numa diária, bases diferentes são o normal, não a exceção.

⚠️ **E não dá para acreditar num campo só porque o nome dele promete a resposta.** Um MXF
OP-Atom de som declarava `comment_Soundroll TC Rate = 25` num projeto a 23,976 — usar essa
taxa deslocou o som em 36 s. O que derrubou a tag foi um **árbitro independente dentro do
próprio arquivo**: o relógio de parede do gravador (`comment_Shoot Date`, do `OriginationTime`
do BWF), que só a hipótese de 23,976 reproduz — com 26 ms de erro. Detalhe e tabela do
contra-teste em [../protocolos/mxf/timecode.md](../protocolos/mxf/timecode.md) §4.

**Corolário para quem guarda "segundos desde a meia-noite":** o valor tem duas procedências
possíveis e elas NÃO são a mesma unidade.

| origem | o que conta | herda o 0,1 % do NTSC? | volta do dia |
|---|---|---|---|
| `time_reference` de um **BWF** | amostras desde a meia-noite REAL | não | **86 400 s** exatos |
| um **timecode** `HH:MM:SS:FF` | frames na base nominal, cada um durando `1/fps` | sim | `tc_day_seconds(fps)` = **86 486 s** a 23,976 |

A 24 fps cravado as duas coincidem e a distinção some — motivo pelo qual ela passa
despercebida em validação feita só em material 24. A 23,976 são **86 s de erro por dia
atravessado**. Quem misturar as duas procedências no mesmo campo precisa carregar junto a
taxa: a presença dela é o que diz qual volta usar.

## SRT conta tempo real; o grid de frames denuncia o fps — `confirmado` (2026-10-02)

- O tempo do SRT é **tempo real** (relógio do player), não um rótulo de TC: o frame na
  timeline é `round(ms × num / (den × 1000))`. Em 23.976, `01:00:00,000` cai no frame 86 314
  (`00:59:56:10` de TC), não em `01:00:00:00`. Só em **24 redondo** os dois coincidem. O
  Legenda → AAF até a v1.0.0 posicionava pelo tempo real, mas **exibia** `h:m:s` + ms→frame,
  e a prévia divergia do AAF em ~1 s a cada 16 min (corrigido na v1.1.0).
- SRT exportado de software de legendagem cai no grid de frames do vídeo (≤ 1 ms do frame
  exato); SRT cronometrado à mão não cai em grid nenhum (amostra `BIN AVID/legenda teste`:
  ~5 % em todas as taxas, que é o acaso). **23.976 e 24 se separam bem**, porque um grid
  escorrega 1 frame a cada 1000 em relação ao outro (só ~5 % de coincidência). Já **23.976 e
  29.97 coincidem a cada 4/5 frames** (4 × 1001/24000 = 5 × 1001/30000), o que dá ~25 % de
  falso acerto. O limiar de "o fps escolhido serve" precisa ficar acima disso (o app usa 50 %).
- ⚠️ Um SRT feito **contando TC de 23.976 como se fosse tempo** (`ms = ff × 1000/24`) cai
  exatamente no grid de 24 e é indistinguível de um SRT de 24 fps real. O grid aponta a
  suspeita, mas não decide sozinho.

## Ponte de TC via o ORIGINAL (técnica de relink) — `confirmado` (2026-06-14)

Quando a timeline já está relinkada ao **original** (não ao offline), o TC de câmera de cada
segmento vem do original casado — e os **erros herdados do offline deixam de importar** (TC zerado
ou fps convertido no offline tornam-se irrelevantes):

```python
TC_camera_do_segmento = TC_do_ORIGINAL_casado + (source_start / fps_da_fonte)
```

Uso prático (ligar uma timeline a **trims da cor**, que têm duração diferente mas TC preservado):
- O portão de **duração não serve**; o gate é **contenção de TC**: candidato = nome do clipe
  (presente no nome do trim) **+** range de TC do trim **contém** o range de TC de câmera do segmento.
- **Offset (seek)** = `TC_camera − TC_trim` = o **handle de cabeça**. Determinístico, sem busca visual.
- Trims duplicados do mesmo clipe são desambiguados justamente pela contenção de TC.

Fonte: `RELINKER/docs/color-relink.md` (amostras `TESTES DE TC E DIFERENCIACAO DE DRONES/`).

## TC em multicâmera: o que ele resolve e o que ele NÃO resolve — `confirmado` (2026-07-12)

Numa diária de ficção (N tomadas, um som direto por tomada), o TC é a ferramenta mais poderosa que
existe para sincronizar — **e a mais fácil de usar errado.** As quatro regras abaixo foram medidas
com material real (`DRAMASYNC`, `sync/tcmatch.py`; dataset `PRODUCAO-A`, 4 diárias).

### 1. O TC de uma câmera contra o de OUTRA não vale NADA

Câmeras não jamadas têm relógios arbitrários (no dataset: CAM A em `01:31`, CAM B em `23:18` — 22 h
de distância). **Só o som que as duas gravaram as liga.** Nunca posicionar uma câmera em relação a
outra por TC.

### 2. O ALINHAMENTO DO DESENHO: deslizar o padrão de blocos e buracos

Câmera e gravador têm relógios diferentes, mas ambos correm em tempo real: a diferença entre eles é
uma **constante Δ**. Como gravaram os mesmos momentos, o padrão de blocos (gravando) e buracos
(parado) é o mesmo nos dois — **deslizar um sobre o outro revela Δ sem decodificar um frame de
áudio.**

Medido: **o TC prevê o offset de sync com ~0,1 s (2–3 frames).** Δ é constante por REGIME e só muda
quando alguém reinicia/rejama um aparelho.

O ganho não é velocidade, é **correção**: reduz de ~24 para ~1,1 os candidatos a som por clipe. Numa
busca cega, as tomadas repetidas competem entre si e a correlação escolhe a errada.

### 3. O alinhamento precisa SABER QUANDO NÃO SABE

Com um som **contínuo** cobrindo o dia, deslizar as câmeras para qualquer lugar dentro dele dá
cobertura total: não há pico, há um **platô** (de ~54 min, no caso medido), e o argmax devolve um Δ
arbitrário **com cara de resposta**. Detectar a largura do platô e devolver vazio → cair na forma de
onda. Sem isso, o método mente com confiança.

### 4. A POSIÇÃO vem do grafo de sync; o TC só ANCORA as ilhas

O TC de uma câmera pode não ser relógio de parede: uma câmera em **rec-run** (o TC só avança
gravando) posiciona errado — no caso medido, 51 s de intervalo onde a realidade dizia 166 s.

> **Regra:** dentro de uma ilha do grafo clipe↔som mandam os OFFSETS medidos. O TC só ancora as
> ilhas ENTRE SI — onde é indispensável (numa diária, uma tomada não tem relação com a outra) e onde
> é confiável (**free-run**).

E o REGIME de um clipe se descobre pelo **TEMPO** dele, não pelo Δ dele: um clipe mal sincronizado
tem Δ errado, então agrupar por Δ o joga no regime errado — justamente o clipe que se quer consertar.
Usar as âncoras confiáveis PRÓXIMAS NO TEMPO.

---

## Ler uma janela de áudio com precisão de amostra (ffmpeg) — `confirmado` (2026-07-12)

Todo app que compara áudio (sync, waveform, monitor) precisa extrair um TRECHO de um arquivo. Se a
janela não começar na amostra pedida, cada faixa ganha o seu próprio erro e o alinhamento morre.

```bash
ffmpeg -v error -ss {start} -t {dur} -i {arquivo} -vn -ac 2 -ar 48000 -f f32le pipe:1
```

**`-ss` ANTES do `-i` é busca rápida E exata à amostra** no ffmpeg moderno (≥ 2.1: ele busca o
keyframe anterior e decodifica/descarta até o ponto exato). Medido contra a extração do arquivo
inteiro: **deslocamento ZERO, correlação 1,0000** — tanto em AAC dentro de mp4 quanto em WAV de 5
canais.

`-ss` DEPOIS do `-i` também é exato, mas decodifica desde o início e descarta: lento para posições
distantes. **Não use `-noaccurate_seek`.**

Custo medido (janela de 15 s, estéreo, 48 kHz = 5,7 MB): 22 ms num WAV, 57 ms num mp4/AAC.

---

## Velocidade e rampa entre NLEs

| NLE | onde mora | fidelidade |
|---|---|---|
| AAF | `speed_ratio` + `source_offset_map` + `motion_effect_type` | fonte rica |
| DRT | `MediaTimemapBA` (curva Bézier 2D) | **fiel SÓ na forma exata** (2026-10-12: quadros inteiros, sem aproximação, +0,001 — ver drt-drp/estruturas.md §1) |
| OTIO | `LinearTimeWarp` (só constante) | rampa = bake/metadata |

**Tradução recomendada Avid→DRT:** amostrar o `source_offset_map` e emitir **keyframes lineares
densos** (Douglas-Peucker, `interp=0`) — frame-exato e à prova de freeze/reverse/rampa-aparada.
Detalhe: [../protocolos/drt-drp/dados/timemap.json](../protocolos/drt-drp/dados/timemap.json).

⭐ **REGRA (o autor, 2026-10-12): entre NLEs DIFERENTES a rampa é replicada QUADRO A QUADRO** — praticamente um
keyframe por quadro, cada quadro no valor exato da fonte; NÃO se recria curva editável ("a ciência de curva de
velocidade de cada fabricante é única": aproximar cria diferença). A curva nativa (keyframes, alças, âncora,
interpolação) só se preserva do MESMO programa para ele mesmo (Avid → Avid). Estudar a curva de cada NLE serve à
LEITURA e ao caminho do mesmo programa.
**Refinamento (mesmo dia):** só as CURVAS (rampas) se "queimam" quadro a quadro. Velocidade **constante** (linear,
para mais ou para menos) vai como velocidade constante NATIVA do destino, sem quadro a quadro. **Optical Flow** no
Premiere/Resolve num clipe **desacelerado** (ex.: 50 % fixo) → **FluidMotion** no Avid (é na câmera lenta que ele cria
os quadros que não existem); em aceleração não faz diferença. `pendente`: rampa com Optical Flow que passa por câmera
lenta (o quadro a quadro inteiro não sintetiza) — decisão do autor quando aparecer.

**Tradução recomendada Premiere → Avid (2026-10-12, `confirmado` no laboratório do MC):** `MotionEffect` com o
**mapa (p1) = posição exata da fonte em cada quadro** — o render do MC segue o mapa, não a curva — e a curva (p0) só como
apoio (vel_Avid = vel_Premiere × taxa da fonte ÷ taxa da timeline) — pela regra acima, a forma final é um keyframe por
quadro (`pendente`: o gráfico de POSIÇÃO com um keyframe por quadro, medir o render); clipe de outra taxa =
adaptador PROMOVIDO; velocidade de um Nest vai para DENTRO do Collapse. Detalhe: `../protocolos/avb/estruturas.md`
§"Rampa (Timewarp)".

### ⭐ A MATRIZ das rampas entre os três NLEs — validada no laboratório (2026-10-12, B22)

Modelo NEUTRO = a posição EXATA da fonte em cada quadro do plano (todos os três mostram o PISO dela). Onde a curva
começa e termina sai das próprias posições (velocidade quadro a quadro igual = constante; muda = curva). Casos: A
(constante → curva → constante) e B (começa DENTRO da curva) — **mesmo quadro 48/48 nos SEIS sentidos**:

| de ↓ / para → | Avid | Premiere | Resolve |
|---|---|---|---|
| **Avid** (leitor: mapa p1 / p0 da bin) | — | ✅ | ✅ (forma exata do DRT) |
| **Premiere** (leitor: `_remap_fonte`) | ✅ | — | ✅ (forma exata do DRT) |
| **Resolve** (leitor: canto arredondado, drt-drp §1) | ✅ | ✅ | — |

Escritores: Avid = gráfico de POSIÇÃO, keyframe por quadro só na curva, Linear no constante (avb/estruturas.md);
Premiere = Time Remapping com canto onde a velocidade muda, curva começando em (0, 0) e In inteiro (prproj/estruturas.md);
Resolve = `MediaTimemapBA` só com quadros inteiros, colineares juntados, +0,001 (drt-drp/estruturas.md). Velocidade
constante = nativa; Optical Flow em câmera lenta = FluidMotion / `TimeInterpolationType 2` / (Resolve: pendente) —
nas posições fracionárias cada um sintetiza a seu modo.

**No APP (De Lá Pra Cá, ramo `rampas`, 2026-10-12):** ✅ forma exata do DRT (`7b6a568`); ✅ leitor do Avid com o gráfico
de posição; ✅ **escritor do Avid pelo gráfico de POSIÇÃO** (`avb_export/translate.py`, molde `EFF_TIMEWARP_POSICAO` =
o preset do MC) quando a origem NÃO é o Avid — origem dita por quem chama ou lida do AAF (`origem.py`,
[assinatura-de-origem.md](assinatura-de-origem.md)); Avid → Avid continua com a curva nativa (decisão do autor). Os
keyframes são só os quadros onde a velocidade muda (`motor/rampa.py::keyframes_hibridos`): entre eles, linear exato.
**`confirmado` pela imagem: o MC 25.6 renderizou a B22 com os Timewarps escritos pelo app → A 48/48 (21 keyframes),
B 48/48 (16).** ✅ leitor do Resolve (`rampa.posicoes_do_timemap`, o canto arredondado, `timemap_decode` + `<In>` do clipe)
48/48 contra o render do Resolve. ⚠️ Fonte de OUTRA taxa: o gráfico de posição sobre o adaptador de taxa NÃO foi medido —
o escritor mantém o caminho antigo (curva aproximada + mapa) e avisa no log. Faltam no app as ROTAS (Premiere → Avid,
Resolve → *: o leitor de DRT inteiro) e o escritor * → Premiere (espera o lado Premiere do app, decisão do autor).

### Como o quadro do meio é feito (interpolação de tempo) — os três NLEs

| intenção | Premiere `TimeInterpolationType` | Resolve `RETIME_*` (paramID 0x5B) | Avid `_SFX_RENDER` (Type no Motion Effect Editor) |
|---|---|---|---|
| quadro inteiro (amostragem) | ausente = Frame Sampling (`hipótese`) | 1 Nearest | **2 Both Fields** (0 Duplicated, 1 Interpolated, 3 VTR-Style também dão quadro inteiro pelo piso) |
| mistura de quadros | 1 = Frame Blending (`hipótese`) | 2 Frame Blend | 4 Blended Interpolated (5 Blended VTR) |
| fluxo óptico | **2 = Optical Flow** (`confirmado` pela imagem, B22, 2026-10-12) | 3 Optical Flow | **6 FluidMotion** (7 FluidMotion Draft) — o equivalente do Optical Flow (o autor, 2026-10-12) |

Os valores do Avid foram LIDOS no editor (2026-10-12); os do Premiere ainda pedem a interface.
⭐ **Na tradução (decisão do autor, 2026-10-12): só a linha do fluxo óptico se correlaciona.** A mistura de quadros
(Frame Blending / Frame Blend / Blended Interpolated — inclusive o padrão do adaptador de taxa do MC) vai como quadro
inteiro, o padrão dos três: "dificilmente gera bons resultados".

## O mesmo rótulo de TC com e sem drop-frame é o MESMO TC (`confirmado`, laboratório BL08 P7, 2026-11-22)

O original de 29,97 grava `16:58:50;00` (DF) e a conversão copiou o rótulo como `16:58:50:00` (NDF) — comum quando o
conversor perde só a marca de drop-frame. Contados em quadros contínuos, os dois ficam **61 s** longe (1832066 × 1833900), e
o portão de TC do casador do religar recusava o original certo como "timecode diferente". ⇒ Quem compara TC de casamento
aceita também o rótulo idêntico tirando o `;`/`:` (Conformar `media/matcher_masters._portao_tc`). A posição na fonte não
depende disso: a ponte pelo original conta em segundos desde o início do arquivo.

