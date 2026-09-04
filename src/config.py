"""프로젝트 설정 파일(`config.yaml`) 로더.

전체설계 11-3절 "언어 선택/탐지"의 config 기반 어댑터 선택을, 미니PJT에서는 관리 화면
(전체설계 12절, 정식 개발 단계에서 이 파일을 대신 관리) 없이 이 파일 하나로 구현한다.
반환 값 형태만 유지하면, 나중에 관리 화면이 생겨 설정 출처가 파일에서 DB로 바뀌어도
`agent.py`는 이 함수 하나만 다시 구현하면 되고 Supervisor·어댑터 코드는 그대로다.
"""

from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
_LOAD_PROFILE_PATH = Path(__file__).resolve().parent.parent / "data" / "load_profile.yaml"


def _load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or _CONFIG_PATH
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_source(config_path: Path | None = None) -> dict[str, str]:
    """`config.yaml`의 `source` 항목(점검 대상 프로젝트 루트)을 읽어 반환한다.

    전체설계 12절 "관리 화면"이 정식 개발 단계에서 관리할 정보를 미니PJT에서는 이 파일로
    대신한다. **(결정, 2026-09-03 — 사용자 요청)** 예전엔 언어별로 `sources.<language>`
    를 따로 뒀지만, 언어는 이제 이 루트 아래 파일을 스캔해 자동 감지하므로(`agent.py`의
    `_detect_languages()`) 언어별 경로가 필요 없어졌다 — 프로젝트 전체에 대해 `source`
    하나만 있으면 충분하다. `{"type": "local", "path": ...}`(구현됨) 또는
    `{"type": "git", "url": ...}`(로드맵, 아직 미구현 — `src/tools.py`의 어댑터 생성
    지점이 `NotImplementedError`로 안내한다) 형태다. 항목이 없으면 빈 dict를 반환해
    호출부가 자체 기본 경로를 쓰게 한다.
    """
    return dict(_load_config(config_path).get("source", {}))


def load_except_languages(config_path: Path | None = None) -> list[str]:
    """`config.yaml`의 `exceptLanguages` 목록(자동 감지된 언어 중 점검에서 제외할 언어)을
    읽어 반환한다. 기본값은 빈 리스트 — 감지된 언어는 어댑터가 있는 한 기본적으로 전부
    점검 대상이다."""
    return list(_load_config(config_path).get("exceptLanguages", []))


def load_db_config(config_path: Path | None = None) -> dict[str, Any]:
    """`config.yaml`의 `db` 설정(엔진 종류 + 연결 정보)을 읽어 반환한다(전체설계 3-5-1절
    "db_adapter 레지스트리" — 언어 어댑터와 같은 설정 기반 라우팅 구조). 미니PJT는
    `engine: sqlite`만 실제로 구현했다(CLAUDE.md 10-B절 "유보 사항").

    **필드 집합은 `engine`에 따라 다르다(둘 다 동시에 오지 않음)** — `engine: sqlite`면
    `path`/`schema_path`(파일 경로), 그 외 상용 DB(`oracle`/`edb`/`db2` 등, 아직 어댑터
    미구현)면 `path`/`schema_path` 없이 `host`/`port`/`database`/`user`/`password_ref`
    (커넥션 정보)만 온다 — SQLite는 서버·인증이 없는 임베디드 DB라 커넥션 정보 자체가
    의미 없기 때문이다. 호출부는 반드시 `engine` 값으로 분기해야 하고, 특정 키의 존재
    여부로 엔진을 추측하면 안 된다.
    """
    return dict(_load_config(config_path).get("db", {}))


def load_load_profile(profile_path: Path | None = None) -> dict[str, int]:
    """`data/load_profile.yaml`의 부하 프로파일(`expected_concurrent_users`,
    `requests_per_minute`)을 읽어 반환한다(전체설계 3-5-2절, CLAUDE.md 10-B절)."""
    path = profile_path or _LOAD_PROFILE_PATH
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def is_live_probe_enabled(config_path: Path | None = None) -> bool:
    """`config.yaml`의 `live_probe` 플래그(pentest/load-test 실제 HTTP 프로빙 활성화 여부,
    전체설계 10-0절/CLAUDE.md 10-C절)를 읽어 반환한다. 기본값 `False` — 로컬이라도 서버
    프로세스를 띄우는 부수효과가 있어 꺼진 상태를 기본으로 둔다."""
    return bool(_load_config(config_path).get("live_probe", False))


def load_staging_config(config_path: Path | None = None) -> dict[str, Any]:
    """`config.yaml`의 `staging` 설정(모의해킹/부하테스트 대상 서버 주소, CLAUDE.md 10-N절)을
    읽어 반환한다.

    `base_url`이 있으면 그 주소를 그대로 쓰고 로컬 서브프로세스를 띄우지 않는다 — 실제
    배포에서 **조직이 이미 운영 중인 스테이징/테스트 서버**를 가리키는 용도다. 없으면
    (기본값) 이 프로젝트 안의 더미 스테이징 앱(`data/staging_app`)을 로컬 `uvicorn`
    서브프로세스로 자동 기동한다 — 미니PJT 실증 전용 지름길이다.

    **(결정, 2026-09-04 — 사용자 지적) 소스 경로나 git 저장소 위치로부터 서버를 자동으로
    빌드·기동하는 기능은 의도적으로 두지 않는다** — 임의의 외부 프로젝트를 어떻게 빌드하고
    띄우는지는 프로젝트마다 다르고, 이를 자동화하면 신뢰할 수 없는 빌드/설치 스크립트를
    그대로 실행하는 것과 같아 임의 코드 실행 위험이 크다. 항상 사람이 미리 등록한
    `base_url`(이미 떠 있는 서버의 주소)만 받는다 — `db`/`source` 설정과 같은 원칙이다.
    """
    return dict(_load_config(config_path).get("staging", {}))
