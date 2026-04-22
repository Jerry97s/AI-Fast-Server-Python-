$ErrorActionPreference = "Stop"

$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$file = Join-Path $repoRoot "COMMIT_HISTORY.md"
if (!(Test-Path -LiteralPath $file)) {
  throw "COMMIT_HISTORY.md not found: $file"
}

$line = (git -C $repoRoot -c i18n.logOutputEncoding=utf-8 log -1 --date=short --pretty=format:"- %ad %h %s").Trim()
if ([string]::IsNullOrWhiteSpace($line)) {
  throw "git log returned empty"
}

$content = Get-Content -LiteralPath $file -Raw -Encoding UTF8

$marker = "## 최근 커밋"
$idx = $content.IndexOf($marker)
if ($idx -lt 0) {
  # 없으면 파일 끝에 섹션 생성
  $content = $content.TrimEnd() + "`r`n`r`n" + $marker + "`r`n"
  $idx = $content.IndexOf($marker)
}

# marker 줄 끝 다음 위치
$after = $content.IndexOf("`n", $idx)
if ($after -lt 0) {
  $after = $idx + $marker.Length
} else {
  $after = $after + 1
}

if ($content -match [regex]::Escape($line)) {
  return
}

$beforeText = $content.Substring(0, $after)
$afterText = $content.Substring($after)
$newContent = $beforeText + "`n" + $line + "`n" + $afterText

Set-Content -LiteralPath $file -Encoding UTF8 -NoNewline -Value $newContent
Write-Host ("Updated COMMIT_HISTORY.md: " + $line)

