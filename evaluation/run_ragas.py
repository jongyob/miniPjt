"""3일차 3번: `test_queries.csv` 기반 실제 `ragas` 지표 산출.

조건 8(평가 지표)의 1순위 — `test_queries.csv`의 `note`를 `ground_truth`(ragas의
`reference`)로 재사용해 `context_recall`까지 포함한 4개 지표(`context_recall`/
`context_precision`/`faithfulness`/`answer_relevancy`)를 실제 `ragas` 라이브러리로
계산한다. **(결정, 2026-09-03, 사용자 요청)** 이 미니PJT 범위에서는 설치·API 비용이
예산을 넘기면 2순위/최후 수단(LLM-as-Judge 근사)으로 내려가는 조건을 적용하지 않는다 —
항상 1순위(이 스크립트)를 시도한다.

실행: `python -m evaluation.run_ragas [리포트 파일명]`(프로젝트 루트에서 실행해야 `src`
패키지를 찾는다). 리포트 파일명을 생략하면 `ragas_report.md`, 주면 그 이름으로 저장한다
(`run_eval.py`가 라운드 이름을 인자로 받는 것과 같은 이유 — 재검증마다 기존 결과를
덮어쓰지 않고 별도 파일로 남긴다).

**역할 분리(2026-09-03 결정)**: `POST /query` 호출(질문에 답하는 3개 전문 Agent)은
`_report_llm()`(`REPORT_MODEL_ID`)을 쓰고, ragas 지표 계산 자체(4개 지표를 판정하는
"검증" 역할)는 `_default_llm()`(`MODEL_ID`, Sonnet 4.5 이상 권장)을 쓴다 — 두 역할이
같은 함수(`_build_llm()`)로 만들어지므로 토큰 사용량은 모델 ID별로 자동 집계된다
(`get_token_usage_summary()`).

**(결정) `ragas.evaluate()`(배치 API)가 아니라 각 지표의 `single_turn_score()`를 문항마다
직접 호출한다.** `evaluate()`는 내부적으로 `nest_asyncio` + `asyncio.wait_for(...,
timeout=...)`를 쓰는데, Python 3.14에서 `RuntimeError: Timeout should be used inside a
task`로 실제로 깨지는 것을 실측 확인했다 — `nest_asyncio`(마지막 릴리스가 오래돼
Python 3.12+의 `asyncio.timeout()` task-컨텍스트 요구사항과 안 맞음)와 이 프로젝트가
쓰는 최신 Python(3.14)의 조합 문제다(4절 "requirements.txt"에 이미 기록된 "ragas +
최신 Python" 버전 갈등의 또 다른 사례). `single_turn_score()`는 이 타임아웃 래퍼를
안 거치고 `loop.run_until_complete()`로 직접 실행해 문제가 재현되지 않는 것까지 실측
확인했다 — 결과값(지표 점수)은 동일하고 실행 경로만 다르다.

**재개(resume) 설계**: 질문-답변 수집(`_collect_qa()`)과 지표 채점(`_score_samples()`)
둘 다 문항마다 즉시 저장하고 재개 가능하다(Bedrock 할당량 초과가 오늘 여러 번 겪은
정상적인 운영 조건이라 반드시 필요, `run_eval.py`의 `_load_partial_results`와 같은
설계) — `single_turn_score()`로 문항 단위 호출을 쓰기로 한 덕분에 지표 채점 단계도
`evaluate()`의 배치 처리와 달리 문항 단위 재개가 가능해졌다(부수적 이득).
"""

import csv
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient

from src.api import app
from src.retriever import default_embeddings
from src.tools import _default_llm, get_token_usage_summary, reset_token_usage

_CSV_PATH = Path(__file__).resolve().parent / "test_queries.csv"

# **(결정) `ragas`를 모듈 최상단에서 import하지 않는다.** `ragas.executor`가 import 시점에
# `nest_asyncio.apply()`를 호출해 프로세스 전역 asyncio 상태를 패치하는데, 이게 Starlette
# `TestClient`가 쓰는 anyio의 블로킹 포털과 충돌해 `AttributeError: 'NoneType' object has
# no attribute 'set_name'`으로 `_collect_qa()`의 첫 `POST /query` 호출부터 깨지는 것을
# 실측 확인했다 — QA 수집이 끝나기 전에 ragas를 import하면 그 시점부터 TestClient 자체가
# 못 쓰게 된다. 그래서 `_score_samples()`(QA 수집이 전부 끝난 뒤에만 호출됨) 안에서
# 지연 import한다. 지표 이름은 순수 문자열 상수로 미리 선언해, 이 상수를 쓰는 `_write_report()`
# 는 ragas를 import할 필요가 없게 한다.
_METRIC_NAMES = ["context_recall", "context_precision", "faithfulness", "answer_relevancy"]


def _atomic_write_json(path: Path, data: list | dict) -> None:
    """`run_eval.py`의 `_atomic_write_json()`과 같은 이유(원자적 쓰기)로 그대로 재사용."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _merge_token_usage(a: dict[str, dict[str, int]], b: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    merged = {model_id: dict(counts) for model_id, counts in a.items()}
    for model_id, counts in b.items():
        bucket = merged.setdefault(model_id, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 0})
        for key, value in counts.items():
            bucket[key] = bucket.get(key, 0) + value
    return merged


def _save_token_usage(tokens_path: Path, token_usage: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    """지금까지 누적된 사용량을 `token_usage`에 합치고 저장한 뒤, 현재 프로세스분을 초기화한다."""
    token_usage = _merge_token_usage(token_usage, get_token_usage_summary())
    reset_token_usage()
    _atomic_write_json(tokens_path, token_usage)
    return token_usage


def _collect_qa(qa_path: Path, tokens_path: Path, token_usage: dict[str, dict[str, int]]) -> list[dict]:
    """모든 문항에 대해 `POST /query`를 호출해 ragas가 요구하는 형태로 모은다.

    문항마다 즉시 저장한다 — Bedrock 할당량 초과로 중간에 멈춰도 이미 모은 답변이
    사라지지 않는다(`run_eval.py`의 `_load_partial_results` 재개 설계와 같은 이유).
    """
    client = TestClient(app)
    with open(_CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    done = {r["id"]: r for r in _load_json(qa_path, [])}
    collected = [done[row["id"]] for row in rows if row["id"] in done]

    for row in rows:
        if row["id"] in done:
            print(f"[ragas:수집] {row['id']} -> 이미 수집됨(건너뜀)")
            continue

        response = client.post("/query", json={"question": row["input"]})
        data = response.json()
        # ragas는 retrieved_contexts가 빈 리스트면 일부 지표에서 에러를 내므로, 실제로
        # contexts가 없는 응답(예: 범위 밖 질문)에는 빈 문자열 하나를 넣어 방어한다.
        contexts = [c["text"] for c in data["contexts"]] or [""]

        entry = {
            "id": row["id"],
            "category": row["category"],
            "user_input": row["input"],
            "response": data["answer"],
            "retrieved_contexts": contexts,
            "reference": row["note"],
        }
        collected.append(entry)
        print(f"[ragas:수집] {row['id']} ({row['category']}) 수집 완료 — contexts {len(contexts)}건")

        _atomic_write_json(qa_path, collected)
        _save_token_usage(tokens_path, token_usage)

    return collected


def _score_samples(
    samples: list[dict], scores_path: Path, tokens_path: Path, token_usage: dict[str, dict[str, int]]
) -> dict[str, dict[str, float]]:
    """수집된 질문-답변마다 4개 ragas 지표를 `single_turn_score()`로 직접 채점한다.

    `ragas.evaluate()`(배치 API) 대신 이 방식을 쓰는 이유는 모듈 docstring 참고 —
    Python 3.14에서 `evaluate()`가 `RuntimeError: Timeout should be used inside a task`로
    깨지는 것을 실측했다. 문항마다 즉시 저장해 재개 가능하다.

    `ragas`를 여기서(QA 수집이 전부 끝난 뒤) 지연 import하는 이유는 모듈 상단 주석
    참고 — import 시점에 `nest_asyncio.apply()`가 실행돼 `TestClient`를 깨뜨린다.
    """
    from ragas import SingleTurnSample
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    metrics = [context_recall, context_precision, faithfulness, answer_relevancy]
    llm = LangchainLLMWrapper(_default_llm(disable_parallel_tool_use=False))
    embeddings = LangchainEmbeddingsWrapper(default_embeddings())
    for metric in metrics:
        metric.llm = llm
        if hasattr(metric, "embeddings"):
            metric.embeddings = embeddings

    scores: dict[str, dict[str, float]] = _load_json(scores_path, {})

    for sample in samples:
        if sample["id"] in scores:
            print(f"[ragas:채점] {sample['id']} -> 이미 채점됨(건너뜀)")
            continue

        turn_sample = SingleTurnSample(
            user_input=sample["user_input"],
            response=sample["response"],
            retrieved_contexts=sample["retrieved_contexts"],
            reference=sample["reference"],
        )
        row_scores: dict[str, float] = {}
        for metric in metrics:
            row_scores[metric.name] = metric.single_turn_score(turn_sample)
        scores[sample["id"]] = row_scores
        print(f"[ragas:채점] {sample['id']} ({sample['category']}) -> {row_scores}")

        _atomic_write_json(scores_path, scores)
        _save_token_usage(tokens_path, token_usage)

    return scores


def run_ragas(report_path: Path) -> None:
    qa_path = report_path.with_suffix(".qa.json")
    scores_path = report_path.with_suffix(".scores.json")
    tokens_path = report_path.with_suffix(".tokens.json")

    token_usage = _load_json(tokens_path, {})
    reset_token_usage()

    samples = _collect_qa(qa_path, tokens_path, token_usage)
    token_usage = _load_json(tokens_path, {})  # _collect_qa가 마지막으로 저장한 누적값

    print(f"[ragas] {len(samples)}문항 수집 완료 — 지표 채점 시작(검증 모델 사용)")
    scores = _score_samples(samples, scores_path, tokens_path, token_usage)
    token_usage = _load_json(tokens_path, {})  # _score_samples가 마지막으로 저장한 누적값

    _write_report(report_path, samples, scores, token_usage)
    print(f"[ragas] 완료 — {report_path}")


def _write_report(
    report_path: Path,
    samples: list[dict],
    scores: dict[str, dict[str, float]],
    token_usage: dict[str, dict[str, int]],
) -> None:
    metric_names = _METRIC_NAMES

    lines = [
        "# 3일차 3번 — RAGAS 평가 지표 결과",
        "",
        "## 모델별 토큰 사용량",
        "",
    ]
    if not token_usage:
        lines.append("(토큰 사용량 집계 없음)")
    else:
        lines.append("| 모델 | 호출 수 | 입력 토큰 | 출력 토큰 | 총 토큰 |")
        lines.append("|---|---|---|---|---|")
        grand_total = 0
        for model_id, counts in sorted(token_usage.items()):
            lines.append(
                f"| `{model_id}` | {counts.get('calls', 0):,} | {counts.get('input_tokens', 0):,} | "
                f"{counts.get('output_tokens', 0):,} | {counts.get('total_tokens', 0):,} |"
            )
            grand_total += counts.get("total_tokens", 0)
        lines.append(f"\n**전체 합계: {grand_total:,} 토큰**")
    lines.append("")

    lines.append(f"## 지표별 평균 점수 (전체 {len(samples)}문항)")
    lines.append("")
    lines.append("| 지표 | 평균 |")
    lines.append("|---|---|")
    for metric_name in metric_names:
        values = [scores[s["id"]][metric_name] for s in samples if s["id"] in scores]
        values = [v for v in values if v == v]  # NaN 제외
        mean_score = sum(values) / len(values) if values else float("nan")
        lines.append(f"| `{metric_name}` | {mean_score:.3f} |" if mean_score == mean_score else f"| `{metric_name}` | N/A |")
    lines.append("")

    lines.append("## 문항별 상세 점수")
    lines.append("")
    header_cols = ["id", "category"] + metric_names
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "---|" * len(header_cols))
    for sample in samples:
        row_scores = scores.get(sample["id"], {})
        row_values = [sample["id"], sample["category"]]
        for metric_name in metric_names:
            value = row_scores.get(metric_name)
            row_values.append(f"{value:.3f}" if isinstance(value, float) and value == value else "N/A")
        lines.append("| " + " | ".join(row_values) + " |")
    lines.append("")

    lines.append("## 알려진 제약")
    lines.append("")
    lines.append(
        "- `reference`(ground truth)는 `test_queries.csv`의 `note` 필드를 그대로 재사용한다 — "
        "스키마에 정답 문장 전용 컬럼이 없어서다(조건 8 1순위, 계획 문서 참고). `note`에는 "
        "판정 기준 설명·배경 문장이 섞여 있어 순수 정답 문장보다 노이즈가 있다."
    )
    lines.append(
        "- `retrieved_contexts`는 `POST /query`의 `contexts` 필드를 그대로 쓰는데, 이 필드는 "
        "질문과 무관하게 **그 시점의 findings 전체**를 담는다(API 스펙 고정, `agent.py`가 "
        "질문 내용과 무관하게 항상 3개 카테고리를 전부 스캔하는 설계와 동일한 이유) — 특정 "
        "질문에 대해 좁혀진 검색 결과가 아니므로, `context_precision`이 실제 응답 품질보다 "
        "낮게 나올 수 있다."
    )
    lines.append(
        "- negative/guardrail 카테고리(Q7-9, Q14-15 등)처럼 범위 밖 요청을 정직하게 거절하는 "
        "게 정답인 문항은, `note`가 '거절해야 한다'는 취지 설명이라 이 문항에 대한 "
        "`context_recall`/`context_precision` 수치는 문자 그대로의 사실 일치도보다는 근사값으로 "
        "해석해야 한다."
    )
    lines.append(
        "- `ragas.evaluate()`(배치 API) 대신 각 지표의 `single_turn_score()`를 문항마다 직접 "
        "호출한다 — Python 3.14 + `nest_asyncio` 조합에서 `evaluate()`가 "
        "`RuntimeError: Timeout should be used inside a task`로 깨지는 것을 실측 확인했다. "
        "결과값은 동일하고 실행 경로만 다르다."
    )
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import sys

    report_name = sys.argv[1] if len(sys.argv) > 1 else "ragas_report.md"
    run_ragas(Path(__file__).resolve().parent / report_name)
