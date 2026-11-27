# EDL para o som: onde a fonte se perde — proposta (2026-11-25)

Página para o autor analisar: `docs/plano/2026-11-25-edl-para-o-som/index.html` (publicada; o link fica no handoff).

## A pergunta (autor, 2026-11-25)

Com material em nest, subclipe, merged clip, multicâmera, group clip…, a EDL exportada leva a informação certa para a
equipe de som? "Investigar possíveis problemas que ocorrem de EDLs exportados para equipe de som e que chegam errado e
ninguém sabe dizer exatamente."

## O que já se sabe (rodada 1, mesma data — banco `protocolos/edl/README.md`)

Clipes simples: Premiere 26.0.2 = só CMX 3600, 1 vídeo + 4 canais, reel `AX` sem tape name, MacRoman; MC 25.12 =
10 formatos, UTF-8 (acento do reel vira U+FFFD), reel = nome da fonte (8 no CMX_3600), um evento por trilha até A10.
O canal da EDL é a TRILHA da timeline, não o canal do arquivo. Banco: o merged por ponto de entrada põe o som 1 quadro
antes (240 → 239); o WAV lido em "tempo real" a 23,976 cai fora numa multicâmera do gerador do laboratório.

## Hipótese central

A EDL diz UMA fonte por evento (reel + TC + trilha). As estruturas que escondem outra fonte (nest, merged, multicâmera,
group, AutoSync) obrigam o NLE a escolher uma camada; se ele escolhe a errada, a EDL fica bem formada e aponta para o
lugar errado — por isso "ninguém sabe dizer".

## Os casos

| # | NLE | estrutura | risco a medir |
|---|---|---|---|
| S1 | os dois | subclipe do master | o nome do comentário é do subclipe; reel/TC do master? |
| S2 | Premiere | merged por TC | o som sai com o reel e o TC da CÂMERA? |
| S3 | Premiere | merged por ponto de entrada | idem + o quadro a menos (banco) |
| S4 | Premiere | multicâmera (ângulo ativo) | a câmera ativa ou a fonte multicâmera? o som direto com o reel dele? |
| S5 | Premiere | nest | o nest vira a fonte (reel = nome do nest)? |
| S6 | MC | AutoSync (subclipe sincronizado) | imagem e som com reels próprios? |
| S7 | MC | group clip do jeito do editor (sequência com CAM A na V1, CAM B na V2…, só o som direto; botão direito no monitor Record › criar grupo) | a câmera ativa e o som direto com o reel e o TC certos? |
| S8 | MC | multigroup / troca de ângulo no meio | cada trecho com a sua câmera? |
| S9 | MC | collapse (nest) | o MC desce até as fontes? |
| S10 | os dois | som direto polifônico usado só em alguns canais (3 e 5) | a EDL diz qual canal do ARQUIVO? |
| S11 | os dois | sound rolls com nomes que começam igual | colisão no reel de 8 caracteres |

## Exportações por caso

- Premiere: padrão · "Usar rolagem de som/timecode de som" · "Usar nome do arquivo de origem".
- MC: File_129 e CMX_3600 · Formatting › Source TC (Start × as opções de som/aux que o MC oferecer) · Reel ID Type.

## O conferidor

Um script que lê cada EDL e, evento a evento, acha o arquivo pelo reel (nome) e confere o trecho contra o PLANO da
montagem (a verdade: cada caso é montado por nós, com mídia que diz em cada quadro e canal o que é). Saída: certo ·
alerta · errado calado, por caso × NLE × exportação. Depois serve ao produto: conferir uma EDL antes de ela sair.

## A ordem

1. Receita nova (B31): duas câmeras com TC e som guia, som direto polifônico de 6 canais (BWF com sound roll e nomes de
   canal), nomes que começam igual. Gerar e verificar.
2. Premiere: montar S1–S5, S10, S11 por script (merged e multicâmera pelo menu nativo pelo NOME).
3. MC: S1, S6–S11 (o group pelo gesto do editor, pilotado; ou escrito pelo pyavb — `spikes/carta_aberta_group_clip.py`).
4. Exportar as variantes (pilotado) e rodar o conferidor.
5. Banco (`protocolos/edl/`), lista de conferência para mandar EDL ao som, relatório.

## Decisões do autor (2026-11-25)

1. O group clip do MC é ESCRITO POR PROGRAMA (pyavb, sync por TC, só o som direto) — `spikes/carta_aberta_group_clip.py`.
2. A exportação que as casas de som pedem, e que entra como variante obrigatória: **uma única trilha de vídeo com os
   cortes da cena, e todas as trilhas de áudio com os cortes da montagem.** No Premiere isso esbarra no número fixo de
   canais (4) por EDL: são VÁRIAS EDLs (uma por grupo de trilhas) — medir como ficam e se casam entre si.
3. **O MC primeiro** (S1, S6–S11); o Premiere depois.
