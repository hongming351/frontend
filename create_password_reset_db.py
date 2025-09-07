#!/usr/bin/env python3
"""
创建密码重置表脚本
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import db

def create_password_reset_table():
    """创建密码重置表"""
    try:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            user_role ENUM('student', 'teacher', 'admin') NOT NULL,
            contact_type VARCHAR(20) NOT NULL,  -- 'email' 或 'telenum'
            contact_value VARCHAR(100) NOT NULL,
            verification_token VARCHAR(10) NOT NULL,  -- 6位验证码
            token_hash VARCHAR(64) NOT NULL,  -- 验证码的MD5哈希
            expires_at DATETIME NOT NULL,
            status ENUM('active', 'used', 'expired') DEFAULT 'active',
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at DATETIME NULL,

            INDEX idx_username_role (username, user_role),
            INDEX idx_token_hash (token_hash),
            INDEX idx_contact (contact_type, contact_value),
            INDEX idx_expires_at (expires_at),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        print("正在创建 password_reset_tokens 表...")
        db.execute_update(create_table_sql)
        print("✅ 密码重置表创建成功！")

        return True

    except Exception as e:
        print(f"❌ 创建表失败: {e}")
        return False

if __name__ == "__main__":
    print("开始创建密码重置数据库表...")
    if create_password_reset_table():
        print("\n🎉 数据库表创建完成！")
    else:
        print("\n💥 数据库表创建失败！")