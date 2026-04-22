## 커밋 내역 (프로젝트 기록)

- **GitHub 커밋 페이지**: `https://github.com/Jerry97s/AI-Fast-Server-Python-/commits/master`

이 문서는 “작업 요약(사람이 읽기 쉬운 형태)”을 남기기 위한 페이지입니다.  
정확한 변경 파일/라인은 GitHub 커밋 페이지에서 확인하세요.

---

## 자동 기록(권장)

커밋할 때마다 이 파일에 내역을 남기려면 아래 중 하나를 사용합니다.

- **수동(가장 단순)**: 커밋 후 `scripts/update_commit_history.ps1` 실행
- **자동(권장)**: git `post-commit` 훅으로 스크립트를 연결 (아래 가이드 참고)

### post-commit 훅 설정(로컬 개발환경)

1) PowerShell에서 저장소 루트에서 실행:

```powershell
Copy-Item -Force .\scripts\post-commit.ps1 .\.git\hooks\post-commit
```

2) 그 다음부터 커밋하면 자동으로 `COMMIT_HISTORY.md`가 갱신됩니다.

---

## 최근 커밋

- 2026-04-22 2944756 feat: 개인화 규칙/기억 주입
- 2026-04-22 56a2d2d docs: README에 프로젝트 분석 결과 반영 (구조·아키텍처·수준 점수·개선 과제)
- 2026-04-22 f5bb299 docs: 프로젝트 구조·장단점·개선점·수준 점수 분석 문서 추가
- 2026-04-22 54f3ba9 Initial commit: AI Fast Server Python project
