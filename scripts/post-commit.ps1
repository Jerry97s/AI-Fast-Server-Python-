# git post-commit hook (PowerShell)
# 커밋 직후 COMMIT_HISTORY.md를 갱신합니다.

try {
  $repoRoot = (git rev-parse --show-toplevel).Trim()
  & (Join-Path $repoRoot "scripts\update_commit_history.ps1") | Out-Null
} catch {
  # 훅에서 실패해도 커밋을 망치지 않도록 조용히 무시
}

