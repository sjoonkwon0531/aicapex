# 빅테크 AI 투자 시뮬레이터

https://aicapex.sjoonkwon.com

권석준(성균관대학교)의 시나리오 시뮬레이터 세 개와 허브 페이지입니다.

| 경로 | 파일 | 내용 |
|---|---|---|
| `/` | `public/index.html` | 허브 |
| `/hyperscaler` | `public/hyperscaler.html` | 하이퍼스케일러 주가 시뮬레이터 |
| `/google` | `public/google.html` | 구글 양다리 전략 시뮬레이터 |
| `/commerce` | `public/commerce.html` | 에이전트 커머스 시뮬레이터 |

## 배포
`main` 브랜치에 커밋하면 Cloudflare Workers가 `wrangler.jsonc` 설정으로 `public/` 폴더를 배포합니다. 빌드 단계는 없습니다.

## 고칠 때
- 페이지는 `public/` 안의 HTML을 직접 고칩니다. 각 파일은 외부 의존성(d3, Google Fonts)만 CDN에서 불러오는 단일 파일입니다.
- 없는 주소는 `public/404.html`을 보여 줍니다.
- 새 페이지를 더하면 `public/sitemap.xml`에도 주소를 넣습니다.
