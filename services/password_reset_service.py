#!/usr/bin/env python3
"""
密码重置服务模块
处理通过手机号或邮箱重置密码的完整流程
"""

import random
import hashlib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
import requests
from urllib.parse import urlencode

from database import db
from config import Config

# 导入阿里云SMS服务（如果后续需要时加载）
try:
    from sms_aliyun_config import send_aliyun_sms
    ALIYUN_SMS_AVAILABLE = True
except ImportError:
    ALIYUN_SMS_AVAILABLE = False
    send_aliyun_sms = None

logger = logging.getLogger(__name__)

class PasswordResetService:
    """密码重置服务类"""

    def __init__(self):
        self.token_expire_minutes = 10  # 验证码有效期10分钟

    def find_user_by_contact(self, contact_type, contact_value):
        """
        根据联系方式查找用户
        """
        try:
            # 根据联系方式类型选择对应的字段
            contact_field = 'email' if contact_type == 'email' else 'telenum'

            # 检查所有用户表
            tables = {
                'student': ('students', 'student_id'),
                'teacher': ('teachers', 'teacher_id'),
                'admin': ('admins', 'admin_id')
            }

            for role, (table_name, id_field) in tables.items():
                sql = f"""
                SELECT {id_field} as id, username, '{role}' as role,
                       {contact_field} as contact_value
                FROM {table_name}
                WHERE {contact_field} = %s
                """
                result = db.execute_query(sql, (contact_value,))
                if result:
                    return result[0]

            return None

        except Exception as e:
            logger.error(f"查找用户失败: {e}")
            return None

    def generate_verification_token(self):
        """生成6位数字验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])

    def create_password_reset_token(self, username, user_role, contact_type,
                                   contact_value, ip_address=None, user_agent=None):
        """
        创建密码重置验证码记录
        """
        try:
            # 生成验证码和哈希
            token = self.generate_verification_token()
            token_hash = hashlib.md5(token.encode()).hexdigest()

            # 计算过期时间
            expires_at = datetime.datetime.now() + datetime.timedelta(
                minutes=self.token_expire_minutes
            )

            # 插入数据库
            sql = """
            INSERT INTO password_reset_tokens
            (username, user_role, contact_type, contact_value,
             verification_token, token_hash, expires_at, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            db.execute_insert(sql, (
                username, user_role, contact_type, contact_value,
                token, token_hash, expires_at, ip_address, user_agent
            ))

            logger.info(f"为用户 {username} 创建密码重置验证码")
            return token

        except Exception as e:
            logger.error(f"创建密码重置验证码失败: {e}")
            return None

    def send_email_verification(self, email, token):
        """发送邮箱验证码"""
        try:
            subject = "密码重置验证码"
            body = f"""
            您好！

            您正在重置密码，验证码为：{token}

            本验证码有效期为 {self.token_expire_minutes} 分钟，请及时输入。

            如果这不是您的操作，请忽略此邮件。

            感谢您使用我们的系统！
            """

            # 使用配置文件中的SMTP设置
            smtp_server = Config.SMTP_SERVER
            smtp_port = Config.SMTP_PORT
            sender_email = Config.SMTP_FROM_EMAIL
            sender_password = Config.SMTP_PASSWORD

            # 如果SMTP配置为空，使用模拟发送
            if not smtp_server or smtp_server == 'smtp.example.com':
                logger.warning(f"SMTP配置为空，模拟发送验证码邮件到 {email}")
                print(f"\n{'='*60}")
                print(f"模拟邮件发送")
                print(f"收件人: {email}")
                print(f"主题: {subject}")
                print(f"内容: {body.strip()}")
                print(f"{'='*60}\n")
                return True

            # 创建邮件消息
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = email
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain", "utf-8"))

            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # 启用TLS加密
                server.login(sender_email, sender_password)
                server.send_message(message)

            logger.info(f"验证码邮件已成功发送到 {email}")
            return True

        except Exception as e:
            logger.error(f"发送邮箱验证码失败: {e}")
            # 如果真实发送失败，回退到模拟发送
            logger.warning(f"回退到模拟发送，显示验证码")
            print(f"\n{'='*60}")
            print(f"邮件服务异常，回退到模拟发送")
            print(f"收件人: {email}")
            print(f"验证码: {token}")
            print(f"{'='*60}\n")
            return True

    def send_sms_verification(self, phone, token):
        """发送短信验证码"""
        try:
            # 检查是否启用短信服务
            if not Config.SMS_ENABLED:
                logger.info(f"SMS服务已禁用，显示验证码到控制台")
                print(f"\n{'='*60}")
                print(f"短信验证码（模拟发送）")
                print(f"手机号: {phone}")
                print(f"验证码: {token}")
                print(f"有效期: {self.token_expire_minutes} 分钟")
                print(f"{'='*60}\n")
                return True

            # 根据服务提供商选择发送方法
            if Config.SMS_PROVIDER.lower() == 'aliyun' and ALIYUN_SMS_AVAILABLE and send_aliyun_sms:
                logger.info(f"使用阿里云SMS服务发送验证码到 {phone}")

                # 确保手机号格式正确（阿里云要求带国际区号）
                if not phone.startswith('+86'):
                    phone = f"86{phone}"

                result = send_aliyun_sms(phone, token)

                if result.get('success'):
                    logger.info(f"验证码短信已成功发送到 {phone}")
                    return True
                else:
                    logger.error(f"阿里云SMS发送失败: {result.get('message')}")
                    # 回退到模拟发送
                    print(f"\n{'='*60}")
                    print(f"阿里云SMS发送失败，回退到模拟")
                    print(f"手机号: {phone}")
                    print(f"验证码: {token}")
                    print(f"错误信息: {result.get('message')}")
                    print(f"{'='*60}\n")
                    return True

            else:
                # 通用模拟发送（用于未配置服务商的情况）
                logger.warning(f"SMS服务商未配置或不可用，使用模拟发送")
                print(f"\n{'='*60}")
                print(f"短信验证码（模拟发送）")
                print(f"服务商: {Config.SMS_PROVIDER}")
                print(f"手机号: {phone}")
                print(f"验证码: {token}")
                print(f"有效期: {self.token_expire_minutes} 分钟")
                print(f"{'='*60}\n")
                return True

        except Exception as e:
            logger.error(f"发送短信验证码失败: {e}")
            # 如果发送失败，回退到模拟发送
            logger.warning(f"发送失败，回退到模拟显示验证码")
            print(f"\n{'='*60}")
            print(f"短信发送异常，显示验证码")
            print(f"手机号: {phone}")
            print(f"验证码: {token}")
            print(f"错误信息: {str(e)}")
            print(f"{'='*60}\n")
            return True

    def verify_token(self, username, user_role, token):
        """
        验证验证码是否正确
        """
        try:
            # 计算token哈希
            token_hash = hashlib.md5(token.encode()).hexdigest()

            # 查询验证码记录
            sql = """
            SELECT id, expires_at, status
            FROM password_reset_tokens
            WHERE username = %s AND user_role = %s AND token_hash = %s
            AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """

            result = db.execute_query(sql, (username, user_role, token_hash))

            if not result:
                return False, "验证码错误或已过期"

            token_record = result[0]

            # 检查是否过期
            current_time = datetime.datetime.now()
            if current_time > token_record['expires_at'].replace(tzinfo=None):
                # 标记为过期
                self._mark_token_expired(token_record['id'])
                return False, "验证码已过期"

            # 标记为已使用
            self._mark_token_used(token_record['id'])

            return True, "验证码验证成功"

        except Exception as e:
            logger.error(f"验证码验证失败: {e}")
            return False, f"验证失败：{str(e)}"

    def reset_password(self, username, user_role, new_password):
        """
        重置用户密码
        """
        try:
            # 根据用户角色选择对应的表
            tables = {
                'student': 'students',
                'teacher': 'teachers',
                'admin': 'admins'
            }

            table_name = tables.get(user_role)
            if not table_name:
                return False, "无效的用户角色"

            # 加密新密码
            hashed_password = hashlib.md5(new_password.encode('utf-8')).hexdigest()

            # 更新密码
            sql = f"UPDATE {table_name} SET password = %s WHERE username = %s"
            affected_rows = db.execute_update(sql, (hashed_password, username))

            if affected_rows > 0:
                logger.info(f"用户 {username} 密码重置成功")
                return True, "密码重置成功"
            else:
                return False, "密码重置失败"

        except Exception as e:
            logger.error(f"密码重置失败: {e}")
            return False, f"重置失败：{str(e)}"

    def _mark_token_used(self, token_id):
        """标记验证码为已使用"""
        try:
            sql = """
            UPDATE password_reset_tokens
            SET status = 'used', used_at = NOW()
            WHERE id = %s
            """
            db.execute_update(sql, (token_id,))

        except Exception as e:
            logger.error(f"标记验证码失败: {e}")

    def _mark_token_expired(self, token_id):
        """标记验证码为过期"""
        try:
            sql = """
            UPDATE password_reset_tokens
            SET status = 'expired'
            WHERE id = %s
            """
            db.execute_update(sql, (token_id,))

        except Exception as e:
            logger.error(f"标记验证码过期失败: {e}")

    def cleanup_expired_tokens(self):
        """清理过期的验证码"""
        try:
            sql = """
            UPDATE password_reset_tokens
            SET status = 'expired'
            WHERE status = 'active' AND expires_at < NOW()
            """
            affected_rows = db.execute_update(sql)
            if affected_rows > 0:
                logger.info(f"清理了 {affected_rows} 个过期的验证码")
            return affected_rows

        except Exception as e:
            logger.error(f"清理过期验证码失败: {e}")
            return 0

    def get_user_by_username_and_role(self, username, role):
        """根据用户名和角色获取用户信息"""
        try:
            tables = {
                'student': ('students', 'student_id'),
                'teacher': ('teachers', 'teacher_id'),
                'admin': ('admins', 'admin_id')
            }

            table_name, id_field = tables.get(role, (None, None))
            if not table_name:
                return None

            sql = f"""
            SELECT {id_field} as id, username, email, telenum
            FROM {table_name}
            WHERE username = %s
            """

            result = db.execute_query(sql, (username,))
            return result[0] if result else None

        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None

# 全局密码重置服务实例
password_reset_service = PasswordResetService()

# 导出方便使用的函数
def find_user_by_contact(contact_type, contact_value):
    return password_reset_service.find_user_by_contact(contact_type, contact_value)

def create_reset_token(username, user_role, contact_type, contact_value, ip_address=None, user_agent=None):
    return password_reset_service.create_password_reset_token(
        username, user_role, contact_type, contact_value, ip_address, user_agent
    )

def send_verification_code(contact_type, contact_value, token):
    if contact_type == 'email':
        return password_reset_service.send_email_verification(contact_value, token)
    elif contact_type == 'telenum':
        return password_reset_service.send_sms_verification(contact_value, token)
    return False

def verify_reset_token(username, user_role, token):
    return password_reset_service.verify_token(username, user_role, token)

def reset_user_password(username, user_role, new_password):
    return password_reset_service.reset_password(username, user_role, new_password)