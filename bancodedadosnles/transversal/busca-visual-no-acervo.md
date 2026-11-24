# Busca visual no acervo — "onde mais eu tenho um plano assim?"

> **Medido em 2026-09-11**, Ciclo Assist, Windows 11 / MC 25.6, mídia real (bin de cena com
> três planos e vários takes cada). Confiança: `confirmado` para o número; ⚠️ `hipotese`
> para o que a medição **não** cobriu — ver o fim.

O editor quer duas coisas que se parecem e não são a mesma: **achar outra tomada do mesmo
enquadramento** (match cut, cobertura) e **achar uma pessoa**. Este arquivo trata da
primeira, que é a que se resolve barato.

## O que foi comparado, e o resultado

Precisão em `top-k` sobre quadros extraídos de takes, com o gabarito de graça que uma cena
dá: *dado um quadro, os vizinhos mais parecidos deveriam ser do MESMO plano*.

| motor | tamanho em disco | acerto | tempo por quadro |
|---|---|---|---|
| ao acaso (piso) | — | **38%** | — |
| **pHash** (DCT 32×32, só numpy) | **0 MB** | **93%** | 2 ms |
| **MobileNetV2 em ONNX** (classificador usado como extrator) | **14 MB** | **99%** | 5 ms |

⇒ **Não é preciso CLIP de 350 MB** para "planos parecidos". E nenhum dos dois exige torch:
o `onnxruntime` sozinho roda o segundo.

⚠️ **"Planos parecidos" é imagem → imagem**, e a frase acima vale só para isso. Ver
§ *O que este motor NÃO faz* — é a razão de o CLIP voltar à mesa em outra pergunta.

## ⛔⛔ A armadilha do INSTRUMENTO, e ela invalida a medida inteira

A primeira versão da medição deixava os quadros do **próprio take** no conjunto de busca.
Quatro quadros de um mesmo take são quase a mesma imagem — então os vizinhos mais próximos
eram sempre os irmãos, e **qualquer motor marcava 100%**, inclusive um que comparasse o
tamanho em bytes.

⭐ **A pergunta real é "onde MAIS existe algo assim?"**, e ela só aparece quando o take de
origem sai do conjunto. Quem for repetir esta medição em outro app: exclua a origem, ou o
número não quer dizer nada. E vale para o produto, não só para a medição — a busca em
produção também exclui a própria mídia.

## Detalhes de implementação que economizam trabalho

- **O vetor é a saída final do classificador.** O grafo do `mobilenetv2-12.onnx` não expõe a
  penúltima camada, e para SEMELHANÇA os logits normalizados já servem — é o que foi medido.
- **Normalizar o vetor** (L2) faz o produto escalar ser a parecença: a busca vira uma
  multiplicação de matriz.
- **Poucos quadros por clipe.** 12 espalhados cobrem o material; quadros vizinhos do mesmo
  plano dizem a mesma coisa e só engordam o índice.
- **Uma linha por mídia no resultado**, a do melhor quadro — senão os doze quadros de um
  plano tomam a lista inteira e quem pergunta vê um resultado só, doze vezes.
- **Sem Pillow:** o `ffmpeg` decodifica o JPEG e redimensiona para 224×224 numa chamada,
  entregando `rgb24` cru que o numpy lê do buffer (`-f rawvideo`). Uma dependência a menos.
- **Escala:** 358 mídias × 12 quadros = 4.296 vetores de 1.000 floats ≈ 17 MB. Varrer tudo
  em memória custa **4–6 ms** por busca. Índice aproximado (FAISS e afins) só se paga uma
  ordem de grandeza acima disso.

## ⚠️ O que a medição NÃO prova

Ela foi feita **dentro de uma cena fechada** — mesma luz, mesmo cenário, mesmo figurino.
Isso é o caso do match cut e da cobertura, e é o caso que o editor pede mais.

**"Ache a Personagem F em outra cena" continua por medir.** Um classificador do ImageNet descreve a
imagem, não a identidade da pessoa; é plausível que o acerto caia muito entre cenários
diferentes. Um app que use isto deve dizer ao usuário o que está entregando — *parecença de
enquadramento e conteúdo* — em vez de prometer reconhecimento de pessoa.

## ⭐⭐ O que este motor NÃO faz: buscar por FRASE — adicionado 2026-09-13

O MobileNetV2 é um classificador usado como extrator: ele transforma **imagem** em vetor e
nada mais. **Não tem codificador de texto.** "Ache um close noturno no consultório" não é uma
busca em que ele vai mal — é uma operação que não existe nele. `confirmado` (por construção).

Consequência no produto que usa este motor: a busca por descrição só alcança o que um modelo
**já decupou**, e a resposta precisa carregar esse tamanho (*"3 mídias decupadas de 23"*) para
"não achei" não virar "o seu material não tem isso".

⇒ Um par **CLIP / SigLIP** (codificador de imagem + codificador de texto treinados juntos)
fecha exatamente esse buraco: a frase vira vetor no mesmo espaço dos quadros, e a busca alcança
o acervo inteiro sem ninguém ter olhado. É a técnica do Premiere 26 e do Resolve 21 — ver
[ia-embarcada-nos-nles.md](ia-embarcada-nos-nles.md).

| pergunta | motor que responde |
|---|---|
| "outro take com este enquadramento" (imagem → imagem) | MobileNetV2 basta — 99%, 14 MB (medido acima) |
| "onde tem X?" sobre material **não decupado** (texto → imagem) | CLIP / SigLIP — ⚠️ acerto `hipotese`, por medir |
| "onde tem X?" com julgamento, texto na imagem, negação | descrição escrita por VLM — só sobre os candidatos |

⚠️ As camadas se somam (*retrieve then rerank*): o vetor de texto acha os 50, a descrição
explica os 5. E medir CLIP pede a mesma higiene do instrumento deste arquivo — a origem fora
do conjunto — mais um gabarito de FRASES, que ainda não existe.

## ⭐⭐ SigLIP 2 na CPU de um notebook de edição — MEDIDO 2026-09-13

`onnx-community/siglip2-base-patch16-256-ONNX`, onnxruntime 1.30 **só CPU**, 4 threads, i7-13650HX,
16 GB, **Media Composer aberto** (segurando 11,3 GB privados). Gabarito: 25 mídias decupadas por
VLM (Haiku 4.5 / qwen3-vl), campos fechados; placar = AUC do melhor quadro de cada mídia.
`_CICLO ASSIST/spikes/busca_por_frase.py`.

| variante | RAM do texto (pico) | imagem | frase | AUC pt | AUC en |
|---|---|---|---|---|---|
| **fp** (imagem fp32 355 MB + texto fp16 539 MB) | ~850 MB (1.049) | 108 ms/quadro | 31 ms | **0,86** | **0,86** |
| imagem int8 + texto fp16 | ~850 MB | 52 ms | 31 ms | 0,73 | 0,72 |
| imagem fp32 + texto int8 | ~430 MB (595) | 117 ms | 16 ms | 0,75 | 0,82 |
| int8 nas duas (90 + 270 MB) | ~430 MB (595) | 53 ms | 16 ms | 0,58 | 0,65 |

- `medido`: a quantização int8 estraga **as duas** metades; só a fp passa. O texto fp16 na CPU
  ocupa ~850 MB (não os 539 do arquivo).
- `medido`: português e inglês empatam (0,86) na fp — o tokenizer Gemma é multilíngue de verdade.
- `inferido`: `local` e `momento` saem ≥ 0,91; `enquadramento=conjunto` fica perto de moeda
  (0,58), classe ambígua até para quem decupou.
- ⚠️ n pequeno (vários atributos com 1–2 positivos) e gabarito de modelo (~10% de erro).
- ⚠️ Os `snapshots\` de um cache HF copiado do macOS são `XSym` de 1.067 bytes: o Windows não
  os segue; os `blobs\` têm o conteúdo.

### Com 172 mídias (2026-09-14) — o número honesto

Mesmo spike, fp, gabarito de 172 mídias decupadas pelo `qwen3-vl:8b` (não por gente):
**AUC 0,79 pt / 0,84 en** (com 25 mídias tinha dado 0,86/0,86 — a amostra pequena inflava).
Por atributo: close 0,94 · detalhe 0,89 (n=3) · interior 0,87/0,94 · exterior 0,93 · geral
0,70 pt / 0,82 en · conjunto 0,65 · médio 0,54 · dia 0,69 · noite 0,72. `medido`: inglês
passa português por ~0,05 com a mesma frase traduzida. 152 ms/quadro, 31 ms/frase.

⛔ `medido`: carregar o codificador de imagem ao lado do Media Composer levou o sistema a
**169 MB livres, 98% de carga** (começou com 601 MB). Num notebook de edição de 16 GB,
SigLIP local disputa a memória com o NLE — foi para um servidor na rede
(`_CICLO ASSIST/servidor_mac/siglip_servidor.py`).

### ⭐⭐ O MESMO modelo num servidor da rede local — MEDIDO 2026-09-14

Mac mini M1 (16 GB) servindo quadro→vetor e frase→vetor por HTTP (`/vetores`, lote de 16
imagens / 32 frases), notebook Windows mandando os JPEG que já tinha em cache. **Mesmo ONNX,
mesmos 1.088 quadros, mesmas 22 frases, mesmo gabarito de 172 mídias.**

| | notebook (CPU, ao lado do MC) | Mac pela rede |
|---|---|---|
| AUC média pt / en | 0,79 / 0,84 | **0,79 / 0,84** (±0,00) |
| tempo por quadro | 152 ms | **66 ms** (1.088 em 72 s) |
| memória no notebook | ⛔ 169 MB livres, carga 98% | ⭐ 43 MB no processo, carga 61% |

- `medido`: **redimensionar com Pillow (servidor) ou com ffmpeg (notebook) NÃO muda o placar.**
  Os vetores diferem (cos 0,976–0,997 em 4 imagens), a AUC não se mexeu, atributo a atributo.
  ⇒ quem manda o quadro não precisa pré-redimensionar para casar com o índice.
- `medido`: a rede local não aparece na conta — 66 ms/quadro pela rede é o mesmo número do Mac
  medindo a si mesmo; o lote de 16 dilui a ida e volta. (Wi-Fi, JPEG de quadro.)
- `medido`: no Mac, SigLIP quente = **1.411 MB** (`footprint`, não RSS — o macOS comprime
  página parada e o RSS mostrava 0,02 GB com o modelo carregado). Com o VLM de 8B quente ao
  lado, a pressão de memória vai a "atenção" (nível 2 de 4), 16–18% livre.
- ⚠️ `pendente`: AUC e tempo com o VLM **realmente ocupado** ao lado (a fila estava parada).
- ⇒ O padrão que se confirma: **o NLE fica com a máquina do editor; percepção pesada vai para
  um servidor da rede**, e o custo de rede é irrelevante ao lado do custo de memória local.

## Onde está a implementação

`_CICLO ASSIST/spikes/busca_visual.py` (a medição) e `cicloassist/midia/vetores.py` (o
produto: vetorizar por master, guardar `vetores.npy`, e a busca).
