# EBC (TV Brasil) — NOR 704: formato padrão de entrega em alta definição (06/06/2019)

Fontes: `MANUAIS ENTREGA/PUBLICOS/EBC/EBC NOR 704 … (2019-06-06).pdf` (14 pág., Deliberação DIREX nº 42) e a versão
anterior da mesma norma usada em edital das TVs públicas (`PUBLICOS/TVS PUBLICAS (FINANCIADOR-V)/…`, mesmos parâmetros).
Confiança: `documento` (norma da casa; o Manual de Tecnologia diz que a Engenharia atualiza "sempre que necessário").
Destino: **TV aberta brasileira (EBC e TVs públicas)** — o mundo da radiodifusão, bem diferente do de cinema/streaming.

- **Arquivo:** XDCAM HD422 (MPEG-2 4:2:2P@HL, 50 Mb/s), **1920×1080i, 59,94i, Top Field First**, 16:9 nativo sem
  barras, **TC drop frame** sem descontinuidade. Entrega em disco XDCAM (23/50 GB), HD externo exFAT/Journaled ou a
  ferramenta da EBC.
- **Cabeça:** barras SMPTE HD com tom de 1 kHz a −20 dBFS de 00:59:38:00 a 00:59:47:29 · **claquete** de 00:59:48:00 a
  00:59:57:29 (estado/região, proponente, título, direção, roteiro, episódio, ID "1x5", versão com/sem Libras,
  tipologia, público) · black 00:59:58:00–00:59:59:29 · **programa em 01:00:00:00**.
- **Áudio:** 48 kHz/24 bits, referência −20 dBFS, picos em −10 dBFS, loudness contínuo; estéreo compatível com mono.
  Mapas de canal: finalizado + SAP (1–2 PT, 3–4 língua original) · finalizado + audiodescrição (3–4 PT com AD) ·
  finalizado sem AD (1–4 mix) · bruto (1 depoimento/locução, 2 ambiente) · **internacional** (1–2 mix, 3 diálogos,
  4–5 música, 6–7 efeitos, 8 ambiente). Trilha para Pro Tools em OMF2/AIFF com TC drop frame.
- **Acessibilidade** (ABNT NBR 15290): closed caption EIA-708 (pré-gravado 100% de acerto), audiodescrição mixada nos
  intervalos, **janela de Libras** (≈ metade da altura × ¼ da largura, sem nada por cima), legendas em português para
  todo trecho em língua estrangeira; pasta `ACESSIBILIDADE/CLOSED CAPTION` e `/AUDIODESCRIÇÃO` com o nome do clipe.
- **Área de segurança:** gráficos e legendas a 5% da borda; ação a 3,5%. 4:3 de acervo vira 16:9 com **pillarbox**,
  nunca esticado.
