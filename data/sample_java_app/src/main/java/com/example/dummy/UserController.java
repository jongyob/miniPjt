package com.example.dummy;

import java.sql.ResultSet;

/**
 * 코드 품질 점검 Agent 실습용 더미 소스.
 */
public class UserController {

    private final DbHelper dbHelper;

    public UserController(DbHelper dbHelper) {
        this.dbHelper = dbHelper;
    }

    // 보안 위반(의도적, SQL Injection): 사용자 입력을 검증/파라미터 바인딩 없이 쿼리 문자열에
    // 직접 결합해 사내 공용 DbHelper.executeRaw()로 그대로 실행함. DbHelper는 java.sql.Statement를
    // 감싼 사내 유틸리티라, SpotBugs/Semgrep의 기본(커스텀 룰 없는) 설정으로는 이 호출을 SQL
    // 실행 지점으로 인식하지 못해 놓치기 쉽습니다 — 실제로는 이런 사내 래퍼 때문에 정적
    // 스캐너가 통과시킨 SQL Injection이 나중에 모의해킹에서 발견되는 경우가 흔합니다.
    public ResultSet findUserByName(String username) throws Exception {
        String query = "SELECT * FROM users WHERE username = '" + username + "'";
        return dbHelper.executeRaw(query);
    }
}
