@echo off
rem Duplo clique (Windows): gera os casos do pacote Base e confere cada arquivo.
rem A midia sai em saida\base\<caso>\ (pode apagar: este arquivo refaz).
cd /d "%~dp0"
set PYTHONPYCACHEPREFIX=%LOCALAPPDATA%\laboratorio-de-midia\pyc
set FALHOU=0
for %%R in (receitas\base\*.json) do (
  py -3 -m lab.gerar "%%R" --verificar || set FALHOU=1
)
echo.
if "%FALHOU%"=="0" (echo Tudo gerado e conferido. A midia esta em saida\base.) else (echo ALGO NAO CONFERIU - veja acima.)
pause
