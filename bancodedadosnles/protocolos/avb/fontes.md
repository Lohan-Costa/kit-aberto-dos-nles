# AVB — fontes / rastreabilidade

| data | o quê | como / amostra | confiança |
|---|---|---|---|
| 2026-06-27 | Cabeçalho AObjDoc byte a byte | `pyavb 1.4.0` `avb/file.py` (AVBFile.__init__/write_header) cruzado com hexdump de `ARQUIVOS PARA ANALISAR/BIN/AUDIO-MAR (2).avb` | confirmado |
| 2026-06-27 | Leitura do grafo de objetos | `avb.open()` nos 3 bins (`AUDIO-MAR (2).avb`, `bin nova.avb`, `03_OC_EDIT VALENDO.avb`) — todos abriram | confirmado |
| 2026-06-27 | Taxonomia de mobs | histograma de `mob_type`/`usage` de `03_OC_EDIT VALENDO.avb` (1200 mobs) | confirmado |
| 2026-06-27 | Tabela de 66 classes | `avb.utils.AVBClaseID_dict` | confirmado |
| 2026-06-28 | Relink AMA ponta-a-ponta no MC | byte-patch de `path_posix`+`_AMA_FILE_DATE_TIME` → import no MC 25.12 → online | confirmado |
| 2026-06-28 | **Writer do pyavb não aceito pelo MC** p/ mobs AMA modificados | A/B no MC: troca de MobID via pyavb-write → offline (v5..v9); a MESMA troca via byte-surgery → online. Amostra `BS MOBID TEST Bin.avb` vs `CLONE DJI v5..v9` | confirmado |
| 2026-06-28 | Layout do MobID no disco (intercalado c/ tags) | `pyavb ioctx.read_mob_id`/`read_uuid`/`write_uuid` + busca da região de 24B no cru de `teste 10 Bin.avb` (essência 3x, master 1x, arquivo 2x) | confirmado |
| 2026-06-28 | TOC `object_positions` + `instance_id` p/ scoping | `pyavb file.py` (AVBFile.read_object: `object_positions[idx]` + header 8B, dados não comprimidos) cruzado com contagem de duração/data por intervalo de objeto | confirmado |
| 2026-06-28 | Clonagem de mídia AMA nova (byte-surgery) | `tools/avb_clone.py` clonou DJI_0004 (2434f) e DJI_0005 (5884f) do template `teste 10` → MC 25.12 → online + tocando duração inteira | confirmado |
| 2026-07-04 | Motion effect de VÍDEO no tradutor via parser do Relinker | O `Segment` do Relinker traz speed_keyframes/source_offset_map (unidade source-por-timeline = a que o control point do AVB MotionEffect espera, NÃO o speed_ratio recíproco); `avb_export/translate.py::_motion_entry_from_seg`; validado no MC (B001 85% slow + a006 125% fast tocam com velocidade) | confirmado |
| 2026-07-04 | Autoria genérica do CDCIDescriptor de vídeo do ffprobe | diff de A004 1920x1088 vs B001 2048x1088 (descriptors reais aceitos pelo MC) isolou os campos de geometria; autorar 2048 do skeleton 1920 saiu IDÊNTICO ao B001 real (offline). Ver `dados/cdci-video-descriptor.json`; ferramenta `RELINKER/src-python/avb_export/video_descriptor.py` | confirmado |
| 2026-07-04 | Port do backend AVB p/ o Relinker | pacote `RELINKER/src-python/avb_export/` (translate/video_descriptor/clone/relink/merge/nle_model + templates.json embutido); comando sidecar `export_avb`; regressão 12/12 portada passa; saída idêntica ao eng-rev original (fingerprint) | confirmado |
| 2026-07-04 | Reader tolerante + decode do ext 0x02 do PCMA | `eng-rev/tools/avb_read.py`: drain-patch generalizado (não crasha) + decode 0x02 = `read_assert_tag(0x47)+u32 LE` (faixas de música). 133 PCMA lidos, 0 crash, 8 valores 0x02 minerados | confirmado |
| 2026-07-04 | Field-correlator de corpus (constante vs derivado) | `eng-rev/tools/avb_corpus.py`: em 45 CDCI AMA-H.264 (--where) exatamente 9 campos variam (= o mapa de geometria) e 49 constantes; revelou 2 populações (H.264 vsub=2 vs DNxHD vsub=1) | confirmado |
| 2026-07-04 | Golden-diff offline (portão sem MC) | `eng-rev/tools/avb_golden.py video`: re-autora cada CDCI H.264 real do skeleton+ffprobe chamando o gerador de produção (`avb_export.video_descriptor`) e diffa vs o real -> 45/45 IDÊNTICOS => MC aceita por lógica, sem round-trip humano | confirmado |
| 2026-07-04 | Gerador + golden de ÁUDIO (PCMA do ffprobe) | `avb_export/audio_descriptor.py` + `avb_golden.py audio`: 50/50 PCMA essência IDÊNTICOS (int 16/24b + float 32b, 1-5ch). O golden PEGOU um gap: `SoundEssenceCoding` presente só no float — corrigido e re-validado offline | confirmado |
| 2026-07-04 | Mapeador de offset + byte-patch de descriptor | `eng-rev/tools/avb_offsets.py`: instrumenta o read do pyavb -> byte exato de cada campo. Byte-patch da geometria CDCI 1920->2048 re-lê IDÊNTICO ao B001 real => clone format-genérico na via byte-surgery online. Caixas têm tag 0x47 antes de cada valor (den=próximo s32) | confirmado |
| 2026-07-04 | Clone AMA format-genérico (byte-surgery) | `eng-rev/tools/avb_clone_generic.py` compõe avb_clone(cadeia) + avb_descriptor_patch(geometria) + avb_relink(path tam!=) + Timecode start por clipe. CONFIRMADO NO MC: bin de 43 câmeras (1 template) online, B001 2048 não-corrompido, TC certo | confirmado |
| 2026-07-04 | Media-bin builder genérico | `oc_integration/build_media_generic.py`: clone_generic por arquivo + merge + emite media_map. 43 câmeras H.264 de 1 template -> CONFIRMADO NO MC (online, B001 2048 ok, TC por clipe). Substitui build_from_relinked (cruzamento-only) | confirmado |
| 2026-07-04 | Timecode start por clipe (offset -2) | Bug do clone: TC herdava do template. Avid armazena `Timecode.start = ffprobe_TC_frames - 2` (offset -2 constante, 4/4 H.264). TC num SourceMob (Timecode component, fps=24 non-drop). Byte-patch em avb_clone_generic -> TC construído == real (788822/126968/279711/764846) | confirmado |

| 2026-07-05 | Áudio PCMA: samples ≠ frames + taxa de amostragem | `RELINKER/avb_export/clone_generic.py`: master/tracks em frames@edit_rate, `PCMADescriptor.length` em samples@sample_rate; `samples=ceil(frames/er*sr)`; byte-patch de sample_rate/edit_rate/average_bps p/ taxa real. Corrige `PMM_INSUFFICIENT_MEDIA`+`CM_INVALID_DUP` no save (offline audio). Bin `PRODA_AVB_TESTE_09` | confirmado |
| 2026-07-10 | Áudio MPEG embutido (MPGADescriptor) coerente | `.mov/.mp4` c/ AAC/MP2 vira mob MPGA separado; clonar o vídeo exige ajustar TAMBÉM a track própria do MPGA + `descriptor.length` ao frame-count real (master sozinho não alcança: 5267 vs 5268). Dup-range ao Extract sem isso. `clone_generic.py` | confirmado |
| 2026-07-10 | **Transições: REGRA DO HANDLE** (achado central do `CM_INVALID_DUP`) | Comparação campo-a-campo TransitionEffect autorado vs bin nativa `03_OC_EDIT VALENDO.avb`: objeto IDÊNTICO (left_length=15 constante, precompute/curva eram falsas pistas). Regra medida: clipe antes precisa `handle_after≥L−C`, depois `handle_before≥C`. 0 violações em 194 reais; 10 na nossa (todas offline). Ver `dados/transicoes-handle.json` | confirmado |
| 2026-07-10 | Fix handle offline (folga sintética) | mídia offline autorada com `master_len+=2H` + clipes deslocados `+H` (H=maior transição+margem). Violações 10→0. `avb_export/media_bin.py::_offline_specs` + `translate.py::set_offline_handles`. Validado no MC (`PRODA_AVB_TESTE_23.avb` salva com dissolves) | confirmado |
| 2026-07-10 | Curva de blend da transição reescalada ao L real | `param_list[N].control_track` (N=0 áudio, 1 vídeo): offset do último control point + length = L da instância, não do template. `translate.py::_set_dissolve_curve`. 86/86 coerentes | confirmado |
| 2026-07-10 | Fades clipe↔silêncio + corte-seco no cutpoint | fade-in `[Filler,Trans,Clip]` / fade-out `[Clip,Trans,Filler]`; corte-seco apara cauda A em L−C e cabeça B em C (source_start) p/ o corte cair no cutpoint. `translate.py::_position_row`/`_trim_tail`/`_trim_head`. PRODA 86→135 transições (+49 fades), MC OK | confirmado |
| 2026-07-10 | Ganho de áudio: Audio Gain → PanVolumeEffect | OperationGroup `'Audio Gain'` (AAFRational, `level=num/2^29`, 2^29=0dB) → `PanVolumeEffect` (level_set=True, pan=16384, `_TRK_CLIP_G=1` na track). Unity não embrulha. PRODA 166 PanVolumeEffect, validado no MC (dB certos + sync) | confirmado |
| 2026-07-10 | **Título Avid Titler+: texto no param `Text Box Text` (blob AVUP)** | V3=sub-seq 2 do NestedScope; op `'Avid Titler+ Legacy'`; texto no blob AVUP (`'PUVA'` após UUID 16B; data UTF-8). Bytes crus via `param['Value'].data` (`.value` devolve `[]`). Extração feita (`RELINKER/aaf/parser.py::_extract_title_params`), `text='PRODUCAO-A'`. Ver `dados/titler-texto.json`. Reconstrução AVB pendente | confirmado (extração) / pendente (reconstrução) |

Amostras: `eng-rev-bin-e-mdb/ARQUIVOS PARA ANALISAR/BIN/`. Bin nativa ground-truth da PRODA: `z ignore o que esta aqui/PRODUCAO-A/_PROJETO/01_EDICAO/PRODUCAO-A/03_OC_EDIT VALENDO.avb`. Bins de teste geradas: `RELINKER/AAFs-modelos/AVBs/PRODA_AVB_TESTE_NN.avb`.
Ferramenta: `pyavb` 1.4.0 (PyPI: `pyavb`, import `avb`), autor Mark Reid (markreidvfx/pyavb).
Ecossistema: descoberta/RE em `eng-rev-bin-e-mdb/` (laboratório) → consolidação em `RELINKER/` (app) → conhecimento no banco. Os dois convergem e se alimentam.


## 2026-08-09 — `_MONSTATE` (monitor da timeline)

**Como:** o Órbita autorou uma `.avb`, o Media Composer 25.12 a abriu, o editor ligou o MONITOR na
V2 pela GUI e salvou. Diff dos `session_attr` da bin salva contra o que o writer escrevia
(`avid/writer.py` marcava `_MONSTATE=0` em TODAS as tracks de vídeo).

**Amostra:** `primeiro teste dentro do avid.avb`, projeto `MULTCAM IMPORT PARA PLUGIN`
(2 câmeras + 1 áudio estéreo, 23.976 fps).

**Prova:** depois da correção, a bin gerada saiu **idêntica** à salva pelo MC nesse atributo
(picture 1→`0`, picture 2→`1`, sound 1 e 2→`2`). Coberto por
`DRAMASYNC/src-python/tests/test_avid_writer.py::TestOMonitorDaTimeline`, com dois testes que
guardam armadilhas: que a marcada é a **última** track de vídeo (e não a primeira), e que o som
**não** pode ser uniformizado com o vídeo.

**Não resolvido:** o que `_ENBLSTATE` controla.

## 2026-08-20 — plugins AMA, motores de leitura e procedência da bin

**Amostras**

| bin | o que é |
|---|---|
| `ORBITA - TESTE/XOCN LINK.avb` | 3 Sony X-OCN 8K (LT/ST/XT) pelo plugin nablet + 1 ProRes 4444 4K pelo `MSP_MXF`. MC 25.6.0.58781 / Win 11 |
| `ORBITA - TESTE/prores.avb` | **o MESMO arquivo ProRes**, linkado pelo **UME** |
| `MIDIAS DE TESTES/TESTE ATALHO/TESTE  ATALHO Bin.avb` | X-OCN 6K linkado pelo nablet **5.1.0.5530** (MC 21.12) + MXF nativos |
| `47_PRODUCAO-A/…/02_OC_EDITS.avb` e mais 67 bins | acervo real, varrido para a tabela GUID→plugin |

**Método**

Experimento controlado dos dois lados, com harness em
`MIDIAS DE TESTES/SONY XOCN/medicao/` (`medicao_xocn.py`, `ROTEIRO.md`):

- **três codecs, um motor** — LT/ST/XT na mesma bin ⇒ o `descriptor.uuid` é do plugin.
- **um arquivo, dois motores** — o mesmo ProRes por `MSP_MXF` e por UME ⇒ o `uuid` muda.
- `snapshot antes` / `snapshot depois` em volta da instalação do plugin: 154→159 binários
  catalogados com SHA-256 e `FileVersion`, `RegisteredExtensions.xml` guardado inteiro, e
  varredura de 12 GUIDs conhecidos em 7 codificações.
- Os 16 bytes de `_CONTAINER_HANDLER_GUID` rastreados até `UME/MXF_ContainerHandler.acf`.

**Documentação do fabricante**

`nablet SONY RAW X-OCN AMA Plugin Release Notes and Manual v2026.8.0.pdf` — é dele a
confirmação de que o nome do plugin gravado na bin é **carimbado no link e nunca atualizado**.

**Correções que saíram daqui**

- `dados/avb-header.json` campo 12: `ATob` não é constante, é o discriminador de tipo de
  documento (`ATob` bin, `ATpj` projeto) → [../projeto-avid/](../projeto-avid/README.md).
- `dados/ama-online.json`: o "há DOIS mecanismos de assinatura de tipo" (2026-07-02) era, na
  verdade, **dois motores de leitura** — `mecanismo_handler` fica marcado como superado por
  `dois_motores` e `camadas_de_identidade`.
- `../../transversal/banco-de-midias-compartilhado.*`: o `mob_id` de mídia AMA não é gerado
  fresco *sempre* — é gerado quando o arquivo não tem UMID para copiar.

---

## 2026-08-21/22 — entrelaçamento e a rota até o arquivo (Promo Entrega, Win11, MC 2025.6.58781)

**Primeira vez que a família mede entrelaçamento do lado Avid.** Origem: 6 bins reais em
`Documents/Avid Projects/` (ORBITA - TESTE, XOCN LINK, prores, BENDITO FIELD Bin), lidas com
pyavb, mais `ffprobe` sobre os `.mxf` correspondentes.

| bloco | confiança |
|---|---|
| `CDCIDescriptor.frame_layout` + `line_map` guardam o entrelaçamento; num `MultiDescriptor` o CDCI está **dentro** de `descriptors` | confirmado |
| Todo material progressivo desta máquina: `frame_layout=0`, `line_map=[42,0]`. **Nenhuma amostra entrelaçada chegou a uma bin** — os valores 1/3 seguem por confirmar | confirmado / **pendente** |
| **Mídia AMA** → `WinFileLocator.path` traz o caminho. **Mídia gerenciada** → o locator EXISTE e o `path` é **string vazia** (`if loc:` passa e entrega `''`) | confirmado |
| Caminho do Avid é letra + `//` + barras normais (`D//A/B/x.mxf`) | confirmado |
| `material_package_umid` (ffprobe) == `mob_id` do SourceClip da bin, byte a byte — ⚠️ em **ordem de bytes diferente** (pyavb GUID little-endian × MXF big-endian SMPTE, nos 16 últimos) | confirmado |
| TC da composição: `component.fps` é a taxa de **contagem** (30 para 29,97), `edit_rate` é 29.97; `flags=0` na amostra non-drop — **drop-frame não medido** | confirmado / **pendente** |
| ⚠️ `ffprobe` reporta `r_frame_rate=15000/1001` **e** `avg_frame_rate=30000/1001` nestes OP-Atom | confirmado |

Dados: [`dados/entrelacamento-e-locators.json`](dados/entrelacamento-e-locators.json).
Método completo do rabo de vídeo:
[`../../transversal/rabo-de-video-campo-escondido.md`](../../transversal/rabo-de-video-campo-escondido.md).


---

## 2026-09-13 (noite) — clipe de MATTE KEY na bin, e 1080i/59.94 sem drop-frame (Ciclo Assist, Win11, MC 2025.6.58781, pyavb 1.4.0)

Origem: projeto `MAIS VC AUTO` montado pelo editor — artes `.mov` QuickTime Animation com
alpha (`qtrle`, `argb`, 1920×1080, 30p), um MXF XDCAM 1080i/29,97 (`mpeg2video`
`field_order=tt`) e um roteiro só em PNG. Duas bins: `MAIS VC AUTO Bin` (mídia **importada**,
nomes `.new.01`) e `MIDAS LINK` (a mesma mídia **linkada AMA**). Lidas com pyavb em cópia.
Código: `cicloassist/avid/take.py` (`especie`, `efeito_de_chave`).

| bloco | confiança |
|---|---|
| ⭐⭐ **Arquivo com alpha vira, na bin, um CLIPE DE MATTE KEY:** `CompositionMob` `usage_code = 3` (o MESMO `"effect"` do preset de Color Correction) chamada `Matte Key: <nome>`, com uma `Track` → `TrackEffect` **`EFF2_BLEND_MATTE_KEY`** de 3 trilhas: **1 = `Filler`** (o fundo), **2 = `SourceClip` → master `track_id 1`** (preenchimento), **3 = `SourceClip` → mesmo master `track_id 2`** (alpha); `keyframes` = `EffectParamList` com 2 `ParameterItem` (0% e 100%, `level 1073741824`, `scale 65536`) | confirmado |
| ⭐ O master dessas trilhas é **oculto** (`user_placed=False`), `MasterMob` com `usage = "precompute"` e duas trilhas de imagem. Na importação: preenchimento `MPGIDescriptor`, alpha `RGBADescriptor`, ambos **1920×540** (`frame_layout` 1 e 3 — campos). Na AMA: a mesma forma, com `_IMPORTED_AMA: 1` | confirmado |
| ⇒ **O que separa matte key de preset é haver MÍDIA dentro do `TrackEffect`.** Um leitor que recuse todo `usage == "effect"` como preset recusa as artes (foi o que impediu o modelo de usá-las) | confirmado |
| Os mobs de arquivo das artes importadas guardam o locator do **arquivo original** (`rdp HJ.mov`): pela bin se chega ao `.mov`, e ele decodifica no ffmpeg (`qtrle`) | confirmado |
| Taxas na AMA: as artes `30/1` e uma vinheta `24/1` ficam com `edit_rate` 30 e 24 na bin, dentro de um projeto 29,97; na importação, tudo vira 29,97 | confirmado |
| **Timecode:** TODOS os `Timecode` das duas bins têm **`flags = 0`** — o MXF (`01:00:00:00`, dois-pontos, `start=108000`, `fps=30`), os `.mov` (`start=0`) e a sequência autorada com `flags=0` e regravada pelo MC. Projeto `1080i//59.94`, `iTCFormat=1` nas configurações | confirmado |
| ⭐⭐ **Drop-frame MEDIDO** (bin `SEQ ANALISE`, sequência `TC DROPFRAME` criada pelo editor no MC): `Timecode.flags = 1`, `fps = 30`, **`start = 107892`** — a contagem CONTÍNUA de `01;00;00;00` (108000 − 2 × 54). A non-drop da mesma bin: `flags = 0`, `start = 108000`. ⇒ o `start` é sempre quadro contínuo; o drop-frame só muda o RÓTULO (a regra do [`../../transversal/tempo-e-timecode.md`](../../transversal/tempo-e-timecode.md) vale para o AVB) | confirmado |
| ⭐⭐ **Matte key DENTRO da timeline MEDIDO** (sequência `ANALISE MATTE`): na V2, direto na `Sequence`, **o mesmo `TrackEffect EFF2_BLEND_MATTE_KEY` do clipe da bin** — trilha 1 `Sequence[Filler]` com `TrackRef relative_scope=1` (o fundo é a trilha de BAIXO), trilhas 2/3 `SourceClip` → `precompute` `track_id` 1/2, `param_list` com 3 `ParameterItem`, `keyframes`. A V2 inteira: `Filler`, efeito, `Filler`, efeito, `Filler` de rabo. Ordem das trilhas: V1, **V2**, A1…A4 | confirmado |
| O que o MC **acrescenta** ao editar: `attributes._MATCH` (`MobRef` para o clipe de matte key da bin), caches de reprodução (`left_bob`, `bob_data` com `MPGPosition`/`DIDPosition`) e, nos `SourceClip` internos, `_BOUNDS_REFORMATTING_OPTION = 0` + `_IMAGE_BOUNDS_OVERRIDE` (XML de enquadramento `-800/1 -450/1 1600/1 900/1`) | confirmado |
| O MC guardou **oculto** na bin da sequência o clipe de matte key (`usage=effect`) e o master `precompute` — o mesmo "fecho" que o Ciclo Assist grava para subclipes | confirmado |
| Um segundo matte key da mesma sequência (`rdp AM`) tem as trilhas 2/3 como `Sequence` de 3 componentes, com um `TrackEffect` ANINHADO no preenchimento — forma diferente, causa não medida (efeito aplicado pelo editor?) | observado |
| ⭐ **Autoria conferida contra a referência** (Ciclo Assist, `timeline.Cobertura`): copiar o `TrackEffect` do clipe da bin e aparar dá, campo a campo, o efeito que o MC gravou — diferença só nos atributos que o MC acrescenta (linha acima). **Carregar no MC ainda não testado** | confirmado (arquivo) / pendente (MC) |

---

## 2026-09-13 — master AMA pela bin, a espécie do item, e a string nula (Ciclo Assist, Win11, MC 2025.6.58781, pyavb 1.4.0)

Origem: bins `BIN COM MIDIA AMA LINK` e `BIN COM SEQUENCIA AMA LINK` montadas pelo editor
(BRAW, MOV do RED e WAV linkados), `BIN ORIGEM`, e as diárias gerenciadas de
`O PRODUCAO-A` — projeto `_ASSIST ANTERIOR`. Código: `cicloassist/avid/take.py`,
`cicloassist/avid/avb_fiel.py`, `spikes/a_bin_ama_regravada.py`.

| bloco | confiança |
|---|---|
| ⭐ **Cadeia do master AMA, inteira DENTRO da bin:** `MasterMob` → mob de arquivo (`MultiDescriptor` ou `PCMADescriptor`, `MSMLocator`) → mob físico (`MediaDescriptor` ou `TapeDescriptor`, `WinFileLocator` com o caminho em `path_utf8`). Em mídia gerenciada a cadeia sai da bin no primeiro passo | confirmado |
| ⚠️ O mob de arquivo AMA tem o **MESMO nome** do master (`A003_03170837_C001` ×2). Achar item pelo nome sem preferir o master devolve o mob de arquivo conforme a ordem da bin | confirmado |
| Um arquivo AMA tem imagem e som JUNTOS: as tracks de picture e de sound do master apontam o **mesmo** caminho — o filtro por sufixo `_A01` do OP-Atom não se aplica | confirmado |
| ⛔ O `.mov` do RED tem **4 streams de áudio mono** (as pistas 3 e 4 em -90 dB nos 77 clipes da pasta); sem `-map`, o ffmpeg só lê a primeira | confirmado |
| BRAW: `ffprobe` abre o contêiner e lê o áudio (`pcm_s24le`, 2 canais), mas o vídeo sai `codec_name=unknown` — o ffmpeg comum não decodifica (o [`../mxf/README.md`](../mxf/README.md) aponta o SDK Blackmagic) | confirmado |
| `usage_code = 3` (`usage == "effect"`) é **efeito salvo na bin** — medido: o `Color Correction` da `BIN ORIGEM`, `CompositionMob` de `length 0`, uma `TrackEffect` `EFF2_RGB_COLOR_CORRECTION` com 36 `ParameterItem`. É o preset que o editor arrasta para a bin | confirmado |
| Master reconhecido pelo **tipo** (`MasterMob`), não pelo `usage`: normalmente `usage_code = 7` (`"mastermob"`), mas uma bin de `PRODE` tem **36 masters com `usage_code = 0`** | confirmado |
| Nenhuma bin do projeto tem group clip (`usage_code = 4`) nem clipe de matte key — **não medidos** (⭐ o matte key foi medido depois: ver a seção de 2026-09-13 "MAIS VC AUTO"; ⭐ o group clip foi LIDO em 2026-11-11: `sincronizacao-e-subclipes.md` §5) | pendente |
| ⛔ String com tamanho `0xFFFF` = campo **nulo**; o pyavb a regrava `00 00` e o MC recusa a bin inteira → [`escrita.md`](escrita.md) | confirmado |


---

## 2026-08-25/26 — sincronização e autoria de subclipe (Assist anterior, Win11, MC 2025.6.58781)

**Primeira vez que a família ESCREVE subclipe** — até aqui o banco só registrava o inverso
(`denest.achatar`, De Lá Pra Cá). Origem: `_ASSIST ANTERIOR/assist_anterior/modulos/preparar/`,
sobre `D02_SYNC.avb` — diária 2 de *PRODUCAO-A* sincronizada pelo **Órbita** e aberta no
MC pelo autor.

Tema novo: [`sincronizacao-e-subclipes.md`](sincronizacao-e-subclipes.md).
Dados: [`dados/autorar-subclipe.json`](dados/autorar-subclipe.json).

| bloco | confiança |
|---|---|
| Subclipe = `CompositionMob` com `usage_code=2`, relido como `usage == 'subclip'` | confirmado |
| As 4 armadilhas do pyavb ao autorar: `Composition()` ignora o nome; `TrackGroup` usa `edit_rate=25`; índice da track é sequencial por mídia e **não** o `track_id`; `Track.media_kind` é `@property` que deriva do componente | confirmado |
| Anatomia da bin sincronizada do Órbita: 1 `CompositionMob` de corte seco + masters na mesma bin; `V1` + 5 trilhas de som direto + **2 de som de câmera** | confirmado |
| ⭐ **Som direto × som de câmera se distingue pelo MASTER**: o do gravador de campo não tem trilha de imagem, o da câmera tem | confirmado |
| `SourceClip.start_time` é **sempre 0** nesta saída (`adapter.py:89`) → a fronteira da tomada vem da posição na timeline | confirmado |
| Em todas as 24 tomadas o som liga **antes** da câmera (98 a 299 frames) e costuma parar depois | confirmado |
| ⚠️ **O mob não sobrevive ao `close()`** do `topen` — e `mob.name` continua respondendo, o que esconde o defeito (ver [`escrita.md`](escrita.md)) | confirmado |
| O MC **abre** a bin autorada e **mostra** os subclipes | confirmado |
| O MC resolve subclipe cujo master mora em **outra bin**? | **pendente** |
| Imagem e som **em sincronia** no source monitor | **pendente** |
| A mesma anatomia vale para a saída do **AutoSync do MC**? | **pendente** — nenhuma bin do AutoSync foi lida |

⚠️ Rastreabilidade da rodada dentro do Avid, com os vereditos item a item:
`_ASSIST ANTERIOR/docs/VALIDACAO-P2A.md`.

---

## 2026-08-29/30 — `_ASSIST ANTERIOR`, módulo Assistir: emitir o corte de uma cena

App: `_ASSIST ANTERIOR` (`assist_anterior/modulos/assistir/`). Material: *PRODUCAO-A*, cena C04 —
`CENAS/C04.avb` (16 subclipes) e os WAVs de som direto da D02. **Validado na GUI pelo autor**,
Media Composer 25.6, Windows.

Registrado em [`escrita.md`](escrita.md), três seções novas no fim.

| bloco | confiança |
|---|---|
| ⛔⛔ Toda track de `Sequence` tem de **terminar** em `Filler` — `CompIsFiller(last)`, `ASequence.c:1549`. Invariante ESTRUTURAL, distinta da de duração: a soma pode fechar e a bin ser recusada assim mesmo | **confirmado** — 7 de 7 timelines não abriram sem o trail; abriram com ele |
| Uma sequência escrita pelo PRÓPRIO Media Composer termina toda track em `Filler` | **confirmado** — lido da `SYNC.avb` do projeto |
| ⛔ `SourceClip` apontando **SUBCLIPE** que não está na bin **não resolve** — o MC cai com `ACCESS_VIOLATION` (`0xC0000005`) ao carregar a timeline. A bin ABRE e lista as durações certas; o crash é ao abrir a timeline | **confirmado** |
| ⭐ A distinção que explica a seção *"Bin com SÓ A TIMELINE"*: **master** resolve pelo `msmMMOB.mdb` (é mídia); **subclipe** é `CompositionMob`, objeto de bin, e não tem registro de mídia | **confirmado** pelo par de casos (bin de 6 KB com masters funciona, 2026-08-08; bin de 64 KB com subclipes cai, 2026-08-30) |
| ⭐⭐ Levar os mobs **ocultos** (`item.user_placed = False`) entrega a "bin só com timeline" sem perder a resolução. Medido na `SYNC.avb` do Órbita: **299 itens, 1 visível** | **confirmado** |
| ⭐ **Por que ocultar é o comportamento certo:** toda bin do MC é banco independente, e `matchframe`/`reveal file` levam o editor à bin em que o clipe **não** está oculto — a de ORIGEM, onde ele o organizou | **confirmado** — conhecimento operacional do autor |
| `SourceClip` apontando subclipe com `start_time` **não-zero** é estrutura válida e abre no MC | **confirmado** — 645 frames, 6 cortes, in/out dentro do clipe |
| Track de imagem POVOADA sai `_ENBLSTATE=0/_MONSTATE=0` do `translate.py`, e a V1 VAZIA sai `1/1` — o que deixa a timeline com vídeo nascendo com o vídeo desligado | **confirmado** (o valor certo para o caso de conferência é `1/1`: **inferido**, um caso) |

### ⚠️ A pergunta que continuava pendente, e o que hoje NÃO respondeu

A tabela anterior lista *"O MC resolve subclipe cujo master mora em **outra bin**?"* como
pendente. **Continua pendente** — hoje mediu-se o caso vizinho e diferente: uma **timeline** cujo
**subclipe** mora em outra bin (não resolve, cai). O caso de origem — subclipe numa bin, master
noutra — não foi tocado.

### ⚠️ Custo de não ter consultado o banco

A seção *"Bin com SÓ A TIMELINE"* (2026-08-08) já estava escrita quando esta rodada começou, e
não foi lida. O resultado foi um crash no Media Composer do autor e dois experimentos para
redescobrir metade do que estava registrado — e a outra metade (a distinção master × subclipe)
só apareceu ao ler a seção **depois**. → *Consultar `escrita.md` ANTES de autorar bin é mais
barato que qualquer experimento.*

| 2026-09-20 | A bin no DISCO fica para trás da bin aberta: subclipe sem o mob do master, que volta sem nome — e o conserto é salvar a bin, não procurar mídia | falha real de transcrição nos 10 subclipes da `CENAS\C07.avb` às 09:16, bin gravada às 09:17:12, e o mesmo arquivo resolvendo depois do save (Assist anterior) | confirmado |
| 2026-09-24 | Timeline INTEIRA como lista de eventos: `speed_ratio` = timeline÷fonte, `param_list[0]` = fonte÷timeline, `param_list[1]` = mapa de offset, `[1000,1001]` = conformação, `Selector [Filler, clipe]` = clipe desabilitado, trilhas internas de efeito são `Sequence[Filler(0), clipe, Filler(0)]` — ver `estruturas.md` §"Ler uma timeline INTEIRA" | 5 sequências reais lidas por `_DeLaPraCa/motor/avb_bin/segmentos.py` (curta PRODA MC 25.6/Win; PRODE; PROGRAMA-J; 2 de 2008): todas as trilhas fecham no comprimento da sequência e os masters batem com `avb_bin/masters.py`; DRT gerado da bin do PROGRAMA-J (2 clipes = 743 frames = a sequência) | confirmado |
| 2026-09-24 | `nle_model.locator_path` (lê só `path_posix`) devolve `None` em toda bin do Windows — o caminho está em `WinFileLocator.path_utf8` | 4 bins reais do Windows, locator impresso campo a campo | confirmado |
| 2026-09-24 | `Selector [Filler, clipe]` = clipe desligado que o Resolve importa como `Flags=2` (som); som de subclipe embrulhado em `PanVolumeEffect` | comparação com o DRT nativo do Resolve 19 da mesma timeline | confirmado |
| 2026-09-25 | `avb.open(caminho)` deixa o arquivo aberto quando o cabeçalho falha: no Windows a `.avb` fica TRANCADA (WinError 32) até o processo cair | `.avb` inválida de 1 byte no `tests/test_receber.py` do De Lá Pra Cá; o `TemporaryDirectory` não conseguiu apagar. Sumiu abrindo o arquivo antes e fechando na falha (`avb_export/reader.py::topen`) | confirmado (Win) · Mac inferido |
| 2026-10-12 | Rampa sobre clipe de outra taxa: o MC recusa calado efeito de velocidade sobre o adaptador (precisa do Promote no Motion Effect Editor, 6296); Promote = `_MIXMATCH_MOTIONADAPTER 4` + curva/mapa; velocidade em quadros da fonte por quadro; âncora = pp code 14; o render segue o MAPA (p1); escrita pelo `_set_motion_speed` = piso(mapa) 144/144 | laboratório `avid_rampas.py`, LAB_RAMPA_M0–M3 (B02 25/59,94 + B14_FRENTE_100 transcodificados na taxa de origem), Promote feito pelo autor no LAB_RAMPA_MC_P4c; gabarito dos 8 presets Timewarp (LAB_EF_TIMEWARP) | confirmado |
| 2026-10-25 | Motion do Premiere → Resize/PIP/3D Warp na bin: unidades AFX/DVE, espelho = `DVE_ROT_Y_U` 180, `DVE_ROT_Z_U` com sinal oposto ao do Resolve, keyframe de parâmetro por `ParamClip` linear no `control_track` | PRODC_CORTE02 no MC 25.12 (Mac) × referência, 144 pontos pela foto do Record: 108 → 133 (`_DeLaPraCa` 54c242f; `estruturas.md` §Motion do Premiere) | confirmado |
| 2026-10-25 | AniMatte escrito do zero (BZFX gerado, keyframe por quadro, `keyframe_size` = 168 + bloco) a partir da máscara do Premiere; imagem parada com adaptador de taxa = PGLUE_IMPOLITE_PORT_NUMBER | PRODC_CORTE02 no MC 25.12 × referência: 133 → 144/144 (`_DeLaPraCa` f9b8c01) | confirmado |
| 2026-10-25 | Link de BWF de gravador no MC: master = sSCENE/sTAKE, `_USER` do bext/iXML (TapeID, Shoot Date, Scene, Take, TRK renumeradas, Production, Circled), fonte de tape = sTAPE | bin do autor com 3 WAV do PRODC (MixPre-6) linkados no MC 25.12 Mac × `_DeLaPraCa/motor/media/bwf.py` (igual campo a campo, `ba285a3`) | confirmado |
| 2026-10-25 | Laboratório do nome no link de WAV: CENA+TAKE (bext ou iXML) → `CENA/TAKE`; sem → o arquivo com a extensão como está; `;` NÃO muda (Mac 25.12); acento ok; nome longo não trunca | 11 WAV sintéticos (`laboratorio-de-midia/lab/bancadas/avid/nomes_audio.py`), AMA Management limpa, Source Browser do MC 25.12 Mac; bin `saida/bancadas/avid/nomes_audio_bin_mc2512.avb` | confirmado |
| 2026-10-28 | Title+ atual: o MC grava ACENTO cru em UTF-8 no `Code` (é, ó, Ç, Ã, Ê, Ũ, ’); controle (tab) vai como `0x9` pelo escritor; `{ } =` pendente | varredura de 574 `.avb` (Avid Projects do Mac + MIDIAS DE TESTES): `TITLE EXEMPLOS`, `PROJ-X - RG_DIRECTO-BOARD_RELINK`, `TEST PRODC COM TEXT 1_SEQ` | confirmado (acento) |
| 2026-10-29 | Ganho de clipe: `level` int32 → teto +12,04 dB; Premiere (até +15) → Avid vai a +12 contado | bins `VOLUME FIXO` e `VOLUME 15DB 2` (LAB_ARRASTO_MAC, MC 25.12 Mac) montadas pela rota Premiere → Avid, timeline + Audio Mixer (Clip); varredura das bins reais sem automação de volume | confirmado |
| 2026-10-29 | Automação de volume = 2ª trilha do PanVolumeEffect (control_code 1000, ControlClip linear, offset desde o início do clipe, value na escala do ganho); `_TRK_AUTO_G` | bins `VOLUME FIXO` (autor), `VOLUME KF` (Add Keyframe pela API) e `VOLUME KF APP 2` (escrita pelo app, abre com a curva), LAB_ARRASTO_MAC, MC 25.12 Mac | confirmado |
| 2026-11-21 | O Input Sizing do Resolve no MC pela rota do Conformar (PIP/Resize/3D Warp): 10 de 10 casos <= 3,8 px de 1920 (o piso da foto do monitor); o SetPosition pela API travou o MC 25.12 Mac | `lab/bancadas/avid_sizing.py` (MC 25.12.0 Mac, LAB_ARRASTO_MAC) | confirmado (Mac) |
