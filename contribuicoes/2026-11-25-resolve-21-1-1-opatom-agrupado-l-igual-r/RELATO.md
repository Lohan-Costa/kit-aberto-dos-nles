# Resolve Studio 21.1.1: o OP-Atom do laboratório, agrupado num clipe, também sai L = R no render (como o XDCAM de 8 mono)

- Programa e versão: DaVinci Resolve Studio 21.1.1.10            - Sistema: macOS 27.2.1, Apple Silicon (arm64)
- Confiança: confirmado (nesta máquina); que é o mesmo mecanismo do XDCAM (trilhas mono tocando nos dois lados): inferido
- Como reproduzir: receita `receitas/base/B01.json` (kit no commit `426850d`), bancada `lab/bancadas/resolve.py`
  (`preparar` → `stills` → `renderizar` → `esperar_render`) pela API externa, num projeto novo do Local Database,
  e `python3 -m lab.bancadas.conferir <trabalho> <saida>/base/B01_FORMATOS`

## O que se viu

O OP-Atom gravado pelo laboratório (`B01_V01.mxf` + `B01_A01.mxf` + `B01_A02.mxf`, com o MaterialPackage que agrupa)
entra como UM item "Video + Audio" de 2 canais, como o banco já descreve (`protocolos/mxf/README.md`). Mas o render da
timeline sai com os dois canais misturados, igual ao XDCAM de 8 mono.

## O que se mediu (o número, o quadro)

Saída do `conferir` (render ProRes 422 + PCM 24 bits/48 kHz, 10 s a 25 qps):

| perfil | stills (5 posições) | render | tons por canal (verdade: [300], [400]) |
|---|---|---|---|
| MP4 H.264 | 5/5 | 250 quadros, TC 01:00:00:00 | [300], [400] ✅ |
| MOV ProRes 422 | 5/5 | idem | [300], [400] ✅ |
| MXF OP1a DNxHD | 5/5 | idem | [300], [400] ✅ |
| MXF XDCAM 50 (8 mono) | 5/5 | idem | [300, 400], [300, 400] ⛔ (já no banco, 21.1.0.14) |
| MXF OP-Atom (V+A1+A2) | 5/5 | idem | **[300, 400], [300, 400]** ⛔ (novo) |

Todo o resto do B01 no 21.1.1.10 bate com o que o banco mediu no 21.1.0.14 (quadro exato, TC, claques).
O "Audio Ch: verdade 0, NLE 2" que o `conferir` aponta no `B01_V01.mxf` é esperado: a verdade do V01 sozinho não tem
áudio, e o Resolve agrupou os 2 canais dos irmãos.

Para comparação, a mesma B01 no Premiere 26.0.2 (mesma máquina, preferências Use File): MP4/MOV certos; MXF OP1a,
XDCAM e OP-Atom todos L = R — bate com o banco (25.6.5 → 26.0.2 idênticos).

## O que não se mediu

- O conserto por `SetAudioMapping` (o do XDCAM, `plugins/resolve-scripting/api-scripting.md`) aplicado ao OP-Atom agrupado.
- O mesmo OP-Atom agrupado no 21.1.0.14 — o que diria se é mudança da 21.1.1 ou se sempre foi assim desde que o
  laboratório passou a agrupar.
- Windows.
