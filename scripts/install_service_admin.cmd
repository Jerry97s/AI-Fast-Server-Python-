@echo off
chcp 65001 >nul
setlocal

:: 이 스크립트 위치: AI_Agent_Py\scripts\ → 프로젝트 루트는 한 단계 위
set "ROOT=%~dp0.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

cd /d "%ROOT%"

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo 관리자 권한이 필요합니다. UAC 창을 확인하세요.
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%ROOT%' -Verb RunAs"
  exit /b 0
)

where python >nul 2>&1
if %errorlevel% neq 0 (
  echo [오류] python 이 PATH에 없습니다.
  pause
  exit /b 1
)

echo [1/4] pywin32...
python -m pip install "pywin32>=307" -q
if %errorlevel% neq 0 (
  pause
  exit /b 1
)

echo [2/4] 서비스 등록 AiAgentApi...
python "%ROOT%\windows_service.py" install
if %errorlevel% neq 0 (
  pause
  exit /b 1
)

echo [3/4] 시작 유형 = 자동
sc config AiAgentApi start= auto

echo [4/4] 서비스 시작
python "%ROOT%\windows_service.py" start

echo.
echo 완료: http://127.0.0.1:8787/health
pause
endlocal
