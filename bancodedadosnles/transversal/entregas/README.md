# Entregas — o que as casas de pós pedem (módulo de análise de manuais)

> ⚠️ **Manual é GUIA, não lei** (autor, 2026-10-04): pode estar errado, impreciso ou desatualizado; serve para
> direcionar a entrega e a conversa com a casa, e é maleável. Nada daqui vira requisito duro de app: no máximo
> opção, preset ou aviso que a pessoa ajusta — e sempre se combina com a casa da vez.

Aberto em 2026-10-04 (pedido do autor). Lê os **manuais de entrega dos fornecedores** (cor/conform, som,
plataformas) para três usos:
1. **os apps** (De Lá Pra Cá e família): o que já atendemos, o que é opção, o que é lacuna — `lacunas.md`;
2. **boas práticas** de quem entrega (o editor, o assistente): a mesma exigência dita por várias casas, e onde
   elas DIVERGEM — `matriz.md`;
3. **achar o que falta mapear** quando entra um manual novo: o que ele pede que a matriz ainda não tem.

Mapa do site da Netflix em português (850 páginas, 2026-10-04): `netflix-site-mapa.md`; índice original e texto em
`8 REFERENCIA/MANUAIS ENTREGA/PUBLICOS/NETFLIX (site)/`.

## Arquivos
- `matriz.md` — exigência × fornecedor, por tema (timeline de cor, projeto/cor, TC e bipes, referência, som,
  VFX, mudança de corte, arquivo/nomes/taxa). ⚠️ marca as divergências.
- `lacunas.md` — cada exigência contra o que o app faz (auto · opção · pessoa · lacuna · fora).
- `fichas/` — UMA por manual: o resumo fiel do texto E dos prints (as janelas de export com cada opção), a
  versão, a data e o arquivo de origem. Sem contatos pessoais.

## Os manuais
Ficam em `PROGRAMAS COM CLAUDE/8 REFERENCIA/MANUAIS ENTREGA/TECH SPECS/` (fora do banco: são documentos dos fornecedores).

| Ficha | Fornecedor | Área | Versão/data |
|---|---|---|---|
| `casa-pos-1-conform-v1.5` | CASA-POS-1 | cor/conform (Resolve) | v1.5 |
| `casa-pos-1-netflix-offline-online-v8` | CASA-POS-1 (Netflix MPS) | conform/online | v8, jul/2024 |
| `casa-pos-2-conform-avid` | casa-pos-2 | conform (Avid → Resolve) | sem data (arq. 2026-09) |
| `casa-pos-3-conform-avid` | CASA-POS-3 | conform (Avid → Resolve), canal CANAL-L | sem data (arq. 2026-09) |
| `netflix-pix-v12` | Netflix | revisão (Pix) e locked cut | v12 (2021) + Locked Cut v3.0 (2019) |
| `netflix-npc-sdr-prores-v1.0` | Netflix | arquivo NPC não final | v1.0, 06/04/2026 |
| `casa-pos-4-som-2026` | CASA-POS-4 | pós de som (Pro Tools) | 2026 |
| `casa-pos-5-edicao-de-som-2021.2` | 1927 Audio | edição de som | 2021.2 |
| `casa-pos-6-producao-u` | −12dB (CIDADE-V) | pós de som, um projeto | 25/03/2026 |
| `netflix-studio-partner-site` | Netflix (site público) | turnover editorial, Conform/VFX Pulls, títulos, mapa do site | lido em 2026-10-04 (inglês) |
| `estudio-o-sound-editorial-turnover` | estudio-o (EUA) | turnover de som | público |
| `estudio-n-picture-handover` | ESTUDIO-N (NZ) | conform, cor e som | v1, 14/11/2022 |
| `cinemateca-deposito-legal-portaria-221-2025` | Cinemateca Brasileira / MinC | preservação (depósito legal) | 27/06/2025 |
| `ebc-nor-704-tv-publica` | EBC / TVs públicas | master de TV aberta brasileira | 06/06/2019 |
| `cbc-radio-canada-program-delivery-v5.1` | CBC/Radio-Canada | master de TV | v5.1, 2016 |
| `svt-file-delivery-e-arquivo` | SVT (Suécia) | master de TV e arquivo | v5.1 (2021), v2.7 |
| `rte-guide-commissioned-programmes` | RTÉ (Irlanda) | master de TV | 2019 |
| `dpp-as11-uk` | DPP (Reino Unido) | AS-11, apresentação | 2014 |
| `channel4-dpp-as11-v5.2` | Channel 4 / DPP | AS-11 completo | v5.2 (2022/2023) |
| `ebu-r128-loudness` | EBU | loudness | R 128-2023 |
| `discovery-global-tech-specs-v6` | Discovery (WBD) | master (resumo; "confidencial") | v6, 2020 |
| `empresa-p-dcp-dsm` | EMPRESA-P | DSM para DCP | sem data |
| `amazon-prime-video-video-requirements` | Amazon Prime Video | mezanino de distribuição | 21/08/2026 |
| `apple-tv-channels-subscription-video-spec` | Apple | pacote de distribuição | 1.11 |
| `hbo-max-av-specs-marca` | HBO Max | marca/promo (baixa relevância) | — |
| `pbs-tos-e-pbsd-global-specs` | PBS / PBS Distribution | master de TV (EUA, 29,97 DF) | TOS 2020 · PBSd 2025-10-09 |
| `paramount-anz-network10-technical-delivery-2026` | Paramount ANZ / Network 10 | master de TV (Austrália) | 2026 (Dom. 1.0, Int. 1.2) |
| `uktv-acquisitions-technical-delivery-2026` | UKTV | master de TV (aquisição, UK) | 2026 |
| `telepacifico-protocolo-2025` | Telepacífico (Colômbia) | master de TV pública | 2025 |

Os PÚBLICOS ficam em `PROGRAMAS COM CLAUDE/8 REFERENCIA/MANUAIS ENTREGA/PUBLICOS/<instituição>/` (PDFs, ou o texto salvo da página).

## Como entra um manual novo
1. O autor solta o PDF em `PROGRAMAS COM CLAUDE/0 ENTRADA/` (a antiga `A ORGANIZAR`) e pede para organizar.
2. O PDF vai para `8 REFERENCIA/MANUAIS ENTREGA/TECH SPECS/` (pasta do fornecedor se forem vários).
3. Ler **texto e páginas como imagem** (os prints trazem as configurações: `brew install poppler` deu ao leitor
   o `pdftoppm`; só o texto perde as janelas de export inteiras — aconteceu na 1ª leitura, 2026-10-04).
4. Escrever a ficha; levar cada exigência à `matriz.md` (nova linha ou nova sigla numa linha existente; ⚠️ se
   diverge); e à `lacunas.md` se um app a toca. Registrar em `../fontes.md`.

Confiança de tudo aqui: `documento` — o que a casa PEDE. Não é medição de NLE.
