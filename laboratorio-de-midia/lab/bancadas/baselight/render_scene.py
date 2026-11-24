"""(cópia do `estudo/ferramentas/render_scene.py` com RENDER_FAIXAS, BL08, 2026-11-22.) Renderiza uma scene inteira em ProRes 422 HQ, no espaço de cor de ENTRADA do 1º plano (a imagem sai ~ igual ao
original, para a conferência do laboratório ler as barras). Uso: render_scene.py <host:job:scene> <pasta_saida> [video LUT: scale (padrão) | none …]
⭐ 2026-11-21: sem o Video LUT "scale" (Full to Legal) o ProRes sai com valores de faixa CHEIA marcados como legais
(patamares esticados: 1,07 / −0,10); com ele o render = o still."""
import sys, time, flapi
cena, pasta = sys.argv[1], sys.argv[2]
c = flapi.Connection("localhost"); c.connect()
s = c.Scene.open_scene(c.Scene.parse_path(cena), {flapi.OPENFLAG_READ_ONLY})
ids = s.get_shot_ids()
import os
cs = os.environ.get("RENDER_CS")       # BRAW (PRODUCAO-A) entra em BMD_Linear_WG: a saída tem de ser um espaço de VÍDEO
for p_ in ([] if cs else ids):          # senão, o espaço de entrada do 1º plano com fonte (o 1º pode ser um preto de 1 quadro)
    try:
        sh = s.get_shot(p_.ShotId); cs = sh.get_actual_input_colour_space(); sh.release(); break
    except flapi.FLAPIException:
        continue
rs = c.RenderSetup.create_from_scene(s)
d = rs.get_deliverable(0)
d.Name = "LAB"; d.Disabled = 0; d.IsMovie = 1; d.FileType = "lqtmov"; d.MovieCodec = "apch"
d.FileNameExtension = ".mov"; d.OutputDirectory = pasta; d.RenderColourSpace = cs
d.RenderVideoLUT = sys.argv[3] if len(sys.argv) > 3 else "scale"
rs.set_deliverable(0, d)
if os.environ.get("RENDER_FAIXAS"):     # (BL08) vários trechos "a,b;c,d" em quadros da scene — pula os planos OFFLINE,
    faixas = []                          # que derrubam o render inteiro ("Missing file /images1/…")
    for par in os.environ["RENDER_FAIXAS"].split(";"):
        a_, b_ = (int(x) for x in par.split(","))
        fr = flapi.FrameRange(); fr.Start, fr.End = a_, b_; faixas.append(fr)
    rs.set_frames(faixas)
elif os.environ.get("RENDER_FAIXA"):      # (estudo) só um trecho: "início,fim" em quadros da scene
    a_, b_ = (int(x) for x in os.environ["RENDER_FAIXA"].split(","))
    fr = flapi.FrameRange(); fr.Start, fr.End = a_, b_
    rs.set_frames([fr])
else:
    rs.select_all()
qm = c.QueueManager.create_local()
op = rs.submit_to_queue(qm, "LAB " + cena)
print("op", op.ID, "cor", cs, "aviso", op.Warning, "saida", rs.get_output_filename_for_deliverable(0))
rs.release(); s.close_scene()
t0 = time.time()
while True:
    st = qm.get_operation_status(op.ID)
    if st.Status in ("Done", "Failed", "Error") or time.time() - t0 > float(os.environ.get("PRAZO_RENDER", "900")):
        print("status", st.Status, st.ProgressText); break
    time.sleep(2)
log = qm.get_operation_log(op.ID)
for item in [i for i in log if i.Type != "info"][:6] + log[-2:]:
    print("log", item.Type, item.Frame, item.Message, (item.Detail or "")[:200])
qm.archive_operation(op.ID)
