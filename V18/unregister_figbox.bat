@echo off
REM Unregister .figbox file association. Run as Administrator.
echo Removing .figbox association ...
reg delete "HKCR\.figbox" /f >nul 2>&1
reg delete "HKCR\FigBox.Project" /f >nul 2>&1
echo Done.
pause
