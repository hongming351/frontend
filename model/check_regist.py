from database import db
from .check_login import hash_password, exist_user
import logging

logger = logging.getLogger(__name__)

def add_user(username, password, identity, telenum, email=None):
    """普通用户注册"""
    try:
        # 检查用户是否已存在
        if exist_user(username):
            logger.warning(f"用户 {username} 已存在")
            return {"success": False, "message": "用户名已存在"}
        
        # 对密码进行MD5加密
        hashed_password = hash_password(password)
        
        # 根据角色选择对应的表
        table_mapping = {
            'student': 'students',
            'teacher': 'teachers',
            'admin': 'admins'
        }
        
        if identity not in table_mapping:
            logger.error(f"无效的用户身份: {identity}")
            return {"success": False, "message": "无效的用户身份"}
        
        table_name = table_mapping[identity]
        
        # 插入新用户到对应的表
        sql = f"""
        INSERT INTO {table_name} (username, password, telenum, email) 
        VALUES (%s, %s, %s, %s)
        """
        result = db.execute_update(sql, (username, hashed_password, telenum, email))
        
        if result > 0:
            logger.info(f"用户 {username} 注册成功到{table_name}表")
            return {"success": True, "message": "用户注册成功"}
        else:
            logger.error(f"用户 {username} 注册失败")
            return {"success": False, "message": "用户注册失败"}
            
    except Exception as e:
        logger.error(f"用户注册异常: {e}")
        return {"success": False, "message": f"注册异常: {str(e)}"}

def admin_add_teacher(username, telenum, email=None, course_assignment=None):
    """管理员添加教师账户"""
    try:
        # 检查用户是否已存在
        if exist_user(username):
            logger.warning(f"教师 {username} 已存在")
            return {"success": False, "message": "用户名已存在"}
        
        # 使用手机号作为初始密码
        password = telenum
        hashed_password = hash_password(password)
        
        # 插入新教师到teachers表
        sql = """
        INSERT INTO teachers (username, password, telenum, email, status) 
        VALUES (%s, %s, %s, %s, 'active')
        """
        result = db.execute_update(sql, (username, hashed_password, telenum, email))
        
        if result > 0:
            logger.info(f"教师 {username} 添加成功")
            return {
                "success": True, 
                "message": "教师添加成功",
                "data": {
                    "username": username,
                    "telenum": telenum,
                    "email": email
                }
            }
        else:
            logger.error(f"教师 {username} 添加失败")
            return {"success": False, "message": "教师添加失败"}
            
    except Exception as e:
        logger.error(f"教师添加异常: {e}")
        return {"success": False, "message": f"教师添加异常: {str(e)}"}

def update_user_password(username, new_password):
    """更新用户密码（更新所有用户表）"""
    try:
        hashed_password = hash_password(new_password)
        
        # 更新admins表
        sql = "UPDATE admins SET password = %s WHERE username = %s"
        result = db.execute_update(sql, (hashed_password, username))
        if result > 0:
            logger.info(f"管理员 {username} 密码更新成功")
            return {"success": True, "message": "密码更新成功"}
            
        # 更新teachers表
        sql = "UPDATE teachers SET password = %s WHERE username = %s"
        result = db.execute_update(sql, (hashed_password, username))
        if result > 0:
            logger.info(f"教师 {username} 密码更新成功")
            return {"success": True, "message": "密码更新成功"}
            
        # 更新students表
        sql = "UPDATE students SET password = %s WHERE username = %s"
        result = db.execute_update(sql, (hashed_password, username))
        if result > 0:
            logger.info(f"学生 {username} 密码更新成功")
            return {"success": True, "message": "密码更新成功"}
            
        logger.warning(f"用户 {username} 密码更新失败：用户不存在")
        return {"success": False, "message": "密码更新失败：用户不存在"}
            
    except Exception as e:
        logger.error(f"密码更新异常: {e}")
        return {"success": False, "message": f"密码更新异常: {str(e)}"}
