#!/usr/bin/env python3
"""
阿里云短信服务快速测试脚本
不用启动完整应用就能测试短信发送功能
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 导入阿里云SMS服务
    from sms_aliyun_config import AliyunSmsService
    from config import Config

    def test_sms_config():
        """测试阿里云SMS配置"""
        print("🔍 检查阿里云SMS配置...\n")

        service = AliyunSmsService()

        print("📋 配置信息:")
        print(f"   AccessKey ID: {Config.SMS_API_KEY[:8]}...{'****' if Config.SMS_API_KEY else '未配置'}")
        print(f"   SMS启用状态: {'✅ 已启用' if Config.SMS_ENABLED else '❌ 已禁用'}")
        print(f"   服务提供商: {Config.SMS_PROVIDER}")
        print(f"   短信签名: {Config.SMS_SIGN_NAME}")
        print(f"   模板ID: {Config.SMS_TEMPLATE_CODE}")
        print()

        return Config.SMS_ENABLED

    def test_sms_sending():
        """测试短信发送"""
        print("📱 开始测试阿里云SMS发送...\n")

        test_phone = input("请输入测试手机号（格式：13800138000）: ").strip()
        if not test_phone:
            print("❌ 手机号不能为空")
            return

        # 生成测试验证码
        import random
        test_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        print(f"\n生成测试验证码: {test_code}")

        # 调用阿里云SMS服务
        from sms_aliyun_config import send_aliyun_sms

        try:
            result = send_aliyun_sms(test_phone, test_code)

            if result.get('success'):
                print("✅ 发送成功!")
                print(f"   请求ID: {result.get('request_id', 'N/A')}")
                print("\n请检查手机号是否收到短信!")
            else:
                print("❌ 发送失败:")
                print(f"   错误信息: {result.get('message', '未知错误')}")

        except Exception as e:
            print(f"❌ 发送异常: {e}")

    def test_simulation_mode():
        """测试模拟模式"""
        print("\n🧪 测试模拟发送模式...")
        print("如果不想实际发送短信，可以启用模拟模式")

        print("\n模拟发送结果:")
        print("=" * 60)
        print("短信验证码（模拟发送）")
        print("手机号: 138****8000")
        print("验证码: 123456")
        print("内容: 您的密码重置验证码为：123456，有效期 10 分钟")
        print("=" * 60)

    def main():
        """主测试程序"""
        print("🚀 阿里云SMS服务测试工具\n")

        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()

        # 测试配置
        sms_enabled = test_sms_config()

        if sms_enabled:
            choice = input("\n选择测试模式:\n1. 实际发送测试短信\n2. 模拟发送演示\n请选择 (1或2): ").strip()

            if choice == '1':
                test_sms_sending()
            else:
                test_simulation_mode()
        else:
            print("💡 提示: SMS服务目前被禁用，使用模拟发送模式")
            test_simulation_mode()

        print("\n🎯 测试完成！")
        print("如果遇到问题，请参考 ALIYUN_SMS_SETUP_GUIDE.md 文档")

    if __name__ == "__main__":
        main()

except ImportError as e:
    print("❌ 导入失败，请确保所有依赖已安装")
    print(f"错误信息: {e}")
    print("请检查 sms_aliyun_config.py 文件是否存在"