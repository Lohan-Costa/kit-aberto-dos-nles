# AMA Management — XML + AMA Metadata Folders

Como o Media Composer rastreia mídia **AMA-linkada** (referenciada no lugar de onde está, sem
copiar para o `Avid MediaFiles`). Confiança: **confirmado** (XML é texto; estrutura das pastas
observada na amostra).

Amostra: `ARQUIVOS PARA ANALISAR/AMA MANAGMENT/`.

## O arquivo `Managed AMA Media Folders.xml`

XML simples, uma entrada por pasta de mídia gerenciada:

```xml
<ManagedAMAFolderList>
  <OneFolder>
    <media_pathname>/Volumes/.../PRODUCAO-A/MIDIAS/TRILHAS/MIXADAS/</media_pathname>
    <metadata_pathname>/Users/Shared/AvidMediaComposer/AMA Management/AMA Metadata Folders/MIXADAS14109323/</metadata_pathname>
  </OneFolder>
  ...
</ManagedAMAFolderList>
```

- `media_pathname` = onde está a mídia original (externa).
- `metadata_pathname` = a *AMA Metadata Folder* correspondente (sempre em
  `/Users/Shared/AvidMediaComposer/AMA Management/AMA Metadata Folders/<ID>`).
- O ID da pasta segue `<PREFIXO><hex>` (ex.: `MIXADAS14109323`, `SFX1416bd4f`, `SD04142eb6be`) —
  prefixo derivado do nome da pasta de mídia + sufixo hex.
- **Observação prática:** na amostra há **56 `<OneFolder>` mas só 9 pastas únicas** — o MC
  **anexa sem deduplicar**. Um writer nosso pode (a) deduplicar e (b) anexar com segurança.

## A AMA Metadata Folder (por dentro)

Cada pasta (ex.: `MIXADAS14109323/`) contém:

- **um `.aaf` por arquivo de mídia** — ex.: `00;12;12 Piano e Cordas.wav.aaf`. É o descriptor do
  AMA-link: o metadado que o MC lê para "conhecer" o arquivo sem importar. **Isto é território já
  dominado** — geração/escrita de AAF AMA está em [../aaf/escrita.md](../aaf/escrita.md) §AMA e em
  [../aaf/dados/ama-constantes.json](../aaf/dados/ama-constantes.json).
- **um `amaFMID.pmr`** — mesmo formato do [pmr-fmid.md](pmr-fmid.md) (a confirmar byte a byte),
  indexando os MobIDs daquela pasta.

## O caminho para "intervir em vez de contornar"

Hoje a casa contorna o AMA Management. Para **injetar dados novos**, a receita provável é:

1. Gerar o(s) `.aaf` de AMA-link por arquivo (pyaaf2 — já sabemos, ver aaf/escrita.md).
2. Gerar/atualizar o `amaFMID.pmr` da pasta (ver [pmr-fmid.md](pmr-fmid.md) — falta round-trip).
3. Criar a *AMA Metadata Folder* com ID no padrão `<PREFIXO><hex>`.
4. Anexar (deduplicando) o `<OneFolder>` no `Managed AMA Media Folders.xml`.

Passos 1 e 4 são de baixo risco (AAF conhecido; XML texto). Os passos 2 e 3 dependem de fechar o
`.pmr` e o esquema do ID — e de **validar no Media Composer** (há acesso).

## Validado: o conjunto AMA é portátil e suficiente (confirmado, 2026-06-27, MC 25.12.0.58863)

Teste de ponta a ponta com 3 mídias (2 `.mov` + 1 `.WAV` na pasta `MIDIAS BRUTAS/`):

1. Esvaziou-se `/Users/Shared/AvidMediaComposer/AMA Management/`.
2. **Copiou-se** (não gerou) o conjunto capturado de volta: o `Managed AMA Media Folders.xml` + a
   *AMA Metadata Folder* `MIDIAS BRUae8ba35c/` (com `amaMMOB.mdb`, `amaFMID.pmr`, `<wav>.aaf`).
3. Abriu-se projeto novo e **importou-se a bin original** (`PORJETO LINK REPLICAR Bin.avb`).
4. **Resultado: os 3 clipes ficaram ONLINE e tocam.** ✅

O que isso confirma:
- O **conjunto de arquivos AMA é completo e portátil**: restaurá-lo na pasta real + importar a bin
  reproduz o estado linkado, **sem reimportar a mídia**. (Pré-condição: a mídia no caminho do
  `media_pathname` do XML; e **relançar o MC** se estava aberto, pois ele lê o XML na inicialização.)
- **A AMA Management é necessária** (a bin sozinha não basta — ver correção abaixo).
- Agrupamento: 3 arquivos na **mesma pasta de origem** compartilham **uma** metadata folder; só o
  `.WAV` ganhou `.aaf` standalone (os `.mov`/QuickTime ficam só no `.mdb`).

O que **ainda não** está provado: gerar esses arquivos do zero, e abrir no MC uma bin escrita por
pyavb.

### O `.aaf` standalone NÃO é necessário pro link (inferido, 2026-06-27)

Descoberta importante: o `.aaf` da AMA Metadata Folder é uma **AAF codificada em KLV/MXF** (começa
com MXF Header Partition Pack + Primer + ~716 pacotes KLV; URLString em UTF-16, URL-encoded). **Não
é a AAF OLE/Structured-Storage** — o `pyaaf2` não a lê nem escreve.

Teste de necessidade: montou-se a pasta real **sem** o `<wav>.aaf` (só XML + `amaMMOB.mdb` +
`amaFMID.pmr`), relançou-se o MC, criou-se **projeto novo** e importou-se a bin → **os 3 clipes,
inclusive o WAV, ficaram ONLINE**. Logo, o link é resolvido pelo `amaMMOB.mdb`/`amaFMID.pmr`; o
`.aaf` parece ser descriptor auxiliar (waveform/metadados), não a fonte da resolução.

### Modelo correto (v3, validado pelo usuário — 2026-06-27)

Houve duas conclusões erradas no caminho: **v1** "bin autossuficiente, sem cache" (ignorou a AMA
Management leftover) e **v2** "AMA Management é o resolvedor obrigatório" (over-correção baseada num
teste contaminado por symlink). A v3, ancorada em testes limpos do usuário:

- **A bin resolve sozinha** pelo `MacFileLocator.path_posix` quando aponta p/ **arquivo real**:
  com a AMA Management **vazia**, importar a bin relinkada (caminhos reais novos) → **ONLINE e
  tocando**, e o MC **NÃO recriou** a AMA Management. Logo ela **não é obrigatória**.
- **A AMA Management é OPCIONAL mas PRIORITÁRIA:** se existir uma entrada referenciando a mesma
  mídia, o MC a usa **no lugar** do `path_posix` da bin. Daí o conflito observado: a bin aponta p/ X,
  mas "Reveal File" abre o **original**; se o original foi movido/apagado, o conform falha
  (`InitContainerHandler failed`). Era o "cache global" suspeitado lá no início — opcional, não
  obrigatório.
- **Quem cria a AMA Management:** o **AMA-link via Source Browser** (ao montar a bin), **não** o
  import de uma bin. As metadata folders vistas "repopuladas" eram leftover dessa montagem.

**Fluxo de relink confiável:** (1) patch do `path_posix` na bin (apontando p/ arquivo real);
(2) **remover qualquer entrada conflitante na AMA Management** p/ aquelas mídias (senão ela
sequestra a resolução). Sem conflito, a bin sozinha já traz online.

Em aberto: o MC parece **não resolver via symlink** (provável causa de uma bin relinkada p/ symlinks
ter ficado offline com a AMA Management vazia) — confirmar com alvo de arquivo real.

## Pendente

- Confirmar `amaFMID.pmr` == `msmFMID.pmr` (mesmo layout). [parcial: header `0x7a9` igual]
- Decifrar a regra exata do sufixo hex do ID da pasta (`MIDIAS BRU` + `ae8ba35c`).
- Geração do zero: escrever `amaMMOB.mdb` (Bento) é o bloqueio; `.aaf` do WAV e XML são viáveis já.
- Retarget: editar `.mdb`/`.pmr` para apontar a mídia em outro caminho (relink programático).
