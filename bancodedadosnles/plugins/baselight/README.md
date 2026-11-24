# Baselight (FilmLight) — projetos, mídia, conform e a FLAPI

> **Versão:** Baselight **7.0.3.26500** para macOS (o `.dmg` de 2026-11-07). **Confiança de tudo abaixo: `hipotese`**
> — lido da documentação oficial que vem DENTRO do instalador (aberto sem instalar, 2026-11-21) e do GitHub oficial;
> nada medido ainda. Cada item sobe para `confirmado` quando for medido no programa (o trial começa na ativação).
> Impressão digital: o nome do `.app` (`/Applications/Baselight/<versão>/Baselight-<versão>.app`) e o `filmlightapi-<versão>`
> da roda Python.

**Para que nos serve** (autor, 2026-11-21): o Baselight **só recebe**. A sequência do MC ou do Premiere tem de chegar
conectada nos originais de câmera, pronta para cor. Plano do Ciclo Assist: `2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-21-baselight.md`.
⭐ **A estação do Baselight só tem o Baselight** (autor): nunca abrir com outro NLE aberto; fechar MC/Premiere/Resolve
antes, com force quit se preciso. O Mac mini M4 de 16 GB está no mínimo do programa.

## Onde estão as fontes

- `PROGRAMAS COM CLAUDE/8 REFERENCIA/BASELIGHT/instalador-7.0.3-extraido/…/Contents/`:
  `doc/FL-BL-UG-1027-v7_UserGuide.pdf` (o manual, ~1 000 páginas; Conform nas págs. 336–368, Job/Scene e o banco nas
  ~110–125), `doc/FL-BL-TR-0845-BLTrainingManual.pdf`, `doc/FL-BL-QR-0449-Utilities.pdf` (os utilitários de linha de
  comando), `doc/flapi/python.html` (a referência da API), `share/flapi/schema/schema.json` (a API em JSON:
  `Classes`/`Constants`/`ValueTypes`), `doc/FL-GN-TN-0476-FLESpec.txt` (o FLE → [../../protocolos/fle/](../../protocolos/fle/README.md)),
  `doc/release_history*.html|txt` (notas de versão — ricas em detalhes de conform de AAF).
- `8 REFERENCIA/BASELIGHT/`: transcrições do vídeo de introdução e do webinar da FLAPI; `recursos.rtf` (links).
- GitHub oficial: `github.com/FilmLightAPI/enhancements` (exemplos; `FLAPI Tools/Python CLI Examples/insert_seq.py` cria
  job + scene + insere mídia), `FilmLightAPI/flapi-dev-mcp` (MCP oficial para DESENVOLVER scripts FLAPI com um agente).

## Como ele guarda projetos

- **Não há arquivo de projeto.** Tudo vive num **PostgreSQL** (o instalador traz `postgresql-9.3.4-r7.pkg`) num
  *database host* (`localhost` numa máquina só). Hierarquia: host → **job** (o projeto) → pastas → **scene** (a timeline;
  pode ser um filme inteiro, um rolo ou um plano só). Grava sozinho a cada mudança (o "save" fecha uma versão).
- Trava por scene (*Database scene lock*); `bl-unlock` destrava.
- Entre máquinas: `bl-export` (job ou scene para arquivo) e `bl-import`. A FLAPI **não** exporta scene; o webinar da
  FilmLight chama o `bl-export` por subprocesso.
- Linha de comando: `bl-mkjob`, `bl-mkscene`, `bl-lsjobs`, `bl-lsscenes`, `bl-lshosts`, `bl-delete`, `bl-jobs` (Job
  Manager sozinho). Ajuda: `<utilitário> -i` (ou `--help`). No Mac, em `…/Contents/bin/` (o guia antigo diz
  `/Applications/Baselight/Current/Utilities/Tools`; o MCP da FilmLight diz que esse caminho NÃO existe no Mac 7.x).

## Como ele importa mídia

- Nada é copiado: o plano na timeline é uma *sequence strip* (a "Layer 0") com um ponteiro para o arquivo.
  Filme = um arquivo (R3D, ARRI, BRAW, MXF, MOV…); sequência de quadros pela sintaxe FilmLight `nome.%.7F.exr`.
- Na mão: **FLUX Manage** (Ctrl+B). Boa prática do vídeo oficial: o *container path* da scene na raiz do projeto.
- Ao inserir mídia com LUT embutida da câmera, pergunta se aplica (o vídeo oficial: "Do not apply" e lembrar).
- FLAPI: `SequenceDescriptor.get_for_template(caminho, ini, fim)` / `get_for_template_with_timecode(caminho, tcIni,
  tcFim)` → `Scene.insert_sequence(seq, onde, relativoA, espacoDeCor, formato, fps)`; `onde` = `INSERT_START`,
  `INSERT_END`, `INSERT_BEFORE`/`AFTER` (na mesma trilha, relativo a um Shot), `INSERT_ABOVE`/`BELOW` (outra trilha).
  `insert_blank(r, g, b, duração, …)` para buracos. Do Shot: `get_src_start_timecode`, `get_src_end_timecode`,
  `get_record_timecode`, `get_metadata_strings(["clip","tape","srctc"])`.

## Como ele importa timelines (o conform)

Scene › Conform (Win/Ctrl+E). Dois passos: carregar a lista (mostra os eventos e o que já dá para deduzir, como a taxa)
e conformar com as opções; o resultado é uma aba por combinação tentada, com a % de mídia achada, as alternativas quando
há mais de um candidato e o relatório de mídia referenciada/handles/faltante.

**Formatos lidos:** CMX 3600 · **AAF do Avid** · **XML do Premiere** (o xmeml do FCP 7: cortes, dissolves, algumas
transições e camadas) · DLEDL do Autodesk · **FLE** (da FilmLight, com o caminho do arquivo). Multitrilha por AAF ou XML.
**Não lê OTIO nem FCPXML** (nenhuma menção no manual).

**Opções que importam para nós:**
- *Range Type*: **Source** (conformar nos originais) × Record (cortar um render da edição).
- *Search directory*: até 7 pastas, com subpastas; filtro por template e por extensão; TC track 1/2.
- *Match Events by*: **Avid UID** (só em AAF do Avid) · nome de arquivo · tape no caminho · tape no cabeçalho · nenhum (só TC).
- *Overwrite Tape Name* (EDL que trunca a fita em 8 caracteres) · *Treat Tape as* spacer.
- *Frame Rate*: 30 → 24, pulldown 2:3, 50@25 e 60@30.
- *Apply Image Transforms*: as transformações do evento viram uma camada (padrão **Layer 99**, categoria Editorial).
- *Apply ASC CDL* / *Apply LUTs* do evento.
- *Scene Timecode*: sobrescrever o TC da timeline pelo da EDL, ou posicionar pelo TC já existente.
- **Partial conform**: conformar contra planos já na timeline (relink, VFX, o que faltou).
- **Sequence versioning**: achar versões novas de uma mídia pelo nome.

**Das notas de versão (7.x), sobre AAF:** "Conforming an Avid AAF will now use the assigned Avid **Locator**"; detecção do
formato da sequência com **3D Warp e FrameFlex** (antes caía num 1920×1080 de reserva); aviso por clipe quando a mídia
não pode ser consultada; nomes e cores de marcadores do MC; dissolve sempre como operador Transition; SDK AAF 1.2.0.
⭐ Para o Conformar isso casa com o `motor/aaf/writer.py`, que regrava só os `URLString` dos locators.

- **Conferir contra a referência é À MÃO** (manual pág. 349, 454, 1 000+): o filme de referência (QuickTime com TC queimado,
  saído da edição) numa scene à parte, os cursores das duas scenes no mesmo grupo de *ganging*, sync point, e o
  Wipe Layout (Ctrl+F2) / multi-cursor para olhar plano a plano. Não há comparação automática — o lugar do nosso
  "quadros da timeline × vid ref" (plano do Ciclo Assist).

**`bl-conform`** (linha de comando; script cifrado do interpretador `flicicw` da FilmLight — o uso exato só com
`bl-conform --help` instalado): conforma numa scene nova **ou existente**; `--FilenamePrefix` (aparar o prefixo comum
dos caminhos da EDL), `rp=` em `--defaultfilter`/`--src`, `--stereoeye`, LUT, CDL de XML e cópia de grades.
Irmãos: `bl-cmx2fl` (CMX → FLE), `bl-genedl` (EDL de todos os arquivos de pastas), `bl-scenedetect` (FLE por detecção de
corte), `bl-shots` (lê/troca os arquivos das strips de uma scene).

## O lado do MC: o que o AAF já leva (medido 2026-11-21, MC 25.12 Mac, `confirmado`)

Sequência montada sobre masters **transcodificados no próprio MC** (AMA → Clip › Consolidate/Transcode → DNx SQ) e
exportada pelo `ExportFile` (preset "AAF" de fábrica, link sem exportar mídia): o AAF traz a cadeia INTEIRA até o
original — `SourceClip` da sequência → `MasterMob` `<nome>.new.01` → `SourceMob` com `CDCIDescriptor` (o MXF em
`Avid MediaFiles/MXF/1/V01…mxf`) → `SourceMob` com **`ImportDescriptor` e o Locator do ORIGINAL**
(`file:///SSD/…/A001C001_….mov`; os `start` da cadeia em 0, o in só no clipe da sequência). ⇒ Mas isso NÃO é o cenário de projeto (autor, 2026-11-21): a conversão pode ter sido feita FORA do MC, sem metadado
nenhum dela; o editor online religa as mídias originais no MC e entrega um AAF apontado para elas — e na sala de cor o
Baselight pode ainda apontar para OUTRO caminho (uma cópia local dos originais 4K/8K, pela banda). O caminho do AAF é
informação, não endereço: o conform tem de valer por nome/TC/fita. ⭐ "O Baselight se dá bem com o MC" (autor) = ele
entende melhor os EFEITOS do AAF do MC, não a mídia. ⚠️ O MC do Mac grava o Locator com o NOME DO VOLUME
(`file:///SSD/…`), sem `/Volumes/`. Kit: `laboratorio-de-midia/lab/bancadas/avid_baselight.py`, receita `receitas/baselight/BL01_CONFORM.json`.

## O kit K1/BL02 de ponta a ponta, ANTES do Baselight (medido 2026-11-21, MC 25.12 Mac, `confirmado`)

`laboratorio-de-midia/lab/bancadas/avid_baselight.py`: dailies ProRes Proxy feitos FORA do MC (mesmo nome e TC dos
originais) → sequência no MC → AAF offline (só conhece os dailies) → **o fluxo do Conformar** (`relink.preparar` +
`aplicar`: 4/4 masters por nome exato, 18 referências trocadas) → AAF online exportado do MC (masters = os AMA dos
originais; Locators nos `.mov` de câmera; ins preservados) → **conferência original × vid ref**: 6/6 eventos EXATOS pelo
código de barras (1º, meio e último quadro), e a lista sabotada (in +1, clipe trocado) ACUSADA.
- ⛔ Importar no MC o AAF do `relink_aaf` SEM o "remapear" do `relink.py` reaproveita os masters dos DAILIES que já estão
  no projeto (mesmos MobIDs) — a sequência fica nos dailies. E conferir pela IMAGEM não distingue daily de original quando
  o daily foi feito do original (o texto queimado "3840×2160" estava nos dois): conferir pela cadeia/MobID ou resolução.
- ⚠️ O online perdeu o A2 (offline e religado com 2 trilhas de som, o AAF do online com 1) — pendente no Conformar.
- ⚠️ `parse_aaf` devolve o `local_path` do Locator do Mac como `/SSD/…` (sem `/Volumes/`).
- Comparação por imagem (diferença média de cinza, original reduzido a 1920×1080 × ref DNxHR LB): certo 1,1–1,7; quadro
  vizinho 2,9–11,8; clipe trocado ~7. Na mídia SINTÉTICA o vizinho difere só nos dígitos — material real terá margem
  maior (a medir).
- FLE gerado da lista (`fle/…_CAMINHO.fle` e `_NOME.fle`): `# fps 24` para 23,976 e caminhos com espaço = a medir no
  Baselight.

## O lado do PREMIERE, antes do Baselight (medido 2026-11-21, Premiere 27.0.0 Mac, `confirmado`)

`laboratorio-de-midia/lab/bancadas/premiere_baselight.py`: os mesmos dailies e cortes da BL02 montados pela ponte (in e
posição por `Time.ticks`, quadro-exato) → XML (`Sequence.exportAsFinalCutProXML`) → a cópia religada pelo motor do
Conformar (`prproj/copia.gravar_copia`: 4 `<Media>` nos originais, FrameRect no raster novo) → `importSequences` → Scale
50 no original UHD (o que o produto faz) → o XML das sequências novas → **conferência original × vid ref do Premiere**
(`exportAsMediaDirect` ProRes 422): CORTE SECO 6/6 e DUAS TRILHAS 2/2 EXATOS; imagem certo ~0,8 × vizinho ≥ 2,4 (com
ref ProRes a margem é maior que com o DNxHR LB do MC).
- O xmeml do Premiere leva, por `<file>`: `pathurl`, `timecode/string` do arquivo, raster (`samplecharacteristics`) —
  **sem reel/tape**; a sequência começa em 00:00:00:00; o `<file>` repetido vem só pelo `id`. No religado: o raster do
  original (3840) e o `Scale` 50 no clipitem — o caso a medir no Baselight ("Apply Image Transforms").
- ⛔ O `importSequences` traz a sequência com o MESMO NOME da original: achar/exportar por `sequenceID` (a 1ª exportação
  da bancada saiu da sequência ANTIGA, dos dailies).

## Efeitos escritos PELA BIN no MC e conferidos × vid ref (medido 2026-11-21, MC 25.12 Mac, `confirmado`)

BL04 (`avid_baselight.montar_efeitos`): os segmentos neutros → `avb_export.build_avb` (origem "premiere") numa bin
nova, sobre os dailies; o MC abriu e renderizou. Lido quadro a quadro no vid ref (código de barras): dissolve 12 ✅,
50 % ✅ (cada quadro 2×), 200 % ✅ (pula 1), congelado ✅; ⛔ **REVERSO toca PARA FRENTE** (300 → 347) — e o AAF que o
MC exporta dele diz 300 → 253 (`parse_aaf`: in 253, mapa 47 → −1): o AAF que iria à cor NÃO bate com a imagem. O
online pelo fluxo do produto (`relink`) mantém os efeitos (velocidades pelo mapa, `PaintResize_v2`, `SBlend_v2`); a
conferência (mapa de fonte por quadro, pula a transição) dá 5/6 exatos e ACUSA o reverso; Resize/3D Warp ficam sem
conferência pela barra (comparar com a transformação aplicada = a fazer). ⚠️ Defeito do Conformar a corrigir: o
reverso do `avb_export` (origem premiere: `speed` negativo com o inner no in) — no MC precisa de outra forma.

✅ **Corrigido (BL04 R2, mesmo dia):** a velocidade constante negativa no `EFF_ADV_MOTION_CTL` levava o MAPA (p1) de 0
a +|v|·n, e o MC renderiza pelo mapa ([../../protocolos/avb/estruturas.md](../../protocolos/avb/estruturas.md) §Rampa);
o AAF que ele exporta, por outro lado, recalcula pela CURVA — daí a imagem e o AAF discordarem. O reverso vai agora
pelo gráfico de POSIÇÃO, um keyframe por quadro (`translate._reverso_por_posicao`), com o clipe de dentro no quadro
mais BAIXO: 48/48 quadros 300 → 253, os outros 240 da sequência iguais, e o AAF online diz o mesmo (in 253, mapa 47 → 0).
Convenção do segmento neutro: `source_start_frames` do reverso = o 1º quadro MOSTRADO (Premiere); o do AAF do Avid =
o clipe de dentro (o mais baixo), com o mapa.

✅ **Geometria conferida contra o vid ref** (`laboratorio-de-midia/lab/geometria.py`): o original com a transformação
LIDA DO AAF aplicada pelo ffmpeg (scale → rotate → overlay no raster da timeline) × o quadro do ref, medido só nos
pixels que mudam entre o quadro certo e os vizinhos. Unidades do MC 25.12 (`PaintResize_v2`, `SBlend_v2`), medidas por
ajuste fino que não moveu a hipótese: **posição em milésimos da largura (x) e da altura (y), +Y para CIMA; `rot_z`
positivo = horário na tela** (o −10 gira anti-horário); escala 1 = 100 %. Resultado: certo 2,6–9,2 × vizinho 12,6–169
(nos pixels que mudam); imagem inteira 1,6–2,4. Sabotados (in +1, −2) e transformação errada (giro com o sinal trocado,
sem giro, Y trocado: imagem 27–35) ACUSADOS. BL04 R2: **8/8 exatos** (6 pela barra, 2 pela geometria).

## Drop-frame 29,97 antes do Baselight (medido 2026-11-21, MC 25.12 Mac, `confirmado`)

Projeto **LAB BASELIGHT 2997DF** (1080p/29.97); originais D1 (A002C001, 14:59:50;00), D2 (B002C001, 15:09:55;00) e D3
(C002C001, 15:00:50;00 — o quadro 300 é **15:01:00;02**, logo depois do pulo; D1/D2 atravessam 15:00 e 15:10, décimos
minutos, que NÃO pulam). Dailies feitos fora (o `convertido` agora preserva o `;`), timeline do produto em DF (`flags 1`,
01:00:00;00 = 107892).
- ⛔ **Defeito do Conformar achado e corrigido:** o online parou com 0/2 casados — o `tc_quadros` do master é contagem
  CONTÍNUA e o TC do arquivo (sondagem do ffprobe, `14:59:50;00`) era lido como NDF: 54 s de diferença às 15h, "timecode
  diferente" no arquivo certo (`media/matcher_masters._tc_em_quadros`). Depois: 4 sequências religadas, 0 falhas.
- Conferência × vid ref (preset DNxHR LB em 29,97): **13/13 eventos exatos** (BL02 e BL05, corte seco e duas trilhas),
  inclusive o plano que atravessa o pulo.
- FLE com `# fps 30DF` e os rótulos DF com `:` (a spec não diz o separador — `hipotese` até o Baselight ler): o plano do
  pulo sai `15:00:59:10 15:01:00:29` = 48 quadros, conferidos contra o rótulo GRAVADO no quadro do original (em NDF seriam
  50). É o caso a ver no Baselight.

## A FLAPI

- Cliente/servidor: o servidor é o **Baselight aberto** ou o **flapid** (serviço sem interface; `fl-service start flapi`).
  Local sem token; outra máquina da rede com usuário + **token**. Os mesmos métodos no Baselight, Daylight e NARA.
  ⛔ **Não há FLAPI** no Baselight for Avid (Editions) nem no BLG para Flame.
- Python 3: a roda `share/flapi/python/filmlightapi-<versão>-py3-none-any.whl` (reinstalar a cada versão do Baselight —
  a roda velha não conhece os métodos novos). O Baselight cria uma venv ao abrir a 1ª vez.
- Padrão: `conn = flapi.Connection("localhost"); conn.connect()`; estáticos pela conexão (`conn.JobManager`,
  `conn.Scene.new_scene`, `conn.SequenceDescriptor…`), de instância no objeto. **Todo objeto pego tem de ser
  `release()`** (vaza memória num serviço de longa duração). Escrita entre `scene.start_delta("…")` e `end_delta()` (uma
  transação = um desfazer); depois `save_scene()`, `close_scene()`. Leitura: abrir com a bandeira de só leitura.
- Job/scene: `JobManager.job_exists/create_job/scene_exists/delete_scene(host, job, scene, ignoreLocks)`;
  `Scene.new_scene(flapi.ScenePath({"Host","Job","Scene"}), {"format": "HD 1920x1080", "colourspace": …, "frame_rate":
  24.0, "field_order": flapi.FIELDORDER_PROGRESSIVE})`; `open_scene(caminho, flags)` (flags de só leitura, descartar ou
  recuperar alterações não salvas).
- **Não há** método de conform nem de leitura de AAF/EDL/XML (o `MultiPaste` lê EDL/ALE só para copiar metadados/CDL). Para
  conformar: `bl-conform` por subprocesso, ou montar plano a plano com `insert_sequence`.
- App Scripts: menus e diálogos dentro do Baselight (`MenuItem`, `DynamicDialog`, BETA).
- `QueueManager`/`RenderSetup`: render local ou na fila de outra máquina.

## Instalação no Mac (medido 2026-11-21, Baselight 7.0.3.26500, macOS 15 Sequoia, Mac mini M4)

`confirmado`:
- O `.pkg` é assinado (Developer ID Installer: FilmLight Ltd, 7Y42QSARBT) e notarizado. Instala
  `/Applications/Baselight/<versão>/` (cada versão numa pasta, mais `Current`) e dois receipts:
  `uk.ltd.filmlight.BaselightCore` e `uk.ltd.filmlight.PostgreSQL-9.3.4`.
- ⚠️ **No fim, o instalador avisa** *"vol service has not been set up"*. É preciso REINICIAR e depois rodar
  `sudo <app>/Contents/bin/fl-service setup vol` num Terminal de verdade: o `!` do Claude Code não tem tty para o sudo.
  O serviço cria o autofs `/vol` (`/etc/auto.vol` em `/private/vol`, mais `/vol` → `System/Volumes/Data/vol`) e
  exporta por NFS para localhost `/System/Volumes/Data/Library/Application Support/FilmLight` (no `/etc/exports`). O
  Darwin não tem loopback mount, então o volume local passa por NFS.
- **Os daemons sobem com o sistema, sem o Baselight aberto e sem licença:** `cache-daemon` (porta 49160), `flapid`
  (a FLAPI), `flit-daemon`, `flmhl-daemon`, `fl-cleaner`, `vold`, `postgresql`. Todos rodam sob `fl-supervise`, e os
  logs ficam em `/Library/Application Support/FilmLight/log/`.
- `etc/licence.flic` nasce com 0 byte. O `bl-prefs` (Preferences Editor) ABRE SEM pedir ativação: dá para configurar
  antes de começar o trial. Na 1ª abertura ele pede ao macOS acesso à rede local.
- O cache em disco vem VAZIO, e sem ele o Baselight roda sem cache em disco. Ele se ajusta em `bl-prefs` › System › Cache
  › *Baselight on-disk cache location* e é gravado por usuário em
  `~/Library/Preferences/FilmLight/Baselight/bluserprefs` (`cache_directory` e `cache_directory__Mac`). O padrão é
  20 GB de cache em disco, miniaturas em `/Library/Caches/FilmLight/Thumbnails` (1 GB) e 50 % da RAM em memória.
  Aqui o cache ficou em `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_BASELIGHT/cache`.

## Medido no trial (2026-11-21, Baselight 7.0.3.26500, Mac; laboratório BL02/BL04 R2/BL05)

`confirmado` (diário e fotos: `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_BASELIGHT/estudo/`):
- **FLAPI:** a roda já vem instalada na venv da FilmLight (`/Library/Application Support/FilmLight/python/3.12-v7-venv`).
  ⚠️ O serviço `flapi` lê a licença só ao subir; se subiu antes da ativação, o JobManager responde "without a valid
  licence" até `sudo fl-service restart flapi` (o nome do serviço é o da pasta `drv/`, e não `flapid`). Dá para criar o
  job, ler scenes (`get_src_start_frame` = quadro do arquivo) e RENDERIZAR (RenderSetup + QueueManager local; ProRes
  HQ HD a 88 fps).
- **`bl-conform` com AAF do MC:** sem `--multiples` ele para se houver variantes; `--outset` gera o `.set` com as
  `CHOOSEn` e `--inset` o reusa. O `RemovePrefix` sai sozinho do Locator. Por filtro: Avid UID 0 %, Filename/ClipName
  100 %, None 25–33 %. **O AAF que aponta para os DAILIES conforma nos ORIGINAIS** quando o nome do arquivo é igual:
  6/6 planos certos, como no AAF religado. Também ficam certos: V1+V2, 29,97 DF (escolhe `TC_30DF` sozinho), câmera
  lenta, acelerado e congelado.
- ❌ **Reverso do MC:** toca para trás, mas a partir do início do clipe interno (≈ +47 quadros: 346→300 onde o MC mostra
  300→253).
- ❌ **Resize (`PaintResize_v2`) e 3D Warp (`SBlend_v2`) do MC: não aplicados**, mesmo com `--ApplyTransforms Yes`.
- **FLE:** a interface (Scene › Conform) aceita o nosso FLE (6/6, por Filename, TC no Header). O `bl-conform` recusa o
  mesmo arquivo ("No valid conform identified"), inclusive com `--container`. Automação de FLE: a descobrir.
- Ao conformar com a pasta de busca fora do container da scene (`/images1`), a interface pergunta "Change Container?".
  O `bl-conform` só avisa ("not within container") e segue.
- **Geometria do MC:** o conform cria a camada "Layer:1 Transform" (GR_TransformRop) com valores NEUTROS, ou seja, ele
  sabe que há transformação mas não lê os parâmetros de `PaintResize_v2`/`SBlend_v2`. O BLG de cada plano sai pela
  FLAPI (`get_blg_payload`, base64 + zlib).
- **Dissolve do MC:** mesmo lugar e duração; a curva difere (o Baselight mistura no espaço de trabalho; hipótese).
- **XML do Premiere (FCP XML) pelo `bl-conform`:** Filename/ClipName 100 %, 6/6 e 2/2, tanto o XML dos proxies quanto
  o religado.

## Corrigir velocidade, reverso e geometria (medido 2026-11-21, 7.0.3, laboratório BL04 R2)

`confirmado`:
- **FLE com opticals** (`{fps N}`, reverso com início > fim, `{fps 0}`, `{dissolve}`), conformado pela interface:
  reverso, câmera lenta, acelerado e congelado batem com o vid ref quadro a quadro. O FLE não tem transformação.
- **Camada Transform no BLG:** o 2º `BEZ_Transform2dInterp` do `GR_TransformRop` aponta para 7 `GM_Bezier1dInterp`:
  escala X, escala Y, rotação (rad, positivo = anti-horário), posição X e Y (fração da LARGURA, origem em cima à
  esquerda), pivô X e pivô Y. Cada valor aparece como `f <double hex> <n>:6 0 0 0 0 -1 0.001 <%.20g> ` (n conta o espaço
  final). O payload é base64(uint64 LE do tamanho + zlib(texto)).
- Na interface, os campos usam pixels (centro 960/540) e graus.
- **Conversão MC → Baselight** (unidades do `lab/geometria.do_avid`): X = 960 + dx, Y = 540 + dy, a mesma escala,
  rotação = −rot.
- Gerado por programa (`estudo/ferramentas/blg_transform.py`, byte a byte igual ao da interface) e aplicado pela FLAPI
  (`Shot.delete_all_layers` + `apply_blg_payload`), o BLG fica igual ao vid ref no Resize e no 3D Warp do MC.
- Ver também: o manual completo vem no app (`Contents/doc/FL-BL-UG-1027-v7_UserGuide.pdf`). Retime = Insert › Temporal
  › Retime, com os gráficos Velocity×Time e Time×Time (o Time×Time é o mesmo conceito do gráfico de posição do MC).
- **Retime no BLG:** com velocidade constante, o `GR_RetimeRop 9:gr_retime 2 1 0 2 f <vel double hex> f <frame offset
  hex> … SnapToFrame` guarda a velocidade como fração (−1,0 = reverso). ⚠️ Com o Frame Offset 0, o 1º quadro é o do
  ponto de entrada; é por isso que o reverso do AAF do MC saiu deslocado. Na rampa, o RetimeRop aponta para um
  `GM_Bezier1dInterp` animado (`t … 6 0 <n keys> …`): tempo em SEGUNDOS, valor em fração, tangentes Bézier (a decifrar).
  `hipotese`: as rampas do Premiere e do MC cabem aí. A medir: o gráfico Time×Time; gerar por programa e conferir no
  render.
- ⭐ **Retime Time×Time por programa (`confirmado`, Baselight 7.0.3 Mac, 2026-11-21; render × vid ref pelo código de
  barras):** o RetimeRop tem 2 parâmetros, cada um `f <double hex>` (constante) ou `o <índice na lista de refs>`
  (curva): `gr_retime 2 <nrefs> <refs…> 2 <velocidade> <tempo>`. O AAF do MC entra com velocidade `f 1.0` e o
  parâmetro de TEMPO apontando para um `GM_Bezier1dInterp` com **um keyframe por quadro**: `t 0…0 <n>:6 0 <k>
  [tempo valor 0 0 0 0]×k 0 17 -1 0.001 0 ` (tangentes zeradas = linear; `<n>` conta o corpo com UM dos dois espaços
  do fim). **Leitura: quadro de fonte = in do plano + piso(valor × fps da scene)**, tempo e valor em segundos.
  - Por que o reverso do AAF saiu errado (346→300 em vez de 300→253): o importador gravou o gráfico de posição do MC
    em quadros/24 (não /23,976 — o piso come 1 quadro) e ancorado no FIM do trecho (o MC lê a partir de in − 47).
  - **Correção:** trocar só essa curva (valor = (q + 0,5)/fps, o meio do quadro, para o piso nunca cair no vizinho;
    q negativo funciona — vai para antes do in) e aplicar com `delete_all_layers` + `apply_blg_payload` (o payload
    do plano inteiro, retime incluído). Reverso **48/48 exatos**; rampa sintética q = k²/47 (0 %→200 %) **48/48**.
    Ferramentas: `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_BASELIGHT/estudo/ferramentas/blg_retime.py` + `aplicar_retime.py`.
  - ⚠️ Velocidade CONSTANTE que vem só do intervalo de fonte (200 %: 96 quadros de fonte em 48) não cria RetimeRop:
    o plano não tem retime no BLG. ✅ Plano sem RetimeRop: aplicar o BLG de OUTRO plano que tenha (mesma mídia), com a
    curva trocada — o retime vem junto no `apply_blg_payload` (medido na rampa B do Premiere, abaixo).
- ⭐ **O DISSOLVE mistura no espaço de TRABALHO da scene (`confirmado`, Baselight 7.0.3 Mac, AAF do MC 25.12,
  2026-11-21):** lugar e duração certos; a curva difere porque o padrão (`ecs_DissolveCombineType 0`, "Dissolve Combines
  In" = Native) mistura em T-Log/E-Gamut 2, e o MC mistura em vídeo (linear em código: α = 1 − k/12). Prova: o α do
  Baselight muda com o brilho e o do MC não; com o espaço de trabalho `Video_Full` a curva fica igual à do MC (≤ ~0,02).
  Os tipos 1–3 (Linear, Double Negative, Double Camera — `hipotese` pela ordem do manual) ficam mais longe. O dissolve
  não está no BLG do plano e a FLAPI não tem API de transição. ⇒ Não é defeito a corrigir por arquivo: é o espaço de
  trabalho que o colorista escolhe — no máximo um AVISO na entrega.
- ⭐ **A MÁSCARA de opacidade = composição na PILHA (`confirmado` na interface, Baselight 7.0.3 Mac, 2026-11-21):** as
  trilhas NÃO compõem (a de cima só cobre). Monta-se no plano de cima: camada (P) › Layer Mode › Background Replacement ›
  New Background Shot (o fundo como 2ª pilha) + aba Matte › Shape. Formato (lido do `.blscene` do `bl-export`, um SQLite
  com o histórico de gestos e os objetos no texto do BLG): camada `GR_InsideOutsideRop` "Comp:Over"; fundo = pilha
  "Layer:0" com `GR_SequenceRop`; shape `GR_ShapeRop` → `BEZ_FilledShapeInterp` {transform, feather, opacidade, curva
  `BEZ_Bezier2dInterp`: pontos x, y em FRAÇÃO DA LARGURA (origem em cima à esquerda) + tangentes}. A suavidade vai só
  PARA FORA, "Feather 50" ≈ 0,25 da largura, perfil S-Curve High (o Premiere centra a suavidade, em px). ⛔
  `get_blg_payload` recusa plano com 2 sequências ("Allow Multi-Input BLGs"); `Export.do_export_BLG` deu erro interno
  (`gmc_get_viewing_format`). ✅ GERADA POR PROGRAMA: BLG do plano + os objetos da composição (ids novos; faixas com a LINHA contada de baixo: imagem,
  fundo, shape, camada; `GM_Timeline` refeita) → `apply_blg_payload` ACEITA multi-input; render = o feito à mão. A FLAPI não
  abre a scene aberta na interface ("Write lock exists").
  ⭐ **O in do FUNDO** (`confirmado` pelo render, 16 planos, 2026-11-21): quem manda é o 1º número do `GR_SequenceRop` do
  fundo (`… <caminho> d f<x> d f0x1p+0 …`, float em hex), o deslocamento em SEGUNDOS do quadro 0 do arquivo; o
  `GM_ConformData` do fundo (in/out) NÃO muda a imagem. O Baselight trunca: `ent/fps` deu o quadro ent−1 → gravar
  `(ent + 0,5)/fps` (o mesmo meio quadro do Retime). A caixa da shape: o `BEZ_Transform2dInterp` dela = escala x, y (1),
  três zeros, centro (0,5; 0,28125 — fração da largura); o raio da suavidade é o `GM_Bezier1dInterp` 0,25 ao lado.
  Valor sem chave = `0 f <hex big-endian> <n>:6 0 0 0 0 -1 0.001 <valor> ` (n conta até o 1º espaço do fim). ⚠️ Plano
  com multi-input não se relê pela FLAPI: guardar o BLG simples ANTES de compor (ferramenta `aplicar_composicao.py`).
  ⭐ **A suavidade em números** (`confirmado` por render, 14 raios + a B14 inteira, 2026-11-21): largura 10–90 % =
  0,475·r·W e meio da borda a 0,558·r·W para FORA da shape (r = raio em fração da LARGURA; linear de 0,005 a 0,4; não
  depende do tamanho da shape). Premiere 23.2: 10–90 % = 0,9155·F px, centrada. Tradução Premiere → Baselight (a frente
  DENTRO no Premiere = a caixa do FUNDO do outro lado no Baselight): r = 0,835·0,9155·F/(0,475·W), lado da caixa =
  x·W + E − 0,03·F + 0,558·r·W ⇒ erro máximo de alfa 0,023–0,030 de F10 a F500 (casando só a 10–90 % ficava 0,08: as
  curvas diferem — Premiere ≈ gaussiana σ 0,39·F; o ClassicSCurve tem o rabo mais longo do lado da shape). Perfil
  `ClassicSCurve` = o padrão (`etc/preferences` `shape_feather_profile`, escondido); os outros: `pendente`.
  ⭐ **Shape animada** (`confirmado` por render, B14 ANIM/DESIGUAL/ESPARSO, 2026-11-21): cada coordenada de ponto é um
  `GM_Bezier1dInterp`; com chaves = `0 t 0…0 <n>:6 0 <N> (<tempo s desde o início do plano> <valor> 0 0 0 0)×N 0 17 -1
  0.001 0` (o formato da curva do Retime; tangentes zeradas = linear). Um keyframe por quadro com a borda que o Premiere
  MOSTRA (linear entre as chaves dele, parado depois da última) ⇒ ≤ 1,0 px em todo quadro.
  ⛔ Animar só pontos que não são o 1º deixa a curva PARADA: ponha chaves em TODOS os pontos (os parados repetindo).
  ⭐ **Inverter (a frente DENTRO da shape)** (`confirmado` por render, 2026-11-21): a 1ª das três bandeiras do
  `GR_ShapeRop` (`… Z 3 t f t 13:ClassicSCurve`). ⛔ A 1ª bandeira do `BEZ_FilledShapeInterp` (`0 t 1 0 …`) derruba o
  `flapid` no `submit_to_queue`. A suavidade continua para FORA da shape (para o lado do fundo, invertida).
  ⭐ **A mistura é no espaço de TRABALHO da scene** (como o dissolve): em T-Log o meio da borda fica a 0,548·r·W da shape
  (normal) e 0,458·r·W (invertida); em `Video_Full` (`bl-conform --space Video_Full`) 0,50·r·W nas duas (simétrica) e
  a curva casa melhor com o Premiere. Tradução por modo (minimax × Premiere 23.2 F50/F201/F500, alfa normalizado; raio =
  a·F/W, borda da shape b·F px para FORA da borda do Premiere): T-Log fora 1,62/0,869 (erro 0,030), T-Log dentro
  1,618/0,75 (0,033), vídeo fora 1,74/0,867 e dentro 1,736/0,87 (0,019). O espaço de trabalho é do colorista: ler o
  da scene antes de traduzir.
- ⭐ **A shape por dentro** (`confirmado` na interface + `.blscene`, 7.0.3 Mac, 2026-11-21): ponto do
  `BEZ_Bezier2dInterp` = x, y (fração da LARGURA, y para baixo), ângulo e comprimento da alça de ENTRADA, ângulo e
  comprimento da de SAÍDA (rad; fração da largura; a de saída aponta para o ponto seguinte; canto vivo = comprimento 0).
  Feather Radius da interface = raio × 200. Perfis: S-Curve High `ClassicSCurve`, S-Curve Low `SubtleSCurve`, Linear e
  Smoothed Top End (`pendente` o nome). Não há suavidade centrada: "Custom Inner/Outer Curves" = Inner/Outer Scale (escala
  em torno do centro) ou uma curva EXTERNA própria (a suavidade vai da de dentro à de fora) — no arquivo, a 1ª bandeira do
  `BEZ_FilledShapeInterp` + um filho (a curva externa); a bandeira sem o filho derruba o `flapid`.
- ⭐ **Máscara do Premiere com Motion/nest/proxy → Baselight** (`confirmado` por render, lab B16, 2026-11-21): a shape
  vive no QUADRO — leve o contorno da fonte ao quadro pelo Motion (X = 0,5 + (x − 0,5)·escala + posição; suavidade ×
  escala × largura do quadro / largura da fonte): borda ≤ 1,4 px. ⛔ O `bl-conform` ignora a escala do Basic Motion de um
  xmeml gerado: o Motion vai por BLG (camada Transform ENTRE a imagem e a composição, só a frente se transforma) → o
  quadro inteiro difere do Premiere 0,06–0,44 níveis em média.
  ⭐ **Com velocidade** (B16 inteira): o Retime Time×Time (dentro da pilha da imagem) + a composição no mesmo BLG → 15/21
  ≤ 1,4 px (os 6 restantes = o pendente do leitor, igual no Resolve). ⛔ xmeml com out − in ≠ duração vira velocidade DO
  PLANO e o Retime soma; o in do xmeml é na taxa da timeline (100 qps: 4 → 17); com fonte de outra taxa o valor da curva
  ~~sai × fps_fonte²/fps_tl (compensar)~~ ⛔ ERRADO (corrigido na 18ª rodada, ver abaixo).
- ⭐⭐ **Retime com fonte de OUTRA taxa** (`confirmado` pelo número gravado na imagem, B16, 2026-11-21): o Baselight toca a
  fonte de outra taxa em tempo real (100 qps = 4,17 quadros por quadro) e o Retime (SnapToFrame) só pousa nessa grade
  (degraus de ~17). ⇒ **declarar no xmeml o arquivo na taxa da timeline** (`<file><rate>` = a da sequência; o `<in>` em
  quadros da FONTE): 1 quadro de fonte por quadro e a curva Time×Time manda no quadro exato (in + q). O `<in>` do xmeml é na
  taxa do clipitem: dado em quadros da fonte com a taxa verdadeira, cai fora do arquivo e o `--multiples` escolhe uma
  variante por tempo de GRAVAÇÃO (91 %, arquivos trocados). Imagem parada com número no fim do nome ("…530x298.psd.jpg")
  vira sequência ("procura o 297") — `pendente`.
- ⭐ **PRODUCAO-C (R04, real) prproj → Baselight sem máscaras/títulos: 110 de 133 pontos** contra a referência (retime +
  Motion animado + flip por BLG); o que falta é máscara, título e a imagem parada.
- ⭐ **O fundo da composição vindo de OUTRO plano** (`confirmado` por render, lab B14, 2026-11-21): Transform numa faixa logo
  ABAIXO da faixa do fundo = só o fundo; tempo pelo `GR_SequenceRop` do fundo (`d f<deslocamento s> d f<passo>`: in 10 passo
  2,5 → 10,12,15… exato). ⛔ `GR_RetimeRop` na lista da pilha "Layer:0": ignorado no fim, PRETO antes da sequência.
- ⛔ **FLAPI que trava** (7.0.3 Mac): ler o mesmo plano duas vezes, ou o `release` de um plano de 3 trilhas, deixa a chamada
  parada; um delta por plano matou o cliente no apply. Cliente morto com a scene aberta = "Scene Is Already Write Locked" até
  `fl-service restart flapi` (root; pelo pedido de senha do macOS: `osascript -e 'do shell script "…" with administrator
  privileges'`). Ler numa sessão só-leitura e escrever numa curta, num delta só.
- ⭐ **Plano com várias trilhas** (`confirmado`, lab BL11, 2026-11-21): cada clipe do xmeml vira um plano com o seu tempo.
  ⛔ `Shot.get_blg_payload` devolve a pilha de quem está POR CIMA no 1º quadro do plano (não a do plano); ✅
  `apply_blg_payload` escreve no plano certo. Identifique o plano pelo metadado `clip` (`get_metadata_strings({"clip"})` = o
  nome do clipitem) e monte o BLG a partir de moldes, nunca do lido.
- ⛔⛔ **O prefixo de comprimento do BLG conta BYTES** (`confirmado`, 7.0.3 Mac, 2026-11-22, 23ª rodada): campo com
  comprimento errado não dá erro — o `apply_blg_payload` aceita e o `end_delta` PARA para sempre (0 % de CPU; a scene fica
  "Write Locked"). Caso medido: o rótulo `s11:(1024×540)` do `GR_SequenceRop` (o `×` = 2 bytes em UTF-8) lido do `.blscene`
  (SQLite devolve TEXTO) e gravado no BLG em latin1 (10 bytes declarando 11). ⇒ todo texto que entra num BLG vai na visão de
  BYTES do UTF-8 (`s.encode("utf-8").decode("latin1")` antes do `encode("latin1")`), inclusive nomes e caminhos com acento ou
  NFD. ⛔ Corrige a conclusão de 21/11 ("muitas composições num processo param a FLAPI"): era este byte — um plano sozinho
  parava igual, e sem o `×` as 10 composições do PRODC gravam em 0,2 s cada. Os travamentos da 21ª rodada (ler o mesmo plano
  2×, `release` do plano de 3 trilhas) usavam o mesmo fundo: provavelmente a mesma causa (`hipotese`).
  Com a correção, o PRODC com as máscaras: **115 de 133** (21 s 0,98; 03 s 0,77 — a 2ª máscara por cima ainda aproximada).
- ⭐ **Máscara sobre máscara e fundo que troca no meio do plano** (`confirmado` por render × a sequência do Premiere, 7.0.3
  Mac, 2026-11-22, PRODC): (1) as faixas entre o FUNDO e a camada de composição agem só no ramo do fundo ⇒ a composição do
  fundo mascarado entra ALI (aninhada; até 3 níveis medidos no PRODC). (2) ⛔ **O BLG não guarda tempo por faixa**: faixas de
  um trecho do plano são descartadas no `apply_blg_payload` (a 1ª esticada ao plano todo; lido no `bl-export`). O formato
  da faixa na scene é `1 o 0 <INÍCIO s> <FIM s> <linha> f f 0` (fim, não duração). ⇒ trecho = pela SHAPE animada: uma
  composição por trecho, todas no plano inteiro; fora do trecho a shape é uma caixa muito maior que o quadro (com a shape
  invertida, a frente cobre tudo e a composição deixa passar). Nada embaixo = fundo preto (Transform de escala ~0).
- ✅ **Imagem parada pelo xmeml** (`confirmado`, 7.0.3 Mac, 2026-11-22): `<in>0</in>` e o `bl-conform` casa um .jpg com número
  no fim do nome ("…530x298.psd.jpg") e segura a imagem pelo plano inteiro; com um in qualquer (p. ex. herdado de quadros
  de fonte) ele procura o quadro N de uma "sequência" e não acha. Escala: o Baselight encaixa a imagem no quadro.
- ⭐ **Scene editada por fora** (`confirmado`, 7.0.3 Mac, 2026-11-22): `bl-export` → editar o SQLite (nome na tabela
  `Directory`; estado novo numa linha NOVA da `State` — ela é compartilhada —, `DataHash` 0 aceito) → `bl-import host:job
  arquivo.blscene` cria a scene. Ali as faixas têm tempo ABSOLUTO (o que o BLG não guarda).
- ⭐ **Texto/títulos** (`confirmado` por render × a sequência do Premiere, 7.0.3 Mac, 2026-11-22, PRODC): o Text como FONTE
  (`Scene.insert_text`, Insert › Sources › Text) sai sobre PRETO; DENTRO de uma camada de grade (P → Change Operator Type
  → Text) é COMPOSITE (filho `GM_InterpDiscrete` `i1` em vez de `i2`) e desenha sobre a imagem. Faixa na scene: tempo
  absoluto, linha MENOR = mais em cima (blocos por trilha: V1 3072, V2 2048, V3 1024, V4 0); buraco sob camada = xadrez
  (pôr Blank preto). Posição = deslocamento do centro (534 X / 535 Y no modelo), fração da largura, y para baixo; fonte =
  nome do ARQUIVO .ttf (o Baselight traz só Liberation/Ubuntu/Noto; as do macOS pelo nome do arquivo em
  `/System/Library/Fonts/Supplemental`) ou o CAMINHO COMPLETO do arquivo (`confirmado`: a fonte do Creative Cloud, oculta e
  numerada em `~/Library/Application Support/Adobe/CoreSync/plugins/livetype/.r/`, achada pelo nome PostScript da tabela
  `name`; não copiar o arquivo). ⛔ O Text não tem TRACKING (espaço entre letras): título do Premiere com tracking sai mais
  estreito. ⛔ `Application.open_scene_in_ui`/`get_current_cursor`: erro interno no 7.0.3 Mac.
- ⛔ **.blscene editado por fora**: objeto NOVO exige um DELTA novo (no antigo = "Database corrupt"; `CheckHash` NULL
  aceito; o `Reference` Main aponta para ele); `Revision` é a versão do FORMATO do objeto (não incrementar); strings com
  prefixo em bytes UTF-8 e o texto real.
- ⭐ **AAF do Media Composer → Baselight (PRODUCAO-A, `confirmado` por render × vid ref, 7.0.3 Mac, 2026-11-22):** AAF sem
  caminho de mídia casa 100 % nos BRAW pelo nome do clipe/fita (passar só as pastas dos ORIGINAIS no `--src`, nunca a dos
  convertidos). ⛔ O FrameFlex padrão do MC PREENCHE o quadro; o Baselight ENCAIXA (letterbox) — fonte DCI 4096×2160 sai com
  faixas: Transform de escala preencher/encaixar (1,0667). O conform reproduz buracos e títulos como `GR_BlankRop` (e os
  dissolves numa linha abaixo); estabilização do MC não é aplicada; Motion Control (velocidade) é.
- ⛔⛔ **Duas faixas na MESMA linha e no mesmo tempo derrubam o `flapid` ao abrir a scene** (o supervisor religa em ~15 s).
  Linhas por trilha: blocos de 1024, a trilha mais ALTA no bloco 0 (3 trilhas: V1 2048, V2 1024, V3 0; 4 trilhas: V1 3072).
- `RenderSetup.set_frames([FrameRange])` renderiza só um trecho; BRAW entra como `BMD_Linear_WG` (render com
  `RenderColourSpace = "Video_Full"`); render do filme (26 min, BRAW 4K → ProRes HD): 15 min 40 s, 40 qps.
- ⚠️ **Render pela FLAPI precisa da INTERFACE aberta** (`confirmado`, 7.0.3 Mac, 2026-11-22): sem ela, a operação do
  `QueueManager.create_local()` faz o pré-render e fica "Queued" para sempre; abrir o Baselight a processa (30 s).
- ⭐ **Qual job/scene o colorista tem aberto** (`confirmado`, 7.0.3 Mac, 2026-11-22): `bl-lsscenes -k -q host:job` mostra
  o LOCK no fim da linha (`host:job:scene Read|Write`); a scene aberta na interface, mesmo "Open Read Only", aparece com
  lock e o perde ao fechar (⌘W). Varra os jobs pulando `baselight_gallery` (as scenes de galeria ficam com lock de escrita
  o tempo todo). ⛔ A FLAPI de FORA não diz: `Application.get()` é a do serviço (`flapid`) e `get_current_scene_name` /
  `get_open_scene_names` respondem vazio com uma scene aberta na interface; e o lock da galeria com o nome do job fica
  preso ao ÚLTIMO job aberto, mesmo trocando no Job Manager. Implementado: `_CICLO ASSIST/modulos/conformar/motor/
  baselight/enviar.py` (`job_aberto`). Windows: não há Baselight para Windows.
- ⭐ **Markers e stills pela FLAPI** (`confirmado`, 7.0.3 Mac, 2026-11-21): `Scene.add_mark(quadro, categoria, nota)`
  (categorias `DefaultMark` e `GMMA_RED`/`GMMA_*` cores; `get_mark_ids`/`get_mark`/`delete_mark`; marcar as nossas pela
  nota para não apagar as do colorista). Stills: `Export.do_export_still(qm, scene, StillExportSettings)` com
  `Source=AllShots`, `Frames=Marked`, `MarkCategory={…}`, `Filename="%{Clip}_%{TimelineFrame}"`, `ColourSpace`,
  `Format` → JPEG (sem `FileType`; `"tif"` é recusado). Sai também de plano multi-input. As cores do still saem certas;
  as do render ProRes do `RenderSetup` (deliverable no espaço de entrada) saíram com os patamares esticados (~legal→full):
  para conferir contra o ref, use o still. ⭐ **Corrigido (14ª rodada):** a causa era `RenderVideoLUT "none"` (faixa cheia
  num ProRes marcado legal); com `"scale"` (Full to Legal) o render = a origem, valor por valor. Render DPX com
  `RenderColourSpace` = o do still, × still DPX: 99,9 % idênticos, máx 1 nível ⇒ export e still IGUAIS. Still aceita
  `FileType "DPX"` (maiúsculas). Deliverable sem `RenderColourSpace` sai no espaço de TRABALHO (log). ⛔ Um DPX com Name +
  FileNameExtension + VideoLUT trocados juntos derrubou o `flapid` (não isolado).
- ⭐ **Rampa do Premiere → Baselight (`confirmado`, Premiere 27.0.0 + Baselight 7.0.3 Mac, 2026-11-21; lab BL06 = a
  B22):** o XML (xmeml) do Premiere leva o Time Remapping como `timeremap` com `graphdict` de poucos pontos INTEIROS (só
  os cantos; a transição suave some). Pelo `bl-conform --Retime Yes`: a rampa A (começa no in) vira Time×Time e erra 1
  quadro em 11 de 48; a rampa B (in DENTRO da curva) **não vira retime nenhum** — toca a 100 %, erro de até 34 quadros.
  ⇒ O XML não serve para rampa. **Pelo BLG gerado** (posições do Premiere por quadro = piso do `_remap_fonte` do
  Conformar → um keyframe por quadro): **A 48/48 e B 48/48** iguais ao render do Premiere.
- ⚠️ **Piloto:** os campos numéricos do Baselight não aceitam o texto Unicode do `digitar`. É preciso clicar, End,
  Backspace e mandar as teclas por código.

## Licença

Ativação online (serial + Machine ID → `licence.flic`) ou por arquivo; licença flutuante no Baselight M. Trial de 14
dias, que começa na ativação. ⛔ Não se investiga reset de trial; para mais tempo, pedir à FilmLight.

## A medir (o roteiro do trial)

- [ ] `bl-conform --help`, `bl-mkjob -i`, `bl-mkscene -i` (o uso real).
- [ ] Onde o Postgres guarda os jobs no Mac; o que o `bl-export` gera.
- [ ] A FLAPI conectando pela roda; criar job/scene; ler os planos de uma scene conformada.
- [ ] Conform de AAF do MC: original × religado pelo Conformar; Avid UID × Locator × nome × TC; multicam, subclipe,
      aninhada, velocidade, dissolve, reposição (Layer 99), drop-frame, anamórfico.
- [ ] Conform de XML do Premiere × FLE gerado por nós.
- [ ] O FLE `# fps 30DF` com `:` (BL05 DF): o plano 15:00:59:10–15:01:00:29 entra com 48 quadros?
- [ ] O reverso (BL04 R2) e a geometria (`PaintResize_v2` 150 % +100/+50, `SBlend_v2` −10°) no Baselight: a mesma
      imagem do vid ref? (a conferência do laboratório já sabe medir).

## Quem casa a mídia: o laboratório de pegadinhas BL08 (`confirmado` por render, 7.0.3 Mac, Premiere 27.0, 2026-11-22)

18 planos de um xmeml do Premiere (dailies) → `bl-conform` nos originais; o render lido quadro a quadro (código de barras
+ cor da câmera) diz qual arquivo e qual quadro entrou. Laboratório: `laboratorio-de-midia` `lab/casamento.py` +
`lab/bancadas/baselight_casamento.py`; plano no Ciclo Assist `docs/plano/2026-11-22-lab-casamento-baselight.md`.
- ⛔⛔ **O `bl-conform` converte o `<in>` do xmeml pelas taxas NOMINAIS** (`confirmado`, 2026-11-23, PRODUCAO-C pela
  janela do app, Baselight 7.0.3): quadro do arquivo = `in × timebase_arquivo / timebase_sequência`, ignorando o `<ntsc>`.
  Sequência 23,976 com arquivo 25 ou 100 qps: o ponto sai 0,1 % antes (PRJ-0006-217: 6741 em vez de 6747; LOU_7310 a
  100 qps: 10692 × 10702) — 56 de 74 planos fora do ponto, explicados os 72 de vídeo pela conta nominal. Quando os dois
  são NTSC (29,97 numa 23,976: o BL08) ou nenhum, o fator se cancela — por isso não apareceu antes. Conserto (Ciclo
  Assist `entrega._compensar_taxa_nominal`): in e out andam o MESMO Δ = round(in·(k − 1)), k = (fps/tb do arquivo) /
  (fps/tb da sequência) — a duração fica (out − in ≠ duração vira velocidade). Pela janela de novo: 74 de 74.
  (O estudo resolvia de outro jeito: o arquivo declarado na taxa da timeline + o Retime Time×Time.)
- ⭐ **Imagem parada com número no fim do nome** ("…530x298.psd.jpg"): o `bl-shots` dá in/out pelo número (298–420), a
  imagem fica a mesma no plano todo — a conferência olha só o arquivo.
- ⭐⭐ **Os efeitos do Premiere pelo PRODUTO** (`confirmado` pelo render, PRODUCAO-C pelo caminho do painel, Ciclo Assist
  `motor/baselight/efeitos.py` + `mascaras.py`, 7.0.3 Mac, 2026-11-23): 68 → 128 de 133 pontos com velocidade + Motion,
  130 com as máscaras (falta só o título, 08–09 s). As regras do estudo valem no produto sem mudança: BLG a partir dos
  MOLDES (o Retime Time×Time e o Transform; a composição da caixa como texto), nunca o lido; as 67 curvas e os BLGs das
  10 máscaras saem iguais aos do estudo (menos o nº do evento no `GM_ConformData`, que não muda a imagem). Decisão do
  produto: o arquivo de taxa ≠ a da timeline vai declarado na taxa da timeline quando QUALQUER camada do Ciclo entra num
  plano dele (velocidade, Motion, máscara ou fundo de máscara) — o Retime vai em toda pilha que o Ciclo grava; o
  arquivo sem camada fica na taxa real (o caminho medido no BL08). `pendente`: o trecho 763–771 (C0296, 100 qps,
  máscara) dá mínimo 0,89 contra 0,94 do estudo com BLG, xmeml e fundo iguais — a causa não está no BLG.
  ✅ Títulos (opção do autor): o `bl-import` de uma scene exportada e editada (a camada Text num delta novo) entra com o
  NOME novo no mesmo job e traz os markers; `bl-delete host:job:scene` apaga a provisória. Pelo produto: 132 de 133.
- ⛔ **O Baselight NÃO obedece ao caminho do xmeml:** com o caminho exato do original, `--Filter Filename` ainda escolhe
  pelo NOME entre homônimos (dois `A001C003` de TC zero e durações diferentes: pegou o errado, calado). A duração não
  entra na escolha. Com a ÁRVORE de pastas dos dailies igual à dos originais ele acerta — usa o fim do caminho; numa
  pasta plana, erra. `ClipName` e `None` erram mais (None: `PLACA_297` → `PLACA_298`; DF × NDF com 2 quadros).
- ⛔ **Fonte de outra taxa declarada com a taxa do DAILY:** o proxy 23,976 de um original 59,94 — o xmeml diz `<file><rate>`
  24 e o `<in>` 47; o Baselight acha o original de 59,94 e usa 47 como QUADRO DELE (−1,8 s, calado). Declarando no
  `<file>` a taxa, o TC e a duração do ORIGINAL, o ponto sai exato (o in do clipitem é na taxa da timeline).
- ⛔ **Nome com acento no exFAT do Mac:** o caminho em NFC no xmeml deixa o plano offline; em NFD (como a pasta lista),
  casa. ⇒ o xmeml leva o nome COMO O DISCO LISTA (matriz, "Unicode do nome"; Windows `pendente`).
- ⭐ **`bl-shots -replace`** troca o arquivo de UM plano (linha `in out "antigo" "novo"`, faixa na FONTE) sem reconformar;
  o render sai com o arquivo novo. ⚠️ A FLAPI (`get_sequence_descriptor`) continuou devolvendo o arquivo ANTIGO logo
  depois (o `bl-shots` e o render, o novo) — conferir pelo `bl-shots`/render.
- ⚠️ O render pela FLAPI FALHA inteiro num plano offline ("Missing file /images1/…"): renderizar só as faixas com mídia
  (`rs.set_frames([...])`; o `FrameRange.End` é EXCLUSIVO).
- Placar (certo / alerta / errado calado): A Filename 15/2/1 (árvore igual) · 12/3/3 (pasta plana) · ClipName 13/2/3 ·
  None 12/1/5 · B (o original decidido no xmeml) 12/5/1 · **C (B + conferência + `bl-shots -replace` + markers
  "[Ciclo]") 14/4/0**.
- **O lado do MC (AAF do MC 25.12 Mac, mesmos 18 planos; render):** A Filename 13/2/3 · ClipName 11/2/5 · None 10/2/6 ·
  C 10/5/3. P1/P2 resolvidos no C (troca + markers). ⛔ **P3 errado em TODOS, até no C:** o AAF religado
  (`relink_aaf`: só os Locators) leva a taxa do DAILY; o Baselight usa o in como quadro do original de 59,94 (−107
  quadros). A conferência C confere o ARQUIVO, não o PONTO — tem de conferir o in (`bl-shots -inputrange`) e corrigir
  (`bl-shots -replace` com TRÊS números muda o offset de fonte; `pendente` de medir). ⛔ **P7 FECHADO pelo vid ref do MC
  (`confirmado`, MC 25.12 Mac):** master de 29,97 numa sequência 23,976 — o MC começa no quadro 359 do original (o in
  convertido de tempo: 11,97 s) e toca um quadro de fonte por quadro; o Baselight, com o MESMO AAF, começa no 287 (o
  número cru: −72 quadros, −2,4 s, calado) e os planos seguintes chegam 12 quadros ANTES dos do MC (o comprimento do plano
  de outra taxa difere; o vid ref do MC tem 853 quadros, a scene 864). O P3 no vid ref do MC é exato (178): o −107 é do
  Baselight. ⇒ fonte de OUTRA TAXA no AAF do MC não chega certa ao Baselight; a conferência tem de usar o vid ref do MC.
- ⛔ **MC 25.12 Mac: `LinkFile` com acento falha** em NFC e em NFD ("CORACÃßAÃÉO_01.mov cannot be linked", ErrorType 66:
  UTF-8 lido como MacRoman) — o mesmo defeito do 24.6 Windows; a mensagem do Conformar ("use o Media Composer 2025")
  está ERRADA para o Mac.
- ⚠️ **MC 25.12 Mac preso depois do `ExportFile` do vid ref** (2026-11-22): o arquivo saiu inteiro (18 s), mas a barra
  "Exporting Files… 00:00:03 of 00:00:03" ficou na tela, o MC a ~100 % de CPU por > 7 min e a barra de menus inacessível
  pela acessibilidade (o Quit não chega); desligar o serviço do Ciclo Assist não soltou. O autor fechou à mão. Na 1ª
  exportação da mesma sessão (o AAF) isso não aconteceu. Causa: não medida.
- ⭐ **Conform pela INTERFACE com conflitos (BL08, 2026-11-22):** a janela mostra as variantes com a % de eventos achados
  e, por evento, os candidatos com botão de escolha e % (homônimos aparecem os dois com 100 %, sem dizer por quê). A
  variante que casa por "Tape Name In Header/Metadata" achou o daily RENOMEADO (o reel do daily = o nome do original),
  que o `bl-conform --Filter Filename` deixava offline. Referência visual: `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_BASELIGHT/
  estudo/fotos/referencia-conform/`.
- ⭐⭐ **A entrega e a conferência no PRODUTO (Conformar `motor/baselight/`, 2026-11-22, `confirmado` no BL08):**
  `entrega.reescrever` (o `<file>` de cada daily → o original decidido: caminho como o disco lista, taxa, TC, duração,
  raster; sem decisão = OFFLINE de propósito) → `bl-conform --Filter Filename --multiples` → `bl-shots -inputrange
  -outputrange` → `conferencia.conferir` (arquivo + 1º e ÚLTIMO quadro visível; tolerância = 1 quadro da timeline na taxa
  da fonte) → `linhas_de_troca` no `bl-shots -replace`. Premiere BL08: 13 ok + 1 arquivo diferente (P1) + 4 offline →
  depois da troca **14 ok + 4 offline com motivo**. Sobre a scene do caminho A, a mesma conferência ACUSA o P3 que passava
  calado ("in 47 × 118, out 94 × 237"). O in do xmeml conta desde o INÍCIO do arquivo (a ponte pelo original): TC zerado
  na conversão não entra na conta — P11 (original 20:00, daily zerado) e P12 (original zerado, daily 21:00) `confirmados`
  (in 71 × 71, out 118 × 118, nos caminhos A e do produto). Final do Premiere: **16 ok + 4 offline com motivo**.
- ⭐ **Reel como critério e empate só com confirmação VISUAL (decisões do autor, 2026-11-22; Conformar
  `prproj/originais.py`):** sem arquivo com o nome do daily, o casador casa pelo REEL dele (P4); empate entre originais
  diferentes se resolve só se o quadro do daily × o de cada candidato (25/50/75 %, semelhança em cor 64×36, o pior dos três)
  confirma UM (piso 0,95, margem 0,05; medido P2: 0,999 × 0,897). Sem confirmação = empate, para o editor. BL08 pelo
  produto: **19 ok + 1 offline (P10, sequência DPX)**; o Baselight de novo trocou P1 e P2 sozinho e a conferência corrigiu.
- ⭐ **As mesmas regras no casador do AAF/MC (Conformar `media/matcher.py` + `media/confirmacao.py`, 2026-11-22):** o
  empate se confirma pelo quadro do DAILY que o AAF aponta (antes, só com vídeo de referência); o reel vem do arquivo do
  daily, porque o MC 25.12 não leva o `reel_name` ao AAF (`protocolos/aaf/estruturas.md`). Papel do MC no BL08: **14 certos,
  1 alerta (P10), 0 errados**, com o P2 confirmado pela imagem e o P4 pelo reel.
- ⭐⭐ **O lado do MC pela MESMA entrega (Conformar `baselight/do_aaf.py`, 2026-11-22, `confirmado` por render):** em vez do
  AAF religado, um xmeml gerado da LEITURA do AAF (o `source_start_frames` do MC já conta, na taxa da timeline, desde o início
  do arquivo = o `<in>` do xmeml) → `entrega.reescrever` → `bl-conform` → conferência → `bl-shots -replace`. ⛔ O
  `bl-conform` recusa o xmeml sem `sequence/media/video/format` ("Element 'format' not found", e1624). BL08 (os 17 planos do
  AAF): conform 13 ok + 3 trocados pelo Baselight (P1, P2, a cópia do P9) + 1 offline → corrigido **16 ok + 1 offline (P10)**;
  render **16 de 16 certos**, com o **P3 (178) e o P7 (389) no ponto** — os dois que o Baselight errava pelo AAF religado.
  Montagem do MC refeita com os 20 planos (P11/P12): papel 16/1/0; Baselight 18 ok + 1 offline; **render 18 de 18**, P11 (original
  TC 20h × daily zerado) e P12 (original zerado × daily 21h) certos na câmera e no quadro — a ponte pelo original ignora o TC.
- ⭐ **Sequência de imagens no xmeml (BL08 P10, 2026-11-22, `confirmado` por render):** com o caminho de UM quadro no
  `<file>` (`A003C001.1641600.dpx`), o `bl-conform` conforma a sequência como imagem PARADA (o 1º quadro no plano inteiro),
  embora o `bl-shots` dê in/out em números de quadro. Com a sintaxe FilmLight no `pathurl` (`A003C001.%.7F.dpx`, o `%`
  como `%25`) ela anda, e o `bl-shots` conta o ponto pelo NÚMERO do quadro no nome (in = 1º número + posição). ⛔ Mas
  entrou **7 quadros adiante, constante** (in 0 → 1641607, 23 → 1641630, 48 → 1641655; com o arquivo a 25 qps, 23 → 1641631),
  qualquer que fosse o TC declarado no `<file>` (00:00:00:00 ou 19:00:00:00); o DPX do laboratório não tem TC nem taxa
  no cabeçalho. Causa: `pendente`. A conferência acusa como "fora do ponto" (marker), não passa calado.
- ⛔ **E sem `<duration>` no `<file>` a sequência também entra PARADA** (2026-11-22, `confirmado` pelo `bl-shots`, 7.0.3):
  mesmo com a sintaxe `%.7F`, o `<file>` sem `<duration>` deu in = out = 1641607 (um quadro só no plano inteiro); com
  `<duration>144</duration>` (o número de quadros da sequência), in 1641630 → out 1641677. Achado pelo app (o xmeml
  partindo do original DPX, sem duração legível pelo ffprobe): a entrega do Conformar agora CRIA o `<duration>`.
- **Nome de job e scene (7.0.3, `confirmado`):** espaço e "·" passam (`bl-mkscene … "ZZ teste Ciclo · import 02"`); `:`
  separa host:job:scene. `bl-conform --destscene` numa scene que JÁ existe não a substitui: põe as faixas novas POR
  BAIXO das antigas (o `--help`) — o Ciclo nunca conforma numa scene existente (nome livre, " · import 02").

## Atualizar corte: levar a cor da v1 para a montagem v2 (laboratório BL09, `confirmado` pela FLAPI, 7.0.3 Mac, 2026-11-22)

Bancada `laboratorio-de-midia/lab/bancadas/baselight/atualizar_corte.py` (seis originais limpos do BL08; a cor de cada
plano é um CDL com slope R = 1 + k/100, lido de volta do BLG). A v2 tem uma mudança de cada tipo: plano NOVO (mesmo
arquivo de um RETIRADO, outro trecho), MOVIDO, APARADO, ESTENDIDO, TAKE TROCADO, dois planos do mesmo arquivo.

| via | v2 | o que sobra / o limite |
|---|---|---|
| ⛔ editar a scene do colorista no lugar (FLAPI) | — | a FLAPI só apaga (`delete_shot`) e insere (`insert_sequence`): **não há aparar** |
| `bl-conform --CopyGrades Yes` numa scene NOVA | 0/7 | não tem de onde copiar: ele copia dos planos que JÁ estão na scene de destino |
| `--CopyGrades` por cima de uma CÓPIA da v1 | 7/7 | a v1 fica numa trilha cinza por cima; o que da v1 passa do fim da v2 ENTRA no render; o marker da scene fica no quadro de gravação (cai em outro plano) |
| Multi-Paste (FLAPI), `MatchBy` arquivo + TC (ou + número de quadro) | **7/7** | scene limpa; o log diz "No matching shots found" (novo, take trocado) e "Conflict!"; markers da scene NÃO vão |
| Multi-Paste só pelo nome (`Filename` + `AlwaysMatch`) | 5/7 | ⛔ erra calado: o plano novo herdou a cor do RETIRADO, o movido a de outro plano do mesmo arquivo ("Conflict!" no log, e cola assim mesmo). `Filename` sozinho é recusado ("Invalid value Filename for MatchBy[0]") |
| plano a plano pelo BLG (`get_blg_payload` + `get_blg_resources` → `apply_blg_payload`), mesmo arquivo e trecho de fonte em comum | **7/7** | o casamento é de quem copia |

- ⚠️ **Plano que o colorista DIVIDIU** (S4 cortado em dois na scene dele, cores diferentes; a v2 apara esse plano): o
  Multi-Paste põe UMA cor (a do 1º pedaço) no plano inteiro ("Multiple matches contribute to this shots grade"); a cópia
  pelo BLG escolhe um pedaço. Nenhuma acerta sozinha: o certo é cortar o plano da v2 no mesmo quadro de FONTE (quem
  monta o xmeml pode).
- Multi-Paste pela FLAPI: `c.MultiPaste.create().multi_paste(scene, MultiPasteSettings(Source="MultipleScenes",
  SourceScenes=["host:job:scene"], MatchBy=[…], MatchQuality="ExactMatch", PasteGrades=1, LayerZeroBehaviour="StackOnly",
  SourceShots="CopyAll", DestShots="OverwriteAll", PasteLocation="Above", MaintainTracks=1, …), shot_ids)` — **dentro de
  um delta** (sem ele: "No current delta"); `get_log()` dá o relatório por plano. Aparado e estendido casam com
  `ExactMatch` (o trecho em comum basta).
- **Duplicar uma scene sem tocar nela:** `bl-export host:job:scene x.blscene` → `bl-import host:job:PASTA x.blscene` (na
  raiz do job dá "Scene … already exists") → `JobManager.rename_scene(host, job, "PASTA:nome", "nome novo")` (com `:`; a
  scene vai para a RAIZ do job com o nome novo). `JobManager.create_folder(host, job, pasta)`.
- O BLG de `get_blg_payload`: base64 → **8 bytes de cabeçalho** → zlib → texto; o CDL é `GR_CDLGradeRop` com os 10
  valores em hexadecimal de double (slope RGB, offset RGB, power RGB, saturação).
- ⚠️ A primeira scene aberta na interface num job NOVO pergunta o formato da galeria do job ("Creating New Per-Job Gallery
  … Choose Format"; o formato da scene vem marcado; Ok).
- ⭐ **No produto (Ciclo Assist, 2026-11-22):** Multi-Paste arquivo + TC e, depois, a conferência pela IMPRESSÃO da cor
  (os operadores `GR_…Rop` do BLG com os doubles, SEM a camada 0 — `GR_AudioSequenceRop`, `GR_ImageTransformParamsRop`,
  `GR_PluginInputRop`, `GR_InsideOutsideRop` estão em todo plano): a mesma cor dá a mesma impressão em scenes diferentes
  (v1 × Multi-Paste × `apply_blg_payload`: iguais). Corrigir = `Shot.delete_all_layers()` + `apply_blg_payload` (provado:
  2 planos errados de propósito → certos). Plano dividido pelo colorista: o xmeml da v2 cortado no mesmo quadro de fonte
  ANTES do conform → cada metade casa com o seu pedaço (8/8). `_CICLO ASSIST/modulos/conformar/motor/baselight/
  atualizar.py` + `cor_flapi.py`. ⚠️ `StackOnly` não leva a camada 0 (o reposicionamento do colorista).
- ⛔ **Scene ABERTA na interface com mudança NÃO SALVA** (`confirmado`, 7.0.3 Mac, 2026-11-22, pilotado): abrir de fora
  só para leitura é RECUSADO — "Scene must be opened read/write to recover or discard autosave data". Abrir para escrita
  recuperaria ou descartaria o autosave do colorista: nunca. Depois do ⌘S (Scene › Save) a leitura de fora passa e já traz
  o valor novo (slope 1,2 lido na hora). Salva e aberta para edição (lock "Write") o colorista não atrapalha: a leitura e o
  Multi-Paste dela como ORIGEM funcionam, e ela não é modificada (a data de modificação não muda).
- ⚠️ **Várias scenes abertas** na mesma interface: cada uma tem o seu lock (uma "Read" aberta uma hora antes continua lá,
  atrás); a do colorista é a "Write". O Multi-Paste NÃO deixa lock na scene de origem (medido).
- ⚠️ Campo numérico da interface (Slope): clique no campo, **End + Backspace** e as teclas por código; ⌘A não seleciona
  o texto (o valor digitado fica inválido e o campo volta ao de antes, calado).
- ⭐ **Cor ANIMADA (keyframes) num plano aparado** (`confirmado`, 7.0.3 Mac, 2026-11-22, pilotado + FLAPI): o keyframe do
  CDL vira `o <ref>` → `GM_Bezier1dInterp … t <hex> <n>:6 0 <k> [tempo valor ângulo compr. ângulo compr.]×k 0 2 -1 0.001
  <v>  ` (tempo em SEGUNDOS desde o INÍCIO DO PLANO; `<n>` = tamanho do corpo − 1; cabeçalho do payload = `<Q` tamanho do
  texto). O **Multi-Paste DESLOCA** os keyframes pela diferença de fonte (S4 aparado 12 na cabeça: 7/41 → −5/29, presos à
  imagem); o **`apply_blg_payload` NÃO** (copia 7/41 cru: a animação escorrega 12 quadros). Reescrever o tempo e o
  `<n>` e reaplicar funciona (o Baselight aceita; −5/29). Produto: `atualizar.deslocar_keyframes`.
- ⭐ **Faixa de cor sobre VÁRIOS planos** (o "look"; `confirmado`, 7.0.3, 2026-11-22): faz-se na interface com uma
  camada em cada plano (Layer › Insert Layer – Base Grade, P) e **Edit › Toggle Split/Join Strips (⌘K)** com as faixas
  selecionadas (⇧+clique; Insert In Marks/Gaps NÃO a estende). No BLG de CADA plano ela aparece inteira, com o
  `GM_Strip` do tamanho do PLANO (início 0, duração do plano) — o BLG não diz que ela atravessa. Na atualização ela vai
  com a cor de cada plano que manteve a cor; plano novo ou take trocado dentro dela não recebe nada (nem o look).
- ⚠️ Interface: clique na RÉGUA move o cursor, mas não sobre a etiqueta do próprio cursor; Navigate › Next Frame = →,
  Next Cut = X, Scene Head = ⌘Home; Mark In/Out = ⇧[ / ⇧]; o keyframe de um parâmetro = o ícone de chave sob a roda
  (depois dele, mudar o valor noutro quadro cria o 2º keyframe).
- ⭐ **Só uma camada de um BLG** (`confirmado`, 7.0.3, 2026-11-22): o grafo é `GM_Timeline 2:gm 3 <S+3> <faixas…> 7 8 10 0 0
  S S 0 S S+1 1 S+2` (S = nº de faixas); cada `GM_Strip 2:gm 1 1 <moldura> 1 o 0 <início> <duração> <índice> f f 0`
  (camadas 0…S−2 de cima para baixo, a mídia S−1); a moldura `GR_InsideOutsideRop … 7 3 0 <inteiro> <operador> …
  <n>:Layer:<N>`. Tirar faixas do `GM_Timeline` (refazendo as contas e os índices) e deixar os objetos soltos: o
  `apply_blg_payload` aceita, descarta os soltos e a mídia do plano NÃO muda (aplicado no take trocado: C001C004 ficou).
  Produto: `atualizar.so_camadas` (o look no plano novo/take trocado, decisão do autor).
- ⛔ **`bl-conform` sem `--TimeType Source` numa timeline CURTA** (`confirmado`, BL09 V2B, 2026-11-22): todo arquivo
  mais longo que a timeline ⇒ o passo por tempo de GRAVAÇÃO também dá 100 % e pode ser o escolhido: cada plano entra
  com a fonte = a posição na timeline (5 de 5 fora do ponto). Xmeml de montagem = `--TimeType Source` sempre.
- ⛔ **Multi-Paste com `MaintainTracks=1` numa scene vinda do AAF** (`confirmado`, PRODUCAO-A, 7.0.3, 2026-11-22): o log
  diz "Unambiguous match" e "Grades pasted onto 99 shots" e NADA entra no BLG dos planos (a cor vai para uma trilha que a
  v2 não tem). Com `MaintainTracks=0` cola. No BL09 (uma trilha) os dois funcionavam. ⇒ conferir SEMPRE pela leitura.
- ⭐ **Caso real: PRODUCAO-A, PRODA_CORTE.02 → corte final "PARA COR" (19/12/2023)** (2026-11-22): a v1 = a CR03T3 da
  28ª rodada copiada para o job "PRODUCAO-A" com uma cor por plano (CDL), um look em 3 vizinhos e uma cor animada; a v2
  = o AAF do corte final pelo caminho do produto (`baselight_conform._entregar`, relink emulado pelo nome do clipe): 99
  planos em 12 s, conform 99/99, cor 99/99 (97 pelo Multi-Paste, 2 corrigidos pela conferência), conferido por fora com
  os valores lidos dos dois lados; o look nos 3 planos; os keyframes no lugar.
- ⭐ **Grupos** (`confirmado`, BL09, 7.0.3, 2026-11-22): `Scene.set_group(nome, [ShotId…])` / `get_groups()` /
  `get_group(nome)` (dentro de um delta). O Multi-Paste com `PasteGroups=0` NÃO leva grupo nenhum (a scene nova sai `{}`,
  calada); com `PasteGroups=1` leva o NOME e só os planos que ELE casou — o take trocado sai do grupo, calado. ⇒ Produto:
  `PasteGroups=0` e os grupos refeitos pelo casamento do Ciclo (`atualizar.levar_grupos`), relidos, o que ficou de fora dito.
- ⭐ **Várias trilhas** (`confirmado`, BL09 MT, 7.0.3, 2026-11-22): o `bl-conform` de um xmeml com V1+V2 mantém as trilhas
  (o plano PARCIALMENTE coberto entra INTEIRO na trilha dele, o de cima por cima) e DEIXA FORA o plano coberto INTEIRO.
  `bl-shots -inputrange -outputrange` lista as tiras de todas as trilhas (o mesmo quadro de início pode repetir).
  ⛔ A conferência que casava "esperado × tira" só pelo quadro de início, esperando o escondido, TROCOU pelo `-replace` a
  imagem do plano VISÍVEL (o S5x virou o arquivo do S5 escondido). Conserto: o escondido não é esperado; mesmo início =
  casar pelo arquivo, depois pelo fim, cada tira uma vez (`entrega.esperado` + `conferencia.conferir`).
  A cor da scene ACHATADA e JUNTADA pelo colorista vai à v2 bagunçada de novo pelo mapeamento de fonte (9/9: os dois
  pedaços do corte à toa aparado herdam a cor do plano que ele juntou; o inserto, a dele).
- ⭐ **O render da cor voltando à montagem** (`confirmado`, BL09, 7.0.3, 2026-11-22): o render ProRes de um plano
  (`RenderSetup` + `FrameRange`; End EXCLUSIVO: 96–143 deu 47 quadros) grava o **TC de FONTE** do plano (17:00:02:12) e o
  **reel = o nome do original** (`reel_name` C001C003 na trilha de TC). Direto ao Baselight ele entra offline (o
  `bl-conform` procura pelo nome nas pastas dos originais); o casador do Premiere o recusava (duração, TC, "cópia").
  Produto: o TRECHO (`prproj/originais._trecho`: mesma taxa, TC real, inteiro dentro do original, pelo reel ou pelo nome)
  → o original, com o `<in>/<out>` deslocado pela diferença de TC (`entrega._deslocar_trechos`, pelo `<file>` DO DAILY) e
  o marker "[Ciclo] um trecho do original…: o render da cor voltando?" → 7/7 com a cor do colorista.
- ⭐ **O reposicionamento do colorista é uma CAMADA Transform** (`GR_TransformRop`), não a camada 0: o `StackOnly` a leva
  e a impressão do BLG a compara (S4 aparado e S6 estendido, 7/7).
- ⛔ **A camada 0 do colorista** (`confirmado`, BL09 + PRODUCAO-A, 7.0.3, 2026-11-22): o espaço de cor de ENTRADA
  (`Shot.get/set_input_colour_space`; nomes de `FormatSet.factory_formats().get_colour_space_names()` — "Rec709_Video" não
  existe e só falha no `end_delta`) e o DECODE do RAW (`get/set_decode_parameters`: BRAW `wbkv` K, `wbtn`, `expo`, `fiso`
  ISO, `tcon`…; ProRes: "No decode parameters available for this shot"). Com `StackOnly` os dois SE PERDIAM e a impressão
  do BLG não via (7/7 com o S2 errado). `LayerZeroBehaviour="LayerZeroAndStack"`, `LayerZeroOverwrite=1`,
  `LayerZeroAudio=0`, `InputColourSpace=1`: levam os dois, a mídia e os pontos não mudam. ⛔ O `apply_blg_payload` MEXE no
  decode (tirou o `fiso` de 2 BRAW): a camada 0 se confere DEPOIS da correção pelo BLG. ⛔ Plano sem mídia (título,
  preto): `get_input_colour_space` levanta "attempt to read a NULL keyed by grsr_InputColourSpace". PRODUCAO-A com o
  decode mudado em 2 planos (4500 K, +0,5): 99/99.
- ⚠️ **Delta que falha deixa a scene TRAVADA** (2026-11-22): o processo morreu com o delta aberto (o `end_delta` recusou);
  a scene ficou com a trava "Write" do `flapid`, e `bl-unlock -a` não a tirou. ⇒ `cancel_delta()` em todo `except`.
- ⭐ **Decisão do autor (2026-11-23): o take trocado e o plano novo entram no GRUPO como no look** — no grupo do plano que
  substituem, ou no dos dois vizinhos; marker "[Ciclo] … entrou no grupo “X” do colorista". BL09: o C001C004 no "SALA".
- ⭐ **O render da cor voltando PELO MC** (`confirmado`, BL09, MC 25.12 Mac + Baselight 7.0.3, 2026-11-23): a v2 montada no
  MC com o render no lugar do S3 (in 4, 40 quadros); o AAF não leva o reel (`tape_name` vazio) e grava `local_path` vazio
  no segmento da Carta — o arquivo vem de `carta.arquivos`, com o caminho SEM `/Volumes`. O casador dos masters
  (`media/matcher_masters`) recusava o original pela duração e pelo TC; agora o TRECHO (a mesma regra do Premiere) o
  aceita pelo reel do arquivo, com 0,85 (topo da revisão). ⛔⛔ **Erro calado achado**: o `montar_midia` troca o daily pelo
  original e o `source_start_frames` continua contado desde o início do DAILY — o plano entrou em 4–43 do original (em vez
  de 64–103) e a conferência APROVOU, porque o xmeml esperado tinha o mesmo erro. Vale também para o DRT do Resolve (pelo código do
  `drp/writer`, o `In` conta desde o início do arquivo; não medido no Resolve) e para um original escolhido à mão para um daily consolidado. Conserto no ponto da troca
  (`avb_bin.segmentos._deslocar_trecho`); e o `existe_aqui` do `_montar` passou a tentar o `/Volumes` (sem ele o arquivo
  do master nunca "existia aqui" no Mac). Resultado: 7/7 conform e cor, C001C003 64–103, marker no quadro 96.
- ⭐ **O render de um plano de OUTRA TAXA** (`confirmado`, BL08/BL09, 7.0.3 Mac, 2026-11-23): A002C001 (29,97 DF) e
  B001C005 (59,94) numa scene de 23,976, renderizados pela FLAPI (a fila só renderiza com a INTERFACE aberta: "no
  application rendering from the queue"; duas faixas no mesmo `set_frames` viram UM .mov só). O render sai na taxa da
  TIMELINE (23,976, 48 quadros) com uma trilha `tmcd` HÍBRIDA: timescale 24000/1001 (anda a 23,976), mas `nframes` = a
  base do ORIGINAL (30 com o flag DF, 60) e o contador = o quadro EXATO de fonte do original no in do plano (1832425 =
  16:58:50;00 contínuo + 359; 2592118 = 12:00:00:00 + 118 na base 60; na mesma taxa, 1468860 = 17:00:02:12). ⛔ O ffprobe
  converte o de 60 por TEMPO ("12:00:01:23", fração de quadro perdida) e RECUSA o de 30 DF ("Drop frame is only allowed
  with multiples of 30000/1001": TC nenhum). O reel sai `A002C001.mov` (COM a extensão: o plano entrou pelo nome do
  arquivo; no BL09, pelo `<reel>` do xmeml, sem). Produto: `prproj.originais.tmcd_cru` (lê o `moov` com seek, 4 bytes da
  mídia) entra na `sondar`; o `_trecho` aceita taxa diferente só com a base do contador = a do original, desloca em
  TEMPO (quadros do original / taxa dele) e a entrega converte para quadros da timeline; o reel perde a extensão.
  Pelo caminho do Premiere: 3/3 no quadro de fonte (47, 364, 128 = a conta pelo tempo; bancada `outra_taxa.py`); o do MC
  dá o mesmo In (291 e 51 quadros da timeline) pelos arquivos reais, sem o MC aberto.
- ⭐ **O trecho no caminho Premiere → RESOLVE** (`confirmado` pela imagem, Premiere 2027 + Resolve Studio 21.1 Mac,
  2026-11-23; bancada `premiere_outra_taxa.py`): o `.prproj` com um plano normal, o render de mesma taxa e os dois de outra
  taxa. ⛔ O `prproj_para_drt.montar` trocava o render pelo original SEM o deslocamento (o mesmo erro calado do MC) →
  `_deslocar_trecho` (na `source_fps` do segmento, que o `_ler` relê na taxa do original) + marker amarelo "Trecho do
  original". ⛔ O casador dava EMPATE no C001C003: os originais do BL09 são cópias dos do BL08 — o ramo do trecho não tinha a
  regra das cópias idênticas (agora tem). ⛔ E o Resolve arredonda o In inteiro para BAIXO na fonte de outra taxa (363 e 127
  em vez de 364 e 128) → o In com fração (`protocolos/drt-drp/estruturas.md`, §3). Resultado: 4/4 no quadro (47, 64, 364,
  128, lidos no número queimado), com os 3 markers.
- ✅ **O render de outra taxa pelo MC VIVO** (`confirmado`, 2026-11-23, MC 25.12 Mac; lab `mc_outra_taxa.py`): os renders de 29,97 DF e 59,94 (23,976, TC no contador cru do `tmcd`) linkados no MC entram com edit rate 23,976; o AAF exportado pelo MC → o casador do produto acha o trecho pelo reel (0,85, a revisar) → Baselight: **3/3** no quadro de fonte (47, 364, 128). ✅ o som de outra taxa no DRT: com fração, como o vídeo (`protocolos/drt-drp/estruturas.md` §3).

- ⭐⭐ **Atualizar corte COM EFEITOS** (`confirmado` pelo render, 7.0.3 Mac, 2026-11-23; PRODC real, lab
  `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_BASELIGHT/estudo/ferramentas/lab_atualizar_efeitos.py`): ⛔ o Multi-Paste "Above"
  cola a pilha INTEIRA do colorista — com o Retime/Transform/composição que o conform da v1 gravou — por cima da pilha da
  v2 (efeitos DOBRADOS), e copiar o BLG inteiro da v1 traz os efeitos VELHOS (a v2 mudou velocidade/Motion/máscara). ✅ O
  desenho que fechou: **marcar as faixas do conform pelo NOME** e levar só as do colorista para cima da pilha da v2.
  - O **nome da camada** é a 1ª string `<n>:<texto>` da moldura da faixa seguida da cor do rótulo (`42ca0000 …`):
    `9:Transform` (GR_TransformRop), `7:Layer:0` (o fundo da composição), `17:Layer:1 Comp:Over`, `5:Shape`, `7:Tracker`;
    a da mídia não tem `Layer:`. Trocado no BLG (`15:Ciclo Transform`, o prefixo em BYTES) o `apply_blg_payload` aceita, o
    nome volta igual na leitura e **a imagem não muda** (PRODC marcado × sem marca: 1591 de 1591 quadros, dif. 0,000).
  - ⭐ **O `.blscene` (`bl-export`) é a leitura certa da pilha de CADA plano**: lê o plano mascarado (multi-input, que o
    `get_blg_payload` recusa) e o da trilha de baixo (o `get_blg_payload` devolve a pilha de quem está por cima — medido de
    novo: o TitleCard do V1 sob o JUL_7503 vinha com o Transform dele). O plano = o bloco de linhas da trilha (1024 por
    trilha) com a faixa da MÍDIA no mesmo tempo (a última linha do bloco); a pilha = as faixas do bloco que cobrem o
    plano. As chaves de curva no `.blscene` contam do início da FAIXA (as dos planos medidos começam em 0).
    ⛔ Duas armadilhas: (1) o arquivo guarda também as faixas que SAÍRAM da timeline — só valem os filhos do
    `GM_Timeline` (a versão final); (2) leva a mudança **NÃO SALVA** da interface (BL09 "V1 dividida": delta "Change to
    CDLGrade" depois do salvo; `Reference` "Main" `DeltaIds` = {4,5,4,5}, o `@readable` = {4,4,4,4}) — o estado salvo = o
    1º de `Main.DeltaIds` e os pais (`Delta.ParentDeltaId`); é o que a FLAPI só-leitura e o render veem.
  - Objetos do `.blscene` transplantados para o BLG: estado escapado (`\\`, `\"`, a quebra `\n" "`), texto na visão de
    bytes, ids novos, a faixa `1 o 0 <início> <duração> <linha> f f 0` com a duração das da base.
  - `Shot.insert_cdl_layer_above` põe o CDL **logo acima da imagem** (embaixo das outras camadas) e funciona em plano
    multi-input; `apply_blg_payload` ACRESCENTA a pilha (por isso o `delete_all_layers` antes).
  - ⚠️ O Baselight relê o `-0,0` (`8000000000000000`) de uma curva do Transform como `0`: comparar números, não o hex.
  - Resultado: v1 = PRODC com efeitos + 10 máscaras + um CDL por arquivo; v2 = a mesma montagem com velocidade (congelada)
    e Motion mudados em 3 planos, um mascarado → atualizar: 74/74 conferidos (12 mascarados + 1 de trilha de baixo pela
    scene exportada); **o render = a v2 montada do zero com o mesmo CDL, 1591 de 1591 quadros, dif. 0,000** (a v1 difere
    só nos 3 planos mudados). BL09 (look, grupos, divisão, multitrilha, reposição): iguais a antes. Implementado:
    `_CICLO ASSIST/modulos/conformar/motor/baselight/camadas.py` + `cor_flapi.py`.

## O Stabilize do Media Composer no Baselight (`confirmado` pela imagem, MC 25.12 / Baselight 7.0.3 Mac, 2026-11-23)

- ⭐ **Como TRANSFORM ANIMADO, um keyframe por quadro** (a precisão da montagem, como nas rampas): o tracker viaja no AAF
  (`OpGrpTKMNTrackerDataAry`, `protocolos/avb/estruturas.md` §Stabilize) e a conta do MC já medida (u = p − G₃₀·filtro(p)
  + desloc., depois o Auto-Zoom Z) vira, por quadro, **escala Z, X = 960 − uₓ·W·Z, Y = 540 − u_y·H·Z** na camada
  Transform (a posição é onde o CENTRO cai, Y para baixo, escala em torno do centro; keyframes em k/fps desde o início do
  plano). Ferramentas `estudo/ferramentas/estabilizar_mc.py` (series → aplicar, `blg_pilha.com_transform` com séries) e
  `medir_estab.py` (correlação de fase × o vid ref). PRODUCAO-A, os 2 planos estabilizados (scene "CR05 ESTAB"):
  C011 (393 q, Z 1,0117) desvio 2,21 px → **0,01 px**, semelhança 0,957 → **0,992**; C013 (203 q, V2, Z 1,0428) desvio
  6,42 px (y) → **0,05 px**, tremor quadro a quadro 3,2 → **0,06 px**, semelhança 0,881 → **0,995**. Igual ao render do MC.
- O estabilizador NATIVO (manual v7 p. 840–842): operador Transform + um tracker (1 ponto, 2 pontos ou área) numa faixa
  de tracker, ligado pelo **Stabilise (invert)**; aba Filtering (Shake/Noise, Motion, Threshold) devolve parte do
  movimento; Apply por escala/rotação/X/Y.
- ⭐ **O formato no BLG** (`confirmado` por amostra feita na interface, pilotado; scene "0 CR06 ESTAB NATIVO", plano
  C013; texto em `estudo/producao-a/estab/C013_nativo_blg.txt`): Insert › Transforms › Transform, "New Tracker: 1 point"
  (o alvo nasce no CENTRO da imagem — na CR, em cima da pessoa, que se mexe: o ponto desceu 77 px), Tracking ▶,
  "Return To Transform" → no Transform: `Track1 - One Point Track` / `TrackerRop<id>[Track1]`, Stabilise (invert) ligado,
  Apply X/Y. Objetos:
  - `GR_TrackerRop` (faixa "Tracker" ACIMA do Transform; `gr_tracker 5 2 0 <core> 0 7:Tracker … 6:Track1 6:Track1`) →
  - `TRACK_Transform2dInterpCore` (`track 1 4 <a> <b> <c> <saida> 7 o 0 o 1 o 2 o 3 …`): três `GM_Bezier1dInterp` = a aba
    Filtering (Shake/Noise 0, Motion 0, Threshold 0,7, animáveis) + a saída:
  - `TRACK_TrackOutputInterp` (doubles BIG-ENDIAN em hex): cabeçalho com o ponto de referência (960, 540) no quadro 0 e as
    caixas (padrão 38,88, busca 97,2); depois `0 <N>` e N registros de 14 campos: **tempo (k/fps, s), X, Y (px de
    1920×1080, Y para baixo), X e Y do quadro anterior, dX, dY, marca t/f, 2 valores de movimento, 4 de erro**; o último
    é um terminador (tempo −1, zeros). C013: N = 203 (202 pontos + o fim).
  - No Transform, `BEZ_TrackedTransformInterp` (`bez 2 1 <core> 2 z o 0 1 0 1 1 0 f`) liga o rastreio (o Stabilise e os
    Apply devem estar nesses números — `inferido`).
  ⇒ Escrever o rastreio do MC aqui é possível (os X/Y por quadro do `OpGrpTKMNTrackerDataAry`), mas o filtro do Baselight
  (Shake/Motion/Threshold) é outro algoritmo que o G₃₀·filtro do MC e o Stabilise não dá zoom: o resultado seria PARECIDO,
  não igual (como o Warp Stabilizer do Premiere). `pendente`: os campos de movimento/erro e se o Baselight os recalcula.
- ✅ **Decisão do autor (2026-11-23): o TRACKER NATIVO** (o colorista ajusta como estabilizador). Primeiro passo
  `confirmado`: o rastreio do MC escrito no `TRACK_TrackOutputInterp` da amostra (`estabilizar_mc.py nativo`: ponto de
  referência = o do quadro 0; registros com tempo, X, Y, anterior, dX, dY, `t`, dX/2, dY/2 e erros 0) e aplicado num
  C013 limpo ("CR07 ESTAB MC NATIVO") — o Baselight USA esses pontos: com o Filtering zerado (Motion 0) ele trava a
  imagem no quadro 0, e o render × o vid ref dá exatamente a curva suave do MC menos o quadro 0 (medido −14,8/−55,7 px,
  desvio 23,2/30,7; previsto 18,6/53,1, desvio 22,6/29,3; o resto = o zoom 104 % do MC e o sinal da medida). O ponto do
  MC anda (Y 457→541): o MC tira só o tremor (G σ 15), o Stabilise zerado tira tudo.
- ⭐ **O Filtering calibrado** (`confirmado` pela imagem, 2026-11-23, C013 na "CR07 ESTAB MC NATIVO"; renders de 6 s pela
  fila local, SEM a interface aberta): o manual (p. 841) diz Motion = fração do movimento LENTO devolvida, Shake/Noise =
  fração do tremor devolvida, Threshold = a separação entre os dois. O MC devolve todo o lento (G σ 15) e tira todo o
  tremor ⇒ **Shake 0, Motion 1, Threshold 0,05**. Medida: a correção aplicada (render × o plano sem estabilizar, correlação
  de fase) × o alvo do MC −(p − G₁₅p). Varredura do Threshold (Motion 1): 0,95 ≈ G σ 5 · 0,7 (o padrão) ≈ σ 5 · 0,3 ≈ σ 10 ·
  ≤ 0,1 ≈ σ 15 com **piso** de desvio 0,78 / 1,72 px (0,05, 0,02 e 0 iguais). O resto é DERIVA LENTA (1–3 px no meio do
  plano, a forma do filtro do Baselight não é um Gauss), não tremor: o tremor tirado é o do MC (2ª diferença 0,39 × 0,37).
  Com o zoom Z e o deslocamento d no Transform (escala Z fixa; posição X = 960 − dₓ·W·Z, Y = 540 − d_y·H·Z, em px/1920 no
  BLG; o rastreio é aplicado ANTES da escala, como no MC), × o vid ref: desvio 0,80 / 1,72 px, tremor q→q **0,07 / 0,18**
  (sem estabilizar 3,55 / 1,98), semelhança **0,994** (Transform animado 0,995; sem 0,881); desloc. médio −1,0 / −0,9 px.
  Ferramentas `estudo/ferramentas/estab_filtro.py`, `estab_transform.py`, `estab_correcao.py`, `estab_varrer.sh`.
  ⇒ Com Motion 1 o nativo fica só PARECIDO. ⛔ E o filtro dele NÃO se prevê pelo rastreio: um filtro linear livre
  ajustado no C013 explica 0,15 px no próprio plano, mas no teste cruzado (ajusta em X, testa em Y) erra 0,8–1,5 px.
- ⭐⭐ **Igual ao MC com o tracker nativo** (`confirmado` pela imagem, 2026-11-23, decisão do autor "compensa"; C011 e C013
  na "CR07 ESTAB MC NATIVO"): **Motion 0** (trava no quadro 0, exato e previsível) e o **Transform** leva escala Z fixa e
  posição POR QUADRO = X(k) = 960 + Z·(G(pₓ)(k) − pₓ(0)) − (Z − 1)·(pₓ(k) − pₓ(0)) − dₓ·W·Z (Y igual, com H; G = Gauss
  σ 30·filtro, borda nearest). ⭐ **O tracker do Baselight desloca DEPOIS da escala** (px de tela, não × Z): sem o termo
  (Z − 1) o resto do C013 (Z 1,0428) foi exatamente (p − p₀)(Z − 1) (correlação 0,98/1,0, ganho ≈ 1). × o vid ref: C011
  desvio 0,01/0,01 px, semelhança 0,9919; C013 0,22/0,04 px, 0,9954 — os mesmos números do Transform animado.
  Plano sem tracker: as faixas Transform + Tracker da amostra enxertadas (`blg_pilha.objetos/_desc/_renumerar`, ids
  novos, duração do plano; as faixas do plano sobem 2 linhas: imagem 2, Tracker 1, Transform 0; fora dos objetos o BLG só
  difere no offset e na duração, que são do plano). Ferramenta `estudo/ferramentas/estab_nativo.py` (com conferência na
  volta). ⛔ Erro calado no caminho: regex de curva CONSTANTE (`f <hex> N:6 0 0 0 0 -1 0.001 v`) não pega a ANIMADA
  (`t <hex> N:6 0 <n> …`) — a 2ª passada não mudava nada e o render repetia o anterior; trocar a curva inteira pelo N.
  O ponto de referência do `TRACK_TrackOutputInterp` está na POSIÇÃO 9/10 do cabeçalho (não procurar o 960).
  `pendente`: se o Baselight recalcula os 2 campos de movimento dos registros (o render não depende deles com Motion 0).
- ✅ **No produto** (Ciclo Assist `ff20a2c`, 2026-11-23): `modulos/conformar/motor/baselight/blg_estab.py` (as contas,
  só stdlib) + `estabilizar_flapi.py` + o molde `moldes/estabilizador_nativo.txt` (29 objetos, 3,2 KB); a regra de quem
  vai é a do Resolve (`estabilizacao.traduzivel`). Roda depois do conform, da conferência e da cor; ⛔ plano que JÁ tem
  tracker (o do colorista, pelo Multi-Paste) não se reescreve. Marker no plano: o porquê do Motion 0 ("subir o Motion
  devolve o lento duas vezes"). Prova pelo produto, scene nova do AAF real ("CR08 PRODUTO ESTAB"): C011 0,01/0,01 px,
  C013 0,22/0,04 px × o vid ref. ⛔ Antes, o plano estabilizado ia ao Baselight SEM estabilização e sem aviso.
- ⛔⛔ **O rastreio vai no formato de TRABALHO da scene, não no raster do xmeml** (`confirmado`, 2026-11-23, pela
  janela do app): o `bl-conform` do xmeml criou a scene em HD 1920×1080 (o `WorkingFormat`) mesmo com o xmeml declarando
  4128×2176 (o raster do 1º arquivo, um BRAW); com o rastreio em px de 4128 o movimento saiu 2,15× maior e os planos
  ficaram PIORES que sem estabilizar (semelhança 0,72/0,51). Ler pela FLAPI: `scene.get_scene_settings().get_single(
  "WorkingFormat")` → `scene.get_formats().get_format(nome).get_resolution()` = {Width, Height}. Corrigido
  (`blg_estab.no_formato`); pela janela de novo: C011 0,01/0,01 px, C013 0,22/0,04 px, markers nos dois.
- ⭐ **Scene UHD (`confirmado`, 2026-11-23, "CR10 ESTAB UHD 1W": o mesmo AAF, `WorkingFormat` = UltraHD 3840×2160):** o
  rastreio e a posição vão em px do formato de trabalho E o cabeçalho do `TRACK_TrackOutputInterp` leva **1/LARGURA nos
  campos 5 e 6** (a amostra HD tem `3f41111111111111` = 1/1920; UHD `3f31111111111111` = 1/3840): o Baselight normaliza o
  ponto por eles. Com o 1/1920 do molde numa scene UHD o tracker deslocou o DOBRO (o resto = −(p − p₀), coeficiente
  −1,0, resto 0,1–0,2 px). Com 1/W: C011 0,01/0,01 px, C013 0,22/0,04 px — os números do HD. (A posição do Transform
  é px / LARGURA nos dois eixos, em qualquer formato.) `pendente`: as caixas do tracker (38,88/97,2) ficam na escala do
  HD — só a aparência para o colorista que for rastrear de novo; não vistas na interface.
- ⚠️ Durante o rastreio, aviso "I/O: File /Volumes/V-001/…" (o BRAW de 37 GB num HD a ~60 MB/s): leitura atrasada.
- ⚠️ zsh: um glob sem resultado (`ls *.mov`) ABORTA o comando inteiro — numa sequência de renders para o mesmo `.mov`
  isso sobrescreveu três renders. Renomear pelo caminho exato.
