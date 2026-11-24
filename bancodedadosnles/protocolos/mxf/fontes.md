# Fontes — MXF

Rastreabilidade das descobertas deste protocolo. (Os blocos anteriores a 2026-08 estão
narrados em [README.md](README.md) e [timecode.md](timecode.md), com data e app de origem
inline.)

## 2026-08-20 — codecs proprietários (Sony X-OCN)

**Amostra:** `MIDIAS DE TESTES/SONY XOCN/Scene1/` — quatro clipes de Sony VENICE
(`CameraAttributes: MPC-3628`), 24p, 15 s cada, gravados na mesma diária (2022-06-24) e
distribuídos pela Sony como material de demonstração:

| clipe | codec | tamanho |
|---|---|---|
| `A002C041_22062469` | ProRes 4444 4096×2160 (**controle**) | 1,98 GB |
| `A002C042_22062495` | X-OCN **LT** 8192×4320 | 2,93 GB |
| `A002C043_2206243M` | X-OCN **ST** 8192×4320 | 4,97 GB |
| `A002C044_220624KN` | X-OCN **XT** 8192×4320 | 7,25 GB |

Cada um com sidecar `M01.xml` — e com um AppleDouble `._*.mxf` de 4096 bytes ao lado.

**Método**

- `ffprobe` (build local), `-show_format` e `-show_streams`, com o **código de saída
  conferido explicitamente** — foi assim que a falha silenciosa apareceu.
- `pymediainfo` / `MediaInfo.dll` do venv do `_DeLaPraCa`.
- Sidecar `M01.xml` lido como XML.
- Linkagem real no MC 25.6.0.58781 / Win 11, com o plugin
  `nablet SONY RAW X-OCN AMA Plug-In 2026.8.0.6299`, e a bin resultante lida com pyavb
  (`ORBITA - TESTE/XOCN LINK.avb`). Os MobIDs da bin foram comparados byte a byte com os
  UMIDs que o `ffprobe` lê do arquivo.
- Harness e resultados: `MIDIAS DE TESTES/SONY XOCN/medicao/` (`medicao_xocn.py`,
  `ROTEIRO.md`, `snapshot_antes.json`, `snapshot_depois.json`).

**Documentação do fabricante consultada**

`nablet SONY RAW X-OCN AMA Plugin Release Notes and Manual v2026.8.0.pdf` e
`nablet AMA Plugins Manager User Manual.pdf` (requisitos de storage, modos de playback,
conflito com o plugin legado `Sony PV-RW1`, licenciamento).
- 2026-10-06 — a correção da colisão de MobID (sanitizar o AAF, famílias de MobID, verificação pelos bytes) em codecs-proprietarios.md, de `SANITIZADOR_DE_AAF/CLAUDE.md` (validado no MC em 2026-08-20). Registrado pelo zelador do SSD ao arquivar.
- **Laboratório de Mídia, 2026-10-06** — MXF OP-1a, XDCAM 50 e OP-Atom ESCRITOS pelo ffmpeg 8.1.1 (Mac): TC no formato, um `material_package_umid` por arquivo, `qmax 28`. Ver README §MXF escrito pelo ffmpeg.
