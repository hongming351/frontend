#!/usr/bin/env python3
"""
阿里云短信服务配置示例
配置方法：
1. 访问 https://dysms.console.aliyun.com/
2. 开通短信服务
3. 创建AccessKey（在阿里云控制台-用户管理-AccessKey管理）
4. 添加签名和模板
"""

import os
import hmac
import hashlib
import base64
import urllib.parse
import time
import uuid
import requests
from config import Config

class AliyunSmsService:
    """阿里云短信服务"""

    def __init__(self):
        # API配置
        self.access_key_id = Config.SMS_API_KEY or os.environ.get('ALIYUN_ACCESS_KEY_ID', '')
        self.access_key_secret = Config.SMS_SECRET or os.environ.get('ALIYUN_ACCESS_KEY_SECRET', '')
        self.endpoint = 'https://dysmsapi.aliyuncs.com/'

        # 短信配置
        self.sign_name = os.environ.get('ALIYUN_SMTP_SIGN_NAME', '您的应用名称')
        self.template_code = os.environ.get('ALIYUN_SMTP_TEMPLATE_CODE', 'SMS_123456789')

        # 验证配置
        if not self.access_key_id or not self.access_key_secret:
            print("⚠️  阿里云API密钥未配置，将使用模拟发送")

    def send_verification(self, phone_number, code):
        """
        发送验证码短信

        Args:
            phone_number: 手机号码（带国际区号，如+8613800000000）
            code: 验证码字符串

        Returns:
            dict: 返回结果 {'success': bool, 'message': str, 'request_id': str}
        """
        if not self.access_key_id or not self.access_key_secret:
            # 模拟发送
            print(f"\n{'='*50}")
            print("📱 阿里云短信服务 - 模拟发送")
            print(f"📞 手机号码: {phone_number}")
            print(f"🔢 验证码: {code}")
            print(f"📝 短信签名: {self.sign_name}")
            print(f"📄 模板ID: {self.template_code}")
            print(f"{'='*50}\n")
            return {
                'success': True,
                'message': '模拟发送成功',
                'request_id': str(uuid.uuid4())
            }

        try:
            # 构建请求参数
            params = {
                'AccessKeyId': self.access_key_id,
                'Format': 'JSON',
                'RegionId': 'cn-hangzhou',
                'SignatureMethod': 'HMAC-SHA1',
                'SignatureNonce': str(uuid.uuid4()),
                'Timestamp': self._get_utc_timestamp(),
                'Action': 'SendSms',
                'Version': '2017-05-25',
                'SignName': self.sign_name,
                'TemplateCode': self.template_code,
                'PhoneNumbers': phone_number,
                'TemplateParam': f'{{"code":"{code}","time":"{5}"}}'  # 5分钟有效期
            }

            # 添加签名
            signature = self._create_signature(params)
            params['Signature'] = signature

            # 发送请求
            response = requests.post(self.endpoint, data=params, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get('Code') == 'OK':
                    return {
                        'success': True,
                        'message': '发送成功',
                        'request_id': result.get('RequestId', '')
                    }
                else:
                    return {
                        'success': False,
                        'message': result.get('Message', f'API错误: {result.get("Code", "Unknown")}'),
                        'request_id': result.get('RequestId', '')
                    }
            else:
                return {
                    'success': False,
                    'message': f'HTTP错误: {response.status_code}',
                    'request_id': ''
                }

        except Exception as e:
            print(f"阿里云SMS发送异常: {e}")
            return {
                'success': False,
                'message': f'发送失败: {str(e)}',
                'request_id': ''
            }

    def _get_utc_timestamp(self):
        """获取UTC格式时间戳"""
        from datetime import datetime
        import time
        return datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')

    def _create_signature(self, params):
        """创建API签名"""
        # 对参数进行排序并编码
        sorted_params = sorted(params.items(), key=lambda item: item[0])
        canonicalized_query_string = '&'.join([
            urllib.parse.quote(key, safe='') + '=' + urllib.parse.quote(str(value), safe='')
            for key, value in sorted_params
        ])

        # 构建签名字符串
        string_to_sign = 'POST&%2F&' + urllib.parse.quote(canonicalized_query_string, safe='')

        # 计算HMAC-SHA1签名
        key = (self.access_key_secret + '&').encode('utf-8')
        message = string_to_sign.encode('utf-8')
        signature = hmac.new(key, message, hashlib.sha1).digest()
        signature_base64 = base64.b64encode(signature).decode('utf-8')

        return signature_base64

# 全局阿里云短信服务实例
aliyun_sms_service = AliyunSmsService()

# 便捷函数
def send_aliyun_sms(phone, code):
    """发送阿里云短信验证码"""
    return aliyun_sms_service.send_verification(phone, code)

if __name__ == "__main__":
    # 测试代码
    print("阿里云短信服务测试")
    result = send_aliyun_sms("13800138000", "123456")
    print(f"发送结果: {result}")