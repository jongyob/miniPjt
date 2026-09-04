"""POST /query 엔드포인트.

1일차 1번: 스켈레톤만 만든다 — question을 받아 더미 응답을 반환한다. 2일차 5번: Supervisor
(`src/agent.py`)와 리포트 저장(`src/report.py`)을 실제로 연결한다.

**(신규, 2026-09-03 — 사용자 요청)** 터미널에서 `curl`로 `POST /query`를 직접 호출하는 게
번거롭다는 요청으로, 브라우저에서 버튼 하나로 전체 점검을 실행하고 진행률·완료 여부를 볼 수
있는 최소 UI(`GET /`)와 그 뒤에서 쓰는 `POST /scan`/`GET /scan/{job_id}`를 추가했다. 0-2절
"API 스펙(고정)"이 요구하는 `POST /query`는 그대로 유지하고(요청/응답 모양 변경 없음), 이
UI 전용 엔드포인트들은 0-1절 목록 밖의 순수 추가다(`config.yaml`/`reports/`와 같은 선례).
"""

import time
import uuid
from pathlib import Path
from threading import Thread
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.agent import LANGUAGE_STATUSES, make_supervisor
from src.report import save_report
from src.tools import get_token_usage_summary, reset_token_usage

load_dotenv()

app = FastAPI()

# 여러 요청에 걸쳐 재사용 — 어댑터 캐싱(1일차 2번)과 같은 이유로 매 요청마다 다시 만들지
# 않는다. `agent.py`/`report.py` 둘 다 서로를 몰라야 순환 임포트가 안 생기므로(2일차 4번
# 결정), 이 둘을 잇는 조립은 두 모듈을 모두 아는 이 파일에서 한다.
_supervisor = make_supervisor()
_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
_STATIC_DIR = Path(__file__).resolve().parent / "static"


class QueryRequest(BaseModel):
    """POST /query 요청 바디."""

    question: str


class ContextItem(BaseModel):
    """근거 조각 — Finding과 RAG 문서 조각을 같은 모양으로 담는다(API 스펙 고정)."""

    doc_id: str
    text: str


class TraceEvent(BaseModel):
    """실행 기록 한 건."""

    step: str
    input: Any = None
    output: Any = None


class QueryResponse(BaseModel):
    """POST /query 응답 바디 — answer/contexts/trace 세 키(API 스펙 고정)."""

    answer: str
    contexts: list[ContextItem]
    trace: list[TraceEvent]


def _findings_to_contexts(findings: list) -> list[ContextItem]:
    contexts: list[ContextItem] = []
    for finding in findings:
        text = f"{finding.summary}\n{finding.detail}" if finding.detail != finding.summary else finding.summary
        contexts.append(ContextItem(doc_id=finding.id, text=text))
        if finding.reference is not None:
            contexts.append(
                ContextItem(doc_id=finding.reference.doc_id, text=finding.reference.text)
            )
    return contexts


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """질문을 Supervisor에 전달하고, 그 결과로 리포트를 갱신한 뒤 API 스펙대로 응답을 조립한다.

    `contexts`는 Finding과 RAG 문서 근거를 같은 `{doc_id, text}` 모양으로 통일한다(CLAUDE.md
    2절 결정) — Finding 항목은 `doc_id`에 Finding ID, `text`에 `summary`+`detail` 요약을
    넣고, Finding에 `reference`(RAG 근거)가 있으면 그 문서도 별도 항목으로 추가한다.

    **(결정, 2026-09-03 — 사용자 요청)** 이 호출 한 번에 실제로 든 모델별 토큰 사용량을
    `reset_token_usage()`/`get_token_usage_summary()`로 직접 계산해 `save_report()`에
    넘긴다 — `report.md`/`report.json`(0-1/0-2절 API 스펙 밖의 추가 산출물) 상단에만
    반영되고, 이 함수가 반환하는 `QueryResponse`(스펙 고정: `answer`/`contexts`/`trace`)
    자체는 건드리지 않는다. **알려진 제약**: 토큰 집계가 프로세스 전역 상태라, 동시에
    여러 요청이 들어오면 서로 섞일 수 있다 — 로컬 1인 사용 규모(조건 9)라 실제로 부딪힐
    상황이 아니다.
    """
    reset_token_usage()
    result = _supervisor.invoke({"question": request.question})
    findings = result["findings"]
    token_usage = get_token_usage_summary()

    save_report(
        findings,
        reports_dir=_REPORTS_DIR,
        language_statuses=LANGUAGE_STATUSES,
        token_usage=token_usage,
    )

    trace = [TraceEvent(**event) for event in result.get("trace", [])]
    return QueryResponse(
        answer=result["answer"], contexts=_findings_to_contexts(findings), trace=trace
    )


# ---------------------------------------------------------------------------
# 최소 UI (신규, 2026-09-03 — 사용자 요청: 터미널 없이 버튼 하나로 실행 + 진행률/완료 확인)
# ---------------------------------------------------------------------------

# Supervisor는 질문 내용과 무관하게 항상 3개 전문 Agent를 전부 병렬 실행하므로(3-6절
# "선택적 실행"은 로드맵), "실행" 버튼은 그 특성을 그대로 쓰는 고정 질문 하나만 보낸다 —
# 언어별로 버튼을 나눌 필요가 없다(사용자 요청: "언어별 실행도 아닌데").
_SCAN_QUESTION = "이 프로젝트에서 감지된 모든 언어의 보안/오류/성능 이슈를 전부 점검해서 리포트를 만들어줘"

# Supervisor 그래프의 노드 이름 그대로(`agent.py`의 `add_node` 호출과 맞춤) — 진행률 계산의
# 분모(총 5단계)로 쓴다. `.stream(stream_mode="updates")`가 노드가 끝날 때마다 그 이름으로
# 이벤트를 주므로(실측 확인), 폴링하는 프런트엔드가 "N/5단계 완료"를 그릴 수 있다.
_SCAN_STEPS = ["call_security", "call_error", "call_performance", "build_findings", "aggregate"]

_jobs: dict[str, dict[str, Any]] = {}


def _run_scan_job(job_id: str) -> None:
    """백그라운드 스레드에서 Supervisor를 스트리밍 실행하며 `_jobs[job_id]`를 갱신한다.

    Celery/Redis 같은 별도 작업 큐 없이 `threading.Thread` + 메모리 dict만 쓴다 — 로컬
    1인 사용 미니PJT 규모에서는 충분하고, 새 의존성을 추가하지 않아도 된다.
    """
    job = _jobs[job_id]
    try:
        reset_token_usage()
        collected: dict[str, Any] = {}
        for update in _supervisor.stream({"question": _SCAN_QUESTION}, stream_mode="updates"):
            for node_name, node_output in update.items():
                if node_output:
                    collected.update(node_output)
                job["completed_steps"].append(node_name)

        findings = collected.get("findings", [])
        timestamped_path = save_report(
            findings,
            reports_dir=_REPORTS_DIR,
            language_statuses=LANGUAGE_STATUSES,
            token_usage=get_token_usage_summary(),
        )

        counts = {"security": 0, "error": 0, "performance": 0}
        for finding in findings:
            counts[finding.category] += 1

        job["status"] = "done"
        job["answer"] = collected.get("answer", "")
        job["counts"] = counts
        job["total"] = len(findings)
        job["report_md"] = timestamped_path.read_text(encoding="utf-8")
        job["report_file"] = timestamped_path.name
    except Exception as exc:  # noqa: BLE001 - 백그라운드 스레드라 여기서 잡아 상태에 남겨야 함
        job["status"] = "error"
        job["error"] = str(exc)
    finally:
        job["finished_at"] = time.monotonic()


@app.post("/scan")
def start_scan() -> dict[str, str]:
    """전체 점검을 백그라운드로 시작하고 즉시 `job_id`를 반환한다(UI 전용, API 스펙 밖)."""
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {
        "status": "running",
        "completed_steps": [],
        "started_at": time.monotonic(),
    }
    Thread(target=_run_scan_job, args=(job_id,), daemon=True).start()
    return {"job_id": job_id}


@app.get("/scan/{job_id}")
def get_scan_status(job_id: str) -> dict[str, Any]:
    """`job_id`의 진행 상황 또는 최종 결과를 반환한다(UI 전용, API 스펙 밖)."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="알 수 없는 job_id입니다.")

    elapsed = (job.get("finished_at", time.monotonic())) - job["started_at"]
    response: dict[str, Any] = {
        "status": job["status"],
        "completed_steps": job["completed_steps"],
        "total_steps": len(_SCAN_STEPS),
        "elapsed_seconds": round(elapsed, 1),
    }
    if job["status"] == "done":
        response.update(
            {
                "answer": job["answer"],
                "counts": job["counts"],
                "total": job["total"],
                "report_md": job["report_md"],
                "report_file": job["report_file"],
                "languages": [
                    {"name": name, "status": status, "display": display}
                    for name, status, display in LANGUAGE_STATUSES
                ],
            }
        )
    elif job["status"] == "error":
        response["error"] = job["error"]
    return response


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """실행 버튼 + 진행률/결과 화면(UI 전용, API 스펙 밖) — `static/index.html`을 그대로 서빙."""
    return (_STATIC_DIR / "index.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn

    # 로컬 실행 기본값은 127.0.0.1(외부 노출 금지, 조건 9). Docker에서는 Dockerfile CMD가
    # --host 0.0.0.0을 명시로 실행하므로 이 기본값과 무관하다(CLAUDE.md "컨테이너 안에서
    # 127.0.0.1 바인딩의 함정" 참고).
    uvicorn.run(app, host="127.0.0.1", port=8000)
