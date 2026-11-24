# PRPROJ — Áudio com canais adaptativos (crítico)

Confiança `inferido`. Fonte: `DRAMASYNC/docs/reverse-engineering/premiere-multicam-prproj.md` §7.

## Por que importa

Se a Multicam Source Sequence **não** usar tracks de áudio com `ChannelType=1` (adaptive), ao
aninhar a sequência em outra timeline o áudio vem como **um único bloco "nest"** indesmontável —
o departamento de sonorização não acessa os canais individuais. Por isso o áudio adaptativo é
requisito, não detalhe.

## Requisito para 2 canais de som direto (WAV stereo)

- 2 `AudioClipTrack` com `ChannelType=1, SubType=1, Assign=1`, ambas `MZ.TrackTargeted=1`.
- `NumAdaptiveChannels=2` no `AudioTrackGroup` (governa o roteamento real).
- Cada clip com `SecondaryIndex`/`OrigChGrp` para selecionar o canal correto do WAV.

## Cadeia por canal do WAV (N = 0 ou 1)

```
AudioClipTrackItem → SubClip → AudioClip → AudioMediaSource → Media
                                   ↑ SecondaryContent (ChannelIndex=N)
```

O `AudioMediaSource` é o **mesmo objeto** (mesmo ObjectID) para os dois canais do mesmo WAV.
`SecondaryContent` mapeia o `AudioClip` ao canal N (`<ChannelIndex>N</ChannelIndex>`).

### Campos diferenciadores por canal

| Objeto | Campo | Canal 0 (A1) | Canal 1 (A2) |
|--------|-------|-------------|-------------|
| AudioClipTrack | `MZ.SourceTrackNumber` | `0` | `-1` |
| AudioClipTrack | `ID` | `2` | `3` |
| AudioClipTrack | `Index` | `0` | `1` |
| SubClip | `OrigChGrp` | `0` | `1` |
| AudioClip | `SecondaryIndex` | ausente | `1` |
| SecondaryContent | `ChannelIndex` | `0` | `1` |

## Effects chain da track (não do clip)

Cada `AudioClipTrack` tem `AudioTrack` com `ComponentOwner → AudioComponentChain` contendo
`AudioFader` + `AudioMeter`, mais um `Panner` (`StereoTo16ChannelPanProcessor`):

- `AudioChannelLayout` da track adaptativa de 2 canais: `[{"channellabel":100},{"channellabel":101}]`
  (100=L, 101=R). No **clip** o layout é mono (`[{"channellabel":0}]`, `ChannelType=0`).
- Panner: `Matrix=[[0,[0]],[1,[1]]]` (pass-through ch0→out0, ch1→out1); `OutputAudioChannelLayout`
  com 16 entradas de 0.
- `NextPannerID = 4294967277` (0xFFFFFFED, constante).

## MasterClip da sequência: 32 canais fixos

O `AudioClip` do MasterClip que representa a multicam no bin aponta para `AudioSequenceSource`
(não `AudioMediaSource`) e tem **exatamente 32 `SecondaryContent`** (ChannelIndex 0–31) —
estrutura fixa, independente do número real de canais. O `NumAdaptiveChannels=2` do
`AudioTrackGroup` é que governa o roteamento real.

ClassIDs de áudio: ver [dados/classids.json](dados/classids.json) (`componentes_av`).

## Mais de 2 canais — multicanal adaptativo (som direto de 5 canais)

Confiança `inferido` (lido de multicam NATIVA do Premiere, criada por *Create Multi-Camera
Source Sequence*; reproduzido byte-a-byte no builder — mas ver o BUG ABERTO abaixo, que
persistiu). Fonte: Órbita/DRAMASYNC 2026-07-18 (`.dev/reverse-engineering/…` §14).

Para N>2 canais o desenho MUDA em relação ao estéreo acima:

- **Master track (`AudioMixTrack`)**: `ChannelType=3` (adaptativo, não 1), e o
  `AudioChannelLayout` do fader/meter/chain/panner/inlet é de **32 canais discretos**
  `[{"channellabel":0}]×32`. O panner da master é `DefaultPanProcessor` com
  `Component.ID=4294967280`, `DefaultPannerInputChannelType=3`, `DefaultPannerOutputChannelType=3`;
  o `AudioTrack.NextPannerID=4294967279`. (Os 32 são o teto do barramento; `NumAdaptiveChannels`
  diz quantos valem.)
- **Panner de cada track de canal**: `StereoTo16ChannelPanProcessor`
  (ClassID `1a356806-5dc5-4e2f-914c-d8353e1a6581`, Version 2), com **matriz POR PAR**:
  o canal `c` entra na entrada `c%2` (o `SecondaryIndex=c` do clipe põe par na esquerda,
  ímpar na direita) e a matriz roteia o par inteiro para as saídas do par —
  `Matrix=[[0,[2⌊c/2⌋]],[1,[2⌊c/2⌋+1]]]`. Ex. 5 canais: tracks com matriz
  `[[0,[0]],[1,[1]]]`, `[[0,[0]],[1,[1]]]`, `[[0,[2]],[1,[3]]]`, `[[0,[2]],[1,[3]]]`,
  `[[0,[4]],[1,[5]]]`. `OutputAudioChannelLayout` = 32 discretos.
- **MasterClip da sequência**: o `AudioClip` (que aponta para `AudioSequenceSource`) tem
  `AudioChannelLayout` de **32 discretos** (mesmo barramento da master), não N.
- **Props das tracks TARGETED do som** (multicam nativa — só 4 props, SEM
  `MZ.SourceTrackState`/`MZ.SourceTrackNumber`, que são de track de source-monitor):
  `MZ.TrackTargeted=1`, `CM.KeyframeMode=true`, `TL.SQTrackExpanded=0`,
  `TL.SQTrackExpandedHeight=41`. Só os **pares completos** são targeted; um canal ÍMPAR
  solto no fim (total ímpar) **NÃO** é targeted (props vazias). Ex. 5 canais: canais 0–3
  targeted, canal 4 não.
- **Tracks de ÁUDIO DE ÂNGULO (câmera)**: uma multicam nativa inclui o áudio de CADA câmera
  (o som original), por canal, como tracks a MAIS (depois das do som direto), **não-targeted
  (Properties VAZIO)** e FORA de `NumAdaptiveChannels`. Carregam o áudio da câmera via o
  `AudioMediaSource` multicanal da câmera com `SecondaryContent.ChannelIndex=canal`.

## Bug ABERTO: multicam GERADA é lida como "0 Channel" (não "Multichannel")

`pendente`. Uma multicam adaptativa **gerada** (não pelo Premiere) é lida no bin como
`"0 Channel mapped to N Mono"` — toca ao abrir como TIMELINE, mas fica **MUDA no monitor de
origem** e **sem waveform ao dar nest**. A NATIVA do Premiere diz `"Multichannel mapped to N
Mono"` e funciona. O tooltip "0 Channel" é a assinatura do problema.

Diffando a gerada e a nativa NO MESMO PROJETO (mesma mídia, mesmo espaço de OIDs — método
abaixo), tudo o que dá para comparar bate: master track, `AudioTrackInlet` (32 discretos,
7 Sources), MasterClip, `ClipChannelGroup`, matrizes dos panners, e as props das tracks
(reproduzidas EXATAS). Mesmo assim persistiu o "0 Channel". **Suspeito não resolvido:** o
`"N Channel"` do tooltip vem provavelmente do `AudioStream`/`AudioSettings` da própria
sequência-como-fonte (via `AudioSequenceSource`), não das tracks — foi onde o diff parou.
Quem for resolver: comparar TUDO alcançável do `AudioSequenceSource` para baixo, incluindo
os objetos de fonte (`AudioStream`, `AudioSettings`, `Media`) da sequência.

## Método que isolou as diferenças (reutilizável)

Pedir ao usuário para pôr a versão NATIVA (que funciona) e a GERADA no **mesmo `.prproj`** e
diffar: mesma mídia, mesmo espaço de OIDs → diff limpo, cada diferença aparece isolada.
Foi o que separou master/inlet/master-clip/props uma a uma. Muito melhor que diffar dois
arquivos distintos (OIDs e durações diferentes viram ruído).

## 🆕 Medido no Premiere 26.0.2 (PRODB, 2026-10-04) — `confirmado` no projeto real

- O canal que um clipe da TIMELINE toca: `AudioClip › SecondaryContents › SecondaryContentItem
  Index="k" ObjectRef → SecondaryContent { Content, ChannelIndex }` (ChannelIndex 0-based). O nome do
  container é `SecondaryContentItem`, não `SecondaryContent` (um grep pelo nome errado dá "nenhum
  clipe tem canal"). No filme: 2.243 clipes mono (1 item), 293 estéreo (2 itens); 2.425 leem o canal 0.
- Clipe que vem de um take aninhado: `Source = AudioSequenceSource` (271 no filme). O De Lá Pra Cá
  trata o canal N do clipe de fora como a trilha N do take (áudio adaptativo) — `inferido`.
- **Volume do clipe:** componente `Volume`, parâmetro `Level` = amplitude LINEAR com **1,0 = +15 dB**
  (o máximo do Premiere): o padrão 0,177828 = 10^(−15/20) = 0 dB (6.150 parâmetros de Channel Volume
  nesse valor no filme). **dB = 20·log10(v) + 15.** Keyframes: `Keyframes` = `tempo,valor,…;`.
  Formato medido (2026-10-03, PRODB): cada keyframe = `ticks,valor,0,0,<alça in>,0.1666…,<alça out>,0.1666…;`
  (ticks de 254.016.000.000/s; valor linear). No filme: 20 clipes com keyframes — **3 com UM só** (vale
  o clipe todo = volume fixo, já traduzido), 4 com dois, 13 com quatro (rampas: forma no DRT `pendente`).
- **Velocidade do clipe de áudio:** `AudioClip › PlaybackSpeed` — no projeto, só CONSTANTES (0,5; 1,05;
  2,5; 2,0…), nenhuma negativa (reverso). 38 clipes no filme (entram a 100% até medir a forma no DRT).
- ⚠️ **Caminhos com `..` dentro do `.prproj`** (medido 2026-10-03): o Premiere grava `FilePath` relativos
  resolvidos pela metade, ex. `…/24Y07M23/../../../../../08_20240724/SOM_A/…/27A-1T05.WAV` — 55 clipes
  de áudio do filme. O SO resolve; uma tranca que recusa `..` os deixava OFFLINE calada (Mac e Windows).
  Resolver pelo TEXTO (`posixpath`/`ntpath.normpath`, pela forma) antes de checar UNC.
- O texto dos campos vem escapado do XML (`&amp;`): um `FilePath` "doors &amp; closing.wav" não
  existe no disco até desescapar.
- Números do filme (DU_CORTE_06): 20 trilhas, 2.536 clipes (2.059 WAV), 1.224 transições, 260
  clipes desligados; efeitos: Volume 1.108, Channel Volume 205, Studio Reverb 146, EQ 49, Dynamics 46…
