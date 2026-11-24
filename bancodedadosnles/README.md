# Banco de Dados NLEs — memória de engenharia reversa de formatos de edição

> **Isto não é um app.** É uma **memória organizada** das descobertas sobre os formatos/protocolos
> dos NLEs (Avid, Premiere, DaVinci Resolve) e sobre a tradução entre eles. Os apps que estamos
> desenvolvendo **alimentam** este banco (toda descoberta nova é registrada aqui) e **consultam**
> este banco (para não reinventar a roda: ClassIDs, GUIDs, ticks, cadeias de resolução, fórmulas
> de conversão de efeitos, etc.).

## Para que serve

Cada app de edição (AAF/DRT/PRPROJ) precisa, repetidamente, das mesmas verdades de baixo nível:
a tabela de `ClassID` do Premiere, a cadeia `CompositionMob → … → URLString` do Avid, a taxa de
ticks, o layout do blob `EffectFiltersBA` do Resolve, o de-para de posição entre as três NLEs.
Em vez de cada projeto redescobrir isso, **a verdade vive aqui, uma vez, versionada e citável**.

## Por onde começar

⭐⭐ **[transversal/operacoes-de-nle.md](transversal/operacoes-de-nle.md)** — o mapa por **mecânica**
(como se move um clipe, como se insere mídia, como se mexe em bin e metadado), com uma coluna por
NLE. O resto do banco está organizado por **produto** e por **formato**; este arquivo é o índice
por **capacidade**, e é o que responde às perguntas que todo app nosso repete.

⭐⭐⭐ **[transversal/matriz-de-plataforma.md](transversal/matriz-de-plataforma.md)** — a **regra
master do desenvolvimento**: todo app nasce numa plataforma e roda na outra. Antes de escrever
código que toque em caminho, disco, processo, porta ou diálogo do sistema, consulte a linha da
variável — Windows e macOS lado a lado — e registre ali os dois lados do que descobrir.

## Como está organizado

```
bancodedadosnles/
  README.md            ← este arquivo
  INDEX.md             ← índice mestre navegável (o "mapa")
  CONVENCOES.md        ← schema dos JSON, níveis de confiança, como contribuir
  protocolos/
    aaf/               ← Avid Advanced Authoring Format
    prproj/            ← Adobe Premiere Pro project
    drt-drp/           ← DaVinci Resolve Timeline / Project
    mxf/               ← essência / wrapper (MXF, UMID)
    otio/              ← OpenTimelineIO (intercâmbio aberto)
  transversal/         ← o que NÃO pertence a um formato só:
                          modelo neutro de efeitos, tempo/timecode, mapa de tradução entre NLEs,
                          e COMO ANALISAR O EXECUTÁVEL DO CONCORRENTE (método de eng. reversa
                          de aplicativo — usar quando a doc não existe ou o SDK é fechado)
```

Cada pasta de protocolo segue o mesmo padrão:

```
protocolos/<formato>/
  README.md       ← visão geral em prosa: o que é o formato, como abrir, mapa das peças
  <tema>.md       ← descobertas narradas por tema (estruturas, efeitos, escrita, …)
  dados/*.json    ← os fatos estruturados, prontos para um app importar
  fontes.md       ← de onde veio cada descoberta (qual app/doc validou) — rastreabilidade
```

## Como um app consulta (camada de dados)

Os arquivos em `protocolos/*/dados/*.json` e `transversal/*.json` são a **interface de consumo**.
São JSON puro, sem dependência, importável de Python, Go, Rust ou JS. Cada arquivo é
auto-descritivo: traz `_meta` (protocolo, confiança, atualização, fontes) e os dados.

Exemplo (Python):

```python
import json, pathlib
BANCO = pathlib.Path("/.../bancodedadosnles")
classids = json.loads((BANCO/"protocolos/prproj/dados/classids.json").read_text())
sequence_class = classids["entries"]["Sequence"]["classid"]
```

Há também um helper opcional `consulta.py` (stdlib pura) que resolve ids e dá atalhos:

```python
from consulta import Banco
banco = Banco()
banco.classid("Sequence")          # -> "6a15d903-..."  (ClassID do PRPROJ)
banco.ticks_por_segundo()          # -> 254016000000
banco.dados("aaf/operationdefs")   # -> dict do JSON
banco.confianca("drt-drp/timemap") # -> "confirmado"
```
CLI: `python consulta.py listar` · `python consulta.py mostrar prproj/classids`.

### Ferramentas que fazem o banco ser consultado

| peça | o que faz |
|---|---|
| `../CLAUDE.md` (pasta-mãe dos apps) | lido pelo Claude Code em TODA sessão de todo app, nas duas máquinas: banco primeiro, regra master de plataforma |
| [`skills/ciclo-media-dev/`](skills/ciclo-media-dev/SKILL.md) | a skill `/ciclo-media-dev`: achar o banco, consultar antes, revisar plataforma, registrar depois. Ligar em cada máquina: `python3 skills/instalar.py` (Windows: `py skills\instalar.py`) |
| [`skills/piloto/`](skills/piloto/SKILL.md) · [`skills/emissora-secdev-skill/`](skills/emissora-secdev-skill/SKILL.md) | `/piloto` (operar a máquina) e o desenvolvimento seguro; o mesmo `instalar.py` liga as três |
| [`transversal/ferramentas-de-desenvolvimento.md`](transversal/ferramentas-de-desenvolvimento.md) | o mapa das ferramentas da família: ⭐ REA, piloto, zelador, laboratório, skills, gancho de contexto |
| [`verificar_plataforma.py`](verificar_plataforma.py) | varre um repositório com as regex de [`transversal/matriz-de-plataforma.json`](transversal/matriz-de-plataforma.json) e mostra, em cada ocorrência, os dois lados e a armadilha |

A **prosa** (`*.md`) é para humanos e agentes LLM lerem — explica o *porquê* e as nuances que
um JSON não carrega. A regra: **todo número/constante que um app usaria fica também no JSON**;
o Markdown narra e contextualiza.

## Princípio editorial

- **Registrar como foi descoberto**, não só o resultado: medido empiricamente? inferido? hipótese?
  (ver níveis de confiança em `CONVENCOES.md`). Uma constante "validada no Resolve 19" vale mais
  que uma "provável".
- **Citar a fonte**: qual app, qual arquivo de amostra, qual data. Rastreabilidade > certeza falsa.
- **Dizer a VERSÃO do NLE** em que a coisa foi medida, sempre. Formato é versionado: o PRPROJ
  numera cada elemento, e `Sequence` passou de `Version="11"` (Premiere 2024/2025) para `12`
  (2026). Uma descoberta sem versão é uma descoberta sem validade conhecida — regra e campos
  em [CONVENCOES.md §1.1](CONVENCOES.md).
- **Não duplicar o código dos apps** — referenciar. Aqui mora o *conhecimento do formato*, não a
  implementação. Se o RELINKER tem o parser, aqui fica o mapa que o parser usa.
```
