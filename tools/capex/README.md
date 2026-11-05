# /capex 빅테크 AI 설비투자 추적

공개 페이지: https://aicapex.sjoonkwon.com/capex

| 파일 | 역할 |
|---|---|
| `page.html` | 페이지 본문과 그림 코드(원래 Claude 대시보드용으로 쓴 것). 수정은 여기서 한다. |
| `build_capex.py` | `page.html`에 정적 런타임(`dash` 대체 스크립트), 머리말, 그림 n을 붙여 `public/capex.html`을 만든다. |
| `prepare_data.py` | 갱신 파이프라인의 `out/*.csv`를 `public/capex/data/<id>.csv`로 옮긴다. 7개사만 남긴다. |

## 월간 갱신 (매달 22일 예약 작업)
1. 파이프라인(`run_all.sh`)을 돌려 `out/`을 만든다.
2. `python3 tools/capex/prepare_data.py <out 폴더>`
3. 최신 완결 분기가 바뀌었으면 `page.html`에서 분기를 가리키는 문구를 고친다(파이프라인 README의 "페이지에서 분기를 가리키는 곳").
4. `python3 tools/capex/build_capex.py` 후 커밋·푸시. Cloudflare가 1분 안에 배포한다.

그림 n은 https://memsim.sjoonkwon.com/data/kr_customs_ytd.csv 를 읽는다(연구실 노트북이 매일 만들고, memsim의 `_headers`가 이 출처에만 CORS를 연다). 읽지 못하면 `public/capex/data/kr_customs.csv`(2026-11-05 고정, 같은 열 구성)로 그린다. 월간 갱신은 이 파일을 건드리지 않는다.
