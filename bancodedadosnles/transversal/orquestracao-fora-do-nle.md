# Orquestrar fluxos FORA do NLE: Griptape, MCP nos dois sentidos, central com avisos e porteiro

> Medido em 2026-11-20, Windows 11, pelo estudo `1 IDEIAS/GRIPTAPE E CICLO ASSIST` (5 provas, cada uma com
> `LEIA-ME.md` em `provas/`). Versões: **griptape 1.13.0** (framework), **griptape-nodes 0.112.0** (motor; app
> 0.105.1; biblioteca padrão 0.91.1; editor web v131), **mcp 2.3.0** (Python), cérebro **Ollama 0.33.3 /
> `qwen3-vl:8b-instruct`** no Mac mini M4 16 GB da LAN. Nada aqui tocou o Ciclo Assist real.

A pergunta da família: um app nosso (o Ciclo Assist) pode conversar com um ORQUESTRADOR de fluxos que coordena
várias máquinas e dá acesso a ferramentas pagas da empresa, sem que cada estação tenha conta e chave? Resposta
medida: sim, com quatro peças — e com regras que valem para qualquer orquestrador, não só o Griptape.

## 1. O Griptape são duas coisas (e só uma pede conta) — `confirmado`

| peça | o que é | conta |
|---|---|---|
| framework `griptape` | biblioteca Python: `Agent`, `Pipeline`, `Workflow` (DAG com ramos paralelos), ferramentas `BaseTool` + `@activity` | nenhuma. `OllamaPromptDriver(model, host="http://IP:11434")` fala com o Ollama da rede |
| Griptape Nodes | **motor** local (`uv tool install griptape-nodes`) + **editor** web (`app.nodes.griptape.ai`) | API key da Griptape Cloud (a conta GRATUITA bastou para tudo aqui) |

- Motor sem perguntas: `griptape-nodes init --no-interactive --api-key gt-… --workspace-directory <pasta>
  --storage-backend local --no-register-diffusers-library --no-register-griptape-cloud-library`; ligar:
  `griptape-nodes engine`. ~0,66 GB no disco (motor 313 MB + área com a biblioteca 328 MB).
- O motor escuta SÓ em `127.0.0.1` (8124 e **8125 = MCP**). O editor web acha o motor **pela nuvem da Griptape**
  (nenhuma porta aberta na rede): os comandos do editor trafegam por ela (`inferido`). O MCP local não passa por ela.

## 2. ⭐⭐ O motor do Griptape Nodes FALA MCP — para fora e para dentro — `confirmado`

- **Para fora:** servidor MCP próprio em `http://127.0.0.1:8125/mcp/`, **53 ferramentas** — tudo o que o editor
  faz (criar fluxo/node, ligar, `SetParameterValue`, `StartFlow`, salvar, `AutoLayoutFlow`). Um fluxo montado por
  um cliente MCP (5,7 s) apareceu **igual no editor**, com o resultado; mudança feita pelo MCP apareceu na hora no
  editor; o ▶ do editor rodou o mesmo fluxo. ⇒ **a IA monta, o profissional vê e ajusta.**
- **Para dentro:** `CreateMCPServerRequest` (transporte `streamable_http`, `url`, `headers`) cadastra um servidor MCP
  de fora; o node `MCPToolNode` → `ToolList` → `Agent.tools` dá ao agente TODAS as ferramentas dele. Um "Assist de
  mentira" (MCP, `listar_midias` / `procurar_som_do_clipe` / `sincronizar`) foi usado certo 2 de 2 (6 chamadas, sync
  dos 3 clipes certos, 27,5 s com Qwen 8B).
- Fluxo salvo = **arquivo `.py`** (versionável) — e ⚠️ leva DENTRO a última execução (pedido, resposta, conversa do
  agente): com material de cliente, isso viaja com o arquivo.
- Biblioteca padrão: 307 nodes; `OllamaPrompt` (e Anthropic/OpenAI/Bedrock), `MCPToolNode`/`MCPTaskNode`,
  `ExecutePython`, laços, `RetryGroupNode`, arquivos, 60 de vídeo (inclusive Seedance, pago). O `Agent` vem com
  provedor `griptape_cloud` e modelo Claude por padrão (cobrado): ligar um `OllamaPrompt` em `model` troca.

### Armadilhas do motor 0.112.0 — `confirmado`

| armadilha | o que fazer |
|---|---|
| `EnsureWorkflowAndFlowRequest` com `workflow_name` só abre fluxo JÁ SALVO | sem nome abre um novo (`unsaved:<id>`) |
| com mais de um cliente aberto (o editor), o pedido MCP sem fluxo falha: "names no workflow" | cabeçalho HTTP **`X-Griptape-Workflow-Id: <id>`**; sem ele vale o que a sessão MCP abriu |
| ⛔ `StartFlowRequest` pelo MCP **volta em ~30 s com o fluxo ainda rodando** (sem erro, resposta vazia) | esperar o node final `RESOLVED` (`GetNodeResolutionStateRequest`), com prazo |
| ⛔ `DiscoverMCPServerCapabilitiesRequest` declarado mas **sem handler** ("No manager found"); o `griptape-nodes request` fica pendurado | não usar; o `MCPToolNode` conecta na hora de rodar |
| `griptape-nodes request` não acha o motor padrão do `~/.local/share/griptape_nodes/engines.json` | `GTN_ENGINE_ID=<default_engine_id>` |
| a saída do `request` é formatada (rich) e quebra linha a 80 colunas DENTRO das strings | `COLUMNS=100000`, `json.loads(..., strict=False)`, ler `payload.result` |
| `CreateMCPServerRequest` não está entre as 53 ferramentas do MCP do motor | pela CLI (`request`) ou pelo editor |
| `mcp` 2.x: `FastMCP` virou `MCPServer` (`mcp.server.mcpserver`) | host/porta no `run(transport="streamable-http", host=, port=)` |

## 3. ⭐⭐ A central com AVISOS: esperar horas sem segurar nada — `confirmado`

Uma central (agente Griptape) coordenando 2 máquinas (ingest 60 s → MC sync 5 s), cenários normal / falha /
central derrubada no meio da espera:

- **Contrato máquina ↔ central:** pedir = resposta IMEDIATA com id; terminar = **AVISO** (POST) com estado e
  resultado; **o aviso se repete até ser entregue** (5 s). Com isso a queda da central não perde trabalho: entregue
  na 4ª tentativa ao processo novo, que seguiu pela conversa em arquivo.
- Entre um aviso e outro NINGUÉM espera: cada evento acorda um agente novo; a conversa mora num arquivo
  (`LocalConversationMemoryDriver`). Normal: 88 s de rodada, **24,6 s de modelo** — 6 h de conversão custariam o mesmo.
- Falha: o agente não pediu o passo seguinte e explicou o problema ao editor.
- ⛔⛔ O achado de desenho está em [modelo-de-execucao-de-agente.md](modelo-de-execucao-de-agente.md) (o estado do
  fluxo é do CÓDIGO): a memória do Griptape guarda só TEXTO e o Qwen 8B "disse que pediu" sem pedir.

## 4. ⭐⭐ O porteiro: quem pede, o que pode, quanto tem — `confirmado` (prova; login de verdade `pendente`)

O Griptape não separa usuários (uma chave por motor; MCP sem senha). Um porteiro NOSSO na frente (stdlib + SQLite,
22/22 cenários): **token → grupo → saldo** antes de o pedido seguir; 401/403/404/402 vão ao livro-caixa também.

- O editor **não monta fluxo**: recebe um **cardápio** de serviços prontos (montados por administradores) com preço
  `fixo`, `por_segundo` ou `por_mil_tokens`. Moeda do autor: **estaleca, 1 = R$ 1**, guardada em milésimos (inteiro).
- **Permissão por GRUPO**, nunca por pessoa — no produto, os grupos do **Microsoft Entra ID** (mudou de equipe /
  desligado → o acesso acompanha sem mexer no porteiro). Token simples na prova.
- **Reserva + cobrança (pré-autorização):** reserva a estimativa (segundo começado, para cima) DENTRO da mesma
  trava que decide; cobra o uso REAL no fim; falha devolve tudo. Medido: 2 upscales simultâneos que juntos passavam
  do saldo → um 202, outro 402; reservou 7, cobrou 6,4.
- ⛔ Erro pego pelo placar: a cobrança usava a fórmula ARREDONDADA da reserva. São duas contas.
- Só vale se for a **única porta**: motor aceitando só o porteiro, conta e chaves de provedor só com administradores.
- Independente do orquestrador: serve na frente do ComfyUI, de uma API direta ou de um serviço da casa.

## 5. O que o Ciclo Assist precisaria (proposta — nada feito lá)

1. O MCP dele acessível ao orquestrador por HTTP (`streamable_http`) com token — hoje serve o CLI do Claude local.
2. Tarefas longas respondendo na hora com id; AVISO de fim para fora, com nova tentativa (o canal de progresso que
   ele já tem para a janela, mandado também para fora).
3. As ferramentas que mudam algo com a guarda DENTRO delas (como o `sincronizar` que recusa clipe sem som).
4. Cada estação mandando o pedido ao porteiro com a identidade de quem está nela.

## Ver também

- [modelo-de-execucao-de-agente.md](modelo-de-execucao-de-agente.md) — o estado do fluxo é do código.
- [cli-do-modelo-como-motor.md](cli-do-modelo-como-motor.md) §10 — o Ollama do Mac mini na rede.
- [matriz-de-plataforma.md](matriz-de-plataforma.md) §E — `python -I` ignora `PYTHONIOENCODING` (redescoberto aqui).
- [mapa-de-portas.md](mapa-de-portas.md) — 8124/8125 do motor, 7850–7853 e 7860 das provas.
