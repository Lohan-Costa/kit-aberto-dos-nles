# Nomes por padrão: a gramática de wildcard, e as armadilhas dela

> Origem: **Assist anterior** (`assist_anterior/nomes/`, 2026-08-28) e **Órbita**
> (`src-python/nomes/`, portado em 2026-09-05). Ambos em produção.
>
> ⭐ Isto entrou no banco porque **não havia nada aqui sobre nomear em lote**, e é
> uma mecânica que todo produto nosso vai querer: renomear clipe na bin, nomear
> subclipe, nomear a bin de cena, nomear o arquivo exportado. A gramática é uma só.

---

## 1. A sintaxe — `confirmado`, e ela é MINÚSCULA de propósito

| token | significado |
|---|---|
| `%campo` | o valor do campo |
| 🆕 `%{campo}` | o mesmo valor, com a tag **fechada** |
| `%%` | um `%` literal |
| qualquer outra coisa | literal |

**Sem modificadores.** Não há `%campo:upper`, padding nem slicing. Onde a coluna crua
não serve, quem resolve é um **campo derivado já pronto** (`%cena`, `%plano`, `%take2`),
calculado na camada de baixo.

⭐ A razão é de manutenção: um modificador é uma segunda linguagem dentro da primeira,
e quem a escreve tem de a documentar, validar e mostrar erro. Um campo derivado a mais
custa uma função.

### ⚠️⚠️ O RECUO na fronteira do `_` — a peça que decide o desenho

`_` é caractere **válido** de nome de campo (as colunas do Avid normalizam
`Shoot Date` → `shoot_date`). Mas o padrão que o editor escreve é
`C%cena_P%plano_T%take2`, onde `_P` e `_T` são **literais**.

Um casamento guloso lê `plano_t` e não acha campo — e aí o `_T` sumiria em silêncio,
com um nome plausível na tela. A regra é: **recuar até o maior prefixo do catálogo que
termine num `_`**, devolvendo o resto como literal.

⛔ **E a fronteira em `_` não é negociável:** sem ela, `%scenex` recuaria para
`scene` + `x`, e um erro de digitação viraria um nome plausível. Com ela, `%scenex` é
desconhecido e a tela pinta de vermelho.

⚠️ **O hífen NÃO pode ser caractere de campo.** Foi tentado (`%nome-original`) e
recusado: `-` é comum demais em nome de arquivo, e aceitá-lo quebraria
`C%cena-T%take`. Medido: `%nome-original` lê apenas `%nome` e deixa `-original` como
literal.

### 🆕 ⭐⭐ A TAG FECHADA `%{campo}` — o caso que o recuo NÃO salva (2026-09-06)

O recuo resolve `%shoot_T%take` porque existe uma fronteira (`_`) para recuar até ela.
**Não existe fronteira nenhuma** em:

```
C%cenaP%plano     →  lido como  %cenaP  (campo que não existe)
```

`cenaP` não tem `_`, e adivinhar onde o campo termina no meio de um literal colado é
**chute**. As duas saídas conhecidas já estavam catalogadas como ruins (acusar erro
recusa um padrão legítimo; render vazio produz lote truncado e plausível) — porque a
pergunta é **ambígua no texto**, e não há resposta certa a extrair dela.

⭐ **A saída é tirar a pergunta: delimitar.** `%{cena}` não recua e não adivinha —
o campo é o que está entre as chaves.

```
C%{cena}P%{plano}-T%{take}
```

⚠️⚠️ **E a peça que faz isso funcionar não é a sintaxe — é o GESTO.** A forma fechada só
serve se o editor a produzir sem saber que ela existe: **confirmar uma sugestão do
autocomplete (Enter, Tab, clique) escreve a forma fechada**, e o card de atalho também.
Quem digita continua podendo usar `%campo` solto; o que se garante é que o **caminho de
menos esforço** produza a forma sem ambiguidade.

⛔ **O que NÃO se fez:** exigir confirmação para todo campo (*"se não confirmar, o
programa não gera o wildcard"*, pedido literal do autor). Isso quebraria todo padrão já
escrito — inclusive o padrão de fábrica `%nome` — e puniria quem digita mais rápido que
a lista aparece, sem resolver nada que a delimitação não resolva.

Regras de borda, todas com teste:

| caso | resposta |
|---|---|
| `%{cena` (aberta) | **desconhecida**, e consome só `%{` + o identificador |
| `%{}` / `%{25}` | desconhecida |
| `%%{cena}` | escape ganha — literal `%{cena}` |
| `%{shoot_t}` | **não recua**: quem fechou já disse onde o campo acaba |

⚠️ A tag aberta **não pode engolir o resto do padrão**: meio padrão é o estado normal de
quem está digitando, e o vermelho cobriria um trecho correto — além de tirar do
autocomplete o token onde a mão está.

### 🆕 A CAIXINHA sobre o input, e o pixel que decide a implementação

O formato veio de um print do DaVinci Resolve: cada tag como uma pílula com fundo
próprio. A técnica de colorir um `<input>` é um **espelho** — o texto do input fica
transparente e um `<div>` idêntico atrás desenha os pedaços coloridos —, e isso impõe uma
restrição dura: **as duas camadas casam caractere a caractere**.

| tentação | por que não |
|---|---|
| esconder `%{` e `}` para a pílula ficar limpa | são caracteres **reais**; sumir com três desloca o cursor de tudo o que vem depois |
| dar `padding` horizontal à pílula | empurra o texto e tira o cursor de registro |

⭐ **A solução:** delimitadores desenhados, apenas **apagados**, e padding só **vertical**
(que não afeta a métrica de linha). O respiro visual vem dos próprios delimitadores
ocupando o lugar deles. *A caixinha é decorativa na métrica e informativa na leitura — a
única forma de ela poder existir sobre um input.*

---

## 2. O semáforo do preview — `confirmado` (decisão do autor, 2026-08-28)

| situação | resposta |
|---|---|
| `%campo` que não existe | 🔴 **bloqueia** |
| o nome renderizado sai vazio | 🔴 **bloqueia o LOTE INTEIRO**, e basta um |
| campo existe mas está vazio neste item | 🟡 marca a linha |
| dois itens com o mesmo nome | 🟡 marca **os dois** |

⭐ **Colisão de nome não bloqueia** — o Avid aceita nome repetido, e travar seria
inútil em documentário sem cena. Mas é marcada **dos dois lados**: quem vê só o
segundo assinalado conclui que o primeiro está certo.

⚠️ **Vazio bloqueia o lote, não o item.** Aplicar metade é pior que não aplicar: a bin
fica em dois estados e ninguém sabe onde parou.

### 🆕 ⛔⛔ SÃO DOIS SEMÁFOROS, e confundi-los custou dois defeitos (2026-09-06)

A tabela acima vale para **RENOMEAR**: escrever por cima de nomes que já existem. Ela
**não vale para CRIAR** (nomear subclipes que ainda vão nascer), e a diferença é a linha
do vazio:

| | renomear | criar |
|---|---|---|
| campo desconhecido | 🔴 bloqueia | 🔴 bloqueia |
| nome sai vazio | 🔴 **bloqueia o lote** | ⭐ **cai no nome de origem** |
| padrão vazio | 🔴 bloqueia | ⭐ **cai no padrão de fábrica** |

⭐ A razão é do material, não do código: ao renomear, metade aplicada deixa a bin em dois
estados; ao criar, um take que não casa o padrão **continua sendo material que o editor
quer na bin** — recusar tudo por causa dele faria uma tomada sem claquete impedir as
cinquenta que têm.

⛔ **Os dois defeitos que saíram de aplicar o semáforo errado**, ambos achados pelo autor
usando (Órbita, aba Subclipar):

1. **Um aviso vermelho falso, com o campo ainda vazio** — *"Algum item ficaria SEM
   NOME"* — que **desligava os dois botões** por um problema que aquele caminho não tem.
2. **A prévia sumindo inteira** quando um único item renderizava vazio: com
   `%nomedoaudio`, um take sem áudio bloqueava, e a tela (que só desenha as linhas
   quando não está bloqueada) escondia a lista toda. Sintoma que engana muito: *"a tag
   sozinha não funciona, mas com um 'a' no fim funciona"* — o `" a"` garantia nome
   não-vazio.

⚠️ **E o fallback tem de se DECLARAR.** O nome que veio do fallback aparece no meio da
lista com outra cara; sem uma marca (âmbar, e contagem no resumo), o editor não tem como
saber que ali o padrão não pegou. *O log dizia; a tela, não.*

---

## 3. ⭐⭐ O preview roda no MOTOR, nunca no cliente

O espelho colorido da caixa de texto pede um parser — e a tentação é escrevê-lo em
JavaScript, onde a tela está. **Não se faz.** Seriam duas implementações da mesma
gramática, e a que divergisse seria **a que o editor CONFERE contra a que o motor
APLICA**.

O contrato é uma função só:

```
prever(padrao, fichas) -> {
  bloqueado: bool,
  invalidos: [token],      # os que não são campo
  tokens:    [{bruto, inicio, fim, campo, cauda}],
  linhas:    [{nome, vazios, vazio_total, repetido}],
}
```

O cliente **pinta** `tokens` e **desenha** `linhas`. Não interpreta nada.

⚠️ E o `cauda` viaja para a tela poder **mostrar** que houve recuo: é uma decisão do
motor sobre o que o editor digitou, e decisão calada não passa.

### 🆕 ⛔⛔ "No motor" não basta: tem de ser o MESMO CÓDIGO QUE ESCREVE (2026-09-06)

A regra acima foi seguida à risca e **mesmo assim** o preview mentiu. O motivo é sutil e
vale para qualquer produto:

> O preview do **criar** chamava o `prever` genérico; a escrita chamava a função de
> aplicar, que tinha **uma regra a mais** (o fallback para o nome de origem). Duas
> implementações da mesma pergunta, ambas no servidor — e a que divergia era exatamente
> *a que o editor confere* contra *a que o motor aplica*.

⭐ **O conserto é estrutural: `aplicar` passa a ESCREVER O QUE `prever` DEVOLVEU.** Não
"chama a mesma gramática", não "usa a mesma regra" — consome a mesma resposta. Um teste
compara as duas saídas e reprova se um dia divergirem.

### 🆕 ⛔ E o cliente não pode GUARDAR as fichas

O painel recebia as fichas na leitura e as devolvia a cada tecla. Quando a tela permitiu
**editar um campo** (a cena, em lote), a resposta da edição trazia os itens atualizados e
**não as fichas** — que envelheciam ali, caladas. A tela desenhava `C25-1_T01` e a bin
recebia `C25_T02`.

⭐ **Regra:** as fichas ficam no lado que escreve, e o preview manda só
`{id_da_leitura, padrao}`. Some a chance de envelhecer, e a lista deixa de subir inteira
a cada tecla digitada.

⚠️ O sintoma foi o que denunciou a causa, e o autor o descreveu sem saber: *"só depois
que eu apaguei os clipes das outras cenas que o painel pareceu ter dado um refresh"* — a
rota de remover era a única que devolvia fichas. **O preview se consertava por
acidente.**

---

## 4. Procedência do campo — três naturezas, não duas

| natureza | significado |
|---|---|
| `medido` | veio de coluna do NLE ou atributo do mob — **fato** |
| `derivado` | calculado por nós a partir de outro campo — **palpite fundamentado** |
| `historico` | veio do que o APP já fez com o item |

⭐ A terceira entrou em 2026-09-05 e não é um caso de `derivado`: um campo derivado se
**recalcula** a partir do que está na tela; um campo de histórico só existe porque
houve uma ação nossa antes. **Se o histórico sumir, ele some junto** — o que nenhum
campo medido nem derivado faz. Por isso se pinta diferente.

⚠️ E a precedência é declarada: **coluna medida > campo do item > derivado**. O
derivado nunca apaga o medido, mas **preenche** o medido-vazio.

### 🆕 ⭐⭐ A exceção: o campo que a TELA deixa editar ganha de todos (2026-09-06)

Quando a interface permite **corrigir um campo à mão** (no Órbita, a cena), esse campo
sai da precedência geral e passa a render **o que está na tela**.

⛔ Sem a exceção, uma bin com uma coluna homônima (`Cena`, em português) faria a coluna
crua ganhar da correção que o editor **acabou de digitar** — a tela mostrando uma coisa e
o NLE recebendo outra, calado.

⭐ E a coluna não se perde: ela continua acessível **pelo nome dela** (`%scene`). O autor
nomeou os dois propósitos ao pedir:

> *"`%cena` = valor indicado no painel refletindo possível alteração manual e o
> presumido. `%scene` = valor da coluna Scene como ele é."*

⚠️ **A armadilha de leitura aqui:** no material dele isso já funcionava **por acaso** —
a coluna se chama `Scene` (inglês), normaliza para `scene` e não colidia com `cena`.
Funcionar por acaso e funcionar por construção parecem iguais até a primeira bin em
português.

---

## 5. As armadilhas que já cobraram

⛔ **`or ""` engole o take 0.** `0 or ""` é `""` em Python, e um take 0 sumiria do
nome sem rastro. O certo é `"" if bruto is None else str(bruto)`. *(Achado por teste
de mutação.)*

⛔ **`zfill(2)`, nunca fatiar.** `[-2:]` truncaria, e o take `100` viraria `00`,
colidindo com o take 0 — dois clipes com o mesmo nome e nada na tela denunciando.

⛔ **Take fracionário precisa preservar o ponto.** Um órfão batizado pela posição sai
como `T002.1`; um `re.sub(r"\D", "", ...)` devolveria `0021`, virando um take 21 que
pode existir de verdade.

⭐ **Todo item do mesmo lote tem de ter as MESMAS chaves.** Sem completar a união, um
`%production` bloquearia num clipe e passaria no vizinho, **dentro do mesmo arrasto** —
porque um tem a coluna e o outro não.

⚠️ **Toda chave produzida tem de ser digitável.** A normalização de nome de coluna
(`"Shoot Date"` → `shoot_date`) e a validação de campo do padrão são **a mesma regra**;
se divergirem, existe campo no catálogo que o padrão não alcança.

---

## 6. Onde escrever, e como conferir

⚠️⚠️ **`SetMobInfo` é UMA COLUNA POR CHAMADA** — cinquenta clipes são cinquenta idas
ao Media Composer, e a tela precisa mostrar isso andando.

⚠️⚠️ **`Save Bin` (DoCommand 1004) é ASSÍNCRONO.** Ele devolve "aceito", não
"gravado". Uma leitura do `.avb` logo em seguida devolve o estado ANTERIOR, com toda a
cara de resposta boa — foi assim que um spike concluiu *"não persiste"* sobre algo que
persistia. Quem escreve em lote **confirma relendo o disco**, e "não confirmado" é
resposta legítima que a tela precisa mostrar.

⭐ **Só escreva o que MUDA.** Num lote de 50 em que 3 mudam, 47 escritas seriam gRPC
jogado fora e sujeira na bin.

---

## Onde isto está implementado

| arquivo | o quê |
|---|---|
| `DRAMASYNC/src-python/nomes/template.py` | a gramática, o recuo, 🆕 a tag fechada, o render |
| `DRAMASYNC/src-python/nomes/campos.py` | catálogo, precedência, procedência |
| `DRAMASYNC/src-python/nomes/preview.py` | o semáforo do **renomear** |
| 🆕 `DRAMASYNC/src-python/avid/nomear.py::prever` | o semáforo do **criar** — e a fonte única de `aplicar` |
| `DRAMASYNC/src-python/avid/renomear.py` | a costura com o Media Composer |
| `DRAMASYNC/plugins/avid-panel/static/painel.html` | 🆕 o espelho, a caixinha e o gesto que fecha a tag |
| `_ASSIST ANTERIOR/assist_anterior/nomes/` | a origem, onde nasceu |

⭐ **ADR de referência:** `DRAMASYNC/docs/adr/0024-a-tag-fechada-e-a-forma-sem-ambiguidade.md`
(vai para o repositório público).
