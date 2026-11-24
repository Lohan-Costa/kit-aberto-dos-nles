# Sync com fala — material REAL para testar sincronia por áudio (2026-11-04)

**Por que existe:** o som sintético do laboratório (ruído + rajadas, D06) NÃO serve para o sync por áudio do Premiere —
ele responde "Audio synchronize failure — a match could not be found", embora a correlação ache o deslocamento. Para
testar sincronia por áudio (Premiere Synchronize, Merge Clips, Multi-Camera; Órbita; Resolve), use estes pares, que
têm FALA. O gabarito abaixo é a correlação cruzada da forma de onda (8 kHz, mono, pico com 2º pico ≤ 8 %).

⚠️ **Exceção à regra do laboratório, autorizada pelo autor em 2026-11-04:** a mídia é REAL e mora aqui em
`referencias/sync-com-fala/` (fora do Git pelo `.gitignore`), cópia de `MIDIAS DE TESTES/1 PRODUCOES/…`.
O original continua lá; se esta pasta sumir, refaça a cópia pelos caminhos abaixo.

## `producao-a/` — 1 câmera + som direto (PRODUCAO-A, D02, 2023-04-05)

| arquivo | o que é |
|---|---|
| `A001_03170436_C009.mp4` | Blackmagic 4K convertido, 23,976, som guia estéreo, TC 04:35:43:23, 81,5 s |
| `PRODUCAO-A - 05-04 C4 P4-T003.WAV` | som direto, 5 canais, BWF `time_reference` 2258832576 (13:04:19), 92,1 s |

- **Gabarito:** a câmera começa **6,2690 s** depois do início do WAV (r 0,26). Os TCs NÃO servem (relógios diferentes).
- Premiere 26.0, Synchronize por áudio: **6,2563 s = 150 quadros** (gabarito 150,3).
- Origem: `MIDIAS DE TESTES/1 PRODUCOES/PRODUCAO-A/MIDIAS/CONVERTIDOS/D02_230405/` (`01_CAMERAS/CAM_A_Blackmagic-4k/A01/`
  e `02_SOM-DIRETO/SD02/`). Cópias inteiras.

## `PRODE/` — 2 câmeras + som direto (PRODE, 2024-05-31) — o caso MULTICAM

| arquivo | o que é |
|---|---|
| `PRODE_CAM-A_C0077_trecho.mov` | Sony, ProRes, 23,976, estéreo; trecho de 150 s a partir de 60 s do original |
| `PRODE_CAM-B_PANA2783_trecho.mov` | Panasonic, 23,976, 4 pistas (3 mono + 1 estéreo); os primeiros 130 s |
| `PRODE_ZOOM0034_Tr12_trecho.wav` | Zoom, 170 s a partir de 1790 s do original (95 min) |

- **Gabarito (nos TRECHOS):** CAM A começa **9,7705 s** depois do WAV; CAM B **20,8382 s**; B − A = **11,0679 s**
  (r 0,23 / 0,26 / 0,57).
- Premiere 26.0, Multi-Camera por áudio: CAM A 9,7598 s (234 quadros; gabarito 234,26), CAM B 20,8125 s (499; 499,62).
- ⚠️ **O TC dos trechos é o do ORIGINAL** (recorte `-c copy`: a CAM A diz 01:56:32:00 e começa 60 s depois) e o BWF do
  WAV também não foi atualizado. Não use o TC destes trechos como verdade.
- ⚠️ No original, a pasta `CAM A` tem um **U+F028** no fim do nome (espaço final de um nome criado no Mac, como o Windows
  o guarda): digitado, o caminho não abre. Ache pelo padrão (`CAM*A*`).
- Origem: `MIDIAS DE TESTES/1 PRODUCOES/PRODE/MIDIA MULTCAM/` (`CAM A/20240531_C0077-039.mov`, `CAM B/20240531_PANA2783-017.mov`,
  `SOM DIRETO/20240531_ZOOM0034_Tr12.WAV`). No original: CAM A em 1739,77 s do WAV e CAM B em 1810,84 s.
