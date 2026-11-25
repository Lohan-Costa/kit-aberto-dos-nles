# ffprobe 9.0.2 repete a linha do stream no CSV quando se pede `stream_tags` — um teste do laboratório falha com a mídia certa

- Programa e versão: ffmpeg/ffprobe 9.0.2 (Homebrew)            - Sistema: macOS 27.2.1, Apple Silicon (arm64)
- Confiança: confirmado (nesta máquina); que a causa é o ffprobe 9 e não a build do Homebrew: inferido
- Como reproduzir: `python3 -m lab.gerar receitas/base/B01.json --verificar` e depois
  `ffprobe -v error -select_streams v:0 -show_entries "stream=nb_frames,width,height,r_frame_rate:stream_tags=timecode" -of csv=p=0 <saida>/B01_FORMATOS/B01_MOV-PRORES.mov`

## O que se viu

`laboratorio-de-midia/tests/test_prproj_mascara.py::TestMascaraDeObjeto::test_matte_ao_lado_com_a_duracao_da_midia`
falha (kit no commit `426850d`), embora o matte gerado esteja certo:

```
AssertionError: '1920,1080,25/1,300\n\n1920,1080,25/1,300,01:00:00:00' != '1920,1080,25/1,300,01:00:00:00'
```

## O que se mediu (o número, o quadro)

Na amostra B01 (ProRes, 250 quadros), o comando acima devolve TRÊS linhas — o stream sem a tag, uma vazia, o stream
com a tag:

```
1920,1080,25/1,250

1920,1080,25/1,250,01:00:00:00
```

Os valores estão certos; só a forma da saída mudou. Resto da suíte `laboratorio-de-midia/tests piloto/tests`:
59 passaram, 7 pularam (moldes de produção que não vêm na cópia pública, B10 não gerado, 2 só do Windows), 1 falhou (este).

## O que não se mediu

- O ffprobe 9.0.2 de outra origem (build oficial, Windows) e o ffprobe 8 nesta máquina — o que diria se é do 9 ou da build.
- Se outros pontos do kit leem `-of csv=p=0` com `stream_tags` e tropeçam igual (não procurei).
- Contorno provável (não aplicado): pegar a última linha não vazia, ou ler com `-of json`.
