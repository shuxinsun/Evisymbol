import re

class Node:
    def __init__(self, op, left=None, right=None, leaf_type=None):
        self.op = op            # ADD or LEAF
        self.left = left
        self.right = right
        self.leaf_type = leaf_type  # "SYM" or "CONST"

    def shape(self):
        if self.op == "LEAF":
            return ("LEAF", self.leaf_type)
        return (
            "ADD",
            self.left.shape() if self.left else None,
            self.right.shape() if self.right else None,
        )


def tokenize(expr):
    expr = expr.replace(" ", "")
    return re.findall(r'[A-Za-z_.][A-Za-z0-9_.@]*|0x[0-9a-fA-F]+|\d+|[+\-]', expr)


def is_const(tok):
    return tok.startswith("0x") or tok.isdigit()


def make_leaf(tok):
    if is_const(tok):
        return Node("LEAF", leaf_type="CONST")
    return Node("LEAF", leaf_type="SYM")


def parse_expr(tokens):
    node = make_leaf(tokens[0])
    i = 1
    while i < len(tokens):
        op = tokens[i]  # + or -
        right = make_leaf(tokens[i + 1])

        # + 和 - 统一为 ADD
        node = Node("ADD", node, right)
        i += 2
    return node


def build_ast(label):
    tokens = tokenize(label)
    if not tokens:
        return Node("LEAF", leaf_type="CONST")
    return parse_expr(tokens)


def match_label(pred_label, gt_label):
    """
    结构必须一致，且叶子节点“类型”一致（符号 vs 常量）
    """
    try:
        pred_tree = build_ast(pred_label)
        gt_tree = build_ast(gt_label)
        return pred_tree.shape() == gt_tree.shape()
    except Exception:
        return False
