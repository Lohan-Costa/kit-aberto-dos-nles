"""
consulta.py — acesso de leitura ao Banco de Dados NLEs.

Helper sem dependências (só stdlib) para os apps consultarem os fatos estruturados
(`protocolos/*/dados/*.json` e `transversal/*.json`) sem reimplementar o acesso.

Uso:
    from consulta import Banco
    banco = Banco()  # autodetecta a raiz (pasta deste arquivo)

    # Carregar um arquivo de dados pelo "id" (caminho relativo sem .json):
    classids = banco.dados("prproj/classids")
    seq = classids["entries"]["sequencia"]["Sequence"]   # ClassID da Sequence

    # Atalhos comuns:
    banco.classid("Sequence")                 # -> "6a15d903-..."
    banco.ticks_por_segundo()                 # -> 254016000000
    banco.confianca("aaf/operationdefs")      # -> "confirmado"
    banco.listar()                            # -> lista de ids de dados disponíveis

CLI:
    python consulta.py listar
    python consulta.py mostrar prproj/classids
    python consulta.py classid Sequence
"""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from typing import Any


class Banco:
    """Interface de leitura do banco. Resolve ids -> arquivos JSON e os cacheia."""

    def __init__(self, raiz: str | pathlib.Path | None = None) -> None:
        self.raiz = pathlib.Path(raiz) if raiz else pathlib.Path(__file__).resolve().parent

    # ---- núcleo -----------------------------------------------------------

    def _caminho(self, dados_id: str) -> pathlib.Path:
        """Resolve um id (ex.: 'prproj/classids' ou 'transversal/tempo-e-timecode') em path."""
        dados_id = dados_id.removesuffix(".json")
        candidatos = [
            self.raiz / "protocolos" / f"{dados_id}.json",                  # protocolos/<fmt>/<arq>
            self.raiz / "protocolos" / pathlib.Path(dados_id).parent
            / "dados" / f"{pathlib.Path(dados_id).name}.json",               # protocolos/<fmt>/dados/<arq>
            self.raiz / f"{dados_id}.json",                                  # transversal/<arq>, seguranca/dados/<arq>
            self.raiz / pathlib.Path(dados_id).parent
            / "dados" / f"{pathlib.Path(dados_id).name}.json",               # plugins/<nle>/dados/<arq>
        ]
        for c in candidatos:
            if c.exists():
                return c
        raise FileNotFoundError(
            f"Dados '{dados_id}' não encontrados. Tente um de: {', '.join(self.listar())}"
        )

    @lru_cache(maxsize=None)
    def dados(self, dados_id: str) -> dict[str, Any]:
        """Carrega e retorna o JSON de dados pelo id (cacheado)."""
        return json.loads(self._caminho(dados_id).read_text(encoding="utf-8"))

    def listar(self) -> list[str]:
        """Lista todos os ids de dados disponíveis (caminhos relativos sem .json)."""
        ids: list[str] = []
        for p in sorted(self.raiz.glob("protocolos/*/dados/*.json")):
            ids.append(f"{p.parent.parent.name}/{p.stem}")
        for p in sorted(self.raiz.glob("transversal/*.json")):
            ids.append(f"transversal/{p.stem}")
        # Painéis DENTRO do NLE (APIs de scripting/UI, não formatos de arquivo).
        for p in sorted(self.raiz.glob("plugins/*/dados/*.json")):
            ids.append(f"plugins/{p.parent.parent.name}/{p.stem}")
        # Seções que não são protocolo (não têm um formato de arquivo por trás) e
        # guardam os dados em <secao>/dados/. Hoje: `seguranca`.
        for p in sorted(self.raiz.glob("seguranca/dados/*.json")):
            ids.append(f"seguranca/dados/{p.stem}")
        return ids

    def confianca(self, dados_id: str) -> str | None:
        """Nível de confiança declarado no _meta do arquivo."""
        return self.dados(dados_id).get("_meta", {}).get("confianca")

    # ---- atalhos de alto valor -------------------------------------------

    def classid(self, nome: str) -> str:
        """ClassID do PRPROJ por nome de elemento (ex.: 'Sequence', 'Media', 'AudioClip')."""
        for grupo in self.dados("prproj/classids")["entries"].values():
            if nome in grupo:
                return grupo[nome]
        raise KeyError(f"ClassID '{nome}' não encontrado em prproj/classids")

    def ticks_por_segundo(self) -> int:
        return self.dados("prproj/ticks")["constantes"]["ticks_por_segundo"]

    def ticks_por_frame(self, fps: str = "23976") -> int:
        return self.dados("prproj/ticks")["constantes"][f"ticks_por_frame_{fps}"]


def _cli(argv: list[str]) -> int:
    banco = Banco()
    if not argv or argv[0] in {"-h", "--help", "ajuda"}:
        print(__doc__)
        return 0
    cmd, *resto = argv
    if cmd == "listar":
        print("\n".join(banco.listar()))
    elif cmd == "mostrar" and resto:
        print(json.dumps(banco.dados(resto[0]), ensure_ascii=False, indent=2))
    elif cmd == "classid" and resto:
        print(banco.classid(resto[0]))
    else:
        print(f"Comando desconhecido: {cmd}. Use: listar | mostrar <id> | classid <nome>")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_cli(sys.argv[1:]))
