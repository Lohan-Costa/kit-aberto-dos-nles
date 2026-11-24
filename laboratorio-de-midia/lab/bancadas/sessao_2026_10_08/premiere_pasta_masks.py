"""Como o Premiere 26 ACHA a pasta `<projeto> Masks` (máscara de objeto, .prmf): pelo nome do ARQUIVO do projeto?
Quatro cópias do projeto de rotoscopia do autor (B10) — controle, projeto renomeado com a pasta antiga, projeto e pasta
renomeados juntos, sem a pasta — abertas uma a uma pela ponte; o mesmo quadro exportado em cada uma e comparado ao controle.

    python3 -m lab.bancadas.sessao_2026_10_08.premiere_pasta_masks
"""
import json
import os
import shutil
import time

from lab.bancadas import premiere as pr

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ORIG = os.path.join(RAIZ, "resultados", "B10_ROTO", "premiere-26.0.2-autor")
NOME = "rotoscopia_teste_premiere26"
TRAB = os.path.join(RAIZ, "saida", "bancadas", "premiere", "pasta_masks")
CASOS = {  # caso: (nome do .prproj, nome da pasta Masks ou None)
    "A_controle": (NOME, NOME + " Masks"),
    "B_projeto_renomeado": ("renomeado", NOME + " Masks"),
    "C_projeto_e_pasta_renomeados": ("renomeado", "renomeado Masks"),
    "D_sem_pasta": (NOME, None),
}
SEGUNDOS = (3, 6, 9)


def preparar() -> dict:
    caminhos = {}
    for caso, (proj, pasta) in CASOS.items():
        d = os.path.join(TRAB, caso)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        shutil.copy2(os.path.join(ORIG, NOME + ".prproj"), os.path.join(d, proj + ".prproj"))
        if pasta:
            shutil.copytree(os.path.join(ORIG, NOME + " Masks"), os.path.join(d, pasta),
                            ignore=shutil.ignore_patterns("._*"))
        caminhos[caso] = os.path.join(d, proj + ".prproj")
    return caminhos


def quadros(projeto: str, saida: str) -> dict:
    os.makedirs(saida, exist_ok=True)
    js = """(function(){
      var ok = app.openDocument(%s, true, true, true, true);
      if (!ok) return {aberto:false};
      var s = app.project.sequences[0]; app.project.openSequence(s.sequenceID); s = app.project.activeSequence;
      app.enableQE(); var q = qe.project.getActiveSequence(); var feitos = [];
      var segs = %s;
      for (var i = 0; i < segs.length; i++) {
        s.setPlayerPosition(String(segs[i] * 254016000000));
        var arq = %s + "/q" + segs[i]; q.exportFramePNG(q.CTI.timecode, arq); feitos.push(arq);
      }
      return {aberto:true, seq:s.name, feitos:feitos};
    })()""" % (json.dumps(projeto), json.dumps(list(SEGUNDOS)), json.dumps(saida))
    r = pr.executar(js)
    for a in r.get("feitos", []):
        limite = time.time() + 15
        while not os.path.exists(a + ".png") and time.time() < limite:
            time.sleep(0.3)
    time.sleep(1)
    pr.executar("app.project.closeDocument(false, false)")
    return r


def main():
    caminhos = preparar()
    if not pr._premiere_vivo():
        if os.path.exists(pr.ARQ_PONTE):
            os.replace(pr.ARQ_PONTE, pr.ARQ_PONTE + ".anterior")
        pr.abrir_premiere("2026")
    pr.esperar_ponte(300)
    res = {}
    for caso, prj in caminhos.items():
        res[caso] = quadros(prj, os.path.join(TRAB, caso, "quadros"))
        print(caso, res[caso], flush=True)
    with open(os.path.join(TRAB, "resultado.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
