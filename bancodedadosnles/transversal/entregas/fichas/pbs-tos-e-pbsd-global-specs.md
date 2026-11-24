# PBS (EUA) — TOS Submission (2020) e PBS Distribution Global Technical Specifications (2025-10-09)

Fontes: `MANUAIS ENTREGA/PUBLICOS/PBS/PBS-TOS-pt1-submission-2020-07-01.pdf` (24 pág., exibição na rede PBS) e
`PBSd-GLOBAL-TECHNICAL-SPECIFICATIONS-2025-10-09.pdf` (PBS Distribution, venda internacional). Públicos.
Confiança: `documento` — GUIA, não lei. Destino: **master de TV norte-americana** (29,97 DF).

## TC e cabeça
- **TOS (exibição):** arquivo começa em **00:59:45;00**; ≥ 15 s de preto ou claquete, 2 s de preto limpo,
  **programa em 01:00:00;00**; 15 s de preto na cauda; TC contínuo do começo ao fim; **drop frame** (29,97).
  O primeiro segmento sempre em 1:00:00;00; preto entre segmentos é programa salvo se marcado como "não vai ao ar".
- **PBSd (distribuição):** programa em **01:00:00;00 OU 10:00:00;00**; 29,97 = DF; 23,98/24/25 = NDF.
  Claquete de **13 s** em 00:59:45;00 (título, episódio, duração do 1º ao último quadro de imagem, sem claquete nem
  textless; configuração de áudio, taxa, data, produtora) + 2 s de preto + programa; 15 s de preto no fim.
  Sem barras e tom antes da claquete. ⚠️ O próprio texto diz "quinze (13) segundos": a palavra e o número divergem.
- Sem VITC/BITC queimado, sem bugs de classificação, sem blacks comerciais (conteúdo contínuo).

## Textless e outros
- PBSd: textless do programa inteiro (sem lower thirds identificadores e qualquer texto na tela); aberturas e
  créditos COM texto vão **depois do programa textless, separados por 2 s de preto**.
- Formatos PBSd: ProRes 422 HQ (MOV) ou DNxHD 175 MXF OP1a; UHD/HDR10 ProRes 422 HQ/4444 ou DNxHR HQ; IMF App 2E.
- Loudness (os dois): **−24 LKFS ±2 LU** (ATSC A/85, BS.1770-3), true peak −2 dBTP; mono não é aceito.
- Legenda fechada em `.scc` com o mesmo TC e taxa do master. QC automático (Baton) na entrada.

## Para os apps
- Mais uma prova de que o TC de início é do DESTINO (aqui hora 1 OU hora 10, a critério): opção, nunca regra.
- "Duração = do primeiro ao último quadro de IMAGEM" é exatamente o que a conferência pela imagem já mede.
