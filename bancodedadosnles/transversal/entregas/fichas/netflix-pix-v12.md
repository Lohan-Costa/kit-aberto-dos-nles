# Netflix — Pix Information v12 (PT-BR, 2021) + Locked Cut Deliverables v3.0 (2019)

Fontes: `MANUAIS ENTREGA/TECH SPECS/Netflix_Pix_Information_v12_PT_BR_20211208.pdf` (20 pág.) e
`International Originals - Locked Cut Deliverables v3.0_Portuguese_20190207.pdf` (5 pág.; o mesmo
conteúdo da seção IV do Pix v12). Confiança: `documento`. Destino: **revisão de cortes e dailies na
Netflix** (Pix) e **entrega do corte aprovado** (Content Hub).

- **Arquivo para o Pix:** 1920×1080, H.264 em .mov (AVC "H264 settings" recusado), áudio AAC-LC/MPEG-4
  < 160 kb/s; dados ≤ 4.000 kb/s (dailies) e ≤ 10.000 kb/s (cortes); máx. 6 GB; TC master no canto
  superior direito (só cortes).
- **Marca d'água** (dailies e cortes): "Property of Netflix – DATA", 50% de opacidade, letras brancas, na
  imagem ativa. Cortes: TC sup. direito · notas de VFX sup. esquerdo (shot number + escopo) · notas de
  diálogo inferior centro · notas de música inferior direito. Com tarja (não 16:9), as informações na
  tarja; sem tarja, caixa preta semitransparente. ⚠️ NÃO aplicar essa marca no material que vai para
  a ilha (Avid) — lá só os burn-ins combinados.
- **Dailies:** pasta por dia `CODIGO_DAY001_aaaammdd`; nomes `[EP]-[Cena][Plano]-[Take][Câmera].mov`
  (filme sem EP); sufixos `_vfx`, `_vp`, `_SELECTS`.
- **Line-up dos cortes:** 00:59:50:00 claquete · 00:59:55:00 black · 00:59:58:00 2-pop com bipe de 1
  quadro · 01:00:00:00 1 s de black · 01:00:01:00 programa → créditos → cartela da produção → cartela
  do estúdio → 1 s de black. Crédito "A Netflix…" no início; vinheta de abertura não precisa.
- **Claquete:** título e episódio, descrição do corte (Netflix Cut 2, LOCKED CUT…), data aaaa/mm/dd, TRT,
  notas (áudio/títulos/música/VFX provisórios).
- **Nomes:** `CODIGO_EP101_NFLXCUT1_aaaammdd` (filme sem EP), `…_LOCKED_…`, `…_MUSICCUT1_…`, `…_SC002_…`.
- **Corte aprovado (Locked Cut):** o .mov nas especificações do Pix (Pix + Content Hub), `_ENG` se
  legendado; **DME temporários 2.0** (diálogo, música, efeitos) em WAV
  (`…_LOCKED_DIALOGUE/_MUSIC/_FX_aaaammdd.wav`); legendas em inglês temporárias (TXT, XML, DFXP, SRT,
  CSV, Excel — STL não).
- **Change List** (corte aprovado → IMF: TC/duração, diálogo, texto na tela, audiodescrição) até 48 h
  antes do IMF; **Forced Narrative List** junto com o corte aprovado. O IMF final não tem legenda
  queimada.

## Nos prints (lidos como imagem, 2026-10-04)
- **Cortes com tarja:** VFX Shot Name no topo esquerdo, "Property of Netflix – data" no centro superior, TC no
  topo direito; embaixo: descrição do VFX à esquerda, nota de diálogo no centro, nota de música à direita (a
  marca d'água do próprio Pix com nome/IP fica no meio). **Sem tarja:** o mesmo, com caixa preta
  semitransparente.
- **Claquete:** SHOW TITLE · EP101 NFLX CUT 1 · DATE: YYYY/MM/DD · TRT: HH:MM:SS · NOTES (TEMP COLOR, TEMP
  MUSIC, TEMP TITLES, TEMP VFX).
