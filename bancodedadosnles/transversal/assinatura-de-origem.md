# Assinatura de origem de AAF, xmeml, FCPXML e OTIO — quem escreveu este arquivo?

> **Medido em 2026-10-12, Windows 11** (De Lá Pra Cá, estudo pedido pelo autor para o Receber Avid → Avid):
> Media Composer **25.6** (Win) e **25.12** (Mac, 69 AAFs antigos do SSD) · Premiere Pro **23.2.0** (Win) ·
> DaVinci Resolve Studio **19.0.0b** (Win). Amostras em
> `MIDIAS DE TESTES/3 CONJUNTOS DOS APPS/_DeLaPraCa/03 CASOS/ATUALIZAR/O01 ASSINATURA DE ORIGEM/<nle>-<versão>-win/`.
> Dados consumíveis: [assinatura-de-origem.json](assinatura-de-origem.json).

Os formatos nativos (AVB, PRPROJ, DRT/DRP) já dizem de onde vêm. Os de **intercâmbio** chegam soltos numa pasta,
e o Receber precisa saber quem os escreveu — o caminho Avid → Avid (relinkar a timeline que já está no MC) só vale
para o que saiu do Avid, e a tradução muda conforme o autor do arquivo.

## A tabela (confirmado — um export de cada, lido com pyaaf2 / texto)

| formato | Avid MC | Premiere | Resolve |
|---|---|---|---|
| **AAF** `Header.IdentificationList[]` | `CompanyName` **`Avid Technology, Inc.`** · `ProductName` **`Avid Media Composer 25.6`** (25.12: `… 25.12.0.58863`) · `Platform` `AAFSDK (Win64)` / `AAFSDK (MacOS X)` · toolkit **2.0.9** (Win 25.6) / **2.0.10** (Mac 25.12) | **`Adobe`** · **`Premiere Pro`** · `ProductVersionString` **`23.2.0`** (o único que preenche) · `AAFSDK (Win64)` · toolkit **1.2.0 `VersionBeta`** | **`Blackmagic Design`** · **`DaVinci Resolve`** · `ProductVersion` 19.0.0 · `AAFSDK (Win32)` (sic, num Windows 64) · toolkit **1.1.6** |
| **xmeml** (FCP 7 XML) | não exporta | **`version="4"`**, tabulação, LF; `<sequence id="sequence-1" TL.SQ…= MZ.…= Monitor.…=>`, `<track TL.SQTrack…>`, `premiereTrackType=`, **`<parameter authoringApp="PremierePro">`** | **`version="5"`**, 4 espaços, **CRLF**; nenhum atributo próprio; o **nome da sequência ganha o sufixo `" (Resolve)"`** |
| **FCPXML** | não exporta | não exporta | 1.8 = arquivo; **1.10 = PASTA** com `Info.fcpxml` dentro (mesmo com a extensão `.fcpxml` que se pediu); 4 espaços; marca só no nome (`" (Resolve)"`) |
| **OTIO** | `pendente` (o 25.6 não mostrou export de OTIO) | **o 2023 não exporta** (autor, 2026-10-12); 2025+ `pendente` | metadados **`Resolve_OTIO`** na timeline (`{"Resolve OTIO Meta Version": "1.0"}`) e em cada clipe |
| **EDL** | — | — | **nenhuma marca** (só `TITLE:` e `FCM:`): EDL não tem origem |
| ↳ CORRIGE (2026-11-25, MC 25.12 × Premiere 26.0.2, Mac) | `TITLE:` com 3 espaços, sem linha em branco entre eventos, `*FROM CLIP NAME:  `, canais `A3`…`A10`, UTF-8 | reel `AX`, linha em branco, `* AUDIO LEVEL AT … (REEL AX A1)`, `EFFECTS NAME IS`, `AA/V`, MacRoman no Mac | reel `AX`, linha em branco, 2 espaços no fim do evento, ASCII | marca DECLARADA continua não havendo, mas o desenho é **pista** (nunca prova): [protocolos/edl](../protocolos/edl/README.md) §3 |

## A regra de classificação (do mais forte ao mais fraco)

1. **AAF:** a ÚLTIMA entrada do `IdentificationList` é quem gravou por último; a PRIMEIRA, quem criou. Casar
   `CompanyName` (estável) e não `ProductName` (o MC põe a versão dentro do nome). Export novo dos três = **1 entrada**.
2. **xmeml:** `authoringApp="PremierePro"` ou `TL.SQ`/`MZ.` → Premiere; `version="5"` sem nada disso → Resolve
   (ou o próprio FCP 7, que não é alvo). O BOM **não** decide: uma amostra antiga do Premiere tinha, a 23.2 não.
3. **OTIO:** chave `Resolve_OTIO` nos metadados → Resolve. Sem namespace conhecido → `desconhecida`.
4. ⚠️ **O sufixo `" (Resolve)"` é pista, não prova:** ele mora no NOME, e o nome viaja — a timeline que sai do Resolve,
   entra no Premiere e sai de novo continua "(Resolve)". Usar só para confirmar o que a estrutura já disse.
5. Sem marca (EDL, ou OTIO/FCPXML de quem não se identifica) → **`desconhecida`**, nunca um palpite: o Receber
   pergunta ou trata pelo caminho genérico.

## ⛔ Armadilhas

- ⛔⛔ **Um AAF que passou pelo De Lá Pra Cá continuava dizendo "Avid Media Composer".** O app copia o arquivo e
  edita com `pyaaf2` em `rw` (relink, achatar, remapear), e o pyaaf2 **não acrescenta `Identification`** ao salvar
  (medido: `saidas/*.aaf`, 1 entrada só, a do MC). O AAF spec manda quem modifica acrescentar a sua. **Decisão do
  autor (2026-10-12): o app acrescenta a dele, preservando a do Avid** — o Receber passa a distinguir "do Avid" de
  "do Avid, já tratado pelo DLPC". Idem no OTIO que o app escreve (namespace próprio nos metadados).
  **Feito no app (`motor/origem.py` → `marcar_aaf`, nos três `aaf2.open(…, 'rw')`): `CompanyName` `Ciclo Media`,
  `ProductName` `De Lá Pra Cá`, `ProductID` fixo, `Platform` `pyaaf2 (win32)`.** ✅ `confirmado`: o **MC 25.6 (Win)
  importa o AAF com a Identification extra** sem diálogo e com a sequência íntegra (12/12 segmentos iguais à original,
  lidos da bin depois do import — 2026-10-12, `O01_MARCADO.aaf`). Premiere e Resolve importando o AAF marcado: `pendente`.
- ⚠️ **`Date` da Identification é UTC** (export às 16h24 de Brasília gravou `19:24`) — não comparar com a hora local
  do arquivo.
- ⚠️ **FCPXML 1.10 do Resolve é uma PASTA**: `os.path.getsize` dá 0 e `open()` falha; o documento é `Info.fcpxml`
  dentro dela.
- ⚠️ **Premiere, `app.project.exportAAF` de sequência com rampa/time remap** abre o diálogo **"AAF Export Log"**
  ("Cannot export variable rate video clip …") — o AAF É gravado; ENTER não fecha, só o clique no OK (cadastrado no
  catálogo do piloto, `catalogos/premiere/aaf_export_log.png`).
- ⛔ **Premiere no Windows, `sequence.exportAsFinalCutProXML(caminho, 1)` com `/` devolve `false` e não grava nada**;
  com `\` funciona (o `exportAAF` aceitou `/`). Linha na [matriz de plataforma](matriz-de-plataforma.md) §G2.

## Pendente

- OTIO do Premiere 2025+/26 e do Avid (se exportarem); FCPXML do próprio Final Cut (Mac).
- Cadeia: o que fica no `IdentificationList` quando o MC importa um AAF do Resolve e o exporta de novo (hipótese: export
  é arquivo novo → 1 entrada, a do MC; a origem anterior se perde — se confirmado, a Carta Aberta é quem guarda a
  ancestralidade).
- Os mesmos exports no macOS (`Platform` muda; o resto deve ser igual — `hipotese`).
