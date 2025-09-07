#!/usr/bin/env python
# -*- coding: utf-8 -*-
print("测试开始...")

# 测试基本的字典操作
test_case = {"id": 1, "input": "test", "output": "expected"}
print(f"test_case.get('input'): {test_case.get('input')}")
print(f"test_case.get('output'): {test_case.get('output')}")
print(f"'input' in test_case: {'input' in test_case}")
print(f"'output' in test_case: {'output' in test_case}")

# 测试failed_cases字符串
try:
    failed_cases_string = 'failed_cases'
    print(f"字符串: {failed_cases_string}")
except Exception as e:
    print(f"错误: {e}")

print("测试完成")