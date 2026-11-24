# Painel servido por HTTP, extensão invisível, e o que o Premiere diz da identidade de um item

> **Medido em 2026-09-17**, Premiere Pro **23.2.0 (build 69)**, Windows 11, CEP com Chromium
> **88.0.4324.150**. Instrumentos, os dois **sem ninguém na frente**:
> `_CICLO ASSIST/spikes/o_premiere_por_dentro.py` (+ a extensão `spikes/premiere_sonda/`),
> ~26 s, e `spikes/o_painel_no_premiere.py`, que sobe o serviço, instala uma variante
> invisível do painel de produto e exercita a ponte inteira.
> Tudo aqui é `confirmado` nessa versão; no macOS e noutras versões, `pendente`.

## 1. ⭐⭐ Extensão INVISÍVEL com arranque automático FUNCIONA — `confirmado`

```xml
<Lifecycle>
  <AutoVisible>false</AutoVisible>
  <StartOn>
    <Event>com.adobe.csxs.events.ApplicationActivate</Event>
    <Event>applicationActivate</Event>
  </StartOn>
</Lifecycle>
<UI><Type>Custom</Type> …</UI>
```

🆕 **macOS também (2026-10-06, Premiere 25.6.5):** a extensão invisível do laboratório (`laboratorio-de-midia/lab/bancadas/premiere/ponte-cep`, com Node: `--enable-nodejs` + `--mixed-context`) subiu sozinha ~60 s depois do `open -a`, sem janela, e serviu `evalScript` a noite inteira. `confirmado` no Mac.

Instalada na pasta de extensões e com o Premiere aberto por linha de comando, a página rodou
sozinha **em ~3 s**, sem janela, sem clique, com `__adobe_cep__` e `evalScript` vivos. Não se
sabe qual dos dois nomes de evento disparou (os dois estavam declarados).

- ⭐ Responde a pergunta aberta da ponte Órbita ↔ Ciclo Assist
  (`DRAMASYNC/.dev/PONTE-CICLO-ASSIST.md` §5a, saída "b"): **uma extensão invisível pode fazer
  o poll sem o painel do Órbita aberto.**
- ⭐ **E é um método de medição:** `app.newProject(caminho)` cria um projeto descartável sem
  diálogo, `app.project.importFiles(...)` importa, `app.project.closeDocument(0, 0)` +
  `app.quit()` fecham **sem perguntar nada** (o processo saiu sozinho). Uma sonda inteira
  roda sem o editor.
- ⛔ **Instalada, ela roda toda vez que o Premiere abre.** Instrumento assim tem de se
  desinstalar no `finally`.
- ⚠️ `app.project.path` **sem projeto aberto** lança `Error: Unknown error exception` — não
  devolve vazio.

## 2. ⭐⭐⭐ A página SERVIDA por HTTP tem `__adobe_cep__` — `confirmado`

O desenho do painel do Media Composer (`.avpi` só com um loader, a interface servida pelo
serviço local — ver `../avid-panel-sdk/`) **vale no CEP**:

| como a página chegou | `window.__adobe_cep__` | `evalScript("app.version")` |
|---|---|---|
| `file://…/index.html` da extensão | `object` | `23.2.0` |
| **a janela NAVEGOU** para `http://127.0.0.1:<porta>/pagina` | **`object`** | **`23.2.0`** |
| `<iframe src="http://127.0.0.1:<porta>/…">` dentro da página da extensão | **`object`** (o iframe tem o seu) | — |
| iframe lendo `parent.__adobe_cep__` | `undefined` (cross-origin) | via `postMessage`: `23.2.0` em **6,9 ms** |

⭐ Consequência: a extensão pode ser **só um loader** que navega para o serviço; a interface e o
ExtendScript chegam dele, e atualizar a interface não exige reinstalar a extensão. O `jsx` do
`ScriptPath` continua vindo do disco da extensão.

### Os cabeçalhos que o serviço recebe — `confirmado`

| quem pede | `Origin` | `Sec-Fetch-Site` |
|---|---|---|
| página `file://` da extensão (`fetch`) | **`file://`** | `cross-site` |
| navegação da janela para o serviço | — | `cross-site` (`Sec-Fetch-Mode: navigate`) |
| **página servida**, `GET` same-origin | **nenhum** | **`same-origin`** |
| página servida, `POST` same-origin | `http://127.0.0.1:<porta>` | `same-origin` |

⭐ É **exatamente o quadro do QtWebEngine do Media Composer**, trocando `avpi://` por `file://`:
o porteiro por `Sec-Fetch-Site: same-origin` serve sem mudança, e um `GET` same-origin continua
**sem `Origin`** (a armadilha do `avid-panel-sdk`: quem apostar no `Origin` vê os GETs caírem).
⚠️ Todo `fetch` da página `file://` com corpo JSON passa por **preflight `OPTIONS`**.

## 3. ⭐ A ida e volta serviço → painel → ExtendScript → serviço: **2,5–4,9 ms** — `confirmado`

Long-poll (`GET /pedido` segura até haver pedido) → `evalScript` → `POST /resposta`. Dez
voltas, alternando `app.version` e uma leitura de seleção + contagem da bin: **2,5 a 4,9 ms**
cada, medidos do lado do serviço. Compare com o piso de **~500 ms** por chamada da API gRPC do
Media Composer (`../avid-panel-sdk/`): no Premiere a ponte não é o gargalo.

## 4. ⭐⭐ Proxy, OP-Atom e timecode: o que o item diz — `confirmado`

### Proxy anexado

| | antes de `attachProxy` | depois |
|---|---|---|
| `getMediaPath()` | o original | **o original (não muda)** |
| `hasProxy()` | `false` | `true` |
| `getProxyPath()` | `""` | o caminho do proxy |
| `canProxy()` | `true` (vídeo) · **`false` em áudio puro** (WAV, OP-Atom de som) | |

`attachProxy(caminho, 0)` devolveu `true` com um proxy H.264 640 px de mesmo TC e mesmos 4
canais. ⭐ **Quem identifica a mídia pelo `getMediaPath()` vê sempre o original**, com ou sem
proxy: o proxy anexado não atrapalha a identidade. ⚠️ Proxy IMPORTADO como mídia principal
(sem `attachProxy`) é outra coisa — aí o `getMediaPath()` é o proxy.

### 🆕 O que o `attachProxy` recusa e o que ele ACEITA calado — `confirmado` (25.6.5, macOS, 2026-11-07)

Medido com 11 pares (proxies ProRes Proxy do Resolve 21.1; Ciclo Assist, plano
`docs/plano/2026-11-07-premiere-proxy-e-merged.md` §P0), ~15 ms por chamada:

| par | `attachProxy` |
|---|---|
| original 4 canais, proxy 2 canais | **`false`**, sem motivo |
| WAV (`canProxy()` = `false`) | **`false`** |
| ⛔ DCI 4096×2160 com proxy 1920×1080 *letterbox* (outra proporção) | **`true`** — aceito calado |
| ⛔ **outro material**: mesmos 2 canais, outra duração (192 × 312 quadros) e outro TC | **`true`** — aceito calado |
| estéreo (1 pista de 2 canais) com proxy em 2 pistas mono | `true` |
| mp4 H.264/AAC com proxy mov ProRes/PCM | `true` |
| DCI 4096×2160 → 2048×1080 · UHD → 1920×1080 · BRAW 4096×2160 → 2048×1080 | `true` |

⇒ ⛔⛔ **O Premiere só confere o NÚMERO DE CANAIS.** Proporção, duração, TC e identidade do
material são de quem anexa — conferir o par (taxa, TC, nº de quadros, proporção) ANTES.
- Anexar de novo TROCA o proxy; `getMediaPath()` continua o original em todos.
- ✅ O botão liga mesmo: `app.setEnableProxies(0|1)` / `app.getEnableProxies()` existem, e o
  `exportFramePNG` do QE respeita (proxy em negativo: desligado = original, ligado = negativo).
- ✅ **BRAW no Premiere do Mac** (importador da Blackmagic instalado): importa, `canProxy()` `true`,
  proxy 2048×1080 anexado; o quadro com o proxy é o mesmo enquadramento e o mesmo log.
- ⛔ **Merged clip NÃO usa o proxy do clipe da bin** — ver `subclipe-e-merged-clip.md` §3c.

### OP-Atom da `Avid MediaFiles` importado direto

- **Cada arquivo vira um item SEPARADO** — `V01…mxf` e `A01…mxf` do mesmo master entraram como
  dois itens com o **mesmo nome** (`20240531_PANA2774.new.01`, o `material_package_name`). O
  Premiere **não** remonta o master a partir dos OP-Atom.
- `getMediaPath()` = o arquivo OP-Atom (`…\PRODE\V01.E69CCE70_….mxf`).
- `Column.Intrinsic.TapeName` = o `reel_name` do MXF (`20240531_PANA2774`).

### Timecode e duração

- `item.startTime()` = o TC de início **em ticks** (`254016000000` por segundo): `23:16:47:11`
  ↔ `21309723771336000`. Igual para o original e para o OP-Atom convertido dele.
- `getProjectMetadata()` traz `Column.Intrinsic.MediaStart` (`23:16:47:11`),
  `MediaDuration`, `FilePath`, `VideoInfo`, `TapeName`.
- ⚠️ Em áudio puro, `MediaDuration` vem em **amostras** depois dos segundos
  (`00:03:23:40614`) e `getFootageInterpretation().frameRate` sai `2.754e-8` — não é quadro.
- `xmpDM:timeValue` do XMP repete o TC nos arquivos que o têm (MOV, MP4, WAV), mas vem
  **vazio nos MXF** — use `startTime()` ou `MediaStart`.

### Subclipe

`createSubClip(nome, "2s em ticks", "5s em ticks", 0, 1, 1)` criou o item; o subclipe tem o
**mesmo `getMediaPath()`** e herda o proxy. ⚠️ **`getInPoint()`/`getOutPoint()` do subclipe
devolveram 0 e 51,55 s — o master inteiro, não os 2–5 s pedidos** (com
`hasHardBoundaries = 0`). ⭐ **Onde o recorte mora está no §7.**

## 5. ⛔⛔ Dois hifens num COMENTÁRIO do manifesto matam a extensão, em silêncio — `confirmado`

Medido em 2026-09-17, no 23.2. Um comentário do `manifest.xml` explicava por que o painel
**não** usa `--enable-nodejs`. XML não permite `--` dentro de comentário, e o resultado é:

- a extensão **não aparece**, nem no menu nem no arranque automático;
- **nenhum erro na tela**, nenhum arquivo a mais, nada no painel de extensões;
- o motivo só aparece em **`%TEMP%\CEP11-PPRO.log`** (`LogLevel` ligado na chave
  `HKCU\Software\Adobe\CSXS.<N>`):
  `ERROR XPATH Comment must not contain '--' (double-hyphen)`.

⭐ **O sintoma é idêntico ao de "o PlayerDebugMode não está ligado"** — e as duas conferências
que a gente faz (pasta certa? debug mode ligado?) passam. Um `ET.parse()` no manifesto, num
teste, custa quatro linhas.

## 6. ⭐ O `__adobe_cep__` NÃO depende do Node — `confirmado`

O manifesto do Ciclo Assist não declara `--enable-nodejs` nem os `--allow-file-access`, e a
página `file://` carregou, fez `fetch` para `http://127.0.0.1` em `mode: "no-cors"`, navegou
para o serviço e, na página servida, continuou com `__adobe_cep__` e `evalScript` vivos.

⭐ **Vale a decisão de segurança:** a página servida renderiza texto que o modelo escreveu;
com Node nela, uma falha de renderização viraria um shell na estação do editor.

## 7. ⭐⭐ O recorte de um SUBCLIPE mora nos METADADOS DO PROJETO — `confirmado`

O §4 deixou a pergunta em aberto (`getInPoint/getOutPoint` devolvem o master inteiro). A
resposta, medida com `createSubClip(nome, 2 s, 5 s, hard, 1, 1)` nos dois modos:

```
Column.Intrinsic.MediaStart      23:16:47:11   (o do ARQUIVO; com hard boundaries vira o do subclipe)
Column.Intrinsic.SubclipStart    23:16:49:10
Column.Intrinsic.SubclipEnd      23:16:52:10
Column.Intrinsic.SubclipDuration 00:00:02:23   (71 quadros)
```

- **início no arquivo = `SubclipStart` − TC do arquivo** (47 quadros): a base é o TC do
  ARQUIVO, nunca o `MediaStart`, que muda com hard boundaries.
- ⚠️ **O Premiere arredonda para BAIXO**: 2 s a 23,976 são 47,95 quadros → 47.
- `getInPoint()/getOutPoint()`, com ou sem argumento de tipo de mídia (1 a 4), devolvem o
  clipe inteiro no subclipe SOFT; no HARD devolvem 0 → duração do subclipe.
- ⭐ E `VideoInPoint`/`VideoOutPoint` trazem `offset` em TICKS (o `startTime` do item), o que
  dá o mesmo número sem passar por timecode: no hard, `offset` é o do master + 2 s exatos.
- ⚠️ **`createSubClip` cria o subclipe na RAIZ do projeto**, não na bin do clipe original.

## 7b. O item importado se chama como o ARQUIVO, com a extensão — `confirmado`

> **Medido em 2026-09-22**, Premiere Pro **23.2**, Windows 11, por
> `_CICLO ASSIST/spikes/vetores_no_premiere.py` (sem ninguém na frente).

`app.project.importFiles([...], true, bin, false)` com um `.mp4`, um `.wav` e um `.mp4`
gerado pelo ffmpeg: **3 de 3** itens nasceram com `name` = nome do arquivo **com a extensão**
(`A001_03170214_C001.mp4`, `10 Car Interior B.wav`, `GERADO_AGORA.mp4`). O nome do master
do Avid para o mesmo material não tem extensão (`A001_03170214_C001`).

- ⚠️ Quem compara nome de item do Premiere com nome de clipe de outro NLE (ou com o `stem`
  do arquivo) precisa tirar a extensão antes — ou vai achar que são materiais diferentes.
- ⚠️ E quem batiza coisas com o nome do item (pasta de cache, rótulo) herda a extensão.
- Não medido: item renomeado pelo editor (aí o `name` é o dele), e o macOS.

## 7c. 🆕 Premiere 23.6 (Windows): a ponte do De Lá Pra Cá — `confirmado` (2026-10-19)

> Premiere Pro **23.6.0 (build 65)**, Windows 11, CSXS.11. Produto: `_DeLaPraCa/plugins/premiere/cep/` (extensão
> invisível, só o loader) + `servico/premiere_ponte.py` (a fila do Ciclo Assist) + a página `/premiere/ponte`.

- A extensão invisível (§1) sobe no 23.6 do mesmo jeito: com o Premiere aberto pelo executável, a página estava de
  pé em **~3 s** (lida pela depuração remota) e navegou para o serviço; o `evalScript("app.version")` deu `23.6.0`.
- ⛔⛔ **A página servida obedece à CSP do SERVIDOR.** O serviço manda `Content-Security-Policy: default-src 'self'`
  (sem `'unsafe-inline'` em `script-src`): o `<script>` EMBUTIDO na página da ponte foi recusado **em silêncio** — a
  página carregou, `__adobe_cep__` presente, nenhuma função dela definida, nenhuma batida no serviço. O sintoma é
  igual ao de "a extensão não subiu". Script em ARQUIVO próprio (`<script src="/premiere/ponte.js">`) resolve sem
  afrouxar a política. Vale para qualquer app da família que sirva a página do CEP com CSP.
- `app.openDocument(caminho)` pela ponte abriu uma CÓPIA de projeto do 23.2 (`Project Version="41"`) no 23.6 em
  **~3 s, sem diálogo**; `app.project.sequences` e `activeSequence` lidos logo depois. Na tela inicial,
  `app.project.path` lança (§1): a leitura do estado protege com `try`.
- 🔧 **Método — ver por dentro da extensão invisível:** um arquivo `.debug` na pasta da extensão instalada
  (`<ExtensionList><Extension Id="…"><HostList><Host Name="PPRO" Port="8092"/>…`) abre a depuração remota no
  arranque; `GET http://127.0.0.1:8092/json` diz em que página ela está, e o `Runtime.evaluate` do protocolo de
  depuração roda código nela (o Node 22+ da máquina tem `WebSocket` global: 15 linhas, sem dependência). ⛔ É uma
  porta que controla o Premiere: só na cópia instalada, e apagar depois. Log do CEP: `LogLevel` = `6` na chave
  `HKCU\Software\Adobe\CSXS.11` → `%TEMP%\CEP11-PPRO.log` e `%TEMP%\CEPHtmlEngine11-PPRO-<versão>-<id>.log`.

## 8. O que não foi medido

- macOS (as duas sondas rodam lá: o script precisa do caminho do Premiere e da pasta de
  extensões do Mac);
- qual dos dois eventos de `StartOn` disparou;
- merged clip (a API não cria um — `subclipe-e-merged-clip.md`): a LEITURA de um merged
  pelas trilhas da sequência interna está escrita no Ciclo Assist e ainda não foi exercitada
  contra um merged de verdade;
- o painel do PRODUTO (`Type=Panel`, aberto pelo menu) — o que foi exercitado sem ninguém na
  frente é a variante invisível do mesmo loader e da mesma página.
