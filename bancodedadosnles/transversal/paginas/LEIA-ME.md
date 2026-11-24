# Páginas (artefatos) da família — o design system do autor

Toda página publicada (proposta, relatório, plano) usa o design system **"Lohan Costa · Apresentações"**
(cópia do autor: https://claude.ai/artifact/3c4rXhPSdVw8oBVhUNHKsQ; decisão do autor, 2026-11-22: "usar como padrão
dos artefatos"). Nada de paleta inventada.

- `tema.css` — os tokens (claro e escuro) e os componentes em escala de página: capa escura com eyebrow, barra âmbar
  e números; `section`/`.cab`; `.card` (`.acao`, `.aviso`); `.selo`; `.provas`/`.prova` (pipeline numerado);
  `.tabela`; `.diagrama` (SVG com `.g-slate/.g-teal/.g-violet`, `.destaque`, `.con` tracejado âmbar); `ol.passos`;
  `.rodape`; o placar `.marca` (certo · alerta · errado · a medir).
- Como usar: publicar a página COM o `tema.css` ao lado (`publish_files`, `as: "tema.css"`, e
  `<link rel="stylesheet" href="tema.css">` + o link das fontes que está no topo do arquivo). Página de um arquivo só:
  colar o conteúdo do `tema.css` num `<style>`.
- Regras do DS: o âmbar nunca é a cor principal; verde-água cheio só em destaque; texto escuro sobre `teal`/`amber`,
  branco sobre `teal-fill`; ênfase por negrito, nunca por tamanho novo; tom de conversa, sem "não é X, é Y".
- Exemplos: `1 IDEIAS/GRIPTAPE E CICLO ASSIST/docs/relatorio-provas.html` ·
  `2 ATIVOS/_CICLO ASSIST/docs/plano/2026-11-22-lab-casamento-baselight/`.
- **Voz (autor, 2026-11-22):** a página é de apresentação e registro, não uma conversa com o autor. Nada de
  "você pediu", "como você decidiu", "você foi avisado" → "como foi decidido", "o editor é avisado",
  "decisão do autor". Perguntas pendentes em voz neutra ("Decisões pendentes").
