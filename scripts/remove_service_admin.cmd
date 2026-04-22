@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
cd /d "%ROOT%"

net session >nul 2>&1
if %errorlevel% neq 0 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%ROOT%' -Verb RunAs"
  exit /b 0
)

where python >nul 2>&1
if %errorlevel% neq 0 (
  echo Python 없음 — net으로만 중지 후 제거 시도
  net stop AiAgentApi 2>nul
  sc delete AiAgentApi 2>nul
  pause
  exit /b 0
)

python "%ROOT%\windows_service.py" stop
python "%ROOT%\windows_service.py" remove
echo 제거 완료
pause
endlocal
