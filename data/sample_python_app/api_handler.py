"""API 요청을 처리하는 더미 핸들러 — 확장 phase 5-1-A 점검 대상 소스.

bandit이 잡아야 하는 명령어 주입(security)과 pylint가 잡아야 하는 미사용 import(error)를
의도적으로 심어, 실제 스캔 결과가 정확히 이 두 건만 나오는지 검증하는 용도다(5-1-A 1번).
Vue3/Java와 같은 원칙으로 performance 카테고리 대상 케이스는 넣지 않는다(Java의 N+1이
여전히 이 카테고리의 유일한 케이스).
"""

import os
import sys


class ApiHandler:
    """사용자 요청을 처리하는 더미 API 핸들러."""

    def ping_host(self, hostname: str) -> None:
        """사용자가 입력한 호스트에 ping을 보낸다.

        입력 검증이나 이스케이프 없이 셸 명령 문자열에 그대로 결합해 실행한다 — 명령어
        주입(command injection) 취약점이다.
        """
        os.system("ping -c 1 " + hostname)
