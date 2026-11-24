"""Gera a cópia PÚBLICA do KIT ABERTO DOS NLEs a partir dos repositórios privados, sem tocar neles (decisões do autor,
2026-11-23: anonimizar TUDO; história nova; o método num repositório, o Ciclo Assist noutro).

    python3 exportar_publico.py <pasta de saída>            # gera e escreve o RELATORIO.md (nada é publicado)

O que faz, nesta ordem:
  1. lista os arquivos VERSIONADOS de cada repositório (`git ls-files`) — o que não está no Git não vai;
  2. regra de PERMISSÃO (`regras.json`): o arquivo vai só se casar uma regra "vai" e nenhuma "fica" antes dela —
     o que ninguém previu fica de fora por padrão; binário (byte nulo no começo) nunca vai sem regra "binario";
  3. troca cada nome pelo apelido fixo (`PRIVADO-apelidos.json`, que NUNCA vai), no conteúdo E no caminho do arquivo;
  4. a VARREDURA na cópia: nome da lista, caminho pessoal, e-mail, segredo, arquivo grande — "bloqueia" impede a
     publicação; "revisar" vai ao relatório para uma pessoa (ou um Claude) ler;
  5. os testes que ficaram sem os dados (os arquivos de dados ficaram de fora e um teste incluído os cita).

Só stdlib. Roda no Mac e no Windows (os caminhos dos repositórios vêm SUBINDO até achar `bancodedadosnles`).
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))


def _familia() -> str:
    p = AQUI
    while not os.path.isdir(os.path.join(p, "bancodedadosnles")):
        if os.path.dirname(p) == p:
            raise SystemExit("não achei a pasta da família (com bancodedadosnles) subindo de " + AQUI)
        p = os.path.dirname(p)
    return p


def _git_arquivos(repo: str) -> list[str]:
    r = subprocess.run(["git", "-c", "safe.directory=*", "-C", repo, "ls-files", "-z"], capture_output=True)
    if r.returncode:
        raise SystemExit(f"git ls-files falhou em {repo}: {r.stderr.decode(errors='replace')[-300:]}")
    return [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]


def _binario(caminho: str) -> bool:
    with open(caminho, "rb") as fh:
        return b"\0" in fh.read(8192)


def _casa(rel: str, padrao: str) -> bool:
    return fnmatch.fnmatchcase(rel, padrao) or fnmatch.fnmatchcase(os.path.basename(rel), padrao)


def decidir(rel: str, regras: list[list[str]], binario: bool) -> tuple[bool, str]:
    """(vai?, motivo). `regras` = [[acao, padrão], …] na ordem; a 1ª que casar decide; nenhuma = fica."""
    for acao, padrao in regras:
        if _casa(rel, padrao):
            if acao == "fica":
                return False, f"regra: fica {padrao}"
            if binario and acao not in ("binario", "prproj"):
                return False, "binário sem regra própria"
            return True, f"regra: {acao} {padrao}"
    return False, "nenhuma regra (fica por padrão)"


# ── os apelidos ──────────────────────────────────────────────────────────────────────────────────────────────────────
#: fronteira de nome: letra ou dígito do lado = parte de outra palavra; o "_" SEPARA (prova_produto_PRODC)
#: ⚠️ o "\n" escrito no código ("…\nPERSONAGEM-F\n…") é fronteira: o "n" da barra não é parte do nome (5º ensaio, 2026-11-24)
_ANTES, _DEPOIS = r"(?:(?<![A-Za-z0-9À-ÿ])|(?<=\\[nrt]))", r"(?![A-Za-z0-9À-ÿ])"


def _corpo(nome: str) -> str:
    """O nome em regex: o espaço também casa a quebra de linha (com o "#" do comentário que continua) e o "%20" do
    endereço — um título quebrado no meio de um comentário e um "47_NOME%20DO%20FILME" de um caminho em URL passavam
    pela troca (3º ensaio, 2026-11-24)."""
    return r"(?:%20|\s+(?:#\s*)?)".join(re.escape(x) for x in nome.split(" "))


def compilar(apelidos: list[dict]) -> list[tuple[re.Pattern, str, str]]:
    """[{de, para, maiusculas: bool, solto: bool, exceto_antes: regex de largura fixa}] → (regex, troca, de). `solto` = sem a fronteira (prefixos como
    "PRODA_"). Os mais longos primeiro ("Assist anterior" antes de "Emissora")."""
    out = []
    for a in sorted(apelidos, key=lambda a: -len(a["de"])):
        corpo = _corpo(a["de"])
        rx = corpo if a.get("solto") else _ANTES + corpo + _DEPOIS
        if a.get("exceto_antes"):   # ex.: "usuario" é o usuário da máquina, mas "com.ciclomedia.*" é a marca (o id)
            rx = f"(?<!{a['exceto_antes']})" + rx
        out.append((re.compile(rx, 0 if a.get("maiusculas") else re.IGNORECASE), a["para"], a["de"]))
    return out


def trocar(texto: str, regras: list, contagem: dict) -> str:
    for rx, para, de in regras:
        texto, n = rx.subn(lambda _m, p=para: p, texto)   # a troca é LITERAL (o apelido pode ter "\\")
        if n:
            contagem[de] = contagem.get(de, 0) + n
    return texto


# ── a varredura ──────────────────────────────────────────────────────────────────────────────────────────────────────
SEGREDOS = [r"sk-ant-[A-Za-z0-9_-]{16,}", r"ghp_[A-Za-z0-9]{30,}", r"github_pat_[A-Za-z0-9_]{30,}",
            r"AKIA[0-9A-Z]{16}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"xox[abp]-[A-Za-z0-9-]{10,}"]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
#: os genéricos (exemplo, o git do GitHub, o teste de segurança com evil.com)
EMAIL_OK = ("noreply@anthropic.com", "git@github.com", "users.noreply.github.com", "@exemplo.", "@example.", "@evil.com")


def varrer(texto: str, bloqueio: list[re.Pattern], revisar: list[re.Pattern]) -> list[tuple[str, str, int, str]]:
    """[(nível, o quê, linha, trecho)] na cópia já trocada."""
    achados = []
    linhas = texto.splitlines()

    def onde(pos: int) -> tuple[int, str]:
        n = texto.count("\n", 0, pos)
        return n + 1, (linhas[n] if n < len(linhas) else "")[:160]

    for rx in bloqueio:
        for m in rx.finditer(texto):
            achados.append(("bloqueia", f"nome: {m.group(0)}", *onde(m.start())))
    for s in SEGREDOS:
        for m in re.finditer(s, texto):
            achados.append(("bloqueia", "segredo", *onde(m.start())))
    for m in EMAIL.finditer(texto):
        e = m.group(0).lower()
        if not any(ok in e for ok in EMAIL_OK) and not e.endswith((".py", ".md", ".json", ".png", ".js", ".css")):
            achados.append(("bloqueia", f"e-mail: {m.group(0)}", *onde(m.start())))
    for rx in revisar:
        for m in rx.finditer(texto):
            achados.append(("revisar", f"termo: {m.group(0)}", *onde(m.start())))
    return achados


# ── a exportação ─────────────────────────────────────────────────────────────────────────────────────────────────────
def exportar(saida: str) -> dict:
    fam = _familia()
    regras = json.load(open(os.path.join(AQUI, "regras.json"), encoding="utf-8"))
    priv = json.load(open(os.path.join(AQUI, "PRIVADO-apelidos.json"), encoding="utf-8"))
    trocas = compilar(priv["apelidos"])
    bloqueio = [re.compile(_ANTES + _corpo(t) + _DEPOIS, re.IGNORECASE) for t in priv["bloqueia"]]
    bloqueio += [re.compile(p) for p in priv.get("bloqueia_regex", [])]
    revisar = [re.compile(p) for p in priv.get("revisar_regex", [])]
    rel: dict = {"repos": {}, "trocas": {}, "achados": [], "sem_dados": [], "grandes": []}
    for alvo in regras["alvos"]:
        repo = os.path.join(fam, alvo["repo"])
        destino = os.path.join(saida, alvo["destino"])
        info = {"incluidos": 0, "excluidos": {}, "bytes": 0}
        incluidos, excluidos = [], []
        for arq in _git_arquivos(repo):
            orig = os.path.join(repo, arq)
            if not os.path.isfile(orig):
                continue
            binario = _binario(orig)
            vai, motivo = decidir(arq, alvo["regras"], binario)
            if not vai:
                info["excluidos"][motivo] = info["excluidos"].get(motivo, 0) + 1
                excluidos.append(arq)
                continue
            novo_rel = trocar(arq, trocas, rel["trocas"])
            novo = os.path.join(destino, novo_rel)
            os.makedirs(os.path.dirname(novo), exist_ok=True)
            if motivo.startswith("regra: prproj"):
                # o .prproj é XML em gzip: abre, troca e varre como texto, recomprime
                import gzip
                texto = trocar(gzip.decompress(open(orig, "rb").read()).decode("utf-8"), trocas, rel["trocas"])
                with open(novo, "wb") as fh:
                    fh.write(gzip.compress(texto.encode("utf-8")))
                for nivel, oque, linha, trecho in varrer(texto, bloqueio, revisar):
                    rel["achados"].append({"nivel": nivel, "oque": oque, "arquivo": f"{alvo['destino']}/{novo_rel}",
                                           "linha": linha, "trecho": trecho})
            elif binario:
                dados = open(orig, "rb").read()
                with open(novo, "wb") as b:
                    b.write(dados)
                # o binário vai como está: o texto de DENTRO dele (e o de dentro do zip: .drt/.drp) também é varrido
                partes = [dados]
                if dados[:2] == b"PK":
                    import io
                    import zipfile
                    try:
                        with zipfile.ZipFile(io.BytesIO(dados)) as z:
                            partes += [z.read(n) for n in z.namelist()]
                    except zipfile.BadZipFile:
                        pass
                for parte in partes:
                    for nivel, oque, *_ in varrer(parte.decode("latin1"), bloqueio, []):
                        rel["achados"].append({"nivel": nivel, "oque": oque + " (dentro do binário)",
                                               "arquivo": f"{alvo['destino']}/{novo_rel}", "linha": 0, "trecho": ""})
            else:
                bruto = open(orig, "rb").read()
                try:
                    texto = bruto.decode("utf-8")
                except UnicodeDecodeError:
                    texto = bruto.decode("latin1")
                texto = trocar(texto, trocas, rel["trocas"])
                with open(novo, "w", encoding="utf-8", newline="") as fh:
                    fh.write(texto)
                for nivel, oque, linha, trecho in varrer(texto, bloqueio, revisar):
                    rel["achados"].append({"nivel": nivel, "oque": oque, "arquivo": f"{alvo['destino']}/{novo_rel}",
                                           "linha": linha, "trecho": trecho})
            for nivel, oque, *_ in varrer(novo_rel, bloqueio, []):     # o NOME do arquivo também
                rel["achados"].append({"nivel": nivel, "oque": oque + " (no nome do arquivo)",
                                       "arquivo": f"{alvo['destino']}/{novo_rel}", "linha": 0, "trecho": novo_rel})
            tam = os.path.getsize(novo)
            info["bytes"] += tam
            if tam > regras.get("grande_bytes", 1_000_000):
                rel["grandes"].append({"arquivo": f"{alvo['destino']}/{novo_rel}", "bytes": tam})
            info["incluidos"] += 1
            incluidos.append((arq, novo))
        # os testes que citam um arquivo de dados que ficou de fora
        nomes_fora = {os.path.basename(x): x for x in excluidos if not x.endswith((".md", ".py"))}
        for arq, novo in incluidos:
            if not re.search(r"(^|/)tests?/|test_", arq) or not arq.endswith(".py"):
                continue
            texto = open(novo, encoding="utf-8", errors="replace").read()
            citados = sorted({n for n in nomes_fora if n in texto})
            if citados:
                rel["sem_dados"].append({"teste": f"{alvo['destino']}/{arq}", "dados": citados[:6], "n": len(citados)})
        rel["repos"][alvo["destino"]] = info
    montar_kit(saida)
    return rel


def montar_kit(saida: str) -> None:
    """A forma do repositório público (fase 3, 2026-11-24): a raiz do kit faz o papel da pasta da família — o código acha
    `bancodedadosnles`, `piloto` e `laboratorio-de-midia` SUBINDO de pasta pelo nome. `kit/raiz/` (já trocado e varrido
    como o resto do banco) vai ao topo, `kit/site/` vira `docs/` (o GitHub Pages) e o `COMECE-AQUI.md` fica na raiz."""
    import shutil
    kit = os.path.join(saida, "kit-aberto-dos-nles")
    fonte = os.path.join(kit, "bancodedadosnles", "kit")
    if not os.path.isdir(fonte):
        return
    if os.path.isdir(os.path.join(fonte, "raiz")):
        shutil.copytree(os.path.join(fonte, "raiz"), kit, dirs_exist_ok=True)
    if os.path.isdir(os.path.join(fonte, "site")):
        shutil.copytree(os.path.join(fonte, "site"), os.path.join(kit, "docs"), dirs_exist_ok=True)
    if os.path.isfile(os.path.join(fonte, "COMECE-AQUI.md")):
        shutil.copy2(os.path.join(fonte, "COMECE-AQUI.md"), kit)
    shutil.rmtree(fonte)


def relatorio(rel: dict, saida: str) -> str:
    b = [a for a in rel["achados"] if a["nivel"] == "bloqueia"]
    r = [a for a in rel["achados"] if a["nivel"] == "revisar"]
    L = ["# Relatório da exportação pública (rodada de ensaio — nada foi publicado)", ""]
    L.append(f"**Bloqueios: {len(b)}** · a revisar: {len(r)} · testes sem os dados: {len(rel['sem_dados'])} · "
             f"arquivos grandes: {len(rel['grandes'])}")
    L += ["", "## O que entrou e o que ficou de fora", "", "| destino | entraram | MB | ficaram de fora (motivo: n) |",
          "|---|---:|---:|---|"]
    for d, i in rel["repos"].items():
        fora = "; ".join(f"{k}: {v}" for k, v in sorted(i["excluidos"].items(), key=lambda kv: -kv[1]))
        L.append(f"| {d} | {i['incluidos']} | {i['bytes'] / 1e6:.1f} | {fora} |")
    L += ["", "## As trocas (nome → apelido; o nome fica só aqui, que é privado)", "", "| nome | trocas |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in sorted(rel["trocas"].items(), key=lambda kv: -kv[1])]

    def tabela(titulo, itens, n=80):
        out = ["", f"## {titulo} ({len(itens)})", ""]
        por = {}
        for a in itens:
            por.setdefault(a["oque"], []).append(a)
        for oque, xs in sorted(por.items(), key=lambda kv: -len(kv[1])):
            out.append(f"- **{oque}** — {len(xs)}×: " + "; ".join(f"`{x['arquivo']}:{x['linha']}`" for x in xs[:4]))
        return out[:n + 3]
    L += tabela("Bloqueios (impedem a publicação)", b)
    L += tabela("A revisar", r)
    L += ["", f"## Testes que ficaram sem os dados ({len(rel['sem_dados'])})", ""]
    L += [f"- `{t['teste']}` — {t['n']} arquivo(s): {', '.join(t['dados'])}" for t in rel["sem_dados"]]
    if rel["grandes"]:
        L += ["", "## Arquivos grandes", ""] + [f"- `{g['arquivo']}` — {g['bytes'] / 1e6:.1f} MB" for g in rel["grandes"]]
    texto = "\n".join(L) + "\n"
    with open(os.path.join(saida, "RELATORIO.md"), "w", encoding="utf-8") as fh:
        fh.write(texto)
    with open(os.path.join(saida, "relatorio.json"), "w", encoding="utf-8") as fh:
        json.dump(rel, fh, ensure_ascii=False, indent=1)
    return texto


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    saida = os.path.abspath(sys.argv[1])
    if os.path.exists(saida) and os.listdir(saida):
        raise SystemExit(f"a pasta de saída não está vazia: {saida}")
    os.makedirs(saida, exist_ok=True)
    print(relatorio(exportar(saida), saida)[:3000])
