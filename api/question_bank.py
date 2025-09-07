from flask import Blueprint, jsonify, request, session
from database import db
import logging

logger = logging.getLogger(__name__)
question_bank_bp = Blueprint('question_bank', __name__)

@question_bank_bp.route('/api/question-bank/problems', methods=['GET'])
def get_question_bank_problems():
    """获取题库题目列表（支持筛选）"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '').strip()
        language = request.args.get('language', '').strip()
        difficulty = request.args.get('difficulty', '').strip()
        knowledge_points = request.args.get('knowledge_points', '').strip()
        problem_type = request.args.get('problem_type', '').strip()

        offset = (page - 1) * per_page

        # 构建查询条件
        conditions = []
        params = []

        # 根据题型选择不同的表 (修复：从中文改为英文值，与前端保持一致)
        if problem_type == 'programming':
            base_sql = """
                SELECT
                    'progressing' as question_type,
                    progressing_questions_id as id,
                    title,
                    language,
                    description,
                    difficulty,
                    knowledge_points,
                    created_at
                FROM progressing_questions
                WHERE 1=1
            """
            count_sql = "SELECT COUNT(*) as total FROM progressing_questions WHERE 1=1"

        elif problem_type == 'choice':
            base_sql = """
                SELECT
                    'choice' as question_type,
                    choice_questions_id as id,
                    title,
                    language,
                    description,
                    difficulty,
                    knowledge_points,
                    created_at
                FROM choice_questions
                WHERE 1=1
            """
            count_sql = "SELECT COUNT(*) as total FROM choice_questions WHERE 1=1"

        elif problem_type == 'judgment':
            base_sql = """
                SELECT
                    'judgment' as question_type,
                    judgment_questions_id as id,
                    title,
                    language,
                    description,
                    difficulty,
                    knowledge_points,
                    created_at
                FROM judgment_questions
                WHERE 1=1
            """
            count_sql = "SELECT COUNT(*) as total FROM judgment_questions WHERE 1=1"

        else:
            # 查询所有题型
            base_sql = """
                SELECT * FROM (
                    SELECT
                        'progressing' as question_type,
                        progressing_questions_id as id,
                        title,
                        language,
                        description,
                        difficulty,
                        knowledge_points,
                        created_at
                    FROM progressing_questions
                    UNION ALL
                    SELECT
                        'choice' as question_type,
                        choice_questions_id as id,
                        title,
                        language,
                        description,
                        difficulty,
                        knowledge_points,
                        created_at
                    FROM choice_questions
                    UNION ALL
                    SELECT
                        'judgment' as question_type,
                        judgment_questions_id as id,
                        title,
                        language,
                        description,
                        difficulty,
                        knowledge_points,
                        created_at
                    FROM judgment_questions
                ) AS all_questions WHERE 1=1
            """
            count_sql = """
                SELECT
                    (SELECT COUNT(*) FROM progressing_questions) +
                    (SELECT COUNT(*) FROM choice_questions) +
                    (SELECT COUNT(*) FROM judgment_questions) as total
            """

        # 添加筛选条件 - 统一处理逻辑
        if search:
            search_param = f'%{search}%'
            conditions.append("(title LIKE %s OR description LIKE %s)")
            params.extend([search_param, search_param])

        if language:
            conditions.append("language = %s")
            params.append(language)

        if difficulty:
            conditions.append("difficulty = %s")
            params.append(difficulty)

        if knowledge_points:
            kp_param = f'%{knowledge_points}%'
            conditions.append("knowledge_points LIKE %s")
            params.append(kp_param)

        # 构建完整查询
        where_clause = " AND " + " AND ".join(conditions) if conditions else ""
        final_sql = base_sql + where_clause + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        # 获取总数
        if problem_type and conditions:
            # 如果指定了题型且有筛选条件，需要传递筛选参数
            count_params = params[:-2] if params else []  # 去掉分页参数
            try:
                count_query = count_sql + where_clause
                logger.debug(f"Count SQL: {count_query}, Params: {count_params}")
                total_result = db.execute_query(count_query, count_params)
                logger.debug(f"Count result: {total_result}")
            except Exception as e:
                logger.error(f"Count query failed: {e}, SQL: {count_query}, Params: {count_params}")
                raise e
        elif problem_type and not conditions:
            # 如果指定了题型但没有筛选条件，直接使用基础count_sql
            try:
                logger.debug(f"Count SQL: {count_sql}, Params: []")
                total_result = db.execute_query(count_sql, [])
                logger.debug(f"Count result: {total_result}")
            except Exception as e:
                logger.error(f"Count query failed: {e}, SQL: {count_sql}")
                raise e
        else:
            # 如果没有指定题型，直接使用count_sql
            try:
                logger.debug(f"Count SQL: {count_sql}, Params: []")
                total_result = db.execute_query(count_sql, [])
                logger.debug(f"Count result: {total_result}")
            except Exception as e:
                logger.error(f"Count query failed: {e}, SQL: {count_sql}")
                raise e

        total = total_result[0]['total'] if total_result else 0

        # 获取题目列表
        problems = db.execute_query(final_sql, params)

        return jsonify({
            "success": True,
            "data": problems,
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"获取题库题目失败: {e}")
        return jsonify({"success": False, "message": "获取题库题目失败"}), 500

@question_bank_bp.route('/api/question-bank/problem/<int:problem_id>', methods=['GET'])
def get_problem_detail(problem_id):
    """获取题目详情"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        problem_type = request.args.get('type', '').strip()

        if not problem_type:
            return jsonify({"success": False, "message": "题目类型不能为空"}), 400

        if problem_type == 'progressing':
            # 获取编程题详情
            problem = db.execute_query("""
                SELECT
                    progressing_questions_id as id,
                    'progressing' as question_type,
                    title,
                    language,
                    description,
                    difficulty,
                    knowledge_points,
                    input_description,
                    output_description,
                    solution_idea,
                    reference_code,
                    created_at
                FROM progressing_questions
                WHERE progressing_questions_id = %s
            """, (problem_id,))

            if not problem:
                return jsonify({"success": False, "message": "题目不存在"}), 404

            problem = problem[0]

            # 获取测试用例
            test_cases = db.execute_query("""
                SELECT input, output, is_example
                FROM progressing_questions_test_cases
                WHERE progressing_questions_id = %s
                ORDER BY id
            """, (problem_id,))

            problem['test_cases'] = test_cases

        elif problem_type == 'choice':
            # 获取选择题详情
            problem = db.execute_query("""
                SELECT
                    choice_questions_id as id,
                    'choice' as question_type,
                    title,
                    language,
                    description,
                    difficulty,
                    knowledge_points,
                    options,
                    correct_answer,
                    solution_idea,
                    created_at
                FROM choice_questions
                WHERE choice_questions_id = %s
            """, (problem_id,))

            if not problem:
                return jsonify({"success": False, "message": "题目不存在"}), 404

            problem = problem[0]

        elif problem_type == 'judgment':
            # 获取判断题详情
            problem = db.execute_query("""
                SELECT
                    judgment_questions_id as id,
                    'judgment' as question_type,
                    title,
                    language,
                    description,
                    difficulty,
                    knowledge_points,
                    correct_answer,
                    solution_idea,
                    created_at
                FROM judgment_questions
                WHERE judgment_questions_id = %s
            """, (problem_id,))

            if not problem:
                return jsonify({"success": False, "message": "题目不存在"}), 404

            problem = problem[0]

        else:
            return jsonify({"success": False, "message": "无效的题目类型"}), 400

        return jsonify({
            "success": True,
            "data": problem
        })

    except Exception as e:
        logger.error(f"获取题目详情失败: {e}")
        return jsonify({"success": False, "message": "获取题目详情失败"}), 500


@question_bank_bp.route('/api/question-bank/stats', methods=['GET'])
def get_question_bank_stats():
    """获取题库统计信息"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        # 获取各题型数量
        progressing_count = db.execute_query("SELECT COUNT(*) as count FROM progressing_questions")[0]['count']
        choice_count = db.execute_query("SELECT COUNT(*) as count FROM choice_questions")[0]['count']
        judgment_count = db.execute_query("SELECT COUNT(*) as count FROM judgment_questions")[0]['count']

        # 获取各语言统计
        language_stats = db.execute_query("""
            SELECT language, COUNT(*) as count
            FROM (
                SELECT language FROM progressing_questions WHERE language IS NOT NULL AND language != ''
                UNION ALL
                SELECT language FROM choice_questions WHERE language IS NOT NULL AND language != ''
                UNION ALL
                SELECT language FROM judgment_questions WHERE language IS NOT NULL AND language != ''
            ) AS all_languages
            GROUP BY language
            ORDER BY count DESC
        """)

        # 获取各难度统计
        difficulty_stats = db.execute_query("""
            SELECT difficulty, COUNT(*) as count
            FROM (
                SELECT difficulty FROM progressing_questions WHERE difficulty IS NOT NULL AND difficulty != ''
                UNION ALL
                SELECT difficulty FROM choice_questions WHERE difficulty IS NOT NULL AND difficulty != ''
                UNION ALL
                SELECT difficulty FROM judgment_questions WHERE difficulty IS NOT NULL AND difficulty != ''
            ) AS all_difficulties
            GROUP BY difficulty
            ORDER BY count DESC
        """)

        return jsonify({
            "success": True,
            "data": {
                "total_problems": progressing_count + choice_count + judgment_count,
                "progressing_count": progressing_count,
                "choice_count": choice_count,
                "judgment_count": judgment_count,
                "language_stats": language_stats,
                "difficulty_stats": difficulty_stats
            }
        })

    except Exception as e:
        logger.error(f"获取题库统计失败: {e}")
        return jsonify({"success": False, "message": "获取题库统计失败"}), 500

@question_bank_bp.route('/api/question-bank/problems', methods=['POST'])
def create_problem():
    """创建新题目"""
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

        # 验证基本字段
        required_fields = ['question_type', 'language', 'knowledge_points', 'difficulty', 'title', 'description']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({"success": False, "message": f"字段 '{field}' 不能为空"}), 400

        question_type = data['question_type']
        language = data['language'].strip()
        knowledge_points = data['knowledge_points'].strip()
        difficulty = data['difficulty'].strip()
        title = data['title'].strip()
        description = data['description'].strip()
        solution_idea = data.get('solution_idea', '').strip()

        if question_type == 'programming':
            # 创建编程题
            # 验证编程题特定字段
            input_description = data.get('input_description', '').strip()
            output_description = data.get('output_description', '').strip()
            reference_code = data.get('reference_code', '').strip()
            test_cases = data.get('test_cases', [])

            # 插入编程题
            result = db.execute_query("""
                INSERT INTO progressing_questions
                (title, language, description, difficulty, knowledge_points, input_description, output_description, solution_idea, reference_code, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (title, language, description, difficulty, knowledge_points, input_description, output_description, solution_idea, reference_code))

            # 获取插入的题目ID
            problem_id = db.execute_query("SELECT LAST_INSERT_ID() as id")[0]['id']

            # 插入测试用例
            if test_cases:
                for test_case in test_cases:
                    if test_case.get('input') or test_case.get('output'):
                        db.execute_query("""
                            INSERT INTO progressing_questions_test_cases
                            (progressing_questions_id, input, output, is_example)
                            VALUES (%s, %s, %s, %s)
                        """, (problem_id, test_case.get('input', ''), test_case.get('output', ''), False))

        elif question_type == 'choice':
            # 创建选择题
            # 验证选择题特定字段
            options = data.get('options', {})
            correct_answer = data.get('correct_answer', '').strip()

            if not options or not correct_answer:
                return jsonify({"success": False, "message": "选择题必须包含选项和正确答案"}), 400

            if correct_answer not in ['A', 'B', 'C', 'D']:
                return jsonify({"success": False, "message": "正确答案必须是A、B、C或D"}), 400

            # 将选项转换为JSON字符串
            import json
            options_json = json.dumps(options, ensure_ascii=False)

            # 插入选择题
            result = db.execute_query("""
                INSERT INTO choice_questions
                (title, language, description, difficulty, knowledge_points, options, correct_answer, solution_idea, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (title, language, description, difficulty, knowledge_points, options_json, correct_answer, solution_idea))

            # 获取插入的题目ID
            problem_id = db.execute_query("SELECT LAST_INSERT_ID() as id")[0]['id']

        elif question_type == 'judgment':
            # 创建判断题
            # 验证判断题特定字段
            correct_answer = data.get('correct_answer')

            if correct_answer is None:
                return jsonify({"success": False, "message": "判断题必须包含正确答案"}), 400

            # 转换为布尔值
            if isinstance(correct_answer, str):
                correct_answer = correct_answer.lower() == 'true'
            elif isinstance(correct_answer, bool):
                correct_answer = correct_answer
            else:
                return jsonify({"success": False, "message": "判断题正确答案格式错误"}), 400

            # 插入判断题
            result = db.execute_query("""
                INSERT INTO judgment_questions
                (title, language, description, difficulty, knowledge_points, correct_answer, solution_idea, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (title, language, description, difficulty, knowledge_points, correct_answer, solution_idea))

            # 获取插入的题目ID
            problem_id = db.execute_query("SELECT LAST_INSERT_ID() as id")[0]['id']

        else:
            return jsonify({"success": False, "message": "无效的题目类型"}), 400

        return jsonify({
            "success": True,
            "message": "题目创建成功",
            "data": {
                "id": problem_id,
                "question_type": question_type
            }
        })

    except Exception as e:
        logger.error(f"创建题目失败: {e}")
        return jsonify({"success": False, "message": "创建题目失败"}), 500

@question_bank_bp.route('/api/question-bank/problem/<int:problem_id>', methods=['DELETE'])
def delete_problem(problem_id):
    """删除题目"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False,
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401

        problem_type = request.args.get('type', '').strip()

        if not problem_type:
            return jsonify({"success": False, "message": "题目类型不能为空"}), 400

        if problem_type not in ['progressing', 'choice', 'judgment']:
            return jsonify({"success": False, "message": "无效的题目类型"}), 400
        # 检查题目是否存在
        if problem_type == 'progressing':
            table_name = 'progressing_questions'
            id_column = 'progressing_questions_id'
            test_cases_table = 'progressing_questions_test_cases'
        elif problem_type == 'choice':
            table_name = 'choice_questions'
            id_column = 'choice_questions_id'
        elif problem_type == 'judgment':
            table_name = 'judgment_questions'
            id_column = 'judgment_questions_id'

        # 检查题目是否存在
        existing_problem = db.execute_query(f"SELECT {id_column} FROM {table_name} WHERE {id_column} = %s", (problem_id,))

        if not existing_problem:
            return jsonify({"success": False, "message": "题目不存在"}), 404

        # 删除题目
        if problem_type == 'progressing':
            # 先删除相关的测试用例
            db.execute_query(f"DELETE FROM {test_cases_table} WHERE {id_column} = %s", (problem_id,))

        # 删除题目本身
        db.execute_query(f"DELETE FROM {table_name} WHERE {id_column} = %s", (problem_id,))

        return jsonify({
            "success": True,
            "message": "题目删除成功"
        })

    except Exception as e:
        logger.error(f"删除题目失败: {e}")
        return jsonify({"success": False, "message": "删除题目失败"}), 500

@question_bank_bp.route('/api/question-bank/problem/<int:problem_id>', methods=['PUT'])
def update_problem(problem_id):
    """编辑题目"""
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

        # 获取题目类型，如果未提供则从数据库查询
        problem_type = data.get('question_type', '').strip()

        if not problem_type:
            # 从数据库尝试推断题目类型
            for table, type_name in [
                ('progressing_questions', 'progressing'),
                ('choice_questions', 'choice'),
                ('judgment_questions', 'judgment')
            ]:
                id_column = f"{table.split('_')[0]}_questions_id"
                result = db.execute_query(f"SELECT {id_column} FROM {table} WHERE {id_column} = %s", (problem_id,))
                if result:
                    problem_type = type_name
                    break

            if not problem_type:
                return jsonify({"success": False, "message": "题目不存在"}), 404
        else:
            # 验证题目是否存在
            if problem_type not in ['progressing', 'choice', 'judgment']:
                return jsonify({"success": False, "message": "无效的题目类型"}), 400

        # 构建更新字段列表
        update_fields = []
        update_values = []

        # 通用字段处理
        common_fields = ['title', 'language', 'description', 'difficulty', 'knowledge_points', 'solution_idea']
        for field in common_fields:
            if field in data:
                value = data[field].strip() if isinstance(data[field], str) else data[field]
                if value != '':  # 只更新非空值
                    update_fields.append(f"{field} = %s")
                    update_values.append(value)

        # 根据题型处理特定字段
        if problem_type == 'progressing':
            # 编程题特定的更新字段
            progressing_specific_fields = ['reference_code', 'input_description', 'output_description']
            for field in progressing_specific_fields:
                if field in data:
                    value = data[field].strip() if isinstance(data[field], str) else data[field]
                    update_fields.append(f"{field} = %s")
                    update_values.append(value)

            # 更新编程题
            table_name = 'progressing_questions'
            id_column = 'progressing_questions_id'

            # 检查题目是否存在
            existing = db.execute_query(f"SELECT {id_column} FROM {table_name} WHERE {id_column} = %s", (problem_id,))
            if not existing:
                return jsonify({"success": False, "message": "题目不存在"}), 404

            if update_fields:
                update_sql = f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE {id_column} = %s"
                update_values.append(problem_id)
                affected = db.execute_update(update_sql, update_values)

            # 处理测试用例更新
            if 'test_cases' in data and isinstance(data['test_cases'], list):
                # 先删除现有的测试用例
                db.execute_query(f"DELETE FROM progressing_questions_test_cases WHERE {id_column} = %s", (problem_id,))

                # 插入新的测试用例
                for test_case in data['test_cases']:
                    if isinstance(test_case, dict) and (test_case.get('input') or test_case.get('output')):
                        db.execute_query(f"""
                            INSERT INTO progressing_questions_test_cases
                            ({id_column}, input, output, is_example)
                            VALUES (%s, %s, %s, %s)
                        """, (problem_id, test_case.get('input', ''), test_case.get('output', ''), False))

        elif problem_type == 'choice':
            # 选择题特定字段
            if 'options' in data:
                import json
                options_json = json.dumps(data['options'], ensure_ascii=False)
                update_fields.append("options = %s")
                update_values.append(options_json)

            if 'correct_answer' in data:
                correct_answer = data['correct_answer'].strip()
                if correct_answer not in ['A', 'B', 'C', 'D']:
                    return jsonify({"success": False, "message": "正确答案必须是A、B、C或D"}), 400
                update_fields.append("correct_answer = %s")
                update_values.append(correct_answer)

            # 更新选择题
            table_name = 'choice_questions'
            id_column = 'choice_questions_id'

            # 检查题目是否存在
            existing = db.execute_query(f"SELECT {id_column} FROM {table_name} WHERE {id_column} = %s", (problem_id,))
            if not existing:
                return jsonify({"success": False, "message": "题目不存在"}), 404

            if update_fields:
                update_sql = f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE {id_column} = %s"
                update_values.append(problem_id)
                affected = db.execute_update(update_sql, update_values)

        elif problem_type == 'judgment':
            # 判断题特有字段
            if 'correct_answer' in data:
                correct_answer = data['correct_answer']
                # 转换为布尔值
                if isinstance(correct_answer, str):
                    correct_answer = correct_answer.lower() == 'true'
                elif isinstance(correct_answer, bool):
                    correct_answer = correct_answer
                else:
                    return jsonify({"success": False, "message": "判断题正确答案格式错误"}), 400

                update_fields.append("correct_answer = %s")
                update_values.append(correct_answer)

            # 更新判断题
            table_name = 'judgment_questions'
            id_column = 'judgment_questions_id'

            # 检查题目是否存在
            existing = db.execute_query(f"SELECT {id_column} FROM {table_name} WHERE {id_column} = %s", (problem_id,))
            if not existing:
                return jsonify({"success": False, "message": "题目不存在"}), 404

            if update_fields:
                update_sql = f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE {id_column} = %s"
                update_values.append(problem_id)
                affected = db.execute_update(update_sql, update_values)

        if not update_fields and 'test_cases' not in data:
            return jsonify({"success": False, "message": "没有有效的更新内容"}), 400

        return jsonify({
            "success": True,
            "message": "题目更新成功",
            "data": {
                "id": problem_id,
                "question_type": problem_type
            }
        })

    except Exception as e:
        logger.error(f"更新题目失败: {e}")
        return jsonify({"success": False, "message": "更新题目失败"}), 500
# 临时调试路由 - 题型筛选问题
@question_bank_bp.route('/api/debug/filter-test', methods=['GET'])
def debug_filter_test():
    """调试题型筛选功能"""
    try:
        # 解析查询参数
        problem_type = request.args.get('problem_type', '').strip()
        difficulty = request.args.get('difficulty', '').strip()
        language = request.args.get('language', '').strip()

        logger.info(f"调试筛选参数: problem_type={problem_type}, difficulty={difficulty}, language={language}")

        # 模拟筛选逻辑 (使用英文值)
        conditions = []
        params = []

        if problem_type == 'programming':
            base_sql = "SELECT * FROM progressing_questions WHERE 1=1"
            count_sql = "SELECT COUNT(*) as total FROM progressing_questions WHERE 1=1"
        elif problem_type == 'choice':
            base_sql = "SELECT * FROM choice_questions WHERE 1=1"
            count_sql = "SELECT COUNT(*) as total FROM choice_questions WHERE 1=1"
        elif problem_type == 'judgment':
            base_sql = "SELECT * FROM judgment_questions WHERE 1=1"
            count_sql = "SELECT COUNT(*) as total FROM judgment_questions WHERE 1=1"
        else:
            return jsonify({"error": "无效的题型", "problem_type": problem_type})

        if language:
            conditions.append("language = %s")
            params.append(language)

        if difficulty:
            conditions.append("difficulty = %s")
            params.append(difficulty)

        where_clause = " AND " + " AND ".join(conditions) if conditions else ""
        final_count_sql = count_sql + where_clause

        logger.info(f"最终 COUNT SQL: {final_count_sql}")
        logger.info(f"参数: {params}")

        # 尝试执行查询
        try:
            total_result = db.execute_query(final_count_sql, params)
            total = total_result[0]['total'] if total_result else 0
            logger.info(f"查询结果: {total_result}, 总计: {total}")

            return jsonify({
                "success": True,
                "message": "调试成功",
                "problem_type": problem_type,
                "difficulty": difficulty,
                "language": language,
                "count_sql": final_count_sql,
                "params": params,
                "total": total
            })

        except Exception as e:
            logger.error(f"数据库查询失败: {e}, SQL: {final_count_sql}, Params: {params}")
            return jsonify({
                "success": False,
                "error": str(e),
                "count_sql": final_count_sql,
                "params": params
            }), 500

    except Exception as e:
        logger.error(f"调试失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# 临时调试路由
@question_bank_bp.route('/api/debug/test-cases', methods=['POST'])
def debug_test_cases():
    """调试测试用例接收"""
    try:
        data = request.get_json()
        logger.info(f"接收到的数据: {data}")

        test_cases = data.get('test_cases', [])
        logger.info(f"测试用例数量: {len(test_cases)}")

        if test_cases:
            for i, tc in enumerate(test_cases):
                logger.info(f"测试用例 {i+1}: input='{tc.get('input', '')}', output='{tc.get('output', '')}'")

        return jsonify({
            "success": True,
            "message": "调试数据已记录",
            "received_data": data,
            "test_cases_count": len(test_cases)
        })

    except Exception as e:
        logger.error(f"调试测试用例失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500