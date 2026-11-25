# Tamanho de arquivo de NLE — o que é projeto inteiro e o que é uma timeline (e quanta memória custa abrir)

`confianca`: classificação = `confirmado` (autor, 2026-10-28); fator de memória = `confirmado` num caso (medido
2026-10-28, Mac, Python 3.12, De Lá Pra Cá) — `hipotese` para projetos mais complexos.

## A classificação (autor, 2026-10-28)

| carrega | formatos | o que guarda |
|---|---|---|
| **PROJETO INTEIRO** | `.prproj` (Premiere), `.drp` (Resolve) | todas as timelines, as pastas, os nests, o media pool/browser |
| **VÁRIAS TIMELINES, sem estrutura de projeto** | `.avb` (bin do Avid) | as sequências e os masters de uma bin; sem árvore de pastas |
| **UMA TIMELINE** | AAF, XML (FCP7), FCPXML, DRT, OTIO | a montagem de uma sequência |

⚠️ Nuance: o AAF PODE levar mais de uma sequência (o MC exporta várias selecionadas num AAF só) — na prática, nada
perto do tamanho de um projeto inteiro. Conclusão do autor: o teto de tamanho é assunto de `.prproj`/`.drp` (e, de
longe, `.avb`); os de uma timeline não chegam lá.

## Quanto custa abrir (medido)

O `.prproj` é XML compactado (gzip). Para lê-lo o app descompacta tudo e indexa os objetos:

| projeto real | no disco | descompactado | pico de memória ao abrir (`Projeto()` do De Lá Pra Cá) |
|---|---|---|---|
| PRODUCAO_B edição (Premiere 24) | 48 MB | 812 MB | **2,95 GB** (1,46 mi de objetos, 3,3 s) |
| PRODUCAO_B finalização | 12 MB | 230 MB | — |
| CANAL-K Copa 2026 | 3 MB | 69 MB | — |
| PRODUCAO-C | 3 MB | 51 MB | — |

- Compactação típica: ~17×. Memória para abrir: ~**3,6× o descompactado** (texto + índice).
- **O limite é de TRAVAMENTO, não de lentidão:** enquanto cabe na RAM, maior = proporcionalmente mais lento; passou da
  RAM, o sistema troca para o disco, tudo (o NLE junto) fica parado e o processo pode cair. Um teto FIXO não serve: ele
  depende da RAM da máquina (num Mac de 16 GB, ~4 GB descompactados já pediriam ~15 GB).
- **Bomba de compressão:** um arquivo pequeno que descompacta em dezenas de GB (malicioso ou corrompido). Medir o
  tamanho descompactado SEM guardar (contar no fluxo) antes de abrir.
- ⏳ O PRODUCAO_B é grande mas SIMPLES; projeto com muitos efeitos/nests/multicam pode ter outro fator — calibrar com
  casos reais. `.drp` e `.avb`: fator `pendente`.

## A regra proposta (De Lá Pra Cá, aprovação do diálogo pendente)

Medir antes de abrir → estimar a memória (fator × descompactado) contra a RAM: 🟢 até ~50 % abre direto; 🟡 50–80 %
um diálogo PRÓPRIO do app (nunca `confirm`, ficha B077) explicando que vai demorar e pode deixar a máquina lenta, com
continuar/cancelar; 🔴 acima de ~80 % ou proporção de bomba: recusa explicando que travaria.
