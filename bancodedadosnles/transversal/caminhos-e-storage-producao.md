# Caminhos e storage em produção — como o original é referenciado e onde ele mora

Transversal porque **qualquer** app que precise sair de um projeto de NLE e chegar no **arquivo
original em disco** atravessa isto: as formas de URL que o NLE grava, o layout real do storage de
produção, e a identidade de volume que decide se dá para linkar sem copiar.

Descoberto no `LOCALIZADOR_DE_MIDIA_PELO_AAF` (2026-08-17) com AAF real do *PRODUCAO-Q* e teste
em ambiente real de produção (Emissora). Complementa — não repete — o layout da `Avid MediaFiles`, que
está em [protocolos/mxf/README.md](../protocolos/mxf/README.md).

---

## 1. Formas de URL que o Avid grava no AAF (`confirmado`)

O `URLString` do `NetworkLocator` (em `EssenceDescriptor.Locator`) aparece em **cinco formas
irregulares no mesmo arquivo**. Um parser que trate só uma delas perde metade do acervo.

| forma no AAF | vira | onde apareceu |
|---|---|---|
| `file://SERVIDOR/share/pasta/arq.mxf` | `\\SERVIDOR\share\pasta\arq.mxf` | Nexis, ingest |
| `file://SERVIDOR//volumes/x/y.mov` | idem, **colapsando `//` do path** | VFX edit-in-place |
| `file:///VOLUME/pasta/arq.mov` | `/VOLUME/pasta/arq.mov` (POSIX/volume Mac) | ingest visto do Mac |
| `file:////C/Users/x/arq.mp4` | `C:\Users\x\arq.mp4` (**letra sem dois-pontos**) | import de estação Windows |
| `file:///C:/Users/x/arq.mp4` | `C:\Users\x\arq.mp4` | import de estação Windows |
| 🆕 `file:///D%3A/LINK%20ATALHO/arq.mxf` | `D:\LINK ATALHO\arq.mxf` (**`:` percent-encoded**) | import de estação Windows |

### 🆕 São SETE, contando o `.avp` (2026-08-23)

Reextração de `MIDIAS DE TESTES/01 - telas fotoblog minidv.aaf` (o mesmo AAF do *PRODUCAO-Q*, 107 locators) mais um segundo AAF local, no `DRAMASYNC`:

⚠️⚠️ **As duas grafias de letra de unidade convivem no mesmo acervo** —
`file:////C/Users/…` (quatro barras, letra **sem** dois-pontos) e `file:///D%3A/…` (três
barras, dois-pontos **percent-encoded**). Um parser que trate só uma **falha calado** na
outra: não levanta erro, só devolve caminho que não existe.

⚠️ **E há uma sétima forma, fora do AAF:** os `WINF`/`WinFileLocator` dentro do `.avp` usam
`letra + // + barras normais` — `Y//_Jobs/PRODUCAO-A/…/OC-Corte_00.avb`. Ver
[../protocolos/projeto-avid/README.md](../protocolos/projeto-avid/README.md), que também
avisa: um `.avp` guarda **saves anteriores não truncados** depois do fim da tabela de
objetos, então um `grep` de caminhos ali colhe **caminhos-fantasma de onde o projeto morava
antes**.

Contagem dos sinais nos 107 locators do AAF do Nexis, para calibrar quem for escrever o
parser:

| sinal | quantos |
|---|---|
| percent-encoding | **107/107** |
| tudo em minúsculas depois do host | **99/107** |
| acento **cru** convivendo com `%20` na mesma string (`Cena%2011%20-%20…Opções%204x3`) | 1 |
| barra dupla no meio do caminho | 4 |

⚠️ O acento cru ao lado de `%20` **na mesma string** é o caso que quebra quem assume
"ou está tudo codificado, ou nada está".

### A pegadinha que custou um bug: percent-encoding

**Todas** as URLs vêm percent-encoded: `avid%20mediafiles`, `DIGITACAO%20TEXTO%20v4.mov`. Um filtro
que procure `"avid mediafiles"` na URL **crua nunca casa** — e o resultado é a mídia gerenciada do
Avid vazando como se fosse o original. `unquote()` **antes** de qualquer comparação.

### A barra dupla depois do host

`file://servidor-vfx.emissora.exemplo//volumes/edit_in_place/...` — o path começa com `//`.
Concatenar ingenuamente dá `\\host\\volumes\...` (barra dupla no meio), que é caminho inválido.
Colapsar `/{2,}` no path antes de montar a UNC.

### O mesmo arquivo aparece em DUAS caixas diferentes

O mesmo `.mov` foi visto como `.../pedro_e_nina/2026-07-30/digitacao texto v4.mov` (no
`CDCIDescriptor`) e `.../PEDRO_E_NINA/2026-07-30/DIGITACAO TEXTO v4.mov` (no `ImportDescriptor`).
**Comparação de caminho e de nome tem de ser case-insensitive**, sempre.

Implementação de referência: `LOCALIZADOR_DE_MIDIA_PELO_AAF/app/aaf_reader.py::url_to_path`.

---

## 2. Layout do storage de produção (`confirmado` para os caminhos lidos)

Cinco famílias distintas no **mesmo projeto** — é a razão de um app de coleta não poder assumir um
storage só.

### 2.1 Mídia gerenciada do Avid (Nexis) — **nunca é o original**

```
\\NEXIS-01-A\<projeto>\avid mediafiles\mxf\<workspace>.<n>\<nome-truncado><track>.<hash>.mxf
```

`<workspace>` visto: `srvegpaws295875.1`, `srvegpaws277417.1`, `srvegpaws308593.1`,
`srvegpaws345060.1` (host `.n`) e `ilha_eg_offline_25.1` (ilha de edição `.n`).

⚠️ **O nome do clipe vem TRUNCADO no nome do MXF** (`inferido`, mas consistente em 40+ amostras):
`6K_F017_260615_UPP05` → `6k_f017_26v01…`; `WhatsApp Video 2026-07-21 at 17.26.11.mp4` →
`whatsapp video 202eae20c0ba.mxf`. Logo **não se recupera o nome do clipe a partir do nome do MXF
gerenciado** — use o `MobName`/`MasterMob` ou o `.mdb` (ver [protocolos/msm/](../protocolos/msm/)).

Sufixo antes do `.mxf` marca a track: `…v.mxf` = vídeo, `…a.mxf` = áudio; e há a forma
`<nome>v01.<hash>.<n>.mxf`. Detalhes de agrupamento em
[protocolos/mxf/README.md](../protocolos/mxf/README.md).

**Para busca de originais, essa árvore é ruído**: podar por `avid mediafiles`, `omfi mediafiles`,
`avid attic` (case-insensitive, após `unquote`).

### 2.2 Ingest de cartão de câmera

Visto do **Mac** (é a estação que ingere):

```
/Macintosh HD/Volumes/INGEST/<PROJETO>/MEDIA_PRODUCER/Externa/<MM-MÊS>/<MM-DD>/<CARTÃO>/<arquivo>
```

Exemplo real: `/Macintosh HD/Volumes/INGEST/PEDRO_E_NINA/MEDIA_PRODUCER/Externa/06-JUNHO/06-15/4K_CYBERSHOT_260611_UPP05/DSC03652.JPG`

O **mesmo** storage visto do **Windows**: `\\servidor-ingest\ingest\<projeto>\…`, mapeado em `P:`.
Note `MM-MÊS` com o mês em português (`06-JUNHO`) e `MM-DD` como pasta de dia.

### 2.3 Arte / telas (assistente de pós)

```
Q:\ASSISTENTES_POS\<ASSISTENTE>\<PROJETO>\ARTE\TELAS\<Cena NN - descrição>\<arquivo>.mp4
```

Exemplos: `…\ARTE\TELAS\Cena 56\Cena-56-desktop-lan-house-nina-3.mp4` e
`…\ARTE\TELAS\Cena 11 - Hotel - Opções 4x3 e 16x9\Computador-Hotel-Nina-Cena-11-wide.mp4`.
⚠️ Pasta com **acento e caracteres de largura variável** (`Opções`, `4x3 e 16x9`) — normalizar
Unicode (NFC) ao comparar, senão o mesmo nome divergindo entre NFD do macOS e NFC do Windows não
casa.

### 2.4 VFX edit-in-place

```
\\servidor-vfx.emissora.exemplo\volumes\edit_in_place\vfx_edicao\<projeto>\<AAAA-MM-DD>\<arquivo>.mov
```

Visto do Mac como `/EDIT_IN_PLACE/VFX_Edicao/<PROJETO>/<AAAA-MM-DD>/`. Pasta do dia em ISO aqui —
convenção **diferente** da do ingest (§2.2). Há subpasta por tipo (`…/2026-07-30/digitacao/`).

### 2.5 Import de estação (o caso solto)

`C:\Users\<usuário>\Downloads\<arquivo>.mp4` — material que entrou pela máquina de alguém. **Não é
localizável em nenhuma raiz de rede**; um app de coleta tem de tratar como "faltando" e pedir o
arquivo à mão, não tentar adivinhar.

---

## 3. Nome de fita/cartão = nome de pasta no ingest

O padrão do `TapeDescriptor` (mob name) é:

```
<RESOLUÇÃO>_<CÂMERA|ROLO>_<AAMMDD>_<OPERADOR/UPP>
```

| nome de fita | resolução | câmera/rolo | data | posto |
|---|---|---|---|---|
| `4K_CYBERSHOT_260611_UPP05` | 4K | CYBERSHOT | 2026-06-11 | UPP05 |
| `6K_F017_260615_UPP05` | 6K | F017 (rolo) | 2026-06-15 | UPP05 |
| `HD_MINIDV_260613_UPP05` | HD | MINIDV | 2026-06-13 | UPP05 |

⭐ **O nome da fita é o nome da PASTA do cartão no ingest** (`confirmado` para
`4K_CYBERSHOT_260611_UPP05`: no mesmo AAF, o `ImportDescriptor` do `DSC03652.JPG` termina em
`.../4K_CYBERSHOT_260611_UPP05/DSC03652.JPG` e o `TapeDescriptor` do mesmo masterclipe se chama
`4K_CYBERSHOT_260611_UPP05`. `inferido` para os demais, que só têm fita, sem path para cruzar).

**Por que isso vale ouro numa rede lenta:** dá para **priorizar a varredura** pelas pastas cujo
nome bate com a fita. Numa varredura de vários minutos, o material costuma ser achado antes de o
scan terminar. Implementado em
`LOCALIZADOR_DE_MIDIA_PELO_AAF/app/scanner.py::scan_root(priority_names=…)`.

⚠️ A data no nome da fita é a **da gravação/cartão**, não a do dia de ingest — e no ingest a pasta
de dia (`06-15`) coincidiu com a data da fita (`260615`) nas amostras, mas isso **não** foi
verificado como regra.

---

## 4. Identidade de volume (decide hardlink vs symlink vs cópia) — `confirmado`

Para saber se dois caminhos estão no **mesmo volume** (única condição de hardlink):

```python
# \\srv\share\a\b.mxf  →  \\srv\share
# S:\a\b.mxf (mapeado) →  \\srv\share
# D:\a\b.mxf (local)   →  d:
```

⚠️ **A letra mapeada pode apontar para um share ANINHADO.** Medido em produção: `P:` resolve para
`\\servidor-ingest\ingest\pedro_e_nina` — servidor + share + **subpasta**, não servidor + share. Se a via
UNC reduz a `\\srv\share` e a via letra devolve a UNC inteira, **o mesmo storage vira dois volumes
diferentes** e o hardlink grátis é perdido. Reduzir **os dois lados** a servidor+share.

A letra → UNC sai de `WNetGetConnectionW` (`mpr.dll`); devolve erro para drive local.
Referência: `LOCALIZADOR_DE_MIDIA_PELO_AAF/app/links.py::volume_key`.

Dois shares distintos no mesmo servidor contam como volumes distintos (conservador: podem estar no
mesmo volume físico e o hardlink funcionaria, mas prever cópia e **tentar de fato** na execução é o
lado seguro do erro).

---

## 5. Levar o original ao NLE sem copiar — o que funciona no Windows (`confirmado`)

Medido em Windows 11 sem elevação. Complementa a nota de symlink em macOS de
[protocolos/msm/ama-management.md](../protocolos/msm/ama-management.md).

| mecanismo | sem admin | atravessa volume | o Avid abre |
|---|---|---|---|
| **hardlink** (`CreateHardLink`) | ✔ | ✘ | ✔ — é outra entrada de diretório para o mesmo arquivo, não é reparse point |
| **symlink** (`CreateSymbolicLinkW`) | ✘ `WinError 1314` | ✔ | ✔ no macOS; **em Windows sem registro de validação** |
| atalho `.lnk` / alias | ✔ | ✔ | ✘ o Avid lê os bytes do atalho como essência → `Header partition not found` |
| junction (`mklink /J`) | ✔ | só volume **local** | irrelevante — *"Local volumes are required"* para UNC |

Três detalhes que só aparecem tentando:

1. **`os.symlink` do Python não serve.** O CPython não passa
   `SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE` (`0x2`), então falha **mesmo com o Modo
   Desenvolvedor ligado**. Chamar `CreateSymbolicLinkW` direto (ctypes) com o flag; retentar sem ele
   em Windows < 10/1703, que devolve `ERROR_INVALID_PARAMETER` para o flag desconhecido.
2. **Política de avaliação de symlink** (`fsutil behavior query SymlinkEvaluation`): padrão tem
   Local-to-Remote **ENABLED** e **Remote-to-Remote DISABLED**. Ou seja, pasta de links **dentro de
   um share** apontando para **outro share** não resolve — e o link é criado com sucesso, aparece
   normal no Explorer, e só o NLE falha. **Rebaixar para cópia nesse caso** em vez de criar link que
   mente.
3. **Privilégio de symlink vem de três lugares**: processo elevado, Modo Desenvolvedor ligado, ou
   política de grupo. Não deduzir — **testar** criando um link numa pasta temporária.

---

## 6. Receita para um app que precise achar originais

1. Ler os locators, `unquote` **antes** de qualquer comparação, e converter as 5 formas de URL (§1).
2. Descartar o que aponta para `avid mediafiles`/`omfi mediafiles`/`avid attic` — é mídia
   gerenciada, não o original (§2.1).
3. Chaves de busca, nesta ordem de confiança: basename do `ImportDescriptor` (tem a extensão real) →
   nome do SourceMob de arquivo → nome do MasterMob.
4. Usar o nome da fita como **pista de pasta** para priorizar a varredura (§3).
5. Comparar nome/caminho case-insensitive e com Unicode normalizado (NFC) (§1, §2.3).
6. Antes de coletar, calcular a identidade de volume (§4) e escolher o mecanismo (§5) — e **prever
   para o usuário** o que vai virar link e o que vai virar cópia, porque a diferença é entre
   instantâneo e horas de rede.
