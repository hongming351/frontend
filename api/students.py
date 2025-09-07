from flask import Blueprint, jsonify, request, session
from database import db
import logging
import hashlib
import csv
import io
import json
import re
import zipfile
import tempfile
import os
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
students_bp = Blueprint('students', __name__)

@students_bp.route('/api/students/profile', methods=['GET'])
def get_student_profile():
    """获取当前学生个人资料"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        # 查询学生详细信息
        sql = """
            SELECT student_id as id, username, email, telenum, status, created_at
            FROM students
            WHERE student_id = %s
        """
        student = db.execute_query(sql, (student_id,))
        
        if not student:
            return jsonify({"success": False, "message": "学生信息不存在"}), 404
            
        logger.info(f"获取学生 {student_id} 个人资料成功")
        return jsonify({"success": True, "data": student[0]})
    except Exception as e:
        logger.error(f"获取学生个人资料失败: {e}")
        return jsonify({"success": False, "message": "获取个人资料失败"}), 500

@students_bp.route('/api/student/course/info', methods=['GET'])
def get_course_info():
    """获取课程和班级信息"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        course_id = request.args.get('course_id')
        class_id = request.args.get('class_id')

        if not course_id:
            return jsonify({"success": False, "message": "缺少课程ID参数"}), 400

        # 获取课程信息
        course_sql = """
            SELECT course_id, course_name, description
            FROM courses
            WHERE course_id = %s
        """
        course = db.execute_query(course_sql, (course_id,))

        if not course:
            return jsonify({"success": False, "message": "课程不存在"}), 404

        result = {
            "course_id": course[0]['course_id'],
            "course_name": course[0]['course_name'],
            "description": course[0]['description']
        }

        # 如果提供了班级ID，获取班级信息
        if class_id:
            class_sql = """
                SELECT class_id, class_name, teacher_id
                FROM classes
                WHERE class_id = %s
            """
            class_info = db.execute_query(class_sql, (class_id,))

            if class_info:
                # 获取教师信息
                teacher_sql = "SELECT username FROM teachers WHERE teacher_id = %s"
                teacher = db.execute_query(teacher_sql, (class_info[0]['teacher_id'],))

                result.update({
                    "class_id": class_info[0]['class_id'],
                    "class_name": class_info[0]['class_name'],
                    "teacher_name": teacher[0]['username'] if teacher else "未知教师"
                })
            else:
                result.update({
                    "class_id": None,
                    "class_name": "班级信息获取失败",
                    "teacher_name": "未知教师"
                })
        else:
            # 如果没有提供班级ID，尝试获取学生在该课程中的班级信息
            class_sql = """
                SELECT c.class_id, c.class_name, c.teacher_id
                FROM classes c
                JOIN student_classes sc ON c.class_id = sc.class_id
                JOIN teacher_courses tc ON c.teacher_id = tc.teacher_id
                WHERE sc.student_id = %s AND tc.course_id = %s
                LIMIT 1
            """
            class_info = db.execute_query(class_sql, (student_id, course_id))

            if class_info:
                teacher_sql = "SELECT username FROM teachers WHERE teacher_id = %s"
                teacher = db.execute_query(teacher_sql, (class_info[0]['teacher_id'],))

                result.update({
                    "class_id": class_info[0]['class_id'],
                    "class_name": class_info[0]['class_name'],
                    "teacher_name": teacher[0]['username'] if teacher else "未知教师"
                })
            else:
                result.update({
                    "class_id": None,
                    "class_name": "未找到班级信息",
                    "teacher_name": "未知教师"
                })

        logger.info(f"学生 {student_id} 获取课程 {course_id} 信息成功")
        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"获取课程信息失败: {e}")
        return jsonify({"success": False, "message": "获取课程信息失败"}), 500

@students_bp.route('/api/student/assignments', methods=['GET'])
def get_student_assignments():
    """获取学生的作业表列表"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        course_id = request.args.get('course_id')
        class_id = request.args.get('class_id')

        if not course_id:
            return jsonify({"success": False, "message": "缺少课程ID参数"}), 400

        # 获取作业表
        assignments_sql = """
            SELECT DISTINCT
                ha.id as id,
                ha.title,
                ha.description,
                ha.deadline as deadline,
                ha.created_at
            FROM homework_assignments ha
            WHERE ha.course_id = %s
        """

        params = [course_id]

        # 如果提供了班级ID，进一步筛选
        if class_id:
            assignments_sql += " AND ha.class_id = %s"
            params.append(class_id)
        else:
            # 如果没有班级ID，获取学生所有班级的作业
            assignments_sql += """
                AND ha.class_id IN (
                    SELECT sc.class_id
                    FROM student_classes sc
                    WHERE sc.student_id = %s
                )
            """
            params.append(student_id)

        assignments_sql += " ORDER BY ha.created_at DESC"

        assignments = db.execute_query(assignments_sql, tuple(params))

        # 为每个作业查询完成状态
        for assignment in assignments:
            # 查询该学生在该作业中的提交记录数
            submission_check_sql = """
                SELECT COUNT(*) as submission_count
                FROM student_answers sa
                WHERE sa.student_id = %s AND sa.homework_id = %s
                AND sa.status IN ('submitted', 'graded')
            """
            submission_result = db.execute_query(submission_check_sql, (student_id, assignment['id']))

            # 如果有提交记录，标记为已完成，否则为进行中
            assignment['status'] = 'completed' if submission_result and submission_result[0]['submission_count'] > 0 else 'pending'

            # 处理时间格式
            if assignment['deadline']:
                assignment['deadline'] = assignment['deadline'].strftime('%Y-%m-%d %H:%M:%S')

        logger.info(f"学生 {student_id} 获取课程 {course_id} 的作业表列表成功，共 {len(assignments)} 个作业")
        return jsonify({"success": True, "data": assignments})

    except Exception as e:
        logger.error(f"获取作业表失败: {e}")
        return jsonify({"success": False, "message": "获取作业表失败"}), 500

@students_bp.route('/api/student/assignment/detail', methods=['GET'])
def get_assignment_detail():
    """获取作业详情"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        assignment_id = request.args.get('assignment_id')
        if not assignment_id:
            return jsonify({"success": False, "message": "缺少作业ID参数"}), 400

        # 获取作业基本信息
        assignment_sql = """
            SELECT
                ha.id,
                ha.title,
                ha.description,
                ha.deadline as publish_deadline,
                ha.created_at,
                CASE
                    WHEN EXISTS(
                        SELECT 1 FROM student_answers sa
                        WHERE sa.student_id = %s AND sa.homework_id = ha.id
                        AND sa.status IN ('submitted', 'graded')
                    ) THEN 'completed'
                    ELSE 'pending'
                END as status
            FROM homework_assignments ha
            WHERE ha.id = %s
        """
        assignment = db.execute_query(assignment_sql, (student_id, assignment_id))

        if not assignment:
            return jsonify({"success": False, "message": "作业不存在"}), 404

        assignment_data = assignment[0]

        # 获取作业包含的题目
        problems_sql = """
            SELECT
                hq.question_id as id,
                CASE
                    WHEN hq.question_type = 'progressing' THEN pq.title
                    WHEN hq.question_type = 'choice' THEN cq.title
                    WHEN hq.question_type = 'judgment' THEN jq.title
                END as title,
                CASE
                    WHEN hq.question_type = 'progressing' THEN pq.description
                    WHEN hq.question_type = 'choice' THEN cq.description
                    WHEN hq.question_type = 'judgment' THEN jq.description
                END as description,
                CASE
                    WHEN hq.question_type = 'progressing' THEN pq.difficulty
                    WHEN hq.question_type = 'choice' THEN cq.difficulty
                    WHEN hq.question_type = 'judgment' THEN jq.difficulty
                END as difficulty,
                CASE
                    WHEN hq.question_type = 'progressing' THEN '编程题'
                    WHEN hq.question_type = 'choice' THEN '选择题'
                    WHEN hq.question_type = 'judgment' THEN '判断题'
                    ELSE hq.question_type
                END as type,
                hq.score,
                CASE
                    WHEN sa.status IS NOT NULL AND sa.status IN ('submitted', 'graded') THEN 'completed'
                    ELSE 'pending'
                END as status
            FROM homework_questions hq
            LEFT JOIN progressing_questions pq ON hq.question_id = pq.progressing_questions_id AND hq.question_type = 'progressing'
            LEFT JOIN choice_questions cq ON hq.question_id = cq.choice_questions_id AND hq.question_type = 'choice'
            LEFT JOIN judgment_questions jq ON hq.question_id = jq.judgment_questions_id AND hq.question_type = 'judgment'
            LEFT JOIN student_answers sa ON hq.question_id = sa.question_id
                AND sa.homework_id = hq.homework_id
                AND sa.student_id = %s
            WHERE hq.homework_id = %s
            ORDER BY hq.order_num
        """

        problems = db.execute_query(problems_sql, (student_id, assignment_id))

        # 处理题目数据，确保没有NULL值
        for problem in problems:
            # 处理可能为NULL的字段
            problem['title'] = problem['title'] or f"题目 {problem['id']} (数据缺失)"
            problem['description'] = problem['description'] or "暂无描述"
            problem['difficulty'] = problem['difficulty'] or "未知"

        # 计算完成统计
        total_problems = len(problems)
        completed_problems = sum(1 for p in problems if p['status'] == 'completed')

        result = {
            "id": assignment_data['id'],
            "title": assignment_data['title'],
            "description": assignment_data['description'],
            "deadline": assignment_data['publish_deadline'].strftime('%Y-%m-%d %H:%M:%S') if assignment_data['publish_deadline'] else None,
            "status": assignment_data['status'],
            "total_problems": total_problems,
            "completed_problems": completed_problems,
            "problems": problems
        }

        logger.info(f"学生 {student_id} 获取作业 {assignment_id} 详情成功")
        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"获取作业详情失败: {e}")
        return jsonify({"success": False, "message": "获取作业详情失败"}), 500

@students_bp.route('/api/student/problem/detail', methods=['GET'])
def get_problem_detail():
    """获取题目详情用于答题"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        problem_id = request.args.get('problem_id')
        assignment_id = request.args.get('assignment_id')

        if not problem_id:
            return jsonify({"success": False, "message": "缺少题目ID参数"}), 400

        if not assignment_id:
            return jsonify({"success": False, "message": "缺少作业ID参数"}), 400

        # 验证作业是否存在
        assignment_check_sql = "SELECT id FROM homework_assignments WHERE id = %s"
        assignment_exists = db.execute_query(assignment_check_sql, (assignment_id,))
        if not assignment_exists:
            return jsonify({"success": False, "message": "作业不存在"}), 404

        # 首先获取题目在作业中的信息
        homework_question_sql = """
            SELECT hq.question_id, hq.question_type
            FROM homework_questions hq
            WHERE hq.question_id = %s AND hq.homework_id = %s
        """

        homework_question = db.execute_query(homework_question_sql, (problem_id, assignment_id))

        if not homework_question:
            return jsonify({"success": False, "message": "题目不存在于作业中"}), 404

        question_type = homework_question[0]['question_type']

        # 根据题目类型获取详细信息
        if question_type == 'progressing':
            # 获取编程题详情
            sql = """
                SELECT
                    progressing_questions_id as id,
                    title,
                    description,
                    language,
                    difficulty,
                    knowledge_points,
                    input_description,
                    output_description,
                    solution_idea,
                    reference_code,
                    created_at,
                    'progressing' as question_type
                FROM progressing_questions
                WHERE progressing_questions_id = %s
            """

            # 获取第一个示例测试用例的SQL查询
            test_case_sql = """
                SELECT input, output
                FROM progressing_questions_test_cases
                WHERE progressing_questions_id = %s AND is_example = 1
                ORDER BY id
                LIMIT 1
            """
        elif question_type == 'choice':
            # 获取选择题详情
            sql = """
                SELECT
                    choice_questions_id as id,
                    title,
                    description,
                    language,
                    difficulty,
                    knowledge_points,
                    options,
                    correct_answer,
                    solution_idea,
                    created_at,
                    'choice' as question_type
                FROM choice_questions
                WHERE choice_questions_id = %s
            """
        elif question_type == 'judgment':
            # 获取判断题详情
            sql = """
                SELECT
                    judgment_questions_id as id,
                    title,
                    description,
                    language,
                    difficulty,
                    knowledge_points,
                    correct_answer,
                    solution_idea,
                    created_at,
                    'judgment' as question_type
                FROM judgment_questions
                WHERE judgment_questions_id = %s
            """
        else:
            return jsonify({"success": False, "message": "未知题目类型"}), 400

        problem = db.execute_query(sql, (problem_id,))

        if not problem:
            return jsonify({"success": False, "message": "题目不存在"}), 404

        problem_data = problem[0]

        # 处理特殊字段
        if question_type == 'progressing':
            # 获取编程题的第一个示例测试用例
            test_case = db.execute_query(test_case_sql, (problem_id,))
            if test_case:
                problem_data['sample_input'] = test_case[0]['input']
                problem_data['sample_output'] = test_case[0]['output']
            else:
                problem_data['sample_input'] = ""
                problem_data['sample_output'] = ""

        elif question_type == 'choice':
            # 解析选项JSON
            if problem_data['options']:
                try:
                    if isinstance(problem_data['options'], str):
                        problem_data['options'] = json.loads(problem_data['options'])
                    else:
                        problem_data['options'] = problem_data['options']
                except (json.JSONDecodeError, TypeError):
                    problem_data['options'] = {}

        # 格式化时间字段
        if problem_data['created_at']:
            problem_data['created_at'] = problem_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        # 清理可能为NULL的字段
        for key in problem_data:
            if problem_data[key] is None:
                problem_data[key] = ""

        logger.info(f"学生 {student_id} 获取题目 {problem_id} (类型: {question_type}) 详情成功")
        return jsonify({"success": True, "data": problem_data})

    except Exception as e:
        logger.error(f"获取题目详情失败: {e}")
        return jsonify({"success": False, "message": "获取题目详情失败"}), 500

@students_bp.route('/api/student/courses', methods=['GET'])
def get_student_courses():
    """获取当前登录学生所参加的课程列表"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        # 查询学生参加的课程，包括班级信息
        # 使用子查询确保每个课程只返回一次，选择第一个班级作为主要信息
        sql = """
            SELECT
                co.course_id AS id,
                co.course_name AS name,
                co.description AS description,
                t.username AS teacher_name,
                sc.class_id AS class_id,
                c.class_name AS class_name
            FROM courses co
            JOIN teacher_courses tc ON co.course_id = tc.course_id
            JOIN teachers t ON tc.teacher_id = t.teacher_id
            JOIN classes c ON t.teacher_id = c.teacher_id
            JOIN student_classes sc ON c.class_id = sc.class_id
            WHERE sc.student_id = %s
            AND sc.class_id = (
                SELECT MIN(sc2.class_id)
                FROM student_classes sc2
                JOIN classes c2 ON sc2.class_id = c2.class_id
                WHERE sc2.student_id = %s AND c2.course_id = co.course_id
            )
            ORDER BY co.course_name;
        """
        courses = db.execute_query(sql, (student_id, student_id))
        
        logger.info(f"学生 {student_id} 的课程列表: {courses}")
        return jsonify({"success": True, "data": courses})
    except Exception as e:
        logger.error(f"获取学生课程列表失败: {e}")
        logger.error(f"SQL: {sql}")
        logger.error(f"参数: {(student_id,)}")
        import traceback
        logger.error(f"完整错误信息: {traceback.format_exc()}")
        return jsonify({"success": False, "message": f"获取课程列表失败: {str(e)}"}), 500

@students_bp.route('/api/students/register', methods=['POST'])
def register_single_student():
    """教师注册单个学生账号"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        username = data.get('username', '').strip()
        student_id = data.get('student_id', '').strip()
        email = data.get('email', '').strip()
        telenum = data.get('telenum', '').strip()
        password = data.get('password', student_id)  # 如果没有提供密码，默认使用学号

        # 验证必填字段
        if not all([username, student_id, email, telenum]):
            return jsonify({"success": False, "message": "请填写所有必填字段"}), 400

        # 验证用户名长度
        if len(username) < 2 or len(username) > 50:
            return jsonify({"success": False, "message": "用户名长度必须在2-50字符之间"}), 400

        # 验证学号长度
        if len(student_id) < 1 or len(student_id) > 20:
            return jsonify({"success": False, "message": "学号长度必须在1-20字符之间"}), 400

        # 验证邮箱格式
        import re
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            return jsonify({"success": False, "message": "邮箱格式不正确"}), 400

        # 验证手机号格式
        phone_regex = r'^1[3-9]\d{9}$'
        if not re.match(phone_regex, telenum):
            return jsonify({"success": False, "message": "手机号必须为11位数字且以1开头"}), 400

        # 检查用户名是否已存在
        check_username_sql = "SELECT COUNT(*) as count FROM students WHERE username = %s"
        username_exists = db.execute_query(check_username_sql, (username,))[0]['count']

        if username_exists:
            return jsonify({"success": False, "message": f"用户名 '{username}' 已存在"}), 400

        # 检查学号是否已存在
        check_student_id_sql = "SELECT COUNT(*) as count FROM students WHERE student_id = %s"
        student_id_exists = db.execute_query(check_student_id_sql, (student_id,))[0]['count']

        if student_id_exists:
            return jsonify({"success": False, "message": f"学号 '{student_id}' 已存在"}), 400

        # 检查邮箱是否已存在
        check_email_sql = "SELECT COUNT(*) as count FROM students WHERE email = %s"
        email_exists = db.execute_query(check_email_sql, (email,))[0]['count']

        if email_exists:
            return jsonify({"success": False, "message": f"邮箱 '{email}' 已被使用"}), 400

        # 检查手机号是否已存在
        check_telenum_sql = "SELECT COUNT(*) as count FROM students WHERE telenum = %s"
        telenum_exists = db.execute_query(check_telenum_sql, (telenum,))[0]['count']

        if telenum_exists:
            return jsonify({"success": False, "message": f"手机号 '{telenum}' 已被使用"}), 400

        # 密码哈希处理
        hashed_password = hashlib.md5(password.encode()).hexdigest()

        # 插入新学生记录
        insert_sql = """
            INSERT INTO students (username, student_id, password, email, telenum, status, created_at)
            VALUES (%s, %s, %s, %s, %s, 'active', NOW())
        """
        params = (username, student_id, hashed_password, email, telenum)

        affected = db.execute_update(insert_sql, params)

        if affected > 0:
            logger.info(f"教师注册学生账号成功: {username} (学号: {student_id})")

            return jsonify({
                "success": True,
                "message": "学生账号创建成功！初始密码为学号",
                "data": {
                    'username': username,
                    'student_id': student_id,
                    'email': email,
                    'telenum': telenum,
                    'default_password': password
                }
            })
        else:
            return jsonify({"success": False, "message": "学生账号创建失败"}), 500

    except Exception as e:
        logger.error(f"教师注册学生失败: {e}")
        return jsonify({"success": False, "message": "学生账号创建失败"}), 500


@students_bp.route('/api/students/batch-register', methods=['POST'])
def batch_register_students():
    """教师批量注册学生账号（通过CSV文件）"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "请上传CSV文件"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "请上传有效的CSV文件"}), 400

        # 检查文件类型
        if not file.filename.lower().endswith('.csv'):
            return jsonify({"success": False, "message": "只支持CSV文件格式"}), 400

        try:
            # 读取文件内容并检测编码
            file_content = file.stream.read()
            
            # 尝试多种编码方式（支持Excel生成的CSV文件）
            encodings_to_try = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            decoded_content = None
            
            for encoding in encodings_to_try:
                try:
                    decoded_content = file_content.decode(encoding)
                    logger.info(f"成功使用编码 {encoding} 解码CSV文件")
                    break
                except UnicodeDecodeError:
                    continue
            
            if decoded_content is None:
                return jsonify({"success": False, "message": "无法解码CSV文件，请使用UTF-8或GBK编码"}), 400

            # 处理不同行尾格式（Excel可能使用CRLF）
            decoded_content = decoded_content.replace('\r\n', '\n').replace('\r', '\n')
            
            # 使用更强大的CSV解析器，支持带引号的字段
            stream = io.StringIO(decoded_content)
            csv_reader = csv.reader(stream)

            # 读取表头
            try:
                headers = next(csv_reader)
            except StopIteration:
                return jsonify({"success": False, "message": "CSV文件为空或格式不正确"}), 400

            # 去除字段首尾空格和可能的引号
            headers = [h.strip().strip('"').strip("'") for h in headers]

            # 兼容 Excel 导出 UTF-8 BOM（再次检查，因为有些编码可能已经处理了BOM）
            if headers and isinstance(headers[0], str) and headers[0].startswith('\ufeff'):
                headers[0] = headers[0].replace('\ufeff', '')

            # 验证CSV格式（支持多种表头格式）
            valid_headers = [
                ['用户名', '学号', '邮箱', '手机号'],
                ['username', 'student_id', 'email', 'telenum'],
                ['name', 'student_id', 'email', 'phone'],
                ['姓名', '学号', '邮箱', '电话']
            ]

            header_valid = False
            for valid_header in valid_headers:
                if headers == valid_header:
                    header_valid = True
                    break

            if not header_valid:
                return jsonify({
                    "success": False,
                    "message": f"CSV文件格式不正确，请使用标准格式。检测到的表头: {headers}",
                    "detected_headers": headers
                }), 400

            # 解析学生数据
            students_data = []
            row_number = 1
            for row in csv_reader:
                row_number += 1
                # 跳过空行
                if not any(row) or len(row) < 4:
                    continue

                # 清理每个字段（去除空格和引号）
                cleaned_row = [field.strip().strip('"').strip("'") for field in row]
                
                # 确保至少有4个字段，不足的用空字符串填充
                while len(cleaned_row) < 4:
                    cleaned_row.append('')

                student_data = {
                    'username': cleaned_row[0],
                    'student_id': cleaned_row[1],
                    'email': cleaned_row[2],
                    'telenum': cleaned_row[3],
                    'row_number': row_number
                }
                students_data.append(student_data)

            if len(students_data) == 0:
                return jsonify({"success": False, "message": "CSV文件中没有有效的数据"}), 400

            if len(students_data) > 100:
                return jsonify({"success": False, "message": "单次最多只能上传100个学生"}), 400

            # 验证和处理学生数据
            success_count = 0
            error_messages = []
            processed_students = []

            for student in students_data:
                try:
                    # 验证必填字段（更详细的错误信息）
                    missing_fields = []
                    if not student['username']:
                        missing_fields.append('用户名')
                    if not student['student_id']:
                        missing_fields.append('学号')
                    if not student['email']:
                        missing_fields.append('邮箱')
                    if not student['telenum']:
                        missing_fields.append('手机号')
                    
                    if missing_fields:
                        error_messages.append(f"第{student['row_number']}行：以下字段不能为空: {', '.join(missing_fields)}")
                        continue

                    # 验证用户名长度
                    if len(student['username']) < 2 or len(student['username']) > 50:
                        error_messages.append(f"第{student['row_number']}行：用户名 '{student['username']}' 长度必须在2-50字符之间")
                        continue

                    # 验证学号长度
                    if len(student['student_id']) < 1 or len(student['student_id']) > 20:
                        error_messages.append(f"第{student['row_number']}行：学号 '{student['student_id']}' 长度必须在1-20字符之间")
                        continue

                    # 验证邮箱格式
                    import re
                    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                    if not re.match(email_regex, student['email']):
                        error_messages.append(f"第{student['row_number']}行：邮箱 '{student['email']}' 格式不正确")
                        continue

                    # 验证手机号格式
                    phone_regex = r'^1[3-9]\d{9}$'
                    if not re.match(phone_regex, student['telenum']):
                        error_messages.append(f"第{student['row_number']}行：手机号 '{student['telenum']}' 必须为11位数字且以1开头")
                        continue

                    # 检查用户名是否已存在
                    check_username_sql = "SELECT COUNT(*) as count FROM students WHERE username = %s"
                    username_exists = db.execute_query(check_username_sql, (student['username'],))[0]['count']

                    if username_exists:
                        error_messages.append(f"第{student['row_number']}行：用户名 '{student['username']}' 已存在")
                        continue

                    # 检查学号是否已存在
                    check_student_id_sql = "SELECT COUNT(*) as count FROM students WHERE student_id = %s"
                    student_id_exists = db.execute_query(check_student_id_sql, (student['student_id'],))[0]['count']

                    if student_id_exists:
                        error_messages.append(f"第{student['row_number']}行：学号 '{student['student_id']}' 已存在")
                        continue

                    # 检查邮箱是否已存在
                    check_email_sql = "SELECT COUNT(*) as count FROM students WHERE email = %s"
                    email_exists = db.execute_query(check_email_sql, (student['email'],))[0]['count']

                    if email_exists:
                        error_messages.append(f"第{student['row_number']}行：邮箱 '{student['email']}' 已被使用")
                        continue

                    # 检查手机号是否已存在
                    check_telenum_sql = "SELECT COUNT(*) as count FROM students WHERE telenum = %s"
                    telenum_exists = db.execute_query(check_telenum_sql, (student['telenum'],))[0]['count']

                    if telenum_exists:
                        error_messages.append(f"第{student['row_number']}行：手机号 '{student['telenum']}' 已被使用")
                        continue

                    # 密码默认为学号，使用MD5哈希
                    hashed_password = hashlib.md5(student['student_id'].encode()).hexdigest()

                    # 插入新学生记录
                    insert_sql = """
                        INSERT INTO students (username, student_id, password, email, telenum, status)
                        VALUES (%s, %s, %s, %s, %s, 'active')
                    """
                    params = (student['username'], student['student_id'], hashed_password,
                             student['email'], student['telenum'])

                    affected = db.execute_update(insert_sql, params)

                    if affected > 0:
                        success_count += 1
                        processed_students.append({
                            'username': student['username'],
                            'student_id': student['student_id'],
                            'email': student['email'],
                            'telenum': student['telenum'],
                            'default_password': student['student_id']
                        })
                        logger.info(f"批量注册学生成功: {student['username']} (学号: {student['student_id']})")

                except Exception as e:
                    error_messages.append(f"第{student['row_number']}行：处理失败 - {str(e)}")
                    logger.error(f"批量注册学生失败: {e}")

            # 返回处理结果
            result = {
                "success": success_count > 0,
                "message": f"成功注册 {success_count} 个学生账号",
                "data": {
                    "success_count": success_count,
                    "error_count": len(error_messages),
                    "processed_students": processed_students,
                    "error_messages": error_messages[:50]  # 最多返回50条错误信息
                }
            }

            # 如果有错误但也有成功的情况
            if success_count > 0 and error_messages:
                result["message"] += f"，{len(error_messages)} 个失败"
                result["success"] = True

            return jsonify(result), 200 if success_count > 0 else 400

        except Exception as e:
            logger.error(f"CSV文件处理失败: {e}")
            return jsonify({"success": False, "message": f"文件处理失败: {str(e)}"}), 400

    except Exception as e:
        logger.error(f"批量注册学生失败: {e}")
        return jsonify({"success": False, "message": "批量注册学生失败"}), 500

@students_bp.route('/api/students', methods=['GET'])
def get_all_students():
    """获取所有学生列表（教师端）"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 获取搜索参数
        search_term = request.args.get('search', '').strip()

        # 构建查询
        base_sql = """
            SELECT student_id, username, student_id as student_number,
                   email, telenum, status, created_at
            FROM students
            WHERE status = 'active'
        """

        params = []
        if search_term:
            base_sql += """
                AND (username LIKE %s OR student_id LIKE %s OR email LIKE %s)
            """
            search_pattern = f"%{search_term}%"
            params = [search_pattern, search_pattern, search_pattern]

        base_sql += " ORDER BY created_at DESC"

        students = db.execute_query(base_sql, tuple(params))

        logger.info(f"教师获取学生列表成功，共 {len(students)} 名学生")
        return jsonify({"success": True, "data": students})
    except Exception as e:
        logger.error(f"获取学生列表失败: {e}")
        return jsonify({"success": False, "message": "获取学生列表失败"}), 500

@students_bp.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """删除学生账号"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 检查学生是否存在
        check_sql = "SELECT username FROM students WHERE student_id = %s AND status = 'active'"
        student = db.execute_query(check_sql, (student_id,))

        if not student:
            return jsonify({"success": False, "message": "学生不存在"}), 404

        # 删除学生（软删除：将状态改为inactive）
        delete_sql = "UPDATE students SET status = 'inactive' WHERE student_id = %s"
        affected = db.execute_update(delete_sql, (student_id,))

        if affected > 0:
            logger.info(f"学生 {student_id} ({student[0]['username']}) 已被删除")
            return jsonify({
                "success": True,
                "message": f"学生 {student[0]['username']} 已被删除"
            })
        else:
            return jsonify({"success": False, "message": "删除失败"}), 500

    except Exception as e:
        logger.error(f"删除学生失败: {e}")
        return jsonify({"success": False, "message": "删除学生失败"}), 500

# 学生修改密码功能
@students_bp.route('/api/students/change-password', methods=['PUT'])
def change_student_password():
    """学生修改密码"""
    try:
        # 检查学生权限
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session['user_id']
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
        sql = "SELECT password FROM students WHERE student_id = %s"
        result = db.execute_query(sql, (student_id,))

        if not result:
            return jsonify({"success": False, "message": "用户不存在"}), 404

        stored_password = result[0]['password']

        # 验证原密码
        hashed_old_password = hashlib.md5(old_password.encode()).hexdigest()
        if hashed_old_password != stored_password:
            return jsonify({"success": False, "message": "原密码错误"}), 400

        # 检查新密码是否与原密码相同
        hashed_new_password = hashlib.md5(new_password.encode()).hexdigest()
        if hashed_new_password == stored_password:
            return jsonify({"success": False, "message": "新密码不能与原密码相同"}), 400

        # 更新密码
        update_sql = "UPDATE students SET password = %s WHERE student_id = %s"
        affected = db.execute_update(update_sql, (hashed_new_password, student_id))

        if affected > 0:
            logger.info(f"学生 {student_id} 密码修改成功")
            return jsonify({
                "success": True,
                "message": "密码修改成功，请重新登录",
                "logout_required": True
            })

        return jsonify({"success": False, "message": "密码修改失败"}), 400

    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return jsonify({"success": False, "message": "修改密码失败"}), 500

# 存储ZIP中的代码内容，用于后续提交
_zip_code_cache = {}

@students_bp.route('/api/student/run_zip_code', methods=['POST'])
def run_student_zip_code():
    """学生运行ZIP文件中的代码，进行测试"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        # 检查是否有文件上传
        if 'code_zip' not in request.files:
            return jsonify({"success": False, "message": "请上传zip文件"}), 400

        file = request.files['code_zip']
        if file.filename == '':
            return jsonify({"success": False, "message": "请上传有效的zip文件"}), 400

        # 检查文件类型
        if not file.filename.lower().endswith('.zip'):
            return jsonify({"success": False, "message": "只支持zip格式的文件"}), 400

        # 获取其他参数
        problem_id = request.form.get('problem_id')
        language = request.form.get('language', 'python')

        if not problem_id:
            return jsonify({"success": False, "message": "缺少题目ID参数"}), 400

        # 验证题目存在且为编程题
        problem_check_sql = """
            SELECT pq.progressing_questions_id, pq.title
            FROM progressing_questions pq
            WHERE pq.progressing_questions_id = %s
        """
        problem_info = db.execute_query(problem_check_sql, (problem_id,))
        if not problem_info:
            return jsonify({"success": False, "message": "题目不存在或不是编程题"}), 404

        # 保存上传的zip文件到临时位置
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_zip_path = temp_file.name

        try:
            # 从ZIP文件中提取并执行代码
            execution_result = _execute_zip_code(temp_zip_path, language, problem_id)

            # 将提取的代码存储在缓存中，供后续提交使用
            cache_key = f"{student_id}_{problem_id}"
            _zip_code_cache[cache_key] = {
                'code': execution_result.get('extracted_code', ''),
                'language': language,
                'timestamp': db.execute_query("SELECT NOW()")[0]['NOW()']
            }

            logger.info(f"学生 {student_id} ZIP代码运行完成 - 题目 {problem_id}")
            return jsonify({
                "success": True,
                "message": "ZIP文件代码运行完成",
                "data": execution_result
            })

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_zip_path)
            except:
                pass

    except Exception as e:
        logger.error(f"学生ZIP代码运行失败: {e}")
        return jsonify({"success": False, "message": f"运行失败：{str(e)}"}), 500

@students_bp.route('/api/student/submit_code_zip', methods=['POST'])
def submit_student_code_zip():
    """学生提交ZIP文件中的代码"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        # 获取参数
        problem_id = request.form.get('problem_id')
        assignment_id = request.form.get('assignment_id')

        if not all([problem_id, assignment_id]):
            return jsonify({"success": False, "message": "缺少必要参数"}), 400

        # 验证题目和作业关系
        homework_question_sql = """
            SELECT hq.question_id, hq.question_type
            FROM homework_questions hq
            WHERE hq.question_id = %s AND hq.homework_id = %s
        """
        homework_question = db.execute_query(homework_question_sql, (problem_id, assignment_id))

        if not homework_question:
            return jsonify({"success": False, "message": "题目不存在于作业中"}), 404

        if homework_question[0]['question_type'] != 'progressing':
            return jsonify({"success": False, "message": "此题目不是编程题"}), 400

        # 从缓存中获取之前运行的代码
        cache_key = f"{student_id}_{problem_id}"
        cached_code = _zip_code_cache.get(cache_key)

        if not cached_code:
            return jsonify({"success": False, "message": "未找到已运行的ZIP代码，请先运行代码"}), 400

        # 检查缓存是否过期（5分钟）
        import datetime
        if (datetime.datetime.now() - cached_code['timestamp']).seconds > 300:
            # 清理过期缓存
            del _zip_code_cache[cache_key]
            return jsonify({"success": False, "message": "代码已过期，请重新运行ZIP文件"}), 400

        # 获取题目分数并评估代码
        score_sql = "SELECT score FROM homework_questions WHERE question_id = %s AND homework_id = %s"
        score_result = db.execute_query(score_sql, (problem_id, assignment_id))
        score = score_result[0]['score'] if score_result else 0

        # 评估编程题答案
        is_correct = _evaluate_programming_answer(cached_code['code'], problem_id)

        # 准备答案数据
        answer_data = {
            'student_id': student_id,
            'homework_id': assignment_id,
            'question_id': problem_id,
            'question_type': 'progressing',
            'status': 'submitted',
            'is_correct': is_correct,
            'score': score if is_correct else 0
        }

        # 检查是否已提交过答案
        existing_answer_sql = """
            SELECT id FROM student_answers
            WHERE student_id = %s AND homework_id = %s AND question_id = %s
        """
        existing = db.execute_query(existing_answer_sql, (student_id, assignment_id, problem_id))

        if existing:
            return jsonify({"success": False, "message": "该题目已提交过答案，无法重复提交"}), 400

        # 插入答题记录
        insert_sql = """
            INSERT INTO student_answers
            (student_id, homework_id, question_id, question_type, answer_text, status, is_correct, score, last_attempt_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        params = (
            answer_data['student_id'], answer_data['homework_id'], answer_data['question_id'],
            answer_data['question_type'], cached_code['code'], answer_data['status'],
            answer_data['is_correct'], answer_data['score']
        )

        affected = db.execute_update(insert_sql, params)

        if affected > 0:
            # 记录编程题提交历史
            if answer_data['question_type'] == 'progressing':
                _record_programming_submission(student_id, assignment_id, problem_id, cached_code['code'])

            # 清理缓存
            del _zip_code_cache[cache_key]

            logger.info(f"学生 {student_id} ZIP代码提交题目 {problem_id} 成功 - 评判结果: {'正确' if is_correct else '错误'}")
            return jsonify({
                "success": True,
                "message": "ZIP代码提交成功！",
                "data": {
                    "course_id": homework_question[0]['course_id'],
                    "class_id": homework_question[0]['class_id'],
                    "is_correct": is_correct,
                    "score": answer_data['score']
                }
            })

    except Exception as e:
        logger.error(f"学生ZIP代码提交失败: {e}")
        return jsonify({"success": False, "message": f"提交失败：{str(e)}"}), 500

@students_bp.route('/api/student/submit_answer', methods=['POST'])
def submit_student_answer():
    """学生提交题目答案"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        problem_id = data.get('problem_id')
        assignment_id = data.get('assignment_id')
        answer = data.get('answer')
        answer_type = data.get('answer_type')

        if not all([problem_id, assignment_id, answer_type]):
            return jsonify({"success": False, "message": "缺少必要参数"}), 400

        # 验证题目和作业关系
        homework_question_sql = """
            SELECT hq.question_id, hq.question_type, hq.score, ha.course_id, ha.class_id
            FROM homework_questions hq
            JOIN homework_assignments ha ON hq.homework_id = ha.id
            WHERE hq.question_id = %s AND hq.homework_id = %s
        """
        homework_question = db.execute_query(homework_question_sql, (problem_id, assignment_id))

        if not homework_question:
            return jsonify({"success": False, "message": "题目不存在于作业中"}), 404

        question_data = homework_question[0]
        question_type = question_data['question_type']
        score = question_data['score'] or 0
        course_id = question_data['course_id']
        class_id = question_data['class_id']

        # 验证答案格式
        if not _validate_answer_format(answer, question_type):
            return jsonify({"success": False, "message": "答案格式不正确"}), 400

        # 检查是否已提交过答案（不允许重复提交）
        existing_answer_sql = """
            SELECT id FROM student_answers
            WHERE student_id = %s AND homework_id = %s AND question_id = %s
        """
        existing_answer = db.execute_query(existing_answer_sql, (student_id, assignment_id, problem_id))

        if existing_answer:
            return jsonify({"success": False, "message": "该题目已提交过答案，无法重复提交"}), 400

        # 准备答案数据
        answer_data = {
            'student_id': student_id,
            'homework_id': assignment_id,
            'question_id': problem_id,
            'question_type': question_type,
            'status': 'submitted',
            'last_attempt_at': db.execute_query("SELECT NOW()")[0]['NOW()']
        }

        # 根据题目类型处理答案
        if question_type == 'progressing':
            answer_data['answer_text'] = answer
            # 编程题自动评分（这里可以调用代码运行服务）
            is_correct = _evaluate_programming_answer(answer, problem_id)
            answer_data['is_correct'] = is_correct
            answer_data['score'] = score if is_correct else 0
        elif question_type == 'choice':
            answer_data['choice_answer'] = answer
            # 选择题自动评分
            correct_answer = _get_choice_correct_answer(problem_id)
            is_correct = answer == correct_answer
            answer_data['is_correct'] = is_correct
            answer_data['score'] = score if is_correct else 0
        elif question_type == 'judgment':
            answer_data['judgment_answer'] = 1 if answer.lower() == 'true' else 0
            # 判断题自动评分
            correct_answer = _get_judgment_correct_answer(problem_id)
            is_correct = answer_data['judgment_answer'] == correct_answer
            answer_data['is_correct'] = is_correct
            answer_data['score'] = score if is_correct else 0

        # 插入答案记录
        insert_sql = """
            INSERT INTO student_answers
            (student_id, homework_id, question_id, question_type, answer_text, choice_answer, judgment_answer,
             is_correct, score, status, last_attempt_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            answer_data['student_id'], answer_data['homework_id'], answer_data['question_id'],
            answer_data['question_type'], answer_data.get('answer_text'), answer_data.get('choice_answer'),
            answer_data.get('judgment_answer'), answer_data['is_correct'], answer_data['score'],
            answer_data['status'], answer_data['last_attempt_at']
        )

        affected = db.execute_update(insert_sql, params)

        if affected > 0:
            # 记录编程题提交历史（如果需要）
            if question_type == 'progressing':
                _record_programming_submission(student_id, assignment_id, problem_id, answer)

            logger.info(f"学生 {student_id} 提交题目 {problem_id} 答案成功")

            return jsonify({
                "success": True,
                "message": "作业提交成功",
                "data": {
                    "course_id": course_id,
                    "class_id": class_id,
                    "is_correct": answer_data['is_correct'],
                    "score": answer_data['score']
                }
            })
        else:
            return jsonify({"success": False, "message": "答案保存失败"}), 500

    except Exception as e:
        logger.error(f"学生提交答案失败: {e}")
        return jsonify({"success": False, "message": "提交失败，请重试"}), 500

def _validate_answer_format(answer, question_type):
    """验证答案格式"""
    if not answer or not answer.strip():
        return False

    if question_type == 'choice':
        return answer in ['A', 'B', 'C', 'D', 'a', 'b', 'c', 'd']
    elif question_type == 'judgment':
        return answer.lower() in ['true', 'false', '1', '0', '正确', '错误']
    elif question_type == 'progressing':
        return len(answer.strip()) > 0
    return False

def _evaluate_programming_answer(code, problem_id):
    """评估编程题答案（简化版，实际应该调用代码运行服务）"""
    # 这里应该调用代码运行和测试服务
    # 暂时返回随机结果作为示例
    import random
    return random.choice([True, False])

def _get_choice_correct_answer(problem_id):
    """获取选择题正确答案"""
    sql = "SELECT correct_answer FROM choice_questions WHERE choice_questions_id = %s"
    result = db.execute_query(sql, (problem_id,))
    return result[0]['correct_answer'] if result else None

def _get_judgment_correct_answer(problem_id):
    """获取判断题正确答案"""
    sql = "SELECT correct_answer FROM judgment_questions WHERE judgment_questions_id = %s"
    result = db.execute_query(sql, (problem_id,))
    return result[0]['correct_answer'] if result else None

def _record_programming_submission(student_id, homework_id, question_id, code):
    """记录编程题提交历史"""
    try:
        sql = """
            INSERT INTO programming_submissions
            (student_id, homework_id, question_id, submission_code, submit_time, run_status)
            VALUES (%s, %s, %s, %s, NOW(), 'success')
        """
        db.execute_update(sql, (student_id, homework_id, question_id, code))
    except Exception as e:
        logger.error(f"记录编程题提交历史失败: {e}")
        # 不影响主流程

@students_bp.route('/api/student/run_code', methods=['POST'])
def run_student_code():
    """学生运行编程题代码"""
    try:
        # 检查学生会话
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False,
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session.get('user_id')
        if not student_id:
            return jsonify({"success": False, "message": "无法获取学生信息"}), 401

        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        code = data.get('code', '').strip()
        language = data.get('language', 'python')
        problem_id = data.get('problem_id')

        if not code:
            return jsonify({"success": False, "message": "代码不能为空"}), 400

        if not problem_id:
            return jsonify({"success": False, "message": "缺少题目ID参数"}), 400

        # 验证题目存在且为编程题
        problem_check_sql = """
            SELECT pq.progressing_questions_id, pq.title
            FROM progressing_questions pq
            WHERE pq.progressing_questions_id = %s
        """
        problem_info = db.execute_query(problem_check_sql, (problem_id,))
        if not problem_info:
            return jsonify({"success": False, "message": "题目不存在或不是编程题"}), 404

        # 获取测试用例
        test_cases_sql = """
            SELECT input, output, is_example
            FROM progressing_questions_test_cases
            WHERE progressing_questions_id = %s
            ORDER BY id
        """
        test_cases = db.execute_query(test_cases_sql, (problem_id,))

        # 执行代码
        execution_result = _execute_code(code, language, test_cases)

        # 记录运行历史
        _record_code_run(student_id, problem_id, code, language, execution_result)

        logger.info(f"学生 {student_id} 运行题目 {problem_id} 代码成功")
        return jsonify({
            "success": True,
            "message": "代码运行完成",
            "data": execution_result
        })

    except Exception as e:
        logger.error(f"学生运行代码失败: {e}")
        return jsonify({"success": False, "message": "运行失败，请重试"}), 500

def _execute_code(code, language, test_cases):
    """执行代码并返回结果"""
    import subprocess
    import tempfile
    import os
    import time

    start_time = time.time()
    result = {
        "status": "success",
        "execution_time": 0,
        "output": "",
        "error": "",
        "test_results": []
    }

    try:
        if language == 'python':
            # Python代码执行
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                # 如果有测试用例，使用测试用例执行
                if test_cases:
                    all_passed = True
                    for i, test_case in enumerate(test_cases):
                        test_result = {
                            "input": test_case['input'],
                            "expected_output": test_case['output'],
                            "actual_output": "",
                            "passed": False,
                            "error": ""
                        }

                        try:
                            # 创建临时输入文件
                            with tempfile.NamedTemporaryFile(mode='w', delete=False) as input_file:
                                input_file.write(test_case['input'] or "")
                                input_file_path = input_file.name

                            # 执行Python代码
                            process = subprocess.run(
                                ['python', temp_file],
                                input=test_case['input'] or "",
                                text=True,
                                capture_output=True,
                                timeout=10  # 10秒超时
                            )

                            test_result["actual_output"] = process.stdout.strip()
                            test_result["error"] = process.stderr.strip()

                            # 比较输出
                            expected = test_case['output'].strip() if test_case['output'] else ""
                            actual = process.stdout.strip()

                            if process.returncode == 0 and actual == expected:
                                test_result["passed"] = True
                            else:
                                all_passed = False

                        except subprocess.TimeoutExpired:
                            test_result["error"] = "执行超时"
                            all_passed = False
                        except Exception as e:
                            test_result["error"] = str(e)
                            all_passed = False
                        finally:
                            # 清理临时输入文件
                            if 'input_file_path' in locals():
                                try:
                                    os.unlink(input_file_path)
                                except:
                                    pass

                        result["test_results"].append(test_result)

                    result["status"] = "success" if all_passed else "partial"
                else:
                    # 没有测试用例，直接执行
                    process = subprocess.run(
                        ['python', temp_file],
                        text=True,
                        capture_output=True,
                        timeout=10
                    )

                    if process.returncode == 0:
                        result["output"] = process.stdout
                    else:
                        result["error"] = process.stderr or "执行失败"

            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass

        elif language == 'cpp':
            # C++代码执行
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
                f.write(code)
                temp_file = f.name

            executable_file = temp_file.replace('.cpp', '')

            try:
                # 编译C++代码 - 使用配置中的GPP路径
                from flask import current_app
                gpp_path = current_app.config.get('GPP_PATH', 'g++')

                compile_process = subprocess.run(
                    [gpp_path, temp_file, '-o', executable_file],
                    text=True,
                    capture_output=True,
                    timeout=10
                )

                if compile_process.returncode != 0:
                    result["status"] = "error"
                    # 处理不同的编译错误类型
                    stderr = compile_process.stderr.strip()
                    if not stderr:
                        stderr = "编译失败，可能是语法错误或头文件缺失"

                    result["error"] = stderr

                    # 添加编译错误特殊处理
                    if "g++: command not found" in stderr or "系统找不到指定的文件" in stderr:
                        result["error"] = f"编译器未找到: {stderr}\n\n💡 解决方案:\n1. 设置环境变量GPP_PATH指向g++.exe的完整路径\n2. 或者安装GCC编译器到标准位置\n3. 或者使用Python语言代替C++"
                    elif "undefined reference" in stderr:
                        result["error"] = f"链接错误: {stderr}\n\n💡 调试建议:\n• 检查是否包含了所有必要的头文件\n• 确认函数名称和参数是否正确"
                    elif "expected" in stderr or "syntax error" in stderr.lower():
                        result["error"] = f"语法错误: {stderr}\n\n💡 调试建议:\n• 检查语法格式是否正确\n• 确认分号、括号是否匹配\n• 查看变量声明是否完整"
                    elif "cannot open include file" in stderr.lower():
                        result["error"] = f"头文件错误: {stderr}\n\n💡 调试建议:\n• 检查include语句的拼写\n• 确认系统已安装标准库"
                    else:
                        result["error"] = f"编译错误: {stderr}"
                else:
                    # 如果有测试用例，使用测试用例执行
                    if test_cases:
                        all_passed = True
                        for i, test_case in enumerate(test_cases):
                            test_result = {
                                "input": test_case['input'],
                                "expected_output": test_case['output'],
                                "actual_output": "",
                                "passed": False,
                                "error": ""
                            }

                            try:
                                # 执行编译后的程序
                                process = subprocess.run(
                                    [executable_file],
                                    input=test_case['input'] or "",
                                    text=True,
                                    capture_output=True,
                                    timeout=10
                                )

                                test_result["actual_output"] = process.stdout.strip()
                                test_result["error"] = process.stderr.strip()

                                # 比较输出
                                expected = test_case['output'].strip() if test_case['output'] else ""
                                actual = process.stdout.strip()

                                if process.returncode == 0 and actual == expected:
                                    test_result["passed"] = True
                                else:
                                    all_passed = False

                            except subprocess.TimeoutExpired:
                                test_result["error"] = "执行超时"
                                all_passed = False
                            except Exception as e:
                                test_result["error"] = str(e)
                                all_passed = False

                            result["test_results"].append(test_result)

                        result["status"] = "success" if all_passed else "partial"
                    else:
                        # 没有测试用例，直接执行
                        process = subprocess.run(
                            [executable_file],
                            text=True,
                            capture_output=True,
                            timeout=10
                        )

                        if process.returncode == 0:
                            result["output"] = process.stdout
                        else:
                            result["error"] = process.stderr or "执行失败"

            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                    if os.path.exists(executable_file):
                        os.unlink(executable_file)
                except:
                    pass

        elif language == 'java':
            # Java代码执行
            # 提取类名（从类定义中提取）
            class_name = None
            class_pattern = r'public\s+class\s+(\w+)'
            match = re.search(class_pattern, code)
            if match:
                class_name = match.group(1)
            else:
                result["status"] = "error"
                result["error"] = "无法识别Java类名，请确保代码包含 public class ClassName"
                # 为编译错误创建空的测试结果
                if test_cases:
                    result["test_results"] = []
                    for test_case in test_cases:
                        result["test_results"].append({
                            "input": test_case['input'],
                            "expected_output": test_case['output'],
                            "actual_output": "",
                            "passed": False,
                            "error": result["error"]
                        })
                return result

            # 创建以类名为基础的临时文件
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"{class_name}.java")

            # 移除BOM字符以避免编译错误
            if code.startswith('\ufeff'):
                code = code[1:]
                logger.info(f"检测并移除了Java代码的BOM字符")

            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)

            # 编译Java文件
            class_file = temp_file.replace('.java', '.class')

            # 编译Java代码
            compile_process = subprocess.run(
                ['javac', temp_file],
                text=True,
                capture_output=True,
                timeout=10
            )

            if compile_process.returncode != 0:
                result["status"] = "error"
                # 优化编译错误信息
                stderr = compile_process.stderr.strip()
                if not stderr:
                    stderr = "编译失败，可能是语法错误或头文件缺失"

                # 处理不同的编译错误类型
                if "g++: command not found" in stderr or "系统找不到指定的文件" in stderr:
                    result["error"] = f"编译器未找到\n解决方法:\n1. 检查JAVA_HOME环境变量设置\n2. 确认javac命令是否在PATH路径中\n3. 或者使用其他编程语言测试"
                elif "expected" in stderr or "syntax error" in stderr.lower() or ";" in stderr.lower():
                    result["error"] = f"语法错误\n调试建议:\n• 检查分号是否完整\n• 确认括号是否匹配\n• 验证变量名称是否正确\n\n错误详情:\n{stderr}"
                elif "cannot find symbol" in stderr.lower():
                    result["error"] = f"符号未找到\n调试建议:\n• 检查变量是否已声明\n• 确认方法名是否正确\n• 验证导入的包是否存在\n\n错误详情:\n{stderr}"
                elif "class" in stderr.lower() and "is public" in stderr.lower():
                    result["error"] = f"类名错误\n调试建议:\n• 确保类的声明为public class ClassName格式\n• 检查类名是否与文件名匹配\n\n错误详情:\n{stderr}"
                else:
                    result["error"] = f"编译错误\n{stderr}"

                # 为编译错误创建测试结果，显示哪些测试用例无法执行
                if test_cases:
                    result["test_results"] = []
                    for i, test_case in enumerate(test_cases):
                        result["test_results"].append({
                            "input": test_case['input'],
                            "expected_output": test_case['output'],
                            "actual_output": "",
                            "passed": False,
                            "error": "编译失败，无法执行测试用例"
                        })
                return result

            # 如果有测试用例，使用测试用例执行
            if test_cases:
                all_passed = True
                failed_tests_count = 0
                for i, test_case in enumerate(test_cases):
                    test_result = {
                        "input": test_case['input'],
                        "expected_output": test_case['output'],
                        "actual_output": "",
                        "passed": False,
                        "error": "",
                        "test_case_index": i + 1
                    }

                    try:
                        # 执行Java程序
                        process = subprocess.run(
                            ['java', '-cp', os.path.dirname(temp_file), class_name],
                            input=test_case['input'] or "",
                            text=True,
                            capture_output=True,
                            timeout=10
                        )

                        test_result["actual_output"] = process.stdout.strip()
                        stderr_output = process.stderr.strip()

                        # 比较输出
                        expected = test_case['output'].strip() if test_case['output'] else ""
                        actual = process.stdout.strip()

                        if process.returncode == 0 and actual == expected:
                            test_result["passed"] = True
                        else:
                            all_passed = False
                            failed_tests_count += 1

                            # 增强错误信息
                            if process.returncode != 0:
                                if stderr_output:
                                    test_result["error"] = f"运行时错误: {stderr_output}"
                                else:
                                    test_result["error"] = "程序执行失败，返回码非零"
                            elif actual != expected:
                                test_result["error"] = "输出结果不匹配"
                                # 显示具体的差异
                                if len(actual) > 100 or len(expected) > 100:
                                    test_result["error"] += f"\n实际输出长度: {len(actual)} 字符\n期望输出长度: {len(expected)} 字符"
                                else:
                                    # 突出显示差异的建议
                                    test_result["error"] += "\n可能原因: 多余/缺少的空格、空行或换行符"

                    except subprocess.TimeoutExpired:
                        test_result["error"] = "执行超时 (可能存在死循环或性能问题)"
                        test_result["actual_output"] = "执行超时"
                        all_passed = False
                        failed_tests_count += 1
                    except Exception as e:
                        test_result["error"] = f"执行异常: {str(e)}"
                        all_passed = False
                        failed_tests_count += 1

                    result["test_results"].append(test_result)

                result["status"] = "success" if all_passed else ("error" if failed_tests_count == len(test_cases) else "partial")

                # 添加失败测试用例的汇总信息
                if not all_passed:
                    result["error"] = f"部分测试用例失败 ({failed_tests_count}/{len(test_cases)} 个失败)\n请查看下方详细的测试用例结果"
            else:
                # 没有测试用例，直接执行
                process = subprocess.run(
                    ['java', '-cp', os.path.dirname(temp_file), class_name],
                    text=True,
                    capture_output=True,
                    timeout=10
                )

                if process.returncode == 0:
                    result["output"] = process.stdout
                else:
                    result["error"] = process.stderr or "执行失败"
                    result["status"] = "error"

            # 清理临时文件
            try:
                os.unlink(temp_file)
                if os.path.exists(class_file):
                    os.unlink(class_file)
            except:
                pass
        else:
            result["status"] = "error"
            result["error"] = f"不支持的编程语言: {language}"

    except subprocess.TimeoutExpired:
        result["status"] = "error"
        result["error"] = "代码执行超时"
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"执行错误: {str(e)}"

    # 计算执行时间
    result["execution_time"] = int((time.time() - start_time) * 1000)  # 毫秒

    return result

def _record_code_run(student_id, problem_id, code, language, result):
    """记录代码运行历史"""
    try:
        sql = """
            INSERT INTO code_runs
            (student_id, problem_id, code, language, status, execution_time, output, error, run_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        db.execute_update(sql, (
            student_id,
            problem_id,
            code,
            language,
            result.get('status', 'unknown'),
            result.get('execution_time', 0),
            result.get('output', ''),
            result.get('error', '')
        ))
    except Exception as e:
        logger.error(f"记录代码运行历史失败: {e}")
        # 不影响主流程

def _extract_zip_file(zip_file_path, extract_to):
    """解压zip文件到指定目录"""
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return True, "解压成功"
    except zipfile.BadZipFile:
        return False, "无效的zip文件格式"
    except Exception as e:
        return False, f"解压失败: {str(e)}"

def _find_code_files(extract_path, language):
    """在解压目录中查找代码文件"""
    code_files = []

    # 定义不同语言的文件扩展名映射
    language_extensions = {
        'python': ['.py', '.PY'],
        'cpp': ['.cpp', '.cc', '.cxx', '.c++', '.CPP', '.CC'],
        'java': ['.java', '.JAVA']
    }

    try:
        # 遍历所有文件
        for root, dirs, files in os.walk(extract_path):
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)

                # 检查文件扩展名是否匹配
                if ext in language_extensions.get(language, []):
                    # 获取文件的相对路径（相对于解压根目录）
                    relative_path = os.path.relpath(file_path, extract_path)
                    code_files.append({
                        'path': file_path,
                        'relative_path': relative_path,
                        'filename': file,
                        'extension': ext
                    })

        return code_files
    except Exception as e:
        logger.error(f"查找代码文件失败: {e}")
        return []

def _validate_code_files(code_files, language):
    """验证找到的代码文件"""
    if not code_files:
        return False, "未找到任何代码文件"

    if language == 'java':
        # Java必须有且只有一个类文件作为主入口
        main_classes = []
        for file_info in code_files:
            try:
                with open(file_info['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 查找public class声明
                    import re
                    match = re.search(r'public\s+class\s+(\w+)', content)
                    if match:
                        class_name = match.group(1)
                        # 验证类名是否与文件名匹配
                        expected_filename = f"{class_name}.java"
                        if file_info['filename'] != expected_filename:
                            return False, f"Java类名 {class_name} 与文件名 {file_info['filename']} 不匹配"
                        main_classes.append(file_info)
            except Exception as e:
                return False, f"读取文件 {file_info['filename']} 失败: {str(e)}"

        if len(main_classes) != 1:
            return False, f"Java项目应有且只有一个public主类，找到 {len(main_classes)} 个"

    return True, "代码文件验证通过"

def _load_code_from_files(code_files, language):
    """从代码文件中读取代码内容"""
    try:
        if language == 'java':
            # Java只读取主类文件
            for file_info in code_files:
                with open(file_info['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                # 查找是否包含main方法，一定要是主类才读取
                if 'public static void main' in content or 'void main(' in content:
                    return content
            return ""

        elif language in ['python', 'cpp']:
            # Python和C++可以有多个文件，这里读取第一个文件
            # 实际项目中可能需要更复杂的处理，如处理多个文件
            if code_files:
                with open(code_files[0]['path'], 'r', encoding='utf-8') as f:
                    return f.read()

        return ""
    except Exception as e:
        logger.error(f"读取代码文件失败: {e}")
        return ""

def _execute_zip_code(zip_file_path, language, problem_id):
    """从ZIP文件中提取代码并执行，返回执行结果"""

    # 结果模板
    result = {
        "status": "error",
        "execution_time": 0,
        "output": "",
        "error": "",
        "test_results": [],
        "extracted_code": "",
        "files_found": [],
        "validation_message": ""
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. 解压zip文件
            extract_path = os.path.join(temp_dir, 'extracted')
            os.makedirs(extract_path)
            success, message = _extract_zip_file(zip_file_path, extract_path)

            if not success:
                result["error"] = message
                return result

            # 2. 查找代码文件
            code_files = _find_code_files(extract_path, language)
            result["files_found"] = [
                {
                    "filename": f["filename"],
                    "path": f["relative_path"],
                    "extension": f["extension"]
                }
                for f in code_files
            ]

            # 3. 验证代码文件
            valid, message = _validate_code_files(code_files, language)
            result["validation_message"] = message

            if not valid:
                result["error"] = message
                result["status"] = "error"
                return result

            # 4. 读取代码内容
            code_content = _load_code_from_files(code_files, language)
            if not code_content:
                result["error"] = "无法读取代码内容"
                return result

            result["extracted_code"] = code_content

            # 5. 获取测试用例并执行代码
            test_cases_sql = """
                SELECT input, output, is_example
                FROM progressing_questions_test_cases
                WHERE progressing_questions_id = %s
                ORDER BY id
            """
            test_cases = db.execute_query(test_cases_sql, (problem_id,))

            # 6. 使用现有的代码执行引擎运行代码
            execution_result = _execute_code(code_content, language, test_cases)

            # 7. 合并结果
            result.update({
                "status": execution_result["status"],
                "execution_time": execution_result["execution_time"],
                "output": execution_result.get("output", ""),
                "error": execution_result.get("error", ""),
                "test_results": execution_result.get("test_results", [])
            })

            return result

        except Exception as e:
            logger.error(f"执行ZIP代码失败: {e}")
            result["error"] = f"执行失败: {str(e)}"
            return result

def _evaluate_zip_submission(zip_file, language, problem_id):
    """评估zip文件提交的编程题答案（用于兼容性）"""
    execution_result = _execute_zip_code(zip_file, language, problem_id)
    is_correct = execution_result["status"] in ["success", "partial"]
    return is_correct, "代码评测完成"
