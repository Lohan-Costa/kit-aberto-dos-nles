# Netflix Studio Partner Help Center — mapa do site (varredura completa, 2026-10-04)

Site https://studiopartner.netflix.net/studio/ lido inteiro pela API pública (em inglês, sem login): **850 páginas**
(786 na árvore de navegação + 64 achadas só por botão). Confiança: `documento` — é GUIA, não lei.

- Índice com os títulos originais e o link de cada página: `MANUAIS ENTREGA/PUBLICOS/NETFLIX (site)/MAPA.md`.
- Texto de cada página: `MANUAIS ENTREGA/PUBLICOS/NETFLIX (site)/paginas/<slug>.md` (o slug é o fim do endereço).
- Análise do que interessa aos apps: `fichas/netflix-studio-partner-site.md`.
- Este mapa traduz as áreas; os nomes entre crases são os slugs (para abrir a página ou o arquivo de texto).

## As cinco grandes áreas

| Área (título no site) | O que tem | Interessa aos apps? |
|---|---|---|
| Produção e pós "branded" (originais Netflix) | políticas, IA generativa, entrega, imagem, som, VFX, QC, sustentabilidade | ⭐ sim — o miolo |
| Processamento e entrega "non branded" (licenciados) | especificações de entrega, modelos, utilitários, programa de parceiros de fulfillment (NPFP) | pouco |
| Localização de conteúdo | guias de legenda por idioma, dublagem, roteiros, controle de qualidade linguístico | não (só o TC de legenda) |
| Ferramentas e plataformas | Asset QC, Backlot, Content Hub, Media Production Suite (MPS), Aspera, rastreamento de VFX | ⭐ MPS e Content Hub |
| Páginas soltas | guias do Backlot, Conform Pulls, VFX Pulls, rastreamento de VFX | ⭐ Conform Pulls |

## Produção e pós (originais Netflix) — o que ler, por assunto

| Assunto | Páginas (slug) |
|---|---|
| Entrega: especificações | `editorial-cut-turnover-specification` (lista do corte e vídeo de referência) · `spec-image-sound-mps` · `branded-imf-delivery-specifications` · `branded-dcp-spec` · `branded-music-and-effects-specifications` · `branded-non-graded-archival-master-spec` · `branded-titles-and-graphics-requirements` · `branded-vfx-archival-asset-spec` · `delivery-netflix-language-codes-branded` |
| Entrega: boas práticas | `editorial-media-folder-structure-file-naming` · `textless-delivery-guidelines` · `prerelease-servicing-turnovers` (TC 00:00:00:00) · `best-practices-imf-delivery` · `delivery-for-textless-version-imf` · `printmaster-extraction` |
| Imagem: pós e cor | `branded-dailies-best-practices` · `branded-color-managed-workflow-in-resolve-for-aces` · `amf-in-an-aces-workflow` · `branded-framing-and-working-resolution-considerations` · `branded-framing-charts-best-practices` |
| Som | `branded-sound-mix-spec-and-best-practices` (−27 LKFS) · `m-and-e-creation-and-delivery-guidelines` · `branded-dolby-atmos-home-mix-deliverable-requirements` · `branded-asset-naming-sound-mastering-and-music-archival` · `branded-live-action-production-sound` |
| VFX | `branded-vfx-best-practices` · `branded-vfx-shot-version-naming-recommendations` · `branded-vfx-plate-naming-best-practices` · `branded-vfx-slates-and-overlays-guidelines` · `branded-vfx-media-review-delivery-specifications` · `branded-plate-capture-and-conform` (produção virtual) |
| QC | `branded-production-qc-glossary` e cerca de 110 páginas de erros de QC (`bqc-error-code-*`), ex. `bqc-error-code-framing-error` |

## Ferramentas — o que ler

| Ferramenta | Páginas (slug) |
|---|---|
| Conform Pulls (busca o original na nuvem pela EDL) | `using-conform-pulls` · `conform-pulls-user-guide` ⭐ · `conform-pulls-faq` · `conform-pulls-feature-support` · `conform-pulls-settings` · `conform-pulls-downloading` |
| VFX Pulls | `vfxpulls-capability` · `vfx-pull-frame-rate-compatibility` · `vfxpulls-day-correctness` · `vfxpulls-loop-test` · `vfxpulls-newmasters` · `vfx-pull-spec-template` · `vfx-pull-camera-formats` |
| Dailies do MPS | `mps-dailies-assistant-editor-guide` ⭐ · `mps-dailies-guide` · `dailies-editorial-guide` · `dailies-dit-guidance` |
| Content Hub (entrega do corte) | `contenthub-deliveringcuts` · `contenthub-navigating-deliverytonetflix` · `writtenguide-ch-reasonforredelivery` |
| QC automático (códigos de erro) | cerca de 140 páginas `automated-error-code-*` (ex. `automated-error-code-timedtext-maximumoffsetexceeded`: legenda em hora 1 em vez de hora 0) e `incorrect-timecode` |

## Fora do nosso alcance (lido, mas sem uso previsto)
Privacidade de elenco e equipe, segurança de conteúdo, saúde e segurança, IA generativa, sustentabilidade,
podcasts, faturamento de localização, guias de estilo de legenda por idioma, portal de artes, ferramentas internas
(Starship, Lucid, Nutshell, Grand Bazaar) e solução de problemas de rede/Aspera.
