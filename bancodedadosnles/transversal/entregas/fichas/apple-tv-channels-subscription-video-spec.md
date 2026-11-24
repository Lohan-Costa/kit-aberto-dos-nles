# Apple TV Channels — Subscription Video Asset Specification 1.11 (help.apple.com)

Fonte: https://help.apple.com/itc/TV/channels/subvideospec/en.lproj/static.html (texto salvo em
`MANUAIS ENTREGA/PUBLICOS/APPLE/`, ~18 mil palavras). Confiança: `documento`. Destino: **pacote de DISTRIBUIÇÃO** para
canais da Apple TV (importador iTunes: pacote `.itmsp` com `metadata.xml`); originais Apple TV+ têm spec própria, não
pública. Referencia a "Apple Transactional Film Specification" para formatos de TC.

- **TC do programa começa em 00:00:00:00** (o manual: a Apple exige que o TC comece no início do programa em 00:00:00:00);
  legendas fechadas podem levar `program.start.timecode` = −01:00:00:00 para compensar um master que começa em 01:00.
- **Recorte por METADADO**, não na imagem: `crop.top/bottom/left/right` obrigatório quando há pixels inativos
  (letterbox, pillarbox, windowbox); `image.textless_master` declarado; SDR e HDR (Dolby Vision, HDR10) com TCs iguais.
- Capítulos com TC e imagem, Dolby Atmos com downmix, prévias (preview) e "epic stage" como assets próprios.
