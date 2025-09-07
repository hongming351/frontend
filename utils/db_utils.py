# -*- coding: utf-8 -*-
from database import db
import json

def import_problem_to_db(title, description, input_desc=None, output_desc=None, test_cases=None,
                        difficulty='中等', solution_idea=None, reference_code=None,
                        question_type='programming', options=None, correct_answer=None, is_true=None,
                        language='Python', knowledge_points=None):
    """
    将生成的题目导入数据库
    :param title: 题目名称
    :param description: 题目描述
    :param input_desc: 输入说明（编程题）
    :param output_desc: 输出说明（编程题）
    :param test_cases: 测试用例列表（编程题），格式: [{'input': '...', 'output': '...', 'is_example': True/False}, ...]
    :param difficulty: 难度
    :param solution_idea: 解题思路
    :param reference_code: 参考代码（编程题）
    :param question_type: 题目类型（programming/choice/judgment）
    :param options: 选择题选项列表，格式: [{'key': 'A', 'text': '选项内容', 'is_correct': True/False}, ...]
    :param correct_answer: 选择题正确答案（如"A"）
    :param is_true: 判断题正确答案（True/False）
    :param language: 编程语言
    :param knowledge_points: 知识点
    """
    try:
        if question_type == 'programming':
            # 创建编程题记录（插入到progressing_questions表，与题库管理一致）
            sql = """
                INSERT INTO progressing_questions (title, language, description, difficulty, knowledge_points,
                                                 input_description, output_description, solution_idea, reference_code,
                                                 created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = [
                title, language, description, difficulty, knowledge_points or '',
                input_desc, output_desc, solution_idea, reference_code
            ]
            problem_id = db.execute_insert(sql, params)

            # 插入测试用例
            if test_cases and len(test_cases) > 0:
                for test_case in test_cases:
                    if isinstance(test_case, dict) and (test_case.get('input') or test_case.get('output')):
                        db.execute_update("""
                            INSERT INTO progressing_questions_test_cases
                            (progressing_questions_id, input, output, is_example)
                            VALUES (%s, %s, %s, %s)
                        """, (problem_id, test_case.get('input', ''), test_case.get('output', ''), False))

            return {"success": True, "id": problem_id}

        elif question_type == 'choice':
            # 创建选择题记录（插入到choice_questions表）
            sql = """
                INSERT INTO choice_questions (title, language, description, difficulty, knowledge_points,
                                            options, correct_answer, solution_idea, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = [
                title, language, description, difficulty, knowledge_points or '',
                json.dumps(options) if options else '[]',
                correct_answer, solution_idea
            ]
            choice_id = db.execute_update(sql, params)
            return {"success": True, "id": choice_id}

        elif question_type == 'judgment':
            # 创建判断题记录（插入到judgment_questions表）
            sql = """
                INSERT INTO judgment_questions (title, language, description, difficulty, knowledge_points,
                                              correct_answer, solution_idea, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            params = [
                title, language, description, difficulty, knowledge_points or '',
                is_true, solution_idea
            ]
            judgment_id = db.execute_update(sql, params)
            return {"success": True, "id": judgment_id}

        else:
            return {"success": False, "error": "不支持的题目类型"}

    except Exception as e:
        return {"success": False, "error": str(e)}