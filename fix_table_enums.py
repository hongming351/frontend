#!/usr/bin/env python3
"""
修复数据库表枚举值脚本
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

def fix_contact_type_enum():
    """修改contact_type字段的枚举值"""
    try:
        print("正在修改 password_reset_tokens 表的 contact_type 枚举值...")

        # 首先删除现有的枚举约束
        drop_enum_sql = """
        ALTER TABLE password_reset_tokens
        MODIFY COLUMN contact_type VARCHAR(20) NOT NULL COMMENT '联系方式类型：email或telenum'
        """

        print("删除枚举约束...")
        db.execute_update(drop_enum_sql)

        # 然后重建为主键约束，但保持varchar类型
        alter_sql = """
        ALTER TABLE password_reset_tokens
        MODIFY COLUMN contact_type VARCHAR(20) NOT NULL,
        MODIFY COLUMN user_role ENUM('student','teacher','admin') NOT NULL
        """

        print("更新字段定义...")
        db.execute_update(alter_sql)

        print("✅ contact_type 字段修复完成")

        # 验证表结构
        print("\n验证修复结果...")
        result = db.execute_query("DESCRIBE password_reset_tokens")

        print("=== 修复后的字段信息 ===")
        for row in result:
            print(f"{row['Field']}: {row['Type']} (允许NULL: {row['Null']})")

        return True

    except Exception as e:
        print(f"❌ 修复表枚举失败: {e}")
        return False

if __name__ == "__main__":
    print("开始修复数据库表枚举值...")
    if fix_contact_type_enum():
        print("\n🎉 资料库表枚举修复完成！")
        print("现在可以正常使用 'telenum' 作为联系方式类型了。")
    else:
        print("\n💥 数据库表枚举修复失败！")