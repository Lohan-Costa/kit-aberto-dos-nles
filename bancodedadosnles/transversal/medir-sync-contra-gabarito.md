# Medir sync contra gabarito — a bin do editor como instrumento

> Como transformar uma timeline montada à mão num **instrumento de medição** para um
> motor de sincronia. Método, não formato: vale para qualquer app que pareie mídia e
> precise saber se está melhorando ou piorando.
>
> **Confiança:** `confirmado`. Medido em 2026-08-22/23 no Órbita (DRAMASYNC), MC 25.6 /
> Windows 11, com três diárias reais de *PRODUCAO-A* e *PRODE* sincronizadas à mão pelo
> editor.

---

## 1. ⭐⭐ Por que isto existe: o custo de NÃO ter régua

Numa única sessão, sem instrumento, foram propostos **quatro** consertos para o mesmo
defeito de pareamento. **Três foram revertidos**, e cada um parecia sólido no papel:

| tentativa | raciocínio | o que a medição mostrou |
|---|---|---|
| alargar o alcance da âncora de relógio | "sem âncora perto, use a do dia" | clipes a **5h57** do lugar, agora com `sync_source: timecode` e **sem aviso** — erro marcado virou erro confiante |
| desfazer o par sem apoio | "confiança 1,02 é ruído com cara de dado" | a diária caiu de **34 tomadas para 23**; 11 pareamentos CORRETOS foram apagados |
| alargar a lista de candidatos (25%) | "dê mais opções à correlação" | placar idêntico: consertou um clipe e quebrou outro |

⚠️ **A segunda só foi descoberta porque o autor abriu uma versão ANTERIOR do app,
instalada, e comparou a olho.** Sem isso, uma regressão grave teria sido commitada como
melhoria.

⭐ **Lição de método, antes de qualquer detalhe técnico:** antes de "melhorar" um motor
que já funcionou, **rode a versão que funcionava no mesmo material e guarde o número
como linha de base**. Uma versão instalada de meses atrás é uma régua legítima.

---

## 2. Por que a BIN, e não um XML

O Media Composer **não exporta XML de timeline**. Mas exporta a si mesmo: a `.avb`
carrega a sequência inteira, com as trilhas e os MobIDs. (Sobre ler a bin em vez do AAF
exportado, ver [../protocolos/avb/dados/ler-timeline-sem-aaf.json](../protocolos/avb/dados/ler-timeline-sem-aaf.json).)

⭐ **E a pergunta certa muda conforme o NLE.** Palavras do editor, ao entregar o
gabarito:

> *"Não se prenda muito à relação do TC entre os arquivos, pois vários eu desloquei pra
> frente ou pra trás para casar com o sync. Observe mais a ORDEM dos arquivos e qual
> vídeo casa com qual áudio."*

Ou seja: numa timeline montada à mão, **a posição absoluta é arrumação; o pareamento é
julgamento**. Medir posição contra uma bin manual mede o hábito do editor; medir
**quem casa com quem** mede o motor.

---

## 3. Como extrair a verdade da bin

O empilhamento é a resposta: o som direto de um clipe é o que ocupa o mesmo trecho da
timeline que ele.

```
para cada SourceClip de vídeo (início, fim):
    os blocos de som que se sobrepõem  →  o par
```

Três armadilhas, todas encontradas na prática:

### ⚠️ 3a. O áudio da PRÓPRIA CÂMERA aparece nas trilhas de som

Ele tem o mesmo nome do vídeo. Contá-lo faz **todo** clipe parecer sincronizado.
Descartar comparando o nome.

### ⚠️ 3b. Uma bin pode guardar VÁRIAS diárias

O editor reuniu três numa bin só (`SYNC MANUAL - GABARITO.avb`, uma `CompositionMob` por
diária). Isso é bom — o conjunto de referência anda junto —, mas a ferramenta tem de
**escolher pelo nome e, sem indicação, listar o que achou em vez de pegar a primeira**.

⭐ E é bom por um motivo que passa despercebido: **com UM gabarito só, ajustar limiar até
aquele material passar é ajuste ao caso, não conserto.** Três diárias transformam
"melhorou" em "melhorou sem quebrar as outras duas".

### ⚠️⚠️ 3c. Case e nome de arquivo NÃO servem de chave

Duas medições foram invalidadas pelo instrumento, não pelo motor:

- **caixa:** o mesmo material é `A005_03180050_C001.mp4` no disco e
  `a005_03180050_C001` como masterclipe. Comparar cru fez **35 de 37 clipes** parecerem
  erro. (O `caminhos-e-storage-producao.md` §1 já avisava: comparação de nome é
  case-insensitive, **sempre**.)
- **nome de hash:** em mídia gerenciada o arquivo às vezes é `V01.E69CCF0F….mxf`, sem
  relação com o clipe — e aí casar por nome devolve **0/13 com cara de motor quebrado**.
  Pelo MobID: **13/13**.

⭐ **A chave é o MobID.** O nome serve quando o Avid nomeia a mídia como o clipe, e
falha quando não nomeia — e as duas convenções convivem no MESMO volume (ver
[../protocolos/mxf/README.md](../protocolos/mxf/README.md)).

⚠️ Ao converter MobID, **tire o prefixo `urn:smpte:umid:` ANTES**: um conversor que
filtre dígitos hexadecimais da string inteira colhe o `e` de *smpte* e o `d` de *umid* —
64 dígitos viram 66 e a conversão recusa. Custou uma rodada.

---

## 4. ⭐⭐ O número que importa não é o acerto

É a **honestidade do aviso**. Um motor que erra 3 e sinaliza os 3 é utilizável — o
editor sabe onde olhar. Um que erra 1 em silêncio é pior, porque ensina a confiar no que
não dá.

Daí a matriz:

```
                  sinalizado    calado
  acertou            12          22      ← aviso em clipe CERTO dilui o aviso
  ERROU               1           0      ← o calado é o veneno
```

**Dois números, não um.** O quadrante `errou+calado` é o que se persegue até zerar; o
`acertou+sinalizado` é o custo escondido — o editor que confere 13 para achar 1 aprende a
não conferir nenhum.

Resultado final das três diárias, depois dos consertos: **13/13, 25/26 e 35/37, com ZERO
erros calados nas três.**

---

## 5. ⭐ O que a régua achou, e que nenhuma teoria tinha achado

O último erro silencioso não era "correlação fraca" nem "candidato de menos". Era um
**empate**:

```
sob o mesmo Δ de relógio, para o mesmo clipe de câmera:
    som A   sobrepõe 201,8 s
    som B   sobrepõe 201,8 s      ← empate EXATO
```

O código guardava o de maior sobreposição com `if overlap > melhor`. **Num empate, `>` é
falso — fica o primeiro da lista.** A escolha era a ORDEM DOS ARQUIVOS, não uma medida. E
a correlação de forma de onda, quando enfim consultada, separava os dois com folga
(**5,28 contra 1,13**).

⭐⭐ **A lição que fecha o ciclo:** as três tentativas fracassadas partiam de uma teoria
sobre *por que o julgamento erra*. A que funcionou começou pela pergunta mais burra —
**quais opções foram postas à mesa, e com que números?** A resposta (dois valores
idênticos) não precisava de teoria nenhuma.

*Antes de teorizar sobre o julgamento, olhe as opções postas à mesa.*

---

## 6. Cross-ref

- Ler a lista de edição pela bin, nunca por AAF exportado:
  [../protocolos/avb/dados/ler-timeline-sem-aaf.json](../protocolos/avb/dados/ler-timeline-sem-aaf.json)
- Nomenclatura e duração da mídia gerenciada:
  [../protocolos/mxf/README.md](../protocolos/mxf/README.md)
- Comparação de nome/caminho (case, NFC, percent-encoding):
  [caminhos-e-storage-producao.md](caminhos-e-storage-producao.md) §1
- Como medir cache sem se enganar (a régua do processo frio):
  [banco-de-midias-compartilhado.md](banco-de-midias-compartilhado.md) §3
- Implementação de referência: `DRAMASYNC/src-python/tools/gabarito_avb.py`
  (o irmão `gabarito.py` mede POSIÇÃO a partir de XML do Premiere).
