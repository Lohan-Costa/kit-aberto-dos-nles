# Convenções do banco

Regras para que o banco seja consistente, consultável por máquina e confiável.

## 1. Níveis de confiança

Toda descoberta carrega um nível. É o campo mais importante do banco: distingue o que um app
pode usar cegamente do que ainda é palpite.

| nível | significado | quando usar |
|---|---|---|
| `confirmado` | Validado empiricamente (round-trip, abriu no NLE-alvo, byte-exato, ou medido). | A constante/estrutura foi testada e bateu. |
| `inferido` | Derivado com forte evidência de amostra real, mas sem teste de ida-e-volta. | Lido de um arquivo real e coerente, ainda não reescrito/reaberto. |
| `hipotese` | Suposição plausível a confirmar. | Analogia, doc oficial não verificada na prática, 1 ponto só. |
| `pendente` | Sabe-se que existe, falta decifrar. | Campo/blob identificado mas não decodificado. |

No Markdown, marcar inline quando útil: `(confirmado, RELINKER 2026-06-13)`.
No JSON, é o campo `confianca` (por arquivo em `_meta`, ou por entry quando varia).

## 1.1 Toda descoberta carrega a VERSÃO do app em que foi medida

Tão obrigatório quanto o nível de confiança, e pela mesma razão: um fato de formato só vale
dentro da versão que o produziu. Os NLEs versionam estrutura entre releases — no PRPROJ, cada
elemento tem seu próprio atributo `Version`, e eles mudam (`Sequence` era `11` no Premiere
2024/2025 e é `12` no 2026).

- No Markdown: banner no topo do arquivo dizendo a versão, e a **impressão digital** que permite
  conferir (no PRPROJ, a tabela de `Version` por elemento).
- No JSON: `_meta.nle` com a versão exata, e `_meta.impressao_digital` quando houver como
  fingerprintar.
- Descoberta aplicada a um arquivo de outra versão cuja impressão digital diverge **volta a ser
  `hipotese`** até ser remedida.

**Onde ler a versão** (não confiar em caminho de preset nem no nome da pasta de instalação —
eles ficam obsoletos dentro do projeto):

| formato | campo |
|---|---|
| PRPROJ | `MZ.BuildVersion.Modified` no `Project` (o `Created` é a versão que criou, quase sempre outra) |

## 2. Schema dos arquivos `dados/*.json`

Todo JSON de dados é auto-descritivo e segue esta forma:

```json
{
  "_meta": {
    "protocolo": "prproj",
    "titulo": "ClassIDs dos elementos do PRPROJ",
    "confianca": "inferido",
    "atualizado": "2026-06-27",
    "fontes": ["DRAMASYNC/docs/reverse-engineering/premiere-multicam-prproj.md"],
    "nle": "Adobe Premiere Pro 2024/2025",          // versão EXATA em que foi medido
    "impressao_digital": {"Sequence": 11},          // como conferir se outra amostra é a mesma versão
    "notas": "Lidos de PROJETO_MULTICAM_TEMPLATE.prproj"
  },
  "entries": {
    "Sequence": {
      "classid": "6a15d903-8739-11d5-af2d-9b7855ad8974",
      "confianca": "confirmado",
      "nota": "container de timeline"
    }
  }
}
```

Regras:
- `_meta` é **obrigatório**. `entries` (ou `items`/`mappings`, conforme o conteúdo) carrega os dados.
- Datas em ISO `YYYY-MM-DD`. Sempre absolutas (nunca "ontem").
- `fontes` aponta para caminhos relativos à pasta `PROGRAMAS COM CLAUDE/` (onde vivem os apps) ou
  URLs. Permite rastrear de volta à origem.
- `confianca` no entry **sobrepõe** a do `_meta` quando presente.
- Não inventar valor. Se não se sabe, omitir o campo ou usar `"confianca": "pendente"`.

## 3. Estrutura de uma pasta de protocolo

```
protocolos/<formato>/
  README.md     ← o que é, container (gzip/zip/COM), como abrir, mapa das peças, ponteiros
  <tema>.md     ← estruturas.md, efeitos.md, escrita.md, … (descobertas narradas)
  dados/*.json  ← os fatos (schema acima)
  fontes.md     ← rastreabilidade: app/amostra/data de cada bloco de descoberta
```

## 4. Estilo da prosa

- Português. Direto. O leitor é um dev (ou um agente) que vai implementar parser/writer.
- Mostrar a **cadeia de resolução** e o **caminho de acesso** (ex.: atributo pyaaf2, tag XML).
- Quando houver fórmula, escrevê-la executável (Python-ish) e dizer a unidade.
- Linkar entre temas com caminhos relativos. Linkar de volta ao app que implementa.

## 5. Como contribuir (apps alimentando o banco)

Quando um app descobre algo novo sobre um formato:
1. Achar a pasta do protocolo (ou criar tema novo).
2. Narrar no `.md` (o quê + como foi descoberto + nível de confiança).
3. Se for constante/estrutura que um app consumiria, adicionar/atualizar o `dados/*.json`.
4. Registrar a fonte em `fontes.md` e atualizar `_meta.atualizado`.
5. Atualizar `INDEX.md` se criou arquivo/tema novo.

Promoção de confiança: quando algo `inferido`/`hipotese` passa num teste de ida-e-volta, subir
para `confirmado` e anotar como foi validado.

## 6. Descoberta de PLATAFORMA registra os dois lados

Tudo que depende do sistema operacional — caminho, pasta do sistema, PATH, sistema de arquivos,
Unicode de nome, porta, encoding, diálogo, pasta do NLE — entra na
[matriz de plataforma](transversal/matriz-de-plataforma.md), **uma linha por variável, com a coluna
Windows e a coluna macOS**.

- O lado não medido entra como `pendente`, nunca em branco nem presumido igual.
- A confiança pode divergir por lado; no JSON, `confianca` vira objeto (`{"windows": …, "macos": …}`).
- A história da descoberta vai para a narrativa da sessão; a matriz guarda o fato e o link.
- ⭐ **Por que é regra e não sugestão:** cinco portes medidos (2026-08-15 a 2026-09-14) repetiram
  os mesmos erros com o conhecimento já no banco — em narrativa, onde ninguém o consulta ao
  escrever código. Banco que só se lê depois do defeito não se paga.
