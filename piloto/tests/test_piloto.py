"""Testes do piloto que NÃO operam a máquina (nenhum clique, nenhuma tecla): catálogos, reconhecimento por foto,
freio, achar a família. Rodar: `py -m pytest tests` (Windows) · `.venv/bin/python -m pytest tests` (Mac), no piloto."""
from __future__ import annotations

import json
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from piloto import apps, pontes  # noqa: E402

WINDOWS = sys.platform == "win32"


def test_cada_app_tem_catalogo_valido():
    for chave in apps.APPS:
        pasta = apps.catalogo(chave)
        itens = json.load(open(os.path.join(pasta, "catalogo.json"), encoding="utf-8"))
        for it in itens:
            assert {"nome", "foto"} <= set(it), it
            assert os.path.isfile(os.path.join(pasta, it["foto"])), it["foto"]
            # cada entrada diz o que fazer: clicar, tecla ou só esperar
            assert "clique" in it or "tecla" in it or it.get("esperar"), it["nome"]


def test_reconhece_cada_foto_do_catalogo_e_em_outra_escala(tmp_path):
    from PIL import Image
    from piloto import vigia
    cat = vigia.carregar_catalogo(apps.catalogo("avid"))
    for it in cat:
        assert vigia.reconhecer(it["_foto"], cat)["nome"] == it["nome"]
        # a mesma janela a 80 % (o monitor com outra escala do Windows)
        im = Image.open(it["_foto"])
        menor = tmp_path / ("p_" + it["foto"])
        im.resize((int(im.width * 0.8), int(im.height * 0.8))).save(menor)
        achado = vigia.reconhecer(str(menor), cat)
        assert achado is not None and achado["nome"] == it["nome"], it["nome"]
        assert abs(achado["_escala"][0] - 0.8) < 0.01


def test_foto_desconhecida_nao_e_reconhecida(tmp_path):
    from PIL import Image
    from piloto import vigia
    cat = vigia.carregar_catalogo(apps.catalogo("avid"))
    estranha = tmp_path / "estranha.png"
    Image.new("RGB", (400, 200), (200, 30, 30)).save(estranha)
    assert vigia.reconhecer(str(estranha), cat) is None


def test_freio_pelo_arquivo(tmp_path):
    from piloto import maos
    parar = tmp_path / "PARAR"
    maos.registrar_freio(str(parar))
    maos.checar_freio()                                       # sem o arquivo: segue
    parar.write_text("")
    with pytest.raises(maos.Parado):
        maos.checar_freio()
    # Parado NÃO é Exception: um `except Exception` de laço não o engole
    assert not issubclass(maos.Parado, Exception)
    maos.ARQUIVOS_PARAR.remove(str(parar))


def test_acha_a_familia():
    assert os.path.isdir(os.path.join(pontes.familia(), "bancodedadosnles"))


@pytest.mark.skipif(WINDOWS, reason="teclas do Mac")
def test_teclas_do_mac_por_constante_e_por_letra():
    from piloto import maos
    assert maos.codigo("s") == maos.codigo("S") == 1           # o S do Cmd+S
    assert maos.codigo(maos.ENTER) == 36 and maos.ESC == 53 and maos.F12 == 111
    # os modificadores viram BANDEIRA do evento (o Qt lê a bandeira, não só a tecla)
    assert set(maos._FLAG) == {maos.CMD, maos.SHIFT, maos.ALT, maos.CTRL}


def test_mesmas_funcoes_nos_dois_sistemas():
    """O código de quem usa o piloto não muda de sistema: mãos e olhos do Mac têm os nomes do Windows (lidos do
    código-fonte — o módulo do outro sistema não carrega aqui)."""
    import ast
    pasta = os.path.join(RAIZ, "piloto")

    def nomes(arq):
        arvore = ast.parse(open(os.path.join(pasta, arq), encoding="utf-8").read())
        return {n.name for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_")}
    assert nomes("maos_windows.py") - nomes("maos_macos.py") == set()
    usados_pelo_vigia = {"janelas", "janela_principal", "dialogos", "fotografar", "foto_da_tela", "rodando",
                         "respondendo", "existe", "fechar", "titulo"}
    assert usados_pelo_vigia <= nomes("olhos_windows.py") and usados_pelo_vigia <= nomes("olhos_macos.py")


def test_borda_mostra_o_modo_e_respeita_o_prazo():
    """A borda nunca fica acesa por um piloto morto: `ativo`/`pausado` valem até `ate`; `parado` fica só o tempo de
    ser visto (é a confirmação de que o freio pegou); `livre` não mostra nada."""
    from piloto import borda_comum as B
    t = 1000.0
    assert B.o_que_mostrar({"modo": "ativo", "desde": t, "ate": t + B.TTL_S}, t + 1) == "ativo"
    assert B.o_que_mostrar({"modo": "pausado", "desde": t, "ate": t + B.TTL_S}, t + 1) == "pausado"
    assert B.o_que_mostrar({"modo": "ativo", "desde": t, "ate": t + B.TTL_S}, t + B.TTL_S + 0.1) is None
    assert B.o_que_mostrar({"modo": "parado", "desde": t, "ate": t}, t + 1) == "parado"
    assert B.o_que_mostrar({"modo": "parado", "desde": t, "ate": t}, t + B.PARADO_VISIVEL_S + 0.1) is None
    assert B.o_que_mostrar({"modo": "livre", "desde": t, "ate": t + B.TTL_S}, t + 1) is None
    assert B.o_que_mostrar({}, t) is None                     # arquivo ausente ou corrompido: nada na tela
    ativo = {"modo": "ativo", "desde": t, "ate": t + B.TTL_S}
    # o toque e o F12 aparecem NA HORA, mesmo entre um comando e outro do piloto
    assert B.o_que_mostrar(ativo, t + 1, toque=t + 0.5) == "pausado"
    assert B.o_que_mostrar(ativo, t + 1, toque=t + 1 - B.QUIETO_S - 0.1) == "ativo"
    assert B.o_que_mostrar(ativo, t + 1, freio=True) == "parado"
    assert B.o_que_mostrar(ativo, t + B.TTL_S + 1, freio=True) is None   # piloto morto: nem o vermelho fica
    assert "continua em 10 s" in B.texto_da_pausa(t, t) and "continua em 1 s" in B.texto_da_pausa(t + B.QUIETO_S - 0.5, t)


def test_borda_estado_e_toque_em_disco(tmp_path, monkeypatch):
    from piloto import borda_comum as B
    monkeypatch.setattr(B, "ESTADO", str(tmp_path / "estado.json"))
    monkeypatch.setattr(B, "TOQUE", str(tmp_path / "toque.json"))
    monkeypatch.setattr(B, "VIVO", str(tmp_path / "vivo.json"))
    assert B.ler_estado() == {} and B.ultimo_toque() == 0.0 and not B.borda_viva()
    d = B.escrever_estado("ativo", agora=50.0)
    assert B.ler_estado()["modo"] == "ativo" and d["ate"] == 50.0 + B.TTL_S and d["texto"]
    B.gravar_toque(42.5, "mouse")
    assert B.ultimo_toque() == 42.5
    B.bater_ponto(100.0)
    assert B.borda_viva(100.5) and not B.borda_viva(100.0 + B.VIVO_S + 0.1)
    with pytest.raises(ValueError):
        B.escrever_estado("azul")
