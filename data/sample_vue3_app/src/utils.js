// 코드 품질 점검 Agent 실습용 더미 소스 — eslint가 잡아내도록 위반 패턴을 의도적으로 심음

export function runUserExpression(expr) {
  // 보안 위반(의도적): eval 사용
  return eval(expr)
}

export function buildGreeting(name) {
  const unusedVariable = 'this value is never read' // 미사용 변수(의도적)
  return `Hello, ${name}!`
}
