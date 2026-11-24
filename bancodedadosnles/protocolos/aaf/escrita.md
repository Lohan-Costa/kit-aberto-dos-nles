# AAF — Escrita (relink e AMA)

Como **escrever** num AAF com pyaaf2 sem quebrar a estrutura. Confiança: `confirmado` (validado
no Media Composer 2021), salvo onde indicado.

---

## 1. Relink de URLString (o caso base)

```python
import aaf2
from pathlib import Path

with aaf2.open(path, 'rw') as f:           # 'rw' ou 'r+' habilitam escrita
    loc['URLString'].value = Path(local_path).as_uri()  # percent-encoded automaticamente
    # f.save() é chamado no __exit__
```

- O setter verifica `writeable`, codifica em **UTF-16LE** e chama `mark_modified()`.
- O writer **só toca** `URLString` dos `SourceMob [ImportDescriptor]`. Selector, CompositionMob
  (AppCode 4/5), Group e todas as referências entre eles **não são tocados** → o Group Clip
  continua funcional com todos os ângulos após o relink.

---

## 2. AMA auto-link (enxertar a essência do original) — `confirmado` (MC 2021, 2026-06-03)

Constantes/AUIDs/caminhos consumíveis: [dados/ama-constantes.json](dados/ama-constantes.json).

### O problema (por que o relink cirúrgico não bastava)
O Avid só **toca** uma mídia AMA quando o **descriptor de essência** (logo abaixo do MasterMob)
descreve o **arquivo real** — com sub-descriptors (MPEG2 vídeo, PCM áudio) e o **UMID do arquivo**.
No relink que só troca `URLString`, esse nível continuava sendo o **proxy** do Avid MediaFiles
(`CDCIDescriptor` → `V01.xxx.mxf`), e a URL do original caía num `ImportDescriptor` enterrado que o
Avid não consulta no AMA. Sintoma:
> *Cannot create the AMA sample mapper to play this clip — **SelectFileMob() failed**.*

### A solução — "enxerto" de essência (`aaf/writer.py::_graft_ama_essence`)
Ativada por `relink_aaf(..., ama_autolink=True)` (default). A peça-chave é o **`create_ama_link`**
do pyaaf2, que lê o cabeçalho do MXF/WAV e gera `MasterMob → SourceMob[essência com UMID real]`.
Para cada MasterMob relinkado:
1. `create_ama_link(original)` → `(MasterMob, SourceMob)`.
2. **Descarta** o MasterMob extra (`f.content['Mobs'].pop(...)`) — mantém o MasterMob ORIGINAL,
   porque a timeline referencia o `mob_id` dele.
3. **Repointa** os SourceClips de cada slot do master para a SourceMob de essência nova
   (picture→picture, sounds→sounds em ordem), preservando `mob_id`, `slot_id`, `start`, `length`.
4. Corrige a `URLString` para o **formato Avid** (nome do volume como raiz, percent-encoded —
   `path_to_aaf_url`; o `create_ama_link` grava `file:///Volumes/…` cru, que **quebra** o AMA) e
   seta o `MediaContainerGUID`.
5. Marca o master com `_IMPORTED_AMA = 1`.

**Format-aware** (`_build_ama_source`): MXF linka direto; QuickTime `.mov/.mp4`, WAV passam por
`ffprobe` (`_ffprobe_meta`) → `create_ama_link` com metadata; `MediaContainerGUID` por tipo.

### Patches necessários no pyaaf2 1.7.1
- **`MXFMPEG2VideoDescriptor.link`**: `NameError` (usa `d` antes de existir), estoura em qualquer
  MXF XDCAM. Fix: setar `ResolutionID` e delegar ao `link` do pai (CDCI). ⚠️ Hardcode `4076`
  (XDCAM HD 50Mbit) — derivar do header no rewrite.
- **ContainerDef "AAFKLV"**: `create_ama_link` faz `lookup_containerdef("AAFKLV")`, mas o AAF do
  Avid registra essa def (mesma AUID) com o **nome "MXF"** → lookup por nome falha. Fix: renomear a
  def existente (referências são por AUID; nome é só rótulo).

### Limite ~~intransponível~~ + fluxo aceito
Auto-link **100% sem toque é inviável**: o Avid mantém o `amaMMOB.mdb` (AMA Management) que **só ele
cria**. Fluxo final validado: app gera a pasta de atalhos/symlinks (`stage_media`) → editor
**AMA-linka a pasta uma vez** → clipes ficam online por **identidade de UMID**, sem Relink manual.
⚠️ Apagar a pasta `AMA Management` com o Avid **aberto** contamina o estado — limpar só com ele fechado.

> **CORRIGE (2026-08-10, De Lá Pra Cá — MC):** o limite acima vale para quem está **FORA** do Avid.
> **Dentro dele, ele cai.** `LinkFile` (mcapi) faz o **próprio Avid** criar o AMA Management e o
> `amaMMOB.mdb` — a peça que só ele sabe criar passa a ser criada por ele, a pedido. Com os masters
> AMA já online, um AAF cujos MobIDs apontem para eles importa **online**, e **quem monta a timeline
> é o Media Composer** (efeitos, transições, timewarp e estabilizadores intactos por construção).
>
> Fluxo validado em escala (100 masters, 1121 segmentos, 0 falhas):
> `LinkFile(originais)` → `DoCommand(1004 Save)` → achatar + remapear MobID no AAF → `ImportFile`.
>
> A frase original **não estava errada** — estava condicionada a um contexto que o texto não dizia.
> Ver `plugins/avid-panel-sdk/dados/mcapi-grpc.json` → `ImportFile_aceita_AAF`.

### Pendências (`pendente`)
- Auto-link de QuickTime/`.mov` no MC 2021 ainda não validado (MXF sim).
- Derivar `ResolutionID` do header para MPEG2 de outras taxas.

Detalhe completo: `RELINKER/docs/ama-autolink.md`. Ver também a geração de AAF do zero em
[geracao.md](geracao.md) (mesma função `create_ama_link`, mesmo princípio de MobID).

---

## 3. Export para outras NLEs (saídas adicionais)

O AAF do Avid é a saída primária; o RELINKER também escreve:
- **OTIO** (`.otio`) — baseline aberto, fidelidade limitada (ver [../otio/](../otio/)).
- **DRT/DRP** (Resolve) — engenharia reversa premium (ver [../drt-drp/](../drt-drp/)).

A camada de export é agnóstica: `Segment[]` → modelo de timeline intermediário → writer por NLE.

## Trocar `mob_id` re-chaveia `f.content.mobs` — `confirmado` (pyaaf2, SANITIZADOR_DE_AAF 2026-08-20)

`f.content.mobs` do pyaaf2 é chaveado por MobID. Atribuir `mob.mob_id = MobID.new()` **re-chaveia o
dicionário**, e iterar sobre ele enquanto isso acontece levanta
`RuntimeError: dictionary keys changed during iteration`. Sempre materializar a lista antes:
`for mob in list(f.content.mobs): ...`. Custou uma execução falha. O caso de uso (desfazer colisão
de MobID herdado do UMID do MXF) está em
[../mxf/codecs-proprietarios.md](../mxf/codecs-proprietarios.md) §"sanitizar o AAF".
