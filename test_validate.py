#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试validate_test_cases函数的简单脚本
"""
import sys
import os
sys.path.append('.')

# 模拟参考代码
reference_code = '''
import java.util.Scanner;

public class HouseRobber {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        int n = scanner.nextInt();
        int[] nums = new int[n];
        for (int i = 0; i < n; i++) {
            nums[i] = scanner.nextInt();
        }

        if (n == 0) {
            System.out.println(0);
            return;
        }
        if (n == 1) {
            System.out.println(nums[0]);
            return;
        }

        int[] dp = new int[n];
        dp[0] = nums[0];
        dp[1] = Math.max(nums[0], nums[1]);

        for (int i = 2; i < n; i++) {
            dp[i] = Math.max(dp[i-1], dp[i-2] + nums[i]);
        }

        System.out.println(dp[n-1]);
    }
}
'''

# 模拟测试用例数据（包含id字段）
test_cases = [
    {"id": 1, "input": "4\n1 2 3 1", "output": "4"},
    {"id": 2, "input": "5\n2 7 9 3 1", "output": "12"},
    {"id": 3, "input": "1\n5", "output": "5"}
]

# 模拟简单的validate_test_cases函数
def simple_test_validate():
    """简单的测试函数来验证测试用例格式"""
    print("测试validate_test_cases函数...")
    print(f"参考代码长度: {len(reference_code)} 字符")
    print(f"测试用例数量: {len(test_cases)}")

    for i, test_case in enumerate(test_cases):
        print(f"\n测试用例 {i+1}:")
        print(f"  ID: {test_case.get('id')}")
        print(f"  Input: {test_case.get('input')}")
        print(f"  Expected Output: {test_case.get('output')}")

        # 检查字段是否存在
        if 'input' in test_case and 'output' in test_case:
            print("  ✓ 字段完整")
        else:
            print("  ✗ 字段不完整")

if __name__ == "__main__":
    simple_test_validate()