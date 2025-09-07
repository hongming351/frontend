# MySQL 数据库 oljudge 结构和内容总结

## 表列表

- admins (4 行)
- choice_questions (22 行)
- classes (15 行)
- courses (3 行)
- homework_assignments (44 行)
- homework_questions (149 行)
- homework_submissions (21 行)
- judgment_questions (17 行)
- password_reset_tokens (9 行)
- programming_submissions (17 行)
- progressing_questions (29 行)
- progressing_questions_test_cases (122 行)
- student_answers (42 行)
- student_answers_backup (1 行)
- student_classes (42 行)
- student_zip_submissions (0 行)
- students (38 行)
- teacher_courses (16 行)
- teacher_student_answers (42 行)
- teachers (10 行)
- zip_processing_logs (0 行)

## 表结构

### admins

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| admin_id | int | NO | PRI | NULL |
| username | varchar(50) | NO | UNI | NULL |
| password | varchar(255) | NO |  | NULL |
| email | varchar(100) | NO | UNI | NULL |
| telenum | varchar(20) | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### choice_questions

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| choice_questions_id | int | NO | PRI | NULL |
| title | varchar(255) | NO |  | NULL |
| language | varchar(20) | YES |  | NULL |
| difficulty | varchar(20) | YES |  | NULL |
| knowledge_points | varchar(20) | YES |  | NULL |
| description | text | NO |  | NULL |
| options | json | YES |  | NULL |
| correct_answer | varchar(10) | NO |  | NULL |
| solution_idea | text | YES |  | NULL |
| created_at | datetime | YES |  | NULL |
| updated_at | datetime | YES |  | NULL |

### classes

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| class_id | int | NO | PRI | NULL |
| course_id | int | NO | MUL | NULL |
| teacher_id | int | NO | MUL | NULL |
| class_name | varchar(50) | NO | MUL | NULL |
| language | enum('C++','Python') | NO |  | NULL |
| description | text | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### courses

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| course_id | int | NO | PRI | NULL |
| course_name | varchar(100) | NO | MUL | NULL |
| language | enum('C++','Python') | NO | MUL | NULL |
| description | text | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### homework_assignments (作业分配表)

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| title | varchar(255) | NO |  | NULL |
| description | text | YES |  | NULL |
| class_id | int | YES | MUL | NULL |
| teacher_id | int | YES | MUL | NULL |
| course_id | int | YES | MUL | NULL |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP |
| publish_date | date | YES |  | NULL |
| deadline | date | YES |  | NULL |

### homework_questions (作业题目表)

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| homework_id | int | NO | MUL | NULL |
| question_id | int | NO |  | NULL |
| question_type | enum('progressing','choice','judgment') | NO |  | NULL |
| score | int | YES |  | 10 |
| order_num | int | YES |  | 0 |
| created_at | datetime | YES |  | CURRENT_TIMESTAMP |
| updated_at | datetime | YES |  | CURRENT_TIMESTAMP |

### judgment_questions

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| judgment_questions_id | int | NO | PRI | NULL |
| title | varchar(255) | NO |  | NULL |
| language | varchar(20) | YES |  | NULL |
| difficulty | varchar(20) | YES |  | NULL |
| knowledge_points | varchar(20) | YES |  | NULL |
| description | text | NO |  | NULL |
| correct_answer | tinyint(1) | YES |  | NULL |
| solution_idea | text | YES |  | NULL |
| created_at | datetime | YES |  | NULL |
| updated_at | datetime | YES |  | NULL |

### progressing_questions

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| progressing_questions_id | int | NO | PRI | NULL |
| title | varchar(255) | NO |  | NULL |
| language | varchar(20) | YES |  | NULL |
| description | text | NO |  | NULL |
| difficulty | enum('简单','中等','困难') | YES |  | NULL |
| knowledge_points | text | YES |  | NULL |
| solution_idea | text | YES |  | NULL |
| reference_code | text | YES |  | NULL |
| created_at | datetime | YES |  | NULL |
| updated_at | datetime | YES |  | NULL |
| input_description | text | YES |  | NULL |
| output_description | text | YES |  | NULL |

### progressing_questions_test_cases

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | NULL |
| progressing_questions_id | int | NO | MUL | NULL |
| input | text | NO |  | NULL |
| output | text | NO |  | NULL |
| is_example | tinyint(1) | YES |  | NULL |

### homework_submissions (作业提交表)

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| student_id | int | NO | MUL | NULL |
| homework_id | int | NO | MUL | NULL |
| submit_status | enum('submitted','graded','returned') | NO | MUL | submitted |
| submitted_at | datetime | YES |  | NULL |
| graded_at | datetime | YES |  | NULL |
| total_score | decimal(6,2) | YES |  | 0.00 |
| auto_score | decimal(6,2) | YES |  | 0.00 |
| manual_score | decimal(6,2) | YES |  | 0.00 |
| total_questions | int | YES |  | 0 |
| answered_questions | int | YES |  | 0 |
| correct_questions | int | YES |  | 0 |
| teacher_comment | text | YES |  | NULL |
| graded_by | int | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### programming_submissions (编程题提交历史表)

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| student_id | int | NO | MUL | NULL |
| homework_id | int | NO | MUL | NULL |
| question_id | int | NO |  | NULL |
| submission_code | text | NO |  | NULL |
| language | varchar(20) | YES |  | Python |
| submit_time | datetime | NO |  | NULL |
| run_status | enum('pending','running','success','failed','timeout','error') | YES | MUL | pending |
| execution_time | int | YES |  | NULL |
| memory_usage | int | YES |  | NULL |
| test_results | json | YES |  | NULL |
| passed_tests | int | YES |  | 0 |
| total_tests | int | YES |  | 0 |
| score | decimal(5,2) | YES |  | 0.00 |
| compile_error | text | YES |  | NULL |
| runtime_error | text | YES |  | NULL |
| ip_address | varchar(45) | YES |  | NULL |
| user_agent | text | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### student_answers (学生答案表)

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| student_id | int | NO | MUL | NULL |
| homework_id | int | NO |  | NULL |
| question_id | int | NO | MUL | NULL |
| question_type | enum('progressing','choice','judgment') | NO |  | NULL |
| answer_text | text | YES |  | NULL |
| choice_answer | varchar(10) | YES |  | NULL |
| judgment_answer | tinyint(1) | YES |  | NULL |
| is_correct | tinyint(1) | YES |  | NULL |
| score | decimal(5,2) | YES |  | NULL |
| teacher_comment | text | YES |  | NULL |
| status | enum('submitted','graded') | NO | MUL | submitted |
| last_attempt_at | datetime | YES |  | NULL |
| graded_at | datetime | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### student_classes

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | NULL |
| student_id | int | NO | MUL | NULL |
| class_id | int | NO | MUL | NULL |
| joined_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### students

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| student_id | int | NO | PRI | NULL |
| username | varchar(50) | NO | UNI | NULL |
| password | varchar(255) | NO |  | NULL |
| email | varchar(100) | NO | UNI | NULL |
| telenum | varchar(20) | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| status | enum('active','inactive') | YES |  | NULL |

### teacher_courses

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | NULL |
| teacher_id | int | NO | MUL | NULL |
| course_id | int | NO | MUL | NULL |
| assigned_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### teachers

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| teacher_id | int | NO | PRI | NULL |
| username | varchar(50) | NO | UNI | NULL |
| password | varchar(255) | NO |  | NULL |
| email | varchar(100) | NO | UNI | NULL |
| telenum | varchar(20) | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| status | enum('active','inactive') | YES |  | NULL |

### password_reset_tokens

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| email | varchar(255) | NO | MUL | NULL |
| token | varchar(255) | NO | UNI | NULL |
| expires_at | datetime | NO |  | NULL |
| used | tinyint(1) | YES |  | 0 |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### student_answers_backup

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO |  | 0 |
| student_id | int | NO |  | NULL |
| homework_id | int | NO |  | NULL |
| question_id | int | NO |  | NULL |
| question_type | enum('progressing','choice','judgment') | NO |  | NULL |
| answer_text | text | YES |  | NULL |
| choice_answer | varchar(10) | YES |  | NULL |
| judgment_answer | tinyint(1) | YES |  | NULL |
| is_correct | tinyint(1) | YES |  | NULL |
| score | decimal(5,2) | YES |  | NULL |
| teacher_comment | text | YES |  | NULL |
| status | enum('draft','submitted','graded') | YES |  | draft |
| submit_count | int | YES |  | 0 |
| first_attempt_at | datetime | YES |  | NULL |
| last_attempt_at | datetime | YES |  | NULL |
| graded_at | datetime | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### student_zip_submissions

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| student_id | int | NO | MUL | NULL |
| homework_id | int | NO |  | NULL |
| question_id | int | NO | MUL | NULL |
| zip_filename | varchar(255) | NO |  | NULL |
| zip_content | longblob | NO |  | NULL |
| file_size | int | YES |  | NULL |
| language | varchar(20) | YES | MUL | python |
| extract_status | enum('pending','success','failed') | YES |  | pending |
| validation_status | enum('pending','valid','invalid') | YES |  | pending |
| evaluation_status | enum('pending','success','failed','error') | YES | MUL | pending |
| is_correct | tinyint(1) | YES |  | NULL |
| score | decimal(5,2) | YES |  | NULL |
| evaluation_result | json | YES |  | NULL |
| error_message | text | YES |  | NULL |
| submit_time | datetime | NO | MUL | NULL |
| ip_address | varchar(45) | YES |  | NULL |
| user_agent | text | YES |  | NULL |
| created_at | timestamp | YES |  | CURRENT_TIMESTAMP |
| updated_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### teacher_student_answers

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| answer_id | int | NO |  | 0 |
| student_id | int | NO |  | NULL |
| student_name | varchar(50) | NO |  | NULL |
| homework_id | int | NO |  | NULL |
| homework_title | varchar(255) | NO |  | NULL |
| question_id | int | NO |  | NULL |
| question_title | varchar(255) | YES |  | NULL |
| question_type | enum('progressing','choice','judgment') | NO |  | NULL |
| question_type_name | varchar(3) | YES |  | NULL |
| answer_text | text | YES |  | NULL |
| choice_answer | varchar(10) | YES |  | NULL |
| judgment_answer | tinyint(1) | YES |  | NULL |
| is_correct | tinyint(1) | YES |  | NULL |
| score | decimal(5,2) | YES |  | NULL |
| status | enum('submitted','graded') | NO |  | submitted |
| teacher_comment | text | YES |  | NULL |
| submit_time | datetime | YES |  | NULL |
| graded_at | datetime | YES |  | NULL |
| deadline | date | YES |  | NULL |

### teacher_courses

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | NULL |
| teacher_id | int | NO | MUL | NULL |
| course_id | int | NO | MUL | NULL |
| assigned_at | timestamp | YES |  | CURRENT_TIMESTAMP |

### zip_processing_logs

| 列名 | 类型 | 可空 | 键 | 默认值 |
|------|------|------|----|--------|
| id | int | NO | PRI | AUTO_INCREMENT |
| zip_submission_id | int | YES | MUL | NULL |
| log_type | enum('info','warning','error') | YES |  | info |
| message | text | NO |  | NULL |
| log_time | timestamp | YES | MUL | CURRENT_TIMESTAMP |

## 表内容样本

### admins

| admin_id | username | password | email | telenum | created_at | updated_at |
|----------|----------|----------|-------|---------|------------|------------|
| 1 | admin1 | admin123 | <admin1@example.com> | 13800000001 | 2025-08-22 10:36:41 | 2025-08-22 10:36:41 |
| 2 | admin2 | admin456 | <admin2@example.com> | 13800000002 | 2025-08-22 10:36:41 | 2025-08-22 10:36:41 |
| 3 | test_admin | 0192023a7bbd73250516f069df18b500 | <admin@example.com> | 13900139000 | 2025-08-22 16:13:27 | 2025-08-22 16:13:27 |
| 4 | dvdrg | e10adc3949ba59abbe56e057f20f883e | cdvbvbrns@youxiang | 12121227181 | 2025-08-22 16:25:08 | 2025-08-22 16:25:08 |

### students (部分)

| student_id | username | password | email | telenum | created_at | updated_at | status |
|------------|----------|----------|-------|---------|------------|------------|--------|
| 1 | student_zhang | student123 | <zhangsan@example.com> | 13700000001 | 2025-08-22 10:36:41 | 2025-08-24 10:44:27 | active |
| 2 | student_li | student456 | <lisi@example.com> | 13700000002 | 2025-08-22 10:36:41 | 2025-08-24 10:44:27 | active |
| ... | ... | ... | ... | ... | ... | ... | ... |

### teachers

| teacher_id | username | password | email | telenum | created_at | updated_at | status |
|------------|----------|----------|-------|---------|------------|------------|--------|
| 1 | teacher_wang | teacher123 | <wang@example.com> | 13900000001 | 2025-08-22 10:36:41 | 2025-08-23 09:04:07 | active |
| 2 | teacher_li | teacher456 | <li@example.com> | 13800000002 | 2025-08-22 10:36:41 | 2025-08-24 18:52:02 | active |
| ... | ... | ... | ... | ... | ... | ... | ... |

### courses

| course_id | course_name | language | description | created_at | updated_at |
|-----------|-------------|----------|-------------|------------|------------|
| 1 | C++编程 | C++ | 学习C++语言编程 | 2025-08-22 10:36:41 | 2025-08-22 10:36:41 |
| 2 | Python编程 | Python | 学习Python语言编程 | 2025-08-22 10:36:41 | 2025-08-22 10:36:41 |

### classes

| class_id | course_id | teacher_id | class_name | language | description | created_at | updated_at |
|----------|-----------|------------|------------|----------|-------------|------------|------------|
| 1 | 1 | 3 | 1班 | C++ | C++编程1班 | 2025-08-22 10:36:41 | 2025-08-23 10:42:58 |
| 2 | 1 | 3 | 2班 | C++ | C++编程2班 | 2025-08-22 10:36:41 | 2025-08-23 10:42:58 |
| ... | ... | ... | ... | ... | ... | ... | ... |

## 结论

数据库 oljudge 包含 21 张表，存储了管理员、学生、教师、课程、班级、题目、作业提交、编程题提交、密码重置等功能。

### 修改内容

- 修改了数据类型：
  - judgment_questions.correct_answer → BOOLEAN → tinyint(1)
  - choice_questions.options → JSON (改为可空)
  - progressing_questions_test_cases.is_example → BOOLEAN → tinyint(1)
- 移除了 progressing_questions.type 列
- **重新设计了作业系统**：
  - 删除了原来的 homework_tables
  - 创建了 homework_assignments：作业分配表（存储作业基本信息）
  - 创建了 homework_questions：作业题目表（存储作业包含的题目，支持每作业多题）
- **新增学生作业提交功能表**：
  - homework_submissions：作业提交表（跟踪作业提交状态和评分）
  - programming_submissions：编程题提交历史表（记录编程题的多次提交）
  - student_answers：学生答案表（存储学生的作答记录）
  - student_answers_backup：学生答案备份表（备份学生答案数据）
  - teacher_student_answers：教师查看学生答案表（为教师提供便捷的查询视图）
- 添加了外键约束：
  - homework_assignments.class_id → classes.class_id
  - homework_assignments.teacher_id → teachers.teacher_id
  - homework_assignments.course_id → courses.course_id
  - homework_questions.homework_id → homework_assignments.id
  - progressing_questions_test_cases.progressing_questions_id → progressing_questions.progressing_questions_id
- 扩展了homework_assignments表，添加了publish_date和deadline字段用于作业发布时间和截止时间管理
- 删除了不匹配的测试用例数据

### 2025-08-30 更新

**新增表：**

- password_reset_tokens：密码重置令牌表，支持用户密码重置功能
- problems：编程题表，存储编程题题目信息（旧的progressing_questions表的替代）
- student_zip_submissions：学生ZIP文件提交表，支持计算机专业学生的项目提交
- zip_processing_logs：ZIP处理日志表，记录文件处理过程

**新增视图（已存在但未充分描述）：**

- student_answers_backup：学生答案备份表
- teacher_student_answers：教师查看学生答案视图（教师工作台视图）

**数据更新统计：**

- students：从23行增至38行
- teachers：从8行增至10行
- classes：从9行增至15行
- courses：从2行增至3行
- homework_assignments：新增44个作业
- homework_questions：新增149道题目
- homework_submissions：新增21份提交
- programming_submissions：新增17次编程提交
- progressing_questions：从7题增至29题
- progressing_questions_test_cases：从34个用例增至122个

### 新的作业系统功能

- 支持教师创建作业并指定班级
- 每个作业可包含多种题型的多道题目
- 支持题目顺序和分值设置
- 支持级联删除（删除作业时自动删除相关题目）
- **新增作业提交和评分功能**：
  - homework_submissions表跟踪作业提交状态和总体评分
  - programming_submissions表记录编程题的多次提交历史，包括执行结果和测试通过情况
  - student_answers表存储学生的所有作答记录，支持草稿、提交、评分状态
  - teacher_student_answers表为教师提供便捷的学生答案查询视图
- **增强的作业管理**：
  - 支持设置作业发布时间(publish_date)和截止时间(deadline)
  - 支持多种提交状态管理(draft, submitted, graded, returned)
  - 支持自动评分和人工评分分离存储

### 使用示例

```sql
-- 创建作业
INSERT INTO homework_assignments (title, description, class_id, teacher_id, course_id)
VALUES ('第一次编程作业', '基础编程练习', 1, 1, 1);

-- 向作业添加题目
INSERT INTO homework_questions (homework_id, question_id, question_type, score, order_num)
VALUES (1, 1, 'progressing', 20, 1),
       (1, 2, 'choice', 10, 2),
       (1, 1, 'judgment', 5, 3);

-- 查询作业详情
SELECT ha.title, hq.question_id, hq.question_type, hq.score, hq.order_num
FROM homework_assignments ha
JOIN homework_questions hq ON ha.id = hq.homework_id
WHERE ha.id = 1;

-- 学生提交作业答案
INSERT INTO student_answers (student_id, homework_id, question_id, question_type, answer_text, choice_answer, judgment_answer, status)
VALUES (1, 1, 1, 'choice', NULL, 'A', NULL, 'submitted');

-- 记录编程题提交
INSERT INTO programming_submissions (student_id, homework_id, question_id, submission_code, language, submit_time, run_status)
VALUES (1, 1, 2, 'print("Hello World")', 'Python', NOW(), 'success');

-- 查询作业提交状态
SELECT hs.*, sa.question_id, sa.is_correct, sa.score
FROM homework_submissions hs
JOIN student_answers sa ON hs.student_id = sa.student_id AND hs.homework_id = sa.homework_id
WHERE hs.student_id = 1 AND hs.homework_id = 1;

-- 教师查看学生答案（使用视图）
SELECT * FROM teacher_student_answers
WHERE homework_id = 1 AND teacher_id = 1
ORDER BY student_name, question_id;
```

现在数据库结构更加完整，支持学生作业提交、编程题执行、教师评分等全方位功能。
