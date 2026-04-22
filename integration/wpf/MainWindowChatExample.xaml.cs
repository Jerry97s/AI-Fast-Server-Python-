// WPF MainWindow.xaml.cs에 맞게 복사·수정하세요.
// Xaml: TextBox UserInputTextBox, TextBlock 또는 TextBox ReplyTextBlock, Button SendButton

using System;
using System.Threading.Tasks;
using System.Windows;
using YourApp.Integration;

namespace YourApp;

public partial class MainWindow : Window
{
    private readonly AiAgentClient _agent = new("http://127.0.0.1:8787/");
    private readonly string _sessionThreadId = Guid.NewGuid().ToString("N");

    public MainWindow()
    {
        InitializeComponent();
        Loaded += (_, _) =>
        {
            ReplyTextBlock.Text = "Python API가 http://127.0.0.1:8787 에서 실행 중인지 확인하세요.";
        };
    }

    private async void SendButton_Click(object sender, RoutedEventArgs e)
    {
        var text = UserInputTextBox.Text?.Trim();
        if (string.IsNullOrEmpty(text)) return;

        SendButton.IsEnabled = false;
        try
        {
            var reply = await _agent.SendMessageAsync(text, _sessionThreadId).ConfigureAwait(true);
            ReplyTextBlock.Text = reply;
        }
        catch (Exception ex)
        {
            ReplyTextBlock.Text = "오류: " + ex.Message;
        }
        finally
        {
            SendButton.IsEnabled = true;
        }
    }

    protected override void OnClosed(EventArgs e)
    {
        _agent.Dispose();
        base.OnClosed(e);
    }
}
