@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"
python -m thrilla %*
exit /b %ERRORLEVEL%

