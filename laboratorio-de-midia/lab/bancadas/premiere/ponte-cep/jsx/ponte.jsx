// PONTE DO LABORATÓRIO — o lado ExtendScript (ES3). Executa o código recebido e devolve SEMPRE uma string
// JSON {ok, valor | erro, linha}. O JSON global do ExtendScript não é garantido (banco, api-extendscript.md):
// serializador próprio, pequeno.
if (typeof $._lab_json !== "function") {
    $._lab_json = function (v) {
        if (v === null || v === undefined) return "null";
        var t = typeof v;
        if (t === "number") return isFinite(v) ? String(v) : "null";
        if (t === "boolean") return v ? "true" : "false";
        if (t === "string") {
            return '"' + v.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n")
                          .replace(/\r/g, "\\r").replace(/\t/g, "\\t") + '"';
        }
        if (v instanceof Array) {
            var a = [];
            for (var i = 0; i < v.length; i++) a.push($._lab_json(v[i]));
            return "[" + a.join(",") + "]";
        }
        if (t === "object") {
            var o = [];
            for (var k in v) { if (v.hasOwnProperty(k)) o.push($._lab_json(String(k)) + ":" + $._lab_json(v[k])); }
            return "{" + o.join(",") + "}";
        }
        return $._lab_json(String(v));
    };
    $._lab_executar = function (codigo) {
        try {
            var valor = eval(codigo);
            return $._lab_json({ ok: true, valor: valor });
        } catch (e) {
            return $._lab_json({ ok: false, erro: String(e), linha: e.line });
        }
    };
}
