# Metadado de canal do som direto — onde vive, e as quatro condições em que ele chega

> Quem precisa saber **quem é cada canal** de um WAV/OP-Atom multipista: atribuição de falante,
> aparo por voz, mapa personagem→canal. Levantado no **Assist anterior**, 2026-09-02, varrendo o
> projeto Avid inteiro do autor: **18 bins, 517 masters de som**, quatro produções diferentes.
>
> Complementa [decupagem-por-transcricao.md](decupagem-por-transcricao.md) (o que fazer com a
> transcrição) e [../protocolos/msm/pmr-fmid.md](../protocolos/msm/pmr-fmid.md) (como achar o
> arquivo). Aqui é a pergunta do meio: **achei o arquivo, mas de quem é cada canal?**

## 1. Onde o nome do canal mora numa `.avb` — `confirmado`

⛔⛔ **Não é atributo do master nem da trilha.** As colunas de bin vivem dentro do atributo
`_USER`, que é um container aninhado. Um leitor que olhe `mob.attributes` direto vê só
`_COLOR_*`, `_GEN`, `_ORG_BIN`, `_USER` e conclui, errado, que a bin não tem metadado.

```python
import avb
from avb_bin.percurso import e_master

with avb.open(caminho_avb) as f:                    # ⚠️ leitura preguiçosa: tudo DENTRO do with
    for m in f.content.mobs:
        if not e_master(m):
            continue
        u = dict(dict(m.attributes or {}).get("_USER") or {})
        trk = {k: str(v or "") for k, v in u.items() if str(k).upper().startswith("TRK")}
        # {'TRK1': 'MixL', 'TRK2': 'MixR', 'TRK3': 'BOOM 1', 'TRK4': 'PESSOA-H', ...}
```

⭐ **E elas sobrevivem à mídia gerenciada.** A coluna é da BIN; o OP-Atom não tem nada disso
(§4). Um app que leia a bin sabe o papel do canal sem tocar em mídia nenhuma.

⚠️ A trilha (`mob.tracks[i]`) **não** carrega nome: `track.name` é `None` em todas as 517
amostras. O que houve foi `AudioMixerCompSolo`/`AudioMixerCompMute` em uma bin — estado do
mixer, não identidade.

## 2. As quatro condições, com contagem real — `confirmado`

| condição | onde, no acervo medido | o que existe | o que a atribuição consegue |
|---|---|---|---|
| **A · nome completo, mixagem nomeada** | `PRODUCAO-F/SOM DIRETO` **51/51** | `MixL · MixR · BOOM 1 · BOOM 2 · PESSOA-H · DITO · STEREO MS L/R` | tudo: mistura e boom fora da disputa, e as pessoas vêm com o **nome do personagem** |
| **B · nome parcial, 1-2 vazios** | `D03 SOM` **36/36** · `PRODE` **36/73** | `TRK1='' TRK2='' TRK3=MIC2 TRK4=MIC3 TRK5=BOOM` | funciona: vazias viram `sem-nome` e não disputam; duas lapelas dão a margem |
| **C · sem nome, com mapa do app** | `C04` 15/31 · `C07` 9/19 · `D02_SOM` **24/24** | zero `TRK`; coluna própria `GA Personagem = "MIC2=Personagem F; MIC3=Eduardo"` | ⚠️ **o mapa aponta para nomes que a bin não tem** — só fecha se houver outra fonte para o nome |
| **D · nada** | `D01_SOM` 0/5 · `D04_SOM` 0/20 · `PRODE 2` 0/50 · `PRODE 3` 0/46 | nada | `não avaliado`, e é a resposta certa |

⭐⭐ **A condição C é uma armadilha de projeto, não de formato.** Um app que grave o mapa
personagem→canal **por NOME de trilha** cria uma referência pendurada: quando a bin não tem
`TRK`, o mapa existe e não ancora em nada. ⇒ **grave também a POSIÇÃO** (`TRK4` → índice 4), que
é o que sempre existe.

## 3. Três variações que quebram suposições — `confirmado`

**3a. A posição NÃO diz o papel.** Prova documental, mesma diária e mesmo técnico de som
(`PRODUCAO-F/SOM DIRETO`, 51 masters):

```
19 takes:  TRK3=BOOM 2   TRK4=BOOM 1   TRK5=PESSOA-H   TRK6=DITO
 8 takes:  TRK3=BOOM 1
 7 takes:  TRK3=BOOM 1   TRK4=STEREO MS L   TRK5=STEREO MS R
```

O canal 3 é `BOOM 2` num take e `BOOM 1` noutro; o canal 4 é `BOOM 1` num e metade de um par
mid-side noutro. ⛔ **Qualquer regra do tipo "1-2 é a mixagem, o resto são os mics" está errada**
— a ordem é escolha do técnico e muda dentro da mesma diária. (Dito pelo editor antes de a
varredura confirmar: *"essa ordem varia de acordo com o técnico de som e condição do material"*.)

**3b. O número de canais varia DENTRO da mesma bin.** `PRODUCAO-F`: 3ch×8, 5ch×9, **6ch×27**,
7ch×7. `PRODE 3`: 2, 3, 4 e 5. `D04_SOM`: 3, 4 e 5. ⇒ nada de assumir largura fixa; é por master.

**3c. Metade de uma bin pode ter nome e a outra metade não.** `PRODE/_ASSIST ANTERIOR`: 36 de 73.
⇒ a estratégia se decide **por master**, nunca por bin.

## 4. O OP-Atom não carrega o papel — `confirmado` (ffprobe, 2026-09-02)

```
TAG:file_package_name = PRODUCAO-A - 05-04 C7 P1-T001
TAG:track_name        = PRODUCAO-A - 05-04 C7 P1-T001_A01     ← só a POSIÇÃO
```

Um OP-Atom de som é **mono** (`pcm_s24le`, 48 kHz, `channels=1`), um arquivo por canal, e o
`track_name` é o nome do master mais o sufixo `_A0x`. **Não há iXML, não há papel.** ⇒ na mídia
gerenciada, a identidade do canal só pode vir da bin (§1) ou do editor.

⭐ De brinde: o header de um OP-Atom lista os `file_package_umid` **dos outros canais do mesmo
clipe** (streams com `data_type=audio` e `codec_name=unknown`). Dá para descobrir o conjunto a
partir de um arquivo só — embora o `.pmr` já responda isso mais barato.

## 5. Custo de transcrever POR CANAL — `confirmado` (2026-09-02)

Máquina: i7-13650HX + **RTX 4050 6 GB**, whisper.cpp cuBLAS, `large-v3-turbo`, VAD silero.

```
custo marginal ... 1,6 s por MINUTO de áudio   (fator 0,03× — ~37× o tempo real)
carga do modelo .. ~1,7 s, uma vez por processo

take de 4 min × 1 canal ....  6,4 s      cena de 10 takes × 4 min, mixagem ..  1,1 min
take de 4 min × 5 canais ... 32,2 s      cena de 10 takes × 4 min, 5 canais .  5,4 min
```

⭐⭐ **Transcrever canal a canal é viável**, e era o que se supunha proibitivo. Comparação no
mesmo take (`D03`, `C14 P2/006`, 120 s, 5 canais):

| | mixagem dos 5 (`ffmpeg -ac 1`) | canal a canal |
|---|---|---|
| tempo | 3,4 s | 14,1 s (**4,1×**) |
| deixas | 5 blocos longos | 28 (com repetição entre canais) |
| **quem falou** | ✗ | ⭐ *"Olha aqui, chegou a sentença"* aparece **só no A04** ⇒ é o ator do `MIC3` |
| granularidade | 5 blocos | o A02 quebrou em 14, separando *"Ação"* e *"Volta, volta, volta"* — **direção, não diálogo** |
| perda | *"Boa, cheguei"* (A03) e *"Mortou, temos o direito"* (A05) não entraram | — |

⚠️ **A mixagem NÃO perdeu o miolo neste take** — trouxe as 5 falas, inclusive a do canal
isolado. O ganho do canal a canal aqui **não é mais texto, é atribuição e granularidade**. Quem
esperar "a mistura come falas" vai medir e não achar; o que ela come é **quem falou** e as
bordas.

## 6. ⛔ O detector de canal problemático NÃO está resolvido — `hipotese`

Perseguindo um relato do editor (*"um microfone pode perder o sinal ou, pior, gerar ruído de
interferência"*), medimos por canal: RMS, fator de crista, fração de janelas de 20 ms abaixo de
10% do RMS do próprio canal ("silêncio"), e correlação com a **soma dos outros**.

Um canal se destacou em 6 de 6 takes — `MIC3`: correlação **0,08–0,28** contra 0,5–0,93 dos
outros, silêncio **0,00**, crista 38 e 30 contra 11–14. Parecia a assinatura do defeito.

⛔⛔ **E não era.** Transcrito, o `MIC3` entrega fala limpa: *"Olha aqui, chegou a sentença,
vamos cumprir, já podemos subir"*. Era a **lapela de um ator distante do boom** — a voz dele não
chega aos outros microfones, então não correlaciona; e o piso de ruído baixo faz o "silêncio"
relativo dar zero.

⭐ **A lição:** os mesmos números medem *"este canal ouve OUTRA coisa"* — que é exatamente o que
a atribuição quer — e **não** distinguem sozinhos *mic com defeito* de *ator afastado*. Separar
os dois exige o conteúdo (há fala inteligível ali?), não a estatística. E, no acervo medido,
**não foi achado um take com interferência real** para calibrar: fica `pendente`.

⭐ Achado lateral, esse sim inequívoco: em `D03/FOLLY` o canal **A02 está mudo** (RMS 0,0,
silêncio 1,00, correlação 0,000) nos 6 takes. Canal mudo é trivial de detectar; canal ruidoso
não.

## 6b. ⛔⛔ Quatro estatísticas que NÃO separam lapela de boom — `confirmado` (2026-09-03)

Perseguindo *"quais canais são pessoas?"* sem coluna `TRK`, quatro medidas foram rodadas
sobre a **mídia gerenciada** (OP-Atom → proxy multipista), contra os dois gabaritos mais
limpos do acervo: `D03 SOM` (36/36 com `TRK`) e `PRODUCAO-F/SOM DIRETO` (51/51 com nome).
**Nenhuma serve sozinha.** Registradas para ninguém repetir.

| medida | como | veredito |
|---|---|---|
| **cobertura** — fração das janelas com voz em que o canal está ativo (janela de 0,5 s, limiar a meia faixa dinâmica própria) | ⛔ não separa: `BOOM` 0,47–0,70 × `MIC3` 0,58–0,80. A lapela capta o outro ator alto o bastante para "estar ativa" quase sempre |
| **dominância bruta** — fração das janelas em que o canal é o mais alto | ⛔ acha a mistura, mas é **artefato de ganho**: na D03 o boom entra 20 dB acima das lapelas por escolha do técnico. Muda a mesa, muda o veredito |
| **R² da regressão múltipla** — "este canal é combinação linear dos outros?" | ⛔⛔ **degenerado**: quando um canal é a soma exata de outros dois (`TRK2 = MIC2 + MIC3`), o conjunto fica deficiente de posto e **todo** canal vira combinação dos demais. Deu `1,000` para os cinco, lapelas inclusive |
| ⭐ **dominância exclusiva** — lidera por ≥3 dB **depois de normalizar cada canal pelo próprio p95** | ordena certo, e **não tem corte absoluto**: `PESSOA-H` 0,54–0,63 · `MIC3` 0,13–0,38 · `MIC2` **0,00–0,05** · boom numa tomada **sem lapela** 0,29. Não há limiar entre 0,05 e 0,29 que guarde o `MIC2` e recuse o boom |

⚠️ **A correlação de amostra (60 s) também já havia falhado**, por outra razão e de forma
instrutiva: ela acha a **mistura** (soma linear dos outros: 0,54 e 0,85 contra as duas
lapelas) e **não acha o boom** (caminho acústico independente: 0,00–0,06). Quem esperar
que "o canal que ouve todo mundo correlaciona com todo mundo" mede e não acha.

⭐⭐ **A assimetria que decide o projeto:** classificar uma lapela como não-pessoa perde
**um** personagem; classificar a mistura como pessoa perde **todos** — ela é a mais alta
em quase toda janela e resolveria a cena inteira para um falante só. ⇒ um detector que
erra "para menos" ainda é inaceitável, porque o `MIC2` é exatamente quem ele perde.

⇒ **Confirma o §6 por outro caminho:** *separar os dois exige o conteúdo, não a
estatística*. O desenho que sobra é o do `falas/ilhas.py` do Assist anterior — **a
estatística levanta a suspeita, o ASR dá o veredito** —, sustentado pelo custo medido no
§5 (1,6 s por minuto de áudio por canal).

## 6c. Duas surpresas do material, achadas medindo — `confirmado` (2026-09-03)

Na `D03 SOM.avb`, cujas colunas dizem `TRK1='' TRK2='' TRK3=MIC2 TRK4=MIC3 TRK5=BOOM`:

```
corr(A01, A05) = 1,000   ⇒ TRK1 e' COPIA BIT A BIT do BOOM, com 3 dB (√2) de diferenca
corr(A02, MIC3) = 0,854
corr(A02, MIC2) = 0,535  ⇒ TRK2 e' a MISTURA das duas lapelas
```

⇒ O gravador escreveu o **barramento L/R** nas duas primeiras trilhas, e o L dele é só o
boom. ⛔ Duas consequências para quem lê metadado de canal:

1. **Trilha sem nome não é uma coisa só.** O §2 já dizia que `''` não é pessoa; aqui `''`
   é *cópia do boom* num canal e *mistura* no outro, **na mesma tomada**. Tratar as duas
   igual é perder a informação que existe.
2. ⭐ **Canal duplicado é trivial de achar e vale a pena achar** — `corr = 1,000` não tem
   ambiguidade —, e um canal redundante na atribuição é ruído puro: ele empata com o
   original dentro de qualquer margem.

## 7. O vocabulário de papéis dá conta do acervo — `confirmado`

Os **11 nomes reais** que o projeto inteiro contém, classificados por
`assist_anterior/som/canais.py` (papéis técnicos são fechados; **o que não é nenhum deles é uma
pessoa**):

```
MixL, MixR ............... mistura      BOOM, BOOM 1, BOOM 2 ..... boom
STEREO MS L, STEREO MS R . ambiente     PESSOA-H, DITO, MIC2, MIC3 ... pessoa
'' (vazio) ............... sem-nome
```

⚠️ `sem-nome` **não é pessoa**: na `D02` as duas sem nome são a mixagem. Classificar a mistura
como pessoa é o defeito de origem — ela contém todas as vozes.

## 8. ⭐⭐ Quem fala, pela lapela: NORMALIZAR cada canal pelo próprio nível — `confirmado` (n = 1 take, 2026-11-06)

Ciclo Assist (`cicloassist/midia/falantes.py`), take `PRODUCAO-A C4 P4-T003` (BWF 5 canais; iXML interleave 1–2
sem nome = mixdown, 3 = MIC2, 4 = MIC3, 5 = BOOM), transcrição da mixagem (21 falas), gabarito = o "Separar falas
sobrepostas" do Premiere 27.1 (`ia-embarcada-nos-nles.md` §3e).

| regra | equipe ("Cena 4…", "Ação", "Cortou") | atores | concordância com a Adobe |
|---|---|---|---|
| lapela mais alta em **dBFS cru**, margem 3 dB (a do Assist anterior) | "MIC2 por 5–8 dB" ⛔ | resolvidos | 10 de 19 |
| ⭐ **cada canal menos o PRÓPRIO p95** do take, margem 3 dB | **ambígua, 0–3 dB** | resolvidos por **9–21 dB** | **9 de 11** |

⇒ O ganho da mesa (aqui a MIC2 ~8 dB acima da MIC3) decide a fala da equipe no cru; normalizado, a equipe — que
chega parecida em todas as lapelas — empata, que é o que o Assist anterior mediu na D02 (equipe 0–3 dB). É a
"dominância exclusiva" do §6b aplicada à fala inteira.
⚠️ O preço: uma lapela cujo ator NÃO fala no take tem o p95 feito de vazamento e "sobe" até empatar ⇒ ambígua (falha
segura). ⚠️ A margem de 3 dB continua não calibrada contra verdade-terreno.

## O que NÃO foi feito

- **Mic com defeito real não foi medido** (§6). O detector separa "ouve outra coisa" de
  "redundante"; para "quebrado" falta amostra.
- **Nada foi escrito em bin.** Toda a varredura é leitura.
- **Não se mediu material de outra casa.** São quatro produções, todas do mesmo autor e com dois
  fluxos de importação (direto e via Resolve). A distribuição das quatro condições **não é
  estatística de mercado** — é a prova de que as quatro existem.
- **A coluna `GA Personagem` é do Assist anterior**, não uma convenção do Avid. Aparece aqui porque
  ilustra a armadilha da referência pendurada (§2C).
- **Não se testou escrever `TRK` de volta** na bin — se o MC aceita a coluna vinda de fora é
  `pendente`.

## 7a. Cena, plano e take: bext × iXML × nome (2026-11-08, Zoom F8 e dois projetos novos)

> **CORRIGE (2026-11-08) o fim do §7**, que dizia que o F8 não traz plano e que "cena e plano só estão no nome". Aquilo olhou só o `bext`
> (o que o ffprobe mostra). No `PRODUCAO-A` (D02, Zoom F8, 3 WAV abertos) o **iXML** traz `SCENE = PRODUCAO-A - 05-04 C4 P1` e `TAKE = 001`,
> enquanto o `bext` traz só `SCENE = PRODUCAO-A - 05-04`. Dois campos com o mesmo nome e valores diferentes no mesmo arquivo.

Medido em `D:\AUDIOS ANALISAR` (Sound Devices, iXML e bext iguais nos 96 WAV), `confirmado`:
- `PRODUCAO_B` (43): nome `18-1T01`, `SCENE = 18-1`. Formas: `#-#` 31 · `#B-#-#` 6 · `#-EXTRA` 2 · `#B-#` 2 · `#-#-#` 2.
- `Diaria 03` (53): nome `E3C2P1T01`, `SCENE = E3C2P1`. Formas: `E#C#P#` 43 · `E#C#ctP#` 9 (`ct`: sentido não confirmado).
- Em 95 de 95 da raiz, nome = `SCENE` + `T` + `TAKE`. ⚠️ Pasta de descarte real: `FALSETAKES` (sem espaço), que `claquete.PASTAS_DE_DESCARTE` não conhece.

Aplicado (autor, 2026-11-08): `E#C#P#T#` lido com o episódio em campo próprio (`ct` guardado como está: o autor não sabe o que é, e o motor não interpreta);
`FALSETAKES` é descarte; `número-número` só se separa em cena e plano quando pelo menos 2/3 das tomadas da diária têm essa forma, marcado como presumido
(`identidade.presumir_da_forma`, `convencao = "forma_da_diaria"`). `hipotese`: que `18-1` seja cena-plano; a regra vem de uma diária só.

**Regra de leitura proposta por modelo (2026-11-08, Ciclo Assist, Sonnet 5.5, PRODUCAO_B, 43 WAV), `confirmado` numa rodada:** conferir só contra o metadado não basta. Sem saber o plano, o modelo propôs
`{cena}-#T{take}`: o take bate em 100% com o iXML, e mesmo assim `18-1T01` e `18-2T01` virariam a mesma tomada. A conferência precisa procurar **colisão de identidade** entre arquivos diferentes (canais mono do mesmo take não contam).
E uma regra feita sobre o nome do arquivo precisa aceitar `/` no lugar do RÓTULO do take para valer no master do MC (`SCENE/TAKE`, `protocolos/avb/estruturas.md`): só o rótulo, porque o resto é a SCENE (`18-EXTRAT01` lá é `18-EXTRA/01`). `pendente` conferir numa bin real.

## 7. O take gravado em WAVs mono separados (2026-11-08, Ciclo Assist, módulo Sincronizar)

⛔ **Medido** (motor `sync/engine.py`, sintético: câmera 25p + dois WAV mono com o mesmo `time_reference`, método timecode):
sem tratamento, o 1º canal casa com a câmera (quadro 0) e o 2º sai órfão **depois** dele (quadro 100, o fim do 1º): o motor
resolve sobreposição dentro da fonte, e dois canais do mesmo take se sobrepõem por natureza. No Media Composer o `avid/adapter.py`
punha todos os sons na mesma trilha. **Confiança:** `confirmado` no motor; a montagem no NLE com o conserto é `pendente`.

**O critério adotado** (`modulos/sincronizar/servidor/fichas.py`): um canal cada, mesmo TC e mesma duração, dois ou mais; com TC
zerado o nome também tem de bater (sem o número final). **O conserto:** só o 1º canal entra no sync; os outros voltam ao mapa na
posição dele, um por trilha. ⚠️ Eles voltam como sons sem câmera: o merged clip do Premiere (que itera as tomadas) leva só o 1º.

**Gravador real sem o campo Plano** (Zoom F8, `PRODUCAO-A - 05-04 C4 P4-T003.WAV`, ffprobe): as tags trazem `SCENE`, `TAKE`,
`TAPE`, `CIRCLED`, `NOTE`, sem plano, e o `SCENE` guarda o nome da produção e da diária, não a cena. Cena e plano só estão
no nome do arquivo. ⇒ Quem lê cena, plano e take é o NOME, por `media/claquete.py` (rótulo + número, os três obrigatórios): tags só quando o nome
não casa. Em 2026-11-08 o vocabulário ganhou `SCENE`, `SHOT` e `SH` a pedido do autor, ainda `hipotese`: sem material real de outra produção que os use.
