"""As mãos POR MENSAGEM respeitam o mesmo freio das outras e acham o item de menu pelo nome. Não clica em nada:
o freio levanta ANTES de qualquer mensagem, e o menu é um HMENU criado aqui, sem janela."""
import ctypes
import os
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows")


@pytest.fixture
def maos(monkeypatch, tmp_path):
    from piloto import maos_windows as m
    parar = tmp_path / "PARAR"
    monkeypatch.setattr(m, "ARQUIVOS_PARAR", [str(parar)])
    monkeypatch.setattr(m, "SEM_BORDA", True)
    enviadas = []
    monkeypatch.setattr(m._u, "PostMessageW", lambda *a: enviadas.append(a) or 1)
    return m, parar, enviadas


def test_freio_vale_para_mensagem(maos):
    m, parar, enviadas = maos
    parar.write_text("")
    for gesto in (lambda: m.msg_clicar(0, 10, 10), lambda: m.msg_tecla(0, 0x41),
                  lambda: m.msg_rolar(0, 10, 10, 1), lambda: m.comando_menu(0, "File > Save")):
        with pytest.raises(m.Parado):
            gesto()
    assert enviadas == []                                    # nenhuma mensagem saiu


def test_item_de_menu_pelo_nome(maos):
    m, _, _ = maos
    u = ctypes.windll.user32
    u.CreateMenu.restype = u.CreatePopupMenu.restype = ctypes.c_void_p
    u.AppendMenuW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_wchar_p]
    barra, arquivo, novo = u.CreateMenu(), u.CreatePopupMenu(), u.CreatePopupMenu()
    u.AppendMenuW(novo, 0, 11605, "Sequence From Clip")
    u.AppendMenuW(arquivo, 0x10, novo, "&New")
    u.AppendMenuW(arquivo, 0, 57603, "&Save\tCtrl+S")
    u.AppendMenuW(barra, 0x10, arquivo, "&File")
    m_get = m._u.GetMenu
    try:
        m._u.GetMenu = lambda h: barra
        assert m.item_de_menu(0, "File > Save")[2] == 57603
        assert m.item_de_menu(0, "file > new > sequence from clip...")[2] == 11605
        with pytest.raises(LookupError):
            m.item_de_menu(0, "File > Exit")
    finally:
        m._u.GetMenu = m_get
