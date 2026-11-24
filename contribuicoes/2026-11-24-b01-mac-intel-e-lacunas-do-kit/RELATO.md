# Primeira instalação num Mac Intel: B01 no Resolve 21.1.2 e no Premiere 26.5.3, portas do MC 24.12.6 no Mac, e três lacunas do kit público

- Programa e versão: DaVinci Resolve Studio 21.1.2.10 · Adobe Premiere Pro 26.5.3 · Avid Media Composer 24.12.6
- Sistema: macOS 26.7.3, Mac Intel (x86_64), GPU AMD Radeon RX 6900 XT; ffmpeg 8.1.2 (build estático evermeet.cx); Python 3.14.0
- Confiança: confirmado (o que está em "O que se mediu"); o resto, como dito em cada item
- Como reproduzir: `python3 -m lab.gerar receitas/base/B01.json --verificar`; bancadas `lab/bancadas/resolve.py`
  (`preparar` → `stills` → `renderizar`, fps 25) e `lab/bancadas/premiere.py` (`preparar` → `stills` → `renderizar`, "2026");
  `python3 -m lab.bancadas.conferir <trabalho> saida/base/B01_FORMATOS`

## O que se viu

1. **Homebrew não serve mais no Mac Intel** (Tier 3 desde 09/2026, sem bottles). Contorno: ffmpeg/ffprobe 8.1.2 estáticos
   na pasta própria do laboratório (`~/Library/Application Support/laboratorio-de-midia/ffmpeg/`), que o `lab/ffmpeg.py`
   já procura primeiro. Sugestão: o README do laboratório citar esse caminho para Mac Intel.
2. **15 testes da suíte do laboratório falham no kit público** por arquivos de referência que não vêm no repositório:
   `resultados/` está no `.gitignore` (B09_COR/prproj, B10_ROTO/premiere-26.0.2-*, `resultados/*/prproj`) e
   `lab/moldes/resolve/{mascara_modelo.dvcc,recibo_modelo.bin,versao_importada.bin}` não existem. Os testes deveriam
   PULAR com aviso (como fazem sem ffmpeg) ou os arquivos entrarem no kit.
3. **A bancada do Media Composer não roda fora do Windows nem fora da máquina do autor**: `lab/bancadas/avid.py` usa
   `interface_win`/`vigia_windows` e importa o cliente da API (`avid.mcapi`) de `2 ATIVOS/_DeLaPraCa`, que não está no kit.
   Sem esse cliente (ou os `.proto`), não há como chamar o 9100.
4. No Premiere 26.5.3 desta máquina, a primeira abertura ficou ~2 min em "Initializing GPU" durante o `newProject`/import;
   a ponte seguiu respondendo e o script continuou sozinho (não é diálogo).

## O que se mediu (o número, o quadro)

- **B01 gerado e verificado**: 8 arquivos, TUDO CONFERE (MP4 H.264, MOV ProRes, MXF OP1a, XDCAM 50 8 mono, OP-Atom V01/A01/A02, WAV BWF).
- **Resolve Studio 21.1.2.10**: 6 itens no pool para 8 arquivos (OP-Atom agrupado num "Video + Audio" de 2 canais, como
  esperado com o gravador atual); 25/25 stills no quadro e TC certos; 5/5 renders ProRes com 250 quadros, código e TC
  01:00:00:00 exatos; MP4/MOV/OP1a com L = 300 Hz, R = 400 Hz; XDCAM e OP-Atom L = R. Conserto do XDCAM por
  `SetAudioMapping` estéreo (canais 1–2) antes de criar a timeline: render L = 300 Hz só, R = 400 Hz só.
- **Premiere 26.5.3**: 8/8 importados, nenhum recusado; 25/25 stills exatos; 5/5 renders com 250 quadros e TC certos;
  MP4/MOV com canais certos; MXF OP1a estéreo, XDCAM e OP-Atom L = R no render (como no 25.6.5).
- **Media Composer 24.12.6 (Mac)**: com o MC fechado, nenhuma porta da API em LISTEN; com um projeto aberto, o MC escuta
  **9100 em `[::1]` e em `127.0.0.1`**, e responde ao prefácio HTTP/2 com SETTINGS (gRPC); o gateway escuta 4920/4930
  só em `[::1]`.

## O que não se mediu

- Nenhuma RPC no 9100 do MC no Mac (falta o cliente): "responde sem token" segue `hipotese` aqui.
- B02–B06 e as outras receitas nesta máquina.
- A versão do Premiere (Beta) 26.5.0 instalada aqui.
