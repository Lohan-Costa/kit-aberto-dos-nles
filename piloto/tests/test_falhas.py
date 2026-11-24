"""`piloto.falhas`: as falhas registradas pelo sistema depois de uma marca (o .ips do Mac)."""
import json, os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from piloto import falhas


def test_ips_novo_e_filtro():
    with tempfile.TemporaryDirectory() as d:
        velho = os.path.join(d, "Velho-2026.ips")
        open(velho, "w").write("{}\n{}")
        os.utime(velho, (time.time() - 3600,) * 2)
        marca = falhas.agora()
        novo = os.path.join(d, "AvidMediaComposer-2026.ips")
        with open(novo, "w") as fh:
            fh.write(json.dumps({"app_name": "AvidMediaComposer", "bug_type": "309"}) + "\n")
            fh.write(json.dumps({"exception": {"type": "EXC_CRASH", "signal": "SIGABRT"}}))
        orig, falhas._pastas = falhas._pastas, lambda: [d]
        try:
            if falhas.SISTEMA != "macos":
                return
            achadas = falhas.desde(marca)
            assert [f["app"] for f in achadas] == ["AvidMediaComposer"] and achadas[0]["motivo"] == "SIGABRT", achadas
            assert falhas.desde(marca, ["Baselight"]) == []
            assert "caiu às" in falhas.frase(achadas[0])
        finally:
            falhas._pastas = orig


if __name__ == "__main__":
    test_ips_novo_e_filtro()
    print("ok")
