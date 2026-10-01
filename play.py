def is_ok(s):
    stack = []
    for c in s:
        if c == '(':
            stack.append(c)
        else:
            if not stack:
                return False
            stack.pop()
    return not stack
print(is_ok("()"))     # 猜：
print(is_ok("("))      # 猜：
print(is_ok(")("))     # 猜：
print(is_ok("(())"))   # 猜：
def is_ok(s):
    stack = []
    for c in s:
        if c == '(' or c == '[':
            stack.append(c)              # 两种左括号都放盘子
        elif c == ')':
            if not stack or stack.pop() != '(':
                return False             # 关门时必须弹出来的是 ( 才行
        elif c == ']':
            if not stack or stack.pop() != '[':
                return False
    return not stack
print(is_ok("([])()[]"))