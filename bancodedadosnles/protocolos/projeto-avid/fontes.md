# Fontes — projeto Avid (`.avp`, projeto em rede, binlock)

Rastreabilidade: de onde veio cada bloco de descoberta deste protocolo.

## 2026-08-20 — sessão de análise de projeto em rede + binlock

**Amostras**

| amostra | o que é | onde |
|---|---|---|
| `TESTE ATALHO/` | projeto **criado em rede com binlock**, copiado para disco local com o `.lck` junto. MC 21.12.10 / Windows. Usuário `usuario-rede`, estação `ESTACAO-01` | `MIDIAS DE TESTES/TESTE ATALHO/` |
| `PRODUCAO-A/` | projeto **100% local**, 68 bins, criado no macOS (MC 23.3.1) e editado no Windows (MC 23.3) | `MIDIAS DE TESTES/_PROJETOS EM ANDAMENTO/47_PRODUCAO-A/_PROJETO/01_EDIT/PRODUCAO-A/` |
| `ORBITA - TESTE/` | projeto local em MC 25.6.0.58781 / Win 11 | `Documents/Avid Projects/ORBITA - TESTE/` |

**Método**

- Cabeçalho do `.avp` parseado à mão com o layout de [../avb/dados/avb-header.json](../avb/dados/avb-header.json),
  campo a campo, e comparado byte a byte com o `.avb` do mesmo projeto → revelou o `ATpj`.
- `pyavb` 1.4.0 aberto contra os dois `.avp` → `AssertionError`, rastreada até
  `avb/file.py:162`.
- Tabela de objetos percorrida (`fourcc + u32 size + data`) até `num_objects`, o que expôs os
  9.630 bytes de sobra no `.avp` do PRODUCAO-A.
- Estrutura de pastas dos dois projetos comparada arquivo a arquivo; `.avp` e `Settings.xml`
  da raiz diffados contra os da pasta da estação (idênticos).
- `.lck` dumpado em hex e analisado: string inicial, contagem de zeros, e varredura de
  inteiros de 64 bits na faixa `0x00007f00_00000000`–`0x00007fff_ffffffff` (ponteiros
  user-mode do Windows) → 10 ocorrências, espaçadas de 16 em 16 bytes.

**O que veio de relato, não de medição**

O **ciclo de vida do `.lck`** (criado ao abrir, apagado ao fechar, remoção manual libera a
bin no último estado salvo, e o caso do lock órfão depois de um crash) é conhecimento de
prática do usuário, registrado em 2026-08-20. **Não foi reproduzido em bancada** — não havia
ambiente compartilhável disponível. O *formato* do arquivo é medido; a *semântica* é relatada.

**Correção que saiu daqui**

`../avb/dados/avb-header.json` campo 12 estava documentado como constante `"ATob"`. É o
discriminador de tipo de documento (`ATob` = bin, `ATpj` = projeto). Corrigido lá com
ponteiro para cá.

## 2026-08-24 — Mimiq e Osiris 2 (material virgem)

| descoberta | fonte | confiança |
|---|---|---|
| ⭐⭐⭐ **Há DOIS mecanismos de lock:** o `<bin>.lck` (pasta comum, caso degradado) e o **`Flock`** da API de shared storage da Avid | módulo `AvidSharedStorageAccess` do Mimiq: `ASIsFlockPresent`, `ASGetFlockList_UTF8/16`, `ASGetFlockWSList`, `?GetFileLock@AWinFileSystemObject@@` | confirmado (símbolos exportados) |
| ⭐ **Um app pode PERGUNTAR quem tem o lock** — o `.lck`, sem PID nem timestamp, não permite | mesma fonte | inferido |
| ⭐ **Canal de notificação `/Media Composer/NewBinSharingMsg`** — o MC é avisado, não fica olhando o disco | mesma fonte | inferido |
| ⭐⭐⭐ **O TERCEIRO eixo de integração: ficar EMBAIXO do app** — nenhum dos dois fala com o MC; fazem o armazenamento comum PARECER Avid Shared Storage | os dois produtos | confirmado |
| **Mimiq (.NET):** usa a própria API da Avid (`ASMountWorkspace`/`ASMountWS`) e descobre workspace varrendo volumes atrás de pastas **`Avid MediaFiles`** | `.pdb` `AvidSharedStorageAccess`, `Workspaces`, `Mimiq`, `Localization` | confirmado |
| **Osiris 2 (Qt):** monta por **`BindfsMount`** sobre **`pamFS`**, variante de **macFUSE** com `.kext` + `.appex` | `PackageInfo` do `.pkg` + símbolos do binário | confirmado |
| ⚠️ **Osiris não é app solto: é cliente de plataforma** — `BinLocking` é capacidade **licenciada** ao lado de `strawberry`/`spycer`; o lock é **arbitrado por servidor** | lista de capacidades no binário | inferido |
| ⭐ **Restrições lidas na UI:** no Windows um workspace precisa ser **letra de unidade**; o produto **recusa versão de MC não suportada**; *"Bin Locking is not working"* tem mensagem própria | tabela de localização do Mimiq | confirmado |
| ⚠️ **Falso positivo evitado:** `OMFI` aparece 4× no binário do Osiris e **NÃO é OMFI** — são fragmentos de símbolo C++ mangled de `LicenseHandler` | leitura de contexto | *contar ocorrência sem ler contexto teria inventado um achado* |

Método e limites: [storage-como-integracao.md §A régua](storage-como-integracao.md). ⭐ **Nada foi
descompilado** — os nomes de `.pdb` entregaram a arquitetura num MSI que renomeia arquivos para
hash, exatamente como a receita da técnica previa. ⛔ Licenciamento não examinado; o `pamfs.fs` não
analisado; o protocolo Osiris↔Strawberry não mapeado. Nada instalado, **nenhum `.kext` carregado,
nenhum volume montado**.

