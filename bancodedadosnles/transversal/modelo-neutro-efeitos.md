# Modelo neutro de efeitos — a "pedra de Roseta" entre NLEs

Como traduzir um efeito geométrico de uma NLE para outra preservando a **intenção**. As fórmulas
consumíveis estão em [modelo-neutro-efeitos.json](modelo-neutro-efeitos.json). Confiança
`confirmado` (medido contra chart de grade, 2026-06-14), salvo onde indicado.

## As três camadas (cardinalidades diferentes)

1. **Intenção (modelo neutro)** — mapeada **uma vez por primitiva**, reusada por todos os efeitos.
   `3D Warp`, `Resize`, `Pan & Zoom`, `PiP` do Avid são as MESMAS primitivas (position/scale/
   rotation/anchor/crop/opacity).
2. **Convenção (unidade/origem/âncora/ordem)** — mapeada **uma vez por NLE**.
3. **Codec (ler/escrever bytes)** — **possivelmente por efeito**; é a única camada que pode exigir
   amostra por efeito. Mas a maioria dos geométricos do Avid compartilha o esquema de param-ID.

→ Não se cria amostra de todo efeito; cria-se um conjunto que **abrange** cada primitiva isolada +
cada efeito suspeito de codec diferente.

## Modelo neutro (unidade canônica)

| campo | unidade neutra |
|---|---|
| `scale` | fator (1.0 = 100%) |
| `position` | fração do raster (x: +direita; y: +cima) |
| `rotation` | graus |
| `crop` | fração por borda |
| `opacity` | 0..1 |
| `anchor` | fração do raster (centro = padrão) |
| `keyframes` | `[{t (0..1), valor, interp, handles}]` |

Velocidade **não** entra aqui — é tratada à parte (`speed_ratio`/`source_offset_map`) e é o único
efeito que o importador do Resolve preserva. Ver [tempo-e-timecode.md](tempo-e-timecode.md).

## Convenção por NLE (medido 2026-06-14)

| primitiva | **Avid** | **Resolve** | **Premiere** | neutro |
|---|---|---|---|---|
| Position X | `DVE_POS_X_U` **milésimos** (÷1000) | `posX = px/1920` (fração, f64le) | px absoluto → `frac=px/W` | fração da largura |
| Position Y | `DVE_POS_Y_U` milésimos, **+Y cima** | `posY = px/1080` (fração), **+Y cima** | px, **+Y baixo** (inverter) | fração da altura, +Y cima |
| Scale X/Y | `DVE_SCALE_*` **%** (÷100) | `zoom` **fator** (omite eixo=1.0) | `Scale` **%** | fator, **anchor=centro** |
| Rotation | `DVE_ROT_Z_U` **graus** | `rotation` **graus** | `Rotation` **graus** | graus |
| Crop | `DVE_CROP_*` ±999 | `crop = px/dim` (fração) | `Crop` **%** | fração por borda |
| Opacity | `DVE_FG_KEY_OPACITY_U` 0–100 | `opacity` 0–100 | `Opacity` 0–100 | 0..1 |

**Por que Avid/Resolve são resolution-independent e Premiere não:** Avid e Resolve guardam posição
como **fração**; Premiere guarda **pixel absoluto** (mesmo "150px" vira fração diferente por
resolução). Confirmado no blob do Resolve (byte-idêntico FHD/UHD): `0.138889 = 150/1080`.

## Fórmulas de conversão validadas (neutro = fração, +X dir, +Y cima)

- **Avid → neutro:** `frac = pos/1000` (X, Y). +Y já cima.
- **Resolve → neutro:** `frac_x = px/largura`, `frac_y = px/altura`. +Y cima.
- **Premiere → neutro:** `frac = offset_px/dim_raster`; **inverter sinal de Y**.
- **Scale:** fator puro (Avid ÷100, Premiere %÷100, Resolve direto). Anchor = centro, posição
  independente da escala → sem resíduo de ordem para pos+scale.
- **Crop Avid→Resolve:** `crop_l/crop_b = (v+999)/1998`; `crop_r/crop_t = (999−v)/1998`. Validado.

Exemplo: Avid pos 150 (frac 0.15) → Resolve TL 1920×1080 = `(288, 162) px`. Resíduos < 1%.

## Perfis de extração do Avid (o nome/sinal muda por efeito)

A regra de **valor** (milésimos/%) é compartilhada; o **nome do param** e o **sinal** mudam por
efeito. Ver tabela em [../protocolos/aaf/dados/operationdefs.json](../protocolos/aaf/dados/operationdefs.json):
- `3D Warp` (SBlend_v2) e `Resize`/`PiP` → `DVE_*`/`AFX_*`, +X direita.
- `Pan & Scan` → sinal **invertido** (move a janela).
- `FrameFlex` (SpatialAdapter) → esquema próprio (`zoom=100/Size`, `frac_pos=-Pos/Size`).

## Onde escrever no destino
- **Resolve/DRT:** blob `EffectFiltersBA` — decodificado e escrito byte-exato. Ver
  [../protocolos/drt-drp/dados/effectfiltersba.json](../protocolos/drt-drp/dados/effectfiltersba.json).
- **Premiere/.prproj:** XML gzipado — convenção de origem (top-left) + âncora é decisiva.
- **OTIO:** metadata específica do Resolve.

## Armadilhas (resumo)
- **Valor de UI engana:** traduzir a **fração**, não o número de UI.
- **Origem Premiere (top-left) vs Avid/Resolve (centro):** converter a origem, não só a unidade.
- **Ordem das operações:** fixar ordem canônica (scale → rotate → translate em torno da âncora).

## Pendências (`pendente`/`hipotese`)
- Sinal de rotação por NLE; anchor 2D; flip/flop; **keyframes + interpolação** (a curva entre
  keyframes difere entre NLEs — sub-problema próprio, mesmo método da rampa); divisor fino do crop
  do Avid; estratégia de Image Scaling do Resolve para mismatch de aspecto.

## Método da matriz de calibração (etapa futura)
Mesmo método que decifrou AAF/AMA/DRT: criar projeto no Avid com vários efeitos + timeline
equivalente no Resolve/Premiere → exportar AAF + DRT/OTIO/.prproj → **diffar** para derivar cada
fórmula e o de-para "efeito Avid ↔ nó do destino". Plano em `RELINKER/docs/effect-sampling-plan.md`.
