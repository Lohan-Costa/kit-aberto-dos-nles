# Analisar o executável do concorrente

Técnica de engenharia reversa **de aplicativo**, não de formato de arquivo. Estreou em
2026-08-08/09 (Jumper e Quickture) e rendeu mais do que meses relendo a própria
documentação — por isso virou tema deste banco. Fatos consumíveis em
[analise-de-executaveis.json](analise-de-executaveis.json).

## Por que isto vale

**Documentação de concorrente é escassa e enviesada; o binário é fonte primária.** O
Quickture não tem documentação técnica nenhuma — nem `llms.txt`, nem OpenAPI, nem
página de developers. Ainda assim, em uma sessão saiu a arquitetura inteira: stack,
rotas de nuvem, o que sobe da máquina do cliente e em que resolução.

E há um caso especial que muda o jogo: **quando o concorrente é parceiro oficial de uma
plataforma cujo SDK é fechado para nós, o produto dele é a documentação que falta.** O
Panel SDK do Media Composer não tem download público e a Avid não aceita novos
parceiros. O painel do Jumper carrega o protobuf `mcapi` compilado do `.proto`
**oficial** — foi ele que confirmou que a nossa reconstrução por reflection estava
completa (faltava 1 símbolo em 262), e foi o manifesto dele que revelou que o `url` do
`uiItem` aceita HTTP absoluto, fato que destravou o painel do Órbita depois de meses
parecendo limite da plataforma.

## A ordem de ataque (do mais barato ao mais caro)

Nunca comece pelo binário. Cada degrau só se paga quando o anterior secou.

1. **`llms.txt`** no domínio de documentação. Se existir, é o índice de tudo em markdown
   cru — foi assim que as ~99 páginas do Jumper apareceram de uma vez.
2. **OpenAPI / spec**. `api-reference/openapi.json` e afins. Schemas de request/response
   revelam decisões de arquitetura que a prosa não conta.
3. **Política de privacidade**. Software puramente local não precisa de Data Privacy
   Framework nem de transferência internacional. Foi o primeiro sinal de que o Quickture
   era cloud, antes de qualquer download.
4. **Tamanho do instalador.** 6 MB não carrega modelo de ML; 5 GB carrega. O contraste
   entre Jumper (4–5 GB) e Quickture (6–180 MB) contou a história antes de abrir.
5. **Extrair o instalador sem instalar** (receitas abaixo).
6. **Metadados primeiro**: manifestos, `config.json`, licenças, `.dist-info`. Baratos e
   muito reveladores.
7. **Nomes de símbolo/módulo**: arquitetura sem tocar em lógica.
8. **Strings dirigidas**: endpoints, portas, argumentos de linha de comando.
9. **Pare aqui.** Ver §A régua.

## Receitas de extração

Todas **sem instalar** e sem executar nada. Detalhe em
[analise-de-executaveis.json](analise-de-executaveis.json).

| Pacote | Como abrir |
|---|---|
| `.dmg` | `yes \| hdiutil attach X.dmg -nobrowse -readonly -noverify` · `hdiutil detach /Volumes/…` no fim. O `yes` responde ao EULA, que trava a montagem calado. |
| `.pkg` | `xar -xf X.pkg` → `cat Payload \| gunzip -dc \| cpio -i` |
| `.zxp` `.avpi` `.appex` `.asar` | são ZIP: `unzip` |
| `.msi` + `.cab` | `unzip` do wrapper, depois `cabextract -d out X.cab` |
| PyInstaller | cookie `MEI\014\013\012\013\016` no fim do executável → TOC → `PYZ-00.pyz`; `marshal.loads` do TOC do PYZ dá a **lista de módulos** |
| Rust | `strings \| grep -oE "cargo/registry/src/[^/]+/[a-z0-9_-]+-[0-9.]+"` → a árvore de dependências **exata, com versão** |
| PE sem nome (MSI renomeia para hash) | `strings` → nome do `.pdb` e export name identificam a DLL |
| Source map | ler **só** o array `sources` (caminhos), nunca `sourcesContent` |

## Onde o rendimento se concentra

Sinais que custam segundos e entregam muito:

- **`model_licenses/` ou `LICENSE_*.txt`** — identificam os AUTORES dos modelos de ML.
  `LICENSE_IGLOVIKOV` entregou o RetinaFace; `ATTRIBUTION_NVIDIA` entregou o Parakeet.
- **`config.json` de modelo (HuggingFace/timm)** — `architectures`, `timm_model_name`,
  `hf_tokenizer_name`, `embed_dim`. É a arquitetura declarada, não inferida.
- **`cargo/registry`** — dependências Rust com versão. As crates de domínio (`avb`,
  `cfb`, `symphonia`) dizem o que o app sabe fazer.
- **Manifesto de plugin** (`avid-manifest.json`, `CSXS/manifest.xml`) — revela os
  **limites da plataforma** e o que é possível pedir a ela. O campo `usesApi`, o
  `allowedDomains` e o `url` do `uiItem` valem mais que páginas de doc.
- **Ausência também informa.** Nenhuma lib de vector DB no bundle do Jumper provou que a
  busca é força bruta em RAM. Nenhuma crate de ML no Quickture provou que a inferência é
  remota.

## ⚠️ A régua — onde parar, e por quê

> ⭐ **REVISADA em 2026-08-24, por decisão do autor.** A versão anterior proibia ler lógica.
> O texto antigo está preservado ao fim desta seção, porque metade do banco foi escrita sob
> ele e citá-lo explica por que certas entradas são mais rasas do que poderiam ser.

**Leia tudo. Escreva mecanismo, não código.**

Ler 100% de qualquer artefato é permitido — lógica, algoritmo, fluxo de controle — quando o
objetivo é **entender como um problema foi resolvido**. O que muda é o **registro**: o banco
anota *o mecanismo e o porquê* — a forma da solução, as armadilhas, os limites, o custo —
nunca trechos transcritos.

⭐ **O teste prático:** se um achado só se explica colando o código do outro, ele foi
entendido mal. Descrever *"alinham pela interseção das janelas de TC e aparam cabeça e
cauda"* é entendimento; colar a aritmética é cópia, e é pior, porque não ensina nada.

### Continua fora de escopo, sempre

- **Contornar licenciamento ou trial.** Ler como um produto licencia é arquitetura; **quebrar**
  o licenciamento não é. Na prática: pule as funções de licença — elas não respondem pergunta
  nenhuma sobre o NLE.
- Extrair pesos de modelo proprietário.
- **Redistribuir** qualquer coisa extraída.

### O que NÃO mudou, e é o que fazia a regra valer

⭐⭐ **Toda análise continua obrigada a registrar "o que NÃO foi feito"**, com a mesma clareza
do que foi. Isso nunca foi uma restrição — é o que permite reler o material meses depois e
**saber em que confiar**. Uma entrada sem essa seção é uma entrada que ninguém consegue
calibrar.

E os **níveis de confiança** (`confirmado` / `inferido` / `hipotese` / `pendente`) continuam
obrigatórios por afirmação, não por documento.

### ⚠️ Duas consequências de ler mais fundo

1. **O que se lê aqui pode sair daqui.** O banco é interno, mas as conclusões viram ADR em
   `docs/adr/`, que é **público**. Ler pode ser 100%; **escrever num ADR é publicar**.
2. ⭐ **Contaminação é o risco real, não o legal.** Seis meses depois ninguém lembra se aquela
   cascata de fallback foi ideia nossa ou lida num bundle. Registrar **mecanismo** em vez de
   código é o que mantém a fronteira legível para o nosso próprio eu futuro.

### O texto anterior (vigente até 2026-08-24)

> *"Ler configuração, manifesto, licença, nome de símbolo e endpoint é entender arquitetura.
> Descompilar lógica é copiar implementação."*
>
> Consequências que ele produziu, e que hoje são **dívida de leitura**, não decisão:
> - O `scene_detection` do Jumper ficou como "existe, com este nome"; a lógica, `pendente`.
> - O clustering facial do Jumper ficou `inferido`, mesmo sendo descompilável.
> - **O source map do Quickture continha o TypeScript original completo**; foi lida apenas a
>   lista de 243 caminhos de arquivo. ⭐ Sob a régua nova este é **o artefato não lido mais
>   rico que o banco possui** — arquitetura de produto em código legível, sem desofuscação.

## Higiene operacional

- Montar `-readonly`, **desmontar ao terminar**, conferir `/Volumes`.
- Nada instalado, nenhum binário executado, nenhuma conta criada.
- **Apagar os temporários** — a extração dos CABs do Quickture gerou 10 GB.
- **Registrar o que NÃO foi feito**, com a mesma clareza do que foi. É isso que permite
  reler o material meses depois e saber em que confiar.

## Calibração — o que a técnica acerta e o que erra

Placar real da primeira sessão (inferências feitas só de documentação, depois conferidas
contra o binário): **6 certas, 4 erradas, 3 parciais**.

| Acerta | Erra |
|---|---|
| Arquitetura de sistema (há índice? é local? usa VLM?) | **Escolha de componente** — "é InsightFace" era ArcFace-shaped e estava errado; é RetinaFace + LVFace |
| Ordem de grandeza (tamanhos, throughput) | **Ausência** — "não há detecção de cena" era falso; existia um módulo inteiro. A doc não lista o que ela não menciona |
| Padrões de produto (o agente recebe metadado, não mídia) | Contagem de parâmetros por tamanho de disco, quando há quantização misturada |

### ⭐⭐ O eixo **AUSÊNCIA** falhou pela quinta vez — e agora sabemos por quê

A coluna da direita tem um padrão: quase toda inferência errada é uma **conclusão de que algo
não existe**. Vale a pena listar as cinco, porque juntas dizem uma coisa só:

| # | conclusão errada | o que era |
|---|---|---|
| 1 | "não há detecção de cena" (Jumper) | havia um módulo inteiro |
| 2 | "um modelo no disco ⇒ a feature existe" (Jumper) | as skills dizem que não há timing por palavra |
| 3 | "um SDK no bundle ⇒ o agente roda local" (Eddie) | era instrumentação do Sentry |
| 4 | "o arquivo do modelo existe ⇒ funciona" (Chat Video Pro) | `ggml-base.en.bin` tinha **313 bytes** |
| 5 | ⭐ **"não há drag MC → painel"** (Panel SDK do Avid) | **há — só não é rpc** |

O caso 5 é o mais instrutivo, porque a evidência era boa: enumerou-se `Drop*`/`Drag*` no binário
do Media Composer e só apareceram os três de saída. O erro não estava na busca, estava num
**pressuposto que ninguém escreveu**: *"se a capacidade existe, existe um símbolo para ela"*.

⭐ **A regra nova, e a mais transferível deste arquivo:**

> **Antes de concluir "não existe", escreva onde você procurou — e pergunte que outras
> superfícies a plataforma tem.**

Uma plataforma que hospeda uma **webview** tem, no mínimo, duas superfícies: a API dela e a do
**navegador**. Arrasto, área de transferência, `postMessage`, `fetch`, armazenamento local — nada
disso aparece em `strings` do executável hospedeiro, porque quem implementa é o Chromium. Foi
exatamente aí que o drag do Avid estava: `text/x.avid.mc-api-asset-list+json` entregue ao
`ondrop` do DOM, sem uma linha no manifesto e sem um símbolo no binário.

O mesmo raciocínio vale para as outras quatro: em todas, a busca foi feita numa superfície só
(inventário de arquivos, lista de dependências) e a resposta morava em outra (prompt de runtime,
tamanho do arquivo, tráfego). **Ausência só é fato dentro da superfície onde você procurou.**

⭐ **Lição que vale mais que o placar:** *prompt de runtime é fonte mais confiável que
inventário de arquivos*. O Jumper empacota um `qwen3-forced-aligner`, mas as skills dele
declaram "there are no word-level timestamps". **Um modelo no disco não é uma feature.**

## Quando repetir

- Um limite parece ser da plataforma e não do nosso código → **olhe como um concorrente
  com acesso oficial resolveu**. Foi o caso do painel do Avid.
- Precisamos saber o que um app manda para fora antes de aprovar seu uso com material
  sob embargo (o proxy 512×288 do Quickture não está em documentação nenhuma).
- Vamos escolher uma stack e alguém já resolveu o mesmo problema em produção — a lista
  de dependências é uma decisão de arquitetura revisada por quem apanhou antes.

## Ver também

- 🆕 ⭐⭐ [`ia-embarcada-nos-nles.md`](ia-embarcada-nos-nles.md) — **6º caso (2026-09-13): os próprios
  NLEs**, Premiere 26.0.2 e Resolve Studio 21.1, lidos no macOS com `otool -L`, `strings` e
  `xxd`. ⭐ Limite novo da técnica: **pesos criptografados** (CoreML `.mlem`, `.bin` FlatBuffers)
  não impedem identificar a técnica — o **identificador do pacote** (`ai/speech-recognition,2.0,
  large-v3-turbo`), as **mensagens de log** (`MediaSearcher::BetterMode`) e os **nomes de classe**
  (`MultiPeriodDiscriminatorV2` → RVC) deram a arquitetura sem tocar num peso. Confirma a régua:
  entender a técnica para escolher a alternativa aberta, nunca extrair o modelo.
- 🆕 ⭐⭐ `../plugins/avid-panel-sdk/esion-arquitetura.md` — **5º caso (2026-08-15): ESION Studio**,
  e o **2º painel do Media Composer**. O mais valioso até agora em relação custo/retorno: a
  análise **revogou um fato que este banco dava como `confirmado`** (§Calibração, caso 5) e
  entregou o mecanismo completo do drag bin→painel, que se procurava como se fosse um comando.
  Rendeu ainda uma **rota nova de instalar preset do Avid** (XML de setting única largado em
  `Avid Media Composer/Settings/`, em vez de editar o `Settings.xml` de 5 MB com o editor
  fechado) e o **fechamento em 100% do `mcapi.proto`** contra uma 2ª cópia oficial, de build mais
  novo que a do Jumper. ⭐ Receita de extração nova: **um `.dmg` se abre no Windows com o 7-Zip**,
  que enxerga o HFS aninhado sozinho — e quando o instalador `.exe` de Inno Setup não abre (o
  7-Zip não suporta o formato), **o instalador do outro sistema operacional costuma trazer os
  mesmos arquivos**, porque um painel é HTML/JS. Não force o pacote difícil: troque de pacote.
- `../plugins/avid-panel-sdk/paineis-de-terceiros.md` — o caso completo, com o que rendeu
  para o Panel SDK
- `../plugins/premiere-cep/chat-video-pro-arquitetura.md` — **4º caso (2026-08-09): Chat Video Pro**.
  ⚠️ **A calibração falhou pela TERCEIRA vez no mesmo eixo, e desta vez de graça:** o `whisper/` tem
  `ggml-base.en.bin` de **313 bytes** e `whisper.wasm` de **257** — arquivos de texto dizendo "baixe
  o modelo real" — ao lado de workers completos de 1–1,5 MB. Depois de "um modelo no disco não é uma
  feature" (Jumper) e "um SDK no bundle não é um agente" (Eddie), agora: **o arquivo do modelo pode
  ser um comentário**. ⭐ **Regra nova, custo dois `ls -la`: confira o TAMANHO do arquivo antes de
  concluir que a capacidade existe.** Rendeu também: quando a extensão traz `MAC_INSTALL.md` /
  `README.md` próprios, **leia — e depois desconfie**: este manda instalar ffmpeg pelo `brew` e diz
  que o embutido "pode vir numa versão futura", com o binário universal já na pasta. Doc atrasa em
  relação ao build, inclusive a interna.
- `../plugins/premiere-cep/premiere-copilot-arquitetura.md` — **3º caso (2026-08-09): Premiere
  Copilot**. Novo limite da técnica: **quando o app não está no disco, o inventário de arquivos não
  existe**. O painel tem 5 KB e baixa 2 MB de JS a cada abertura — a arquitetura só apareceu no
  `postinstall` (que revela as features pelas pastas que cria), nos presets `.epr` (que revelam o
  que sobe) e num `GET` no endpoint público do loader. Mostra também que **comparar a build
  instalada com o instalador novo captura uma virada de arquitetura em movimento** (backend Python
  de 345 MB em abril, removido em julho) — coisa que nenhuma das duas fotos isoladas mostraria.
- `../plugins/premiere-cep/eddie-ai-arquitetura.md` — **2º caso (2026-08-09): Eddie AI**. Confirma a
  calibração: a inferência óbvia ("`@anthropic-ai/sdk` nas deps ⇒ o agente roda na máquina") estava
  **errada** — era instrumentação do Sentry. *Um SDK no bundle não é um agente*, exatamente como
  *um modelo no disco não é uma feature*. Rendeu também duas receitas novas: **ler o cabeçalho do
  `app.asar`** (`base = 8 + uint32@4`, JSON em 16 com tamanho em `uint32@12` → árvore de arquivos e
  `package.json` sem extrair nada) e **buscar o config remoto** que o app monta no boot (URL
  previsível em bucket público entregou o endpoint real de produção, que o hardcoded não dava).
- `PROGRAMAS COM CLAUDE/EDT-ASSIST/pesquisa/` — as duas dissecações em detalhe
  (arquitetura de produto e camada de IA), com `fontes.md` registrando método e limites
