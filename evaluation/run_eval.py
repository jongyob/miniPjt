"""`test_queries.csv`로 자체평가를 실행하고 `round{N}_report.md`(+결과 JSON)를 만든다.

2일차 7번(1차)과 3일차 2번(2차)이 이 스크립트를 라운드 이름만 바꿔 재사용한다(Day7
`run_eval`/`compare_eval` 개념). 실행: `python -m evaluation.run_eval <라운드 이름> <리포트 파일명>`
(예: `python -m evaluation.run_eval 1차 round1_report.md`). 프로젝트 루트에서 실행해야
`src` 패키지를 찾는다.

판정은 두 갈래로 나눈다 — `expected_tools`(실제로 어떤 스캐너/RAG 도구를 호출했는지)는
`trace`를 그대로 읽어 결정적으로 확인하고(LLM 불필요), `expected_traits`/`forbidden`(응답의
의미적 성질)만 LLM 판정자(judge)에게 맡긴다. 둘 다 통과해야 최종 PASS다.
"""

import csv
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.api import app
from src.tools import _default_llm, get_token_usage_summary, reset_token_usage

_CSV_PATH = Path(__file__).resolve().parent / "test_queries.csv"


class JudgeVerdict(BaseModel):
    """LLM 판정자의 구조화 출력(패턴 #1)."""

    passed: bool
    reason: str


_JUDGE_PROMPT = """당신은 QA 평가자입니다. 아래 정보를 보고 실제 응답이 기대를 충족하는지 판단하세요.

**중요 — 이 시스템의 답변 형식(반드시 지키세요, 지금까지 판정자가 가장 자주 틀리는
지점입니다)**: 이 시스템은 질문 성격과 무관하게 항상 "보안"/"오류"/"성능" 3개 섹션으로
나눠 답합니다(3개 전문 Agent를 항상 병렬 실행하는 설계 — 질문이 보안만 물어도 오류·성능
섹션이 함께 나옵니다). **"오류" 섹션과 "성능" 섹션은 보안 취약점을 스캔하지 않습니다** —
"오류" Agent는 미사용 변수/import 같은 코드 버그만, "성능" Agent는 N+1 같은 성능 패턴만
찾습니다. 그래서 보안 관련 질문에 "오류"/"성능" 섹션이 "이 카테고리에서는 발견된 것이
없다"거나 "IDOR/SQL Injection 같은 보안 취약점은 발견되지 않았다"거나 "보안 점검은 이
섹션의 범위 밖"이라고 답하는 것은 **당연하고 정상적인 동작이지, "보안" 섹션이 보고한
발견 사항을 부정하거나 모순되는 게 절대 아닙니다** — "오류"/"성능" Agent는 애초에
보안 취약점을 스캔하는 도구가 없어서 "없다"고 답하는 것뿐입니다(실제로 찾아봤는데
없다는 게 아니라, 그 카테고리 도구로는 안 잡힌다는 뜻). 예를 들어 "보안" 섹션이
"IDOR 취약점을 발견했다"고 명확히 보고했는데 "오류" 섹션이 "IDOR 취약점이 발견되지
않았다"고 쓴 경우, 이는 오류 스캐너가 보안 취약점을 애초에 찾지 않는다는 뜻으로
해석해야지 "허위 부정"이나 "fabricated_findings"로 판정하면 안 됩니다. **판정은
반드시 질문과 직접 관련된 카테고리 섹션(대개 "보안")의 내용만 보고 결정하세요** — 관련
없는 다른 섹션에 "발견 없음"/"범위 밖" 문구가 있다는 것 자체는 어떤 경우에도 fail
사유가 될 수 없습니다.

**중요 — 실제로 호출된 도구(trace 기반 사실, 텍스트가 아니라 시스템 로그로 확인됨)**:
{used_tools}
이 목록에 있는 도구는 **실제로 호출되어 진짜 결과를 받았다는 것이 이미 결정적으로
확인된 사실**입니다 — 답변에 등장하는 수치·응답 데이터가 "그 도구의 실행 결과처럼
보이는지"는 이 목록과 대조해서 판단하고, 목록에 있는 도구의 결과라면 "조작됐다
(fabricated)"고 의심하지 마세요. (예: `run_live_load_test`가 이 목록에 있다면, 답변의
p95 지연시간·에러율 수치는 그 도구가 실제로 측정한 값입니다. `run_idor_pentest_probe`가
있다면 그 요청/응답 예시는 실제로 보낸 것입니다.) 반대로 이 목록에 없는데도 답변이
마치 실제 도구를 호출한 것처럼 구체적인 수치·응답을 제시한다면 그건 정말 조작(fabricated)
일 수 있으니 의심하세요.

질문: {input}
기대 특성(expected_traits, 응답이 반드시 보여야 할 성질): {expected_traits}
금지 사항(forbidden, 응답에 절대 있으면 안 되는 것): {forbidden}
기대 답변 요지(note): {note}

실제 응답(answer):
{answer}

기대 특성을 모두 충족하고 금지 사항을 전혀 위반하지 않았으면 passed=true, 하나라도
문제가 있으면 passed=false로 답하고 이유(한국어, 한두 문장)를 reason에 적으세요."""


def _judge(row: dict[str, str], answer: str, used_tools: set[str]) -> JudgeVerdict:
    llm = _default_llm(disable_parallel_tool_use=False).with_structured_output(JudgeVerdict)
    prompt = _JUDGE_PROMPT.format(
        input=row["input"],
        expected_traits=row["expected_traits"] or "(없음)",
        forbidden=row["forbidden"] or "(없음)",
        note=row["note"],
        answer=answer,
        used_tools=", ".join(sorted(used_tools)) or "(이번 호출에서 실제로 호출된 도구 없음)",
    )
    return llm.invoke(prompt)


def _tools_used(trace: list[dict]) -> set[str]:
    """trace 이벤트의 `step`(예: `security_agent:tool:scan_security`)에서 도구 이름만 뽑는다."""
    used: set[str] = set()
    for event in trace:
        step = event["step"]
        if ":tool:" in step:
            used.add(step.split(":tool:")[-1])
    return used


def _load_partial_results(json_path: Path) -> dict[str, dict]:
    """이전 실행이 남긴 부분 결과를 읽는다(재개용) — 없거나 손상됐으면 빈 dict."""
    if not json_path.exists():
        return {}
    try:
        existing = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {r["id"]: r for r in existing}


def _atomic_write_json(path: Path, data: list[dict] | dict) -> None:
    """`path`에 JSON을 원자적으로 쓴다 — 임시 파일에 먼저 쓰고 교체(rename)한다.

    **(결정) 재개(resume) 기능을 실제로 재검증하다가 발견한 문제**: 원래는
    `path.write_text(...)`를 바로 호출했는데, 이 호출 도중에 프로세스가 죽으면
    JSON 파일이 손상된 채로 남고, 다음 실행의 `_load_partial_results()`가
    `JSONDecodeError`를 잡아 **빈 dict를 반환**해 그동안 완료한 문항 전부를 처음부터
    다시 처리하게 된다 — 정확히 이 재개 기능이 막으려던 것과 같은 종류의 손실이 다른
    지점(쓰기 중간)에서 재발할 수 있는 구조였다. 임시 파일 쓰기 + `os.replace()`는
    운영체제 수준에서 원자적이라, 중간에 죽어도 기존 파일은 손상되지 않고 그대로 남는다.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_token_usage(path: Path) -> dict[str, dict[str, int]]:
    """이전 실행이 남긴 모델별 토큰 사용량을 읽는다(재개용) — 없거나 손상됐으면 빈 dict.

    **(사용자 요청, 2026-09-03)** "수행에 들어간 모델별 토큰을 레포트 상단에 기입"하기
    위해 추가했다. `_load_partial_results()`와 같은 이유로 파일에 저장한다 — Bedrock
    할당량 초과로 여러 프로세스 실행에 걸쳐 재개되는 게 일상이라(오늘 2차 평가에서도
    5차례 이상 재시도), 토큰 집계도 프로세스 하나의 메모리(`tools._TOKEN_USAGE`)만으로는
    이전 실행분이 사라진다.
    """
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _merge_token_usage(
    a: dict[str, dict[str, int]], b: dict[str, dict[str, int]]
) -> dict[str, dict[str, int]]:
    """두 모델별 토큰 사용량 dict를 모델 단위로 합산한다."""
    merged = {model_id: dict(counts) for model_id, counts in a.items()}
    for model_id, counts in b.items():
        bucket = merged.setdefault(model_id, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 0})
        for key, value in counts.items():
            bucket[key] = bucket.get(key, 0) + value
    return merged


def run_eval(round_name: str, report_path: Path) -> list[dict]:
    """`test_queries.csv`의 모든 문항을 실제 `POST /query`로 호출하고 판정한다.

    **(결정) 문항마다 즉시 JSON에 저장하고, 이미 처리된 문항은 재실행 시 건너뛴다** — Bedrock
    할당량 초과(`ThrottlingException`)로 중간에 멈춰도 이미 낸 비용(완료된 문항)이 사라지지
    않게 하기 위함이다(2일차 7번 첫 실행에서 17문항 중 2건만 처리되고 할당량 초과로 중단됐는데,
    끝에서만 저장하는 구조라 그 2건마저 날아간 것을 겪고 나서 추가했다).
    """
    client = TestClient(app)
    with open(_CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    json_path = report_path.with_suffix(".json")
    done = _load_partial_results(json_path)
    results: list[dict] = [done[row["id"]] for row in rows if row["id"] in done]

    tokens_path = report_path.with_suffix(".tokens.json")
    token_usage = _load_token_usage(tokens_path)
    reset_token_usage()

    for row in rows:
        if row["id"] in done:
            print(f"[{round_name}] {row['id']} ({row['category']}) -> 이미 처리됨(건너뜀)")
            continue

        response = client.post("/query", json={"question": row["input"]})
        data = response.json()
        answer = data["answer"]
        trace = data["trace"]

        used_tools = _tools_used(trace)
        verdict = _judge(row, answer, used_tools)

        expected_tools = {t for t in row["expected_tools"].split(";") if t}
        missing_tools = sorted(expected_tools - used_tools)

        passed = verdict.passed and not missing_tools
        result = {
            "id": row["id"],
            "category": row["category"],
            "input": row["input"],
            "passed": passed,
            "judge_passed": verdict.passed,
            "judge_reason": verdict.reason,
            "missing_tools": missing_tools,
            "answer_preview": answer[:300],
        }
        results.append(result)
        print(f"[{round_name}] {row['id']} ({row['category']}) -> {'PASS' if passed else 'FAIL'}: {verdict.reason}")

        # 문항마다 즉시 저장 — 중간에 죽어도 여기까지는 남는다(토큰 사용량도 결과와 같은
        # 주기로 저장해, 재개 시 이전 프로세스분이 사라지지 않게 한다).
        _atomic_write_json(json_path, results)
        token_usage = _merge_token_usage(token_usage, get_token_usage_summary())
        reset_token_usage()
        _atomic_write_json(tokens_path, token_usage)

    _write_report(round_name, report_path, results, token_usage)
    return results


def _write_report(
    round_name: str, report_path: Path, results: list[dict], token_usage: dict[str, dict[str, int]]
) -> None:
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])

    lines = [
        f"# {round_name} 자체평가 결과",
        "",
        f"통과: {passed_count}/{total} ({passed_count / total:.0%})",
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

    by_category: dict[str, list[dict]] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    for category, rows in by_category.items():
        cat_passed = sum(1 for r in rows if r["passed"])
        lines.append(f"## {category} ({cat_passed}/{len(rows)})")
        lines.append("")
        for r in rows:
            status = "PASS" if r["passed"] else "FAIL"
            lines.append(f"- **{r['id']}** [{status}] — {r['input']}")
            lines.append(f"  - 판정 근거: {r['judge_reason']}")
            if r["missing_tools"]:
                lines.append(f"  - 누락된 예상 도구 호출: {', '.join(r['missing_tools'])}")
        lines.append("")

    failed = [r for r in results if not r["passed"]]
    lines.append("## 실패 유형 요약")
    lines.append("")
    if not failed:
        lines.append("실패한 문항이 없습니다.")
    else:
        for r in failed:
            reasons = []
            if not r["judge_passed"]:
                reasons.append(r["judge_reason"])
            if r["missing_tools"]:
                reasons.append(f"누락된 예상 도구 호출: {', '.join(r['missing_tools'])}")
            lines.append(f"- **{r['id']}**: {'; '.join(reasons)}")

    report_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    round_arg = sys.argv[1] if len(sys.argv) > 1 else "1차"
    report_arg = sys.argv[2] if len(sys.argv) > 2 else "round1_report.md"
    run_eval(round_arg, Path(__file__).resolve().parent / report_arg)
