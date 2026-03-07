@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "EXE_PATH=%PROJECT_ROOT%\dist\FL-Lingo\FL-Lingo.exe"

if exist "%EXE_PATH%" goto have_exe

set "EXE_PATH=%PROJECT_ROOT%\FL-Lingo.exe"
if exist "%EXE_PATH%" goto have_exe

echo FL Lingo executable not found.
echo Expected at:
echo   %PROJECT_ROOT%\dist\FL-Lingo\FL-Lingo.exe
echo or
echo   %PROJECT_ROOT%\FL-Lingo.exe
exit /b 1

:have_exe
reg add "HKCU\Software\Classes\.FLLingo" /ve /d "FLLingo.Project" /f >nul
reg add "HKCU\Software\Classes\FLLingo.Project" /ve /d "FL Lingo Project" /f >nul
reg add "HKCU\Software\Classes\FLLingo.Project\DefaultIcon" /ve /d "\"%EXE_PATH%\",0" /f >nul
reg add "HKCU\Software\Classes\FLLingo.Project\shell\open\command" /ve /d "\"%EXE_PATH%\" \"%%1\"" /f >nul

echo .FLLingo is now associated with:
echo   %EXE_PATH%
exit /b 0
