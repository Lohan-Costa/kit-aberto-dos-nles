# Publicar um repositório privado como público — o fluxo, e o que vaza nele

> **De onde isto veio:** a sessão de 2026-08-23/24 do **Órbita**, que auditou o app inteiro,
> descobriu material sigiloso no repositório público, purgou tudo e reconstruiu o canal de
> publicação. Nada aqui é hipotético: cada item custou tempo real, e **três dos quatro erros
> mais caros foram cometidos DEPOIS de eu "verificar"**.
>
> **Por que isto mora no banco de NLEs, sendo assunto de infraestrutura:** todo app de post
> deste ecossistema é desenvolvido contra **material real de produção** — nomes de clipe, de
> bin, de cena, caminhos de storage da emissora. Não existe "material de teste neutro" quando
> o produto é uma ferramenta de montagem. Quem publicar o segundo app vai reencontrar
> exatamente o mesmo problema, e ele não aparece em nenhum guia genérico de open source.
>
> Nível de confiança de tudo abaixo: **`confirmado`** — medido no repositório público real,
> antes e depois de cada correção.

---

## 1. ⭐⭐ O desenho que funciona: allowlist, nunca denylist — `confirmado`

O repositório público é **gerado**, nunca editado à mão. Um script (`publish.py`) copia do
privado só o que está numa lista explícita, e um workflow o roda em CI a cada tag.

⭐ **A propriedade que faz isso valer:** um arquivo novo na raiz do projeto **nasce invisível**
para o público. Esquecer de publicar algo é chato; esquecer de excluir algo é o risco de
verdade — e a allowlist inverte o custo do esquecimento.

Peças que compõem o canal, todas necessárias:

| peça | para quê |
|---|---|
| allowlist de caminhos | decide o que sai |
| lista de diretórios ignorados | `target/`, `node_modules/`, `.venv/`, `build/`, `dist/` — entram por dentro de pasta permitida |
| `.gitignore` **gerado** | o do privado revela o esquema interno (pastas de notas, base de conhecimento) e **não pode ser copiado** |
| varredura de segredos | gitleaks/talisman como gate obrigatório |
| **varredura de MATERIAL** | ver §3 — é a que faltava |

⚠️ **Rodar o gerador localmente é proibido, e por um motivo não óbvio:** a máquina de
desenvolvimento tem justamente as pastas que não podem sair. Rodar em CI, num checkout limpo,
é o que garante que a allowlist esteja sendo testada de verdade.

---

## 2. ⛔⛔ O CHECKLIST DE ITENS SÓ PEGA O QUE JÁ ACONTECEU UMA VEZ — `confirmado`

**O achado mais transferível desta sessão inteira**, e ele não é técnico.

O projeto tinha um checklist de segurança de publicação, escrito com cuidado, com três itens
nomeados (uma tabela específica, uma frase específica, um raciocínio específico). Ele foi
**seguido corretamente** antes de um release — e mesmo assim **22 identificadores reais de
infraestrutura** foram para o repositório público, porque nenhum deles era um dos três.

⭐ **A correção não é acrescentar um quarto item. É trocar a NATUREZA da regra:**

> **Regra de CLASSE, não de item.** Não pode sair: nome de servidor, share, workspace ou letra
> mapeada; nome de projeto/produção, inteiro ou truncado; nome de arquivo de mídia real (clipe,
> bin, sequência, cartão); caminho absoluto de máquina e nome de usuário do sistema; UMID de
> mídia real; caminho de documento interno.

⚠️ **E uma regra de classe sem execução automática é intenção, não controle** — ver §3.

---

## 3. ⭐ A guarda de material: um `grep` que aborta a publicação — `confirmado`

Um passo no gerador que varre o artefato inteiro procurando uma lista de termos proibidos, e
**falha o publish** se achar qualquer um.

```python
TERMOS_PROIBIDOS = ["NEXIS-01", "servidor-ingest", "<produção>", "<volume do autor>", ...]

def run_material_scan(dest):
    achados = [f"{q}: {t!r}" for q in dest.rglob("*") if q.is_file()
               for t in TERMOS_PROIBIDOS if t in q.read_text(errors="ignore")]
    if achados:
        sys.exit(1)
```

⚠️⚠️ **A lista de termos proibidos é ela própria sigilosa** — ela é um índice do que existe.
Ponha-a no **gerador**, que não está na allowlist, e nunca num arquivo publicado.

⭐ **Ela se pagou na primeira execução:** pegou duas ocorrências que uma varredura manual
cuidadosa, feita minutos antes pela mesma pessoa, tinha deixado passar.

**Varra o artefato inteiro, não só o que você acha que mudou.** O modo de falha típico é um
comentário escrito hoje com um exemplo real ao lado do código.

---

## 4. ⛔ Anonimizar fixture: LISTA BRANCA, e o motivo é de tipo — `confirmado`

Fixtures de teste de app de post são metadado de mídia real: caminhos, nomes de clipe, UMIDs.
Anonimizá-los é obrigatório e **falha de dois jeitos opostos** se feito por texto cru.

Duas tentativas erradas, medidas:

1. **Substituição no texto do JSON** → renomeou as **CHAVES** do esquema (`"sequencia"` virou
   hash). O arquivo deixa de ser legível pelo código que o consome.
2. **Substituição em toda string do JSON** → renomeou os **VALORES DE FORMATO**. O
   `operational_pattern_ul` (`060e2b34.04010102…`, o rótulo SMPTE que diz se o MXF é OP-Atom
   ou OP1a) virou hash, e **12 testes caíram** porque o parser deixou de reconhecer o formato.

⭐⭐ **A lição: num fixture, "nome" e "formato" moram no mesmo tipo (string), e só o ESQUEMA
sabe a diferença.** Por isso a regra é **lista branca de campos**:

```python
CAMPOS_DE_MATERIAL = {"path", "material_package_name", "file_package_name", "reel_name"}
CAMPOS_DE_UMID     = {"material_package_umid", "file_package_umid"}
# tudo o que não está aqui passa INTACTO, por construção
```

O modo de falha vira *"esqueci de anonimizar um campo"* (que um grep encontra) em vez de
*"quebrei o parser"* (que só o teste encontra).

### Duas propriedades que a substituição precisa preservar

- **TOKEN, não string inteira.** O motor de sync ordena a fila de busca por **prefixo comum**
  entre nome de master e nome de arquivo. Trocar cada nome por um identificador aleatório
  quebra os testes por construção. Mapeando token a token (`20240531` → `20260101`,
  `pana2774` → `cam0001`), prefixos compartilhados continuam compartilhados.
- **UMID: preserve o rótulo SMPTE, troque os 16 bytes finais.** O prefixo é padrão da norma e
  não identifica nada; o fixture continua plausível para quem for auditar o parser.

⚠️ **E o `null` existe.** Um gabarito usa `null` para "este clipe não tem par" — um `re.sub`
recebendo `None` estoura no meio da escrita.

⚠️ **Talisman/gitleaks confunde UMID com número de cartão de crédito** (64 dígitos hex). A
exceção é legítima e precisa ser versionada com a justificativa.

---

## 5. ⭐ Teste que lê disco não pode NOMEAR o material — `confirmado`

Um teste que abre uma pasta de mídia real e crava o nome do arquivo põe material sigiloso
dentro de **código publicado**. E é frágil de qualquer jeito.

```rust
// ⛔ antes
format!("{base}/SOM DIRETO/20240531_ZOOM0034_Tr12.WAV")

// ✅ depois — pergunta ao disco qual é
let som = fs::read_dir(&dir)?.filter_map(Result::ok)
    .map(|e| e.file_name().to_string_lossy().into_owned())
    .find(|n| n.to_ascii_lowercase().ends_with(".wav"))
    .expect("a pasta de som da mídia de exemplo não tem .wav");
```

Mesma disciplina para asserções: em vez de `assert!(files[0].ends_with("<clipe real>.mov"))`,
verifique a **propriedade** — `assert_eq!(files, files_ordenados_naturalmente)`. Prova a mesma
coisa e não depende de qual material está na pasta.

---

## 6. ⛔⛔ Purgar de verdade: apagar tag NÃO apaga do servidor — `confirmado`

Um canal de publicação que força um commit único em `main` a cada release **limpa a `main`
sozinho** na próxima publicação. **As TAGS não.** Cada tag ancora um commit com a árvore
daquela versão, e cada release está presa a uma tag.

| ação | efeito real |
|---|---|
| `git push --delete refs/tags/vX` | objeto vira **inalcançável**, continua recuperável por SHA |
| `git push --force` em `main` | idem |
| **apagar e recriar o repositório** | ⭐ **objeto sai do servidor** |

⚠️ **Meça o custo antes de propor:** forks, stars, watchers e downloads. No caso medido eram
**0, 0, 0 e 111** — o que tornou a recriação barata. Com forks, é impossível: cada fork retém
tudo e não se purga.

### A ordem que não deixa o produto sem download

1. Publicar a versão **limpa** primeiro, e **verificar** que ela está no ar com os artefatos.
2. Só então apagar o que é velho.

Um script de purga deve ter **trava**: recusar-se a apagar se a versão nova não estiver no ar
com os instaladores. (No caso medido, essa trava salvou três vezes, porque o release falhou
três vezes antes de subir.)

### ⚠️ Recriar o repositório destrói a chave de publicação

Se o push do CI usa **deploy key**, a metade pública está registrada **no repositório** — e
morre com ele. A privada vive como secret e **não se lê de volta**, então não dá para
rederivar a pública.

**Gere um par novo ANTES de apagar**, e tenha o plano pronto:
`ssh-keygen -t ed25519` → pública vira deploy key **com escrita** no repo novo → privada vira
o secret no repo privado. ⚠️ **A caixa "Allow write access" é o erro mais fácil de cometer.**

---

## 7. ⛔⛔ A ARMADILHA DE VERIFICAÇÃO — `confirmado`

Quatro erros caros nesta sessão, e **em todos eu tinha verificado antes**. O padrão é único:

> **Verifiquei o lugar que CONFIRMAVA, nunca o que poderia desmentir.**

| o que quebrou | o que eu "verifiquei" |
|---|---|
| `--locked` com o lockfile em versão antiga | rodei o comando **sem** a flag nova |
| pin de pacote que exige Python 3.12 (CI é 3.11) | `pip --dry-run` no venv de **desenvolvimento**, que é 3.12 |
| `--locked` passado a um comando que não o aceita | validei o **YAML**, não o comando |
| escopo do vazamento ("é de hoje") | medi só onde a auditoria já apontava — nunca perguntei **"desde quando?"** |

⚠️⚠️ **E uma armadilha de ferramenta, específica e traiçoeira:** conferir conteúdo publicado com
`Invoke-RestMethod` sobre um `.json` **parseia o JSON em objeto**, e o regex depois roda no
objeto — devolvendo **"0 ocorrências" sem ter lido texto nenhum**. Foi um falso "limpo".
Leitura autoritativa: a API de `contents` (base64) ou `Invoke-WebRequest -UseBasicParsing`.

⭐ **A regra que sai daqui:** *uma verificação que não pode falhar não está verificando.* Antes
de aceitar um "passou", pergunte o que aconteceria se o defeito existisse — se a resposta for
"o mesmo resultado", a verificação é decorativa.

---

## 8. ⚠️ Mudança de CI: uma de cada vez — `confirmado`

Quatro mudanças de pipeline mandadas juntas (lockfile, pins de Python, pinagem de ações por
SHA, permissões do token). **Três quebraram o release, em sequência**, cada uma escondendo a
seguinte, a **20 minutos de build por ciclo**.

**Mudança de CI não se valida por leitura.** Ou se roda o comando exato no ambiente de
destino, ou se manda uma de cada vez.

### O que atrapalha o diagnóstico, e o conserto

Sem CLI autenticada não se lê o log de workflow de repositório **privado** — vê-se *que*
falhou, não *por quê*. Dois dos três ciclos foram gastos só localizando a causa.

⭐ **O contorno que funcionou enquanto isso:** o repositório **público** expõe
`/actions/runs/<id>/jobs` **sem credencial**, e isso já diz **qual PASSO** falhou (o *conteúdo*
do log continua exigindo auth). Quando o pipeline tem duas pernas — gerar o público, depois
compilar nele — metade do diagnóstico é gratuita.

---

## 9. A receita de conferência pós-publicação — `confirmado`

Confira o **RESULTADO**, nunca o status do workflow. *Status é intenção; artefato com
`state=uploaded` é fato.*

```
1. o release existe, não é rascunho, e tem TODOS os instaladores?
2. o CHANGELOG do PÚBLICO abre com a versão nova?   (prova que a allowlist copiou o certo)
3. as pastas privadas dão 404 no público?
4. a varredura de material passa contra o artefato?
5. a tag chegou no repositório de origem?
```

⚠️ **Os artefatos aparecem DEPOIS do release existir.** Num caso medido, o release surgiu com
1 de 2 instaladores e ficou assim por ~4 minutos. Conferir cedo demais é o mesmo erro de
conferir o status.

---

## 10. O que ficou pendente (para quem continuar)

- **Hash-pinning de verdade** nas dependências Python (`--require-hashes`). Fixar a versão
  impede resolução silenciosa; não prova que o artefato baixado é o mesmo.
- **Alinhar a versão de linguagem entre desenvolvimento e CI.** O desencontro (3.12 × 3.11)
  produziu uma das três quebras e volta a cobrar no próximo pin.
