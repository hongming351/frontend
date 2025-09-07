#!/usr/bin/env python3
"""
检查数据库表结构脚本
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

def check_table_structure():
    """检查password_reset_tokens表的结构"""
    try:
        # 查询表结构
        result = db.execute_query("""
        SHOW CREATE TABLE password_reset_tokens
        """)

        if result:
            print("=== password_reset_tokens 表结构 ===")
            print(result[0]['Create Table'])
        else:
            print("❌ 表不存在")

        # 检查列的具体信息
        columns_result = db.execute_query("""
        SHOW COLUMNS FROM password_reset_tokens
        """)

        if columns_result:
            print("\n=== 列详细信息 ===")
            for col in columns_result:
                print(f"- {col['Field']}: {col['Type']} ({col['Null']}) {col['Default'] or 'NULL'}")

        # 检查索引信息
        index_result = db.execute_query("""
        SHOW INDEX FROM password_reset_tokens
        """)

        if index_result:
            print("\n=== 索引信息 ===")
            for idx in index_result:
                print(f"- {idx['Key_name']}: {idx['Column_name']} ({idx['Index_type']})")

        return True

    except Exception as e:
        print(f"❌ 查询表结构失败: {e}")
        return False

if __name__ == "__main__":
    print("正在检查数据库表结构...")
    check_table_structure()