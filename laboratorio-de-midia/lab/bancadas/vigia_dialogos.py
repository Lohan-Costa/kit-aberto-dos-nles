"""VIGIA DE DIÁLOGOS — fecha, sozinho, os diálogos CONHECIDOS que travam a ponte do Premiere, para a bancada rodar sem o
autor ("eu não posso ficar acompanhando esse processo sempre", 2026-10-07). macOS: pela acessibilidade (System Events),
que o Terminal tem — aperta um botão PELO NOME numa janela de um processo PELO NOME; nunca tecla no app da frente.

    python3 -m lab.bancadas.vigia_dialogos            # vigia até ser interrompido (a bancada o liga em segundo plano)
    python3 -m lab.bancadas.vigia_dialogos explorar   # só descreve as janelas dos processos de interesse, sem clicar

Regras (REGRAS): só diálogo conhecido, só o botão seguro dele. Diálogo DESCONHECIDO que fica parado: print, registro e
NADA de clique (o vigia continua). O relatório de erro da Adobe de um Premiere que caiu é fechado (= "Não enviar").
Registro: `saida/bancadas/vigia/vigia.jsonl` + o print de cada diálogo em `saida/bancadas/vigia/`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA = os.path.join(RAIZ, "saida", "bancadas", "vigia")
PROCESSOS = ("Adobe Premiere Pro", "Problem Reporter", "Relatório de Problemas", "AdobeCrashReporter", "Adobe Crash Reporter",
             "UserNotificationCenter")

# (processo contém, algum texto da janela contém [título ou texto], botão a apertar) — em inglês e português
# (processo contém, título ou texto contém, botão) — botão "RETURN" = o padrão do diálogo do Premiere (ver _DESCREVER)
REGRAS = [
    ("Adobe Premiere Pro", ("Carregar projeto", "Load Project"), ("RETURN",)),
    ("Adobe Premiere Pro", ("Converter projeto", "Convert Project"), ("RETURN",)),
    ("Adobe Premiere Pro", ("File Import Failure", "Falha na importação", "Falha ao importar"), ("RETURN",)),
    ("Adobe Premiere Pro", ("Projeto modificado", "Project Modified"), ("RETURN",)),
    # fontes que faltam (o projeto real usa fonte que a máquina não tem): OK = substituir pela padrão — o autor:
    # "um sobre fonte que pode ser ignorado"
    ("Adobe Premiere Pro", ("Resolve Fonts", "Resolver fontes", "Resolver Fontes"), ("RETURN",)),
    # ALERTA genérico, título "Adobe Premiere Pro" e só OK (ex.: "The project could not be loaded, it may be damaged or
    # contain outdated elements"): Return = OK; o print guarda o texto, e quem chamou vê que o projeto não abriu
    ("Adobe Premiere Pro", ("Adobe Premiere Pro",), ("RETURN",)),
    # a ESCOLHA DE PASTA/ARQUIVO que abre sozinha (ex.: "Localizar" do aviso "Arquivos de máscara ausentes" do 26 — o Return
    # do vigia no aviso é o "Localizar"): Cancelar; o aviso volta e, logo depois de um Cancelar destes, o modal sem título
    # recebe ESC = "Agora não" (ver `_modal_sem_titulo`). Medido 2026-10-08 (projeto sem a pasta `<projeto> Masks`).
    ("Adobe Premiere Pro", ("Abrir", "Open", "Escolher", "Choose"), ("Cancelar", "Cancel")),
    # a janela do macOS só entrega o TÍTULO: "Relatório de Problemas para Adobe Premiere (Beta)" — só de Premiere
    ("Problem Reporter", ("Relatório de Problemas para Adobe Premiere", "Problem Report for Adobe Premiere",
                          "encerrou inesperadamente", "quit unexpectedly"), ("OK", "Ignorar", "Ignore")),
    ("Relatório de Problemas", ("encerrou inesperadamente", "quit unexpectedly"), ("OK", "Ignorar", "Ignore")),
    ("Crash", ("Ocorreu um erro", "An error occurred", "relatório de erro", "crash report"), ("Não enviar", "Don't Send", "Don’t Send")),
]

# Os diálogos do Premiere (25/26/27) NÃO são "window" para a acessibilidade: são UI elements com subrole AXDialog, e
# os BOTÕES deles não aparecem (medido 2026-10-07, "Carregar projeto" no 26.0.2). O que funciona: conferir que o diálogo
# EM FOCO (AXFocusedWindow) tem o título conhecido, trazer o Premiere para a frente e mandar Return — o botão padrão
# (OK no "Carregar projeto" e no "Converter projeto"; Cancelar no "Projeto modificado", que não grava nada).
_DESCREVER = r'''
set saida to ""
tell application "System Events"
  repeat with nomeP in {%s}
    try
      tell process (nomeP as text)
        set foco to ""
        try
          set foco to name of (value of attribute "AXFocusedWindow")
        end try
        if foco is missing value then set foco to ""
        -- os elementos (onde o Premiere põe os diálogos) E as janelas (onde o macOS põe o "Relatório de Problemas")
        set lista to {}
        try
          set lista to lista & (every window)
        end try
        try
          set lista to lista & (every UI element)
        end try
        repeat with e in lista
          try
            set t to name of e
            if t is missing value then set t to ""
            set sr to ""
            try
              set sr to subrole of e
            end try
            if sr is missing value then set sr to ""
            set bs to ""
            try
              repeat with b in (every button of e)
                try
                  set nb to name of b
                  if nb is not missing value then set bs to bs & nb & "|"
                end try
              end repeat
            end try
            set ts to ""
            try
              repeat with x in (every static text of e)
                set ts to ts & (value of x as text) & " ¦ "
              end repeat
            end try
            -- separadores que texto nenhum usa (o texto do "Relatório de Problemas" tem quebras de linha)
            set US to (ASCII character 31)
            set saida to saida & (nomeP as text) & US & t & US & sr & US & bs & US & ts & US & foco & (ASCII character 30)
          end try
        end repeat
      end tell
    end try
  end repeat
end tell
return saida
'''


def _processos() -> list[str]:
    r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of every process'],
                       capture_output=True, text=True, timeout=30)
    nomes = [n.strip() for n in r.stdout.split(",")]
    return sorted({n for n in nomes if any(p in n for p in PROCESSOS) or "Crash" in n or "Problem" in n})


def janelas() -> list[dict]:
    procs = _processos()
    if not procs:
        return []
    alvo = ", ".join('"%s"' % p for p in procs)
    r = subprocess.run(["osascript", "-e", _DESCREVER % alvo], capture_output=True, text=True, timeout=60)
    out = []
    for linha in r.stdout.split("\x1e"):
        partes = linha.split("\x1f")
        if len(partes) < 6:
            continue
        proc, titulo, papel, botoes, textos, foco = partes[:6]
        out.append({"processo": proc, "titulo": titulo, "papel": papel, "botoes": [b for b in botoes.split("|") if b],
                    "textos": textos[:2000], "em_foco": foco == titulo and titulo != ""})
    return out


def _as(texto: str) -> str:
    """Texto para AppleScript: entre aspas, com \\ e " escapados — acento como é (o \\u00f3 do JSON o AppleScript não lê)."""
    return '"' + texto.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _apertar(processo: str, titulo: str, botao: str) -> str:
    """Botão pelo NOME (janelas comuns do macOS, como o relatório de falha)."""
    js = '''tell application "System Events" to tell process %s
      click button %s of (first UI element whose name is %s)
      return "ok"
    end tell''' % (_as(processo), _as(botao), _as(titulo))
    r = subprocess.run(["osascript", "-e", js], capture_output=True, text=True, timeout=30)
    return (r.stdout or r.stderr).strip()


def _return(processo: str, titulo: str) -> str:
    """Return no diálogo do Premiere — SÓ se o diálogo em foco ainda for o de título conhecido."""
    js = '''tell application "System Events" to tell process %s
      set f to value of attribute "AXFocusedWindow"
      if (name of f) is not %s then
        -- o diálogo conhecido está aberto mas sem foco (outro por cima, ou o app atrás): traz ELE para a frente
        try
          perform action "AXRaise" of (first UI element whose name is %s)
        end try
        delay 0.3
        set f to value of attribute "AXFocusedWindow"
        if (name of f) is not %s then return "o foco não é o diálogo esperado: nada feito"
      end if
      set frontmost to true
      delay 0.3
      set f to value of attribute "AXFocusedWindow"
      if (name of f) is not %s then return "o foco mudou: nada feito"
      keystroke return
      return "return"
    end tell''' % (_as(processo), _as(titulo), _as(titulo), _as(titulo), _as(titulo))
    r = subprocess.run(["osascript", "-e", js], capture_output=True, text=True, timeout=30)
    return (r.stdout or r.stderr).strip()


def _registrar(evento: dict) -> None:
    os.makedirs(PASTA, exist_ok=True)
    with open(os.path.join(PASTA, "vigia.jsonl"), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(evento, ensure_ascii=False) + "\n")


def _print(nome: str) -> str:
    os.makedirs(PASTA, exist_ok=True)
    arq = os.path.join(PASTA, time.strftime("%Y%m%d-%H%M%S") + "-" + "".join(c if c.isalnum() else "_" for c in nome)[:40] + ".png")
    subprocess.run(["screencapture", "-x", arq], capture_output=True, timeout=30)
    return arq


def principal(j: dict) -> bool:
    """A janela PRINCIPAL do Premiere também é AXDialog: o título é o caminho do projeto, vazio, ou a tela inicial."""
    t = j["titulo"]
    # ⚠️ "Adobe Premiere Pro" NÃO é a principal: é o título dos ALERTAS genéricos ("The project could not be loaded…")
    return t == "" or t.startswith("/") or t.endswith(".prproj") or t.endswith(".prproj *") or t in ("Início", "Home")


def regra_para(j: dict):
    texto = j["titulo"] + " " + j["textos"]
    for proc, sinais, botoes in REGRAS:
        if proc in j["processo"] and any(s in texto for s in sinais):
            for b in botoes:
                if b == "RETURN" or b in j["botoes"]:
                    return b
    return None


PID = os.path.join(PASTA, "vigia.pid")


def _premiere_aberto() -> bool:
    return subprocess.run(["pgrep", "-f", r"^/Applications/Adobe Premiere Pro[^/]*/Adobe Premiere Pro[^/]*\.app/Contents/MacOS/Adobe Premiere Pro( \(Beta\)| 20[0-9][0-9])$"], capture_output=True).returncode == 0


MANDATO = os.path.join(PASTA, "vigia.mandato")


def _vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def mandato_valido() -> tuple[bool, str]:
    """⛔⛔ O vigia só AGE com mandato (autor, 2026-11-15): "só intervir em janelas quando o Ciclo Assist ou o Claude
    estiverem pilotando, nunca depois que terminarem e liberarem a máquina". MEDIDO no mesmo dia: ligado pelo
    `esperar_ponte()` de um `python3 -c` de 1 s, ele ficou vivo a MANHÃ INTEIRA e apertou Return ~30× no Color Picker do
    editor (e um OK num relatório de falha do Avid). Mandato = o processo DONO vivo E dentro do prazo (se houver)."""
    try:
        with open(MANDATO, encoding="utf-8") as fh:
            m = json.load(fh)
    except (OSError, ValueError):
        return False, "sem mandato"
    if not _vivo(int(m.get("dono", 0))):
        return False, f"o dono {m.get('dono')} terminou"
    if m.get("ate") and time.time() > float(m["ate"]):
        return False, "mandato vencido"
    return True, m.get("motivo", "")


def ligar(dono: int | None = None, ttl_s: float | None = None, motivo: str = "") -> int | None:
    """Dá o MANDATO ao processo `dono` (padrão: quem chama) e sobe o vigia (um só). O vigia sai sozinho quando o dono
    terminar ou o prazo `ttl_s` vencer sem `renovar()`. Desligar = `desligar()` (ou use `with pilotando(...)`)."""
    if sys.platform != "darwin":
        return None                   # Windows: pendente (UI Automation)
    os.makedirs(PASTA, exist_ok=True)
    with open(MANDATO, "w", encoding="utf-8") as fh:
        json.dump({"dono": dono or os.getpid(), "ate": (time.time() + ttl_s) if ttl_s else None, "motivo": motivo,
                   "desde": time.strftime("%Y-%m-%d %H:%M:%S")}, fh)
    try:
        with open(PID, encoding="utf-8") as fh:
            pid = int(fh.read().strip())
        if _vivo(pid):
            return pid
    except (OSError, ValueError):
        pass
    log = open(os.path.join(PASTA, "vigia.log"), "a", encoding="utf-8")
    pr = subprocess.Popen([sys.executable, "-m", "lab.bancadas.vigia_dialogos"], cwd=RAIZ, stdout=log, stderr=log,
                          start_new_session=True)
    with open(PID, "w", encoding="utf-8") as fh:
        fh.write(str(pr.pid))
    return pr.pid


def renovar(ttl_s: float) -> None:
    try:
        with open(MANDATO, encoding="utf-8") as fh:
            m = json.load(fh)
        m["ate"] = time.time() + ttl_s
        with open(MANDATO, "w", encoding="utf-8") as fh:
            json.dump(m, fh)
    except (OSError, ValueError):
        pass


def desligar() -> None:
    """Tira o mandato e encerra o vigia. Chame no `finally` de toda pilotagem."""
    for arq in (MANDATO,):
        try:
            os.remove(arq)
        except OSError:
            pass
    try:
        with open(PID, encoding="utf-8") as fh:
            pid = int(fh.read().strip())
        if _vivo(pid):
            os.kill(pid, 15)
        os.remove(PID)
    except (OSError, ValueError):
        pass


class pilotando:
    """`with pilotando("rodada B07"):` — liga com mandato preso a ESTE processo e desliga no fim, aconteça o que acontecer."""
    def __init__(self, motivo: str = "", ttl_s: float | None = None):
        self.motivo, self.ttl_s = motivo, ttl_s

    def __enter__(self):
        ligar(motivo=self.motivo, ttl_s=self.ttl_s)
        return self

    def __exit__(self, *exc):
        desligar()
        return False


def _relatorio_adobe() -> str | None:
    """A janela "Ocorreu um erro" da Adobe (processo AdobeCrashReport) não expõe NADA à acessibilidade (2026-10-07).
    Ela só relata um Premiere que já morreu: fechá-la = "Não enviar". Pede para sair; se não sair, encerra o processo."""
    r = subprocess.run(["pgrep", "-x", "AdobeCrashReport"], capture_output=True, text=True)
    pids = r.stdout.split()
    if not pids:
        return None
    img = _print("relatorio_adobe")
    subprocess.run(["osascript", "-e", 'tell application "AdobeCrashReport" to quit'], capture_output=True, timeout=15)
    time.sleep(3)
    if subprocess.run(["pgrep", "-x", "AdobeCrashReport"], capture_output=True).returncode == 0:
        for pid in pids:
            try:
                os.kill(int(pid), 15)
            except OSError:
                pass
        modo = "encerrado (TERM)"
    else:
        modo = "saiu (quit)"
    _registrar({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "acao": "fechou o relatório de erro da Adobe", "modo": modo,
                "print": img})
    print(time.strftime("%H:%M:%S"), "fechou o relatório de erro da Adobe:", modo, flush=True)
    return modo


_ULTIMO_CANCELAR = [0.0]          # quando o vigia cancelou uma escolha de pasta/arquivo (ver REGRAS)


_MODAL_SEM_TITULO = r'''
tell application "System Events" to tell process %s
  repeat with e in (every UI element)
    try
      set n to name of e
      if n is missing value then set n to ""
      if n is "" and (subrole of e) is "AXDialog" and (value of attribute "AXModal" of e) is true then
        set {w, h} to size of e
        if w <= 500 and h <= 300 then
          perform action "AXRaise" of e
          delay 0.3
          set frontmost to true
          delay 0.3
          %s
          return "%s (" & w & "x" & h & ")"
        end if
      end if
    end try
  end repeat
  return ""
end tell
'''


def _modal_sem_titulo() -> str | None:
    """Alerta do Premiere SEM título para a acessibilidade, modal e pequeno ("Project Modified", "The project could not
    be loaded…", 476×247 no 25.6.5) — a janela principal também não tem título, mas não é modal. Print, Return (o
    botão padrão: OK no alerta, Cancelar no "Project Modified") e registro.
    ⛔ Só tamanho de ALERTA (≤ 500 × 300): o Color Picker do Premiere também é um modal sem título (512 × 374/354/474) e
    levou Return ~30× em 2026-11-15 (o filtro era `w < 1200`)."""
    for proc in _processos():
        if "Premiere" not in proc:
            continue
        chk = subprocess.run(["osascript", "-e", 'tell application "System Events" to tell process %s to get (count of (every UI element whose subrole is "AXDialog"))' % _as(proc)],
                             capture_output=True, text=True, timeout=30)
        if not chk.stdout.strip() or chk.stdout.strip() == "0":
            continue
        img = None
        # logo depois de cancelar a escolha de pasta que o Return deste mesmo aviso abriu: ESC ("Agora não"), senão é laço
        esc = time.time() - _ULTIMO_CANCELAR[0] < 20
        tecla, nome = ("key code 53", "esc") if esc else ("keystroke return", "return")
        r = subprocess.run(["osascript", "-e", _MODAL_SEM_TITULO % (_as(proc), tecla, nome)], capture_output=True, text=True, timeout=30)
        res = (r.stdout or r.stderr).strip()
        if res.startswith(("return", "esc")):
            if esc:
                _ULTIMO_CANCELAR[0] = 0.0
            img = _print("modal_sem_titulo")
            _registrar({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "acao": "apertou", "botao": ("ESC" if esc else "RETURN") + " (modal sem título)",
                        "resultado": res, "print_depois": img, "processo": proc})
            print(time.strftime("%H:%M:%S"), "apertou", nome.upper(), "num modal sem título em", proc, "→", res, flush=True)
            return res
    return None


def vigiar(intervalo: float = 1.5, ate_s: float | None = None, sem_premiere_s: float = 600, persistente_s: float = 60) -> int:
    """Vigia até `ate_s` ou até ficar `sem_premiere_s` sem Premiere. Diálogo DESCONHECIDO: ignorado enquanto for
    passageiro (janelas de progresso — "Importar arquivos", "Codificando…" — também são AXDialog sem botão); se FICAR
    mais de `persistente_s`, print + registro, uma vez, e o vigia CONTINUA (sair deixava a bancada sem proteção)."""
    fim = time.time() + ate_s if ate_s else None
    primeira_vez: dict[tuple, float] = {}
    avisados: set = set()
    ultimo_premiere = time.time()
    while fim is None or time.time() < fim:
        ok, motivo = mandato_valido()
        if not ok:
            _registrar({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "acao": "saiu", "motivo": motivo})
            print(time.strftime("%H:%M:%S"), "vigia saindo:", motivo, flush=True)
            return 0
        if _premiere_aberto():
            ultimo_premiere = time.time()
        elif time.time() - ultimo_premiere > sem_premiere_s:
            return 0
        try:
            _relatorio_adobe()
            js = janelas()
            if any(j["papel"] == "AXDialog" and j["titulo"] == "" for j in js) and mandato_valido()[0]:
                time.sleep(2)             # um modal sem título: dá 2 s (o print mostra o que era) e responde
                _print("antes_modal_sem_titulo")
                _modal_sem_titulo()
        except subprocess.TimeoutExpired:
            js = []
        agora = time.time()
        presentes = set()
        feitos_agora = set()          # a mesma janela vem duas vezes (como window e como UI element)
        for j in js:
            if (j["processo"], j["titulo"]) in feitos_agora:
                continue
            if not j["botoes"] and j["papel"] != "AXDialog":
                continue
            if principal(j):
                continue
            b = regra_para(j)
            chave = (j["processo"], j["titulo"])
            if b and not mandato_valido()[0]:
                continue                  # o mandato caiu entre a leitura e a ação: não toca em nada
            if b:
                img = _print(j["titulo"] or j["processo"])
                r = _return(j["processo"], j["titulo"]) if b == "RETURN" else _apertar(j["processo"], j["titulo"], b)
                if b in ("Cancelar", "Cancel"):
                    _ULTIMO_CANCELAR[0] = time.time()
                _registrar({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "acao": "apertou", "botao": b, "resultado": r,
                            "print": img, **j})
                print(time.strftime("%H:%M:%S"), "apertou", b, "em", j["processo"], "/", j["titulo"], "→", r, flush=True)
                feitos_agora.add((j["processo"], j["titulo"]))
                continue
            presentes.add(chave)
            primeira_vez.setdefault(chave, agora)
            if agora - primeira_vez[chave] > persistente_s and chave not in avisados:
                avisados.add(chave)
                img = _print("DESCONHECIDO " + (j["titulo"] or j["processo"]))
                _registrar({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "acao": "DESCONHECIDO persistente — precisa do autor",
                            "print": img, **j})
                print(time.strftime("%H:%M:%S"), "DIÁLOGO DESCONHECIDO PARADO (não cliquei):", j, flush=True)
        for k in list(primeira_vez):
            if k not in presentes:
                primeira_vez.pop(k)
        time.sleep(intervalo)
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "explorar":
        for j in janelas():
            print(json.dumps(j, ensure_ascii=False))
        return 0
    if not mandato_valido()[0]:
        print("vigia: sem mandato (ninguém pilotando) — não vigio. Ligue por `ligar()` ou `with pilotando(...)`.")
        return 2
    return vigiar()


if __name__ == "__main__":
    raise SystemExit(main())
