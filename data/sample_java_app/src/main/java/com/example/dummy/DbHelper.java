package com.example.dummy;

import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.Statement;

/**
 * 코드 품질 점검 Agent 실습용 더미 소스.
 */
public class DbHelper {

    private final Connection connection;

    public DbHelper(Connection connection) {
        this.connection = connection;
    }

    // 원시 SQL 문자열을 그대로 실행하는 사내 공용 DB 헬퍼(실제 회사 코드에서 흔한 "직접 만든
    // JDBC 래퍼" 패턴을 흉내냄). SpotBugs/Semgrep의 기본 룰셋은 java.sql.Statement/
    // PreparedStatement 같은 표준 JDBC API 호출 지점만 SQL 실행 지점(sink)으로 인식하므로,
    // 이런 사내 래퍼를 SQL 실행 지점으로 잡으려면 팀이 직접 커스텀 룰을 추가해야 합니다 —
    // 안 하면 기본 설정으로는 이 메서드를 거치는 호출부의 SQL Injection을 놓칩니다.
    public ResultSet executeRaw(String sql) throws Exception {
        Statement statement = connection.createStatement();
        return statement.executeQuery(sql);
    }
}
