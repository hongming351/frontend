#!/usr/bin/env python3
"""
简单的阿里云SMS测试脚本
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入必要的模块
from dotenv import load_dotenv
load_dotenv()

from sms_aliyun_config import send_aliyun_sms
from config import Config

def main():
    print("🚀 阿里云SMS快速测试")
    print(f"SMS启用状态: {Config.SMS_ENABLED}")
    print(f"AccessKey配置: {'✅ 已配置' if Config.SMS_API_KEY else '❌ 未配置'}")

    if Config.SMS_ENABLED:
        print("\n请先在 .env 文件中配置阿里云信息后再测试")
        print("参考 ALIYUN_SMS_SETUP_GUIDE.md 获取配置说明")
    else:
        print("\n当前处于模拟发送模式，运行完整测试：")
        result = send_aliyun_sms("13800138000", "123456")
        print(f"\n测试结果: {result}")

if __name__ == "__main__":
    main()