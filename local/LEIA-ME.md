# local/ — a camada privada

Tudo o que é desta pessoa e deste ambiente fica aqui, e o `.gitignore` impede que vá ao Git: o diagnóstico da máquina,
casos de produções reais, nomes de clientes e de pessoas, caminhos, fotos de tela, o `HANDOFF.md` das sessões.

A IA consulta as duas camadas — o banco público (`bancodedadosnles/`) e esta. Ao contribuir com o kit, ela generaliza e
anonimiza o que veio daqui, mostra o que vai sair e só envia com o "pode enviar" da pessoa (skill `ciclo-contribuir`).

Sugestão de arrumação (a IA cria conforme precisar):

```
local/
├─ HANDOFF.md          o que foi feito, o que falta (a próxima sessão começa por ele)
├─ diagnostico.md      a máquina: sistema, programas e versões, o que passou no laboratório
├─ descobertas.md      o que se mediu aqui e ainda não foi ao banco (com confiança, versão e sistema)
└─ producoes/<nome>/   casos reais, só desta máquina
```
