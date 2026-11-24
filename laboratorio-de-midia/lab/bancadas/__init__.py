"""Bancadas: o laboratório operando os NLEs (o Claude opera; o autor dá a missão).

Cada bancada tem duas metades:
- a que roda DENTRO do NLE (`resolve.py`: só a API do Resolve + json; sem ffmpeg, sem o resto do lab);
- a que confere o que o NLE mostrou (`conferir.py`: lê os stills e os renders com o `lab.ler`).
"""
