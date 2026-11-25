---
name: piloto
description: Operar o computador sozinho — mouse, teclado, olhar a tela, janelas e diálogos — pelo PILOTO da família Ciclo Media (PROGRAMAS COM CLAUDE/piloto). Para testar e automatizar apps (Media Composer, Premiere, Resolve ou qualquer programa) onde a API não alcança: clicar e arrastar no monitor, mexer em controles, abrir janelas, fechar diálogos conhecidos, fotografar e medir o resultado. Windows e macOS (mesmas funções; o Mac desde 2026-10-14).
when_to_use: Quando o autor disser "pode pilotar" (ou "pilota", "faz sozinho", "opera você") — é o pedido para EXECUTAR a tarefa operando a máquina, sem pedir que ele clique; quando uma tarefa exigir ação na interface de um programa que a API não faz (desenhar uma máscara, arrastar um controle, abrir um editor, responder a um diálogo); quando um app travar a automação com uma janela de erro ou aviso; e ao escrever código que mande tecla ou clique para outro programa.
---

# Pilotar: o Claude operando a máquina

O piloto mora em `PROGRAMAS COM CLAUDE/piloto/` (ache-o SUBINDO de pasta, nunca caminho fixo). Leia o `CLAUDE.md`
dele uma vez. As peças:

| peça | módulo | para quê |
|---|---|---|
| **mãos** | `piloto.maos` | `frente(hwnd)`, `clicar(x, y)`, `arrastar(x0, y0, x1, y1)`, `tecla(vk, *mods)`, `digitar(texto)`, `relativo(hwnd, x, y)`, `devolver_ao_terminal()`, freio |
| **olhos** | `piloto.olhos` | `janelas(exe)`, `janela_principal(exe)`, `dialogos(exe)`, `fotografar(hwnd, arq)`, `foto_da_tela(pasta, nome)`, `rodando(exe)` |
| **vigia** | `piloto.vigia` | `com_prazo(acao, prazo, exe, pasta, catalogo, …)` (cão de guarda), `varrer` (diálogos conhecidos pela foto), `Travado`, `DialogoAberto` |
| **apps** | `piloto.apps` | perfil de cada app (executável, catálogo de diálogos, janelas que não são modais, log de falha) |
| **pontes** | `piloto.pontes` | a API de cada app (`media_composer()`, `comando(m, id)`); Premiere e Resolve: ver o cabeçalho |

O `import` escolhe o sistema sozinho (`maos_windows`/`maos_macos`, …). O nome do app vem de `apps.processo("resolve")`
("Resolve.exe" no Windows, "Resolve" no Mac) e o log de falhas de `apps.eventlog("avid")`. **No Mac, rode com o Python
do piloto**: `piloto/.venv/bin/python` (tem Pillow e pytest; recriar: `python3.12 -m venv --copies .venv` +
`pip install pillow pytest`).

```python
import os, sys
p = os.path.abspath(os.getcwd())
while not os.path.isdir(os.path.join(p, "piloto", "piloto")):
    p = os.path.dirname(p)
sys.path.insert(0, os.path.join(p, "piloto"))
from piloto import maos, olhos, vigia, apps, pontes
```

## Antes de começar

1. **Avise em uma linha** que vai operar a máquina e que o **freio é F12** (ou criar o arquivo `piloto/PARAR`; no
   **Mac, mexer no mouse também para**). No Windows, **mexer no mouse/teclado PAUSA** (ver a borda abaixo).

## ⭐⭐ A BORDA: o autor vê quando o piloto age, e se o freio pegou (autor, 2026-10-30; só Windows)

Na primeira ação das mãos sobe uma faixa em volta de cada monitor, com uma etiqueta no topo
(`piloto/borda_windows.py`, combinado em `borda_comum.py`):

| cor | quer dizer |
|---|---|
| **azul** | o piloto está agindo (ou esperando no vigia); F12 para; ESPAÇO (ou mexer) pausa |
| **âmbar** | o autor mexeu de verdade: o piloto espera 10 s de sossego (a etiqueta conta) e segue |
| **vermelho** | parou (F12, `PARAR`, ou a pausa virou parada) — fica ~4 s e some: é a confirmação |
| sem borda | o piloto não está agindo; F12 não faz nada |

- **A pausa vira PARADA** em quatro casos: toque no meio de um ARRASTO; TECLA física no meio de uma DIGITAÇÃO (a
  pausa segura as mãos do piloto, não a tecla do autor — ela entra no campo: medido, o projeto nasceu
  "PILOTO  BORDA TESTE 2" com um espaço a mais); a janela da frente mudou durante a pausa; pausa de mais de 120 s.
  Depois de uma parada, foto e pergunte ao autor antes de seguir.
- ⭐ **ESPAÇO é a tecla de pausa** (autor, 2026-10-30): com a borda acesa, a borda a ENGOLE — pausa e não chega ao
  programa (não vira espaço no texto que o piloto digita). As outras teclas passam: é ação de pânico do autor, e numa
  digitação elas PARAM o piloto (medido: o campo ficou `PILk`, Create não foi clicado). Não se mata o teclado.
- **A borda muda NA HORA** do gesto do autor, e **guarda o F12** apertado entre um comando e outro (quando o
  piloto não está olhando): a próxima ação para. Só vale para aquela borda — a tarefa seguinte não herda.
- `devolver_ao_terminal()` ignora o freio de propósito: devolver o controle é o que o F12 pede.
- ⭐ **Velocidade:** passos de um fluxo já medido vão num comando só, conferidos pelo TÍTULO/retângulo das janelas
  (fotos guardadas); ler foto a cada passo é para tela nova ou desvio. A demora entre ações era o turno do modelo,
  não o piloto (medido: abrir o Resolve e criar o projeto = ~15 s num comando, contra ~1 min passo a passo).
- O toque conta só se for FÍSICO (os ganchos de baixo nível vêem a marca `INJECTED` do `SendInput`).
- A borda **não aparece nas fotos** (`WDA_EXCLUDEFROMCAPTURE`): o reconhecimento por foto não muda. Deixa o clique
  passar e não pega o foco.
- `devolver_ao_terminal()` apaga a borda — mais um motivo para ele estar no `finally`. Se o piloto morrer, ela some
  sozinha em 45 s (o prazo é renovado por toda ação e toda checagem do freio).
- `maos.ligar_borda()` acende antes da primeira ação (útil antes de uma espera longa); `PILOTO_SEM_BORDA=1` desliga.
- ⬜ Mac: `ligar_borda`/`desligar_borda` existem e não fazem nada; lá mexer no mouse PARA (não pausa).
2. **Consulte o banco** sobre o app (a regra da família): `bancodedadosnles/plugins/avid-panel-sdk/windows.md`,
   `transversal/matriz-de-plataforma.md` seção F. Muito do que parece precisar de clique a API já faz — **API
   primeiro, piloto onde ela não alcança**.
3. Regras do app que valem sempre (ex.: MC e Resolve nunca abertos juntos — `CLAUDE.md` do app).

## ⛔⛔⛔ O foco é do NLE só enquanto o piloto opera; ao terminar, volta ao TERMINAL (autor, 2026-10-29)

- **Ao terminar uma tarefa pilotada, chame `maos.devolver_ao_terminal()`** e confira o `True`. Vale também quando a
  tarefa termina por erro, por um `Parado` ou por um diálogo desconhecido: ponha a chamada num `finally`. Se ela
  devolver `False`, diga isso ao autor.
- **Só traga o NLE para a frente na hora de agir nele** (`frente` antes do gesto). Não o deixe na frente "para depois".
- **Por quê:** o autor acompanha a sessão pelo terminal. Com o NLE na frente, ele não sabe se já pode trazer o
  terminal de volta nem o que está acontecendo, e muitas vezes corrigiu uma operação vendo o que o piloto tentava.
  Com o NLE e o terminal à vista mas o foco no NLE, o que ele digita achando estar no terminal vira ATALHO do NLE.
- Windows (medido 2026-10-29): o terminal é achado pelo console de um processo de cima desta sessão. No Windows
  Terminal, o dono da `PseudoConsoleWindow` é a janela `CASCADIA_HOSTING_WINDOW_CLASS`, com o título da sessão; no
  console clássico, a própria janela. Ele traz a JANELA; se o Windows Terminal tiver várias abas, fica na frente a aba
  que já estava ativa. Mac: sobe pelos pais até um app de janela (`pendente`, não medido).

## ⛔⛔ Abriu ou fechou um programa: confira as FALHAS do sistema e DIGA (autor, 2026-11-22)

`marca = falhas.agora()` antes de abrir/fechar; depois, `falhas.desde(marca, ["Avid", "Baselight"])` e, para cada uma,
`falhas.frase(f)` ao autor. **Por quê:** o macOS mostrou "Relatório de Problemas" na tela do autor (MC abortou ao abrir,
Baselight caiu ao sair com a FLAPI conectada) e a sessão não viu — "mesmo que inofensivas pro usuário algo está errado".
- **Fechar só com o programa OCIOSO** (render terminado, scene fechada, a API desligada há uns segundos).
- **MC: o "Leave the application?" aparece SEMPRE ao pedir para fechar.** Não é diálogo desconhecido: 3 s depois do
  Quit, foto, clique em Leave (a posição pela foto) e espere o PROCESSO sair.
- ⛔⛔ **MC que cai ao abrir pelo terminal (Mac) = o `LANG` da sessão**, não o `AvidIdentityHandler`: o `open -a` repassa
  `LANG=pt_BR.UTF-8` e a DekoLibrary aborta (`PRESETS_DOC::Init` → `k_double` "Number required"). Abrir por
  `apps.abrir(chave)` ou `env -u LANG -u LC_ALL open -a …` (regra abaixo; matriz de plataforma). Redescoberto TRÊS vezes
  (24/10, 22/11, 23/11) — a de 23/11 porque o `grep --include=*.md` no zsh falhou como glob e a consulta ao banco não rodou.

## ⛔⛔⛔ Nada age na máquina depois que a pilotagem termina (autor, 2026-11-15)

Vigia, cão de guarda, laço que fecha diálogo: **só existem enquanto alguém pilota** (o Ciclo Assist numa operação, ou
o Claude numa tarefa) — e morrem junto. Nunca um processo de fundo que sobreviva a quem o ligou.
- **Por quê:** o `vigia_dialogos` do laboratório, ligado sem querer pelo `esperar_ponte()` de um `python3 -c`, ficou
  vivo a manhã inteira e apertou Return ~30× no Premiere do autor (fechou o Color Picker, painel fechou, timeline deu
  play) — e a sessão tirou conclusões erradas do Premiere por causa dele.
- **Como:** o vigia do laboratório só age com MANDATO (`with vigia_dialogos.pilotando("motivo"):`, preso ao processo
  dono, conferido a cada volta e antes de cada tecla). Ao terminar uma tarefa: `ps -axo pid,command | grep -i vigia` e
  nada deve sobrar. Comportamento estranho no app durante um teste → antes de concluir, confira se há vigia rodando.

## ⛔⛔⛔ REGRA MÁXIMA: nunca operar às cegas (autor, 2026-10-17)

**Medir antes de executar, sempre.** Nenhum clique, tecla ou loop roda sem que a tela tenha sido olhada logo antes.

- **Vigia visual de minuto em minuto é OBRIGATÓRIO em toda execução do piloto automático:** a cada ~60 s (e a cada
  ação), foto da tela + leitura da imagem (subagente Sonnet para o tipo já validado; Opus para tela nova) + checagem
  dos processos. Rodada que não acompanha a tela não roda.
- **Loop de clique/tecla sem foto entre as tentativas é proibido.** Ação que não surtiu efeito = foto e PARE para
  entender; nunca repetir o mesmo clique. (2026-10-17: o duplo-clique no Select Project repetiu 10× no vazio
  enquanto um diálogo de layout de teclado tinha aparecido; só o F12 do autor parou.)
- **O ponto do clique precisa cair num monitor VISÍVEL.** Janela do MC pode abrir parcialmente fora da tela (Select
  Project no 2º monitor com topo em y = −450; diálogo `AvidMediaComposer` inteiro acima da tela): `relativo()` dá
  coordenada negativa e o clique some. Confira o retângulo, traga a janela para dentro da tela e meça de novo antes.
  ⭐⭐ **No PRODUTO (Ciclo Assist, o piloto embutido), NÃO se traz a janela** (autor, 2026-11-02): janela com parte
  na faixa sem monitor ou cortada fora da tela = a operação PARA e diz ao editor por quê — o layout é dele
  (`localizador.JanelaCortada`, `tela.parte_fora`, folga de 16 px para a maximizada em (−9, −9)). Trazer a janela é
  só do piloto numa sessão de desenvolvimento, com o autor olhando.
- **A posição de uma janela muda entre aberturas** — medida de uma abertura não vale para a seguinte.

## O ciclo: olhar → decidir → agir → olhar

- **Foto ANTES e DEPOIS de cada ação** (`foto_da_tela` ou `fotografar` + Read da imagem). Nunca encadeie cliques às
  cegas: a janela pode não ter aberto, o foco pode ter ido para outro lugar, um diálogo pode ter aparecido.
- **Coordenadas pela foto.** Meça na foto em pixels reais. Na foto de UMA janela, use `relativo(hwnd, x, y)`. Foto
  da tela reduzida para leitura: multiplique pela escala informada.
- **`frente(hwnd)` e confira o retorno antes de teclar.** Tecla que cai na janela errada vira comando de outro
  programa — o pior modo de falha é agir no programa errado calado.
- **Nenhuma espera sem prazo.** Ação longa (abrir, exportar, renderizar) vai dentro de `vigia.com_prazo`, com o
  catálogo do app: ele confere app vivo, janela respondendo, falha no log e diálogos.
- **Diálogo desconhecido: foto e PARE.** Nunca clique em diálogo que não conhece. Se ele se repete e o autor disse
  o que fazer, cadastre: foto em `piloto/catalogos/<app>/` + entrada no `catalogo.json` (`clique` em pixels da foto,
  `tecla`, ou `esperar`; `so_quando` para o que só vale num contexto).
  ⭐ **No PRODUTO (Ciclo Assist) existe o agente do piloto** (autor, 2026-11-08; `cicloassist/piloto/auxilio.py`): quando o script desiste, um
  modelo olha a tela e sugere, e o CÓDIGO decide (lista fechada de botões; OK só se for a única escolha; texto que fala em apagar, substituir ou
  falha = pergunta ao editor; o ponto passa pela cruz; o mesmo clique não se repete; 4 consultas por operação). Esta regra de PARAR continua
  valendo para o piloto da família, em sessão de desenvolvimento. MEDIDO no MC 2024.6: "Project already exists" resolvido (OK, US$ 0,027,
  projeto aberto em 42,6 s); "Leave the application?" recusado, nada clicado.
- ⛔⛔ **Com um diálogo aberto, a API do MC fica muda** (2026-11-09, MC 2024.6): `GetAppInfo` estoura o prazo, e o clique em Executar esperou 20 s. Toda ferramenta cuja conferência fala com a API recusa o fluxo antes de o piloto olhar a tela; na dúvida, conferir se há modal antes de culpar a API. ⚠️ Corrigido só no `salvar_tudo` (Ciclo Assist).
- ⚠️ **O menu File, colado à borda esquerda, reprova na conferência às vezes** (2026-11-08/09, 2 falhas em ~6 cliques): a cruz cobre a palavra curta. Tentar de novo costuma passar.
- ⛔⛔ **Aviso sobre a Select Project: focar o AVISO, não ela** (2026-11-08, MC 2024.6). Com o aviso de teclado em cima a Select Project fica
  desabilitada, e o foco é recusado volta após volta. E nem todo modal se chama "AvidMediaComposer": o de projeto repetido e o "Leave the
  application?" se chamam **"Avid Media Composer"** (389×117 e 238×117), e bloqueiam as outras janelas igual. Modal = janela pequena e
  habilitada com a principal desabilitada (`cicloassist/avid/socorro.py`). ⚠️ Painel solto do layout livre também é pequeno e habilitado.
- **Valor por teclado, não por arrasto.** Para levar um controle deslizante a um número exato: clicar no botão dele
  e usar as setas (um passo por toque) — conferido no AniMatte (Hor 0 → 20 com 20 toques).

## Armadilhas já pagas (não redescubra)

- ⛔⛔⛔ **Arrastar do FINDER para um app (Mac): a soltura pode MOVER o arquivo** (2026-11-23, Ciclo Assist). Trazer o
  Finder à frente sobe TODAS as janelas dele; uma janela antiga do Finder por cima do ponto de soltura RECEBE o arquivo e o
  MOVE para a pasta dela, calado (3 .prproj do PRODUCAO-C foram parar em "PRODUCAO-A"; devolvidos com `mv -n`). E
  outra janela (o Terminal) entre o Finder e o app engole a soltura. ⇒ antes: feche as outras janelas do Finder; traga o
  APP à frente e DEPOIS o Finder (o app fica logo abaixo); confira que nenhuma janela do Finder cobre o ponto; depois de
  soltar, confira no DISCO que a pasta de origem está intacta e no log do app que a soltura chegou. Vista de ícones: o
  ícone é o ponto de pega mais seguro (na de lista a coluna do nome pode estar rolada para fora).
- ⛔ **Roda do mouse sobre controle deslizante Qt muda o VALOR.** Rolar lista = clicar na faixa da barra de rolagem.
- ⛔ **Escala de tela do Windows (125 %)**: o piloto se declara ciente de DPI; código seu que use `ctypes` sem isso
  erra o lugar do clique.
- ⛔ **Dois monitores**: coordenadas na área de trabalho VIRTUAL (o piloto já faz).
- ⛔⛔ **Escala MISTA (125 % + 100 %): a janela Qt MUDA DE TAMANHO ao trocar de monitor** (2026-11-02, Win 11, MC 2024.6;
  monitor 2 à direita, área virtual (0, −549) 3840×1629): a Select Project foi de 1352×759 para 1082×607 (×0,80 = 100/125)
  e a aba New Project a ESTICOU para 1082×751 — retângulo lido antes de trocar de aba cortou o Create fora do recorte.
  ⇒ Releia o retângulo da janela DEPOIS de todo gesto que muda o conteúdo dela. O MC (no 1º arranque da rodada) nasceu no
  monitor PRINCIPAL; com a Select Project aberta a principal não aceita foco (Win+Shift+→ só move a Select Project).
  O localizador na área inteira (3840 px → 1366) ainda acertou Open/Quit/New Project; recortar pelo monitor é margem.
- ⛔⛔ **O layout PADRÃO do MC com dois monitores (2024.6, medido 2026-11-02):** a principal ("Avid Media Composer  -
  projeto", com menus e bins) fica num monitor; **Composer + Timeline vão para uma 2ª janela de topo** no outro, SEM
  moldura (`WS_POPUP`), com o título **"AvidMediaComposer"** — o MESMO do aviso de teclado e da barra de carregar — e
  12 px MAIOR que a principal. Três armadilhas: "a maior janela" escolhe a do Composer; "existe janela
  AvidMediaComposer" vê um aviso que não existe; "a timeline está na principal" não acha. ⇒ principal = título que
  COMEÇA com "Avid Media Composer"; aviso = esse título E janela pequena (< 1/4 do monitor; aviso 518×190, barra
  402×125); a timeline: procurar nas janelas grandes do MC, as não principais primeiro (`cicloassist/janela.py`,
  `avid/salvar.py`). E "a janela da frente" pode ser a da Timeline: recortar pela janela de TRABALHO, não pela da frente.
- ⭐⭐ **Layout LIVRE (painéis flutuantes, medido 2026-11-02): cada painel solto é uma janela de topo com o NOME DO
  PAINEL no título** ("Timeline", "Bins", "Composer", "Audio Mixer", "Effect Palette"…), de qualquer tamanho e em
  qualquer monitor. ⇒ ache o painel pelo TÍTULO (`janela.do_painel`), e só sem ele (encaixado) procure nas janelas
  grandes. Não precisa de calibração: o Windows diz onde cada painel está, de graça e sempre certo. A principal fica
  só com os menus, e o Ctrl+S com o foco nela salva tudo (.avp e bin regravados, 1,6 s, com uma bin suja).
  O MC REABRE com o layout livre (posições iguais), mas NUMERA o painel: "Bins" voltou "Bins.1", noutro lugar e
  tamanho — aceite o título + ".N". Fluxo `preparar-diaria-no-mc` 8 de 8 neste layout (2026-11-02).
- ⛔⛔ **Recorte PEQUENO no localizador erra o ponto** (Sonnet 5.5, 2026-11-02): no recorte só do aviso de teclado
  (518×190) o "Don't warn me again" saiu 29 px ABAIXO (x certo), estável; a conferência recusou 45 vezes. Com 150 px
  de margem (818×490): exato. ⇒ recorte < 800×480 ganha margem (`localizador.MINIMO`).
- ⛔⛔ **Com um aviso MODAL do MC na tela, focar a principal é RECUSADO** (ela fica desabilitada): sem janela nenhuma na
  frente (o app acabara de sair dela), o abrir esperou 302 s sem agir. Foque o AVISO. E erro de foco engolido num laço
  de espera tem de ir para o log — calado, ele escondeu a causa por 5 min.
- ⭐ **Monitor 2 mudado de LADO (à esquerda, área virtual (−1920, −559), 2026-11-02):** o MC guarda o layout livre POR
  MONITOR, não em coordenada absoluta — os painéis que estavam em x ≥ 1920 reabriram no monitor da esquerda, nas mesmas
  posições relativas (nenhum fora de tela); o Resolve maximizado foi junto com o monitor. Coordenada negativa no clique
  e no recorte: provada (a timeline achada em (−722, 235)). Fluxo do MC 8 de 8 nos dois arranjos.
- ⛔⛔ **Dois "AvidMediaComposer" pequenos ao mesmo tempo** (barra de carregar + aviso de teclado): a barra vazia na
  frente, DESABILITADA pelo modal, e o aviso habilitado nascido ATRÁS da principal. ⇒ vale o HABILITADO (`IsWindowEnabled`),
  e ele é trazido à frente antes da foto, mesmo com outra janela do MC já lá.
- ⛔⛔ **A barra de carregar pode ficar PRESA atrás da Select Project** (2026-11-03, MC 2024.6, um monitor): a
  "AvidMediaComposer" 402×125, visível e DESABILITADA, com a Select Project habilitada e livre e a lista de projetos
  VAZIA, por mais de 3 min. Não é aviso: aviso modal fica habilitado e desabilita a Select Project
  (`avid/abrir._barra_presa`). Quit → "Leave the application?" → Leave fechou em 9,9 s, e o MC reaberto veio normal.
  Invisível para quem olha: o retângulo dela cabe INTEIRO dentro do da Select Project, e ela é VAZIA (sem texto nem
  progresso — vista só depois do Quit, atrás do Leave). Nasceu 1 s depois do "Application ready for user" do
  EVENTLOG, que não registra erro nenhum; a 2ª abertura, com a mesma sequência no log, veio sem ela. Causa: não medida.
- ⛔⛔ **O MENU aberto do MC também se chama "AvidMediaComposer"** (pequeno, habilitado; classe
  `Qt51512QWindowPopupDropShadowSaveBits`, `WS_EX_TOOLWINDOW|TOPMOST`): quem conta "aviso" pelo título + tamanho pega o
  menu, tenta trazê-lo à frente e o item some. Popup (`…QWindowPopup…` na classe) NUNCA é aviso. E o Esc enviado com a
  PRINCIPAL na frente não fecha um menu Qt aberto — clicar no título do menu de novo fecha.
- ⭐ Provados no layout livre com o monitor 2 à esquerda (2026-11-02): o REFRESH do painel lateral na janela "Bins.1"
  solta (renomear bin → fantasma some, `GetBins` == disco, 24,8 s, US$ 0,04 — criar PASTA o MC vê sozinho, sem
  gesto); a janela do app FIXADA no monitor 2 sai para o fundo no passo pilotado e volta fixada (4,6 s → 15,9 s);
  fechar o MC 30,6 s (a 1ª vez depois de montar o layout passou de 60 s — não explicado; uma medida).
- ⚠️ **Resolve 19.1.4 com escala MISTA (2026-11-02):** abre no monitor PRINCIPAL; o Project Manager levado ao de
  100 % encolhe ×0,64 (1440×810 → 922×518, legível: rearranja), e a janela do PROJETO abre onde ELA estava (lugar
  próprio, não o do Project Manager). Win+Shift+→ maximizada deixa-a "maximizada" com 1554×865 num monitor de
  1920×1080 (~80 %, o papel de parede à mostra): retângulo de janela maximizada NÃO é o do monitor — fotografe e
  meça antes de clicar por posição. O conform pela API não liga (12 s e 1,6 s, iguais nos dois monitores).
- ⚠️ MC no layout livre: File → Exit → Leave levou MAIS de 60 s para o processo sumir (o padrão, 31,5 s) — uma medida
  só; o `fechar` acusou erro com o MC fechando. Medir de novo antes de mexer no prazo.
  ⛔⛔ **Remedido (2026-11-04, MC 2024.6, layout livre, depois de um dia de syncs/conversões no projeto): ~3,5 MIN**
  do Leave ao processo sumir, a principal "Not Responding" e a memória subindo a 1,2 GB (gravando o projeto). Não
  é travamento: com o Leave dado, espere o PROCESSO (conferindo-o) e NÃO tente o File → Exit de novo — numa janela
  travada o foco é recusado. `IsHungAppWindow` na principal = já saindo, só esperar (Ciclo Assist `avid/abrir.py`).
- ⛔ **Conferir um VAZIO pede recorte amplo:** a timeline sem sequência, num recorte de 480×270, é cinza liso, e a
  conferência (com razão) não confirma. Recorte 1280×720 enviado a 960 px mostra as bordas (`RECORTE_AMPLO`).
- ⛔ `GetWindowRect` num processo que NÃO se declarou ciente de DPI devolve retângulos VIRTUALIZADOS a 125 % (a principal
  maximizada saiu 1536×816): o módulo que lê retângulo se declara sozinho, não confia em quem importou antes.
- ⛔ **Título de janela é frágil** (o MC 25.6 usa DOIS espaços: "Avid Media Composer  - projeto"): use
  `janela_principal(exe)`.
- ⛔ **Janela do MC/Resolve é Qt**: a automação do Windows não vê texto nem botões — reconhecer pela FOTO.
  (Remedido no MC 2024.6, 2026-11-01: a UI Automation devolve 3 painéis — os dois monitores `OglVideoWin` e a área Qt
  inteira —, nenhum botão nem menu, nem pela visão crua.)
- ⭐ **Localizar pela foto com o `claude -p` (Ciclo Assist, `spikes/o_localizador_ve_a_tela.py`, 2026-11-01)**: imagem
  no stream-json de ENTRADA (`--input-format stream-json`, bloco `image` base64), `--tools ""` e `--system-prompt`
  próprio ⇒ **~2 mil tokens e US$ 0,01–0,02 por pergunta, ~3–6 s** (Sonnet 5.5; sem o piso de ~40 mil do prompt
  padrão). Foto do MC reduzida a 1366 px: menu File, monitor Record e janela de projeto no lugar (erro ≤ 3 px no menu).
  ⛔ **O 2º passe num RECORTE pode PIORAR**: "área vazia da timeline" acertou no 1º (cinza acima da V1) e o recorte
  levou para o vão entre dois clipes da V1 (clicar ali move a agulha). ⛔ **Alvo ambíguo** (abas de bin truncadas
  "O…E", "M…T") deu 1º e 2º passes 185 px longe um do outro, e o modelo DISSE que deduziu ⇒ discordância entre passes
  ou "deduzo" = não clicar.
- ⛔ **Mudança no idioma do teclado do Windows** faz o MC abrir um aviso que deixa a API em "Busy" — o catálogo do
  MC já o resolve.
- ⛔⛔ **ABRIR O MC = focar ANTES de olhar** (autor, 2026-10-31 — "você sempre erra"). O MC sobe SEM foco, e sem foco o
  aviso de layout de teclado NÃO aparece: ele nasce no primeiro instante em que o MC ganha o foco. Foto tirada antes do
  foco diz "livre" e o próximo clique cai no aviso. ⇒ Depois de abrir (e de novo ao chegar na Select Project e ao abrir
  o projeto): `frente(principal)` → ~1,5 s → foto (e `FindWindowW(None, "AvidMediaComposer")`, que `dialogos` não vê)
  → só então seguir. Apareceu: **"Don't warn me again"**, nunca OK — o OK só o tira agora e ele volta no meio do
  trabalho. O catálogo já clica no Don't warn.
  ⛔ **`FindWindowW(None, "AvidMediaComposer")` sozinho MENTE** (2026-11-01, MC 2024.6): com o projeto aberto e nenhum
  aviso na tela ele achou uma janela OCULTA com esse título, que fica lá o tempo todo. Conte só janela VISÍVEL com o
  título exato (`olhos.janelas` ou `IsWindowVisible`). ⚠️ E o aviso VOLTOU na abertura de 01/11 mesmo depois do
  "Don't warn me again" de 31/10 (o teclado do Windows alterna ENG/PTB2) — conferir em toda abertura.
- ⛔ **App que guarda estado em memória** (o MC serve o mob da sessão): o que você escreve no disco com o app aberto
  pode ser desfeito por ele. Escreva numa cópia com identidade nova.
- O `DoCommand` do MC é assíncrono: use `pontes.comando` (espera o anterior).
- ⛔ **TUDO o que espera o app vai dentro do `vigia.com_prazo`, com `saude=`** (no MC: `apps.saude_avid`). Uma
  montagem fora dele esperou 2 min uma bin que não existia mais: o MC tinha caído e reaberto na tela de projetos, e
  ninguém olhava (o autor viu antes de mim). "Select Project" só é normal ABRINDO o MC.
- ⛔ **`frente()` antigo SOLTAVA a janela maximizada** (SW_RESTORE; corrigido 2026-10-12 — se a janela aparecer solta, desconfie primeiro de quem chamou ShowWindow). **Depois de uma queda a janela pode voltar SOLTA**: coordenadas medidas com ela maximizada erram calado. Maximize
  e confira o retângulo antes de ler/clicar por posição. Maximizada pelo Windows, a janela começa em (−9, −9): a foto
  dela (PrintWindow) sai 9 px deslocada em relação à tela — desconte a posição da janela.
- ⛔ **Comando que "liga" pode INVERTER** (as trilhas V1/V2/A1… do MC): leia o estado pela foto, inverta só o que
  difere e espere ~1 s antes de reler.
- O freio: o F12 apertado ANTES de o piloto carregar não conta (o bit "apertada desde a última consulta" vinha sujo).

- ⛔ **Arrasto SINTÉTICO do Media Pool do Resolve não sai do Resolve** (19.1.4, 2026-10-19): a miniatura arrasta dentro
  dele, mas nenhuma outra janela recebe (nem a sonda nativa). O do Premiere sai. Teste de arrasto Resolve → fora = mão
  do autor (banco, resolve-scripting/api-scripting.md). Arrasto para uma janela que o clique na origem vai cobrir:
  ponha o ALVO em `HWND_TOPMOST` durante o gesto e devolva depois.
- ⛔⛔ **Janela própria por `ctypes` (borda, sobreposição): o WNDPROC é UM por PROCESSO** (2026-11-04, Ciclo Assist —
  o serviço CAIU no meio de um turno e levou a conversa do editor). `RegisterClassExW` vale uma vez por processo e grava
  o ponteiro do callback daquele momento; na 2ª subida ele falha ("já registrada") e a classe segue chamando o callback
  da 1ª instância, já coletado → `0xc0000005` no python.exe, módulo "unknown", seguido de `0xc000041d`. Reproduzir a
  QUEDA é sorte (o slot liberado costuma ser reusado pelo próprio callback novo); o defeito se prova pelo PONTEIRO:
  `GetClassLongPtrW(hwnd, GCLP_WNDPROC=-24)` ≠ o callback vivo, com outros `WINFUNCTYPE` nascendo entre as subidas
  (como as listagens de janelas fazem). Conserto: o `WINFUNCTYPE` no MÓDULO, nunca solto, repassando à instância da vez
  (`cicloassist/piloto/borda.py`). A borda do `piloto/` não sofre disto: roda num processo por vez.
- ⛔ **`SetWindowPos(hwnd, HWND_TOPMOST=-1, …)` por `ctypes` SEM `argtypes` não faz nada, calado** (Python 64 bits: o -1
  vai como int de 32 bits; 2026-10-21). Sintoma: o "alvo por cima" do arrasto ficou atrás do Premiere e o arrasto inteiro
  "não chegou". Declare `u.SetWindowPos.argtypes = [HWND, HWND, c_int, c_int, c_int, c_int, c_uint]` e passe
  `wintypes.HWND(-1)`. Foto NO MEIO do gesto (botão ainda apertado) é o que mostra isso.
- ⛔⛔ **O PONTO DE SOLTAR é conferido pela janela que está SOB ele, logo antes do gesto** (2026-11-02, Ciclo Assist): o app trazido à frente num comando volta para TRÁS do terminal quando o `devolver_ao_terminal()` roda — no comando seguinte o arrasto do Explorer soltou o caminho de um `.prproj` na CAIXA DE ENTRADA da sessão. Antes de `arrastar`: `GetAncestor(WindowFromPoint(alvo), GA_ROOT)` == a janela do alvo (o WebView2 é OUTRO processo: comparar pela janela RAIZ, nunca pelo PID), e o alvo trazido à frente no MESMO comando do gesto.
- ⛔ **Clique num item seguido de arrasto = DUPLO CLIQUE** (a bin do Premiere abriu numa aba em vez de arrastar, 2026-10-21):
  selecione antes (clique/Ctrl+clique, foto), espere, e arraste SEM clicar de novo.
- ⛔ **Caminho DIGITADO no diálogo de arquivo do Windows com teclado ABNT2 (PTB2) sai inválido** ("The file name is not
  valid", 2026-10-19): a tecla sintética troca caractere. Colar (Set-Clipboard + Ctrl+V) também falhou ali, e Alt+N
  abriu o menu de sistema. Para carregar arquivo num app nosso, prefira a rota do serviço (`/receber/abrir`) ao diálogo.
- ⛔ **Item de bin do MC: clique no ÍCONE, nunca no NOME** (autor, 2026-10-22). Um clique no nome abre a caixa de
  RENOMEAR daquele item; o duplo clique no nome não carrega nada (a `C07_FALA01` só ficou selecionada, e uma tecla
  depois disso renomearia o item). Pelo ícone à esquerda: um clique seleciona, o duplo clique abre no lugar certo
  (master/subclipe no Source, sequência na Record). O ARRASTO também sai do ícone. Na visão de lista do 24.6 o ícone
  fica em x ≈ 368 da bin em aba.
- ⛔ **Posição medida em outra sessão NÃO vale na Select Project do MC** (2026-10-23): o `criar_projeto` da bancada
  clicou no "Project name" pela fração antiga (0,297) — o campo estava em 0,343 — e o projeto nasceu "Untitled Project"
  (o autor fechou e apagou). Rotina que clica por posição só roda depois de uma foto DESTA abertura conferir o alvo.
- ⛔ **Lista suspensa/menu do MC não sobrevive ao `devolver_ao_terminal()`** (2026-10-31, MC 2024.6): abrir o Format da
  Select Project num comando e escolher no seguinte = a lista fecha quando o terminal ganha o foco, e o clique cai no
  terminal. Abrir + abrir o submenu + fotografar num comando, deixar o MC na frente (avisar o autor para não digitar),
  e escolher no próximo; submenu: mover o mouse na HORIZONTAL até ele antes de descer. ⚠️ O submenu HD 1080 do 2024.6
  tem 1080p/100, /119.88, /120 e os TR — a ordem da bancada (`_FORMATOS_HD1080`) não vale: ler na foto.
- ⚠️ (2026-11-04, MC 2024.6: a PRINCIPAL saiu inteira com `fotografar`, mesmo COBERTA pelo terminal — remedir antes de
  confiar em qualquer uma das duas notas; a de baixo pode valer para outra janela/versão.) **`fotografar(hwnd)` de janela Qt do MC sai VAZIA** (só a moldura): foto da TELA (`foto_da_tela`) e recorte pelo
  retângulo da janela — com dois monitores, descontar a origem da área virtual (`GetSystemMetrics(76/77)`; ex. (0, −549)).
- ⛔ **Janela de ferramenta não é diálogo**: o Motion Effect Editor / Effect Editor do MC ficam abertos sem bloquear (estão no `nao_modais`); janela nova desse tipo, cadastre lá em vez de fechá-la.
- ⛔ **Digitar só com `maos.digitar_em(hwnd, texto, *teclas)`**, que confere a janela da frente ANTES de cada tecla e
  levanta `ForaDeFoco`. O `digitar` solto mandou um caminho + Enter para o MC quando o diálogo de arquivo demorou a
  abrir: as letras viraram atalhos (T, Z = Lift…), a timeline foi levantada e o autor a recuperou pelo Undo
  (2026-10-13). Diálogo de OUTRO processo (PowerShell/Explorer) não aparece em `olhos.dialogos(exe)`: ache pelo título.
- ⛔ **O catálogo só reconhece na escala de monitor (0,75–1,34)**: um aviso de 482×113 bateu com uma foto de 753×179 a
  0,64 e o cão de guarda clicou no vazio por 10 min (2026-10-13, corrigido no `reconhecer`). Aviso do MC no 2º monitor
  com o título "Avid Media Composer" é diálogo como qualquer outro: foto e parar.
- ⛔ **`~/.claude/skills/piloto` é uma JUNÇÃO (Windows) / um symlink (Mac) para esta pasta**: editar aqui já vale lá.
  NUNCA copie o `SKILL.md` de um lado para o outro — `cp` sobre o mesmo arquivo o TRUNCA (zerou esta skill duas vezes,
  2026-10-13). Ligar numa máquina nova: `bancodedadosnles/skills/instalar.py`.

## No Mac (medido 2026-10-14, macOS 15.6.1, Resolve 21.1, monitor 1920×1080 escala 1)

- **Permissões do TERMINAL** (o processo responsável, não o Python): Acessibilidade (teclas, cliques, diálogos) e
  Gravação de Tela (fotos e títulos). `olhos.permissoes()` diz o que falta — sem elas o clique some CALADO e a foto sai
  só com o papel de parede.
- O "hwnd" é o **número da janela do macOS** (CGWindowID). `janelas()` vem da FRENTE para trás; `classe` = subrole da
  acessibilidade; `tem_dono` = é diálogo (AXDialog/AXSystemDialog ou modal — o Project Settings do Resolve é
  `AXUnknown` + modal).
- **Pontos × pixels:** o clique vai em PONTOS, a foto sai em PIXELS. `relativo(hwnd, x, y)` (medido na foto da
  janela) e `da_foto(x, y)` (na foto da tela) já dividem por `olhos.escala()`. Numa tela Retina (2×) **recalibre**
  antes de confiar: só a escala 1 foi medida.
- **Teclas**: códigos do Mac nas constantes (`ENTER`, `ESC`, `CMD`, `ALT` = Option…) ou um caractere: `tecla("s", CMD)`.
  O Ctrl dos atalhos do Windows costuma ser o **CMD** no Mac.
- **Freio do mouse** (só no Mac): o cursor fora de onde o piloto o deixou = o autor voltou → `Parado`. Depois de um
  `Parado`, `maos.soltar_freio()` para operar de novo. O F12 é o do teclado FÍSICO (o sintético não aciona; teclado
  Apple pode precisar do fn).
- `frente(hwnd)` = AXFrontmost + AXRaise e confere pela janela de TECLADO (`olhos.janela_da_frente()`); ~1 s.
- ⛔⛔ **Tecla para "o app da frente" (`tell application "System Events" to key code …`) com o TERMINAL na frente
  vai para a sessão do Claude Code: o Esc INTERROMPE o turno** (2026-11-05 — três comandos "rejeitados" sem o autor
  ter tocado em nada). Antes de toda tecla sintética, confira o app da frente por `lsappinfo info -only name
  \`lsappinfo front\`` (a pergunta `frontmost` ao System Events MENTE) e não tecle se for o Terminal; diálogo se fecha
  pelo BOTÃO (acessibilidade) ou com a tecla entregue ao PROCESSO.
- ⛔ **`choose file`/`choose folder` do `osascript` nasce SEM o foco do teclado** (processo de fundo): o diálogo tem
  de ser aberto DENTRO de `tell application "System Events"` + `activate` (Ciclo Assist `servico/seletor.py`).
- `olhos.fechar(hwnd)` sem foco: botão de fechar/Cancelar pela acessibilidade; o Qt do Resolve não os expõe → Esc
  entregue AO PROCESSO (`CGEventPostToPid`).
- A variante "por título" do Premiere no Mac é a do laboratório (`lab/bancadas/vigia_dialogos.py`).

### No Mac com os três NLEs (medido 2026-10-24: MC 25.12, Premiere 2026, Resolve 21.1 — abertos juntos, o que no Mac pode)

- ⛔ **Abrir app SEMPRE por `apps.abrir(chave)`** (tira o `LANG`/`LC_*` da sessão). O MC aberto por `open -a` do
  terminal herda `LANG=pt_BR.UTF-8` e ABORTA na tela de abertura (aviso "encerrou inesperadamente"; pode clicar OK).
  Gadget do Frida: `apps.abrir("avid", {"DYLD_INSERT_LIBRARIES": "~/ferramentas/frida-gadget/frida-gadget.dylib"})`.
- MC: todas as janelas dele são `AXDialog` (a principal também); o piloto trata a MAIOR não modal como principal.
- Premiere: processo "Adobe Premiere Pro 2026" (`apps.processo` = prefixo `"Adobe Premiere Pro*"`), dono das janelas
  "Adobe Premiere"; a tela inicial é janela FLUTUANTE (camada 3); a acessibilidade não diz a janela da frente (o piloto
  usa o `lsappinfo`). Pode pedir LOGIN da Adobe ao abrir — trava rodada sozinha: foto e parar.
- **Menu pelo NOME** (System Events) é firme; o clique sintético no menu do Premiere não abriu:
  `osascript -e 'tell application "System Events" to tell (first process whose unix id is <pid>) to click menu item "<item>" of menu 1 of menu item "<sub>" of menu "<menu>" of menu bar 1'`.
  Ler o "Desfazer" (`get name of menu item 1 of menu "Edit"`) confere se um gesto editou algo.
  ⛔ **Fechar o Premiere: pelo MENU, não por AppleEvent.** Na tela inicial o `tell application "Adobe Premiere Pro
  2026" to quit` ficou sem resposta (timeout -1712, 2026-10-28); `click menu item "Sair do Premiere" of menu 1 of menu
  bar item 2 of menu bar 1` fechou em 2 s. O item tem o nome do idioma do sistema — leia os nomes antes de clicar.
- **Arrasto entre apps funciona** (CGEvent): arraste com o app de ORIGEM já na frente — o 1º gesto num app de trás só
  o ativa. Sonda: `piloto/sondas/arrasto_nativo_mac.swift`. Saem: Finder, bin e timeline do Premiere, bin do MC,
  timeline do Resolve. Ficam dentro: segmento da timeline do MC, Media Pool do Resolve (sintético).
- ⛔ **Cmd+clique sintético (`_mouse(…, bandeiras=0x100000)`) deixa o Command PRESO** (2026-11-12, Premiere 26.0.2): os
  cliques simples seguintes SOMARAM à seleção da bin e o arrasto levou a seleção antiga junto. Depois de todo clique
  com modificador: `_tecla_crua(CMD, True)` + `_tecla_crua(CMD, False)` (com o app certo na frente — `lsappinfo front`).
  Seleção do Premiere se confere pela ponte, não pelo realce da foto.
- Janela FIXADA no topo (o pino do Ciclo Assist) sobe de camada e SOME de `olhos.janelas()`: use o retângulo lido antes.
- ⛔ **Diálogo "Save changes…" do Premiere (23.6) ATRÁS do Terminal** (2026-11-15): `frente(hwnd do diálogo)` devolveu
  False e o clique caiu no TERMINAL (sem efeito, por sorte). O que trouxe: `tell application "System Events" to set
  frontmost of (first process whose unix id is <pid>) to true` + conferir `lsappinfo front` ANTES do clique. O botão
  não aparece na acessibilidade (`click button "No" of window 1` = índice inválido). ⛔ E a foto da JANELA do diálogo
  (`fotografar`) deu o "No" 23 px acima do real: meça num recorte da TELA (`screencapture -R x,y,w,h`), não na foto da
  janela pequena. Fechar o Premiere sem salvar: Quit pelo id do app → o diálogo → No pela tela.
- ⛔ **`frente(hwnd)` devolveu True e o app da frente era "Python"** (2026-11-15, janela do Ciclo Assist/Tauri): o
  próprio processo do piloto ficou na frente. Conferir `lsappinfo front` NO MESMO script, logo antes do clique, e
  abortar se não for o app certo (o clique teria caído noutro lugar). Firme: `set frontmost of (first process whose unix
  id is <pid>) to true` pelo System Events, 1,5 s, conferir, clicar.
- ⛔ **O Cmd+Shift+G do diálogo de arquivo deixa o SHIFT preso** (2026-11-23, janela do Ciclo Assist/Tauri): os
  cliques seguintes no app viraram Shift+clique (a seleção de texto crescendo a cada clique) e nem a roda nem o Page Down
  rolavam a página. Depois de todo `tecla(…, CMD, SHIFT)`: `_tecla_crua(SHIFT/CMD, True)` + `False` com o app certo na
  frente. E rolar o WebView arrastando a BARRA de rolagem pegou quando a roda não pegava. No diálogo do `choose file` o
  Enter não confirmou o arquivo selecionado: clique no botão "Escolher" (o ponto pela foto da tela).
- ⚠️ **Seleção de vários itens na bin do Premiere (lista): Shift+clique, não Cmd+clique** (2026-11-12, 26.0.2 Mac): três
  Cmd+cliques sintéticos seguidos selecionaram itens ERRADOS (o CAM1 e uma linha que não foi clicada); clique no
  primeiro + Shift+clique no último (`_mouse(…, bandeiras=0x20000)`) pegou o intervalo exato. Soltar o modificador
  depois (`_tecla_crua`) e conferir a seleção pela ponte (`/premiere/selecao`).
- ⭐ **Ângulo ativo da multicâmera do Premiere** (gesto do autor, 2026-11-12, 26.0.2 Mac): duplo clique no ÍCONE da
  multicâmera na bin → o Origem abre o mosaico (1 trilha = 1 ângulo, 2–4 = 4, 5–9 = 9), borda AMARELA = ativo; um
  clique no ângulo troca; Arquivo › Salvar (menu pelo nome) grava o `TrackIndex`. ⚠️ Com DOIS projetos abertos a aba
  "Compartimento" pode ser do OUTRO projeto (o título da janela muda): confira o título antes de agir.
- ⛔ **Diálogo MODAL do Premiere (Mac): o `digitar_em(hwnd)` recusa** (2026-11-25, 26.0.2, "Arquivo offline"): a janela de
  teclado que o macOS informa continua a PRINCIPAL, e o `ForaDeFoco` sai sem digitar nada. As teclas chegam ao diálogo:
  conferir o APP da frente por `lsappinfo front` e usar `digitar`. Campo de TC (o valor azul) vira texto num clique; dígitos
  + Tab (o Enter aciona o OK). ⚠️ Item de menu do Premiere depende do PAINEL em foco: o "Arquivo offline…" vem
  DESABILITADO com o foco nos Controles de efeitos — clique na aba do painel Projeto e confira `enabled of menu item`.
- O diálogo "Selecionar uma Pasta" (osascript `choose folder`, dono "Eventos do Sistema"): `frente` + Cmd+Shift+G +
  `digitar(caminho)` + Enter entra na pasta; **Escolher** escolhe a pasta ATUAL (sem nada selecionado).
- MC: o nome de item novo na bin (sequência criada por Splice) nasce em MODO DE RENOMEAR — clicar no vazio da bin antes
  de qualquer tecla. Os botões amarelo/vermelho da barra da timeline são MODOS de segmento; Splice/Overwrite ficam
  embaixo do monitor.
- ⛔⛔ **O LAÇO na timeline do MC — as regras do autor (2026-10-28):**
  1. **Laço = arrastar com o Option (Alt no Windows) APERTADO.** Com ele o arrasto vira laço mesmo começando em cima de
     clipe ou filler, sem pegá-los. SEM o Option, o arrasto PEGA o que está embaixo: o "laço" de V4 até V1 arrastou o
     FILLER da V4 por cima de ~22 s da V1 (`Lift-Overwrite`, desfeito pelo menu Edit — o "Undo <nome>" diz o que foi
     feito; conferir ANTES e DEPOIS). O laço "puro" sem Option só existe começando FORA das trilhas (entre a trilha
     de cima e a régua de TC) — quase nunca usado.
  2. **Só entra o segmento INTEIRO dentro do laço;** o que fica parcialmente fora não é selecionado (há uma opção de
     User Profile que muda isso — o autor não a liga).
  3. **Sempre da ESQUERDA para a DIREITA.** Da direita para a esquerda o laço seleciona PONTOS DE CORTE e entra no
     TRIM MODE — edição, nunca nos nossos testes (relink/conform).
  4. (medido) Laço DENTRO de uma trilha só (começo e fim na V1) não selecionou nada; o que funciona é começar na trilha
     de CIMA e terminar ABAIXO da última (ex.: da V2 até abaixo da V1).
- MC, a timeline (autor + medidas, 2026-10-28):
  - **Trilhas:** seletor AZUL = trilha ligada, CINZA = desligada; o clique no seletor alterna. Com o PAINEL DA TIMELINE em
    foco, **Cmd+A liga todas as trilhas** e **Shift+Cmd+A desliga todas** (Ctrl no Windows) — NÃO selecionam clipes. (No
    teste de 28/10 o Shift+Cmd+A não pegou: o foco não estava no painel da timeline — clique antes num ponto VAZIO dela.)
  - **Limpar a seleção de clipes:** um clique simples num lugar VAZIO da timeline — de preferência o espaço entre a trilha
    de cima e a régua de TC superior (não mexe em nada); a trilha TC1 (entre vídeo e áudio) também limpa, mas MOVE a
    agulha para onde clicou.
  - **Marcas:** clique na régua de TC (só move a agulha) + DoCommand 6209 (IN) / 6210 (OUT); limpar as duas = DoCommand
    6214 (Clear Both Marks; a tecla padrão é G). O desenho no Avid é `]` no IN e `[` no OUT.
  - `Collapse` (DoCommand 6251) com SEGMENTOS selecionados junta a SELEÇÃO, não o IN/OUT.
  - DoCommand pelo Python do APP (`.venv` do De Lá Pra Cá): o venv do piloto não tem gRPC.
  - ⭐ **Bin/pasta escrita por fora (Órbita, DLPC, pyavb) não aparece no painel de bins até um SAVE** (autor, 2026-10-31,
    Win 2024.6): foco num lugar que NÃO seja a bin (um vazio da timeline) + **Ctrl+S** (Cmd+S no Mac) salva tudo e o
    painel passa a mostrar a bin/pasta nova. MEDIDO: a pasta `CENAS` do Órbita apareceu na hora. Fazer isso depois de
    toda escrita por fora, antes de procurar a bin na tela.
    ⛔ **Só com algo MODIFICADO** (2026-11-01): sem nada sujo, "Save All Bins" fica cinza e o Ctrl+S não grava nada.
    Bin do pyavb aberta pela API já fica suja (`*`). Conferir pela data do `.avp`, não pela foto.
  - ⛔ **A foto da JANELA (`PrintWindow`) não mostra menu aberto** (2026-11-01): o menu é outra janela de topo. Para
    ler menu/lista suspensa, foto da TELA (BitBlt da área virtual).
  - ⭐ **Toggle Source/Record in Timeline** (autor, 2026-10-31, Win 2024.6): o ícone na barra de baixo da timeline, à
    direita do ⊙. **Verde** = a timeline mostra o que está no SOURCE (clipe ou sequência); apagado = a do RECORD (a
    sequência ativa). Verde no MC = Source, azul = Record. No modo Source só se marca IN/OUT e liga/desliga trilha —
    nada se edita. Serve ao piloto para VER um clipe trilha a trilha (offline = vermelho) e a forma de onda do áudio
    (ligar no menu ☰ do canto inferior esquerdo da timeline).
  - ⛔ **MC 2024.6 Windows: não há DoCommand pela ponte do Ciclo Assist** (`McApiNaoImplementado`), e o Exit da
    bancada é ignorado calado. Sair = menu **File → Exit** (com o MC na frente, no mesmo comando) → "Leave the
    application?" → **Leave** (~10 s até o processo sumir; medido 3 vezes em 2026-10-31).
  - ⭐ **O projeto aberto está no TÍTULO da janela principal** (2026-11-01, Win 2024.6): `Avid Media Composer  - desktop`
    (DOIS espaços antes do hífen). É a prova de "o projeto abriu" sem API nem foto — `cicloassist/avid/abrir.py`.
    ⛔ Mas o título FICA VELHO depois de **File → Close Project** (continua "- desktop" com a Select Project na tela):
    com a janela "Select Project" visível, não há projeto aberto. E o título muda ANTES de terminar de carregar (a
    barra "Initializing Format pane" usa o título "AvidMediaComposer", o mesmo do aviso de teclado): pronto = título
    E nenhuma janela "AvidMediaComposer" visível.
  - ⛔ **A janela FIXADA no topo de quem pilota cobre o alvo** (2026-11-01, teste pelo chat do Ciclo Assist): o pino do
    app (always-on-top) escondeu o Create da Select Project. Antes de fotografar e clicar em outro programa, a janela
    do app sai da frente — `HWND_NOTOPMOST` E `HWND_BOTTOM` (só NOTOPMOST a deixa no alto da faixa não fixada) — e
    volta como estava no fim, sem ativar (`cicloassist/piloto/espaco.py`). Provado: Create visível durante, pino de
    volta depois.
  - ⭐ **Rápido na Select Project (2026-11-01, Win 2024.6, `cicloassist/avid/abrir.py`):** o ESTADO sai dos títulos
    das janelas (de graça, a cada 0,5 s): fim do carregamento = janela "Select Project" visível; menu/lista suspensa =
    janela NOVA do processo (esperar por ela, nunca tempo fixo — 0,4 s depois do clique o File ainda não estava
    aberto). Uma pergunta acha TODOS os alvos da tela e as conferências rodam em paralelo (~7 s por tela, eram ~10 s
    POR CLIQUE). ⛔ Alt+F NÃO abre o File (apesar do F sublinhado). ⭐ Projeto na lista: a lista vem em ordem
    DECRESCENTE e corta o nome ("CICLO TESTE …") — procurar pela foto falha; clicar uma linha qualquer e DIGITAR o
    nome (busca do Qt) rola e seleciona, e quem diz se o projeto existe é a pasta em `Documents\Avid Projects`.
    ⛔ A barra de carregar ("AvidMediaComposer") some e VOLTA: pronto = título certo E nenhuma barra por 1,5 s.
    Medido: sair 25 s, trocar 41 s, abrir da Select Project 27 s — o resto é o MC carregando o projeto (~20 s).
  - ⭐ **Select Project / New Project no 2024.6 (Win, 2026-11-01, provado pelo Ciclo Assist):** a Select Project é uma
    JANELA PRÓPRIA (título "Select Project") que nasce ATRÁS da principal — focar a principal mostra um MC vazio, só
    menus. Abas **Projects** | **New Project** no alto; a lista abre com **Open** (rodapé, à direita de Quit); a aba
    New Project tem Project name, Format (lista ▸ HD 1080 ▸ 1080p/25, por clique) e **Create**. Trocar de projeto =
    File → Close Project (~3 s) → a Select Project volta. Medido: sair 37 s · abrir da lista 22 s · criar 58 s ·
    trocar 55 s; US$ 0,04–0,12 de localizador por operação.
  - ⛔ **Atalho que o usuário PERSONALIZA (G, Mark IN/OUT…) só serve ao PILOTO**, que conhece este Mac; no DLPC só vale
    atalho FIXO do MC (o Cmd+A/Shift+Cmd+A das trilhas) ou o DoCommand pelo id.
- Resolve: montar laboratório pela API (MCP `DaVinci Resolve`: `CreateProject`, `ImportMedia`, `CreateTimelineFromClips`)
  em vez de clicar.

## ⭐⭐ Agir SEM o mouse do sistema (spike 2026-11-04 — o cua-driver/Hermes medido; matriz, seção F)

O que dispensa coordenada de TELA, do mais firme ao mais frágil — use o primeiro que o app aceitar:
1. **API** (gRPC do MC, ExtendScript/CEP, API do Resolve) — continua a primeira.
2. **Premiere: menu NATIVO por ID** — `WM_COMMAND` com o id do item (lido de `GetMenu`), com o Premiere atrás e sem
   foco. Diálogo de arquivo: o caminho por `WM_SETTEXT` no Edit do combo 1148 + `IDOK` (sem teclado ⇒ sem ABNT2).
3. **Resolve: a UIA** — `InvokePattern`/`ValuePattern`/`TogglePattern` pelo NOME (botões, menus, campos), e o estado
   se LÊ (Project Settings inteiro). ⚠️ Traz o Resolve à frente. ⛔ O MC NÃO tem UIA (o `qwindows.dll` dele veio sem).
4. **Por mensagem** (`PostMessage` ao HWND mais fundo, ponto do CLIENTE): MC, Premiere e Resolve aceitam clique,
   duplo clique e tecla; Ctrl/Alt só com `AttachThreadInput` + `SetKeyboardState`. MC: menu por Alt+letra à BARRA e
   letra/setas ao popup (sem coordenada); a TIMELINE do MC só com ele ATIVO e o ponto na tela.
5. **`SendInput`** (o de sempre) — OBRIGATÓRIO para arrasto entre painéis e para o laço da timeline do MC (ele lê o
   botão FÍSICO). Laço com Alt pelo `maos.arrastar(..., modificadores=(ALT,))` ✅ no Windows (2026-11-04).
- **Foto coberta:** `fotografar(hwnd)` (`PrintWindow`) mostrou os três NLEs inteiros, cobertos e com parte FORA da tela.
⭐ No piloto (2026-11-05): `maos.msg_clicar(top, x_tela, y_tela)`, `msg_tecla`, `msg_rolar`, `comando_menu(hwnd, "File > Save")` (acha o id pelo NOME e RECUSA item cinza — o id fura a regra), `caminho_no_dialogo`; todas atrás do mesmo freio. `olhos.fotografar` recusa janela que não responde (a foto travaria). Sondas: `piloto/sondas/`. UIA do Resolve: ainda só sonda.

- ⛔ **Não embrulhe script do piloto no `timeout` do bash** (2026-11-05): `devolver_ao_terminal()` passa a dar False — o
  terminal é achado subindo a cadeia de processos, e o `timeout` a quebra. Use o prazo da própria ferramenta.
- ⭐ **MC sem coordenada:** Alt+letra à BARRA (`msg_tecla(barra, ord('F'), ALT)`), letra sublinhada ao POPUP; letra
  repetida (Close/Close Project) só move o destaque → foto do popup e Enter. Select Project: `msg_clicar` na lista +
  o nome por `msg_tecla(..., char=c)` + Open — 18 s sem localizador. Leave do Exit pelo ponto do catálogo.
- ⭐⭐ **MC abre SEM coordenada nenhuma, só teclado** (2026-11-09, MC 2024.6, confirmado, 3 de 3): com a Select Project focada o foco já está na LISTA; digitar
  o nome move a seleção (`SendInput` Unicode) e Enter abre (0,3 s até a janela sumir). Aviso de idioma: o foco nasce no OK, **Tab leva ao "Don't warn me again"**, Espaço aciona.
  Abrir do lançamento ao projeto: 47,5–48,7 s e US$ 0, contra 61–75 s e US$ 0,04–0,07 pela foto (`avid/abrir.py`). ⛔ Esperar ~1,5 s depois de focar: o aviso nasce com o foco e um espaço do nome o responderia.
  ⭐ Aviso e barra de carregar têm o mesmo título, mas a forma os separa: 518×190 (2,7:1) e 402×125 (3,2:1); a 125 % `pendente`.
- ⛔ **Na Select Project o menu File não abre** (a principal fica desabilitada, 2026-11-09): sair é o botão Quit, que faz a mesma pergunta "Leave the application?".
- ⛔ Com um diálogo aberto a API não responde e leva ~20 s para desistir (`GetAppInfo`, 2026-11-09): conferir as janelas antes de culpar o gRPC.

## Depois

- Diálogo novo, armadilha nova ou diferença de plataforma: registre (catálogo do piloto, banco, matriz com os dois
  lados). O piloto só fica bom se cada sessão deixar o que aprendeu.
- O que for de UM app (fluxos, posições de botão) fica em quem usa — a bancada do laboratório, o app —, não no pacote.
- **macOS:** pronto e medido no Resolve (2026-10-14); MC e Premiere medidos em 2026-10-24 (seção acima). Pendentes: catálogo `avid` com fotos
  do Mac — as do Windows têm outro desenho de janela), o Premiere pelo piloto, tela Retina e o F12 físico.
