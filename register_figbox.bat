@echo off
REM Register .figbox -> open with this V17 source tree (for development).
REM Production users should use the version generated in dist/ after running
REM build_exe_v17.py. Run THIS file as Administrator.
setlocal
set HERE=%~dp0
set RUN_PY=%HERE%run_v17.py
where pythonw >nul 2>&1
if %errorlevel% neq 0 (
  echo [Error] pythonw.exe not found in PATH.
  pause & exit /b 1
)
for /f "delims=" %%i in ('where pythonw') do set PYW=%%i & goto :found
:found
echo Registering .figbox -> %PYW% %RUN_PY%
reg add "HKCR\.figbox" /ve /d "FigBox.Project" /f >nul
reg add "HKCR\FigBox.Project" /ve /d "FigBox Academic Figure Project" /f >nul
reg add "HKCR\FigBox.Project\shell\open\command" /ve /d "\"%PYW%\" \"%RUN_PY%\" \"%%1\"" /f >nul
echo Done. You can now double-click .figbox files.
pause
