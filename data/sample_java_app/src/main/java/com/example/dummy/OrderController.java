package com.example.dummy;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;

/**
 * 코드 품질 점검 Agent 실습용 더미 소스.
 */
public class OrderController {

    private final Connection connection;

    public OrderController(Connection connection) {
        this.connection = connection;
    }

    // 보안 위반(의도적, IDOR — 깨진 객체 수준 권한 부여 / OWASP API1:2023):
    // 요청으로 받은 orderId의 주문을 currentUserId 소유인지 검증하지 않고 그대로 조회해 반환함.
    // 숫자 orderId를 그대로 조회할 뿐 문자열 결합이 아니라서 SQL Injection은 아니고,
    // PMD/SpotBugs/eslint 같은 정적 분석 도구는 패턴 매칭 대상이 없어 원천적으로 못 잡는
    // 비즈니스 로직 취약점입니다 — 실제로는 다른 사용자의 orderId를 순차적으로 넣어보는
    // 모의해킹에서 드러납니다.
    public ResultSet getOrder(long orderId, long currentUserId) throws Exception {
        Statement statement = connection.createStatement();
        String query = "SELECT * FROM orders WHERE id = " + orderId;
        return statement.executeQuery(query);
        // 조회된 주문의 소유자(user_id)와 currentUserId를 비교하는 검증이 없음 — 의도적 누락
    }
}
