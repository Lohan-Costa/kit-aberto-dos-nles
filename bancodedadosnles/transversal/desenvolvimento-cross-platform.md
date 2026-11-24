# Desenvolver o MESMO projeto em macOS e Windows — armadilhas medidas

> ⭐⭐⭐ **Para CONSULTAR, use a [matriz de plataforma](matriz-de-plataforma.md)** — uma linha por
> variável, os dois lados, e as regras. Esta página é a NARRATIVA das sessões (o porquê e como
> cada armadilha apareceu); fato novo de plataforma entra lá, e a história dele, aqui.

> **De onde isto veio:** uma sessão de 2026-08-15 levando um app Tauri + React + sidecar Python
> (o Órbita) de macOS para Windows, com o projeto vivendo num **SSD externo exFAT** que troca de
> máquina. Nenhuma das armadilhas abaixo é hipotética: todas custaram tempo real, e **quase todas
> se manifestaram como "travou" ou "não aparece nada", nunca como erro**.
>
> ⭐ **A lição que atravessa todas elas:** o modo de falha caro no cross-platform não é o erro —
> é o **silêncio**. Um caminho que não existe, um timeout que sempre cai no fallback, um
> executável do SO errado: nada disso levanta exceção. O código segue em frente e o sintoma
> aparece longe da causa. Por isso a regra que fecha este arquivo (§6) é *checar se FUNCIONA, não
> se EXISTE*.

---

## 1. ⭐ `localhost` no Windows pode custar SEGUNDOS por requisição — `confirmado`

**O caso mais caro da sessão**, e o mais transferível: um servidor de desenvolvimento (Vite) que
subia normalmente, e uma janela de app que ficava **em branco por mais de 5 minutos** antes da
interface aparecer. Nada falhava. Nada logava.

### O mecanismo

1. O Node moderno resolve `localhost` para **`::1` (IPv6)** ao **escutar**. Um servidor
   configurado com "host: localhost" (ou o default de vários frameworks) acaba escutando **só em
   IPv6**.
2. O cliente (aqui, o WebView2) pede `http://localhost:<porta>` e o Windows tenta **IPv4
   primeiro**.
3. Não há ninguém em `127.0.0.1`. E — este é o detalhe que multiplica o custo — a máquina
   **DESCARTA o pacote em vez de recusá-lo**. Recusa é instantânea; descarte é **timeout**.
4. Só depois do timeout o cliente cai para o IPv6 e é atendido.

### Os números (mesma URL, mesmo servidor, mesmo cache quente)

| endereço pedido | tempo por requisição |
|---|---|
| `http://[::1]:1420/@vite/client` | **0,012 – 0,18 s** |
| `http://127.0.0.1:1420/@vite/client` (ninguém escutando) | **2,03 s** (timeout fixo) |
| `http://localhost:1420/@vite/client` | **2,98 → 5,03 → 15,7 s** (piorando a cada tentativa) |

Um app em modo dev carrega **dezenas de módulos** (58 no caso medido). `58 × 3–15 s` = os tais
cinco minutos. Depois de fixar IPv4 dos dois lados: **0,198 – 0,263 s** por módulo.

### Por que só aparece no Windows

No macOS o IPv4 é **recusado na hora** (sem timeout), então o fallback para IPv6 é instantâneo e
o problema é invisível. É um bug que **não existe** na máquina de quem desenvolveu.

### A correção

**Fixar a família dos dois lados, explicitamente.** Não basta corrigir um:

```ts
// servidor (ex.: vite.config.ts)
server: { host: "127.0.0.1", port: 1420 }
```
```jsonc
// cliente (ex.: tauri.conf.json)
"devUrl": "http://127.0.0.1:1420"
```

⚠️ Mudar um sem o outro traz o problema de volta — invertido (agora o cliente tenta IPv6 e não
há ninguém lá).

**Regra geral:** em IPC local (dev server, sidecar, painel de plugin falando com app), **use
literal de IP, nunca o nome `localhost`**. Se o serviço-alvo escuta em IPv6 (é o caso do
`avid-api-gateway`, ver
[plugins/avid-panel-sdk/windows.md](../plugins/avid-panel-sdk/windows.md)), use `[::1]`
explicitamente. O nome é o que introduz a ambiguidade.

### Como diagnosticar em 30 segundos

```powershell
Get-NetTCPConnection -LocalPort <porta> -State Listen | Select LocalAddress,LocalPort
```
`LocalAddress` sozinho já responde. E compare os três endereços com `curl -w "%{time_total}"` —
se `[::1]` voa e `localhost` arrasta, é isto.

---

## 2. `node_modules` NÃO atravessa sistema operacional — `confirmado`

Num disco compartilhado, `node_modules/` copiado do macOS **existe** no Windows e está **errado**:
os pacotes com binário nativo vêm só para a plataforma que instalou.

**Sintoma:** `Error: Cannot find native binding` / `Cannot find module '@<pkg>/cli-win32-x64-msvc'`.
É o [npm/cli#4828](https://github.com/npm/cli/issues/4828) — o npm **não** baixa a dependência
opcional que faltou depois; ele considera a árvore satisfeita.

**Correção:** apagar `node_modules/` e reinstalar. Use `npm ci` (determinístico, respeita o
lockfile) em vez de `npm install`.

⚠️ **A checagem de "já está instalado" não pode ser `if (exists node_modules)`** — a pasta existe.
Tem de olhar o **pacote nativo da plataforma atual**:

```bat
if not exist "node_modules\@scope\pkg-win32-x64-msvc\" ( rmdir /s /q node_modules & npm ci )
```

Mesmo raciocínio vale para qualquer artefato compilado que viaje no disco: `target/` do Rust,
`.venv/` do Python, binários de sidecar.

---

## 3. venv do Python compartilhado entre os dois SOs — ⚠️ **CORRIGIDO em 2026-08-15**

> ⚠️⚠️ **CORREÇÃO DE UM FATO ANTES REGISTRADO COMO `confirmado`.** Esta seção dizia que um
> mesmo `.venv` carrega os dois mundos lado a lado, "porque o exFAT distingue maiúsculas e os
> nomes não colidem". **Não é o que se mede a partir do Windows.** A camada Win32 é
> **insensível à caixa**, e a distinção do sistema de arquivos não a atravessa:
>
> ```powershell
> Test-Path .venv\lib   # True
> Test-Path .venv\Lib   # True   ← a MESMA pasta
> ```
>
> Ou seja: `Lib` e `lib` (e `Scripts` e... não, `bin`≠`Scripts`) são o mesmo diretório para
> qualquer ferramenta rodando no Windows, e um `python -m venv` no `.venv` compartilhado
> **escreve o `site-packages` do Windows dentro da árvore do macOS**. O que a redação antiga
> observou provavelmente foi o *macOS* enxergando as duas árvores — o lado que de fato
> distingue.
>
> ⭐ **A lição de método é a mesma de §6, aplicada a este próprio arquivo:** "os nomes não
> colidem" foi **inferido do sistema de arquivos**, não **medido no SO que ia usar**. Uma
> propriedade do FS não é uma propriedade da API que fala com ele.
>
> **Recomendação nova: um venv POR SISTEMA OPERACIONAL** (`.venv` + `.venv-win`), com o
> segundo no `.gitignore`. Custa ~1 GB de disco duplicado e elimina a classe inteira de
> problema — inclusive o do `pyvenv.cfg`, descrito abaixo, que passa a não existir.

O texto original, mantido porque a armadilha do `pyvenv.cfg` continua real para quem insistir
no venv único (e porque o macOS de fato vê as duas árvores):

Num sistema de arquivos que distingue maiúsculas, um mesmo `.venv` *parece* carregar os dois
mundos lado a lado:

```
.venv/Scripts/  +  .venv/Lib/          ← Windows
.venv/bin/      +  .venv/lib/          ← macOS
```

⚠️ **Mas o `pyvenv.cfg` é UM SÓ.** Ele guarda o interpretador de quem rodou `python -m venv` por
**último**. Se foi o macOS, o `Scripts\python.exe` do Windows **continua existindo no disco** e
falha ao rodar:

```
No Python at '/opt/homebrew/opt/python@3.11/bin\python.exe'
```

**Correção:** recriar só o lado do SO atual — `py -3.x -m venv <caminho>` sobrescreve o
`pyvenv.cfg` e repovoa `Scripts/`, **sem tocar** em `bin/`+`lib/`, que têm nomes diferentes.

⚠️ **Confira a VERSÃO antes de recriar:** os pacotes já instalados em `Lib/site-packages` têm
extensões C compiladas para uma versão específica (`*.cp312-win_amd64.pyd`). Recriar com 3.11
quando os wheels são cp312 dá `ModuleNotFoundError: numpy._core._multiarray_umath` — a pasta está
cheia, e nada importa.

---

## 4. `pip install --upgrade pip` falha no Windows e deixa lixo — `confirmado`

O pip não consegue substituir os próprios arquivos **enquanto está rodando**:

```
ERROR: Could not install packages due to an OSError:
[WinError 145] The directory is not empty: '...\\site-packages\\pip-XX.dist-info\\licenses\\src'
```

E deixa para trás uma pasta `~ip-XX.dist-info` que, a partir dali, faz **toda** chamada futura de
pip imprimir `WARNING: Ignoring invalid distribution ~ip` — inclusive as que funcionam.

**Correção:** tirar o `--upgrade pip` dos scripts de setup. Não é necessário para instalar as
dependências do projeto, e a fragilidade é conhecida do pip no Windows. Se já aconteceu, apagar a
pasta `~ip-*.dist-info` limpa o aviso.

---

## 5. Armadilhas menores, todas silenciosas — `confirmado`

| armadilha | o que acontece | correção |
|---|---|---|
| **Subprocesso pisca console** | Todo `Command`/`subprocess` no Windows abre uma janela preta. Num laço de polling, pisca sem parar. | Flag `CREATE_NO_WINDOW` (`0x08000000`) na criação do processo. |
| **Teste crava separador POSIX** | `assert caminho == "a/b"` falha no Windows contra `os.path`/`Path`, que devolvem `a\b`. **O código de produção estava certo; o teste é que assumia POSIX.** | Comparar com `os.path.join(...)` / `str(Path(...))`, nunca com string crua. |
| **`file:` URI com letra de unidade** | `assert uri.startswith("file:/")` falha: no Windows o caminho absoluto começa pela letra (`file:D:\...`). | Verificar só `startswith("file:")`. **Medido:** o ffmpeg lê `file:D:\...\-report.mov` normalmente — ele separa protocolo no PRIMEIRO `:`, então a letra de unidade não confunde o parser. |
| **Dependência "de tabela"** | Um pacote que o código importa mas que **não está** no `requirements.txt`, e que só existia na máquina original por efeito colateral de outra instalação. Funciona por anos e quebra no primeiro ambiente limpo. | Criar o ambiente **do zero** periodicamente — é o único jeito de descobrir. |

---

## 5b. ⭐ O MESMO arquivo tem NOME DIFERENTE nos dois SOs — `confirmado`

Num volume compartilhado, um nome criado no macOS com **espaço no fim** (ou ponto no fim) não é
representável no Windows. O macOS então grava esses caracteres mapeados para a **área de uso
privado do Unicode** — convenção antiga de *Services for Macintosh*:

| criado no macOS | gravado no disco | como o Windows lê |
|---|---|---|
| `CAM A ` (espaço no fim) | `CAM A\u{F028}` | `CAM A` + caractere invisível |
| `CAM A.` (ponto no fim) | `CAM A\u{F029}` | idem |

Medido: `ls | cat -A` mostrou os bytes `EF 80 A8` (= U+F028) no lugar do espaço final.

**Três consequências práticas:**

1. **Um literal de caminho com espaço no fim só funciona num dos SOs.** Foi assim que um teste
   de fixture quebrou: `"…/CAM A "` achava a pasta no Mac e não no Windows. A correção é
   **descobrir** o nome (`read_dir` + `starts_with`), não cravá-lo.
2. **`trim()` não resolve.** U+F028 **não é whitespace** para as bibliotecas padrão, então um
   nome "aparado" no macOS continua com o caractere no Windows — e ele vaza para rótulos de
   interface como um símbolo invisível.
3. ⚠️ **Não "conserte" desfazendo o mapeamento cegamente.** Traduzir U+F028→espaço em todo nome
   que o app lê é decisão de produto, não higiene: quem escrever o nome de volta pode gerar um
   arquivo diferente do que existe.

---

## 6. ⭐ A regra que unifica tudo: cheque se FUNCIONA, não se EXISTE

Repare no padrão de §2, §3 e §5: em todos, o artefato **existe** e está **errado**.

| checagem ingênua | por que falha | checagem certa |
|---|---|---|
| `if exists node_modules/` | existe, é do outro SO | procurar o **pacote nativo desta plataforma** |
| `if exists .venv/Scripts/pip.exe` | existe, aponta para o Python do outro SO | **executar** `python.exe -c "import sys"` e olhar o código de saída |
| `if exists <pasta>` (caminho montado com rótulo de volume) | no Windows o caminho é sintaticamente válido e nunca existe | resolver o caminho **de verdade** antes de usar |

**Um script de setup que só testa presença dá falso "tudo pronto" e empurra a falha para longe.**
O custo de executar a checagem de verdade é milissegundos; o custo de não executar foi, nesta
sessão, horas de depuração no lugar errado.

---

## 7. Sobre discos externos (exFAT/USB) — `inferido`

O projeto vivia num SSD externo exFAT. Efeitos observados, úteis para calibrar expectativa:

- **Varredura de árvore grande é cara.** `src-tauri/target/` tinha **99.536 arquivos / 43,7 GB**;
  qualquer ferramenta que faça glob a partir da raiz do projeto paga por isso.
- **Pipeline de CSS/transform continua lento mesmo com cache quente** (~5 s num módulo que
  importa CSS, contra ~2 ms nos demais). Não foi investigado a fundo.
- **exFAT não guarda permissão POSIX** — `chmod`/`0600` não têm efeito. Segredo que dependa de
  permissão de arquivo **não pode** morar no disco compartilhado; guarde em `%APPDATA%`/`~`, cuja
  ACL é privada ao perfil.
- ⚠️ `inferido`: parte da lentidão pode ser antivírus em tempo real (estava ligado) somado ao USB.
  Não foi isolado.
- ⚠️ **E o exFAT distinguir caixa NÃO faz o Windows distinguir** — ver a correção no §3. Uma
  propriedade do sistema de arquivos não é uma propriedade da API que fala com ele.

---

## 8. ⭐ Um `.ps1` sem BOM é lido como ANSI — e o acento vira ASPAS — `confirmado`

Custou uma sessão de depuração no lugar errado, e é 100% transferível para qualquer projeto
que escreva PowerShell com texto em português.

**O mecanismo.** O **Windows PowerShell 5.1** (o `powershell.exe` que vem no sistema, não o
`pwsh` 7) lê um arquivo `.ps1` **sem BOM** como **ANSI/cp1252**, não como UTF-8. Então:

| no arquivo (UTF-8) | bytes | lido como cp1252 | o que o parser vê |
|---|---|---|---|
| `—` (traço longo) | `E2 80 94` | `â€"` | `0x94` = **`”`** |
| `“` `”` (aspas curvas) | — | — | idem |

E o PowerShell **aceita `”` como delimitador de string**. Uma única linha de comentário ou de
mensagem com traço longo fecha uma string onde não devia, o resto da linha vira código, e as
chaves deixam de fechar.

**O sintoma acusa o lugar errado.** O erro é
`Missing closing '}' in statement block or type definition` apontando para uma chave que está
lá, **dezenas de linhas depois** do acento que causou tudo. Passa-se um bom tempo contando
chaves. Medido em `dev.ps1` do De Lá Pra Cá, 2026-08-15.

**A correção:** gravar o `.ps1` em **UTF-8 COM BOM** (`EF BB BF`).

```powershell
$t = [IO.File]::ReadAllText($p, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($p, $t, [Text.UTF8Encoding]::new($true))
```

⚠️ **E confira em vez de confiar** — muitas ferramentas de edição (inclusive as de agente)
gravam UTF-8 *sem* BOM e desfazem a correção calada. A checagem custa uma linha e não precisa
executar o script:

```powershell
$e = $null
[System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$e); $e
```

⭐ **A alternativa que também funciona é manter o `.ps1` em ASCII puro** (sem acento nem traço
longo, nem em comentário). Mais robusto contra edições futuras, ao custo da legibilidade num
projeto que documenta em português. Escolha uma das duas — e registre qual, no topo do arquivo.

---

## 9. ⭐ `$ErrorActionPreference = "Stop"` mata o script na SONDAGEM — `confirmado`

Padrão em quase todo script PowerShell "bem-feito", e no Windows PowerShell 5.1 ele tem um
efeito que ninguém espera: **qualquer linha que um EXECUTÁVEL escreva em stderr vira um
`NativeCommandError` terminante** — mesmo com código de saída 0, e mesmo quando escrever ali é
o comportamento certo do programa.

**O caso medido:** um script de setup que sonda qual Python existe na máquina —

```powershell
foreach ($v in @("3.13","3.12","3.11")) { & py "-$v" -c "import sys"; if ($LASTEXITCODE -eq 0) {...} }
```

Numa máquina sem o 3.13, `py -3.13` imprime `No suitable Python runtime found` em stderr, e o
script **morre na primeira iteração** — ou seja, na sondagem que existe justamente para
descobrir que aquela versão não está lá. O `2>$null` não salva: o *pai* pode remesclar.

**A correção:** `$ErrorActionPreference = "Continue"` e verificação **explícita** de
`$LASTEXITCODE` (ou do artefato que o comando deveria ter produzido) depois de cada comando
externo que importa. Mais verboso, e é o que funciona.

⭐ É a mesma família do aviso já conhecido sobre `2>&1` em executável nativo — só que aqui a
armadilha aparece **sem** ninguém escrever redirecionamento nenhum.

⚠️ Corolário no mesmo eixo, medido no serviço Python: no Windows, um cliente que fecha uma
conexão *keep-alive* faz o `socketserver` levantar `ConnectionResetError [WinError 10054]` e
**despejar um traceback completo** — onde o POSIX devolve leitura vazia e segue calado. Com um
painel batendo `/health` de 4 em 4 segundos, o log vira uma parede de tracebacks idênticos, e
o efeito prático é que um erro **de verdade** passa despercebido no meio. Sobrescrever
`handle_error` para engolir `ConnectionResetError`/`BrokenPipeError`/`ConnectionAbortedError`
resolve.

---

## Fontes

**Primeira passada — Órbita (Tauri v2 + React + sidecar Python), 2026-08-15.** §1 a §7.
Medições com `curl -w "%{time_total}"`, `Get-NetTCPConnection`, `Get-CimInstance Win32_Process`,
e execução real dos scripts de setup nos dois SOs.

**Segunda passada — De Lá Pra Cá (plugin do Media Composer: serviço Python + painel `.avpi`),
2026-08-15, mesma máquina.** §8 e §9, mais a **correção do §3**. Dois apps de arquitetura
diferente atravessando a mesma fronteira no mesmo dia: o que apareceu nos dois é da
plataforma, não do app. Verificação: 85 casos de regressão verdes no Windows, serviço
servindo a UI do painel, `.avpi` instalado em `%PROGRAMDATA%` sem elevação.

O caso do Avid (caminhos, gateway, rótulo de volume, enumeração de processos) está em
[plugins/avid-panel-sdk/windows.md](../plugins/avid-panel-sdk/windows.md).

**Quarta passada — Decupador de Mídia (motor Python + onnxruntime + whisper.cpp + llama.cpp),
2026-08-22.** A seção "Levar um projeto de ML local do macOS para o Windows", no fim desta
página. Primeiro projeto do ecossistema cujo peso é **modelo de ML e binário externo** em vez de
interface, e primeira travessia em que o lado macOS era um **Apple Silicon com MLX** — stack que
simplesmente não existe do outro lado.

Máquinas: origem **Apple M4, 16 GB, macOS**, projeto em SSD externo exFAT (`SSD`);
destino **Dell G15 5530, i7-13650HX 14C/20T, 16 GB, RTX 4050 6141 MiB, driver 596.08 (CUDA
13.2), Windows 11 23H2**, com o mesmo SSD externo montado em `D:` e o trabalho pesado num NVMe
interno NTFS de 4 TB (`S:`).

Medições: `python -m decupador.cli decupar` sobre 748 s de material real (o mesmo bloco de
novela dos dois lados), varredura de `intra_op_num_threads` do onnxruntime e de `-ngl` do
llama.cpp, `llama-tokenize` para contagem de tokens, `nvidia-smi` para VRAM, `Get-NetTCPConnection`
para confirmar ausência de rede, e leitura de stdout cru com `cat -A` — que foi o que revelou os
dois achados do llama.cpp. Verificação de equivalência: contagem de planos, cenas, falantes,
segmentos e caracteres contra a tabela do marco 1.

---

## Diálogos nativos e PowerShell gerado em memória (medido 2026-08-16, `_DeLaPraCa`)

Dois achados de Windows que custaram meia sessão e não são de formato de NLE — são de
**app que fala com o sistema**, e por isso valem para qualquer um do ecossistema.

### ⚠️⚠️ O `Missing closing '}'` também pega script gerado em MEMÓRIA

A seção do `.ps1` sem BOM (acima) descreve o caractere não-ASCII que vira `”` e fecha a
string onde não devia. **A mesma coisa acontece com script passado por `-Command`**, sem
arquivo nenhum no meio: bastou haver comentários em português (`—`, `⚠️`, acentos)
**dentro de um here-string `@"…"@` de `Add-Type`** para o PowerShell 5.1 morrer com

    Missing closing '}' in statement block or type definition.

apontando para o fim do bloco, longe do acento. ⭐ **Regra:** todo script de PowerShell
gerado por outro processo é **ASCII puro**; a explicação fica no código que o gera, nunca
dentro da string. E o sintoma engana duas vezes — se o chamador tiver *fallback*, o erro
vira "o diálogo antigo abriu sozinho", sem nenhuma mensagem.

### ⚠️ O truque do `OpenFileDialog` para escolher PASTA devolve DUAS formas

`OpenFileDialog` com `ValidateNames=$false` + `CheckFileExists=$false` é o truque comum
para ganhar o Explorer moderno num seletor de pasta. Medido: o `FileName` volta em duas
formas conforme o gesto —

| gesto do usuário | `FileName` |
|---|---|
| SELECIONA a pasta e confirma | a própria pasta |
| ENTRA na pasta e confirma com o nome reservado | `<pasta>\<nome reservado>` |

Aplicar `GetDirectoryName` nos dois casos entrega a pasta **MÃE** no primeiro — e o app
indexa o acervo inteiro em vez da diária. Só "funciona" em pasta sem subpastas, onde o
usuário acaba entrando nela por falta de opção. **Teste `Directory.Exists` antes.**

⛔ **E a conclusão que importa mais que as duas:** no PowerShell 5.1 não há diálogo de
pasta moderno sem COM na unha (`IFileOpenDialog` + `FOS_PICKFOLDERS`), e declará-lo à mão
custou uma `NullReferenceException` na leitura dos resultados — depuração de COM por
inspeção, num trecho que só roda com alguém clicando. Apps **Tauri** ganham isso de graça
com o crate **`rfd`** (`AsyncFileDialog::pick_folder`, usado no RELINKER em
`src-tauri/src/lib.rs`); um serviço **Python puro** não tem equivalente.

### ✅ CORRIGE (2026-08-16): Python puro TEM equivalente — é `ctypes`

A frase acima — *"um serviço Python puro não tem equivalente"* — está **errada**, e o
erro é instrutivo: a conclusão foi tirada da linguagem em que as duas tentativas
fracassaram, e generalizada para todas as outras.

**O que continua verdade:** no **PowerShell 5.1** não há caminho bom. Declarar
`IFileOpenDialog` em PowerShell estoura `NullReferenceException` ao ler os resultados, e
o truque do `OpenFileDialog` devolve as duas formas da tabela acima.

**O que era falso:** que isso fosse propriedade da *interface COM*. É propriedade da
*linguagem*. Em `ctypes` a vtable se indexa direto, o marshalling é explícito, e o
trecho que só se depurava por inspeção passa a ser código Python comum.

⭐ **E o ganho decisivo não foi estético, foi de MÉTODO: dá para medir sem abrir a
janela.** O que tornou a tentativa em PowerShell cara foi cada ciclo exigir um humano
clicando. Montar o diálogo e **ler as opções de volta** não abre nada:

```
CoCreateInstance(CLSID_FileOpenDialog, IID_IFileOpenDialog)  -> S_OK
GetOptions()                                                 -> 0x1808   (padrão)
SetOptions(0x1808 | PICKFOLDERS | FORCEFILESYSTEM | PATHMUSTEXIST | ALLOWMULTISELECT)
GetOptions()                                                 -> 0x1a68   ✅ gravou
```

Isso vira **teste de regressão** (`_DeLaPraCa/tests/test_dialogo_win.py`), e é o que
protege a parte que falha em silêncio: **os índices da vtable**. Errar um índice não dá
erro de escrita nenhum — chama-se outro método, com outra assinatura, e o processo morre
com violação de acesso ou devolve lixo.

Índices, para quem for repetir (a ordem é herança acumulada):

| interface | índices | métodos |
|---|---|---|
| `IUnknown` | 0–2 | `QueryInterface`, `AddRef`, `Release` |
| `IModalWindow` | 3 | `Show` |
| `IFileDialog` | 4–26 | `SetOptions`=9, `GetOptions`=10, `SetTitle`=17, `SetOkButtonLabel`=18, `GetResult`=20 |
| `IFileOpenDialog` | 27–28 | `GetResults`=27, `GetSelectedItems`=28 |

⚠️ `FOS_FORCEFILESYSTEM` não é enfeite: sem ele o usuário pode escolher uma pasta
**virtual** da shell (uma biblioteca, "Este Computador") — existe na tela e não existe
para o `os.scandir`. Mesmo modo de falha silenciosa de sempre.

⚠️ E o diálogo **continua tendo de rodar num processo à parte** — não pelo COM, mas
porque um modal dentro de um serviço HTTP trava o servidor. Trocar PowerShell por um
Python filho ainda mata duas armadilhas desta página de uma vez: o `.ps1` sem BOM e o
`[Console]::OutputEncoding` (a saída em UTF-8 passa a ser por construção).

**Confirmado na tela** em 2026-08-16, Windows 11 23H2, Python 3.11 do `.venv-win`, nos
dois cenários que importam: aberto do terminal, e aberto **pelo serviço rodando sob o
Media Composer** — inclusive vindo para a FRENTE da janela do MC. A janela dona é uma
`STATIC` 1×1 com `WS_EX_TOPMOST|WS_EX_TOOLWINDOW`, criada com `CreateWindowExW`,
mostrada com `SW_SHOWNA` e passada como *owner* no `Show`. ⚠️ Sem dono ela nasce
**atrás** da janela do app e o usuário conclui que o botão não fez nada — a mesma
armadilha do `osascript` no macOS, que precisa do `activate`.

⭐ **A lição de calibração, que é a que se repete neste banco:** *"tentei X em A e
falhou"* não é *"X é impossível"*. Antes de escrever a conclusão ampla, pergunte **qual
eixo** falhou — a capacidade, ou a linguagem em que você a pediu. É a mesma disciplina
de separar *versão* de *sistema operacional*, escrita para ferramentas.

⭐ **A lição de requisito, que valeu mais que a técnica:** o pedido era "um seletor com
barra de endereço", mas o gesto impedido era **colar um caminho** — prática comum para
chegar a uma diária na rede. Um campo de texto ao lado do botão resolveu o que três
tentativas de trocar o diálogo não resolveram. *Antes de trocar a ferramenta, confirme
qual gesto está sendo impedido.*

### ✅ CORRIGE (2026-08-16): a lição acima parou na metade do caminho

O campo de texto **foi removido**, e o usuário explicou por quê: quando disse que
precisava colar um caminho, **não estava pedindo um campo na interface do plugin** —
estava descrevendo o que o **Explorer** faz e o diálogo velho não fazia. A frase foi lida
como *"falta um lugar para colar"* e virou superfície nova nossa, quando o que faltava
era a superfície **dele**.

⚠️ **O agravante que faz disto uma armadilha, e não um detalhe de UI:** o campo
*funcionava*. Resolvia o sintoma, o editor conseguia seguir, e por isso o problema real —
a janela errada — ficou parado até alguém reclamar de novo. **Um contorno que funciona é
o melhor esconderijo de um requisito mal lido.**

⭐ **A régua, agora inteira — são DUAS perguntas, não uma:**

1. **Qual gesto** está sendo impedido? (a que este banco já tinha)
2. **Em que superfície** ele deveria acontecer — na janela que a pessoa usa todo dia, ou
   numa que ela teria de aprender?

Quando a resposta de (2) é "na do sistema", construir a nossa **cobra caro duas vezes**:
uma interface a mais para aprender, e a original continua faltando. O sinal de alerta é
estar reimplementando algo que a superfície nativa já tem — colar caminho, histórico,
favoritos, busca. **Se você está recriando um pedaço do Explorer, provavelmente devia
estar abrindo o Explorer.**

⭐ E o desfecho fecha o círculo com a correção técnica acima: o campo só existiu porque a
janela certa parecia inalcançável. Assim que o `IFileOpenDialog` entrou (por `ctypes`), o
contorno perdeu a razão de ser — e o gesto de arrastar a pasta **do próprio Explorer**
passou a cobrir o resto. *Conclusão técnica errada gera requisito mal resolvido:* aceitar
"não dá" cedo demais não custa só a funcionalidade, custa uma interface inventada para
compensá-la.

---

## Levar um projeto de ML local do macOS para o Windows (medido 2026-08-22, Decupador de Mídia)

Segunda travessia macOS → Windows do banco, e a primeira de um projeto cujo peso é **modelo de
ML e binário externo**, não interface. O padrão do §6 (*cheque se FUNCIONA, não se EXISTE*) se
repetiu **quatro vezes**, e nenhuma das quatro levantou exceção.

### ⭐⭐ O cache do HuggingFace copiado do macOS vem cheio de stubs `XSym` — `confirmado`

O achado mais transferível desta sessão, e o parente direto do U+F028 do §5b.

O `huggingface_hub` grava `blobs/<sha>` com o conteúdo e `snapshots/<rev>/<arquivo>` como
**symlink** para o blob. Num volume exFAT o macOS não tem symlink de verdade, então ele **emula**
com a convenção antiga de *Services for Macintosh*: um arquivo comum de **exatamente 1067 bytes**.

```
$ head -c 120 snapshots/<rev>/onnx/vision_model.onnx
XSym
0079
094e527fe128332a822d8081c24402f0
../../../blobs/f5cb16728a704703f05516ded628397e11dbca4de2eb5db04b0c0bcee988aa7a
```

Formato: magia `XSym`, tamanho do alvo em 4 dígitos, MD5, caminho relativo, preenchido com
espaços até 1067.

**Do lado do macOS tudo funciona** — ele resolve o link. **Do lado do Windows são 1 KB de ASCII
no lugar de um modelo de 355 MB**, e a biblioteca de inferência receberia texto. Medido em 13 de
13 arquivos de snapshot de quatro repositórios diferentes.

⚠️ **E o `robocopy` propaga o defeito sem reclamar:** ele copiou 2,65 GB, 45 arquivos, **zero
falhas** — porque do ponto de vista dele são todos arquivos comuns. O relatório de sucesso é
verdadeiro e inútil.

⭐ **O que pegou o problema foi conferência de TAMANHO**, não de existência: um piso mínimo
plausível por arquivo, que o projeto já tinha por causa do `ggml-base.en.bin` de 313 bytes
registrado em [plugins/premiere-cep](../plugins/premiere-cep/chat-video-pro-arquitetura.md). A
disciplina foi escrita olhando o produto do concorrente e se pagou no **nosso próprio cache**.

**Conserto:** varrer `snapshots/**` procurando arquivo de 1067 bytes que comece por `XSym`, ler
o alvo da 4ª linha e trocar por **hardlink** para o blob (mesmo volume NTFS, custo zero, e é
exatamente o layout que o `huggingface_hub` usa no Windows). Cópia serve se os dois estiverem em
volumes diferentes.

⚠️ **Não conserte "baixando de novo"** sem olhar: os blobs estão íntegros. O que quebrou foi só
a camada de links.

### ⚠️⚠️ Ferramenta de linha de comando muda de papel entre versões — `confirmado`

O `llama-cli` do llama.cpp **b10581** não é mais o completador de texto que era: virou uma
**interface de chat interativa**. Ele **ignora** `-no-cnv` e `--no-display-prompt`, e escreve no
**stdout** um banner em arte ASCII, a lista de comandos (`/exit`, `/regen`, `/clear`), o eco do
prompt depois de um `> `, e a geração embrulhada em código ANSI. O comportamento antigo mudou de
nome: é o **`llama-completion`**.

⭐ **O que faz disto uma armadilha e não um detalhe:** o extrator de JSON do chamador procurava a
primeira `{` e casava por profundidade — então **a resposta saía correta com o banner na
frente**. O teste passou. Só olhando o stdout cru (`cat -A`) o problema apareceu. *"Funciona" não
é prova de que o contrato é o que você pensa.*

Regra: ao integrar binário de terceiro por subprocesso, **inspecione o stdout cru uma vez**, e
prefira o executável cujo contrato é "só a resposta" ao que tem UI.

### ⚠️⚠️ A flag que silencia o log silencia a RESPOSTA — `confirmado`

Continuação direta do item acima, e a que custou mais caro das duas.

Depois de trocar para o `llama-completion`, sobrou ruído no stdout (dois códigos ANSI e um
`[end of text]`). A flag que parece resolver é `--log-disable`. O que ela faz de verdade, no
b10581:

```
llama-completion ... --log-disable  ->  exit 0 · stdout VAZIO · stderr VAZIO · 45 s gastos
llama-completion ... (sem a flag)   ->  exit 0 · stdout = só a geração · stderr = todo o log
```

Ou seja: **a geração é emitida pela mesma facilidade de log que a flag desliga**, e desligá-la
apaga o resultado junto. E a flag era **desnecessária desde o começo** — sem ela a separação de
fluxos já é a que se queria.

⭐⭐ **A lição não é sobre a flag, é sobre ESCALA DE TESTE.** Com um prompt de sondagem de 30
tokens o defeito **passou despercebido**; ele só apareceu com o prompt real de 10.691 tokens, no
fim de uma execução de pipeline inteira, **dez minutos depois**, e disfarçado — o erro que subiu
foi `ValueError: nenhum JSON na resposta do LLM: ''`, que acusa o **modelo**, quando o culpado
era a **linha de comando**. É a mesma família do §12 de [seguranca](../seguranca/README.md)
(*"rode uma operação legítima de ponta a ponta, com material real"*), aplicada a integração de
binário em vez de a endurecimento.

**Duas regras que ficam:**
1. Ao integrar binário por subprocesso, **trate saída vazia com código 0 como ERRO explícito**,
   com mensagem que aponte para a invocação. Sem isso o sintoma aparece a jusante, apontando
   para o componente errado.
2. **Toda flag de "silenciar" merece um teste com carga real** antes de entrar. Silenciar é
   exatamente a categoria de opção cujo efeito colateral é invisível.

### ⚠️ Duas ferramentas, a mesma DLL, versões diferentes — `confirmado`

O whisper.cpp e o llama.cpp distribuem, cada um, a sua cópia de `ggml.dll`, `ggml-base.dll` e
`ggml-cpu-*.dll`. Extraídos na **mesma** pasta, o segundo sobrescreve as do primeiro, e sobra um
`whisper.dll` ao lado de um `ggml-base.dll` que não é o dele. O Windows resolve DLL pelo
**diretório do executável**, então o efeito é crash — ou resultado errado em silêncio.

Regra: **uma subpasta por ferramenta**, e o resolvedor de binário procura nelas. Vale para
qualquer par de binários que compartilhe uma runtime.

### ⚠️ Dotfile criado no macOS chega ao Windows com atributo HIDDEN — `confirmado`

Um `.gitignore` vindo do macOS por exFAT tem atributo `H`. No Windows, **truncar um arquivo
oculto levanta `PermissionError`**: `Path.write_text()` falha, enquanto acrescentar ao fim
(`>>`) e `open(..., "r+")` funcionam. O erro acusa permissão, e a causa é um atributo — não há
nada de errado com a ACL. Reescreva com `r+` + `truncate()`, ou tire o atributo antes.

### ⚠️ A saída do CLI fica presa em buffer quando alguém a lê — `confirmado`

O Python só usa buffer de **linha** quando o stdout é terminal. Redirecionado para arquivo ou
lido por outro processo, passa a buffer de **bloco**: uma rodada de dez minutos com progresso por
estágio não imprime **nada** até o fim, e o sintoma é "travou". Uma linha resolve:
`sys.stdout.reconfigure(line_buffering=True)`. É irmão do modo de falha silencioso de sempre.

### ⭐⭐ Mais não é melhor depois do limite — a curva em U aparece duas vezes

As duas medidas na mesma máquina (i7-13650HX, 14C/20T híbrido P+E; RTX 4050 com 6141 MiB):

**Threads do `onnxruntime`** (SigLIP 2 fp32, 355 MB, CPU):

| intra_op | padrão | 1 | 2 | 4 | 6 | 8 | 14 | 20 |
|---|---|---|---|---|---|---|---|---|
| ms/frame | **206** | 1516 | 986 | 721 | 628 | 644 | 3041 | 3430 |

**Camadas na GPU (`-ngl`)** do llama.cpp (Qwen3-8B Q4_K_M, 5,03 GB, prompt de 7,5 KB):

| ngl | 0 | 16 | 24 | 28 | 32 | 99 |
|---|---|---|---|---|---|---|
| segundos | 77,7 | 45,2 | 31,6 | **24,7** | 39,8 | 78,7 |

Duas lições:

1. **O padrão do onnxruntime ganha de qualquer ajuste manual**, e cravar o número de threads
   lógicos (20) é **17× pior** que deixar quieto. Num processador híbrido P+E, espalhar por
   todos os núcleos joga trabalho nos E-cores e a barreira espera pelo mais lento.
2. **Offload total para a GPU custa o mesmo que GPU nenhuma** quando o modelo não cabe: aos 99
   o peso transborda os 6 GB, o driver pagina para a RAM do sistema, e perde-se tudo que se
   ganhou. O joelho tem de ser **medido por máquina** e gravado junto do resultado.

⚠️ **E uma armadilha de medição no meio disso:** o primeiro número de embedding foi **5439
ms/frame**, 26× pior que o real. Era **cache de disco frio** — o teste "aquecia" com uma chamada
antes de medir, mas o `onnxruntime` só toca as páginas dos pesos conforme executa, então a
segunda chamada ainda pagava I/O de um arquivo de 355 MB. Medida repetida com o arquivo quente:
**213 ms/frame**. *Uma chamada de aquecimento não aquece o que é paginado sob demanda.*

### O que o port CUSTOU, e o que provou — medido no mesmo material dos dois lados

748 s de material (um bloco de novela), o mesmo arquivo, primeiro num **Apple M4 16 GB** e
depois num **i7-13650HX 16 GB + RTX 4050 6 GB**:

| estágio | M4 | Windows | |
|---|---|---|---|
| ingest | — | 0,2 s | hash **idêntico** |
| áudio 16 kHz mono | 0,5 s | 1,3 s | |
| planos (scdet + SigLIP em CPU) | **83,8 s** | **506,6 s** | ✗ 6,0× mais lento |
| transcrição (whisper.cpp) | 35,5 s | **28,7 s** | ✓ **mais rápido** (cuBLAS > Metal aqui) |
| diarização (sherpa-onnx, CPU) | 38,5 s | 95,0 s | ✗ 2,5× |

⭐ **A leitura útil: o que roda em CPU perdeu, o que roda em GPU ganhou.** O M4 tem CPU muito
mais forte por núcleo para inferência ONNX (59 ms/frame contra 213 ms no i7), e é isso que
carrega os estágios de planos e diarização. Já o ASR, que no Windows encontra um cuBLAS de
verdade, **bate o Metal do M4**. Ao planejar um port destes, separe os estágios por onde a
conta é feita antes de estimar.

⚠️ E o estágio de planos perdeu **6,0×** onde o custo por frame só explica **3,6×** — o resto é
suspeita, ainda não confirmada, de **lote grande demais numa chamada só do onnxruntime** (o
código passa centenas de frames de uma vez, e a medição de 213 ms/frame foi feita com lote 2).
`hipotese`, a medir.

### ⭐ A prova de equivalência que apareceu no lugar da planejada

A intenção era comparar os vetores de embedding dos dois sistemas, mas o sidecar da rodada do
macOS não tinha sido preservado. O que apareceu no lugar é **mais forte**: o estágio de planos
saiu **número por número igual** — `143 do scdet −17 +32 = 158 planos, 59 cenas`, e 19 falantes
na diarização.

Esses números são o resultado de comparar similaridades de embedding contra **três limiares
diferentes** (0,93 de confirmação de corte, 0,88 de dissolve, 0,82 de agrupamento em cena).
Baterem exato nos três significa que os embeddings são numericamente equivalentes **e** que
scdet, refino e agrupamento atravessaram intactos.

⭐ **Regra de método:** quando o artefato de referência para uma comparação não existe, procure
um **resultado a jusante que dependa de muitos limiares**. Ele prova mais do que a comparação
direta, porque uma diferença numérica pequena teria mudado pelo menos uma das decisões.

### O que atravessou sem tocar

`onnxruntime`, `sherpa-onnx` (com wheel cp311 para Windows), `numpy`, `xxhash`, `ffmpeg`, e todo
o código de hash, de leitura de metadado e de escrita atômica. ⭐ O **hash parcial de conteúdo
saiu idêntico nos dois sistemas** (`952a8fcaf530a9fa` para o mesmo arquivo), que é a propriedade
que faz um sidecar gerado num lado ser reconhecido no outro.

E uma confirmação do §5 desta página: **`huggingface_hub` e `transformers` eram dependências de
tabela** — não estavam no `requirements.txt` e chegavam de carona no `mlx-lm`, que é justamente
o pacote que o port removeu. Ambiente novo do zero é o que revela isso.

## 5ª passada (2026-09-02) — ⚠️ o `XSym` mordeu de novo, noutro app, e o banco já sabia

`confirmado`, Assist anterior. O autor copiou 7 GB de modelos do SSD para
`%LOCALAPPDATA%\assist_anterior\modelos` e a interface continuou dizendo que faltava tudo. Os
quatro modelos estavam lá — como arquivos de **1067 bytes**. É exatamente o `XSym` da 4ª
passada, três meses depois, num app diferente.

⭐⭐ **A lição não é sobre o formato — é sobre CONSULTAR.** A página já descrevia a armadilha, o
tamanho do stub e o conserto. Ninguém leu antes de gastar uma hora redescobrindo. *O banco só
se paga quando é a primeira parada, não a última.*

Dois acréscimos que a 5ª passada traz:

- ⭐ **Existe conserto SEM tocar no disco do usuário.** A 4ª passada recomenda trocar o stub por
  **hardlink** para o blob. Serve, e é melhor para quem instala. Mas um consumidor **somente de
  leitura** pode simplesmente **seguir o link**: o `XSym` traz o alvo em texto na 4ª linha,
  relativo ao próprio arquivo. Vinte linhas de Python, nada mudado no disco, e funciona para
  qualquer cache que tenha atravessado. ⚠️ Com limite de saltos: um `XSym` pode apontar para
  outro, e um ciclo não pode virar laço infinito.
- ⛔⛔ **A conferência de TAMANHO não é opcional, e a ausência dela é um falso-verde de manual.**
  O `verificar()` do Assist anterior testava `is_file()` e dizia **pronto** com os quatro modelos
  sendo stubs. Quem descobriu foi o `whisper-cli`, minutos depois, com uma mensagem que acusava
  o binário. A 4ª passada já dizia que *"quem pegou foi conferência de tamanho"* — e o segundo
  app não a tinha. ⇒ **todo verificador de modelo compara o tamanho contra o esperado**, ainda
  que grosseiramente (metade serve; não é checagem de integridade, é a rede que separa *"o
  arquivo está aí"* de *"há um ponteiro no lugar dele"*).

## Sidecar Python: um `import scipy` custou 15 s dentro do app (medido 2026-09-17, Órbita, Windows)

Sintoma, visto pelo autor: criar merged clips no painel do Premiere "demorou" — o Media
Composer faz o equivalente quase instantâneo. O log do app, com marcadores por passo:

| | comando | a escrita em si |
|---|---|---|
| antes | **15,40 s** | 0,17 s |
| depois de tirar o `scipy` do caminho | **0,57 s** (imports 0,06 s) | 0,51 s |

A escrita não usava `scipy`: ele entrava por importações de módulo INTEIRO para pegar uma
função pequena (`sync.engine` pela conta de duração, `sync.tcmatch` pela leitura de timecode,
e o `tcmatch` importava `scipy.signal` no topo). No sidecar recém-iniciado, a primeira
operação que tocava esses módulos pagava a importação.

⚠️⚠️ **O número fora do app mente para baixo:** o mesmo comando, num processo novo com o
MESMO Python do venv, levava **1,6 s** — não 15. A diferença é do contexto do processo do app
(causa exata não isolada; o cache de bytecode não era desviado — conferido). Moral: **meça
dentro do app**, com marcador por passo no log, antes de concluir que "é rápido".

⭐ **Regra para sidecar:** operação que o usuário dispara de um painel não pode depender de
módulo pesado por tabela. Função leve mora em módulo leve; biblioteca pesada é importada
DENTRO da função que a usa. `confirmado` pela rodada seguinte do autor: *"agora foi quase
instantâneo, esse é o feedback que o usuário deve esperar"*.

⚠️ Em Windows e macOS: o custo relativo pode mudar no Mac (medido só no Windows) — `pendente`.

## pywebview: duas armadilhas medidas no Sanitizador de AAF (2026-08-20, Windows) — `confirmado`

> Registrado pelo zelador do SSD em 2026-10-06, ao arquivar o `SANITIZADOR_DE_AAF`.

- ⚠️⚠️ **Nada de referência a janela dentro do objeto `js_api`.** O pywebview monta a ponte JS
  varrendo o objeto com `dir()` (`webview/util.py::get_functions`) e **desce recursivamente em todo
  atributo não-chamável** que não comece com `_`. Um `self.janela = janela` faz ele percorrer o
  objeto .NET do WinForms (`native.AccessibilityObject.Owner.ActiveControl.DefaultFont…`) até
  estourar a recursão: **~400 KB de erro no log a cada abertura**. O app funciona, o log cresce sem
  limite e esconde o erro de verdade. Vale para `@property` também (`getattr` a executa). Correção:
  nome começando com `_` (`_janela`) ou `_serializable = False`. Custou dois rebuilds.
- **Soltar arquivo dentro da janela não funciona e não tem conserto neste stack** (ver a linha na
  [matriz](matriz-de-plataforma.md) §F): a interface diz isso, e o caminho é argv.

## Projeto Rust/Tauri movido de pasta, e o `.dmg` no exFAT (FLATFILE-MULTCAM, 2026-07-03)

Mover o projeto de `~/Documents/PROGRAMAS COM CLAUDE` para o SSD levou junto
`frontend/src-tauri/target/` (6,5 GB) com centenas de arquivos citando o caminho antigo, e o build
morreu em `failed to build app` (o erro real, mais acima no log: `failed to read plugin
permissions: … No such file or directory` no caminho morto). Apagar `target/` resolveu; o
VP9WAVDCP teve o mesmo sintoma. Depois disso, com o projeto no exFAT, o `.app` saiu e o `.dmg`
falhou: o `hdiutil` não cria a imagem lá. Ver as duas linhas novas na
[matriz](matriz-de-plataforma.md) §H. ⭐ **Para o zelador:** toda mudança de pasta de um projeto
Tauri precisa apagar `target/` antes do próximo build — ele se regenera.
