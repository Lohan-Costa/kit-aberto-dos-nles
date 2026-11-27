# HANDOFF do estudo — a 2ª metade: tudo até o PRO TOOLS

Estado em 2026-11-25 (noite): 1ª metade fechada e publicada (`LEIA-ME.md`). O autor: "essa é a primeira metade do teste,
falta trazer tudo pra um Pro Tools pra fazer a transferência completa e tentar achar onde as informações se perdem".

## O que fazer
1. O AAF de cada caso, dos dois NLEs, com vídeo e só áudio → Pro Tools (Import Session Data). Conferir cada clipe:
   arquivo, trecho, canal. (Banco: o AAF do Premiere com merged só sai certo sem vídeo — medir aqui.)
2. O conform pela EDL (EDL + os WAV originais numa ferramenta de conform), comparado com o AAF.
3. O que o som direto carrega até a sessão: sound roll, cena/take, nomes dos canais (iXML).
4. A variante que as casas pedem: 1 vídeo com os cortes da cena + todo o áudio com os cortes da montagem (no Premiere, 2
   EDLs: canais 1–4 e 5–6 — casam?).
5. O placar NLE → EDL/AAF → Pro Tools; atualizar o relatório (uma página da 2ª metade, mesmo tema).

## Decisões pendentes (do autor)
- A versão do Pro Tools e a máquina; a ferramenta de conform por EDL.
- S10 (canais 3/5) e S11 (mesmo rolo) também no Premiere antes da transferência? (o canal 3/5 exige o mapeamento de canais
  do clipe). O collapse (S9) foi adiado.
- Opções do diálogo do Premiere ainda não medidas: "Usar rolagem de som/timecode de som", "Usar nome do arquivo de
  origem"; no MC: Reel ID Type `Source File`/`Tape`, as opções de Source TC para o som. Um caso SEM jam (sync por claquete).

## Cuidados (pagos nesta metade)
- Premiere: merged e multicâmera estão em `app.project.sequences` — nunca `deleteSequence` em lote.
- Premiere: `importFiles` na RAIZ seleciona; a entrada vai nos SELECIONADOS (o nome acha o item antigo).
- MC: List Tool — conferir a fileira de trilhas (Input › Tracks) antes de todo Preview; o botão alterna.
- MC: som direto se INJETA (`autorar_masters`), não se linka (o modal "Audio Start-Time Options" a cada WAV).
- Laboratório (`laboratorio-de-midia`) tinha pendências que NÃO são desta sessão (fim de linha do Windows, provável):
  não commitar do Mac sem conferir com `-c core.autocrlf=true`.
