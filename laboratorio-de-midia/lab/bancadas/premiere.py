"""Bancada do Premiere Pro — o laboratório opera o Premiere pela PONTE (`premiere/ponte-cep/`).

A ponte é uma extensão CEP invisível que sobe sozinha com o Premiere e executa ExtendScript recebido por
HTTP em 127.0.0.1, com token (autorizada pelo autor em 2026-10-06, "ponte livre"). Instrumento de bancada:
**instalar → rodar → remover** — instalada, ela sobe toda vez que o Premiere abre (banco,
plugins/premiere-cep/painel-servido-e-identidade.md §1).

Instala por CÓPIA, nunca symlink: o `com.orbita.sonda` era symlink para o SSD e quebrou quando o Órbita
mudou de pasta (2026-10-06).

    from lab.bancadas import premiere as p
    p.instalar(); p.reabrir_premiere("2025"); p.esperar_ponte()
    p.executar("app.version")
    ...
    p.remover()
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import http.client
import urllib.error
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, "premiere", "ponte-cep")
ID = "com.usuario.lab.ponte"


def _pasta_extensoes() -> str:
    if os.name == "nt":
        return os.path.join(os.environ["APPDATA"], "Adobe", "CEP", "extensions")
    return os.path.expanduser("~/Library/Application Support/Adobe/CEP/extensions")


def _pasta_dados() -> str:
    if os.name == "nt":
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "laboratorio-de-midia")
    return os.path.expanduser("~/Library/Application Support/laboratorio-de-midia")


ARQ_PONTE = os.path.join(_pasta_dados(), "ponte-premiere.json")


def instalar() -> str:
    destino = os.path.join(_pasta_extensoes(), ID)
    if os.path.lexists(destino):
        remover()
    shutil.copytree(FONTE, destino, ignore=shutil.ignore_patterns("._*", ".DS_Store"))
    return destino


def remover() -> bool:
    destino = os.path.join(_pasta_extensoes(), ID)
    if os.path.islink(destino):
        os.unlink(destino)
    elif os.path.isdir(destino):
        shutil.rmtree(destino)
    else:
        return False
    return True


def _nome(ano: str) -> str:
    """'2025' → 'Adobe Premiere Pro 2025'; 'Beta' → 'Adobe Premiere Pro (Beta)' (o Beta 27.1, 2026-10-07)."""
    return "Adobe Premiere Pro (Beta)" if ano.lower() == "beta" else f"Adobe Premiere Pro {ano}"


def _maior(ano: str) -> str:
    """O começo do app.version de cada ano: '2025' → '25.'. O Beta não tem ano fixo: qualquer um serve."""
    return "" if ano.lower() == "beta" else ano[2:] + "."


def _app(ano: str) -> str:
    if os.name == "nt":
        return rf"C:\Program Files\Adobe\{_nome(ano)}\Adobe Premiere Pro.exe"
    return f"/Applications/{_nome(ano)}/{_nome(ano)}.app"


def preset_prores(ano: str) -> str:
    """O preset "Match Source - Apple ProRes 422" da instalação. ⛔ No Windows o `exportAsMediaDirect` RECUSA o preset nulo
    ("Illegal Parameter type", 23.2, 2026-10-10); o arquivo está em `Settings/EncoderPresets/ConsolidateAndTranscode`."""
    if os.name == "nt":
        return os.path.join(os.path.dirname(_app(ano)), "Settings", "EncoderPresets", "ConsolidateAndTranscode",
                            "Match Source - Apple ProRes 422.epr")
    return os.path.join(_app(ano), PRESET_PRORES)


def fechar_premiere(ano: str, ate_s: float = 180) -> bool:      # o Beta 27.1 levou > 60 s para sair
    """Fecha pelo próprio app (sem matar): sem projeto aberto, sai sem perguntar."""
    if sys.platform != "darwin":
        raise NotImplementedError("Windows: pendente")
    # pela ponte primeiro: o "quit" do AppleScript ficou 60 s sem resposta no 26.0.2 parado na tela inicial
    # (2026-10-07), e o app.quit() da ponte fechou na hora
    try:
        with open(ARQ_PONTE, encoding="utf-8") as fh:
            info = json.load(fh)
        if str(info.get("premiere", "")).startswith(_maior(ano)) and (ano.lower() != "beta" or
                                                                   int(str(info["premiere"]).split(".")[0]) >= 27):
            executar("app.quit()", info=info, timeout=15)
    except (OSError, ValueError, RuntimeError):
        pass
    try:
        subprocess.run(["osascript", "-e", f'tell application "{_nome(ano)}" to quit'],
                       capture_output=True, timeout=ate_s)
    except subprocess.TimeoutExpired:
        pass
    limite = time.time() + ate_s
    while time.time() < limite:
        # só o executável PRINCIPAL: o AdobeIPCBroker (com o caminho do Premiere nos argumentos) e o
        # crashpad_handler (dentro de Contents/MacOS) ficam vivos depois que o Premiere fecha (2026-10-06)
        if subprocess.run(["pgrep", "-f", "^" + re.escape(f"{_app(ano)}/Contents/MacOS/{_nome(ano)}") + "( |$)"],
                          capture_output=True).returncode != 0:
            return True
        time.sleep(1)
    return False


def abrir_premiere(ano: str) -> None:
    if sys.platform != "darwin":
        raise NotImplementedError("Windows: pendente")
    # sem o LANG/LC_* da sessão do terminal (matriz de plataforma, seção B: o MC aberto assim aborta; regra do piloto)
    env = {k: v for k, v in os.environ.items() if k != "LANG" and not k.startswith("LC_")}
    subprocess.run(["open", "-a", _app(ano)], check=True, env=env)


def reabrir_premiere(ano: str) -> None:
    """O CEP só varre a pasta de extensões quando o Premiere abre."""
    if os.path.exists(ARQ_PONTE):
        os.replace(ARQ_PONTE, ARQ_PONTE + ".anterior")
    fechar_premiere(ano)
    abrir_premiere(ano)


def esperar_ponte(ate_s: float = 180, vigia: bool = True) -> dict:
    """O VIGIA DE DIÁLOGOS (fecha os diálogos conhecidos que travariam a ponte) sobe PRESO a este processo: quando o
    script que chamou terminar, ele sai sozinho (⛔ 2026-11-15: sem isso ele sobreviveu a um `python3 -c` e apertou
    Return no Premiere do editor a manhã inteira). Uso interativo, com alguém na frente: `vigia=False`."""
    if vigia:
        from . import vigia_dialogos
        vigia_dialogos.ligar(motivo="premiere.esperar_ponte")
    limite = time.time() + ate_s
    while time.time() < limite:
        if os.path.exists(ARQ_PONTE):
            with open(ARQ_PONTE, encoding="utf-8") as fh:
                info = json.load(fh)
            try:
                executar("1+1", info=info, timeout=10)
                return info
            except OSError:
                pass
        time.sleep(2)
    raise TimeoutError(f"a ponte não subiu em {ate_s:.0f} s (log: {os.path.join(_pasta_dados(), 'ponte-premiere.log')})")


class PremiereCaiu(RuntimeError):
    """A ponte sumiu E o Premiere não está mais rodando: caiu (ou foi encerrado). `retomar()` reabre e refaz."""


def _premiere_vivo() -> bool:
    return subprocess.run(["pgrep", "-f", r"^/Applications/Adobe Premiere Pro[^/]*/Adobe Premiere Pro[^/]*\.app/Contents/MacOS/Adobe Premiere Pro( \(Beta\)| 20[0-9][0-9])$"], capture_output=True).returncode == 0


def retomar(ano: str, funcao, *args, tentativas: int = 2, **kw):
    """Roda `funcao`; se o Premiere CAIR no meio, espera o vigia fechar as janelas de falha, reabre o Premiere `ano`
    e roda de novo (até `tentativas` vezes). Cada queda fica no registro do vigia."""
    from . import vigia_dialogos
    for n in range(tentativas + 1):
        try:
            return funcao(*args, **kw)
        except PremiereCaiu as e:
            vigia_dialogos._registrar({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "acao": "QUEDA do Premiere",
                                       "funcao": getattr(funcao, "__name__", str(funcao)), "tentativa": n + 1, "erro": str(e)})
            print(time.strftime("%H:%M:%S"), f"⚠️ o Premiere caiu ({e}); reabrindo e refazendo ({n + 1}/{tentativas})", flush=True)
            if n == tentativas:
                raise
            time.sleep(8)                     # o vigia fecha o "encerrou inesperadamente" / o relatório da Adobe
            reabrir_premiere(ano)
            esperar_ponte(300)


def executar(codigo: str, info: dict | None = None, timeout: float = 600):
    """Roda ExtendScript no Premiere e devolve o valor da última expressão (já desserializado).
    Erro no ExtendScript vira RuntimeError com a linha."""
    if info is None:
        with open(ARQ_PONTE, encoding="utf-8") as fh:
            info = json.load(fh)
    req = urllib.request.Request(f"http://127.0.0.1:{info['porta']}/executar", data=codigo.encode("utf-8"),
                                 headers={"X-Lab-Token": info["token"], "Content-Type": "text/plain"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resposta = json.loads(r.read().decode("utf-8"))
    except (ConnectionError, urllib.error.URLError, http.client.HTTPException) as e:
        time.sleep(2)
        if not _premiere_vivo():
            raise PremiereCaiu(f"{type(e).__name__}: {e}") from e
        raise
    # strict=False: parâmetro binário (o Blob do Lumetri, 2026-10-07) traz caractere de controle dentro da string
    saida = json.loads(resposta["saida"], strict=False) if resposta.get("saida") else {"ok": False, "erro": "sem saída"}
    if not saida.get("ok"):
        raise RuntimeError(f"ExtendScript: {saida.get('erro')} (linha {saida.get('linha')})")
    return saida.get("valor")


# ---------------------------------------------------------------------------------------------------------
# A bancada: o mesmo roteiro e o mesmo json da do Resolve (`premiere.json` no lugar de `resolve.json`),
# para o `conferir.py` servir aos dois.
# ---------------------------------------------------------------------------------------------------------
import re

TICKS = 254016000000          # ticks do Premiere por segundo
PRESET_PRORES = "Contents/Settings/EncoderPresets/ConsolidateAndTranscode/Match Source - Apple ProRes 422.epr"

_LIB = r"""
function _lab_itens(pasta, saida) { saida = saida || [];
  for (var i = 0; i < pasta.children.numItems; i++) { var c = pasta.children[i];
    if (c.type == 2) _lab_itens(c, saida); else saida.push(c); }
  return saida; }
function _lab_seq(nome) { for (var i = 0; i < app.project.sequences.numSequences; i++) {
    if (app.project.sequences[i].name == nome) return app.project.sequences[i]; } return null; }
function _lab_trilhas(col, n) { var o = [];
  for (var i = 0; i < n; i++) { var t = col[i], cl = [];
    for (var j = 0; j < t.clips.numItems; j++) { var c = t.clips[j];
      cl.push({nome: c.name, inicio: c.start.ticks, fim: c.end.ticks, entrada: c.inPoint.ticks}); }
    o.push({trilha: i + 1, nome: t.name, itens: cl}); }
  return o; }
function _lab_seqinfo(s) { var st = s.getSettings();
  return {nome: s.name, id: s.sequenceID, zero: s.zeroPoint, fim: s.end, timebase: s.timebase,
    largura: st.videoFrameWidth, altura: st.videoFrameHeight, par: st.videoPixelAspectRatio,
    canais_de_audio: st.audioChannelCount, tipo_de_audio: st.audioChannelType, exibicao_tc: st.videoDisplayFormat,
    video: _lab_trilhas(s.videoTracks, s.videoTracks.numTracks), audio: _lab_trilhas(s.audioTracks, s.audioTracks.numTracks)}; }
"""


def _js(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _ler(trabalho: str) -> dict:
    caminho = os.path.join(trabalho, "premiere.json")
    if os.path.isfile(caminho):
        with open(caminho, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def _gravar(trabalho: str, dados: dict) -> None:
    os.makedirs(trabalho, exist_ok=True)
    with open(os.path.join(trabalho, "premiere.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def _canais(audio_info: str | None) -> str:
    """'48000 Hz - 24-bit - Stereo mapped to 2 Mono' → '2'; '8 Channel' → '8'; 'Mono' → '1'.
    ⚠️ O 27.1 (Beta) TRADUZ este texto conforme o idioma do app ('Estéreo mapeado para 2 Mono', 'Canal 8 mapeado
    para 8 Mono'; o 26.0.2 em português ainda escrevia em inglês): ler os dois idiomas."""
    if not audio_info:
        return "0"
    m = (re.search(r"(\d+) Channel", audio_info) or re.search(r"Canal (\d+)", audio_info)
         or re.search(r"- (\d+) Mono$", audio_info) or re.search(r"(?:mapped to|mapeado para) (\d+) Mono", audio_info))
    if m:
        return m.group(1)
    cabeca = re.split(r" (?:mapped to|mapeado para)", audio_info)[0]
    if "Stereo" in cabeca or "Estéreo" in cabeca:
        return "2"
    if "Mono" in cabeca:
        return "1"
    m = re.search(r"([\d.]+) ", audio_info.split(" - ")[-1])
    return m.group(1) if m else "?"


def _tc_de_amostras(tc: str, fps: float, sr: int = 48000) -> str:
    """O Premiere mostra o início de áudio em amostras ('01:00:00:00000'): vira HH:MM:SS:FF."""
    h, m, s, a = tc.split(":")
    return f"{h}:{m}:{s}:{int(int(a) / sr * fps + 1e-6):02d}"


def preparar(caso: str, trabalho: str, nome_projeto: str, variante: str | None = None) -> dict:
    from .. import tc as _tc
    dados = _ler(trabalho)
    projeto = os.path.join(os.path.abspath(trabalho), nome_projeto + ".prproj")
    with open(os.path.join(caso, "verdade.json"), encoding="utf-8") as fh:
        verdade = json.load(fh)
    arqs = [os.path.join(os.path.abspath(caso), a["arquivo"]) for a in verdade["arquivos"]
            if variante is None or a.get("variante") == variante]
    recusados = dados.get("recusados", [])
    os.makedirs(os.path.abspath(trabalho), exist_ok=True)     # o app.newProject não cria a pasta: devolve false
    aberto = executar(_LIB + """(function(){ var alvo = %s, atual = '';
      try { atual = app.project.path; } catch (e) {}
      if (atual == alvo) return 'já aberto';
      if (atual) { try { app.project.save(); app.project.closeDocument(1, 0); } catch (e) {} }
      if (new File(alvo).exists) return app.openDocument(alvo, true, true, true);
      return app.newProject(alvo); })()""" % _js(projeto))
    if executar("(function(){ try { return app.project.path; } catch (e) { return ''; } })()") != projeto:
        raise RuntimeError(f"o Premiere não abriu {projeto} (devolveu {aberto!r})")
    ja = set(executar(_LIB + "(function(){var o=[], it=_lab_itens(app.project.rootItem); for (var i=0;i<it.length;i++) "
                             "o.push(it[i].getMediaPath()); return o;})()") or [])
    novos = [a for a in arqs if a not in ja and a not in recusados]
    if novos:
        # ⚠️ o Premiere mostra "File Import Failure" MESMO com suppressUI, e o diálogo trava o script; e
        # o retorno é true com o arquivo recusado (banco). Quem foi recusado fica na lista e não volta.
        dados["import_devolveu"] = executar("app.project.importFiles(%s, true, app.project.rootItem, false)" % _js(novos))
    itens = executar(_LIB + """(function(){ var o=[], it=_lab_itens(app.project.rootItem);
      for (var i=0;i<it.length;i++) { var c=it[i]; if (!c.getMediaPath()) continue;
        var f=c.getFootageInterpretation(), m=c.getAudioChannelMapping;
        o.push({nome:c.name, caminho:c.getMediaPath(), md:c.getProjectMetadata(), fps:f.frameRate,
                par:f.pixelAspectRatio, campo:f.fieldType, mapa:{tipo:m.audioChannelsType, clipes:m.audioClipsNumber}}); }
      return o; })()""")
    presentes = {i["caminho"] for i in itens}
    dados["recusados"] = sorted(set(recusados) | {a for a in novos if a not in presentes})
    a0 = verdade["arquivos"][0]
    fps_nome = a0.get("fps") or (a0.get("video") or {}).get("fps")      # o B01 é de antes do campo "fps"
    fps_v = float(_tc.taxa(fps_nome))
    pool = []
    for i in itens:
        kv = dict(re.findall(r"<premierePrivateProjectMetaData:Column\.Intrinsic\.(\w+)>([^<]*)</", i["md"]))
        tem_v, tem_a = bool(kv.get("VideoInfo")), bool(kv.get("AudioInfo"))
        inicio = kv.get("MediaStart", "")
        if inicio.count(":") == 3 and len(inicio.split(":")[3]) > 2:
            inicio = _tc_de_amostras(inicio, fps_v)
        quadros = ""
        if tem_v and kv.get("MediaDuration"):
            b = round(i["fps"])
            quadros = str(_tc.tc_para_quadros(kv["MediaDuration"].replace(";", ":"), b))
        res = kv.get("VideoInfo", "")
        m = re.match(r"(\d+) x (\d+)", res)
        # o Premiere escreve o DF com ";" em TUDO ("01;00;59;15") e não tem campo de drop-frame: a marca é o ";"
        df_clipe = ";" in inicio
        if df_clipe:
            inicio = inicio.replace(";", ":")[:8] + ";" + inicio.replace(";", ":")[9:]
        # "File Name" é o ARQUIVO: o nome do item pode ser o do CLIPE (o OP-Atom costurado entra como "B01" nos 3
        # itens no 26.0.2) e aí as sequências se confundiam
        pool.append({"Drop frame": "1" if df_clipe else "0", "File Name": os.path.basename(i["caminho"]),
                     "Clip Name": i["nome"], "Type": "Video + Audio" if tem_v and tem_a else ("Video" if tem_v else "Audio"),
                     "Start TC": inicio, "End TC": kv.get("MediaEnd"), "Frames": quadros,
                     "FPS": round(i["fps"], 6) if tem_v else fps_v, "Resolution": f"{m.group(1)}x{m.group(2)}" if m else "",
                     "PAR": i["par"], "Audio Ch": _canais(kv.get("AudioInfo")), "Video Codec": None,
                     "Format": os.path.splitext(i["nome"])[1].lstrip(".").upper(),
                     "AudioInfo": kv.get("AudioInfo"), "VideoInfo": kv.get("VideoInfo"), "MediaTimebase": kv.get("MediaTimebase"),
                     "mapa_de_audio": i["mapa"], "File Path": i["caminho"]})
    # uma sequência por clipe, começando no TC do clipe (setZeroPoint), como a timeline do Resolve
    por_nome = {os.path.basename(a["arquivo"]): a for a in verdade["arquivos"]}
    timelines = []
    for c in pool:
        esp = por_nome.get(c["File Name"], a0)
        e_fps = esp.get("fps") or (esp.get("video") or {}).get("fps") or fps_nome
        nome = "TL " + c["File Name"]
        info = executar(_LIB + """(function(){ var nome=%s, s=_lab_seq(nome);
          if (!s) { var it=_lab_itens(app.project.rootItem), alvo=null;
            for (var i=0;i<it.length;i++) if (it[i].getMediaPath()==%s) alvo=it[i];
            s = app.project.createNewSequenceFromClips(nome, [alvo], app.project.rootItem); s.name = nome;
            s.setZeroPoint(%s); }
          return _lab_seqinfo(s); })()""" % (_js(nome), _js(c["File Path"]), _js(str(_inicio_ticks(c, float(_tc.taxa(e_fps)))))))
        tb = int(info["timebase"])
        timelines.append({"nome": info["nome"], "clipe": c["File Name"], "modo": None if "Video" in c["Type"] else "audio",
                          "fps": e_fps, "base": round(float(_tc.taxa(e_fps))), "drop_frame": bool(esp.get("drop_frame")),
                          "id": info["id"], "inicio_tc": c["Start TC"], "zero_ticks": info["zero"],
                          "inicio_quadro": 0, "fim_quadro": int(info["fim"]) // tb, "timebase": tb,
                          "resolucao": [info["largura"], info["altura"]], "canais_de_audio": info["canais_de_audio"],
                          "tipo_de_audio": info["tipo_de_audio"], "exibicao_tc": info["exibicao_tc"],
                          "trilhas": {"video": info["video"], "audio": info["audio"]}})
    executar("app.project.save()")
    versao_app = executar("app.version")
    dados["preferencias"] = preferencias(versao_app)
    dados.update({"produto": "Adobe Premiere Pro", "versao": versao_app, "projeto": projeto,
                  "variante": variante, "fps": fps_nome, "pool": pool, "timelines": timelines,
                  "base": round(fps_v), "drop_frame": bool(verdade["arquivos"][0].get("drop_frame"))})
    _gravar(trabalho, dados)
    return {"pool": len(pool), "recusados": dados["recusados"], "timelines": [t["nome"] for t in timelines]}


def _inicio_ticks(c: dict, fps: float) -> int:
    from .. import tc as _tc
    b = round(fps)
    # o TC do clipe como NÚMERO DE QUADROS REAIS desde a meia-noite (no drop-frame, o rótulo é maior)
    q = _tc.tc_para_quadros(c["Start TC"], b, ";" in c["Start TC"])
    return int(round(q * TICKS / fps))


def stills(trabalho: str, so: list[str] | None = None, pausa: float = 0.5) -> dict:
    from .. import tc as _tc
    dados = _ler(trabalho)
    base, df = dados.get("base", 25), bool(dados.get("drop_frame"))
    # ABSOLUTO: o Premiere resolve caminho relativo pela pasta DELE (medido 2026-10-06: o still sumiu)
    pasta = os.path.join(os.path.abspath(trabalho), "stills")
    os.makedirs(pasta, exist_ok=True)
    feitos = dados.get("stills", {})
    for t in dados["timelines"]:
        if t.get("modo") in ("audio", "sem_stills") or (so and t["nome"] not in so):
            continue
        base, df = t.get("base", base), bool(t.get("drop_frame", df))      # cada sequência na taxa do SEU clipe
        dur = t["fim_quadro"]
        inicio = _tc.tc_para_quadros(t["inicio_tc"], base, df)
        virada = next((k for k in range(1, dur) if _tc.rotulo(inicio + k, base, df) // base
                       != _tc.rotulo(inicio + k - 1, base, df) // base), None)
        meia = next((k for k in range(1, dur) if _tc.rotulo(inicio + k, base, df) < _tc.rotulo(inicio + k - 1, base, df)), None)
        pos = {0, (dur - 1) // 2, dur - 1} | ({virada - 1, virada} if virada else set()) | ({meia - 1, meia} if meia else set())
        lista = []
        for k in sorted(pos):
            alvo = _tc.quadros_para_tc(inicio + k, base, df)
            arq = os.path.join(pasta, f"{t['nome']}_{k:04d}")
            r = executar("""(function(){ app.project.openSequence(%s); var s=app.project.activeSequence;
              app.enableQE(); var q=qe.project.getActiveSequence();
              s.setPlayerPosition(%s); var tc=q.CTI.timecode;
              return {cti:tc, pos:s.getPlayerPosition().ticks, exp:q.exportFramePNG(tc, %s)}; })()"""
                         % (_js(t["id"]), _js(str(k * t["timebase"])), _js(arq)))
            limite = time.time() + 10
            while not os.path.exists(arq + ".png") and time.time() < limite:
                time.sleep(0.2)
            time.sleep(pausa)
            # ⚠️ o CTI.timecode do QE é RELATIVO ao início da sequência (00:00:04:24 com a régua em 01:00:04:24,
            # medido 2026-10-06, 25.6.5): a agulha se confere pela posição em ticks do DOM
            q_agulha = int(r["pos"]) // t["timebase"]
            na_agulha = _tc.quadros_para_tc(inicio + q_agulha, base, df)
            mesmo = q_agulha == k
            lista.append({"posicao_na_timeline": k, "tc_pedido": alvo, "tc_na_agulha": na_agulha,
                          "cti_qe_relativo": r["cti"], "agulha_pegou": mesmo,
                          "exportou": os.path.exists(arq + ".png"), "arquivo": os.path.relpath(arq + ".png", trabalho)})
        feitos[t["nome"]] = lista
    dados["stills"] = feitos
    _gravar(trabalho, dados)
    return {n: [s["agulha_pegou"] and s["exportou"] for s in l] for n, l in feitos.items()}


def renderizar(trabalho: str, ano: str, so: list[str] | None = None) -> dict:
    """`exportAsMediaDirect` (sem o Media Encoder): ProRes 422 'Match Source', uma sequência por vez."""
    dados = _ler(trabalho)
    preset = preset_prores(ano)
    pasta = os.path.join(os.path.abspath(trabalho), "renders")
    os.makedirs(pasta, exist_ok=True)
    jobs = [j for j in dados.get("renders", {}).get("jobs", []) if not so or j["timeline"] not in so]
    for t in dados["timelines"]:
        if t.get("modo") == "audio" or (so and t["nome"] not in so):
            continue
        nome = t["nome"].replace("TL ", "RENDER ").rsplit(".", 1)[0] + ".mov"
        t0 = time.time()
        r = executar("""(function(){ app.project.openSequence(%s); var s=app.project.activeSequence;
          return s.exportAsMediaDirect(%s, %s, 0); })()""" % (_js(t["id"]), _js(os.path.join(pasta, nome)), _js(preset)),
                     timeout=900)
        jobs = [j for j in jobs if j["timeline"] != t["nome"]] + [
            {"timeline": t["nome"], "arquivo": "renders/" + nome, "job": str(r), "s": round(time.time() - t0, 1)}]
    dados["renders"] = {"jobs": jobs}
    _gravar(trabalho, dados)
    return dados["renders"]


# ⛔ `app.project.save()` SEM projeto aberto (o Premiere na tela inicial) DERRUBA o 25.6.5 — o try/catch não segura
# (2026-10-07, duas quedas com "Ocorreu um erro"). Só salva se `app.project.path` disser que há projeto.
FECHAR_SE_ABERTO = """(function(){ var a = ''; try { a = app.project.path; } catch (e) {}
  if (a) { app.project.save(); app.project.closeDocument(1, 0); } return a; })()"""


def salvar_e_fechar() -> None:
    executar(FECHAR_SE_ABERTO)


def guardar_projeto(trabalho: str, caso_nome: str) -> dict:
    """Salva, copia o .prproj para `resultados/<caso>/prproj/` (no Git: é o insumo do estudo de downgrade) e
    grava a impressão digital (versão do formato e de cada classe) ao lado."""
    from .. import prproj_estrutura
    dados = _ler(trabalho)
    executar("app.project.save()")
    versao = dados.get("versao") or executar("app.version")
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    destino = os.path.join(raiz, "resultados", caso_nome, "prproj")
    os.makedirs(destino, exist_ok=True)
    copia = os.path.join(destino, f"premiere-{versao}-{sys.platform}.prproj")
    shutil.copyfile(dados["projeto"], copia)
    imp = prproj_estrutura.impressao(copia)
    imp["arquivo"] = os.path.basename(copia)
    with open(copia.replace(".prproj", ".estrutura.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(imp, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return {"copia": copia, "Project": imp["Project"], "classes": len(imp["classes"])}


def rodada(caso: str, trabalho: str, nome_projeto: str, ano: str, variante: str | None = None,
           render: bool = True) -> dict:
    p = preparar(caso, trabalho, nome_projeto, variante)
    s = stills(trabalho)
    r = renderizar(trabalho, ano) if render else None
    g = guardar_projeto(trabalho, os.path.basename(os.path.abspath(caso)))
    return {"pool": p["pool"], "recusados": p["recusados"], "stills_ok": all(all(v) for v in s.values()),
            "renders": [j["job"] for j in (r or {}).get("jobs", [])], "prproj": g}


def sequencias_hd(trabalho: str, clipe_hd: str) -> dict:
    """B05: cada clipe numa sequência COM AS CONFIGURAÇÕES DO CLIPE HD (1920×1080): 'TL HD …' do jeito que o
    Premiere põe por padrão (preferência de escala da máquina) e 'TL HD AJUSTADO …' com setScaleToFrameSize."""
    dados = _ler(trabalho)
    novos = []
    for c in dados["pool"]:
        if "Video" not in c["Type"]:
            continue
        for modo, nome in (("hd", "TL HD " + c["File Name"]), ("hd_ajustado", "TL HD AJUSTADO " + c["File Name"])):
            info = executar(_LIB + """(function(){ var nome=%s, s=_lab_seq(nome);
              if (!s) { var it=_lab_itens(app.project.rootItem), hd=null, alvo=null;
                for (var i=0;i<it.length;i++) { if (it[i].getMediaPath()==%s) hd=it[i]; if (it[i].getMediaPath()==%s) alvo=it[i]; }
                s = app.project.createNewSequenceFromClips(nome, [hd], app.project.rootItem); s.name = nome;
                for (var k=s.videoTracks.numTracks-1;k>=0;k--) while (s.videoTracks[k].clips.numItems) s.videoTracks[k].clips[0].remove(false, false);
                for (var k=s.audioTracks.numTracks-1;k>=0;k--) while (s.audioTracks[k].clips.numItems) s.audioTracks[k].clips[0].remove(false, false);
                s.videoTracks[0].overwriteClip(alvo, 0);
                // "Scale to Frame Size": não é método do TrackItem do DOM no 25.6.5 ("is not a function");
                // está no QE (strings do ScriptLayerPProQE). Precisa da sequência aberta.
                if (%s) { app.project.openSequence(s.sequenceID); app.enableQE();
                  var qi = qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0); qi.setScaleToFrameSize(true); } }
              return _lab_seqinfo(s); })()""" % (_js(nome), _js(clipe_hd), _js(c["File Path"]), "true" if modo == "hd_ajustado" else "false"))
            tb = int(info["timebase"])
            dados["timelines"] = [t for t in dados["timelines"] if t["nome"] != info["nome"]]
            dados["timelines"].append({"nome": info["nome"], "clipe": c["File Name"], "modo": modo, "id": info["id"],
                                       "inicio_tc": "00:00:00:00", "inicio_quadro": 0, "fim_quadro": int(info["fim"]) // tb,
                                       "timebase": tb, "resolucao": [info["largura"], info["altura"]],
                                       "fps": dados["fps"], "base": dados["base"], "drop_frame": False,
                                       "trilhas": {"video": info["video"], "audio": info["audio"]}})
            novos.append(info["nome"])
    executar("app.project.save()")
    _gravar(trabalho, dados)
    return {"timelines": novos}


def sync_por_tc(trabalho: str, video: str, som: str) -> dict:
    """B06: a sequência começa no TC do som (o mais cedo) e cada clipe vai no SEU TC: a câmera (vídeo + som)
    no V1/A1, o BWF numa trilha de áudio abaixo. A API do Premiere não tem sincronizar/merge (banco)."""
    from .. import tc as _tc
    dados = _ler(trabalho)
    pv = next(c for c in dados["pool"] if c["File Name"] == video)
    ps = next(c for c in dados["pool"] if c["File Name"] == som)
    fps = float(_tc.taxa(dados["fps"]))
    deslocamento = (_inicio_ticks(pv, fps) - _inicio_ticks(ps, fps)) / TICKS
    nome = "TL SYNC MANUAL POR TC"
    info = executar(_LIB + """(function(){ var nome=%s, s=_lab_seq(nome);
      if (!s) { var it=_lab_itens(app.project.rootItem), v=null, a=null;
        for (var i=0;i<it.length;i++) { if (it[i].getMediaPath()==%s) v=it[i]; if (it[i].getMediaPath()==%s) a=it[i]; }
        s = app.project.createNewSequenceFromClips(nome, [v], app.project.rootItem); s.name = nome;
        for (var k=s.videoTracks.numTracks-1;k>=0;k--) while (s.videoTracks[k].clips.numItems) s.videoTracks[k].clips[0].remove(false, false);
        for (var k=s.audioTracks.numTracks-1;k>=0;k--) while (s.audioTracks[k].clips.numItems) s.audioTracks[k].clips[0].remove(false, false);
        s.setZeroPoint(%s);
        s.videoTracks[0].overwriteClip(v, %s);
        s.audioTracks[2].overwriteClip(a, 0); }
      return _lab_seqinfo(s); })()""" % (_js(nome), _js(pv["File Path"]), _js(ps["File Path"]),
                                         _js(str(_inicio_ticks(ps, fps))), deslocamento))
    tb = int(info["timebase"])
    dados["timelines"] = [t for t in dados["timelines"] if t["nome"] != nome] + [{
        "nome": info["nome"], "clipe": video, "modo": "sem_stills", "sync": "manual", "id": info["id"],
        "inicio_tc": ps["Start TC"], "inicio_quadro": 0, "fim_quadro": int(info["fim"]) // tb, "timebase": tb,
        "fps": dados["fps"], "base": dados["base"], "drop_frame": False,
        "trilhas": {"video": info["video"], "audio": info["audio"]}}]
    executar("app.project.save()")
    _gravar(trabalho, dados)
    return {"video": [(a["trilha"], [(i["nome"], int(i["inicio"]) // tb, int(i["fim"]) // tb) for i in a["itens"]]) for a in info["video"] if a["itens"]],
            "audio": [(a["trilha"], [(i["nome"], int(i["inicio"]) // tb, int(i["fim"]) // tb) for i in a["itens"]]) for a in info["audio"] if a["itens"]]}


GUIDS_MAPA_AUDIO = {"0551e2a0-6da1-4691-800e-b3ded5ca94f7": "Use File", "b7f34681-bada-438d-83d6-7f12236011ba": "Mono"}
CHAVES_PREFERENCIAS = ("BE.Prefs.DefaultChannelMapID_95_Mono", "BE.Prefs.DefaultChannelMapID_95_Stereo",
                       "BE.Prefs.DefaultChannelMapID_95_51", "BE.Prefs.DefaultChannelMapID_95_MultiMono",
                       "BE.Prefs.General.DefaultScaleToFrameSize", "BE.Prefs.General.DefaultSetToFrameSize",
                       "BE.Prefs.StillImages.ScaleToProject")


def preferencias(versao: str) -> dict:
    """As preferências que mudam o resultado (Default Audio Tracks, Default Media Scaling), lidas do arquivo do
    perfil ANTES de medir. Duas rodadas já foram contaminadas por preferência da máquina (2026-10-06: áudio em
    Mono no 25.6.5; "Set to Frame Size" no 26.0.2): a medição vale junto com isto."""
    import glob
    maior = versao.split(".")[0] + ".0"
    docs = os.path.expanduser("~/Documents") if os.name != "nt" else os.path.join(os.environ.get("USERPROFILE", ""), "Documents")
    # o Beta tem pasta e arquivo próprios: "Premiere Pro (Beta)/27.0/Profile-*/Adobe Premiere Pro (Beta) Prefs" (27.1, 2026-10-07)
    arqs = glob.glob(os.path.join(docs, "Adobe", "Premiere Pro", maior, "Profile-*", "Adobe Premiere Pro Prefs")) + \
        glob.glob(os.path.join(docs, "Adobe", "Premiere Pro (Beta)", maior, "Profile-*", "Adobe Premiere Pro (Beta) Prefs"))
    if not arqs:
        return {"erro": f"preferências da {maior} não achadas em {docs}/Adobe"}
    arqs.sort(key=os.path.getmtime, reverse=True)      # as duas existindo (estável e Beta da mesma versão): a mais recente
    with open(arqs[0], "rb") as fh:
        texto = fh.read().decode("utf-8", "replace")
    out = {"arquivo": arqs[0]}
    for k in CHAVES_PREFERENCIAS:
        m = re.search(r"<%s>([^<]*)<" % re.escape(k), texto)
        v = m.group(1) if m else None
        out[k] = GUIDS_MAPA_AUDIO.get(v, v)
    return out
