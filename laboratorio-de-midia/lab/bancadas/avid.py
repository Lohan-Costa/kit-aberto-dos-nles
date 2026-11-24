"""Bancada do MEDIA COMPOSER no Windows — a ponte (gRPC do próprio MC em [::1]:9100, pelo cliente do De Lá Pra Cá), o
abrir/fechar, o perfil e o projeto do laboratório. Desenho aprovado pelo autor em 2026-10-11
(https://claude.ai/artifact/MzPuChcFZEEuKbWcRe7G6B).

Regras (CLAUDE.md do laboratório): toda ação passa pelo cão de guarda (`vigia_windows.com_prazo`: prazo + MC vivo +
respondendo + EVENTLOG + diálogos do catálogo `avid/dialogos/`); o FOCO dispara coisas no MC (a janela do layout de
teclado, a varredura da MediaFiles) — frente + varrer antes e depois. Perfil do laboratório: DLPC_LAB; projetos em
`Documents\\Avid Projects\\DLPC LAB\\`, um por taxa; mídia escrita pelo laboratório em `D:\\Avid MediaFiles\\MXF\\3572`.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

from . import interface_win as I
from . import vigia_windows as V

EXE = r"C:\Program Files\Avid\Avid Media Composer\AvidMediaComposer.exe"
PERFIL = "DLPC_LAB"
PROJETOS = os.path.join(os.path.expanduser("~"), "Documents", "Avid Projects", "DLPC LAB")
MIDIA_DO_LAB = r"D:\Avid MediaFiles\MXF\3572"
_AQUI = os.path.dirname(os.path.abspath(__file__))
from . import _piloto  # noqa: E402,F401
from piloto import apps as _apps  # noqa: E402
#: os diálogos conhecidos do MC moram no PILOTO desde 2026-10-12 (um catálogo só para a família)
CATALOGO = _apps.catalogo("avid")
FOTOS = os.path.join(os.path.dirname(os.path.dirname(_AQUI)), "saida", "bancadas", "avid", "vigia")
DLPC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_AQUI))), "2 ATIVOS", "_DeLaPraCa")

# DoCommand (banco, plugins/avid-panel-sdk/dados/docommand-commands.json)
CMD_SAIR, CMD_FECHAR_PROJETO = 1010, 1172


#: janelas do MC que NÃO são modais: a "Settings", a "Select Project" e as bins soltas ("Bins.1"… — numa sessão nova o
#: OpenBin abre a bin numa janela própria, 2026-10-11)
NAO_MODAIS = ("Settings", "Select Project", "Motion Effect Editor", "Effect Editor", "Effect Palette", "Tracking", "Bins", "De Lá Pra Cá", "Órbita",
              "Promo Entrega", "Ciclo Assist") + tuple(f"Bins.{n}" for n in range(1, 10))


def _catalogo() -> list[dict]:
    return V.carregar_catalogo(CATALOGO)


def mc():
    """O cliente da API do MC (o do De Lá Pra Cá: `servico/avid/mcapi.py`)."""
    for p in (os.path.join(DLPC, "plugins", "media-composer", "servico"), os.path.join(DLPC, "motor")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from avid.mcapi import MediaComposer
    return MediaComposer()


def rodando() -> bool:
    return bool(V.pids_do_premiere(V.AVID))


def principal() -> int | None:
    return V._janela_principal(V.AVID)


def frente_e_varrer() -> list[dict]:
    """A regra do foco: traz o MC para a frente e resolve os diálogos (os do catálogo; desconhecido = erro com foto)."""
    h = principal()
    if h:
        I.frente(h)
        time.sleep(1.5)
    return V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)


def afastar_bins(x: int = 1960, y: int = 60) -> list[str]:
    """Leva as bins soltas ("Bins.N") para o 2º monitor: no meio da tela elas cobriam a timeline, que a bancada de
    efeitos lê e clica por coordenada (2026-10-11)."""
    import ctypes
    fora = []
    for d in V.dialogos(V.AVID):
        # ⛔ o Motion Effect Editor solto ficou SOBRE a lista de efeitos da paleta (2026-10-12): o duplo-clique no preset
        # caía nele e nada era aplicado, sem aviso. As janelas de ferramenta também vão para o 2º monitor.
        ferramenta = d["titulo"] in ("Motion Effect Editor", "Effect Editor")
        if d["titulo"].startswith("Bins.") or ferramenta:
            x0, y0, x1, y1 = I.retangulo(d["hwnd"])
            ctypes.windll.user32.MoveWindow(d["hwnd"], x + (700 if ferramenta else 0), y, x1 - x0, y1 - y0, True)
            fora.append(d["titulo"])
    return fora


def sem_dialogos(voltas: int = 8, ignorar: tuple = NAO_MODAIS) -> bool:
    """Frente → varrer até não sobrar diálogo (as janelas do layout de teclado vêm em fila, uma por foco e a API fica
    parada enquanto alguma estiver aberta). Devolve se esvaziou."""
    for _ in range(voltas):
        h = principal()
        if h:
            I.frente(h)
            time.sleep(1.5)
        V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=ignorar)
        if not [d for d in V.dialogos(V.AVID) if d["titulo"] not in ignorar]:
            return True
        time.sleep(1.5)
    return False


def guardado(acao, prazo: float, pronto=None):
    """A ação sob o cão de guarda do piloto: prazo, MC vivo e respondendo, queda no EVENTLOG, diálogos — e o MC NUM
    PROJETO (`apps.saude_avid`): a "Select Project" é ignorada como diálogo (é normal na ABERTURA), mas no meio de um
    trabalho quer dizer que o projeto fechou (2026-10-12: o MC caiu, reabriu na Select Project e uma montagem fora do
    guarda esperou 2 min sem ninguém olhar). Não use para abrir/fechar projeto."""
    return V.com_prazo(acao, prazo, V.AVID, FOTOS, _catalogo(), pronto=pronto, ignorar=NAO_MODAIS,
                       saude=_apps.saude_avid)


def comando(cmd_id: int, prazo: float = 60):
    with mc() as m:
        return guardado(lambda: m._chamar("DoCommand", _timeout=prazo, commandId=cmd_id), prazo)


def fechar(prazo: float = 120) -> None:
    """Sai do MC pelo DoCommand Exit (o MC grava as bins). Espera o processo sumir, com o cão de guarda."""
    if not rodando():
        return
    try:
        with mc() as m:
            m._chamar("DoCommand", _timeout=30, commandId=CMD_SAIR)
    except Exception:                 # noqa: BLE001 — a conexão cai quando o MC sai; o que conta é o processo
        pass
    fim = time.time() + prazo
    while rodando():
        if time.time() > fim:
            raise V.Travado(f"o MC não fechou em {prazo:.0f} s", V.foto_da_tela(FOTOS, "nao_fechou"))
        V.varrer(V.AVID, _catalogo(), FOTOS, contexto="fechar", ignorar=NAO_MODAIS)
        time.sleep(2)


def abrir_ate_select_project(prazo: float = 180) -> int:
    """Abre o MC e espera a janela "Select Project" (a abertura dispara "Application ready for user" no EVENTLOG)."""
    if not rodando():
        subprocess.Popen([EXE], creationflags=0x08000000)
    fim = time.time() + prazo
    while time.time() < fim:
        for d in V.dialogos(V.AVID):
            if d["titulo"] == "Select Project":
                return d["hwnd"]
        try:
            V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)
        except V.DialogoAberto:
            raise
        time.sleep(2)
    raise V.Travado(f"a janela Select Project não apareceu em {prazo:.0f} s", V.foto_da_tela(FOTOS, "sem_select_project"))


# Posições na janela "Select Project" como FRAÇÃO do tamanho dela (a escala muda com o monitor: 1354 px a 125 %,
# 1083 px a 100 % — medido nas duas, 2026-10-11)
_SP = {"aba_projetos": (0.522, 0.156), "aba_novo": (0.643, 0.156), "lista_1a_linha": (0.30, 0.366),
       "open": (0.917, 0.918), "quit": (0.825, 0.918)}


def _clicar_sp(h: int, chave: str, duplo: bool = False) -> None:
    esq, topo, dir_, base = I.retangulo(h)
    fx, fy = _SP[chave]
    I.clicar(int(esq + fx * (dir_ - esq)), int(topo + fy * (base - topo)), duplo)


def abrir_projeto(nome: str, prazo: float = 180, parado: float = 30) -> dict:
    """Do zero até o projeto aberto: abre o MC (se preciso), escolhe o projeto pelo NOME na lista da "Select Project"
    (digitar o nome seleciona a linha) e Open; espera o título da janela principal trazer o nome. A REGRA DO FOCO: trazer
    a Select Project para a frente faz o MC soltar a janela do layout de teclado — então frente → esperar → varrer, e só
    depois clicar (2026-10-11: o 1º Open caiu na hora da janela e o projeto não abriu). Select Project parada 15 s depois
    do Open → Open de novo; nada muda por `parado` s → `Travado` com foto (nada de esperar o prazo inteiro)."""
    import ctypes
    h = abrir_ate_select_project()
    ignorar = ("Select Project", "Settings")

    def preparar():
        if not I.frente(h):
            raise V.Travado("a Select Project não veio para a frente", V.foto_da_tela(FOTOS, "sp_sem_foco"))
        for _ in range(4):                      # o foco solta os diálogos: resolve todos antes de clicar
            time.sleep(1.5)
            if not V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=ignorar):
                break
        I.frente(h)

    def titulo() -> str:
        p = principal()
        t = ctypes.create_unicode_buffer(256)
        if p:
            ctypes.windll.user32.GetWindowTextW(p, t, 256)
        return t.value.rstrip()

    preparar()
    _clicar_sp(h, "aba_projetos")
    time.sleep(0.8)
    _clicar_sp(h, "lista_1a_linha")
    time.sleep(0.3)
    I.digitar(nome)
    time.sleep(0.5)
    _clicar_sp(h, "open")
    inicio = ultimo = time.time()
    estado, tentativas = None, 1
    while time.time() - inicio < prazo:
        sp_aberta = any(d["titulo"] == "Select Project" for d in V.dialogos(V.AVID))
        if titulo().endswith(nome) and not sp_aberta:
            # as janelas do layout de teclado chegam em FILA logo depois de abrir e a API fica parada enquanto houver
            # uma: esvaziar e perguntar de novo (2026-10-11: duas varridas não bastaram)
            for _ in range(6):
                sem_dialogos()
                try:
                    with mc() as m:
                        return m.projeto(recarregar=True)
                except Exception:            # noqa: BLE001 — API parada por diálogo: varrer e tentar de novo
                    time.sleep(2)
            raise V.Travado(f"{nome!r} abriu mas a API não responde", V.foto_da_tela(FOTOS, "api_parada"))
        resolvidos = V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=ignorar)
        agora = (sp_aberta, titulo(), len(V.dialogos(V.AVID)))
        if agora != estado or resolvidos:
            estado, ultimo = agora, time.time()
        if sp_aberta and time.time() - ultimo > 15 and tentativas < 3:
            preparar()
            _clicar_sp(h, "open")
            tentativas += 1
            ultimo = time.time()
        if time.time() - ultimo > parado:
            raise V.Travado(f"nada mudou em {parado:.0f} s abrindo {nome!r}", V.foto_da_tela(FOTOS, "abrir_parado"))
        time.sleep(2)
    raise V.Travado(f"o projeto {nome!r} não abriu em {prazo:.0f} s", V.foto_da_tela(FOTOS, "projeto_nao_abriu"))


_SP.update({"nome_projeto": (0.583, 0.297), "formato": (0.576, 0.393), "create": (0.917, 0.918),
            "menu_hd1080": (480 / 1083, 475 / 847)})
#: a ORDEM dos itens no submenu HD 1080 (o separador o teclado pula; lida no print, MC 25.6, 2026-10-11)
_FORMATOS_HD1080 = {"1080i/50": 0, "1080i/59.94": 1, "1080p/23.976": 2, "1080p/24": 3, "1080p/25": 4,
                    "1080p/29.97": 5, "1080p/30": 6, "1080p/50": 7, "1080p/59.94": 8, "1080p/60": 9}


def voltar_a_select_project(prazo: float = 120) -> int:
    """Fecha o projeto aberto (DoCommand Close Project) e devolve a "Select Project" (com o cão de guarda)."""
    if not any(d["titulo"] == "Select Project" for d in V.dialogos(V.AVID)):
        with mc() as m:
            try:
                m._chamar("DoCommand", _timeout=60, commandId=CMD_FECHAR_PROJETO)
            except Exception:             # noqa: BLE001 — a resposta pode não vir; o que conta é a janela
                pass
    fim = time.time() + prazo
    while time.time() < fim:
        for d in V.dialogos(V.AVID):
            if d["titulo"] == "Select Project":
                return d["hwnd"]
        V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)
        time.sleep(2)
    raise V.Travado("a Select Project não voltou", V.foto_da_tela(FOTOS, "sem_select_project"))


def criar_projeto(nome: str, formato: str, confirmar=None) -> dict:
    """Um projeto do laboratório em `PROJETOS` (a Location que a Select Project lembra): aba New Project → nome →
    Format (abre a lista e DIGITA o formato, ex. "1080i/59.94") → Create; depois abre como `abrir_projeto`. `confirmar`
    (opcional) recebe a foto da janela antes do Create e devolve se segue."""
    h = voltar_a_select_project()
    if not I.frente(h):
        raise V.Travado("a Select Project não veio para a frente", V.foto_da_tela(FOTOS, "sp_sem_foco"))
    for _ in range(4):
        time.sleep(1.5)
        if not V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS):
            break
    I.frente(h)
    _clicar_sp(h, "aba_novo")
    time.sleep(1.0)
    _clicar_sp(h, "nome_projeto")
    time.sleep(0.3)
    I.tecla(0x41, 0x11)
    I.digitar(nome)
    time.sleep(0.3)
    # o Format é um MENU em níveis (Ultra HD, 2K, 4K, 8K, 16K, HD 1080 ▸ …). Digitar não escolhe, e clicar no item por
    # posição errou 2 de 4 (o submenu muda de lugar conforme o formato já escolhido — 2026-10-11). Pelo TECLADO, que não
    # depende de posição: abrir o menu → ↓ ×6 (HD 1080) → → (abre o submenu no 1º item) → ↓ ×n → Enter.
    if formato not in _FORMATOS_HD1080:
        raise ValueError(f"formato {formato!r} sem posição no menu (há: {', '.join(_FORMATOS_HD1080)})")
    _clicar_sp(h, "formato")
    time.sleep(0.8)
    for _ in range(6):
        I.tecla(0x28)
        time.sleep(0.12)
    I.tecla(0x27)
    time.sleep(0.6)
    for _ in range(_FORMATOS_HD1080[formato]):
        I.tecla(0x28)
        time.sleep(0.12)
    I.tecla(I.ENTER)
    time.sleep(0.8)
    if confirmar is not None and not confirmar(V.fotografar(h, os.path.join(FOTOS, f"novo_{nome}.bmp"))):
        raise RuntimeError("criação cancelada na conferência")
    _clicar_sp(h, "create")
    fim = time.time() + 180
    import ctypes
    while time.time() < fim:
        p = principal()
        t = ctypes.create_unicode_buffer(256)
        if p:
            ctypes.windll.user32.GetWindowTextW(p, t, 256)
        if t.value.rstrip().endswith(nome) and not any(d["titulo"] == "Select Project" for d in V.dialogos(V.AVID)):
            frente_e_varrer()
            time.sleep(2)
            frente_e_varrer()
            with mc() as m:
                p = m.projeto(recarregar=True)
            if p.get("type") != formato:
                raise V.Travado(f"o projeto {nome!r} saiu {p.get('type')!r}, não {formato!r} — apagar e refazer",
                                V.foto_da_tela(FOTOS, "formato_errado"))
            return p
        V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)
        time.sleep(2)
    raise V.Travado(f"o projeto {nome!r} não foi criado", V.foto_da_tela(FOTOS, "nao_criou"))


#: presets do laboratório (só valem no lab — regra do autor): o XML com o envelope COMPLETO do `<perfil> Settings.xml`
#: (DomainMagic/DomainKey + `<AvClass id="SETG"/>` + o bloco `EXst`). Sem o SETG o `LoadSetting` responde
#: "No settings objects" (banco, 2026-08-16); com ele entra NA HORA, com o MC aberto (2026-10-11).
PRESETS = os.path.join(_AQUI, "avid", "presets")
PRESET_DNXLB = "DLPC_LAB_DNXLB"        # MXF OP1a DNxHR LB, áudio em mono (_EXPORTFORMAT 23); do "dnxlb" do autor


#: a taxa vive no preset (2026-10-11: o dnxlb feito a 23.976 recusou a sequência a 24 — "Edit rate of the sequence does
#: not match the edit rate in the shim"): `descriptor.samplerate` dos descritores, `iSeqFrameRate` (a nominal) e o
#: `ATN_ES_SEQ_FRAME_RATE` (double little-endian em hexa). Uma variante por taxa, gerada do mesmo XML.
_TAXAS_DO_PRESET = {"23.976": ("24000//1001", 24.0), "24": ("24//1", 24.0), "25": ("25//1", 25.0),
                    "29.97": ("30000//1001", 30.0), "50": ("50//1", 50.0)}


def _preset_da_taxa(fps: str) -> tuple[str, str]:
    import struct
    with open(os.path.join(PRESETS, PRESET_DNXLB + ".xml"), encoding="utf-8") as f:
        xml = f.read()
    if fps == "23.976":
        return PRESET_DNXLB, xml
    racional, nominal = _TAXAS_DO_PRESET[fps]
    nome = f"{PRESET_DNXLB}_{fps.replace('.', '')}"
    hexa = " ".join(f"{b:x}" for b in struct.pack("<d", nominal))
    xml = xml.replace(f">{PRESET_DNXLB}<", f">{nome}<", 1)
    xml = xml.replace('"value":"24000//1001","type":"Rational"', f'"value":"{racional}","type":"Rational"')
    xml = xml.replace('name="iSeqFrameRate" type="double">24.000000<', f'name="iSeqFrameRate" type="double">{nominal:.6f}<')
    import re
    xml = re.sub(r"(ATN_ES_SEQ_FRAME_RATE</AvProp>.*?BobData\" type=\"bytes\">)8 [0-9a-f ]+?<",
                 lambda m: f"{m.group(1)}8 {hexa} <", xml, count=1, flags=re.S)
    return nome, xml


def instalar_preset(fps: str = "23.976") -> str:
    """Instala o preset do laboratório DA TAXA no projeto aberto por `LoadSetting` e devolve o nome. O `unique_id` é o
    próprio nome: repetir é inofensivo ("Completed"); outro id com o mesmo nome = "Some setting already exist."."""
    nome, xml = _preset_da_taxa(fps)
    with mc() as m:
        guardado(lambda: m._chamar("LoadSetting", _timeout=60, unique_id=nome, xml_setting=xml), 60)
        lista = list(m._chamar("GetListOfExportSettings").body.setting_names)
    if nome not in lista:
        raise RuntimeError(f"o preset {nome!r} não entrou (export: {lista})")
    return nome


def exportar(mob_id: str, destino: str, nome_arquivo: str, preset: str = PRESET_DNXLB, prazo: float = 600,
             estavel: int = 4) -> str:
    """`ExportFile` de um mob com o preset do laboratório. O rpc responde "Completed" ANTES do arquivo existir
    (assíncrono): espera o arquivo aparecer e o tamanho parar por `estavel` leituras (3 s cada). Diálogo no meio =
    erro com foto; nada em `prazo` s = `Travado`. Devolve o caminho do arquivo."""
    import glob
    os.makedirs(destino, exist_ok=True)
    for velho in glob.glob(os.path.join(destino, nome_arquivo + ".*")):   # a saída é do laboratório: sem o velho, o
        os.remove(velho)                                                 # arquivo achado só pode ser deste export
    with mc() as m:
        guardado(lambda: m._chamar("ExportFile", _timeout=60, mob_id=mob_id, file_name=nome_arquivo,
                                   export_settings_name=preset, destination_path=destino), 60)
    inicio, ultimo, iguais = time.time(), None, 0
    while time.time() - inicio < prazo:
        V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)
        agora = [(f, os.path.getsize(f)) for f in sorted(glob.glob(os.path.join(destino, nome_arquivo + ".*")))]
        # ⛔ o render de efeito (rampa, 2026-10-12) deixa o arquivo PARADO em 8 MB por dezenas de segundos entre blocos:
        # enquanto a janela de progresso ("Exporting Files…", título "AvidMediaComposer") existir, não terminou.
        progresso = any(d["titulo"] == "AvidMediaComposer" for d in V.dialogos(V.AVID))
        iguais = iguais + 1 if agora and agora == ultimo and not progresso else 0
        ultimo = agora
        if agora and iguais >= estavel:
            return agora[0][0]
        time.sleep(3)
    raise V.Travado(f"o export de {nome_arquivo!r} não terminou em {prazo:.0f} s", V.foto_da_tela(FOTOS, "export"))


ASSIST = os.path.join(os.path.dirname(DLPC), "_CICLO ASSIST")


def _timeline():
    """O montador de timeline `.avb` do Ciclo Assist (`cicloassist/avid/timeline.py`): código em produção, validado
    no MC 25.6 (Filler de rabo, tracks alinhadas, UID da bin preservado). Reusado, não reescrito."""
    if ASSIST not in sys.path:
        sys.path.insert(0, ASSIST)
    from cicloassist.avid import timeline
    return timeline


def montar_sequencia(bin_avb: str, nome: str, cortes: list[tuple], prazo: float = 120) -> str:
    """Acrescenta à bin (caminho absoluto) a sequência `nome` com os `cortes` = [(nome_do_master, in, duração), …]
    em sequência, e devolve o mob_id DA API da sequência. A dança do banco (avb/escrita.md, 2026-09-11): `CloseBin`
    (o MC salva e larga o arquivo) → pyavb grava ao lado e troca → `OpenBin` (relê do disco)."""
    import avb
    T = _timeline()
    with mc() as m:
        # o CloseBin ANTES de ler: é ele que grava no disco o master recém-importado (2026-10-11: lida antes, a bin
        # do projeto 24 ainda não tinha o master do import)
        try:
            m.fechar_bin(bin_avb)
        except Exception:                    # noqa: BLE001 — bin já fechada responde erro (normal)
            pass
        with avb.open(bin_avb) as f:
            masters = {mm.name: mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}
            if not masters:
                raise RuntimeError(f"a bin {bin_avb} não tem master clip no disco")
            entradas = []
            for nome_master, inicio, dur in cortes:
                mm = masters[nome_master]
                taxa = mm.edit_rate
                trilhas = tuple(sorted((t.media_kind, t.index) for t in mm.tracks
                                       if t.media_kind in ("picture", "sound")))
                entradas.append(T.Entrada(mob_id=str(mm.mob_id), duracao=dur, trilhas=trilhas, start_time=inicio))
        T.acrescentar_timeline(bin_avb, nome, entradas, taxa)
        m.abrir_bin(bin_avb)
        fim = time.time() + prazo
        while time.time() < fim:
            for it in m.itens_de(bin_avb, flags=("AllTypes",)):
                if it.name == nome:
                    frente_e_varrer()
                    return it.mob_id
            V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)
            time.sleep(2)
    raise V.Travado(f"a sequência {nome!r} não apareceu na bin", V.foto_da_tela(FOTOS, "sequencia"))


def montar_camadas(bin_avb: str, nome: str, camadas: list[tuple], prazo: float = 120) -> str:
    """Sequência com UM clipe por trilha de imagem, empilhados (V1, V2, …): `camadas` = [(nome_do_master, in, duração),
    …] de baixo para cima — o fundo e a frente de uma máscara (AniMatte, 2026-10-12). Devolve o mob_id da API.

    O montador do Ciclo Assist põe na V2 só arte de matte key; aqui a V1 sai dele (a forma validada) e as trilhas de
    cima são a MESMA forma da V1 — `Sequence[Filler 0, SourceClip, Filler de rabo]`, `track_id` 1 do master — com só o
    índice da trilha trocado, inseridas logo depois da V1 (a ordem que o MC grava: V1, V2, A1…)."""
    import avb
    T = _timeline()
    original = T.montar_timeline

    with mc() as m:
        try:
            m.fechar_bin(bin_avb)
        except Exception:                    # noqa: BLE001 — bin já fechada responde erro (normal)
            pass
        with avb.open(bin_avb) as f:
            masters = {mm.name: mm for mm in f.content.mobs if mm.mob_type == "MasterMob"}
            ids = {n: str(masters[n].mob_id) for n, _i, _d in camadas}
            taxa = masters[camadas[0][0]].edit_rate
        total = camadas[0][2]

        def com_camadas(f, nome_, entradas, edit_rate, *a, **k):
            comp = original(f, nome_, entradas, edit_rate, *a, **k)
            for indice, (n, inicio, dur) in enumerate(camadas[1:], start=2):
                if dur > total:
                    raise ValueError(f"a camada {n!r} ({dur}) passa do fundo ({total})")
                sc = f.create.SourceClip(edit_rate, "picture")
                sc.mob_id = T.MobID(ids[n])
                sc.track_id = 1
                sc.start_time = inicio
                sc.length = dur
                seq = f.create.Sequence(edit_rate, "picture")
                seq.components = [T._filler(f, edit_rate, 0, "picture"), sc]
                seq.components.append(T._trail_filler(f, edit_rate, "picture", seq.components, total))
                tr = f.create.Track()
                tr.index = indice
                tr.component = seq
                tr.lock_number = 0
                tr.filler_proxy = T._referencia_de_track(f, edit_rate, "picture")
                tr.session_attr = T._atributos(f, _ENBLSTATE=1, _MONSTATE=1)
                comp.tracks.insert(indice - 1, tr)
            return comp

        n0, i0, d0 = camadas[0]
        T.montar_timeline = com_camadas
        try:
            T.acrescentar_timeline(bin_avb, nome, [T.Entrada(mob_id=ids[n0], duracao=d0, trilhas=(("picture", 1),),
                                                             start_time=i0)], taxa)
        finally:
            T.montar_timeline = original
        m.abrir_bin(bin_avb)
        fim = time.time() + prazo
        while time.time() < fim:
            for it in m.itens_de(bin_avb, flags=("AllTypes",)):
                if it.name == nome:
                    frente_e_varrer()
                    return it.mob_id
            V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)
            time.sleep(2)
    raise V.Travado(f"a sequência {nome!r} não apareceu na bin", V.foto_da_tela(FOTOS, "camadas"))


def drt_pelo_dlpc(mob_id: str, caminho_drt: str, nome: str | None = None) -> dict:
    """O DRT da sequência pelo MESMO caminho do painel do De Lá Pra Cá (`servico/sessao_export.py`: salvar a bin →
    ler o `.avb` → mídia gerenciada pelo `.pmr` → `drp.writer.build_drt`), sem o painel. Devolve o resultado da
    sessão (o que o painel mostraria) com `saida`."""
    servico = os.path.join(DLPC, "plugins", "media-composer", "servico")
    for p in (servico, os.path.join(DLPC, "motor")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from sessao_export import SessaoExport

    class _Servico:
        def media_composer(self):
            return mc()

    s = SessaoExport(_Servico())
    s._preparar(mob_id)
    s._gerar("drt", caminho_drt, nome or s.nome_da_sequencia(), "")
    return s.estado.resultado


def importar(arquivo: str, bin_avb: str, prazo: float = 300) -> str:
    """`ImportFile` do arquivo para a bin (mídia GERENCIADA; o MC escolhe a pasta numérica do drive D:) e espera o
    master aparecer na bin — o rpc responde "Completed" em 0,3 s e o import termina depois (banco, windows.md).
    Devolve o nome do master. Já na bin = não importa de novo."""
    nome = os.path.basename(arquivo)
    # o MC pode dar ao master o nome SEM a extensão ("B19_TREMIDO", MC 25.6, 2026-10-23): aceitar os dois
    nomes = (nome, os.path.splitext(nome)[0])

    def na_bin(m):
        return next((it.name for it in m.itens_de(bin_avb, flags=("masterClips",)) if it.name in nomes), None)

    with mc() as m:
        if na_bin(m):
            return na_bin(m)
        guardado(lambda: m._chamar("ImportFile", _timeout=60, file_path=arquivo, import_settings_name="Untitled",
                                   destination_video_drive="SSD (D:)",
                                   destination_audio_drive="SSD (D:)", destination_bin=bin_avb), 60)
        fim = time.time() + prazo
        while time.time() < fim:
            V.varrer(V.AVID, _catalogo(), FOTOS, ignorar=NAO_MODAIS)
            achado = na_bin(m)
            if achado:
                return achado
            time.sleep(3)
    raise V.Travado(f"o import de {nome!r} não chegou à bin", V.foto_da_tela(FOTOS, "import"))


def drt_do_disco(bin_avb: str, mob_id: str, caminho_drt: str, nome: str | None = None,
                 raster: tuple[int, int] = (1920, 1080)) -> dict:
    """O DRT pelos MESMOS passos do painel (`resolver_midia` → `montar_midia` → `build_drt`), mas com o MC FECHADO:
    lê a `.avb` já salva e o índice da mídia gerenciada. Só serve quando todos os masters estão na gerenciada (o MC é
    perguntado apenas pelos que não estão). Para refazer o DRT depois de mexer no writer sem reabrir o MC."""
    servico = os.path.join(DLPC, "plugins", "media-composer", "servico")
    for p in (servico, os.path.join(DLPC, "motor")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from avb_bin.segmentos import ler_timeline_de_arquivo, montar_midia
    from drp.writer import build_drt
    from sessao_export import resolver_midia
    leitura = ler_timeline_de_arquivo(bin_avb, mob_id=mob_id)
    midia = resolver_midia(None, leitura)
    if len(midia["na_gerenciada"]) != len(leitura["masters"]):
        raise RuntimeError("há master fora da mídia gerenciada: use drt_pelo_dlpc (com o MC)")
    segmentos, casados, metadados = montar_midia(
        leitura, midia["arquivos"], os.path.dirname(caminho_drt),
        {k: m.get("colunas_mc") or {} for k, m in leitura["masters"].items()}, midia["gerenciados"])
    saida = build_drt(segmentos, casados, caminho_drt, timeline_name=nome or leitura["composition_name"],
                      timeline_fps=leitura["timeline_fps"], offline=metadados, timeline_size=raster)
    return {k: v for k, v in saida.items() if k != "clips"}
