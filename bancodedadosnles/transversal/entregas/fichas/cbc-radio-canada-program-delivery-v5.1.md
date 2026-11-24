# CBC/Radio-Canada — Technical Specifications for Program Delivery v5.1 (21/09/2016)

Fonte: `MANUAIS ENTREGA/PUBLICOS/CBC RADIO-CANADA/CBC Technical specs for program delivery.pdf` (31 pág., público).
Confiança: `documento` (2016: pode estar desatualizado). Destino: **master de programa para TV** (inglês e francês).

- **Pacote:** um A/V convertido a 29,97i + um no FORMATO ORIGINAL, closed caption (.SCC/.CAP), metadados XML,
  galeria e stills JPEG; nome `PGMID` (ex. `TheShowXYZ_S02_E04.mxf`); teste de entrega antes.
- **HD:** 1920×1080 4:2:2 8/10 bits, BT.709, **29,97i upper field first** (aceitos 23,976p, 25i, 25p, 29,97p; taxa
  constante do leader ao fim). MXF OP1a (SMPTE ST 378, índices completos) com **XDCAM HD422 50** (preferido) ou
  DNxHD 115–220; ou MOV com **ProRes 422/HQ**; PCM 24/48.
- **Estrutura (TC):** 09:59:30:00 tons 5 s · 09:59:35:00 **ID vocal + ruído rosa** 20 s (cada canal se anuncia) e
  slate · 09:59:55:00 silêncio/black 3 s · **09:59:58:00 1 quadro de sincronismo** (1 kHz + barras) · black 2 s ·
  **programa em 10:00:00:00**; segmentos separados por 1 s de black; trailer. Web: sem leader, 1 s de black antes e
  depois.
- **TC** contínuo do início ao fim; **29,97 em drop frame**.
- **Áudio:** CBC 8 canais `L R C LFE Ls Rs DV-L DV-R`; Radio-Canada 10 (`… Lo Ro`); sem DV, mix estéreo no lugar;
  **−24 LKFS ±2 LU** (programa e diálogo), **−2 dBTP**; tom em fase em todos os canais usados; canal sem uso, mudo.
- Barras SMPTE RP219 (HD); área de ação/título segura; regras de conversão de SD em HD.
