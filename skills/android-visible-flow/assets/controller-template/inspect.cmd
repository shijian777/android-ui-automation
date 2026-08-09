@echo off
setlocal
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Runtime not found. Run setup.cmd first.
  exit /b 2
)
if "%~1"=="" (
  echo Usage: inspect.cmd DEVICE_SERIAL
  exit /b 2
)
"%PYTHON_EXE%" -m ticketflow --inspect --serial "%~1"
exit /b %errorlevel%
