using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.ServiceProcess;

namespace YourApp.Integration;

/// <summary>
/// WPF 시작 시 AiAgentApi Windows 서비스가 중지되어 있으면 시작합니다.
/// 배포 전에 관리자 PC에서 scripts/install_service_admin.cmd 로 서비스를 한 번 등록해야 합니다.
/// </summary>
public static class AgentApiServiceStarter
{
    /// <summary>windows_service.py 의 _svc_name_ 과 동일해야 합니다.</summary>
    public const string ServiceName = "AiAgentApi";

    /// <summary>
    /// 서비스가 없거나 시작 권한이 없으면 예외 없이 무시합니다(디버깅 로그만).
    /// 자동 시작이면 보통 이미 Running 입니다.
    /// </summary>
    public static void EnsureRunning(TimeSpan? waitUntilRunning = null)
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return;

        waitUntilRunning ??= TimeSpan.FromSeconds(45);

        try
        {
            using var ctl = new ServiceController(ServiceName);
            if (ctl.Status != ServiceControllerStatus.StopPending && ctl.Status != ServiceControllerStatus.Stopped)
                return;

            try
            {
                ctl.Start();
                ctl.WaitForStatus(ServiceControllerStatus.Running, waitUntilRunning.Value);
            }
            catch (InvalidOperationException ex)
            {
                Debug.WriteLine($"[AiAgentApi] 시작 실패(서비스 미설치 가능): {ex.Message}");
            }
            catch (System.ServiceProcess.TimeoutException ex)
            {
                Debug.WriteLine($"[AiAgentApi] 시작 대기 시간 초과: {ex.Message}");
            }
        }
        catch (InvalidOperationException ex)
        {
            Debug.WriteLine($"[AiAgentApi] 서비스 컨트롤러 생성 실패(미설치?): {ex.Message}");
        }
    }

    /// <summary>
    /// 현재 상태 반환 (서비스 없음 → null).
    /// </summary>
    public static ServiceControllerStatus? TryGetStatus()
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return null;

        try
        {
            using var ctl = new ServiceController(ServiceName);
            ctl.Refresh();
            return ctl.Status;
        }
        catch (InvalidOperationException)
        {
            return null;
        }
    }

    /// <summary>서비스가 없거나 Running이 아닐 때 안내 문구 (빈 문자열이면 OK).</summary>
    public static string GetStatusHint()
    {
        if (!RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            return string.Empty;

        var status = TryGetStatus();
        if (!status.HasValue)
            return $"API 서비스({ServiceName})가 설치되지 않은 것 같습니다. Python 쪽 scripts\\install_service_admin.cmd 를 관리자로 한 번 실행하세요.";

        return status.Value == ServiceControllerStatus.Running
            ? string.Empty
            : $"API 서비스({ServiceName}) 상태: {status.Value}. services.msc에서 시작하거나, install_service_admin.cmd로 다시 설치하세요.";
    }
}
