# Addendum — o que a desofuscação revelou (e o que ela corrigiu)

2026-08-24, a pedido do autor: desembrulhar o que tinha ficado fechado nas análises do
[Chop Chop](chopchop-arquitetura.md), dos [quatro painéis](quatro-paineis-timeline.md) e do
[Selector](selector-conform.md).

**O que foi feito, e como:** os `main.js` do Chop Chop (610 KB) e do Selector (652 KB) estão
protegidos por `javascript-obfuscator` com `stringArrayEncoding`. O esquema foi **lido no corpo do
decodificador** — base64 com **alfabeto rotacionado** (minúsculas primeiro:
`abcdefghijklmnopqrstuvwxyzABCDEF…0123456789+/=`), seguido de `decodeURIComponent`, isto é, os
bytes são UTF-8 — e **reimplementado em Python**. ⭐ **Nenhuma linha do código deles foi
executada**, e o que se reconstruiu foi a **tabela de strings** (passos 7–8 da ordem de ataque),
não o fluxo de controle. Resultado: **2.259** strings do Chop Chop e **2.466** do Selector, em
claro.

⚠️ **O SDK de licenciamento (`aesp.umd.js`, 2 MB) NÃO foi tocado** — é o único item que a régua
marca como fora de escopo *sempre*, e não carrega fato de arquitetura.

---

## 1. ⭐⭐ O `runOrder` do Selector é medido por uma ferramenta que eles embarcam

A análise anterior inferiu que `runOrder` era custo medido e que os filtros passavam por um portão
de *medir + testar*. As strings confirmam, com o nome do instrumento:

```
FiltersProfiler.init() started / finished
Finished testing All Filters
Finished testing Clip Filters
Finished testing Item Filters
```

⭐ **Isso promove a leitura de `inferido` para bem sustentado**: existe um *profiler* de filtros no
próprio produto, e é ele que produz o número. E reforça a leitura do §3 da
[selector-conform.md](selector-conform.md): o *"Has effects"* parado em `clipOnHold` **sem
`runOrder`** é um filtro que **não passou pelo profiler** — não um esquecimento de catálogo.

## 2. ⭐ A "mesma oficina" deixa de ser inferência

| evidência | onde |
|---|---|
| `Copyright 2025 Empresa Terceira` | strings do **Selector** |
| `dev@exemplo.org` + `This version expires on:` | strings do **Chop Chop** |
| `Chop Chop Media Systems` / `ChopChopMediaSystems` | strings do **Chop Chop** |

A sessão anterior inferiu "marcas diferentes, oficina a mesma" pelos pacotes npm in-house. Agora há
**evidência direta**: a EMPRESA-TERCEIRA (*Empresa Terceira*, austríaca) assina o Selector, e o
build do Chop Chop pede feedback para o e-mail da EMPRESA-TERCEIRA. **Chop Chop Media Systems é a marca; a
EMPRESA-TERCEIRA é quem constrói.**

⚠️ E o build do Chop Chop analisado é de **avaliação** (`This version expires on:`) — o que muda o
peso de qualquer conclusão sobre o que "o produto faz": pode haver caminho que só a versão paga
exercita.

## 3. ⛔ CORREÇÃO — Markers Pro não tem payload cifrado

**O que eu escrevi:** *"JSXBIN cuja tabela de símbolos entrega só um stub decodificador, com a
lógica num blob cifrado por dentro. Duas camadas de proteção deliberada."*

**O que é:** **JSXBIN dentro de JSXBIN.** O `.jsx` externo é ES 2.0 e contém uma string única de
68.546 caracteres que começa com `@JSXBIN@ES@2.1@` — um segundo JSXBIN, entregue a `eval()`. Os
símbolos que eu li como "stub decodificador" (`eval`, `charCodeAt`, `replace`, polyfill de JSON)
são o **carregador** do nível interno.

⭐ **A lição, e ela é de método:** *"parece cifrado" costuma ser "está embrulhado duas vezes"* — e a
diferença importa, porque uma é trivial de abrir e a outra não. Eu concluí "cifra" a partir da
**assinatura dos símbolos**, sem olhar o que a maior string continha. Bastava decodificar a maior
corrida e ler os 15 primeiros caracteres.

⚠️ **O nível interno continua sem leitura:** o ES 2.1 usa codificação diferente da ES 2.0 e o
decodificador de pares não se aplica. Parei aí — é arqueologia de formato com retorno baixo, já
que o vocabulário de marcador completo já veio do Automation Blocks.

**O que o painel (`panel/js/panel.js`, 2,1 MB) entregou**, esse sim legível: `getMarkers(0|1|2)`,
`pasteMarkers(68)`, `markerMove`, um mapa de atalhos (`copy`, `paste`, `toLeft`) e
`com.aescripts.markerspro.*` — **6ª aparição do canal aescripts** neste banco. ⭐ E o painel
embarca **`ajv`** (validador de JSON Schema): marcadores são validados contra schema, o que sugere
**importar/exportar conjuntos de marcadores** — relevante para a ideia de relatório de conform.

## 4. ⭐ Chop Chop: o que o painel revelou

- **O parser de nome é regex com GRUPOS NOMEADOS**, montado a partir de gabaritos:
  `(?<episodeStr>…)`, `(?<sceneStr>…)`, `(?<shotStr>…)`, com marcadores `${valueId}` e `${notSep}`
  interpolados a partir dos identificadores que o usuário digita. ⭐ *O separador não é literal no
  regex — é parâmetro*, e é isso que permite os três conjuntos de identificadores do manual sem
  três parsers.
- ⭐⭐ **Como distinguir preset de ingest de preset de encoding:** eles leem
  **`<IngestPreset>true</IngestPreset>`** dentro do `.epr` (`ValidationManager.isIngestPreset()`,
  `GuidedOptionsManager.selectEncodingPresetFile()`). Isso resolve, com uma tag, a dor que o banco
  já registrava como *"ler o XML do `.epr`, nunca o nome"* — agora com o campo exato.
- **Localização mais ampla do que se via:** além de inglês, há **pt-BR** e **chinês simplificado
  e tradicional** (`文件必须是编码预设…`, `檔案必須是編碼預設…`).
- 🔒 ⚠️ **As chaves do LicenseSpring estão TAMBÉM no bundle do painel**, em claro:
  `8c914b3c-a44a-466a-9e7b-ce05c598ef58` (akey) e `BRQpd33YXNg05ItqOHTFfRO…` (skey) — **as mesmas**
  do `ccsbrconfig.json` da edição Resolve. *A mesma credencial, em dois produtos, em dois lugares,
  sem cifra.* Some-se ao par AES fixo já registrado.

## 5. ⚠️ Caminhos de máquina de desenvolvimento vazados nos dois

```
I:\PROGRAMAS\PR\_CUSTOM\_CEP\com.selectorForPR.tmmw\common\FiltersDB.json
C:\Users\usuario\Documents\Adobe\Adobe Media Encoder\13.0\Presets
C:\Users\usuario\AppData\Roaming\Chop Chop Media Systems\Chop Chop Sync and Bin\Temp\
```

⭐ **Vale como lição para nós, não como troféu:** caminho absoluto de desenvolvimento entra no
bundle sem ninguém notar — expõe nome de usuário, layout de disco e estrutura interna do projeto.
**Conferir isso antes de publicar** é barato e nunca está na lista.

## 6. ⛔ O que a desofuscação NÃO deu — e isso também é resultado

⭐⭐ **O `main.js` do Selector não tem uma linha sobre o Premiere.** Nas 2.466 strings: **zero**
ocorrências de `effect`, `component`, `http`, `marker`, `xml`. É construção de DOM, gerência de
filtros, notificação e UI de licença. **Toda a lógica que toca o NLE vive no JSXBIN**, cuja tabela
de símbolos já tinha sido lida.

⚠️ **Ou seja: a decisão anterior de parar antes de desofuscar estava CERTA quanto ao rendimento.**
O que a desofuscação rendeu de fato foi (a) a confirmação do `FiltersProfiler`, (b) a identidade
do fornecedor, (c) as chaves e caminhos vazados, e (d) os detalhes do Chop Chop do §4 — nada disso
sobre a API do Premiere. *Desembrulhar mais fundo não é o mesmo que chegar mais perto do que
interessa.*

## ⚠️ A régua desta rodada

- Reconstruída a **tabela de strings** dos dois bundles, reimplementando o decodificador em
  Python. **Nada do código deles foi executado.**
- **Nenhum fluxo de controle foi reconstruído**; nenhuma lógica transcrita. O regex do §4 está
  **descrito**, não copiado.
- **`aesp.umd.js` (SDK de licenciamento) não foi tocado.** Nenhum mecanismo de licença foi
  examinado, contornado ou testado — e as chaves do §4 estão registradas como **achado de higiene**,
  não para uso.
- O nível interno do Markers Pro (ES 2.1) **não foi decodificado**.
- Temporários apagados.
