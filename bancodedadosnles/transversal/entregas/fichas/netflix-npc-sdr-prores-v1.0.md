# Netflix — SDR ProRes 422 HQ Spec for NPC (não final), v1.0 (06/04/2026)

Fonte: `MANUAIS ENTREGA/TECH SPECS/SDR Non-final ProRes for NPC Spec v1.0.pdf` (2 pág.). Confiança:
`documento`. Destino: **arquivo para sessão de exibição/pesquisa** (NPC), ainda não final.

- Um arquivo só (muxed), áudio conformado à imagem.
- **Vídeo:** QuickTime MOV, ProRes 422 HQ, 1920×1080, PAR 1:1, imagem ativa escalada dentro do
  container (ex. 1920×800 para 2.4), BT.709/D65/BT.1886 (gama 2.4), progressivo, taxa NATIVA (sem
  VFR), 10 bits, legal range 4:2:2.
- **Áudio:** PCM linear 48 kHz/24 bits; loudness −27 LKFS ±2 LU (dialog-gated), pico ≤ −2 dBTP
  (ITU-R BS.1770-1); OU 5.1+2.0 (8 canais: L R C LFE Ls Rs, 2.0 L R) OU só 2.0.
- **Tempo:** 1 s black/silêncio · pré-roll NPC (1 min) · 1 s · ident Netflix · 1 s · programa (sem
  créditos nem ident final) · 1 s · fim. Dois episódios = um long play, pré-roll só no 1º, cartela de
  transição de 5 s no lugar dos créditos do 1º.
- **Arquivo limpo:** sem TC queimado, sem marca d'água; texto só se essencial; narrativa forçada
  queimada se essencial.
- **Nome:** `[TITULO]_[TIPO DE CORTE]_[VERSAO]_[AAAAMMDD]`.
