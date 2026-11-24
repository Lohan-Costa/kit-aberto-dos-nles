# Telepacífico (Colômbia, TV pública regional) — Protocolo de entrega 2025

Fonte: `MANUAIS ENTREGA/PUBLICOS/TELEPACIFICO (COLOMBIA)/Protocolo_Final_2025.pdf` (público, em espanhol).
Confiança: `documento` — GUIA. Destino: **TV pública latino-americana** (vizinha da EBC/TVs públicas BR).

- Vídeo: MXF OP1a, **1080i 29,97**, 4:2:2 ou 4:2:0 (XDCAM 420 35 Mb/s citado), 16:9; níveis 0–700 mV, croma ≤ 263 mV.
- **TC: o clipe exportado começa em 00:00:00:00** — e o protocolo manda CONFERIR no MediaInfo que o TC saiu em zero.
- Áudio: mix no canal 1, 48 kHz/16 bits, picos entre −20 e −10 dBFS (média −12 dBFS) — medido em dBFS, não em LKFS.
- Closed caption CEA-708 embutido no MXF (pista SMPTE 436M) ou SRT/CC por capítulo; Roll-Up 2, Courier New.
- Claquete no início; cada bloco identificado; tabela de blocos com TC de entrada/saída/duração (o exemplo usa
  blocos começando em 00:00:10:00 e 00:10:00:00).
- Entrega final em disco rígido com master, especificações, fotos, cessão de direitos (acervo).

## Para os apps
- Mais uma "hora zero" fora da Netflix (TV pública colombiana), contra a hora 1 da EBC: o TC de início é do destino.
- "Conferir no MediaInfo que o TC saiu certo" é uma checagem que o app poderia oferecer no relatório (lacuna leve).
