"""언어/DB 어댑터, 실측 프로빙 도구, 공통 LLM 생성 지점을 모두 모아 둔 곳.

- `_default_llm()`: **검증** 역할(java_lite_adapter의 실제 소스 코드 리뷰, `run_eval.py`의
  판정자, 향후 ragas 내부 LLM)이 공유하는 LLM 생성 지점 — `.env`의 `MODEL_ID`로 고정한다.
  2차 자체평가(CLAUDE.md 10-J절 이후)에서 이 역할에 약한 모델(Haiku)을 쓰면 판정 자체가
  신뢰할 수 없어진다는 것을 실측으로 확인해, Sonnet 4.5 이상의 고급 모델을 쓰도록
  의도된 역할이다(사용자 결정, 2026-09-03).
- `_report_llm()`: **레포팅** 역할(`security_agent`/`error_agent`/`performance_agent`가
  이미 검증된 결과를 사람이 읽기 쉽게 요약·설명하는 것)이 쓰는 LLM 생성 지점 — `.env`의
  `REPORT_MODEL_ID`로 고정한다(미설정 시 `MODEL_ID`로 대체). 이 역할은 새로운 판정을
  만들지 않고 이미 정해진 결과를 옮겨 적을 뿐이라 값싼 모델(Haiku)로도 충분하다는 것이
  사용자 결정이다.
- 모델을 바꾸려면 `.env`의 `MODEL_ID`/`REPORT_MODEL_ID`만 바꾸면 되고 코드는 손대지
  않는다 — 이번 미니PJT에서 Bedrock 쿼터 문제로 여러 번 모델을 바꿔가며 실측 검증됨.
- `vue3_adapter`/`java_lite_adapter`/`python_adapter`: 언어별 점검 어댑터. 셋 다 같은
  `PROJECT_SOURCE_ROOT`를 받아 내부에서 각자 관련 파일을 재귀적으로 탐색한다(`npm
  audit`/`eslint`, LLM 코드 리뷰 — MyBatis XML의 `${}` SQLi 포함, `bandit`/`pylint`).
- `db_adapter`: `config.yaml`의 `db.engine`에 따라 조립되는 실측 DB 조회 도구(현재
  sqlite만 구현, oracle/edb/db2는 등록만 되고 미구현 — 로드맵).
- `probe_idor_vulnerability()`/`run_concurrent_load_test()`: `data/staging_app/`에
  직접 띄운 FastAPI 서버를 대상으로 한 실측 pentest/부하테스트 도구.

`_default_llm()`을 `agent.py`가 아니라 이 파일에 두는 이유는, Supervisor(`agent.py`)가
결국 이 파일(언어 어댑터)을 임포트해야 하는데, `java_lite_adapter`도 LLM이 필요해서
`_default_llm()`을 `agent.py`에 두면 agent.py -> tools.py -> agent.py로 순환 임포트가
생기기 때문이다. 이 파일에 두면 `agent.py`가 `tools.py`를 임포트하는 한 방향 흐름만
남는다.
"""

import atexit
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Literal

import requests
from langchain_aws import ChatBedrockConverse
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel

from src.config import load_db_config, load_source, load_staging_config

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_PROJECT_SOURCE_ROOT = _PROJECT_ROOT / "data"


def resolve_project_root() -> Path:
    """`config.yaml`의 `source`(전체설계 12절 "관리 화면"의 미니PJT 대체 구현)를 읽어
    점검 대상 프로젝트 루트를 정한다 — `type: local`만 실제로 지원하고, `type: git`은
    아직 clone 로직이 없는 로드맵이라 명확한 에러로 안내한다. 설정이 아예 없으면 기본값
    (`data/`)을 쓴다.

    **(결정, 2026-09-03 — 사용자 요청)** 예전엔 언어별로 `sources.<language>.path`를
    따로 뒀지만, 언어별 경로 대신 **프로젝트 전체에 대해 이 루트 하나만** 설정한다 —
    `vue3_adapter`/`java_lite_adapter`/`python_adapter`가 전부 이 같은 루트를 받아 각자
    내부적으로 재귀 탐색(`_discover_npm_project_dir`/`_discover_java_files`/`bandit -r`)
    으로 자기 언어에 맞는 파일을 찾고, `agent.py`의 `_detect_languages()`도 같은 루트를
    스캔해 어떤 언어가 실제로 있는지 자동 감지한다.

    `path`는 절대경로도 그대로 지원한다 — Agent가 실행되는 위치와 점검 대상 프로젝트가
    완전히 다른 경로에 있을 수 있기 때문이다(실사용 시나리오). `Path.__truediv__`는
    오른쪽 피연산자가 절대경로면 왼쪽(`_PROJECT_ROOT`)을 버리고 그 절대경로를 그대로
    반환하므로(표준 라이브러리 동작, 실측 확인) 상대/절대 경로를 모두 같은 코드로 처리할
    수 있다.
    """
    source = load_source()
    source_type = source.get("type")
    if source_type == "local" and source.get("path"):
        resolved = _PROJECT_ROOT / source["path"]
        # (결정, 2026-09-03 — 사용자 지적: 절대경로는 실행 환경(로컬/Docker/다른 머신)마다
        # 달라야 하는데 config.yaml에는 한 값만 고정돼 있음) 존재하지 않는 경로를 그냥
        # 넘기면 `os.walk()`/`rglob()`가 예외 없이 빈 결과만 반환해(실측 확인) 언어가
        # "0개 감지됨"으로 조용히 잘못 넘어간다 — Docker 컨테이너나 다른 머신, zip 압축
        # 해제 후처럼 경로가 실제로 안 맞을 때 원인을 찾기 매우 어려워진다. 그래서 여기서
        # 미리 존재를 확인해 요란하게(loud) 실패시킨다.
        if not resolved.is_dir():
            raise FileNotFoundError(
                f"config.yaml의 source.path가 가리키는 디렉터리가 없습니다: {resolved} — "
                "실행 환경(로컬/Docker/다른 머신)에 맞는 경로로 config.yaml을 수정하세요."
            )
        return resolved
    if source_type == "git":
        raise NotImplementedError(
            "config.yaml의 source가 type: git으로 설정되어 있지만, git 클론은 아직 "
            "구현되지 않은 로드맵입니다(전체설계 12절 참고). type: local로 바꿔주세요."
        )
    return _DEFAULT_PROJECT_SOURCE_ROOT


# 한 번만 계산해 재사용한다 — 세 어댑터가 전부 같은 루트를 쓰고, `agent.py`의 언어 자동
# 감지도 같은 루트를 다시 훑어야 하므로, 매번 config.yaml을 다시 읽고 판단할 필요가 없다.
PROJECT_SOURCE_ROOT = resolve_project_root()


# ---------------------------------------------------------------------------
# 모델별 토큰 사용량 집계 (사용자 요청, 2026-09-03 — "수행에 들어간 모델별 토큰을
# 레포트 상단에 기입")
# ---------------------------------------------------------------------------

# {model_id: {"input_tokens": N, "output_tokens": N, "total_tokens": N, "calls": N}}
_TOKEN_USAGE: dict[str, dict[str, int]] = {}


class _UsageTrackingCallback(BaseCallbackHandler):
    """`ChatBedrockConverse` 응답의 `usage_metadata`를 모델별로 누적하는 콜백.

    LLM 인스턴스 생성 시점에 붙여 두면(`callbacks=[...]`), `create_react_agent`의 ReAct
    루프처럼 그 LLM이 내부적으로 여러 번 호출되는 경우도 전부 자동으로 잡힌다 — LangChain
    콜백은 Runnable 체인/그래프 실행 전체에 전파되기 때문에, 호출부마다 따로 계측 코드를
    넣을 필요가 없다.
    """

    def __init__(self, model_id: str) -> None:
        self._model_id = model_id

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        bucket = _TOKEN_USAGE.setdefault(
            self._model_id, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "calls": 0}
        )
        for generation_list in response.generations:
            for generation in generation_list:
                usage = getattr(getattr(generation, "message", None), "usage_metadata", None)
                if not usage:
                    continue
                bucket["input_tokens"] += usage.get("input_tokens", 0) or 0
                bucket["output_tokens"] += usage.get("output_tokens", 0) or 0
                bucket["total_tokens"] += usage.get("total_tokens", 0) or 0
                bucket["calls"] += 1


def get_token_usage_summary() -> dict[str, dict[str, int]]:
    """지금까지 누적된 모델별 토큰 사용량을 반환한다(리포트 상단에 쓰기 위함)."""
    return {model_id: dict(counts) for model_id, counts in _TOKEN_USAGE.items()}


def reset_token_usage() -> None:
    """모델별 토큰 사용량 누적을 초기화한다 — 평가 라운드를 새로 시작하기 전에 호출한다."""
    _TOKEN_USAGE.clear()


def _build_llm(model_id: str, *, disable_parallel_tool_use: bool) -> ChatBedrockConverse:
    """`model_id`로 Bedrock 모델을 생성하고 토큰 사용량 추적 콜백을 붙인다.

    `_default_llm()`/`_report_llm()`이 공유하는 내부 헬퍼 — 병렬 도구 호출 우회
    (`disable_parallel_tool_use`)와 토큰 집계 로직을 한 곳에만 둔다.
    """
    region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
    extra_fields: dict[str, Any] = {}
    if disable_parallel_tool_use:
        extra_fields["tool_choice"] = {"type": "auto", "disable_parallel_tool_use": True}
    return ChatBedrockConverse(
        model=model_id,
        region_name=region,
        additional_model_request_fields=extra_fields or None,
        callbacks=[_UsageTrackingCallback(model_id)],
    )


def _default_llm(*, disable_parallel_tool_use: bool = True) -> ChatBedrockConverse:
    """**검증** 역할의 LLM — 환경변수 `MODEL_ID`로 지정된 Bedrock 모델을 생성해 반환한다.

    `java_lite_adapter`의 실제 소스 코드 리뷰, `run_eval.py`의 판정자(judge), 향후 ragas
    내부 LLM처럼 "새로운 판정을 직접 내리는" 역할이 이 함수를 쓴다(사용자 결정,
    2026-09-03 — 이 역할에 약한 모델을 쓰면 판정 자체가 신뢰할 수 없다는 것을 2차
    자체평가에서 실측 확인). 모델을 바꾸려면 `.env`의 `MODEL_ID`만 바꾸면 되고 코드는
    손대지 않는다(모델 독립성, 조건 9).

    **(결정, mini-pjt_이종엽 — 병렬 도구 호출 비활성화, `disable_parallel_tool_use`
    파라미터로 조정 가능)** 기본값(`True`)에서는 `additional_model_request_fields`로
    `disable_parallel_tool_use`를 켭니다. 1일차 4번에서 `create_react_agent` + 이 조합으로
    실제 테스트하다가 `ValidationException: toolUse.name ... [a-zA-Z0-9_-]+` 에러를
    실측으로 재현했는데, 원인은 우리가 고정한 `langchain-core==0.3.86`(ragas 호환을 위해
    구버전 세대로 고정, 위 "requirements.txt" 절 참고)의 스트리밍 도구 호출 병합 버그
    (`merge_dicts()`가 병렬 tool_use 블록을 잘못 합쳐 이름이 깨짐 —
    langchain-ai/langchain#34807과 같은 계열의 알려진 문제)입니다. 라이브러리를 올릴 수
    없으므로(ragas 깨짐), 애초에 병렬 도구 호출 자체를 못 하게 막아 버그가 발동할 상황을
    안 만드는 쪽으로 우회합니다.

    **(결정, mini-pjt_이종엽 — 1일차 6번에서 예외 추가)** `with_structured_output()`은
    내부적으로 `toolConfig.toolChoice.tool`을 직접 설정하는데, 이게 위 고정 tool_choice와
    같이 있으면 `ValidationException: tool_choice/type conflicts with ... toolChoice.tool`
    로 실제로 충돌하는 것을 확인했습니다(`java_lite_adapter` 작성 중 발견). 그래서
    `with_structured_output`을 쓰는 호출(병렬 도구 호출 자체가 없는 단발성 구조화 추출)은
    `disable_parallel_tool_use=False`로 이 함수를 호출해 충돌을 피합니다.
    """
    return _build_llm(os.environ["MODEL_ID"], disable_parallel_tool_use=disable_parallel_tool_use)


def _report_llm(*, disable_parallel_tool_use: bool = True) -> ChatBedrockConverse:
    """**레포팅** 역할의 LLM — 환경변수 `REPORT_MODEL_ID`로 지정된 Bedrock 모델을 생성해
    반환한다(미설정 시 `MODEL_ID`로 대체 — 기존 단일 모델 구성과 하위 호환).

    `security_agent`/`error_agent`/`performance_agent`처럼 "도구가 이미 내린 판정을 사람이
    읽기 쉽게 요약·설명만 하는"(3절 원칙) 역할이 이 함수를 쓴다 — 새로운 판정을 만들지
    않으므로 `_default_llm()`(검증)보다 값싼 모델로도 충분하다는 것이 사용자 결정이다
    (2026-09-03).
    """
    model_id = os.environ.get("REPORT_MODEL_ID") or os.environ["MODEL_ID"]
    return _build_llm(model_id, disable_parallel_tool_use=disable_parallel_tool_use)


# ---------------------------------------------------------------------------
# vue3_adapter: Vue3 실전 스캐너(npm audit/eslint) 연동 (1일차 2번)
# ---------------------------------------------------------------------------

_VUE3_PROJECT_DIR = _PROJECT_ROOT / "data" / "sample_vue3_app"

# npm/npx의 실제 실행 파일 경로를 미리 찾아둔다 — Windows에서는 npm이 npm.cmd라서
# subprocess.run(["npm", ...], shell=True)로 인자를 섞어 부르면 깨지기 쉽다.
# shutil.which로 실제 경로를 찾아 shell=False로 그대로 실행하면 윈도우/리눅스 모두 안전하다.
_NPM = shutil.which("npm") or "npm"
_NPX = shutil.which("npx") or "npx"

# Agent 카테고리 매핑(CLAUDE.md "더미 점검 대상 소스" 절 결정 그대로) — npm/eslint 규칙
# 이름 자체가 언어별 지식이라, 이 매핑도 어댑터 안에 둬서 Agent 코드가 몰라도 되게 한다
# (조건 4: 언어 이름이 들어간 로직은 어댑터 안에만).
_VUE3_SECURITY_ESLINT_RULES = {"no-eval", "vue/no-v-html"}
_VUE3_ERROR_ESLINT_RULES = {"no-unused-vars"}
# performance: Vue3 쪽 도구에는 해당 규칙이 없음 — N+1(Java 쪽)이 이 카테고리의 유일한 케이스


def _ensure_npm_install(project_dir: Path) -> None:
    """`node_modules`가 없으면 `npm install`을 실행해 만든다."""
    if (project_dir / "node_modules").exists():
        return
    subprocess.run(
        [_NPM, "install"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )


_NPM_AUDIT_MAX_ATTEMPTS = 3
_NPM_AUDIT_TIMEOUT_SECONDS = 30


def _run_with_hard_timeout(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess:
    """`subprocess.run(timeout=...)`과 달리, Windows에서 `.CMD` 래퍼(`npm.CMD` 등)가 실제로
    띄우는 손자 프로세스(`node.exe`)까지 확실히 죽이는 타임아웃 실행.

    **(결정, 2026-09-04 — 실측으로 발견)** `subprocess.run(cmd, timeout=15)`이 실제로는
    15초가 아니라 **63.9초** 만에야 `TimeoutExpired`를 반환하는 것을 직접 재현해 확인했다.
    원인: Windows에서 `npm.CMD`는 `cmd.exe`를 거쳐 실제 작업을 하는 `node.exe`를 손자
    프로세스로 띄우는데, `subprocess.run`의 기본 타임아웃 처리는 `Popen.kill()`로 **직계
    자식(cmd.exe)만** 죽이고 손자(node.exe)는 고아로 남긴다. 그 고아 프로세스가 파이프를
    계속 붙들고 있어 `communicate()`가 실제로 끝날 때까지 원래 지정한 타임아웃의 몇 배를
    기다리게 된다(관찰: `Get-Process`로 타임아웃 한참 뒤에도 살아있는 `node.exe`를 직접
    확인함). `taskkill /F /T /PID`로 프로세스 트리 전체를 죽여야 진짜 타임아웃이 지켜진다.
    """
    process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
        else:
            process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        raise


def _run_npm_audit(project_dir: Path) -> list[dict[str, Any]]:
    """`npm audit --json`을 실행해 취약점 목록을 원시 딕셔너리 리스트로 반환한다.

    **(결정, 2026-09-04 — 실측으로 간헐성 확인, 재시도 로직 추가)** npm 레지스트리의
    벌크 취약점 조회 엔드포인트(`POST /-/npm/v1/security/advisories/bulk`)가 이 재검증
    기간 동안 계속 무응답이라 완전히 죽은 장애로 판단했었다. 그런데 같은 명령을 짧은
    간격으로 3번 연달아 실행해보니 **1번은 몇 초 만에 정상 응답, 2번은 타임아웃** —
    영구 장애가 아니라 **간헐적 장애**였다. 그래서 "제외"가 아니라 짧은 타임아웃으로
    여러 번 재시도하는 게 맞는 대응이다. 또한 npm 자신도 레지스트리 응답을 못 받으면
    `{"message": "network timeout at: ..."}` 형태의 에러를 **유효한 JSON으로** 뱉는데
    (`vulnerabilities` 키 자체가 없음), 이걸 `.get("vulnerabilities", {})`로 무심코
    처리하면 "장애로 데이터를 못 받음"이 "취약점 0건"으로 둔갑하는 거짓 음성이 된다 —
    이 경우도 명시적으로 재시도 대상/실패로 취급하고 절대 빈 리스트로 넘기지 않는다.
    """
    last_error: Exception | str | None = None
    for _ in range(_NPM_AUDIT_MAX_ATTEMPTS):
        try:
            result = _run_with_hard_timeout(
                [_NPM, "audit", "--json"], cwd=project_dir, timeout=_NPM_AUDIT_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired as exc:
            last_error = exc
            continue

        # 취약점이 있으면 npm audit의 종료 코드가 0이 아니므로 returncode는 확인하지 않는다.
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"npm audit 출력 파싱 실패: {result.stderr or result.stdout}") from exc

        if "vulnerabilities" not in data:
            last_error = data.get("message", data)
            continue

        findings: list[dict[str, Any]] = []
        for package_name, vuln in data["vulnerabilities"].items():
            for advisory in vuln.get("via", []):
                if not isinstance(advisory, dict):
                    # via 항목이 문자열(다른 취약 패키지 이름 참조)이면 간접 의존성이라 건너뜀
                    continue
                advisory_id = advisory.get("url", "").rstrip("/").rsplit("/", 1)[-1] or package_name
                findings.append(
                    {
                        "tool": "npm-audit",
                        "rule": advisory_id,
                        "file": "package.json",
                        "line": None,
                        "severity": advisory.get("severity", vuln.get("severity", "low")),
                        "message": (
                            f"{advisory.get('title', '알 수 없는 취약점')} "
                            f"({package_name} {vuln.get('range', '')}) - {advisory.get('url', '')}"
                        ),
                    }
                )
        return findings

    raise RuntimeError(
        f"npm audit이 {_NPM_AUDIT_MAX_ATTEMPTS}번 재시도 후에도 레지스트리 응답을 받지 "
        f"못했습니다(간헐적 외부 장애로 추정) — 마지막 오류: {last_error}"
    )


def _run_eslint(project_dir: Path) -> list[dict[str, Any]]:
    """`eslint . --ext .js,.vue -f json`을 실행해 결과를 원시 딕셔너리 리스트로 반환한다."""
    result = subprocess.run(
        [_NPX, "eslint", ".", "--ext", ".js,.vue", "-f", "json"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # 위반이 있으면 eslint의 종료 코드가 1이므로 returncode는 확인하지 않는다.
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"eslint 출력 파싱 실패: {result.stderr or result.stdout}") from exc

    findings: list[dict[str, Any]] = []
    for file_result in data:
        file_path = Path(file_result["filePath"])
        try:
            relative_path = file_path.relative_to(project_dir).as_posix()
        except ValueError:
            relative_path = file_path.name
        for message in file_result.get("messages", []):
            if not message.get("ruleId"):
                continue  # 규칙 없는 메시지(파싱 에러 등)는 건너뜀
            findings.append(
                {
                    "tool": "eslint",
                    "rule": message["ruleId"],
                    "file": relative_path,
                    "line": message.get("line"),
                    "severity": "high" if message.get("severity") == 2 else "medium",
                    "message": message.get("message", ""),
                }
            )
    return findings


def _discover_npm_project_dir(root: Path) -> Path:
    """`root`에 `package.json`이 직접 있으면 그대로 쓰고, 없으면 하위 트리에서(`node_modules`
    제외) 가장 얕은 `package.json`을 찾아 그 디렉터리를 npm 프로젝트 루트로 쓴다 —
    `sources.vue3`의 경로가 전용 폴더가 아니라 여러 언어가 섞인 상위 폴더를 가리켜도
    동작하게 하기 위함이다."""
    direct = root / "package.json"
    if direct.exists():
        return root
    candidates = sorted(
        (path for path in root.rglob("package.json") if "node_modules" not in path.parts),
        key=lambda path: len(path.parts),
    )
    if not candidates:
        raise FileNotFoundError(
            f"{root} 아래에서 package.json을 찾지 못했습니다 — sources.vue3.path 설정을 "
            "확인하세요."
        )
    return candidates[0].parent


class Vue3Adapter:
    """Vue3 프로젝트용 언어 어댑터 — `npm audit`/`eslint`를 실제로 연동한다.

    `security_agent`/`error_agent`/`performance_agent`는 이 클래스의 세 메서드만 호출하고,
    `npm`/`eslint`/`vue` 같은 이름은 전혀 몰라도 된다(조건 4).
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = _discover_npm_project_dir(project_dir or _VUE3_PROJECT_DIR)
        self._raw_cache: dict[str, list[dict[str, Any]]] | None = None

    def _scan(self) -> dict[str, list[dict[str, Any]]]:
        """`npm audit`+`eslint`를 한 번만 실행하고 카테고리별로 나눠 캐싱한다."""
        if self._raw_cache is not None:
            return self._raw_cache

        _ensure_npm_install(self.project_dir)
        audit_findings = _run_npm_audit(self.project_dir)
        eslint_findings = _run_eslint(self.project_dir)

        security: list[dict[str, Any]] = list(audit_findings)
        error: list[dict[str, Any]] = []
        performance: list[dict[str, Any]] = []

        for finding in eslint_findings:
            if finding["rule"] in _VUE3_SECURITY_ESLINT_RULES:
                security.append(finding)
            elif finding["rule"] in _VUE3_ERROR_ESLINT_RULES:
                error.append(finding)
            # 매핑에 없는 규칙(프리셋이 자동으로 켤 수 있는 스타일 규칙 등)은 버린다 —
            # 의도한 findings만 정확히 나오게 하기 위함(CLAUDE.md "더미 점검 대상 소스" 참고)

        self._raw_cache = {"security": security, "error": error, "performance": performance}
        return self._raw_cache

    def run_security(self) -> list[dict[str, Any]]:
        """보안 관점 원시 발견 목록(`npm audit` 전부 + `eslint` 보안 관련 규칙)."""
        return self._scan()["security"]

    def run_error(self) -> list[dict[str, Any]]:
        """오류 관점 원시 발견 목록(`eslint` 코드 품질 규칙)."""
        return self._scan()["error"]

    def run_performance(self) -> list[dict[str, Any]]:
        """성능 관점 원시 발견 목록. Vue3 쪽에는 해당 규칙이 없어 항상 빈 리스트를 반환한다."""
        return self._scan()["performance"]


vue3_adapter = Vue3Adapter(PROJECT_SOURCE_ROOT)


# ---------------------------------------------------------------------------
# java_lite_adapter: 도구 없이 LLM이 직접 코드를 리뷰 (1일차 6번)
# ---------------------------------------------------------------------------

# (결정, 2026-09-03) 예전엔 `.../java/com/example/dummy`까지 정확히 내려간 경로가
# 기본값이었다 — 재귀 탐색이 생기기 전엔 정확한 패키지 디렉터리를 알아야 했기 때문이다.
# 이제는 `_discover_java_files()`/`_discover_mybatis_xml_files()`가 재귀적으로 찾으므로,
# 기본값도 Maven 프로젝트 루트(`src/main/java`+`src/main/resources`를 모두 포함하는
# 앱 폴더)로 넓혀 `config.yaml` 설정 없이도 MyBatis 매퍼 XML까지 함께 발견되게 한다.
_JAVA_SRC_DIR = _PROJECT_ROOT / "data" / "sample_java_app"

# AwsConfig.java(하드코딩 자격증명)는 gitleaks 같은 도구가 이미 잘 잡는 부류라 애초에
# 리뷰 대상에 넣지 않는다(탐지 대상 아님, mask_pii 가드레일 테스트 픽스처로만 씀 —
# CLAUDE.md 참고). 나머지 파일(UserController/DbHelper/OrderController/OrderService)은
# `_discover_java_files()`가 `src_dir` 아래에서 전부 찾아 security/performance 두
# 카테고리 모두에 같이 준다 — 어떤 파일이 SQLi 대상이고 어떤 파일이 N+1 대상인지는 이제
# 파일 목록이 아니라 카테고리별 지시문(`_SECURITY_INSTRUCTIONS`/`_PERFORMANCE_
# INSTRUCTIONS`)의 "다른 범주는 findings에 포함하지 마라" 원칙으로만 가른다 — sources.java
# 의 경로가 정확한 패키지 디렉터리가 아니라 더 넓은 상위 폴더를 가리켜도(예: `data`) 같은
# 방식으로 동작하게 하기 위함이다.
_JAVA_EXCLUDED_FILENAMES = {"AwsConfig.java"}


def _discover_java_files(src_dir: Path) -> list[Path]:
    """`src_dir` 아래에서 재귀적으로 `.java` 파일을 전부 찾는다(`_JAVA_EXCLUDED_FILENAMES`
    제외)."""
    return sorted(
        path for path in src_dir.rglob("*.java") if path.name not in _JAVA_EXCLUDED_FILENAMES
    )


def _discover_mybatis_xml_files(src_dir: Path) -> list[Path]:
    """`src_dir` 아래에서 재귀적으로 MyBatis 매퍼 XML을 찾는다(확장, CLAUDE.md 10-D절).

    MyBatis는 SQL을 `.java`가 아니라 `.xml` 매퍼 파일에 적는다 — `${}`(문자열 치환, SQL
    Injection 위험)와 `#{}`(파라미터 바인딩, 안전)를 구분해야 하는데, 표준 JDBC API
    호출만 인식하는 정적분석 도구 기본 룰셋은 이 파일 형식 자체를 보지 않는다. `pom.xml`/
    `web.xml` 같은 무관한 XML까지 리뷰 대상에 넣지 않도록, MyBatis 매퍼의 표식(`<mapper`
    루트 엘리먼트)이 실제로 있는 파일만 골라낸다."""
    candidates = sorted(src_dir.rglob("*.xml"))
    return [path for path in candidates if "<mapper" in path.read_text(encoding="utf-8")]

_SECURITY_INSTRUCTIONS = """당신은 보안 코드 리뷰어입니다. 아래 Java 소스(와, 있다면 MyBatis
매퍼 XML)를 검토하세요.

이 프로젝트에는 정적분석 도구(SpotBugs/Semgrep 등)가 아직 연동되어 있지 않습니다. 하지만
그 도구들이 이미 잘 잡는 패턴(표준 JDBC API를 직접 호출하는 트리비얼한 SQL Injection,
하드코딩된 비밀번호/키)까지 처음부터 찾을 필요는 없습니다 — 그건 나중에 실전 도구가 붙으면
담당할 몫입니다. 대신 아래 세 가지만 찾아주세요.

1. IDOR(깨진 객체 수준 권한 부여): 요청 파라미터로 받은 리소스 ID(주문 ID 등)를 그대로
   조회하면서, 그 리소스가 요청자 소유인지 검증하는 코드가 없는 경우.
2. 사내 래퍼를 거친 SQL Injection: 표준 JDBC API(Statement/PreparedStatement)를 직접
   호출하는 게 아니라, 사내 공용 유틸리티 클래스를 거쳐 실행되는 SQL Injection — 문자열
   결합으로 만든 쿼리가 그 래퍼로 전달되는 경우.
3. MyBatis 매퍼 XML의 `${}` SQL Injection: `<select>`/`<update>`/`<delete>`/`<insert>`
   태그 안에서 `#{...}`(파라미터 바인딩, PreparedStatement로 컴파일되어 안전)가 아니라
   `${...}`(문자열 치환, SQL이 그대로 조립됨)를 쓰는 경우 — 특히 정렬 컬럼명·테이블명처럼
   `#{}`로는 파라미터화할 수 없어 실무에서 실수로 `${}`를 쓰는 자리가 전형적인 사례입니다.
   같은 파일 안에 `#{}`만 쓰는 안전한 쿼리가 있다면 그건 findings에 넣지 마세요 — `${}`를
   쓰는 것만 대상입니다.

위 세 가지에 해당하지 않는 것(하드코딩된 비밀번호 등)은 절대 findings에 포함하지 마세요."""

_PERFORMANCE_INSTRUCTIONS = """당신은 성능 코드 리뷰어입니다. 아래 Java 소스를 검토하세요.

반복문 안에서 컬렉션의 각 항목마다 별도의 쿼리를 던지는 N+1 패턴만 찾아주세요 — 이건
한 줄짜리 정규식이 아니라 여러 줄의 제어 흐름(반복문 범위와 그 안의 쿼리 호출)을 이해해야
판단할 수 있는 문제라, 일반적인 무료 정적분석 도구로는 안정적으로 잡히지 않습니다.

같은 코드에 다른 문제(SQL Injection, 리소스 미반환/미종료, 그 밖의 무엇이든)가 보이더라도
그건 이 리뷰의 대상이 아닙니다 — 그런 패턴은 SpotBugs/Semgrep 같은 무료 정적분석 도구가
기본 룰셋으로 이미 잘 잡는 종류라 여기서 다시 판정하면 토큰 낭비입니다. N+1이 아닌 것은
findings에 절대 포함하지 마세요.

message에는 반드시 반복문 안 쿼리가 실제로 조회하는 테이블 이름과 WHERE 절 컬럼을 정확히
포함하세요(예: "order_items 테이블을 order_id 컬럼으로 조회") — 이 정보가 없으면 이후 DB
실행계획 조회 단계에서 엉뚱한 테이블을 조회하게 됩니다."""

_COMMON_INSTRUCTIONS_SUFFIX = """

각 발견에 rule(케밥 케이스 규칙 이름, 예: idor-missing-ownership-check), file(파일명),
line(가능하면 줄 번호, 모르면 비워둠), severity(high/medium/low 중 하나), message(한국어로
무엇이 문제인지 한두 문장)를 채워 응답하세요. 문제를 못 찾으면 findings를 빈 리스트로
두세요."""


class LlmRawFinding(BaseModel):
    """Java lite 리뷰에서 LLM에게 요구하는 발견 한 건의 출력 형식."""

    rule: str
    file: str
    line: int | None = None
    severity: Literal["high", "medium", "low"]
    message: str


class LlmReviewResult(BaseModel):
    """Java lite 리뷰 구조화 출력(패턴 #1) — `with_structured_output`으로 강제한다."""

    findings: list[LlmRawFinding]


class JavaLiteAdapter:
    """Java 프로젝트용 언어 어댑터 — 실전 도구 없이 LLM이 코드를 직접 리뷰한다(라이트).

    `security_agent`/`error_agent`/`performance_agent`는 이 클래스의 세 메서드만 호출하고,
    "도구가 없어서 LLM이 코드를 읽는다"는 사실 자체도 몰라도 된다(조건 4).
    """

    def __init__(self, src_dir: Path | None = None) -> None:
        self.src_dir = src_dir or _JAVA_SRC_DIR
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._discovered_files: list[Path] | None = None
        self._discovered_xml_files: list[Path] | None = None

    def _java_files(self) -> list[Path]:
        if self._discovered_files is None:
            self._discovered_files = _discover_java_files(self.src_dir)
        return self._discovered_files

    def _mybatis_xml_files(self) -> list[Path]:
        if self._discovered_xml_files is None:
            self._discovered_xml_files = _discover_mybatis_xml_files(self.src_dir)
        return self._discovered_xml_files

    def _review(
        self, category: str, instructions: str, include_mybatis_xml: bool = False
    ) -> list[dict[str, Any]]:
        """`src_dir` 아래에서 발견된 `.java` 파일(+ `include_mybatis_xml=True`면 MyBatis
        매퍼 XML도) 전부를 LLM에게 통째로 보여주고 구조화된 발견 목록을 받는다 — 어떤
        파일이 이 카테고리와 실제로 관련 있는지는 `instructions`의 "다른 범주는 포함하지
        마라" 원칙으로 LLM이 가른다."""
        if category in self._cache:
            return self._cache[category]

        files = [(path, "java") for path in self._java_files()]
        if include_mybatis_xml:
            files += [(path, "xml") for path in self._mybatis_xml_files()]
        if not files:
            self._cache[category] = []
            return []

        sources = "\n\n".join(
            f"### {path.name}\n```{fence}\n{path.read_text(encoding='utf-8')}\n```"
            for path, fence in files
        )
        structured_llm = _default_llm(disable_parallel_tool_use=False).with_structured_output(
            LlmReviewResult
        )
        result: LlmReviewResult = structured_llm.invoke(
            instructions + _COMMON_INSTRUCTIONS_SUFFIX + "\n\n" + sources
        )

        findings = [
            {
                "tool": "llm-review",
                "rule": f.rule,
                "file": f.file,
                "line": f.line,
                "severity": f.severity,
                "message": f.message,
            }
            for f in result.findings
        ]
        self._cache[category] = findings
        return findings

    def run_security(self) -> list[dict[str, Any]]:
        """보안 관점 원시 발견 목록 — IDOR, 사내 래퍼 경유 SQL Injection, MyBatis 매퍼
        XML의 `${}` SQL Injection이 대상."""
        return self._review("security", _SECURITY_INSTRUCTIONS, include_mybatis_xml=True)

    def run_error(self) -> list[dict[str, Any]]:
        """오류 관점 원시 발견 목록. Java lite에는 목표 케이스가 없어 항상 빈 리스트
        (LLM 미호출 — 파일이 발견되더라도 이 카테고리는 애초에 호출하지 않아 토큰을 아낀다)."""
        return []

    def run_performance(self) -> list[dict[str, Any]]:
        """성능 관점 원시 발견 목록 — N+1 패턴만 대상."""
        return self._review("performance", _PERFORMANCE_INSTRUCTIONS)


java_lite_adapter = JavaLiteAdapter(PROJECT_SOURCE_ROOT)


# ---------------------------------------------------------------------------
# python_adapter: bandit/pylint 실전 연동 (확장 phase 5-1-A, 3일계획 5-1-A절)
# ---------------------------------------------------------------------------

_PYTHON_PROJECT_DIR = _PROJECT_ROOT / "data" / "sample_python_app"

# bandit/pylint는 (npm/npx와 달리) 별도 시스템 실행 파일이 아니라 이 venv에 pip로 설치한
# 파이썬 패키지다 — `shutil.which("bandit")`는 venv가 "활성화"되지 않은 셸에서는 Scripts
# 디렉터리가 PATH에 없어 못 찾는 것을 실측으로 확인했다. `sys.executable -m bandit`로
# 호출하면 지금 이 인터프리터(venv)에 설치된 패키지를 PATH와 무관하게 항상 정확히 찾는다.
_BANDIT = [sys.executable, "-m", "bandit"]
_PYLINT = [sys.executable, "-m", "pylint"]

# pylint는 eslint처럼 한 번 실행에 여러 성격의 규칙(오류성 + 리팩터/컨벤션성)을 함께
# 쏟아낸다 — 실측 결과 우리 더미 소스(공개 메서드 1개짜리 클래스)에 "too-few-public-
# methods"(리팩터 제안, R0903)가 의도한 "unused-import"(W0611)와 함께 나오는 것을
# 확인했다. eslint 때와 같은 원칙으로, error 카테고리에 해당하는 규칙만 명시적으로 골라
# 쓰고 나머지는 버린다. bandit은 npm audit처럼 애초에 보안 전용 도구라 규칙 필터링 없이
# 전부 security로 보낸다.
_PYTHON_ERROR_PYLINT_SYMBOLS = {"unused-import"}


def _run_bandit(project_dir: Path) -> list[dict[str, Any]]:
    """`bandit -f json`을 실행해 보안 발견 목록을 원시 딕셔너리 리스트로 반환한다."""
    result = subprocess.run(
        # 실측 확인: bandit은 `-r`(재귀) 없이 디렉터리를 넘기면 아무것도 스캔하지 않고
        # 조용히 빈 결과를 반환한다(에러도 없음) — 반드시 `-r`을 붙여야 한다.
        [*_BANDIT, "-r", "-f", "json", str(project_dir)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # 발견이 있으면 bandit의 종료 코드가 1이므로 returncode는 확인하지 않는다.
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bandit 출력 파싱 실패: {result.stderr or result.stdout}") from exc

    findings: list[dict[str, Any]] = []
    for item in data.get("results", []):
        file_path = Path(item["filename"])
        try:
            relative_path = file_path.resolve().relative_to(project_dir).as_posix()
        except ValueError:
            relative_path = file_path.name
        findings.append(
            {
                "tool": "bandit",
                "rule": item["test_id"],
                "file": relative_path,
                "line": item.get("line_number"),
                "severity": item.get("issue_severity", "medium"),
                "message": f"{item.get('test_name', '')}: {item.get('issue_text', '')}",
            }
        )
    return findings


def _run_pylint(project_dir: Path) -> list[dict[str, Any]]:
    """`pylint --output-format=json`을 실행해 결과를 원시 딕셔너리 리스트로 반환한다."""
    result = subprocess.run(
        [*_PYLINT, "--output-format=json", str(project_dir)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # 발견이 있으면 pylint의 종료 코드가 0이 아니므로 returncode는 확인하지 않는다.
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"pylint 출력 파싱 실패: {result.stderr or result.stdout}") from exc

    findings: list[dict[str, Any]] = []
    for item in data:
        file_path = Path(item["path"])
        try:
            relative_path = file_path.resolve().relative_to(project_dir).as_posix()
        except ValueError:
            relative_path = file_path.name
        findings.append(
            {
                "tool": "pylint",
                "rule": item["symbol"],
                "file": relative_path,
                "line": item.get("line"),
                "severity": item.get("type", "medium"),
                "message": item.get("message", ""),
            }
        )
    return findings


class PythonAdapter:
    """Python 프로젝트용 언어 어댑터 — `bandit`/`pylint`를 실제로 연동한다(확장 phase 5-1-A).

    `security_agent`/`error_agent`/`performance_agent`는 이 클래스의 세 메서드만 호출하고,
    `bandit`/`pylint` 같은 이름은 전혀 몰라도 된다(조건 4).
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        self.project_dir = project_dir or _PYTHON_PROJECT_DIR
        self._raw_cache: dict[str, list[dict[str, Any]]] | None = None

    def _scan(self) -> dict[str, list[dict[str, Any]]]:
        """`bandit`+`pylint`를 한 번만 실행하고 카테고리별로 나눠 캐싱한다."""
        if self._raw_cache is not None:
            return self._raw_cache

        bandit_findings = _run_bandit(self.project_dir)
        pylint_findings = _run_pylint(self.project_dir)

        security: list[dict[str, Any]] = list(bandit_findings)
        error: list[dict[str, Any]] = [
            finding for finding in pylint_findings if finding["rule"] in _PYTHON_ERROR_PYLINT_SYMBOLS
        ]

        self._raw_cache = {"security": security, "error": error, "performance": []}
        return self._raw_cache

    def run_security(self) -> list[dict[str, Any]]:
        """보안 관점 원시 발견 목록(`bandit` 전부)."""
        return self._scan()["security"]

    def run_error(self) -> list[dict[str, Any]]:
        """오류 관점 원시 발견 목록(`pylint`의 오류성 규칙만)."""
        return self._scan()["error"]

    def run_performance(self) -> list[dict[str, Any]]:
        """성능 관점 원시 발견 목록. Python 쪽에는 해당 규칙이 없어 항상 빈 리스트를 반환한다."""
        return self._scan()["performance"]


python_adapter = PythonAdapter(PROJECT_SOURCE_ROOT)


# 5-1-B: DB 연결 + 부하 파라미터 (전체설계 3-5절, CLAUDE.md 10-B절). 언어 어댑터와 달리
# security/error/performance 세 메서드짜리 `LanguageAdapter` 프로토콜을 따르지 않는다 —
# `performance_agent`가 별도 도구로 직접 붙여 쓰는 보조 어댑터다.

_DB_SCHEMA_SQL = _PROJECT_ROOT / "data" / "sample_db" / "schema.sql"
_DB_PATH = _PROJECT_ROOT / "data" / "sample_db" / "app.db"

_FORBIDDEN_SQL_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create", "replace", "attach", "pragma",
)


class ReadOnlySqlError(ValueError):
    """SELECT 이외의 SQL을 막기 위한 예외(보안 경계 — CLAUDE.md 10-B절 "보안 경계",
    전체설계 3-5-1절 "읽기 전용 계정" 원칙을 SQLite에 맞게 대체한 것)."""


def _assert_select_only(sql: str) -> None:
    normalized = sql.strip().lower()
    if not normalized.startswith("select"):
        raise ReadOnlySqlError(f"explain_query는 SELECT문만 허용합니다 — 거부된 SQL: {sql!r}")
    if any(keyword in normalized for keyword in _FORBIDDEN_SQL_KEYWORDS):
        raise ReadOnlySqlError(f"SELECT문에 금지된 키워드가 포함되어 있습니다 — 거부된 SQL: {sql!r}")


def _build_sample_db(db_path: Path, schema_path: Path) -> None:
    """`schema.sql`로 더미 DB를 매번 새로 만든다 — 고정 산출물로 커밋하지 않는다(CLAUDE.md
    10-B절)."""
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.commit()
    finally:
        connection.close()


class DbAdapter:
    """SQLite 전용 DB 어댑터 — `performance_agent`가 스키마/실행계획을 조회할 때 쓴다.

    전체설계 3-5-1절 인터페이스 중 SQLite에서 의미 있는 두 가지만 구현한다(`get_schema()`,
    `explain_query(sql)`) — `get_connection_pool_config()`은 SQLite가 파일 기반이라
    커넥션 풀 개념이 약해 이번 범위에서는 생략한다(로드맵에 남김).
    """

    def __init__(self, db_path: Path | None = None, schema_path: Path | None = None) -> None:
        self.db_path = db_path or _DB_PATH
        self.schema_path = schema_path or _DB_SCHEMA_SQL
        self._built = False
        self._build_lock = threading.Lock()

    def _ensure_db(self) -> None:
        """`_built` 확인 후 `_build_sample_db()`를 부르는 구간을 직렬화한다(결정,
        2026-09-04 — 소스 전체 재검증 중 발견). Supervisor가 `performance_agent`의
        `get_db_schema`/`explain_query`와 `build_findings`의 `attach_db_evidence()`를
        병렬로 실행하므로, 잠금 없이는 두 스레드가 동시에 `_built=False`를 보고
        `_build_sample_db()`를 중복 실행할 수 있다 — `_build_sample_db()`가 기존 DB
        파일을 `unlink()`한 뒤 새로 만드는데, 한 스레드가 그 파일을 `unlink()`하는 순간
        다른 스레드가 이미 연 커넥션으로 쓰는 중이면 Windows에서 `PermissionError`가
        날 수 있는 실제 위험이었다."""
        with self._build_lock:
            if not self._built:
                _build_sample_db(self.db_path, self.schema_path)
                self._built = True

    def get_schema(self) -> list[dict[str, Any]]:
        """테이블별 컬럼과 인덱스 목록을 반환한다(읽기 전용 — `sqlite_master`/`PRAGMA`만 조회)."""
        self._ensure_db()
        connection = sqlite3.connect(self.db_path)
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            tables = [row[0] for row in cursor.fetchall()]

            schema = []
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                cursor.execute(f"PRAGMA index_list({table})")
                indexes = [row[1] for row in cursor.fetchall()]
                schema.append({"table": table, "columns": columns, "indexes": indexes})
            return schema
        finally:
            connection.close()

    def explain_query(self, sql: str) -> list[dict[str, Any]]:
        """`EXPLAIN QUERY PLAN`으로 실행계획을 반환한다 — SELECT문이 아니면 거부한다."""
        _assert_select_only(sql)
        self._ensure_db()
        connection = sqlite3.connect(self.db_path)
        try:
            cursor = connection.cursor()
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()


# "엔진 이름 문자열" -> 실제 DB 어댑터 클래스, 또는 이름은 알려져 있지만 아직 어댑터가 없으면
# `None`(전체설계 3-5-1절 "db_adapter 레지스트리" — 언어 어댑터 레지스트리(agent.py의
# `_LANGUAGE_ADAPTER_REGISTRY`)와 같은 설정 기반 라우팅 구조). 미니PJT는 `sqlite`만 실제로
# 구현했다 — Oracle/EDB/Db2는 벤더별 드라이버·실행계획 조회 문법·스키마 카탈로그가 전부
# 달라 어댑터 하나를 새로 구현해야 하는 로드맵이다(CLAUDE.md 10-B절 "유보 사항"). 이름만
# 미리 등록해 둬서 "아예 모르는 값을 오타로 넣은 경우"(`ValueError`)와 "알려진 로드맵
# 대상이라 아직 구현이 없는 경우"(`NotImplementedError`)를 구분한다.
_DB_ADAPTER_REGISTRY: dict[str, type | None] = {
    "sqlite": DbAdapter,
    "oracle": None,
    "edb": None,
    "db2": None,
}


def _resolve_db_adapter_from_config() -> DbAdapter:
    """`config.yaml`의 `db.engine`을 읽어 레지스트리에서 어댑터를 만든다. `path`/
    `schema_path`가 있으면 그 경로를, 없으면 기존 기본 경로를 쓴다.

    **(결정, 2026-09-03 — 사용자 지적)** `db.engine`별로 필요한 필드 집합이 서로 다르다
    — `sqlite`는 `path`/`schema_path`(파일 경로)만, `oracle`/`edb`/`db2` 같은 상용 DB는
    `path`/`schema_path`는 아예 없이 `host`/`port`/`database`/`user`/`password_ref`
    (커넥션 정보)만 온다. SQLite는 서버·인증이 없는 임베디드 DB라 애초에 호스트/포트/
    계정 개념 자체가 없기 때문이다. 그래서 이 함수는 **`engine` 값 자체로 분기**하고
    (`if engine != "sqlite": ...`가 아니라 레지스트리 조회 후 `adapter_cls is None`
    분기), `path`/`schema_path`가 config에 있는지 여부로 분기하지 않는다 — 상용 DB
    어댑터를 실제로 구현할 때도 이 원칙을 그대로 지켜야 한다(`db_config.get("path")`가
    없다고 해서 sqlite가 아니라고 추측하면 안 되고, `engine`을 직접 봐야 한다).
    """
    db_config = load_db_config()
    engine = db_config.get("engine", "sqlite")
    if engine not in _DB_ADAPTER_REGISTRY:
        raise ValueError(
            f"config.yaml의 db.engine에 등록되지 않은 값이 있습니다: {engine!r}. "
            f"사용 가능한 값: {sorted(_DB_ADAPTER_REGISTRY)}"
        )
    adapter_cls = _DB_ADAPTER_REGISTRY[engine]
    if adapter_cls is None:
        raise NotImplementedError(
            f"DB 엔진 {engine!r}은 레지스트리에 이름만 있고 실제 어댑터는 아직 구현되지 "
            "않았습니다(로드맵, CLAUDE.md 10-B절 '유보 사항' 참고). host/port/database/"
            "user/password_ref 같은 커넥션 정보를 받는 어댑터를 새로 구현해야 합니다."
        )
    # 여기 도달하면 engine == "sqlite"뿐이다(레지스트리에 다른 구현체가 아직 없으므로) —
    # sqlite 전용 필드(path/schema_path)만 읽는다.
    db_path = _PROJECT_ROOT / db_config["path"] if db_config.get("path") else _DB_PATH
    schema_path = (
        _PROJECT_ROOT / db_config["schema_path"] if db_config.get("schema_path") else _DB_SCHEMA_SQL
    )
    return adapter_cls(db_path=db_path, schema_path=schema_path)


db_adapter = _resolve_db_adapter_from_config()


# 5-2: pentest_agent/load_test_agent 최소 실증 (전체설계 10-0절/3-5-3절, CLAUDE.md 10-C절).
# "Agent가 직접 수행"의 기본 경로(전용 도구 없이 표준 HTTP 클라이언트 `requests`로 직접
# 요청) — `data/staging_app/app.py`(우리가 직접 만든 최소 실행 가능 더미 서버)에 실제로
# 요청을 보낸다. db_adapter와 같은 이유로 `LanguageAdapter` 프로토콜을 따르지 않는 별도
# 보조 도구다 — security_agent/performance_agent가 필요할 때만 호출하는 선택적 도구다.

_STAGING_HOST = "127.0.0.1"
_STAGING_PORT = 8500
_STAGING_BASE_URL = f"http://{_STAGING_HOST}:{_STAGING_PORT}"

_staging_process: subprocess.Popen | None = None
_staging_lock = threading.Lock()


def _ensure_staging_server() -> str:
    """모의해킹/부하테스트 대상 서버의 base_url을 반환한다.

    `config.yaml`의 `staging.base_url`이 설정되어 있으면 **그 주소를 그대로 쓰고 아무것도
    기동하지 않는다** — 실제 배포에서 조직이 이미 운영 중인 스테이징 서버를 가리키는
    경우다(CLAUDE.md 10-N절). 설정이 없으면(기본값) 이 프로젝트 안의 더미 스테이징 앱
    (`data/staging_app/app.py`)을 `uvicorn` 서브프로세스로 로컬에 기동한다(최초 1회만,
    이후 재사용) — 미니PJT 실증 전용 지름길이다. **안전 경계**: 로컬 기동 시
    `127.0.0.1`에만 바인딩해 외부에서 접근 불가능하다. **소스/git 위치로부터 서버를
    자동으로 빌드·기동하는 기능은 없다** — 항상 사람이 미리 등록한 주소만 받는다.

    **(결정, 2026-09-04 — 소스 전체 재검증 중 발견) `_staging_lock`으로 기동 구간을
    직렬화한다** — Supervisor 그래프가 `call_security`/`call_performance`/`build_findings`
    를 병렬로 실행하므로, 잠금 없이 최초 1회 기동 여부를 확인·기동하면 두 스레드가 동시에
    `_staging_process is None`을 보고 각각 `subprocess.Popen()`을 호출해 같은 포트를
    두고 경합하는 실제 레이스 컨디션이 있었다(패자 프로세스가 고아로 남거나 승자를 기다리며
    불필요하게 10초를 태울 수 있었다).
    """
    configured_url = load_staging_config().get("base_url")
    if configured_url:
        return str(configured_url).rstrip("/")

    with _staging_lock:
        global _staging_process
        if _staging_process is not None and _staging_process.poll() is None:
            return _STAGING_BASE_URL
        _staging_process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "data.staging_app.app:app",
                "--host", _STAGING_HOST, "--port", str(_STAGING_PORT),
            ],
            cwd=str(_PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        atexit.register(_staging_process.terminate)

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            requests.get(f"{_STAGING_BASE_URL}/orders/1", params={"current_user_id": 1}, timeout=0.5)
            return _STAGING_BASE_URL
        except requests.exceptions.RequestException:
            time.sleep(0.2)
    raise RuntimeError("스테이징 서버(data/staging_app)가 제한 시간 안에 기동하지 않았습니다.")


# (공격자 user_id, 시도할 order_id, 실제 소유자 user_id) — 전부 앱 내부 고정 시드 데이터
# 기준이라 상태를 바꾸지 않는 GET 프로빙만으로 검증 가능하다(안전 경계: 읽기 전용, localhost
# 전용, 상한 있는 고정 목록 — 임의 스캔이 아님).
_PENTEST_PROBES = [(1, 3, 2), (1, 4, 3)]


def probe_idor_vulnerability() -> list[dict[str, Any]]:
    """스테이징 서버에 실제 GET 요청을 보내 IDOR(소유권 검증 누락)을 살아있는 상태로
    검증한다 — `OrderController.java`의 정적 리뷰 판정을 실제 HTTP 왕복으로 재확인한다."""
    base_url = _ensure_staging_server()
    findings: list[dict[str, Any]] = []
    for attacker_id, target_order_id, owner_id in _PENTEST_PROBES:
        response = requests.get(
            f"{base_url}/orders/{target_order_id}",
            params={"current_user_id": attacker_id},
            timeout=2,
        )
        body = response.json()
        leaked = response.status_code == 200 and body.get("user_id") not in (None, attacker_id)
        if leaked:
            findings.append(
                {
                    "tool": "pentest-http",
                    "rule": "idor-live-probe",
                    "file": "data/staging_app/app.py",
                    "line": None,
                    "severity": "high",
                    "message": (
                        f"공격자(user_id={attacker_id})가 소유하지 않은 주문(order_id="
                        f"{target_order_id}, 실제 소유자 user_id={owner_id})을 "
                        f"GET /orders/{target_order_id}로 조회했더니 소유권 검증 없이 "
                        f"HTTP 200과 함께 그대로 반환되었습니다(응답 본문: {body}). "
                        "실제 요청으로 확인한 IDOR입니다."
                    ),
                }
            )
    return findings


_LOAD_TEST_ENDPOINT = "/orders/1/items"
_LOAD_TEST_MAX_CONCURRENCY = 50  # 로컬 서버 보호 상한 — load_profile.yaml 값이 더 커도 이 값을 넘지 않는다
_LOAD_TEST_LATENCY_THRESHOLD_MS = 300


def run_concurrent_load_test(expected_concurrent_users: int = 50) -> list[dict[str, Any]]:
    """스테이징 서버에 동시 GET 요청을 실제로 보내 부하 상황에서의 p95 지연시간·에러율을
    직접 측정한다 — `OrderService.java`의 N+1이 실제 동시 요청 하에서도 느려지는지를 코드
    분석이 아니라 실측으로 재확인한다."""
    base_url = _ensure_staging_server()
    concurrency = min(expected_concurrent_users, _LOAD_TEST_MAX_CONCURRENCY)
    errors = 0

    def _probe(_: int) -> float | None:
        nonlocal errors
        start = time.monotonic()
        try:
            response = requests.get(f"{base_url}{_LOAD_TEST_ENDPOINT}", timeout=5)
        except requests.exceptions.RequestException:
            errors += 1
            return None
        if response.status_code != 200:
            errors += 1
            return None
        return time.monotonic() - start

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(_probe, range(concurrency)))
    latencies = sorted(latency for latency in results if latency is not None)
    error_rate = errors / concurrency

    # (결정, 2026-09-04 — 소스 전체 재검증 중 발견) 요청이 전부 실패하면(latencies가 비어
    # p95를 계산할 수 없음) "발견 없음"으로 조용히 반환하면 안 된다 — 부하테스트의 가장 나쁜
    # 결과(전체 장애)가 정상 상태와 똑같이 보고되는 거짓 음성이었다. 전체 실패는 그 자체로
    # high severity finding으로 보고한다.
    if not latencies:
        return [
            {
                "tool": "load-test-http",
                "rule": "high-latency-under-concurrent-load",
                "file": "data/staging_app/app.py",
                "line": None,
                "severity": "high",
                "message": (
                    f"GET {_LOAD_TEST_ENDPOINT}에 동시 요청 {concurrency}건을 보냈으나 "
                    f"전부({errors}건) 실패해 지연시간을 측정할 수조차 없었습니다(에러율 "
                    f"{error_rate:.0%}). 동시 부하 상황에서 서버가 완전히 응답하지 못함을 "
                    "실측으로 확인했습니다."
                ),
            }
        ]

    p95_index = max(0, int(len(latencies) * 0.95) - 1)
    p95_latency_ms = latencies[p95_index] * 1000

    if p95_latency_ms < _LOAD_TEST_LATENCY_THRESHOLD_MS and error_rate == 0:
        return []

    return [
        {
            "tool": "load-test-http",
            "rule": "high-latency-under-concurrent-load",
            "file": "data/staging_app/app.py",
            "line": None,
            "severity": "high" if p95_latency_ms >= _LOAD_TEST_LATENCY_THRESHOLD_MS * 2 else "medium",
            "message": (
                f"GET {_LOAD_TEST_ENDPOINT}에 동시 요청 {concurrency}건(부하 프로파일 예상 "
                f"동시 사용자 {expected_concurrent_users}명 기준, 로컬 서버 보호를 위해 "
                f"{concurrency}건으로 상한)을 보낸 결과 p95 지연시간 {p95_latency_ms:.0f}ms, "
                f"에러율 {error_rate:.0%}가 관측되었습니다. 임계치"
                f"({_LOAD_TEST_LATENCY_THRESHOLD_MS}ms) 초과로 동시 부하 상황에서 실제로 지연이 "
                "발생함을 실측으로 확인했습니다."
            ),
        }
    ]
