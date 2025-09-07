from flask import Blueprint, jsonify, request, session
from database import db
import logging

logger = logging.getLogger(__name__)
courses_bp = Blueprint('courses', __name__)

@courses_bp.route('/api/courses', methods=['GET'])
def get_courses():
    """获取所有课程列表"""
    try:
        sql = """
            SELECT course_id as id, course_name as name, language, description, created_at, updated_at
            FROM courses 
            ORDER BY course_name
        """
        courses = db.execute_query(sql)
        return jsonify({"success": True, "data": courses})
    except Exception as e:
        logger.error(f"获取课程列表失败: {e}")
        return jsonify({"success": False, "message": "获取课程列表失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course(course_id):
    """获取单个课程信息"""
    try:
        sql = """
            SELECT course_id as id, course_name as name, language, description, created_at, updated_at
            FROM courses 
            WHERE course_id = %s
        """
        course = db.execute_query(sql, (course_id,))
        
        if course:
            return jsonify({"success": True, "data": course[0]})
        return jsonify({"success": False, "message": "课程不存在"}), 404
    except Exception as e:
        logger.error(f"获取课程信息失败: {e}")
        return jsonify({"success": False, "message": "获取课程信息失败"}), 500

@courses_bp.route('/api/courses', methods=['POST'])
def create_course():
    """创建新课程"""
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
            
        required_fields = ['name', 'language']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400
        
        # 验证语言类型
        if data['language'] not in ['C++', 'Python']:
            return jsonify({"success": False, "message": "语言类型必须是C++或Python"}), 400

        sql = """
            INSERT INTO courses (course_name, language, description)
            VALUES (%s, %s, %s)
        """
        params = (
            data['name'],
            data['language'],
            data.get('description', '')
        )
        
        affected = db.execute_update(sql, params)
        
        if affected > 0:
            # 获取新创建的课程
            get_sql = "SELECT * FROM courses WHERE course_id = LAST_INSERT_ID()"
            new_course = db.execute_query(get_sql)[0]
            
            logger.info(f"课程创建成功: {data['name']}")
            return jsonify({
                "success": True, 
                "message": "课程创建成功",
                "data": new_course
            }), 201
        
        return jsonify({"success": False, "message": "课程创建失败"}), 400
    except Exception as e:
        logger.error(f"创建课程失败: {e}")
        return jsonify({"success": False, "message": "创建课程失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>', methods=['PUT'])
def update_course(course_id):
    """更新课程信息"""
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
            return jsonify({"success": False, "message": "无更新数据"}), 400
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        allowed_fields = ['name', 'language', 'description']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                update_values.append(data[field])
        
        if not update_fields:
            return jsonify({"success": False, "message": "没有有效的更新字段"}), 400
        
        # 验证语言类型
        if 'language' in data and data['language'] not in ['C++', 'Python']:
            return jsonify({"success": False, "message": "语言类型必须是C++或Python"}), 400
        
        # 添加课程ID到参数列表
        update_values.append(course_id)
        
        sql = f"UPDATE courses SET {', '.join(update_fields)} WHERE course_id = %s"
        affected = db.execute_update(sql, update_values)
        
        if affected > 0:
            logger.info(f"课程 {course_id} 更新成功")
            return jsonify({"success": True, "message": "课程更新成功"})
        
        return jsonify({"success": False, "message": "课程不存在或未更改"}), 404
    except Exception as e:
        logger.error(f"更新课程失败: {e}")
        return jsonify({"success": False, "message": "更新课程失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>', methods=['DELETE'])
def delete_course(course_id):
    """删除课程"""
    try:
        # 检查管理员权限
        if 'identity' not in session or session['identity'] != 'admin':
            return jsonify({
                "success": False, 
                "message": "需要管理员权限",
                "redirect": "/login"
            }), 401

        # 检查课程是否有关联的班级
        check_classes_sql = "SELECT COUNT(*) as count FROM classes WHERE course_id = %s"
        class_count = db.execute_query(check_classes_sql, (course_id,))[0]['count']
        
        if class_count > 0:
            return jsonify({
                "success": False, 
                "message": "无法删除课程，该课程下有关联的班级"
            }), 400
        
        # 检查课程是否有关联的教师
        check_teachers_sql = "SELECT COUNT(*) as count FROM teacher_courses WHERE course_id = %s"
        teacher_count = db.execute_query(check_teachers_sql, (course_id,))[0]['count']
        
        if teacher_count > 0:
            return jsonify({
                "success": False, 
                "message": "无法删除课程，该课程有关联的教师"
            }), 400

        sql = "DELETE FROM courses WHERE course_id = %s"
        affected = db.execute_update(sql, (course_id,))
        
        if affected > 0:
            logger.info(f"课程 {course_id} 删除成功")
            return jsonify({"success": True, "message": "课程删除成功"})
        
        return jsonify({"success": False, "message": "课程不存在"}), 404
    except Exception as e:
        logger.error(f"删除课程失败: {e}")
        return jsonify({"success": False, "message": "删除课程失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>/classes', methods=['GET'])
def get_course_classes(course_id):
    """获取课程的所有班级"""
    try:
        sql = """
            SELECT c.id, c.class_name, c.description, c.created_at, c.updated_at,
                   t.username as teacher_name, t.teacher_id as teacher_id
            FROM classes c
            JOIN teachers t ON c.teacher_id = t.teacher_id
            WHERE c.course_id = %s
            ORDER BY c.class_name
        """
        classes = db.execute_query(sql, (course_id,))
        return jsonify({"success": True, "data": classes})
    except Exception as e:
        logger.error(f"获取课程班级失败: {e}")
        return jsonify({"success": False, "message": "获取课程班级失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>/teachers', methods=['GET'])
def get_course_teachers(course_id):
    """获取教授该课程的所有教师"""
    try:
        sql = """
            SELECT t.teacher_id as id, t.username, t.email, t.telenum, tc.created_at
            FROM teacher_courses tc
            JOIN teachers t ON tc.teacher_id = t.teacher_id
            WHERE tc.course_id = %s
            ORDER BY t.username
        """
        teachers = db.execute_query(sql, (course_id,))
        return jsonify({"success": True, "data": teachers})
    except Exception as e:
        logger.error(f"获取课程教师失败: {e}")
        return jsonify({"success": False, "message": "获取课程教师失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>/students', methods=['GET'])
def get_course_students(course_id):
    """获取选修该课程的所有学生"""
    try:
        sql = """
            SELECT DISTINCT s.student_id as id, s.username, s.email, s.telenum, s.student_id,
                   c.class_name, t.username as teacher_name
            FROM student_classes sc
            JOIN classes c ON sc.class_id = c.class_id
            JOIN students s ON sc.student_id = s.student_id
            JOIN teachers t ON c.teacher_id = t.teacher_id
            WHERE c.course_id = %s
            ORDER BY s.username
        """
        students = db.execute_query(sql, (course_id,))
        return jsonify({"success": True, "data": students})
    except Exception as e:
        logger.error(f"获取课程学生失败: {e}")
        return jsonify({"success": False, "message": "获取课程学生失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>/available-students/<int:class_id>', methods=['GET'])
def get_available_students_for_class(course_id, class_id):
    """获取课程中可添加到指定班级的学生列表（排除已在该班级的学生）"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 检查教师是否有权限管理该课程和班级
        check_sql = """
            SELECT COUNT(*) as count
            FROM classes c
            JOIN teacher_courses tc ON c.course_id = tc.course_id
            WHERE c.class_id = %s AND tc.teacher_id = %s AND c.course_id = %s
        """
        has_permission = db.execute_query(check_sql, (class_id, session['user_id'], course_id))[0]['count']

        if not has_permission:
            return jsonify({
                "success": False,
                "message": "没有权限管理该班级"
            }), 403

        sql = """
            SELECT s.student_id as id, s.username, s.email, s.telenum
            FROM students s
            WHERE s.status = 'active'
            AND s.student_id NOT IN (
                SELECT sc.student_id
                FROM student_classes sc
                WHERE sc.class_id = %s
            )
            AND s.student_id IN (
                SELECT DISTINCT sc.student_id
                FROM student_classes sc
                JOIN classes c ON sc.class_id = c.class_id
                WHERE c.course_id = %s
            )
            ORDER BY s.username
        """
        students = db.execute_query(sql, (class_id, course_id))
        return jsonify({"success": True, "data": students})
    except Exception as e:
        logger.error(f"获取可添加学生列表失败: {e}")
        return jsonify({"success": False, "message": "获取可添加学生列表失败"}), 500

@courses_bp.route('/api/courses/<int:course_id>/unenrolled-students', methods=['GET'])
def get_unenrolled_students_for_course(course_id):
    """获取未选择该课程的所有学生列表 - 核心业务逻辑"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 检查教师是否有权限管理该课程
        check_sql = """
            SELECT COUNT(*) as count
            FROM teacher_courses tc
            WHERE tc.course_id = %s AND tc.teacher_id = %s
        """
        has_permission = db.execute_query(check_sql, (course_id, session['user_id']))[0]['count']

        if not has_permission:
            return jsonify({
                "success": False,
                "message": "没有权限管理该课程"
            }), 403

        # 获取搜索参数
        search_term = request.args.get('search', '').strip()

        # 核心SQL查询：查找所有未选择该课程的活跃学生
        # 使用LEFT JOIN确保获取所有学生，然后过滤掉已选课的学生
        sql = """
            SELECT DISTINCT
                s.student_id as id,
                s.username,
                s.email,
                s.telenum,
                s.student_id as student_id,
                s.status,
                s.created_at
            FROM students s
            WHERE s.status = 'active'
            AND s.student_id NOT IN (
                SELECT DISTINCT sc.student_id
                FROM student_classes sc
                INNER JOIN classes c ON sc.class_id = c.class_id
                WHERE c.course_id = %s
            )
        """

        params = [course_id]

        # 如果有搜索条件，添加搜索过滤
        if search_term:
            sql += " AND (s.username LIKE %s OR s.email LIKE %s OR s.student_id LIKE %s)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        sql += " ORDER BY s.username"

        students = db.execute_query(sql, params)

        # 添加详细的调试日志
        logger.info(f"课程 {course_id} 的未选课学生查询:")
        logger.info(f"  - 教师ID: {session['user_id']}")
        logger.info(f"  - 搜索条件: '{search_term}'")
        logger.info(f"  - 找到学生数量: {len(students)}")
        if students:
            logger.info(f"  - 示例学生: {students[0]['username']} (ID: {students[0]['id']})")

        return jsonify({
            "success": True,
            "data": students,
            "course_id": course_id,
            "search_term": search_term,
            "total_count": len(students)
        })

    except Exception as e:
        logger.error(f"获取未选课学生列表失败: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"获取未选课学生列表失败: {str(e)}"
        }), 500
