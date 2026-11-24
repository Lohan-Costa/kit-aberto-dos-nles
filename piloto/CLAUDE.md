# PILOTO — o Claude operando o computador

Vale a regra da família (`../CLAUDE.md`): o banco primeiro, a matriz de plataforma antes de tocar em processo, janela,
teclado ou diálogo do sistema.

**O que é:** ferramenta da família (autor, 2026-10-12) para o Claude operar a máquina sozinho quando a API de um app
não alcança: **mãos** (mouse e teclado), **olhos** (janelas e fotos), **vigia** (prazo, queda e diálogos conhecidos
pela foto) e **pontes** (achar a API de cada app). Nasceu na bancada do `laboratorio-de-midia` (Effect Editor e
AniMatte do Media Composer pilotados sem o autor, 2026-10-11/12). As regras de operação estão na skill **`/piloto`**
(`bancodedadosnles/skills/piloto/SKILL.md`). Quando o autor diz **"pode pilotar"**, é para operar sozinho.

```
piloto/
├─ piloto/       o pacote: maos_/olhos_/vigia_ windows e macos · vigia_comum (o cão de guarda dos dois) · apps · pontes
├─ catalogos/    os diálogos conhecidos de cada app (foto + o que fazer): avid/ · premiere/ · resolve/
├─ exemplos/     uso real (mc_effect_editor.py = o teste ao vivo no MC)
├─ tests/        o que não opera a máquina (catálogos, reconhecimento por foto, freio)
└─ saida/        fotos do vigia e das rodadas — fora do Git
```

⭐ **CALIBRADO POR AMBIENTE.** As leituras de tela (posições, cores, desenho das janelas) foram medidas num ambiente
só: notebook Windows 1920×1080, escala 125 %, MC 25.6 maximizado no layout padrão. Outro monitor, escala, layout de
janelas, versão do app ou máquina (o Mac) = **recalibrar antes de operar** (fotografar, medir de novo, registrar). O que
não depende de posição (API, bin, render, reconhecimento de diálogo pela foto) atravessa; o que lê a tela por
coordenada, não. Prefira sempre achar pelo PADRÃO na foto a posição fixa.

**Para ler (e mostrar à equipe):** `docs/piloto-e-autonomia.html` — abre com duplo clique em qualquer navegador; é a
cópia local do artefato https://claude.ai/artifact/8D8gFuYkoBThaw12SSBMoA. Mudou um, atualize o outro.

**Divisão de trabalho (autor, 2026-10-12):** Opus pensa e decide; Sonnet por subagente lê imagens de um tipo já
validado pelo Opus (medido: igual em telas limpas; Haiku não serve para estrutura); o piloto coleta e opera em lote.

Regras desta pasta:
- **O pacote não conhece app nenhum** além do perfil em `apps.py`: o que é de um app (atalhos, posições de botão,
  fluxos) mora em quem usa (a bancada do laboratório, o app). Aqui só o que serve a todos.
- **Diálogo novo que se repete** = foto em `catalogos/<app>/` + entrada no `catalogo.json` com o que fazer (`clique`
  em pixels da foto, `tecla`, ou `esperar`). Desconhecido nunca leva clique.
- **macOS (2026-10-14):** mesmos nomes de função, só biblioteca padrão (`ctypes` em CoreGraphics/acessibilidade +
  `screencapture`); medido no Resolve 21.1 (as notas estão na skill e na matriz, seção F). O Python do Mac é o
  `.venv/` daqui (Pillow + pytest; não vai para o Git). MC 25.12 e Premiere 2026 medidos em 2026-10-24 (os três NLEs abertos juntos; abrir sempre por `apps.abrir`, sem
  o `LANG` da sessão; arrasto entre apps funciona; sonda `sondas/arrasto_nativo_mac.swift`). Falta: tela Retina e as
  fotos dos diálogos do MC do Mac no catálogo.
- Testes: `py -m pytest tests` (Windows) · `.venv/bin/python -m pytest tests` (Mac) — não clicam em nada. O teste ao
  vivo é o exemplo do MC.
