"""Finding 리스트를 사람이 읽는 `report.md`와 기계용 `report.json`으로 저장한다.

2일차 3번. 저장 위치는 `reports/`(0-1절 필수 목록에 없는 추가 디렉터리이며 `evaluation/`의
1·2차 자체평가 리포트와는 별개 산출물 — CLAUDE.md 2절 "리포트 저장 위치" 결정 참고).
Supervisor 그래프에 실제로 연결하는 것은 2일차 4~5번(파이프라인 완주·`api.py` 연결) 몫이다.

**(결정, 2026-09-03 — 사용자 요청, `report.md` 가독성 개선)** 개발자/설계자/PL/PM이 이
파일 하나만 보고 "어디서/무엇이/왜/어떻게 고치는지"를 한눈에 알 수 있어야 한다는 요청으로
`_render_finding()`을 다시 썼다:
- **위치/문제/원인/수정 방법** 4단으로 보안·오류·성능 구분 없이 통일된 포맷을 쓴다(예전엔
  카테고리마다 사실상 같은 포맷이었지만 "원인"/"수정 방법"이 아예 없었다).
- `그룹 G-N`(파일 단위 그룹핑 ID, `agent.py`의 `assign_group_ids()` 내부 집계용) 표시를
  뺐다 — 이 파이프라인 밖에서는 아무 의미가 없는 순수 내부 식별자다.
- RAG 체크리스트에서 검색해 온 "근거 문서" 원문(특히 "정적 도구가 못 잡는 이유" 같은,
  Agent가 왜 이 체크리스트를 참고했는지 설명하는 개발 노트)을 뺐다 — 독자가 문제를
  고치는 데 필요한 정보가 아니고, 벡터 검색 청크 경계 때문에 문장이 중간에 잘려 나오기도
  했다. 대신 "수정 방법"은 알려진 규칙/키워드 기반 고정 안내문(`_RULE_GUIDANCE`/
  `_KEYWORD_GUIDANCE`)으로 매번 완전한 문장을 만든다 — RAG 청크를 그대로 보여주는 것보다
  안정적이다. (`report.json`/`POST /query`의 `contexts`는 원본 데이터를 그대로 유지한다
  — API 스펙 고정 필드이자 ragas 등 기계 소비자를 위한 것이라 사람이 읽는 `report.md`와
  다르게 손대지 않는다.)
- 글자 수로 강제로 잘라내는 부분이 없다 — 이 파일은 원래도 그런 자리가 없었지만, 이번
  요청("가끔 글자제한이 걸려있는데 없애 달라")에 맞춰 명시적으로 확인·기록해 둔다.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from src.agent import Finding, mask_pii

_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

_CATEGORY_TITLES = {
    "security": "보안",
    "error": "오류",
    "performance": "성능",
}

_SEVERITY_LABELS = {"high": "높음", "medium": "중간", "low": "낮음"}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# 리포트 상단 "감지된 언어" 줄에 상태별로 붙이는 코멘트(사용자 요청, CLAUDE.md 10-F절).
# "active"는 아무 코멘트도 붙이지 않는다 — 실제로 점검된 언어라는 게 기본값이기 때문이다.
_LANGUAGE_STATUS_LABELS = {"active": "", "excepted": "(점검제외)", "unsupported": "(점검불가)"}

# 규칙 ID -> (원인, 수정 방법). bandit/eslint/pylint는 항상 같은 규칙 이름을 내는 고정
# 카탈로그라 정확히 일치시킬 수 있다.
_RULE_GUIDANCE: dict[str, tuple[str, str]] = {
    "B105": (
        "소스 코드에 비밀번호·자격증명이 그대로 하드코딩돼 있습니다.",
        "값을 환경변수나 시크릿 매니저로 옮기고, 소스에는 참조만 남기세요.",
    ),
    "B307": (
        "검증되지 않은 입력을 eval()로 그대로 실행하면 임의 코드 실행으로 이어질 수 있습니다.",
        "eval() 대신 ast.literal_eval() 같은 안전한 파싱 방법을 쓰세요.",
    ),
    "B605": (
        "셸을 거쳐 외부 명령을 실행하면 입력값에 셸 메타문자가 섞였을 때 명령어 주입으로 이어집니다.",
        "subprocess를 shell=False로 호출하고 인자를 리스트로 분리해서 넘기세요.",
    ),
    "unused-import": (
        "더 이상 쓰이지 않는 import가 남아 있습니다.",
        "사용하지 않는 import 문을 삭제하세요.",
    ),
    "no-unused-vars": (
        "선언만 되고 실제로 쓰이지 않는 변수가 있습니다.",
        "사용하지 않는 변수를 삭제하거나, 의도적으로 남긴 경우 밑줄 접두사(_)로 표시하세요.",
    ),
    "no-eval": (
        "eval() 사용은 임의 코드 실행 위험이 있습니다.",
        "eval() 대신 안전한 대안(JSON.parse 등)으로 교체하세요.",
    ),
    "vue/no-v-html": (
        "v-html은 사용자 입력을 그대로 HTML로 렌더링해 XSS 위험이 있습니다.",
        "신뢰할 수 없는 데이터는 텍스트 바인딩으로 렌더링하거나 DOMPurify 같은 라이브러리로 살균하세요.",
    ),
}

# 위 고정 카탈로그에 없는 규칙(Java LLM 리뷰가 매번 살짝 다르게 짓는 규칙 이름, npm audit의
# GHSA ID 등)은 규칙 이름에 포함된 키워드로 근사 매칭한다 — `agent.py`의
# `_RAG_REFERENCE_KEYWORDS`와 같은 이유(LLM이 짓는 규칙 이름이 매번 살짝 다른 것을 실측
# 확인했다). 먼저 일치하는 항목을 쓰므로 더 구체적인 키워드를 앞에 둔다.
_KEYWORD_GUIDANCE: list[tuple[str, tuple[str, str]]] = [
    (
        "idor",
        (
            "리소스를 조회할 때 소유권(요청자와 실제 소유자가 같은지) 검증이 없습니다.",
            "조회한 리소스의 소유자 필드와 현재 인증된 사용자를 비교해, 다르면 403을 반환하도록 고치세요.",
        ),
    ),
    (
        "mybatis",
        (
            "MyBatis에서 ${}(문자열 치환)를 써서 사용자 입력이 SQL에 그대로 삽입됩니다.",
            "가능한 경우 #{}(파라미터 바인딩)로 바꾸고, 컬럼명처럼 바인딩이 안 되는 값만 화이트리스트로 검증하세요.",
        ),
    ),
    (
        "sql-injection",
        (
            "사용자 입력을 검증 없이 SQL 문자열에 직접 결합해 실행합니다.",
            "파라미터 바인딩(PreparedStatement)으로 바꾸고, 문자열 결합으로 SQL을 만들지 마세요.",
        ),
    ),
    (
        "n-plus-one",
        (
            "목록을 조회한 뒤 각 항목마다 반복문 안에서 개별 쿼리를 또 실행합니다.",
            "IN 절이나 JOIN으로 한 번에 조회하도록 배치 처리로 바꾸세요.",
        ),
    ),
    (
        "n+1",
        (
            "목록을 조회한 뒤 각 항목마다 반복문 안에서 개별 쿼리를 또 실행합니다.",
            "IN 절이나 JOIN으로 한 번에 조회하도록 배치 처리로 바꾸세요.",
        ),
    ),
]


def _guidance_for(finding: Finding) -> tuple[str, str]:
    """(원인, 수정 방법)을 반환한다.

    알려진 규칙/키워드가 없으면 "원인"은 발견 내용(summary)을 그대로 쓰고 "수정 방법"은
    일반 안내 문구로 대체한다 — 항상 두 필드가 채워진 채로 통일된 포맷을 유지하기 위함이다.
    """
    guidance = _RULE_GUIDANCE.get(finding.rule)
    if guidance:
        return guidance
    rule_lower = finding.rule.lower()
    for keyword, mapped in _KEYWORD_GUIDANCE:
        if keyword in rule_lower:
            return mapped
    if finding.tool.lower() in ("npm-audit", "npm_audit", "npm audit", "audit"):
        return (
            "사용 중인 라이브러리 버전에 알려진 보안 취약점이 있습니다.",
            "패키지를 취약점이 패치된 버전 이상으로 업그레이드하세요.",
        )
    return (finding.summary, "코드 리뷰를 통해 구체적인 수정 방안을 확인하세요.")


def _render_language_line(language_statuses: list[tuple[str, str, str]]) -> str:
    """`agent.py`의 `LANGUAGE_STATUSES`(자동 감지 + `exceptLanguages` 반영 결과)를
    "감지된 언어: Vue3, Java 1.8(점검제외), Go(점검불가)" 형태의 한 줄로 렌더링한다.

    **(결정, 2026-09-03 — 사용자 요청)** 계열 이름(`name`, `exceptLanguages` 매칭용
    "vue"/"java")이 아니라 **표시 이름**(`display`, 실제 프로젝트에서 감지한 버전이
    반영된 "Vue3"/"Java 1.8")을 보여준다 — `exceptLanguages`에는 버전 없이 적어도,
    리포트에는 실제 감지된 버전이 나오게 하기 위함이다.
    """
    if not language_statuses:
        return "감지된 언어: 없음"
    parts = [
        f"{display}{_LANGUAGE_STATUS_LABELS[status]}" for name, status, display in language_statuses
    ]
    return "감지된 언어: " + ", ".join(parts)


def _render_finding(finding: Finding) -> str:
    """Finding 한 건을 위치/문제/원인/수정 방법 4단 통일 포맷으로 렌더링한다.

    `mask_pii`를 여기서 다시 적용한다 — LLM 프롬프트 구성 시점(1일차 3번, 이미 적용됨)과
    리포트 저장 직전, 두 번 마스킹한다는 조건 9 설계를 그대로 따른다.
    """
    summary = mask_pii(finding.summary)
    location = f"{finding.file}:{finding.line}" if finding.line is not None else finding.file
    severity_label = _SEVERITY_LABELS.get(finding.severity, finding.severity)
    cause, fix = _guidance_for(finding)
    cause = mask_pii(cause)

    return "\n".join(
        [
            f"### {finding.id} — [{severity_label}] {location}",
            "",
            f"- **문제**: {summary}",
            f"- **원인**: {cause}",
            f"- **수정 방법**: {fix}",
            f"- 참고: `{finding.tool}`(`{finding.rule}`)",
            "",
        ]
    )


def _render_token_usage_section(token_usage: dict[str, dict[str, int]]) -> list[str]:
    """모델별 토큰 사용량을 "## 모델별 토큰 사용량" 표로 렌더링한다(사용자 요청,
    CLAUDE.md 10-L절 — 평가 리포트(`round*_report.md`/`ragas_report.md`)에는 있던
    것이 정작 이 제품 리포트에는 빠져 있던 것을 사용자가 지적해 추가했다)."""
    lines = ["## 모델별 토큰 사용량", ""]
    if not token_usage:
        lines.append("(토큰 사용량 집계 없음)")
        lines.append("")
        return lines
    lines.append("| 모델 | 호출 수 | 입력 토큰 | 출력 토큰 | 총 토큰 |")
    lines.append("|---|---|---|---|---|")
    grand_total = 0
    for model_id, counts in sorted(token_usage.items()):
        lines.append(
            f"| `{model_id}` | {counts.get('calls', 0):,} | {counts.get('input_tokens', 0):,} | "
            f"{counts.get('output_tokens', 0):,} | {counts.get('total_tokens', 0):,} |"
        )
        grand_total += counts.get("total_tokens", 0)
    lines.append("")
    lines.append(f"**전체 합계: {grand_total:,} 토큰**")
    lines.append("")
    return lines


def render_markdown(
    findings: list[Finding],
    language_statuses: list[tuple[str, str, str]] | None = None,
    token_usage: dict[str, dict[str, int]] | None = None,
) -> str:
    """전체 Finding 리스트를 카테고리(보안/오류/성능)별로 묶은 Markdown 리포트로 렌더링한다.

    각 카테고리 안에서는 심각도(높음→중간→낮음) 순으로 정렬해, 가장 시급한 문제가 먼저
    보이게 한다. `language_statuses`(`agent.py`의 `LANGUAGE_STATUSES`)를 주면 리포트
    상단에 "감지된 언어" 줄을 추가한다 — 자동 감지됐지만 어댑터가 없는 언어는 "(점검불가)",
    `config.yaml`의 `exceptLanguages`로 의도적으로 뺀 언어는 "(점검제외)"로 표시한다
    (사용자 요청, CLAUDE.md 10-F절). 생략하면(기존 호출부·테스트 호환) 그 줄 없이 예전과
    동일하다. `token_usage`(`src/tools.py`의 `get_token_usage_summary()`)를 주면 리포트
    최상단에 "모델별 토큰 사용량" 표를 추가한다(사용자 요청, CLAUDE.md 10-L절) — 이
    호출 한 번(질문 응답 또는 전체 스캔)에 실제로 든 모델별 호출 수·입력/출력/총 토큰을
    보여준다.
    """
    counts = {category: 0 for category in _CATEGORY_TITLES}
    for finding in findings:
        counts[finding.category] += 1

    lines = ["# 코드 품질 리포트", ""]
    if token_usage is not None:
        lines += _render_token_usage_section(token_usage)
    if language_statuses is not None:
        lines.append(_render_language_line(language_statuses))
        lines.append("")
    lines += [
        f"총 {len(findings)}건 — 보안 {counts['security']} / 오류 {counts['error']} / "
        f"성능 {counts['performance']}",
        "",
    ]
    for category, title in _CATEGORY_TITLES.items():
        category_findings = [f for f in findings if f.category == category]
        lines.append(f"## {title} ({len(category_findings)}건)")
        lines.append("")
        if not category_findings:
            lines.append("발견된 것이 없습니다.")
            lines.append("")
            continue
        category_findings = sorted(
            category_findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, 3)
        )
        for finding in category_findings:
            lines.append(_render_finding(finding))
    return "\n".join(lines)


def save_report(
    findings: list[Finding],
    reports_dir: Path | None = None,
    language_statuses: list[tuple[str, str, str]] | None = None,
    token_usage: dict[str, dict[str, int]] | None = None,
) -> Path:
    """`reports_dir`(기본값 `reports/`)에 리포트를 저장하고, 실행마다 만든 타임스탬프
    파일(`.md`)의 경로를 반환한다.

    **(결정, 2026-09-03 — 사용자 요청 "이력 보존")** 이전에는 매 실행마다 `report.md`/
    `report.json`을 그대로 덮어써서 직전 실행 결과가 사라졌다(실측으로 확인된 문제).
    이제는 실행마다 `report_<UTC 타임스탬프>.md`/`.json`(예: `report_20260903_143022.md`)
    을 **새 파일로** 만들어 이력을 남기고, 동시에 `report.md`/`report.json`("최신" 편의
    사본 — 기존 UI(`GET /`)·API가 그대로 찾아 쓸 수 있게 유지)도 함께 갱신한다. 타임스탬프는
    초 단위라 같은 초 안에 두 번 저장하면 덮어써질 수 있지만, 이 파이프라인은 매 실행이
    최소 수 초~수십 초 걸려(LLM 호출) 실제로 부딪힐 일이 없다 — 마이크로초까지 넣는 건
    이번 범위에서는 과한 정밀도라 넣지 않았다. `language_statuses`는 `render_markdown()`
    으로 그대로 전달해 리포트 상단의 "감지된 언어" 줄에 반영한다(CLAUDE.md 10-F절).

    **(결정, 2026-09-03 — 사용자 요청)** `token_usage`(`src/tools.py`의
    `get_token_usage_summary()`)를 주면 리포트 최상단에 "모델별 토큰 사용량" 표를
    추가한다 — 평가 리포트(`round*_report.md`/`ragas_report.md`)에는 이미 있었는데
    정작 이 제품 리포트에는 빠져 있던 것을 사용자가 지적해 추가했다. 호출부(`api.py`)가
    이 호출 한 번(질문 응답 또는 전체 스캔)에 해당하는 토큰 사용량만 넘기도록
    `reset_token_usage()`/`get_token_usage_summary()`를 직접 관리한다 — `report.py`는
    받은 값을 그대로 렌더링만 한다(기존 "순수 템플릿" 설계 유지).
    """
    reports_dir = reports_dir or _REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)

    markdown = render_markdown(findings, language_statuses, token_usage)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "languages": (
            [
                {"name": name, "status": status, "display": display}
                for name, status, display in language_statuses
            ]
            if language_statuses is not None
            else []
        ),
        "token_usage": token_usage or {},
        "findings": [_masked_finding_dict(finding) for finding in findings],
    }
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    timestamped_md = reports_dir / f"report_{timestamp}.md"
    timestamped_md.write_text(markdown, encoding="utf-8")
    (reports_dir / f"report_{timestamp}.json").write_text(json_text, encoding="utf-8")

    # "최신" 편의 사본 — 이력 파일과 내용은 완전히 같다.
    (reports_dir / "report.md").write_text(markdown, encoding="utf-8")
    (reports_dir / "report.json").write_text(json_text, encoding="utf-8")

    return timestamped_md


def _masked_finding_dict(finding: Finding) -> dict:
    """`Finding`을 dict로 직렬화하면서 `summary`/`detail`/`reference.text`에 `mask_pii`를
    다시 적용한다.

    `report.json`은 기계용(ragas의 `contexts` 생성 등)이라 `group_id`/`reference` 등
    원본 필드를 전부 그대로 유지한다 — 사람이 읽는 `report.md`만 가독성을 위해 다르게
    구성한다(모듈 docstring 참고). `model_dump()`를 그대로 쓰면 `reference`(중첩된
    `ReferenceDoc`)의 `text`는 재마스킹을 거치지 않고 그대로 나간다 — Markdown 출력은 이미
    재마스킹하고 있었는데 JSON 쪽에서만 빠져 있던 것을 실측 재검증 중 발견해 고쳤다.
    """
    data = finding.model_dump()
    data["summary"] = mask_pii(finding.summary)
    data["detail"] = mask_pii(finding.detail)
    if data["reference"] is not None:
        data["reference"]["text"] = mask_pii(finding.reference.text)
    return data
