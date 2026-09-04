# 3일차 3번 — RAGAS 평가 지표 결과

## 모델별 토큰 사용량

| 모델 | 호출 수 | 입력 토큰 | 출력 토큰 | 총 토큰 |
|---|---|---|---|---|
| `global.anthropic.claude-sonnet-4-6` | 16 | 26,084 | 3,493 | 29,577 |
| `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 9 | 18,099 | 2,100 | 20,199 |

**전체 합계: 49,776 토큰**

## 지표별 평균 점수 (전체 23문항)

| 지표 | 평균 |
|---|---|
| `context_recall` | 0.192 |
| `context_precision` | 0.238 |
| `faithfulness` | 0.126 |
| `answer_relevancy` | 0.354 |

## 문항별 상세 점수

| id | category | context_recall | context_precision | faithfulness | answer_relevancy |
|---|---|---|---|---|---|
| Q1 | positive | 0.000 | 0.000 | 0.000 | 0.779 |
| Q2 | positive | 0.000 | 0.000 | 0.387 | 0.334 |
| Q3 | positive | 0.250 | 0.241 | 0.167 | 0.537 |
| Q4 | positive | 1.000 | 0.417 | 0.154 | 0.532 |
| Q5 | positive | 0.500 | 0.500 | 0.143 | 0.000 |
| Q6 | positive | 0.000 | 0.000 | 0.222 | 0.249 |
| Q7 | negative | 0.000 | 0.000 | 0.000 | 0.812 |
| Q8 | negative | 0.000 | 0.000 | 0.333 | 0.593 |
| Q9 | negative | 0.000 | 0.000 | 0.000 | 0.579 |
| Q10 | edge | 0.000 | 0.000 | 0.071 | 0.568 |
| Q11 | edge | 1.000 | 1.000 | 0.160 | 0.677 |
| Q12 | edge | 1.000 | 0.812 | 0.000 | 0.495 |
| Q13 | edge | 0.000 | 0.000 | 0.167 | 0.683 |
| Q14 | guardrail | 0.000 | 0.167 | 0.000 | 0.000 |
| Q15 | guardrail | 0.000 | 0.167 | 0.000 | 0.000 |
| Q16 | positive | 0.000 | 0.200 | 0.000 | 0.000 |
| Q17 | positive | 0.333 | 0.111 | 0.433 | 0.000 |
| Q18 | positive | 0.000 | 1.000 | 0.321 | 0.000 |
| Q19 | positive | 0.000 | 0.111 | 0.207 | 0.563 |
| Q20 | positive | 0.333 | 0.250 | 0.143 | 0.000 |
| Q21 | positive | 0.000 | 0.167 | 0.000 | 0.000 |
| Q22 | edge | 0.000 | 0.125 | 0.000 | 0.000 |
| Q23 | positive | 0.000 | 0.196 | 0.000 | 0.741 |

## 알려진 제약

- `reference`(ground truth)는 `test_queries.csv`의 `note` 필드를 그대로 재사용한다 — 스키마에 정답 문장 전용 컬럼이 없어서다(조건 8 1순위, 계획 문서 참고). `note`에는 판정 기준 설명·배경 문장이 섞여 있어 순수 정답 문장보다 노이즈가 있다.
- `retrieved_contexts`는 `POST /query`의 `contexts` 필드를 그대로 쓰는데, 이 필드는 질문과 무관하게 **그 시점의 findings 전체**를 담는다(API 스펙 고정, `agent.py`가 질문 내용과 무관하게 항상 3개 카테고리를 전부 스캔하는 설계와 동일한 이유) — 특정 질문에 대해 좁혀진 검색 결과가 아니므로, `context_precision`이 실제 응답 품질보다 낮게 나올 수 있다.
- negative/guardrail 카테고리(Q7-9, Q14-15 등)처럼 범위 밖 요청을 정직하게 거절하는 게 정답인 문항은, `note`가 '거절해야 한다'는 취지 설명이라 이 문항에 대한 `context_recall`/`context_precision` 수치는 문자 그대로의 사실 일치도보다는 근사값으로 해석해야 한다.
- `ragas.evaluate()`(배치 API) 대신 각 지표의 `single_turn_score()`를 문항마다 직접 호출한다 — Python 3.14 + `nest_asyncio` 조합에서 `evaluate()`가 `RuntimeError: Timeout should be used inside a task`로 깨지는 것을 실측 확인했다. 결과값은 동일하고 실행 경로만 다르다.
