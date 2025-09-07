from flask import Blueprint, jsonify, request, session
from database import db
import logging
import hashlib
import json
from decimal import Decimal

logger = logging.getLogger(__name__)
teachers_bp = Blueprint('teachers', __name__)

# 辅助函数：加密密码
def encrypt_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# 辅助函数：转换Decimal类型为float，用于JSON序列化
def convert_decimal(obj):
    """递归转换对象中的Decimal类型为float"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimal(item) for item in obj)
    else:
        return obj

@teachers_bp.route('/api/teachers', methods=['GET'])
def get_teachers():
    """获取所有教师列表"""
    try:
        sql = """
            SELECT t.teacher_id as id, t.username, t.email, t.telenum, t.status,
                   GROUP_CONCAT(DISTINCT c.course_name ORDER BY c.course_name SEPARATOR ', ') as course_assignment
            FROM teachers t
            LEFT JOIN teacher_courses tc ON t.teacher_id = tc.teacher_id
            LEFT JOIN courses c ON tc.course_id = c.course_id
            GROUP BY t.teacher_id
            ORDER BY t.username
        """
        teachers = db.execute_query(sql)
        return jsonify({"success": True, "data": teachers})
    except Exception as e:
        logger.error(f"获取教师列表失败: {e}")
        return jsonify({"success": False, "message": "获取教师列表失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/assign-courses', methods=['POST'])
def assign_courses_to_teacher(teacher_id):
    """批量分配课程给教师（管理员权限）"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login",
                "error_code": "ADMIN_REQUIRED"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False, 
                "message": "无请求数据",
                "error_code": "NO_DATA"
            }), 400

        if 'course_ids' not in data:
            return jsonify({
                "success": False, 
                "message": "缺少课程ID数据",
                "error_code": "MISSING_COURSE_IDS"
            }), 400

        # 获取课程ID列表
        course_ids = data['course_ids']
        if not isinstance(course_ids, list):
            return jsonify({
                "success": False, 
                "message": "课程ID必须是数组格式",
                "error_code": "INVALID_COURSE_IDS_FORMAT"
            }), 400

        # 检查教师是否存在
        check_teacher_sql = "SELECT teacher_id, username FROM teachers WHERE teacher_id = %s"
        teacher_info = db.execute_query(check_teacher_sql, (teacher_id,))
        
        if not teacher_info:
            return jsonify({
                "success": False,
                "message": f"教师ID {teacher_id} 不存在",
                "error_code": "TEACHER_NOT_FOUND"
            }), 404

        teacher_name = teacher_info[0]['username']

        # 先删除教师已有的所有课程分配
        try:
            delete_sql = "DELETE FROM teacher_courses WHERE teacher_id = %s"
            db.execute_update(delete_sql, (teacher_id,))
            logger.info(f"已清除教师 {teacher_name}(ID:{teacher_id}) 的所有课程分配")
        except Exception as e:
            logger.error(f"清除教师课程分配失败: {e}")
            return jsonify({
                "success": False,
                "message": "清除现有课程分配失败",
                "error_code": "CLEAR_COURSES_FAILED"
            }), 500

        # 批量插入新的课程分配
        success_count = 0
        failed_count = 0
        failed_courses = []
        valid_course_names = []

        if not course_ids:
            return jsonify({
                "success": False,
                "message": "请至少选择一个课程",
                "error_code": "NO_COURSES_SELECTED"
            }), 400

        # 检查所有课程是否存在（只有当有课程ID时才检查）
        existing_course_ids = set()
        existing_courses = []
        
        if course_ids:
            existing_courses = db.execute_query(
                "SELECT course_id, course_name FROM courses WHERE course_id IN %s",
                (tuple(course_ids),)  # Convert list to tuple for IN clause
            )
            existing_course_ids = {c['course_id'] for c in existing_courses}
        
        # 执行分配
        for course_id in course_ids:
            try:
                if course_id not in existing_course_ids:
                    failed_count += 1
                    failed_courses.append({
                        "course_id": course_id,
                        "reason": "课程不存在"
                    })
                    continue
                
                # 执行分配
                insert_sql = "INSERT INTO teacher_courses (teacher_id, course_id) VALUES (%s, %s)"
                db.execute_update(insert_sql, (teacher_id, course_id))
                success_count += 1
                
                # 获取课程名称
                course_name = next(c['course_name'] for c in existing_courses if c['course_id'] == course_id)
                valid_course_names.append(course_name)
                
            except Exception as e:
                failed_count += 1
                failed_courses.append({
                    "course_id": course_id,
                    "reason": str(e)
                })
                logger.error(f"为教师 {teacher_id} 分配课程 {course_id} 失败: {e}", exc_info=True)

        logger.info(f"管理员为教师 {teacher_name}(ID:{teacher_id}) 分配课程结果: 成功 {success_count} 门, 失败 {failed_count} 门")

        result = {
            "success": True if success_count > 0 else False,
            "message": f"课程分配完成: 成功 {success_count} 门, 失败 {failed_count} 门",
            "data": {
                "teacher_id": teacher_id,
                "teacher_name": teacher_name,
                "assigned_courses": valid_course_names,
                "failed_assignments": failed_courses if failed_count > 0 else None
            }
        }

        # 如果全部失败则返回错误状态码
        if success_count == 0:
            return jsonify(result), 400
        
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"分配课程给教师失败: {e}")
        return jsonify({"success": False, "message": "课程分配失败"}), 500

@teachers_bp.route('/api/teachers/search', methods=['GET'])
def search_teachers():
    """搜索教师"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        query = request.args.get('q', '')
        if not query:
            return jsonify({"success": False, "message": "请输入搜索关键词"}), 400
        
        sql = """
            SELECT t.teacher_id as id, t.username, t.email, t.telenum, t.status,
                   GROUP_CONCAT(DISTINCT c.course_name ORDER BY c.course_name SEPARATOR ', ') as course_assignment
            FROM teachers t
            LEFT JOIN teacher_courses tc ON t.teacher_id = tc.teacher_id
            LEFT JOIN courses c ON tc.course_id = c.course_id
            WHERE (t.username LIKE %s OR t.email LIKE %s OR t.telenum LIKE %s)
            GROUP BY t.teacher_id
            ORDER BY t.username
            LIMIT 50
        """
        search_pattern = f"%{query}%"
        teachers = db.execute_query(sql, (search_pattern, search_pattern, search_pattern))
        
        return jsonify({"success": True, "data": teachers})
    except Exception as e:
        logger.error(f"搜索教师失败: {e}")
        return jsonify({"success": False, "message": "搜索教师失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>', methods=['GET'])
def get_teacher(teacher_id):
    """获取单个教师信息"""
    try:
        sql = """
            SELECT t.teacher_id as id, t.username, t.email, t.telenum, t.status,
                   GROUP_CONCAT(DISTINCT c.course_name ORDER BY c.course_name SEPARATOR ', ') as course_assignment
            FROM teachers t
            LEFT JOIN teacher_courses tc ON t.teacher_id = tc.teacher_id
            LEFT JOIN courses c ON tc.course_id = c.course_id
            WHERE t.teacher_id = %s
            GROUP BY t.teacher_id
        """
        teacher = db.execute_query(sql, (teacher_id,))
        
        if teacher:
            return jsonify({"success": True, "data": teacher[0]})
        return jsonify({"success": False, "message": "教师不存在"}), 404
    except Exception as e:
        logger.error(f"获取教师信息失败: {e}")
        return jsonify({"success": False, "message": "获取教师信息失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/courses', methods=['GET'])
def get_teacher_courses(teacher_id):
    """获取教师教授的所有课程"""
    try:
        sql = """
            SELECT c.course_id as id, c.course_name as name, c.language, c.description, c.created_at, c.updated_at,
                   tc.assigned_at as assigned_at
            FROM teacher_courses tc
            JOIN courses c ON tc.course_id = c.course_id
            WHERE tc.teacher_id = %s
            ORDER BY c.course_name
        """
        courses = db.execute_query(sql, (teacher_id,))
        return jsonify({"success": True, "data": courses})
    except Exception as e:
        logger.error(f"获取教师课程失败: {e}")
        return jsonify({"success": False, "message": "获取教师课程失败"}), 500

@teachers_bp.route('/api/teachers/current/courses', methods=['GET'])
def get_current_teacher_courses():
    """获取当前登录教师教授的所有课程"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']
        sql = """
            SELECT c.course_id as id, c.course_name as name, c.language, c.description, c.created_at, c.updated_at,
                   tc.assigned_at as assigned_at
            FROM teacher_courses tc
            JOIN courses c ON tc.course_id = c.course_id
            WHERE tc.teacher_id = %s
            ORDER BY c.course_name
        """
        courses = db.execute_query(sql, (teacher_id,))
        return jsonify({"success": True, "data": courses})
    except Exception as e:
        logger.error(f"获取当前教师课程失败: {e}")
        return jsonify({"success": False, "message": "获取课程列表失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/classes', methods=['GET'])
def get_teacher_classes(teacher_id):
    """获取教师创建的所有班级，支持按课程ID过滤"""
    try:
        course_id = request.args.get('course_id')
        
        if course_id:
            # 按课程ID过滤
            sql = """
                SELECT c.class_id as id, c.class_name, c.description, c.created_at, c.updated_at,
                       co.course_name as course_name, co.language as course_language
                FROM classes c
                JOIN courses co ON c.course_id = co.course_id
                WHERE c.teacher_id = %s AND c.course_id = %s
                ORDER BY c.class_name
            """
            classes = db.execute_query(sql, (teacher_id, course_id))
        else:
            # 获取所有班级
            sql = """
                SELECT c.class_id as id, c.class_name, c.description, c.created_at, c.updated_at,
                       co.course_name as course_name, co.language as course_language
                FROM classes c
                JOIN courses co ON c.course_id = co.course_id
                WHERE c.teacher_id = %s
                ORDER BY co.course_name, c.class_name
            """
            classes = db.execute_query(sql, (teacher_id,))
            
        return jsonify({"success": True, "data": classes})
    except Exception as e:
        logger.error(f"获取教师班级失败: {e}")
        return jsonify({"success": False, "message": "获取教师班级失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/students', methods=['GET'])
def get_teacher_students(teacher_id):
    """获取教师管理的所有学生"""
    try:
        sql = """
            SELECT DISTINCT s.student_id as id, s.username, s.email, s.telenum,
                   c.class_name, co.course_name as course_name
            FROM student_classes sc
            JOIN classes c ON sc.class_id = c.class_id
            JOIN courses co ON c.course_id = co.course_id
            JOIN students s ON sc.student_id = s.student_id
            WHERE c.teacher_id = %s
            ORDER BY s.username
        """
        students = db.execute_query(sql, (teacher_id,))
        return jsonify({"success": True, "data": students})
    except Exception as e:
        logger.error(f"获取教师学生失败: {e}")
        return jsonify({"success": False, "message": "获取教师学生失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/assign-course', methods=['POST'])
def assign_course_to_teacher(teacher_id):
    """为教师分配课程"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        if not data or 'course_id' not in data:
            return jsonify({"success": False, "message": "缺少课程ID"}), 400
        
        course_id = data['course_id']
        logger.info(f"管理员尝试为教师 {teacher_id} 分配课程 {course_id}")
        
        # 检查教师是否存在
        check_teacher_sql = "SELECT COUNT(*) as count FROM teachers WHERE teacher_id = %s"
        teacher_exists = db.execute_query(check_teacher_sql, (teacher_id,))[0]['count']
        
        if not teacher_exists:
            logger.warning(f"教师 {teacher_id} 不存在")
            return jsonify({"success": False, "message": "教师不存在"}), 404
        
        # 检查课程是否存在
        check_course_sql = "SELECT COUNT(*) as count FROM courses WHERE course_id = %s"
        course_exists = db.execute_query(check_course_sql, (course_id,))[0]['count']
        
        if not course_exists:
            logger.warning(f"课程 {course_id} 不存在")
            return jsonify({"success": False, "message": "课程不存在"}), 404
        
        # 检查是否已经分配过该课程
        check_assignment_sql = """
            SELECT COUNT(*) as count FROM teacher_courses 
            WHERE teacher_id = %s AND course_id = %s
        """
        already_assigned = db.execute_query(check_assignment_sql, (teacher_id, course_id))[0]['count']
        
        if already_assigned:
            logger.warning(f"教师 {teacher_id} 已经教授课程 {course_id}")
            return jsonify({
                "success": False, 
                "message": "该教师已经教授此课程"
            }), 400

        # 执行分配
        sql = "INSERT INTO teacher_courses (teacher_id, course_id) VALUES (%s, %s)"
        affected = db.execute_update(sql, (teacher_id, course_id))
        
        if affected > 0:
            logger.info(f"教师 {teacher_id} 分配课程 {course_id} 成功")
            # 获取课程名称
            get_course_name_sql = "SELECT course_name FROM courses WHERE course_id = %s"
            course_name = db.execute_query(get_course_name_sql, (course_id,))[0]['course_name']
            return jsonify({
                "success": True, 
                "message": f"成功分配课程 '{course_name}' 给教师",
                "data": {
                    "teacher_id": teacher_id,
                    "course_id": course_id,
                    "course_name": course_name
                }
            }), 201
        
        logger.error(f"教师 {teacher_id} 分配课程 {course_id} 失败，无行受影响")
        return jsonify({"success": False, "message": "课程分配失败"}), 400
    except Exception as e:
        logger.error(f"分配课程失败: {e}")
        return jsonify({"success": False, "message": f"分配课程失败: {str(e)}"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/remove-course/<int:course_id>', methods=['DELETE'])
def remove_course_from_teacher(teacher_id, course_id):
    """移除教师教授的课程"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        # 检查教师是否有该课程的班级
        check_classes_sql = """
            SELECT COUNT(*) as count FROM classes 
            WHERE teacher_id = %s AND course_id = %s
        """
        has_classes = db.execute_query(check_classes_sql, (teacher_id, course_id))[0]['count']
        
        if has_classes:
            return jsonify({
                "success": False, 
                "message": "无法移除课程，该教师在此课程下有关联的班级"
            }), 400

        sql = "DELETE FROM teacher_courses WHERE teacher_id = %s AND course_id = %s"
        affected = db.execute_update(sql, (teacher_id, course_id))
        
        if affected > 0:
            logger.info(f"教师 {teacher_id} 移除课程 {course_id} 成功")
            return jsonify({"success": True, "message": "课程移除成功"})
        
        return jsonify({"success": False, "message": "教师未教授此课程"}), 404
    except Exception as e:
        logger.error(f"移除课程失败: {e}")
        return jsonify({"success": False, "message": "移除课程失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/import-students', methods=['POST'])
def import_students_to_class(teacher_id):
    """教师导入学生到班级"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False, 
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 检查是否是教师本人操作
        if session['user_id'] != teacher_id:
            return jsonify({
                "success": False, 
                "message": "只能操作自己的账户"
            }), 403

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400
        
        required_fields = ['class_id', 'student_ids']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400
        
        class_id = data['class_id']
        student_ids = data['student_ids']
        
        if not isinstance(student_ids, list):
            return jsonify({"success": False, "message": "student_ids必须是数组"}), 400
        
        # 检查教师是否有权限管理该班级
        check_class_sql = "SELECT teacher_id FROM classes WHERE class_id = %s"
        class_info = db.execute_query(check_class_sql, (class_id,))
        
        if not class_info or class_info[0]['teacher_id'] != teacher_id:
            return jsonify({
                "success": False, 
                "message": "只能管理自己创建的班级"
            }), 403
        
        # 批量导入学生
        success_count = 0
        error_count = 0
        errors = []
        
        for student_id in student_ids:
            try:
                # 检查学生是否存在
                check_student_sql = "SELECT COUNT(*) as count FROM students WHERE student_id = %s"
                student_exists = db.execute_query(check_student_sql, (student_id,))[0]['count']
                
                if not student_exists:
                    errors.append(f"学生ID {student_id} 不存在")
                    error_count += 1
                    continue
                
                # 检查学生是否已经在该班级中
                check_enrollment_sql = """
                    SELECT COUNT(*) as count FROM student_classes 
                    WHERE class_id = %s AND student_id = %s
                """
                already_enrolled = db.execute_query(check_enrollment_sql, (class_id, student_id))[0]['count']
                
                if already_enrolled:
                    errors.append(f"学生ID {student_id} 已经在该班级中")
                    error_count += 1
                    continue
                
                # 导入学生
                insert_sql = "INSERT INTO student_classes (class_id, student_id) VALUES (%s, %s)"
                db.execute_update(insert_sql, (class_id, student_id))
                success_count += 1
                
            except Exception as e:
                errors.append(f"学生ID {student_id} 导入失败: {str(e)}")
                error_count += 1
        
        logger.info(f"教师 {teacher_id} 导入学生到班级 {class_id}: 成功 {success_count}, 失败 {error_count}")
        
        result = {
            "success": True,
            "message": f"导入完成: 成功 {success_count} 个, 失败 {error_count} 个",
            "data": {
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors
            }
        }
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"导入学生失败: {e}")
        return jsonify({"success": False, "message": "导入学生失败"}), 500

@teachers_bp.route('/api/teachers', methods=['POST'])
def create_teacher():
    """创建新教师账号（管理员权限）"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400

        required_fields = ['username', 'email', 'telenum']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400

        # 检查用户名是否已存在
        check_username_sql = "SELECT COUNT(*) as count FROM teachers WHERE username = %s"
        username_exists = db.execute_query(check_username_sql, (data['username'],))[0]['count']

        if username_exists:
            return jsonify({
                "success": False, 
                "message": "用户名已存在"
            }), 400

        # 检查邮箱是否已存在
        check_email_sql = "SELECT COUNT(*) as count FROM teachers WHERE email = %s"
        email_exists = db.execute_query(check_email_sql, (data['email'],))[0]['count']

        if email_exists:
            return jsonify({
                "success": False, 
                "message": "邮箱已存在"
            }), 400

        # 检查手机号是否已存在
        check_telenum_sql = "SELECT COUNT(*) as count FROM teachers WHERE telenum = %s"
        telenum_exists = db.execute_query(check_telenum_sql, (data['telenum'],))[0]['count']

        if telenum_exists:
            return jsonify({
                "success": False, 
                "message": "手机号已存在"
            }), 400

        # 设置默认密码为123456
        password = data.get('password', '123456')
        encrypted_password = encrypt_password(password)

        # 创建教师账号
        sql = """
            INSERT INTO teachers (username, password, telenum, email, status)
            VALUES (%s, %s, %s, %s, 'active')
        """
        params = (
            data['username'],
            encrypted_password,
            data['telenum'],
            data['email']
        )

        affected = db.execute_update(sql, params)

        if affected > 0:
            # 获取新创建的教师ID
            get_teacher_sql = "SELECT teacher_id FROM teachers WHERE username = %s"
            teacher_id = db.execute_query(get_teacher_sql, (data['username'],))[0]['teacher_id']

            logger.info(f"管理员创建教师账号成功: {data['username']}")
            return jsonify({
                "success": True, 
                "message": "教师账号创建成功",
                "data": {
                    "teacher_id": teacher_id,
                    "username": data['username'],
                    "email": data['email'],
                    "telenum": data['telenum'],
                    "password": password  # 返回初始密码信息
                }
            }), 201

        return jsonify({"success": False, "message": "教师账号创建失败"}), 400
    except Exception as e:
        logger.error(f"创建教师账号失败: {e}")
        return jsonify({"success": False, "message": "创建教师账号失败"}), 500

@teachers_bp.route('/api/teachers/create', methods=['POST'])
def create_teacher_with_courses():
    """创建新教师账号并分配课程（管理员权限）"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400

        required_fields = ['username', 'telenum']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400

        # 检查用户名是否已存在
        check_username_sql = "SELECT COUNT(*) as count FROM teachers WHERE username = %s"
        username_exists = db.execute_query(check_username_sql, (data['username'],))[0]['count']

        if username_exists:
            return jsonify({
                "success": False, 
                "message": "用户名已存在"
            }), 400

        # 检查手机号是否已存在
        check_telenum_sql = "SELECT COUNT(*) as count FROM teachers WHERE telenum = %s"
        telenum_exists = db.execute_query(check_telenum_sql, (data['telenum'],))[0]['count']

        if telenum_exists:
            return jsonify({
                "success": False, 
                "message": "手机号已存在"
            }), 400

        # 检查邮箱是否已存在（如果提供了邮箱）
        email = data.get('email', None)
        if email:
            check_email_sql = "SELECT COUNT(*) as count FROM teachers WHERE email = %s"
            email_exists = db.execute_query(check_email_sql, (email,))[0]['count']

            if email_exists:
                return jsonify({
                    "success": False, 
                    "message": "邮箱已存在"
                }), 400

        # 设置默认密码为123456
        password = data.get('password', '123456')
        encrypted_password = encrypt_password(password)

        # 创建教师账号
        sql = """
            INSERT INTO teachers (username, password, telenum, email, status)
            VALUES (%s, %s, %s, %s, 'active')
        """
        params = (
            data['username'],
            encrypted_password,
            data['telenum'],
            email
        )

        affected = db.execute_update(sql, params)

        if affected > 0:
            # 获取新创建的教师ID
            get_teacher_sql = "SELECT teacher_id FROM teachers WHERE username = %s"
            teacher_id = db.execute_query(get_teacher_sql, (data['username'],))[0]['teacher_id']

            # 处理课程分配
            course_ids = data.get('course_ids', [])
            assigned_courses = []
            
            if course_ids and isinstance(course_ids, list):
                # 插入课程分配
                insert_sql = "INSERT INTO teacher_courses (teacher_id, course_id) VALUES (%s, %s)"
                
                # 检查每个课程是否存在
                for course_id in course_ids:
                    check_course_sql = "SELECT COUNT(*) as count FROM courses WHERE course_id = %s"
                    course_exists = db.execute_query(check_course_sql, (course_id,))[0]['count']
                    
                    if course_exists:
                        db.execute_update(insert_sql, (teacher_id, course_id))
                        # 获取课程名称
                        get_course_name_sql = "SELECT course_name FROM courses WHERE course_id = %s"
                        course_name = db.execute_query(get_course_name_sql, (course_id,))[0]['course_name']
                        assigned_courses.append(course_name)

            logger.info(f"管理员创建教师账号成功: {data['username']}，分配课程: {len(assigned_courses)} 门")
            return jsonify({
                "success": True, 
                "message": "教师账号创建成功",
                "data": {
                    "teacher_id": teacher_id,
                    "username": data['username'],
                    "email": email,
                    "telenum": data['telenum'],
                    "password": password,  # 返回初始密码信息
                    "assigned_courses": assigned_courses
                }
            }), 201

        return jsonify({"success": False, "message": "教师账号创建失败"}), 400
    except Exception as e:
        logger.error(f"创建教师账号失败: {e}")
        return jsonify({"success": False, "message": "创建教师账号失败"}), 500


@teachers_bp.route('/api/teachers/<int:teacher_id>', methods=['PUT'])
def update_teacher(teacher_id):
    """更新教师基本信息（管理员权限）"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400

        # 先检查教师是否存在
        check_teacher_sql = "SELECT teacher_id FROM teachers WHERE teacher_id = %s"
        teacher_info = db.execute_query(check_teacher_sql, (teacher_id,))
        
        if not teacher_info:
            return jsonify({
                "success": False,
                "message": f"教师ID {teacher_id} 不存在",
                "error_code": "TEACHER_NOT_FOUND"
            }), 404

        # 构建更新语句和参数
        update_fields = []
        params = []
        
        # 检查并添加可更新的字段
        if 'username' in data:
            update_fields.append("username = %s")
            params.append(data['username'])
            
            # 检查用户名是否已被其他教师使用
            check_username_sql = "SELECT COUNT(*) as count FROM teachers WHERE username = %s AND teacher_id != %s"
            username_exists = db.execute_query(check_username_sql, (data['username'], teacher_id))[0]['count']
            
            if username_exists:
                return jsonify({
                    "success": False, 
                    "message": "用户名已存在",
                    "error_code": "USERNAME_EXISTS"
                }), 400
        
        if 'email' in data:
            update_fields.append("email = %s")
            params.append(data['email'])
            
            # 检查邮箱是否已被其他教师使用
            if data['email']:
                check_email_sql = "SELECT COUNT(*) as count FROM teachers WHERE email = %s AND teacher_id != %s"
                email_exists = db.execute_query(check_email_sql, (data['email'], teacher_id))[0]['count']
                
                if email_exists:
                    return jsonify({
                        "success": False, 
                        "message": "邮箱已存在",
                        "error_code": "EMAIL_EXISTS"
                    }), 400
        
        if 'telenum' in data:
            update_fields.append("telenum = %s")
            params.append(data['telenum'])
            
            # 检查手机号是否已被其他教师使用
            check_telenum_sql = "SELECT COUNT(*) as count FROM teachers WHERE telenum = %s AND teacher_id != %s"
            telenum_exists = db.execute_query(check_telenum_sql, (data['telenum'], teacher_id))[0]['count']
            
            if telenum_exists:
                return jsonify({
                    "success": False, 
                    "message": "手机号已存在",
                    "error_code": "TELENUM_EXISTS"
                }), 400
        
        if 'status' in data:
            update_fields.append("status = %s")
            params.append(data['status'])
        
        if not update_fields:
            return jsonify({"success": False, "message": "没有需要更新的字段"}), 400
        
        # 添加WHERE子句参数
        params.append(teacher_id)
        
        # 执行更新
        sql = f"UPDATE teachers SET {', '.join(update_fields)} WHERE teacher_id = %s"
        affected = db.execute_update(sql, params)
        
        if affected > 0:
            # 获取更新后的教师信息
            get_teacher_sql = "SELECT teacher_id as id, username, email, telenum, status FROM teachers WHERE teacher_id = %s"
            updated_teacher = db.execute_query(get_teacher_sql, (teacher_id,))[0]
            
            logger.info(f"管理员更新教师信息成功: 教师ID={teacher_id}")
            return jsonify({
                "success": True, 
                "message": "教师信息更新成功",
                "data": updated_teacher
            })
        
        logger.error(f"更新教师信息失败: 教师ID={teacher_id} 更新未生效")
        return jsonify({
            "success": False, 
            "message": "更新未生效，请检查数据",
            "error_code": "UPDATE_FAILED"
        }), 400
    except Exception as e:
        logger.error(f"更新教师信息失败: {e}")
        return jsonify({"success": False, "message": "更新教师信息失败"}), 500


@teachers_bp.route('/api/teachers/<int:teacher_id>', methods=['DELETE'])
def delete_teacher(teacher_id):
    """删除教师账号（管理员权限）"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False,
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        # 检查教师是否存在
        check_teacher_sql = "SELECT COUNT(*) as count FROM teachers WHERE teacher_id = %s"
        teacher_exists = db.execute_query(check_teacher_sql, (teacher_id,))[0]['count']
        if not teacher_exists:
            return jsonify({"success": False, "message": "教师不存在"}), 404

        # 检查教师是否有关联的班级
        check_classes_sql = "SELECT COUNT(*) as count FROM classes WHERE teacher_id = %s"
        has_classes = db.execute_query(check_classes_sql, (teacher_id,))[0]['count']
        if has_classes > 0:
            return jsonify({
                "success": False,
                "message": f"无法删除，该教师名下有 {has_classes} 个班级，请先处理这些班级。"
            }), 400

        # 1. 删除教师的课程分配
        delete_courses_sql = "DELETE FROM teacher_courses WHERE teacher_id = %s"
        db.execute_update(delete_courses_sql, (teacher_id,))
        logger.info(f"已删除教师 {teacher_id} 的所有课程分配")

        # 2. 删除教师账号
        delete_teacher_sql = "DELETE FROM teachers WHERE teacher_id = %s"
        affected = db.execute_update(delete_teacher_sql, (teacher_id,))

        if affected > 0:
            logger.info(f"管理员成功删除教师账号: ID={teacher_id}")
            return jsonify({"success": True, "message": "教师删除成功"})

        logger.warning(f"尝试删除教师 {teacher_id}，但未在数据库中找到或删除失败")
        return jsonify({"success": False, "message": "教师删除失败"}), 400

    except Exception as e:
        logger.error(f"删除教师失败: {e}")
        return jsonify({"success": False, "message": "删除教师失败，请查看服务器日志"}), 500


@teachers_bp.route('/api/teachers/change-password', methods=['PUT'])
def change_teacher_password():
    """教师修改密码"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "缺少请求数据"}), 400

        # 验证必需字段
        required_fields = ['old_password', 'new_password', 'confirm_password']
        for field in required_fields:
            if not data.get(field) or not data.get(field).strip():
                return jsonify({"success": False, "message": f"缺少必需字段: {field}"}), 400

        old_password = data['old_password'].strip()
        new_password = data['new_password'].strip()
        confirm_password = data['confirm_password'].strip()

        # 验证新密码长度
        if len(new_password) < 6:
            return jsonify({"success": False, "message": "新密码长度不能少于6位"}), 400

        # 验证新密码和确认密码是否一致
        if new_password != confirm_password:
            return jsonify({"success": False, "message": "新密码和确认密码不一致"}), 400

        # 获取当前用户的密码
        sql = "SELECT password FROM teachers WHERE teacher_id = %s"
        result = db.execute_query(sql, (teacher_id,))

        if not result:
            return jsonify({"success": False, "message": "用户不存在"}), 404

        stored_password = result[0]['password']

        # 验证原密码
        hashed_old_password = encrypt_password(old_password)
        if hashed_old_password != stored_password:
            return jsonify({"success": False, "message": "原密码错误"}), 400

        # 检查新密码是否与原密码相同
        hashed_new_password = encrypt_password(new_password)
        if hashed_new_password == stored_password:
            return jsonify({"success": False, "message": "新密码不能与原密码相同"}), 400

        # 更新密码
        update_sql = "UPDATE teachers SET password = %s WHERE teacher_id = %s"
        affected = db.execute_update(update_sql, (hashed_new_password, teacher_id))

        if affected > 0:
            logger.info(f"教师 {teacher_id} 密码修改成功")
            return jsonify({
                "success": True,
                "message": "密码修改成功，请重新登录",
                "logout_required": True
            })

        return jsonify({"success": False, "message": "密码修改失败"}), 400

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return jsonify({"success": False, "message": "修改密码失败"}), 500

@teachers_bp.route('/api/teachers/<int:teacher_id>/create-student', methods=['POST'])
def create_student_by_teacher(teacher_id):
    """教师创建学生账号"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 检查是否是教师本人操作
        if session['user_id'] != teacher_id:
            return jsonify({
                "success": False, 
                "message": "只能操作自己的账户"
            }), 403

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400
        
        required_fields = ['username', 'student_id', 'email', 'telenum']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400
        
        # 检查用户名是否已存在
        check_username_sql = "SELECT COUNT(*) as count FROM students WHERE username = %s"
        username_exists = db.execute_query(check_username_sql, (data['username'],))[0]['count']
        
        if username_exists:
            return jsonify({
                "success": False, 
                "message": "用户名已存在"
            }), 400
        
        # 检查学号是否已存在
        check_student_id_sql = "SELECT COUNT(*) as count FROM students WHERE student_id = %s"
        student_id_exists = db.execute_query(check_student_id_sql, (data['student_id'],))[0]['count']
        
        if student_id_exists:
            return jsonify({
                "success": False, 
                "message": "学号已存在"
            }), 400
        
        # 检查邮箱是否已存在
        if data['email']:
            check_email_sql = "SELECT COUNT(*) as count FROM students WHERE email = %s"
            email_exists = db.execute_query(check_email_sql, (data['email'],))[0]['count']
            
            if email_exists:
                return jsonify({
                    "success": False, 
                    "message": "邮箱已存在"
                }), 400
        
        # 检查手机号是否已存在
        check_telenum_sql = "SELECT COUNT(*) as count FROM students WHERE telenum = %s"
        telenum_exists = db.execute_query(check_telenum_sql, (data['telenum'],))[0]['count']
        
        if telenum_exists:
            return jsonify({
                "success": False, 
                "message": "手机号已存在"
            }), 400
        
        # 设置默认密码为学号
        password = data['student_id']  # 初始密码默认为学号
        encrypted_password = encrypt_password(password)
        
        # 创建学生账号
        sql = """
            INSERT INTO students (username, password, telenum, email, student_id, status)
            VALUES (%s, %s, %s, %s, %s, 'active')
        """
        params = (
            data['username'],
            encrypted_password,
            data['telenum'],
            data['email'],
            data['student_id']
        )
        
        affected = db.execute_update(sql, params)
        
        if affected > 0:
            # 获取新创建的学生ID
            get_student_sql = "SELECT student_id FROM students WHERE username = %s"
            student_id = db.execute_query(get_student_sql, (data['username'],))[0]['student_id']
            
            logger.info(f"教师 {teacher_id} 创建学生账号成功: {data['username']} (学号: {data['student_id']})")
            return jsonify({
                "success": True, 
                "message": "学生账号创建成功",
                "data": {
                    "student_id": student_id,
                    "username": data['username'],
                    "student_id": data['student_id'],
                    "email": data['email'],
                    "telenum": data['telenum'],
                    "password": password  # 返回初始密码信息
                }
            }), 201
        
        return jsonify({"success": False, "message": "学生账号创建失败"}), 400
    except Exception as e:
        logger.error(f"创建学生账号失败: {e}")
@teachers_bp.route('/api/teacher/dashboard/stats', methods=['GET'])
def get_teacher_dashboard_stats():
    """获取教师仪表盘统计数据"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']

        # 获取教师的作业数量
        assignments_sql = "SELECT COUNT(*) as count FROM homework_assignments WHERE teacher_id = %s"
        assignments_result = db.execute_query(assignments_sql, (teacher_id,))
        total_assignments = assignments_result[0]['count'] if assignments_result else 0

        # 由于没有学生提交表，暂时使用模拟数据
        pending_grading = 0  # 待批改数量
        completion_rate = 0  # 平均完成率
        average_score = 0   # 平均成绩

        # 获取教师教授的课程信息（用于侧边栏显示）
        courses_sql = """
            SELECT c.course_name, c.language, COUNT(cls.class_id) as class_count
            FROM teacher_courses tc
            JOIN courses c ON tc.course_id = c.course_id
            LEFT JOIN classes cls ON c.course_id = cls.course_id AND cls.teacher_id = tc.teacher_id
            WHERE tc.teacher_id = %s
            GROUP BY c.course_id, c.course_name, c.language
        """
        courses_result = db.execute_query(courses_sql, (teacher_id,))

        course_assignment = ""
        student_count = 0
        if courses_result:
            course = courses_result[0]
            course_assignment = f"{course['course_name']} ({course['language']})"
            student_count = course['class_count'] * 10  # 估算每班10名学生

        result = {
            "success": True,
            "data": {
                "total_assignments": total_assignments,
                "pending_grading": pending_grading,
                "completion_rate": completion_rate,
                "average_score": average_score,
                "course_assignment": course_assignment,
                "student_count": student_count
            }
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取教师仪表盘统计失败: {e}")
        return jsonify({"success": False, "message": "获取统计数据失败"}), 500
@teachers_bp.route('/api/teacher/assignments', methods=['GET'])
def get_teacher_assignments():
    """获取当前登录教师的所有作业"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']

        # 获取教师的所有作业 - 包含班级信息和真实完成率
        sql = """
            SELECT ha.id, ha.title, ha.description, ha.created_at, ha.updated_at,
                   ha.publish_date, ha.deadline,
                   GROUP_CONCAT(DISTINCT c.class_name ORDER BY c.class_name SEPARATOR ', ') as classes,
                   co.course_name, co.language,
                   COUNT(DISTINCT hq.id) as question_count,
                   COUNT(DISTINCT sc.student_id) as total_students,
                   COUNT(DISTINCT sa.student_id) as submitted_count
            FROM homework_assignments ha
            LEFT JOIN classes c ON ha.class_id = c.class_id
            LEFT JOIN courses co ON ha.course_id = co.course_id
            LEFT JOIN homework_questions hq ON ha.id = hq.homework_id
            LEFT JOIN student_classes sc ON ha.class_id = sc.class_id
            LEFT JOIN student_answers sa ON ha.id = sa.homework_id
            WHERE ha.teacher_id = %s
            GROUP BY ha.id, ha.title, ha.description, ha.created_at, ha.updated_at, ha.publish_date, ha.deadline, co.course_name, co.language
            ORDER BY ha.created_at DESC
        """

        assignments = db.execute_query(sql, (teacher_id,))

        # 格式化数据
        formatted_assignments = []
        for assignment in assignments:
            # 使用正确的日期字段
            publish_date = assignment['publish_date']
            deadline = assignment['deadline']

            # 获取班级学生总数
            total_students = assignment['total_students']

            # 计算完成率（基于已提交学生数）
            submitted_count = assignment['submitted_count']
            completion_rate = (submitted_count / total_students * 100) if total_students > 0 else 0

            formatted_assignments.append({
                'id': assignment['id'],
                'name': assignment['title'],
                'classes': assignment['classes'] or '未分配班级',
                'publish_date': publish_date.strftime('%Y-%m-%d') if publish_date else '-',
                'deadline': deadline.strftime('%Y-%m-%d') if deadline else '-',
                'problem_count': assignment['question_count'],
                'submitted': f"{submitted_count}/{total_students}",
                'completion_rate': round(completion_rate)
            })

        return jsonify({"success": True, "data": formatted_assignments})

    except Exception as e:
        logger.error(f"获取教师作业失败: {e}")
        return jsonify({"success": False, "message": "获取作业列表失败"}), 500

@teachers_bp.route('/api/teacher/submissions/pending', methods=['GET'])
def get_pending_submissions():
    """获取当前登录教师的待批改作业"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']

        # 获取所有有提交记录的学生作业组合（按作业聚合）
        aggregated_sql = """
            SELECT
                sa.student_id,
                sa.homework_id,
                s.username as student_name,
                s.email as student_email,
                ha.title as assignment_name,
                c.class_name,
                MAX(sa.last_attempt_at) as last_submit_time,
                COUNT(CASE WHEN sa.status IN ('submitted', 'graded') THEN 1 END) as submitted_questions,
                COUNT(CASE WHEN (sa.status = 'graded') OR (sa.status = 'submitted' AND sa.is_correct = 1) THEN 1 END) as completed_questions
            FROM student_answers sa
            JOIN students s ON sa.student_id = s.student_id
            JOIN homework_assignments ha ON sa.homework_id = ha.id
            JOIN classes c ON ha.class_id = c.class_id
            WHERE ha.teacher_id = %s
            AND sa.status IN ('submitted', 'graded')
            GROUP BY sa.student_id, sa.homework_id, s.username, s.email, ha.title, c.class_name
            HAVING submitted_questions > 0
            ORDER BY last_submit_time DESC
        """

        aggregated_submissions = db.execute_query(aggregated_sql, (teacher_id,))

        # 获取每个作业的题目总数
        homework_questions_sql = """
            SELECT homework_id, COUNT(*) as total_questions
            FROM homework_questions
            GROUP BY homework_id
        """
        homework_questions = db.execute_query(homework_questions_sql)
        homework_total_map = {hw['homework_id']: hw['total_questions'] for hw in homework_questions}

        # 获取待批改题目数量（状态为submitted且未评分）
        pending_questions_sql = """
            SELECT student_id, homework_id, COUNT(*) as pending_questions
            FROM student_answers
            WHERE status = 'submitted' AND (score IS NULL OR score = 0)
            GROUP BY student_id, homework_id
        """
        pending_questions = db.execute_query(pending_questions_sql)
        pending_map = {}
        for pq in pending_questions:
            key = f"{pq['student_id']}_{pq['homework_id']}"
            pending_map[key] = pq['pending_questions']

        # 格式化数据
        formatted_submissions = []
        for submission in aggregated_submissions:
            student_homework_key = f"{submission['student_id']}_{submission['homework_id']}"

            # 获取该作业的总题目数
            total_questions = homework_total_map.get(submission['homework_id'], 0)

            # 获取已提交和已完成的题目数
            submitted_count = submission['submitted_questions']
            completed_count = submission['completed_questions']

            # 获取待批改题目数
            pending_count = pending_map.get(student_homework_key, 0)

            # 计算完成率（基于已提交题目数）
            completion_rate = (submitted_count / total_questions * 100) if total_questions > 0 else 0

            # 生成完成情况文本（只返回已提交数量，格式化由前端负责）
            completed_problems = submitted_count

            # 完成情况状态
            if completion_rate == 100:
                completion_status = 'completed'
            elif completion_rate >= 50:
                completion_status = 'partial'
            else:
                completion_status = 'incomplete'

            formatted_submissions.append({
                'id': f"{submission['student_id']}_{submission['homework_id']}",
                'student_name': submission['student_name'],
                'student_id': submission['student_id'],
                'email': submission['student_email'],
                'assignment_name': submission['assignment_name'],
                'class_name': submission['class_name'],
                'homework_id': submission['homework_id'],
                'submit_time': submission['last_submit_time'].strftime('%Y-%m-%d %H:%M:%S') if submission['last_submit_time'] else None,
                'completed_problems': completed_problems,
                'completion_rate': round(completion_rate, 1),
                'completion_status': completion_status,
                'total_questions': total_questions,
                'submitted_count': submitted_count,
                'completed_count': completed_count,
                'pending_count': pending_count,
                'status': '待批改' if pending_count > 0 else '已完成'
            })

        return jsonify({"success": True, "data": formatted_submissions})

    except Exception as e:
        logger.error(f"获取待批改作业失败: {e}")
        return jsonify({"success": False, "message": "获取待批改作业失败"}), 500

@teachers_bp.route('/api/teacher/assignments', methods=['POST'])
def create_assignment():
    """创建新作业"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400

        required_fields = ['title', 'publish_date', 'deadline', 'class_ids', 'question_ids']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400

        # 验证班级ID列表
        class_ids = data.get('class_ids', [])
        if not isinstance(class_ids, list) or len(class_ids) == 0:
            return jsonify({"success": False, "message": "至少需要选择一个班级"}), 400

        # 验证题目ID列表
        question_ids = data.get('question_ids', [])
        if not isinstance(question_ids, list) or len(question_ids) == 0:
            return jsonify({"success": False, "message": "至少需要选择一道题目"}), 400

        # 检查是否前端提供了题目类型信息
        question_types = data.get('question_types', [])
        use_frontend_types = isinstance(question_types, list) and len(question_types) == len(question_ids)

        # 检查教师是否有权限管理这些班级
        check_classes_sql = """
            SELECT class_id, class_name, course_id
            FROM classes
            WHERE class_id IN %s AND teacher_id = %s
        """
        teacher_classes = db.execute_query(check_classes_sql, (tuple(class_ids), teacher_id))

        if len(teacher_classes) != len(class_ids):
            return jsonify({"success": False, "message": "只能为自己的班级布置作业"}), 403

        # 检查题目是否存在（需要检查三个不同的题目表）
        valid_question_ids = set()
        question_type_map = {}  # 存储题目ID到题目类型的映射

        if question_ids:
            if use_frontend_types:
                # 如果前端提供了题目类型信息，直接使用前端提供的信息
                logger.info("使用前端提供的题目类型信息")
                for i, question_id in enumerate(question_ids):
                    question_type = question_types[i]
                    # 验证题目在对应表中是否存在
                    if question_type == 'progressing':
                        check_sql = "SELECT COUNT(*) as count FROM progressing_questions WHERE progressing_questions_id = %s"
                    elif question_type == 'choice':
                        check_sql = "SELECT COUNT(*) as count FROM choice_questions WHERE choice_questions_id = %s"
                    elif question_type == 'judgment':
                        check_sql = "SELECT COUNT(*) as count FROM judgment_questions WHERE judgment_questions_id = %s"
                    else:
                        continue  # 无效的题目类型

                    result = db.execute_query(check_sql, (question_id,))
                    if result and result[0]['count'] > 0:
                        valid_question_ids.add(question_id)
                        question_type_map[question_id] = question_type
            else:
                # 使用优先级查询：编程题(1) > 选择题(2) > 判断题(3)
                # 这样可以确保如果一个ID在多个表中存在，选择优先级最高的那个

                # 构建UNION查询来同时获取所有题目类型的信息
                union_sql = """
                    SELECT progressing_questions_id as id, 'progressing' as question_type, 1 as priority
                    FROM progressing_questions
                    WHERE progressing_questions_id IN %s

                    UNION

                    SELECT choice_questions_id as id, 'choice' as question_type, 2 as priority
                    FROM choice_questions
                    WHERE choice_questions_id IN %s

                    UNION

                    SELECT judgment_questions_id as id, 'judgment' as question_type, 3 as priority
                    FROM judgment_questions
                    WHERE judgment_questions_id IN %s

                    ORDER BY id, priority
                """

                all_questions = db.execute_query(union_sql, (tuple(question_ids), tuple(question_ids), tuple(question_ids)))

                # 处理结果，为每个ID选择优先级最高的类型
                current_id = None
                best_priority = float('inf')
                best_type = None

                for q in all_questions:
                    if current_id != q['id']:
                        # 保存之前ID的最佳结果
                        if current_id is not None:
                            valid_question_ids.add(current_id)
                            question_type_map[current_id] = best_type

                        # 开始处理新ID
                        current_id = q['id']
                        best_priority = q['priority']
                        best_type = q['question_type']
                    else:
                        # 同一ID，检查是否优先级更高（数字越小优先级越高）
                        if q['priority'] < best_priority:
                            best_priority = q['priority']
                            best_type = q['question_type']

                # 处理最后一个ID
                if current_id is not None:
                    valid_question_ids.add(current_id)
                    question_type_map[current_id] = best_type

        # 验证所有题目都存在
        invalid_question_ids = set(question_ids) - valid_question_ids
        if invalid_question_ids:
            return jsonify({"success": False, "message": f"以下题目不存在: {list(invalid_question_ids)}"}), 400

        # 为每个班级创建作业
        created_assignments = []
        for class_info in teacher_classes:
            class_id = class_info['class_id']
            course_id = class_info['course_id']

            # 创建作业分配记录
            assignment_sql = """
                INSERT INTO homework_assignments (title, description, teacher_id, class_id, course_id, publish_date, deadline, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            import datetime
            now = datetime.datetime.now()

            # 执行插入并获取新插入的ID
            try:
                with db.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(assignment_sql, (
                            data['title'],
                            data.get('description', ''),
                            teacher_id,
                            class_id,
                            course_id,
                            data.get('publish_date'),  # 发布日期
                            data.get('deadline'),      # 截止日期
                            now,
                            now
                        ))
                        assignment_id = cursor.lastrowid

                        if assignment_id > 0:
                            # 为作业添加题目
                            question_sql = "INSERT INTO homework_questions (homework_id, question_id, question_type) VALUES (%s, %s, %s)"
                            for question_id in question_ids:
                                cursor.execute(question_sql, (assignment_id, question_id, question_type_map[question_id]))
            except Exception as e:
                logger.error(f"创建作业和题目失败: {e}")
                continue

                created_assignments.append({
                    'assignment_id': assignment_id,
                    'class_id': class_id,
                    'class_name': class_info['class_name']
                })

        logger.info(f"教师 {teacher_id} 创建作业成功: {data['title']}，分配给 {len(created_assignments)} 个班级")

        return jsonify({
            "success": True,
            "message": f"作业创建成功，已分配给 {len(created_assignments)} 个班级",
            "data": {
                "title": data['title'],
                "class_count": len(created_assignments),
                "question_count": len(question_ids),
                "assignments": created_assignments
            }
        }), 201

    except Exception as e:
        logger.error(f"创建作业失败: {e}")
        return jsonify({"success": False, "message": "创建作业失败"}), 500

@teachers_bp.route('/api/teacher/classes', methods=['GET'])
def get_teacher_classes_current():
    """获取当前登录教师的所有班级，支持按课程ID过滤"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']
        course_id = request.args.get('course_id')

        if course_id:
            # 按课程ID过滤
            sql = """
                SELECT c.class_id as id, c.class_name as name, c.description,
                       co.course_id, co.course_name, co.language
                FROM classes c
                JOIN courses co ON c.course_id = co.course_id
                WHERE c.teacher_id = %s AND c.course_id = %s
                ORDER BY c.class_name
            """
            classes = db.execute_query(sql, (teacher_id, course_id))
        else:
            # 获取所有班级
            sql = """
                SELECT c.class_id as id, c.class_name as name, c.description,
                       co.course_id, co.course_name, co.language
                FROM classes c
                JOIN courses co ON c.course_id = co.course_id
                WHERE c.teacher_id = %s
                ORDER BY co.course_name, c.class_name
            """
            classes = db.execute_query(sql, (teacher_id,))

        return jsonify({"success": True, "data": classes})

    except Exception as e:
        logger.error(f"获取教师班级失败: {e}")
        return jsonify({"success": False, "message": "获取班级列表失败"}), 500

@teachers_bp.route('/api/questions', methods=['GET'])
def get_questions():
    """获取所有题目（用于布置作业时选择）"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 支持按知识点、难度、语言筛选
        knowledge_point = request.args.get('knowledge_point')
        difficulty = request.args.get('difficulty')
        language = request.args.get('language')

        all_questions = []

        # 获取编程题
        progressing_sql = """
            SELECT progressing_questions_id as id, title, description, difficulty,
                   knowledge_points, language, 'progressing' as question_type, created_at
            FROM progressing_questions
            WHERE 1=1
        """
        progressing_params = []

        if knowledge_point:
            progressing_sql += " AND knowledge_points LIKE %s"
            progressing_params.append(f"%{knowledge_point}%")

        if difficulty:
            progressing_sql += " AND difficulty = %s"
            progressing_params.append(difficulty)

        if language:
            progressing_sql += " AND language = %s"
            progressing_params.append(language)

        progressing_sql += " ORDER BY created_at DESC"

        progressing_questions = db.execute_query(progressing_sql, progressing_params)
        all_questions.extend(progressing_questions)

        # 获取选择题
        choice_sql = """
            SELECT choice_questions_id as id, title, description, difficulty,
                   knowledge_points, language, 'choice' as question_type, created_at
            FROM choice_questions
            WHERE 1=1
        """
        choice_params = []

        if knowledge_point:
            choice_sql += " AND knowledge_points LIKE %s"
            choice_params.append(f"%{knowledge_point}%")

        if difficulty:
            choice_sql += " AND difficulty = %s"
            choice_params.append(difficulty)

        if language:
            choice_sql += " AND language = %s"
            choice_params.append(language)

        choice_sql += " ORDER BY created_at DESC"

        choice_questions = db.execute_query(choice_sql, choice_params)
        all_questions.extend(choice_questions)

        # 获取判断题
        judgment_sql = """
            SELECT judgment_questions_id as id, title, description, difficulty,
                   knowledge_points, language, 'judgment' as question_type, created_at
            FROM judgment_questions
            WHERE 1=1
        """
        judgment_params = []

        if knowledge_point:
            judgment_sql += " AND knowledge_points LIKE %s"
            judgment_params.append(f"%{knowledge_point}%")

        if difficulty:
            judgment_sql += " AND difficulty = %s"
            judgment_params.append(difficulty)

        if language:
            judgment_sql += " AND language = %s"
            judgment_params.append(language)

        judgment_sql += " ORDER BY created_at DESC"

        judgment_questions = db.execute_query(judgment_sql, judgment_params)
        all_questions.extend(judgment_questions)

        # 按创建时间排序（移除数量限制）
        all_questions.sort(key=lambda x: x['created_at'], reverse=True)

        return jsonify({"success": True, "data": all_questions})

    except Exception as e:
        logger.error(f"获取题目列表失败: {e}")
        return jsonify({"success": False, "message": "获取题目列表失败"}), 500

@teachers_bp.route('/api/teacher/assignments/<int:assignment_id>', methods=['GET'])
def get_assignment_detail(assignment_id):
    """获取作业详情，包括题目信息"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']

        # 首先检查作业是否存在且属于当前教师
        check_sql = """
            SELECT ha.id, ha.title, ha.description, ha.publish_date, ha.deadline,
                   ha.created_at, ha.updated_at, c.class_name, co.course_name, co.language
            FROM homework_assignments ha
            LEFT JOIN classes c ON ha.class_id = c.class_id
            LEFT JOIN courses co ON ha.course_id = co.course_id
            WHERE ha.id = %s AND ha.teacher_id = %s
        """
        assignment_info = db.execute_query(check_sql, (assignment_id, teacher_id))

        if not assignment_info:
            return jsonify({"success": False, "message": "作业不存在或无权限访问"}), 404

        assignment = assignment_info[0]

        # 获取作业包含的所有题目
        questions_sql = """
            SELECT hq.question_id, hq.question_type
            FROM homework_questions hq
            WHERE hq.homework_id = %s
            ORDER BY hq.id
        """
        question_links = db.execute_query(questions_sql, (assignment_id,))

        questions_detail = []

        for link in question_links:
            question_id = link['question_id']
            question_type = link['question_type']

            if question_type == 'progressing':
                # 获取编程题详情
                q_sql = """
                    SELECT progressing_questions_id as id, title, description, language,
                           difficulty, knowledge_points, input_description, output_description,
                           solution_idea, reference_code, created_at
                    FROM progressing_questions
                    WHERE progressing_questions_id = %s
                """
                q_result = db.execute_query(q_sql, (question_id,))

            elif question_type == 'choice':
                # 获取选择题详情
                q_sql = """
                    SELECT choice_questions_id as id, title, description, language,
                           difficulty, knowledge_points, options, correct_answer,
                           solution_idea, created_at
                    FROM choice_questions
                    WHERE choice_questions_id = %s
                """
                q_result = db.execute_query(q_sql, (question_id,))

            elif question_type == 'judgment':
                # 获取判断题详情
                q_sql = """
                    SELECT judgment_questions_id as id, title, description, language,
                           difficulty, knowledge_points, correct_answer,
                           solution_idea, created_at
                    FROM judgment_questions
                    WHERE judgment_questions_id = %s
                """
                q_result = db.execute_query(q_sql, (question_id,))

            if q_result:
                question = q_result[0]
                question['question_type'] = question_type
                questions_detail.append(question)

        # 构建返回数据
        result_data = {
            'id': assignment['id'],
            'title': assignment['title'],
            'description': assignment['description'],
            'class_name': assignment['class_name'],
            'course_name': assignment['course_name'],
            'course_language': assignment['language'],
            'publish_date': assignment['publish_date'].strftime('%Y-%m-%d %H:%M:%S') if assignment['publish_date'] else None,
            'deadline': assignment['deadline'].strftime('%Y-%m-%d %H:%M:%S') if assignment['deadline'] else None,
            'created_at': assignment['created_at'].strftime('%Y-%m-%d %H:%M:%S') if assignment['created_at'] else None,
            'updated_at': assignment['updated_at'].strftime('%Y-%m-%d %H:%M:%S') if assignment['updated_at'] else None,
            'questions': questions_detail,
            'question_count': len(questions_detail)
        }

        return jsonify({
            "success": True,
            "data": result_data
        })

    except Exception as e:
        logger.error(f"获取作业详情失败: {e}")
        return jsonify({"success": False, "message": "获取作业详情失败"}), 500

@teachers_bp.route('/api/teacher/assignment/<int:assignment_id>/submissions', methods=['GET'])
def get_assignment_submissions(assignment_id):
    """获取作业的学生提交情况"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']

        # 检查作业是否属于当前教师
        check_sql = """
            SELECT ha.id, ha.title, ha.class_id, c.class_name, co.course_name
            FROM homework_assignments ha
            JOIN classes c ON ha.class_id = c.class_id
            JOIN courses co ON ha.course_id = co.course_id
            WHERE ha.id = %s AND ha.teacher_id = %s
        """
        assignment_info = db.execute_query(check_sql, (assignment_id, teacher_id))

        if not assignment_info:
            return jsonify({"success": False, "message": "作业不存在或无权限访问"}), 404

        assignment = assignment_info[0]

        # 获取班级所有学生
        students_sql = """
            SELECT s.student_id, s.username, s.email
            FROM student_classes sc
            JOIN students s ON sc.student_id = s.student_id
            WHERE sc.class_id = %s
            ORDER BY s.username
        """
        all_students = db.execute_query(students_sql, (assignment['class_id'],))

        # 获取学生的答题情况
        submissions = []
        for student in all_students:
            student_id = student['student_id']

            # 获取该学生在该作业中的答题记录
            answers_sql = """
                SELECT
                    sa.question_id,
                    sa.question_type,
                    sa.status,
                    sa.score,
                    sa.is_correct,
                    sa.last_attempt_at as submit_time,
                    sa.teacher_comment,
                    CASE
                        WHEN sa.question_type = 'progressing' THEN pq.title
                        WHEN sa.question_type = 'choice' THEN cq.title
                        WHEN sa.question_type = 'judgment' THEN jq.title
                    END as question_title
                FROM student_answers sa
                LEFT JOIN progressing_questions pq ON sa.question_id = pq.progressing_questions_id AND sa.question_type = 'progressing'
                LEFT JOIN choice_questions cq ON sa.question_id = cq.choice_questions_id AND sa.question_type = 'choice'
                LEFT JOIN judgment_questions jq ON sa.question_id = jq.judgment_questions_id AND sa.question_type = 'judgment'
                WHERE sa.student_id = %s AND sa.homework_id = %s
                ORDER BY sa.question_id
            """
            student_answers = db.execute_query(answers_sql, (student_id, assignment_id))

            # 计算统计信息
            total_questions = len(student_answers)
            submitted_count = sum(1 for answer in student_answers if answer['status'] == 'submitted')
            graded_count = sum(1 for answer in student_answers if answer['status'] == 'graded')
            correct_count = sum(1 for answer in student_answers if answer['is_correct'])
            total_score = sum(answer['score'] or 0 for answer in student_answers if answer['status'] == 'graded')

            # 构建学生提交详情
            student_submission = {
                'student_id': student['student_id'],
                'student_name': student['username'],
                'email': student['email'],
                'total_questions': total_questions,
                'submitted_count': submitted_count,
                'graded_count': graded_count,
                'correct_count': correct_count,
                'total_score': total_score,
                'completion_rate': round((submitted_count / total_questions * 100), 2) if total_questions > 0 else 0,
                'answers': []
            }

            # 添加每道题的答题详情
            for answer in student_answers:
                answer_detail = {
                    'question_id': answer['question_id'],
                    'question_title': answer['question_title'] or f"题目 {answer['question_id']}",
                    'question_type': answer['question_type'],
                    'status': answer['status'],
                    'score': answer['score'],
                    'is_correct': answer['is_correct'],
                    'submit_time': answer['submit_time'].strftime('%Y-%m-%d %H:%M:%S') if answer['submit_time'] else None,
                    'teacher_comment': answer['teacher_comment']
                }
                student_submission['answers'].append(answer_detail)

            submissions.append(student_submission)

        # 计算班级统计信息
        class_stats = {
            'total_students': len(submissions),
            'submitted_students': sum(1 for s in submissions if s['submitted_count'] > 0),
            'graded_students': sum(1 for s in submissions if s['graded_count'] > 0),
            'avg_completion_rate': round(sum(s['completion_rate'] for s in submissions) / len(submissions), 2) if submissions else 0,
            'avg_score': round(sum(s['total_score'] for s in submissions if s['graded_count'] > 0) / max(1, sum(1 for s in submissions if s['graded_count'] > 0)), 2)
        }

        result = {
            'assignment_info': {
                'id': assignment['id'],
                'title': assignment['title'],
                'class_name': assignment['class_name'],
                'course_name': assignment['course_name']
            },
            'class_stats': class_stats,
            'submissions': submissions
        }

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"获取作业提交情况失败: {e}")
        return jsonify({"success": False, "message": "获取作业提交情况失败"}), 500

@teachers_bp.route('/api/teacher/assignment/<int:student_id>/<int:homework_id>/submissions', methods=['GET'])
def get_student_assignment_submissions(student_id, homework_id):
    """获取学生特定作业的所有题目提交详情"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']

        # 验证教师有权限查看此作业
        check_sql = """
            SELECT ha.id FROM homework_assignments ha
            WHERE ha.id = %s AND ha.teacher_id = %s
        """
        if not db.execute_query(check_sql, (homework_id, teacher_id)):
            return jsonify({"success": False, "message": "无权限查看此作业"}), 403

        # 获取作业基本信息
        assignment_sql = """
            SELECT ha.title as assignment_name, s.username as student_name,
                   s.email as student_email, ha.class_id, c.class_name
            FROM homework_assignments ha
            JOIN students s ON s.student_id = %s
            JOIN classes c ON ha.class_id = c.class_id
            WHERE ha.id = %s
        """
        assignment_info = db.execute_query(assignment_sql, (student_id, homework_id))

        if not assignment_info:
            return jsonify({"success": False, "message": "作业或学生信息不存在"}), 404

        assignment = assignment_info[0]

        # 获取该作业包含的所有题目
        questions_sql = """
            SELECT hq.question_id, hq.question_type
            FROM homework_questions hq
            WHERE hq.homework_id = %s
            ORDER BY hq.id
        """
        homework_questions = db.execute_query(questions_sql, (homework_id,))

        # 获取学生的答题情况
        submissions = []
        for question in homework_questions:
            q_id = question['question_id']
            q_type = question['question_type']

            # 获取题目详情
            if q_type == 'progressing':
                question_sql = """
                    SELECT progressing_questions_id as id, title, description, language,
                           difficulty, knowledge_points, input_description, output_description,
                           solution_idea, reference_code, created_at
                    FROM progressing_questions
                    WHERE progressing_questions_id = %s
                """
            elif q_type == 'choice':
                question_sql = """
                    SELECT choice_questions_id as id, title, description, language,
                           difficulty, knowledge_points, options, correct_answer,
                           solution_idea, created_at
                    FROM choice_questions
                    WHERE choice_questions_id = %s
                """
            elif q_type == 'judgment':
                question_sql = """
                    SELECT judgment_questions_id as id, title, description, language,
                           difficulty, knowledge_points, correct_answer,
                           solution_idea, created_at
                    FROM judgment_questions
                    WHERE judgment_questions_id = %s
                """

            question_detail = db.execute_query(question_sql, (q_id,))

            if not question_detail:
                continue

            question_info = question_detail[0]
            question_info['question_type'] = q_type

            # 获取学生答题记录
            answer_sql = """
                SELECT sa.question_id, sa.status, sa.score, sa.is_correct,
                       sa.answer_text, sa.choice_answer, sa.judgment_answer,
                       sa.teacher_comment, sa.last_attempt_at,
                       sa.graded_at
                FROM student_answers sa
                WHERE sa.student_id = %s AND sa.homework_id = %s AND sa.question_id = %s
            """
            student_answer = db.execute_query(answer_sql, (student_id, homework_id, q_id))

            submission = {
                'question_id': q_id,
                'question_title': question_info.get('title', f'题目 {q_id}'),
                'question_type': q_type,
                'question_description': question_info.get('description', ''),
                'is_graded': False,
                'score': None,
                'submit_time': None,
                'grade_time': None,
                'status': '未提交',
                'student_answer': None,
                'code': None,
                'execution_result': None,
                'solution_idea': question_info.get('solution_idea'),
                'teacher_comment': None,
                'correct_answer': question_info.get('correct_answer'),
                'reference_code': question_info.get('reference_code'),
                'options': question_info.get('options'),
                'input_description': question_info.get('input_description'),
                'output_description': question_info.get('output_description')
            }

            if student_answer:
                answer = student_answer[0]

                # 根据题目类型获取学生答案和判断正误
                student_answer_text = None
                is_correct = answer['is_correct']

                if q_type == 'progressing':
                    # 编程题：从programming_submissions表获取最新提交的代码和执行结果
                    code_sql = """
                        SELECT submission_code, run_status, execution_time,
                               memory_usage, compile_error, runtime_error, test_results
                        FROM programming_submissions
                        WHERE student_id = %s AND homework_id = %s AND question_id = %s
                        ORDER BY submit_time DESC LIMIT 1
                    """
                    code_result = db.execute_query(code_sql, (student_id, homework_id, q_id))
                    if code_result:
                        code_info = code_result[0]
                        student_answer_text = code_info['submission_code']
                        submission['code'] = code_info['submission_code']
                        submission['execution_result'] = f"运行状态: {code_info['run_status']}"
                        if code_info['execution_time']:
                            submission['execution_result'] += f"\n执行时间: {code_info['execution_time']}ms"
                        if code_info['memory_usage']:
                            submission['execution_result'] += f"\n内存使用: {code_info['memory_usage']}KB"
                        if code_info['compile_error']:
                            submission['execution_result'] += f"\n编译错误: {code_info['compile_error']}"
                        if code_info['runtime_error']:
                            submission['execution_result'] += f"\n运行错误: {code_info['runtime_error']}"
                        if code_info['test_results']:
                            submission['execution_result'] += f"\n测试结果: {code_info['test_results']}"
                elif q_type == 'choice':
                    # 选择题：从choice_answer列获取，并判断正误
                    student_answer_text = answer['choice_answer']
                    if student_answer_text and question_info['correct_answer']:
                        is_correct = student_answer_text.upper() == question_info['correct_answer'].upper()
                elif q_type == 'judgment':
                    # 判断题：从judgment_answer列获取，并判断正误
                    if answer['judgment_answer'] is not None:
                        # 修改：返回前端期望的字符串格式 'true' 或 'false'
                        student_answer_text = 'true' if answer['judgment_answer'] else 'false'
                        if question_info['correct_answer'] is not None:
                            is_correct = answer['judgment_answer'] == question_info['correct_answer']
                    else:
                        student_answer_text = None
                else:
                    # 其他类型：从answer_text列获取
                    student_answer_text = answer['answer_text']

                submission.update({
                    'is_graded': answer['status'] == 'graded',
                    'score': answer['score'],
                    'submit_time': answer['last_attempt_at'].strftime('%Y-%m-%d %H:%M:%S') if answer['last_attempt_at'] else None,
                    'grade_time': answer['graded_at'].strftime('%Y-%m-%d %H:%M:%S') if answer['graded_at'] else None,
                    'status': '已批改' if answer['status'] == 'graded' else '待批改',
                    'student_answer': student_answer_text,
                    'teacher_comment': answer['teacher_comment'],
                    'is_correct': is_correct
                })

                # 处理特殊字段
                if q_type == 'choice' and submission['options']:
                    try:
                        import json
                        submission['options'] = json.loads(submission['options'])
                    except:
                        submission['options'] = {}

            submissions.append(submission)

        # 计算作业统计信息
        total_questions = len(submissions)
        submitted_count = sum(1 for s in submissions if s['submit_time'] is not None)
        completed_count = sum(1 for s in submissions if s['is_graded'] or (s['submit_time'] and s['status'] == 'submitted'))
        pending_count = sum(1 for s in submissions if s['submit_time'] and not s['is_graded'])

        completion_rate = (completed_count / total_questions * 100) if total_questions > 0 else 0

        # 获取最新提交时间
        latest_submit_time = None
        if submissions:
            submit_times = [s['submit_time'] for s in submissions if s['submit_time']]
            if submit_times:
                latest_submit_time = max(submit_times)

        result = {
            'student_id': student_id,
            'student_name': assignment['student_name'],
            'student_email': assignment['student_email'],
            'assignment_name': assignment['assignment_name'],
            'homework_id': homework_id,
            'total_questions': total_questions,
            'submitted_count': submitted_count,
            'completed_count': completed_count,
            'pending_count': pending_count,
            'completion_rate': round(completion_rate, 1),
            'latest_submit_time': latest_submit_time,
            'submissions': submissions
        }

        # 转换Decimal类型为float以便JSON序列化
        result = convert_decimal(result)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"获取学生作业提交详情失败: {e}")
        return jsonify({"success": False, "message": "获取学生作业提交详情失败"}), 500


@teachers_bp.route('/api/teacher/submission/<int:student_id>/<int:homework_id>/<int:question_id>', methods=['GET'])
def get_student_answer_detail(student_id, homework_id, question_id):
    """获取学生的具体答题详情"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']

        # 验证教师有权限查看此作业
        check_sql = """
            SELECT ha.id FROM homework_assignments ha
            WHERE ha.id = %s AND ha.teacher_id = %s
        """
        if not db.execute_query(check_sql, (homework_id, teacher_id)):
            return jsonify({"success": False, "message": "无权限查看此作业"}), 403

        # 获取学生答案详情
        answer_sql = """
            SELECT
                sa.*,
                s.username as student_name,
                s.email as student_email,
                CASE
                    WHEN sa.question_type = 'progressing' THEN pq.title
                    WHEN sa.question_type = 'choice' THEN cq.title
                    WHEN sa.question_type = 'judgment' THEN jq.title
                END as question_title,
                CASE
                    WHEN sa.question_type = 'progressing' THEN pq.description
                    WHEN sa.question_type = 'choice' THEN cq.description
                    WHEN sa.question_type = 'judgment' THEN jq.description
                END as question_description,
                CASE
                    WHEN sa.question_type = 'progressing' THEN pq.solution_idea
                    WHEN sa.question_type = 'choice' THEN cq.solution_idea
                    WHEN sa.question_type = 'judgment' THEN jq.solution_idea
                END as solution_idea,
                CASE
                    WHEN sa.question_type = 'progressing' THEN pq.reference_code
                    WHEN sa.question_type = 'choice' THEN cq.correct_answer
                    WHEN sa.question_type = 'judgment' THEN jq.correct_answer
                END as correct_answer
            FROM student_answers sa
            JOIN students s ON sa.student_id = s.student_id
            LEFT JOIN progressing_questions pq ON sa.question_id = pq.progressing_questions_id AND sa.question_type = 'progressing'
            LEFT JOIN choice_questions cq ON sa.question_id = cq.choice_questions_id AND sa.question_type = 'choice'
            LEFT JOIN judgment_questions jq ON sa.question_id = jq.judgment_questions_id AND sa.question_type = 'judgment'
            WHERE sa.student_id = %s AND sa.homework_id = %s AND sa.question_id = %s
        """
        answer_detail = db.execute_query(answer_sql, (student_id, homework_id, question_id))

        if not answer_detail:
            return jsonify({"success": False, "message": "答案记录不存在"}), 404

        answer = answer_detail[0]

        # 处理特殊字段
        if answer['question_type'] == 'choice' and answer['options']:
            try:
                answer['options'] = json.loads(answer['options'])
            except:
                answer['options'] = {}

        # 格式化时间字段
        for field in ['last_attempt_at', 'graded_at', 'created_at', 'updated_at']:
            if answer[field]:
                answer[field] = answer[field].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({"success": True, "data": answer})

    except Exception as e:
        logger.error(f"获取学生答题详情失败: {e}")
        return jsonify({"success": False, "message": "获取学生答题详情失败"}), 500

@teachers_bp.route('/api/teacher/submission/grade', methods=['POST'])
def grade_student_answer():
    """教师评分学生答案"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        teacher_id = session['user_id']
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400

        required_fields = ['student_id', 'homework_id', 'question_id', 'score']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400

        student_id = data['student_id']
        homework_id = data['homework_id']
        question_id = data['question_id']
        score = data['score']
        comment = data.get('comment', '')

        # 验证教师有权限评分此作业
        check_sql = """
            SELECT ha.id FROM homework_assignments ha
            WHERE ha.id = %s AND ha.teacher_id = %s
        """
        if not db.execute_query(check_sql, (homework_id, teacher_id)):
            return jsonify({"success": False, "message": "无权限评分此作业"}), 403

        # 获取题目分数上限
        question_sql = """
            SELECT score FROM homework_questions
            WHERE homework_id = %s AND question_id = %s
        """
        question_info = db.execute_query(question_sql, (homework_id, question_id))

        if not question_info:
            return jsonify({"success": False, "message": "题目不存在于作业中"}), 404

        max_score = question_info[0]['score'] or 0

        # 验证分数合理性
        if score < 0 or score > max_score:
            return jsonify({"success": False, "message": f"分数必须在0-{max_score}之间"}), 400

        # 更新学生答案
        update_sql = """
            UPDATE student_answers
            SET score = %s, teacher_comment = %s, status = 'graded', graded_at = NOW()
            WHERE student_id = %s AND homework_id = %s AND question_id = %s
        """

        affected = db.execute_update(update_sql, (score, comment, student_id, homework_id, question_id))

        if affected > 0:
            logger.info(f"教师 {teacher_id} 为学生 {student_id} 的题目 {question_id} 评分成功: {score} 分")

            return jsonify({
                "success": True,
                "message": "评分成功",
                "data": {
                    "student_id": student_id,
                    "question_id": question_id,
                    "score": score,
                    "max_score": max_score
                }
            })
        else:
            return jsonify({"success": False, "message": "评分失败，可能答案不存在"}), 404

    except Exception as e:
        logger.error(f"教师评分失败: {e}")
        return jsonify({"success": False, "message": "评分失败"}), 500
