# Estudo: EDL para o som — onde a informação se perde entre a montagem e a casa de som

> Pergunta do autor (2026-11-25): "investigar possíveis problemas que ocorrem de EDLs exportados para equipe de som e que
> chegam errado e ninguém sabe dizer exatamente". Estudo em duas metades: (1) o que SAI do NLE — feita; (2) a
> transferência completa até o PRO TOOLS — a fazer (`HANDOFF.md`).

## O resultado da 1ª metade (MC 25.12 e Premiere 26.0.2, Mac)

Relatório com prints: `relatorio-1a-metade/` (publicado: https://claude.ai/artifact/D6MQHsJ5gyi5Kbrmd7CaB4).
O fato de formato está no banco, em `protocolos/edl/README.md` §5b (MC) e §5c (Premiere); aqui fica o ESTUDO inteiro.

- ⛔ O canal da EDL é a TRILHA da timeline: um WAV de 6 usado nos canais 3/5 sai `A`/`A2` (os dois NLEs).
- ⛔ Premiere: multicâmera e nest saem com o TC DELES, reel `AX` e o nome da multicâmera/nest — nada leva à fonte.
- ⛔ Premiere: o merged por pontos de entrada põe o som 1 quadro antes; a EDL é fiel a ele.
- ⛔ Premiere: 4 canais de áudio por EDL — 6 canais viram 4, calado.
- ⛔ MC: o List Tool lembra as trilhas marcadas da sequência anterior e exporta só A1/A2, calado.
- ⭐ SÓ ÁUDIO (sem nenhum segmento de vídeo) = a MESMA EDL de som, nos dois NLEs (o AAF do Premiere com merged não
  se repete aqui). ⭐ "Usar timecode de áudio do clipe" no merged NÃO muda a EDL (só o TC do merged).
- ⭐ O reel do som é o sound roll do iXML: todos os takes do dia com o mesmo reel; só o TC separa (alerta).
- ⭐ MC: o group NA TIMELINE é uma cópia do `Selector` do grupo — sem ela o MC não mostra o (G) nem a troca de ângulo.

## O que está aqui

| pasta | o quê |
|---|---|
| `proposta/` | o plano (`PLANO.md`) e a página da proposta (11 casos S1–S11, decisões do autor) |
| `relatorio-1a-metade/` | a página do relatório, o tema e os prints |
| `edls/mc/`, `edls/premiere/` | as EDLs conferidas e os `plano*.json` (a VERDADE de cada evento); `… TRILHAS HERDADAS` = as provas do List Tool |
| `edls/rodada-1/` | a rodada anterior (a mesma sequência B30 nos dois NLEs, a tabela campo a campo do §1–4) |

## Onde mora o resto

- Mídia: receita `laboratorio-de-midia/receitas/base/B31_EDL_SOM.json` (+ `lab/edl_som.py rotular`, o iXML);
  B30_EDL para a rodada 1.
- Projetos: MC `LAB COR MC` (bins `B31 EDL SOM_*`); Premiere `MIDIAS DE TESTES/9 SAIDAS DOS APPS/_CICLO ASSIST/
  2026-11-25 EDL SOM PREMIERE/B31 EDL SOM PREMIERE v02.prproj`. Saídas e fotos: `9 SAIDAS…/2026-11-25 EDL SOM MC|PREMIERE`.
- Código (Ciclo Assist): `modulos/conformar/motor/edl/leitura.py` (o leitor) e `conferir.py` (certo · alerta · errado
  calado); testes `test_edl_leitura` 25/25, `test_edl_conferir` 41/41 (fixtures em `04 SINTETICOS/EDL SOM MC|PREMIERE`).
  Spikes: `spikes/edl_som_mc/` (casos por pyavb, `--so-audio`, export pelo List Tool) e `spikes/edl_som_premiere/`
  (ponte: preparar/importar/mover/montar; `exportar_edl.py` pilotado; `plano.py`).
- Conferir uma EDL: `python -m motor.edl.conferir <plano.json> <edl>…` (da pasta `modulos/conformar`).
