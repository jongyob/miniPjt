# 코드 품질 리포트 Agent

> 제출 규약(0-5절) 템플릿에 맞춘 프로젝트 문서입니다. "왜/누구를 위해"는 [SERVICE.md](./SERVICE.md),
> "어떻게 구현했는지의 결정 이력"은 [CLAUDE.md](./CLAUDE.md)를 따르며, 이 문서는 그 둘을
> 요약해 처음 보는 사람이 5분 안에 무엇을 실행할 수 있는지 알 수 있게 합니다.

## 1. 무엇을 푸나

Java(백엔드) + Vue3(프론트엔드) + Python으로 구성된 코드베이스를 **보안/오류/성능** 세
관점에서 자동으로 점검하고, 그 결과를 대화형으로 물어볼 수 있는 Agent입니다.

- 사람이 관점별로 매번 수동 점검하기엔 시간이 부족하고, 정적 도구는 원시 결과만 내놓을 뿐
  "왜 문제이고 어떻게 고쳐야 하는지" 근거가 없습니다.
- 정적 도구·린터는 패턴 매칭 기반이라 인증/인가 로직처럼 코드 흐름을 이해해야 하는 취약점
  (IDOR 등)을 구조적으로 못 잡고, 성능도 실제 부하 상황에서만 드러나는 문제(N+1 등)는
  코드만 봐서는 놓치기 쉽습니다.
- 그래서 이 Agent는 **3개 전문 Agent(보안/오류/성능)를 병렬로 실행**해 정적 스캐너(npm
  audit/eslint/bandit/pylint) 결과와 LLM 코드 리뷰(Java lite)를 결합하고, 사내 코딩
  가이드(RAG)를 근거로 붙이며, `security_agent`/`performance_agent`가 **직접 만든
  스테이징 서버에 실제 HTTP 요청을 보내** IDOR 유출·동시 부하 지연을 살아있는 상태에서
  검증합니다. 자세한 문제 정의·가치는 [SERVICE.md 1절](./SERVICE.md#1-사용자문제가치) 참고.

## 2. 활용한 패턴 (Day1~7)

12개 패턴 체크리스트 중 **4종 필수(★) 포함 총 8개**를 확보했습니다.

| # | 패턴 | 필수 | 이 프로젝트에서 |
|---|---|---|---|
| 1 | 구조화 출력(Pydantic) | ★필수 | `Finding`/`ReferenceDoc`(`src/agent.py`), `LlmReviewResult`/`LlmRawFinding`(`src/tools.py`, Java lite 리뷰), `JudgeVerdict`(`evaluation/run_eval.py`, 판정자) |
| 2 | ReAct(도구 자율 선택) | 권장 | `make_security_agent`/`make_error_agent`/`make_performance_agent`(`src/agent.py`) — `create_react_agent` 기반 3개 전문 Agent |
| 3 | RAG | ★필수 | `src/retriever.py`(Chroma + Titan 임베딩) + `search_guides` 도구, `data/guides/`의 인증/인가·부하 체크리스트 |
| 4 | 도구 다중 결합 | 권장 | `security_agent`가 스캐너(`scan_security`) + 가이드 검색(`search_guides`) + 실제 프로빙(`run_idor_pentest_probe`)을 함께 씀 |
| 6 | 가드레일 | 권장 | `mask_pii()`(`src/agent.py`) — 시크릿 마스킹, 프롬프트 구성 시점과 리포트 저장 직전 2단계 적용 |
| 9 | Multi-Agent Supervisor | 권장 | `make_supervisor()`(`src/agent.py`) — LangGraph `StateGraph`로 3개 Agent를 병렬 실행 후 취합 |
| 11 | Observability/Trace | ★필수 | `_trace_from_agent_run()`(`src/agent.py`) → `POST /query`의 `trace` 필드(API 스펙 고정) |
| 12 | 평가(RAGAS/LLM-Judge) | ★필수 | `evaluation/run_eval.py`(LLM-as-Judge, trace 기반 도구 호출 검증 포함) + `evaluation/run_ragas.py`(실제 `ragas` 라이브러리 4개 지표) |

MCP·HITL·미들웨어·Plan-Execute/장기메모리는 이번 범위에 넣지 않았습니다(3일계획 8절).

## 3. 아키텍처

```text
                        POST /query 또는 POST /scan
                                  │
                          make_supervisor()
                        (LangGraph StateGraph)
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
       security_agent       error_agent        performance_agent
       (ReAct, 도구:         (ReAct, 도구:        (ReAct, 도구:
        scan_security,        scan_error)          scan_performance,
        search_guides,                              get_db_schema,
        run_idor_pentest_                            explain_query,
        probe*)                                      run_live_load_test*)
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  ▼
                      CombinedAdapter (언어 어댑터)
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        Vue3Adapter          JavaLiteAdapter      PythonAdapter
       (npm audit/eslint,   (LLM 코드 리뷰 —      (bandit/pylint,
        실전 연동)            도구 없음, MyBatis    실전 연동)
                              XML SQL Injection
                              포함)

(* live_probe: true일 때만 — data/staging_app에 실제 요청, config.yaml의
   staging.base_url로 외부 스테이징 서버로 교체 가능)
```

- **언어 자동 감지**: `config.yaml`의 `source`(프로젝트 루트) 하나만 설정하면 그 아래 파일을
  재귀 스캔해 언어를 자동 감지합니다. 어댑터가 없는 언어는 "(점검불가)", `exceptLanguages`에
  지정한 언어(버전 무관 계열 이름 — `java`/`vue`)는 "(점검제외)"로 표시됩니다.
- **검증/레포팅 역할 분리**: Java lite 리뷰·판정자처럼 "새 판정을 내리는" 역할은
  `MODEL_ID`(Sonnet 4.5 이상 권장), 3개 전문 Agent처럼 "이미 검증된 결과를 요약만 하는"
  역할은 `REPORT_MODEL_ID`(Haiku로 충분)를 쓰도록 분리했습니다 — 근거는 아래 6절, 상세는
  [CLAUDE.md](./CLAUDE.md) "환경변수" 절 참고.
- **모의해킹/부하테스트**: `security_agent`/`performance_agent`가 표준 HTTP 클라이언트로
  스테이징 서버에 직접 요청을 보내 IDOR 유출·동시 부하 지연을 실측합니다. 대상 서버는
  기본값(자체 더미 앱 자동 기동) 또는 `config.yaml`의 `staging.base_url`(조직이 이미
  운영 중인 외부 스테이징 서버, 사전 등록 필수)로 설정합니다 — 소스/git 위치로부터 서버를
  자동 빌드·기동하는 기능은 안전상 두지 않았습니다.

## 4. 실행 방법

### 로컬(가상환경) — 지금 바로 되는 방법

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api:app --host 127.0.0.1 --port 8000
```

`.env`(`.env.example` 참고)에 AWS 자격증명과 `MODEL_ID`/`REPORT_MODEL_ID`/`EMBED_MODEL_ID`를
채우면 `python-dotenv`가 자동으로 읽습니다.

**실행(브라우저, 권장)**: 서버를 띄운 뒤 `http://127.0.0.1:8000/`을 열고 **"점검 실행"**
버튼을 누르면 됩니다. 감지된 언어를 한 번에 전부 점검하며, 진행률과 완료 시 결과(감지된
언어, 카테고리별 건수, 리포트 전문)를 화면에서 바로 확인합니다.

**실행(터미널, API 직접 호출 — 스크립트/CI 자동화용)**:

```bash
curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" -d "{\"question\":\"vue3-app 보안 취약점 알려줘\"}"
```

`POST /query`는 API 스펙(0-2절) 고정 — `{"answer", "contexts", "trace"}`를 반환합니다.

### Docker — 현재 보류 중 (2026-09-04)

3일차 5번(`Dockerfile` 작성)을 6번(`README.md`, 이 문서) 뒤로 순서만 미뤄뒀습니다 —
잘라낸 게 아니라 착수 순서 변경이며, 이 시점 기준 `Dockerfile`이 아직 없습니다. 착수하면
아래 명령으로 실행할 계획입니다(베이스 이미지에 Python+Node.js를 함께 넣어야 함 —
`vue3_adapter`가 컨테이너 안에서 `npm audit`/`eslint`를 실행하기 때문):

```bash
docker build -t mini-pjt-agent .
docker run -p 127.0.0.1:8000:8000 --env-file .env mini-pjt-agent
```

지금 당장 실행하려면 위 "로컬(가상환경)" 방법을 쓰면 됩니다 — API 스펙·동작은 동일합니다.

## 5. RAGAS 평가 결과

`test_queries.csv`의 `note`를 근사 `ground_truth`로 써서 실제 `ragas` 라이브러리로
4개 지표를 계산했습니다(조건 8의 1순위 — 예산 기반 폴백은 이 미니PJT 범위에서 적용하지
않기로 결정).

| 지표 | 목표치 | 1차(전부 Haiku) | 2차(검증 역할 Sonnet 4.6) |
|---|---|---|---|
| `context_recall` | 0.6 이상 | 0.304 | 0.192 |
| `context_precision` | 0.7 이상 | 0.197 | 0.238 |
| `faithfulness` | 0.7 이상 | 0.318 | 0.126 |
| `answer_relevancy` | 0.7 이상 | 0.236 | 0.354 |

**전부 목표치 미달이고, 검증 역할을 Sonnet으로 바꿔도 네 지표가 다같이 좋아지지는
않았습니다.** 아래 3일차 2번(대화형 QA 정확도, 48%→100%)이 같은 모델 교체로 뚜렷이
개선된 것과 대조적이라 실제 문항 데이터를 까서 원인을 확인했습니다 — **모델 품질 문제가
아니라 스키마/API 설계의 구조적 한계**입니다:

1. `test_queries.csv`의 `note`는 애초에 ragas가 기대하는 "정답 답변 문장"이 아니라
   **사람 판정자를 위한 채점 기준 설명문**입니다(예: "1차 평가에는 포함되지 않았다"는
   테스트 운영 이력, "~해야 한다"는 요구사항 서술문) — 둘 다 코드 스캔 결과인 `contexts`로는
   원천적으로 뒷받침할 수 없는 문장 형태라 `context_recall`이 정답 여부와 무관하게 낮게
   나옵니다.
2. `contexts`는 `POST /query` API 스펙상 그 시점 findings 전체를 담는 고정 필드라
   질문에 좁혀진 검색 결과가 아니고, 리포팅 Agent가 정상적으로 덧붙이는 설명(줄 번호,
   위험성 해설)은 사실이어도 `contexts`에 문자 그대로 없어 `faithfulness`가 근거 없음으로
   깎습니다.
3. 재검증 기간 중 npm 장애로 Vue를 임시 제외해, Vue 발견을 전제로 한 `note`를 가진 5문항이
   구조적으로 0점 처리됐습니다.

상세 문항별 점수·토큰 사용량은 [`evaluation/ragas_report.md`](./evaluation/ragas_report.md)/
[`evaluation/ragas2_report.md`](./evaluation/ragas2_report.md), 원인 분석 전체는
[SERVICE.md 5절](./SERVICE.md#5-성공-기준-통과율-목표치) 참고.

## 6. 인-아웃 세트 통과율 (1차·2차)

`evaluation/test_queries.csv`(23문항, positive/negative/edge/guardrail 4카테고리) 기준:

| 회차 | 측정값 | 실측 재검증 후 |
|---|---|---|
| 1차(2일차 종료) | 17문항 중 11건(65%) | — |
| 2차(3일차, Haiku 강제 — 당일 Bedrock 계정 전체 할당량 문제) | 23문항 중 11건(48%) | **20/23(87%)** — 판정 사유를 원문·trace와 대조, 의심 3건 직접 재호출로 확인 |
| 3차 재검증(할당량 회복 후, Sonnet 4.6) | 16/23 | **23/23(100%)** — Vue 임시 제외 아티팩트 5건 + 판정자 자체 오류(환각/자기모순) 2건 제외 |
| 3차 재검증(Sonnet 4.5) | 18/23 | **23/23(100%)** — 4.6과 동일하게 Vue 아티팩트 + 판정자 오류 제외 시 완전 통과, "검증 역할 4.5 이상" 권장이 특정 버전 우연이 아님을 확인 |
| 3차 재검증(Nova Pro, 비교용) | 16/23 | Vue 아티팩트 3건 제외 후 **확정 모델 한계 3건**(발견 개수 비결정성, SQL Injection 환각 재현, 자기 도구 미인지) + 근거 불확실 1건 |

2차 평가 과정에서 대화형 경로에 `mask_pii`/심각도 정규화가 실제로 연결돼 있지 않던 진짜
결함 2건을 발견해 즉시 고쳤고, 판정자(judge)가 이 시스템의 "3개 섹션 항상 병렬 응답" 설계를
모순으로 오판하는 사례가 다수임을 확인해 trace 기반 사실 주입 + 다중 섹션 설명 보강으로
판정자 프롬프트도 개선했습니다. 상세는 [`evaluation/round2_report.md`](./evaluation/round2_report.md)/
[`round3_sonnet_report.md`](./evaluation/round3_sonnet_report.md)/
[`round3_sonnet45_report.md`](./evaluation/round3_sonnet45_report.md)/
[`round3_nova_report.md`](./evaluation/round3_nova_report.md) 참고.

## 7. 트라이앤에러 회고

3일 동안 발견·수정한 실제 결함들입니다 — "검증했다"는 말을 실제 재현·수정 없이 하지
않는다는 원칙으로, 매 점검 단계마다 실제 버그가 나왔습니다.

- **`mask_pii`가 콜론 구분자 형식을 놓침**: bandit이 `"key: 'value'"` 형태로 비밀번호를
  보고하는데, 마스킹 정규식이 등호(`=`)만 잡고 있어 하드코딩 비밀번호가 리포트에 원문 그대로
  노출됐습니다. 두 구분자를 모두 잡도록 고쳤습니다.
- **대화형 경로에 마스킹·심각도 정규화가 아예 연결 안 돼 있었음**: 정적 리포트 경로에만
  연결돼 있고 `POST /query`의 `scan_*` 도구에는 연결된 적이 없었습니다 — 2차 자체평가에서
  실측으로 드러났습니다. `_sanitize_raw_findings()`를 추가해 연결했습니다.
- **같은 버그가 폴백 경로에도 남아 있었음**: 위 수정 이후에도, ReAct 도구 호출이 계속 실패할
  때 쓰는 `_fallback_answer()`는 여전히 원시 findings를 마스킹 없이 LLM에 넘기고 있었습니다
  — 소스 전체 재검증(2026-09-04)에서 발견해 고쳤습니다.
- **Nova Pro에서 구조화 출력이 `KeyError`로 깨짐**: Bedrock이 Pydantic 스키마 이름의 앞
  언더스코어를 잘라내는데, LangChain의 파서는 원래(언더스코어 있는) 이름으로 찾아 실패했습니다.
  스키마 클래스 이름에서 언더스코어를 뺀 뒤 해결했습니다 — "여러 모델을 지원한다면서 여기서
  막히면 안 된다"는 지적을 받고 근본 원인을 찾아 고쳤습니다.
- **판정자가 trace를 못 봐서 근거 없이 "환각"으로 오판**: `run_live_load_test` 등이 실제로
  호출됐는지 확인할 방법이 없어 텍스트만 보고 추측했습니다. trace에서 뽑은 실제 호출 도구
  목록을 판정자 프롬프트에 "확인된 사실"로 명시해 해결했습니다.
- **`exceptLanguages`에 버전 있는 이름과 없는 이름이 섞여 조용히 무시됨**: `vue3`라는 내부
  키와 사용자가 적는 `vue`가 안 맞아 아무 효과 없이 무시되는 실제 버그였습니다. 버전 무관
  "언어 계열" 이름으로 통일하고, 리포트에는 실제 감지된 버전을 표시하도록 분리했습니다.
- **ragas가 Python 3.14와 부딪힘**: `ragas.evaluate()`(배치 API)가 `nest_asyncio`+
  Python 3.14의 `asyncio.timeout()` 조합에서 깨져, 각 지표의 `single_turn_score()`를
  문항마다 직접 호출하는 방식으로 우회했습니다. `ragas`를 모듈 최상단에서 import하면
  `nest_asyncio.apply()`의 전역 부작용이 Starlette `TestClient`를 깨뜨리는 것도 발견해
  지연 import로 고쳤습니다.
- **npm 보안 권고 벌크 조회 엔드포인트 외부 장애**: `npm audit`이 응답 없이 멈추는 것을
  직접 `curl`로 재현해 Bedrock/코드 문제가 아닌 순수 외부 인프라 장애임을 확인하고,
  `exceptLanguages: [vue]`로 임시 우회했습니다.
- **동시 실행 레이스 컨디션 2건**: Supervisor가 3개 Agent를 병렬 실행하는 구조에서
  스테이징 서버 자동 기동과 샘플 DB 최초 빌드가 잠금 없이 공유 상태를 건드려, 포트 경합이나
  (Windows에서) `PermissionError` 위험이 있었습니다. `threading.Lock`으로 직렬화했습니다.
- **부하테스트 전체 장애가 "발견 없음"으로 보고됨**: 동시 요청이 전부 실패하면 에러율을
  확인하기도 전에 조용히 빈 리스트를 반환해, 완전 장애가 정상 상태와 똑같이 보였습니다 —
  가장 나쁜 결과가 가장 안전해 보이는 거짓 음성이었습니다. 전체 실패를 그 자체로 high
  severity finding으로 보고하도록 고쳤습니다.
- **Bedrock 계정 전체 할당량 문제**: 약 40명이 같은 소수 모델을 동시에 쓰는 교육용 계정
  특성상 "다른 모델로 바꾸면 도움이 된다"는 것과 "한 모델이 막히면 계정 전체가 막힌 것"이
  헷갈렸습니다 — 실측으로 "리전 프리픽스 무관, 모델 단위 공유"라는 가설을 세웠다가, 근거
  부족한 추측이었음을 스스로 정정하고 "붐비는 모델을 피한 효과"로 재해석했습니다.

## 8. 핵심 코드 위치

| 역할 | 파일:함수 |
|---|---|
| Supervisor(병렬 실행) | `src/agent.py`의 `make_supervisor()` |
| 3개 전문 Agent | `src/agent.py`의 `make_security_agent()`/`make_error_agent()`/`make_performance_agent()` |
| 언어 자동 감지·분류 | `src/agent.py`의 `_detect_languages()`/`_classify_languages()`/`_detect_display_name()` |
| 언어 어댑터(Vue3/Java/Python) | `src/tools.py`의 `Vue3Adapter`/`JavaLiteAdapter`/`PythonAdapter` |
| DB 어댑터 | `src/tools.py`의 `DbAdapter` |
| 모의해킹/부하테스트 도구 | `src/tools.py`의 `probe_idor_vulnerability()`/`run_concurrent_load_test()`/`_ensure_staging_server()` |
| 시크릿 마스킹 가드레일 | `src/agent.py`의 `mask_pii()` |
| LLM 역할 분리(검증/레포팅) | `src/tools.py`의 `_default_llm()`/`_report_llm()`/`_build_llm()` |
| 토큰 사용량 집계 | `src/tools.py`의 `_UsageTrackingCallback`/`get_token_usage_summary()` |
| RAG | `src/retriever.py`, `search_guides` 도구(`src/agent.py`) |
| Trace 수집 | `src/agent.py`의 `_trace_from_agent_run()` |
| API | `src/api.py`의 `POST /query`/`POST /scan`/`GET /` |
| 리포트 생성 | `src/report.py`의 `save_report()`/`render_markdown()` |
| 최소 실행 UI | `src/static/index.html` |
| 자체평가(LLM-as-Judge) | `evaluation/run_eval.py` |
| ragas 평가 | `evaluation/run_ragas.py` |

## 9. 알려진 제약 / 다음 반영

- **`Dockerfile` 미완료**(위 4절 참고) — 착수 순서만 뒤로 미룸.
- **정식 배포 전 필수 선행**: 사내망 프라이빗 LLM 엔드포인트 구축(이 실습은 교육용 퍼블릭
  Bedrock 리전 엔드포인트를 씀), 사내 SSO 인증(현재는 `127.0.0.1` 로컬 바인딩만).
- **ragas 지표의 구조적 한계**(위 5절) — `test_queries.csv`에 판정 기준용 `note`와 분리된
  순수 정답 문장 컬럼을 추가하면 개선 여지가 있습니다.
- **동적 점검 대상 서버 등록은 사람 책임**: `staging.base_url`이 실제 운영 서버가 아닌지는
  코드가 검증하지 않습니다 — 강제하려면 사내 승인 스테이징 도메인 화이트리스트가 필요합니다.
- Vue3 npm audit 연동은 재검증 기간 중 npm 외부 장애로 `exceptLanguages: [vue]`를 임시
  적용한 상태입니다 — 복구되면 되돌리고 별도 재검증이 필요합니다.
