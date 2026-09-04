# 코드 품질 리포트

## 모델별 토큰 사용량

| 모델 | 호출 수 | 입력 토큰 | 출력 토큰 | 총 토큰 |
|---|---|---|---|---|
| `global.anthropic.claude-sonnet-4-5-20250929-v1:0` | 3 | 12,480 | 1,302 | 13,782 |
| `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 6 | 12,345 | 1,255 | 13,600 |

**전체 합계: 27,382 토큰**

감지된 언어: C(점검불가), Csharp(점검불가), Java 1.8, Python, Vue3(점검제외)

총 8건 — 보안 6 / 오류 1 / 성능 1

## 보안 (6건)

### SEC-1 — [높음] OrderController.java:19

- **문제**: 요청 파라미터로 받은 orderId를 그대로 조회하면서, 그 주문이 currentUserId 소유인지 검증하는 코드가 없습니다. 다른 사용자의 주문 ID를 순차적으로 시도하면 타인의 주문 정보를 열람할 수 있습니다(IDOR, OWASP API1:2023).
- **원인**: 리소스를 조회할 때 소유권(요청자와 실제 소유자가 같은지) 검증이 없습니다.
- **수정 방법**: 조회한 리소스의 소유자 필드와 현재 인증된 사용자를 비교해, 다르면 403을 반환하도록 고치세요.
- 참고: `llm-review`(`idor-missing-ownership-check`)

### SEC-2 — [높음] UserController.java:22

- **문제**: 사용자 입력(username)을 검증·파라미터 바인딩 없이 쿼리 문자열에 직접 결합한 뒤, 사내 공용 DbHelper.executeRaw()로 실행합니다. 악의적인 입력(예: "' OR '1'='1")이 들어오면 SQL Injection이 발생합니다.
- **원인**: 사용자 입력을 검증 없이 SQL 문자열에 직접 결합해 실행합니다.
- **수정 방법**: 파라미터 바인딩(PreparedStatement)으로 바꾸고, 문자열 결합으로 SQL을 만들지 마세요.
- 참고: `llm-review`(`sql-injection-custom-wrapper`)

### SEC-3 — [높음] OrderMapper.xml:21

- **문제**: MyBatis 매퍼에서 정렬 컬럼명을 ${}(문자열 치환)로 처리하고 있습니다. sortColumn에 "id; DROP TABLE orders; --" 같은 악의적인 값이 들어오면 그대로 SQL이 조립되어 실행됩니다. 화이트리스트 검증을 추가하거나, 안전하게 정렬 컬럼을 매핑하는 로직이 필요합니다.
- **원인**: MyBatis에서 ${}(문자열 치환)를 써서 사용자 입력이 SQL에 그대로 삽입됩니다.
- **수정 방법**: 가능한 경우 #{}(파라미터 바인딩)로 바꾸고, 컬럼명처럼 바인딩이 안 되는 값만 화이트리스트로 검증하세요.
- 참고: `llm-review`(`mybatis-dollar-brace-injection`)

### SEC-4 — [높음] sample_python_app/api_handler.py:22

- **문제**: start_process_with_a_shell: Starting a process with a shell, possible injection detected, security issue.
- **원인**: 셸을 거쳐 외부 명령을 실행하면 입력값에 셸 메타문자가 섞였을 때 명령어 주입으로 이어집니다.
- **수정 방법**: subprocess를 shell=False로 호출하고 인자를 리스트로 분리해서 넘기세요.
- 참고: `bandit`(`B605`)

### SEC-6 — [중간] sample_python_app/auth_utils.py:16

- **문제**: blacklist: Use of possibly insecure function - consider using safer ast.literal_eval.
- **원인**: 검증되지 않은 입력을 eval()로 그대로 실행하면 임의 코드 실행으로 이어질 수 있습니다.
- **수정 방법**: eval() 대신 ast.literal_eval() 같은 안전한 파싱 방법을 쓰세요.
- 참고: `bandit`(`B307`)

### SEC-5 — [낮음] sample_python_app/auth_utils.py:8

- **문제**: hardcoded_password_string: Possible hardcoded password = "***MASKED_SECRET***"
- **원인**: 소스 코드에 비밀번호·자격증명이 그대로 하드코딩돼 있습니다.
- **수정 방법**: 값을 환경변수나 시크릿 매니저로 옮기고, 소스에는 참조만 남기세요.
- 참고: `bandit`(`B105`)

## 오류 (1건)

### ERR-1 — [중간] sample_python_app/api_handler.py:10

- **문제**: Unused import sys
- **원인**: 더 이상 쓰이지 않는 import가 남아 있습니다.
- **수정 방법**: 사용하지 않는 import 문을 삭제하세요.
- 참고: `pylint`(`unused-import`)

## 성능 (1건)

### PERF-1 — [높음] OrderService.java:28

- **문제**: 반복문 안에서 orderIds 컬렉션의 각 항목마다 별도의 쿼리를 실행하는 N+1 패턴이 발견되었습니다. order_items 테이블을 order_id 컬럼으로 조회하고 있습니다. orderIds를 IN 절로 한 번에 조회하도록 리팩토링하세요.
- **원인**: 목록을 조회한 뒤 각 항목마다 반복문 안에서 개별 쿼리를 또 실행합니다.
- **수정 방법**: IN 절이나 JOIN으로 한 번에 조회하도록 배치 처리로 바꾸세요.
- 참고: `llm-review`(`n-plus-one-query-in-loop`)
