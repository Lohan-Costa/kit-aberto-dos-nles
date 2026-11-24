# A bin sincronizada e a autoria de subclipe

> Origem: **Assist anterior**, módulo `Preparar`, 2026-08-25/26. Amostra real: `D02_SYNC.avb`
> — diária 2 do curta *PRODUCAO-A*, sincronizada pelo **Órbita** (DRAMASYNC) e aberta no
> **Media Composer 2025.6** pelo autor.
>
> ⭐ Isto é a metade **inversa** de [`escrita.md § RELINK PELA BIN`](escrita.md), que
> **desfaz** subclipe (`denest.achatar`). Aqui se **cria** um.

---

## 1. A anatomia de uma bin sincronizada — `confirmado` (2026-08-26)

O que a sincronização entrega é **uma `CompositionMob` de corte seco** (`usage_code = 0`),
com os masters de câmera e de som na mesma bin. Medido em `D02_SYNC.avb`:

| | |
|---|---|
| `CompositionMob` | **1** (a timeline), `length = 612969` @ 23.976 |
| `MasterMob` | **50** — 24 de som direto + 26 de câmera |
| `SourceMob` | 248 |

### As trilhas da sequência

```
picture idx=1                    ← a câmera
sound   idx=1 … idx=5            ← o som direto (5 canais do gravador de campo)
sound   idx=6, idx=7             ← ⚠️ o SOM DA CÂMERA
timecode idx=1 … idx=8
DescriptiveMetadata idx=1
```

⚠️⚠️ **O som da câmera vem em trilhas de som como qualquer outro.** Nada na trilha diz que
aquele áudio é de câmera. Um leitor que trate "todo segmento de som" como uma tomada
fabrica **uma tomada por clipe de câmera** — medido: 26 falsas tomadas numa bin de 24
tomadas reais, e nenhuma delas estourou nada.

### ⭐ Como distinguir som direto de som de câmera, estruturalmente

A resposta **não** está no nome, no índice da trilha nem em convenção: está no **master**.

| origem | tracks do `MasterMob` |
|---|---|
| gravador de campo (WAV) | `sound 1 … sound 5` — **sem imagem** |
| câmera | `picture 1` + `sound 1` + `sound 2` — **é o mesmo arquivo** |

```python
def e_de_camera(mob) -> bool:
    """O master carrega imagem? Então o som que vem dele é som de câmera."""
    tracks = mob.tracks() if callable(mob.tracks) else mob.tracks
    return any(str(t.component.media_kind).lower() == "picture" for t in tracks)
```

⚠️ Vale para a saída do **Órbita**. A saída do **AutoSync do Media Composer** não foi lida
— `pendente`. A regra é estrutural e deve valer, mas ninguém mediu.

### ⚠️⚠️ `SourceClip.start_time` é SEMPRE 0 nesta saída

O adapter do Órbita crava clipe inteiro, sem trim: `DRAMASYNC/src-python/avid/adapter.py`
linha 89, dentro de `_seg()`, escreve `"source_start_frames": 0` incondicionalmente — e o
docstring de `daily_to_avb_segments` (linha 113) diz o mesmo em palavras: *"entra INTEIRO
(`source_start=0`), na sua posição de timeline, a 100%"*. Consequência para quem lê:

> **A fronteira de uma tomada vem da POSIÇÃO NA TIMELINE, nunca do offset de origem.**

Um leitor que regredisse para `start_time` faria toda tomada começar no frame zero do
master — **sem estourar**, com a suíte verde, sobre material inteiramente errado.

### O que a sincronização NÃO alinha

Medido nas 24 tomadas da D02: o gravador de som **liga antes da câmera em todas elas**,
entre **98 e 299 frames** (4 a 12,5 s @ 23.976), e costuma parar depois. Somado:
**4 477 frames** de som sem imagem na cabeça e **3 467** na cauda.

⭐ Isso não é defeito do sync — é a ordem de produção (som roda, câmera roda, claquete).
Mas significa que **a janela de som e a janela de imagem de uma tomada não coincidem**, e
quem for cortar por uma delas precisa decidir qual.

---

## 2. Autorar um subclipe em pyavb — `confirmado` (2026-08-26)

Um subclipe é uma `CompositionMob` com `usage_code = 2` (relida, `mob.usage == "subclip"`),
cujas tracks carregam um `SourceClip` apontando ao **master**, com `track_id`, `start_time`
e `length` do recorte.

⭐ **Um subclipe pode misturar masters** — é a forma que o AutoSync produz: `V` da câmera,
`A` do som. As tracks não precisam vir todas da mesma mob.

```python
mob = f.create.Composition("nome", "CompositionMob")
mob.name = "C04_P01_T002"        # ⚠️ ver armadilha 1
mob.usage_code = 2
mob.edit_rate = 23.976           # ⚠️ ver armadilha 2
mob.media_kind_id = 0
mob.length = duracao
mob.mc_mode = 0
mob.num_scalars = 0
mob.param_list = None
mob.tracks = []

sc = f.create.SourceClip(edit_rate, "picture")
sc.mob_id = MobID(str_do_master)
sc.track_id = canal_no_master
sc.start_time = frame_inicial
sc.length = duracao

track = f.create.Track()
track.index = 1                  # ⚠️ ver armadilha 3
track.component = sc
track.lock_number = 0
mob.tracks.append(track)

f.content.add_mob(mob).user_placed = True   # ⚠️ sem isto, INVISÍVEL na bin
```

### As quatro armadilhas, todas medidas

**1. `f.create.Composition(nome, tipo)` IGNORA o argumento `nome`.** O `__init__` do pyavb
faz `self.name = mob_type`. Sem atribuir `.name` depois, a bin sai com todo mob chamado
`"CompositionMob"`.

**2. `TrackGroup.__init__` usa `edit_rate = 25`.** Não é o do projeto, não é herdado.
Atribuir sempre.

**3. O índice da track do subclipe é sequencial POR TIPO DE MÍDIA, e não o `track_id` do
master.** São coisas diferentes: `track_id` diz de que canal do master o material vem; o
índice diz em que trilha do subclipe ele aparece. Numa fixture com canais contíguos os dois
coincidem — e um autor que os confunda passa despercebido.

**4. ⚠️⚠️ `Track.media_kind` é `@property` e deriva do COMPONENTE** (`self.component.media_kind`).
Forçar `"sound"` nos `SourceClip` **relabela a própria track de imagem**. A regra prática: o
`media_kind` da `Track` e o do `SourceClip` dentro dela são o mesmo, sempre.

### ⚠️ `user_placed = True` não é enfeite

Sem ele o mob existe no arquivo e **não aparece na bin** do editor — a flag vive no
`BinItem`, e `add_mob` devolve exatamente esse registro. A mecânica já estava no banco
desde 2026-07-02: [`dados/bin-metadata.json`](dados/bin-metadata.json), que documenta o
uso oposto (esconder master relinkado numa bin de entrega). Aqui ela aparece na direção
de mostrar.

### E a regra do `uid`, que vale para toda gravação

`f.content.uid = random.getrandbits(63)` antes de `f.write()`. Sem isso o MC recusa a bin
com `FILE_OPEN_FAILURE` enquanto houver uma de mesmo uid aberta — ver
[`escrita.md § o FILE_OPEN_FAILURE NÃO é do writer`](escrita.md).

### MobID novo a cada autoria

O Media Composer serve mob por MobID **a partir da sessão**, não do arquivo: duas bins com
o mesmo MobID no mesmo boot e a primeira carregada ganha. Toda autoria gera MobIDs frescos.

---

## 3. O que o Media Composer aceitou — e o que ainda não foi verificado

Rodada de 2026-08-26, MC 2025.6, com o autor na máquina:

| | |
|---|---|
| ✅ | O MC **abre** a bin autorada e **mostra** os subclipes |
| ✅ | Subclipes distribuídos em bins por cena, escritas pelo mesmo caminho |
| ⬜ | Carregar no *Source monitor* e ter imagem **e** som |
| ⬜ | O som estar **em sincronia** com a imagem |
| ⬜ | ⚠️ **A pergunta aberta:** o MC resolve um subclipe cujo **master mora noutra bin**? |

⚠️ A última é a que decide se uma "bin de cena leve" é viável. A saída conhecida, se a
resposta for não, é escrever a bin de cena **sobre** a que já contém os masters — ver
[`escrita.md § Bin com SÓ A TIMELINE`](escrita.md), que registra o caso irmão.

Rastreabilidade da rodada: `_ASSIST ANTERIOR/docs/VALIDACAO-P2A.md`.

---

## ⛔⛔ 4. A bin NO DISCO fica para trás da bin ABERTA — e o sintoma é master sem nome

`confirmado` 2026-09-20 (MC 2025.6, Windows, Assist anterior). Quem LÊ o `.avb` lê o último
**save**, não o que o editor está vendo. Enquanto a bin tem alteração não salva, um
subclipe recém-criado (ou recém-relinkado) pode existir no arquivo **sem o mob do master
que ele referencia** — o `SourceClip` aponta para um MobID que não está lá.

**O sintoma, e por que ele engana:** o resolvedor acha o subclipe, mas a fonte volta com
`master = ""` e sem arquivo. Quem só lê a mensagem conclui "a mídia está offline" ou "o
master não está na bin" — e, num produto com LLM, o modelo pede ao editor que *"traga os
masterclipes para a bin"*, coisa que não existe no Avid: o master do subclipe (e o da
timeline e o do groupclipe) **vive oculto dentro da própria bin**.

**Medido:** às 09:16 a transcrição falhou nos 10 subclipes da `CENAS\C07.avb` com
`não achei a mídia de som de '' no acervo local`; a bin foi gravada às **09:17:12**.
Lendo o MESMO arquivo depois do save, o master resolve (`PRODUCAO-A - 05-04 C7 P1-T001`,
5 OP-Atom achados).

⇒ **Quem lê bin de projeto vivo trata "master sem nome" como "a bin não foi salva"** e diz
o gesto (Ctrl+S), em vez de falar de mídia. Implementado em
`_ASSIST ANTERIOR/motores/cicloassist/avid/take.py::por_que_falta`. ⭐ **E dá para PERGUNTAR se a bin está suja** — o banco já tinha a
medição e eu não a consultei: `plugins/avid-panel-sdk/dados/mcapi-grpc.json`,
`A_BIN_ESTA_SUJA_como_descobrir_sem_flag` (2026-08-21). Não há flag (`GetBinInfo` só dá
`is_open`, `lock_state`, `size`), mas `GetMobTrackInfo(mob_id).num_segments` conta a
timeline VIVA e se compara com a gravada. ⚠️ Aquilo vale para TIMELINE; para "o master do
subclipe está no arquivo?" a comparação equivalente não foi medida.

🆕 **Quem ESCREVE a bin por fora pode gravá-la na hora** (`confirmado` 2026-10-21, MC 24.6, Órbita): depois do
`OpenBin` da `.avb` autorada, o Save Bin (`DoCommand` 1004, só 25.x) ou, sem ele, `CloseBin` + `OpenBin` (o
`CloseBin` grava). Medido: a bin do sync montada pelo Órbita passou de **43K** no disco (só a sequência, com
asterisco) para **588K** (masters materializados), e o Subclipar logo em seguida deixou de recusar "a bin ainda não
foi salva". O mesmo fechar-e-reabrir grava o Renomear (`SetMobInfo`) no 24.6: 26 itens, confirmados por releitura
do `.avb`, ida e volta. Ver `plugins/avid-panel-sdk/ativar-no-2021-ftf.md` §MC 24.6.

## ⛔ 4b. O take do órfão PRESUMIDO (`T001.1`) perde o ponto em três lugares

`confirmado` 2026-10-21 (Órbita, D02 da PRODUCAO-A, MC 24.6). O Subclipar batiza o clipe de câmera sem som pela
POSIÇÃO — take do vizinho anterior + `.n` (`T001.1`; antes do primeiro take, `T000`) — e o ponto é a marca de
"presumido". Ele se perdia: (1) o escritor guardava "só os dígitos" na coluna `Take` → `0011`; (2) o `%take2` do
Renomear fazia o mesmo; (3) a claquete lê `C07 P02-T001.1` como `T001`, porque `Path(nome).stem` toma o `.1` por
**extensão de arquivo**. Sintoma visto: `C%cena_P%plano_T%take2` deu `C07_P02_T0011` (um take 11 inexistente); com o
ponto cortado no outro caminho o órfão sairia com o nome do take 1 real — **dois clipes com o mesmo nome**.
⇒ Regra para qualquer leitor de take (Órbita, Ciclo Assist, Assist anterior): o sufixo `.n` vem da COLUNA `Take`, e
nome que já vem sem extensão não passa por `Path.stem`. Corrigido no Órbita nos três pontos (`subclipes.py`,
`renomear.py`, `media/identidade.py`); a gramática da claquete continua cortando — `conferir` nos outros apps.

---

## Onde isto está implementado

| arquivo | o quê |
|---|---|
| `_ASSIST ANTERIOR/assist_anterior/modulos/preparar/takes.py` | o leitor: janelas de som, aparo, órfãos |
| `_ASSIST ANTERIOR/assist_anterior/modulos/preparar/subclipes.py` | o autor: `montar_mob`, `autorar` |
| `DRAMASYNC/src-python/avid/adapter.py` | quem produz a bin sincronizada (`_seg`, linha 89) |
| `_DeLaPraCa/motor/avb_bin/denest.py` | o inverso: desfazer subclipe |

---

## O mesmo subclipe vive em VÁRIAS bins — e quem lista precisa juntar

> **Medido em 2026-09-21**, projeto real de dramaturgia (`_Assist anterior`, 37 bins, Media
> Composer 25.6 / Windows). Confiança: **`confirmado`** para as contagens; ⚠️ `hipotese`
> para a generalização a outros fluxos de trabalho — é UM projeto, de um editor.

Ao indexar os subclipes de um projeto para ordená-los numa busca, o acervo do editor deu:

| | |
|---|---|
| masterclipes visíveis | 1.093 |
| **subclipes** | **150**, cobrindo 108 masters |
| group clips | 0 |
| sequências | 80 |
| efeito salvo na bin | 1 |

⛔⛔ **Mas 290 pares (master, recorte) são apenas 130 recortes DISTINTOS.** O editor **copia
o subclipe entre as bins de trabalho** conforme a cena avança — `C04_FALAS`,
`C04_FALAS NOVO`, `C04_FALAS NOVO 5`, `CENAS/C04`, `ANTIGOS/…` — e um deles apareceu em
**6 bins**. Um app que liste subclipes sem juntar mostra o mesmo take cinco vezes seguidas
antes de qualquer outro material.

⭐ **A identidade é `nome + janela`, não só a janela.** Dois subclipes legitimamente
diferentes podem coincidir no recorte (um take inteiro aparado igual nos dois), e juntá-los
pelo tempo perderia um nome que o editor reconhece.

⚠️ **E só item VISÍVEL conta** (`user_placed`): a bin de falas leva o fecho OCULTO com os
mesmos subclipes, o que multiplicaria a contagem de novo (mesma regra de
`bins.bins_dos_mobs`).

### O custo de indexar, medido

| passo | tempo |
|---|---|
| listar os 150 (abrir as 37 bins com pyavb) | **0,4 s** |
| resolver os 150 (master de cada fonte + in-point + duração) | **3,1 s** (150 de 150) |
| assinar as bins para saber se o índice ainda vale (nome, mtime, tamanho) | **0 ms** |

⇒ 3,5 s é caro para uma interação e barato para uma sessão. ⭐ **Invalide pela assinatura
das bins, nunca por relógio:** relógio erra nos dois sentidos — refaz o que não mudou e
serve o que mudou. Salvar uma bin no MC invalida corretamente, e a conferência é grátis.

### ⚠️⚠️ A janela é POR MASTER, e é aqui que se erra

Um subclipe sincronizado mistura dois masters e eles entram em pontos **diferentes** —
medido no `C04_P01-T002`: **imagem em 0, som em 214 frames**. Quem guardar "o in-point do
subclipe" e usá-lo para localizar algo que está em tempo de SOM (uma fala, um marcador de
áudio) erra ~9 s, **em silêncio**. Guarde uma janela por master, e não uma por subclipe.

⚠️ Group clip: `take.especie` o reconhece (`usage = group`), mas resolver o material de
dentro é outro trabalho — e este projeto tem zero, então a forma dele segue **por medir**.

---

## ⛔⛔ Ler "o que a timeline usa": o `Selector`, e a armadilha do INSTRUMENTO

> **Medido em 2026-09-21**, mesma bin e mesmo projeto da seção acima.

Para responder *"este clipe é usado em alguma timeline?"*, a varredura desce na árvore da
sequência e colhe os `mob_id`. Duas coisas que custam caro aprender depois:

### 1. O `Selector` guarda o que NÃO toca

Um `Selector` tem `selected` (um índice) e os ramos. Os que não são o escolhido são
**alternativas que não aparecem na tela** — o segmento que o editor desligou, a versão
anterior de um trecho. MEDIDO num deles: `selected = 0` apontando um **`Filler`**, com um
`SourceClip` no ramo 1. Ou seja: naquele ponto da timeline **não toca nada**, e uma
varredura ingênua conta o clipe do ramo 1 como "usado".

⇒ Ao descer, siga **só `ramos[selected]`**. Vale para qualquer app que pergunte "o que esta
timeline usa" — relink, conform, inventário de uso, e a busca que originou esta nota.

### 2. ⚠️⚠️ O leitor de timeline pode estar TRUNCANDO, e o número sai errado sem erro

A primeira contagem desta investigação disse que a timeline usava **9 de 44** subclipes da
bin. Estava errada, e não por causa do formato: o leitor de timeline do app corta a saída
por orçamento de caracteres (mostrou **242 de 641 segmentos**), e a contagem foi feita sobre
os nomes da saída truncada. A varredura recursiva da árvore diz **44 de 44**.

⭐ **A lição é de método, e é transversal:** um leitor feito para caber numa resposta de
modelo **não serve de instrumento de medição**. Ele trunca de propósito, e o truncamento não
é erro — é a função dele. Para contar, percorra a estrutura; para mostrar, use o leitor.

⚠️ E a conclusão de produto que quase saiu daí era o oposto da verdade: "esses subclipes
estão na bin e a timeline não usa" viraria um filtro que esconderia material MONTADO.

## 🆕 ⭐⭐ 5. O GROUP CLIP (multicâmera) por dentro — `confirmado` na LEITURA (2026-11-11, Mac, 1 grupo)

Lido por pyavb no `GRUPO-MULTCAM` da bin `EDICAO.avb` do projeto `producao-a-ENSAIO` (Mac mini, feito à mão no MC em
2026-06-28; câmeras `CAM A` e `CAM B` + `SOM-DIRETO.wav`, 23,976). Ciclo Assist, plano `docs/plano/2026-11-11-carta-aberta.md`.
São DOIS mobs, e o segundo é o que guarda a sincronia:

1. **O grupo** — `CompositionMob`, `usage = group` (o `usage_code 4`). Uma trilha por trilha do grupo (V1, A1–A4), e cada
   uma é um **`Selector`** (`is_ganged: True`, `selected: 0` = o ângulo escolhido, `mc_mode: 0`, `length` = o grupo
   inteiro). Cada ângulo é uma `Track` dentro do `Selector` com UM `SourceClip` de `start_time 0` e o grupo inteiro de
   comprimento, apontando a trilha N do mob abaixo. Ângulos de imagem: as trilhas 1 e 2 dele; de som, A1 = trilhas 1/5/9,
   A2 = 2/6, A3 = 3/7, A4 = 4/8.
2. **O mob de alinhamento** — `CompositionMob`, `usage = groupoofter` (o nome é do MC: `<sequência>.10`). Uma trilha
   por trilha de CADA fonte (V1 + A1–A4 da CAM A, V2 + A5–A8 da CAM B, A9 o som direto), cada uma uma `Sequence`
   `Filler · SourceClip(master, start 0) · Filler`. ⭐ **O deslocamento de cada fonte é o `Filler` da frente**: CAM A 233
   quadros, CAM B 0, som 984 — é o ponto de sincronia, e é POR FONTE (como no subclipe sincronizado, §1).

- ⛔ Para traduzir: o ângulo escolhido no grupo é `Selector.selected`; na TIMELINE, o segmento aponta o grupo e tem
  o próprio `Selector` (ver "Ler o que a timeline usa", abaixo) — não medido nesta bin.
- ⭐ O PAR no Premiere (as mesmas fontes, multicâmera por ponto de entrada, 2026-11-12): a mesma relação, mas o Premiere
  CORTA as cabeças antes do In — `plugins/premiere-cep/subclipe-e-merged-clip.md`, "No Mac, e o par do group clip".
- ✅ 🆕 **ESCRITO pelo pyavb e ABERTO no MC 2025.12 (Mac, 2026-11-12)** — Ciclo Assist
  `spikes/carta_aberta_group_clip.py`: o grupo montado SÓ dos três masters + um ponto de sincronia por fonte
  (CAM A 751, CAM B 984, som 0 → deslocamento = maior − o da fonte), numa bin NOVA com o fecho oculto. A forma saiu
  IGUAL à do grupo feito à mão, 18 de 18 itens (`--comparar`: comprimento, Selectors, ângulos, trilhas e Fillers do
  alinhamento). No MC: a bin abre, o item tem o ícone de grupo e 1:46:12 (2556), `LoadMobsIntoViewer` no Source passa,
  a agulha anda (clique na barra). O que bastou: grupo `usage 4`, `mob_type_id 1`, attrs só `_SAVED_AAF_AUDIO_RATE_*`
  (sem `_ORG_BIN`/`_USER_POS`/`_EDIT_MODTIME`); alinhamento `usage 5`, `user_placed False`, SEM `_MATCH` e SEM trilha de
  timecode; ângulo = `Track` só com `component` + `lock_number`; `filler_proxy` só na trilha de imagem do grupo.
  ⚠️ Mídia offline nesse projeto (os masters AMA apontam uma pasta que mudou) — a forma está provada, a REPRODUÇÃO
  com imagem não; ⬜ trocar de ângulo e editar o grupo numa timeline.
  ✅ 🆕 **SINCRONIA PROVADA NA IMAGEM, laboratório controlado (2026-11-12, MC 2025.12, Mac):** 3 câmeras sintéticas
  23,976 (receita `MIDIAS DE TESTES/3 CONJUNTOS DOS APPS/_CICLO ASSIST/carta_aberta/G01_GRUPO_23976.json`, gerador
  `laboratorio-de-midia/lab/multicam.py`; cada quadro traz câmera, TC e nº do quadro), começando em 10:00:05:00 /
  :12:00 / :08:00 → OP-Atom DNxHD pelo Resolve 21.1 (`cicloassist/resolve_opatom.py`) → masters online
  (`cicloassist/avid/importar_opatom.py`) → grupo escrito com os pontos 168 / 0 / 96. Com o MESMO clique na barra do
  Source, os três ângulos mostram **10:00:21:14**, quadros 398 / 230 / 326 (= 398 − 168, 398 − 72): exato no quadro.
  ⭐ **O ângulo escolhido é o `Selector.selected`** (índice do ângulo na lista do Selector, o mesmo em todas as
  trilhas, ganged): escrito 0/1/2, o Source abre na CAM 1/2/3. O TC que o Source mostra para o grupo é o da cena
  (o da fonte escolhida). ⬜ trocar de ângulo com o grupo já na timeline.
  ✅ 🆕 **O SOM de cada ângulo, medido no que o MC EXPORTA (2026-11-12, MC 25.12 Mac, LAB_ARRASTO_MAC)** — Ciclo Assist
  `spikes/carta_aberta_som_dos_angulos.py`: no G01 cada fonte tem um TOM PILOTO (CAM 1 300 Hz, CAM 2 2000, CAM 3 3700,
  som direto 5400) sobre a cena comum (`_cena.wav`), então o export diz QUAL fonte tocou e COM QUE defasagem.
  - ⛔ **`ExportFile` de um GROUP CLIP responde `Completed` (100 %) e NÃO grava nada** (5 min, nenhum arquivo; o master
    no mesmo preset e pasta saiu em 2 s). ⇒ exportar uma SEQUÊNCIA com o grupo: ✅ um `SourceClip` apontando o MobID do
    grupo (V1 + os sons dele, `start 0`, comprimento do grupo; o grupo no fecho oculto) abre e exporta (242 MB, 12 s).
    É a primeira forma de "grupo na timeline" escrita por nós; o MC a aceitou (não comparada com uma feita à mão).
  - ✅ ângulos 0/1/2 → A1 e A2 tocam CAM 1/2/3 (tom 37 dB acima dos outros); desvio 0,0 / −7,0 / −3,0 ms = EXATAMENTE o
    arredondamento do ponto de sincronia ao quadro (7,0 s × 23,976 = 167,83 → 168 q; 3,0 s → 72 q). Imagem já provada.
  - ⭐ **O seletor do SOM escolhe a fonte independentemente da imagem**: imagem `selected 0` (CAM 1) e som `selected 3`
    (o som direto, 4ª alternativa das trilhas de som) → o export traz o quadro da CAM 1 e o tom do som direto, com
    `is_ganged` True OU False. É o que a multicâmera do Premiere toca (som direto embaixo do ângulo) — a tradução
    Premiere → Avid passou a escolher assim (`montar_grupo(angulo_do_som=…)`).
  - ⛔⛔ **Armadilha de MEDIÇÃO (de novo a do MobID da SESSÃO):** a 1ª variante com o som no 3 foi gravada com o MESMO
    MobID do grupo já aberto, e o export tocou a CAM 1 — o MC serviu o grupo da sessão, não o do arquivo. Toda variante
    de mob precisa de MobID NOVO.
  - ⚠️ No grupo traduzido do Premiere o som direto ficou 935 quadros (39 s) ANTES das câmeras — é o WAV do laboratório
    com `time_reference` em segundos reais (`premiere-cep/subclipe-e-merged-clip.md`, "O caminho de VOLTA"), não o MC.
  ⛔ **`SetPosition` não posiciona group clip** no Source (25.12): "Frame offset exceeds mob range" (ErrorType 66) com
  `offset` ou `timecode`, no escrito E no feito à mão — limite da API, não do arquivo.
- ⬜ `pendente`: grupo de câmeras com taxa ou duração diferentes; o
  `usage` do mob na bin (visível/oculto: o `groupoofter` deve ser oculto, `user_placed` não lido aqui); Windows.
