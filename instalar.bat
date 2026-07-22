@echo off
color 0B
echo ===================================================
echo   Instalador Automatico - Extractor de Instagram
echo ===================================================
echo.
echo [1/3] Instalando dependencias necesarias (esto puede tardar unos minutos)...
pip install instaloader selenium webdriver-manager flask customtkinter

echo.
echo [2/3] Creando accesos directos en tu Escritorio...

set SCRIPT="%TEMP%\crear_accesos_%RANDOM%.vbs"

:: -- Acceso Directo: Escritorio --
echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
echo sLinkFile = "%USERPROFILE%\Desktop\Extractor de Seguidores (Escritorio).lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.TargetPath = "pythonw.exe" >> %SCRIPT%
echo oLink.Arguments = """%~dp0gui_app.py""" >> %SCRIPT%
echo oLink.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink.Description = "Abre la interfaz de escritorio del Extractor" >> %SCRIPT%
echo oLink.IconLocation = "%SystemRoot%\System32\shell32.dll,264" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

:: -- Lanzador para la Web --
:: Creamos un pequeño bat oculto o directo
set LAUNCHER="%~dp0iniciar_web.bat"
echo @echo off > %LAUNCHER%
echo echo Iniciando servidor, por favor no cierres esta ventana... >> %LAUNCHER%
echo start http://127.0.0.1:5000 >> %LAUNCHER%
echo python app.py >> %LAUNCHER%

:: -- Acceso Directo: Web --
echo sLinkFile2 = "%USERPROFILE%\Desktop\Extractor de Seguidores (Web).lnk" >> %SCRIPT%
echo Set oLink2 = oWS.CreateShortcut(sLinkFile2) >> %SCRIPT%
echo oLink2.TargetPath = """%~dp0iniciar_web.bat""" >> %SCRIPT%
echo oLink2.WorkingDirectory = "%~dp0" >> %SCRIPT%
echo oLink2.Description = "Abre la interfaz Web premium del Extractor" >> %SCRIPT%
echo oLink2.IconLocation = "%SystemRoot%\System32\shell32.dll,14" >> %SCRIPT%
echo oLink2.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%

echo.
echo [3/3] ¡Instalacion Completada!
echo.
echo Se han creado DOS iconos en tu Escritorio:
echo 1. Extractor de Seguidores (Escritorio) - Interfaz en ventana.
echo 2. Extractor de Seguidores (Web) - Interfaz Premium en el navegador.
echo.
echo Ya puedes cerrar esta ventana y usar los iconos.
pause
