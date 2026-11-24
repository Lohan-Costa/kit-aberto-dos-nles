# ⚠️ REGISTRO HISTÓRICO — script de UMA rodada, na máquina do autor: os caminhos abaixo são os do SSD de trabalho
# dele e não existem noutra máquina. O que se mediu está registrado no banco (bancodedadosnles). Para repetir,
# peça ao Claude para adaptar: achar o laboratório SUBINDO de pasta e gerar a mídia por uma receita
# (skill ciclo-laboratorio) — nunca com o material de uma produção.
"""Bancada da COR do Media Composer (B24_COR_MC, 2026-11-20): a conta de cada controle do Color Correction.

Sem clicar no Effect Editor: a sequência é ESCRITA na bin (pyavb), um segmento da carta por valor de controle, cada um
com um Color Correction LIMPO — o efeito copiado de um CC real (a PRODA_CORTE.00.2) com o `param_list` trocado por:
versão do AVX2 + Relationship Type + Modification Date (o que o CC real sempre tem) + UM parâmetro (o nome do pyavb,
`avb.parameter_uuids`: "Mas Sat", "Mas Gain"…). O MC renderiza no export (`ExportFile`, preset do lab em 1920×1080 com a
compressão da fonte) e a medição compara cada segmento com o segmento sem efeito.

    py -m lab.bancadas.avid_cor montar <nome> <casos.json>   (MC aberto no projeto LAB COR MC)
    py -m lab.bancadas.avid_cor exportar <nome>
Rodar com o Python do Ciclo Assist (pyavb + gRPC).
"""
from __future__ import annotations

import copy
import json
import os
import sys
import time
import uuid as _uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSIST = os.path.join(os.path.dirname(RAIZ), "2 ATIVOS", "_CICLO ASSIST")
if ASSIST not in sys.path:
    sys.path.insert(0, ASSIST)

from cicloassist.avid.mcapi import MediaComposer  # noqa: E402

PROJETO = r"D:\MIDIAS DE TESTES\1 PRODUCOES\PRODUCAO-A\PROJETO\LAB COR MC"
BIN = os.path.join(PROJETO, "LAB COR MC Bin.avb")
BIN_REL = "LAB COR MC Bin.avb"
MASTER = "B24_CARTA_COR"
#: o CC real de onde sai o MOLDE do efeito (a 2ª ocorrência na PRODA: Mas Sat 87,5 + curva Master)
MOLDE_BIN = r"D:\MIDIAS DE TESTES\1 PRODUCOES\PRODUCAO-A\PROJETO\PRODUCAO-A\_TRABALHO\01_EDIT\03_OC_EDIT VALENDO.avb"
MOLDE_SEQ = "PRODA_CORTE.00.2"
#: o que o CC real sempre leva (fica no molde); o resto sai
FICA = {"MC AVX2 EFFECT VERSION", "Relationship Type", "Modification Date",
        # ⛔⛔ MEDIDO (2026-11-20, MC 24.6): sem as TRÊS bandeiras do HSL (valor 1, enable falso, como o CC real grava)
        # o MC IGNORA o efeito inteiro — o Sat 0 sai idêntico ao original. Tirar qualquer uma delas basta.
        "HSL Bypass", "HSL Setup Bypass", "HSL Setup Master Bypass"}
QUADROS = 12            # por segmento
ENTRADA = 24            # o quadro da carta onde cada segmento começa
SAIDA = os.path.join(RAIZ, "saida", "bancadas", "avid_cor")
PRESET = "LAB_COR_1080"
PRESET_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avid", "presets", "DLPC_LAB_DNXLB.xml")


def _molde(f_lab, inteiro: bool = False):
    """O TrackEffect de CC copiado para o arquivo da bin do lab."""
    import avb
    from avb.parameter_uuids import PARAMETER_UUIDS as P
    sys.path.insert(0, os.path.join(ASSIST, "modulos", "conformar", "motor"))
    from cicloassist.carta import timeline as T
    S = T._conformar()
    seg = sys.modules[[k for k in sys.modules if k.endswith("avb_bin.segmentos")][0]]
    achados, orig = [], seg.informativo

    def espia(c):
        if str(getattr(c, "effect_id", "")) == "EFF2_RGB_COLOR_CORRECTION":
            achados.append(c)
        return orig(c)
    seg.informativo = espia
    try:
        with avb.open(MOLDE_BIN) as f:
            seq = next(m for m in f.content.mobs if m.name == MOLDE_SEQ)
            S.ler_timeline(f, seq)
            te = achados[1].copy(f_lab)
    finally:
        seg.informativo = orig
    for p in [p for p in te.param_list if not inteiro and P.get(str(p.uuid)) not in FICA]:
        te.param_list.remove(p)          # ⛔ é um AVBRefList: trocar por list() quebra a escrita
    return te


def _item(f, nome: str, valor):
    from avb.parameter_uuids import PARAMETER_UUIDS as P
    por_nome = {n: u for u, n in P.items()}
    it = f.create.ParameterItem()
    it.uuid = _uuid.UUID(por_nome[nome])
    if isinstance(valor, bool) or (isinstance(valor, int) and nome.startswith(("Invert", "HSL"))):
        it.value_type, it.value = 1, int(valor)
    else:
        it.value_type, it.value = 2, (int(valor) if float(valor).is_integer() else float(valor))
    it.name, it.enable, it.control_track, it.contribs_to_sig = "", True, None, True
    return it


#: a escala da curva no blob (medida na PRODA: a curva neutra vai de (256, 256) a (766, 766))
CURVA_0, CURVA_1 = 256.0, 766.0


def _curva(te, pontos) -> None:
    """Troca a curva Master do molde (blob `CFUserParam` de 16 pares (x, y) em double LE) pelos `pontos`, dados de 0 a 1
    na escala da curva, e o `Num Master Curve Keys`."""
    import struct
    from avb.parameter_uuids import PARAMETER_UUIDS as P
    por = {P.get(str(p.uuid)): p for p in te.param_list}
    xs = []
    for x, y in pontos:
        xs += [CURVA_0 + (CURVA_1 - CURVA_0) * x, CURVA_0 + (CURVA_1 - CURVA_0) * y]
    xs += [0.0] * (32 - len(xs))
    blob = por["Curves Master"].value
    blob.data = bytearray(struct.pack("<32d", *xs))
    por["Num Master Curve Keys"].value = len(pontos)


def montar(nome: str, casos: list[dict]) -> str:
    """A sequência `nome`: um segmento da carta por caso ({} = sem efeito; {"Mas Sat": 50} = CC com Sat 50)."""
    import avb
    from cicloassist.avid import timeline as T
    from cicloassist.avid.atributos import copiar_atributos
    with MediaComposer() as m:
        try:
            m._chamar("CloseBin", _timeout=60, bin_path=BIN_REL)
        except Exception:                                   # noqa: BLE001 — já fechada
            pass
        with avb.open(BIN) as f:
            mm = next(x for x in f.content.mobs if x.mob_type == "MasterMob" and x.name == MASTER)
            taxa, mob = mm.edit_rate, str(mm.mob_id)
        entradas = [T.Entrada(mob_id=mob, duracao=QUADROS, trilhas=(("picture", 1),), start_time=ENTRADA)
                    for _ in casos]
        T.acrescentar_timeline(BIN, nome, entradas, taxa)
        novo = BIN + ".novo"
        with avb.open(BIN) as f:
            seq = [x for x in f.content.mobs if x.name == nome and x.mob_type == "CompositionMob"][-1]
            tr = next(t for t in seq.tracks if t.media_kind == "picture")
            comps = list(tr.component.components)
            clipes = [i for i, c in enumerate(comps) if type(c).__name__ == "SourceClip"]
            assert len(clipes) == len(casos), (len(clipes), len(casos))
            for i, caso in zip(clipes, casos):
                if not caso:
                    continue
                sc = comps[i]
                caso = dict(caso)
                te = _molde(f, inteiro=bool(caso.pop("_molde_inteiro", False)))
                from avb.parameter_uuids import PARAMETER_UUIDS as P
                curvas = caso.pop("_curva", None)
                for tirar in caso.pop("_tirar", []):
                    for p in [p for p in te.param_list if P.get(str(p.uuid)) == tirar]:
                        te.param_list.remove(p)
                if curvas is not None:
                    _curva(te, curvas)
                for k, v in caso.items():
                    velho = next((p for p in te.param_list if P.get(str(p.uuid)) == k), None)
                    if velho is not None:
                        te.param_list.remove(velho)
                    te.param_list.append(_item(f, k, v))
                te.length = sc.length
                te.left_bob, te.precomputed = None, None
                dentro = f.create.Sequence(sc.edit_rate, "picture")
                dentro.components = [sc]
                te.tracks[0].component = dentro
                comps[i] = te
            tr.component.components = comps
            urn = str(seq.mob_id)
            f.write(novo)
        copiar_atributos(BIN, novo)
        os.replace(novo, BIN)
        m._chamar("OpenBin", _timeout=60, bin_path=BIN_REL)
        # ⛔ pelo MobID do que foi escrito, nunca pelo NOME: uma sobra de tentativa com o mesmo nome vinha antes
        from cicloassist.avid.mcapi import mob_id_da_api
        alvo = mob_id_da_api(urn)
        fim = time.time() + 60
        while time.time() < fim:
            if any(it.mob_id == alvo for it in m.itens_da_bin(BIN_REL, tipos=("sequences",))):
                return alvo
            time.sleep(2)
    raise RuntimeError(f"a sequência {nome!r} ({alvo}) não apareceu na bin")


def _preset_xml() -> str:
    with open(PRESET_BASE, encoding="utf-8") as f:
        xml = f.read()
    xml = xml.replace(">DLPC_LAB_DNXLB<", f">{PRESET}<", 1)
    xml = xml.replace('name="iDestWidth" type="int16">1280<', 'name="iDestWidth" type="int16">1920<')
    xml = xml.replace('name="iDestHeight" type="int16">720<', 'name="iDestHeight" type="int16">1080<')
    return xml


def exportar(mob_id: str, nome: str, prazo: float = 600) -> str:
    import glob
    sys.path.insert(0, os.path.join(os.path.dirname(RAIZ), "piloto"))
    from piloto import olhos
    os.makedirs(SAIDA, exist_ok=True)
    for velho in glob.glob(os.path.join(SAIDA, nome + ".*")):
        os.remove(velho)
    with MediaComposer() as m:
        m._chamar("LoadSetting", _timeout=60, unique_id=PRESET, xml_setting=_preset_xml())
        m._chamar("ExportFile", _timeout=60, mob_id=mob_id, file_name=nome, export_settings_name=PRESET,
                  destination_path=SAIDA)
    inicio, ultimo, iguais = time.time(), None, 0
    while time.time() - inicio < prazo:
        agora = [(f, os.path.getsize(f)) for f in sorted(glob.glob(os.path.join(SAIDA, nome + ".*")))]
        progresso = any(j["titulo"] == "AvidMediaComposer" for j in olhos.janelas("AvidMediaComposer.exe"))
        iguais = iguais + 1 if agora and agora == ultimo and not progresso else 0
        ultimo = agora
        if agora and iguais >= 3:
            return agora[0][0]
        time.sleep(2)
    raise TimeoutError(f"o export de {nome!r} não terminou em {prazo:.0f} s")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    acao, nome = sys.argv[1], sys.argv[2]
    if acao == "montar":
        with open(sys.argv[3], encoding="utf-8") as f:
            print(montar(nome, json.load(f)))
    elif acao == "exportar":
        print(exportar(sys.argv[3], nome))
