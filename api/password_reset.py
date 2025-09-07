#!/usr/bin/env python3
"""
密码重置API
处理忘记密码相关的HTTP请求
"""

from flask import Blueprint, jsonify, request, session
import logging

from services.password_reset_service import (
    find_user_by_contact,
    create_reset_token,
    send_verification_code,
    verify_reset_token,
    reset_user_password
)

logger = logging.getLogger(__name__)
password_reset_bp = Blueprint('password_reset', __name__)

@password_reset_bp.route('/api/password-reset/find-user', methods=['POST'])
def find_user():
    """根据邮箱或手机号查找用户"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        contact_type = data.get('contact_type')  # 'email' 或 'telenum'
        contact_value = data.get('contact_value', '').strip()

        if not contact_type or not contact_value:
            return jsonify({"success": False, "message": "请输入完整的联系方式"}), 400

        if contact_type not in ['email', 'telenum']:
            return jsonify({"success": False, "message": "无效的联系方式类型"}), 400

        # 查找用户
        user = find_user_by_contact(contact_type, contact_value)
        if not user:
            return jsonify({"success": False, "message": f"未找到绑定此{contact_type}的用户"}), 404

        # 临时存储用户信息用于下一步发送验证码
        session[f'password_reset_user_{contact_value}'] = {
            'username': user['username'],
            'role': user['role'],
            'contact_type': contact_type,
            'contact_value': contact_value
        }

        logger.info(f"找到用户 {user['username']}，准备发送验证码")

        return jsonify({
            "success": True,
            "message": "用户查找成功",
            "data": {
                "username": user['username'],
                "role": user['role']
            }
        })

    except Exception as e:
        logger.error(f"查找用户失败: {e}")
        return jsonify({"success": False, "message": "查找用户失败"}), 500

@password_reset_bp.route('/api/password-reset/send-code', methods=['POST'])
def send_verification_code_handler():
    """发送验证码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        contact_type = data.get('contact_type')
        contact_value = data.get('contact_value', '').strip()

        if not contact_type or not contact_value:
            return jsonify({"success": False, "message": "缺少必要参数"}), 400

        # 检查会话中是否有用户信息
        session_key = f'password_reset_user_{contact_value}'
        if session_key not in session:
            return jsonify({"success": False, "message": "请先验证联系方式"}), 400

        user_data = session[session_key]

        # 创建验证码
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')

        token = create_reset_token(
            user_data['username'],
            user_data['role'],
            contact_type,
            contact_value,
            ip_address,
            user_agent
        )

        if not token:
            return jsonify({"success": False, "message": "验证码生成失败"}), 500

        # 发送验证码
        if send_verification_code(contact_type, contact_value, token):
            logger.info(f"验证码已发送至 {contact_value}")

            # 将验证码存储在会话中，用于测试（生产环境中应该移除）
            session[f'password_reset_token_{contact_value}'] = token

            return jsonify({
                "success": True,
                "message": f"验证码已发送至您的{contact_type}",
                "data": {
                    # 生产环境中不要返回验证码，这里仅用于测试
                    "verification_token": token if contact_type == 'telenum' else None
                }
            })
        else:
            return jsonify({"success": False, "message": f"验证码发送失败，请稍后重试"}), 500

    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        return jsonify({"success": False, "message": "发送验证码失败"}), 500

@password_reset_bp.route('/api/password-reset/verify-code', methods=['POST'])
def verify_code():
    """验证验证码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        contact_type = data.get('contact_type')
        contact_value = data.get('contact_value', '').strip()
        verification_token = data.get('verification_token', '').strip()

        if not all([contact_type, contact_value, verification_token]):
            return jsonify({"success": False, "message": "请输入完整的验证码"}), 400

        # 检查会话中是否有用户信息
        session_key = f'password_reset_user_{contact_value}'
        if session_key not in session:
            return jsonify({"success": False, "message": "请重新获取验证码"}), 400

        user_data = session[session_key]

        # 验证验证码
        success, message = verify_reset_token(
            user_data['username'],
            user_data['role'],
            verification_token
        )

        if success:
            # 验证成功，将验证状态存储在会话中
            session[f'password_reset_verified_{contact_value}'] = {
                'username': user_data['username'],
                'role': user_data['role'],
                'contact_type': contact_type,
                'contact_value': contact_value,
                'verified_at': str(request.environ.get('REMOTE_ADDR', ''))
            }

            # 清理临时会话数据
            if session_key in session:
                del session[session_key]

            logger.info(f"用户 {user_data['username']} 验证码验证成功")
            return jsonify({"success": True, "message": "验证码验证成功"})

        return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        logger.error(f"验证码验证失败: {e}")
        return jsonify({"success": False, "message": "验证码验证失败"}), 500

@password_reset_bp.route('/api/password-reset/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        contact_type = data.get('contact_type')
        contact_value = data.get('contact_value', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()

        if not all([contact_type, contact_value, new_password, confirm_password]):
            return jsonify({"success": False, "message": "请填写所有必填字段"}), 400

        if new_password != confirm_password:
            return jsonify({"success": False, "message": "两次输入的密码不一致"}), 400

        if len(new_password) < 6:
            return jsonify({"success": False, "message": "密码长度不能少于6位"}), 400

        # 检查验证状态
        verified_key = f'password_reset_verified_{contact_value}'
        if verified_key not in session:
            return jsonify({"success": False, "message": "请先进行验证"}), 400

        verified_data = session[verified_key]

        # 重置密码
        success, message = reset_user_password(
            verified_data['username'],
            verified_data['role'],
            new_password
        )

        if success:
            # 清理会话数据
            if verified_key in session:
                del session[verified_key]

            logger.info(f"用户 {verified_data['username']} 密码重置成功")
            return jsonify({"success": True, "message": "密码重置成功，请使用新密码登录"})
        else:
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        logger.error(f"密码重置失败: {e}")
        return jsonify({"success": False, "message": "密码重置失败"}), 500

@password_reset_bp.route('/api/password-reset/resend-code', methods=['POST'])
def resend_code():
    """重新发送验证码"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        contact_type = data.get('contact_type')
        contact_value = data.get('contact_value')

        if not contact_type or not contact_value:
            return jsonify({"success": False, "message": "缺少必要参数"}), 400

        # 检查是否可以重新发送（防止频繁发送）
        resend_key = f'password_reset_resend_{contact_value}'
        if resend_key in session:
            # 简单的频率限制（1分钟内只能发送一次）
            import time
            last_send_time = session.get(resend_key, 0)
            if time.time() - last_send_time < 60:
                return jsonify({"success": False, "message": "请等待1分钟后重新发送"}), 429

        # 将请求重定向到发送验证码的处理函数
        session[resend_key] = time.time()

        # 重新调用发送验证码逻辑
        request_data = {
            'contact_type': contact_type,
            'contact_value': contact_value
        }

        # 这里临时修改request.data来复用send_verification_code_handler
        original_data = request.get_json()
        request._cached_json = (request_data, request._cached_json[1]) if hasattr(request, '_cached_json') else None

        try:
            return send_verification_code_handler()
        finally:
            # 恢复原始数据
            if original_data:
                request._cached_json = (original_data, request._cached_json[1]) if hasattr(request, '_cached_json') else None

    except Exception as e:
        logger.error(f"重新发送验证码失败: {e}")
        return jsonify({"success": False, "message": "重新发送验证码失败"}), 500