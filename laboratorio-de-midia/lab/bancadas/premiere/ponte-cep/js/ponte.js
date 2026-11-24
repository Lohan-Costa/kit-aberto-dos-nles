// PONTE DO LABORATÓRIO — servidor HTTP no 127.0.0.1 que executa ExtendScript no Premiere.
// Segurança (banco, seguranca/README.md): porta aleatória só no loopback; token de 32 bytes num arquivo
// 0600 que só o usuário lê; pedido com header Origin é recusado (navegador = página da web, nunca o lab);
// Host conferido por IGUALDADE. Instrumento de bancada: o lab instala, usa e remove.
(function () {
  var http = require("http"), crypto = require("crypto"), fs = require("fs"), path = require("path"), os = require("os");
  var cep = window.__adobe_cep__;
  var pasta = process.platform === "win32"
    ? path.join(process.env.LOCALAPPDATA || os.homedir(), "laboratorio-de-midia")
    : path.join(os.homedir(), "Library", "Application Support", "laboratorio-de-midia");
  try { fs.mkdirSync(pasta, { recursive: true }); } catch (e) {}
  var token = crypto.randomBytes(32).toString("hex");
  var log = path.join(pasta, "ponte-premiere.log");
  function anota(t) { try { fs.appendFileSync(log, new Date().toISOString() + " " + t + "\n"); } catch (e) {} }

  var servidor = http.createServer(function (req, res) {
    var porta = servidor.address().port;
    function responde(cod, corpo) {
      res.writeHead(cod, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(corpo));
    }
    if (req.headers.origin) return responde(403, { erro: "origem recusada" });
    if (req.headers.host !== "127.0.0.1:" + porta) return responde(403, { erro: "host recusado" });
    if (req.headers["x-lab-token"] !== token) return responde(401, { erro: "token" });
    if (req.method !== "POST" || req.url !== "/executar") return responde(404, { erro: "rota" });
    var partes = [];
    req.on("data", function (c) { partes.push(c); });
    req.on("end", function () {
      var codigo = Buffer.concat(partes).toString("utf8");
      var t0 = Date.now();
      cep.evalScript("$._lab_executar(" + JSON.stringify(codigo) + ")", function (saida) {
        responde(200, { saida: saida, ms: Date.now() - t0 });
      });
    });
  });
  servidor.listen(0, "127.0.0.1", function () {
    var porta = servidor.address().port;
    cep.evalScript("app.version", function (versao) {
      var arq = path.join(pasta, "ponte-premiere.json");
      fs.writeFileSync(arq, JSON.stringify({ porta: porta, token: token, premiere: versao, pid: process.pid,
                                              iniciada: new Date().toISOString() }), { mode: 384 });
      try { fs.chmodSync(arq, 384); } catch (e) {}
      anota("ponte no ar: 127.0.0.1:" + porta + " Premiere " + versao);
    });
  });
})();
