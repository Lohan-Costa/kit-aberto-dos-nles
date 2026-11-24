# Ver o painel servido sem abrir o NLE — Chrome headless por CDP

> **Medido em 2026-09-20**, Ciclo Assist 0.2.0, Windows 11, Chrome 141 headless, painel
> servido em `http://127.0.0.1:7824/painel`. Confiança: **`confirmado`** para a técnica e
> para os três defeitos que ela achou; ⚠️ **`hipotese`** para qualquer afirmação de que o
> que se vê aqui é o que o NLE mostra — ver *O que isto NÃO prova*.

O desenho que a casa usa nos dois NLEs é **loader + interface SERVIDA por HTTP**: o `.avpi`
do Media Composer carrega `http://127.0.0.1:<porta>/painel` no QtWebEngine, e a extensão CEP
do Premiere navega para a mesma página (medido em
`plugins/premiere-cep/painel-servido-e-identidade.md`). ⇒ **A página é uma página normal**,
e qualquer navegador a abre — inclusive um sem ninguém na frente.

## Por que isto vale uma entrada de banco

Num painel, os dois modos de falha mais caros **não aparecem em teste nenhum**:

1. *"a tela não faz nada"* — um `getElementById` que volta `null`, um `fetch` para rota que
   não existe. O arquivo compila; `node --check` passa.
2. *"o layout quebra em 400 px"* — que é a largura em que estes painéis vivem.

E o custo de descobrir isso dentro do NLE é alto: abrir o Media Composer, reinstalar ou dar
Reload, e **ter o editor na frente**. O banco já registra que spike que mexe em monitor ou
bin roda com o editor olhando (`plugins/avid-panel-sdk/`); o painel puro não precisa disso.

## A receita

```
serviço no ar  →  chrome --headless=new --remote-debugging-port=9333
               →  GET http://127.0.0.1:9333/json      (pega o webSocketDebuggerUrl)
               →  WebSocket: Page.enable · Runtime.enable
               →  Emulation.setDeviceMetricsOverride(width=400, …)
               →  Page.navigate
               →  Runtime.evaluate  (clicar abas, preencher campos, disparar botões)
               →  Page.captureScreenshot(captureBeyondViewport=True)
```

- ⭐⭐ **`Emulation.setDeviceMetricsOverride`, nunca `--window-size` sozinho.** A
  `--window-size` **inclui a moldura da janela**: pedir 400 deu **504 px de viewport**, e
  nessa largura o defeito de layout não aparecia. Foi a diferença entre o print dizer "está
  bom" e o print mostrar o cartão quebrado.
- ⭐ **`captureBeyondViewport=True`** pega a página inteira, não só a dobra — numa lista de
  resultados é o que permite ver o quinto cartão.
- ⭐ **Devolver uma `Promise` do `Runtime.evaluate`** (com `awaitPromise`) permite clicar
  **depois** que a tela respondeu: `busca → espera → clica no resultado` num roteiro só.
- ⭐ **Ler o DOM depois do clique conta o estado:** um botão que respondeu já mudou de
  texto, então `b.click(); return b.textContent` diz se o handler correu.
- ⚠️ **Não precisa de dependência.** O CDP fala WebSocket, e o mínimo do RFC 6455 que ele
  usa — handshake, frame de texto mascarado, sem fragmentação — cabe em ~60 linhas. Num app
  que evita dependência por princípio (o Ciclo Assist empacota com PyInstaller), pôr
  Playwright no `requirements` para tirar um print é o rabo abanando o cachorro.
- ⚠️ **`--user-data-dir` próprio**, senão o headless disputa o perfil do Chrome do usuário e
  a porta de depuração não sobe.

## O que ela achou em uma sessão

| defeito | como apareceu | por que teste nenhum pegaria |
|---|---|---|
| a tela de resultados saía **sem miniatura nenhuma** | o print, com o acervo real | a rota devolvia 404 corretamente; o dado é que a nota não tinha a posição |
| um bloco `flex: 1 1 100%` abrindo **ao lado** do texto, e não abaixo | o print | falta de `flex-wrap` no pai — CSS válido, resultado errado |
| o texto descendo **para baixo** da miniatura em 400 px | o print a 400, depois de corrigir o de cima | `flex-basis: auto` num container que agora quebra |

⭐ Os dois últimos foram **criados** pelo conserto do primeiro, e um deles **só existia na
largura real**. É o argumento inteiro: olhar cedo, e olhar na medida certa.

## ⚠️ O que isto NÃO prova

**O QtWebEngine do Media Composer não é o Chrome**, e o CEP do Premiere também não. Coisas
já medidas que continuam valendo só lá dentro:

- o **Reload** do painel trazendo a página ANTIGA quando o serviço não manda
  `Cache-Control: no-store` (Ciclo Assist, 2026-09-11);
- **clique sintético que não chega** a algumas webviews;
- o arrasto (`text/x.avid.mc-api-asset-list+json`, `effectAllowed = "move"`, o `preventDefault`
  incondicional) — ver `plugins/avid-panel-sdk/arrastar.md`;
- o painel como janela top-level que **rouba o foco do MC** e faz o `DoCommand` não agir
  (INDEX §`DoCommand_SO_AGE_NA_JANELA_ATIVA`).

⇒ A leitura certa de um print destes é **"o layout e a lógica estão de pé"**, nunca
*"funciona no produto"*. O ✅ de dentro do NLE continua sendo do editor.

## Ver também

- `plugins/premiere-cep/painel-servido-e-identidade.md` — a medição de que a página servida
  por `127.0.0.1` mantém o `__adobe_cep__` e roda `evalScript`.
- `plugins/avid-panel-sdk/README.md` — o `.avpi`, o gateway órfão e a ordem de instalação.
- `plugins/avid-panel-sdk/arrastar.md` — o que só se mede com o NLE na frente.
