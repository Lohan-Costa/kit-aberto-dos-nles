# PRMF — a máscara de OBJETO do Premiere 2026 (rotoscopia automática)

> Versão medida: **Premiere 26.0.2 (Mac)**, 2026-10-07. Arquivos: `laboratorio-de-midia/resultados/B10_ROTO/premiere-26.0.2-autor/
> rotoscopia_teste_premiere26 Masks/*.prmf` (projeto de rotoscopia do autor sobre o caso sintético B10). Leitor e decodificador
> em Python puro: `laboratorio-de-midia/lab/prmf.py` + `lab/gdeflate.py`; testes `tests/test_prmf.py`. Nível: **`confirmado`**
> (os 281 quadros dos 3 arquivos decodificam igual ao libdeflate da NVIDIA, a referência do GDeflate; a máscara bate com a
> máscara perfeita do B10).

## Onde mora
A máscara de objeto (`AE.ADBE AEMask2` com param 22 "Type" = 4, ver [prproj/escrita.md](../prproj/escrita.md) §11b) guarda o
resultado FORA do projeto: pasta **`<nome do projeto> Masks/`** ao lado do `.prproj`, um **`<guid>.prmf`** por "passada" de
rotoscopia. O param 24 "Controlador" da máscara lista os guids — em ASCII, num FlatBuffers em base64 (CORRIGE 2026-10-08; não UTF-16) → o NOME EXATO de cada `.prmf`. Mover o projeto sem a pasta = máscara perdida. O `.prproj` NÃO guarda o caminho da pasta (nem a palavra "Masks"); cada
auto-save ganha a sua `<nome do auto-save> Masks/` → a regra é `<nome do ARQUIVO do projeto> Masks/` ao lado dele (`confirmado`, Premiere 26 Mac, 2026-10-08, bancada `lab/bancadas/sessao_2026_10_08/premiere_pasta_masks.py`):
  | caso | o Premiere |
  |---|---|
  | nomes originais | abre sem perguntar |
  | projeto renomeado, pasta com o nome antigo | aviso **"Arquivos de máscara ausentes"** (botões "Agora não" / "Localizar") → "Localizar" abre a escolha de PASTA; apontada a pasta antiga (outro nome): **"Dados de máscaras localizados"** |
  | projeto e pasta renomeados juntos (`novo.prproj` + `novo Masks`) | abre sem perguntar |
  | sem a pasta | o aviso diz o CAMINHO EXATO que procurou: `<pasta do .prproj>/<nome do .prproj> Masks` |
  **Project Manager** ("coletar arquivos e copiar", `app.projectManager` com `CLIP_TRANSFER_COPY`): a pasta `<projeto> Masks`
  vai JUNTO, ao lado do projeto copiado, com os `.prmf` idênticos (md5). ⏳ No modo TRANSCODIFICAR: não medido.
  ⚠️ O vigia de diálogos aperta Return nesse aviso (modal sem título, sem texto legível pela acessibilidade) = "Localizar" →
  a escolha de pasta → "Cancelar" volta ao aviso: LAÇO. Para responder "Agora não": pausar o vigia e mandar Esc.
  ⚠️ `exportFramePNG` do QE NÃO mostrou o efeito das máscaras neste projeto (quadros iguais com e sem a pasta) — não serve de juiz. O `.prin` ao lado é outra coisa (índice de busca "LinearFeatureVectorIndex").
O binário: `SF::ObjectSelectionRasterStorage`, `RasterFrameDiskStorageManager`; a borda é refinada na renderização por
`solax::ultimate_urm::ObjectMaskRefiner` (modelo de IA local).

## Formato
| parte | conteúdo |
|---|---|
| cabeçalho (32 bytes) | `'prmf'`, versão u32 = 2, **posição do índice** u64, **tamanho do índice** u64, 32 u64 (início dos dados) |
| dados | um bloco por quadro, cada um um **TileStream GDeflate** |
| índice (fim do arquivo) | **FlatBuffers**: raiz {versão = 2, opções, vetor de quadros} |

**Quadro (tabela FlatBuffers):** marcador u32 (1) · **caixa** = 4 × u32 (**x, y, largura, altura** em px do quadro inteiro —
bate com a caixa justa da verdade do B10) · tamanho do quadro (1920, 1080) · **tempo** u64 em **ticks** (1/254016000000 s,
no tempo da MÍDIA, não da sequência) · posição u64 e tamanho u32 do bloco. Quadro vazio: caixa = quadro inteiro, bloco de 1 byte.

**GDeflate** (NVIDIA + Microsoft DirectStorage, `"SelectionFoundation.RasterSelection.ShouldUseGDeflateCompressionAlgorithm"`
no binário): `TileStream` de 8 bytes (`id` = 4, `magic` = id ^ 0xFF = 0xFB, nº de tiles u16, u32 com tileSizeIdx 2 bits = 1 e
tamanho do último tile 18 bits), offsets u32 × nº de tiles, e cada tile = um fluxo **DEFLATE64** cujos bits foram repartidos
em **32 sub-fluxos** (buffer de 64 bits por sub-fluxo, recarga de 32 bits quando cai abaixo de 32, na ordem dos sub-fluxos;
literal ou comprimento+distância inteiro num sub-fluxo, a distância uma rodada depois). ⚠️ Armadilhas da portagem:
o deflate comum NÃO lê (o 0xED inicial engana: o cabeçalho de Huffman "parece" deflate e quebra); e é **DEFLATE64** — o
símbolo 285 é 3 + 16 bits extras (não 258) e as distâncias vão a 64 KiB (sem isso dessincroniza no meio).

**A máscara descomprimida:** a caixa em **MEIA resolução**, **4 bits por pixel** (16 níveis de opacidade), dois pixels por
byte (o da **esquerda no nibble ALTO** — medido pela concordância bit × posição), linha de ceil(ceil(w/2)/2) bytes,
ceil(h/2) linhas. O arquivo guarda a máscara GROSSA: contra a máscara perfeita do B10, IoU **0,954** ampliando 2×; o Premiere
renderiza **0,985** porque refina a borda com a imagem na hora.

## Tradução para outros programas
`prmf.exportar_matte(prmf, saida.mov, fps, quadros, tc)` → vídeo de MATTE (branco = objeto, ProRes 422 HQ) no tempo da mídia:
Track Matte Key no Premiere 2023, matte externo no Resolve/After Effects. ⏳ Contorno por quadro → caminho de máscara
(`AE.ADBE AEMask` do 22/23) ainda não feito.
