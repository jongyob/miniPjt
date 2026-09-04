"""IDOR·부하테스트 실증용 최소 스테이징 앱 (전체설계 10-0절/3-5-3절, mini-pjt_이종엽 확장
phase 5-2). `OrderController.java`/`OrderService.java`(정적 리뷰 대상)와 같은 취약점을
실제로 살아있는 서버로 재현해, `pentest_agent`/`load_test_agent` 역할의 도구(`src/tools.py`
의 `probe_idor_vulnerability()`/`run_concurrent_load_test()`)가 표준 HTTP 클라이언트로
진짜 요청을 보내 검증할 수 있게 한다.

**안전 경계**: 이 앱은 `127.0.0.1`에만 바인딩되고(`src/tools.py`의 `_ensure_staging_server()`
참고), 상태를 바꾸는 엔드포인트(POST/PUT/DELETE)가 아예 없다 — GET만 존재해 프로빙 자체가
구조적으로 읽기 전용이다. 외부 프로젝트/운영 서버를 대상으로 하지 않는다(전체설계 10-0절
"안전 경계" 원칙).
"""

import threading
import time

from fastapi import FastAPI

app = FastAPI()

# `OrderService.java`가 접속하는 DB의 작은 커넥션 풀(전체설계 3-5-1/3-5-2절 "커넥션 풀
# 크기 20 초과 가능성" 시나리오)을 흉내낸 세마포어 — 동시에 5개 요청만 "커넥션"을 잡을 수
# 있다. 실제 DB 없이도, 동시 요청이 이 용량을 넘으면 대기 시간이 누적돼 부하테스트로 병목이
# 드러나는 것을 재현한다.
_CONNECTION_POOL = threading.Semaphore(5)

# 고정 시드 데이터 — OrderController.java의 도메인(주문은 특정 user_id 소유)을 그대로 재현.
_ORDERS = {
    1: {"id": 1, "user_id": 1, "product_name": "Keyboard"},
    2: {"id": 2, "user_id": 1, "product_name": "Mouse"},
    3: {"id": 3, "user_id": 2, "product_name": "Monitor"},
    4: {"id": 4, "user_id": 3, "product_name": "Desk"},
}


@app.get("/orders/{order_id}")
def get_order(order_id: int, current_user_id: int):
    """`OrderController.java#getOrder()`와 같은 취약점(IDOR)을 그대로 재현한다 — 의도적으로
    `order["user_id"] == current_user_id` 소유권 검증을 하지 않고 그대로 반환한다."""
    order = _ORDERS.get(order_id)
    if order is None:
        return {"error": "not found"}
    return order


@app.get("/orders/{order_id}/items")
def get_order_items(order_id: int):
    """`OrderService.java`의 N+1이 실제 DB 풀스캔으로 유발하는 지연을 커넥션 풀 경합까지
    포함해 흉내낸 더미 엔드포인트 — 부하테스트 대상. `_CONNECTION_POOL`(용량 5)을 잡은 채
    0.1초 "쿼리"를 수행하므로, 동시 요청이 5건을 넘으면 뒤 요청은 그만큼 대기가 누적된다."""
    with _CONNECTION_POOL:
        time.sleep(0.1)
    return {"order_id": order_id, "items": ["item-a", "item-b"]}
