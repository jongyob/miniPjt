"""더미 인증 유틸리티 — 점검 대상 소스 다양화(2026-09-03, 사용자 요청).

`api_handler.py`의 명령어 주입(B605) 1건 외에, bandit이 잡는 서로 다른 두 가지 보안
패턴(하드코딩된 비밀번호, eval 사용)을 추가로 심어 Python 보안 findings의 종류를 넓힌다.
"""

# 보안 위반(의도적): 하드코딩된 비밀번호 — bandit B105(hardcoded_password_string).
DEFAULT_ADMIN_PASSWORD = "admin1234"


def is_valid_debug_token(token: str) -> bool:
    """디버그 전용으로 만든 더미 토큰 검증기 — 실제 서비스에는 있으면 안 되는 패턴.

    보안 위반(의도적): 외부 입력을 eval()로 그대로 실행 — bandit B307(eval).
    """
    return eval(token)
