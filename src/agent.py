"""Supervisor 그래프와 Finding 데이터 모델.

1일차 3번: `Finding` Pydantic 모델과 "원시 결과 -> Finding 리스트" 변환, `mask_pii`
가드레일을 먼저 만든다. 1일차 4번: `security_agent`/`error_agent`/`performance_agent`
생성 함수를 추가한다. 2일차 1번: `CombinedAdapter`(여러 언어 어댑터를 하나로 묶음)와
Supervisor `StateGraph`(3개 Agent 병렬 실행 + 결과 취합)를 추가한다. 2일차 5번:
`trace`(패턴 #11 Observability)를 Supervisor 상태에 추가한다. 확장 phase 준비:
`config.yaml` 기반 언어 어댑터 선택(전체설계 11-3절/12절)을 추가한다.
"""

import json
import operator
import os
import re
import threading
import time
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, Protocol, TypedDict

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from src.config import is_live_probe_enabled, load_except_languages, load_load_profile
from src.retriever import retriever
from src.tools import (
    PROJECT_SOURCE_ROOT,
    DbAdapter,
    _report_llm,
    db_adapter,
    java_lite_adapter,
    probe_idor_vulnerability,
    python_adapter,
    run_concurrent_load_test,
    vue3_adapter,
)

# ---------------------------------------------------------------------------
# 언어 자동 감지 (전체설계 11-3절/12절, CLAUDE.md 10-F절 — 2026-09-03 사용자 요청으로
# `config.yaml`의 정적 `languages` 목록을 대체) — "언어 어댑터 3개 (1일차 4번)" 절보다
# 앞서 둔다. `_LANGUAGE_ADAPTER_REGISTRY`가 아래 3개 전문 Agent 생성 함수보다 먼저
# 필요한 건 아니지만, `_SCOPE_AND_ACTION_GUARDRAIL`(그 함수들의 프롬프트가 참조)이 감지
# 결과에서 활성 언어 이름을 뽑아 써야 해서, 그 프롬프트 상수보다는 먼저 와야 한다.
# ---------------------------------------------------------------------------


class LanguageAdapter(Protocol):
    """언어 어댑터가 갖춰야 할 최소 인터페이스(조건 4).

    아래 세 Agent 생성 함수는 이 인터페이스만 알고 있고, `vue3_adapter`/`java_lite_adapter`
    같은 구체적인 이름이나 `npm`/`eslint`/`vue` 같은 언어·도구 이름은 전혀 모른다.
    """

    def run_security(self) -> list[dict[str, Any]]: ...
    def run_error(self) -> list[dict[str, Any]]: ...
    def run_performance(self) -> list[dict[str, Any]]: ...


# "언어 이름 문자열" -> 실제 어댑터 객체. 예전엔 `config.yaml`의 `languages` 목록이 이
# 딕셔너리의 어떤 키를 쓸지 직접 지정했지만, 이제는 `_detect_languages()`가 자동으로
# 감지한 언어 중 여기 등록된 것만 실제로 점검 대상이 된다 — 새 언어를 지원하려면 이
# 딕셔너리에 어댑터를 추가하고 `_EXTENSION_LANGUAGE_MAP`에 확장자만 매핑하면 된다
# (`make_supervisor()`나 3개 전문 Agent 코드는 손대지 않는다).
_LANGUAGE_ADAPTER_REGISTRY: dict[str, "LanguageAdapter"] = {
    "vue": vue3_adapter,
    "java": java_lite_adapter,
    "python": python_adapter,
}

# 확장자 -> 언어("계열") 이름. 어댑터가 있는 언어(vue/java/python)뿐 아니라, 어댑터가
# 없어도 "실제 프로그래밍 언어"로는 인식해야 리포트에 "점검불가"로 표시할 수 있는 흔한
# 언어까지 등록해 둔다 — txt/md 같은 참고 문서 확장자는 아예 이 맵에 없으므로 자동으로
# 무시된다(사용자 요청: "실제 프로그램에 영향이 있는 언어"만 언어로 취급).
#
# **(결정, 2026-09-03 — 사용자 요청)** 여기 값은 버전이 섞이지 않은 "언어 계열" 이름이다
# (예전엔 Vue를 버전까지 박아 "vue3"로 등록했는데, 실제 버전은 `_detect_display_name()`
# 이 프로젝트의 `package.json`/`pom.xml`을 읽어 별도로 판단한다). `exceptLanguages`와
# `_LANGUAGE_ADAPTER_REGISTRY`는 전부 이 계열 이름 기준으로 비교하므로,
# `exceptLanguages: [vue]`라고 쓰면 실제 감지된 버전이 Vue2든 Vue3든 전부 제외된다.
_EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".vue": "vue",
    ".js": "vue",
    ".java": "java",
    ".py": "python",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".ts": "typescript",
    ".rs": "rust",
    ".kt": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
}

# 언어 감지 스캔에서 건너뛸 디렉터리 — 성능(특히 node_modules)과 오탐 방지 둘 다 목적.
_LANGUAGE_SCAN_SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build"}


def _detect_languages(root: Path) -> set[str]:
    """`root` 아래 모든 파일을 재귀적으로 훑어 `_EXTENSION_LANGUAGE_MAP`에 매핑되는 언어
    이름 집합을 반환한다. 매핑에 없는 확장자(txt/md 등 참고 문서 포함)는 애초에 무시된다."""
    detected: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _LANGUAGE_SCAN_SKIP_DIRS]
        for filename in filenames:
            language = _EXTENSION_LANGUAGE_MAP.get(Path(filename).suffix.lower())
            if language:
                detected.add(language)
    return detected


def _detect_vue_version(root: Path) -> str | None:
    """`package.json`의 `vue` 의존성 버전에서 메이저 버전을 뽑아 "Vue2"/"Vue3" 같은
    표시용 이름을 만든다. `package.json`이 없거나 `vue` 의존성이 없으면 `None`을
    반환한다(추측해서 만들어내지 않는다 — 실제 신호가 없으면 표시할 버전도 없다)."""
    for package_json in root.rglob("package.json"):
        if "node_modules" in package_json.parts:
            continue
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        version = (data.get("dependencies") or {}).get("vue") or (data.get("devDependencies") or {}).get("vue")
        if not version:
            continue
        match = re.search(r"(\d+)", version)
        if match:
            return f"Vue{match.group(1)}"
    return None


def _detect_java_version(root: Path) -> str | None:
    """`pom.xml`(Maven)의 컴파일러 버전 프로퍼티나 `build.gradle`(Gradle)의
    `sourceCompatibility`에서 Java 버전을 뽑는다. 둘 다 없으면(이 미니PJT의 Java 라이트
    리뷰처럼 실제 빌드 파일이 없는 경우) `None`을 반환한다."""
    for pom in root.rglob("pom.xml"):
        try:
            content = pom.read_text(encoding="utf-8")
        except OSError:
            continue
        for tag in ("maven.compiler.release", "maven.compiler.source", "java.version"):
            match = re.search(rf"<{tag}>\s*([^<\s]+)\s*</{tag}>", content)
            if match:
                return f"Java {match.group(1)}"
    for gradle in [*root.rglob("build.gradle"), *root.rglob("build.gradle.kts")]:
        try:
            content = gradle.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"sourceCompatibility\s*=?\s*['\"]?(?:JavaVersion\.VERSION_)?([\d._]+)['\"]?", content)
        if match:
            return f"Java {match.group(1).replace('_', '.')}"
    return None


# 언어 계열 -> 버전 감지 함수. 새 언어에 버전 표시를 추가하려면 여기에 감지 함수 하나만
# 등록하면 된다(다른 코드는 손대지 않는다) — `_LANGUAGE_ADAPTER_REGISTRY`와 같은 설계
# 원칙(조건 4)이다.
_VERSION_DETECTORS: dict[str, Callable[[Path], str | None]] = {
    "vue": _detect_vue_version,
    "java": _detect_java_version,
}


def _detect_display_name(family: str, root: Path) -> str:
    """리포트에 보여줄 이름을 만든다 — 실제 프로젝트 파일에서 버전을 감지할 수 있으면
    "Vue3"/"Java 1.8"처럼 버전까지, 감지할 신호가 없으면(예: `pyproject.toml`에 버전
    정보가 없는 Python, 또는 감지 함수가 아예 없는 언어) 계열 이름만 자본화해서 보여준다
    (사용자 요청, 2026-09-03 — "`exceptLanguages`는 버전 없이, 리포트는 버전을 특정")."""
    detector = _VERSION_DETECTORS.get(family)
    if detector:
        version = detector(root)
        if version:
            return version
    return family.capitalize()


def _classify_languages(
    detected: set[str], except_languages: set[str], source_root: Path
) -> list[tuple[str, str, str]]:
    """감지된 언어를 이름 알파벳 순으로 (계열 이름, 상태, 표시 이름) 3튜플로 정리한다.

    - **계열 이름**(`name`): `exceptLanguages`/`_LANGUAGE_ADAPTER_REGISTRY` 매칭에 쓰는
      버전 무관 이름("vue"/"java"/"python") — `exceptLanguages: [java]`라고 쓰면 실제
      감지된 Java 버전(1.8/17/21 등)과 무관하게 전부 제외된다.
    - **표시 이름**(`display`): 리포트에 실제로 보여줄, 프로젝트에서 실측한 버전이 반영된
      이름("Vue3"/"Java 1.8") — `_detect_display_name()` 참고.
    - `"unsupported"`: `_LANGUAGE_ADAPTER_REGISTRY`에 어댑터가 없어 애초에 점검이 불가능
      (리포트에 "점검불가"로 표시).
    - `"excepted"`: 어댑터는 있지만 `config.yaml`의 `exceptLanguages`에 들어 있어 이번엔
      의도적으로 제외(리포트에 "점검제외"로 표시).
    - `"active"`: 실제로 점검 대상.

    **(결정, 2026-09-03 — 사용자 질문 계기로 발견)** `except_languages`를 소문자로
    정규화한다. `detected`(`_detect_languages()`가 만드는 언어 이름)는 항상 소문자
    ("java"/"python"/"vue" 등)인데, `config.yaml`의 `exceptLanguages`는 사람이 직접
    타이핑하는 값이라 `Java`/`JAVA`처럼 대소문자가 섞일 수 있다 — 정규화 없이는
    `exceptLanguages: [Java]`가 조용히 아무 효과도 없이 무시되고(에러 없이 그냥
    "active"로 남음) 여전히 점검 대상에 포함되는 실제 버그가 있었다(실측 재현
    확인: `_classify_languages({'java'}, {'Java'}, ...)` → `active`로 나옴). 대소문자
    무관하게 항상 의도대로 제외되도록 여기서 한 번만 정규화한다.
    """
    except_languages = {name.lower() for name in except_languages}
    statuses: list[tuple[str, str, str]] = []
    for name in sorted(detected):
        display = _detect_display_name(name, source_root)
        if name not in _LANGUAGE_ADAPTER_REGISTRY:
            statuses.append((name, "unsupported", display))
        elif name in except_languages:
            statuses.append((name, "excepted", display))
        else:
            statuses.append((name, "active", display))
    return statuses


# 한 번만 계산해 재사용한다(파일시스템 재스캔 방지) — `PROJECT_SOURCE_ROOT`도
# `tools.py`에서 이미 한 번만 계산된 값이다.
LANGUAGE_STATUSES: list[tuple[str, str, str]] = _classify_languages(
    _detect_languages(PROJECT_SOURCE_ROOT), set(load_except_languages()), PROJECT_SOURCE_ROOT
)


def _resolve_adapters_from_config() -> list[tuple[str, "LanguageAdapter"]]:
    """자동 감지되고 `exceptLanguages`에 없는 지원 언어들의 (계열 이름, 어댑터) 목록을
    반환한다. 이름을 함께 넘기는 이유는 `CombinedAdapter`가 실행 중 실패한 언어를
    구분해 기록해야 하기 때문이다(아래 "런타임 점검 실패 추적" 참고)."""
    return [
        (name, _LANGUAGE_ADAPTER_REGISTRY[name]) for name, status, _ in LANGUAGE_STATUSES if status == "active"
    ]


# ---------------------------------------------------------------------------
# 런타임 점검 실패 추적 (2026-09-04, 사용자 요청) — 어댑터가 연결은 돼 있지만(활성 상태)
# 실행 중 실제로 실패하는 경우(예: npm 레지스트리 간헐적 장애로 `Vue3Adapter.run_security()`
# 가 재시도 끝에 `RuntimeError`를 던지는 경우)를 위한 것이다. `LANGUAGE_STATUSES`는
# 모듈 로드 시점에 파일 감지만으로 한 번 계산되는 정적 값이라 이런 실행 중 실패를 담을 수
# 없다 — 이건 그 살아있는(요청마다 바뀔 수 있는) 대응물이다. 언어별로 캐싱된 어댑터
# 싱글턴(`vue3_adapter` 등)이 서버 프로세스 생애 동안 재사용되는 것과 같은 원리로, 한 번
# 성공하면(그 언어 어댑터의 내부 캐시가 채워지면) 그 뒤로는 다시 실패할 일이 없고, 실패한
# 동안은 다음 스캔 때마다 다시 시도되므로 별도의 "요청마다 초기화" 로직이 필요 없다 — 최신
# 시도의 성공/실패를 그대로 반영하는 것 자체가 "현재 상태"다.
# ---------------------------------------------------------------------------

_SCAN_FAILURES: dict[str, dict[str, str]] = {}
_SCAN_FAILURES_LOCK = threading.Lock()


def _record_scan_outcome(name: str, category: str, error: BaseException | None) -> None:
    """`(언어, 카테고리)` 조합의 최신 점검 결과를 기록한다. 성공하면(`error is None`)
    이전에 남아 있던 실패 기록을 지운다 — 리포트는 항상 "지금 시점 기준" 실패만 보여준다."""
    with _SCAN_FAILURES_LOCK:
        if error is None:
            _SCAN_FAILURES.get(name, {}).pop(category, None)
        else:
            _SCAN_FAILURES.setdefault(name, {})[category] = str(error)


def get_scan_failures() -> list[dict[str, str]]:
    """현재 시점 기준 점검 실패 중인 `(language, category, reason)` 목록을 반환한다."""
    with _SCAN_FAILURES_LOCK:
        return [
            {"language": name, "category": category, "reason": reason}
            for name, categories in _SCAN_FAILURES.items()
            for category, reason in categories.items()
        ]


# ---------------------------------------------------------------------------
# Finding 데이터 모델 (전체설계 4-1절의 3일 축소판, CLAUDE.md 참고)
# ---------------------------------------------------------------------------


class ReferenceDoc(BaseModel):
    """RAG로 검색한 근거 문서 조각."""

    doc_id: str
    text: str


class Finding(BaseModel):
    """코드 품질 점검 결과 한 건.

    `category`는 단일 값입니다(전체설계의 `tags` 배열 방식 아님, 조건 10).
    """

    id: str
    category: Literal["security", "error", "performance"]
    file: str
    line: int | None = None
    severity: Literal["high", "medium", "low"]
    tool: str
    rule: str
    summary: str
    detail: str
    group_id: str | None = None
    status: Literal["open", "wont_fix"] = "open"
    reference: ReferenceDoc | None = None


_CATEGORY_PREFIX = {"security": "SEC", "error": "ERR", "performance": "PERF"}

# 도구마다 심각도 어휘가 달라서(npm audit: critical/high/moderate/low/info, eslint: 1/2 등)
# Finding에 들어갈 때는 항상 high/medium/low 세 단계로 정규화한다.
_SEVERITY_MAP = {
    "critical": "high",
    "high": "high",
    "moderate": "medium",
    "medium": "medium",
    "low": "low",
    "info": "low",
    # pylint의 메시지 분류(`type` 필드) — npm audit/eslint 어휘와 겹치지 않아 원래
    # 빠져 있었다(결정, 2026-09-04 — 소스 전체 재검증 중 발견). 이 키들이 없으면
    # pylint가 내는 모든 finding이 아래 기본값("medium")으로만 뭉개져, 실제로는
    # error/fatal급 문제가 convention급과 똑같이 "medium"으로 리포트에 나온다.
    "error": "high",
    "fatal": "high",
    "warning": "medium",
    "refactor": "low",
    "convention": "low",
}


def _normalize_severity(raw_severity: Any) -> Literal["high", "medium", "low"]:
    """도구별 심각도 어휘를 high/medium/low 세 단계로 정규화한다."""
    return _SEVERITY_MAP.get(str(raw_severity).lower(), "medium")


# ---------------------------------------------------------------------------
# mask_pii: 시크릿 마스킹 가드레일 (조건 9, 1차 적용 지점)
# ---------------------------------------------------------------------------

# AWS 액세스 키 형식(실제 키: AKIA + 대문자/숫자 16자, 이 프로젝트 더미 값처럼 언더스코어가
# 섞인 "AKIA_DUMMY_EXAMPLE1234" 같은 표기도 함께 잡도록 언더스코어까지 허용한다.
_AWS_ACCESS_KEY_PATTERN = re.compile(r"AKIA[A-Z0-9_]{10,}")

# "...SECRET... = "값""처럼 변수 이름에 secret/password/token/api_key가 들어간 대입문에서
# 오른쪽 문자열 리터럴을 가린다(Java/JS/Python 스타일 대입문에 공통으로 걸리도록 일반화).
# **(결정, 2026-09-03 — 전체 코드베이스 점검 중 발견)** `=`뿐 아니라 `:`도 구분자로
# 허용한다 — bandit의 B105(hardcoded_password_string) 메시지 자체가 "Possible hardcoded
# password: 'admin1234'"처럼 대입 연산자 없이 콜론으로 값을 표기하는 것을 실측으로
# 확인했는데, 원래 `=`만 허용하던 패턴이 이 형태를 놓치는 것을 발견해 고쳤다 — 도구가
# 만든 메시지 안에 있는 더미 값조차 리포트에 그대로 노출되면 안 된다는 조건 9 원칙을
# 실제 도구 출력에서도 지켜야 한다.
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)((?:secret|password|token|api[_-]?key)[a-zA-Z0-9_]*)\s*[:=]\s*[\"']([^\"']{6,})[\"']"
)


def mask_pii(text: str) -> str:
    """하드코딩된 것으로 보이는 자격증명을 텍스트에서 가린다(가드레일, 조건 9).

    `mask_pii`는 LLM 프롬프트 구성 시점(도구 원시 출력 -> Finding 변환 직전)과 리포트 저장
    직전, 두 번 적용한다. 여기서는 첫 번째 적용 지점(변환 시점)을 구현한다 — 두 번째(리포트
    저장 직전)는 2일차 리포트 저장 로직에서 이 함수를 그대로 재사용한다.
    """
    if not text:
        return text
    masked = _AWS_ACCESS_KEY_PATTERN.sub("***MASKED_AWS_ACCESS_KEY***", text)
    masked = _SECRET_ASSIGNMENT_PATTERN.sub(r'\1 = "***MASKED_SECRET***"', masked)
    return masked


def _sanitize_raw_findings(raw_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """대화형 Agent의 `scan_*` 도구가 LLM에 그대로 넘기는 원시 발견 목록에 `mask_pii`와
    심각도 정규화(`_normalize_severity`)를 적용한다.

    **(결정, 2026-09-03 — 2차 자체평가로 실제 발견)** 이 두 가지는 지금까지
    `collect_findings()`가 부르는 `raw_findings_to_findings()`(정적 리포트 경로)에만
    연결돼 있었다. 하지만 `make_security_agent`/`make_error_agent`/`make_performance_agent`
    의 `scan_*` 도구는 `adapter.run_*()`가 반환한 원시 딕셔너리를 마스킹·정규화 없이 그대로
    LLM에 넘기고 있었다 — 즉 대화형 `POST /query` 경로에는 두 가지 모두 실제로 적용된 적이
    없었다. bandit이 콜론 형식으로 내는 하드코딩 비밀번호 메시지가 대화형 응답에 원문
    그대로("admin1234") 노출되는 것을 2차 자체평가(`Q15`)에서 먼저 발견해 마스킹을
    연결했는데, 같은 평가에서 `Q23`(Vue3 minimist)이 npm audit 원본 등급 그대로
    "CRITICAL"이라고 답한 것을 보고 심각도 정규화도 같은 경로 문제라는 것을 추가로
    발견해 함께 연결했다.
    """
    return [
        {
            **raw,
            "message": mask_pii(str(raw.get("message", ""))),
            "severity": _normalize_severity(raw.get("severity")),
        }
        for raw in raw_findings
    ]


# ---------------------------------------------------------------------------
# 원시 어댑터 출력 -> Finding 리스트 변환
# ---------------------------------------------------------------------------


def raw_findings_to_findings(
    raw_findings: list[dict[str, Any]],
    category: Literal["security", "error", "performance"],
) -> list[Finding]:
    """언어 어댑터가 반환한 원시 딕셔너리 리스트를 `Finding` 리스트로 변환한다.

    이 함수가 "도구 원시 출력 -> Finding 변환" 시점이라, 여기서 `mask_pii`를 먼저 적용한다
    (조건 9: LLM에 보내기 전 1차 마스킹). ID는 이 배치 안에서 카테고리 접두어 + 일련번호로
    붙인다 — 여러 어댑터 결과를 합칠 때의 전역 ID는 `CombinedAdapter`(2일차 1번)가 호출
    시점에 이미 하나의 리스트로 합쳐주므로 이 함수 입장에서는 항상 "배치 하나"만 본다.
    파일 단위 그룹핑(`group_id`)은 `assign_group_ids()`(2일차 2번)가 이 함수의 결과에
    이어서 적용한다.
    """
    prefix = _CATEGORY_PREFIX[category]
    findings: list[Finding] = []
    for i, raw in enumerate(raw_findings, start=1):
        message = mask_pii(str(raw.get("message", "")))
        findings.append(
            Finding(
                id=f"{prefix}-{i}",
                category=category,
                file=raw.get("file") or "",
                line=raw.get("line"),
                severity=_normalize_severity(raw.get("severity")),
                tool=raw["tool"],
                rule=raw["rule"],
                summary=message,
                detail=message,
                status="open",
            )
        )
    return findings


def assign_group_ids(findings: list[Finding]) -> list[Finding]:
    """같은 `file`에서 나온 Finding들을 파일 단위로 그룹핑한다(2일차 2번, 조건 2).

    규칙 기반 그룹핑만 합니다 — 함수 단위로 더 세분화하거나 "왜 같이 묶였는지" LLM 요약을
    붙이는 "연결점"은 만들지 않습니다(조건 2, 전면 제외). 카테고리를 가리지 않고 같은
    파일이면 하나의 그룹으로 묶어, 한 파일에 보안·오류·성능 발견이 섞여 있어도 리포트에서
    같이 보이게 합니다. 그룹 ID는 파일이 처음 등장한 순서대로 `G-1`, `G-2`, ...로 붙입니다.
    """
    group_ids_by_file: dict[str, str] = {}
    for finding in findings:
        if finding.file not in group_ids_by_file:
            group_ids_by_file[finding.file] = f"G-{len(group_ids_by_file) + 1}"
        finding.group_id = group_ids_by_file[finding.file]
    return findings


def collect_findings(adapter: "LanguageAdapter") -> list[Finding]:
    """어댑터의 보안/오류/성능 원시 결과를 전부 Finding으로 변환하고 파일 단위로 그룹핑한다.

    카테고리별로 `raw_findings_to_findings()`를 호출해 `SEC-n`/`ERR-n`/`PERF-n` ID를 먼저
    부여한 뒤, 세 카테고리를 합친 전체 리스트에 `assign_group_ids()`로 `group_id`를 매기고
    (2일차 2번), `attach_rag_references()`로 미리 대응이 확정된 규칙에 한해 RAG 근거를
    붙인다(2일차 4번 — 전체 파이프라인을 실제로 돌려보고 나서 발견한 빠진 연결). 이어서
    `attach_db_evidence()`로 N+1 finding에 DB 실행계획/부하 근거를(5-1-B), 마지막으로
    `attach_live_probe_evidence()`로 IDOR/N+1 finding에 실제 HTTP 프로빙 근거를(5-2)
    `detail`에 덧붙인다.
    """
    findings: list[Finding] = []
    findings += raw_findings_to_findings(adapter.run_security(), "security")
    findings += raw_findings_to_findings(adapter.run_error(), "error")
    findings += raw_findings_to_findings(adapter.run_performance(), "performance")
    findings = assign_group_ids(findings)
    findings = attach_rag_references(findings)
    findings = attach_db_evidence(findings)
    return attach_live_probe_evidence(findings)


# 규칙 이름에 포함된 키워드 -> 그 키워드에 맞는 검색 질의. `security_agent`가 이미 실측으로
# 확인한(1일차 5번) "IDOR -> auth_idor_checklist", "N+1 -> load_risk_checklist" 대응을 그대로
# 재사용한다 — 임의의 유사도만으로 붙이면 무관한 문서를 인용하는 환각 문제가 재발하므로(1일차
# 5번에서 실제로 겪음), 미리 대응이 검증된 키워드에만 한정한다. **(결정, 5-1-A 3번 재검증
# 중 발견)** 처음엔 규칙 이름 전체를 정확히 일치시켰는데(예: `idor-missing-ownership-check`),
# 같은 프롬프트로 다시 호출했더니 LLM이 N+1 규칙 이름을 `n-plus-one-query-in-loop`가 아니라
# `n-plus-one-query`로 살짝 다르게 지어내 정확히 일치하지 않아 근거가 안 붙는 것을 실측으로
# 확인했다 — CLAUDE.md에 "경험적으로는 안정적이나 형식적 보장은 아니다"라고 미리 남겨둔
# 우려가 실제로 재발한 것이다. 전체 일치 대신 **규칙 이름에 키워드가 포함되는지**로 완화해
# 이런 사소한 이름 변형에 견고하게 했다 — 그래도 "무관한 규칙엔 검색 자체를 안 한다"는
# 원칙은 그대로 지킨다(키워드가 없는 규칙은 여전히 건너뜀).
_RAG_REFERENCE_KEYWORDS: list[tuple[str, str]] = [
    ("idor", "다른 사람의 리소스 ID로 조회할 때 소유권 검증이 없는 IDOR 취약점"),
    ("n-plus-one", "반복문 안에서 매번 쿼리를 던지는 N+1 성능 문제"),
]


def attach_rag_references(findings: list[Finding]) -> list[Finding]:
    """미리 대응이 확정된 규칙(IDOR/N+1)에 한해 Finding에 RAG 체크리스트 근거를 붙인다.

    `security_agent`의 자연어 답변에는 이미 `search_guides` 도구로 근거가 인용되지만(1일차
    5번), 그건 LLM 대화 메시지 안에만 있어 `report.json`/API `contexts`가 실제로 쓰는
    구조화된 `Finding.reference` 필드에는 반영되지 않았다 — 전체 파이프라인을 실제로 돌려본
    뒤에 발견했다(2일차 4번). `_RAG_REFERENCE_KEYWORDS`에 없는 규칙(Vue3의 `no-eval` 등)에는
    검색 자체를 하지 않는다 — 1일차 5번에서 확인한 "무관하면 인용하지 않는다" 원칙을
    구조화된 데이터에도 동일하게 적용한다.
    """
    for finding in findings:
        rule_lower = finding.rule.lower()
        query = next(
            (query for keyword, query in _RAG_REFERENCE_KEYWORDS if keyword in rule_lower),
            None,
        )
        if query is None:
            continue
        results = retriever.search(query, k=1)
        if results:
            finding.reference = ReferenceDoc(doc_id=results[0]["doc_id"], text=results[0]["text"])
    return findings


# OrderService.java의 N+1이 실제로 던지는 쿼리와 같은 테이블·컬럼(order_items.order_id) —
# `_PERFORMANCE_REVIEW_FILES`/`_RAG_REFERENCE_KEYWORDS`와 같은 원칙으로, 유일한 N+1
# 케이스(Java)에 한정된 하드코딩이다. LLM이 지어낸 자유 텍스트에서 테이블명을 정규식으로
# 뽑아내는 방식은 RAG 참조 매칭에서 이미 겪은 것과 같은 종류의 취약성이라 피한다.
_N_PLUS_ONE_EXPLAIN_QUERY = "SELECT product_name FROM order_items WHERE order_id = 1"


def attach_db_evidence(findings: list[Finding]) -> list[Finding]:
    """N+1 finding에 한해 DB 실행계획(인덱스 유무)과 부하 프로파일 근거를 `detail`에
    덧붙인다(5-1-B, CLAUDE.md 10-B절 "Finding 연동" — 새 필드 없이 기존 `detail`에 담는다).

    이렇게 하지 않으면 `report.md`/`report.json`(대화형 질의 없이 생성되는 정적 산출물)에는
    DB/부하 근거가 전혀 반영되지 않는다 — `performance_agent`의 도구 기반 추론(아래
    `make_performance_agent`)은 대화형 질의에만 답하기 때문이다(실측 확인: 대화형 답변은
    이미 정확했지만 `report.md`에는 이 근거가 없다는 것을 이 단계에서 뒤늦게 발견했다).
    """
    if not any("n-plus-one" in f.rule.lower() for f in findings):
        return findings
    plan = db_adapter.explain_query(_N_PLUS_ONE_EXPLAIN_QUERY)
    plan_text = "; ".join(str(row.get("detail", row)) for row in plan)
    is_full_scan = "SCAN" in plan_text.upper()
    profile = load_load_profile()
    evidence = (
        f" [DB 실행계획: {plan_text or '조회 결과 없음'} — "
        f"{'풀스캔 확인(인덱스 없음)' if is_full_scan else '인덱스 탐색 확인'}. 예상 부하: 동시 "
        f"사용자 {profile.get('expected_concurrent_users')}명, 분당 요청 "
        f"{profile.get('requests_per_minute')}건]"
    )
    for finding in findings:
        if "n-plus-one" in finding.rule.lower():
            finding.detail += evidence
    return findings


def attach_live_probe_evidence(findings: list[Finding]) -> list[Finding]:
    """IDOR/N+1 finding에 한해 실제 HTTP 프로빙(모의해킹·부하테스트) 결과를 `detail`에
    덧붙인다(5-2, 전체설계 10-0절 최소 실증, CLAUDE.md 10-C절).

    `attach_db_evidence()`와 같은 이유(정적 산출물에도 반영 필요)로 존재한다.
    `config.yaml`의 `live_probe`가 꺼져 있으면 스테이징 서버를 띄우는 부수효과 없이 그대로
    반환한다 — 대화형 도구(`make_security_agent`/`make_performance_agent`의
    `enable_live_pentest`/`enable_live_load_test`)와 같은 `probe_idor_vulnerability()`/
    `run_concurrent_load_test()`를 그대로 재사용해 로직이 하나로 유지된다.
    """
    if not is_live_probe_enabled():
        return findings

    if any("idor" in f.rule.lower() for f in findings):
        pentest_findings = probe_idor_vulnerability()
        if pentest_findings:
            evidence = " [실제 HTTP 프로빙: " + "; ".join(f["message"] for f in pentest_findings) + "]"
            for finding in findings:
                if "idor" in finding.rule.lower():
                    finding.detail += evidence

    if any("n-plus-one" in f.rule.lower() for f in findings):
        load_test_findings = run_concurrent_load_test(load_load_profile().get("expected_concurrent_users", 50))
        if load_test_findings:
            evidence = " [실제 부하테스트: " + "; ".join(f["message"] for f in load_test_findings) + "]"
            for finding in findings:
                if "n-plus-one" in finding.rule.lower():
                    finding.detail += evidence

    return findings


# ---------------------------------------------------------------------------
# 전문 Agent 3개 (1일차 4번)
# ---------------------------------------------------------------------------


# 3일차 1번(round1_report.md 기반 개선)에서 실측으로 잡은 두 가지 정직성 문제에 대한
# 공통 지침 — 3개 Agent 프롬프트와 폴백 지시문(아래 _*_FALLBACK_INSTRUCTIONS) 양쪽에
# 덧붙여 한 곳만 고치면 전부 반영되게 한다. (1) Q7/Q9: 질문이 이 프로젝트 범위 밖(다른
# 언어·다른 프로젝트)을 가리켜도 실제로는 항상 Vue3+Java만 스캔하면서 마치 그 대상을
# 점검한 것처럼 결과를 지어내는 문제 — "먼저 정직하게 범위 밖임을 밝히라"로 수정.
# (2) Q10: "지금 바로 반영해줘" 요청에 거절이 약해서(처음엔 "수정 가이드를 안내하겠다"는
# 식으로 여전히 도와주겠다는 뉘앙스가 남는 것을 실측으로 확인) "요청 자체를 명확히
# 거절하라"로 더 강하게 수정.
# **(결정, 5-1-A 3번 연동 확인 중 발견)** 처음엔 "Vue3/Java"를 문자열에 직접 박아
# 넣었는데, Python을 config.yaml에 추가하자마자 error_agent가 실제로는 Python 발견을
# 정확히 보고하면서도 그 답변 안에서 "Python은 이 프로젝트의 점검 범위를 벗어난 것"이라고
# 스스로 모순되게 말하는 것을 실측으로 확인했다 — 하드코딩된 언어 목록이 실제 활성 어댑터와
# 어긋난 것이다. **(2026-09-03 갱신)** 이제 "무엇이 활성 언어인가"의 단일 진실 공급원은
# `config.yaml`의 정적 목록이 아니라 `LANGUAGE_STATUSES`(자동 감지 + `exceptLanguages`
# 반영 결과)이므로, 이 가드레일 문구도 거기서 `"active"`인 것만 읽어 항상 최신으로
# 유지한다 — 새 언어가 감지되거나 `exceptLanguages`가 바뀌어도 이 문구를 따로 고칠
# 필요가 없다.
_ACTIVE_LANGUAGES_LABEL = "/".join(
    display for name, status, display in LANGUAGE_STATUSES if status == "active"
)

_SCOPE_AND_ACTION_GUARDRAIL = (
    f"이 시스템이 실제로 점검하는 대상은 이 프로젝트 안의 더미 {_ACTIVE_LANGUAGES_LABEL} "
    "소스뿐입니다 — 질문이 그 외의 언어나 이 프로젝트 밖의 다른 프로젝트·회사 코드를 "
    "가리키면, 스캔 결과를 그 질문에 억지로 끼워 맞추지 말고 \"이 시스템은 현재 "
    f"{_ACTIVE_LANGUAGES_LABEL}만 지원하며 그 요청은 점검 대상이 아니다\"라고 먼저 정직하게 "
    "밝히세요. 그리고 이 시스템은 점검(리포트 생성)까지만 하며 실제 코드 수정·반영 기능이 "
    "아예 없습니다 — 사용자가 특정 발견 사항을 지금 코드에 반영·수정해 달라고 요청하면, "
    "그 요청 자체를 \"이 시스템은 점검까지만 지원하고 실제 코드 수정 기능은 없다\"고 명확히 "
    "밝히며 정중히 거절하세요. \"수정 가이드를 안내해드리겠다\", \"파일 경로를 알려주시면 "
    "도와드리겠다\"처럼 수정을 돕겠다는 뉘앙스로 답하지 말고, 발견 내용은 리포트로 이미 "
    "제공했으니 실제 반영은 개발팀이 별도로 진행해야 한다고만 안내하세요."
)

# **(결정, 2026-09-03 — 2차 자체평가로 실제 발견)** 2차 자체평가에서 보안 Agent가
# scan_security가 실제로 반환하지 않은 "OrderService.java의 SQL Injection"을 지어내
# 보고한 사례(Q4)가 나왔다 — OrderService.java의 실제 발견은 N+1 성능 문제뿐이다. 기존
# "도구 판정을 다시 평가하거나 의심하지 말라"만으로는 "목록에 없는 새 항목을 추가하지
# 말라"는 것까지 충분히 막지 못한 것으로 보여, 이 문구를 세 카테고리 Agent 프롬프트에
# 공통으로 명시적으로 추가한다.
_NO_FABRICATION_GUARDRAIL = (
    " 도구가 반환한 목록에 없는 파일·항목·취약점 유형을 새로 지어내 답변에 추가하지 "
    "마세요 — 도구 결과에 실제로 있는 것만 그대로 요약하세요."
)


def make_security_agent(adapter: LanguageAdapter, enable_live_pentest: bool = False) -> CompiledStateGraph:
    """보안 전문 Agent를 만든다.

    `adapter`가 어떤 언어(Vue3/Java)인지는 이 함수도, Agent 자신도 모른다 — `run_security()`
    만 호출한다(조건 4). 도구 판정을 그대로 신뢰하고, LLM은 해석·설명만 한다는 원칙(3절)에
    따라 프롬프트에서도 "재판단하지 말라"고 명시한다.

    `enable_live_pentest=True`면(5-2, CLAUDE.md 10-C절) IDOR류 발견을 실제 HTTP 요청으로
    살아있는 상태에서 검증하는 `run_idor_pentest_probe` 도구를 추가로 준다 — 전체설계
    10-0절 "Agent가 직접 수행"의 기본 경로(전용 도구 없이 표준 HTTP 클라이언트로 직접 요청).
    """

    @tool
    def scan_security() -> list[dict[str, Any]]:
        """이 프로젝트의 보안 관점 발견 목록(정적분석 결과 또는 코드 리뷰 결과)을 가져온다."""
        return _sanitize_raw_findings(adapter.run_security())

    @tool
    def search_guides(query: str) -> list[dict[str, str]]:
        """보안 가이드 체크리스트 문서에서 질의와 관련된 근거 조각을 검색한다."""
        return retriever.search(query)

    tools: list[Any] = [scan_security, search_guides]
    live_pentest_instructions = ""
    if enable_live_pentest:

        @tool
        def run_idor_pentest_probe() -> list[dict[str, Any]]:
            """스테이징 서버(로컬 전용, data/staging_app)에 실제 GET 요청을 보내 IDOR
            (소유권 검증 누락)을 살아있는 상태에서 검증한다. 상태를 바꾸지 않는 읽기 전용
            프로빙만 수행한다."""
            return probe_idor_vulnerability()

        tools.append(run_idor_pentest_probe)
        live_pentest_instructions = (
            " scan_security에서 IDOR(소유권 검증 누락)류 발견이 있고 사용자가 그게 실제로 "
            "악용 가능한지 물으면, run_idor_pentest_probe로 실제 요청을 보내 다른 사용자의 "
            "리소스가 실제로 노출되는지 직접 검증하고 그 결과를 근거로 포함하세요."
        )

    prompt = (
        "당신은 보안 전문 조사 Agent입니다. 답변하기 전에 반드시 scan_security 도구를 "
        "호출해 보안 관점 발견 목록을 가져오세요. 도구가 이미 내린 판정(심각도, 규칙 위반 "
        "여부)을 다시 평가하거나 의심하지 말고 그대로 신뢰하세요. 당신의 역할은 그 결과를 "
        "사람이 이해하기 쉽게 요약·설명하는 것으로 한정합니다. 발견된 것이 없으면 없다고 "
        "정직하게 답하세요. search_guides 도구로 인증/인가·IDOR 체크리스트에서 관련 근거를 "
        "찾을 수 있는 항목(예: 소유권 검증 누락, 접근 제어 이슈)에 대해서만 검색해 근거 "
        "문서(doc_id)를 답변에 밝히세요. 검색 결과가 그 항목과 실제로 관련 없으면(예: "
        "라이브러리 취약점·eval 사용처럼 체크리스트 주제와 무관한 경우) 억지로 인용하지 말고 "
        "조용히 무시하세요 — 관련 없는 근거를 붙이는 것은 근거를 아예 안 붙이는 것보다 "
        "나쁩니다." + live_pentest_instructions + _NO_FABRICATION_GUARDRAIL + " " + _SCOPE_AND_ACTION_GUARDRAIL
    )
    return create_react_agent(_report_llm(), tools=tools, prompt=prompt)


def make_error_agent(adapter: LanguageAdapter) -> CompiledStateGraph:
    """오류(버그 유발 패턴) 전문 Agent를 만든다. `adapter`는 `run_error()`만 호출한다(조건 4)."""

    @tool
    def scan_error() -> list[dict[str, Any]]:
        """이 프로젝트의 오류/버그 유발 관점 발견 목록을 가져온다."""
        return _sanitize_raw_findings(adapter.run_error())

    prompt = (
        "당신은 오류(버그 유발 패턴) 전문 조사 Agent입니다. 답변하기 전에 반드시 scan_error "
        "도구를 호출해 발견 목록을 가져오세요. 도구 판정을 그대로 신뢰하고, 결과를 사람이 "
        "이해하기 쉽게 요약·설명하는 역할만 합니다. 발견된 것이 없으면 없다고 정직하게 "
        "답하세요." + _NO_FABRICATION_GUARDRAIL + " " + _SCOPE_AND_ACTION_GUARDRAIL
    )
    return create_react_agent(_report_llm(), tools=[scan_error], prompt=prompt)


def make_performance_agent(
    adapter: LanguageAdapter,
    db_adapter: DbAdapter | None = None,
    load_profile: dict[str, Any] | None = None,
    enable_live_load_test: bool = False,
) -> CompiledStateGraph:
    """성능 전문 Agent를 만든다. `adapter`는 `run_performance()`만 호출한다(조건 4).

    `db_adapter`/`load_profile`을 주면(5-1-B, CLAUDE.md 10-B절) DB 스키마·실행계획 조회
    도구를 추가로 붙여, N+1 같은 코드 패턴 의심을 "이 부하 조건에서 실제로 병목"이라는
    근거 있는 판단으로 확장한다 — 둘 다 없으면(기본값) 기존 5-2일차 동작 그대로다.

    `enable_live_load_test=True`면(5-2, CLAUDE.md 10-C절) 스테이징 서버에 실제 동시 요청을
    보내 지연·에러율을 직접 측정하는 `run_live_load_test` 도구를 추가로 준다 — 전체설계
    10-0절 "Agent가 직접 수행"의 성능 축.
    """

    @tool
    def scan_performance() -> list[dict[str, Any]]:
        """이 프로젝트의 성능 저하 패턴 발견 목록을 가져온다."""
        return _sanitize_raw_findings(adapter.run_performance())

    tools: list[Any] = [scan_performance]
    db_instructions = ""

    if db_adapter is not None:

        @tool
        def get_db_schema() -> list[dict[str, Any]]:
            """DB 테이블별 컬럼과 인덱스 목록을 조회한다(읽기 전용)."""
            return db_adapter.get_schema()

        @tool
        def explain_query(sql: str) -> list[dict[str, Any]]:
            """SELECT문의 실행계획을 EXPLAIN QUERY PLAN으로 조회한다(읽기 전용, SELECT문만
            허용 — SELECT가 아니면 거부된다)."""
            return db_adapter.explain_query(sql)

        tools += [get_db_schema, explain_query]
        db_instructions = (
            " scan_performance에서 N+1처럼 반복 쿼리 패턴이 의심되면, 그 finding의 message에 "
            "적힌 정확한 테이블 이름과 WHERE 절 컬럼을 그대로 사용하세요(다른 테이블을 "
            "추측해서 조회하지 마세요) — get_db_schema로 그 테이블에 인덱스가 있는지 확인하고, "
            "explain_query로 message에 적힌 것과 같은 테이블·컬럼 조건의 SELECT문 실행계획을 "
            "조회해 실제로 풀스캔(SCAN)이 일어나는지 근거를 붙이세요 — 인덱스가 있거나 "
            "실행계획이 인덱스 탐색(SEARCH)이면 병목이 아니라고 정직하게 판단하세요."
        )

    load_instructions = ""
    if load_profile:
        load_instructions = (
            f" 이 서비스의 예상 부하는 동시 사용자 {load_profile.get('expected_concurrent_users')}"
            f"명, 분당 요청 수 {load_profile.get('requests_per_minute')}건입니다 — 풀스캔 근거가 "
            "확인된 쿼리는 이 부하 조건까지 함께 언급해 "
            "\"이 부하에서 실제로 위험하다\"는 식으로 판단 근거를 완성하세요."
        )

    live_load_test_instructions = ""
    if enable_live_load_test:

        @tool
        def run_live_load_test() -> list[dict[str, Any]]:
            """스테이징 서버(로컬 전용, data/staging_app)에 실제 동시 요청을 보내 부하
            상황에서의 p95 지연시간·에러율을 직접 측정한다(읽기 전용 GET, 동시 요청 수
            상한 있음)."""
            return run_concurrent_load_test(load_profile.get("expected_concurrent_users", 50) if load_profile else 50)

        tools.append(run_live_load_test)
        live_load_test_instructions = (
            " N+1 같은 병목이 코드·DB 근거로 의심되고 사용자가 실제 부하 상황에서도 그런지 "
            "물으면, run_live_load_test로 실제 동시 요청을 보내 지연시간·에러율을 직접 측정해 "
            "그 결과를 근거로 포함하세요."
        )

    prompt = (
        "당신은 성능 전문 조사 Agent입니다. 답변하기 전에 반드시 scan_performance 도구를 "
        "호출해 발견 목록을 가져오세요. 도구 판정을 그대로 신뢰하고, 결과를 사람이 이해하기 "
        "쉽게 요약·설명하는 역할만 합니다. 발견된 것이 없으면 없다고 정직하게 답하세요."
        + db_instructions
        + load_instructions
        + live_load_test_instructions
        + _NO_FABRICATION_GUARDRAIL
        + " "
        + _SCOPE_AND_ACTION_GUARDRAIL
    )
    return create_react_agent(_report_llm(), tools=tools, prompt=prompt)


# ---------------------------------------------------------------------------
# Supervisor: 3개 전문 Agent 병렬 실행 + 결과 취합 (2일차 1번)
# ---------------------------------------------------------------------------

# tool_use 병합 버그(2일차 7번)로 도구 호출 자체를 우회할 때 쓰는 폴백 지시문 — 각 Agent의
# 원래 프롬프트(1일차 4번)와 같은 "도구 판정을 그대로 신뢰, 재판단 금지" 원칙만 남기고
# 도구 호출 지시는 뺐다(폴백은 이미 결과를 프롬프트에 직접 받으므로).
_SECURITY_FALLBACK_INSTRUCTIONS = (
    "당신은 보안 전문 조사 Agent입니다. 도구가 이미 내린 판정(심각도, 규칙 위반 여부)을 "
    "다시 평가하거나 의심하지 마세요. " + _SCOPE_AND_ACTION_GUARDRAIL
)
_ERROR_FALLBACK_INSTRUCTIONS = (
    "당신은 오류(버그 유발 패턴) 전문 조사 Agent입니다. 도구가 이미 내린 판정을 다시 "
    "평가하거나 의심하지 마세요. " + _SCOPE_AND_ACTION_GUARDRAIL
)
_PERFORMANCE_FALLBACK_INSTRUCTIONS = (
    "당신은 성능 전문 조사 Agent입니다. 도구가 이미 내린 판정을 다시 평가하거나 의심하지 "
    "마세요. " + _SCOPE_AND_ACTION_GUARDRAIL
)
# 알려진 제약(5-1-B, CLAUDE.md 10-B절): 이 폴백 경로는 `_fallback_answer`(도구 없는 요약)를
# 타므로, `scan_performance`(코드 패턴)까지만 프롬프트에 들어가고 `db_adapter`의 스키마/
# 실행계획, 부하 프로파일 근거는 이 경로에서는 붙지 않는다(둘 다 이 함수 시그니처 밖의
# 별도 도구라서). tool_use 병합 버그가 실제로 발동해야만 영향 있는 드문 경로이고, DoD가
# 요구하는 "도구 판정을 그대로 신뢰"는 여전히 지켜지므로 이번 범위에서는 그대로 둔다.


class CombinedAdapter:
    """여러 언어 어댑터를 하나의 `LanguageAdapter`처럼 보이게 합친다.

    Supervisor가 `source` 루트에서 감지된(그리고 `exceptLanguages`에 없는) 언어를 몇 개든
    한 번에 조사할 수 있도록 쓴다 — 현재는 Vue3/Java/Python 3개지만, 몇 개의 어댑터가
    합쳐졌는지 3개 전문 Agent는 여전히 몰라도 된다(조건 4).

    **(결정, 2026-09-04 — 사용자 요청)** 언어별 원시 호출을 개별적으로 `try/except`한다.
    예전엔 언어 하나(예: npm 레지스트리 장애로 실패하는 Vue3)가 예외를 던지면 파이썬
    리스트 컴프리헨션이 그 자리에서 전체를 중단시켜, **정상 동작 중인 다른 언어(Java/
    Python)의 결과까지 통째로 사라지는** 실제 문제가 있었다. 이제는 언어 하나가 실패해도
    그 언어만 건너뛰고 나머지 언어 결과는 그대로 반환하며, 실패 사실은
    `_record_scan_outcome()`으로 별도 기록해 리포트에 "점검실패" 섹션으로 보여준다.
    """

    def __init__(self, adapters: list[tuple[str, LanguageAdapter]]) -> None:
        self._adapters = adapters

    def _run_category(self, category: str, method_name: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for name, adapter in self._adapters:
            try:
                findings.extend(getattr(adapter, method_name)())
            except Exception as exc:  # noqa: BLE001 - 한 언어의 실패가 다른 언어를 막지 않게 격리
                _record_scan_outcome(name, category, exc)
            else:
                _record_scan_outcome(name, category, None)
        return findings

    def run_security(self) -> list[dict[str, Any]]:
        return self._run_category("security", "run_security")

    def run_error(self) -> list[dict[str, Any]]:
        return self._run_category("error", "run_error")

    def run_performance(self) -> list[dict[str, Any]]:
        return self._run_category("performance", "run_performance")


class SupervisorState(TypedDict, total=False):
    """Supervisor 그래프의 상태.

    `trace`만 여러 노드가 동시에(병렬로) 이어붙여야 해서 `operator.add` 리듀서를 씁니다 —
    나머지 키는 노드마다 자기 키에만 쓰므로 리듀서가 필요 없습니다.
    """

    question: str
    security_answer: str
    error_answer: str
    performance_answer: str
    findings: list[Finding]
    trace: Annotated[list[dict[str, Any]], operator.add]
    answer: str


def _trace_from_agent_run(step_prefix: str, messages: list[Any], elapsed: float) -> list[dict[str, Any]]:
    """ReAct Agent의 메시지 기록에서 도구 호출 이벤트를 뽑아 trace로 만든다(패턴 #11).

    `tools.py`/`retriever.py`를 건드리지 않고도 "스캐너 호출"과 "RAG 검색" 이벤트를 잡을 수
    있다 — `create_react_agent`가 도구 호출 결과를 항상 `ToolMessage`로 메시지 목록에
    남기기 때문이다.

    **(결정, 2026-09-03, 사용자 요청)** 도구 출력 전문을 글자 수로 강제로 자르지 않는다 —
    이전엔 `[:200]`으로 잘라 내용이 중간에 끊겼다. `trace`는 관찰용(패턴 #11)이라 잘린
    내용보다 전체 내용이 더 유용하다.
    """
    events: list[dict[str, Any]] = [
        {"step": f"{step_prefix}:invoke", "input": None, "output": f"{elapsed:.1f}s"}
    ]
    for message in messages:
        if isinstance(message, ToolMessage):
            events.append(
                {
                    "step": f"{step_prefix}:tool:{message.name}",
                    "input": None,
                    "output": str(message.content),
                }
            )
    return events


def _is_tool_use_merge_bug(exc: Exception) -> bool:
    """langchain-core 0.3.86의 `merge_dicts()` 병렬 tool_use 병합 버그(1일차 4번 참고)인지
    확인한다 — `ValidationException: ... toolUse.name ...` 형태로 나타난다."""
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    code = response.get("Error", {}).get("Code")
    return code == "ValidationException" and "toolUse.name" in str(exc)


def _fallback_answer(instructions: str, raw_findings: list[dict[str, Any]]) -> str:
    """도구를 아예 바인딩하지 않고, 이미 가져온 원시 결과를 프롬프트에 직접 넣어 요약만
    시킨다.

    ReAct 도구 호출 경로가 tool_use 병합 버그로 계속 실패할 때의 우회책이다 — 도구 자체를
    안 쓰므로 `toolUse` 콘텐츠 블록이 만들어질 상황이 없어 이 버그가 구조적으로 발생할 수
    없다. 대신 `search_guides`(RAG 인용)는 이 경로에서 못 쓴다 — DoD의 "Finding에 RAG
    근거" 요건은 `attach_rag_references()`(2일차 4번)가 이미 구조화된 데이터 쪽에서
    독립적으로 채우므로 이 폴백과 무관하게 계속 충족된다.

    **(결정, 2026-09-04 — 소스 전체 재검증 중 발견)** `raw_findings`는 `_sanitize_raw_findings()`
    를 반드시 거쳐야 한다 — 이 함수를 거치지 않으면 `scan_*` 도구가 `_sanitize_raw_findings()`
    로 마스킹·정규화한 것과 달리, 이 폴백 경로만 하드코딩 비밀번호 같은 민감정보를 원문
    그대로 LLM 프롬프트에 넣고 그대로 답변에 노출시킬 수 있었다(2026-09-03 `_sanitize_
    raw_findings()`를 처음 도입할 때 이 폴백 경로가 빠져 있던 실제 회귀).
    """
    llm = _report_llm(disable_parallel_tool_use=False)
    findings_json = json.dumps(_sanitize_raw_findings(raw_findings), ensure_ascii=False, indent=2)
    prompt = (
        f"{instructions}\n\n아래는 이미 실행된 스캔 결과입니다(JSON). 이 판정을 다시 "
        "평가하거나 의심하지 말고 그대로 신뢰해, 사람이 이해하기 쉽게 요약·설명하세요. "
        f"목록이 비어 있으면 발견된 것이 없다고 정직하게 답하세요.\n\n{findings_json}"
    )
    return llm.invoke(prompt).content


def _run_category_agent(
    agent: CompiledStateGraph,
    question: str,
    fetch_raw: Callable[[], list[dict[str, Any]]],
    fallback_instructions: str,
    max_attempts: int = 2,
) -> dict[str, Any]:
    """ReAct Agent를 호출하고, tool_use 병합 버그로 계속 실패하면 도구 없는 요약으로
    대체한다.

    **(결정, 2026-09-02, 2일차 7번 1차 평가 중 발견)** `disable_parallel_tool_use`(1일차
    4번)는 `claude-sonnet-4-6`에서는 이 버그를 완전히 막았지만, 모델을 `claude-sonnet-4-5`
    계열로 바꾸자 같은 설정에도 불구하고 재발하는 것을 실측으로 확인했다. **처음엔 일시적인
    문제로 보고 재시도로 우회하려 했으나, 같은 질문으로 3번 재시도해도 매번 2~3초 만에
    똑같이 실패하는 것을 확인해 이 특정 질문·모델 조합에서는 결정적(deterministic)이라고
    결론지었다** — 재시도만으로는 해결되지 않는다. 근본 수정(langchain-core 업그레이드)은
    이미 0.3.x 최신판(0.3.86)이라 불가능하다(더 올리면 ragas가 깨짐, 4절 참고). 그래서 짧게만
    재시도(혹시 모를 일시적 사례 대비)하고, 그래도 안 되면 도구 호출 자체를 우회하는 폴백으로
    넘어간다.
    """
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            result = agent.invoke({"messages": [("user", question)]})
            return {"answer": result["messages"][-1].content, "messages": result["messages"], "fallback": False}
        except Exception as exc:  # noqa: BLE001 - 아래에서 버그 여부를 가려 재던짐
            if not _is_tool_use_merge_bug(exc):
                raise
            last_error = exc
    answer = _fallback_answer(fallback_instructions, fetch_raw())
    return {"answer": answer, "messages": [], "fallback": True, "error": str(last_error)}


def make_supervisor(adapters: list[tuple[str, LanguageAdapter]] | None = None) -> CompiledStateGraph:
    """Supervisor 그래프를 만든다 — 3개 전문 Agent를 병렬로 실행하고 결과를 취합한다.

    `adapters`를 지정하지 않으면 `LANGUAGE_STATUSES`(`config.yaml`의 `source` 루트에서
    자동 감지되고 `exceptLanguages`에 없는 언어, 전체설계 11-3절/12절 — 정식 개발에서는
    관리 화면이 이 파일을 대신 관리)를 `_LANGUAGE_ADAPTER_REGISTRY`에서 찾은 어댑터들과
    맞춰 `CombinedAdapter`로 합쳐 각 전문 Agent에 전달한다. 새 언어를 켜고 끄는 건
    `config.yaml`의 `source`/`exceptLanguages`만 고치면 되고, 이 함수나 3개 전문 Agent
    코드는 그대로다. RAG 근거
    주입은 이미 `make_security_agent` 안의 `search_guides` 도구가 처리하므로(1일차 5번),
    Supervisor는 여기서 추가 RAG 로직을 두지 않는다. `build_findings` 노드는 같은 `combined`
    어댑터의 원시 결과를 `collect_findings()`(2일차 2번)로 직접 `Finding` 리스트(ID+
    `group_id` 부여까지 끝난)로 만든다 — LLM 호출 없이 3개 Agent 노드와 병렬로 실행된다.
    """
    combined = CombinedAdapter(adapters if adapters is not None else _resolve_adapters_from_config())
    live_probe = is_live_probe_enabled()
    security_agent = make_security_agent(combined, enable_live_pentest=live_probe)
    error_agent = make_error_agent(combined)
    performance_agent = make_performance_agent(
        combined,
        db_adapter=db_adapter,
        load_profile=load_load_profile(),
        enable_live_load_test=live_probe,
    )

    def _node_trace(step_prefix: str, outcome: dict[str, Any], elapsed: float) -> list[dict[str, Any]]:
        if outcome["fallback"]:
            return [
                {
                    "step": f"{step_prefix}:fallback",
                    "input": None,
                    "output": f"tool_use 병합 버그로 도구 없는 요약 사용 ({elapsed:.1f}s): {outcome['error']}",
                }
            ]
        return _trace_from_agent_run(step_prefix, outcome["messages"], elapsed)

    def call_security(state: SupervisorState) -> dict[str, Any]:
        t0 = time.monotonic()
        outcome = _run_category_agent(
            security_agent, state["question"], combined.run_security, _SECURITY_FALLBACK_INSTRUCTIONS
        )
        elapsed = time.monotonic() - t0
        return {
            "security_answer": outcome["answer"],
            "trace": _node_trace("security_agent", outcome, elapsed),
        }

    def call_error(state: SupervisorState) -> dict[str, Any]:
        t0 = time.monotonic()
        outcome = _run_category_agent(
            error_agent, state["question"], combined.run_error, _ERROR_FALLBACK_INSTRUCTIONS
        )
        elapsed = time.monotonic() - t0
        return {
            "error_answer": outcome["answer"],
            "trace": _node_trace("error_agent", outcome, elapsed),
        }

    def call_performance(state: SupervisorState) -> dict[str, Any]:
        t0 = time.monotonic()
        outcome = _run_category_agent(
            performance_agent, state["question"], combined.run_performance, _PERFORMANCE_FALLBACK_INSTRUCTIONS
        )
        elapsed = time.monotonic() - t0
        return {
            "performance_answer": outcome["answer"],
            "trace": _node_trace("performance_agent", outcome, elapsed),
        }

    def build_findings(state: SupervisorState) -> dict[str, Any]:
        t0 = time.monotonic()
        findings = collect_findings(combined)
        elapsed = time.monotonic() - t0
        return {
            "findings": findings,
            "trace": [
                {"step": "build_findings", "input": None, "output": f"{len(findings)}건, {elapsed:.1f}s"}
            ],
        }

    def aggregate(state: SupervisorState) -> dict[str, Any]:
        """3개 Agent의 답변을 취합한다 — 도구 판정을 신뢰하는 원칙대로 재판단 없이 그대로 합친다.

        **(결정, 2026-09-02, 3일차 1번)** 3개 Agent는 계속 항상 병렬로 호출한다(질문 성격별로
        일부만 골라 호출하는 라우팅은 이번 미니PJT 범위에서 굳이 넣지 않기로 함 — 전체설계
        11절/10-0절 로드맵으로 남김). 다만 **섹션은 실제로 발견(Finding)이 있는 카테고리에만
        붙인다** — `state["findings"]`(2일차 2번, 이미 계산됨)를 기준으로 판단하므로 각
        Agent의 자연어 답변 문구를 파싱할 필요가 없다. 발견이 하나도 없는 카테고리는 섹션
        자체를 만들지 않는다(예: "보안 문제 없음" 같은 빈 섹션을 억지로 채우지 않음).
        """
        findings = state["findings"]
        category_sections = [
            ("security", "보안", state["security_answer"]),
            ("error", "오류", state["error_answer"]),
            ("performance", "성능", state["performance_answer"]),
        ]
        sections = [
            f"## {title}\n{category_answer}"
            for category, title, category_answer in category_sections
            if any(f.category == category for f in findings)
        ]
        answer = "\n\n".join(sections) if sections else "보안/오류/성능 어느 카테고리에서도 발견된 이슈가 없습니다."
        route_note = {
            "step": "supervisor:route",
            "input": state["question"],
            "output": "3개 전문 Agent 모두 호출(항상 병렬 실행) — 발견이 있는 카테고리 섹션만 답변에 포함",
        }
        return {"answer": answer, "trace": [route_note]}

    graph = StateGraph(SupervisorState)
    graph.add_node("call_security", call_security)
    graph.add_node("call_error", call_error)
    graph.add_node("call_performance", call_performance)
    graph.add_node("build_findings", build_findings)
    graph.add_node("aggregate", aggregate)

    graph.add_edge(START, "call_security")
    graph.add_edge(START, "call_error")
    graph.add_edge(START, "call_performance")
    graph.add_edge(START, "build_findings")
    graph.add_edge("call_security", "aggregate")
    graph.add_edge("call_error", "aggregate")
    graph.add_edge("call_performance", "aggregate")
    graph.add_edge("build_findings", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()
