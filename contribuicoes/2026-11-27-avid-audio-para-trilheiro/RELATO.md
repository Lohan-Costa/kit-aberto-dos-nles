# Avid: organizar o áudio de uma sequência para o músico (som direto / FX / trilha) e centralizar o pan do som direto

- Programa e versão: Avid Media Composer 24.12.6 (gRPC local na porta 9100) · pyavb (venv do kit, 2026-11-27)
- Sistema: macOS 26 (Intel), monitor 2560×1440 escala 1
- Confiança: **confirmado** nesta máquina, numa sequência real de ~27 min, 37 trilhas de áudio e 2.423 clipes de
  áudio. Não foi reproduzido com mídia sintética do laboratório (ver "O que não se mediu").
- Como reproduzir: os passos abaixo; `organizar_audio.py` e `conferir_audio.py` nesta pasta.

## A tarefa

Antes de mandar uma timeline para o músico, o áudio precisava ficar assim:
- A1–A18: som direto;
- A19–A24: FX;
- A25 em diante: trilha;
- par estéreo com o canal L em trilha ÍMPAR e o R em PAR;
- som direto com o pan no CENTRO, porque cada canal é um microfone e não um par estéreo.

## Os passos (o que funcionou)

1. **Achar a sequência aberta.** A API `GetViewerMobs` dá o mob do Record; `GetBinFromMob` dá a `.avb`.
   `GetMobTrackInfo` lista as trilhas e quantos segmentos cada uma tem, mas não diz o conteúdo.
2. **Ler o conteúdo numa CÓPIA da `.avb`** com o pyavb (o MC regrava a bin aberta).
   - A categoria de cada clipe sai do nome do master ou da fonte, por expressão regular:
     - WAV de gravador e câmeras = som direto;
     - biblioteca de efeitos (`_PSE_`, `.aif`…) = FX;
     - `BPM`, `.mp3`… = trilha.
   - O canal do clipe é o `track_id` do SourceClip no master (1 = L, 2 = R). Isso vale também para um master de 6 canais.
3. **Montar uma CÓPIA da sequência numa bin NOVA** (`organizar_audio.py`). A original não é tocada.
   - Só os clipes fora da faixa certa, ou com o par invertido, trocam de trilha.
   - Os pares são casados pelo mesmo master, canais 1 e 2, com início a até 3 quadros um do outro.
   - Cada par vai para o primeiro par livre (ímpar/par) da faixa.
4. **Conferir** com `conferir_audio.py`, ler os números e só então dar `OpenBin` na bin nova:
   - vídeo idêntico;
   - mesmos clipes (posição, duração, fonte, início, canal);
   - mute igual;
   - duração de cada trilha igual.
5. **Pan centro no som direto, pelo Audio Mixer** (modo Clip), operado pelo piloto. Os passos estão logo abaixo.
6. **Salvar** (`OpenBin` locked + `DoCommand 1004`) e conferir de novo pela bin salva:
   `conferir_audio.py … --pan-centro 1-17`.

### O passo 5 no Mixer (MC 24.12 Mac)

- Deixe ligadas **só** as trilhas do som direto.
  - Shift+Cmd+A no painel da timeline desliga todas.
  - Ligue uma a uma pelos **botões de trilha do Audio Mixer**. A timeline acompanha.
- **Option-clique no knob de pan de CADA trilha** (vai para "MID"). Com várias trilhas selecionadas, o Option-clique num
  knob NÃO propaga às outras.
- Marque IN no primeiro quadro e OUT no último. Pela API: `SetPosition` por **offset** + `DoCommand 6209`/`6210`.
- Menu rápido do Mixer (☰) → **Set Pan On Track – In/Out**. Nesta versão não há a opção "Global".
- O Mixer aplica, em cada trilha, o valor que o knob mostra sob a agulha. **Trilha sem clipe sob a agulha não tem knob**:
  faça à parte, com a agulha num clipe dela e só ela selecionada.
- Desfaça o que mudou na tela: `DoCommand 6214` tira as marcas; Cmd+A religa as trilhas; volte a agulha.

## O que se viu

- **Clipe de áudio sem pan definido segue o "Default Pan" do Audio Setting do USUÁRIO**
  (`<user> Settings.xml`: `AUDI defaultPan`, aqui `0`). Nesta máquina ele abre ímpar = L e par = R, e foi isso que a
  pessoa viu no Mixer. Nenhum clipe nem master tinha pan gravado.
  ⇒ Uma timeline "sem pan" muda de aparência conforme a máquina ou o usuário que a abre. Para entregar, o pan tem de ser
  gravado no clipe.
- **Mover um clipe de trilha sem desmontar a sequência:**
  - Na origem, o clipe vira um Filler do mesmo tamanho. Uma transição que sobra entre dois Fillers sai, e os Fillers se
    juntam.
  - No destino, corta-se só o Filler que contém o clipe, com folga para as transições vizinhas. Remontar a trilha
    inteira a partir de "blocos" desmonta crossfades existentes: essa foi a primeira tentativa, recusada pelas asserções.
  - Um crossfade entre um clipe que fica e um que sai vira fade-out + fade-in do mesmo tamanho e cutpoint.
- **Clipe mutado na `.avb`:** é um `Selector` cuja alternativa selecionada é um Filler, com o clipe na outra. Também
  existe `Selector` com um clipe só selecionado, que NÃO é mute.
- **O Set Pan On Track – In/Out embrulha** o SourceClip puro (250 casos) e o Selector (8 casos) num `PanVolumeEffect`
  novo, sem mexer no mute. Os 1.007 mutados (pela regra acima) ficaram iguais antes e depois.
- **pyavb, `copy()` de um mob com AudioSuite** (`ASPIPlugin`) quebra com
  `TypeError: ASPIPlugin.__init__() missing 1 required positional argument: 'root'`, porque o `from_name` chama
  `__init__` sem argumentos. Contorno: um monkeypatch do `__init__` com `root=None`, que está no começo de
  `organizar_audio.py`.

## O que se mediu

- **`PanVolumeEffect.pan` = 16384 é o centro ("MID")**, com `pan_set=True`. Duas medidas:
  - O Mixer gravou exatamente isso nos 1.793 clipes de som direto. O valor lido na bin depois do Save é 1.793/1.793.
  - Uma varredura de 120 bins de outro projeto real achou 18.532 clipes com `pan_set=True`, **todos** com 16384.
    Nenhum tinha pan fora do centro.
  - ⚠️ Ainda **não se mediu o valor de L100 e de R100**: não houve um clipe com pan lateral gravado para ler.
- **`pan_set=False`** aparece com `pan=16384` também: nesse caso o valor é só o padrão do campo e não vale.
- **Resultado da reorganização:**
  - 42 clipes trocaram de trilha (FX vindos de A6–A18 e A25–A28; uma trilha mutada saindo de A23/24);
  - 3 pares de FX com L/R invertidos foram acertados;
  - no máximo 4 FX tocavam ao mesmo tempo, então coube tudo em A19–A22;
  - vídeo idêntico, 2.423/2.423 clipes, mute igual, duração de cada trilha igual;
  - só 4 fades diferentes: o crossfade desfeito em fade-out + fade-in, de 6 quadros.
- O `organizar_audio.py` desta pasta, rodado na mesma bin com os padrões do trabalho, deu resultado **idêntico** ao
  script do trabalho (comparação pelo `conferir_audio.py`). O conferidor também **reprova** quando deve: na versão sem o
  pan, deu 1/1.793 com pan centro.

## Piloto no Mac (MC 24.12)

- O **clique sintético no seletor de trilha da TIMELINE** (o botão "A1") **não liga a trilha**. Foram 3 tentativas,
  com e sem pausa de 120 ms entre apertar e soltar, com o ponto conferido na foto. Uma aba da paleta de efeitos
  respondeu ao mesmo clique.
- O **botão de trilha do Audio Mixer** responde, e a timeline acompanha a seleção.
- **Option-clique**: Option apertado (`_tecla_crua`) + `_mouse` com a bandeira `0x80000` no apertar e no soltar. Funcionou
  no knob de pan.
- O menu rápido do Mixer ficou aberto entre dois comandos, com o MC na frente, sem `devolver_ao_terminal()` no meio.
  O item foi clicado pelo ponto lido na foto.
- `ExportFile` com o preset "AAF" para uma pasta temporária voltou "Completed" e **não gerou arquivo nenhum**. Isso
  reforça a regra do banco de não medir por `ExportFile`. `ExportFile` para uma pasta que não existe dá
  "Can't find destination directory.".
- `LoadMobsIntoViewer` de uma sequência que já está no Record respondeu "Some mobs was skipped.", sem nenhum diálogo
  na tela.

## O que não se mediu

- Reprodução com mídia sintética do laboratório. Falta uma receita de sequência com som direto, FX e trilha, pares
  estéreo e clipes mutados.
- O valor de pan para L100/R100, e a escala completa (0…32768? ±16384?).
- Se o AAF/"Export to Pro Tools" leva o pan do clipe, e se o Pro Tools do músico o respeita.
- Windows, outras versões do MC e telas Retina (piloto).
- Os nomes das opções de `defaultPan` (0 = ímpar L / par R é inferido do que se viu no Mixer, não lido na interface).
