# FLE — a EDL da FilmLight (Baselight, Daylight)

> **Versão da spec:** "FilmLight EDL Specification 1.0" (`doc/FL-GN-TN-0476-FLESpec.txt` dentro do Baselight
> 7.0.3.26500, 2026-11-07). **Confiança: `hipotese`** — lido da spec, nenhum FLE nosso conformado ainda. Cópia da spec:
> `PROGRAMAS COM CLAUDE/8 REFERENCIA/BASELIGHT/instalador-7.0.3-extraido/…/Contents/doc/FL-GN-TN-0476-FLESpec.txt`.

**Por que interessa:** diferente da CMX 3600, cada evento do FLE diz **onde está o arquivo** — o conform não precisa
procurar por fita/TC. O Conformar já sabe o original de cada plano, então um FLE gerado por ele é a rota determinística
para o Baselight (plano: `2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-21-baselight.md`, rota B). Ver
[../../plugins/baselight/](../../plugins/baselight/README.md).

## Forma

Texto, um evento por linha, extensão `.fle`. Cabeçalho e comentários com `#`.

```
# FilmLight EDL                 ← 1ª linha, obrigatória
# fps 24                        ← 24 (padrão), 25, 30, "30DF" (29,97)
# gear 16                       ← só para keycode (perfurações por contagem / por quadro)
# track 1                       ← trilhas: cada uma empilhada sobre a anterior, todas começando em 0
01:02:03:00 01:02:04:10 caminho/do/arquivo
# end                           ← última linha, obrigatória (detecta arquivo truncado)
```

- Três formas de evento, misturáveis: **keycode** (`FN323706 8430 +09 8432 +04 nome`), **timecode**
  (`01:02:03:00 01:02:04:10 nome`) e **quadro** (`0020 0116 nome`). **Saída INCLUSIVA** (`0001 0002` = 2 quadros) —
  ⚠️ diferente da CMX 3600, cuja saída é exclusiva.
- O nome é o **radical do caminho** onde a mídia está. Caracteres proibidos no nome: espaço e `,!$%&*(){}[]<>|~'"\`;:?`
  ⚠️ caminho com espaço (comum nas nossas produções) não cabe — conferir como o Baselight trata, ou usar caminho sem espaço.
- **Buraco**: o evento sem nome. Cor sólida no buraco: `{colour (r, g, b)}`.
- **Opticals** entre chaves no fim da linha, combináveis com vírgula: `{fps 12}` (velocidade; 0 = congelado, negativo =
  reverso; a duração na timeline sai de fim − início + 1), reverso também por in > out, `{dissolve}` / `{dissolve 5}` (só
  no rolo B, o A imediatamente antes), `{flip}`, `{flop}`, `{asc_sop (…)(…)(…), asc_sat 0.85}`.
- Comentário de evento depois de `#` no fim da linha (livre; metadados para outros sistemas).

## Lacunas para o nosso uso (a medir)

- [ ] `# fps` só lista 24/25/30/30DF: e 23,976, 29,97 NDF, 50, 59,94? (O conform do Baselight tem 50@25 e 60@30.)
- [ ] Caminho absoluto × relativo à pasta de busca; espaços no caminho; o `--FilenamePrefix` do `bl-conform` (7.x).
- [ ] Reposição/escala: não existe no FLE — fica para o AAF (Layer 99) ou para a FLAPI.
- [ ] TC de gravação: o FLE não tem; a timeline começa em 0 e o TC da scene se acerta à parte.
