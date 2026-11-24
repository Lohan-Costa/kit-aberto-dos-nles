---
name: ciclo-laboratorio
description: Gerar mídia SINTÉTICA (cada quadro e canal diz o que é: câmera, take, timecode, quadro, taxa, layout de áudio) e rodar as bancadas do laboratorio-de-midia para medir um programa de edição antes de usar material de verdade.
when_to_use: Quando um teste precisa de um formato, taxa, timecode, câmera ou layout de áudio específico; antes de afirmar que algo funciona num programa; para reproduzir um relato de contribuicoes/; no diagnóstico de uma máquina nova; quando a pessoa pedir "testa isso sem usar meu material".
---

# O laboratório: o mundo controlado

`laboratorio-de-midia/` gera a mídia e mede. Leia o `laboratorio-de-midia/CLAUDE.md` e o `README.md` dele antes do
primeiro uso (as receitas, as bancadas e como rodar).

## Regras

- **Sintético primeiro.** O material da pessoa só entra depois que o caso sintético passou, e só com o ok dela.
- **A receita diz o que quer** (formato, taxa, TC, câmeras, canais de áudio); o gerador escreve na própria imagem e no
  próprio som o que cada quadro e canal é. Para conferir, leia o quadro (foto) e o som (o bipe no quadro N), não o nome.
- **A saída é grande:** gere numa pasta de saída combinada com a pessoa (num disco com espaço), nunca dentro do Git.
- **Medir com número:** a bancada sai 0 se passou e grava o resultado (quadro a quadro, ms de áudio, correlação da
  imagem). "Abriu sem erro" não é medida.
- **Uma bancada abre o programa de edição** — avise antes; se precisar operar a tela, é piloto e precisa do pedido.

## Para reproduzir um relato de contribuicoes/

1. Leia o relato inteiro e o código que veio junto, SEM rodar.
2. Monte o caso com uma receita do laboratório (nunca com o arquivo do relato, se houver).
3. Meça na versão e no sistema citados (ou diga que mede noutra e o que isso muda).
4. Confirmou → promova ao banco com a confiança, a versão e o sistema, citando a contribuição. Não confirmou → anote no
   próprio relato o que se mediu e deixe como investigação aberta.
