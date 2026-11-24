# Channel 4 / DPP (Reino Unido) — entrega de programas como arquivos AS-11, v5.2 (UK DPP File v5.0 – 2017; C4 2022)

Fontes: `MANUAIS ENTREGA/PUBLICOS/CHANNEL 4/` — "Programme Delivery Specification File (DPP) v5.2" (32 pág.),
"Programme durations" (2021) e "Full Subtitling Guidelines" (jun/2026); página: channel4.com/4producers/working-us/delivery
(lista também um **kit de créditos finais para Avid** — zip, não baixado). Confiança: `documento`. Destino: **master de
TV britânico** — é o documento DPP completo que BBC, ITV, Sky etc. compartilham (a ficha `dpp-as11-uk` é a
apresentação de 2014).

- **Formatos:** HD 1080i/25 top field first (ou 1080p/25 PsF); UHD especificado (BT.2100), mas o C4 ainda não
  aceita UHD. Arquivo AS-11 UK DPP (MXF OP1a, AVC-Intra 100) com metadados DPP.
- **Layout (TC):** 09:59:30:00 barras 100% 20 s + tom · **09:59:50:00 ident clock ou slate ≥ 7 s** · 09:59:57:06 1
  quadro de tom + 2 quadros ≥ 50% branco (opcional) · black ≥ 2 s 18 q · **programa em 10:00:00:00**. Multipartes:
  freeze 5 s no fim de cada parte, 1 s black, slate da parte seguinte no "minuto cheio − 10 s", 3 s black; fim do
  programa com freeze 5 s e o par tom/branco 10 s depois. Partes em arquivos separados: cada arquivo seguinte na
  PRÓXIMA hora cheia, com line-up e ident deslocados.
- **Um programa por arquivo** (soft ou hard parting conforme a emissora).
- **Loudness (EBU R 128 / Tech 3343):** −23,0 LUFS ±0,5 LU (ao vivo ±1,0); true peak recomendado ≤ −3 dBTP, **falha
  acima de −1 dBTP**; LRA ≤ 18 LU (orientação).
