"""
숫자 연산만 허용하는 안전한 산술 평가 (eval 금지).

허용: + - * / % **, 괄호, 단항 +/-, 정수·실수.
금지: 이름·함수 호출·속성 접근 등 임의 코드 실행.
"""

from __future__ import annotations

import ast
import operator

Number = int | float

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def evaluate_arithmetic(expression: str) -> Number:
    """표현식 문자열을 안전하게 평가합니다."""
    if not expression or not expression.strip():
        raise ValueError("빈 식입니다.")
    tree = ast.parse(expression.strip(), mode="eval")
    if not isinstance(tree, ast.Expression):
        raise ValueError("지원하지 않는 구문입니다.")
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):  # bool은 int의 서브클래스이므로 먼저 거름
            raise ValueError("불리언은 허용되지 않습니다.")
        if isinstance(node.value, int):
            return node.value
        if isinstance(node.value, float):
            return node.value
        raise ValueError("숫자만 허용됩니다.")

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            v = _eval_node(node.operand)
            return -v
        if isinstance(node.op, ast.UAdd):
            return _eval_node(node.operand)
        raise ValueError("지원하지 않는 단항 연산입니다.")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BINOPS:
            raise ValueError("지원하지 않는 이항 연산입니다.")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        fn = _BINOPS[op_type]
        return fn(left, right)

    raise ValueError("허용되지 않는 표현식입니다.")
