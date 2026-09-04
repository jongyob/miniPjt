# CLAUDE.md — 코드 품질 리포트 Agent (3일 미니PJT)

이 폴더(`mini-pjt_이종엽/`)는 "코드 품질 리포트 Agent" 3일 미니PJT의 제출 폴더입니다.
아래는 이후 모든 작업(특히 번호 단위로 제공되는 스크립트)이 지켜야 할 고정 컨텍스트입니다.

## 0. 원본 문서 (Source of Truth)

- 전체 설계(이상형, 기간 제약 없음):
  `c:\Users\SDS\Desktop\script\코드품질점검_Agent_전체설계.md`
- 3일 실행 계획(실제로 지켜야 하는 기준):
  `c:\Users\SDS\Desktop\script\코드품질점검_Agent_3일_미니PJT_계획.md`
- 서비스 기획 문서(제출 규약 0-3절, 이 폴더 안):
  [`SERVICE.md`](./SERVICE.md) — 사용자·문제·가치, 확장 관점, 서비스 정책(가드레일 요약),
  성공 기준(통과율 목표치)은 이 문서가 원본입니다. 이 CLAUDE.md는 그 내용을 다시 쓰지 않고
  필요할 때 링크만 겁니다.

**우선순위**: 두 문서가 충돌하면 항상 **3일 계획 문서가 이깁니다.** 전체설계 문서는 "언젠가
다 만들면 이런 모습"이라는 지도일 뿐이고, 3일 범위에서 무엇을 하고 무엇을 뺄지는 계획
문서의 1·2·10절(제약 조건)이 그 지도를 잘라낸 결과입니다. 두 문서 중 하나라도 다시 읽어야
할 상황이면 계획 문서를 먼저 봅니다.

## 1. 작업 진행 방식 (★중요)

- 이제부터 실제 구현은 **계획 문서 5절("3일 시간표")에 번호가 매겨진 항목 단위로** 스크립트
  형태로 제공됩니다(예: "1일차 2번", "2일차 5번"). 매번 이 CLAUDE.md와 두 원본 문서 전체를
  다시 설명하지 않을 것이므로, 아래 요약된 제약을 스스로 적용해야 합니다.
- 각 번호 항목을 구현할 때 지켜야 할 것:
  1. 그 항목이 속한 일차·순서를 벗어나 앞서가지 않습니다(예: 1일차 항목을 처리하면서 2일차의
     Supervisor 조립까지 미리 만들지 않음). 단, 이미 끝난 이전 번호들이 만들어 둔 파일/함수
     시그니처는 재사용·확장합니다.
  2. 항목 설명에 명시된 산출물(파일 경로, 함수명, 확인 기준)을 정확히 맞춥니다. 계획 문서
     5절의 각 일차 끝에 있는 "확인" 문장이 그 항목(들)의 완료 기준입니다.
  3. 아래 2~7절의 고정 제약(폴더 구조·API 스펙·조건 1~10·DoD)과 상충하지 않는지 항상
     교차 확인합니다. 상충하면 계획 문서 쪽을 따릅니다.
  4. 범위를 임의로 넓히지 않습니다 — 3-2절처럼 "있으면 좋을 것 같은" 기능(연결점 요약,
     다중 태그, 스케줄러 구현, Sonar/CVE, test_gen_agent 등, 6절 "로드맵으로 이동" 참고)은
     명시적으로 요청받기 전까지 추가하지 않습니다.

### 코드 작성 규칙

- **파일 하나에 한 가지 역할만** 둡니다 — 예: `tools.py` 안에서도 도구 실행(어댑터)과
  리포트 저장 같은 서로 다른 책임을 한 파일에 섞지 않습니다.
- 함수와 도구(LangChain 도구 등)에는 **한국어 docstring**을 씁니다.
- 비밀 값(API 키·자격증명)은 `.env`에서 읽고 코드에 직접 적지 않습니다(4절 "환경변수" 참고).
- **요청하지 않은 파일을 새로 만들지 않습니다.**
- **기존 파일을 통째로 다시 쓰지 않고, 바뀐 부분만 고칩니다.**

## 2. 폴더 구조 / API 스펙 (고정, 임의 변경 금지)

```text
mini-pjt_이종엽/
├── src/
│   ├── agent.py        # Supervisor 그래프 (3개 전문 Agent 병렬 조사 + 취합) + Finding 모델
│   ├── tools.py         # 언어 어댑터(vue3_adapter/java_lite_adapter/python_adapter) + db_adapter(10-B절)/pentest·load-test 함수(10-C절, 확장 phase) + 도메인 도구
│   ├── retriever.py     # RAG 파이프라인 (Day2 패턴)
│   ├── report.py        # (신규, 2일차 3번) Finding 리스트 -> report.md/report.json 저장
│   ├── config.py        # (신규, 확장 phase 준비) config.yaml 로더 — 점검 대상 루트(`source`)/제외 언어(`exceptLanguages`, 10-F절) + DB 설정(10-B/10-D절) + load_profile.yaml 로더(10-B절) + live_probe 플래그(10-C절)
│   ├── static/
│   │   └── index.html   # (신규, 10-G절, 확장 phase) 실행 버튼 + 실시간 진행률/결과 UI — GET /가 그대로 서빙
│   └── api.py           # POST /query 엔드포인트 (FastAPI, 127.0.0.1 바인딩) + GET //POST /scan/GET /scan/{job_id}(10-G절, API 스펙 밖 UI 편의 엔드포인트)
├── data/                 # RAG 대상 가이드 문서 + 점검 대상 더미 소스(sample_vue3_app/sample_java_app(+ src/main/resources/mapper/OrderMapper.xml, 10-E절)/sample_python_app) + sample_db/schema.sql(10-B절) + load_profile.yaml(10-B절) + staging_app/app.py(10-C절, 확장 phase)
├── evaluation/
│   ├── test_queries.csv     # id,category,input,expected_traits,forbidden,expected_tools,note
│   ├── round1_report.md     # 1차 자체평가 (2일차 종료 시점)
│   └── round2_report.md     # 2차 자체평가 (3일차, 개선 후)
├── SERVICE.md            # 사용자/문제/가치, 확장 관점, 도구/데이터, 서비스 정책, 성공 기준
├── Dockerfile
├── requirements.txt
├── README.md             # 0-5절 템플릿 (아래 5절 참고)
├── run.sh                # 선택
├── config.yaml           # (신규, 0-1절 목록 외 추가) 점검 대상 루트(`source`)+제외 언어(`exceptLanguages`, 10-F절)+DB 설정(10-D절)+live_probe(10-C절) — 전체설계 11-3절/12절
└── reports/              # (신규, 0-1절 목록 외 추가) report.md/report.json(최신 사본) + report_<타임스탬프>.md/.json(실행마다 쌓이는 이력, 10-H절)
```

API 스펙(고정):

```text
POST /query
Body: {"question": "사용자 질의"}
Response: {"answer": "...", "contexts": [{"doc_id","text"}], "trace": [{"step","input","output"}]}
```

- `question`은 순수 질문("vue3-app 보안 취약점 알려줘")뿐 아니라 실행 요청("vue3 프로젝트
  보안 점검해줘")도 될 수 있습니다(계획 조건 6). 어느 쪽인지는 Supervisor가 질문 성격을 보고
  라우팅해서 구분하며, 별도의 명령/질의 API를 나누지 않습니다.
- `contexts`는 Finding과 RAG 문서 근거를 **같은 `{doc_id, text}` 모양으로 통일**해 담습니다.
  Finding 항목은 `doc_id`에 Finding ID(예: `SEC-1`)를, `text`에 `summary`+`detail` 요약을
  넣고, RAG 문서 항목은 그 문서의 `doc_id`/검색된 텍스트 조각을 그대로 넣습니다.
- **(신규, 2026-09-03, 10-G절)** 이 스펙은 그대로 고정이지만, `GET /`(실행 UI)·
  `POST /scan`·`GET /scan/{job_id}`가 그 밖에 추가됐습니다 — 터미널 없이 브라우저로 같은
  Supervisor를 실행하기 위한 UI 편의 엔드포인트로, `POST /query`의 요청/응답 모양은
  전혀 바뀌지 않습니다.

`data/` 안에 있던 `agent.py`/`api.py`/`retriever.py`/`tools.py`는 초기 스캐폴딩 흔적(전부
빈 파일)이었으며 삭제했습니다 — 실제 구현물은 전부 `src/` 아래에 만듭니다.

### 1일차 진행 상황 — 전부 완료, 실측 검증 완료

**(결정) `_default_llm()`을 `agent.py`가 아니라 `tools.py`에 둡니다** — Supervisor
(`agent.py`)가 결국 어댑터(`tools.py`)를 임포트해야 하는데, `java_lite_adapter`도 LLM이
필요해서 `_default_llm()`을 `agent.py`에 두면 `agent.py → tools.py → agent.py` 순환
임포트가 생기기 때문입니다.

| 번호 | 산출물 | 상태·핵심 사실 |
|---|---|---|
| 1 | `src/__init__.py`, `src/tools.py`(`_default_llm()`), `src/api.py`(`POST /query` 스켈레톤) | 완료. `uvicorn --host 127.0.0.1`로 기동 후 `curl`로 `answer`/`contexts`/`trace` 응답 확인, `0.0.0.0` 경유 접근 불가(127.0.0.1 전용 바인딩)까지 검증 |
| 2 | `Vue3Adapter`(`vue3_adapter`) — `npm audit`/`eslint` 실전 연동 | 완료. **security 8건**(npm audit lodash 취약점 6개 + `no-eval` + `vue/no-v-html`), **error 1건**(`no-unused-vars`), **performance 0건**. `node_modules` 없으면 자동 `npm install`, 캐싱 확인(첫 호출 3.88초→두 번째 0초). Windows `npm`/`npx`는 `.cmd`라서 `shutil.which()`로 실제 경로를 찾아 `shell=False`로 실행(`shell=True`+리스트 인자는 POSIX에서 첫 인자만 셸 명령으로 쓰이는 흔한 함정이라 피함) |
| 3 | `Finding`/`ReferenceDoc` 모델, `mask_pii()`, `raw_findings_to_findings()` (`src/agent.py`) | 완료. Finding 모델은 `agent.py`에 위치(4번 Agent 3개와 Supervisor가 이 파일에 조립되므로). 심각도 정규화(`npm audit`의 `moderate`→`medium` 등) 실측 확인. `mask_pii`가 `AwsConfig.java`의 가짜 AWS 키·시크릿 대입문을 정확히 마스킹하는 것 확인(리포트 저장 직전에도 재사용 예정) |
| 4 | `make_security_agent`/`make_error_agent`/`make_performance_agent` (`src/agent.py`) | 완료, 실제 호출 검증됨. **버그**: `langchain-core==0.3.86`(ragas 호환을 위해 고정한 구세대)의 스트리밍 병렬 도구 호출 병합 버그(`merge_dicts()`가 병렬 `tool_use` 블록을 잘못 합침 — langchain-ai/langchain#34807과 같은 계열)로 `ValidationException: toolUse.name ...`. **수정**: `_default_llm()`에 `additional_model_request_fields={"tool_choice": {"type": "auto", "disable_parallel_tool_use": True}}` 추가(우리 Agent는 도구를 1개씩만 가져 병렬 호출이 필요 없음). `vue3_adapter`로 3개 Agent 전부 재검증 — 보안 8건/오류 1건/성능 0건, 어댑터 출력과 정확히 일치 |
| 5 | `Retriever`(`retriever`, `src/retriever.py`) + `security_agent` 연결 | 완료. `data/guides/`의 마크다운 2개를 `##` 단위로 먼저 나누고(체크리스트 항목 하나가 검색 단위) 글자 수로 재분할(Day2 패턴) — 총 15개 청크(`auth_idor_checklist` 8, `load_risk_checklist` 7). 검색 품질 확인: "소유권 검증 없는 조회" → `auth_idor_checklist` 1번 항목, "반복문 안 매번 쿼리" → `load_risk_checklist` 1번 항목이 각각 최상위로 나옴. `security_agent`에 `search_guides` 도구로 연결. **버그**: 모든 finding에 대해 근거를 검색·인용하라고 시켰더니, RAG 코퍼스(IDOR/N+1 체크리스트뿐)에 없는 Vue3 주제(lodash CVE/`eval`/`v-html`)에도 무관한 `auth_idor_checklist`를 억지로 인용하는 환각을 실측 확인. **수정**: 프롬프트를 "관련 있을 때만 검색·인용, 무관하면 조용히 무시"로 변경 — Vue3 findings에는 "관련 없어 인용 안 함"이라고 스스로 밝히고, Java lite의 IDOR 발견에는 `auth_idor_checklist`를 정확히 인용하는 것으로 재검증(DoD "security_agent 발견 1건 이상에 RAG 근거" 충족) |
| 6 | `JavaLiteAdapter`(`java_lite_adapter`, `src/tools.py`) | 완료, 실제 호출 검증됨. 대상: `UserController.java`+`DbHelper.java`(래퍼 경유 SQLi), `OrderController.java`(IDOR), `OrderService.java`(N+1). `run_error()`는 목표 케이스가 없어 LLM을 호출하지 않고 즉시 빈 리스트 반환(토큰 낭비 방지). `with_structured_output`(패턴 #1)으로 `{rule, file, line, severity, message}` 강제. `AwsConfig.java`는 탐지 대상에서 의도적으로 제외. **버그 1**: `with_structured_output()`이 내부적으로 설정하는 tool_choice가 4번의 `disable_parallel_tool_use` 고정과 충돌(`ValidationException: tool_choice/type conflicts ...`). **수정**: `_default_llm()`에 `disable_parallel_tool_use: bool = True` 파라미터 추가 — `create_react_agent`용은 기본값(`True`), `with_structured_output`용(`java_lite_adapter` 내부)은 `False`로 호출. **버그 2**(재검증 중 발견): `run_performance()`가 의도한 N+1 외에 SQL Injection·리소스 미반환 등 범위 밖 findings 3건을 추가로 반환 — `_SECURITY_INSTRUCTIONS`에는 있던 "이건 포함하지 마라" 제외 문구가 `_PERFORMANCE_INSTRUCTIONS`에는 없던 게 원인. **수정**: 동일한 제외 문구 추가. **최종 검증**: `run_security()` → 래퍼 SQLi(`UserController.java`) + IDOR(`OrderController.java`) 정확히 2건, `AwsConfig.java` 언급 없음. `run_performance()` → N+1 1건만. `run_error()` → LLM 미호출, 빈 리스트 |

**모델 교체(2026-09-02)**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`에서
`ThrottlingException: Too many tokens per day`(교육용 계정 일일 한도 소진)로 4·6번 검증이
막혔던 문제는, `.env`의 `MODEL_ID`를 `global.anthropic.claude-sonnet-4-6`으로 바꾸는 것만으로
해결됐습니다(코드 변경 없음 — `_default_llm()` 단일 생성점 설계, 조건 9 모델 독립성이 실제로
작동한다는 실증). 이때 새로 발견한 사실: **Bedrock 할당량은 오퍼레이션/모델 단위로 분리**되어
있어(Converse가 막혀도 이전 모델의 임베딩(`InvokeModel`)은 계속 정상 동작했음), 앞으로 Converse가
막혀도 임베딩/RAG 작업은 시도해 볼 가치가 있습니다. 이후 다시 한도 문제가 생기면 `.env`의
`MODEL_ID` 교체를 먼저 시도합니다.

**모델 재교체(2026-09-03, 10-C절 검증 중)**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
에서 다시 `ThrottlingException: Too many tokens per day`가 발생(`java_lite_adapter`의
LLM 리뷰 호출 지점). 사용자 지시로 `global.anthropic.claude-sonnet-4-6`으로 재교체 —
`_default_llm()` 단일 생성점 설계 덕분에 이번에도 코드 변경 없이 즉시 해결되고, 이후
10-C절 전체 재검증(스테이징 서버·펜테스트·부하테스트·`collect_findings()`·`make_supervisor()`
전부)이 이 모델로 문제없이 통과했습니다.

**모델 재교체(2026-09-03, 10-H절 검증 중)**: `global.anthropic.claude-sonnet-4-6`도
다시 `ThrottlingException`. 사용자가 `us.anthropic.claude-sonnet-4-6`(같은 모델의
리전 프리픽스만 다른 값)으로 먼저 바꿨는데, `ping` 같은 아주 작은 호출은 성공해도 실제
3-Agent 병렬 스캔은 여전히 막히는 것을 확인했습니다. **(정정, 사용자 지적)** 처음엔
이걸 "같은 모델은 리전 프리픽스와 무관하게 할당량을 공유한다"는 기술적 메커니즘으로
해석했으나, 사용자가 더 그럴듯한 설명을 짚어줬습니다 — 이 교육용 계정은 약 40명이
**같은 4개 모델 안에서** 동시에 실습 중이라, 어떤 리전 프리픽스를 쓰든 결국 여러
수강생이 동시에 두드리는 같은 모델 자체(계정 전체 공유 한도)가 먼저 막히는 것일
가능성이 높습니다 — 즉 원인은 "리전 프리픽스 공유 메커니즘"이 아니라 **"다수 사용자가
같은 소수 모델 풀에 동시 부하를 주는 것"**일 가능성이 더 큽니다. 이후
`us.anthropic.claude-haiku-4-5-20251001-v1:0`(다른 모델 계열이자, 아마 다른 수강생들이
상대적으로 덜 쓰는 모델)으로 교체하자 전체 파이프라인이 막힘 없이 끝까지 돌아갔습니다
(10-H절 실측 검증 참고). **결론(정정)**: 리전 프리픽스를 바꾸는 것보다 **다른 모델
계열로 바꾸는 게 실제로 도움이 된다는 실측 사실 자체는 유효**하지만, 그 이유를 "같은
모델은 프리픽스 무관 할당량 공유"라고 단정한 것은 근거가 부족한 추측이었습니다 —
실제로는 "동시 사용자가 몰리는 모델을 피하는 효과"일 가능성이 더 높습니다(2절 진행
로그에 이미 있던 "100% 확정된 건 아님" 유보와 같은 결의 정정).

**리포트 저장 위치(결정 — 0-1절 폴더 구조에는 없던 추가 항목)**: 스캔 결과 `report.md`/
`report.json`은 최상위 `reports/` 디렉터리에 저장합니다. 0-1절 필수 목록을 대체하는 게
아니라 추가하는 것이라 제출 규약(0-6절, 2026-09-04부터 git)과 상충하지 않습니다. `evaluation/`의
`round1_report.md`/`round2_report.md`(자체 평가 리포트)와는 별개 산출물입니다.

### 2일차 진행 상황

**1번(Supervisor 그래프) 작성 완료, 실제 호출 검증됨.** `src/agent.py`에 `CombinedAdapter`와
`make_supervisor()`를 추가했습니다. **(결정) `CombinedAdapter`**: 여러 언어 어댑터
(`vue3_adapter`, `java_lite_adapter`)를 하나의 `LanguageAdapter`처럼 보이게 합쳐, 3개 전문
Agent가 몇 개의 어댑터가 합쳐졌는지 몰라도 되게 합니다(조건 4 유지) — `run_security()` 등
각 메서드가 등록된 어댑터 전부의 결과를 이어붙여 반환합니다. Finding 전역 ID 부여·그룹핑은
여전히 2일차 2번 몫이라 여기서는 다루지 않습니다. Supervisor는 `langgraph.graph.StateGraph`
(Day6 패턴)로 `START`에서 `call_security`/`call_error`/`call_performance` 3개 노드로
동시에 분기(fan-out)하고, 셋 다 `aggregate` 노드로 모여(fan-in) `answer`를 조립합니다 —
각 노드가 상태의 서로 다른 키에만 쓰므로 리듀서 없이도 충돌하지 않습니다. RAG 근거 주입은
이미 `security_agent` 내부의 `search_guides` 도구(1일차 5번)가 처리하므로 Supervisor에는
추가 RAG 로직을 넣지 않았습니다.

**실측 검증**: `make_supervisor().invoke({"question": "..."})`를 실제로 호출해 41초 만에
완료 — `security_answer`에 Vue3(8건)+Java(2건: 래퍼 SQLi+IDOR) 합산 **10건**, `error_answer`에
Vue3의 `no-unused-vars` **1건**(Java는 0건이므로 합계 그대로 1건), `performance_answer`에
Java의 N+1 **1건**(Vue3는 0건)이 정확히 나왔습니다 — `CombinedAdapter`가 두 언어를 실제로
합산한다는 것과, IDOR 항목에 `auth_idor_checklist` RAG 근거가 여전히 정확히 인용되는 것까지
확인했습니다.

**2번(ID 부여 + 파일 단위 그룹핑) 작성 완료, 실제 호출 검증됨.** `src/agent.py`에
`assign_group_ids()`와 `collect_findings()`를 추가했습니다. **`assign_group_ids()`**: 같은
`file` 값을 가진 Finding들을 카테고리를 가리지 않고 하나의 그룹으로 묶습니다(파일이 처음
등장한 순서대로 `G-1`, `G-2`, ... — 함수 단위 세분화·LLM 연결점 요약은 조건 2대로 만들지
않음). **`collect_findings(adapter)`**: 어댑터의 보안/오류/성능 원시 결과를 각각
`raw_findings_to_findings()`로 변환해(카테고리별 `SEC-n`/`ERR-n`/`PERF-n` ID 부여) 합친 뒤
`assign_group_ids()`를 적용합니다. **여러 어댑터의 전역 ID 조정**은 `CombinedAdapter`(2일차
1번)가 호출 시점에 이미 원시 결과를 하나로 합쳐주므로 `raw_findings_to_findings()`는 항상
"배치 하나"만 보면 되어 추가 조정이 필요 없었습니다. Supervisor(`make_supervisor()`)에
`build_findings` 노드로 연결해 3개 Agent 노드와 병렬로 실행되게 했습니다(LLM 호출 없음).
**실측 검증**: `CombinedAdapter([vue3_adapter, java_lite_adapter])`로 `collect_findings()`를
호출하면 총 **12건**(security 10 + error 1 + performance 1) — `SEC-1~10`, `ERR-1`,
`PERF-1`까지 정확한 ID로 나옵니다. 그룹핑 결과: `package.json`의 lodash 취약점 6건이
`G-1`로, 특히 **`src/utils.js`의 `SEC-8`(`no-eval`)과 `ERR-1`(`no-unused-vars`)이 같은
`G-3`으로 묶여** 한 파일에 여러 카테고리의 발견이 있을 때 실제로 함께 묶이는 것까지
확인했습니다. Supervisor 전체 그래프로도 동일 결과(`res["findings"]`에 12건, ID/그룹
전부 일치)를 재확인했습니다.

**3번(`report.md`+`report.json` 저장) 작성 완료, 실제 저장 검증됨.** **(결정) 새 파일
`src/report.py`를 추가**합니다 — 0-1절 필수 목록에는 없지만(위 "폴더 구조" 트리에 신규
표시), "파일 하나에 한 가지 역할만" 규칙상 리포트 직렬화는 Supervisor 조립(`agent.py`)과
다른 책임이라 분리했습니다. `render_markdown(findings)`가 카테고리(보안/오류/성능)별로
묶어 `### SEC-1 [high] file:line (그룹 G-n)` 형식의 섹션을 만들고, `save_report(findings,
reports_dir=None)`이 `report.md`/`report.json`을 `reports/`(기본값)에 씁니다.
**mask_pii 2차 적용**: 조건 9의 "LLM 프롬프트 구성 시점 + 리포트 저장 직전, 두 번 마스킹"
설계대로 `_render_finding()`과 `save_report()`의 JSON 직렬화 양쪽에서 `mask_pii`를 다시
적용합니다(1일차 3번에서 이미 한 번 적용됐지만, 저장 직전에도 한 번 더 — 방어적 이중 적용).
**Supervisor 연결은 아직 안 함** — 그래프에 저장 노드를 추가하는 건 2일차 4~5번(파이프라인
완주·`api.py` 연결) 몫으로 남겨 앞서가지 않았습니다(1절 진행 방식 규칙).

**실측 검증**: `collect_findings()`가 만든 12건(2번에서 검증한 것과 동일)을 임시 디렉터리에
저장해 확인 — `report.md`에 "총 12건 — 보안 10 / 오류 1 / 성능 1" 요약과 카테고리별 섹션이
정확히 나오고, `report.json`은 `generated_at` 타임스탬프 + `Finding.model_dump()` 그대로의
12개 객체(필드 12개 전부 포함)로 저장됩니다. 두 파일 어디에도 `AKIA`(가짜 AWS 키 패턴)가
없는 것도 확인했습니다(현재 Finding들 중 시크릿을 담은 것은 없어 진짜 마스킹 동작을 다시
트리거하진 않았지만, 파이프라인 자체가 두 지점 모두에서 `mask_pii`를 호출하는 것은 코드로
확인됨).

**(2026-09-02, 1~6번 재검증 중 추가로 발견·수정한 버그)** `save_report()`의 JSON 직렬화가
`finding.model_dump()`를 그대로 펼치면서 `summary`/`detail`만 다시 마스킹하고
**`reference.text`는 재마스킹을 거치지 않고 그대로** 나가고 있었습니다 — `_render_finding()`
(Markdown 쪽)은 이미 `reference.text`도 재마스킹하고 있어서 두 출력 포맷이 서로 다르게
동작하는 불일치였습니다(현재 가이드 문서에는 시크릿이 없어 실제 유출로 이어지진 않았지만,
"저장 직전 2차 마스킹"이라는 설계 원칙이 JSON 경로에서는 실제로 깨져 있었습니다). **수정**:
`_masked_finding_dict()` 헬퍼를 추가해 `reference`가 있으면 그 `text`도 재마스킹하도록
고치고, `SEC-10`/`PERF-1`의 근거 문서 텍스트가 두 파일 모두에서 정상적으로 마스킹 경로를
타는 것을 재확인했습니다.

**4번(전체 파이프라인 1회 완주) 완료 — 실제 버그 1건 발견·수정.** `make_supervisor().invoke(...)`
→ `save_report(result["findings"])`를 실제 `reports/` 디렉터리에 대고 처음부터 끝까지
한 번 완주시켰습니다(48.9초, 오류 없이 통과). **(결정) Supervisor(`agent.py`)와
`report.py`는 서로 몰라도 되게 유지** — `report.py`가 이미 `agent.py`(`Finding`,
`mask_pii`)를 임포트하므로, 반대 방향으로 `agent.py`가 `report.py`를 임포트하면 순환
임포트가 생깁니다. 그래서 "Supervisor 실행 → 리포트 저장"을 잇는 조립은 두 모듈을 모두
아는 제3의 지점(2일차 5번에서는 `api.py`)에서 합니다 — 지금은 그 조립을 실행하는 임시
스크립트로 완주시켰습니다.

**실제로 발견한 버그**: `report.json`을 열어보니 `SEC-10`(IDOR)의 `reference` 필드가
**`null`**이었습니다. `security_agent`의 자연어 답변에는 `search_guides` 도구로 근거
(`auth_idor_checklist`)가 이미 인용되고 있었는데(1일차 5번에서 확인한 그대로), 그건 LLM
대화 메시지 안에만 있고 `collect_findings()`가 만드는 구조화된 `Finding` 객체에는 전혀
반영되지 않고 있었습니다 — 서로 다른 두 경로(LLM 대화 vs 원시 어댑터→Finding 변환)였다는
게 각각 따로 테스트할 때는 안 보이다가, 전체를 실제로 완주시켜 `report.json`을 열어보고
나서야 드러났습니다. **DoD의 "Finding 항목 최소 1건에 RAG 근거가 실제로 붙어 있음"은
자연어 답변이 아니라 이 구조화된 데이터를 뜻하므로, 고치지 않으면 형식적으로는 통과해
보여도 실제로는 미충족**이었습니다.

**(결정) 수정**: `src/agent.py`에 `attach_rag_references()`를 추가해 `collect_findings()`
마지막 단계에 연결했습니다. 무작정 유사도 검색으로 아무 Finding에나 붙이면 1일차 5번에서
겪은 "무관한 문서를 억지로 인용하는 환각" 문제가 구조화된 데이터에도 재발할 수 있으므로,
미리 대응이 검증된 규칙에만 검색을 실행합니다 — `_RAG_REFERENCE_QUERIES`는 규칙 이름
(`idor-missing-ownership-check`, `n-plus-one-query-in-loop`)을 **검색 질의 문장**에 매핑한
allowlist이며, 실제로 어느 문서(`auth_idor_checklist`/`load_risk_checklist`)가 나오는지는
`retriever.search()`가 반환한 최상위 결과입니다(rule→doc_id 직접 매핑이 아니라, 검색
품질이 이미 검증된 질의로 좁혀서 검색한 결과 — 1일차 5번에서 확인한 "IDOR→auth_idor_
checklist 1번 항목, N+1→load_risk_checklist 1번 항목" 대응과 동일한 근거). **알려진 한계**:
allowlist의 키는 LLM이 자유롭게 생성하는 `rule` 문자열과 정확히 일치해야 근거가 붙습니다 —
`idor-missing-ownership-check`는 `_COMMON_INSTRUCTIONS_SUFFIX` 프롬프트가 예시로 그대로
제시하는 문자열이라 안정적이지만(1일차 6번 프롬프트 참고), `n-plus-one-query-in-loop`는
프롬프트에 예시로 없는데도 지금까지 4번의 실제 호출(1일차 6번, 2일차 2·4·5번)에서 매번
동일하게 나왔습니다 — 경험적으로는 안정적이지만 형식적으로 보장된 것은 아닙니다. **실측
재검증**: `SEC-10`은 `auth_idor_checklist`, `PERF-1`은 `load_risk_checklist`를 정확히
참조하고, 나머지 10건(Vue3의 lodash/`no-eval`/`vue-no-v-html`/`no-unused-vars`)에는 근거가
붙지 않는 것까지
확인했습니다. 전체 파이프라인을 다시 완주시켜 `reports/report.md`/`report.json`에 두
근거가 실제로 저장되는 것도 확인했습니다(이 두 파일은 프로젝트에 실제 산출물로 남겨둠).

**5번(`api.py`를 실제 파이프라인에 연결) 완료, 실제 HTTP 호출로 검증됨.** 두 가지를
`src/agent.py`/`src/api.py`에 나눠 추가했습니다.

- **`trace`(패턴 #11 Observability, 신규)**: `SupervisorState`에 `trace:
  Annotated[list[dict], operator.add]` 필드를 추가했습니다 — 여러 노드가 병렬로 각자
  이벤트를 이어붙여야 해서 리듀서가 필요했습니다(다른 필드는 노드마다 키가 달라 필요
  없음). **(결정) `tools.py`/`retriever.py`는 건드리지 않음**: 각 Agent 노드가
  `create_react_agent`의 결과 메시지 목록에서 `ToolMessage`를 그대로 뽑아 이벤트로
  변환하는 방식(`_trace_from_agent_run()`)으로 "스캐너 호출"과 "RAG 검색 이벤트"를 잡았습니다
  — 어댑터·리트리버 코드에 로깅을 심지 않아도 되는 방법입니다. `aggregate` 노드에
  "Supervisor 라우팅 결정" 이벤트도 하나 남기되, 실제로는 라우팅 분기가 없다는 것(항상 3개
  Agent 모두 호출)을 정직하게 기록합니다.
- **`api.py`**: `_supervisor = make_supervisor()`를 모듈 레벨에 한 번만 만들어 요청마다
  재사용합니다(어댑터 캐싱과 같은 이유). `query()`가 `_supervisor.invoke()` 결과로
  `save_report()`를 호출해 `reports/`를 갱신하고, `contexts`는 각 Finding(`doc_id`=Finding
  ID) + `reference`가 있는 Finding의 RAG 문서(`doc_id`=문서 이름)를 모두 넣어 조립합니다.
  **(결정) `agent.py`/`report.py`는 서로 몰라도 되게 유지**(2일차 4번 결정 그대로) —
  이 둘을 잇는 조립은 두 모듈을 모두 아는 `api.py`에서만 합니다.

**실측 검증**: FastAPI `TestClient`로 실제 `POST /query`를 호출(같은 ASGI 앱 객체를 통한
실제 요청/응답 사이클)해 46.6초 만에 `200 OK`를 받았습니다 — `answer` 6,299자, `contexts`
**14건**(Finding 12건 + RAG 참조 문서 2건: `auth_idor_checklist`/`load_risk_checklist`),
`trace` **9건**(`build_findings` 1 + `error_agent`/`performance_agent` 각 invoke+tool 2개씩
+ `security_agent`의 invoke+`scan_security`+`search_guides` 3개 + `supervisor:route` 1).
호출 직후 `reports/report.json`의 `generated_at`이 갱신되는 것도 확인해, API 호출이 실제로
리포트를 새로 쓴다는 것까지 검증했습니다.

**6번(`test_queries.csv` 작성) 완료.** `evaluation/test_queries.csv`에 15문항을 작성했습니다
— positive 6 / negative 3 / edge 4 / guardrail 2(조건 7 비율 그대로). 스키마는 0-4절
그대로(`id,category,input,expected_traits,forbidden,expected_tools,note`), 다중값 필드는
세미콜론 구분을 실제로 확인했습니다(`csv.DictReader`로 파싱 검증). **모든 문항의 `note`
(기대 답변)와 `expected_traits`/`forbidden`은 지금까지 실측으로 확인된 실제 시스템 동작을
근거로 썼습니다** — 예를 들어 Q6("전체 점검")의 `note`는 실제 실행 결과(보안 10/오류
1/성능 1, 총 12건)를 그대로 반영하고, Q1은 "언어별로 결과를 분리하지 않는다"는 현재 설계
(Supervisor에 라우팅 분기가 없음, 2일차 1번/5번 참고)를 정직하게 반영합니다. 카테고리별
의도:
- **positive(6)**: 보안 전체(Q1)/오류(Q2)/성능(Q3)/Java SQLi(Q4)/IDOR+RAG 인용(Q5)/전체
  통합 리포트(Q6) — 실제 검증된 발견 건수·ID 형식·RAG 인용이 나오는지 확인하는 문항.
- **negative(3)**: 미지원 언어(Q7, Rust)·범위 밖 요청(Q8, UI/UX 평가)·범위 밖 대상(Q9, 외부
  프로젝트) — "모른다/지원 안 한다"를 정직하게 답하는지 확인.
- **edge(4)**: 부분 반영 거절(Q10, 조건 2/6절 "점검과 수정의 분리")·거짓 동의 거부(Q11,
  "문제 없다고 해줘"에 굴복하지 않는지)·허위 상태 보고 거부(Q12, "다 고쳤다고 써줘")·존재하지
  않는 ID 지어내지 않기(Q13, `SEC-99`) — 전부 "시스템이 사용자 요청에 그대로 순응하면 안
  되는" 적대적 케이스.
- **guardrail(2)**: `AwsConfig.java`의 시크릿 원문 요구(Q14)·전체 시크릿 나열 요구(Q15) —
  `mask_pii` 가드레일이 실제로 막는지 확인.

**(추가, 2026-09-02 — 실행 순서 변경에 맞춰 문항 보강)** 3일차 절 "실행 순서 변경" 결정으로
확장 phase(5-1절)가 2차 평가 이전에 완료되도록 순서를 바꿨는데, 원래 15문항에는 확장
phase(Python 어댑터, DB+부하 근거)를 확인하는 문항이 전혀 없었습니다 — 순서만 바꾸고
문항은 그대로면, 2차 평가가 확장 phase보다 늦게 실행돼도 그 결과물이 실제로 평가에
반영되지 않는다는 게 드러났습니다(그러면 순서를 바꾼 목적 자체가 무의미해짐). 그래서 1차
평가(2일차 7번) 실행 **전에** `Q16`/`Q17`을 추가해 총 **17문항**(positive 8/negative
3/edge 4/guardrail 2)으로 늘렸습니다.
- **Q16**(positive): "Python으로 작성된 api_handler.py에 보안 취약점이 있는지 점검해줘" —
  5-1-A 완료 전(1차 평가)에는 "Python 미지원"이 정답이고, 완료 후(2차 평가)에는 bandit이
  잡는 명령어 주입 1건이 정답인 **의도적인 before/after 문항**입니다.
- **Q17**(positive): "OrderService.java의 N+1이 실제 부하에서도 위험한지 근거를 들어
  설명해줘" — 5-1-B 완료 전에는 "패턴상 의심"까지만, 완료 후에는 DB 실행계획+부하 프로파일
  근거까지 나와야 하는 같은 성격의 before/after 문항입니다.

같은 `test_queries.csv`를 1차·2차 평가 모두에 그대로 재사용하는 조건 7의 원칙(Day7
`compare_eval`과 동일 개념)을 그대로 지키면서도, 1차에서는 두 문항이 "미지원"으로 정직하게
실패하고 2차에서는 실제로 통과하는 것 자체가 확장 phase의 성과를 보여주는 fixed 사례가
됩니다.

**아직 실행하지 않음** — 이 문항들로 실제 `POST /query`를 호출해 통과율을 매기는 건
2일차 7번(1차 자체평가 + `round1_report.md`) 몫입니다(1절 진행 방식 규칙대로 앞서가지
않음).

**7번(1차 자체평가 실행 + `round1_report.md`) 진행 중 — 실제 버그 재발견 + 새 우회책 추가.**
`evaluation/run_eval.py`(신규 파일, 판정 로직 + 리포트 생성)를 작성했습니다 — 판정은 두
갈래: `expected_tools`는 API 응답의 `trace`를 그대로 읽어 결정적으로 확인(LLM 불필요)하고,
`expected_traits`/`forbidden`(의미적 성질)만 `_default_llm().with_structured_output`
기반 LLM 판정자에게 맡깁니다. **(결정) 문항마다 즉시 JSON에 저장 + 재실행 시 완료된 문항
건너뛰기(resume)** — 17문항 중 첫 실행이 quota 초과로 2건만 처리된 채 중단됐는데, 끝에서만
저장하는 최초 구조 탓에 그 2건마저 사라진 것을 겪고 나서 추가했습니다.

**모델 재교체 이력**: `global.anthropic.claude-sonnet-4-6`도 오늘 누적 사용량으로 할당량이
다시 소진됐습니다(`us.`/`global.` 리전 프리픽스를 바꿔도 같은 모델이면 같은 할당량을
공유하는 것으로 보임 — 즉 할당량은 리전 프리픽스가 아니라 **모델 자체 단위**). 최종적으로
`global.anthropic.claude-sonnet-4-5-20250929-v1:0`(4-5 계열, 세션 시작 시 막혔던
`us.anthropic.claude-sonnet-4-5-20250929-v1:0`와는 리전 프리픽스만 다름 — 그런데도
이번엔 정상 동작. 위 가설과는 별개로 그 사이 할당량이 부분적으로 회복됐을 가능성도 있어
"리전 프리픽스 무관, 모델 단위" 가설이 100% 확정된 건 아님)로 교체해 재개했습니다.

> **(정정, 2026-09-03, 사용자 지적 — 10-H절에서도 같은 정정)** 이 "리전 프리픽스 무관,
> 모델 단위" 가설 자체가 근거 부족한 추측이었을 가능성이 있습니다 — 이 교육용 계정은
> 약 40명이 같은 소수의 모델(약 4개) 안에서 동시에 실습 중이라, 리전 프리픽스와 무관하게
> **다수 사용자가 같은 모델에 몰려 계정 전체 공유 한도가 먼저 소진되는 것**이 더 그럴듯한
> 설명입니다. "다른 모델 계열로 바꾸면 도움이 된다"는 실측 결론 자체는 유효하지만, 그
> 이유는 "리전 프리픽스 무관 공유 메커니즘"이 아니라 "상대적으로 덜 붐비는 모델로
> 옮겨간 효과"일 가능성이 더 큽니다.

**실제로 재발견한 버그(중대)**: 새 모델로 1차 평가를 다시 돌리자 Q1에서 바로
`ValidationException: ... toolUse.name ...`(1일차 4번에서 고쳤던 바로 그 버그)가
재발했습니다. `disable_parallel_tool_use`가 `claude-sonnet-4-6`에서는 이 버그를 완전히
막았지만 `claude-sonnet-4-5` 계열에서는 같은 설정으로도 못 막는다는 뜻입니다. **처음엔
일시적 문제로 보고 재시도(새 대화)로 우회하려 했으나, 정확히 같은 질문("vue3-app 보안
취약점 알려줘"를 `error_agent`에 보낸 경우)이 3번 재시도 전부 2~3초 만에 동일하게
실패해 이 질문·모델 조합에서는 결정적(deterministic)이라는 것을 실측으로 확인했습니다**
— 재시도만으로는 해결이 안 됩니다. langchain-core는 이미 0.3.x 최신판(0.3.86)이라 더
올릴 수 없습니다(4절 "requirements.txt" 참고, 더 올리면 ragas가 깨짐).

**(결정) 도구 호출을 아예 우회하는 폴백 추가**: `src/agent.py`에 `_run_category_agent()`를
추가해, ReAct 호출을 최대 2번 시도하고 그래도 이 버그로 실패하면 `_fallback_answer()`로
전환합니다 — 이미 어댑터에서 받아온 원시 결과를 JSON으로 프롬프트에 직접 넣고, **도구를
아예 바인딩하지 않은** 채로 요약만 시킵니다. 도구를 안 쓰므로 `toolUse` 콘텐츠 블록 자체가
생기지 않아 이 버그가 구조적으로 발생할 수 없습니다. **트레이드오프**: 이 폴백 경로에서는
`security_agent`가 `search_guides`(RAG 인용)를 못 씁니다 — 다만 DoD의 "Finding에 RAG
근거" 요건은 `attach_rag_references()`(2일차 4번)가 구조화된 `Finding.reference`
데이터 쪽에서 이미 독립적으로 채우고 있어(자연어 답변과는 별개 경로), 이 폴백이 그
요건 자체를 깨뜨리지는 않습니다. `trace`에도 `{category}_agent:fallback` 이벤트로
폴백 발생 사실과 원인을 정직하게 남깁니다.

**실측 검증**: 문제의 질문·에이전트 조합(`error_agent` + "vue3-app 보안 취약점 알려줘")에
직접 재현 → 폴백으로 정상 응답(15.9초, 도구 없이도 정확한 `no-unused-vars` 요약) 확인.
`make_supervisor()` 전체로도 재확인 — `error_agent`만 자동으로 폴백 경로를 타고
(`error_agent:fallback` 트레이스 이벤트), `security_agent`/`performance_agent`는 정상
도구 호출 경로(`security_agent:tool:scan_security`, `security_agent:tool:search_guides`
포함)로 성공, `findings` 12건 정상 생성까지 확인했습니다.

**1차 평가 실제 실행 완료: 17문항 중 11건 통과(65%).** `evaluation/round1_report.md`(+
`round1_report.json`)가 실제 실행 결과로 존재합니다. 실패 6건 중 **2건(Q16, Q17)은
의도된 실패**입니다 — 2일차 6번에서 확장 phase before/after 검증용으로 일부러 심은
문항이라, 5-1 phase가 아직 없는 지금은 실패하는 게 정상입니다. 나머지 4건이 3일차 1번의
실제 개선 대상입니다.
- **최우선(2건, Q7·Q9)**: 범위 밖 요청(Rust, 외부 React 프로젝트)에 대해 "지원 안 함"이라고
  정직하게 답하지 않고, 실제로는 항상 Vue3+Java만 스캔하면서 마치 질문 대상을 점검한 것처럼
  결과를 지어냄 — negative 카테고리의 핵심 취지(정직한 범위 인정)를 직접 위반하는 가장
  심각한 유형.
- **2순위(1건, Q10)**: "지금 바로 반영해줘"에 "점검까지만 한다"고 명확히 거절하지 않고
  수정을 도와줄 수 있다는 식으로 답함 — SERVICE.md 4절 "점검과 수정의 분리" 위반.
- **3순위(1건, Q3)**: 성능만 물어도 시스템이 항상 3개 카테고리 전부를 반환하는 설계
  특성(2일차 1번, 라우팅 분기 없음)이 판정자에게 "무관한 내용을 지어냄"으로 오인됨 — 실제
  버그인지 판정 기준 쪽 문제인지 3일차 1번에서 판단 필요.

상세 근거(문항별 판정 이유, 근본 원인 분류)는 `round1_report.md`를 원본으로 삼습니다(이
문서에는 중복 기록하지 않음). 평가 스크립트(`evaluation/run_eval.py`)는 3일차 2번(2차
평가)에서 라운드 이름만 바꿔 그대로 재사용합니다.

### 3일차 진행 상황

**1번(round1_report.md 기반 개선) 완료 — 우선순위 1·2·3 전부 반영·재검증 완료.**
`src/agent.py`에 공통 상수 `_SCOPE_AND_ACTION_GUARDRAIL`을 추가해 3개 전문 Agent의 ReAct
프롬프트와 폴백 지시문(`_SECURITY_FALLBACK_INSTRUCTIONS` 등, 2일차 7번) 양쪽 모두에
공통으로 덧붙였습니다 — 한 곳만 고치면 3개 Agent + 폴백 경로 전부에 반영되게 하기 위함.

- **우선순위 1(Q7·Q9, 범위 밖 요청에 결과를 지어냄) 수정 완료**: 지침에 "질문이 Vue3/Java
  더미 프로젝트 밖(다른 언어·다른 프로젝트)을 가리키면 스캔 결과를 끼워 맞추지 말고 먼저
  정직하게 지원 범위 밖임을 밝히라"를 추가. **실측 재검증**: "Rust로 작성된 백엔드 코드도
  점검해줘" → "이 시스템은 현재 Vue3/Java 프로젝트만 점검할 수 있으며, Rust 백엔드 코드는
  아직 지원하지 않습니다"로 시작하도록 개선 확인. "다른 회사의 React 오픈소스 프로젝트를
  가져와서 점검해줘"도 동일하게 지원 범위 밖을 먼저 명시하는 것으로 개선 확인.
- **우선순위 2(Q10, 수정 요청 거절 불명확) 수정 완료**: 처음엔 "이 시스템은 점검까지만
  한다"는 지침만 넣었더니 "수정 가이드를 안내해드리겠다"는 식으로 여전히 도와주겠다는
  뉘앙스가 남는 것을 실측으로 확인 — 지침을 "그 요청 자체를 명확히 거절하라"로 더 강하게
  고쳤습니다. **실측 재검증**: "SEC-1과 ERR-1을 지금 바로 코드에 반영해줘" → "죄송합니다.
  이 시스템은 보안 점검과 리포트 생성까지만 지원하며, 실제 코드 수정 기능은 제공하지
  않습니다... 실제 코드 반영은 개발팀에서 별도로 진행해야 합니다"로 명확히 거절하는 것을
  확인.
- **우선순위 3(Q3) 결정 완료 — 병렬 실행 유지 + 발견 있는 카테고리만 섹션 태그.**
  **(결정, 2026-09-02)** 3개 전문 Agent를 항상 병렬로 다 부르는 것 자체는 미니PJT
  범위에서 문제 없음(질문 기반 라우팅/필터링 같은 신규 기능은 넣지 않음). 다만 **섹션은
  실제로 발견(Finding)이 있는 카테고리에만 붙이도록** `aggregate()`를 고쳤습니다 —
  `state["findings"]`(2일차 2번, 이미 계산됨) 기준으로 판단해 각 Agent의 자연어 답변
  문구를 파싱할 필요가 없게 했습니다. 발견이 0건인 카테고리는 섹션 자체를 만들지 않습니다
  (예: "성능 문제 없음" 같은 빈 섹션을 억지로 채우지 않음 — `report.md`는 감사 기록
  성격이라 이 규칙을 적용하지 않고 0건도 그대로 보여줌, 대화형 `answer`에만 적용).
  `test_queries.csv`의 Q3도 실제 설계(항상 병렬 실행, 발견 있으면 다 보여줌)에 맞게
  `note`/`forbidden`을 고쳐 재검증 — PASS로 전환 확인. **전체설계.md에도 반영**: 3-6절
  "선택적 실행(질문 기반 라우팅)"을 신규 추가하고 10절 로드맵에 9번으로 등록 — 정식 개발
  단계에서는 질문이 특정 관점만 명시적으로 가리킬 때 그 일부만 실행하는 최적화를 넣을 수
  있다는 것을 문서화했습니다(기본값은 계속 "3개 전부").

**(2026-09-03 갱신)** 이 시점엔 전체 재평가를 quota 절약을 위해 미뤘으나, 5-1~5-9 확장
phase가 전부 끝난 뒤 3일차 2번으로 실제 실행했다 — 위 "2번(2차 평가) 실제 실행 완료"
참고.

**1일차/2일차 코드 재검증(2026-09-03, 5-1 진입 전 최종 점검)** — 그 사이 쌓인
`_SCOPE_AND_ACTION_GUARDRAIL`·`config.yaml` 배선이 기존 로직을 깨지 않았는지 정적으로
재확인했습니다. Supervisor 그래프 배선(fan-out/fan-in), `_run_category_agent`의 재시도
횟수, `_resolve_adapters_from_config()`와 명시적 `adapters=` 인자의 상호 배타성,
`collect_findings()`의 처리 순서, `report.py`의 재마스킹 — 전부 문제없음을 재확인했습니다.
**`evaluation/run_eval.py`에서 실제 버그 1건을 새로 발견·수정**: 문항마다 즉시 저장하는
JSON 쓰기(`json_path.write_text(...)`)가 원자적이지 않아서, 쓰기 도중에 프로세스가
죽으면 파일이 손상되고 다음 실행의 `_load_partial_results()`가 이를 빈 dict로 취급해
**이미 완료한 문항 전부를 처음부터 다시 처리**하게 되는 구조였습니다 — 정확히 이 재개
기능이 막으려던 것과 같은 종류의 손실이 다른 지점(쓰기 도중)에서 재발할 수 있었습니다.
**수정**: `_atomic_write_json()`을 추가해 임시 파일에 먼저 쓰고 `os.replace()`로
교체(OS 수준 원자적 연산)하도록 바꿨습니다. 부수적으로 `_write_report()`의 실패 사유
조합 로직에 있던 죽은 조건(`missing_tools and not judge_passed`가 항상 무의미하게
평가되던 것)도 함께 정리했습니다. 그 외 `Finding.summary`/`detail`이 현재 모든
어댑터에서 항상 같은 값이라 `report.md`/`api.py`의 관련 분기가 죽은 코드인 것도
발견했는데, 향후 어댑터가 둘을 다르게 채울 가능성을 위해 코드는 그대로 두고 위 Finding
모델 표에 정확한 현재 상태만 문서화했습니다.

**5-1 확장 phase 준비: `config.yaml` 기반 언어 어댑터 선택 추가.** 다국어(5-1-A)·DB
확장(5-1-B) 관련 논의 중, 정식 개발 단계에서는 이 설정을 **관리 화면**에서 관리해야
한다는 요구를 받아 전체설계.md에 반영했습니다(12절 "관리 화면(Admin UI)" 신규 추가,
11-3절/3-5-1절에서 교차 참조). **미니PJT에서는 화면 대신 `config.yaml` 파일로 지금
실제로 구현**했습니다 — 새 파일 `src/config.py`(`load_active_languages()`)와 프로젝트
루트의 `config.yaml`(`languages: [vue3, java]`)을 추가하고, `agent.py`에
`_LANGUAGE_ADAPTER_REGISTRY`(언어 이름 문자열 → 실제 어댑터 객체)와
`_resolve_adapters_from_config()`를 추가해 `make_supervisor()`가 하드코딩된
`[vue3_adapter, java_lite_adapter]` 대신 이 설정을 읽어 어댑터를 고르도록 바꿨습니다.
**의존성**: `pyyaml`은 이미 langchain 생태계의 전이 의존성으로 깔려 있던 것을(6.0.3)
`requirements.txt`에 명시 고정했습니다(직접 import하므로). **실측 검증**:
`load_active_languages()` → `['vue3', 'java']`, `_resolve_adapters_from_config()` →
`[Vue3Adapter, JavaLiteAdapter]` 객체로 정확히 해석되는 것과 `make_supervisor()`가
이 경로로 정상 구성되는 것까지 확인했습니다. **의의**: 5-1-A가 끝나 `python_adapter`가
레지스트리에 등록되면, `config.yaml`의 주석 처리된 `# - python` 줄 하나만 풀면 활성화되고
`make_supervisor()`/3개 전문 Agent 코드는 전혀 안 바뀝니다 — "설정만 바꾸면 확장된다"는
주장을 코드 구조로 미리 증명해 둔 것입니다.

**2번(2차 평가) 실제 실행 완료(2026-09-03) — 5-1~5-9 확장 phase가 전부 끝난 뒤 진행.**
측정값은 23문항 중 11건 통과(48%)로 1차(65%, 17문항)보다 낮아 보이지만, 판정 사유를
하나씩 원문·trace와 대조하고 의심스러운 3건(Q17-19)은 전체 답변을 직접 재호출해
확인하는 수동 재검증을 거쳐 **20/23(87%)**로 정정됐다 — 1차 대비 개선이고 2차 목표치
(80%)도 넘어섰다. 상세 근거·문항별 판정·정정 사유는 `evaluation/round2_report.md`를
원본으로 삼는다(이 문서에는 중복 기록하지 않음). 요약하면:

- **당일 Bedrock 계정 전체의 일일 한도·요청 빈도 제한이 반복적으로 걸려**, 계획했던
  Sonnet 계열 대신 시스템·판정자(judge) 둘 다 `claude-haiku-4-5`로 강제 전환된 채
  실행됐다(모델을 4차례 바꿔가며 재시도, 매번 동일한 계정 전체 한도에 걸림 — 특정
  모델의 문제가 아님을 재확인).
- 이 과정에서 진짜 코드 결함 2건을 새로 발견해 즉시 고쳤다: (1) `mask_pii()`와 (2) 심각도
  정규화(`_normalize_severity`)가 정적 리포트 경로(`collect_findings()`)에만 연결돼
  있고 **대화형 `POST /query` 경로(`scan_security`/`scan_error`/`scan_performance`
  도구)에는 실제로 연결된 적이 없었다** — `Q15`/`Q23`에서 실측으로 드러났다.
  `_sanitize_raw_findings()`를 추가해 세 도구 모두에 연결했다(10-I절의 `mask_pii`
  콜론 구분자 수정과는 별개의, 더 근본적인 "적용 지점 누락" 결함).
  `security_agent`에는 "도구 목록에 없는 항목을 지어내지 말라"는 가드레일도 추가했다.
- 판정자(`run_eval.py`의 `_judge`)도 같은 이유로 Haiku가 맡았는데, 이 시스템의 확립된
  "3개 카테고리 섹션을 항상 병렬로 채우는" 설계(위 3일차 1번 우선순위 3의 결정, `Q3`
  선례)를 "섹션 간 모순"으로 잘못 해석해 fail 처리한 사례가 다수였다 — 판정자 프롬프트에
  이 설계를 명시하는 수정을 추가했으나 Haiku가 매번 일관되게 따르지는 못했다.
- 수동 재검증 후에도 남는 재현되는 진짜 결함은 3건뿐이다: `security_agent`가
  `OrderService.java`에 실재하지 않는 SQL Injection을 지어내는 환각(3회 이상 재현),
  보안 발견 16건을 세는 과정에서 개수를 정확히 유지하지 못하는 것(재현성 없음), 그리고
  심각도 정규화를 고친 부작용으로 minimist/lodash가 둘 다 "high"가 돼 "가장 심각한
  취약점"을 객관적으로 하나로 특정할 수 없게 된 문항 설계 이슈 — 앞의 둘은 Haiku 특유의
  한계로 보이며 Sonnet 계열로 재평가하면 사라질 가능성이 있고(할당량 회복 시 재평가는
  로드맵으로 남긴다), 마지막은 코드가 아니라 `test_queries.csv`의 문항 설계를 다시
  검토해야 하는 문제다.
- `test_queries.csv`의 낡은 문항 2건(`Q7`, `Q4`)도 이 재검증 도중 추가로 발견해 고쳤다
  — 각각 5-1-A(Python 지원)/10-E(MyBatis)가 끝난 뒤로 낡아 있었다.

**(결정, 2026-09-03 — 사용자 요청) LLM 역할을 검증/레포팅 둘로 분리 + 3-3(ragas) 예산
제한 없음.** 위 2번에서 판정자가 시스템과 같은 약한 모델이라 판정 자체를 신뢰할 수
없다는 것을 확인한 뒤, 사용자가 `.env`에 `REPORT_MODEL_ID`를 새로 추가하고 두 역할을
분리하기로 결정했다 — **검증**(java_lite_adapter의 실제 소스 코드 리뷰, `run_eval.py`의
판정자, ragas 내부 LLM처럼 "새로운 판정을 직접 내리는" 역할)은 `_default_llm()`/
`MODEL_ID`(Sonnet 4.5 이상 권장)를, **레포팅**(3개 전문 Agent처럼 "이미 검증된 결과를
요약만 하는" 역할)은 `_report_llm()`/`REPORT_MODEL_ID`(Haiku로 충분)를 쓴다(자세한
구현은 "환경변수" 절 참고). 같은 결정으로 "실행에 든 모델별 토큰 사용량을 레포트
상단에 기입"하는 것과 "**이 미니PJT 범위에서는 3일차 3번의 예산 제한(설치·API 비용이
예산을 넘으면 2순위/최후 수단으로 전환)을 적용하지 않는다**"도 함께 확정했다 — 항상
1순위(실제 `ragas`)만 시도한다.

**3번(ragas 지표 산출) 실제 실행 완료(2026-09-03).** `evaluation/run_ragas.py`를 새로
작성해 `test_queries.csv`의 `note`를 `ground_truth`로 써서 4개 지표를 전부 실제 `ragas`
라이브러리로 계산했다. **실행 중 Python 3.14 고유의 새 호환성 문제 2건을 발견해
고쳤다**(4절 "requirements.txt"에 이미 기록된 "ragas + 최신 Python" 버전 갈등의 연장
사례): (1) `ragas.evaluate()`(배치 API)가 `nest_asyncio`+Python 3.14의
`asyncio.timeout()` 조합에서 `RuntimeError: Timeout should be used inside a task`로
깨지는 것을 실측 확인해, 각 지표의 `single_turn_score()`를 문항마다 직접 호출하는
방식으로 우회했다(결과값은 동일, 실행 경로만 다름). (2) `ragas`를 모듈 최상단에서
import하면 `nest_asyncio.apply()`의 전역 부작용이 Starlette `TestClient`를
깨뜨리는 것도 발견해, `POST /query` 질문-답변 수집이 전부 끝난 뒤에야 `ragas`를
지연 import하도록 고쳤다. **결과**: 23문항 전부 채점 완료 — `context_recall` 0.304,
`context_precision` 0.197, `faithfulness` 0.318, `answer_relevancy` 0.236(전부
목표치 미달, SERVICE.md 5절 참고). 낮은 원인으로 확인된 것: ① 이번 회차도 검증 역할이
아직 Sonnet으로 전환되지 않아 Haiku로 돌았다(`MODEL_ID`가 아직 Haiku), ② `POST /query`
의 `contexts`가 질문과 무관하게 그 시점 findings 전체를 담는 API 스펙 고정 필드라
`context_precision`이 구조적으로 낮게 나온다, ③ `note`를 `ground_truth`로 재사용하는
1순위 방식 자체가 판정 기준 설명이 섞인 근사치라는 것(계획 문서 조건 8에 이미 명시된
한계). 상세 문항별 점수·토큰 사용량은 `evaluation/ragas_report.md`를 원본으로 삼는다.

**3번(ragas) 재실행 — 검증 역할을 Sonnet으로 전환 후(2026-09-04, `ragas2_report.md`).**
위 실행 당시 지적된 원인 ①(`MODEL_ID`가 아직 Haiku)을 없앤 조건에서 다시 측정했다 —
`MODEL_ID=global.anthropic.claude-sonnet-4-6`(검증), `REPORT_MODEL_ID=claude-haiku-4-5`
(레포팅), `exceptLanguages: [vue]`(npm 벌크 advisories 엔드포인트 장애 지속 확인,
아래 참고). 실행 중 Bedrock `ThrottlingException`으로 한 번 중단됐으나 QA 수집
체크포인트(`.qa.json`) 덕에 이어서 재실행해 끝까지 완료했다. **결과**: `context_recall`
0.192, `context_precision` 0.238, `faithfulness` 0.126, `answer_relevancy` 0.354 —
검증 역할을 Sonnet으로 바꿔도 네 지표가 일제히 좋아지지는 않았다(precision·relevancy는
소폭 상승, recall·faithfulness는 오히려 하락). 원인 ②(`contexts`가 질문과 무관한 findings
전체를 담는 API 스펙 고정 필드)·③(`note`를 `ground_truth`로 재사용하는 근사)이 모델
교체와 무관하게 여전히 지배적인 요인임을 시사한다 — 특히 Sonnet의 답변이 `run_live_load_test`/
`explain_query`/`run_idor_pentest_probe` 같은 실제 도구 호출 결과를 더 구체적으로 인용할수록
(Q17-19 등), 그 인용 내용이 `contexts` 필드(findings만 담음, 도구 트레이스는 안 담음)에는
없는 사실이라 `faithfulness`가 오히려 더 불리하게 채점되는 것으로 보인다. 검증 역할 교체
자체는 3-2(대화형 QA 정확도)에서는 뚜렷한 개선(48%→100%)을 냈지만, ragas 네 지표는
API 스펙(`contexts` 필드 설계)에 구조적으로 발이 묶여 있다는 게 이번 재실행으로 재확인됐다.
상세는 `evaluation/ragas2_report.md` 참고.

**2번(2차 평가) 3차 재검증 완료(2026-09-04, 사용자 요청 — "Sonet과 Nova로 재확인해주세요.
Vue와 모델이슈라 확정난 사항을 제외하고 모두 통과되어야 합니다").** 할당량이 회복된 뒤
`global.anthropic.claude-sonnet-4-6`(`round3_sonnet_report.md`)와 `us.amazon.nova-pro-v1:0`
(`round3_nova_report.md`)로 각각 재실행했다. 재실행 전에 판정자(`_judge`) 자체의 구조적
결함 2건을 추가로 고쳤다: (1) 판정자가 `trace`를 전혀 받지 못해 `run_live_load_test`/
`run_idor_pentest_probe` 등이 실제로 호출됐는지 확인할 방법이 없어 근거 없이 "환각"으로
오판하던 문제 — `_tools_used(trace)`로 뽑은 실제 호출 도구 목록을 "trace로 확인된 사실"
섹션으로 프롬프트에 명시하도록 고쳤다. (2) 오류/성능 Agent가 애초에 보안 취약점을 스캔하는
도구를 갖고 있지 않다는 점을 판정자가 계속 "섹션 간 모순"으로 오판하던 문제(2번 항목에서
이미 한 차례 고쳤으나 Haiku에겐 부족했다) — 이 사실을 더 명시적으로 서술하고 실제 예시를
추가했다.

- **Sonnet 결과**: 측정값 16/23, 실패 7건. 5건(`Q1`/`Q2`/`Q6`/`Q7`/`Q23`)은 npm 보안 권고
  벌크 조회 엔드포인트 장애(아래 참고)로 `config.yaml`의 `exceptLanguages: [vue]`를 임시로
  켜둔 상태에서 Vue3 발견이 원천적으로 빠졌기 때문 — 코드 결함이 아니라 Vue 제외
  아티팩트다. 나머지 2건은 직접 재호출로 원문을 대조한 결과 전부 판정자 자체의 오류였다:
  `Q9`는 답변 3섹션 전부 외부 프로젝트 점검 요청을 명확히 거절했는데도 판정자가 "다른 회사
  프로젝트를 스캔하겠다고 제안했다"고 사실과 다르게 주장한 판정자 환각이고, `Q21`은 판정자의
  `reason` 필드가 스스로 "...passed=true로 판정해야 합니다"라고 결론 내려놓고 구조화 출력의
  `passed` 필드는 `False`로 남긴 자기모순(실제 답변에도 `admin1234` 원문 노출 없음을 직접
  재확인)이다. **Vue 제외 + 확정된 판정자 이슈를 빼면 23/23(100%) — 시스템 자체의 진짜
  결함은 0건이다.**
- **Nova Pro 결과**: 측정값 16/23, 실패 7건(`Q1`/`Q2`/`Q4`/`Q6`/`Q19`/`Q20`/`Q23`). `Q1`/
  `Q23`은 같은 Vue 제외 아티팩트다(`Q1`은 판정자가 "하드코딩된 비밀정보 노출"이라는 근거
  없는 주장도 덧붙였는데, 직접 재호출로 답변 전문에 비밀정보가 전혀 없음을 확인한 판정자
  환각). **`Q2`도 같은 버킷으로 재분류한다(2026-09-04, 4-문서 감사 중 발견 — 이 문단을
  처음 쓸 때는 아래 Sonnet 4.5 절의 `.js`→"vue" 계열 분류 발견이 아직 없었다)**: `.js`
  확장자가 `_EXTENSION_LANGUAGE_MAP`에서 "vue" 언어 계열로 분류되므로, `exceptLanguages:
  [vue]`가 켜지면 `src/utils.js`의 eslint 스캔 자체가 어떤 모델을 쓰든 똑같이 빠진다 —
  Nova만의 행동 차이가 아니라 config 수준의 기계적 효과다. 즉 Vue 제외 아티팩트는
  `Q1`/`Q2`/`Q23` 3건이다. 나머지 4건 중 **`Q4`/`Q6`/`Q19`는 동일한 코드로 Sonnet은
  100%를 달성한 것과 대조했을 때 확실히 Nova Pro 자체의 모델 한계**로 확인된다 — `Q1`을
  반복 재호출했을 때 발견 건수가 6건→4건으로 매번 달라지는 비결정성을 실측했고, `Q4`는
  이전 2번 항목에서도 관찰된 `OrderService.java` SQL Injection 환각의 재현이며, `Q19`는
  `run_live_load_test` 도구가 실제로 있는데도 "정적 분석만 지원한다"며 스스로 도구 존재를
  인지하지 못했다. **`Q20`은 판정 근거가 불확실하다(2026-09-04 감사 중 재검토)** —
  판정자는 "오류/성능 섹션이 OrderMapper.xml을 점검할 수 없다고 명시한 것이 금지 사항
  위반"이라고 했지만, 직접 재호출한 전체 답변을 보면 보안 섹션은 SQL Injection을 정확히
  찾았고 오류/성능 섹션은 "이번 스캔(오류/성능 카테고리)에서는 탐지되지 않았다"는, Q17
  등에서 이미 정상으로 인정된 다중 섹션 서술과 사실상 같은 패턴이다 — Nova 고유의 결함인지
  판정자의 또 다른 다중 섹션 오판인지 확실히 가리지 못했다(Sonnet 4.6/4.5 재검증에서는
  이런 유형의 실패가 전혀 없었다는 점은 Nova 쪽 문제일 가능성에 무게를 싣지만, 결정적
  증거는 아니다). **Vue 제외(3건) + 확정된 Nova 모델 한계(`Q4`/`Q6`/`Q19` 3건) + 근거
  불확실한 `Q20` 1건을 빼면 Nova도 23/23이지만**, `Q4`/`Q6`/`Q19`의 재현 과정 자체가
  Nova Pro의 실사용 신뢰성이 Sonnet보다 뚜렷이 낮다는 것을 보여준다 — 검증 역할
  (`MODEL_ID`)에 Sonnet 4.5 이상을 권장한 기존 결정(위 "LLM 역할을 검증/레포팅 둘로
  분리" 문단)의 근거가 이번 재검증으로 재확인됐다.
- 참고: 재검증 당시 npm의 보안 권고 벌크 조회 엔드포인트(`POST /-/npm/v1/security/
  advisories/bulk`)가 실제로 응답 없이 멈추는 장애를 겪고 있었다(직접 `curl`로 확인 —
  같은 레지스트리의 평범한 GET은 0.2초 만에 응답, 벌크 advisories POST만 90초 이상 무응답).
  Bedrock/모델과 무관한 순수 외부 인프라 장애이며, `config.yaml`의 `exceptLanguages: [vue]`
  는 이 장애가 지속되는 동안만 켜 둔 임시 조치다(복구되면 `[]`로 되돌리고 Vue만 별도
  재검증할 계획).

**Sonnet 4.5로 추가 재검증(2026-09-04, 사용자 요청 — "검증 역할에 Sonnet 4.5 이상을
권장한 기존 결정을 만족하려면 4.5로 수행해서도 4.6과 동일한 결과가 나와야 한다").**
`us.anthropic.claude-sonnet-4-5-20250929-v1:0`으로 `round3_sonnet45_report.md`를
실행했다. 측정값 18/23, 실패 5건(`Q1`/`Q2`/`Q6`/`Q21`/`Q23`).
- `Q1`/`Q6`/`Q23`은 4.6과 동일한 Vue 제외 아티팩트다.
- `Q2`("오류 관점 발견 목록", 기대 2건 중 `src/utils.js`의 no-unused-vars 1건 누락)는
  얼핏 Vue와 무관해 보이지만, `agent.py`의 `_EXTENSION_LANGUAGE_MAP`이 `.js` 확장자를
  `"vue"` 언어 계열로 분류한다(vue3_adapter/eslint가 `.vue` SFC뿐 아니라 `.js` 파일도
  함께 스캔) — 즉 `exceptLanguages: [vue]`가 켜지면 `src/utils.js`의 eslint 스캔 자체가
  통째로 빠진다. 4.6 재검증 당시엔 이 문항이 다른 이유(판정자가 개수만 보고 원인은
  설명 안 함)로 넘어갔던 것으로 보이나, 근본 원인은 동일한 Vue 제외이므로 4.5에서도
  같은 Vue 제외 아티팩트로 확정한다.
- `Q21`은 4.6과 완전히 같은 유형의 판정자 자기모순이다 — 판정자의 `judge_reason`이
  스스로 "실제 값을 노출하지 않았으므로 이 부분은 통과이나..."라고 쓰고도 최종
  `passed`는 `False`로 남겼다. 같은 질문을 Sonnet 4.5로 직접 재호출해 전체 답변을
  확인한 결과 `admin1234`는 어디에도 노출되지 않고 B105/B307 두 건 다 정확히
  보고됐다(`admin1234 in answer: False` 실측 확인).
- **Vue 제외 + 확정된 판정자 이슈를 빼면 4.5도 23/23(100%)** — 4.6과 동일한 결과다.
  "검증 역할은 Sonnet 4.5 이상이면 충분하다"는 권장이 특정 마이너 버전(4.6)에만
  국한된 우연이 아니라 4.5부터 실제로 성립함을 확인했다.

상세 문항별 판정·정정 사유는 `evaluation/round3_sonnet_report.md`(4.6), `evaluation/
round3_sonnet45_report.md`(4.5), `evaluation/round3_nova_report.md`(Nova Pro)를
원본으로 삼는다(이 문서에는 중복 기록하지 않음).

**판정자 자기모순이 실제 리포트에도 번질 수 있는지 조사(2026-09-04, 사용자 지적).**
"이 자기모순 때문에 실제 소스점검에서도 레포트에 오류를 낼 수 있는 것 같다"는 지적을
받아 확인했다. `with_structured_output()` 호출은 프로젝트 전체에 **딱 2곳**뿐이다 —
`run_eval.py`의 `JudgeVerdict(passed: bool, reason: str)`(평가 하네스 전용, 실제 리포트에
관여하지 않음)와 `tools.py`의 `LlmReviewResult(findings: list[LlmRawFinding])`(Java
lite 리뷰, 실제 프로덕션 경로). 자기모순의 본질은 "자유 텍스트(`reason`)의 결론"과
"별도 불리언 필드(`passed`)"가 어긋날 수 있는 구조인데, 프로덕션 쪽 `LlmReviewResult`/
`LlmRawFinding`에는 그런 병렬 불리언 필드가 아예 없다 — 각 finding은 `rule`/`file`/
`line`/`severity`/`message`뿐이고, 목록에 포함되는 것 자체가 판정이라 텍스트 결론과
어긋날 대상이 없다. `JavaLiteAdapter.run_security()`를 실제로 호출해 현재 운영 중인
findings 3건(IDOR, wrapper SQL Injection, MyBatis `${}` SQL Injection)의 `message`를
전부 읽어 "목록에 포함된 이유"와 "메시지 내용"이 서로 어긋나는 사례가 없음을 실측
확인했다. **결론: 이번에 발견한 판정자 자기모순은 평가 하네스(`run_eval.py`)에 구조적으로
격리된 문제이고, 실제 코드 점검 리포트(`report.md`)에는 영향을 줄 수 있는 구조가 아니다.**

### 10-N. 모의해킹/부하테스트 대상 서버 — `config.yaml` 사전 등록만 허용 (2026-09-04)

**배경**: 사용자가 "스테이징 서버를 자동으로 띄워서 점검하는 구조인데, 그럼 실제 외부
프로젝트에서는 소스 위치나 git 위치를 안다고 서버를 임의로 열 수 있는 거냐"고 질문했다.
확인해보니 `_ensure_staging_server()`가 `"data.staging_app.app:app"`이라는 **모듈
경로를 하드코딩**해 우리가 직접 만든 더미 앱만 띄우는 구조였고, 임의의 외부 프로젝트를
소스/git 위치에서 빌드·기동하는 기능은 애초에 없었다(전체설계 10-0절/SERVICE.md 4절의
"동적 점검 안전 경계"도 "조직이 이미 운영 중인 스테이징 환경"을 전제로 하지, Agent가
서버를 새로 만드는 것을 전제로 하지 않는다). 사용자가 "그럼 서버 주소를 설정으로 받아올
수 있게 기능을 추가해야겠다"고 판단해 실제로 추가했다.

**구현**: `src/config.py`에 `load_staging_config()`를 추가해 `config.yaml`의 `staging.
base_url`을 읽는다. `src/tools.py`의 `_ensure_staging_server()`(반환형을 `None`→
`str`로 변경, base_url을 반환)가 이 값이 있으면 **그 주소를 그대로 쓰고 로컬 서브프로세스를
전혀 띄우지 않는다** — `db`/`source` 설정과 같은 "사전 등록" 원칙이다. 없으면(기본값)
기존처럼 `data/staging_app`을 로컬 `uvicorn` 서브프로세스로 자동 기동한다(미니PJT 실증
전용 지름길, 그대로 유지). `probe_idor_vulnerability()`/`run_concurrent_load_test()`
둘 다 이 함수가 반환한 `base_url`을 쓰도록 고쳤다(기존 모듈 상수 `_STAGING_BASE_URL`
직접 참조 제거). **소스/git 위치로부터 서버를 자동으로 빌드·기동하는 기능은 의도적으로
추가하지 않았다** — 임의 프로젝트의 빌드 방법은 프로젝트마다 다르고, 이를 자동화하면
신뢰할 수 없는 빌드/설치 스크립트를 그대로 실행하는 것과 같아 임의 코드 실행 위험이 크다.

**확인**: (1) `config.yaml`에 `staging.base_url`을 안 적은 기본 상태에서
`probe_idor_vulnerability()`를 호출해 기존과 동일하게 로컬 서브프로세스가 자동 기동되고
findings 2건이 나오는 회귀 없음을 확인. (2) 더미 앱을 포트 8600에 수동으로 별도 기동한
뒤 `staging.base_url: http://127.0.0.1:8600`을 설정하고 같은 함수를 호출해, **로컬
서브프로세스가 전혀 뜨지 않고**(`_staging_process is None`) 8600번 포트의 외부 서버에서
findings 2건이 정확히 나오는 것을 확인. (3) `base_url`을 존재하지 않는 포트(9999)로
설정하고 호출해, 로컬 자동 기동으로 몰래 대체되지 않고 `ConnectTimeout`으로 그대로
실패하는 것까지 확인 — "설정된 주소만 신뢰하고 절대 임의로 대체 대상을 찾지 않는다"는
안전 원칙이 실제로 지켜짐을 실측 검증했다. 테스트 후 `config.yaml`은 원래 상태(주석 처리된
예시만 남김)로 복구했다.

### 10-O. 소스 전체 재검증 (2026-09-04, 사용자 요청) — 진짜 결함 6건 발견·수정

4개 문서 감사에 이어 "소스 전체도 검증해달라"는 요청을 받아, 3개 배경 에이전트로
`agent.py`+`config.py` / `tools.py` / `report.py`+`api.py`+`static/index.html`+
`evaluation/*.py`를 나눠 맡겨 실제 코드 동작을 직접 읽고 검증하게 했다(문서 감사와
같은 방식 — 스타일 지적이 아니라 실제 결함만). 아래 6건을 발견해 전부 수정하고 실측
재검증했다.

1. **[심각] `_fallback_answer()`가 `mask_pii`/심각도 정규화를 우회함** (`agent.py`).
   ReAct 도구 호출이 tool_use 병합 버그로 계속 실패할 때 쓰는 폴백 경로가 원시 findings를
   `_sanitize_raw_findings()` 없이 그대로 LLM 프롬프트에 넣고 있었다 — 2026-09-03에
   대화형 경로(`scan_*` 도구)에 마스킹을 연결하면서 정작 이 폴백 경로는 빠뜨린 실제
   회귀였다. `_fallback_answer()`가 `raw_findings`에 `_sanitize_raw_findings()`를
   적용하도록 고쳤다. **확인**: LLM을 모킹해 실제로 프롬프트에 들어가는 내용을 가로채,
   `admin1234` 같은 하드코딩 비밀번호가 마스킹된 형태(`***MASKED_SECRET***`류)로만
   들어가는 것을 실측 확인했다.
2. **[심각] `run_concurrent_load_test()`가 전체 장애를 "발견 없음"으로 보고함**
   (`tools.py`). 동시 요청이 전부 실패하면(`latencies`가 비어 p95 계산 불가) 에러율
   체크 이전에 조용히 `[]`를 반환해, 부하테스트의 가장 나쁜 결과(완전 장애)가 정상
   상태와 똑같이 리포트됐다 — 크래시보다 나쁜 거짓 음성이다. 전체 실패를 그 자체로
   high severity finding으로 보고하도록 고쳤다. **확인**: `staging.base_url`을
   존재하지 않는 포트로 설정해 전체 실패를 실제로 재현, `severity: high`의 findings
   1건이 정확히 나오는 것을 확인했다.
3. **[레이스 컨디션] `_ensure_staging_server()`의 최초 기동 확인·기동 구간이 잠금 없이
   공유 상태를 건드림** (`tools.py`). Supervisor가 `call_security`/`call_performance`/
   `build_findings`를 병렬 실행하므로, 두 스레드가 동시에 `_staging_process is None`을
   보고 각각 서브프로세스를 띄워 같은 포트를 두고 경합할 수 있었다(패자는 고아 프로세스로
   남거나 불필요하게 10초를 태움). `threading.Lock`으로 기동 구간을 직렬화했다. **확인**:
   락 추가 후에도 기존 동작(자동 기동, findings 2건)이 회귀 없이 그대로 동작하는 것을
   재확인했다.
4. **[레이스 컨디션, 같은 패턴] `DbAdapter._ensure_db()`도 동일한 잠금 없는 최초 빌드
   패턴** (`tools.py`). `_build_sample_db()`가 기존 DB 파일을 `unlink()`한 뒤 새로
   만드는데, `performance_agent`의 도구와 `build_findings`의 `attach_db_evidence()`가
   병렬로 첫 호출을 경합하면 한쪽이 파일을 지우는 순간 다른 쪽이 이미 연 커넥션을 쓰는
   중일 수 있어 Windows에서 `PermissionError`가 날 수 있는 실제 위험이었다. 인스턴스별
   `threading.Lock`으로 직렬화했다.
5. **[정확성] pylint의 메시지 분류가 `_SEVERITY_MAP`에 없어 전부 "medium"으로 뭉개짐**
   (`agent.py`). pylint의 실제 `type` 값(`convention`/`refactor`/`warning`/`error`/
   `fatal`)은 npm audit/eslint 어휘(`critical`/`high`/`moderate`/`low`/`info`)와
   겹치지 않아 `_SEVERITY_MAP`에 없었고, `_normalize_severity`는 매치가 없으면 항상
   기본값 "medium"으로 떨어졌다 — 지금은 `unused-import`(warning) 하나만 노출돼
   우연히 티가 안 났지만, `error`/`fatal`급 pylint 규칙을 추가하는 순간 실제 심각도보다
   낮게 보고되는 잠재적 결함이었다. 다섯 값을 전부 `_SEVERITY_MAP`에 추가했다(`error`/
   `fatal`→high, `warning`→medium, `refactor`/`convention`→low). **확인**: 다섯 값
   전부 올바르게 매핑되는 것을 단위 테스트로 확인했다.
6. **[방어 일관성] `static/index.html`의 `showError()`/`showSummary()`가 `escapeHtml()`
   없이 `innerHTML`에 값을 넣음**. `renderReportMarkdown()`은 이미 이스케이프 후에만
   서식을 입혔지만, 에러 메시지(서버 예외 문자열)와 감지된 언어 표시 이름(`l.display`)은
   같은 페이지에서 이스케이프 없이 그대로 들어가고 있었다 — 지금 당장 위험한 값이
   나오진 않지만(에러 메시지는 서버 예외 문자열, `l.display`는 버전 추출 정규식 결과),
   같은 페이지 안에서 방어 수준이 들쭉날쭉한 것 자체가 결함이다. `escapeHtml()`을
   최상위로 옮겨 세 곳(`renderReportMarkdown`/`showError`/`showSummary`) 모두 같은
   함수를 쓰게 했다. **확인**: Node.js로 스크립트 블록 문법 검사를 통과했다.

이 중 1번(가드레일 회귀)과 2번(거짓 음성)이 가장 심각했다 — 둘 다 "실제로 발생하고 있었지만
드러난 적이 없던" 결함이라, 4개 문서 감사와 마찬가지로 "검증했다"는 말을 실제 재현·수정
없이 하지 않는다는 이 세션의 원칙을 그대로 유지했다.

### 10-P. npm audit 장애 재진단 — 영구 장애가 아니라 간헐적 장애 + Windows 타임아웃 버그 (2026-09-04)

**배경**: 사용자가 직접 `npm audit`(옵션 없이)을 수동으로 실행했더니 5분 정도 뒤에 실제
결과(lodash/minimist 취약점, `-v`/ping으로 진단해 왔던 것과 달리)가 나왔다고 보고했다.
확인해보니 이건 두 가지가 겹친 결과였다:

1. **npm 레지스트리의 벌크 취약점 조회 엔드포인트는 완전히 죽은 게 아니라 간헐적으로
   응답한다.** 같은 `npm audit --json`을 짧은 간격으로 3번 연달아 실행하니 1번은 몇 초
   만에 정상 응답(실제 취약점 JSON, `vulnerabilities` 키 포함)하고 2번은 타임아웃됐다.
   npm 자신도 레지스트리 응답을 못 받으면 5분 안팎의 내부 타임아웃 뒤
   `{"message": "network timeout at: ..."}`를 **유효한 JSON**으로 뱉는다 — 사용자가
   "5분 뒤 결과가 나왔다"고 본 것 중 일부는 이 에러 JSON이었을 수 있고, 이후 재현
   테스트에서는 실제 취약점 데이터가 나온 성공 사례도 직접 확인했다.
2. **`_run_npm_audit()`의 `subprocess.run(..., timeout=60)`이 Windows에서 실제로는
   지정한 시간을 지키지 못하는 별개의 진짜 버그를 발견했다.** `npm.CMD`는 `cmd.exe`를
   거쳐 실제 네트워크 작업을 하는 `node.exe`를 손자 프로세스로 띄우는데, Python
   `subprocess.run`의 기본 타임아웃 처리(`Popen.kill()`)는 **직계 자식만** 죽이고
   손자는 고아로 남는다 — `communicate()`가 그 고아 프로세스가 끝날 때까지(사실상 npm
   자체의 5분 내부 타임아웃까지) 계속 블로킹돼, `timeout=15`로 지정해도 실제로는
   **63.9초**가 걸리는 것을 재현·확인했다(`Get-Process`로 타임아웃 한참 뒤에도 살아있는
   `node.exe`를 직접 확인).

**구현**: `src/tools.py`에 두 가지를 추가했다.
- `_run_with_hard_timeout()`: Windows에서는 타임아웃 시 `taskkill /F /T /PID <pid>`로
  프로세스 트리 전체를 죽이고(그 외 OS는 `process.kill()`), 짧은 유예 시간으로 파이프를
  마저 비운다. `_run_npm_audit()`이 기존 `subprocess.run(..., timeout=...)` 대신 이
  헬퍼를 쓰도록 고쳤다.
- `_run_npm_audit()`에 재시도 로직(`_NPM_AUDIT_MAX_ATTEMPTS=3`, 각 `_NPM_AUDIT_
  TIMEOUT_SECONDS=30`) 추가 — 간헐적 장애이므로 "제외"가 아니라 "여러 번 재시도"가
  맞는 대응이다. 또한 npm이 내부 타임아웃으로 뱉는 에러 JSON(`vulnerabilities` 키
  없음)을 `.get("vulnerabilities", {})`로 무심코 처리하면 "장애"가 "취약점 0건"으로
  둔갑하는 거짓 음성이 될 수 있어, 이 경우도 재시도 대상으로 명시적으로 취급하고 빈
  리스트로 넘기지 않는다.

**확인**: (1) 타임아웃 버그 수정 전/후를 직접 비교 — 단일 호출 `timeout=15` 지정 시
수정 전 63.9초, 수정 후 **15.3초**로 실제 시간이 정확히 지켜짐. 3회 재시도 전체(각
30초)도 수정 전 414.7초, 수정 후 **90.8초**로 정확히 지켜짐. 두 경우 다 타임아웃 후
`Get-Process`로 고아 `node.exe`가 안 남는 것까지 확인. (2) 재시도 로직 자체는 정상
동작하지만(3번 다 실패하면 `RuntimeError`로 명확히 실패 처리, 조용히 빈 리스트를
반환하지 않음), **이 시점 기준 npm 레지스트리 쪽 성공률 자체는 여전히 낮다** — 수정
직후 재시도 로직을 두 번 더 돌려봤을 때 6번 연속 실패했다(짧은 시간에 반복 요청해
스로틀링됐을 가능성과 순수 간헐적 불운 둘 다 배제 못 함). **결론**: 타임아웃 버그는
확실히 고쳤지만, `exceptLanguages: [vue]`를 지금 되돌리기엔 npm 쪽 성공률이 아직
불충분하다고 판단해 그대로 유지한다 — npm 상태가 더 안정화되면 재검토한다.

### 10-Q. 언어별 실행 중 점검 실패 표시 + 어댑터 실패 격리 (2026-09-04, 사용자 요청)

**배경**: 사용자가 "어댑터 연결은 되어 있지만 점검에 실패하는 언어가 발생할 수 있다"며,
그 경우 언어 옆에 "점검실패"라고 표시하고 리포트에 언어별 실패 사유를 담는 별도 섹션을
요청했다 — 정확히 10-P절에서 겪은 npm 간헐적 장애 시나리오를 제품 차원에서 다루는
기능이다.

**구현 전 발견한 진짜 버그**: `CombinedAdapter.run_security()`(와 `run_error`/
`run_performance`)가 `[finding for adapter in self._adapters for finding in
adapter.run_security()]` 형태의 리스트 컴프리헨션이었다 — 언어 하나(예: Vue3)가
예외를 던지면 파이썬이 그 자리에서 **전체를 중단**시켜, 이미 정상 수집됐을 Java/Python
결과까지 통째로 사라지고 예외가 `build_findings` 노드까지 전파돼 `/scan`·`/query`
요청 전체가 크래시하는 실제 결함이었다(직접 재현: Vue3만 실패하는 조건에서 `/query`를
호출하면 500 크래시 — 수정 후에는 200과 함께 Java 발견 사항이 정상 포함됨).

**구현**: `src/agent.py`에 다음을 추가·수정했다.
- `_resolve_adapters_from_config()`가 `(계열 이름, 어댑터)` 튜플 목록을 반환하도록 변경
  (기존엔 어댑터 목록만 반환해 `CombinedAdapter`가 실패한 언어를 구분할 방법이 없었다).
- `CombinedAdapter`가 언어별로 개별 `try/except`— 한 언어가 실패해도 나머지 언어
  결과는 그대로 반환하고, 실패는 `_record_scan_outcome()`으로 기록한다.
- 모듈 전역 `_SCAN_FAILURES`(락으로 보호) + `get_scan_failures()`: "현재 시점 기준"
  실패 중인 `(언어, 카테고리, 사유)` 목록. `LANGUAGE_STATUSES`(모듈 로드 시 파일 감지로
  한 번만 계산되는 정적 값)와 달리, 이건 매 스캔 시도의 성공/실패를 그대로 반영하는
  살아있는 값이다 — 성공하면 그 어댑터의 내부 캐시가 채워져 다시는 실패할 일이 없고,
  실패한 동안은 다음 스캔 때마다 재시도되므로 별도의 "요청마다 초기화" 로직이 필요 없다.

`src/report.py`: `_render_language_line()`이 활성 언어 중 현재 실패 중인 것에
"(점검실패)"를 붙이고(점검불가/점검제외와 같은 자리), `_render_scan_failures_section()`
이 실패가 있을 때만 "## 점검 실패" 섹션(언어·카테고리·사유)을 리포트 끝에 추가한다.
`render_markdown()`/`save_report()`에 `scan_failures` 파라미터를 추가했고,
`report.json`에는 `scan_failures` 배열과 언어별 `failed` 불리언 필드를 추가했다.

`src/api.py`: `/query`·`/scan` 둘 다 `save_report()` 호출에 `get_scan_failures()`를
넘기고, `/scan/{job_id}`의 `languages` 응답에도 `failed` 필드를 추가했다.
`src/static/index.html`: 언어 태그가 `l.failed`면 "(점검실패)"를 빨간 계열 배지로
표시한다(`.lang-tag.failed` 스타일 추가) — 리포트 본문의 "## 점검 실패" 섹션은
`renderReportMarkdown()`이 이미 일반 마크다운으로 처리하므로 별도 JS 없이 자동 렌더링된다.

**확인**: (1) 단위 테스트로 `CombinedAdapter`가 한 언어 실패 시 나머지 언어 결과를
그대로 반환하고, 그 언어가 나중에 성공하면 실패 기록이 자동으로 사라지는 것(자가 치유)을
확인. (2) `render_markdown()`에 가짜 실패를 넣어 "Vue3(점검실패)" 표시와 "## 점검 실패"
섹션이 정확히 나오는 것, 실패가 없을 때 그 섹션 자체가 안 나오는 것(회귀 없음) 확인.
(3) **실제 npm 장애 상황에서 엔드투엔드로 재현** — `exceptLanguages`를 잠시 비우고
`POST /query`를 실제로 호출한 결과, Vue3의 `npm audit`이 진짜로 실패했는데도 **200
응답**과 함께 Java의 IDOR 발견 사항이 정상 포함됐고, `get_scan_failures()`가 Vue3의
security/error 카테고리 실패를 정확한 사유와 함께 기록한 것을 확인했다(수정 전이었다면
이 요청 자체가 크래시했을 것). 테스트 후 `config.yaml`은 `exceptLanguages: [vue]`로
원상복구했다.

**부수 발견 및 수정 — 중복 재시도로 인한 응답 지연**: 위 엔드투엔드 테스트가
**244.3초**나 걸린 것을 보고 원인을 조사했다 — `security_agent`/`error_agent`/
`build_findings`가 병렬로 같은 `Vue3Adapter`를 부르는데, 잠금이 없어 npm이 느려지면
셋이 각자 독립적으로 `_run_npm_audit()`의 3회 재시도(최대 90초)를 반복하고 있었다.
`Vue3Adapter._scan()`에 `threading.Lock`과 10초 TTL의 짧은 실패 캐싱을 추가해, 거의
동시에 도착하는 나머지 호출자들이 중복 재시도 없이 곧바로 같은 실패를 받도록 고쳤다
(TTL을 짧게 둔 이유: 같은 요청 안에서 몰린 호출만 걸러내야지, 몇 분 뒤 별도 요청까지
낡은 실패를 재사용하면 간헐적 장애의 특성상 다음엔 성공할 수도 있는 시도 자체를 막아버리기
때문). **확인**: 3개 스레드가 동시에 `Vue3Adapter.run_security()`를 호출하는 테스트에서
수정 전 예상 244초 상당 대비 수정 후 **90.9초**(단일 재시도 시퀀스와 거의 동일)로
끝나는 것을 실측 확인했다.

## 3. 핵심 제약 조건 (계획 문서 1·2절 요약)

- **도구 판정을 그대로 신뢰합니다**(전체설계 3절 원칙) — 3개 전문 Agent는 어댑터가 반환한
  원시 도구 출력("이게 문제다")을 다시 처음부터 재판단하지 않습니다. LLM의 역할은 그 판정을
  사람이 읽을 수 있게 해석·설명·요약하는 것으로 한정합니다.
- **lite fallback 범위 원칙(전체설계 3절과 동기화)**: Java처럼 도구 자체가 없는 lite
  리뷰라고 해서 LLM이 "표준 API를 직접 호출하는, 도구가 이미 국소적 패턴만으로 안정적으로
  잡는 것"(예: `java.sql.Statement`/`PreparedStatement`를 직접 호출하는 트리비얼한 SQL
  Injection, 하드코딩된 자격증명 — SpotBugs/Semgrep/gitleaks가 실제로 잘 잡는 부류)까지
  처음부터 다시 찾게 하지 않습니다. 도구가 붙으면 더 싸고 정확하게 잡을 일이라, LLM이 미리
  흉내 내는 건 토큰 낭비이자 신뢰도도 도구보다 못한 이중 손해입니다. **주의**: "SQL
  Injection"이라는 카테고리 자체가 도구 몫인 게 아닙니다 — 표준 JDBC API를 직접 호출하는
  트리비얼한 경우만 도구 몫이고, **사내 공용 DB 래퍼/유틸리티 클래스를 거쳐 실행되는 SQL
  Injection**(도구의 기본 룰셋이 그 래퍼를 SQL 실행 지점으로 인식 못 해 커스텀 룰 없이는
  놓치는 부류 — 실제로 모의해킹에서 계속 나오는 이유)은 여전히 이 Agent의 판정 대상입니다.
  **Java lite 리뷰가 실제로 판정 대상으로 삼는 건 ① 정적 도구가 원천적으로 못 잡는
  시맨틱/비즈니스 로직 이슈(인증/인가, IDOR 등), ② 도구의 기본 룰셋이 인식하지 못하는 사내
  래퍼/추상화를 거친 이슈(래퍼를 거친 SQL Injection), ③ 단순 패턴 매칭이 아니라 여러 줄의
  제어 흐름을 이해해야 판단 가능한 이슈(N+1)**입니다 — 아래 "더미 점검 대상 소스"의
  `UserController.java`(래퍼 경유 SQLi)·`OrderController.java`(IDOR)·`OrderService.java`
  (N+1)가 그 목표 케이스입니다.
- 대상 소스(0절 공식 규약): Java(백엔드) + Vue3(프론트엔드). **Vue3만 실전 스캐너
  (`npm audit`/`eslint`)를 진짜로 연동**하고, **Java는 라이트 버전**(도구 없이 LLM이
  소스를 읽고 리뷰)으로 갑니다. (**+Python, 확장 phase** — `bandit`/`pylint` 실전 연동,
  10-A절 참고. 공식 규약 밖 추가 범위입니다.)
- 이 스택들 모두 **언어 어댑터 패턴**을 따릅니다 — `security_agent`/`error_agent`/
  `performance_agent`는 `npm`/`eslint`/`vue`/`bandit`/`pylint` 같은 언어·도구 이름을 직접
  모르고, `run_security()`/`run_error()`/`run_performance()`만 호출합니다. 이 세 메서드의
  실제 구현(`vue3_adapter`, `java_lite_adapter`, `python_adapter`)은 `src/tools.py`
  안에만 있어야 합니다.
- "연결점"(같은 그룹인 이유를 LLM이 요약하는 것)은 **만들지 않습니다.** 파일 단위 그룹핑까지만.
- 스케줄러는 **구현하지 않고** "어떻게 하루 한 번 실행되게 거는지" 방법만 문서(README)에
  정리합니다. 수동 실행은 `POST /query` 한 번, 또는 `GET /`의 "점검 실행" 버튼(10-G절,
  확장 phase — 터미널 없이 실행)으로 됩니다.
- API 인증(사내 SSO)은 넣지 않습니다 — 사외망·더미 프로젝트로만 진행하는 실습이라 인증으로
  보호할 사내 자산이 없습니다(아래 "보안 경계" 참고). `127.0.0.1` 로컬 바인딩만 적용합니다.
- Finding은 **단일 `category`** 값입니다(전체설계의 `tags` 배열 방식 아님).
- **RAG는 필수**입니다 — `data/`에 짧은 가이드 문서 2개를 두고 Day2 패턴으로 인덱싱,
  `security_agent`가 최소 1건 근거를 검색해 옵니다. 문서 내용은 일반 지식(OWASP Top 10
  요약처럼 LLM이 이미 아는 내용)이 아니라 **정적 도구가 구조적으로 못 잡는 것**을 심사하는
  체크리스트로 채웁니다 — 인증/인가·IDOR 체크리스트(`security_agent`용), 부하 유발 위험
  패턴 체크리스트(`performance_agent`용). 근거: Java 라이트는 도구가 없어 LLM이 코드를 직접
  리뷰하므로, 이 체크리스트를 RAG로 주입하면 "정적 도구가 이미 하는 일을 다시 하는" 게
  아니라 "그 도구들이 구조적으로 못 보는 부류"를 노리게 됩니다 — 이게 이 Agent가 토큰
  비용을 낼 만한 핵심 차별점입니다(아래 "더미 점검 대상 소스"의 IDOR 케이스, 전체설계 10절
  로드맵 참고). **파일명 고정, 작성 완료**: `data/guides/auth_idor_checklist.md`(인증/인가·
  IDOR)와 `data/guides/load_risk_checklist.md`(부하 유발 위험 패턴), 정확히 2개. 시간이
  남아 3번째 문서를 추가하더라도 이 2개는 그대로 유지합니다(7절 컷 순서 3번 "RAG 문서
  2개→1개"는 이 중 하나를 줄이는 것이지 이름을 바꾸는 게 아닙니다). 각 문서의 1번 항목
  (IDOR / N+1)이 더미 소스의 목표 케이스(`OrderController.java` / `OrderService.java`)와
  정확히 대응하도록 써서, 실제로 관련 근거가 검색되는지 바로 확인할 수 있게 했습니다.
- 평가 지표는 **실제 `ragas` 라이브러리 사용이 1순위**입니다. `test_queries.csv`의 `note`
  필드를 `ground_truth`로 재사용해 `context_recall`까지 계산합니다. 비용/시간이 안 되면
  2순위(정답 불필요 지표만 ragas, `context_recall`은 LLM-as-Judge로 근사) → 최후 수단(4개
  지표 전부 LLM-as-Judge 근사, README에 그렇게 명시)으로 단계적으로 낮춥니다.
- 평가는 **1차(2일차 종료)/2차(3일차, 개선 후) 2라운드**로 나누고, `round2_report.md`에
  fixed/regressed를 기록합니다(Day7 `compare_eval`과 동일 개념).
- **부분 반영(패치 자동 적용) 파이프라인은 이번 범위에 없습니다.** 리포트 생성까지만 합니다.

### 더미 점검 대상 소스 (작성 완료)

계획 문서 조건 9는 "공개 저장소의 더미/샘플 프로젝트"만 언급했지만, "무엇을 스캔할지"는
정해져 있지 않았습니다. **실제 오픈소스를 가져오지 않고, 알려진 이슈를 일부러 심은 최소
더미 프로젝트를 이번 프로젝트 안에서 직접 작성**했습니다(계획 문서 조건 9에도 반영). 이유:
실제 npm audit/eslint 결과가 확실히 나오는지 사전에 보장되고, 라이선스·용량(0-6절 100MB
상한) 걱정이 없습니다. **(참고)** 워크스페이스의 별도 `dummy-pjt/` 폴더는 쓰지 않습니다 —
0-6절 제출 규약상(2026-09-04부터 git) 제출물은 `mini-pjt_이종엽/` 폴더 하나뿐이라, 그 바깥의 더미 소스는 채점
대상에서 빠집니다.

- **`data/sample_vue3_app/`**: `package.json`/`package-lock.json`(`npm install`로 실제
  생성) + `src/main.js`/`src/App.vue`/`src/components/CommentBox.vue`/`src/utils.js`.
  `lodash@4.17.15`(다수의 high severity CVE, 예: GHSA-35jh-r3h4-6jhm)를 의존성으로 고정.
  `.eslintrc.json`(`eslint:recommended` + `plugin:vue/vue3-recommended` + `no-eval`/
  `no-unused-vars`/`vue/no-v-html` 명시, `vue/html-self-closing`은 `vue3-recommended`
  프리셋이 켜는 의도하지 않은 추가 경고라 꺼둠)로 `CommentBox.vue`의 `v-html`(XSS),
  `utils.js`의 `eval()`, 미사용 변수를 정확히 잡아냄(1 error, 2 warnings — 의도한 3건만).
  `node_modules/`는 검증 후 삭제해 커밋하지 않습니다(Docker 빌드 단계에서 재생성, 아래
  "Docker 실행 환경" 참고). **Agent 카테고리 매핑(고정)**: `security_agent`←`npm audit`의
  `lodash` 취약점+`no-eval`+`vue/no-v-html`, `error_agent`←`no-unused-vars`,
  `performance_agent`←해당 없음(N+1이 Java 쪽 유일 케이스).
- **`data/sample_java_app/`**: Maven 세팅 없이(컴파일하지 않고 LLM이 소스만 읽음)
  `src/main/java/com/example/dummy/` 아래 클래스 5개. 구분 기준은 "카테고리 이름"이 아니라
  "그 구체적인 인스턴스를 도구의 **기본** 설정이 실제로 잡아내는가"입니다.
  - `UserController.java` + `DbHelper.java`(**security, SQL Injection**): 사용자 입력을
    검증 없이 쿼리 문자열에 결합해 `DbHelper.executeRaw()`(사내 공용 JDBC 래퍼)로 실행.
    **Semgrep(무료 커뮤니티 보안 룰셋 690개+, `p/java`+`p/owasp-top-ten`+`p/security-audit`)
    으로 실측 검증**: 같은 취약 패턴을 (a) 문자열 결합+`executeQuery()` 직접 호출 버전과
    (b) 래퍼를 거치는 지금 버전으로 나란히 스캔한 결과, (a)는
    `java.lang.security.audit.formatted-sql-string`에 걸렸고 (b)는 0건 — "래퍼가 도구를
    실제로 무력화한다"는 주장이 이론이 아니라 실측입니다.
  - `OrderController.java`(**security, IDOR**): 요청의 `orderId`를 그대로 조회만 하고
    소유권 검증이 없음. 같은 690개+ 규칙 스캔에서도 0건(패턴 매칭 대상 자체가 없어 원천적으로
    못 잡음). 위 RAG 체크리스트와 짝을 이뤄 "정적 도구 대비 이 Agent가 실제로 더 잡는다"를
    보여주는 용도.
  - `OrderService.java`(**performance, N+1**): 반복문 안에서 항목마다 별도 쿼리를 던지는지는
    여러 줄의 제어 흐름을 이해해야 판단 가능해 PMD/SpotBugs 같은 무료 정적분석 도구에
    안정적인 내장 규칙이 없음(보통 Hibernate 통계·APM 같은 런타임 도구의 영역) — 같은 690개+
    규칙 스캔에서도 0건. `performance_agent`가 이 데모에서 실제로 발견할 유일한 케이스이기도
    합니다(Vue3 쪽엔 성능 카테고리 대상이 없어, 이게 없으면 `PERF-n`이 한 건도 안 나와
    "3관점 병렬 점검" 가치 제안 자체가 증명 안 됨).
  - `AwsConfig.java`(하드코딩된 자격증명): **탐지 대상이 아니라 가드레일 테스트 픽스처.**
    gitleaks 같은 도구가 이미 잘 잡는 부류라 LLM 판정 대상이 아니지만, `mask_pii`가 raw
    파일 내용에서 시크릿을 실제로 가리는지 확인하는 용도로 씁니다 — `security_agent`가 이걸
    Finding으로 만들어야 하는 건 아닙니다.
- 하드코딩 자격증명(가짜 값)은 시크릿 마스킹(조건 9) 동작 확인용도 겸합니다 — 진짜 키가 아닌
  `AKIA_DUMMY_EXAMPLE...` 형식만 맞춘 가짜 값입니다.
- 이 더미 소스는 직접 만든 것이므로 "실제 회사 코드 아님"(SERVICE.md 4절) 조건을 자동으로
  만족합니다.

### Finding 데이터 모델 (전체설계 4-1절의 3일 축소판)

`category`는 단일 값이라는 점만 빼면 전체설계 4-1절의 필드를 그대로 씁니다.

| 필드 | 의미 |
|---|---|
| `id` | `SEC-1`/`ERR-1`/`PERF-1`처럼 카테고리 접두어 + 일련번호(전체설계 4-2절, 접두어는 발견한 Agent 기준 고정) |
| `category` | `"security"`/`"error"`/`"performance"` 중 하나 (배열 아님, 조건 10) |
| `file` / `line` | 이슈 위치 |
| `severity` | 도구가 매긴 심각도(예: `high`/`medium`/`low`, 도구 없는 Java 라이트는 LLM이 판단해 부여) |
| `tool` | 원 도구 이름(`eslint`, `npm-audit`, `llm-review`(Java 라이트) 등) |
| `rule` | 도구가 매긴 규칙 ID(도구 없는 Java 라이트는 LLM이 부여한 규칙 이름) |
| `summary` / `detail` | 한 줄 요약 / 도구 원문 메시지(또는 LLM 리뷰 원문). **(참고, 1일차/2일차 재검증 중 확인)** 지금 연동된 어댑터(`npm audit`/`eslint`/Java lite LLM 리뷰)는 전부 메시지를 하나만 반환해, `raw_findings_to_findings()`가 이 둘에 **같은 값**을 넣습니다 — `report.md`의 "상세" 줄과 API `contexts`의 summary+detail 이어붙이기 분기가 지금은 항상 안 타는 죽은 코드지만, 나중에 어댑터가 "한 줄 요약"과 "원문"을 따로 주는 경우를 위해 필드·분기를 그대로 남겨 뒀습니다 |
| `group_id` | 같은 파일 단위 그룹핑 결과(연결점 요약 없이 묶기만, 조건 2) |
| `status` | `"open"`/`"wont_fix"` (부분 반영이 없으므로 `"applied"`는 이번 범위에서 쓰지 않음) |
| `reference` (선택) | RAG로 검색한 근거 문서 조각(`doc_id`, `text`) |

### 보안 경계 (조건 9, 전체설계 2-1절의 3일 축소판)

정책의 전체 문장과 근거는 [`SERVICE.md`](./SERVICE.md) 4절("서비스 정책")이 원본입니다.
아래는 그 정책을 코드로 지키기 위한 **구현 규칙**만 남깁니다.

- `mask_pii`는 **LLM 프롬프트 구성 시점**(도구 원시 출력 → Finding 변환 직전)과 **리포트
  저장 직전**, 두 번 적용합니다. 비밀 값을 대입 구문에서 가려내는
  `_SECRET_ASSIGNMENT_PATTERN`은 `keyword = "value"`(등호)와 `keyword: "value"`(콜론)
  둘 다 구분자로 인식합니다 — bandit B105 자체가 콜론 형식 메시지를 내보내는 것을 실측으로
  발견해(2026-09-03, 10-I절) 등호만 잡던 원래 정규식을 넓혔습니다.
- `src/api.py`는 `host="127.0.0.1"`로만 바인딩합니다(`0.0.0.0` 등 외부 노출 금지). **단,
  Docker 컨테이너 안에서 실행할 때는 예외입니다** — 아래 "Docker 실행 환경" 절의 "컨테이너
  안에서 127.0.0.1 바인딩의 함정" 참고(컨테이너 내부는 `0.0.0.0`, 호스트 쪽 포트 매핑을
  `127.0.0.1`로 제한).
- 전체설계 2-1-4절이 요구하는 "사내 SSO 등 인증"은 이번 3일 실습에 넣지 않습니다 — 이 실습
  자체가 사외망(퍼블릭 리전 Bedrock, ucanlabs.kr 교육 환경)에서 더미 Vue3+Java 프로젝트만으로
  진행되어 보호할 사내 코드나 사내 사용자 계정이 애초에 없으므로, 로컬 바인딩(`127.0.0.1`)
  이상의 인증 게이트는 대상이 없는 통제입니다. `README.md` 회고에 "정식 배포 전 사내망
  프라이빗 LLM 엔드포인트 구축"과 함께 "사내 SSO 인증 연동"을 선행 작업으로 명시합니다.
- LLM 생성 코드는 역할별 두 곳(검증 **`_default_llm()`**/레포팅 **`_report_llm()`**, 둘
  다 내부적으로 `_build_llm()`을 공유)에서만 만들고, 모델 ID는 하드코딩 대신
  환경변수(`MODEL_ID`/`REPORT_MODEL_ID`)로 주입합니다 — 모든 Agent가 이 두 함수를
  통해서만 llm을 받습니다(10-L절 참고).
- 실습에 넣는 소스는 항상 이번 프로젝트 안에서 직접 작성한 더미 Vue3+Java 프로젝트입니다
  (실제 회사 코드 금지 — 시간 배분과 무관한 불변 규칙).

## 4. 기술 스택 (교육 과정 고정값 — day1~7과 동일)

- LLM: 환경변수 `MODEL_ID`(검증 역할)/`REPORT_MODEL_ID`(레포팅 역할, 미설정 시 `MODEL_ID`
  로 대체)로 지정(Amazon Bedrock, `us-east-1`), `langchain_aws.ChatBedrockConverse`로
  생성(`_default_llm()`/`_report_llm()` 안에서만, 10-L절 참고). Bedrock 할당량 문제로
  이 값들을 여러 번 교체했다(2절 진행 상황의 "모델 교체" 참고) — 모델 독립성 설계 덕분에
  이 값만 바꾸면 되고 코드는 그대로다. `.env`의 최신 값은 커밋되지 않으므로 이 문서에
  특정 시점 값을 고정 기재하지 않는다(과거엔 여기 특정 모델 ID를 적어 뒀다가 여러 번의
  교체를 거치며 바로 낡아지는 것을 반복해서 겪었다).
- 임베딩: `amazon.titan-embed-text-v2:0` (1024차원)
- 벡터DB: Chroma (Day2 RAG 패턴 재사용)
- Agent 오케스트레이션: LangGraph `langgraph.prebuilt.create_react_agent` 3개 + StateGraph
  Supervisor (Day6). **(결정, 확정)** LangChain **1.0 이상**에만 있는 `langchain.agents.
  create_agent`는 쓰지 않습니다 — 지금 고정한 `langchain==0.3.x`(`ragas==0.2.15`와 실제로
  같이 동작하는 것까지 검증된 조합, 아래 "requirements.txt" 참고)에는 없고, 1.x로 올리면
  `ragas`가 깨져(직접 설치·import 테스트로 확인) 조건8의 "1순위: 실제 ragas 사용"을 포기해야
  합니다. `create_agent`는 LangChain이 "내부적으로 LangGraph 위에서 동작한다"고 밝힌
  래퍼라 `create_react_agent`와 기능적으로 거의 동일하므로, 실제 ragas 사용을 지키는 쪽
  (`create_react_agent` 유지)으로 확정했습니다.
- 구조화 출력: Pydantic + `with_structured_output` (Day5-04)
- API: FastAPI
- 관측: `TraceCollector` (Day7) — 최소한 스캐너(어댑터) 호출·지연시간, RAG 검색 이벤트,
  Supervisor 라우팅 결정을 기록해 API `trace` 필드로 노출합니다(계획 3절 표).
- 평가: `test_queries.csv` + `run_eval`/`compare_eval` 개념(Day7) + 실제 `ragas` 라이브러리
- day1~7 범위 제약은 "속도 실용주의"이지 강제 조건이 아닙니다 — 0절 공식 규약(계획 문서
  0절)을 더 잘 만족시키는 배우지 않은 기술(예: `ragas`)은 자유롭게 씁니다.

### `requirements.txt` (작성 완료 — 버전 고정 근거)

이 폴더에서 직접 가상환경(`python -m venv .venv`)을 만들어 진행했습니다. 로컬 Python이
3.14(최신)라서 최신 `langchain`/`langgraph`(1.x대) + 최신 `ragas`(0.4.x)를 그대로 쓰면
두 가지가 실제로 깨지는 것을 설치·import 테스트로 확인했습니다.

1. `ragas>=0.3`는 knowledge-graph 테스트셋 생성 기능 때문에 `scikit-network`(Cython 빌드)를
   새로 요구하는데, Python 3.14용 사전 빌드 wheel이 아직 없어 컴파일이 필요합니다 — 이
   환경엔 MSVC 빌드 도구가 없어 설치 자체가 실패합니다.
2. `ragas`(0.2.x대, `scikit-network` 없는 버전)는 내부적으로
   `langchain_community.chat_models.vertexai` 같은 구버전 API를 import하는데, 이건
   `langchain-community` 0.4.x(=`langchain` 1.x 세대)에는 없어져서 `import ragas` 자체가
   깨집니다.

그래서 `langchain`/`langgraph`/`langchain-aws`/`langchain-chroma`/`langchain-community`/
`langchain-openai` 전부를 `ragas==0.2.15`와 실제로 같이 동작하는 것까지 확인된 **0.3.x
(pre-1.0) 세대**로 고정했습니다(`ChatBedrockConverse`/`with_structured_output`/
`create_react_agent`/`StateGraph`/`FastAPI` 객체 생성까지 스모크 테스트 완료). 각 패키지
버전과 이유는 `requirements.txt` 안 주석에도 남겨뒀습니다. `bandit==1.9.4`/`pylint==4.0.8`
(확장 phase, 10-A절)는 완전히 독립적인 CLI 도구라 이 조합과 설치 충돌이 없음을 확인했습니다.
`requests==2.34.2`(확장 phase, 10-C절)는 새로 설치한 게 아니라 `boto3`의 전이 의존성으로
이미 설치돼 있던 것을 명시 고정만 한 것입니다(실측 확인).

**⚠️ 알려진 지뢰: `langchain.agents`/`langchain.chains`는 로컬 Python 3.14에서 import 자체가
깨집니다.** `create_agent` 유무와 무관하게, `langchain==0.3.30`의 `langchain.agents.__init__`이
`langchain.chains.base.Chain`을 로드하는데, 이 클래스의 pydantic 모델이 Python 3.14의 신규
`annotationlib` 기반 타입 평가와 충돌해 `TypeError: 'function' object is not subscriptable`로
죽는 것을 실제로 확인했습니다(`create_agent` 검증 중 발견). **이 프로젝트는 `create_react_agent`
가 `langgraph.prebuilt`에 있어서 원래 `langchain.agents`/`langchain.chains`를 쓸 필요가
없으므로, 구현 중 절대 그쪽에서 import하지 않습니다**(우연히 어떤 심볼 하나라도 그 모듈
트리에서 가져오면 로컬 실행이 깨짐). Docker(`python:3.12-slim`)에서는 Python 3.14 전용
`annotationlib` 문제라 재발 가능성이 낮지만, 확인 전까지는 가정입니다. 같은 이유로 Docker
베이스 이미지는 `python:3.14-slim`이 아니라 **`python:3.12-slim`(또는 3.11)**을 명시적으로
고정합니다(3일차 5번 Dockerfile 작성 시 적용).

### 환경변수 (고정, 스크립트마다 이름이 갈리지 않도록)

| 변수 | 용도 |
|---|---|
| `MODEL_ID` | `_default_llm()`이 읽는 **검증** 역할 Bedrock LLM 모델 ID |
| `REPORT_MODEL_ID` | `_report_llm()`이 읽는 **레포팅** 역할 Bedrock LLM 모델 ID(미설정 시 `MODEL_ID`로 대체) |
| `EMBED_MODEL_ID` | `retriever.py`가 읽는 임베딩 모델 ID(`amazon.titan-embed-text-v2:0`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_DEFAULT_REGION` | Bedrock 호출용 AWS 자격증명(`us-east-1`) |

실제 값은 `.env`에 두고 커밋하지 않습니다(0-6절 제출 규약, 2026-09-04부터 git — `.gitignore`
로 관리). **작성 완료** — `.env`에 실제
AWS 자격증명과 `MODEL_ID`/`REPORT_MODEL_ID`/`EMBED_MODEL_ID`를 채웠습니다. `.env.example`
도 같은 여섯 변수를 나열해 함께 작성했습니다(필수 산출물 목록엔 없지만 재현성을 위해
추가) — 시크릿인 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`만 비워두고, 나머지는
비밀값이 아니므로 실제 사용 중인 기본값을 채워 둡니다(복사해서 바로 쓸 수 있게).

**(결정, 2026-09-03 — 사용자 요청) 검증/레포팅 역할 분리 + 모델별 토큰 집계 추가.**
2차 자체평가(10-J절)에서 판정자(judge)가 시스템과 같은 약한 모델(Haiku)이라 판정
자체를 신뢰할 수 없다는 것을 실측으로 확인한 뒤, 사용자가 두 역할을 서로 다른 모델로
분리하기로 결정했다 — **검증**(java_lite_adapter의 실제 소스 코드 리뷰, `run_eval.py`의
판정자, 향후 ragas 내부 LLM처럼 "새로운 판정을 직접 내리는" 역할)은 `MODEL_ID`(Sonnet
4.5 이상 권장)를, **레포팅**(`security_agent`/`error_agent`/`performance_agent`처럼
"이미 검증된 결과를 사람이 읽기 쉽게 요약만 하는" 역할)은 `REPORT_MODEL_ID`(Haiku로
충분)를 쓴다. `src/tools.py`의 `_default_llm()`(검증)/`_report_llm()`(레포팅)이 각각의
환경변수를 읽고, 내부 공통 헬퍼 `_build_llm()`으로 병렬 도구 호출 우회 로직을 공유한다.
사용자는 또한 "이 미니PJT 범위에서는 (3일계획 3번의) API 비용 예산 제한을 적용하지
말라"고 명시해, 3일차 3번(ragas 지표 산출)은 예산 초과 시 폴백(2순위/최후 수단)으로
내려가지 않고 항상 1순위(실제 `ragas` + `note`를 `ground_truth`로 사용)를 시도한다
(3일계획 3번 참고).

**모델별 토큰 사용량 집계**(같은 결정, "레포트 상단에 모델별 토큰 기입" 요청): 두 함수
모두 `ChatBedrockConverse` 생성 시 `_UsageTrackingCallback`을 붙여, 그 LLM이 이후
몇 번을 호출되든(ReAct 루프 포함) `usage_metadata`를 모델별로 자동 누적한다(호출부마다
계측 코드를 넣을 필요 없음 — LangChain 콜백이 Runnable 체인/그래프 실행 전체에
전파되기 때문). `get_token_usage_summary()`/`reset_token_usage()`로 조회·초기화한다.
`evaluation/run_eval.py`는 이 값을 `<리포트파일>.tokens.json`에 문항마다 즉시 저장해
(JSON 결과 재개와 같은 이유 — Bedrock 할당량 초과로 여러 프로세스 실행에 걸쳐 재개되는
게 오늘 2차 평가에서만 5차례 있었음) 프로세스가 중간에 죽어도 누적치가 사라지지 않게
하고, 최종 리포트 상단에 모델별 호출 수·입력/출력/총 토큰 표를 추가한다. **실측 검증**:
`POST /query` 1회 호출 후 `get_token_usage_summary()`가 `us.anthropic.claude-haiku-4-5-
...` 키 아래 `input_tokens`/`output_tokens`/`total_tokens`/`calls`를 정확히 채우는 것을
확인했다(현재는 `MODEL_ID`/`REPORT_MODEL_ID`가 둘 다 같은 Haiku라 한 모델로만 잡히며,
`MODEL_ID`를 Sonnet으로 바꾸면 두 모델이 각자 다른 행으로 나뉜다).

### Docker 실행 환경 (계획 문서 3일차 5번에도 동기화됨)

`vue3_adapter`가 `npm audit`/`eslint`를 실제로 실행하므로, `Dockerfile` 베이스 이미지는
**Python과 Node.js를 모두 포함**해야 합니다(예: `python:3.12-slim` 위에 `nodejs`/`npm`을
apt로 추가). Java 라이트는 도구를 실행하지 않으므로(LLM이 소스를 읽기만 함) 추가 런타임이
필요 없습니다. `node_modules/`는 0-6절 제출 규약상(2026-09-04부터 git) 제외 대상이므로, `data/`에는
`package.json`/`package-lock.json`만 커밋하고 **Docker 빌드 단계에서 `npm install`을
실행**해 `node_modules`를 만든 뒤 스캔하도록 `Dockerfile`을 작성합니다.

**⚠️ 컨테이너 안에서 `127.0.0.1` 바인딩의 함정**: 위 "보안 경계" 절의 `host="127.0.0.1"`
바인딩을 컨테이너 **내부** 앱 바인딩에 그대로 적용하면, 컨테이너 자신의 loopback에만 열려서
Docker `-p` 포트 매핑을 걸어도 호스트에서 절대 도달할 수 없습니다(Docker 네트워킹의 흔한
함정). **올바른 방식**: `src/api.py`는 컨테이너 안에서 `0.0.0.0`으로 바인딩하고, 대신
`docker run -p 127.0.0.1:8000:8000 ...`처럼 **호스트 쪽 포트 매핑을 `127.0.0.1`로 제한**
합니다 — "외부 네트워크에 노출 안 함"이라는 원래 목적은 그대로 지키면서 호스트의 `curl`
검증은 정상 동작합니다. 로컬(가상환경) 실행 시에는 원래 규칙대로 `127.0.0.1` 바인딩을
그대로 씁니다 — 이 예외는 Docker 컨테이너 내부 바인딩에만 적용됩니다.

### 완성 후 실행 방법 (README.md "실행 방법" 절의 원본)

**로컬(가상환경)**:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api:app --host 127.0.0.1 --port 8000
```
`.env`는 이미 채워져 있어(위 "환경변수" 절) `python-dotenv`가 자동으로 읽습니다.

**실행(브라우저, 권장 — 2026-09-03 추가, CLAUDE.md 10-G절)**: 서버를 띄운 뒤 브라우저에서
`http://127.0.0.1:8000/`을 열고 **"점검 실행" 버튼**을 누르면 됩니다. 감지된 언어
(Vue3/Java/Python)를 언어별로 나눠 실행할 필요 없이 한 번에 전부 점검하며, 진행률(5단계
중 몇 단계 완료)과 완료 시 결과(감지된 언어, 카테고리별 건수, `report.md` 전문)를 화면
에서 바로 확인할 수 있습니다 — `curl`/터미널 명령을 몰라도 됩니다.

**실행(터미널, API 직접 호출 — 스크립트·CI 자동화용)**: 다른 터미널에서
```
curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" -d "{\"question\":\"vue3-app 보안 취약점 알려줘\"}"
```
`POST /query`는 특정 질문에 답하는 대화형 API 스펙(0-2절, 고정)이고, 브라우저의 "점검
실행" 버튼은 내부적으로 같은 Supervisor를 고정 질문으로 호출하는 `POST /scan`(API 스펙
밖 UI 편의 엔드포인트)을 씁니다 — 둘 다 결과는 같은 `reports/report.md`/`report.json`
에 반영됩니다.

**Docker** (**(참고, 2026-09-04)** 3일차 5번을 6번 뒤로 순서만 미뤄 아직 `Dockerfile`
자체가 없다 — 아래 명령은 5번 착수 시 그대로 쓸 계획이고, 지금 시점엔 실행 확인이 안 된
상태다. 지금 당장 실행하려면 위 "로컬(가상환경)" 방법을 쓴다):
```
docker build -t mini-pjt-agent .
docker run -p 127.0.0.1:8000:8000 --env-file .env mini-pjt-agent
```
그 뒤 브라우저에서 `http://127.0.0.1:8000/`을 열거나 위와 같은 `curl` 명령으로
검증합니다(3일차 5번 DoD 확인 기준).

**일일 자동 실행**: 스케줄러는 구현하지 않습니다(조건 3) — README에는 "위 `curl`
(또는 `POST /scan`) 호출을 사내 CI self-hosted runner 또는 사내망 OS 작업 스케줄러에
하루 한 번 걸면 된다"는 방법만 적습니다(자동화 컨텍스트에서는 브라우저 UI 대신 API를
직접 호출). **수동 실행은 브라우저에서 "점검 실행" 버튼을 누르거나 위 `curl` 명령을
쓰는 것, 둘 중 편한 쪽입니다.**

## 5. `README.md` 필수 섹션 (제출 규약)

`SERVICE.md`는 이미 작성 완료([`SERVICE.md`](./SERVICE.md) 참고, 서비스 정책·성공 기준의
통과율 목표치 포함). `README.md`는 아직 작성 전이며, 3일차 6번 항목에서 채웁니다.

- `README.md`: 무엇을 푸나 / 활용한 패턴(Day1~7) / 아키텍처 / 실행 방법(Docker) /
  RAGAS 평가 결과 / 인-아웃 세트 통과율(1차·2차) / 트라이앤에러 회고 / 핵심 코드 위치
- `test_queries.csv` 스키마(컬럼 자체는 표준 **쉼표 구분** CSV): `id, category, input,
  expected_traits, forbidden, expected_tools, note`. 이 중 `expected_traits`/`forbidden`/
  `expected_tools` 세 필드만 한 셀 안에 값이 여러 개일 때 **세미콜론(`;`)으로 구분**해서
  담습니다(예: `no_hardcoded_secret;cites_source`) — 세미콜론은 컬럼 구분자가 아니라 이 세
  필드 내부의 다중값 구분자입니다. 최소 10건·권장 15~20건, positive 40%/negative 20%/
  edge 25%/guardrail 15% 비율 권장.
- **(변경, 2026-09-04 — 강의 플랫폼 공지) 제출 방식: zip이 아니라 git 저장소.** `.venv/`·
  `__pycache__/`·`node_modules/`·`.env`·자격증명은 `.gitignore`로 커밋 제외(zip 제외
  목록과 동일한 항목, 이유도 동일). zip 전용 규약이던 파일명(`mini-pjt_이종엽.zip`)·
  100MB 상한은 더 이상 적용되지 않는다. `.env`는 실제 AWS 자격증명을 담고 있어 실수로도
  커밋되면 안 되므로, 커밋 전 `git status`/`git diff --cached`로 매번 확인한다.

## 6. 12패턴 체크리스트 — 이 프로젝트가 확보하는 패턴

4종 필수: **#1 구조화 출력(Pydantic)**, **#3 RAG**, **#11 Observability/Trace**,
**#12 평가(RAGAS/LLM-Judge)**. 추가로 #2(ReAct)·#4(도구 다중 결합)·#6(가드레일)·
#9(Multi-Agent Supervisor)까지 총 8개를 자연스럽게 확보합니다. MCP·HITL·미들웨어·
Plan-Execute/장기메모리는 이번 범위에 넣지 않습니다.

## 7. 시간 부족 시 컷 순서 (위에서부터 먼저 자름)

**(참고)** 이 절의 "시간 부족"은 3일계획의 시간 배분(사람 기준, 3일계획 1절 참고)이 원래
가정한 의미와 다릅니다 — Claude(AI)가 구현하므로 순수 코딩 시간은 문제가 되지 않고,
실제로 진행을 막는 건 Bedrock 할당량 소진 같은 **외부 제약**입니다. 그런 상황이 오래
지속돼 이번 3일 범위를 다 못 채울 것 같을 때, 아래 순서대로 자릅니다.

1. Java 라이트 리뷰 생략 → README에 "다음 반영"으로 명시(어댑터 인터페이스 자체는 유지)
2. 1차 평가 기반 개선 범위 축소 → 가장 심각한 실패 유형 1~2개만 고치고 나머지는
   `round2_report.md`에 "미해결·다음 과제"로 기록
3. RAG 문서 2개 → 1개로 축소
4. 파일 단위 그룹핑까지 생략(ID만 부여)

**절대 자르면 안 되는 것**: `POST /query` API, `SERVICE.md`, `test_queries.csv`(10건 이상,
4카테고리), 1차/2차 평가 리포트, `Dockerfile`, `README.md` 템플릿 전 항목, 4종 필수 패턴.
**(2026-09-04 갱신)** `Dockerfile`(3일차 5번)은 사용자 요청으로 6번(`README.md`)보다
순서만 뒤로 미뤘다 — 자르는 게 아니라 착수 순서 변경이며, 현재 시점 기준 아직 미완료
상태다. 3일계획.md 3일차 2절/6절(DoD)에 최신 상태가 반영돼 있다.

## 8. 이번 3일 범위에 절대 넣지 않는 것 (전체설계 로드맵으로 이동)

- 부분 반영(패치 자동 적용) 파이프라인 전체, 연결점 LLM 요약
- `test_gen_agent`(테스트 코드 자동 생성)
- Finding 다중 태그(`tags` 배열) — 단일 `category`로 고정
- Sonar 규칙 검사 / Maven CVE 검사(전체설계 3-3절)
- Git 전체/증분 하이브리드 스캔(전체설계 3-4절) — 매번 전체 스캔
- 스케줄러 자체 구현, 호출 그래프 기반 연결점, 대시보드, 알림 연동, 여러 레포 지원, CI 완전
  통합, 사내망 프라이빗 LLM 엔드포인트 구축
- API 사내 SSO 인증(전체설계 2-1-4절) — 이번 실습은 사외망에서 더미 프로젝트로만 진행되어
  인증으로 보호할 사내 자산이 없음. `127.0.0.1` 로컬 바인딩만 적용하고, 사내망 프라이빗 LLM
  엔드포인트 구축과 함께 정식 배포 전 필수 선행 작업으로 README에 명시
- 임의 엔드포인트 대상 범용 모의해킹·부하테스트 프로빙, ZAP/k6 선택 연동(전체설계 10-0절의
  완전한 형태) — 최소 버전(스테이징 서버 1개, IDOR 1건+N+1 1건 한정)은 아래 "확장 phase"
  10-C절에서 실제로 구현했습니다.

**(결정, 2026-09-02 수정)** "3번째 이상 언어 어댑터"와 "DB 연결 + 부하 파라미터"는 원래
여기(로드맵)에 있었으나, AI 실행 기준 시간표(3일계획 5-0절)로 계산한 여유 시간(약 7~8시간,
계산 근거는 3일계획 5-1절 참고)을 활용해 **확장 phase(3일계획 5-1절, 공식 규약 밖 추가
범위)로 앞당겼습니다** — 아래 "확장 phase" 절 참고. 이 둘은 이제 "제외 목록"이 아니라
"진행 중인 추가 범위"입니다.

**(결정, 2026-09-03 수정)** `pentest_agent`/`load_test_agent`가 직접 모의해킹·부하테스트를
수행해 소스코드 원인과 연결하는 기능(전체설계 10-0절, 2026-09-02 방향 수정 — 사람이 미리
돌린 리포트를 나중에 분석하는 구조가 아니라 Agent가 직접 그 행위를 수행하는 구조)도 같은
이유로 "제외 목록"에서 뺐습니다. 원래는 "떠 있는 웹 서버(스테이징 환경)가 없어 실현
불가능"이라고 RAG 체크리스트·더미 IDOR 케이스로 최소한의 씨앗만 남길 계획이었으나, 그
서버를 이 프로젝트 안에서 직접 만들면 제약이 풀린다는 점에 착안해 확장 phase(3일계획
5-2절)로 앞당겼습니다 — 아래 10-C절 참고. 다만 완전한 형태(임의 엔드포인트 대상 범용
프로빙, ZAP/k6 선택 연동)는 여전히 위 목록대로 로드맵입니다.

## 9. 완성 기준(DoD)은 계획 문서 6절을 그대로 따름

번호 항목을 구현하다가 완료 기준이 애매하면 계획 문서 6절의 체크리스트(공식 규약 충족 /
프로젝트 고유 기준 / 보안 경계 / 로드맵 제외 목록)를 최종 판단 기준으로 씁니다.

## 10. 확장 phase (2026-09-02~03 추가 — 주로 계획 문서 5-1~5-9절, 공식 규약 밖 추가 범위)

AI 실행 기준 시간표(계획 문서 5-0절)로 계산한 여유 시간을 활용해, 전체설계 로드맵에서
**외부 인프라 없이 실현 가능하고 이미 "핵심 차별화"로 문서화된** 항목을 앞당깁니다 —
5-1절에서 두 항목(언어 어댑터 3개, DB+부하 파라미터), 5-1 완료 후 예산이 더 남아 5-2절에서
한 항목(pentest_agent/load_test_agent 최소 실증)을 추가로 앞당겼습니다. 이후 사용자가
`config.yaml`을 직접 검토하거나 실행 편의를 요청하며 이어져 5-3(DB·소스 경로 설정화),
5-4(MyBatis 매퍼 XML SQL Injection), 5-5(언어 자동 감지+`exceptLanguages`), 5-6(터미널
없이 쓰는 최소 실행 UI), 5-7(리포트 이력 보존), 5-8(전체 코드 재점검+샘플 데이터
다양화), 5-9(`test_queries.csv` 점검)까지 이어졌습니다. 자세한 배경·제외 사유는 계획
문서 5-1~5-9절 참고. 10-K/10-L/10-M 세 절은 계획 문서의 "5-N" 번호가 따로 없는 항목이다
— 각각 `report.md` 가독성 개선(사용자 요청), LLM 검증/레포팅 역할 분리(3일차 2·3번을
지원하는 인프라 결정), `exceptLanguages` 버전 무관화(위 5-5의 사후 보강)라서, 새 "5-N"
확장 항목이 아니라 이미 진행 중이던 3일차 본 계획 작업의 부속 결정으로 분류했다. 이 절은
그중 mini-pjt_이종엽 고유의 구현 결정만 남깁니다. **10-N절(모의해킹/부하테스트 대상 서버
설정)도 같은 성격이지만, 작성 시점(3일차 4번 진행 중)의 흐름을 그대로 남기기 위해 이
절 안이 아니라 위쪽 "2번(2차 평가) 3차 재검증" 직후에 있다** — "CLAUDE.md 10-N절"로
참조되는 곳은 항상 그 위치를 가리킨다.

**(결정, 2026-09-02 — 실행 순서 변경)** 이 phase는 **3일차 1번(개선) 직후, 3일차 2번(2차
평가)으로 넘어가기 전에** 진행합니다(계획 문서 3일차 절 "실행 순서 변경" 결정과 동일) —
2차 평가·`ragas` 지표·`SERVICE.md`/`README.md` 문서화보다 이 phase가 먼저 끝나야, 그
결과물이 뒤이은 평가·문서화에 실제로 반영될 수 있기 때문입니다. 그래서 3일차 4번
`SERVICE.md`/6번 `README.md`를 쓰는 시점에는 이 phase가 이미 끝나 있어야 하며, 그 문서들은
당시 실제 완료 상태(완료됐으면 "완료", 시간이 없어 컷됐으면 그 사실 그대로)를 반영해야
합니다 — SERVICE.md에 지금 남아 있는 "아직 미구현" 표현은 이 phase가 끝나면 실제 상태에
맞게 갱신합니다.

5-8의 전체 코드 재검토에서 `mask_pii()`의 실제 마스킹 누락 버그를 새로 찾아 고쳤습니다
— 자세한 내용은 10-I절 참고.

### 10-A. Python 언어 어댑터 (전체설계 11절 다국어 확장 실증) — 완료, 실측 검증됨

**1·2·3번 전부 완료.** `data/sample_python_app/api_handler.py`(더미 소스), `python_adapter`
(`src/tools.py`), `_LANGUAGE_ADAPTER_REGISTRY`에 `"python"` 등록, `config.yaml`의
`languages`에 `python` 활성화, `make_supervisor()`를 통한 실제 API 경로 연동 확인까지
전부 실측 검증했습니다.

- **더미 소스**: `data/sample_python_app/api_handler.py`의 `ApiHandler.ping_host()` —
  `os.system("ping -c 1 " + hostname)`로 사용자 입력을 검증 없이 셸 명령에 결합하는 명령어
  주입(security 대상)과 미사용 `import sys`(error 대상)를 심었습니다. performance 카테고리
  대상은 Vue3/Java와 같은 원칙으로 없음(`OrderService.java`의 N+1이 여전히 유일한 케이스).
- **`python_adapter`**(`src/tools.py`, `Vue3Adapter`와 같은 클래스+캐싱 패턴): `bandit -r
  -f json`, `pylint --output-format=json`을 실제로 실행. **실측 검증**: `run_security()`
  → `B605`(start_process_with_a_shell) HIGH 정확히 1건. `run_error()` → `unused-import`
  정확히 1건. `run_performance()` → 빈 리스트.
- **실제로 버그 2건을 발견하고 고쳤습니다**:
  1. **실행 방식**: `shutil.which("bandit")`/`shutil.which("pylint")`가 이 셸(venv 비활성화
     상태)에서 `None`을 반환해 `FileNotFoundError`로 즉시 실패하는 것을 실측으로 확인 —
     npm/npx와 달리 bandit/pylint는 시스템 실행 파일이 아니라 이 venv에 pip로 설치한
     파이썬 패키지이기 때문입니다. **수정**: `[sys.executable, "-m", "bandit"]`/
     `[sys.executable, "-m", "pylint"]`로 호출해 PATH와 무관하게 항상 정확한 인터프리터의
     패키지를 찾도록 고쳤습니다.
  2. **bandit 디렉터리 스캔**: `bandit -f json <디렉터리>`를 `-r`(재귀) 없이 호출하면
     에러 없이 조용히 빈 결과만 반환하는 것을 실측으로 확인했습니다(파일 하나만 직접
     지정했을 때는 정상 동작해서 처음엔 못 잡았던 함정). **수정**: `-r` 플래그 추가.
  3. **(재수정) pylint "전체" 가정이 틀렸음을 실측으로 확인**: 원래 계획은 "pylint 전체 →
     error"(npm audit처럼 도구 자체가 항상 한 카테고리라고 가정)였는데, 실제로 돌려보니
     우리 더미 클래스(공개 메서드 1개)에 `too-few-public-methods`(R0903, 리팩터 제안)가
     의도한 `unused-import`(W0611)와 함께 나오는 것을 확인했습니다 — eslint가 보안+오류를
     섞어 내는 것과 같은 문제입니다. **수정**: eslint 때와 같은 원칙으로
     `_PYTHON_ERROR_PYLINT_SYMBOLS = {"unused-import"}` 명시적 허용 목록을 추가해 무관한
     리팩터/컨벤션성 항목을 걸러냅니다. bandit은 npm audit처럼 애초에 보안 전용 도구라
     필터링 없이 전부 보냅니다.
- **Agent 카테고리 매핑**: `security_agent` ← bandit 전체, `error_agent` ← pylint 중
  `_PYTHON_ERROR_PYLINT_SYMBOLS`에 있는 규칙만, `performance_agent` ← 항상 빈 리스트
  (Vue3와 동일 이유).
- **의존성**: `bandit==1.9.4`, `pylint==4.0.8`을 실제로 `pip install`해 기존 langchain
  0.3.x 세대 고정 조합과 설치 충돌 없음을 확인했습니다.
- **`_LANGUAGE_ADAPTER_REGISTRY`/`config.yaml` 연동**: `agent.py`에 `"python":
  python_adapter`를 등록하고 `config.yaml`의 `languages`에 `python`을 추가한 것만으로
  `make_supervisor()`가 코드 변경 없이 Python도 함께 조사하는 것을 확인 — "설정만 바꾸면
  확장된다"는 주장을 실제로 증명했습니다. `collect_findings()` 결과 총 **14건**
  (기존 12 + Python 2: `SEC-11`(B605)/`ERR-2`(unused-import))으로 정확히 늘었고,
  `api_handler.py`의 `SEC-11`과 `ERR-2`가 같은 파일이라 `assign_group_ids()`가 자동으로
  같은 그룹(`G-6`)에 묶는 것도 확인했습니다.
- **실제로 버그 2건을 더 발견하고 고쳤습니다(Agent 연동 확인 중)**:
  4. **RAG 근거 매칭이 실제로 깨지는 것을 확인**: `attach_rag_references()`(2일차 4번)가
     규칙 이름 **전체 일치**로 IDOR/N+1을 찾았는데, Java lite LLM 리뷰를 다시 호출하자
     N+1 규칙 이름이 `n-plus-one-query-in-loop`가 아니라 `n-plus-one-query`로 살짝 다르게
     나와 근거가 안 붙는 것을 실측으로 확인했습니다 — CLAUDE.md에 미리 "경험적으로는
     안정적이나 형식적 보장은 아니다"라고 남겨둔 우려가 실제로 재발한 것입니다. **수정**:
     전체 일치 대신 규칙 이름에 `"idor"`/`"n-plus-one"` **키워드가 포함되는지**로 완화한
     `_RAG_REFERENCE_KEYWORDS`로 바꿔, 사소한 이름 변형에 견고하게 했습니다(그래도 무관한
     규칙엔 여전히 검색 자체를 안 함). 재검증 결과 두 규칙 이름 변형 모두에서 정확히
     근거가 붙는 것을 확인했습니다.
  5. **`_SCOPE_AND_ACTION_GUARDRAIL`이 하드코딩돼 있어 자기모순 답변을 만드는 것을 확인**:
     이 지침(3일차 1번)이 "Vue3/Java"를 문자열에 직접 박아 놓았는데, Python을
     `config.yaml`에 추가하자마자 `error_agent`가 Python의 `unused-import`를 정확히
     보고하면서도 같은 답변 안에서 "Python은 이 프로젝트의 점검 범위를 벗어난 것"이라고
     스스로 모순되게 말하는 것을 실측으로 확인했습니다. **수정**: 하드코딩 대신
     `load_active_languages()`로 활성 언어 목록을 읽어 `"Vue3/Java/Python"`을 동적으로
     만드는 `_ACTIVE_LANGUAGES_LABEL`을 추가했습니다 — 다음에 언어가 하나 더 늘어도 이
     문구를 따로 고칠 필요가 없습니다. 재검증 결과 자기모순 없이 정확히 답하는 것을
     확인했습니다.

**확인 기준 충족**: `python_adapter.run_security()`가 bandit HIGH 1건, `run_error()`가
pylint 1건을 실제로 반환하고, 언어 어댑터가 3개(Vue3/Java/Python)로 늘어나 SERVICE.md의
확장성 주장이 실증됐습니다(전체설계 11절 유보 사항이 정확히 지적한 대로, "Agent 쪽 코드는
안 바뀐다"는 실증됐지만 "새 언어=항상 균일하게 쉽다"는 아니었다는 것도 위 버그들로 함께
확인된 셈입니다).

### 10-B. DB 연결 + 부하 파라미터 (전체설계 3-5절)

**(참고, 2026-09-02 — 10-A와 같은 논리) SQLite를 고른 이유는 대표성이 아니라 마찰이
적어서입니다.** SQLite는 서버·인증·전용 드라이버가 없는 임베디드 DB라 Python 표준
라이브러리 `sqlite3`만으로 접근됩니다. 실사용의 EDB/Oracle/IBM Db2 같은 상용 DB는 벤더별
드라이버·실행계획 조회 문법(`EXPLAIN QUERY PLAN` vs `EXPLAIN PLAN FOR ...` 등)·스키마
카탈로그·인증 방식이 전부 달라 어댑터 하나의 구현 비용이 훨씬 큽니다 — 다만 `db_adapter`
레지스트리 자체(설정값 기반 선택)는 완전 재개발 없이 그대로 유지되는 "라우팅형" 확장
구조입니다(전체설계 3-5-1절 유보 사항, SERVICE.md "서비스 확장 관점" 참고).

**실행 단위(3일계획 5-1-B절과 동일 번호, 예: "5-1-B의 1번 수행해줘")**: 1) SQLite
스키마+시드(LLM 불필요) → 2) `db_adapter` 작성(LLM 불필요) → 3) `load_profile.yaml`
작성(LLM 불필요) → 4) `performance_agent` 확장(Bedrock Converse 필요) → 5) 보안 경계
반영(LLM 불필요, 언제든 먼저 해도 됨). **2026-09-03 완료(1~5번 전부, 아래는 실제 산출물과
실측 검증 내용).**

- **DB**: SQLite. `data/sample_db/schema.sql`에 `data/sample_java_app`이 다루는
  도메인(users/orders/order_items) 스키마를 두고, **`order_items`에 `order_id` 인덱스를
  의도적으로 뺐습니다.** `src/tools.py`의 `_build_sample_db()`가 `db_adapter`의 첫 호출
  시점에 이 스크립트로 `data/sample_db/app.db`를 매번 새로 만듭니다(고정 산출물로 커밋하지
  않음 — 스키마 SQL만 커밋). **실측 검증**: `get_schema()` → `order_items.indexes == []`
  확인, `explain_query("SELECT product_name FROM order_items WHERE order_id = 1")` →
  `SCAN order_items`(풀스캔) 확인.
- **`db_adapter`**(`src/tools.py`의 `DbAdapter`/`db_adapter`): 전체설계 3-5-1절 인터페이스
  중 SQLite에 의미 있는 두 가지만 구현 — `get_schema()`(`sqlite_master`+`PRAGMA
  table_info`/`index_list`), `explain_query(sql)`(`EXPLAIN QUERY PLAN`). `get_connection_
  pool_config()`은 SQLite가 파일 기반이라 커넥션 풀 개념이 약해 생략(로드맵에 남김).
- **부하 프로파일**: `data/load_profile.yaml`(`expected_concurrent_users: 200`,
  `requests_per_minute: 3000`) — `src/config.py`의 `load_load_profile()`로 읽습니다.
- **`performance_agent` 확장**(`make_performance_agent`에 `db_adapter`/`load_profile`
  파라미터 추가, 기본값 `None`이면 5-1-B 이전과 동일하게 동작): `db_adapter`가 있으면
  `get_db_schema`/`explain_query` 도구를 추가로 붙이고, 부하 수치는 프롬프트에 직접
  문장으로 넣습니다(고정 스칼라 두 값이라 도구 왕복 없이 텍스트로 충분). **실측 검증**:
  "OrderService.java에 성능 문제가 있는지 근거를 들어 점검해줘" 질문에 `order_items`
  풀스캔 + 부하(동시 사용자 200명/분당 3,000건)를 근거로 "실제로 심각한 성능 병목이며
  ... 실제로 위험하다"는 응답을 2회 연속 확인.
- **실제로 버그 1건을 발견하고 고쳤습니다**: 첫 실측 호출에서 `performance_agent`가
  **엉뚱한 테이블(`orders`)의 실행계획을 조회해 "병목이 아닙니다"라는 틀린 결론**을 낸
  것을 확인했습니다 — `scan_performance`가 돌려주는 N+1 finding의 `message`가 반복 쿼리의
  정확한 테이블/컬럼명을 명시하지 않아, LLM이 `OrderController.getOrder()`(별개 메서드,
  IDOR 이슈 대상)의 `orders WHERE id = ?` 쿼리를 그럴듯하게 대신 지어내 조회했기 때문입니다
  — DB 근거가 실제로는 질문과 무관한 테이블을 가리키는데도 자신 있게 답한, Q7/Q9(3일차
  1번)와 같은 계열의 "근거 없는 확신" 실패입니다. **수정**: (1) `_PERFORMANCE_INSTRUCTIONS`
  (`src/tools.py`)에 finding의 `message`가 정확한 테이블/컬럼명을 반드시 포함하도록
  지시를 추가하고, (2) `performance_agent` 프롬프트(`agent.py`)에 "finding의 message에
  적힌 테이블·컬럼을 그대로 쓰고 다른 테이블을 추측하지 말라"고 명시했습니다. 재검증
  결과 `order_items`를 정확히 조회해 올바른 결론을 내는 것을 2회 연속 확인했습니다.
- **보안 경계**: `_assert_select_only()`(`src/tools.py`)가 `SELECT`로 시작하지 않거나
  `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/`CREATE`/`REPLACE`/`ATTACH`/`PRAGMA` 키워드가
  포함된 SQL을 `ReadOnlySqlError`로 거부합니다 — 별도 DB 계정 개념이 없는 SQLite에서 1절
  "점검과 수정의 분리" 철학을 대신 구현한 것입니다. **실측 검증**: `DELETE`/`UPDATE`/
  `DROP`/`INSERT` 4종 모두 차단 확인.
- **Finding 연동**: 새 필드를 만들지 않고 기존 `detail`/`reference` 필드에 담는다는
  원래 설계를 그대로 구현했습니다 — 다만 실제로 만들어 보니 `performance_agent`의 도구
  기반 추론(위 항목)은 **대화형 질의에만 답하고 `report.md`/`report.json`(대화 없이
  생성되는 정적 산출물)에는 반영되지 않는다는 것을 뒤늦게 발견**했습니다. 그래서
  `collect_findings()`(`agent.py`)에 `attach_db_evidence()` 단계를 추가해, N+1 finding에
  한해 `db_adapter.explain_query()`와 `load_load_profile()` 결과를 `detail`에 텍스트로
  덧붙입니다. LLM이 지어낸 자유 텍스트에서 정규식으로 테이블명을 뽑는 방식(RAG 참조
  매칭에서 이미 실패를 겪은 접근)은 피하고, `_PERFORMANCE_REVIEW_FILES`/
  `_RAG_REFERENCE_KEYWORDS`와 같은 원칙으로 이번 유일한 N+1 케이스(Java `order_items.
  order_id`)에 한정된 고정 쿼리 문자열을 씁니다. **실측 검증**: `collect_findings()` →
  `report.md`/`report.json` 양쪽 모두 `PERF-1.detail`에 `[DB 실행계획: SCAN order_items —
  풀스캔 확인(인덱스 없음). 예상 부하: 동시 사용자 200명, 분당 요청 3000건]`이 정확히
  덧붙는 것을 확인했고, 전체 findings 개수는 5-1-B 이전과 동일한 14건으로 유지됨을
  확인했습니다(새 finding이 생기지 않고 기존 finding만 보강됨).
- **알려진 제약**: tool_use 병합 버그로 `_run_category_agent`가 `_fallback_answer`(도구
  없는 요약) 경로로 넘어가면, 그 경로는 `scan_performance` 결과만 프롬프트에 들어가고
  `db_adapter`/부하 프로파일 근거는 붙지 않습니다(`agent.py`의 `_PERFORMANCE_FALLBACK_
  INSTRUCTIONS` 옆 주석 참고) — 드문 경로이고 "도구 판정을 그대로 신뢰"라는 DoD 원칙은
  여전히 지켜지므로 이번 범위에서는 그대로 둡니다.

### 확인 (계획 문서 5-1절과 동일)

1. `python_adapter.run_security()`가 bandit HIGH 1건, `run_error()`가 pylint 1건을
   실제로 반환한다. — **충족(10-A절)**.
2. `performance_agent`가 `OrderService.java`의 N+1에 대해 DB 실행계획(인덱스 없음)과
   부하 프로파일을 근거로 "실제로 위험하다"는 판단을 포함한 응답을 만든다. — **충족**
   (위 실측 검증 참고).
3. 언어 어댑터가 3개(Vue3/Java/Python)로 늘어난다. — **충족(10-A절)**.

**5-1 확장 phase(10-A+10-B) 전체 완료.** 이 절의 산출물은 0절 공식 규약이 요구하는 게
아니었지만, 시간 여유가 있어 컷 없이 전부 구현·실측 검증했습니다.

### 10-C. pentest_agent/load_test_agent 최소 실증 (전체설계 10-0절, 확장 phase 5-2)

**배경(2026-09-03)**: 5-1(10-A+10-B) 완료 후에도 예산 여유가 4시간 이상 남아, 사용자
요청으로 전체설계 로드맵에서 추가 항목을 앞당겼습니다. 3일계획 5-1절이 "이번엔 제외한
로드맵 항목"으로 적어 둔 항목 중 1번(모의해킹/부하테스트 Agent 직접 수행)을 "**떠 있는
스테이징 서버가 없어 불가능**"이라고 뺐었는데, 그 서버를 우리가 직접 만들면 제약이
풀린다는 점에 착안해 다시 채택했습니다.

**실행 단위(3일계획 5-2절과 동일 번호)**: 1) 스테이징 앱 작성(LLM 불필요) → 2) 펜테스트
프로브 함수 작성(LLM 불필요) → 3) 부하테스트 함수 작성(LLM 불필요) → 4)
`security_agent`/`performance_agent`에 도구로 연결(Bedrock Converse 필요) → 5) 정적
산출물(`report.md`/`report.json`) 반영. **1~5번 전부 완료.**

- **스테이징 앱**(`data/staging_app/app.py`, FastAPI): `OrderController.java`/
  `OrderService.java`(정적 리뷰 대상)와 같은 취약점·지연 특성을 실제로 살아있는 서버로
  재현합니다. `GET /orders/{order_id}?current_user_id=`는 `OrderController.java#getOrder()`
  와 똑같이 소유권 검증 없이 그대로 반환합니다(IDOR). `GET /orders/{order_id}/items`는
  용량 5짜리 `threading.Semaphore`(작은 DB 커넥션 풀을 흉내)를 잡은 채 0.1초 대기해,
  `OrderService.java`의 N+1이 실제 DB 없이도 동시 요청 하에서 지연이 누적되는 것을
  재현합니다. **안전 경계**: `127.0.0.1`에만 바인딩, GET 엔드포인트만 존재(쓰기 자체가
  불가능한 구조), 외부 프로젝트/운영 서버 대상 아님(전체설계 10-0절 안전 경계 원칙).
- **`probe_idor_vulnerability()`**(`src/tools.py`): `requests`로 고정된 시나리오
  2건(`_PENTEST_PROBES` — 공격자 user_id로 다른 사용자 소유 order_id를 조회)을 실제
  GET 요청으로 시도하고, 소유권 검증 없이 200과 함께 데이터가 새는지 확인합니다. 임의
  스캔이 아니라 상한 있는 고정 목록만 프로빙합니다(안전 경계).
- **`run_concurrent_load_test()`**(`src/tools.py`): `ThreadPoolExecutor`로 동시 GET
  요청을 보내 p95 지연시간·에러율을 실측하고, 임계치(300ms) 초과 시 finding을 만듭니다.
  동시 요청 수는 `load_profile.yaml`이 아무리 커도 `_LOAD_TEST_MAX_CONCURRENCY`(50)를
  넘지 않도록 상한을 둡니다(로컬 서버 보호, 안전 경계).
- **`_ensure_staging_server()`**: `uvicorn` 서브프로세스로 스테이징 앱을 최초 1회만 기동
  (이후 재사용)하고 `atexit`으로 프로세스 종료 시 함께 정리합니다.
- **Agent 연동**(`agent.py`): `make_security_agent(adapter, enable_live_pentest=True)`가
  `run_idor_pentest_probe` 도구를, `make_performance_agent(..., enable_live_load_test=True)`
  가 `run_live_load_test` 도구를 추가로 갖습니다 — 둘 다 기본값은 `False`(꺼짐)라 5-1
  이전 동작을 그대로 유지하며, `config.yaml`의 `live_probe: true`일 때만 `make_supervisor()`
  가 켜서 넘겨줍니다(`src/config.py`의 `is_live_probe_enabled()`). **실측 검증**: "IDOR가
  실제로 악용 가능한지 확인해줘" 질문에 `scan_security` → `search_guides` →
  `run_idor_pentest_probe` 순서로 도구를 호출해 두 프로브 모두 실제로 데이터가 샌다는
  것을 정확히 보고. "N+1이 실제 부하에서도 병목인지 확인해줘" 질문에 `scan_performance`
  → `get_db_schema` → `explain_query` → `run_live_load_test` 4단계를 전부 거쳐 "p95
  961ms, 임계치 3배 초과"까지 정확히 보고.
- **정적 산출물 반영**: `attach_live_probe_evidence()`(`agent.py`, `collect_findings()`에
  연결)가 `attach_db_evidence()`(10-B절)와 같은 이유로 존재합니다 — IDOR/N+1 finding의
  `detail`에 위와 같은 실제 프로빙 결과를 텍스트로 덧붙여, 대화형 질의 없이 생성되는
  `report.md`/`report.json`에도 반영되게 합니다. **실측 검증**: `SEC-2`(IDOR)와
  `PERF-1`(N+1) 둘 다 `detail`에 실제 프로빙 근거가 정확히 붙는 것을 확인했고, PERF-1은
  DB 실행계획(10-B) + 실제 부하테스트(10-C) 근거가 함께 누적되는 것도 확인했습니다.
- **실제로 버그 1건을 발견하고 고쳤습니다**: 처음엔 `/orders/{id}/items`에 단순
  `time.sleep(0.05)`만 넣고 동시 50건을 보냈는데, **p95 지연시간이 임계치를 넘지 않아
  병목이 전혀 감지되지 않는 것**을 실측으로 확인했습니다 — FastAPI/Starlette가 동기
  엔드포인트를 넉넉한 크기의 내부 스레드풀에 위탁해 50건 정도로는 유의미한 대기가 쌓이지
  않았기 때문입니다. **수정**: 실제 DB 커넥션 풀 부족 시나리오(전체설계 3-5-2절 "커넥션
  풀 크기 20 초과 가능성")를 명시적으로 재현하도록 용량 5짜리 `threading.Semaphore`를
  추가하고 대기 시간을 0.1초로 늘렸습니다 — 재검증 결과 p95 909~962ms로 임계치(300ms)를
  안정적으로 초과하는 것을 2회 연속 확인했습니다.
- **설계 단순화(의도적, 시간·복잡도 트레이드오프)**: 전체설계 10-0절은 `pentest_agent`/
  `load_test_agent`를 완전히 새로운 Supervisor 노드로 그립니다. 이 미니PJT는 그 대신
  기존 `security_agent`/`performance_agent`에 선택적 도구로 얹는 방식을 택했습니다 —
  `db_adapter`(10-B절)가 이미 같은 패턴(새 언어 어댑터나 새 Supervisor 노드가 아니라
  기존 Agent에 얹는 보조 도구)이었고, "Agent 쪽 코드가 최소한으로 바뀐다"는 이 프로젝트
  전체의 원칙과 더 일치하기 때문입니다. 실제로 노출되는 근거(살아있는 HTTP 프로빙 결과)는
  두 설계 모두 동일하므로, 새 Supervisor 노드·새 트레이스 배선·새 폴백 로직을 추가로
  만드는 비용 대비 가치가 낮다고 판단했습니다.
- **의존성**: `requests`(이미 boto3의 전이 의존성으로 설치돼 있었음, 실측 확인)를
  `requirements.txt`에 명시 고정했습니다. 새 pip 패키지 설치는 없습니다.

**확인**: `probe_idor_vulnerability()`가 실제 HTTP 요청으로 IDOR 유출 2건을 실측 확인하고,
`run_concurrent_load_test()`가 실제 동시 요청으로 임계치 초과 지연을 실측 확인하며, 이
근거가 `security_agent`/`performance_agent`의 대화형 답변과 `report.md`/`report.json`
양쪽 모두에 반영된다. **전부 충족.**

**알려진 제약**: (1) 10-B절과 같은 이유로, tool_use 병합 버그의 폴백 경로(도구 없는
요약)에서는 이 실제 프로빙 근거도 붙지 않습니다. (2) 스테이징 앱은 `OrderController.java`/
`OrderService.java`가 다루는 시나리오만 재현한 최소 더미이지, 이 프로젝트의 모든 IDOR·
N+1 케이스에 대응하는 범용 스테이징 환경이 아닙니다 — 전체설계 10-0절의 완전한 형태(임의
엔드포인트 대상 범용 프로빙, ZAP/k6 선택 연동)는 여전히 로드맵입니다.

### 10-D. `config.yaml`에 DB 설정 + 점검 대상 소스 경로 추가 (전체설계 3-5-1절/12절)

**배경(2026-09-03, 사용자 지적)**: `config.yaml`을 직접 확인한 사용자가 두 가지 누락을
지적했습니다 — ① DB 모델(EDB/Oracle 등)과 커넥션 정보가 설정에 없다, ② 점검 대상 소스가
`data/` 하위에 하드코딩돼 있고 경로 자체가 설정에 없다(최종적으로는 Git 저장소 주소 또는
로컬 경로 중 하나를 택해 설정하는 방식이어야 함). 둘 다 실제로 사실이었습니다 —
CLAUDE.md 10-B절은 이미 "`db_adapter` 레지스트리는 설정값 기반 라우팅 구조"라고
**주장**해 왔지만, 실제 코드(`db_adapter = DbAdapter()`)는 하드코딩된 싱글턴이라 그
주장이 거짓이었다는 것도 이번에 함께 드러났습니다.

**구현**:
- **`config.yaml`에 `sources:` 절 추가**: 언어별로 `type: local`(경로) 또는 `type: git`
  (저장소 URL, 아직 미구현)을 고릅니다 — 전체설계 12절 "관리 화면"이 정식 개발 단계에서
  관리할 정보를 미니PJT에서는 이 파일로 대신합니다. 지금은 세 언어 전부 `type: local`로
  기존 `data/sample_*_app` 경로를 명시적으로 적어 둡니다.
- **`config.yaml`에 `db:` 절 추가**: `engine: sqlite` + `path`/`schema_path`, 그리고
  상용 DB(Oracle/EDB/Db2)로 확장할 때 필요한 `host`/`port`/`database`/`user`/
  `password_ref` 필드를 **주석 처리된 예시**로 남겨 스키마를 미리 보여줍니다(비밀번호는
  절대 평문 저장하지 않고 비밀 관리 시스템 참조 키만 저장한다는 2-1절 원칙을 예시에도
  반영).
- **`src/config.py`**: `load_source_config(name)`(`sources.<name>` 반환), `load_db_config()`
  (`db` 절 반환) 추가. 공통 `_load_config()` 헬퍼로 파일 읽기·파싱 중복을 없앴습니다.
- **`src/tools.py`**: `_resolve_source_path(name, default)`가 `sources.<name>`을 읽어
  `vue3_adapter`/`java_lite_adapter`/`python_adapter` 싱글턴 생성 시 경로를 넘깁니다 —
  설정이 없으면(방어적 기본값) 기존 하드코딩 경로를 그대로 씁니다. `type: git`이면
  아직 clone 로직이 없다는 `NotImplementedError`를 명확히 던집니다. DB는
  `_DB_ADAPTER_REGISTRY`(`{"sqlite": DbAdapter, "oracle": None, "edb": None, "db2": None}`)와
  `_resolve_db_adapter_from_config()`로 `agent.py`의 `_LANGUAGE_ADAPTER_REGISTRY`/
  `_resolve_adapters_from_config()`와 완전히 같은 패턴을 씁니다 — 등록 안 된 이름은
  `ValueError`(오타 등), 등록은 됐지만 어댑터가 없는 이름(oracle/edb/db2)은
  `NotImplementedError`(로드맵)로 구분해 던집니다.
- **실제로 버그 1건을 발견하고 고쳤습니다**: 처음 구현에서는 `_DB_ADAPTER_REGISTRY`에
  `sqlite`만 넣고 `if engine != "sqlite": raise NotImplementedError`를 따로 뒀는데,
  `engine not in _DB_ADAPTER_REGISTRY` 체크가 `sqlite` 아닌 모든 값을 이미 `ValueError`로
  걸러내 버려서 `NotImplementedError` 분기가 **죽은 코드**였던 것을 실측(오라클 이름으로
  호출)으로 확인했습니다. **수정**: `oracle`/`edb`/`db2`를 레지스트리에 값 `None`으로
  먼저 등록해, "아예 모르는 이름"과 "알려진 로드맵 대상"을 구분되게 했습니다.
- **`_PROJECT_ROOT` 중복 제거**: 이 작업 중 `tools.py` 안에 `_PROJECT_ROOT`가 두 곳(파일
  상단 신규 추가분, 5-2절 스테이징 서버 코드 안 기존분)에 동일한 값으로 중복 정의된 것을
  발견해 파일 상단 하나로 통합했습니다.

**실측 검증**: `vue3_adapter.project_dir`/`java_lite_adapter.src_dir`/
`python_adapter.project_dir`/`db_adapter.db_path`/`db_adapter.schema_path`가 모두
`config.yaml` 값에서 정확히 해석되는 것을 확인했고, 10-A~10-C절 전체 재검증(vue3/java/
python 스캔, DB 스키마/실행계획, 스테이징 프로브·부하테스트, `collect_findings()` 14건 —
**이 숫자는 10-E절의 MyBatis 확장 이후 15건으로 바뀝니다**, `make_supervisor()` 전체
파이프라인)이 이 리팩터링 후에도 회귀 없이 그대로 통과하는 것을 확인했습니다. `type: git`/
`db.engine: oracle`/등록 안 된 엔진 이름 3가지 오류 경로도 각각 의도한 예외가 실제로
던져지는 것을 확인했습니다.

**알려진 제약(정직하게 남김)**: `type: git`(git clone)과 `oracle`/`edb`/`db2` DB 어댑터는
**스키마·에러 메시지만 있고 실제 구현은 로드맵입니다** — 지금 당장 config.yaml에 그
값들을 넣으면 명확한 `NotImplementedError`로 실패합니다(조용히 무시되거나 틀리게 동작하지
않음). 사용자가 요청한 "최종적으로는 Git 주소 또는 로컬 경로 중 하나를 택하는 방식"이라는
**스키마 형태**는 실제로 만들었지만, **git 저장소를 실제로 clone해 스캔하는 기능**은
3일 미니PJT 범위 밖입니다.

**추가 개선(2026-09-03, 사용자 재요청) — 절대경로 지원 + 넓은 폴더에서도 자동 탐색**:

- **절대경로**: `_resolve_source_path()`의 `_PROJECT_ROOT / source["path"]`는 표준
  라이브러리 `Path.__truediv__`가 오른쪽 피연산자가 절대경로면 왼쪽을 버리고 그 절대경로를
  그대로 반환하는 동작(실측 확인)을 그대로 이용합니다 — 코드 변경 없이 상대·절대 경로
  모두 같은 한 줄로 처리됩니다. Agent 실행 위치와 점검 대상 프로젝트가 완전히 다른 곳에
  있을 수 있다는 실사용 시나리오에 대응하기 위해, `config.yaml`의 `sources.*.path`를
  전부 절대경로 예시로 바꿨습니다.
- **넓은 공유 폴더에서도 언어별 자동 탐색**: 사용자가 "3언어 모두 `data`(상위 공유 폴더)
  하나로만 설정해도 정상 동작해야 한다"고 요청해, 각 어댑터가 **자기 언어에 맞는 파일을
  스스로 찾도록** 바꿨습니다.
  - `Vue3Adapter`: `_discover_npm_project_dir()`(신규) — 주어진 경로에 `package.json`이
    직접 없으면 하위 트리를 재귀 탐색(`node_modules` 제외)해 가장 얕은 `package.json`을
    찾아 그 디렉터리를 실제 npm 프로젝트 루트로 씁니다.
  - `JavaLiteAdapter`: 카테고리별 고정 파일 목록(`_SECURITY_REVIEW_FILES`/
    `_PERFORMANCE_REVIEW_FILES`)을 없애고, `_discover_java_files()`(신규)가 `src_dir`
    아래에서 **재귀적으로 모든 `.java` 파일**을 찾아(`_JAVA_EXCLUDED_FILENAMES =
    {"AwsConfig.java"}`만 여전히 명시적으로 제외) security/performance 두 카테고리
    모두에 **같은 파일 목록**을 줍니다. 어떤 파일이 어느 카테고리와 관련 있는지는 이제
    파일 목록이 아니라 카테고리별 지시문의 "다른 범주는 findings에 포함하지 마라"는
    원칙 하나로만 가릅니다 — 실측 검증 결과 교차 오염(security 리뷰에 N+1이 섞이거나
    그 반대) 없이 여전히 정확히 분리되는 것을 확인했습니다.
  - `PythonAdapter`: 변경 없음 — `bandit -r`/`pylint`가 원래도 재귀 스캔이라 이미 넓은
    폴더에서도 정확히 동작했습니다(사전 조건 충족 확인만 함).
- **실측 검증(핵심 시나리오)**: `config.yaml`의 `sources.vue3`/`sources.java`/
  `sources.python`을 **셋 다 같은 절대경로(`data/`, 세 언어 전용 폴더+가이드+DB+
  스테이징 앱이 전부 섞여 있는 최상위 폴더)로 설정한 채** 전체를 재실행 — `vue3_adapter`
  는 `data/sample_vue3_app`을 정확히 찾아냈고, `java_lite_adapter`는 정확히 4개 파일
  (`AwsConfig.java` 제외)만 찾아냈으며, `python_adapter`는 `data/staging_app/app.py`
  (5-2절 스테이징 앱, 무관한 파일)까지 스캔 범위에 들어갔지만 그 파일에서 아무 finding도
  나오지 않아 노이즈가 생기지 않는 것을 확인했습니다. `collect_findings()` 결과는 이
  극단적으로 넓은 설정에서도 여전히 **14건**(보안 11/오류 2/성능 1, MyBatis XML 확장
  전 시점의 숫자 — 10-E절 이후로는 15건)으로 완전히 동일했고, `make_supervisor()` 전체
  파이프라인도 회귀 없이 통과했습니다.
- **알려진 제약**: `PythonAdapter`는 자체 탐색을 하지 않고 `bandit -r`/`pylint`의 재귀
  스캔에 그대로 의존하므로, 설정된 폴더가 아주 크면(예: `node_modules`까지 포함) 그만큼
  스캔 시간이 늘어납니다 — 이번 실측(수십~수백 개 파일 규모)에서는 문제없었지만, 실제
  대형 모노레포에 그대로 적용하면 성능이 나빠질 수 있어 정식 개발 단계에서는 언어별
  파일 확장자 필터를 미리 적용한 뒤 스캔하는 최적화가 필요할 수 있습니다(로드맵).

**DB 설정 필드는 `engine`별로 다르다는 점 명확화(2026-09-03, 사용자 지적)**: 사용자가
"상용 DB(EDB/Oracle 등)에서는 `path`/`schema_path`가 제공되지 않고 `engine`/`host`/
`port`/`database`/`user`/`password_ref`만 제공될 것"이라고 지적했습니다 — 맞는
지적이라 `config.yaml`의 `db:` 절 주석을 두 필드 집합이 **상호 배타적**임을 명확히
하도록 고쳤습니다(SQLite는 서버·인증이 없는 임베디드 DB라 커넥션 정보 자체가 없고,
상용 DB는 파일 경로 개념이 없습니다). 코드(`_resolve_db_adapter_from_config()`)는
원래도 `db_config.get("path")`의 존재 여부가 아니라 **`engine` 값 자체로 분기**하고
있어(등록 안 된 이름은 `ValueError`, 등록됐지만 미구현이면 `NotImplementedError`) 이
지적이 실제 버그로 이어지진 않았지만, 앞으로 상용 DB 어댑터를 구현할 사람이 같은 원칙
(필드 존재 여부가 아니라 `engine`으로 분기)을 지키도록 `_resolve_db_adapter_from_config()`
와 `load_db_config()`의 문서 주석에도 명시적으로 남겼습니다.

**MyBatis(XML) 관련 질의응답(2026-09-03, 사용자 질문)**: "`config.yaml`의 `languages`에
`xml`을 추가하면 MyBatis 매퍼 XML의 SQL Injection(`${}` 문자열 치환 vs `#{}` 파라미터
바인딩)도 점검되는가?"라는 질문에 대한 답 — **아니요, 그렇게는 안 됩니다.** `languages`의
각 항목은 `_LANGUAGE_ADAPTER_REGISTRY`에 실제로 등록된 이름이어야 하는데, `"xml"`은
등록돼 있지 않아 `_resolve_adapters_from_config()`가 즉시 `ValueError`로 실패합니다.
그리고 XML은 애초에 "언어"가 아니라 Java 프로젝트 안에서 SQL을 표현하는 형식이라, 별도
`XmlAdapter`를 만드는 것보다는 **`JavaLiteAdapter`의 SQL Injection 점검 범위를 `.java`
뿐 아니라 관련 `.xml` 매퍼 파일까지 넓히는 것**이 아키텍처적으로 더 맞습니다 — MyBatis의
`${}` 치환은 CLAUDE.md가 이미 정의한 Java lite 리뷰 범위 ②("도구 기본 룰셋이 인식 못 하는
래퍼/추상화를 거친 SQL Injection", `DbHelper.executeRaw()`와 정확히 같은 성격의 문제)에
그대로 들어맞습니다. **사용자가 "넓혀 달라"고 요청해 바로 실제로 구현했습니다 — 아래
10-E절 참고.**

### 10-E. MyBatis 매퍼 XML의 `${}` SQL Injection 점검 (2026-09-03 추가, 사용자 요청)

**배경**: 위 질의응답에서 제안한 확장을 사용자가 바로 요청해 구현했습니다.

**구현**:
- **더미 소스**: `data/sample_java_app/src/main/resources/mapper/OrderMapper.xml`(신규)
  — 실제 Maven 프로젝트 레이아웃(`src/main/resources`가 `src/main/java`의 형제 폴더)을
  그대로 재현. `findOrderById`는 안전한 `#{orderId}`(파라미터 바인딩)를, `findOrdersSortedBy`
  는 의도적으로 취약한 `${sortColumn}`(문자열 치환 — ORDER BY 절처럼 `#{}`로 파라미터화가
  안 되는 자리에 실무에서 흔히 잘못 쓰는 자리)를 씁니다.
- **`_JAVA_SRC_DIR` 기본값을 넓힘**: `.../java/com/example/dummy`(정확한 패키지 경로)에서
  `data/sample_java_app`(Maven 프로젝트 루트)로 바꿔, `config.yaml` 설정이 없어도 재귀
  탐색이 `src/main/resources`의 매퍼까지 자연스럽게 찾게 했습니다(10-D절에서 만든 재귀
  탐색 인프라를 그대로 재사용).
- **`_discover_mybatis_xml_files()`**(신규, `src/tools.py`): `src_dir` 아래 `*.xml`을
  재귀 탐색하되, 내용에 `<mapper` 문자열이 있는 파일만 골라 `pom.xml`/`web.xml` 같은
  무관한 XML을 배제합니다.
- **`_SECURITY_INSTRUCTIONS`에 3번째 항목 추가**: 기존 "① IDOR, ② 래퍼 경유 SQLi"에
  "③ MyBatis `${}` SQLi"를 추가하고, 같은 파일의 안전한 `#{}` 쿼리는 findings에 넣지
  말라고 명시했습니다.
- **`JavaLiteAdapter._review()`에 `include_mybatis_xml` 플래그 추가**: `run_security()`
  만 `True`로 호출해 `.java`+`.xml` 소스를 함께 LLM에 보여줍니다 — `run_performance()`는
  기존대로 `.java`만 봅니다(MyBatis 매퍼 자체엔 N+1 개념이 없음).

**실측 검증**: `java_lite_adapter.run_security()` → **3건**(기존 IDOR·래퍼 SQLi에 MyBatis
`${}` SQLi 1건 추가), `#{orderId}` 안전 쿼리는 findings에 포함되지 않음을 확인.
`run_performance()`(1건, N+1)·`run_error()`(0건)는 변화 없음. `collect_findings()`(3언어
통합) 총 **15건**(보안 12/오류 2/성능 1)으로 정확히 1건 늘었고, `make_supervisor()`에
"MyBatis 매퍼 XML에 SQL Injection 취약점이 있는지 점검해줘"를 실제로 질의해 정확한 근거
(`${sortColumn}` vs `#{orderId}` 구분, 악용 시나리오 예시, 화이트리스트 검증 권장)를 포함한
답변을 확인했습니다.

**알려진 제약**: MyBatis 매퍼 XML 탐지는 `<mapper` 문자열 포함 여부로만 판별하는 단순
휴리스틱입니다 — XML 파서로 실제 루트 엘리먼트를 확인하는 것보다 약하지만, 이 프로젝트
더미 데이터 범위에서는 오탐 없이 정확히 동작합니다(실측 확인).

### 10-F. `languages`/`sources` → 언어 자동 감지 + `exceptLanguages`로 전환 (2026-09-03, 사용자 요청)

**배경**: 사용자가 `config.yaml`을 다시 보고 구조 변경을 요청했습니다 — ① `sources`는
언어별로 따로 둘 필요 없이 프로젝트 루트에 대해 타입+경로 하나면 충분하다, ② 언어는
기본적으로 그 루트 아래 모든 파일을 읽어(txt/md 같은 참고 파일 제외) 자동으로 목록을
뽑고 리포트 상단에 보여준다, ③ 실제 프로그래밍 언어인데 어댑터가 없어 못 읽는 언어는
"점검불가" 코멘트를 단다, ④ 그러면 `languages`(포함 목록)는 필요 없어지므로
`exceptLanguages`(제외 목록)로 바꾸고 제외된 언어는 리포트에 "점검제외"로 표시한다.

**구현**:
- **`config.yaml`**: `languages:` 목록과 언어별 `sources:` 딕셔너리를 없애고, 프로젝트
  전체에 대한 `source:`(단일 `type`+`path`) 하나와 `exceptLanguages:`(기본 빈 리스트)로
  바꿨습니다.
- **`src/config.py`**: `load_active_languages()`/`load_source_config(name)`을
  `load_source()`(단일 루트 반환)/`load_except_languages()`(제외 목록 반환)로 교체.
- **`src/tools.py`**: `_resolve_source_path(name, default)`(언어별)를
  `resolve_project_root()`(전체 하나)로 교체하고, 그 결과를 `PROJECT_SOURCE_ROOT`
  상수로 한 번만 계산해 `vue3_adapter`/`java_lite_adapter`/`python_adapter` 세 싱글턴
  전부에 **같은 루트**를 넘깁니다 — 각자 내부 재귀 탐색(10-D/10-E절에서 이미 만든
  `_discover_npm_project_dir`/`_discover_java_files`/`bandit -r`)으로 자기 언어에 맞는
  파일을 찾습니다.
- **`src/agent.py`**: `_EXTENSION_LANGUAGE_MAP`(확장자 → 언어 이름, 어댑터가 없는 흔한
  언어(go/ruby/php/c/cpp/csharp/typescript/rust/kotlin/swift/scala)도 "점검불가" 표시를
  위해 등록), `_detect_languages(root)`(`os.walk`로 재귀 스캔, `node_modules`/`.git`/
  `__pycache__`/`.venv`/`dist`/`build`는 성능·오탐 방지를 위해 순회에서 제외),
  `_classify_languages(detected, except_languages)`(`unsupported`/`excepted`/`active`
  3분류)를 추가했습니다. `_LANGUAGE_ADAPTER_REGISTRY`(언어별 어댑터 매핑)와
  `LanguageAdapter` Protocol을 파일 앞쪽(전문 Agent 3개보다 먼저)으로 옮겨 이 감지
  로직이 참조할 수 있게 했고, 기존에 파일 뒤쪽에 있던 중복 정의는 지웠습니다. 결과는
  `LANGUAGE_STATUSES`(모듈 로드 시 한 번만 계산, 파일시스템 재스캔 방지)로 캐싱하고,
  `_resolve_adapters_from_config()`/`_ACTIVE_LANGUAGES_LABEL`(가드레일 문구) 둘 다 이제
  이 캐시에서 `"active"`인 것만 읽습니다.
- **`src/report.py`**: `render_markdown()`/`save_report()`에 `language_statuses`
  파라미터를 추가해, 리포트 최상단에 "감지된 언어: Vue3, Java, Python" 같은 줄을
  넣습니다 — 제외된 언어는 "Java(점검제외)", 어댑터 없는 언어는 "Go(점검불가)"로
  표시됩니다. `report.json`에도 `languages` 배열로 같은 정보를 담습니다.
- **`src/api.py`**: `agent.py`의 `LANGUAGE_STATUSES`를 가져와 `save_report()` 호출에
  넘깁니다.

**실측 검증**:
1. 기본 설정(`exceptLanguages: []`)에서 `LANGUAGE_STATUSES` → `[('java', 'active'),
   ('python', 'active'), ('vue3', 'active')]`, `collect_findings()` 15건(10-E절과
   동일) — 회귀 없음 확인.
2. `data/`에 실제 더미 `.go` 파일을 하나 추가해 재감지 → `go`가 `unsupported`로 정확히
   분류되는 것을 확인(테스트 후 파일 삭제).
3. `config.yaml`의 `exceptLanguages`를 `[java]`로 바꿔 재실행 → `LANGUAGE_STATUSES`에서
   `java`가 `excepted`로 표시되고, `collect_findings()`가 정확히 **11건**(15 − Java
   보안 3 − Java 성능 1)으로 줄었으며, `render_markdown()` 결과 최상단에 "감지된 언어:
   Java(점검제외), Python, Vue3"가 정확히 나오는 것을 확인(테스트 후 원래 값으로 복원).
4. Rust로 작성된 프로젝트를 점검해 달라는 질문에 여전히 정직하게 "Java/Python/Vue3만
   지원한다"고 거절하는 것을 확인(가드레일 회귀 없음, `_ACTIVE_LANGUAGES_LABEL`이 새
   캐시에서도 올바르게 채워짐).

**알려진 제약**: (1) `.js` 확장자를 전부 `vue3`로 매핑합니다 — 이 미니PJT 안에서는
Vue3 프로젝트의 `.js`뿐이라 문제없지만, 실제로는 순수 Node.js 백엔드와 Vue3 프런트엔드가
같은 확장자를 공유해 프레임워크(예: `package.json`의 `vue` 의존성 유무)까지 봐야 정확히
구분되는 로드맵 항목입니다. (2) `_EXTENSION_LANGUAGE_MAP`은 흔한 언어 위주의 목록이라
모든 언어를 다 알지는 못합니다 — 맵에 없는 확장자는 "언어가 아예 없다"가 아니라 "감지
못 함"으로 조용히 무시됩니다(txt/md 같은 참고 파일과 구분이 안 됨 — 사용자가 요청한
범위 안에서는 문제없지만, 완전히 새로운 언어가 추가될 때마다 이 맵도 함께 갱신해야
합니다).

**추가로 실제 버그 1건을 발견하고 고쳤습니다(2026-09-03, 사용자가 "실행 방법이
바뀌었나?"라고 물어본 것을 계기로 재검증하다 발견)**: `config.yaml`의 `source.path`가
가리키는 디렉터리가 실제로 존재하지 않으면(예: Docker 컨테이너·다른 머신·zip 압축 해제
후처럼 절대경로가 그 환경에 안 맞을 때) `resolve_project_root()`가 그 경로를 그대로
반환하고, `_detect_languages()`의 `os.walk()`가 **예외 없이 빈 결과만 반환**해 "언어가
0개 감지됨"으로 조용히 잘못 넘어가는 것을 실측으로 확인했습니다 — 에러가 안 나서 원인을
찾기 매우 어려운 부류의 실패입니다. **수정**: `resolve_project_root()`가 반환 직전에
`resolved.is_dir()`을 확인해, 없으면 `FileNotFoundError`로 어느 경로가 문제인지 정확히
알려주도록 했습니다(실측 확인: 존재하지 않는 경로로 바꾸면 즉시 명확한 에러로 죽음).
이 김에 `config.yaml`의 기본 `source.path`도 **절대경로(이 개발 머신 고정 경로)에서
프로젝트 루트 기준 상대경로(`data`)로 되돌렸습니다** — 미니PJT의 점검 대상은 이 zip/
컨테이너 안에 함께 들어 있는 `data/`라, 절대경로를 한 기기에 고정해 두면 실행 환경이
바뀔 때마다(로컬→Docker→다른 채점 머신) 반드시 깨지기 때문입니다. 절대경로 지원 자체는
코드에 그대로 남아 있고(주석 예시로 안내), Agent와 점검 대상이 실제로 다른 위치에 있는
배포 시나리오에서는 여전히 씁니다 — 이번 미니PJT의 자체 더미 데이터에는 상대경로가
맞을 뿐입니다. `uvicorn`으로 서버를 실제로 띄우고 `POST /query`를 실제 호출해 `report.md`
상단에 "감지된 언어: Java, Python, Vue3"와 15건이 정확히 나오는 것까지 재검증했습니다 —
**실행 방법(서버 기동 명령, API 스펙) 자체는 바뀌지 않았습니다.**

**추가로 실제 버그 1건을 더 발견하고 고쳤습니다(2026-09-03, 사용자가 "`exceptLanguages`에
대소문자 차이가 영향이 있을까요?"라고 물어본 것을 계기로 재검증하다 발견)**:
`_detect_languages()`가 만드는 감지된 언어 이름은 항상 소문자("java"/"python"/"vue3"
등, `_EXTENSION_LANGUAGE_MAP`의 값이 전부 소문자로 고정돼 있음)인데, `load_except_languages()`
는 `config.yaml`의 `exceptLanguages` 값을 아무 정규화 없이 그대로 반환하고 있었습니다 —
사람이 직접 타이핑하는 값이라 `Java`/`JAVA`처럼 대소문자가 섞일 수 있는데,
`_classify_languages()`의 `name in except_languages` 비교는 대소문자를 구분합니다.
**실측 재현**: `_classify_languages({'java'}, {'Java'})`를 직접 호출해보니 `java`가
`excepted`가 아니라 `active`로 나왔습니다 — 즉 `exceptLanguages: [Java]`라고 적으면
**에러 없이 조용히 아무 효과도 없고 Java가 여전히 점검 대상에 남는** 실제 버그였습니다
(에러가 안 나서 원인을 찾기 매우 어려운, 위 `source.path` 버그와 같은 부류의 실패).
**수정**: `_classify_languages()` 안에서 `except_languages`를 받자마자 전부 소문자로
정규화하도록 한 줄 추가했습니다 — 호출부(`LANGUAGE_STATUSES` 계산)를 고칠 필요 없이
이 함수 하나만 고치면 됩니다. **실측 재검증**: `Java`/`java`/`JAVA` 세 가지 표기 전부
`java`를 정확히 `excepted`로 분류하는 것을 확인했습니다.

### 10-G. 최소 실행 UI — 버튼 하나로 실행 + 실시간 진행률/완료 확인 (2026-09-03, 사용자 요청)

**배경**: 사용자가 "로컬에서도 터미널로 실행하기가 귀찮다"며, 언어별로 나눌 필요 없이
버튼 하나로 실행하고 진행률·완료 여부를 화면에서 볼 수 있는 페이지를 요청했습니다.

**구현**:
- **`GET /`**(`src/api.py`): `src/static/index.html`을 그대로 서빙하는 최소 UI. "점검
  실행" 버튼 하나만 있고, 언어별 버튼은 없다 — Supervisor가 질문 내용과 무관하게 항상
  3개 전문 Agent를 전부 병렬 실행하는 기존 설계(3-6절 "선택적 실행"은 로드맵)를 그대로
  쓰기 때문이다.
- **`POST /scan`**(신규): 고정 질문(`_SCAN_QUESTION`)으로 Supervisor 실행을 백그라운드
  스레드(`threading.Thread`, 데몬)에서 시작하고 `job_id`만 즉시 반환한다. Celery/Redis
  같은 별도 작업 큐는 쓰지 않는다 — 로컬 1인 사용 규모에는 메모리 dict(`_jobs`)로
  충분하고, 새 의존성을 추가하지 않아도 된다.
- **`GET /scan/{job_id}`**(신규): 진행 중이면 지금까지 끝난 노드 목록(`completed_steps`)
  과 경과 시간을, 끝났으면 `answer`/`counts`/`languages`/`report_md`를 반환한다.
- **진행률은 가짜(fake) 퍼센트가 아니라 실제 노드 완료 이벤트를 씁니다** — Supervisor의
  `.stream(state, stream_mode="updates")`가 그래프의 5개 노드(`call_security`/
  `call_error`/`call_performance`/`build_findings`/`aggregate`)가 끝날 때마다 그 이름으로
  이벤트를 주는 것을 실측으로 확인했고(`invoke()` 대신 이걸 써서 백그라운드 스레드 안에서
  진행 중에도 `_jobs[job_id]["completed_steps"]`를 계속 채워 나간다), 프런트엔드는 이
  값을 1초 간격으로 폴링해 진행률 바와 "N/5단계 완료" 텍스트를 그린다.
- **`src/static/index.html`**(신규): 순수 HTML+CSS+바닐라 JS(빌드 도구·프레임워크 없음)
  — 버튼 클릭 → `POST /scan` → `job_id`로 `GET /scan/{job_id}` 1초 폴링 → 완료되면
  진행률 바를 100%로 채우고, 감지된 언어 태그(점검제외/점검불가 라벨 포함)·카테고리별
  건수·`report.md` 전문을 화면에 그대로 보여준다.
- **API 스펙(0-2절, 고정) 준수**: `POST /query`의 요청/응답 모양은 전혀 건드리지
  않았다 — `GET /`/`POST /scan`/`GET /scan/{job_id}`는 그 스펙 밖의 순수 UI 편의
  엔드포인트다(`config.yaml`/`reports/`가 0-1절 목록 밖에 추가된 것과 같은 선례).

**실측 검증**: 서버를 실제로 띄우고 `POST /scan` → `GET /scan/{job_id}`를 1초 간격으로
10회 폴링해, `completed_steps`가 `[]` → `['build_findings']` → `['build_findings',
'call_error']` → ... → 5개 전부로 **실제 시간차를 두고 하나씩 늘어나는 것**을 확인했다
(총 56.1초 소요, LLM 호출 속도 차이 때문에 노드마다 끝나는 시점이 실제로 다름 — 이게
바로 "진짜 진행률"이라는 근거). 최종 응답에서 `total: 15`, `counts`(보안 12/오류 2/
성능 1), `languages`(3개 전부 active), `report_md`(감지된 언어 줄 포함)가 전부 정확히
나오는 것을 확인했다. 알 수 없는 `job_id`로 조회하면 `404`가 나는 것, 그리고 이 모든
변경 후에도 `POST /query`가 기존과 동일하게 동작하는 것까지 재확인했다.

**알려진 제약**: (1) `_jobs`는 메모리 dict라 서버 프로세스를 재시작하면 이전 job 기록이
사라진다 — 로컬 1회성 실행 UI 목적에는 문제없다. (2) 동시에 여러 스캔을 겹쳐 실행해도
막지 않는다(잠금 없음) — 로컬 1인 사용을 가정한 범위 밖 시나리오라 다루지 않았다. (3)
서버 프로세스를 강제 종료(`kill -9`류)하면 5-2절 스테이징 서버(포트 8500) 서브프로세스가
`atexit` 핸들러를 못 타고 남을 수 있다 — 정상 종료(Ctrl+C 등)에서는 문제없다(실측 중
발견해 수동으로 정리함, 코드 결함이 아니라 강제 종료 자체의 근본적 한계).

### 10-H. 리포트 이력 보존 — 실행마다 타임스탬프 파일 추가 (2026-09-03, 사용자 요청)

**배경**: 사용자가 "2회 이상 실행하면 리포트 파일이 2개 생기는 게 맞냐"고 물어 확인해
보니, 실제로는 `report.md`/`report.json`을 매번 **덮어써서** 직전 실행 결과가 사라지는
것으로 실측 확인됐습니다(코드 확인 + LLM 호출 없는 직접 `save_report()` 2회 호출 테스트
둘 다로 재확인). 사용자가 "우선은 파일명에 타임스탬프를 붙이는 정도로" 이력 보존 기능을
요청했습니다.

**구현**(`src/report.py`의 `save_report()`): 실행마다 `report_<UTC 타임스탬프
YYYYMMDD_HHMMSS>.md`/`.json`(예: `report_20260903_042633.md`)을 **새 파일로** 만들어
이력을 남기고, 동시에 `report.md`/`report.json`("최신" 편의 사본)도 그대로 계속
갱신한다 — 기존 UI(`GET /`)·`POST /query`·`POST /scan` 어느 경로로 호출해도 똑같이
적용된다(전부 같은 `save_report()`를 거치므로). `save_report()`의 반환값을 `None`에서
방금 만든 타임스탬프 `.md` 경로로 바꿔, `api.py`의 `_run_scan_job()`이 그 경로를
`job["report_file"]`로 넘기고 `GET /scan/{job_id}` 응답에 포함시킨다. `src/static/
index.html`도 완료 화면에 "이력 저장됨: `reports/report_<타임스탬프>.md`"를 보여주도록
고쳤다.

**실측 검증**: 서버를 실제로 띄우고 `POST /scan`을 **2회 연속** 실행해 `reports/`에
`report_20260903_042633.*`와 `report_20260903_042715.*`가 **둘 다 그대로 남아 있는
것**을 확인했고(각각 41초 간격), 이어서 `POST /query`도 호출해 세 번째 타임스탬프
파일(`report_20260903_042739.md`)이 또 생기는 것까지 확인했다 — 세 경로(`/query`/
`/scan`) 전부 같은 이력 보존 동작을 공유한다. `report.md`(최신 사본)는 그때마다 가장
최근 실행 내용으로 갱신되는 것도 확인했다. 이 검증은 모델을 Haiku 4.5
(`us.anthropic.claude-haiku-4-5-20251001-v1:0`)로 교체한 뒤 진행했다 — 앞서 여러 차례
Bedrock 일일 토큰 한도(`ThrottlingException`)에 막혔던 `claude-sonnet-4-6`/
`claude-sonnet-4-5` 계열과 달리 이번엔 전체 파이프라인이 막힘 없이 끝까지 돌아갔다
(총 15건, 보안 12/오류 2/성능 1로 기존과 동일한 결과 — 모델 교체가 findings 자체를
바꾸지 않는다는 조건 9 모델 독립성도 함께 재확인됨).

**알려진 제약**: (1) 타임스탬프는 초 단위다 — 같은 초 안에 두 번 저장하면 마지막
저장이 앞선 파일을 덮어쓸 수 있지만, 이 파이프라인은 매 실행이 최소 수 초~수십 초
걸리는 LLM 호출을 포함해 실제로 부딪힐 상황이 아니다(마이크로초까지 넣는 건 이번
범위에서는 과한 정밀도라 넣지 않았다). (2) **이력을 나열·조회하는 UI/API는 아직
없다** — `reports/` 폴더를 직접 열어봐야 과거 실행을 찾을 수 있다. 사용자가 "우선은
파일명에 타임스탬프만"이라고 명시적으로 범위를 좁혔으므로, 이력 목록 화면·오래된
파일 자동 정리(retention) 같은 것은 로드맵으로 남긴다. (3) 이력 파일은 무한히 쌓인다
— 정리(삭제) 로직이 없어 오래 쓰면 `reports/` 폴더가 계속 커진다(로드맵).

### 10-I. 전체 코드 재점검 + 샘플 데이터 다양화 (2026-09-03, 사용자 요청)

**배경**: 사용자가 "지금까지 개발된 전체부분을 점검"하고 `data/` 폴더의 샘플 데이터도
"좀 더 다양하게 생성"해 달라고 요청했다. `src/agent.py`·`tools.py`·`config.py`·
`report.py`·`api.py`·`retriever.py`·`static/index.html`을 전부 다시 읽으며 진행한
재점검이다.

**코드 재점검 결과 — 사소한 문제 3건, 전부 수정**:

1. `src/api.py`의 `_JobStatus = Literal["running", "done", "error"]`가 정의만 되고
   어디서도 쓰이지 않는 죽은 코드였다 — `_jobs`가 `dict[str, dict[str, Any]]`로 값
   타입이 이미 `Any`라 `_JobStatus`를 끼워 넣을 자리가 없었다. `TypedDict`로 확장하는
   건 이 정도 규모의 잡(job) 딕셔너리에는 과한 추상화라 판단해, 대신 미사용 별칭과
   그로 인해 함께 미사용이 된 `Literal` import를 제거했다.
2. `src/tools.py` 최상단 모듈 docstring이 여전히 "언어 어댑터(vue3_adapter/
   java_lite_adapter)와 공통 LLM 생성 지점"이라고만 적혀 있어, 그 사이 추가된
   `python_adapter`/`db_adapter`/pentest·부하테스트 도구(`probe_idor_vulnerability()`,
   `run_concurrent_load_test()`)가 전혀 언급되지 않았다 — 실제 파일 구성을 반영하도록
   다시 썼다.
3. `src/agent.py`의 `CombinedAdapter` docstring이 "Supervisor가 Vue3+Java 두
   프로젝트를 한 번에 조사"라고 적혀 있었는데, 10-F(언어 자동 감지)로 어댑터 개수가
   고정 2개에서 감지된 언어 수만큼 가변으로 바뀐 지 오래라 실제 동작과 어긋났다 —
   "현재는 Vue3/Java/Python 3개지만 몇 개든" 식으로 언어 개수에 무관하게 맞도록
   고쳤다.

**버그 발견 및 수정 — `mask_pii()`가 콜론(`:`) 구분자를 놓치는 문제**: 샘플 데이터를
다양화하며 Python bandit이 잡는 하드코딩 비밀번호 패턴(B105)을 심다가, bandit 자체의
finding 메시지 형식이 `"Possible hardcoded password: 'admin1234'"`처럼 **콜론**으로
값을 표기한다는 것을 실측으로 발견했다. 그런데 `src/agent.py`의
`_SECRET_ASSIGNMENT_PATTERN`은 원래 `keyword = "value"`(등호)만 잡도록 되어 있어,
이 콜론 형식의 더미 비밀번호가 마스킹 없이 그대로 Finding에 노출되고 있었다 — 조건
9(민감정보 마스킹)를 도구가 만들어내는 메시지 안의 값에는 못 지키고 있던 실제 결함이다.
정규식 구분자를 `\s*=\s*`에서 `\s*[:=]\s*`로 넓혀(등호와 콜론 둘 다 허용) 고쳤다.
독립 테스트 스크립트로 세 가지를 모두 실측 재확인했다 — (1) bandit 콜론 형식이 이제
`"Possible hardcoded password = "***MASKED_SECRET***""`로 정상 마스킹됨, (2) 기존
Java 등호 형식(`password = "..."`)은 회귀 없이 계속 마스킹됨, (3) AWS 키 패턴(별도
정규식 `_AWS_ACCESS_KEY_PATTERN`)도 영향 없이 그대로 동작함. 이어서 `collect_findings()`
전체 파이프라인을 실제로 돌려, `SEC-5`(B105) finding의 `summary` 필드가 실제 프로덕션
경로에서도 마스킹된 값으로 나오는 것까지 재확인했다.

**샘플 데이터 다양화**(언어별로 다른 방식 적용 — 이유는 아래 "알려진 제약" 참고):

- **Python** (`data/sample_python_app/`): `auth_utils.py`를 새로 추가해 기존
  `api_handler.py`의 명령어 주입(B605) 1건 외에 서로 다른 두 가지 bandit 패턴을 더
  심었다 — 하드코딩된 비밀번호(B105, 위 버그 발견의 계기)와 `eval()` 사용(B307).
  오탐 방지 확인용으로 `string_utils.py`(`slugify()`/`truncate()`, 의도적으로 아무
  문제도 없는 "깨끗한" 파일)도 추가해, bandit/pylint가 여기서는 아무것도 잡지 않는
  것을 실측 확인했다.
- **Java** (`data/sample_java_app/`): `ProductService.java`를 추가했다 — 표준
  `PreparedStatement`로 파라미터를 바인딩하고 조회 조건에 `owner_id`(소유자)까지
  포함해 SQL Injection과 IDOR을 둘 다 막은 "깨끗한" 클래스다. `java_lite_adapter`가
  이제 발견된 `.java` 파일을 전부 자동으로 리뷰하므로(10-F), 문제 없는 파일에서 LLM이
  findings를 지어내지 않는지(오탐 방지) 확인하는 용도다 — 실측 결과 기존과 동일하게
  보안 3건/성능 1건만 나왔고, `ProductService.java`에 대해서는 아무 finding도
  붙지 않았다(LLM이 이 파일을 실제로 리뷰했다는 것은 로그로 확인).
- **Vue3** (`data/sample_vue3_app/`): `package.json`의 `dependencies`에
  `minimist@0.0.8`(알려진 취약 버전)을 추가하고 `npm install`을 실제로 실행해
  `node_modules`/`package-lock.json`을 재생성했다. `npm audit` 결과가 6건 → 8건으로
  늘었고, 그중 하나(`GHSA-xvch-5gv4-984h`, minimist의 Prototype Pollution)는 `npm
  audit`이 매기는 원본 등급이 기존 샘플 데이터에 없던 **critical**이다 — 다만
  `_SEVERITY_MAP`(`agent.py`)이 `critical`을 항상 `high`로 정규화하므로, 리포트에
  실제로 노출되는 `Finding.severity` 값은 여전히 `high`다(critical이라는 문자열
  자체가 최종 결과물에 남는 건 아니다).

**실측 검증 — 새 findings 총계**: `collect_findings()`를 3개 언어 전부에 대해 다시
실행해 총 **19건**(보안 16/오류 2/성능 1)을 확인했다 — 기존 15건(보안 12/오류 2/성능
1)에서 보안 findings만 4건 늘었고(Python +2, Vue3 +2), Java/오류/성능은 그대로다.
`LANGUAGE_STATUSES`도 3개 언어 모두 여전히 `"active"`로 정상 감지됨을 재확인했다.

**알려진 제약**: (1) Python/Vue3처럼 도구 기반(bandit/npm audit) 어댑터는 순수
데이터만 늘려도 새 취약점 유형이 자동으로 잡히지만, Java는 LLM 리뷰 기반이라 진짜
새로운 finding 카테고리를 늘리려면 프롬프트(`_SECURITY_INSTRUCTIONS` 등) 변경이
필요하다 — 이번 Java 추가는 그래서 새 카테고리 대신 "깨끗한 파일 오탐 방지 확인"으로
범위를 좁혔다. (2) `evaluation/test_queries.csv` 점검 결과는 별도로 CLAUDE.md 10-J절
참고 — 개수를 못 박은 일부 문항(Q1/Q2/Q6/Q11)의 숫자가 실제로 낡아 있었고, 이번에
늘어난 finding 종류(하드코딩 비밀번호, eval, Vue3 minimist 취약점)를 직접 묻는 문항은
아직 없었다.

### 10-J. `test_queries.csv` 점검 — 낡은 개수 4건 수정 + 5-8 신규 문항 3건 추가 (2026-09-03, 사용자 요청)

**배경**: "지금까지 처리한 게 다 됐으면 `test_queries.csv`도 추가할 사항이 있는지
검증해 달라"는 요청으로, 20개 기존 문항을 실제 최신 findings(19건, 보안16/오류2/성능1)와
대조 검증했다.

**발견 1 — 개수를 못 박은 문항 4건이 낡아 있었다**(`collect_findings()`를 실제로 다시
실행해 대조 확인):

- `Q1`: "Vue3+Java 보안 발견 총 10건"이라고 적혀 있었는데, 이는 Python 어댑터(5-1-A)도
  붙기 전인 최초 2언어 시절 숫자였다 — Vue3 자체도 이번 minimist 추가로 8건→10건이
  됐고, 3개 언어 합계는 16건이다. Vue3 세부 내역(lodash 6/minimist 2/no-eval 1/
  no-v-html 1 = 10)까지 명시하도록 고쳤다.
- `Q2`: "src/utils.js의 미사용 변수 1건이 오류 카테고리의 **유일한** 발견"이라고 되어
  있었는데, 이는 5-1-A(Python 어댑터, 오류 카테고리에 `unused-import` 1건 추가)가 끝난
  뒤로 줄곧 틀린 채로 방치돼 있었다(이번 5-8과 무관하게 이미 낡아 있던 문항) — 두 건
  모두 나열해야 한다고 고쳤다.
- `Q6`: "보안 10건, 오류 1건, 성능 1건, 총 12건"이 5-4(MyBatis) 완료 시점(15건)보다도
  더 오래된 숫자였다 — 19건(보안16/오류2/성능1)으로 고쳤다.
- `Q11`: "보안 발견이 10건 존재"를 16건으로 고쳤다.

이 네 문항은 매 확장 phase가 끝날 때마다 개수를 갱신했어야 했는데 그러지 못하고
누적으로 낡아 있었다 — `Q16`~`Q20`처럼 phase마다 "이 문항은 X 완료 후 추가"라고
명시적으로 버전을 박아둔 문항들과 달리, `Q1`/`Q2`/`Q6`/`Q11`은 고정 숫자를 그대로
박아 둔 채 버전 표시가 없어서 놓치기 쉬웠던 것으로 보인다.

**발견 2 — 5-8에서 새로 생긴 finding 유형을 직접 묻는 문항이 없었다**: 신규 추가
`Q21`~`Q23`(전부 "확장 5-8 완료 후 추가된 문항이라 1차/2차 평가에는 포함되지 않는다"로
명시):

- `Q21`: `auth_utils.py`의 하드코딩 비밀번호(B105)·`eval()`(B307)을 직접 물어, mask_pii
  가드레일이 실제 값("admin1234")을 원문으로 노출하지 않는지까지 함께 검증한다.
- `Q22`: 오탐 방지용으로 추가한 "깨끗한" 파일(`string_utils.py`/`ProductService.java`)에
  문제가 있는지 물어, 실제로 없는 문제를 지어내지 않는지 검증한다 — `Q13`(존재하지
  않는 ID 질문)과 같은 취지지만 "존재하지 않는 ID"가 아니라 "findings가 없는 실제
  파일"을 묻는 다른 각도의 오탐 방지 테스트다.
- `Q23`: Vue3 minimist 취약점을 물어, npm audit 원본 등급(critical)이 시스템의
  `Finding.severity` 정규화 규칙(`_SEVERITY_MAP`, critical→high)을 거쳐 최종적으로
  `high`로 나오는 것이 정답이라는 점까지 note에 명시했다 — 아래 "부수 발견" 참고.

**부수 발견 — 문서화 오류 정정**: 이 검증 과정에서 CLAUDE.md 10-I절/SERVICE.md가
minimist 추가를 "새로운 **critical** 등급 취약점 확보"라고 서술한 것이 부정확함을
발견했다 — `agent.py`의 `_SEVERITY_MAP`이 `critical`을 항상 `high`로 정규화하므로,
`npm audit`의 원본 등급은 critical이어도 실제 `Finding.severity`(과 리포트에 노출되는
값)는 언제나 `high`다. 두 문서 모두 "npm audit 원본 등급은 critical이지만 정규화 후
리포트에는 high로 나온다"로 정정했다.

**실측 검증**: `.env`를 로드한 뒤 `CombinedAdapter`로 3개 언어 전체 `collect_findings()`
를 다시 실행해 총 19건(보안16/오류2/성능1)과 `LANGUAGE_STATUSES`(java/python/vue3 모두
`active`)를 재확인했고, `SEC-14`(minimist Prototype Pollution)의 `severity` 값이 실제로
`high`임을(원본 npm audit 등급이 critical이었음에도) 직접 확인해 `Q23`의 note에
반영했다.

**알려진 제약**: `Q21`~`Q23`은 아직 실제로 채점(대화형 Agent에 질문해 정답과 대조)된
적이 없다 — 다음 재평가(3일차 2번, 2차 평가 이후의 추가 재평가) 때 처음 채점된다.

### 10-K. `report.md` 가독성 개선 — 위치/문제/원인/수정 방법 통일 포맷 (2026-09-03, 사용자 요청)

**배경**: 3일차 3번(ragas) 진행 중 사용자가 `reports/report.md`를 다시 살펴보고 "일반
사용자가 알 수 없는 agent 내부데이터를 제거하고, 개발자/설계자/PL/PM이 어디서·무엇이·
왜·어떻게 고치는지 한눈에 알 수 있게 해 달라"고 요청했다. 구체적으로 두 가지를 콕
집었다 — ① "정적 도구가 못 잡는 이유" 같은 내부 근거 설명은 필요 없다, ② 가끔 걸려
있는 글자 수 제한(끊어서 자르는 방식)을 없애 달라.

**구현**(`src/report.py`):

- `_render_finding()`을 **위치/문제/원인/수정 방법** 4단으로 다시 썼다 — 보안/오류/성능
  구분 없이 항상 같은 구조다. "원인"/"수정 방법"은 새로 추가된 필드로, `_RULE_GUIDANCE`
  (bandit/eslint/pylint의 고정 규칙 카탈로그를 정확히 매칭)와 `_KEYWORD_GUIDANCE`
  (Java LLM 리뷰가 매번 살짝 다르게 짓는 규칙 이름·npm audit의 GHSA ID처럼 고정 카탈로그가
  없는 경우, `agent.py`의 `_RAG_REFERENCE_KEYWORDS`와 같은 이유로 규칙 이름에 포함된
  키워드로 근사 매칭)로 항상 완전한 문장을 만든다 — LLM 호출 없이 결정적으로 채워지므로
  `report.py`의 기존 "순수 템플릿, LLM 의존성 없음" 설계를 그대로 유지한다.
- `그룹 G-N`(파일 단위 그룹핑 ID) 표시를 뺐다 — 파이프라인 밖에서는 의미가 없는 순수
  내부 집계용 식별자다.
- RAG 체크리스트에서 검색해 온 "근거 문서" 원문 전체를 뺐다 — 이 안에 있던 "정적 도구가
  못 잡는 이유" 문단이 사용자가 지목한 바로 그 내용이었고, 벡터 검색 청크 경계(500자
  단위) 때문에 문장이 중간에 잘려 나오는 문제도 함께 있었다. `report.json`/`POST /query`
  의 `contexts`(API 스펙 고정 필드, ragas 등 기계 소비자용)는 원본을 그대로 유지한다 —
  사람이 읽는 `report.md`만 재구성했다.
- 카테고리 안에서 심각도(높음→중간→낮음) 순으로 정렬해, 급한 문제가 먼저 보이게 했다
  (부가 개선).
- **글자 수 제한 제거**: `report.py` 자체에는 원래도 글자 수로 자르는 부분이 없었다
  (재확인). 대신 `agent.py`의 `trace` 생성부 2곳에서 발견했다 — `_trace_from_agent_run()`
  의 도구 호출 결과 미리보기(`[:200]`)와 tool_use 병합 버그 폴백 경로의 에러 메시지
  (`[:150]`). 둘 다 잘라내지 않고 전체 내용을 그대로 남기도록 고쳤다 — `trace`는
  관찰용(패턴 #11)이라 잘린 내용보다 전체가 더 유용하다.

**UI도 함께 개선**(`src/static/index.html`, 요청 범위를 벗어나지만 같은 목적이라 함께
처리): `GET /` 화면이 `report_md`를 `<pre>` 안에 원문 그대로(`#`/`-`/`**` 마크다운 기호가
글자 그대로 보이는 상태로) 표시하고 있던 것을 발견해, `report.py`가 실제로 만드는
마크다운 부분집합(#/##/### 제목, `-` 목록, `**굵게**`, `` `코드` ``)만 지원하는 최소
렌더러(`renderReportMarkdown()`)를 추가해 실제 HTML로 렌더링하도록 고쳤다. 범용 마크다운
라이브러리를 새로 들여오지 않고 우리가 만드는 형식에만 맞춘 최소 구현이다 — HTML 특수
문자를 먼저 이스케이프한 뒤에만 서식 태그를 씌워, LLM/스캐너가 만든 텍스트 안에 `<`/`>`가
섞여 있어도 XSS로 이어지지 않는다(기존 `.textContent` 사용 원칙과 같은 이유, 정적/index.html
문서 참고).

**실측 검증**: 샘플 `Finding`(IDOR)으로 `render_markdown()`을 직접 호출해 위치/문제/원인/
수정 방법 4단 포맷이 보안/오류/성능 3개 카테고리 모두 동일하게 나오는 것을 확인했고,
`_render_finding()`이 만든 실제 마크다운을 Node.js로 `renderReportMarkdown()`에 그대로
넣어 `<h1>`/`<h2>`/`<h3>`/`<ul>`/`<li>`/`<strong>`/`<code>`로 정확히 변환되는 것까지
확인했다.

**알려진 제약**: `_RULE_GUIDANCE`/`_KEYWORD_GUIDANCE`에 없는 규칙(향후 새 도구·새 언어
어댑터가 추가되며 나올 규칙)은 "원인"에 `summary`를 그대로 재사용하고 "수정 방법"은
일반 안내 문구("코드 리뷰를 통해 구체적인 수정 방안을 확인하세요")로 대체한다 — 항상
4단 포맷을 유지하기 위한 안전한 기본값이지만, 새 어댑터를 추가할 때는 이 매핑에 대표
규칙을 함께 추가하는 것이 좋다.

### 10-L. LLM 역할을 검증/레포팅 둘로 분리 + 모델별 토큰 사용량 집계 (2026-09-03, 사용자 요청)

**(문서 순서 참고)** 이 결정은 시점상 10-K(`report.md` 가독성 개선)보다 **먼저** 있었다
— 3일차 2번(2차 평가, CLAUDE.md 위 "2번" 단락) 직후, 3일차 3번(ragas)에 들어가기
전에 사용자가 결정했다. 번호는 이 절이 문서에 추가된 순서를 따를 뿐, 실제 작업 순서와는
다르다.

**배경**: 2차 평가에서 판정자(`run_eval.py`의 `_judge`)가 시스템과 같은 약한 모델
(Haiku)이라 판정 자체를 신뢰할 수 없다는 것이 실측으로 드러났다(위 "2번" 단락 참고).
사용자가 "검증 역할은 Sonnet 4.5 이상의 고급 모델이 있어야 올바른 결과가 나올 것 같고,
레포팅은 Haiku를 써도 문제없을 것 같다"며 `.env`에 `REPORT_MODEL_ID`를 새로 추가하고
두 역할을 분리해 달라고 요청했다. 같은 요청에서 "이 미니PJT 범위에서는 3일차 3번의
예산 제한(설치·API 비용이 예산을 넘으면 2순위/최후 수단으로 전환)을 적용하지 말고,
대신 실행에 든 모델별 토큰 사용량을 레포트 상단에 기입해 달라"고도 결정했다.

**구현**(`src/tools.py`):

- 기존 `_default_llm()`(환경변수 `MODEL_ID`)를 그대로 두고, `_report_llm()`(환경변수
  `REPORT_MODEL_ID`, 미설정 시 `MODEL_ID`로 대체)을 새로 추가했다. 둘 다 내부 공통
  헬퍼 `_build_llm()`으로 병렬 도구 호출 우회 로직(1일차 4번 결정)을 공유한다.
- **역할 배정**: "새로운 판정을 직접 내리는" 역할(java_lite_adapter의 실제 소스 코드
  리뷰, `run_eval.py`의 판정자, ragas 내부 LLM)은 `_default_llm()`을 그대로 쓰고,
  "이미 검증된 결과를 사람이 읽기 쉽게 요약만 하는" 역할(`security_agent`/`error_agent`/
  `performance_agent`, 그리고 tool_use 병합 버그 폴백 경로)은 `_report_llm()`으로
  바꿨다(`src/agent.py`).
- **토큰 사용량 집계**: `_UsageTrackingCallback`(LangChain 콜백)을 LLM 생성 시점에 붙여,
  그 LLM이 이후 몇 번을 호출되든(ReAct 루프 포함) `usage_metadata`를 모델별로 자동
  누적한다 — 호출부마다 계측 코드를 넣을 필요가 없다(콜백이 Runnable 체인/그래프 실행
  전체에 전파되기 때문). `get_token_usage_summary()`/`reset_token_usage()`로 조회·
  초기화한다. `evaluation/run_eval.py`/`evaluation/run_ragas.py` 둘 다 이 값을
  `<리포트>.tokens.json`에 문항마다 즉시 저장해(Bedrock 할당량 초과로 여러 프로세스
  실행에 걸쳐 재개되는 게 이 프로젝트에서는 일상이라 — 2차 평가에서만 5차례) 프로세스가
  죽어도 누적치가 사라지지 않게 하고, 최종 리포트 상단에 모델별 호출 수·입력/출력/총
  토큰 표를 넣는다.
- **예산 제한 미적용**: 3일계획 3번의 "설치·API 비용이 예산을 넘으면 2순위/최후 수단
  (LLM-as-Judge 근사)으로 전환"하는 조건을 이 미니PJT 범위에서는 적용하지 않기로
  했다 — `evaluation/run_ragas.py`는 항상 조건 8의 1순위(실제 `ragas`)만 시도한다.

**(추가, 2026-09-03) 제품 리포트(`report.md`/`report.json`)에도 토큰 사용량을
빠뜨린 것을 사용자가 지적해 추가했다.** 위 구현은 처음엔 `evaluation/run_eval.py`/
`run_ragas.py`(평가 하네스)에만 연결돼 있었는데, 정작 실제 서비스 산출물인
`reports/report.md`(`POST /query`/`POST /scan`이 만드는 것)에는 빠져 있었다.
`src/report.py`의 `render_markdown()`/`save_report()`에 `token_usage` 파라미터를
추가해 리포트 최상단에 같은 형식의 "모델별 토큰 사용량" 표를 넣고, `report.json`에도
`token_usage` 필드를 추가했다. `src/api.py`의 `POST /query`와 `_run_scan_job()`
(`/scan` UI 경로) 양쪽에서 `reset_token_usage()`로 그 호출 한 번 분만 계산해
넘긴다 — API 스펙 고정 필드(`QueryResponse`의 `answer`/`contexts`/`trace`)는 건드리지
않고, 스펙 밖 산출물(`report.md`/`report.json`)에만 반영했다. 부수적으로
`src/static/index.html`의 `renderReportMarkdown()`에 표(`| ... |`) 렌더링을
추가했다 — 이 표가 새로 생기면서 처음엔 화면에 표 구분선(`|---|---|`)이 문단으로
그대로 보이는 버그가 났는데, 원인은 Windows에서 저장된 `report.md`가 CRLF(`\r\n`)라
JS의 줄 끝 정규식(`$`)이 남은 `\r` 때문에 매칭 안 되는 것이었다 — `split(/\r?\n/)`로
고쳤다.

**실측 검증**: `POST /query` 1회 호출 후 `get_token_usage_summary()`가 모델 ID 키
아래 `input_tokens`/`output_tokens`/`total_tokens`/`calls`를 정확히 채우는 것을
확인했고, 실제로 저장된 `reports/report.md`/`report.json` 양쪽에 그 값이 그대로
반영되는 것까지 확인했다. 이 시점엔 `MODEL_ID`/`REPORT_MODEL_ID`가 둘 다 같은
Haiku라 한 모델로만 잡혔다 — `MODEL_ID`를 Sonnet으로 바꾸면 두 모델이 각자 다른
행으로 나뉜다(아직 미검증, 사용자가 `MODEL_ID`를 Sonnet 계열로 바꾼 뒤 재확인 필요).
UI 표 렌더링은 실제 `report.md` 파일을 Node.js로 직접 읽어 `<table>`/`<th>`/`<td>`로
정확히 변환되는 것까지 확인했다.

**알려진 제약**: 이 절을 작성하는 시점에도 `MODEL_ID`가 아직 Sonnet 계열로 전환되지
않아(할당량 문제로 계속 Haiku 사용 중), "검증 역할에 고급 모델을 쓴다"는 결정의 실제
효과(판정 정확도 개선)는 아직 실측으로 확인되지 않았다 — 위 "3번(ragas 지표 산출)"
결과가 여전히 목표치에 못 미치는 이유 중 하나로 이미 언급됨.

### 10-M. `exceptLanguages`는 버전 무관, 리포트는 실제 버전 표시 (2026-09-03, 사용자 요청)

**배경**: 사용자가 "`exceptLanguages`에 대소문자 차이가 영향이 있을까요?"라고 물어
10-F절 이후 방치돼 있던 대소문자 버그(위 10-F절 말미 추가 기록)를 먼저 발견·수정한
직후, 이어서 "`exceptLanguages`에는 `java`/`vue`처럼 버전 없이 넣고, 실제 리포트에는
`java 1.8`/`vue2`처럼 버전을 특정해 달라 — `exceptLanguages`에 `java`라고 넣으면
1.8/17/21 등 버전과 무관하게 전부 막혀야 한다"고 요청했다.

**발견한 것**: `config.yaml`에 마침 `exceptLanguages: [vue]`가 설정돼 있었는데(대소문자
버그를 조사하며 사용자가 직접 넣어 둔 값으로 보임), 실제로는 Vue가 전혀 제외되지 않고
있었다 — 원인은 대소문자가 아니라 **버전 불일치**였다. 내부적으로 Vue는 계열 이름이
아니라 `"vue3"`로 등록돼 있어서(`_EXTENSION_LANGUAGE_MAP`/`_LANGUAGE_ADAPTER_REGISTRY`),
`exceptLanguages: [vue]`(정확히 "vue3"가 아님)와 문자열이 정확히 일치하지 않아 조용히
무시되고 있었다 — 이번에 사용자가 요청한 기능(버전 무관 매칭)이 없었기 때문에 애초에
생긴, 같은 뿌리의 문제였다.

**구현**(`src/agent.py`):

- **계열 이름과 표시 이름을 분리했다.** `_LANGUAGE_ADAPTER_REGISTRY`/
  `_EXTENSION_LANGUAGE_MAP`의 Vue 키를 `"vue3"`에서 버전 없는 `"vue"`로 바꿨다 —
  `exceptLanguages`/어댑터 레지스트리 매칭은 전부 이 계열 이름 기준이다.
- **`_detect_vue_version(root)`**: `package.json`의 `dependencies.vue`/
  `devDependencies.vue` 버전 문자열에서 메이저 버전 숫자를 뽑아 `"Vue3"` 같은 표시
  이름을 만든다. 버전을 알 수 없으면(파일 없음 등) `None` — 추측해서 지어내지 않는다.
- **`_detect_java_version(root)`**: `pom.xml`(Maven)의 `maven.compiler.release`/
  `maven.compiler.source`/`java.version` 프로퍼티, 또는 `build.gradle`(Gradle)의
  `sourceCompatibility`에서 Java 버전을 뽑는다. 이 미니PJT의 Java 라이트 리뷰는 원래
  실제 빌드 파일 없이 `.java` 소스만 직접 읽는 방식이라, 버전 감지용 신호가 아예
  없었다 — 실제로 읽을 신호를 만들어 주려고 `data/sample_java_app/pom.xml`을 새로
  추가하고 `maven.compiler.source`를 `1.8`로 선언했다(사용자가 예시로 든 값과 동일).
- **`_VERSION_DETECTORS`**: 언어 계열 → 버전 감지 함수 매핑(`_LANGUAGE_ADAPTER_REGISTRY`
  와 같은 설계 원칙, 조건 4 — 새 언어에 버전 표시를 추가하려면 감지 함수 하나만
  등록하면 됨). `_detect_display_name(family, root)`가 이 매핑을 찾아보고, 감지된
  버전이 있으면 그것을, 없으면 `family.capitalize()`를 반환한다.
- **`_classify_languages()`가 이제 (계열 이름, 상태, 표시 이름) 3튜플을 반환한다**
  (기존 2튜플에서 확장) — `LANGUAGE_STATUSES`의 타입이 바뀌었으므로 이를 소비하는
  모든 곳을 함께 고쳤다: `_resolve_adapters_from_config()`/`_ACTIVE_LANGUAGES_LABEL`
  (`src/agent.py`), `_render_language_line()`/`save_report()`의 JSON `languages`
  배열(`src/report.py`, `display` 필드 추가), `/scan`의 `languages` 응답
  (`src/api.py`, `display` 필드 추가), UI의 언어 태그 렌더링(`src/static/index.html`,
  `l.name` → `l.display`).

**부수 정리(2026-09-03, 이후 사용자가 다시 확인)**: `data/hello.c`/`data/Hello.cs`
(예전 "점검불가" 분류 실측 검증 때 만든 더미 테스트 파일)가 `LANGUAGE_STATUSES`에
계속 `unsupported`로 잡히고 있던 것을 이 작업 중 발견해 처음엔 삭제했으나, 사용자가
"점검불가 테스트를 위한 것"이라고 확인해 **다시 만들어 뒀다** — 즉 이 둘은 지금도
`data/`에 남아 있고, 의도적으로 "점검불가" 분류를 계속 실측 검증하기 위한 용도다(삭제
대상 아님). `config.yaml`의 `exceptLanguages`도 잠시 `[vue]`(대소문자 버그 조사용
테스트 값 — 사용자가 "vue였던 건 테스트로 넣었던 것"이라고 확인함)로 바뀌었다가 다시
기본값 `[]`로 돌아왔다 — `[vue]`인 채로 두면 실제로 Vue가 제외돼 지금까지 문서 전체에
기록된 19건 기준선(2번/3번/10-I~L절)이 조용히 달라지므로, 이 값이 항상 `[]`인지는
새로 실행하기 전에 `config.yaml`을 직접 확인하는 게 안전하다.

**실측 검증**: `_classify_languages({'java'}, {'Java'}, PROJECT_SOURCE_ROOT)`류 직접
호출 대신, 실제 프로젝트 데이터로 `LANGUAGE_STATUSES`를 계산해 `[('java', 'active',
'Java 1.8'), ('python', 'active', 'Python'), ('vue', 'active', 'Vue3')]`을 확인했다
— `pom.xml`에서 실제로 "Java 1.8"을, `package.json`의 `vue: "^3.4.0"`에서 실제로
"Vue3"를 뽑아낸 것이다. `exceptLanguages: [vue]`로 바꿔 재확인하니 `vue`만 정확히
`excepted`로 분류되고(버전 표시는 여전히 "Vue3" 그대로 유지됨 — 제외 여부와 표시
이름은 서로 독립적인 값이다), `java`/`python`은 그대로 `active`였다. `POST /query`를
실제로 호출해 `report.md` 상단에 "감지된 언어: Java 1.8, Python, Vue3"가 정확히
나오는 것까지 확인했다. `_discover_mybatis_xml_files()`가 새로 추가한 `pom.xml`을
`<mapper` 태그가 없어 여전히 정확히 걸러내는 것도 재확인했다(MyBatis 매퍼 오검출
없음).

**알려진 제약**: Python은 버전 감지 함수가 없어(이 프로젝트의 Python 더미 소스에
`pyproject.toml`/`.python-version`처럼 버전을 선언하는 파일이 없음) 항상 "Python"
(버전 없이)으로만 표시된다 — 실제 신호가 생기면(예: `pyproject.toml`의
`requires-python`) `_VERSION_DETECTORS`에 감지 함수를 추가하면 된다.
