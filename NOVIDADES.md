# NOVIDADES

O que mudou no kit, do mais novo para o mais antigo, em linguagem de quem edita. A skill `ciclo-novidades` lê este
arquivo para resumir à pessoa o que chegou desde a última vez. O histórico completo está nos envios do GitHub (cada um
começa por `adicionado:`, `corrigido:` ou `mudado:`) e na seção "Últimas atualizações" da página.

## 2026-11-25 — o primeiro retorno da comunidade

- **Corrigido:** a bancada do Media Composer roda no Mac (a API: preset, export, import, montar sequência). O cliente da
  API vem do app aberto (`ciclo-assist-kit-nle`, clonado dentro do kit); abrir o programa e criar projeto pelo piloto
  segue só no Windows, e a bancada diz isso em vez de quebrar.
- **Corrigido:** um teste do laboratório lia o ffprobe em CSV e falhava com o ffprobe 9.0.2, que repete a linha do
  stream; agora lê em JSON.
- **Adicionado:** crédito para quem colabora. Antes de enviar uma contribuição, o seu Claude pergunta se você quer
  aparecer (o @ do GitHub ou um nome) ou ficar anônimo; quando ela entra no kit, a página mostra "com a colaboração
  de…" ao lado da mudança.
- **Adicionado:** o robô da máquina limpa — a cada envio (e toda segunda), um Mac e um Windows recém-criados pelo
  GitHub instalam o ffmpeg, ligam as skills, geram e conferem a mídia sintética e rodam os testes do zero, com o
  Python 3.9 e o 3.12. Pega instrução quebrada antes de uma pessoa tropeçar nela.
- **Corrigido:** na página, a data das últimas atualizações invadia a etiqueta ao lado (agora "25 nov. 2026").
- **Mudado:** o README diz em que máquinas o kit é testado. Mac Intel: não temos máquina — o que se sabe dele vem da
  comunidade.
- Os testes do laboratório que falhavam sem os arquivos de referência (relato de 24/11) já tinham sido resolvidos no
  envio de 25/11 (os projetos e máscaras sintéticos do laboratório entraram no kit).

## 2026-11 — a primeira versão

- **Adicionado:** o banco dos NLEs (formatos AAF, XML, OTIO, EDL, ALE, AVB, PRPROJ, DRT, DRP, FLE, BLG; as APIs e o
  ambiente de cada programa, no Windows e no macOS), o piloto com o vigia, o laboratório de mídia sintética, as skills
  do kit e a quarentena de contribuições.
- **Adicionado:** a página do kit e a porta de entrada (`COMECE-AQUI.md`).
- **Adicionado:** o app aberto Ciclo Assist, em repositório próprio (`ciclo-assist-kit-nle`), clonado dentro do kit.
