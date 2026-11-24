# Premiere Copilot — painel que baixa o próprio aplicativo a cada abertura

Terceiro caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md)
(1º Jumper/Quickture, 2º [Eddie AI](eddie-ai-arquitetura.md)). Fatos consumíveis em
[dados/premiere-copilot.json](dados/premiere-copilot.json).

**Identidade:** `Premiere Copilot` = a pasta **`PremiereGPTBeta`**. O `.pkg`
(`com.trial17.premierecopilot`) instala nela e o `preinstall` apaga tanto `PremiereCopilot` quanto
`PremiereGPTBeta` antes. O manifesto declara `ExtensionBundleId="com.premiere.GPT"`,
`ExtensionBundleName="Premiere GPT"`. São o mesmo produto sob três nomes.

**Por que este caso importa:** é o oposto arquitetural do Eddie. O Eddie põe o motor fora e mantém
lógica no painel; o Premiere Copilot **não tem lógica nenhuma no disco** — nem JS, nem ExtendScript.
E ele mostra uma **virada de arquitetura acontecendo**: até abril/2026 embarcava um backend Python
de 345 MB; a build de julho/2026 é nuvem pura.

## O que foi inspecionado

| peça | versão | tamanho | onde |
|---|---|---|---|
| `.pkg` macOS (ARM e Intel) | 1.0, build 2026-07-01 | 8 MB · 63 arquivos · 15 MB instalados | `/Volumes/SSD/PREMIERE COPILOT/` |
| `.exe` Windows | — | 5,4 MB | idem (PE32, não aberto) |
| Painel instalado na máquina | build 2026-04-06 | **360 MB · 1.606 arquivos** | `/Library/Application Support/Adobe/CEP/extensions/PremiereGPTBeta/` |
| Bundle remoto do app | servido em 2026-08-09 | 2,4 MB JSON | `api.premierecopilot.com/api/snake3` |

ARM e Intel diferem em **30 bytes**: mesmo payload, nenhum binário nativo próprio.

## O painel é um loader de 5 KB

`index.html` (5.144 bytes) é tudo que existe. Ele faz:

```js
const LOADER_URL = "https://api.premierecopilot.com/api/snake3";
const bundle = await (await fetch(LOADER_URL)).json();   // { html, css, js }
document.head.appendChild(style with bundle.css);
document.body.innerHTML = bundle.html;
scriptTag.textContent = bundle.js;  document.body.appendChild(scriptTag);
```

Buscado em 2026-08-09 (HTTP 200, **sem autenticação**): `html` 244 bytes, `css` 258 KB,
**`js` 1.974.715 bytes**. O aplicativo inteiro desce a cada abertura do painel e é injetado no DOM.

E `jsx/library.jsx` tem **19 linhas** — só um `showAlert`. Ou seja: **o ExtendScript também vem no
bundle** e é executado por `evalScript`. Nada de como ele dirige o Premiere está no disco.

Consequência de produto, e ela é forte: **eles mudam o produto — UI, lógica, e o jeito de comandar
a timeline — sem reinstalar nada e sem versão**. É o extremo do que o Eddie faz com config remoto
e autoatualização de ZXP. Não há build a suportar; há uma só, a de agora.

O loader ainda faz dois truques: desliga o menu de contexto e os botões 2/3 do mouse
(anti-inspeção), e **intercepta `DOMContentLoaded`/`load`** substituindo `document.addEventListener`
— porque o bundle é injetado depois desses eventos já terem passado, e sem o shim o app remoto
nunca inicializaria. Detalhe de engenharia bom de guardar para quem injetar app em painel.

## Como ele fala com os LLMs

**Não fala.** Nenhum cliente de LLM roda na máquina: zero chave em claro no bundle (varredura por
`sk-`, `Bearer`, UUID:token não achou nada — os `sk-*` que aparecem são nomes de variável CSS),
nenhum `api.anthropic.com`/`api.openai.com`/`googleapis`. Tudo passa por
**`api.premierecopilot.com`**, que é o único host próprio no bundle.

Os nomes de modelo no bundle são de um **seletor de modelo** exposto ao usuário:
`claude-opus`, `claude-sonnet`, `gpt-5`, `gemini-pro`, `gemini-flash`, `gemini-3-5-flash`. O
roteamento é servidor; o cliente só nomeia.

Terceiros citados: **`api.fal.ai` / `rest.fal.ai`** (geração de imagem/vídeo — casa com
`VideoImageGeneration.epr` e a pasta `image_generation`), **elevenlabs** (voz), `whisper`
(transcrição). Rotas próprias que aparecem em literal: `/api/subtitles-pro/request-upload`,
`/api/subtitles-pro/transcribe`, `/api/subtitles-pro/transcribe/status/` — **upload → job → poll**,
o padrão de sempre. As outras rotas são montadas por template e não saem por `grep` literal.

Há um `claude-cut-*` inteiro de classes CSS (`claude-cut-word.is-deleted`,
`claude-cut-toggle.is-keep`/`.is-cut`, `claude-cut-autopilot`, `claude-cut-segment`,
`claude-cut-timecode--seek`): é uma feature de **corte por transcrição** — marcar palavra como
apagada/mantida e o corte sair disso. Também aparece `www.davinciclaude.com`, provável produto irmão
para o Resolve.

## Como ele opera o Premiere

Três alavancas, todas clássicas de CEP, e nenhuma delas no disco:

1. **`evalScript`** com ExtendScript vindo do bundle (o `library.jsx` local é stub).
2. **Presets de render do AME**, em `js/libs/render/` — o que ele manda o Premiere gerar.
3. **MOGRT + preset de sequência**: `js/libs/mogrt/Texte PremiereGPT.mogrt` (568 KB) e
   `js/libs/sequence/PRESET_EDIT.sqpreset`. Legenda/título entra como **Motion Graphics Template**,
   não como texto desenhado — e sequência nova nasce de `.sqpreset`.

### O que ele manda renderizar (e sobe)

Valores lidos do XML dos `.epr` (FPS pela taxa de ticks 254016000000 — ver
[`../../transversal/tempo-e-timecode.md`](../../transversal/tempo-e-timecode.md)):

| preset | saída | para quê |
|---|---|---|
| `Audio_ForTranscriptionV2` | **mono, 48 kbps** | transcrição — mais enxuto que os 128 kbps do Eddie |
| `Audio_lowRes_NoEffect` | estéreo 64 kbps | análise geral, sem efeitos da timeline |
| `Audio_ForDemucs` | **WAV 44,1 kHz estéreo** | separação de stems (Demucs) — precisa de qualidade cheia |
| `Audio_ForJumpCuts` | **WAV 48 kHz estéreo** | detecção de silêncio precisa de precisão de amostra |
| `VideoImageGeneration` | **3840×2160 @ 25 fps, 16 Mbps** | quadro em 4K para geração de imagem (fal.ai) |
| `EXPORT_PRESET` | 1920×1080 @ 25 fps, 20 Mbps | entrega final |

⭐ **A regra que os dois produtos seguem, e que vale copiar:** *a resolução do derivado é ditada pela
tarefa, não por um "proxy padrão"*. Fala → mono 48 kbps. Silêncio → WAV sem compressão. Imagem →
4K. Um único proxy para tudo é desperdício de banda num caso e perda de qualidade no outro.

⚠️ `EXPORT_PRESET.epr` se chama **"EXPORT_4K 60fps Sequence"** e é 1080p a 25 fps. Nome de preset é
rótulo, não fato — vale para quando lermos os nossos.

## A virada de arquitetura (abr → jul de 2026)

O painel **instalado** na máquina (2026-04-06) tem 345 dos seus 360 MB numa única pasta:
`js/libs/PremiereCopilotAPI/` — um bundle **PyInstaller onedir** (Python 3.12, `_internal/`,
executável `PremiereCopilot` de 30 MB, mais um módulo compilado com **mypyc**
`81d243bd2c585b0f4821__mypyc.cpython-312-darwin.so`, que é obfuscação leve).

Pacotes declarados no `_internal` (inventário, não descompilação):

- **`langchain` 0.3.27** — orquestração de LLM **local**
- **`librosa` + `soundfile` + `soxr` + `numba` + `llvmlite`** — DSP de áudio local (beat, onset)
- **`sklearn` + `scipy` + `numpy` 2.2.4 + `pandas`** — clustering e estatística
- **`matplotlib` + `contourpy` + `kiwisolver`** — gráficos (a pasta `matplotlib_cache` do postinstall)
- **`sqlalchemy`** — banco local (a pasta `rush_db`)
- **`av`** (PyAV) — decodificar mídia
- `cryptography` 46, `orjson`/`ormsgpack`/`msgpack`/`zstandard`, `xxhash`, `uuid_utils`, `PIL`, `yaml`, `click`

**Ausência que informa:** nem então havia `torch`, `whisper` local ou `onnxruntime`. O Python local
fazia **orquestração e DSP**; a inferência sempre foi remota.

No bundle remoto de agora: **zero ocorrências de `PremiereCopilotAPI`**, e o `.pkg` de julho não
carrega a pasta. **O backend Python foi removido.** O `postinstall` ainda cria as onze pastas em
`~/Documents/Adobe/Premiere Pro/Premiere Copilot/` (`audio_sync`, `image_generation`,
`matplotlib_cache`, `music_analysis`, `rush_db`, `script`, `seq_preset`, `sfx`, `temp`,
`thumbnails`, `transcription_analysis`) — resíduo da arquitetura antiga, e um mapa involuntário das
features do produto.

(Os scripts de instalação estão em francês. Editora provavelmente francófona; `com.trial17.*`.)

## ⭐ O achado que muda a NOSSA arquitetura: `child_process` dentro do painel

O [README](README.md) desta pasta afirma "**o CEP sandbox NÃO spawna processo**, mas o `fetch` para
localhost funciona". O bundle do Premiere Copilot usa `child_process` **quatro vezes**, via
`window.require`:

- fallback de área de transferência: `spawn("pbpaste")` / `powershell -command "Get-Clipboard"` e `Set-Clipboard`
- `revealInFileBrowser`: `exec("open -R <path>")` / `explorer /select,<path>`

São caminhos de fallback num produto em produção, com o mesmo `--enable-nodejs --mixed-context` que
nós usamos. **Não medimos** que funciona (`hipotese` → a validar num teste de 5 minutos), mas se
funcionar, o painel pode subir o próprio motor.

⛔ **Onde isso NÃO se aplica — decisão do usuário, 2026-08-09.** Motor dentro do painel resolve
instalação e **cria dependência de um NLE só**. Os nossos casos atuais são multiplataforma e
multi-app (**Premiere + Resolve + Media Composer**), e é justamente o painel fino que deixa os três
compartilharem o mesmo motor — no Avid não existe Node, e o painel
([`../avid-panel-sdk/`](../avid-panel-sdk/)) é QtWebEngine que **não lê disco**. Para o Órbita,
trocar motor externo por motor embarcado seria pagar portabilidade por conveniência de instalação.
**O achado fica guardado para quando houver produto deliberadamente só-para-Premiere** — aí plugin
standalone (painel + motor, uma instalação) passa a ser opção real. É o modelo que o Premiere
Copilot **e** o Eddie escolheram, e note que os dois são efetivamente mono-NLE na prática (o Eddie
duplica a integração inteira para o Resolve por outro caminho, e ignora o Avid).

## Segurança — este é o caso mais grave que já anotamos

O painel executa **~2 MB de JavaScript remoto** a cada abertura, dentro de um CEP com
`--enable-nodejs`, `--allow-file-access` e `--allow-file-access-from-files`, e o manifesto
**não declara `<RequiredPermissions>`** — nenhuma restrição de domínio. Compare: o `Chat Video Pro`,
na mesma máquina, declara `<Permission>https://*.vercel.app</Permission>`.

Quem controlar `api.premierecopilot.com` executa código com o usuário do editor, com acesso a
disco e a `child_process`, em cima de todo material do projeto. Não é vulnerabilidade deles ser
descoberta: **é o mecanismo de entrega do produto**. Para material sob embargo, isso é o item a
levar ao contrato — mais do que "sobe áudio para a nuvem".

Do lado bom: **nenhuma credencial em claro** no bundle (nem fal.ai, nem elevenlabs, nem LLM) — tudo
atrás da API própria. Isso está certo, e é o contraste com os webhooks Slack hardcoded do Eddie.

## O que NÃO foi feito

- Nada instalado (o `.pkg` foi extraído com `xar` + `cpio`, sem `installer`), nada executado, nenhuma
  conta criada, nenhum `.exe` do Windows aberto.
- **Nenhuma lógica descompilada.** O bundle remoto de 2 MB foi lido **só por `grep` dirigido**:
  hosts, rotas `/api/`, portas, nomes de modelo, `child_process`, busca por credencial. Não foram
  lidos os corpos de função, nem o `.pyc` do backend Python — deste saiu só a **lista de pacotes**
  do `_internal`.
- O bundle foi baixado do endpoint público sem autenticação; **nada foi enviado** (só `GET`).
- `child_process` funcionando sob o sandbox: **não medido**.
- Rotas da API além de `/api/subtitles-pro/*`: `pendente` (montadas por template).

## Ver também

- [eddie-ai-arquitetura.md](eddie-ai-arquitetura.md) — o caso oposto: lógica no painel, motor fora
- [README](README.md) — nossa arquitetura (e a afirmação sobre `child_process` a revisar)
- [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md) — a técnica
