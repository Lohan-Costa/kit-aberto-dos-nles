# Ligar o Panel SDK no MC 2021.12 — o toggle `3PDevPanelSDK` e o Feature Toggle File (FTF)

> **Versão medida:** Avid Media Composer **2021.12.10.56256** (Windows 11), build **release**.
> **Impressão digital:** `FTF.dll` sha256 `a3651036c2faab5063ca446f002821d457f701ff3e866f66c84dfe40c0d92f8c`
> (PDB `FTF.pdb`, "Feature Toggle File Library 1.9.0"); `AvidMediaComposer.exe` `dwFileFlags=0x0`.
> Fora desta versão, tudo aqui volta a `hipotese`. Engenharia reversa (REA/Ghidra 12.1.4) + harness
> em C contra o `FTF.dll` real, 2026-10-17. Harnesses: `D:\_ZELADORIA\mc2021-ftf\`.

## Por que este arquivo existe

No MC **25.6/25.12** o Panel SDK está **ligado** e o [README](README.md) cobre o resto. No MC
**2021.12** ele vem **desligado**: medido 2026-10-17, a instalação não tem `C:\ProgramData\Avid\
PanelSDKPlugins`, nem `avid-api-gateway`, nem o gRPC em 9100 — só o QtWebEngine. Um `.avpi` posto à
mão (DLPC e o do parceiro PARCEIRO-Q) **não aparece em menu nenhum**. O SDK existe no binário, atrás
da feature flag **`/Media Composer/3PDevPanelSDK`** (*"Enable 3P development for Panel SDK."*, grupo
`avid.SDK.developer.features`). Este arquivo mapeia COMO essa flag é lida e se dá para ligá-la.

## ⭐ Em que versão o Panel SDK aparece — linha do tempo (confirmado 2026-10-17)

`confirmado` por **inspeção dos instaladores** (sem instalar): arquivos no pacote + `grep -c -a` de
strings no `AvidMediaComposer.exe` de cada versão. Indicador decisivo = o binário `avid-api-gateway.exe`
existir no pacote (é o proxy que serve E registra os painéis).

| versão (Windows) | `avid-api-gateway.exe` | `PanelSDKPlugins` + `.avpi` exemplo | `PanelSDK.json` / `APIGateway` | `GetPluginAccessToken` | `panelsdk reinit` | Panel SDK? |
|---|---|---|---|---|---|---|
| 2021.12.10 | ausente | ausente | ausente | 0 | 0 | **NÃO** |
| 2022.12.9 | ausente (só string ×1 no exe) | ausente | ausente | 0 | 0 | **NÃO** (transição) |
| **2023.8.2** | **presente** | **presente** (`avid-huddle.avpi`) | **presente** | 4 | 3 | **SIM** ⬅ primeira |
| 2024.6.0 | presente | presente | presente | 5 | 2 | SIM |
| 2025.12.2 | presente | presente | presente | 5 | 2 | SIM |

⭐ **A primeira versão com o Panel SDK completo/funcional é a 2023.8.2.** O 2022.12.9 é transição (o exe
já cita `avid-api-gateway`/`avid-manifest`, mas o runtime não vem no pacote). ⇒ **base recomendada para
os plugins/painéis = MC 2023.8.2** (não a 2022). O que o banco mapeou no 25.6/25.12 (mcapi.proto, 60
métodos, gRPC 9100, `.avpi`) deve valer a partir da 2023.8.2, com diferenças de versão a medir. O
`.avpi` de exemplo `avid-huddle.avpi` vem dentro do instalador 2023/2024/25 (amostra oficial p/ validar
o formato do manifesto nessa versão).

## O sistema de feature toggles (FTF)

`confirmado`. O MC lê toggles via `FTF.dll`. No boot (`AvidSearch.exe`/`FUN_140003aec`, código
compartilhado; **`confirmado` também no `AvidMediaComposer.exe`** — ver o call site medido no fim):

```c
FTF_Init("", <bool buildDev>);
FTF_RegisterToggleFile(2, "avid.released.features",      "ReleasedFeatures.ftf");     // tipo 2
FTF_RegisterToggleFile(1, "avid.prereleased.features",   "PreReleasedFeatures.ftf");  // tipo 1
FTF_RegisterToggleFile(1, "avid.SDK.developer.features", "SDKDeveloperToggles.ftf");  // tipo 1
FTF_RegisterToggle("/Media Composer/3PDevPanelSDK", false, "avid.SDK.developer.features");
```

Os `.ftf` ficam em **`%PROGRAMDATA%\Avid\Support\`** (fallback hardcoded `C:\ProgramData\Avid\
Support\`). Cada toggle vive num `std::map` global por nome; o valor efetivo é o override, se houver,
senão o default. **A aplicação é por GRUPO** (`confirmado`, harness `ftftest.exe`): cada toggle só lê
o arquivo do seu grupo — um valor no arquivo de outro grupo é ignorado.

### Formato do `.ftf` por tipo

| tipo | arquivo | formato | assinatura |
|---|---|---|---|
| **2** | `ReleasedFeatures.ftf` | **JSON texto claro** (só precisa começar com `{`) | nenhuma |
| **1** | `SDKDeveloperToggles.ftf`, `PreReleasedFeatures.ftf` | `base64("Salted__"+salt[8]+AES(payload))`, cifrado com o `systemId` da máquina; payload = mensagem **S/MIME assinada (PKCS#7)** | **Avid** |
| **0x7fffffff** | `CIT_OVERRIDE.FTF` (override) | **JSON texto claro** | nenhuma |

- `header.systemId` tem que bater com o device-id da máquina (`ELFGetDeviceID` da `ELF_64.dll`),
  senão `ErrorSystemIdDoesNotMatch` / *"created for a different computer"*. É o que amarra à máquina.
- Corpo de arquivo de grupo (tipo 2/1): `{"header":{"systemId":"…"},"features":{"Media Composer":{"3PDevPanelSDK":true}}}`
- Corpo do CIT_OVERRIDE (tipo 0x7fffffff): toggles **direto na raiz**, sem `features`:
  `{"header":{"systemId":"…"},"Media Composer":{"3PDevPanelSDK":true}}`
- O JSON é RapidJSON; o parser (`FUN_1800769a0`) valida o `header`, e `FUN_18007d460` resolve o
  caminho hierárquico do toggle (`/Media Composer/3PDevPanelSDK` → `"Media Composer"`→`"3PDevPanelSDK"`).

## O `3PDevPanelSDK` só liga por dois caminhos — e ambos barram no trial

### 1. `SDKDeveloperToggles.ftf` (o caminho oficial) — exige assinatura Avid
`confirmado`. É tipo 1 (grupo developer): cifrado com o systemId **e** assinado em PKCS#7, verificado
contra certificado (o app **não** chama `FTF_SetCertificateData(NULL)`, então a verificação roda).
**Forjar é inviável** sem a chave privada da Avid; e um `.ftf` real de outra máquina não serve
(amarrado ao systemId daquela). Um texto claro dá `registerToggleFile: error reading input file`.

### 2. `CIT_OVERRIDE.FTF` (override GLOBAL, sem assinatura) — barra no build-type
`confirmado` in-process (harness `ftfcit.exe`: ligou o `3PDevPanelSDK`, controle `CloudUXPanelDebug=0`).
O CIT é override **global** (vale para toggle de qualquer grupo), tipo 0x7fffffff = **JSON texto
claro, sem cifra nem assinatura**. Fica ao lado do exe do processo (`GetModuleFileNameW(NULL)` →
`C:\Program Files\Avid\Avid Media Composer\CIT_OVERRIDE.FTF`) ou onde `FTF_SetOverridePath` apontar.

🔴 **O gate:** o CIT só é consultado se `FTF_Init` recebe `true` no 2º arg, e o boot passa
`GetVersionBuildType()=='b' || 'd'`. Essa função (`AvCoreM2W10.dll`/`FUN_60402774`) lê o
**`dwFileFlags` do VERSIONINFO do exe do processo**: bit `0x2` (VS_FF_PRERELEASE)→`'b'`, bit `0x8`
(VS_FF_PRIVATEBUILD)→`'d'`, senão release. **Medido: `AvidMediaComposer.exe` tem `dwFileFlags=0x0`
(mask `0x3F`) → release → CIT desabilitado.**

## ⛔⛔ CAUSA RAIZ (confirmado 2026-10-17, teste real): o 2021.12 NÃO TEM o runtime do Panel SDK

`confirmado`. O autor aplicou o patch (o MC **abriu normal** — sem self-check de integridade fatal) e
**o painel não apareceu**; o console não cita painel/gateway/Extensions. Medido no exe e no disco:

| evidência | 2021.12.10 | (25.6, p/ comparar) |
|---|---|---|
| binário `avid-api-gateway` | **ausente** | presente |
| string `avid-api-gateway` no exe | **0** | — |
| string `PanelSDKPlugins` no exe | **0** | presente |
| `GetPluginAccessToken` / `panelsdk` / `avid-manifest` | **0 / 0 / 0** | presentes |
| só vestígios | `qwebchannel.js` (arquivo), `Panel SDK` (1×), `mcapi.MCAPI` (1×) | — |

**E a API gRPC também não existe** (`confirmado` 2026-10-17, MC aberto): o processo tem **0 portas TCP
em LISTEN** e `127.0.0.1:9100` recusa conexão. ⇒ no 2021.12 **não há NEM painel (Panel SDK) NEM a via
de dirigir o MC por fora (gRPC 9100, estilo Órbita)**. Os dois mecanismos vieram depois.

⭐ **O toggle `3PDevPanelSDK` é um resquício; o subsistema que ele habilitaria não existe neste build.**
O `avid-api-gateway` (proxy gRPC-Web que serve E registra os painéis), a varredura de
`%PROGRAMDATA%\Avid\PanelSDKPlugins`, o registro de `.avpi` e o menu de painéis só vieram em versões
posteriores (25.6+). Logo, **ligar o toggle não basta — não há motor de painel para subir.** Todo o
caminho ".avpi/Panel SDK" no 2021.12 está morto por **ausência de runtime**, não por falta de habilitação.

## Veredito (confirmado para o 2021.12.10 trial)

**Impossível rodar um painel Panel SDK no MC 2021.12.10 — o runtime não está no produto.** O toggle
`3PDevPanelSDK` existe e é lido pelo FTF, mas é inerte sem o gateway/registro. Nem o `.ftf` assinado,
nem o CIT_OVERRIDE, nem o patch de build-type mudam isso (o patch foi testado: MC abre, painel não vem).

> ⚠️ Se o "MC 2021 com painéis de terceiros" do trabalho do autor realmente roda painéis, então é
> **outra build/versão** (uma 2021.x/2022 posterior que já trouxe o Panel SDK) ou os tais painéis usam
> **outro mecanismo** (AVX2, ou dirigir o MC por fora). A faixa de versão que introduziu o runtime do
> Panel SDK fica **em aberto** — medir numa instalação entre 2021.12 e 25.6 fecharia.

### (histórico) o gate de build-type — ainda válido, mas secundário
Mesmo que o runtime existisse, o CIT_OVERRIDE (que dispensa assinatura) dependeria do gate de
build-type abaixo; o `.ftf` do grupo developer dependeria da assinatura Avid. Com o runtime ausente,
esses dois pontos deixam de importar na prática.

**Caminhos para destravar (não executados — exigem decisão/risco):**
- **Patch de ~1 bit** no `dwFileFlags` do VERSIONINFO do `AvidMediaComposer.exe` (ligar `0x2`; o mask
  já é `0x3F`) → `GetVersionBuildType`='b' → CIT habilitado. ⚠️ quebra a assinatura Authenticode do
  exe, é sobrescrito por atualização, possivelmente fere a licença, e pode ligar outros
  comportamentos beta/dev. Depois: gerar `CIT_OVERRIDE.FTF` com o systemId real + instalar o `.avpi`.
- `FTF_SetDynamicToggle` (toggle em memória) via injeção em runtime — mais invasivo.
- Pedir à Avid onboarding de desenvolvedor do Panel SDK (SDK oficial é fechado — ver README).

## Call site do `FTF_Init` no `AvidMediaComposer.exe` — `confirmado` (2026-10-17)

O REA/Ghidra não analisa o EXE de 59 MB (timeout 330s). Localizado por parsing dirigido
(`pefile`+`capstone`, script `D:\_ZELADORIA\mc2021-ftf\find2.py`: string da import-by-name → slot IAT →
import thunk `jmp [rip]` → `call` ao thunk). A vizinhança em `0x14051d1f3`:

```asm
call  GetVersionBuildType     ; al = build type
sub   al, 0x62                ; al -= 'b'(0x62)
test  al, 0xfd                ; (al & ~0x02)==0 ?  -> ZF só para 'b'(0x62) e 'd'(0x64)
sete  dl                      ; dl = 1 sse build é beta/dev
lea   rcx, [...]              ; sysID
call  FTF_Init                ; FTF_Init(sysID, dl)
```

Idêntico ao `AvidSearch.exe`. Com `dwFileFlags=0x0` (build `.`), `dl=0` → `ctx+0x138=0` → CIT
desabilitado. **Fecha o veredito no próprio binário do Media Composer, não mais por analogia.**

## Exports úteis do `FTF.dll` (todos `confirmado`)
`FTF_Init(sysID, bool)` · `FTF_InitMessageProc(cb)` · `FTF_RegisterToggleFile(type, token, file)` ·
`FTF_RegisterToggle(name, default, group)` · `FTF_GetToggle(name)→bool` · `FTF_SetOverridePath(dir)` ·
`FTF_SetCertificateData(pem|NULL)` · `FTF_GetDefaultToggleJson(mod, ver, buf, n)` ·
`FTF_SetDynamicToggle(name, bool)`. Passar `systemId` não-vazio ao `FTF_Init` fixa o systemId (útil
para testar em harness sem o device-id real). Dep de carga: `ELF_64.dll` (na pasta do MC).

## Caminho A — datado o ENABLE do painel por comparação de exes (2026-10-17, `confirmado` por strings; medido em 22.12.9, 23.8.2 instalado, 24.6.0, 25.12.2)

O **`/Media Composer/3PDevPanelSDK`** (descrição no exe: *"Enable 3P development for Panel SDK"* = carregar painéis **não-assinados/dev**) é o **mesmo gate em TODAS as versões** (22→25), sempre atrás da assinatura FTF / patch de build-type. **Nenhum comando de console o liga** — o console só tem `panelsdk reinit` (23.8.2 também `reload`; 24.6.0+ `console on|off`).

A habilitação do painel **mudou de natureza depois do 23.8.2**:

| sinal no `AvidMediaComposer.exe` | 22.12.9 | 23.8.2 | 24.6.0 | 25.12.2 |
|---|:-:|:-:|:-:|:-:|
| `3PDevPanelSDK` (toggle FTF dev) | ✅ | ✅ | ✅ | ✅ |
| runtime (`PanelSDKPlugins`, gateway) | ❌ | ✅ | ✅ | ✅ |
| **`IsPanelSDKEnabled()`** (enable geral, `ABinView.cpp`) | ❌ | ❌ | ✅ | ✅ |
| **menu `Extensions` / `Host Panels`** (`PanelSDKMenu.cpp`) | ❌ | ❌ | ❌ | ✅ |

**Medido no 23.8.2 instalado:** runtime de pé (`avid-api-gateway.exe`, **9100** gRPC do MC, gateway `[::1]:4920/4930`, `PanelSDK.json` ports 9100-9110, `APIGateway/config.json` apiPort 4920/pluginPort 4930), 2 `.avpi` em `C:\ProgramData\Avid\PanelSDKPlugins` (o `com.usuario.delapraca.mc.avpi` do autor + `PARCEIRO-Q_1.0.0.avpi`), **mas painéis NÃO aparecem no Tools** — nem o dev nem o comercial. Exe é **release** (`dwFileFlags=0x0` @ file offset **0x4870334**); sem `.ftf` em `ProgramData\Avid\Support`.

**Conclusão:** o **23.8.2 é cedo demais** (só o toggle dev → painel não-assinado some sem gambiarra). O **25.6 do autor mostrava os painéis** por ser da era do `IsPanelSDKEnabled`/Extensions. **Base recomendada p/ os plugins/painéis = 24.6.0+ (idealmente 25.x).** Em aberto: se no 24.6.0+ o enable é default/por setting de UI (menu Extensions/Host Panels) ou se houve ação do autor no 25.6.

## Assinatura de painel .avpi — amostra PARCEIRO-Q (2026-10-17, `confirmado`; dissecado em 23.8.2)

Ampliando a amostra com um painel comercial de terceiro (PARCEIRO-Q, em `ProgramData\Avid\PanelSDKPlugins\PARCEIRO-Q_1.0.0.avpi`): ele é **ASSINADO pela Avid**. O `.avpi` (ZIP) guarda no **comentário do arquivo** uma assinatura **XML-DSig** (`<ds:Signature ID="AvidSign">`): `SignatureMethod` rsa-sha256, canonicalization c14n11, um `<ds:Manifest>` que referencia `PARCEIRO-Q_1.0.0_UNSIGNED.avpi` com `DigestValue` SHA-256, e `<ds:KeyInfo>` com a cadeia X509 — folha **CN="Avid Technology, Inc", O="Avid Technology, Inc", Burlington/Massachusetts/US**, emitida por **DigiCert Trusted G4 Code Signing RSA4096 SHA384 2021 CA1** (raiz DigiCert Trusted Root G4), validade 2025-05-08→2026-05-07. ⇒ a Avid **empacota o `.avpi` cru e assina por cima** (o original vira `..._UNSIGNED.avpi` dentro do processo). Conteúdo do PARCEIRO-Q: `src/index.html` (12,4 MB, bundle), `src/main.js`, `src/css/main.css`, `static/application.svg`, `avid-manifest.json` (companyPrefix `beamwell`, usesApi general/SRT/transportcontrols/timelineEditing/command, uiItems dropdown em "Tools").

**Decisivo:** o PARCEIRO-Q é **assinado** e MESMO ASSIM **não aparece no 23.8.2** (host de painel ausente). ⇒ no 23.8.2 o bloqueio é **de versão**, não de assinatura — assinado ou não, nada aparece. Num 24.6.0+ o assinado aparece; e o painel **não-assinado local** do autor apareceu "sozinho" no 25.6 ⇒ 25.x libera painel local não-assinado por padrão (a confirmar instalando 25.12.2). O `De Lá Pra Cá` do autor é **não-assinado** (só manifesto + static).

### Segunda amostra assinada: Quickture (2026-10-17) — padrão confirmado

Extraído o `.avpi` do `Quickture_Windows_Avid_Helper_1.6.3.msi` (MSI→`app.cab`→`PathFile_...`, 127914 bytes, via 7z, SEM instalar): **assinado com o MESMO esquema e o MESMO certificado** do PARCEIRO-Q — `<ds:Signature ID="AvidSign">` no comentário do ZIP, cert folha **"Avid Technology, Inc"** (DigiCert Trusted G4 Code Signing RSA4096 SHA384 2021 CA1), referencia `quickture_20260402.avpi` por SHA-256. ⇒ **dois produtos comerciais independentes, assinatura idêntica da Avid** → padrão de assinatura de painel 3P está `confirmado` (não é peculiaridade de um fornecedor). O painel do autor (`De Lá Pra Cá`) é o único não-assinado da amostra. Jumper (Windows = `Install Jumper.msi` + 5 `.cab` ~5,4 GB) não dissecado (confirmatório; o painel dele serve de `http://localhost`, não de dentro do `.avpi`).

## TESTE CONCLUSIVO: painel comercial assinado, instalado oficialmente, NÃO aparece no 23.8.2 (2026-10-17, `confirmado`, pilotado)

O autor instalou o **Quickture Avid Helper 1.6.3** (MSI oficial) no MC 23.8.2. Pegada: helper em `C:\Program Files\Quickture Avid Helper\` (`quickture_helper.exe` + `resources\quickture.avpi` — o `.avpi` NÃO vai para `PanelSDKPlugins`; o registro é dinâmico pelo helper). Com o **helper rodando** (PID vivo, escutando **127.0.0.1:3030** = a faixa do `allowedDomains`) e o **MC aberto no projeto** (gateway/9100 de pé), abri o menu **Tools** pelo piloto e fotografei: itens padrão do MC, **nenhum painel** — sem Quickture, sem PARCEIRO-Q (assinado, em PanelSDKPlugins), sem o De Lá Pra Cá (não-assinado), **sem submenu Extensions/Host Panels**.

⇒ **No 23.8.2 nenhum painel aparece, independentemente de assinatura/instalação** (o host de painel — `IsPanelSDKEnabled`/`PanelSDKMenu`/Extensions — só existe no 24.6.0+). O bloqueio é 100% de **versão**. Para rodar QUALQUER painel (comercial ou o do autor), o MC tem de ser **24.6.0+** (base recomendada 25.x; instalar 25.12.2 — exige desinstalar o 23.8.2 antes). O painel do autor é não-assinado mas apareceu "sozinho" no 25.6 ⇒ 25.x carrega painel local não-assinado (a confirmar no 25.12.2).

## ✅ RESULTADO NO MC 25.12.2 (2026-10-17, pilotado): painéis ASSINADOS aparecem; o não-assinado NÃO

Após o autor desinstalar o 23.8.2 e instalar o **25.12.2** (Trial), com os 4 `.avpi` em `PanelSDKPlugins` (avid-huddle, com.usuario.delapraca.mc, quickture, PARCEIRO-Q) e o helper do Quickture rodando: abri o MC pelo piloto (a tela inicial do 25.x é "Select Project" redesenhada — botão **Open** sem foco, ENTER não abre; **duplo-clique na linha do projeto** abre) e o **menu bar do 25.x tem um menu `Extensions`** (entre Script e Help; não existe no 23.8.2). O menu **Extensions** lista: **Quickture** e **PARCEIRO-Q** — os DOIS painéis **assinados pela Avid**. ⛔ O **`De Lá Pra Cá` (não-assinado) NÃO aparece**.

⇒ **Conclusão dupla:** (1) o host de painel do 25.x funciona e carrega painel assinado **sem gambiarra** (versão confirmada como a variável-chave do 23.8.2); (2) **painel NÃO-ASSINADO continua bloqueado no 25.12.2** — precisa do `3PDevPanelSDK` ("Enable 3P development"). Agora, diferente do 2021, **há runtime**, então ligar o `3PDevPanelSDK` no 25.12.2 deve fazer o `De Lá Pra Cá` aparecer. ⚠️ O autor dizia que no 25.6 o painel dele aparecia "sozinho" — ou o 25.6 era mais permissivo com não-assinado (Avid apertou até o 25.12.2), ou havia o toggle ligado. Caminho p/ o painel do autor: assinar (programa de parceiro Avid) OU ligar 3PDevPanelSDK (CIT_OVERRIDE + patch de build-type, agora re-mirado no exe 25.12.2 — offset do dwFileFlags a recalcular).

## ⛔ CORREÇÃO + TESTE LIMPO (2026-10-17 20:00, MC 25.12.2 Windows Trial, pilotado com vigia por minuto)

Correções do que esta página afirmou mais cedo hoje: (1) o gateway é **o mesmo binário** do 23.8.2 ao 25.12.2 (24.6.0 e 25.12.2 com tamanho idêntico) e o verificador `zipdsign` ("package is not signed") **sempre existiu** — portanto a assinatura NÃO explica por que o painel não-assinado funcionava no 25.6/Windows e no 25.12.0/macOS; (2) o `.avpi` do De Lá Pra Cá em `PanelSDKPlugins` é **byte a byte** o que o app monta (`integracoes.avpi`, v0.1.98) — o pacote não é o problema; (3) os toggles achados no exe: `/Media Composer/3PDevPanelSDK` e `/Media Composer/GatewayDevMode` ("Bypass Gateway Authorization for Plugin Loader developers. FOR INTERNAL USE ONLY.", presente desde 23.8.2; o gateway tem `SwitchTo`/`handleSwitchTo` e o log "switched to the developer mode").

**Teste limpo** (procedimento do banco: MC fechado → gateway morto → instalar → abrir): instalado um **painel-teste mínimo não-assinado** (`com.usuario.teste.mc`, manifesto no formato dos que funcionam, entradas com `/`), com o **Órbita** (`com.orbita.sync.avpi`, instalado pelo autor) e o **De Lá Pra Cá** também presentes. Menu **Extensions** = **só Quickture e PARCEIRO-Q** (assinados). **Nenhum dos três não-assinados registrou**; o `avid-huddle` (assinado, cadeia antiga de 4 certs, folha vencida em 2025-10-10) também não. Nada no Tools.

⇒ **No MC 25.12.2 / Windows / Trial, painel não-assinado NÃO registra — qualquer um, não é o De Lá Pra Cá.** Contradiz o histórico (25.6/Windows e 25.12.0/macOS carregaram não-assinado). Variáveis ainda não separadas: **versão** (25.12.0→25.12.2 ou 25.6→25.12) × **licença Trial** × Windows. Controle decisivo: instalar o **25.6** nesta mesma máquina (mesma condição de trial) e repetir o teste.

## ✅ CAUSA ACHADA (2026-10-17 20:55, macOS 15.6.1) — o MC 25.12.2 bloqueia painel não-assinado; o 25.12.0 aceita. É VERSÃO, não SO nem licença

Mesmo Mac (Mac mini, licença Pro), mesmo pacote não-assinado `com.usuario.delapraca.mc.avpi` (3072 bytes), lido pelos
menus via acessibilidade (`osascript` / System Events, sem clicar):

| MC (macOS) | menu Extensions | painéis listados |
|---|---|---|
| **25.12.2.59112** | ❌ não existe | só o Avid Huddle (assinado), e no **Tools** |
| **25.12.0.58863** (reinstalado pelo autor) | ✅ existe | **De Lá Pra Cá** (não-assinado) |

- Nas duas versões: nenhum `.ftf` no Mac, `/Library/Application Support/Avid/Support` vazio, build release assinado
  (Team 4UYUA773XD), gateway filho do MC com `--server_bind_address=[::1] --run_tls_server=false --allow_all_origins`.
- O `avid-api-gateway` tem o **mesmo tamanho** (19 777 472 bytes) no 25.12.0 e no 25.12.2 ⇒ a trava nova está no
  **próprio MC** (o host que registra/mostra o painel), não no gateway.
- ⇒ Junta com o Windows (25.12.2 só mostra Quickture/PARCEIRO-Q, assinados): **a partir do 25.12.2 a Avid só registra
  painel assinado**, nos dois SOs. A formatação do Windows foi coincidência; o que mudou foi a versão instalada.
- O teste de 2026-08-07 (Test Panel) foi no 25.12.0.58863 — o autor lembrava 25.12.2.
- **Regra prática:** para desenvolver/usar painel próprio, **ficar no 25.12.0** (ou anterior com runtime: 23.8.2+;
  o 25.6 também aceitava no Windows). Não atualizar o MC de uma máquina de painel sem testar um painel-teste antes.
- Em aberto: (1) o que exatamente o 25.12.2 checa (assinatura do `.avpi`? lista de parceiros? toggle `3PDevPanelSDK`
  que antes vinha ligado?) — comparar `strings` do `AvidMediaComposer` 25.12.0 × 25.12.2; (2) confirmar no Windows
  instalando o 25.12.0 lá.

## 🔬 MECANISMO DA TRAVA DO 25.12.2 + brecha CIT_OVERRIDE FECHADA (2026-10-17 21:20, Mac, diff dos dois instaladores)

Comparei os dois instaladores `.pkg` do Mac (25.12.0.58863 × 25.12.2.59112), peça por peça, e desmontei o exe.
- **O gateway (`avid-api-gateway`) e o `FTF` framework são IDÊNTICOS byte a byte** nas duas versões (só muda a
  assinatura de código da Avid). ⇒ a trava NÃO está neles.
- **Está no exe `AvidMediaComposer`, na rotina `MCLoaderService::GetPluginList(QObject*)`:** o 25.12.2 ganhou um
  ramo novo (símbolo estático `s_devPluginsEnabled`, 6 ocorrências; 0 no 25.12.0) que, **antes de montar a lista de
  painéis, lê `FTF_GetToggle("/Media Composer/3PDevPanelSDK")` e, se a chave estiver DESLIGADA (padrão), filtra e
  descarta todo `PluginData` com o byte de "não-assinado" ligado** (campo em offset 0x18 do PluginData). No 25.12.0
  a rotina monta a lista direto, **sem consultar a chave e sem filtrar** — por isso painel não-assinado aparece lá.
  ⇒ é 100% diferença de VERSÃO (filtro novo no host), não do SO nem do nosso pacote.
- **`3PDevPanelSDK` é lido pelo `FTF_GetToggle` ESTÁTICO** ⇒ vem dos arquivos registrados; a chave está no grupo
  `developer` = `SDKDeveloperToggles.ftf` (tipo 1: cifrado+assinado+amarrado ao systemId — fechado sem a Avid, já
  provado no Windows).
- ✅ **Brecha `CIT_OVERRIDE` FECHADA (responde a dúvida (a) da noite-3):** o override só liga se o HOST chamar
  `FTF_SetOverridePath` ANTES das registrações. O `AvidMediaComposer` **NÃO chama nem importa `FTF_SetOverridePath`**
  (conferido: `nm -u`, desmonte x86_64+arm64, e ausência da string `CIT_OVERRIDE.FTF`/`OverridePath` no exe — só os 3
  `.ftf` padrão). As chamadas FTF do MC são `FTF_Init`, `FTF_RegisterToggle(File)`, `FTF_GetToggle` (1512×),
  `FTF_GetDynamicToggle`/`FTF_SetDynamicToggle`, `FTF_GetOverrideInfoString` (lê info, não seta caminho). ⇒ gerar um
  `CIT_OVERRIDE.FTF` por máquina NÃO adianta para o MC.
- **Conclusão (opção 2 — assinar — descartada pelo autor):** não há arquivo que o dono gere, sem a Avid, que ligue a
  `3PDevPanelSDK` no 25.12.2. Restaria só rota em runtime (`FTF_SetDynamicToggle` por injeção no processo) — e só SE o
  `FTF_GetToggle` estático consultar os dinâmicos (não confirmado); invasivo. **Caminho dependente escolhido: o
  instalador do painel FIXA a versão do MC** (detecta 25.12.2+ e oferece reinstalar o 25.12.0 com o MC fechado).
- A datar ainda: a partir de qual build exato entrou o filtro (25.12.1? 25.6 não tinha; 24.6.0 a confirmar no teste do Windows).

## 📅 TESTE A no Windows (2026-10-18) — o MC 24.6.0 TAMBÉM esconde painel não-assinado

O autor instalou o **24.6.0.58520** no Windows (por cima do 25.12.2). Medido com o MC aberto: gateway rodando
(mesma linha de comando do 25.x), portas 9100 (MC) e 4920/4930 (gateway) de pé, e em `C:\ProgramData\Avid\PanelSDKPlugins`
os pacotes `com.usuario.teste.mc.avpi`, `com.usuario.delapraca.mc.avpi`, `com.orbita.sync.avpi` (não-assinados),
`PARCEIRO-Q_1.0.0.avpi` (assinado) e `quickture.avpi`. **Tools mostra só Quickture e PARCEIRO-Q** (assinados); nenhum
dos nossos. Os manifestos têm o mesmo formato do PARCEIRO-Q (category, uiItems dropdown em "Tools", targetHosts) ⇒ não é
o pacote.

| MC | painel não-assinado | onde |
|---|---|---|
| 23.8.2 | ❌ (nenhum painel, nem assinado) | Windows |
| **24.6.0** | ❌ (assinados ✅ no Tools) | Windows, 2026-10-18 |
| 25.6 | ✅ | Windows (histórico do autor) |
| 25.12.0 | ✅ | macOS (2026-08-07 e 2026-10-17) |
| 25.12.2 | ❌ (filtro `s_devPluginsEnabled`) | Windows e macOS |

⇒ A liberação de painel não-assinado é uma **janela** da linha 25.x (25.6 → 25.12.0), não o comportamento antigo:
o 24.6.0 já bloqueava (por um mecanismo não desmontado; no 23.8.2 o gate era o `3PDevPanelSDK`), o 25.x abriu, e o
25.12.2 voltou a fechar com o filtro novo. **Base para painel próprio no Windows = 25.12.0 (ou 25.6).** Não há
instalador Windows dessas versões na máquina (só 21.12.10, 22.12.9, 23.8.2, 24.6.0, 25.12.2).

## ✅ TESTE B (2026-10-18, MC 24.6.0 / Windows) — o gRPC 9100 responde a cliente EXTERNO SEM token nem painel registrado

Cliente gRPC externo em Python (grpcio; `.proto` do banco separado nos dois arquivos originais pelo marcador
`// === FILE: MCAPI_Types.proto ===` e compilado com `grpc_tools.protoc`), contra `127.0.0.1:9100`, com
`RequestHeader` **vazio** (`company_id=""`, `access_token=""`). Script: `scratchpad/testeb_9100.py`.

| RPC | resultado (header vazio, sem painel nosso no menu) |
|---|---|
| `GetHostInfo` | ✅ `AvidMediaComposer`, user, workstation |
| `GetAppInfo` | ✅ `Perpetual 2024.6.58520` |
| `GetOpenProjectInfo` | ✅ projeto inteiro (caminho, `1080p/23.976`, raster 1920×1080, frame_rate 24000/1001) |
| `GetBins` | ✅ stream respondeu (projeto-teste sem bins abertas → 1 header `Completed`) |
| `GetListOfWindows` | ⛔ `UNIMPLEMENTED` no 24.6.0 |
| `GetListOfCommands` | ⛔ `UNIMPLEMENTED` no 24.6.0 |

⭐⭐ **Conclusão:** o 9100 **não exige token** e **não exige painel registrado/visível**. O filtro de painel
não-assinado (menu Extensions/Tools) esconde só a JANELA do painel; a **automação pelo 9100 sobrevive** em
qualquer versão com runtime. ⇒ o problema da assinatura/visibilidade do painel está **desacoplado** do problema
de operar o MC por fora. Para as operações que não precisam do drag-in (import, `LinkFile`, export, bins,
marcadores, transporte), **não é preciso painel nem assinatura**.

⚠️ **Ressalva de versão:** a disponibilidade de RPC varia por build. O `.proto` é o do 25.12.0; o 24.6.0 devolve
`UNIMPLEMENTED` em `GetListOfWindows` e `GetListOfCommands` (casa com [windows.md](windows.md): `GetListOfWindows`
ausente no 25.6). Mapear o subconjunto por versão é a continuação. [[arquitetura]]

### Subconjunto de RPC do 9100 por versão (reflection, zero efeito colateral) — 2026-10-18

Reflection do `mcapi.MCAPI` responde no 24.6.0 (`scratchpad/mapa_rpc_24.py` roda contra qualquer versão).
**24.6.0 implementa 47 dos 60 RPC** do contrato 25.12. Os **13 ausentes** são o bloco que chegou depois:

| família ausente no 24.6.0 | RPCs |
|---|---|
| transporte | `StartPlay` `StopPlay` `SetPosition` `MakeViewerActive` |
| janelas | `GetListOfWindows` `MakeActiveWindow` `ShowWindow` `GetListOfSequenceTemplates` |
| comandos | `GetListOfCommands` `DoCommand` `IsCommandsEnabled` |
| outros | `DeleteMarkers` `GetListOfJobQueues` |

⇒ **24.6.0 = superfície "grau relink"** (`ImportFile`/`LinkFile`/bins/`GetMobInfo`/`CreateSubClip`/`ExportFile` presentes);
**transporte + `DoCommand` + janelas só no 25.x.** Para dirigir a timeline / revisão de mídia / export de quadro
posicionado, a base tem de ser 25.x — que também aceita o painel não-assinado (25.12.0/25.6), fechando o ponto ótimo.

**Export de quadro (verificação visual):** `GetListOfExportSettings` lista presets de imagem — **`Windows Image NTSC/PAL`**
e **`Macintosh Image NTSC/PAL`** (export de QUADRO). ⇒ `ExportFile` + preset de *Image* é a rota da verificação visual
por API. ⚠️ Mas posicionar a agulha exige `SetPosition` (transporte) — ausente no 24.6.0; logo a verificação visual
por API pressupõe 25.x (ou fallback ImageGrab pilotado). Import/Link/EDL settings no projeto-teste: só `Untitled`/`Default EDL`.

**25.12.0.58863 (macOS, 2026-10-18): 60 de 60** pela reflection, idêntico ao `dados/mcapi.proto`. Header vazio:
`GetHostInfo`/`GetAppInfo` (`PanelSDK_25.12`)/`GetOpenProjectInfo`/`GetBins` (stream) ✅ e — diferente do 24.6.0 —
`GetListOfWindows` e `GetListOfCommands` ✅ (listas completas). No Mac o MC escuta o 9100 em **`[::1]` e `127.0.0.1`**
(no Windows só `[::1]`); o gateway (4920/4930) segue só em `[::1]`. ⚠️ Matriz: Windows 25.12.0 ainda não medido.

**O "oráculo" do painel não se aplica ao De Lá Pra Cá (conferido 2026-10-18):** o `.avpi` dele é só um *loader*
(`static/loader.html`) que navega a webview para a UI servida pelo serviço local (`127.0.0.1:7823`); **o painel não
faz nenhuma chamada ao gateway**. Quem fala com o MC é o serviço Python, direto no 9100 (`servico/avid/mcapi.py`,
~20 RPC: bins, `GetMobInfo`, `LinkFile`, `ImportFile`, `DoCommand`…), decisão de 2026-08-08 em [roadmap.md](roadmap.md)
com relink real medido (100/100 `LinkFile`). Capturar o 4930 durante um relink dele não mostra nada. Um oráculo de
gateway só teria sentido com um painel de TERCEIRO que use o SDK JS (Huddle, Quickture, PARCEIRO-Q).

## ✅ TRILHA DA ASSINATURA FECHADA (2026-10-18, Windows) — o check é CRIPTOGRÁFICO, no gateway, e é CONSTANTE entre versões

Varredura de strings do `avid-api-gateway.exe` (31 MB, Go; `scratchpad/scan_sign.py`). O verificador é o pacote
Go **`zipdsign`** embutido no gateway:

- `zipdsign/lib.(*File).VerifySignature` + `.Digest` + `validDigest` → **recalcula o digest do conteúdo e compara**,
  via `github.com/austdev/goxmldsig` (`NewDefaultValidationContext`, canonicalizadores c14n11/c14n10/exclusive,
  `(*ValidationContext).DecodeRef`). Tipos XML: `Signature`/`Reference`/`DigestMethod`/`DigestValue`/`X509Data`/`Transform`.
- `zipdsign/lib.(*File).VerifyKeyChain` + `crypto/rsa.VerifyPKCS1v15`/`VerifyPSS` + `x509.CertPool` → valida a
  **cadeia do certificado** contra a **`DigiCert Trusted Root G4` EMBUTIDA no binário** (cert completo embutido,
  validade `130801120000Z`→`380115120000Z`); `Avid Technology, Inc`/`Burlington`/`Engineering` também embutidos
  (folha esperada — pin do subject `inferido`, confirmar na fase REA). Flag `failed_dsig` junto de `PluginData`/`manifest`.

⭐⭐ **Veredito:** verificação **criptográfica, não de presença**. Copiar a assinatura do Quickture quebra em
`validDigest` (digest amarrado ao conteúdo dele); auto-assinar quebra em `VerifyKeyChain` (não encadeia na DigiCert G4
embutida, folha ≠ Avid). **Não existe check fraco para satisfazer com assinatura própria** — "assinado" só pela Avid
(programa de parceiro) ou com a chave privada dela (inviável).

⭐⭐ **Recoloca a "janela 25.x":** o gateway é byte-idêntico entre 25.12.0 e 25.12.2 ⇒ a verificação **nunca mudou**;
sempre rodou e sempre marcou o nosso painel como não-assinado. O que varia entre versões é a decisão do **host**
(`AvidMediaComposer.exe::GetPluginList`) de **esconder** do menu o que o gateway marcou como não-assinado (filtro
`s_devPluginsEnabled`/`3PDevPanelSDK` presente no 24.6.0 e 25.12.2, ausente no 25.12.0). A "janela" é real, mas é sobre
a **política de exibição do host**, não sobre a assinatura. Confirma a dúvida do autor pelo avesso.

**Para a fase REA:** saltar direto para `zipdsign/lib.(*File).VerifySignature`/`.VerifyKeyChain` no gateway (Go, símbolos
preservados) e para `MCLoaderService::GetPluginList` no host — confirmar o pin do subject Avid e ler o ramo exato do filtro.

## 🖥️ MC 24.6 OPERADO POR FORA, pelo app (2026-10-18, Windows 11, MC 2024.6.58520, `confirmado` medindo)

O De Lá Pra Cá passou a abrir o MESMO painel (`/painel?nle=mc`) numa janela do app (Tauri, same-origin com o
serviço), sem o Avid hospedar nada. Medido no 24.6, que esconde o painel não-assinado:

- **Painel fora do Avid funciona**: "conectado", e "Carregar a sequência aberta" leu a timeline do Record pela API.
- **9100 também em `127.0.0.1`** nesta medição (antes, no mesmo Windows, só `[::1]`). Vigiar os DOIS endereços.
- **Reflection à mão**: `ServerReflectionInfo` com `file_containing_symbol: "mcapi.MCAPI"` (pedido montado em bytes,
  `FileDescriptorProto` lido pelo `protobuf`) → 47 RPC em 48 ms, sem o pacote `grpcio-reflection`
  (`_DeLaPraCa/.../avid/mcapi.py` `rpcs()`/`tem()`).
- **Sem `DoCommand` ⇒ sem Save. O `CloseBin` SALVA:** bin nova + `LinkFile` → disco com 0 mobs; depois do `CloseBin`,
  3 (master + fontes). `ImportFile` de AAF numa bin: 0 → 2 `CompositionMob` no disco só depois do `CloseBin`.
- **⚠️ Fechar a bin TIRA do monitor a timeline que mora nela** (Composer e Timeline vazios, conferido em foto) e
  reabrir não a devolve. `LoadMobsIntoViewer` depois volta **no mesmo quadro** (o MC lembra a posição por sequência).
  Ciclo fechar + abrir + carregar = **0,21 s**. ⇒ Save da bin do EDITOR no 24.6 = esse ciclo; bin já fechada = o
  disco já é o último Save (não tocar: `GetListOfBinItems` responde "Bin is not open.").
- **`GetViewerMobs` do 24.6 NÃO preenche `view_type`**: a timeline no Record vem como 0 (no 25.x, 0 = Source).
  `LoadMobsIntoViewer` com `view_type=1` põe no Record. ⛔ Com `view_type=0` e um MASTER, num Composer de monitor
  único, o MC **criou uma sequência `<master>.new.01`** na bin do master — e ela NÃO aparece no filtro `sequences`
  do `GetListOfBinItems`. Critério para "a timeline aberta" no 24.6: o mob do monitor que está no filtro
  `sequences` da própria bin (`GetBinFromMob`).
- **⛔ `LinkFile` recusa caminho com acento/cedilha** ("cannot be linked", ErrorType 66): o MC lê o UTF-8 como
  **MacRoman** (`AÇÃO` → `A√á√ÉO` na mensagem). O MESMO arquivo com nome ASCII linka. Nenhuma forma passou:
  `file:///` com percent-encoding (`ID_FILENAME_SYNTAX`, ErrorType 1000), percent sem esquema, NFD, barras `/`;
  bytes MacRoman no fio → `INTERNAL: Unable to parse request` (o servidor valida UTF-8). Nome curto 8.3 não existe
  em exFAT (o SSD de trabalho). ⚠️ Matriz: 25.6/25.12 **não medidos** para acento no `LinkFile` — o "PATÃO DRONE"
  que ficou de fora no relink do PRODUCAO-A (25.6, 2026-10-13) pode ser o mesmo defeito. Medir antes de concluir.
- `CreateSubClip` de um MASTER com `create_new_sequence=True` cria só o subclipe (nenhuma sequência).
- 🆕 **`LoadMobsIntoViewer` no Source PENDURA o MC** (2026-10-21, projeto DLPC PRODUCAO-A 2024, Composer com Source e
  Record): o master entra, mas a janela fica `IsHungAppWindow` e a resposta chega em **~30 s** (AMA H.264 de 42 min e
  de 3–7 h) — acima dos 20 s de prazo de consulta, e uma 2ª chamada no meio do travamento também estoura. Nesta
  máquina o monitor mostrava `std::exception` no lugar da imagem (o EVENTLOG tem `VDMerror HWSDK_BobDevice` na partida
  — hardware de vídeo), o que pode ser a causa da demora; não separado. Nenhuma `.new.01` nasceu (Composer de DOIS
  monitores; o `.new.01` medido antes foi no de monitor único). ⇒ Ciclo Assist: prazo próprio de 90 s
  (`rotas.TEMPO_DE_CARREGAR_S`).
- 🆕 **`GetViewerMobs` devolve para o Source um mob que NÃO é o master carregado** (mesma sessão): carregado
  `…0101000101 0f0013-…b297c16a…` (o master), o Source responde `…0101050101 0f1013-…2cc35d44…` (outro mob, tipo de
  composição). O MC embrulha o master num mob do monitor. ⇒ "o que está no Source é o X?" não se responde comparando o
  id; o Record (a sequência) volta com o id dela. `hipotese` sobre o que é esse mob — não está em bin nenhuma pelo
  `GetListOfBinItems` (AllTypes, 65 antes e depois).
  ✅ Medido depois (mesma sessão): o embrulho é um mob SEM bin (`GetBinFromMob` → "Bin not found", ErrorType 69),
  1 trilha de vídeo + 1 de áudio com 1 segmento cada (`GetMobTrackInfo`), id NOVO a cada carregamento; carregar o
  MESMO master de novo → `Some mobs was skipped.` em 0,7 s e o embrulho fica igual. ⇒ Quem carregou pode lembrar o
  par (master → embrulho) lendo o monitor depois da pausa de 3 s — o Ciclo Assist faz isso (`rotas._EMBRULHOS`), e
  "já está no Source?" passou a responder certo (1,0 s). Carregar levou de 30,5 s a **60,5 s** em clipes da mesma bin.
  ⚠️ Nesta sessão a janela do MC estava maximizada e o monitor seguia em `std::exception` — não é a janela solta de
  2026-10-12 ([[windows]]); `VDMerror HWSDK_BobDevice` na partida é o suspeito, não confirmado.
- 🆕 **`LinkFile` é ASSÍNCRONO no 24.6 — a "rajada" é o MC ocupado** (`confirmado` 2026-10-21, projeto novo "ORBITA DEMO
  D02", 26 MP4 H.264 + 24 BWAV da D02 da PRODUCAO-A, pilotado). O RPC volta em **~0,1 s** quando aceito; o MC linka
  DEPOIS, com o diálogo de progresso "Linking clips, processing <arquivo>". Um `LinkFile` mandado enquanto esse diálogo
  está aberto volta **"cannot be linked" (ErrorType 66) em 7 s ou 30 s** — o MESMO texto do acento e do RAW sem plugin
  (terceira causa da mesma mensagem). Sem esperar: 17/26 na 1ª volta, 23/26 com 3–6 s de pausa. **Esperando o MC
  sem diálogo (`olhos.dialogos` vazio) antes de cada chamada: 26/26 de primeira.** ⇒ quem linka em lote espera o
  progresso fechar, não um tempo fixo.
- 🆕 **O modal "Audio Start-Time Options" do BWAV, desenhado** (mesma sessão): *"The file "<nome>" contains a start time.
  How do you want the start time imported?"*, combo **Select ▾** (Select · 23.98 · 24 · 25 · 29.97 DF · 29.97 NDF · …),
  File TC/Start TC em `--:--` até escolher a taxa (aí mostra o TC do `bext`, ex. 11:24:31:00), botões **OK** e
  **OK to All**. Janela 382×239 (no 1080p ela abriu em 769,400); relativos ao canto: combo (83,103), item 23.98 (63,151),
  OK (72,215). O `LinkFile` FICA PENDURADO até a resposta (a chamada só volta depois do OK). Um WAV por chamada ⇒ um
  modal por WAV (o "OK to All" não foi testado entre chamadas). 24 WAVs pelo piloto: ~4 s cada, todos em 23.98.
  ⚠️ Abrir o combo e escolher têm de ir no MESMO passo: um `frente()` entre os dois fecha o menu e a escolha não pega.
- 🆕 **Depois do `/avid/montar` do Órbita a TIMELINE fica EM BRANCO** (mesma sessão): a sequência entra no Record (nome
  e TC certos, imagem no monitor depois de um Home), a timeline mostra os cabeçalhos V1/A1–A7 e **nenhum clipe, nem a
  régua** — mudar o zoom não resolve; **duplo clique na sequência da bin desenha tudo**. Causa `pendente` (o
  `LoadMobsIntoViewer` com `view_type=Record` do 24.6, que não preenche `view_type`, é o suspeito). [[windows]]
- 🆕 **Save Bin no 24.6 = `CloseBin` + `OpenBin`, também para RENOMEAR** (`confirmado` 2026-10-21, Órbita): `SetMobInfo`
  em 26 subclipes, `DoCommand` recusado (`UNIMPLEMENTED`), fechar e reabrir a bin → releitura do `.avb` com os 26 nomes
  novos (`confirmado: True`), e o desfazer pelo mesmo caminho. Antes de fechar, guardar as sequências da bin que estão
  num monitor e devolvê-las ao Record depois (fechar tira a timeline do monitor). O Órbita grava assim também a bin
  do sync e a de subclipes logo ao abri-las (43K → 588K no disco).
- 🆕 **`frente()` na janela principal do MC devolve a aba de bin que estava ATIVA** (mesma sessão): clicar a aba "SOM
  DIRETO" e, em outro passo, `frente()` + Ctrl+A selecionou a CAM A. Trocar de aba e agir no mesmo passo.
- **Relink do PRODUCAO-A pela janela do app (2026-10-18, MC 24.6, projeto novo "DLPC PRODUCAO-A 2024", AAF
  `PRODA_RELINKER_ALTA`, 118 masters):** fluxo inteiro sem diálogo nem travamento (leitura 16 s, relink ~45 s), pasta
  `_SEQ/_MIDIAS/_AAF`, timeline no Record, 54 áudios autorados. ⛔ Os 43 `.BRAW` = "cannot be linked" (ErrorType 66,
  o MESMO texto do acento): **faltava o plugin AMA de Blackmagic RAW** — sem `C:\Program Files\Avid\AVX2_Plug-Ins\AMA\BlackmagicRAW`
  num Windows recém-formatado (o Blackmagic RAW estava instalado só para o Resolve). Mesma mensagem, causas diferentes:
  o app separa pelo caminho (não-ASCII) e pela extensão (RAW de câmera). [[raw-de-camera-e-sdk]]
- **Export de quadros por MARCADORES funciona no 24.6** (2026-10-18, PRODUCAO-A relinkado, 38.133 quadros): bin
  `_DLPC` + `DuplicateBinItems` + `MoveBinItems` (o Record do editor não se mexe) → 32 `AddMarker` na **TC1**
  (`track_label {type: 2, number: 1}`, `length=1`, `comment="DLPC qNNNNN"`) → `LoadSetting` do molde `DLPC-JPG.xml`
  com `iSequentialFiles` TRUE e `ATN_ES_SEQ_FILES`/`ATN_EXPORTLOCATORFRAMES`/`ATN_USE_LOCATOR_COMMENT`/
  `ATN_USE_TOPMOST_IMAGE` = 1, nome `0-DLPC-QUADROS-<hora>` → UM `ExportFile` (volta "Completed" em 0 s; os 55 JPEGs
  saem em ~5 s — esperar a pasta parar de crescer, não o retorno). ⚠️ Sem `DeleteMarkers` a cópia leva os 23
  marcadores do editor: saem JPEGs com o comentário deles (e `NNNN.jpg` para marcador sem comentário) — filtrar pelo
  prefixo. `GetMarkers` existe no 24.6 (traz trilha, offset, TC, comentário, cor, autor).
- **Conferência pela referência (mesmo dia):** os 32 quadros × `PRODA_CORTE.02.mov` (38.133 quadros, TC 01:00:00:00)
  com `conferir_conform.comparar_um` nos deslocamentos −2…+2: nos pontos com movimento o deslocamento 0 vence
  sozinho (ex.: q01412 0,999 contra 0,915/0,909), nenhum ponto abaixo de 0,9 no 0; o quadro 0 é preto nos dois
  (o "quadro vazio" da timeline está na referência). ⇒ referência exata, quadro a quadro. ⚠️ Ler a referência por
  tempo pedindo (N − 0,5)/fps: com N/fps exato o arredondamento pode pular para o quadro seguinte.
- **Teste de fogo PRODUCAO-C (R04) Premiere → Avid pelo motor, MC 24.6 (2026-10-18)** — `.prproj` isolado →
  `LinkFile` do vídeo + áudio INJETADO (`avb_bin.audio.autorar_masters`) → `translate.build_avb(origem="premiere")`:
  - ⛔ `LinkFile` de **Broadcast WAV com TC** abre o modal **"Audio Start-Time Options"** (pede a TAXA para ler o TC:
    23.98/24/25/29.97…; "OK to All" NÃO cobre a chamada seguinte da API) e trava a API até alguém responder. ⇒ áudio
    sempre injetado (é o que o relink já faz). O diálogo não tem dono (`tem_dono` False): vigia que olha só
    diálogos com dono não o vê — listar as janelas VISÍVEIS do processo (`InternalGetWindowText`, sem mensagem).
  - ⚠️ `LinkFile` em rajada: 19 de 48 "cannot be linked" (ErrorType 66); repetidos com 3 s de pausa, 14 passaram (os que
    passam voltam em 0,1 s — o MC processa depois). 5 `.mov` H.264 25p da mesma câmera dos que passaram falham SEMPRE
    (7 s ou 30 s), mesma estrutura no ffprobe — causa em aberto.
    ⚠️ CORRIGE (2026-10-18, noite): não é do arquivo — num projeto novo os 13 `PRJ-0006` linkaram (0,1 s cada)
    e os clones injetados também abrem (`protocolos/avb/escrita.md` §"Linka o primeiro, injeta os irmãos"). A
    recusa era do estado daquele projeto; causa segue aberta.
  - 2 WAV sem molde de áudio: 24-bit 4 canais e 24-bit 1 canal (`LOCAL-3-001`, `FAIXA-W-C4-002`).
  - A sequência (1591 q, 6 V, 14 A) abre na bin, mas `LoadMobsIntoViewer` → **`CM_OFFSET_OUT_OF_RANGE`** (ErrorType
    1000) e o monitor mostra o texto no quadro 00:00:04:23 — ali há fonte de 60 qps a 36 % (V2), Collapse com
    velocidade de 2,6 % sobre AMA de 25 qps (V3). Isolar por bissecção (variantes com trilhas/segmentos vazios).
  - ✅ **Causa do `CM_OFFSET_OUT_OF_RANGE` achada por BISSECÇÃO pela API** (variantes da sequência com trechos trocados
    por Filler, cada uma numa bin nova com MobID novo; `LoadMobsIntoViewer` devolve o erro na hora — 28 variantes,
    ~2 min, sem clique): um clipe só — rampa de 60 qps dentro de um nest com `source_offset_map` começando em −0,36 (fase
    do Premiere). O escritor o tomava por ré e caía no motion genérico, que grava o início em quadros da FONTE numa
    trilha na taxa da TIMELINE. Corrigido no app (`translate._entry_outra_taxa`, De Lá Pra Cá `9b8b120`). ⭐ A técnica
    serve para qualquer sequência recusada pelo MC.
  - Depois da correção, a sequência carrega; o monitor mostrou `PGLUE_IMPOLITE_PORT_NUMBER` parado no quadro 119 (não
    impediu o export). **Checkpoint por marcadores** (32 quadros × `PRODC_Trailer_v02_RESGATE.mov`, alinhada no deslocamento
    0): 17 conferem; pretos = os 5 `.mov` não linkados; diferenças = escala/posição do Motion (não traduzido), cor
    (Lumetri/LUT) e máscara/composição (nest com máscara por cima).

## Entrega da timeline no MC 24.6: monitor de trilha, monitor errado e o PGLUE (2026-10-18, noite)

- ⭐ **Sem o monitor de trilha ligado, o MC não mostra imagem NENHUMA** (o quadradinho à esquerda de V1…Vn; ligado
  numa trilha, mostra ela e as de baixo). Característica exclusiva do MC (autor). A `INJ 1_SEQ` entregue pelo relink
  saiu com todos desligados — monitor preto lido como "offline" é diagnóstico errado: os 71 segmentos resolviam até o
  arquivo. ✅ O estado é o `session_attr` `_MONSTATE=1` (já no banco: `protocolos/avb/dados/track-session-attrs.json`
  — eu procurei em `attributes`). Corrigido no app (`8c48e53`, `visibilidade.garantir_monitor` + `translate.py`): a
  `INJ 2_SEQ` abriu mostrando a imagem.
- ⛔ **No 24.6 o `LoadMobsIntoViewer` ignora o Record** (medido 2026-10-18, noite): `view_type=1` e `view_type=0`
  carregam no MESMO monitor (o Source, segundo o autor) — a sequência substituiu o master que estava lá; com o
  monitor da direita ativado por clique, idem; `view_type=2` abre o popup. Recarregar o que já está no monitor dá
  "Some mobs was skipped." (ErrorType 1000). Sem `MakeViewerActive` nem `DoCommand` no 24.6, não há caminho pela
  API para o Record. ⚠️ Corrige a nota acima ("`view_type=1` põe no Record"): o `GetViewerMobs` do 24.6 diz 0 porque
  a sequência ESTAVA no Source.
- `PGLUE_IMPOLITE_PORT_NUMBER` no monitor com o monitor na V6, no quadro 119 (00:00:04:23) da
  `PRODC_Trailer_v02_RESGATE`: lá começa um `EFF_ADV_MOTION_CTL` (adaptador de taxa 60p → 23,976 do escritor da bin)
  sobre o `JUL_7644`. O MESMO quadro deu o mesmo erro na sessão da tarde com a mídia toda pelo `LinkFile` ⇒ é do
  efeito escrito, não da injeção. Causa: `pendente`.
