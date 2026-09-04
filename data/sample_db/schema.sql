-- 코드 품질 점검 Agent 실습용 더미 DB 스키마 (CLAUDE.md 10-B절 참고).
-- data/sample_java_app이 다루는 도메인(users/orders/order_items)에 맞춤.
-- 이 파일만 커밋 대상이고, 실제 .db 파일은 db_adapter가 매 실행 시 이 스크립트로
-- 새로 만든다(고정 산출물로 커밋하지 않음).

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 의도적으로 order_id에 인덱스를 두지 않음 — OrderService.java의 N+1(반복문 안에서
-- order_id로 매번 조회)이 실제로 풀스캔을 유발한다는 근거가 EXPLAIN QUERY PLAN 결과에
-- 드러나게 하기 위함(CLAUDE.md 10-B절).
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

INSERT INTO users (id, name, email) VALUES
    (1, 'Alice', 'alice@example.com'),
    (2, 'Bob', 'bob@example.com'),
    (3, 'Carol', 'carol@example.com');

INSERT INTO orders (id, user_id, created_at) VALUES
    (1, 1, '2026-01-01'),
    (2, 1, '2026-01-02'),
    (3, 2, '2026-01-03'),
    (4, 3, '2026-01-04'),
    (5, 3, '2026-01-05');

INSERT INTO order_items (order_id, product_name) VALUES
    (1, 'Keyboard'), (1, 'Mouse'),
    (2, 'Monitor'),
    (3, 'Desk'), (3, 'Chair'), (3, 'Lamp'),
    (4, 'Webcam'),
    (5, 'Headset'), (5, 'Microphone');
