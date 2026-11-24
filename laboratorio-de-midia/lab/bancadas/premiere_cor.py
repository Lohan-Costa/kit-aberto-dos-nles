"""B09 COR — o que cada versão do Premiere grava e desenha de COR, e o que sobrevive ao DOWNGRADE. Escolhas do autor
(2026-10-07): câmera log/RAW, Lumetri e LUTs, e os efeitos de cor novos do 27.

    python3 -m lab.bancadas.premiere_cor montar                 # no Premiere aberto → saida/bancadas/premiere-<v>/B09_COR
    python3 -m lab.bancadas.premiere_cor downgrade <de> <para>
    python3 -m lab.bancadas.premiere_cor comparar <trab> <trab>

O projeto: o Sony S-Log3 (ProRes 4444 4K da coleta) sobrescrito para "Sony S-Log3/S-Gamut3.Cine"; o mesmo numa
sequência em ACEScct; o ARRIRAW HDE (.arx); o clipe do laboratório com Lumetri em valores conhecidos; a câmera do B06
com LUT de entrada (.cube gerada aqui). Só no 27 (o que o 26/25 não têm): um clipe sobrescrito para "Apple Log/Wide
Gamut" e os efeitos de cor novos — o teste do que acontece com eles no downgrade.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time

from . import premiere as p
from . import premiere_projeto as pp
from .premiere_cor_explora import ARRI, SONY, _INFO

RAIZ = pp.RAIZ
CASO = "B09_COR"
NOME = "LAB B09 COR"
MOV = pp.MOV
CAM = pp.CAM
HD27 = os.path.join(RAIZ, "saida", "base", "B05_RASTERS", "B05_HD_MOV-PRORES.mov")
# (sequência, quadro): no meio de cada uma
QUADROS = {"SEQ SONY": 120, "SEQ SONY ACES": 120, "SEQ ARRI": 120, "SEQ LUMETRI": 120, "SEQ LUT": 120,
           "SEQ APPLE LOG": 120, "SEQ EFEITOS 27": 120}
LUMETRI = ["Lumetri Color", "Cor de Lumetri"]
AJUSTES = {   # o primeiro parâmetro com este nome (o da Correção básica) → valor
    ("Exposure", "Exposição"): 1.0, ("Contrast", "Contraste"): 30.0, ("Saturation", "Saturação"): 150.0,
    ("Temperature", "Temperatura"): 20.0}
EFEITOS_27 = {"lut": ["LUT Transform", "Transformação LUT"], "cor_contraste": ["Color & Contrast", "Cor e contraste"],
              "hsl": ["HSL Key", "Máscara HSL"]}


def cube(caminho: str, n: int = 17) -> None:
    """Uma LUT 3D conhecida: aquece (R ×1,1, B ×0,85) e levanta o preto em 0,03 — o efeito se mede no still."""
    with open(caminho, "w", encoding="ascii", newline="\n") as fh:
        fh.write('TITLE "LAB B09 QUENTE"\nLUT_3D_SIZE %d\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n' % n)
        for b in range(n):
            for g in range(n):
                for r in range(n):
                    R, G, B = (r / (n - 1), g / (n - 1), b / (n - 1))
                    f = lambda x: min(1.0, 0.03 + 0.97 * x)
                    fh.write("%.6f %.6f %.6f\n" % (f(min(1.0, R * 1.1)), f(G), f(B * 0.85)))


def montar(trabalho: str) -> dict:
    v = p.executar("app.version")
    trabalho = os.path.abspath(trabalho)
    p.salvar_e_fechar()
    if os.path.isdir(trabalho):
        os.rename(trabalho, trabalho + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    ins = os.path.join(trabalho, "insumos", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(ins)
    lut = os.path.join(ins, "LAB B09 QUENTE.cube")
    cube(lut)
    projeto = os.path.join(trabalho, NOME + ".prproj")
    passos = []

    def passo(nome, js, timeout=600):
        t0 = time.time()
        try:
            r = p.executar(pp._JS + _INFO + js, timeout=timeout)
            passos.append({"passo": nome, "ok": True, "valor": r, "s": round(time.time() - t0, 1)})
        except Exception as e:  # noqa: BLE001 — o passo que falha (ex.: recurso que a versão não tem) fica registrado
            passos.append({"passo": nome, "ok": False, "erro": str(e), "s": round(time.time() - t0, 1)})
        print(time.strftime("%H:%M:%S"), str(passos[-1])[:300], flush=True)
        return passos[-1]

    novo_27 = v.split(".")[0] >= "27"
    passo("novo projeto", "app.newProject(%s)" % pp._js(projeto))
    arqs = [MOV, CAM, SONY] + ([HD27] if novo_27 else [])
    passo("importar", """(function(){ app.project.importFiles(%s, true, app.project.rootItem, false);
      app.project.importFiles([%s], true, app.project.rootItem, true);
      var it = _lab_itens(app.project.rootItem), o = []; for (var i = 0; i < it.length; i++) o.push(it[i].name); return o; })()"""
          % (pp._js(arqs), pp._js(ARRI[0])), timeout=900)
    _sobrescrever = """(function(){ var c = _lab_midia(%s), l = c.getOverrideColorSpaceList, alvo = null;
      for (var i = 0; i < l.length; i++) if (l[i].name == %s) alvo = l[i];
      if (!alvo) throw new Error("espaço não está na lista desta versão: " + %s);
      var r = c.setOverrideColorSpace(alvo); return [r, _lab_obj(c.getColorSpace()), c.isColorManagedMedia()]; })()"""
    passo("Sony → S-Log3/S-Gamut3.Cine", _sobrescrever % (pp._js(SONY), pp._js("Sony S-Log3/S-Gamut3.Cine"), pp._js("Sony S-Log3/S-Gamut3.Cine")))
    passo("LUT de entrada na câmera B06", """(function(){ var c = _lab_midia(%s), f = c.getFootageInterpretation();
      var r = f.setInputLUTFromFilePath(%s); c.setFootageInterpretation(f);
      return [r, String(c.getFootageInterpretation().inputLUTID), c.getInputLUTID()]; })()""" % (pp._js(CAM), pp._js(lut)))
    if novo_27:
        passo("HD → Apple Log/Wide Gamut (só no 27)", _sobrescrever % (pp._js(HD27), pp._js("Apple Log/Wide Gamut"), pp._js("Apple Log/Wide Gamut")))
    seqs = [("SEQ SONY", SONY), ("SEQ SONY ACES", SONY), ("SEQ ARRI", None), ("SEQ LUMETRI", MOV), ("SEQ LUT", CAM)]
    if novo_27:
        seqs += [("SEQ APPLE LOG", HD27), ("SEQ EFEITOS 27", MOV)]
    for nome, arq in seqs:
        alvo = "_lab_midia(%s)" % pp._js(arq) if arq else """(function(){ var it = _lab_itens(app.project.rootItem);
            for (var i = 0; i < it.length; i++) if (it[i].name.indexOf("F004C009") == 0) return it[i]; return null; })()"""
        passo("sequência " + nome, """(function(){ var c = %s;
          var s = app.project.createNewSequenceFromClips(%s, [c], app.project.rootItem); s.name = %s;
          return [s.name, _lab_obj(s.getSettings().workingColorSpace).name]; })()""" % (alvo, pp._js(nome), pp._js(nome)))
    passo("SEQ SONY ACES em ACEScct", """(function(){ var s = _lab_seq("SEQ SONY ACES"), st = s.getSettings(), l = st.workingColorSpaceList, a = null;
      for (var i = 0; i < l.length; i++) if (l[i].name == "ACEScct") a = l[i];
      st.workingColorSpace = a; s.setSettings(st); return _lab_obj(s.getSettings().workingColorSpace).name; })()""")
    passo("Lumetri", """(function(){ var s = _lab_seq("SEQ LUMETRI"); app.project.openSequence(s.sequenceID); app.enableQE();
      var ti = s.videoTracks[0].clips[0], antes = _lab_matches(ti), fx = _lab_fx(%s);
      qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0).addVideoEffect(fx); var c = _lab_novo(ti, antes);
      var aj = %s, feito = [];
      for (var k = 0; k < aj.length; k++) { for (var i = 0; i < c.properties.numItems; i++) {
          var n = c.properties[i].displayName; if (n == aj[k][0] || n == aj[k][1]) { c.properties[i].setValue(aj[k][2], true); feito.push([i, n, c.properties[i].getValue()]); break; } } }
      return {efeito: fx.name, match: c.matchName, ajustes: feito}; })()""" % (pp._js(LUMETRI), pp._js([[a, b, val] for (a, b), val in AJUSTES.items()])))
    if novo_27:
        for chave, nomes in EFEITOS_27.items():
            passo("efeito novo do 27: " + chave, """(function(){ var s = _lab_seq("SEQ EFEITOS 27"); app.project.openSequence(s.sequenceID); app.enableQE();
              var ti = s.videoTracks[0].clips[0], antes = _lab_matches(ti), fx = _lab_fx(%s);
              qe.project.getActiveSequence().getVideoTrackAt(0).getItemAt(0).addVideoEffect(fx); var c = _lab_novo(ti, antes), ps = [];
              for (var i = 0; i < c.properties.numItems && i < 12; i++) ps.push(c.properties[i].displayName);
              return [fx.name, c.matchName, ps]; })()""" % pp._js(nomes))
    passo("salvar", "app.project.save()")
    with open(os.path.join(trabalho, "montagem.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"versao": v, "projeto": projeto, "lut": lut, "passos": passos}, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    return {"projeto": projeto, "falharam": [x["passo"] for x in passos if not x["ok"]]}


_COR = pp._JS + _INFO + r"""(function(){ var it = _lab_itens(app.project.rootItem), o = {clipes: [], sequencias: []};
  for (var i = 0; i < it.length; i++) if (it[i].getMediaPath()) o.clipes.push(_lab_cor(it[i]));
  for (var i = 0; i < app.project.sequences.numSequences; i++) { var s = app.project.sequences[i], st = s.getSettings();
    o.sequencias.push({nome: s.name, trabalho: _lab_obj(st.workingColorSpace), tone_map: st.autoToneMapEnabled,
      gamut: st.autoInputGamutCompressionEnabled, linear: st.compositeLinearColor, largura: st.videoFrameWidth, altura: st.videoFrameHeight}); }
  return o; })()"""


def retrato(trab: str) -> dict:
    r = pp.retrato()
    cor = p.executar(_COR, timeout=300)
    for c in cor["clipes"]:
        c.pop("overrideList", None)       # a lista é da VERSÃO (exploracao-*.json), não do projeto
        c.pop("md", None)
    r["cor"] = cor
    pasta = os.path.join(os.path.abspath(trab), "stills")
    os.makedirs(pasta, exist_ok=True)
    feitos = {}
    for s in [x["nome"] for x in r["sequencias"]]:
        q = QUADROS.get(s)
        if q is None:
            continue
        arq = os.path.join(pasta, s.replace(" ", "_") + f"_{q:04d}")
        with open(os.path.join(pasta, "exportando.txt"), "w", encoding="utf-8") as fh:   # se o Premiere cair, diz onde
            fh.write(s)
        # duas vezes: o RAW (ARRIRAW) ainda decodificando sai como "Media pending" no 1º (25.6.5, 2026-10-07)
        for vez, destino in enumerate((arq + "_aquecer", arq)):
            p.executar(pp._JS + """(function(){ var s = _lab_seq(%s); app.project.openSequence(s.sequenceID); app.enableQE();
              s.setPlayerPosition(%s); var qs = qe.project.getActiveSequence(); return qs.exportFramePNG(qs.CTI.timecode, %s); })()"""
                       % (pp._js(s), pp._js(str(q * p.TICKS // 24)), pp._js(destino)))
            limite = time.time() + 20
            while not os.path.exists(destino + ".png") and time.time() < limite:
                time.sleep(0.3)
            time.sleep(3.0 if vez == 0 else 1.0)
        if os.path.exists(arq + "_aquecer.png"):
            os.remove(arq + "_aquecer.png")
        feitos[s] = os.path.exists(arq + ".png")
    r["stills"] = feitos
    return r


def _gravar(trab: str, ret: dict) -> None:
    with open(os.path.join(trab, "retrato.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ret, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def comparar(trab_a: str, trab_b: str) -> dict:
    with open(os.path.join(trab_a, "retrato.json"), encoding="utf-8") as fa, open(os.path.join(trab_b, "retrato.json"), encoding="utf-8") as fb:
        ra, rb = json.load(fa), json.load(fb)

    def cor(r):
        return {"clipes": {c["nome"]: {k: c.get(k) for k in ("getColorSpace", "getOriginalColorSpace", "getOverrideColorSpace",
                                                              "isColorManagedMedia", "getInputLUTID", "interp")} for c in r["cor"]["clipes"]},
                "sequencias": {s["nome"]: s for s in r["cor"]["sequencias"]}}
    psnr = {}
    for s, ok in ra.get("stills", {}).items():
        a = os.path.join(trab_a, "stills", s.replace(" ", "_") + f"_{QUADROS[s]:04d}.png")
        b = os.path.join(trab_b, "stills", s.replace(" ", "_") + f"_{QUADROS[s]:04d}.png")
        psnr[s] = pp.psnr(a, b) if os.path.exists(a) and os.path.exists(b) else "falta"
    return {"versoes": [ra["versao"], rb["versao"]], "diferencas": pp.diferencas(pp.normalizar(ra), pp.normalizar(rb)),
            "cor": pp.diferencas(cor(ra), cor(rb)), "psnr_db": psnr}


def downgrade(de: str, para: str) -> dict:
    from .. import prproj_downgrade
    v = p.executar("app.version")
    if v != para:
        raise SystemExit(f"a ponte respondeu do Premiere {v}, não do {para}")
    trab = os.path.join(RAIZ, "saida", "bancadas", f"downgrade-{de}-para-{para}", CASO)
    p.salvar_e_fechar()
    if os.path.isdir(trab):
        os.rename(trab, trab + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(trab)
    alvo = os.path.join(trab, NOME + ".prproj")
    r = prproj_downgrade.rebaixar(os.path.join(RAIZ, "resultados", CASO, "prproj", f"premiere-{de}-darwin.prproj"), alvo, para)
    shutil.copyfile(alvo, os.path.join(trab, "rebaixado-antes-de-abrir.prproj"))
    p.executar("app.openDocument(%s, true, true, true)" % pp._js(alvo), timeout=300)
    abriu = p.executar("(function(){ try { return app.project.path; } catch (e) { return ''; } })()") == alvo
    out = {"de": de, "para": para, "rebaixar": r, "abriu": abriu}
    if abriu:
        _gravar(trab, retrato(trab))
        p.salvar_e_fechar()
        out["contra_a_origem"] = comparar(os.path.join(RAIZ, "saida", "bancadas", f"premiere-{de}", CASO), trab)
        out["contra_o_destino_nativo"] = comparar(os.path.join(RAIZ, "saida", "bancadas", f"premiere-{para}", CASO), trab)
    with open(os.path.join(RAIZ, "resultados", CASO, f"downgrade-{de}-para-{para}-darwin.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    return out


def volta(via: str) -> dict:
    """IDA E VOLTA: o B09 do 27 rebaixado, aberto e SALVO pela versão `via`, aberto de novo no 27 (o que está aberto).
    O 26/25 guardam no arquivo os efeitos e o espaço de cor que não conhecem — eles voltam?"""
    v = p.executar("app.version")
    trab = os.path.join(RAIZ, "saida", "bancadas", f"volta-27-via-{via}", CASO)
    p.salvar_e_fechar()
    if os.path.isdir(trab):
        os.rename(trab, trab + "-anterior-" + time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(trab)
    alvo = os.path.join(trab, NOME + ".prproj")
    shutil.copyfile(os.path.join(RAIZ, "saida", "bancadas", f"downgrade-27.1.0-para-{via}", CASO, NOME + ".prproj"), alvo)
    p.executar("app.openDocument(%s, true, true, true)" % pp._js(alvo), timeout=300)
    _gravar(trab, retrato(trab))
    p.salvar_e_fechar()
    out = {"versao": v, "via": via, "contra_a_origem_27": comparar(os.path.join(RAIZ, "saida", "bancadas", "premiere-27.1.0", CASO), trab)}
    with open(os.path.join(RAIZ, "resultados", CASO, f"volta-27-via-{via}-darwin.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=str)
        fh.write("\n")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    os.chdir(RAIZ)
    if argv[0] == "montar":
        v = p.executar("app.version")
        trab = os.path.join(RAIZ, "saida", "bancadas", f"premiere-{v}", CASO)
        r = montar(trab)
        print(r)
        p.salvar_e_fechar()
        p.executar("app.openDocument(%s, true, true, true)" % pp._js(r["projeto"]), timeout=300)
        ret = retrato(trab)
        _gravar(trab, ret)
        p.salvar_e_fechar()
        destino = os.path.join(RAIZ, "resultados", CASO, "prproj", f"premiere-{v}-darwin.prproj")
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.copyfile(r["projeto"], destino)
        from .. import prproj_estrutura
        imp = prproj_estrutura.impressao(destino)
        imp["arquivo"] = os.path.basename(destino)
        with open(destino.replace(".prproj", ".estrutura.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(imp, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print("stills", ret["stills"])
        return 0
    if argv[0] == "downgrade":
        r = downgrade(argv[1], argv[2])
        print({k: r[k] for k in ("de", "para", "abriu")})
        for k in ("contra_a_origem", "contra_o_destino_nativo"):
            if k in r:
                print(k, "psnr", r[k]["psnr_db"], "| cor:", r[k]["cor"][:6], "| projeto:", r[k]["diferencas"][:6])
        return 0
    if argv[0] == "comparar":
        print(json.dumps(comparar(argv[1], argv[2]), ensure_ascii=False, indent=1, default=str))
        return 0
    if argv[0] == "volta":
        r = volta(argv[1])["contra_a_origem_27"]
        print("psnr", r["psnr_db"], "| cor:", r["cor"][:6], "| projeto:", r["diferencas"][:6])
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
