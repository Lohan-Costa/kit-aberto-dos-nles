# SVT (Suécia) — entrega de programas como arquivo v5.1 (mar/2021) e entrega para MAM/arquivo v2.7

Fontes: `MANUAIS ENTREGA/PUBLICOS/SVT/` — "Technical Specification for the Delivery of Television Programmes as FILES
to SVT v5.1" (35 pág.) e "Technical Specification 4 – File Delivery to MAM & Archive v2.7" (21 pág.), públicos em
b2b.svt.se. Confiança: `documento`. Destino: **master de TV europeia (25 fps)** e **arquivo**. Usa os mesmos títulos
de seção do DPP (Reino Unido), com requisitos próprios.

- **Vídeo:** 1080i/25 ou 1080p/25 (PsF); 50p→25p tirando um quadro sim outro não; conversão de taxa com compensação de
  movimento (conversão de NLE proibida para programa inteiro); Super-16 não conta como HD; barras opcionais, só 100%
  (SMPTE "legado" não). Cinema 2.39/1.85 centrado entre barras pretas; caption safe para 16:9.
- **Legenda:** língua estrangeira SEM legenda queimada; legendas em arquivo DPP-EBU-TT.
- **TC:** contagem de 25, contínuo. Metadados num Excel (modelo da SVT); nomes de arquivo e de canais WAV
  (Apêndice B) definidos; ident clock/slate; alocação de canais AS-11 DPP.
- **Loudness:** **−23 LUFS ±1 LU**, true peak máximo; arquivo: −23 LUFS, **LRA 18 LU**, **−1 dBTP**, LRA de diálogo 6 LU.
- **Arquivo (MAM):** MXF OP1a ou **IMF**, conforme a classe.
