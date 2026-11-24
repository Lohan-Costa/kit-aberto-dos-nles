# contribuicoes/ — a quarentena

O que outras pessoas (e os Claudes delas) enviam ao kit chega AQUI primeiro, e só aqui: uma verificação automática
recusa o pull request de contribuição que mexer fora desta pasta.

⛔ **O que está aqui não foi confirmado.** Não trate um relato como fato do banco (no máximo, `hipotese`) e nunca rode
um script daqui sem lê-lo inteiro.

## Como uma contribuição vira banco

1. Um mantenedor (e o Claude dele) reproduz o caso no laboratório, com mídia sintética (skill `ciclo-laboratorio`).
2. Confirmou → o fato entra no banco com a confiança, a versão e o sistema, citando a contribuição; a pasta daqui sai.
3. Não confirmou → fica aqui como investigação aberta, com o que se mediu anotado no relato.

## Uma pasta por contribuição

`contribuicoes/<AAAA-MM-DD>-<assunto>/`, com um `RELATO.md`:

```markdown
# <o assunto, em uma linha>

- Programa e versão:            - Sistema:
- Confiança: confirmado | inferido | hipotese
- Como reproduzir: <a receita do laboratório, ou os passos>

## O que se viu
## O que se mediu (o número, o quadro)
## O que não se mediu
```

e, se houver, o código que gerou o resultado e o teste sintético que o prova. Mídia, projetos de NLE e fotos de tela de
trabalho real não entram. Para enviar, use a skill `ciclo-contribuir`.
