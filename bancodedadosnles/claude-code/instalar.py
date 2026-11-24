"""
instalar.py — liga ao Claude Code DESTA máquina a linha de status e o aviso de contexto da família.

    py claude-code\\instalar.py              # Windows
    python3 claude-code/instalar.py         # macOS (a linha de status é a macos/statusline.sh, em bash + jq)
    ... --conferir                          # só diz o que está ligado

- a LINHA DE STATUS (modelo · barra do contexto · barra da janela de 5 h e quanto falta para zerar) grava o percentual
  do contexto por sessão em `~/.claude/state/ctx_<sessão>.txt`;
- o GANCHO `aviso_contexto.py` (PostToolUse) lê esse arquivo e, a partir de 85 %, pede o checkpoint (autor, 2026-10-11).
  Um não funciona sem o outro: sem a linha de status, o gancho fica mudo.
- no Windows, também os sons de "terminou" (Stop) e "precisa de você" (Notification).

Os scripts são COPIADOS para `~/.claude/` (o gancho roda a cada ferramenta: não pode depender do SSD estar ligado nem
da letra dele). No `settings.json` só entram `statusLine` e os ganchos que faltam; o resto fica como está, e uma cópia
do arquivo antigo vai para `settings.json.antes-do-instalar`.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
CLAUDE = Path.home() / ".claude"
WINDOWS = sys.platform == "win32"


def _caminho(p: Path) -> str:
    return p.as_posix()


def desejado() -> tuple[dict, dict[str, Path]]:
    """(trechos do settings.json, {destino: origem} dos arquivos)."""
    aviso = CLAUDE / "aviso_contexto.py"
    arquivos = {aviso: AQUI / "aviso_contexto.py"}
    py = "python" if WINDOWS else "python3"
    trechos: dict = {"hooks": {"PostToolUse": [{"matcher": "*", "hooks": [
        {"type": "command", "command": f'{py} "{_caminho(aviso)}"', "timeout": 10}]}]}}
    if WINDOWS:
        status = CLAUDE / "statusline.ps1"
        arquivos[status] = AQUI / "windows" / "statusline.ps1"
        trechos["statusLine"] = {"type": "command",
                                 "command": f'powershell -NoProfile -File "{_caminho(status)}"'}
        som = 'powershell -NoProfile -Command "(New-Object Media.SoundPlayer \'C:\\Windows\\Media\\{}\').PlaySync()"'
        trechos["hooks"]["Stop"] = [{"hooks": [
            {"type": "command", "command": som.format("tada.wav"), "timeout": 10, "async": True}]}]
        trechos["hooks"]["Notification"] = [{"hooks": [
            {"type": "command", "command": som.format("Windows Notify Messaging.wav"), "timeout": 10, "async": True}]}]
    else:
        # macOS (2026-11-06): a linha antiga do Mac (~/.claude/statusline-command.sh) não gravava o percentual, e o
        # aviso dos 85 % nunca disparou no Mac. Esta grava (e precisa do jq: nativo no macOS 15; antes, `brew install jq`).
        status = CLAUDE / "statusline.sh"
        arquivos[status] = AQUI / "macos" / "statusline.sh"
        trechos["statusLine"] = {"type": "command", "command": f'bash "{_caminho(status)}"'}
    return trechos, arquivos


def _norma(cmd: str) -> str:
    """O Windows não distingue maiúsculas no caminho (o settings.json daqui tem `CICLO MEDIA`, o Python dá `Ciclo
    Media`): comparar sem elas, ou o gancho entra em dobro."""
    return cmd.lower() if WINDOWS else cmd


def _comandos(grupos: list) -> set[str]:
    return {_norma(h.get("command", "")) for g in grupos for h in g.get("hooks", [])}


def main() -> int:
    conferir = "--conferir" in sys.argv
    trechos, arquivos = desejado()
    cfg_p = CLAUDE / "settings.json"
    cfg = json.loads(cfg_p.read_text(encoding="utf-8")) if cfg_p.is_file() else {}
    faltas = []
    for destino, origem in arquivos.items():
        igual = destino.is_file() and destino.read_bytes() == origem.read_bytes()
        if not igual:
            faltas.append(f"arquivo {destino.name}")
            if not conferir:
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, destino)
    if "statusLine" in trechos and _norma(json.dumps(cfg.get("statusLine"))) != _norma(json.dumps(trechos["statusLine"])):
        faltas.append("statusLine")
        if not conferir:
            cfg["statusLine"] = trechos["statusLine"]
    ganchos = cfg.setdefault("hooks", {})
    for evento, grupos in trechos["hooks"].items():
        novos = [g for g in grupos if not (_comandos([g]) <= _comandos(ganchos.get(evento, [])))]
        if novos:
            faltas.append(f"gancho {evento}")
            if not conferir:
                ganchos.setdefault(evento, []).extend(novos)
    if conferir:
        print("tudo ligado" if not faltas else "falta: " + ", ".join(faltas))
        return 1 if faltas else 0
    if any(not f.startswith("arquivo") for f in faltas):
        if cfg_p.is_file():
            shutil.copy2(cfg_p, cfg_p.with_name("settings.json.antes-do-instalar"))
        cfg_p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("nada a fazer: já estava ligado" if not faltas else "ligado: " + ", ".join(faltas))
    print("Abra uma sessão NOVA do Claude Code para a linha de status e o gancho valerem.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
