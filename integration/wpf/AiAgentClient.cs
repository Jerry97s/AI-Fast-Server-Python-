using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace YourApp.Integration;

/// <summary>
/// Python AI Agent API (api_server.py)와 통신하는 최소 클라이언트.
/// WPF 프로젝트에 이 파일을 복사한 뒤 네임스페이스만 맞추면 됩니다.
/// </summary>
public sealed class AiAgentClient : IDisposable
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private readonly HttpClient _http;
    private bool _disposed;

    public AiAgentClient(string baseUrl = "http://127.0.0.1:8787/", HttpMessageHandler? handler = null)
    {
        if (string.IsNullOrWhiteSpace(baseUrl))
            throw new ArgumentException("baseUrl is required", nameof(baseUrl));

        if (!baseUrl.EndsWith('/'))
            baseUrl += "/";

        _http = handler is null ? new HttpClient { BaseAddress = new Uri(baseUrl) } : new HttpClient(handler) { BaseAddress = new Uri(baseUrl) };
        _http.Timeout = TimeSpan.FromMinutes(5);
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _http.Dispose();
    }

    /// <param name="userMessage">사용자 입력</param>
    /// <param name="threadId">대화 구분(한 창 = 한 ID, 또는 사용자 ID). null이면 "wpf-default".</param>
    public async Task<string> SendMessageAsync(
        string userMessage,
        string? threadId = null,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(userMessage))
            throw new ArgumentException("message is required", nameof(userMessage));

        var req = new ChatRequestDto
        {
            Message = userMessage,
            ThreadId = string.IsNullOrEmpty(threadId) ? "wpf-default" : threadId,
        };

        var json = JsonSerializer.Serialize(req, JsonOptions);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var response = await _http
            .PostAsync("v1/chat", content, cancellationToken)
            .ConfigureAwait(false);

        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
            throw new AiAgentApiException($"HTTP {(int)response.StatusCode}: {body}");

        var dto = JsonSerializer.Deserialize<ChatResponseDto>(body, JsonOptions);
        if (dto?.Reply is null)
            throw new AiAgentApiException("Invalid response: missing reply");

        return dto.Reply;
    }

    private sealed class ChatRequestDto
    {
        [JsonPropertyName("message")]
        public string Message { get; set; } = "";

        [JsonPropertyName("thread_id")]
        public string ThreadId { get; set; } = "wpf-default";
    }

    private sealed class ChatResponseDto
    {
        [JsonPropertyName("reply")]
        public string Reply { get; set; } = "";

        [JsonPropertyName("thread_id")]
        public string ThreadId { get; set; } = "";
    }
}

public sealed class AiAgentApiException : Exception
{
    public AiAgentApiException(string message) : base(message) { }
}
