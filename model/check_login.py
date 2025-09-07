from database import db
import hashlib
import logging

logger = logging.getLogger(__name__)

def hash_password(password):
    """对密码进行MD5加密"""
    return hashlib.md5(password.encode('utf-8')).hexdigest()

def is_null(username, password, role=None):
    """检查用户名和密码是否为空"""
    if not username or not password:
        return True
    if role and not role:
        return True
    return False

def exist_user(username):
    """检查用户是否存在（检查所有用户表）"""
    try:
        # 检查admins表
        sql = "SELECT admin_id FROM admins WHERE username = %s"
        result = db.execute_query(sql, (username,))
        if len(result) > 0:
            return True
            
        # 检查teachers表
        sql = "SELECT teacher_id FROM teachers WHERE username = %s"
        result = db.execute_query(sql, (username,))
        if len(result) > 0:
            return True
            
        # 检查students表
        sql = "SELECT student_id FROM students WHERE username = %s"
        result = db.execute_query(sql, (username,))
        if len(result) > 0:
            return True
            
        return False
    except Exception as e:
        logger.error(f"检查用户存在性失败: {e}")
        return False

def is_existed(username, password, role):
    """验证用户凭据是否正确"""
    try:
        # 根据角色选择对应的表和ID字段
        table_mapping = {
            'student': ('students', 'student_id'),
            'teacher': ('teachers', 'teacher_id'),
            'admin': ('admins', 'admin_id')
        }
        
        if role not in table_mapping:
            logger.warning(f"无效的用户角色: {role}")
            return None
            
        table_name, id_field = table_mapping[role]
        
        # 查询用户信息（不验证密码）
        # admins表没有status字段，其他表有
        if table_name == 'admins':
            sql = f"""
            SELECT {id_field} as id, username, email, telenum, password, 'active' as status
            FROM {table_name} 
            WHERE username = %s
            """
        else:
            sql = f"""
            SELECT {id_field} as id, username, email, telenum, password, status
            FROM {table_name} 
            WHERE username = %s
            """
        result = db.execute_query(sql, (username,))
        
        if not result:
            logger.warning(f"用户 {username} 不存在于{role}表")
            return None
        
        user = result[0]
        stored_password = user['password']
        
        # 验证密码（强制使用MD5加密）
        hashed_password = hash_password(password)
        password_valid = (hashed_password == stored_password)
        
        if password_valid:
            # 移除密码字段，添加角色信息
            user.pop('password', None)
            user['role'] = role  # 保持前端期望的角色值
            logger.info(f"用户 {username} 登录成功")
            return user
        else:
            logger.warning(f"用户 {username} 登录失败：密码错误")
            return None
            
    except Exception as e:
        logger.error(f"用户验证失败: {e}")
        return None

def get_user_by_username(username):
    """根据用户名获取用户信息（检查所有用户表）"""
    try:
        # 检查admins表
        sql = "SELECT admin_id as id, username, 'admin' as role, email, created_at FROM admins WHERE username = %s"
        result = db.execute_query(sql, (username,))
        if result:
            return result[0]
            
        # 检查teachers表
        sql = "SELECT teacher_id as id, username, 'teacher' as role, email, created_at FROM teachers WHERE username = %s"
        result = db.execute_query(sql, (username,))
        if result:
            return result[0]
            
        # 检查students表
        sql = "SELECT student_id as id, username, 'student' as role, email, created_at FROM students WHERE username = %s"
        result = db.execute_query(sql, (username,))
        if result:
            return result[0]
            
        return None
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        return None
