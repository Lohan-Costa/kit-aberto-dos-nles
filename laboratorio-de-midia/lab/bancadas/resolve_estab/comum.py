import sys, os
APP = "/Volumes/SSD/PROGRAMAS COM CLAUDE/2 ATIVOS/_DeLaPraCa"
sys.path[:0] = [APP + "/motor", APP + "/plugins/media-composer/servico"]
LAB = "/Volumes/SSD/PROGRAMAS COM CLAUDE/laboratorio-de-midia"
TREM = LAB + "/saida/base/B19_ESTABILIZADOR/B19_TREMIDO.mov"
REND = LAB + "/saida/bancadas/avid/estab_mc/B19_MC_ESTAB_100.mxf"
AQUI = os.path.dirname(os.path.abspath(__file__))
def resolve():
    import resolve_externo as R
    r = R.conectar()
    return r[0] if isinstance(r, tuple) else r
