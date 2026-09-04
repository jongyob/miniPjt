package com.example.dummy;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

/**
 * 코드 품질 점검 Agent 실습용 더미 소스 — 점검 대상 소스 다양화(2026-09-03, 사용자 요청).
 */
public class ProductService {

    private final Connection connection;

    public ProductService(Connection connection) {
        this.connection = connection;
    }

    // 의도적으로 문제가 없는 "깨끗한" 메서드: 표준 PreparedStatement로 파라미터를 바인딩해
    // SQL Injection을 막고, 조회 조건에 currentUserId(소유자)까지 포함해 IDOR도 막는다.
    // java_lite_adapter가 이제 발견된 .java 파일을 전부 자동으로 리뷰하므로, 문제 없는
    // 파일에서 findings를 지어내지 않는지(오탐 방지) 확인하는 용도다.
    public ResultSet getProductForUser(long productId, long currentUserId) throws Exception {
        PreparedStatement statement = connection.prepareStatement(
                "SELECT * FROM products WHERE id = ? AND owner_id = ?");
        statement.setLong(1, productId);
        statement.setLong(2, currentUserId);
        return statement.executeQuery();
    }
}
