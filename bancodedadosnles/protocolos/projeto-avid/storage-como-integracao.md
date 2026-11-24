# Bin locking de verdade — e o terceiro eixo de integração: ficar EMBAIXO do app

Oitavo caso da técnica [`../../transversal/analise-de-executaveis.md`](../../transversal/analise-de-executaveis.md),
e o primeiro em que o produto analisado **não é um plugin**.

**Material:** `Mimiq` 1.x (Windows, `.exe` → CAB → MSI) e `Osiris 2` 2.1.6 (macOS, `.pkg`), de
`PROGRAMAS ANALISAR/bin lock/`. Nunca haviam sido abertos. Analisados em 2026-08-24.

> ⭐ **Por que valia abrir:** o [README](README.md) desta pasta marca a semântica do `.lck` como
> **`hipotese` de propósito**. Quem vende lock comercial sabe a semântica — e o binário deles é a
> documentação que falta.

---

## 1. ⭐⭐⭐ O achado: existem DOIS mecanismos de lock, e o banco só conhecia um

O banco documenta o **`<bin>.lck`** — arquivo que o MC cria ao abrir a bin e apaga ao fechar, sem
PID nem timestamp. Isso é o lock de **pasta compartilhada comum**.

**Não é assim que o Avid faz em shared storage.** O módulo `AvidSharedStorageAccess` do Mimiq expõe
a API do cliente de armazenamento da própria Avid, e ela tem o lock como **conceito de primeira
classe**, com nome próprio: **`Flock`** (*file lock*).

```
ASIsFlockPresent          ASGetFlockList_UTF8 / _UTF16
ASGetFlockWSList_UTF8 / _UTF16
?GetFileLock@AWinFileSystemObject@@QEAA_NXZ     ← C++ mangled, do FS object
```

⭐⭐ **Consequência para o banco:** o `.lck` é o mecanismo **degradado**, de quando não há shared
storage. Em NEXIS/Avid Shared Storage o lock é **do cliente de armazenamento**, consultável por API
(`ASIsFlockPresent`), com lista (`ASGetFlockList`) e associação a workspace (`ASGetFlockWSList`).
Um app pode **perguntar quem tem o lock** — coisa que o `.lck`, sem PID nem timestamp, não permite.

⚠️ Isso **não invalida** o que a pasta já registra sobre o `.lck`; **delimita**. As duas metades
convivem, e o `hipotese` do README continua de pé para o caso do `.lck` — o que mudou é que agora
sabemos que ele não é a história inteira.

E há um canal de notificação: **`/Media Composer/NewBinSharingMsg`** — o MC é *avisado* sobre
compartilhamento de bin, não fica só olhando o disco.

---

## 2. ⭐⭐⭐ O terceiro eixo de integração

O [mapa de operações](../../transversal/operacoes-de-nle.md) conhecia dois jeitos de um software
externo agir sobre um NLE:

1. **Dirigir o app pela API** — CEP, Panel SDK, scripting.
2. **Escrever os arquivos do app** — AAF, `.avb`, `.prproj`, `.drt`.

Estes dois produtos revelam o terceiro, e nenhum dos onze anteriores usava:

3. ⭐⭐ **Ficar EMBAIXO do app — apresentar-se como o ARMAZENAMENTO que ele espera.**

Nenhum dos dois fala com o Media Composer. Os dois fazem o armazenamento comum **parecer** Avid
Shared Storage, e o MC então liga o bin locking sozinho, porque acredita estar em shared storage.

⭐ **O nome do produto conta a estratégia:** *Mimiq* — ele **mimetiza**.

### Como cada um faz

| | Mimiq (Windows) | Osiris 2 (macOS) |
|---|---|---|
| stack | **.NET** (`Mimiq.pdb`, `Microsoft.Windows.SDK.NET`) | **Qt** (`osiris2`, 5,9 MB) |
| peça-chave | módulo **`AvidSharedStorageAccess`** (3,2 MB) | **`pamFS`** — variante de **macFUSE** com `.kext` + `.appex` |
| como monta | **`ASMountWorkspace` / `ASMountWS`** — a própria API da Avid | **`BindfsMount`** — *bind mount* de um caminho como volume |
| descoberta | `Workspaces.ScanForWorkspaceDirectories`, procurando pastas **`Avid MediaFiles`** | usuário escolhe caminho + nome de volume |
| privilégio | instalação MSI | `.kext` + helper privilegiado (`ContinuumtransfunctionerHelper`, launchd) |

⚠️ **O Osiris não é um app solto: é cliente de uma plataforma.** A lista de capacidades licenciadas
no binário inclui `BinLocking` ao lado de `ArchivePlugin`, `AuthenticationPlugin`,
`ProjectMetadataPlugin`, `LibraryProjects`, `Deduplication`, `ExtendedArchive` — e os nomes de
produto **`strawberry`, `spycer`, `osiris`**. O lock é **arbitrado por servidor**, não inventado na
máquina.

O próprio binário se descreve: *"Osiris — a lightweight client that enables Avid editors to
collaborate on Media Composer projects simultaneously."*

⭐ **Mimiq resolve local, Osiris resolve em rede.** Duas respostas ao mesmo problema, em camadas
diferentes — e nenhuma delas passa por API de plugin.

---

## 3. Restrições concretas, lidas nas mensagens de UI

Da tabela de localização do Mimiq (9 menções a "Media Composer"):

- ⭐ **`"No drive letter available to mount a Workspace."`** — no Windows, um workspace precisa ser
  **letra de unidade**, não caminho. E há `"Mimiq remount {0} with a drive letter?"`.
- **`"Unsupported Media Composer Version"`** e **`"Install Media Composer before using {0}."`** — o
  produto **detecta a versão do MC** e recusa build não suportada. O acoplamento à versão é real.
- **`"Bin Locking is not working. Try reinstalling {0}."`** — o estado *ligado mas não funcionando*
  existe e é comum o bastante para ter mensagem própria.
- `"The parent drive for this Workspace can no longer be found."`
- Estados de produto: `Bin Locking activated` / `deactivated`, `Add Workspace`, `Adding Workspaces`.

⭐ **`Avid MediaFiles` é o sinal de reconhecimento**: o `Workspaces` varre volumes procurando essa
pasta para decidir o que é workspace (`<foundAvidMediaFiles>`). Bate com o que a pasta
[`../msm/`](../msm/) já sabe sobre o layout de mídia gerenciada.

---

## 4. O que isto abre para qualquer app nosso

1. ⭐⭐ **Perguntar o lock por API em vez de olhar o `.lck`** — onde há shared storage,
   `ASIsFlockPresent` / `ASGetFlockList` respondem *quem* e *o quê*. Um app que hoje adivinha por
   presença de arquivo poderia **saber**. (⚠️ `pendente`: como se chega a essa API sem ser o cliente
   oficial — é DLL da Avid, e não medimos se é redistribuível ou acessível.)
2. ⭐ **Reconhecer workspace por `Avid MediaFiles`** é heurística barata e usada em produção.
3. ⚠️ **Acoplamento a versão do MC é inevitável** até neste nível — os dois produtos checam versão.
4. ⭐ **O eixo "ficar embaixo" existe e é legítimo.** Quando a API do app não expõe o que se precisa
   (e no Avid ela expõe pouco), **mudar a camada** é alternativa real a insistir na API.

---

## ⚠️ A régua desta rodada

Régua vigente (revisada em 2026-08-24): leitura integral permitida, registro de **mecanismo**.

- **O que foi lido:** metadados de pacote (`PackageInfo`, `Distribution`, `Info.plist`), nomes de
  `.pdb`, tabelas de exportação, símbolos C++ e strings de interface. **Nenhum código foi
  descompilado** — não foi preciso: os nomes de símbolo entregaram a arquitetura inteira.
- ⭐ **O `.pdb` identificou tudo** num MSI que renomeia arquivos para hash — exatamente o que a
  §Receitas da técnica previa (`AvidSharedStorageAccess.pdb`, `Mimiq.pdb`, `Workspaces.pdb`,
  `Localization.pdb`).
- ⚠️ **Falso positivo evitado:** `OMFI` aparece 4× no binário do Osiris e **não é OMFI** — são
  fragmentos de símbolos C++ mangled de `LicenseHandler`. *Contar ocorrência sem ler contexto teria
  produzido um achado inventado.*
- ⛔ **Licenciamento não foi examinado** (`LicenseHandler`, `Fsle::LicenseEnforcement`,
  `MachineIdentifier` no Osiris) — fora de escopo sempre.
- **Nada instalado, nada executado.** ⚠️ Nenhum `.kext` foi carregado, nenhum volume montado.
- **Não foi feito:** o `pamfs.fs` (o filesystem em si) não foi analisado; o protocolo Osiris ↔
  servidor Strawberry/Spycer não foi mapeado; o payload do Osiris tem 385 arquivos e só a espinha
  foi lida.

## Buracos que ficam

| # | pergunta |
|---|---|
| 1 | Como um app de terceiro alcança `ASIsFlockPresent` — DLL da Avid é redistribuível? |
| 2 | O `.lck` e o `Flock` coexistem no mesmo volume, ou são exclusivos? |
| 3 | O que trafega em `/Media Composer/NewBinSharingMsg` |
| 4 | Protocolo Osiris ↔ Strawberry/Spycer |
| 5 | O `pamfs.fs` — o que ele implementa além de bind mount |
