#!/usr/bin/env python3
"""
密码重置功能测试脚本
测试邮件和短信验证码发送功能
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.password_reset_service import send_verification_code, PasswordResetService

def test_email_sending():
    """测试邮件发送功能"""
    print("=== 测试邮箱验证码发送 ===")
    token = "123456"  # 测试验证码
    email = "test@example.com"

    print(f"模拟发送验证码到邮箱: {email}")
    result = send_verification_code('email', email, token)

    if result:
        print("✅ 邮件发送测试成功")
    else:
        print("❌ 邮件发送测试失败")

    return result

def test_sms_sending():
    """测试短信发送功能"""
    print("\n=== 测试手机验证码发送 ===")
    token = "654321"  # 测试验证码
    phone = "13800138000"

    print(f"模拟发送验证码到手机号: {phone}")
    result = send_verification_code('telenum', phone, token)

    if result:
        print("✅ 短信发送测试成功")
    else:
        print("❌ 短信发送测试失败")

    return result

def test_verification_flow():
    """测试完整的验证流程"""
    print("\n=== 测试完整密码重置流程 ===")

    service = PasswordResetService()

    # 测试生成验证码
    username = "testuser"
    user_role = "student"
    contact_type = "telenum"
    contact_value = "13800138001"

    token = service.create_password_reset_token(username, user_role, contact_type, contact_value)

    if token:
        print(f"✅ 生成验证码成功: {token}")

        # 测试发送验证码
        result = send_verification_code(contact_type, contact_value, token)
        if result:
            print("✅ 验证码发送成功")

            # 测试验证码验证
            success, message = service.verify_token(username, user_role, token)
            if success:
                print("✅ 验证码验证成功")
            else:
                print(f"❌ 验证码验证失败: {message}")
        else:
            print("❌ 验证码发送失败")
    else:
        print("❌ 生成验证码失败")

def main():
    """主测试函数"""
    print("开始测试密码重置功能...\n")

    # 测试邮件发送
    test_email_sending()

    # 测试短信发送
    test_sms_sending()

    # 测试完整流程
    test_verification_flow()

    print("\n" + "="*50)
    print("测试完成！")
    print("注意：如果SMTP/SMS配置为空，会显示模拟发送结果。")

if __name__ == "__main__":
    main()