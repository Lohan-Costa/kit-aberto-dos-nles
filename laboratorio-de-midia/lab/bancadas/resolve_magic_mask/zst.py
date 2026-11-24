import subprocess,tempfile,os
def comprimir(dados, nivel=3):
    """zstd como o Resolve: um quadro com o tamanho do conteúdo e SEM soma de verificação (cabeçalho 0x60/0x20)"""
    with tempfile.TemporaryDirectory() as d:
        a=os.path.join(d,"c"); open(a,"wb").write(dados)
        subprocess.run(["zstd","-q","-f",f"-{nivel}","--no-check",a,"-o",a+".zst"],check=True)
        return open(a+".zst","rb").read()
def abrir(z):
    return subprocess.run(["zstd","-dc"],input=z,capture_output=True,check=True).stdout
