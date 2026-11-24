---
name: ciclo-novidades
description: Conferir, de tempos em tempos, se o KIT ABERTO DOS NLEs mudou — comparar com o principal no GitHub, resumir o NOVIDADES.md e o que chegou em linguagem de quem edita, e só atualizar com o ok da pessoa, lendo o código que chegou.
when_to_use: No começo de uma sessão, no máximo uma vez por semana (anote a data em local/); quando a pessoa perguntar se há novidades; antes de investigar algo que talvez já tenha sido resolvido por outra pessoa.
---

# Novidades: o que chegou ao kit

1. **Ver se mudou** (só leitura): `git fetch` do principal (`https://github.com/Lohan-Costa/kit-aberto-dos-nles`) e
   compare com a cópia local (`git log HEAD..origin/main --oneline`). Sem Git (kit baixado em .zip): leia o
   `NOVIDADES.md` do GitHub e compare com o local.
2. **Resumir** em poucas linhas, em linguagem de quem edita: o que foi adicionado, corrigido e mudado (os envios começam
   por `adicionado:`, `corrigido:`, `mudado:`). Diga se algo toca um programa ou fluxo que esta pessoa usa (veja
   `local/diagnostico.md`).
3. **Ler antes de trazer:** o que chega é código. Olhe a diferença dos scripts e das skills; diga o que muda no
   comportamento. ⛔ `contribuicoes/` é quarentena: o que está lá não foi confirmado.
4. **Atualizar com o ok:** `git pull` (num fork: "Sync fork" no GitHub, depois `git pull`). Se a pessoa mexeu em
   arquivos do kit, mostre o conflito antes de resolver. Depois, rode `python3 instalar.py --conferir`.
5. Anote em `local/` a data da conferência e o que entrou.
