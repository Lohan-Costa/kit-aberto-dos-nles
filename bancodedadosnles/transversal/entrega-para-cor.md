# Entrega para a COR — o que uma casa de finalização pede (o conform visto do outro lado)

> **MOVIDO (2026-10-04):** este resumo virou a ficha `entregas/fichas/casa-pos-1-conform-v1.5.md` (agora com os
> prints lidos), dentro do módulo de entregas (`entregas/README.md`, `matriz.md`, `lacunas.md`), que cruza a
> CASA-POS-1 com outras 8 casas. O texto abaixo fica como estava, para os links antigos.


Fonte: **Manual de Conform v1.5 da CASA-POS-1** (casa de finalização e cor), PDF de 11 páginas
entregue pelo autor em 2026-10-03. Confiança: `documento` (regra de UMA casa; outras variam). Não é
engenharia reversa: é o requisito de quem RECEBE o conform. Serve para decidir o que um app
automatiza, o que deixa como opção e o que fica com pessoa.

## O que pedem (resumo fiel)

- **Software:** DaVinci Resolve 20.2.2 ou inferior (versões superiores validar antes).
  ⚠️ O autor manda ignorar exigência de versão de casa: o piso é o do app.
- **Projeto:** série = um DRP por episódio; longa = rolos de 25–45 min, um DRP por rolo, sem rolos
  curtos, sem partir uma sequência entre rolos, atenção às emendas de som, Rolo 00 para vinhetas
  (obrigatório para depósito na Cinemateca). ⛔ Divisão por rolos = trabalho de pessoa (autor).
- **Media Management:** "Used Media and Trim Keeping Handles", handles ≥ 10 quadros nos OCFs,
  COPIAR (não transcodar), preservar a estrutura de pastas da câmera; o DRP vai relinkado à mídia
  consolidada, nunca à completa; nada offline; mandar vídeo de referência.
- **Master settings:** resolução = a do delivery de maior resolução; taxa = a da montagem e do MOV.
- **Color management:** ACEScct, ACES 1.3, ODT Rec.709 BT.1886; projeto em SDR Rec.709.
- **Timeline:** sem mídia não usada; áudio = só o do MOV de referência ou uma mix; poucas trilhas;
  desfazer compound e achatar multicam; remover cortes falsos; só marcadores pertinentes; marcadores
  para estabilização, reenquadro, scale e mudanças de cor feitas na montagem; artes, letreiros e
  material de arquivo em trilhas de cima; efeitos de zoom/crop/posição NO clipe, nunca em camada de
  ajuste. Sugestão de trilhas: V1 OCF · V2 arquivo licenciado em alta · V3 stills · V4 artes.
- **TC e bipes** (se a master for deles): longa → R00 00:00:00:00, R01 01:00:00:00…; bipe em TC In
  + 06:00, 1º quadro em + 08:00, último quadro em TC Out − 02:00, bipe no TC Out.
- **LMT:** CDL no node 1, LUT no node 2, batendo com o MOV de referência.
- **Vídeo de referência:** H.264/DNxHD/ProRes 422 Proxy, LPCM, .mov ou .mp4, Rec.709 2.4, mesmo TC
  e taxa da timeline, janela do delivery (ou tarjas), burn-in de Source File Name, Source TC, Rec
  TC, diária (lente/LUT opcional).
- **Material de arquivo:** sem espaços nem caracteres especiais; estrutura de pastas da câmera; TC
  igual ao do offline (senão novo AAF); nunca renomear depois do envio.
- **VFX/GFX:** uma timeline .drt SÓ com os VFX, mesmo TC e bipes, + planilha (EP/rolo, TC, seq,
  shot nº de 4 dígitos, nome do shot, descrição).
- **Atualização de corte:** .drt só com as mídias que mudaram, mesmo start TC, e referência NOVA
  inteira do rolo.

## Onde isto encosta nos apps

- De Lá Pra Cá: a comparação item a item (automático / opção / pessoa / fora) está no organograma
  "Premiere → Resolve: PRODUCAO-B" (https://claude.ai/artifact/M1mX26CLWEePas6Xck9mjt, seção CASA-POS-1).
  Lacunas viáveis: juntar cortes falsos; marcador opcional de reenquadro/scale; aviso de nome com
  espaço/acento; timeline só de VFX + planilha.
- A regra de ofício do vídeo de referência na timeline: [operacoes-de-nle.md](operacoes-de-nle.md) J.3b.
