"""문자열 유틸리티 — 점검 대상 소스 다양화(2026-09-03, 사용자 요청).

의도적 취약점이 없는 "깨끗한" 파일이다 — bandit/pylint가 여기서는 아무것도 잡지 않아야
한다(java_lite_adapter가 이제 발견된 파일을 전부 자동으로 리뷰하는 것처럼, bandit/pylint
도 `sample_python_app/` 전체를 스캔하므로, 문제 없는 파일에서 오탐이 안 나는지 확인하는
용도다).
"""


def slugify(text: str) -> str:
    """문자열을 URL-safe 슬러그로 변환한다."""
    return "-".join(text.strip().lower().split())


def truncate(text: str, max_length: int = 100) -> str:
    """문자열을 최대 길이로 자르고 말줄임표를 붙인다."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
