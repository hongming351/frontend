from flask import Blueprint, jsonify, request, session
from database import db
import logging
import time
import json
logger = logging.getLogger(__name__)
problems_bp = Blueprint('problems', __name__)

@problems_bp.route('/api/problems', methods=['GET'])
def get_problems():
    """获取题目列表"""
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        offset = (page - 1) * per_page

        # 搜索条件
        search = request.args.get('search', '', type=str)

        # 构建SQL查询
        where_clause = "WHERE 1=1"
        params = []

        if search:
            where_clause += " AND (title LIKE %s OR description LIKE %s)"
            params.extend([f'%{search}%', f'%{search}%'])

        # 查询题目总数
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM problems
            {where_clause}
        """
        total = db.execute_query(count_sql, params)[0]['total']

        # 查询题目列表
        sql = f"""
            SELECT id, title, difficulty, tags, create_time
            FROM problems
            {where_clause}
            ORDER BY create_time DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])
        problems = db.execute_query(sql, params)

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
        logger.error(f"获取题目列表失败: {e}")
        return jsonify({"success": False, "message": "获取题目列表失败"}), 500

@problems_bp.route('/api/problems/<int:problem_id>', methods=['GET'])
def get_problem(problem_id):
    """获取单个题目详情"""
    try:
        sql = """
            SELECT id, title, description, input_format, output_format, 
                   sample_input, sample_output, difficulty, tags, test_cases
            FROM problems
            WHERE id = %s
        """
        problem = db.execute_query(sql, [problem_id])

        if not problem:
            return jsonify({"success": False, "message": "题目不存在"}), 404

        # 解析test_cases字段（假设存储为JSON字符串）
        try:
            problem[0]['test_cases'] = json.loads(problem[0]['test_cases'])
        except json.JSONDecodeError:
            problem[0]['test_cases'] = []

        return jsonify({"success": True, "data": problem[0]})
    except Exception as e:
        logger.error(f"获取题目详情失败: {e}")
        return jsonify({"success": False, "message": "获取题目详情失败"}), 500

@problems_bp.route('/api/problems', methods=['POST'])
def create_problem():
    """创建新题目（教师权限）"""
    try:
        # 检查教师权限
        if 'identity' not in session or session['identity'] not in ['teacher', 'admin']:
            return jsonify({
                "success": False, 
                "message": "需要教师或管理员权限",
                "redirect": "/login"
            }), 401

        data = request.get_json()

        # 验证必填字段
        required_fields = ['title', 'description', 'input_format', 'output_format', 
                          'sample_input', 'sample_output', 'difficulty', 'test_cases']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"缺少必填字段: {field}"}), 400

        # 处理标签和测试用例
        tags = ','.join(data.get('tags', []))
        test_cases = json.dumps(data['test_cases'])

        # 插入题目
        sql = """
            INSERT INTO problems (title, description, input_format, output_format, 
                                 sample_input, sample_output, difficulty, tags, test_cases, 
                                 create_time, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        """
        params = [
            data['title'], data['description'], data['input_format'], data['output_format'],
            data['sample_input'], data['sample_output'], data['difficulty'], tags,
            test_cases, session['user_id']
        ]
        problem_id = db.execute_update(sql, params)

        return jsonify({"success": True, "message": "题目创建成功", "problem_id": problem_id}), 201
    except Exception as e:
        logger.error(f"创建题目失败: {e}")
        return jsonify({"success": False, "message": "创建题目失败"}), 500

@problems_bp.route('/api/submit', methods=['POST'])
def submit_code():
    """提交代码判题"""
    try:
        # 检查用户是否登录
        if 'user_id' not in session:
            return jsonify({
                "success": False, 
                "message": "请先登录",
                "redirect": "/login"
            }), 401

        data = request.get_json()

        # 验证必填字段
        required_fields = ['problemId', 'code', 'language']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"缺少必填字段: {field}"}), 400

        problem_id = data['problemId']
        code = data['code']
        language = data['language']

        # 获取题目信息
        problem_sql = "SELECT test_cases FROM problems WHERE id = %s"
        problem = db.execute_query(problem_sql, [problem_id])

        if not problem:
            return jsonify({"success": False, "message": "题目不存在"}), 404

        # 解析测试用例
        try:
            test_cases = json.loads(problem[0]['test_cases'])
        except json.JSONDecodeError:
            return jsonify({"success": False, "message": "题目测试用例格式错误"}), 500

        # 模拟判题过程（实际项目中这里会调用判题引擎）
        passed_count = 0
        total_count = len(test_cases)
        execution_time = 0
        error_message = None
        results = []

        for idx, test_case in enumerate(test_cases):
            # 模拟执行时间
            start_time = time.time()
            time.sleep(0.1)  # 模拟代码执行
            end_time = time.time()
            exec_time = (end_time - start_time) * 1000  # 转换为毫秒
            execution_time += exec_time

            # 模拟代码执行结果（实际项目中这里会调用判题引擎）
            # 随机模拟通过或失败，以便测试不同场景
            import random
            passed = random.choice([True, True, True, False])  # 75%概率通过
            output = test_case['expected_output'] if passed else f'错误输出: {test_case["input"]}'

            if passed:
                passed_count += 1
            elif not error_message:
                error_message = f'测试用例 {idx+1} 失败'

            results.append({
                'test_case_id': idx+1,
                'input': test_case['input'],
                'expected_output': test_case['expected_output'],
                'actual_output': output,
                'passed': passed,
                'execution_time': round(exec_time, 2)
            })

        # 计算平均执行时间
        avg_execution_time = execution_time / total_count if total_count > 0 else 0

        # 保存提交记录
        status = 'success' if passed_count == total_count else 'failed'
        submission_sql = """
            INSERT INTO submissions (problem_id, user_id, code, language, status, 
                                    passed_count, total_count, execution_time, submit_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        submission_params = [
            problem_id, session['user_id'], code, language, status,
            passed_count, total_count, avg_execution_time
        ]
        submission_id = db.execute_update(submission_sql, submission_params)

        # 返回判题结果
        return jsonify({
            "success": True,
            "data": {
                "submission_id": submission_id,
                "status": status,
                "passed_count": passed_count,
                "total_count": total_count,
                "execution_time": round(avg_execution_time, 2),
                "error_message": error_message
            }
        })
    except Exception as e:
        logger.error(f"代码提交失败: {e}")
        return jsonify({"success": False, "message": "代码提交失败"}), 500

@problems_bp.route('/api/test-case/run', methods=['POST'])
def run_test_case():
    """运行单个测试用例"""
    try:
        # 检查用户是否登录
        if 'user_id' not in session:
            return jsonify({
                "success": False, 
                "message": "请先登录",
                "redirect": "/login"
            }), 401

        data = request.get_json()

        # 验证必填字段
        required_fields = ['problemId', 'code', 'language', 'testCase']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"缺少必填字段: {field}"}), 400

        problem_id = data['problemId']
        code = data['code']
        language = data['language']
        test_case = data['testCase']

        # 模拟测试用例运行
        start_time = time.time()
        time.sleep(0.2)  # 模拟代码执行
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # 转换为毫秒

        # 模拟运行结果（实际项目中这里会调用判题引擎）
        # 随机模拟通过或失败，以便测试不同场景
        import random
        passed = random.choice([True, True, True, False])  # 75%概率通过
        output = test_case.get('expected_output', '模拟输出结果') if passed else f'错误输出: {test_case.get("input", "")}'

        result = {
            "success": True,
            "output": output,
            "execution_time": round(execution_time, 2),
            "passed": passed
        }

        return jsonify(result)
    except Exception as e:
        logger.error(f"运行测试用例失败: {e}")
        return jsonify({"success": False, "message": "运行测试用例失败"}), 500