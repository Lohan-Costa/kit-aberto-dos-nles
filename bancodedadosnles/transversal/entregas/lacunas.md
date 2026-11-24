# Entregas × apps — o que já atendemos e o que falta mapear (2026-10-04)

> ⚠️ **Manual é GUIA, não lei** (autor, 2026-10-04): pode estar errado, impreciso ou desatualizado; serve para
> direcionar a entrega e a conversa com a casa, e é maleável. Nada daqui vira requisito duro de app: no máximo
> opção, preset ou aviso que a pessoa ajusta — e sempre se combina com a casa da vez.

Cada linha da `matriz.md` que um app da família pode tocar. Estados: **auto** (o app faz) · **opção** (o app
faz se o editor marcar) · **pessoa** (decidido: fica com gente — não automatizar) · **lacuna** (dá para fazer,
ainda não existe) · **fora** (não é de app nosso). Decisões do autor citadas pela memória.

## De Lá Pra Cá (Avid/Premiere → Resolve, e a volta)

| Exigência (matriz) | Estado | Nota |
|---|---|---|
| Nada offline; casar com os originais; mídia não usada fora | auto | o relink pelos originais; prontidão + trava antes de montar (2026-10-04) |
| Achatar multicam | auto | |
| Nest/compound | **opção** | padrão = compound (autor); para QC/QN/TE, desmarcar → nest aberto em trilhas |
| Efeitos no clipe (zoom/crop/posição/flip/retime/reverso/keyframes) | auto | inclusive em nest/multicam ("o efeito vale para a imagem vista") |
| Camada de ajuste do Premiere | **lacuna** (a medir) | as casas proíbem efeito em adjustment layer; o leitor ainda não diz o que faz com ela |
| Markers do que a casa precisa saber (refazer/conferir) | auto | marcador de timeline com duração do plano (spanned) + cor local |
| Markers por TIPO de interferência (resize, flip, crop, retime %, comp, motion) | **lacuna** | CJ/TE pedem um marker por efeito com o nome do efeito; temos os dados (o leitor sabe cada efeito) |
| Lista de markers TXT/PDF | **lacuna** | o Avid gera; no Resolve, o app poderia gerar a lista do relatório |
| **Trilhas por função** (BASE/CONFORM/RETIME/…) | **lacuna** | o app sabe o que cada plano tem; uma opção "organizar trilhas por função" com o esquema da casa |
| Cortes falsos | **lacuna** decidida | juntar SÓ com pré-check de atributos (autor, 2026-10-03) |
| TC de início | auto | o da origem (Premiere `ZeroPoint`; Avid ainda 01:00:00:00 — mapear todos os formatos, pedido do autor) |
| Cabeça, bipes, rolos | **pessoa** | memória `separacao-por-rolos-e-humana` |
| Vídeo de referência na timeline | auto/opção | achado (só no .prproj) ou indicado (os 4 formatos); som A/B; trilha de cima, desligada — o que foi medido por formato: [abaixo](#vídeo-de-referência-por-formato-de-entrada--o-que-foi-medido-no-resolve) |
| Burn-ins / gerar a referência | **fora** | export do editor; o app pode CONFERIR (ex.: a referência tem a mesma taxa e o mesmo TC da timeline?) — **lacuna leve** |
| Timeline só de VFX + planilha (QC/QN) | **lacuna** | pedido do autor: importar a lista do coordenador de VFX |
| Material de arquivo sem espaço/caractere especial | **pessoa** | o autor decidiu: sem aviso de nome (2026-10-03) |
| Media Management, color management, LMT | **fora** | configuração do Resolve da casa |
| Áudio na timeline de cor | opção | "trazer o áudio" desmarcável; som só da referência (opção B) |
| Fades, crossfades e keyframes de volume (som) | auto | Premiere → Resolve: volume fixo e animado, crossfades (2026-10-04) |
| Pistas de som por conteúdo / distribuição de canais | **lacuna** (talvez) | só se um dia o app entregar para som |
| EDL de vídeo/som/diálogo (CLIP NAME, FILE32/129, sem bipes) | **lacuna** ⭐ | nenhum app nosso escreve EDL hoje; o painel diz "EDL: em breve". Os pulls automáticos da Netflix (conform e VFX) só leem EDL File32/129 limpa ou CSV: gerar isso da timeline encaixa direto |
| Conferência pela IMAGEM | auto (diferencial) | o Conform Pull da Netflix não tem ("perceptual conform: TBD"); ele só avisa multimatch e casa o Tape "fuzzy" |
| Mudança de corte: só o que mudou + referência nova | auto (Resolve) | o "Atualizar timeline" faz o lado de quem RECEBE |
| Mesma taxa do começo ao fim | auto (aviso) | o writer avisa taxa não medida |
| TC de início por destino (hora 0 Netflix/Telepacífico · hora 1 EBC/PBS/Network 10 · hora 10 CBC/RTÉ/C4/PBSd) | **lacuna** (preset) | hoje: o da origem (decisão do autor). Um preset "destino" seria OPÇÃO, nunca imposto; a tabela está em `matriz.md` §9.1 |
| Conferir o TC do arquivo exportado (o Telepacífico manda olhar no MediaInfo) | **lacuna leve** | o app já lê TC com ffprobe: dá para pôr no relatório "o master começa em X" |
| EDL para Conform Pull Netflix (Tapename = nome do clipe sem extensão, 1 trilha, sem efeitos) | **lacuna** ⭐ | junta com a linha EDL acima; os ajustes de export de Avid e Premiere que a Netflix pede estão na ficha |

## Vídeo de referência por formato de entrada — o que foi medido no Resolve

Consolidado em 2026-11-18 a partir do handoff do De Lá Pra Cá (arquivado em `9 ARQUIVADOS/_DeLaPraCa/.dev/HANDOFF.md`,
entradas de 2026-10-09 a 2026-10-19); hoje o código é o módulo **Conformar** do Ciclo Assist. Destino: Resolve
**Studio**, API externa. Todo formato passa pela MESMA tela "antes de montar" (organograma de 2026-10-19, "um fluxo
para todo protocolo"): a referência (MOV/MP4/MXF) entra numa trilha nova acima de todas, desligada; o som dela em
trilha nova (A), só ele (B) ou nenhum; e a conferência pela imagem vem marcada.

| entrada | referência | achada sozinha na timeline? | medido como | resultado | confiança |
|---|---|---|---|---|---|
| `.prproj` | sim | **sim** (`motor/prproj/leitura._referencia_na_timeline`) | janela real do app, vários casos | trailer 144/144; filme de 588 planos 1.144/1.144 pontos (também no Resolve **21.1**); B22 6/6 | `confirmado` (19.1.4 e 21.1) |
| AAF | sim | não — indicar à mão | janela real do app (2026-10-19) | LAB_CORTES_01 7/8 (o 8º passa do fim do render do MC: não é erro); B22 6/6; produção real 107/110 pela bancada | `confirmado` (19.1.4.11) |
| bin `.avb` | sim | não — indicar à mão | só pelo roteiro `tools/bancada_resolve/e2e_protocolo.py` | LAB_CORTES_01: a mesma lista de 14 clipes, 7/8 | `confirmado` pelo serviço · a janela é `pendente` |
| Carta Aberta `.json` | sim | não — indicar à mão | só pelo mesmo roteiro | LAB_CORTES_01 7/8 | `confirmado` pelo serviço · a janela é `pendente` |

- ⚠️ **Todas as medições são de antes da mudança para o Ciclo Assist (2026-11-07)**, no repositório do De Lá Pra Cá.
  Repetidas no Conformar em 2026-11-19 (abaixo).
  - ⭐ **Remedido inteiro (2026-11-19, Windows 11, Resolve Studio 19.1.4.11, dentro do Ciclo Assist)**, os mesmos
    arquivos de 19/10 (`laboratorio-de-midia/saida/protocolos/`), resumos em
    `laboratorio-de-midia/resultados/B23_PROTOCOLOS/2026-11-19_WINDOWS_CONFORMAR/`: LAB_CORTES_01 **7/8** nos quatro
    (bin, AAF, AAF marcado, Carta), B22 **6/6** no `.prproj` e no AAF do Premiere; listas e planos iguais. `confirmado`.
    - ⛔⛔ **Regressão achada e consertada no caminho:** o AAF do Premiere deu **0/6** ("o programa não exportou o
      quadro"). Desde 28/10 o `.drt` começa a timeline no TC da ORIGEM (o B22 começa em 00:00:00:00), e o plano da
      conferência dos protocolos AAF/bin/Carta continuava fixo em 01:00:00:00: a agulha ia uma hora adiante, para fora
      da timeline. ⇒ **Regra:** quem planeja pontos numa timeline tem de usar o MESMO início que quem a escreve
      (`sessao_receber._inicio_da_timeline`, teste `test_inicio_da_conferencia.py`). Origem do Avid em 01:00:00:00 não
      denuncia o defeito: só uma origem que começa noutro TC.
    - A LAB_CORTES_01 sai com **15 clipes** (eram 14) porque o `LAB_CORTES_01.mxf` tem 2 pistas de som mono e, desde a
      soma dos streams (`cfcab5f`, 28/10), o som da referência entra em 2 trilhas. Não é defeito.
- ⚠️ AAF, bin e Carta no Resolve **21** não foram medidos (só o `.prproj`).
- ⚠️ XML, EDL, OTIO e `.drt` não são entrada (o XML aparece só como formato de export, "em breve").
- As peças de API que a referência usa (trilha nova desligada, som em trilha nova, ler a timeline por fora, o marcador
  da conferência) estão em `plugins/resolve-scripting/api-scripting.md`, `confirmado` no 19.1.4.11.

## Boas práticas que valem para o editor (checklist, sem app)

- Pedir a tech spec da casa ANTES do turnover e fazer o **teste de workflow** com material real de 2 diárias (12).
- Combinar a taxa final com a finalização antes da pós de som (DB 19).
- Nunca renomear mídia depois de entrar na timeline; nada de "Versão Final" no nome (data AAAAMMDD).
- Referência: a casa de som recusa H.264 e 2K/4K (DB); a de cor aceita (QC QN).
- Handles e embedded/não embedded variam por casa de som: perguntar (150 q · 5 s · 10 s).
