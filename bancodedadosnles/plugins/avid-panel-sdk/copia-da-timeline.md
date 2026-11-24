# A cópia do editor (Ctrl+C na timeline) — como um painel lê exatamente o que foi selecionado

> **Medido em:** Media Composer **2025.6.58781** (Perpetual, `PanelSDK_25.6`), Windows 11, 2026-09-24,
> com o autor operando a timeline. Projeto `_Assist anterior`, sequência `PRODA_CORTE.02.Exported.01.Copy.01`
> (23,976, início 01:00:00:00). Spikes: `_DeLaPraCa/.dev/spike_monitores.py`,
> `_DeLaPraCa/.dev/spike_createsubclip.py`. macOS: **pendente**.

## O problema

A API do MC **não lê a seleção de segmentos** (vermelha/amarela) nem as marcas IN/OUT de uma
sequência — não há método para isso no `mcapi.proto`. Um painel que precise de "só estes clipes"
(ex.: o INSERT PARA COR/VFX do De Lá Pra Cá) não tem como perguntar diretamente.

## ⭐⭐ A saída: a cópia vira subsequência numa bin do painel, e a bin é lida pelo `.avb`

Receita (confirmado, cada passo medido):

1. O editor seleciona como quiser (segmentos salteados, IN/OUT, qualquer trilha) e dá **Ctrl+C**
   — ou o painel dá, ver a seção "O BOTÃO copia sozinho".
2. `DoCommand(6292 "Clipboard Contents")` → carrega a cópia no monitor **ativo** (neste passo
   medido, o Source; ⚠️ pode ser o Record — ver abaixo). 0,03 s;
   `IsCommandsEnabled([6292])` devolve `enable: true`. **Cada** chamada gera um mob **novo**
   (id diferente), mesmo TC.
3. `GetViewerMobs` → o item do Source é o que vem **sem `view_type`** (é o valor 0 do enum, que
   o `MessageToDict` omite). Dele sai o `mob_id` da cópia.
4. `CreateSubClip(destination_bin_path=<caminho ABSOLUTO da .avb>, mob_id=<cópia>,
   use_clip_bounds=True, end_frame=-1, create_new_sequence=True)` → cria a subsequência na bin.
   0,06 s. **A resposta não traz o mob_id criado** (corpo vazio): identifique pela bin (use uma
   bin nova por coleta) — nomes repetem (`Clipboard Contents.03.sub.02` saiu duas vezes).
5. `DoCommand(1004 Save)` + esperar o arquivo estabilizar (o Save é assíncrono — ver
   `relink_avb.esperar_bin_estabilizar` no De Lá Pra Cá) → ler com `pyavb`.

**Prova de fidelidade (confirmado):** a subsequência criada pela API é **idêntica, entrada por
entrada (125 de 125)**, à que o autor arrastou à mão do Source para uma bin: mesma trilha, TC,
`source_start_frames`, `mob_id` do **master** (o leitor atravessa o subclipe), velocidade,
vazios e transições.

### O que a subsequência carrega

- **A posição original:** o `timeline_start_tc` dela é o TC da timeline onde a cópia começa
  (`01:02:51:12`). Posição de cada clipe = início + deslocamento dentro da subsequência.
- **O que não foi selecionado vira vazio (filler)**, e vazios vizinhos se fundem: um clipe de A1
  pulado entre dois escolhidos apareceu como um vazio de 263 frames somado ao pedaço anterior.
  Um vazio da cópia **não distingue** "buraco original" de "clipe não escolhido" — e não precisa:
  vazio = não vai.
- **Só as trilhas copiadas:** com V1/V2/A1–A16 ligadas, copiar segmentos da V1 trouxe V1 e o som
  linkado (A1–A5), **não** a V2 que estava por cima.
- **Pode ter vazio no fim de uma trilha:** a cópia dura até o fim da trilha mais longa (som 9
  frames além do vídeo → 9 frames de vazio no fim da V1).

## ⭐⭐ O BOTÃO copia sozinho — e a ordem certa (confirmado 2026-09-24, mesmo MC)

O autor quer que o botão do painel dispare a cópia (o editor só seleciona e aperta "Coletar").
Medido com o editor selecionando **sem** Ctrl+C (inclusive um clipe da V2) e clicando no painel;
spike `_DeLaPraCa/.dev/spike_coletar_botao.py`. O que funcionou, ponta a ponta:

1. **Teclado:** `Ctrl+0` (foca a timeline) → `Ctrl+C`, por `SendInput` — a janela em primeiro plano
   é a do MC porque o clique foi no painel (que é janela do MC). Mesmo roteiro do Promo Entrega
   (`teclado.py`, com a armadilha do `MOUSEINPUT`). macOS: `Cmd+0`/`Cmd+C` por `osascript`
   (Acessibilidade) — **pendente**.
2. `DoCommand(6292)` → **abre a cópia no monitor ATIVO**, Source **ou Record**. Depois de o editor
   mexer na timeline o ativo é o Record: a cópia **toma o lugar da sequência na timeline**.
3. Ache a cópia pelo que **mudou**: `GetViewerMobs` antes e depois do 6292; o monitor cujo `mob_id`
   mudou é o que recebeu a cópia. (Não use "o Source": nas primeiras tentativas o Source ficou com a
   cópia VELHA e a conferência afirmou "não copiou" com a cópia nova no Record.)
4. `CreateSubClip` → `Save` → `.avb` (receita acima). O início certo é o `timeline_start_tc` da
   subsequência; o `current_timecode` do monitor não é o início (a cópia pode abrir num frame ≠ 0).
5. Se a cópia tomou o Record: `LoadMobsIntoViewer(Record, <sequência do editor>)` — a sequência
   volta **na mesma posição** (o MC lembra o cursor por sequência; 01:02:36:10 → 01:02:36:10).

### ⚠️⚠️ A cópia do Avid é o TRECHO, não a seleção (confirmado com gabarito, 2026-09-24)

O autor marcou 3 clipes (2 na V1 separados por outros, 1 na V2), anotou em papel **sem contar**, e o
botão coletou. Os 3 vieram exatos (IN e OUT batendo frame a frame — o OUT da subsequência é o frame
seguinte ao último) — e vieram junto **todos os clipes da V1 entre os dois marcados**. Repetido em
outro trecho (`11-xx-xx`), mesmo padrão; o autor confirmou por testes próprios. Regra: **em cada
trilha, o Ctrl+C leva do primeiro ao último segmento selecionado, com tudo o que houver entre eles**
(o que não está em trilha selecionada vira vazio). Não há como o painel saber quais do meio estavam
marcados. Consequência de desenho: coletar clipes separados **um por vez** (lista aditiva) ou
aceitar o trecho e remover sobras na lista.

### ⚠️ Botão sem nada selecionado: volta a ÚLTIMA cópia (confirmado)

Com a timeline sem seleção, `Ctrl+0 → Ctrl+C` **não altera** a cópia guardada: o `6292` reabre a
anterior, idêntica (medido duas vezes seguidas). Não há comando para **limpar** a cópia do MC
(`6290 "Clear Monitor"` limpa monitor, não a cópia). E `IsCommandsEnabled([6224])` devolve
**`true` mesmo sem seleção** — não serve de pré-checagem. Defesa possível só DEPOIS: comparar a
cópia com a última coletada (início + trilhas + clipes) e com a lista.

### A bin da coleta é descartável (confirmado 2026-09-24)

A bin de destino do `CreateSubClip` é **nossa** (a API exige uma; a cópia só existe na memória do MC).
Ciclo medido: `CreateBin(nome fixo)` → `CreateSubClip` → `Save` → ler `.avb` → `CloseBin` (0,44 s) →
**apagar o arquivo**. O `Save` seguinte **não** recria o arquivo; a janela do projeto mostra a
entrada **em vermelho** (bin ausente) até o editor atualizá-la — não há `DoCommand` de refresh do
projeto — e `GetBins` continua listando-a. `CreateBin` com o **mesmo nome** da entrada vermelha
funciona (a bin volta ao normal). ⇒ Um nome FIXO por projeto: no máximo uma entrada, nunca uma pilha.

**Pasta própria, no fim da lista (pedido do autor):** `zMagicLink` (o `z` joga a pasta para o fim da
ordem alfabética). Criar a pasta **no disco** (`mkdir` dentro da pasta do projeto) +
`CreateBin(folder_path="zMagicLink", bin_name="coleta")` funciona **na hora** — o `CreateBin` exige
que a pasta exista (senão `"Directory not found."`). A pasta só **aparece** na janela do projeto e no
`GetBins` depois de o editor dar refresh no projeto — e esse refresh também some com as entradas
vermelhas de bins apagadas. **O ciclo não depende do refresh:** medido dentro de
`zMagicLink/coleta.avb` — abrir cópia → `CreateSubClip` → devolver Record → `Save` → ler →
`CloseBin` → apagar = **8,5 s**, a maior parte esperando o `Save` assíncrono chegar ao disco.
O refresh do projeto pela API: **não existe**. Ele mora só no menu do painel lateral de Bins (☰ ou
botão direito → `Refresh`, sem atalho). `GetListOfCommands` **desta** build (2025.6, 725 comandos)
não tem nenhum refresh de bins/projeto: só `1040 Refresh Media Directories`, `1850 Refresh
In-progress Linked Clips` e `6516 Refresh Sequence ALL`. Para não deixar entrada vermelha: ao fim
da coleta, recriar a bin **vazia** (`CreateBin`, que a abre flutuante) e fechá-la (`CloseBin`).

⭐ Use a subsequência só para saber **QUAIS** segmentos (trilha, IN, OUT); o conteúdo (nome, master,
efeitos, velocidade) vem da **sequência original** lida da `.avb` dela. O `CreateSubClip` embrulha cada
clipe num subclipe (`04-04-05.sub.01`) — o leitor já devolve o master certo, mas o nome carregaria o
`.sub.NN`.

⛔ O que **não** serviu, na mesma medição:

| tentativa | resultado |
|---|---|
| `DoCommand(1915 "Timeline")` → `DoCommand(6224 "Copy to Clipboard")` | não copiou (o 6292 seguinte não trouxe mob novo); causa não isolada |
| `MakeViewerActive` (para garantir o Record ativo) | **não existe no MC 2025.6** |
| `GetViewerMobs.active` (para saber qual monitor está ativo) | vem **ausente** em todos os monitores |
| `DoCommand(6225 "Toggle Source/Record")` | alterna às cegas; não troca o que a TIMELINE mostra (isso é o 6281) |
| `DoCommand(1908 "Clipboard Monitor")` | abre uma janela flutuante própria que **não aparece** no `GetViewerMobs` |
| dois `DoCommand` colados | `"Can't start more than one command on time."` (ErrorType 73): o `DoCommand` volta antes de acabar — repita até vagar (0,1–0,3 s) |

## Armadilhas medidas

| chamada | o que acontece | confiança |
|---|---|---|
| `CreateSubClip` só com `use_clip_bounds=True` (head/end = 0) | `"Invalid start or end offset."` (ErrorType 66) | confirmado |
| `CreateSubClip` com `end_frame` além do fim | `"Invalid add_frame_at_end: Requested frames not available."` — recusa **sem criar nada** | confirmado |
| `CreateSubClip` `end_frame` | é **exclusivo** (3805 cortou o último frame; 3806 = duração exata) | confirmado |
| `CreateSubClip` `use_marks_bounds=True` sobre a cópia | `"Invalid start or end offset."` | confirmado |
| `CreateSubClip` `destination_bin_path` | aceita caminho absoluto e `NOME.avb`; `NOME` sem extensão → `"Bin not found."` (ErrorType 9) | confirmado |
| ⛔ `CreateSubClip` numa bin **FECHADA** (existe no disco e no projeto) | `"Bin is not open."` (**ErrorType 50**). O spike nunca viu isso porque gravava numa bin RECÉM-CRIADA (o `CreateBin` a deixa aberta). O serviço fechava a bin logo depois de criá-la, para não deixar entrada vermelha, e **nenhuma coleta pelo botão funcionou** (2026-09-25, primeira rodada com o autor). Receita: apagar a vazia e recriar com `CreateBin` imediatamente antes do `CreateSubClip`; fechar só no fim. ⭐ **Com a receita, o ciclo completo rodou com o autor no mesmo dia** (MC 25.6/Windows): Coletar → Enviar insert → Trazer no Resolve | confirmado |
| `CreateSubClip` efeito colateral | a bin de destino recebe, além da subsequência, **subclipes de cada clipe** (`04-04-05.sub.01`…) e **cópias dos masters/`msmMMOB`** de que dependem (~80 mobs para 15+22 pedaços) | confirmado |
| `GetBinFromMob` na cópia do Source | `"Bin not found."` (ErrorType 69) — ela não mora em bin nenhuma até o `CreateSubClip` | confirmado |
| `GetMobInfo` na cópia | nenhuma coluna | confirmado |
| `GetMobTrackInfo` na cópia | trilhas copiadas + `num_segments` por trilha (conta vazios) — **não basta** para saber quais clipes: seleção salteada e contínua podem dar a mesma contagem | confirmado |
| `SetPosition` | **não existe no MC 2025.6** (`UNIMPLEMENTED`) | confirmado |

## ⛔ O que NÃO funciona

- **Área de transferência do sistema:** depois do Ctrl+C na timeline, a do Windows fica **vazia**
  (nenhum formato, dono `pid 0`). A cópia vive só dentro do MC. Colar no painel (evento `paste`) não
  tem o que receber. macOS: **pendente**.
- **Contar pedaços** (`GetMobTrackInfo.num_segments`) para deduzir a seleção: ambíguo, ver acima.

## Leituras úteis de passagem (confirmado, mesma medição)

- `GetViewerMobs` do Record: `current_frame` conta **a partir do início da sequência, sem o TC
  inicial** (frame 5642 ↔ `01:03:55:02` numa sequência que começa em 01:00:00:00, 23,976).
- `GetMobTrackInfo(mob da sequência)` devolve por trilha `selected` (o seletor de trilha da
  timeline), `monitored`, `enabled`, `num_segments`. Rótulo de vídeo vem **sem `type`** (valor 0).
- A cópia no Source traz `current_timecode` = o TC da timeline onde a cópia começa, com
  `current_frame` ausente (0).
