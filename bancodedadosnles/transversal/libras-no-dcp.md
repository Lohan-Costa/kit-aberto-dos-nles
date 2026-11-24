# Libras no DCP — vídeo VP9 empacotado como áudio PCM (ISDCF Doc 13)

> **Fonte:** `VP9WAVDCP/vp9-to-wav-dcp` (app "VP9 para WAV", Tauri 2 + Rust, v0.3.0 de
> 2026-07-17), o primeiro app da família. Registrado pelo zelador do SSD em 2026-10-06, ao
> arquivar o projeto, a partir do README, do código e das memórias do Claude do projeto.
> **Confiança:** a estrutura do WAV é `confirmado` pelo validador do próprio app (os WAV gerados
> passam nas 5 checagens abaixo) e pelo uso dos usuários; ⚠️ a exibição numa cabine real com o
> decodificador de Libras **não foi registrada** (`pendente`).
> **Por que está aqui:** é entrega de acessibilidade para cinema, e vai virar caso do laboratório
> de mídia (Libras longo). Quem gerar ou conferir o canal 15 começa por aqui.

## O formato

O DCP carrega o áudio como PCM de 16 canais. O **canal 15** transporta dados: um vídeo VP9 com o
intérprete de Libras, fatiado em blocos de 2 s e escrito como se fosse amostra de áudio. Na
exibição, um decodificador externo lê o canal 15 da saída AES/EBU da cabine e remonta o vídeo.

| atributo | valor |
|---|---|
| vídeo | VP9 (`libvpx-vp9`), **480 × 640** (retrato, 3:4), **24 fps**, `yuv420p`, WebM |
| bitrate | teto de 1,0 Mbps (ver a armadilha) |
| bloco | **2 s** de vídeo por bloco, keyframe no início de cada um |
| WAV | **mono, 48 kHz, 24 bits** PCM |
| tamanho do bloco PCM | **288.000 bytes** (= 2 s × 48.000 × 3 bytes) |
| conteúdo do bloco | cabeçalho de **20 bytes = 5 × uint32 big-endian**: `H1=0xFFFFFFFF`, `Lv`, `Lb=288000`, `Le`, `H2=0xFFFFFFFF`; depois o **EBML header** (`Le` bytes: tudo antes do ID de Segment `0x18538067`), o **Segment VP9** (`Lv` bytes) e zeros até completar o bloco (`packager.rs::build_pcm_block`) |
| canal no DCP | 15 |

O validador do app confere: cabeçalho do WAV (48 kHz/24 bits/mono), o magic em todos os blocos,
os 288.000 bytes por bloco, o EBML header e o Segment VP9 de cada bloco.

## ⚠️⚠️ A armadilha: `-maxrate` sozinho NÃO limita o tamanho de um bloco — `confirmado`

Sintoma relatado por usuários: "Chunk grande demais" (`20 + Le + Lv > 288000`) mesmo com o vídeo
já em VP9 a ~1 Mbps. Causa: o encode usava `-b:v 1000k -maxrate 1000k` **sem `-bufsize`** e sem
keyframes forçados. No `libvpx-vp9`, `-maxrate` sem `-bufsize` é um teto de MÉDIA numa janela, não
um limite por bloco. O orçamento real é **~287.700 bytes por bloco ≈ 1,15 Mbps**, e 2 s de mãos
rápidas estouram o alvo em mais de 15%.

Conserto (v0.3.0):
- VBV apertado: `-b:v`, `-maxrate` e `-bufsize` iguais ao alvo;
- keyframes exatos a cada 2 s: `-force_key_frames expr:gte(t,n_forced*2)`;
- **conferir e recodificar:** segmenta, mede o maior bloco (o tamanho do arquivo do bloco já é
  `Le + Lv`, não precisa interpretar nada) e, se passar de 287.980 bytes, recodifica com
  `alvo × 0,85` (começa em 900 kbps, piso 300 kbps);
- se a entrada já é VP9 conforme (480×640, 24 fps, `yuv420p`, sem crop, `ceil(duração/2)` blocos,
  todos dentro do limite), empacota **sem recompressão**.

⭐ A regra geral: quando o formato de destino tem limite **por bloco**, o controle de taxa do
encoder não é garantia. Meça o bloco e recodifique; o laço é o que garante.

## Distribuição (o que os usuários precisam fazer)

App sem assinatura: no macOS aparece "está danificado e não pode ser aberto" e se resolve com
`xattr -cr "/Applications/VP9 para WAV.app"`; no Windows, SmartScreen → "Mais informações" →
"Executar mesmo assim". O ffmpeg/ffprobe vão como sidecar do Tauri, com o nome do alvo
(`ffmpeg-aarch64-apple-darwin`, `ffmpeg-x86_64-pc-windows-msvc.exe`).
