@echo off
cd /d "%~dp0"
echo Vidalia Demo Analyzer - gerando o executavel (gratuito)...
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% -m pip install --upgrade pyinstaller
%PY% -m PyInstaller --noconfirm --onefile --windowed --name VidaliaDemoAnalyzer --icon vidalia\assets\vidalia.ico --add-data "vidalia\assets;vidalia\assets" --collect-submodules vidalia run_vidalia.py
echo.
echo Executavel gerado em dist\VidaliaDemoAnalyzer.exe
echo Codigo de verificacao SHA-256 (publique junto com o .exe):
certutil -hashfile dist\VidaliaDemoAnalyzer.exe SHA256
pause
