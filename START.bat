@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 scripts\start_local.py %*
  goto :finish
)
where python >nul 2>&1
if %ERRORLEVEL%==0 (
  python scripts\start_local.py %*
  goto :finish
)

echo Нужен Python 3 в PATH ^(команда py или python^).
pause
exit /b 1

:finish
if errorlevel 1 (
  echo.
  pause
)
exit /b %ERRORLEVEL%
