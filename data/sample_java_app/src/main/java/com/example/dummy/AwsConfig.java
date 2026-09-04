package com.example.dummy;

/**
 * 코드 품질 점검 Agent 실습용 더미 소스.
 */
public class AwsConfig {

    // 보안 위반(의도적): 하드코딩된 자격증명 — 실제 키가 아닌 가짜 값(시크릿 마스킹 동작 확인용)
    public static final String AWS_ACCESS_KEY_ID = "AKIA_DUMMY_EXAMPLE1234";
    public static final String AWS_SECRET_ACCESS_KEY = "dummySecretKeyExample1234567890abcdEFGH";

    public static String getAccessKeyId() {
        return AWS_ACCESS_KEY_ID;
    }
}
