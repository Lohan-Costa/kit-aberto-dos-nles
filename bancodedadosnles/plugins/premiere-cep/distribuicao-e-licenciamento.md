# Distribuir e licenciar um painel CEP

O que os quatro concorrentes dissecados resolveram para **entregar, atualizar e cobrar** por um
painel — a parte que não é técnica de NLE mas decide se o produto sai da máquina do dev. Levantado
em 2026-08-09. Fatos consumíveis em [dados/distribuicao.json](dados/distribuicao.json).

Aqui só entra o que foi observado num produto real. A parte de *como instalar para desenvolver*
(pasta CEP, `PlayerDebugMode`, symlink) continua no [README](README.md).

## ⭐ Licenciamento: existe SDK pronto (aescripts+aeplugins)

O `Chat Video Pro` carrega `vendor/aesp.umd.js` (+ `.cjs`): um UMD que exporta o global **`Aesp`**,
com **376 referências a `aescripts.com`** e 349 a `license`, strings em tabela (obfuscado).

É a biblioteca de licenciamento do **aescripts+aeplugins** — o marketplace onde painéis de
Premiere/After Effects são vendidos. `aescripts.com` também aparece no `bundle.js` do painel.

**Por que isso importa:** licenciamento é um daqueles itens que parecem pequenos e comem semanas —
ativação, trial, máquina trocada, offline, reembolso, pirataria. Um produto em produção resolveu
**terceirizando para o marketplace**, e o SDK é `<script>` num painel CEP. Se algum dia vendermos
painel, é o caminho mais curto: não escrever licenciamento, não hospedar servidor de ativação, não
processar cartão.

⚠️ Não avaliado: termos comerciais, percentual da loja, se aceitam produto que fala com nuvem
própria, se há SDK equivalente para o Panel SDK do Avid (o mercado deles é Adobe). `pendente`.

**Alternativa observada:** o Eddie usa **Stripe** dentro do app (`@stripe/react-stripe-js`,
`checkout.stripe.com`) e o Chat Video Pro usa **LemonSqueezy** no backend (`LEMON_API_KEY`) — os
dois caminhos de cobrar direto, sem marketplace, com o custo de fazer a gestão você mesmo.

## Empacotamento: um ZXP por plataforma

**O erro medido:** o `Chat Video Pro` tem **1,2 GB** porque manda binários de **todas** as
plataformas para **todos** os usuários:

| | macOS | Windows |
|---|---|---|
| `ffmpeg`/`ffprobe` | 80 MB cada (universal) | **170 MB cada** |
| Node | `arm64` 121 MB + `x64` 114 MB + `legacy` 91 MB + `node` 91 MB | `node.exe` 71 MB |

Num Mac, ~410 MB nunca executam. Num PC, ~200 MB. **É o 1,2 GB inteiro explicado**, e é evitável
com um ZXP por plataforma — que é exatamente o que o Eddie faz (o `.pkg` dele é por arquitetura, e
o config remoto é buscado em `distributions/{darwin|win32}/{x64|arm64}/`).

Se o painel precisar de binário, três decisões vêm juntas: **qual plataforma**, **como marcar o bit
de execução**, e **como sair da quarentena** (abaixo).

## Atualização: quem manda, e sem pedir licença ao usuário

Três estratégias observadas, em ordem crescente de agressividade:

**1. Instalador refaz a pasta (Premiere Copilot).** O `preinstall` do `.pkg` dá `rm -rf` nas pastas
antigas (`PremiereCopilot` e `PremiereGPTBeta`) e o `postinstall` cria a estrutura de trabalho em
`~/Documents/Adobe/Premiere Pro/<Produto>/`. Simples, exige o usuário rodar instalador.

**2. O app carrega o ZXP e se autoatualiza (Eddie).** `Resources/premiere-panel/com.eddyai.ae.zxp`
+ `panel-manifest.json` com `version`, `gitSha` e **`zxpSha256`**; canais
`IPC_ADOBE_EXTENSION_VERSION` / `IPC_INSTALL_LATEST_ADOBE_EXTENSION`, `sudo-prompt` para escrever em
`/Library`, e a rota **`/reload-extension`** para o painel recarregar **sem fechar o Premiere**.
⭐ O app é a autoridade de versão, não o Exchange. O `zxpSha256` no manifesto é o detalhe certo:
confere antes de instalar.

**3. O painel baixa o aplicativo inteiro a cada abertura (Premiere Copilot).** `index.html` de 5 KB
faz `fetch` e injeta `{html, css, js}` (2,4 MB) no DOM. Nunca há versão no disco. Máxima agilidade,
e o custo de segurança do §último.

**E o mais barato dos três, que serve para o backend:** **config remoto**. O Eddie monta
`s3://…/distributions/{plat}/{arch}/{versão}/config.json` no boot e tira dali o endpoint de
produção — trocar de backend sem republicar painel, com o hardcoded só como fallback. Bucket
público, uma linha de código, resolve o problema de "o painel instalado aponta para o servidor
velho".

## Gatekeeper e quarentena (macOS) — se o painel trouxer binário

Documentado pelo próprio `Chat Video Pro` em `MAC_INSTALL.md`: o download/unzip aplica
`com.apple.quarantine` no binário embutido, e o painel limpa sozinho —
`xattr -d com.apple.quarantine <bin>` + `chmod +x`, via `setMacExecutePermissions`. Se o Gatekeeper
corporativo bloquear, a doc ensina o usuário a rodar na mão.

⚠️ **Se copiarmos, com hash.** Rodar `xattr -d` num binário é o gesto de um malware; e um binário em
`server/bin/` gravável por qualquer processo do usuário vira execução de código com o usuário do
editor. **Verificar o binário por hash antes de executar** (o `zxpSha256` do Eddie é o padrão certo,
aplicado ao lugar errado — ele confere o ZXP, não o executável).

## Segurança de release — checklist derivado dos quatro

Tudo abaixo foi encontrado em produto pago, de empresa real. É a lista do que **não** fazer.

1. **Não deixar `<RequiredPermissions>` vazio.** O Premiere Copilot não declara nenhuma restrição de
   domínio e executa 2 MB de JS remoto a cada abertura com `--enable-nodejs` e
   `--allow-file-access`. Quem controlar o domínio executa código na máquina do editor.
   O Chat Video Pro declara `https://*.vercel.app` — melhor, mas largo demais (qualquer app da
   Vercel). Declarar o **host exato**.
2. **Não embutir webhook nem segredo no painel.** O Eddie carrega **dois incoming webhooks do
   Slack em claro** no servidor do painel: qualquer um com a extensão instalada posta no Slack da
   empresa. Segredo de escrita não sobrevive no cliente — nunca.
3. **Não publicar `.debug`.** Já registrado em [`../../seguranca/`](../../seguranca/) a partir do
   Quickture (porta 8860, DevTools sem auth, em painel com Node). Item de checklist de release.
4. **Não publicar source map com `sourcesContent`.** O Quickture publicou o TypeScript inteiro por
   descuido. O Eddie deixou `.js.map` ao lado de todo `dist`.
5. **Session replay é gravação de tela.** O Eddie usa `@amplitude/plugin-session-replay-browser` +
   `rrweb`: em pós-produção isso captura nome de projeto, de clipe e transcrição na tela. Se um dia
   tivermos telemetria, **replay fica fora** — e o resto entra opt-in.
6. **Placeholder não vai para release.** O Chat Video Pro entrega
   `whisper/ggml-base.en.bin` com **313 bytes** — um comentário dizendo "baixe o modelo real" — e o
   recurso simplesmente não funciona no build enviado. Um teste de tamanho de arquivo no CI resolve.
7. **Nome de preset não é fato.** Dois dos quatro têm `.epr` cujo nome mente (`CVP_ASR_Mono_48k` é
   estéreo; `EXPORT_4K 60fps` é 1080p25). Se distribuirmos preset, o nome tem de ser gerado a partir
   do conteúdo, não digitado.

## Ver também

- [README](README.md) — instalar para desenvolver, CEP vs UXP
- [chat-video-pro-arquitetura.md](chat-video-pro-arquitetura.md) — o SDK do aescripts e o empacotamento de 1,2 GB
- [eddie-ai-arquitetura.md](eddie-ai-arquitetura.md) — autoatualização de ZXP e config remoto
- [premiere-copilot-arquitetura.md](premiere-copilot-arquitetura.md) — o loader remoto e o risco que ele carrega
- [`../../seguranca/`](../../seguranca/) — achados de segurança do ecossistema
