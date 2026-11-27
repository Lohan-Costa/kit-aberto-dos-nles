# B01 (6 perfis) no DaVinci Resolve Studio 21.2: igual ao 21.1

- Programa e versão: DaVinci Resolve Studio 21.2.0.6 (build 21.2.00006)        - Sistema: macOS 27.2.1, Apple M5 Pro (arm64)
- Confiança: confirmado (1 rodada)
- Como reproduzir: `python3 -m lab.gerar receitas/base/B01.json --verificar`; com o Resolve aberto, pela API externa
  (Python 3.9 do sistema), `lab.bancadas.resolve.rodada(r, <caso>, <trabalho>, "LAB B01 FORMATOS", fps="25")`;
  depois `python3 -m lab.bancadas.conferir <trabalho> <caso>`. ffmpeg 9.1 (Homebrew).

## O que se viu
O 21.2 se comporta como o 21.1 registrado no banco (`plugins/resolve-scripting/api-scripting.md`, seção B01 do 21.1).
A API externa conectou sem ajuste ("External scripting using: Local" já ligado).

## O que se mediu (o número, o quadro)
- Pool: 6 itens, todos certos (XDCAM MPEG2, DNxHD 120 do OP1a, H.264 High L4.0, ProRes 422, WAV). O OP-Atom do
  laboratório (`lab/opatom.py`) entrou AGRUPADO: `B01_V01.mxf` "Video + Audio", `Audio Ch` 2 (o conferidor marca
  "DIFERE" porque a verdade do arquivo de vídeo sozinho diz 0 canais — esperado).
- 5 timelines, 25 stills (início · … · fim): quadro e TC exatos, início 01:00:00:00.
- 5 renders ProRes 422: 250 quadros cada, códigos ok, TC 01:00:00:00, claques no segundo exato (primeira em 0,4–0,9 ms);
  `TimeTakenToRenderInMs` 725–1307.
- ⛔ Áudio: mp4, mov e MXF OP1a com L = 300 Hz, R = 400 Hz (certo); XDCAM 8 mono e OP-Atom (2 mono) com L = R =
  300 + 400 Hz — o mesmo L = R que o banco registra para o XDCAM no 21.1.
- Resultado completo: `resolve-21.2.0.6-darwin.json` (nesta pasta).

## O que não se mediu
- O conserto do L = R por `MediaPoolItem.SetAudioMapping` no 21.2.
- Outras taxas (B02) e os casos B03–B06 no 21.2.
- Windows.
