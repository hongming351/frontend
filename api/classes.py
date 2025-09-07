from flask import Blueprint, jsonify, request, session
from database import db
import logging

logger = logging.getLogger(__name__)
classes_bp = Blueprint('classes', __name__)

@classes_bp.route('/api/classes', methods=['GET'])
def get_classes():
    """获取所有班级列表"""
    try:
        sql = """
            SELECT c.class_id as id, c.class_name, c.description, c.created_at, c.updated_at,
                   co.course_name as course_name, co.language as course_language,
                   t.username as teacher_name, t.teacher_id as teacher_id
            FROM classes c
            JOIN courses co ON c.course_id = co.course_id
            JOIN teachers t ON c.teacher_id = t.teacher_id
            ORDER BY co.course_name, c.class_name
        """
        classes = db.execute_query(sql)
        return jsonify({"success": True, "data": classes})
    except Exception as e:
        logger.error(f"获取班级列表失败: {e}")
        return jsonify({"success": False, "message": "获取班级列表失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>', methods=['GET'])
def get_class(class_id):
    """获取单个班级信息"""
    try:
        sql = """
            SELECT c.class_id as id, c.class_name, c.description, c.course_id, c.teacher_id,
                   c.created_at, c.updated_at,
                   co.course_name as course_name, co.language as course_language,
                   t.username as teacher_name
            FROM classes c
            JOIN courses co ON c.course_id = co.course_id
            JOIN teachers t ON c.teacher_id = t.teacher_id
            WHERE c.class_id = %s
        """
        class_info = db.execute_query(sql, (class_id,))
        
        if class_info:
            return jsonify({"success": True, "data": class_info[0]})
        return jsonify({"success": False, "message": "班级不存在"}), 404
    except Exception as e:
        logger.error(f"获取班级信息失败: {e}")
        return jsonify({"success": False, "message": "获取班级信息失败"}), 500

@classes_bp.route('/api/classes', methods=['POST'])
def create_class():
    """创建新班级"""
    try:
        # 检查教师或管理员权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False, 
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无请求数据"}), 400
            
        required_fields = ['class_name', 'course_id']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要字段"}), 400
        
        # 如果是教师，只能为自己创建班级
        teacher_id = session['user_id']
        if session['identity'] == 'teacher':
            # 检查教师是否有权限教授该课程
            check_course_sql = """
                SELECT COUNT(*) as count FROM teacher_courses 
                WHERE teacher_id = %s AND course_id = %s
            """
            can_teach = db.execute_query(check_course_sql, (teacher_id, data['course_id']))[0]['count']
            
            if not can_teach:
                return jsonify({
                    "success": False, 
                    "message": "您没有权限教授该课程"
                }), 403
        else:
            # 管理员可以指定任何教师
            if 'teacher_id' not in data:
                return jsonify({"success": False, "message": "缺少教师ID"}), 400
            teacher_id = data['teacher_id']

        sql = """
            INSERT INTO classes (class_name, description, course_id, teacher_id)
            VALUES (%s, %s, %s, %s)
        """
        params = (
            data['class_name'],
            data.get('description', ''),
            data['course_id'],
            teacher_id
        )
        
        affected = db.execute_update(sql, params)
        
        if affected > 0:
            # 获取最后插入的ID
            last_id_sql = "SELECT LAST_INSERT_ID() as class_id"
            try:
                last_id_result = db.execute_query(last_id_sql)
                if last_id_result and len(last_id_result) > 0:
                    class_id = last_id_result[0]['class_id']
                    
                    # 获取新创建的班级
                    get_sql = """
                        SELECT c.*, co.course_name as course_name, t.username as teacher_name
                        FROM classes c
                        JOIN courses co ON c.course_id = co.course_id
                        JOIN teachers t ON c.teacher_id = t.teacher_id
                        WHERE c.class_id = %s
                    """
                    new_class = db.execute_query(get_sql, (class_id,))[0]
                    
                    logger.info(f"班级创建成功: {data['class_name']}")
                    return jsonify({
                        "success": True, 
                        "message": "班级创建成功",
                        "data": new_class
                    }), 201
            except Exception as e:
                logger.error(f"获取新创建班级信息失败: {e}")
                # 即使获取详细信息失败，也返回成功，因为班级已经创建成功
                return jsonify({
                    "success": True, 
                    "message": "班级创建成功",
                    "data": {
                        "class_id": class_id,
                        "class_name": data['class_name'],
                        "description": data.get('description', ''),
                        "course_id": data['course_id'],
                        "teacher_id": teacher_id
                    }
                }), 201
        
        return jsonify({"success": False, "message": "班级创建失败"}), 400
    except Exception as e:
        logger.error(f"创建班级失败: {e}")
        return jsonify({"success": False, "message": "创建班级失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>', methods=['PUT'])
def update_class(class_id):
    """更新班级信息"""
    try:
        # 检查教师或管理员权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False, 
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无更新数据"}), 400
        
        # 检查班级是否存在且用户有权限
        check_sql = """
            SELECT c.* FROM classes c
            WHERE c.class_id = %s
        """
        class_info = db.execute_query(check_sql, (class_id,))
        
        if not class_info:
            return jsonify({"success": False, "message": "班级不存在"}), 404
        
        # 如果是教师，只能更新自己创建的班级
        if session['identity'] == 'teacher':
            if class_info[0]['teacher_id'] != session['user_id']:
                return jsonify({
                    "success": False, 
                    "message": "只能更新自己创建的班级"
                }), 403
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        allowed_fields = ['class_name', 'description']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                update_values.append(data[field])
        
        if not update_fields:
            return jsonify({"success": False, "message": "没有有效的更新字段"}), 400
        
        # 添加班级ID到参数列表
        update_values.append(class_id)
        
        sql = f"UPDATE classes SET {', '.join(update_fields)} WHERE class_id = %s"
        affected = db.execute_update(sql, update_values)
        
        if affected > 0:
            logger.info(f"班级 {class_id} 更新成功")
            return jsonify({"success": True, "message": "班级更新成功"})
        
        return jsonify({"success": False, "message": "班级不存在或未更改"}), 404
    except Exception as e:
        logger.error(f"更新班级失败: {e}")
        return jsonify({"success": False, "message": "更新班级失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>', methods=['DELETE'])
def delete_class(class_id):
    """删除班级"""
    try:
        # 检查教师或管理员权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False, 
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        # 检查班级是否存在且用户有权限
        check_sql = "SELECT * FROM classes WHERE class_id = %s"
        class_info = db.execute_query(check_sql, (class_id,))
        
        if not class_info:
            return jsonify({"success": False, "message": "班级不存在"}), 404
        
        # 如果是教师，只能删除自己创建的班级
        if session['identity'] == 'teacher':
            if class_info[0]['teacher_id'] != session['user_id']:
                return jsonify({
                    "success": False, 
                    "message": "只能删除自己创建的班级"
                }), 403
        
        # 检查班级是否有关联的学生
        check_students_sql = "SELECT COUNT(*) as count FROM student_classes WHERE class_id = %s"
        student_count = db.execute_query(check_students_sql, (class_id,))[0]['count']
        
        if student_count > 0:
            return jsonify({
                "success": False, 
                "message": "无法删除班级，该班级下有关联的学生"
            }), 400

        sql = "DELETE FROM classes WHERE class_id = %s"
        affected = db.execute_update(sql, (class_id,))
        
        if affected > 0:
            logger.info(f"班级 {class_id} 删除成功")
            return jsonify({"success": True, "message": "班级删除成功"})
        
        return jsonify({"success": False, "message": "班级不存在"}), 404
    except Exception as e:
        logger.error(f"删除班级失败: {e}")
        return jsonify({"success": False, "message": "删除班级失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>/students', methods=['GET'])
def get_class_students(class_id):
    """获取班级的所有学生"""
    try:
        sql = """
            SELECT s.student_id as id, s.username, s.email, s.telenum, s.student_id,
                   sc.joined_at as enrolled_at, s.status
            FROM student_classes sc
            JOIN students s ON sc.student_id = s.student_id
            WHERE sc.class_id = %s
            ORDER BY s.username
        """
        students = db.execute_query(sql, (class_id,))
        return jsonify({"success": True, "data": students})
    except Exception as e:
        logger.error(f"获取班级学生失败: {e}")
        return jsonify({"success": False, "message": "获取班级学生失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>/enroll', methods=['POST'])
def enroll_student(class_id):
    """学生加入班级"""
    try:
        # 检查学生权限
        if 'identity' not in session or session['identity'] != 'student':
            return jsonify({
                "success": False, 
                "message": "需要学生权限",
                "redirect": "/login"
            }), 401

        student_id = session['user_id']
        
        # 检查学生是否已经加入该班级
        check_sql = "SELECT COUNT(*) as count FROM student_classes WHERE class_id = %s AND student_id = %s"
        already_enrolled = db.execute_query(check_sql, (class_id, student_id))[0]['count']
        
        if already_enrolled:
            return jsonify({
                "success": False, 
                "message": "您已经加入该班级"
            }), 400

        sql = "INSERT INTO student_classes (class_id, student_id) VALUES (%s, %s)"
        affected = db.execute_update(sql, (class_id, student_id))
        
        if affected > 0:
            logger.info(f"学生 {student_id} 加入班级 {class_id} 成功")
            return jsonify({
                "success": True, 
                "message": "加入班级成功"
            }), 201
        
        return jsonify({"success": False, "message": "加入班级失败"}), 400
    except Exception as e:
        logger.error(f"加入班级失败: {e}")
        return jsonify({"success": False, "message": "加入班级失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>/enroll/<int:student_id>', methods=['DELETE'])
def remove_student_from_class(class_id, student_id):
    """从班级中移除学生"""
    try:
        # 检查教师或管理员权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False, 
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        # 检查教师是否有权限管理该班级
        if session['identity'] == 'teacher':
            check_class_sql = "SELECT teacher_id FROM classes WHERE class_id = %s"
            class_info = db.execute_query(check_class_sql, (class_id,))
            
            if not class_info or class_info[0]['teacher_id'] != session['user_id']:
                return jsonify({
                    "success": False, 
                    "message": "只能管理自己创建的班级"
                }), 403

        sql = "DELETE FROM student_classes WHERE class_id = %s AND student_id = %s"
        affected = db.execute_update(sql, (class_id, student_id))
        
        if affected > 0:
            logger.info(f"学生 {student_id} 从班级 {class_id} 移除成功")
            return jsonify({"success": True, "message": "学生移除成功"})
        
        return jsonify({"success": False, "message": "学生不在该班级中"}), 404
    except Exception as e:
        logger.error(f"移除学生失败: {e}")
        return jsonify({"success": False, "message": "移除学生失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>/student-count', methods=['GET'])
def get_class_student_count(class_id):
    """获取班级的学生人数"""
    try:
        # 检查班级是否存在
        check_class_sql = "SELECT COUNT(*) as count FROM classes WHERE class_id = %s"
        class_exists = db.execute_query(check_class_sql, (class_id,))[0]['count']
        
        if not class_exists:
            return jsonify({"success": False, "message": "班级不存在"}), 404
        
        # 统计班级中的学生数量
        count_sql = "SELECT COUNT(*) as student_count FROM student_classes WHERE class_id = %s"
        student_count = db.execute_query(count_sql, (class_id,))[0]['student_count']
        
        return jsonify({
            "success": True, 
            "data": {
                "student_count": student_count
            }
        })
    except Exception as e:
        logger.error(f"获取班级学生人数失败: {e}")
        return jsonify({"success": False, "message": "获取班级学生人数失败"}), 500

@classes_bp.route('/api/classes/<int:class_id>/enroll-students', methods=['POST'])
def enroll_students_to_class(class_id):
    """批量添加学生到班级"""
    try:
        # 检查教师或管理员权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False,
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        # 检查教师是否有权限管理该班级
        if session['identity'] == 'teacher':
            check_class_sql = "SELECT teacher_id, course_id FROM classes WHERE class_id = %s"
            class_info = db.execute_query(check_class_sql, (class_id,))

            if not class_info or class_info[0]['teacher_id'] != session['user_id']:
                return jsonify({
                    "success": False,
                    "message": "只能管理自己创建的班级"
                }), 403

        data = request.get_json()
        if not data or 'student_ids' not in data:
            return jsonify({"success": False, "message": "缺少学生ID列表"}), 400

        student_ids = data['student_ids']
        if not isinstance(student_ids, list) or len(student_ids) == 0:
            return jsonify({"success": False, "message": "学生ID列表无效"}), 400

        # 检查学生是否已经在其他班级中（一个学生只能加入一个课程的一个班级）
        check_duplicate_sql = """
            SELECT sc.student_id, c.class_name, co.course_name
            FROM student_classes sc
            JOIN classes c ON sc.class_id = c.class_id
            JOIN courses co ON c.course_id = co.course_id
            WHERE sc.student_id IN %s
            AND c.class_id != %s
            AND c.course_id = (SELECT course_id FROM classes WHERE class_id = %s)
        """
        existing_enrollments = db.execute_query(check_duplicate_sql, (student_ids, class_id, class_id))

        if existing_enrollments:
            duplicate_students = [f"{e['student_id']}（已在班级 {e['class_name']}）" for e in existing_enrollments]
            return jsonify({
                "success": False,
                "message": f"以下学生已经在该课程的其他班级中: {', '.join(duplicate_students)}"
            }), 400

        # 检查学生是否已经在该班级中
        check_existing_sql = "SELECT student_id FROM student_classes WHERE class_id = %s AND student_id IN %s"
        existing_students = db.execute_query(check_existing_sql, (class_id, student_ids))

        existing_student_ids = [s['student_id'] for s in existing_students]
        new_student_ids = [sid for sid in student_ids if sid not in existing_student_ids]

        if not new_student_ids:
            return jsonify({
                "success": False,
                "message": "所有学生都已经在该班级中"
            }), 400

        # 批量插入学生到班级
        enroll_sql = "INSERT INTO student_classes (class_id, student_id) VALUES (%s, %s)"
        enroll_params = [(class_id, student_id) for student_id in new_student_ids]

        affected = db.execute_many_update(enroll_sql, enroll_params)

        if affected > 0:
            logger.info(f"成功添加 {affected} 名学生到班级 {class_id}")
            return jsonify({
                "success": True,
                "message": f"成功添加 {affected} 名学生到班级",
                "data": {
                    "added_count": affected,
                    "already_enrolled_count": len(existing_student_ids)
                }
            }), 201

        return jsonify({"success": False, "message": "添加学生失败"}), 400
    except Exception as e:
        logger.error(f"批量添加学生失败: {e}")
        return jsonify({"success": False, "message": "批量添加学生失败"}), 500

@classes_bp.route('/api/classes/batch-import-students', methods=['POST'])
def batch_import_students_to_class():
    """批量导入学生到班级（通过CSV文件）"""
    try:
        # 检查教师或管理员权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False,
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        # 获取表单数据
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "未找到上传文件"}), 400

        file = request.files['file']
        class_id = request.form.get('class_id')

        if not file or not class_id:
            return jsonify({"success": False, "message": "文件或班级ID缺失"}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({"success": False, "message": "只支持CSV文件"}), 400

        # 检查班级是否存在且教师有权限
        if session['identity'] == 'teacher':
            check_class_sql = "SELECT teacher_id, course_id FROM classes WHERE class_id = %s"
            class_info = db.execute_query(check_class_sql, (class_id,))

            if not class_info or class_info[0]['teacher_id'] != session['user_id']:
                return jsonify({
                    "success": False,
                    "message": "只能管理自己创建的班级"
                }), 403

        # 读取CSV文件内容
        try:
            import csv
            import io

            # 读取文件内容
            file_content = file.read().decode('utf-8-sig')  # 使用utf-8-sig处理BOM
            csv_reader = csv.DictReader(io.StringIO(file_content))

            # 验证CSV格式
            required_columns = {'用户名', '学号', '邮箱', '手机号'}
            if not required_columns.issubset(set(csv_reader.fieldnames or [])):
                return jsonify({
                    "success": False,
                    "message": f"CSV文件缺少必要列: {', '.join(required_columns - set(csv_reader.fieldnames or []))}"
                }), 400

            # 解析学生数据
            students_data = []
            for row_num, row in enumerate(csv_reader, start=2):  # 从第2行开始（第1行是表头）
                # 验证必填字段
                if not all(row.get(col) for col in required_columns):
                    return jsonify({
                        "success": False,
                        "message": f"第{row_num}行数据不完整，所有字段都不能为空"
                    }), 400

                students_data.append({
                    'username': row['用户名'].strip(),
                    'student_id': row['学号'].strip(),
                    'email': row['邮箱'].strip(),
                    'telenum': row['手机号'].strip(),
                    'row_num': row_num
                })

            if len(students_data) == 0:
                return jsonify({"success": False, "message": "CSV文件中没有有效的学生数据"}), 400

            if len(students_data) > 100:
                return jsonify({"success": False, "message": "单次最多支持导入100名学生"}), 400

        except UnicodeDecodeError:
            return jsonify({"success": False, "message": "文件编码错误，请使用UTF-8编码保存CSV文件"}), 400
        except Exception as e:
            logger.error(f"解析CSV文件失败: {e}")
            return jsonify({"success": False, "message": "CSV文件格式错误"}), 400

        # 处理导入逻辑
        success_students = []
        error_messages = []
        success_count = 0
        error_count = 0

        for student_data in students_data:
            try:
                # 根据用户名、学号、邮箱查找学生
                find_student_sql = """
                    SELECT student_id, username, email, telenum, student_id as student_number
                    FROM students
                    WHERE (username = %s OR student_id = %s OR email = %s)
                    AND status = 'active'
                """
                student_info = db.execute_query(find_student_sql, (
                    student_data['username'],
                    student_data['student_id'],
                    student_data['email']
                ))

                if not student_info:
                    error_messages.append(f"第{student_data['row_num']}行：找不到学生 {student_data['username']}（用户名、学号或邮箱）")
                    error_count += 1
                    continue

                student = student_info[0]
                student_id = student['student_id']

                # 检查学生是否已经在该班级中
                check_enrollment_sql = """
                    SELECT COUNT(*) as count FROM student_classes
                    WHERE class_id = %s AND student_id = %s
                """
                already_enrolled = db.execute_query(check_enrollment_sql, (class_id, student_id))[0]['count']

                if already_enrolled:
                    error_messages.append(f"第{student_data['row_num']}行：学生 {student_data['username']} 已经在该班级中")
                    error_count += 1
                    continue

                # 检查学生是否已经在该课程的其他班级中
                check_other_classes_sql = """
                    SELECT c.class_name, co.course_name
                    FROM student_classes sc
                    JOIN classes c ON sc.class_id = c.class_id
                    JOIN courses co ON c.course_id = co.course_id
                    WHERE sc.student_id = %s AND c.class_id != %s
                    AND c.course_id = (SELECT course_id FROM classes WHERE class_id = %s)
                """
                other_enrollments = db.execute_query(check_other_classes_sql, (student_id, class_id, class_id))

                if other_enrollments:
                    other_class = other_enrollments[0]
                    error_messages.append(f"第{student_data['row_num']}行：学生 {student_data['username']} 已经在该课程的其他班级 {other_class['class_name']} 中")
                    error_count += 1
                    continue

                # 添加学生到班级
                enroll_sql = "INSERT INTO student_classes (class_id, student_id) VALUES (%s, %s)"
                affected = db.execute_update(enroll_sql, (class_id, student_id))

                if affected > 0:
                    success_students.append({
                        'username': student['username'],
                        'student_id': student['student_number'] or student['student_id'],
                        'email': student['email'],
                        'telenum': student['telenum']
                    })
                    success_count += 1
                    logger.info(f"学生 {student_id} 成功导入到班级 {class_id}")
                else:
                    error_messages.append(f"第{student_data['row_num']}行：学生 {student_data['username']} 导入失败")
                    error_count += 1

            except Exception as e:
                logger.error(f"处理学生 {student_data['username']} 失败: {e}")
                error_messages.append(f"第{student_data['row_num']}行：学生 {student_data['username']} 处理失败 - {str(e)}")
                error_count += 1

        # 返回结果
        result_data = {
            'success_count': success_count,
            'error_count': error_count,
            'success_students': success_students,
            'error_messages': error_messages
        }

        if success_count > 0:
            message = f"成功导入 {success_count} 名学生"
            if error_count > 0:
                message += f"，{error_count} 名学生导入失败"
        else:
            message = f"导入失败：{error_count} 个学生数据有误"

        logger.info(f"批量导入完成: {message}")

        return jsonify({
            "success": success_count > 0,
            "message": message,
            "data": result_data
        })

    except Exception as e:
        logger.error(f"批量导入学生失败: {e}")
        return jsonify({"success": False, "message": "批量导入学生失败"}), 500

@classes_bp.route('/api/classes/current', methods=['GET'])
def get_current_teacher_classes():
    """获取当前教师创建的所有班级，支持按课程ID过滤"""
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
                SELECT c.class_id as id, c.class_name, c.description, c.created_at, c.updated_at,
                       c.course_id as course_id, co.course_name as course_name, co.language as course_language
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
                       c.course_id as course_id, co.course_name as course_name, co.language as course_language
                FROM classes c
                JOIN courses co ON c.course_id = co.course_id
                WHERE c.teacher_id = %s
                ORDER BY co.course_name, c.class_name
            """
            classes = db.execute_query(sql, (teacher_id,))

        return jsonify({"success": True, "data": classes})
    except Exception as e:
        logger.error(f"获取当前教师班级失败: {e}")
        return jsonify({"success": False, "message": "获取班级列表失败"}), 500
