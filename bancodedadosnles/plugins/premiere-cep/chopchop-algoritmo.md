# Chop Chop (Resolve) — a leitura completa do algoritmo

Continuação de [chopchop-arquitetura.md](chopchop-arquitetura.md), agora com a **régua nova**
(2026-08-24): ler 100% é permitido; o que se registra é **mecanismo, não código**. Nada abaixo é
transcrição — é descrição do que o programa faz e do que isso custa.

Fonte: `ChopChop Resolve.py` desembrulhado (base64 + XOR 248), **2.355 linhas de Python**.

---

## 1. ⭐⭐ O achado principal: o "incremental" é APAGAR E RECONSTRUIR

O manual promete, na página 18: *"It will slot them in the correct place on the correct timeline.
For example, scene 4 shot 3 files will be slotted between scene 4 shot 2 and scene 4 shot 4 files,
even if these are ingested in different batches."*

**Não é o que acontece.** Antes de montar, o programa varre **todas** as trilhas de vídeo e áudio
da timeline da cena, junta cada item e seus vinculados (`GetLinkedItems`), e chama `DeleteClips`
sobre o conjunto inteiro — com um caminho de recuo trilha a trilha se a chamada em bloco falhar. Só
então reconstrói, do zero, a partir do **conteúdo da bin**, que está ordenado por shot/take.

⭐⭐ **O resultado PARECE inserção porque a reconstrução é determinística.** A timeline é uma
**função pura da bin**: mesmos clipes, mesma ordem, mesmo resultado. Reconstruir é sempre correto e
**não exige guardar estado nenhum**.

### Isto responde a pendência que a análise anterior levantou

A pergunta era *"onde mora o estado de uma ingestão incremental?"*. A resposta deles, no Resolve,
é: **em lugar nenhum. A bin é o estado.**

⚠️⚠️ **E o preço é severo e não documentado:** todo trabalho manual que o editor tenha feito
naquela timeline — aparo, efeito, marcador, reordenação, música, qualquer coisa — **é destruído na
próxima ingestão**. O manual não avisa; ele diz "rode num projeto existente para adicionar mais
material".

⭐ **A decisão de desenho que isso expõe, e é nossa também:**

| abordagem | custo |
|---|---|
| **reconstruir** (Chop Chop) | zero estado a manter, sempre correto — **e apaga o trabalho do editor** |
| **inserir de verdade** | preserva o trabalho — exige saber o que a rodada anterior fez (o XMP privado do lado Premiere deles) |

⚠️ Note que as **duas edições do mesmo produto escolheram lados opostos**: o Resolve reconstrói; o
Premiere guarda `assignedTracks` no XMP privado do projeto. Não é incoerência — é a plataforma:
no Premiere existe metadado privado de projeto para pendurar estado, no Resolve não existe
equivalente conveniente.

---

## 2. O parser de nome — e as duas promessas que ele não cumpre

**Modo automático** (o padrão): o programa pega o nome do arquivo, **corta tudo a partir do
primeiro ponto**, passa para maiúsculas e **extrai todas as corridas de dígitos**. Se houver 4 ou
mais, as **quatro primeiras** viram episódio/cena/shot/take. Se houver exatamente 3, viram
cena/shot/take sem episódio. Menos que isso, nada é reconhecido.

⭐ **É isso, literalmente.** Não há semântica — há posição. O que o manual chama de *"can read a
wide variety of identifiers"* é o efeito colateral de ignorar tudo que não é dígito.

⚠️ **Consequência 1 — a promessa "texto antes não confunde" só vale no modo automático.** No modo
manual, o padrão é montado com os separadores do usuário e casado com **`re.match`**, que **ancora
no início da string**. Qualquer coisa antes do primeiro identificador faz o casamento falhar. O
manual promete o oposto ("adding show titles, interviewee names… won't confuse the extension") sem
distinguir os modos.

⚠️ **Consequência 2 — nomes com ponto perdem tudo depois do primeiro ponto.** Um `A001.C002.mov`
(convenção comum de câmera) vira `A001`. Onde o número da tomada mora depois de um ponto, ele
simplesmente não existe para o parser.

⚠️ **Consequência 3 — número extra ANTES desloca tudo, em silêncio.** Como se pegam as *quatro
primeiras* corridas de dígitos, um número a mais no fim é inofensivo, mas um a mais no começo (uma
data, um número de câmera, um `4K`) empurra a leitura e produz episódio/cena/shot/take **plausíveis
e errados**. Nada levanta erro.

⭐ **A regra do manual — *"as long as there are no additional numbers"* — é honesta, e agora
sabemos que é literal.**

---

## 3. ⭐⭐ O alinhamento por timecode é uma INTERSEÇÃO — e ela descarta material

Para cada grupo (shot, take), o programa:

1. toma como referência o **menor Start TC** do grupo;
2. calcula o deslocamento de cada clipe em relação a ela, **embrulhando na meia-noite** (delta maior
   que 12 h vira o equivalente negativo) e **zerando qualquer desvio acima de 120 s**, com aviso;
3. define a janela comum: começa **quando a última câmera começa**, termina **quando a primeira
   câmera acaba**;
4. **apara cada clipe** para essa janela — cabeça e cauda — e põe todos no **mesmo `recordFrame`**.

⭐ **O manual diz "trimmed to the length of the shortest clip". É mais específico que isso: é a
INTERSEÇÃO.** Uma câmera que entrou 30 s atrasada não é só deslocada — ela **corta 30 s da frente
de todas as outras**. Esse material não fica fora de quadro: ele **não é colocado**.

⛔ **E se não houver interseção nenhuma, o shot/take inteiro é PULADO** — com uma linha no console e
mais nada. Numa diária onde uma câmera rodou em rec-run e outra em free-run, isso some com takes
inteiros sem aviso na interface.

⚠️ Para um stringout — cuja função é **revisar o take inteiro** — aparar pela interseção é uma
escolha discutível. É ótima para conferir sincronia, ruim para assistir.

### O caminho de forma de onda não alinha nada

No modo waveform, os clipes de um mesmo shot/take entram todos com `startFrame = 0` no mesmo
`recordFrame`. **Não há cálculo de deslocamento.** Eles são apenas empilhados.

⭐ **É a confirmação, no código, do que o manual admite na página 16:** por forma de onda, câmera A
não fica em sincronia com câmera B. O `AutoSyncAudio` já casou o áudio de cada câmera com o dela
mesma, antes; o empilhamento não faz mais nada.

⚠️ E note a **ordem do pipeline**: o `AutoSyncAudio` é chamado **logo depois da importação**, antes
de ler metadado e antes de montar bin. O sync não sabe de cena, shot nem take — ele opera sobre a
leva inteira de uma vez.

---

## 4. O mapa de trilhas, e o defeito que nós também temos

- **Câmera → índice de trilha por ordem ALFABÉTICA** do `Camera ID` (que vem do nome da pasta de
  origem). É isso que faz o multi-dia cair na mesma trilha: mesma pasta, mesmo nome, mesma posição.
  ⭐ Determinístico e sem estado — coerente com a §1.
- O índice da trilha de vídeo é **`índiceDaCâmera × maxCanaisDeÁudio + 1`**.

⚠️⚠️ **Ou seja: eles criam tantas trilhas de VÍDEO quanto `câmeras × canais de áudio`, e deixam as
intermediárias vazias** — só para manter os índices de vídeo alinhados com os blocos de áudio. Uma
diária de 3 câmeras com 8 canais vira **24 trilhas de vídeo**, 21 delas vazias.

⭐ **O nosso `host.jsx` documenta exatamente a mesma dor** (*"o layout de áudio força tracks de
vídeo vazias entre as câmeras"*), e resolve com `removeEmptyVideoTracks()` do QE no fim. Eles não
limpam. **Convergência independente: o problema é do modelo de trilhas, não da nossa
implementação.**

- Para trocar o *subtipo* de uma trilha de áudio (adaptive N), eles fazem uma dança: apagam todas
  as trilhas menos a primeira, acrescentam a nova com o subtipo certo no fim e apagam a primeira.
  ⭐ **Não há API para mudar o subtipo de uma trilha existente** — só criar com ele.

---

## 5. ⛔ Um defeito real: dois clipes da mesma câmera no mesmo shot/take se sobrescrevem

O agrupamento guarda `grupos[(shot, take)][cameraID] = clipe`. **É um dicionário por câmera.** Se a
mesma câmera tiver dois clipes com o mesmo shot e take — take partido em dois cartões, arquivo
duplicado com caminho diferente, retake que herdou o mesmo nome — o segundo **substitui o primeiro
silenciosamente**, e o primeiro nunca chega à timeline.

⚠️ Não há aviso, log de descarte nem contagem. O editor vê um stringout completo e plausível, com
material faltando.

---

## 6. Como evitam duplicar ao reimportar

Dentro de cada bin de cena, agrupam por **`File Path`** (não por nome). Para cada caminho com mais
de um clipe:

- separam por **`Usage`** (quantas vezes o clipe está em alguma timeline): o que está **em uso**
  fica;
- entre os não usados, leem **`Date Added`**; os que têm data inválida ou ausente são apagados
  direto;
- os demais são resolvidos por data.

⭐ **`Usage` como critério de "não apague este" é a ideia reusável aqui:** o Resolve já sabe se um
clipe está sendo usado; não é preciso rastrear.

---

## 7. Armadilhas da API do Resolve que o código revela

| armadilha | o que fazem |
|---|---|
| ⭐⭐ **Objetos remotos do Resolve não são *hashable*** | usam `id(obj)` como chave de conjunto para deduplicar antes de apagar. *Um `set()` de `MediaPoolItem` estoura.* |
| ⭐ **Não há caminho de um `MediaPoolItem` do tipo `Timeline` para o objeto `Timeline`** | varrem `GetTimelineCount()` / `GetTimelineByIndex(i)` **comparando NOMES** para reencontrar a timeline que acabaram de criar |
| `CreateEmptyTimeline` devolve algo que não serve para tudo | depois de criar, procuram o item de volta na bin pelo nome |
| duração do clipe | tentam `Frames`; se falhar, `End + 1` |
| `AppendToTimeline` precisa de foco | chamam `SetCurrentTimeline` antes de anexar |

⚠️ **Timecode:** a conversão é um `split(":")` de `hh:mm:ss:ff`. **Não há tratamento de
drop-frame** (o `;` faria a conversão falhar), e **a falha devolve 0** — o clipe vai parar no início
da timeline em vez de levantar erro. Erro silencioso da pior espécie: plausível.

⚠️ **Proxies (`ProxyHunt`):** agrupam por **nome**, mantêm o de maior resolução, chamam
`LinkProxyMedia` com o caminho do menor e **apagam o clipe de proxy da media pool**. Com **três**
resoluções do mesmo nome, um dos itens é perdido do rastreio — nem vinculado, nem apagado. E
agrupar proxy por nome pressupõe que o proxy tem exatamente o mesmo nome do original.

---

## O que levar disto para o Órbita

1. ⭐⭐ **A escolha reconstruir × inserir é a decisão de arquitetura, e agora temos os dois lados
   medidos** (§1). Reconstruir é barato e correto e **apaga o trabalho do editor**; se o Órbita
   reconstruir, isso precisa ser dito na interface, não escondido.
2. ⭐ **Aparar pela interseção descarta material** (§3). Se formos alinhar por TC num stringout,
   decidir explicitamente entre *aparar* e *deslocar mantendo tudo* — e nunca pular um take em
   silêncio.
3. ⭐ **Agrupar por `(shot, take, câmera)` num dicionário perde clipe** (§5). A nossa chave precisa
   tolerar N clipes por câmera por take.
4. ⭐ **`Usage` resolve duplicata sem rastrear estado** (§6).
5. ⚠️ **`id(obj)` para objetos remotos do Resolve** e **timeline reencontrada por nome** (§7) — duas
   armadilhas que custariam uma sessão cada.
6. ⚠️ **Drop-frame não tratado e TC inválido virando 0** (§7) — o modo de falha que mais parece
   sucesso.

## ⚠️ A régua desta rodada

Régua nova, autorizada pelo autor em 2026-08-24: leitura integral permitida; registro de
**mecanismo, não de código**. Nada acima é trecho transcrito — nem o regex do §2, nem a aritmética
do §3. Nenhum mecanismo de licença foi examinado, contornado ou testado; o `LicenseWindow` /
`LicenseCheck` do arquivo foi **pulado de propósito**. Nada instalado, nada executado. O lado
Premiere continua em JSXBIN (só tabela de símbolos) — a leitura integral acima é **só da edição
Resolve**.
