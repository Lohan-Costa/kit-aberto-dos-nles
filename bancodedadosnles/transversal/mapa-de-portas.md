# Mapa de portas da família — quem escuta onde, e o que colide

> ⭐⭐ **Consulte ANTES de escolher a porta de um app novo, e antes de subir vários ao mesmo
> tempo.** A família toda roda na MESMA estação do editor, junto com o Media Composer: as
> portas não são detalhe de cada projeto, são um recurso compartilhado. Um app que escolhe
> a porta sozinho descobre o choque em campo, com o painel conversando com o serviço errado.
>
> **Levantado em:** 2026-09-16, Windows 11 23H2 (10.0.22631), lendo o código dos cinco
> repositórios e os `.avpi` realmente instalados em `%PROGRAMDATA%\Avid\PanelSDKPlugins`.
> Confiança: `confirmado` para todas as linhas (lidas do código-fonte e do disco), exceto
> onde a própria linha diz outra coisa.

> 🆕 **2026-10-21:** a coluna "painel `.avpi` instalado" é histórica. Pelo [desenho do app único](app-unico-fora-do-nle.md)
> o painel dentro do MC sai (24.6 e 25.12.2 nem o mostram); os apps falam com o MC direto pela **9100**. A porta de
> cada serviço continua valendo: é a que a janela do app e a ponte do Premiere usam.

## 1. As portas de cada app

| app | script de dev | serviço | painel `.avpi` instalado | outras |
|---|---|---|---|---|
| **Órbita** (`DRAMASYNC`) | `dev.bat` | **7817** (ponte com os plugins, `src-tauri/src/httpserver.rs`) | `com.orbita.sync` | Vite **1420** (`strictPort`) |
| **De Lá Pra Cá** | `dev.ps1` | **7823** | `com.ciclomedia.delapraca.mc` → 7823 | — |
| **Ciclo Assist** (`_CICLO ASSIST`) | `dev.ps1` | **7824** | `com.ciclomedia.cicloassist.mc` v0.2.0 → 7824 | Ollama **11434**; SigLIP no Mac **7825**; `tools/print_painel.mjs` **9333** |
| **Assist anterior** (`_ASSIST ANTERIOR`) | `dev.ps1` | **7830** (era 7823 até 2026-09-16) | `com.ciclomedia.assist_anterior.mc` → 7830 desde 2026-09-19 (antes: o mesmo id do Ciclo Assist, ver §4). ⚠️ O `.avpi` instalado com esse id em 25/08 ainda aponta para a 7823 até o próximo `tools/pack.py` | — |
| **Promo Entrega** | `dev.ps1` | **7829** | `com.ciclomedia.promoentrega.mc` → 7829 | Vite **1421** |

⭐ **Livres e próximas:** 7818–7822, 7826–7828, 7831+. Quem criar app novo pega a seguinte e
**acrescenta a linha aqui**, não no `CLAUDE.md` do próprio projeto — o choque é entre apps,
então o registro tem de morar onde todos olham.

⚠️ O Vite do Órbita usa `strictPort: true`: se a 1420 estiver ocupada ele **falha na hora**,
que é o comportamento certo. O `hmr` na 1421 dele só é configurado quando a variável de
ambiente `TAURI_DEV_HOST` está setada (uso em rede/mobile) — por isso a 1421 do Promo
Entrega convive com o Órbita no uso normal, e **deixaria de conviver** se alguém ligasse o
host de desenvolvimento.

## 2. O que é do Avid, e é UM só para todos

| porta | quem | observação |
|---|---|---|
| **4920 / 4930** | `avid-api-gateway` | processo **filho do Media Composer**, um por sessão, compartilhado por todos os painéis. Escuta só em `[::1]`. |
| **9100–9110** | backend do MC (faixa de `PanelSDK.json`) | é por onde os serviços dirigem o MC por gRPC, **sem token**. |
| **8124 / 8125** | motor do **Griptape Nodes** 0.112.0 (`griptape-nodes engine`) | só `127.0.0.1`; a **8125 é o MCP** do motor (53 ferramentas). Ver [orquestracao-fora-do-nle.md](orquestracao-fora-do-nle.md). |
| **7850–7853, 7860** | provas do estudo Griptape e Ciclo Assist (2026-11-20) | central (7850), Assists de mentira (7851–7853), porteiro (7860). Só ligadas durante as provas. |

⛔ **Zelador de gateway órfão: só mate o ÓRFÃO.** Órbita, De Lá Pra Cá e Promo Entrega têm
essa limpeza, e todos ela conferem se o `ppid` ainda aponta para alguém vivo — com o MC
aberto, ela é um no-op. Mas o `tools/reload.py` do De Lá Pra Cá aceita `--todos`, que mata
gateway com pai vivo: rodar isso com o Avid aberto **derruba a ponte de todos os painéis
de uma vez**, não só a do app que você está mexendo.

## 3. O choque da 7823, e por que ele era invisível no Windows

Até 2026-09-16, **De Lá Pra Cá e Assist anterior serviam os dois a 7823**, e os dois painéis
instalados apontavam para lá. O sintoma dependia de quem subisse primeiro, e o pior caso
era silencioso:

| quem sobe depois | `SO_REUSEADDR` desse app | o que acontece |
|---|---|---|
| Assist anterior | desligado no Windows | `bind()` recusado com `WinError 10048` — erro que se lê ✅ |
| De Lá Pra Cá | **ligado** (até este conserto) | ⛔ o segundo `bind()` é **aceito**; o app novo anuncia que subiu e quem responde é o velho |

⭐ **A lição não é a porta, é o par.** Duas portas iguais só viram bug invisível porque a
outra ponta — `allow_reuse_address` — deixava o segundo processo bindar por cima. Com a
opção desligada no Windows, porta repetida vira erro na primeira tentativa. Ver a linha
`SO_REUSEADDR` da [matriz de plataforma](matriz-de-plataforma.md), seção D.

**Resolvido em 2026-09-16:** Assist anterior foi para **7830** (constante, manifesto, loader e
testes, que o projeto trava juntos de propósito), e o De Lá Pra Cá passou a usar
`allow_reuse_address = sys.platform != "win32"`, como Ciclo Assist e Assist anterior já faziam.

## 4. ⛔⛔ Dois repositórios publicam o MESMO id de painel

`_ASSIST ANTERIOR` é a versão **anterior** do Ciclo Assist: o repositório foi renomeado por
dentro (`NOME_DO_APP = "CicloAssist"`, `NOME_ANTERIOR = "assist_anterior"`), e desde então o
`painel/avid-manifest.json` dele declara `com.ciclomedia.cicloassist.mc` — **o mesmo id** que
o `_CICLO ASSIST` novo empacota.

O arquivo instalado é nomeado **pelo id**. Então empacotar e instalar o painel do repositório
antigo **sobrescreve** o painel do app novo, e a entrada "Ciclo Assist" do menu Tools passa a
apontar para a porta do antigo. Não há aviso: o `.avpi` é substituído e o menu continua com
uma entrada só, aparentemente saudável.

⚠️ **Por isso mover a porta do serviço não basta para rodar o repositório antigo dentro do
MC** — ele precisaria de um id próprio outra vez. Enquanto isso não for decidido, o serviço
dele sobe na 7830 e é alcançável pelo navegador (`http://127.0.0.1:7830/painel`), mas não tem
entrada própria no menu do Avid.

### 4.1 ⛔⛔ E a PASTA DE DADOS também era a mesma — `confirmado` 2026-09-19

O §4 só olhou o id. Na máquina do autor (Windows 11), `%LOCALAPPDATA%\CicloAssist` tinha os
arquivos **dos dois apps misturados**, inclusive dentro das mesmas subpastas:

| subpasta | do `_ASSIST ANTERIOR` | do `_CICLO ASSIST` |
|---|---|---|
| raiz | `bin/` (2,2 GB), `transcricoes/`, `trabalho/` (1 GB) | `config.json`, `estado.json`, `midia/` (310 MB) |
| `modelos/` | `manifesto.json`, `prompts.npz`, `hf/` | `mobilenetv2-12.onnx`, `siglip2-base-256/` |
| `logs/` | `assist_anterior-AAAAMMDD.log` | `cicloassist.log*` |

A causa foi a migração de 03/09 no `_ASSIST ANTERIOR`, que **renomeou a pasta inteira**
`assist_anterior` → `CicloAssist`. Sete dias depois o app novo nasceu com o mesmo nome em disco e
passou a gravar lá. Nenhum dos dois quebrou, porque os nomes de arquivo não colidiam. Foi sorte,
não desenho.

**Resolvido em 2026-09-19:** o `_ASSIST ANTERIOR` voltou a ser **Assist anterior**, com id
`com.ciclomedia.assist_anterior.mc` e pasta `assist_anterior`. ⛔ A migração de volta **não pode ser
um rename da pasta** (levaria os dados do outro app): ela move **só os itens listados** em
`plataforma.NOSSOS_NA_PASTA_ANTERIOR`, e se falhar no meio desfaz o que já moveu. Seis
mutantes, seis mortos.

⭐ Regra que sai daqui: **renomear um app = renomear três coisas** (id do painel, pasta de
dados, prefixo das variáveis de ambiente). E a pasta de dados de um nome abandonado **não fica
livre**: o próximo app que usar o nome herda o que estiver lá.

⭐ A regra geral, que já mordeu antes: **um id de painel = um app**. Renomear um produto sem
renomear o id deixa o id como herança do produto antigo, e o primeiro `pack.py` que rodar do
lado errado troca o painel de quem estava certo.

## 5. Como conferir numa máquina

```powershell
# quem está escutando nas portas da família
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 7817,7823,7824,7825,7829,7830,1420,1421,4920,4930 } |
  Select-Object LocalPort, OwningProcess

# qual painel está instalado, e para qual porta cada um aponta
Get-ChildItem "$env:PROGRAMDATA\Avid\PanelSDKPlugins" -Filter *.avpi
```

No macOS, a pasta dos painéis é `/Library/Application Support/Avid/PanelSDKPlugins` e o
equivalente da primeira consulta é `lsof -nP -iTCP -sTCP:LISTEN`.
