"""
Windows 서비스로 uvicorn(API 서버)을 기동합니다.

사전 준비 (관리자 PowerShell 또는 CMD):
  pip install pywin32
  cd /d <AI_Agent_Py 프로젝트 루트>

설치·시작:
  python windows_service.py install
  python windows_service.py start

중지·삭제:
  python windows_service.py stop
  python windows_service.py remove

환경 변수(선택): AGENT_API_HOST, AGENT_API_PORT — 프로젝트 루트의 .env 도 uvicorn 자식 프로세스에서 읽힙니다.

서비스 이름은 서비스 관리자에서 "AI Agent API (FastAPI)" 로 표시됩니다.
내부 이름(_svc_name_): AiAgentApi
"""

from __future__ import annotations

import codecs
import os
import subprocess
import sys
import threading
import time

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:
    win32event = None
    win32service = None
    win32serviceutil = None
    servicemanager = None

if win32serviceutil is not None:

    class AiAgentApiService(win32serviceutil.ServiceFramework):
        _svc_name_ = "AiAgentApi"
        _svc_display_name_ = "AI Agent API (FastAPI)"
        _svc_description_ = "LangGraph AI Agent HTTP API — WPF 등 클라이언트용."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.process: subprocess.Popen | None = None
            self._log_thread: threading.Thread | None = None
            self._log_stop = threading.Event()

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._log_stop.set()
            win32event.SetEvent(self.stop_event)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )

            host = os.environ.get("AGENT_API_HOST", "127.0.0.1")
            port = os.environ.get("AGENT_API_PORT", "8787")

            creationflags = 0
            if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW

            # pywin32 서비스 환경에서는 sys.executable 이 python.exe가 아니라
            # pythonservice.exe 로 나오는 경우가 많습니다. uvicorn은 python.exe로 실행해야 합니다.
            python_runner = getattr(sys, "_base_executable", None) or sys.executable
            if os.path.basename(python_runner).lower() == "pythonservice.exe":
                candidate = os.path.join(os.path.dirname(python_runner), "python.exe")
                if os.path.exists(candidate):
                    python_runner = candidate

            cmd = [
                python_runner,
                "-X",
                "utf8",
                "-m",
                "uvicorn",
                "api_server:app",
                "--host",
                host,
                "--port",
                str(port),
            ]

            env = os.environ.copy()
            env.setdefault("PYTHONUNBUFFERED", "1")
            # 서비스 환경에서도 stdout/stderr를 UTF-8로 강제 (한글 깨짐 방지)
            env.setdefault("PYTHONUTF8", "1")
            env.setdefault("PYTHONIOENCODING", "utf-8")

            log_dir = os.path.join(_PROJECT_ROOT, "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "service-uvicorn.log")

            def _decode_best_effort(b: bytes) -> str:
                # 서비스/파이썬/uvicorn이 어떤 인코딩으로 내보내든 최대한 읽을 수 있게 시도
                for enc in ("utf-8", "cp949", "utf-16-le", "utf-16", "latin-1"):
                    try:
                        return b.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return b.decode("utf-8", errors="replace")

            def _ts() -> str:
                return time.strftime("%Y-%m-%d %H:%M:%S")

            def _ensure_utf16le_bom(path: str) -> None:
                # 메모장이 안정적으로 인식하도록 UTF-16 LE + BOM으로 기록
                if not os.path.exists(path) or os.path.getsize(path) == 0:
                    with open(path, "wb") as f:
                        f.write(codecs.BOM_UTF16_LE)

            def _write_line_utf16le(path: str, text: str) -> None:
                # 항상 CRLF로 기록 (메모장 표시 호환)
                if not text.endswith("\r\n"):
                    text = text + "\r\n"
                with open(path, "ab") as f:
                    f.write(text.encode("utf-16-le", errors="replace"))

            def _start_log_thread(proc: subprocess.Popen):
                # stdout/stderr를 읽어서 한 줄 단위로 타임스탬프를 붙여 기록
                def _run():
                    _ensure_utf16le_bom(log_path)
                    _write_line_utf16le(log_path, "")
                    _write_line_utf16le(log_path, "=" * 80)
                    _write_line_utf16le(log_path, f"[START] {_ts()} pid={proc.pid}")
                    _write_line_utf16le(log_path, f"runner={python_runner}")
                    _write_line_utf16le(log_path, f"cmd={cmd}")
                    _write_line_utf16le(log_path, f"cwd={_PROJECT_ROOT}")
                    try:
                        assert proc.stdout is not None
                        for raw in iter(proc.stdout.readline, b""):
                            if self._log_stop.is_set():
                                break
                            line = _decode_best_effort(raw).rstrip("\r\n")
                            if line:
                                _write_line_utf16le(log_path, f"[{_ts()}] {line}")
                    except Exception as e:
                        _write_line_utf16le(log_path, f"[{_ts()}] [LOG-THREAD-ERROR] {e}")
                    finally:
                        _write_line_utf16le(log_path, f"[STOP] {_ts()} returncode={proc.poll()}")

                self._log_stop.clear()
                self._log_thread = threading.Thread(target=_run, name="uvicorn-log", daemon=True)
                self._log_thread.start()

            def start_process() -> subprocess.Popen:
                proc = subprocess.Popen(
                    cmd,
                    cwd=_PROJECT_ROOT,
                    creationflags=creationflags,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                _start_log_thread(proc)
                return proc

            try:
                self.process = start_process()
            except OSError as e:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_ERROR_TYPE,
                    servicemanager.PYS_SERVICE_STOPPED,
                    (self._svc_name_, f"uvicorn 시작 실패: {e}"),
                )
                return

            # uvicorn이 즉시 죽는 경우(모듈 없음, .env 없음, 키 없음 등) 자동 재시도
            restart_delays = [2, 5, 10, 20, 30]
            restart_attempt = 0

            while True:
                rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                if rc == win32event.WAIT_OBJECT_0:
                    break
                if self.process is not None and self.process.poll() is not None:
                    code = self.process.returncode
                    servicemanager.LogMsg(
                        servicemanager.EVENTLOG_WARNING_TYPE,
                        servicemanager.PYS_SERVICE_STOPPED,
                        (
                            self._svc_name_,
                            f"uvicorn 프로세스 종료됨 (코드 {code}). 로그: {log_path}",
                        ),
                    )
                    if restart_attempt >= len(restart_delays):
                        break
                    delay = restart_delays[restart_attempt]
                    restart_attempt += 1
                    time.sleep(delay)
                    try:
                        self.process = start_process()
                        continue
                    except OSError as e:
                        servicemanager.LogMsg(
                            servicemanager.EVENTLOG_ERROR_TYPE,
                            servicemanager.PYS_SERVICE_STOPPED,
                            (self._svc_name_, f"uvicorn 재시작 실패: {e}. 로그: {log_path}"),
                        )
                        break

            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self._log_stop.set()
            if self._log_thread is not None:
                self._log_thread.join(timeout=2)

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )

else:
    AiAgentApiService = None  # type: ignore[misc, assignment]


def main():
    if win32serviceutil is None or AiAgentApiService is None:
        print("pywin32 가 필요합니다: pip install pywin32", file=sys.stderr)
        sys.exit(1)
    win32serviceutil.HandleCommandLine(AiAgentApiService)


if __name__ == "__main__":
    main()
