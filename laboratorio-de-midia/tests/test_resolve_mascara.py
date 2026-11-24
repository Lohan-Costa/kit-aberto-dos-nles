"""O Magic Mask da Color do Resolve (cache .dvcc + banco) e a ponte .prmf → Resolve. Os moldes vêm do Resolve Studio 21.1
(macOS, 2026-10-07/08): `lab/moldes/resolve/`. O teste no Resolve de verdade é a bancada (ver o banco, magic-mask.md §7)."""
import glob
import os
import shutil
import sqlite3
import tempfile
import unittest
import zlib

from lab import prmf_para_resolve as ppr, resolve_mascara as rm

M = rm.MOLDES
PASTA_PRMF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "resultados", "B10_ROTO", "premiere-26.0.2-autor", "rotoscopia_teste_premiere26 Masks")


def _tem_zstd():
    try:
        rm._zstd()
        return True
    except RuntimeError:
        return False


class TestDvcc(unittest.TestCase):
    def test_regravar_o_molde_sai_byte_a_byte(self):
        """O molde é um quadro VAZIO gravado pelo Resolve (taxa 0, TC 00:00:00:00): regravado sai idêntico."""
        mascara, w, h = rm.ler_dvcc(rm.MOLDE_DVCC)
        self.assertEqual((w, h, len(mascara)), (1920, 1080, 1920 * 1080))
        with open(rm.MOLDE_DVCC, "rb") as fh:
            original = fh.read()
        self.assertEqual(rm.dvcc(mascara, w, h, 0, 0.0), original)

    def test_ida_e_volta_com_tc_e_outra_resolucao(self):
        m = bytes([0, 255]) * (640 * 360 // 2)
        d = rm.dvcc(m, 640, 360, 150, 25.0)
        self.assertEqual(len(d) % 8192, 0)
        self.assertEqual(d[0x44:0x4F], b"00:00:06:00")
        with tempfile.NamedTemporaryFile(suffix=".dvcc", delete=False) as fh:
            fh.write(d)
        try:
            lido, w, h = rm.ler_dvcc(fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual((lido, w, h), (m, 640, 360))


class TestBanco(unittest.TestCase):
    @unittest.skipUnless(_tem_zstd(), "PULADO — sem zstd")
    def test_tirar_o_campo_12_da_a_versao_rastreada(self):
        """Medido: a versão de cor importada SEM os campos 12 é, byte a byte, a que o Resolve grava depois do tracking."""
        with open(os.path.join(M, "versao_importada.bin"), "rb") as fh:
            imp = fh.read()
        with open(os.path.join(M, "versao_rastreada.bin"), "rb") as fh:
            ras = fh.read()
        novo, k = rm.tirar_campo(imp, 12)
        self.assertEqual((novo, k), (ras, 3))
        self.assertEqual(rm.tirar_campo(ras, 12), (ras, 0))

    @unittest.skipUnless(_tem_zstd(), "PULADO — sem zstd")
    def test_zstd_como_o_resolve(self):
        z = rm.zstd_comprimir(b"x" * 670)
        self.assertEqual(z[:4], b"\x28\xb5\x2f\xfd")
        self.assertEqual(z[4] & 0x24, 0x20)             # tamanho do conteúdo presente, SEM soma de verificação
        self.assertEqual(rm.zstd_abrir(z), b"x" * 670)

    def test_recibo(self):
        r = rm.recibo("0ec9344f-465e-4900-a36e-a8b5c1221794", 0, 299, serie=0x08871F1E)
        d = zlib.decompress(r[4:])
        with open(rm.MOLDE_RECIBO, "rb") as fh:
            molde = zlib.decompress(fh.read()[4:])
        # o molde (do Resolve) só difere no 2º número de série, que o Resolve não grava como série+3
        self.assertEqual(d[:0x96] + d[0x9A:], molde[:0x96] + molde[0x9A:])
        self.assertEqual(int.from_bytes(r[:4], "big"), 178)

    def test_recibo_de_clipe_aparado(self):
        """O recibo que o Resolve gravou para o B10 aparado 50→298 (2026-10-08): a faixa vai em quadros da mídia."""
        d = zlib.decompress(rm.recibo("6f537c7f-8608-4231-b031-04d23756abb3", 50, 298)[4:])
        faixa = [int.from_bytes(d[p:p + 4], "big") for p in (0x86, 0x8E, 0xA6, 0xAE)]
        self.assertEqual(faixa, [50, 249, 50, 298])

    @unittest.skipUnless(_tem_zstd(), "PULADO — sem zstd")
    def test_marcar_em_dia_num_banco_de_mentira(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "Project.db")
            con = sqlite3.connect(db)
            con.execute('create table "ListMgt::LmVersionTable" (Sm2TiItem_id text, pActive text)')
            con.execute('create table "ListMgt::LmVersion" ("ListMgt::LmVersion_id" text, Body blob)')
            con.execute("create table Sm2TiItem (Sm2TiItem_id text, RenderCacheBA blob)")
            with open(os.path.join(M, "versao_importada.bin"), "rb") as fh:
                body = b"\x81" + rm.zstd_comprimir(fh.read())
            ver = "0ec9344f-465e-4900-a36e-a8b5c1221794"
            con.execute("insert into \"ListMgt::LmVersionTable\" values ('item', ?)", (ver,))
            con.execute('insert into "ListMgt::LmVersion" values (?, ?)', (ver, body))
            con.execute("insert into Sm2TiItem values ('item', NULL)")
            con.commit()
            con.close()
            r = rm.marcar_em_dia(db, "item", 0, 299, os.path.join(d, "copias"))
            self.assertEqual(r["campos_12"], 3)
            self.assertTrue(os.path.isfile(r["copia"]))
            con = sqlite3.connect(db)
            b = con.execute('select Body from "ListMgt::LmVersion"').fetchone()[0]
            rc = con.execute("select RenderCacheBA from Sm2TiItem").fetchone()[0]
            con.close()
            with open(os.path.join(M, "versao_rastreada.bin"), "rb") as fh:
                self.assertEqual(rm.zstd_abrir(b[1:]), fh.read())
            self.assertIn(ver.encode(), zlib.decompress(rc[4:]))


class TestPrmf(unittest.TestCase):
    def test_mascaras_das_duas_passadas(self):
        arqs = sorted(glob.glob(os.path.join(PASTA_PRMF, "[!.]*.prmf")))
        m = ppr.mascaras(arqs, 25, 1920, 1080)
        self.assertEqual((min(m), max(m), len(m)), (7, 278, 272))
        self.assertEqual(set(m[150]) <= {0, 255}, True)


if __name__ == "__main__":
    unittest.main()
