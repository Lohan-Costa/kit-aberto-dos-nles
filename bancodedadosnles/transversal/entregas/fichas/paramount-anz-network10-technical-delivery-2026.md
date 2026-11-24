# Paramount ANZ / Network 10 (Austrália) — Technical Delivery Specification 2026 (Domestic 1.0, International 1.2)

Fontes: `MANUAIS ENTREGA/PUBLICOS/PARAMOUNT ANZ (NETWORK 10)/10.01.SPEC_Technical-Delivery-*-2026-*.pdf`
(19 e 16 pág., públicos; o International 1.2 é de 2026-08). Confiança: `documento` — GUIA. Destino: **TV aberta
australiana** (1080i/25 — 50i).

- Vídeo: **XDCAM HD 50** (MPEG-2 HD422 Long GOP 50 Mb/s) preferido; DNxHD 120 aceito; SD em IMX 50. Imagem 4:3
  centralizada com barras laterais, sem distorção.
- **TC:** um TC contínuo e crescente no arquivo (Timecode Track do material package, SMPTE ST 377-1);
  **primeira imagem do programa em 01:00:00:00**. Cabeça: 00:59:58:00 2 s de preto mudo → 01:00:00:00 programa.
  Fim de segmento: ≥ 5 s de preto mudo; fim de programa: ≥ 30 s de preto. Textless no fim do programa.
  Na exibição eles mesmos põem fade de 12 quadros de/para preto.
- Loudness: **−24 LKFS** (Free TV OP-59, BS.1770), também nas promos.
- **Nome de arquivo:** programa.série.episódio, sem espaços (espaço vira ponto) — ex. `new.show.s01.e03`; versão
  nova ganha `V#` no fim, com a lista de mudanças por TC enviada por email.

## Para os apps
- Hora 1 sem barras/claquete, só 2 s de preto: mais uma linha na tabela de TC de início (`../matriz.md` §9.1).
