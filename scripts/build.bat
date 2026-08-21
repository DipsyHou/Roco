@echo off
setlocal EnableExtensions

REM One-shot build: desktop client, online client, server GUI.
REM Run from repo root: scripts\build.bat

cd /d "%~dp0.."
set "ROOT=%CD%"
set "ICON_PATH=%ROOT%\assets\seed.ico"

echo Project root: %ROOT%

if not exist "%ROOT%\.venv" (
  py -m venv "%ROOT%\.venv"
)

call "%ROOT%\.venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install pyinstaller pillow websockets >nul

taskkill /IM RocoDesktop.exe /F >nul 2>nul
taskkill /IM RocoOnlineClient.exe /F >nul 2>nul
taskkill /IM RocoOnlineServer.exe /F >nul 2>nul

if exist "%ROOT%\build" rmdir /s /q "%ROOT%\build"
if exist "%ROOT%\dist" rmdir /s /q "%ROOT%\dist"
del /q "%ROOT%\RocoDesktop.spec" 2>nul
del /q "%ROOT%\RocoOnlineClient.spec" 2>nul
del /q "%ROOT%\RocoOnlineServer.spec" 2>nul

set "ICON_ARG="
if exist "%ICON_PATH%" (
  set "ICON_ARG=--icon %ICON_PATH%"
) else (
  echo Icon not found, building without custom icon.
)

set "PYI_PATHS=--paths %ROOT%"
set "COMMON_DATA=--add-data %ROOT%\assets;assets"
set "ROCO_COLLECT=--collect-submodules roco"
set "WS_CLIENT=--hidden-import websockets --hidden-import websockets.client --hidden-import websockets.exceptions"
set "WS_SERVER=--hidden-import websockets --hidden-import websockets.server --hidden-import websockets.exceptions --collect-submodules roco.server"

echo.
echo [1/3] RocoDesktop.exe (local hot-seat)...
pyinstaller --noconfirm --windowed --onefile %PYI_PATHS% %ROCO_COLLECT% --name RocoDesktop %COMMON_DATA% %ICON_ARG% "%ROOT%\scripts\pyi_desktop_main.py"
if errorlevel 1 goto :fail

echo.
echo [2/3] RocoOnlineClient.exe (online client)...
pyinstaller --noconfirm --windowed --onefile %PYI_PATHS% %ROCO_COLLECT% --name RocoOnlineClient %COMMON_DATA% %WS_CLIENT% %ICON_ARG% "%ROOT%\scripts\pyi_online_client_main.py"
if errorlevel 1 goto :fail

echo.
echo [3/3] RocoOnlineServer.exe (server GUI)...
pyinstaller --noconfirm --windowed --onefile %PYI_PATHS% %ROCO_COLLECT% --name RocoOnlineServer %WS_SERVER% %ICON_ARG% "%ROOT%\scripts\pyi_server_main.py"
if errorlevel 1 goto :fail

echo.
echo Build complete:
echo   %ROOT%\dist\RocoDesktop.exe
echo   %ROOT%\dist\RocoOnlineClient.exe
echo   %ROOT%\dist\RocoOnlineServer.exe
goto :done

:fail
echo.
echo Build failed.
pause
exit /b 1

:done
pause
