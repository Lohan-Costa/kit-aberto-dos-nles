# ffmpeg dentro do navegador (ffmpeg.wasm) — o que trava e o que funciona

> **Fonte:** `BENDITO-FIELD` (Field Cut Detector, beta v1.0 publicada no GitHub Pages em
> 2026-06-20), embrião do módulo "bendito field" do Promo Entrega. Registrado pelo zelador do SSD
> em 2026-10-06, ao arquivar o projeto, a partir do código e das memórias do Claude do projeto.
> **Versões:** `@ffmpeg/ffmpeg` 0.12.10, core ESM auto-hospedado (`vendor/core-esm/` ST e
> `vendor/core-mt-esm/` MT); Chrome desktop (versão não registrada, junho/2026); Firefox como
> controle. **Amostra:** MXF XDCAM HD422 1080i59.94, ~105 MB, 16 trilhas de áudio, com
> split-fields plantados nos frames 43 e 123.
> **Por que está aqui:** é o único registro da família sobre processar mídia de produção 100% no
> navegador. A virada que veio depois (ler os cortes da TIMELINE, dentro do NLE) está em
> [rabo-de-video-campo-escondido.md](rabo-de-video-campo-escondido.md); este arquivo é o lado
> "motor no navegador", útil para qualquer app estático (GitHub Pages) que precise decodificar.

## ⭐⭐ 1. A "parede do Chrome" era o encoder `mjpeg`, não o MXF nem a memória — `confirmado`

Sintoma: no Chrome o decode parava em `Stream mapping → mjpeg` e nada mais acontecia, de forma
intermitente. Foi atribuído primeiro a MXF/MPEG-2, depois a memória, depois ao multithread — **as
três hipóteses estavam erradas**. Isolado com uma página-sonda (`test-decode.html`): **o encoder
`mjpeg` do core single-thread trava no Chrome** ao codificar a sequência de imagens.

Conserto (validado no Chrome; os suspeitos 43/123/289 saíram com 98/95/74%):
- **análise:** saída `-f rawvideo -pix_fmt gray` num único arquivo, sem encoder nenhum; a métrica
  é calculada direto dos bytes (acabou com 354 JPEGs + `createImageBitmap`);
- **imagens para a interface:** `-c:v png` no lugar de `mjpeg`;
- **um motor novo por passada** (`terminate()` entre a análise e a extração) em vez de reusar.

⭐ Lição de método: o diagnóstico só saiu quando uma sonda mínima separou decode de encode. Três
explicações plausíveis seguidas, nenhuma testada isoladamente, custaram a fase inteira.

## ⚠️⚠️ 2. Multithread (COOP/COEP + SharedArrayBuffer) TRAVA o carregamento no Chrome — `confirmado` (Chrome) · Firefox ok

Ligar `Cross-Origin-Opener-Policy`/`Cross-Origin-Embedder-Policy` (no servidor local ou pelo
`coi-serviceworker` no GitHub Pages, que não deixa configurar cabeçalho) para ter
`SharedArrayBuffer` e o core MT: **o Chrome fica preso carregando o core** ("recriando motor");
no Firefox carrega na hora. Re-testado depois do conserto do `mjpeg` (2026-06-20): continua
travando. Com o `coi-serviceworker` houve ainda vídeo preto na primeira carga e erros de módulo
transitórios.

→ **Decisão que ficou:** Chrome-first, **single-thread, sem service worker, sem COOP/COEP** (a
página remove qualquer service worker antigo ao abrir). O piso de velocidade passa a ser o decode
ST: **~3 s por passada** no MXF de 105 MB. ⚠️ A causa do travamento MT não foi isolada
(`hipotese`: memória fixa do `SharedArrayBuffer` no build MT).

## 3. Armadilhas menores, todas medidas no mesmo app

| o quê | efeito | o que fazer | confiança |
|---|---|---|---|
| MXF com 16 trilhas de áudio | o wasm decodifica e guarda áudio que ninguém usa: memória e tempo | `-map 0:v:0 -an` em toda passada de vídeo | `confirmado` |
| `-movflags +faststart` | faz um segundo passe que **aborta no wasm** | não usar; no navegador ele não serve para nada | `confirmado` |
| separar os campos (Upper/Lower) em JS, por linhas pares/ímpares | o campo de baixo saía "contaminado" no Chrome | deixar o ffmpeg separar: filtro `separatefields` | `confirmado` |
| player do MXF | o navegador não toca MXF nem MPEG-2; o proxy H.264 via wasm travava o Chrome | o player foi removido (o produto é só detecção). Se precisar: proxy sem desentrelaçar, para preservar o defeito visível | `confirmado` (decisão do autor) |
| parar cedo | a 2ª passada lia o arquivo inteiro | `-frames:v N` para depois do último suspeito; `-ss` por janela é o próximo passo (risco de erro de um frame, não feito) | `confirmado` |
| GitHub Pages + arquivo de teste | MXF > 100 MB não entra no repositório | o teste online usa o MXF do próprio usuário; o de teste fica no `.gitignore` | `confirmado` |

## 4. O detector que funcionou no navegador (para quem retomar a varredura cega)

Diferença `|Upper − Lower|` por frame + **pico isolado** acima da vizinhança, mais uma
discriminação temporal: medir quanto cada campo muda no tempo (`tU`, `tL`) e exigir
`fieldDiff / min(tU, tL) ≥ 1.2`. Split-field real tem um campo "congelado" (razão alta); combing
de movimento muda os dois campos (razão baixa). Ainda assim, varrendo o arquivo inteiro sem saber
onde estão os cortes, o resultado afogava em falso positivo (48 marcações em 1456 frames) —
por isso a virada para a lista de edição.
