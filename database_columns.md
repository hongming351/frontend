# OLJudge数据库列信息

以下是OLJudge数据库中所有21张表的三列信息：列名、类型和描述。描述基于数据库的功能——这是一个在线编程Judge系统，用于编程教学，支持教师创建课程、班级、作业，学生提交答案和编程代码，系统进行自动化判题和评分。

## admins

| 列名 | 类型 | 描述 |
|------|------|------|
| admin_id | int | 管理员用户唯一标识符 |
| username | varchar(50) | 管理员登录用户名 |
| password | varchar(255) | 管理员密码哈希值 |
| email | varchar(100) | 管理员电子邮件地址 |
| telenum | varchar(20) | 管理员联系电话号码 |
| created_at | timestamp | 管理员账户创建时间戳 |
| updated_at | timestamp | 管理员账户最后更新时间戳 |

## choice_questions

| 列名 | 类型 | 描述 |
|------|------|------|
| choice_questions_id | int | 选择题唯一标识符 |
| title | varchar(255) | 选择题标题 |
| language | varchar(20) | 编程语言种类（C++、Python等） |
| difficulty | varchar(20) | 题目难度等级（简单、中等、困难等） |
| knowledge_points | varchar(20) | 涉及的知识点 |
| description | text | 选择题详细描述 |
| options | json | 选择题选项列表（JSON格式） |
| correct_answer | varchar(10) | 选择题正确选项标识 |
| solution_idea | text | 选择题解题思路说明 |
| created_at | datetime | 题目创建日期时间 |
| updated_at | datetime | 题目更新日期时间 |

## classes

| 列名 | 类型 | 描述 |
|------|------|------|
| class_id | int | 班级唯一标识符 |
| course_id | int | 所属课程ID，外键关联courses表 |
| teacher_id | int | 任课教师ID，外键关联teachers表 |
| class_name | varchar(50) | 班级名称 |
| language | enum('C++','Python') | 班级编程语言 |
| description | text | 班级描述信息 |
| created_at | timestamp | 班级创建时间戳 |
| updated_at | timestamp | 班级更新时间戳 |

## courses

| 列名 | 类型 | 描述 |
|------|------|------|
| course_id | int | 课程唯一标识符 |
| course_name | varchar(100) | 课程名称 |
| language | enum('C++','Python') | 课程编程语言 |
| description | text | 课程描述信息 |
| created_at | timestamp | 课程创建时间戳 |
| updated_at | timestamp | 课程更新时间戳 |

## homework_assignments

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 作业分配唯一标识符 |
| title | varchar(255) | 作业标题 |
| description | text | 作业描述说明 |
| class_id | int | 分配至的班级ID |
| teacher_id | int | 出题教师ID |
| course_id | int | 所属课程ID |
| created_at | datetime | 作业创建日期时间 |
| updated_at | datetime | 作业更新日期时间 |
| publish_date | date | 作业发布日期 |
| deadline | date | 作业截止日期 |

## homework_questions

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 作业题目关联唯一标识符 |
| homework_id | int | 所属作业ID |
| question_id | int | 题目ID |
| question_type | enum('progressing','choice','judgment') | 题目类型（编程题、选择题、判断题） |
| score | int | 题目分值 |
| order_num | int | 题目在作业中的顺序号 |
| created_at | datetime | 关联创建日期时间 |
| updated_at | datetime | 关联更新日期时间 |

## homework_submissions

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 作业提交记录唯一标识符 |
| student_id | int | 提交学生ID |
| homework_id | int | 作业ID |
| submit_status | enum('submitted','graded','returned') | 提交状态 |
| submitted_at | datetime | 提交时间 |
| graded_at | datetime | 评分时间 |
| total_score | decimal(6,2) | 作业总分 |
| auto_score | decimal(6,2) | 自动评分分值 |
| manual_score | decimal(6,2) | 人工评分分值 |
| total_questions | int | 作业题目总数 |
| answered_questions | int | 已答题目数 |
| correct_questions | int | 正确题目数 |
| teacher_comment | text | 教师批改评语 |
| graded_by | int | 批改教师ID |
| created_at | timestamp | 记录创建时间戳 |
| updated_at | timestamp | 记录更新时间戳 |

## judgment_questions

| 列名 | 类型 | 描述 |
|------|------|------|
| judgment_questions_id | int | 判断题唯一标识符 |
| title | varchar(255) | 判断题标题 |
| language | varchar(20) | 编程语言种类 |
| difficulty | varchar(20) | 题目难度等级 |
| knowledge_points | varchar(20) | 涉及的知识点 |
| description | text | 判断题描述 |
| correct_answer | tinyint(1) | 判断题正确答案（1为正确，0为错误） |
| solution_idea | text | 判断题解题思路 |
| created_at | datetime | 题目创建日期时间 |
| updated_at | datetime | 题目更新日期时间 |

## password_reset_tokens

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 密码重置令牌唯一标识符 |
| email | varchar(255) | 用户电子邮件地址 |
| token | varchar(255) | 重置令牌字符串 |
| expires_at | datetime | 令牌过期日期时间 |
| used | tinyint(1) | 令牌是否已被使用 |
| created_at | timestamp | 令牌创建时间戳 |
| updated_at | timestamp | 令牌更新时间戳 |

## programming_submissions

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 编程题提交历史唯一标识符 |
| student_id | int | 提交学生ID |
| homework_id | int | 所属作业ID |
| question_id | int | 题目ID |
| submission_code | text | 学生提交的编程代码 |
| language | varchar(20) | 编程语言（默认Python） |
| submit_time | datetime | 提交时间 |
| run_status | enum('pending','running','success','failed','timeout','error') | 代码运行状态 |
| execution_time | int | 执行时间（毫秒） |
| memory_usage | int | 内存使用量 |
| test_results | json | 测试用例执行结果 |
| passed_tests | int | 通过测试用例数 |
| total_tests | int | 总测试用例数 |
| score | decimal(5,2) | 编程题得分 |
| compile_error | text | 编译错误信息 |
| runtime_error | text | 运行时错误信息 |
| ip_address | varchar(45) | 提交IP地址 |
| user_agent | text | 用户代理信息 |
| created_at | timestamp | 记录创建时间戳 |

## progressing_questions

| 列名 | 类型 | 描述 |
|------|------|------|
| progressing_questions_id | int | 编程题唯一标识符 |
| title | varchar(255) | 编程题标题 |
| language | varchar(20) | 编程语言种类 |
| description | text | 编程题描述 |
| difficulty | enum('简单','中等','困难') | 题目难度等级 |
| knowledge_points | text | 涉及的知识点列表 |
| solution_idea | text | 编程题解题思路 |
| reference_code | text | 参考解答代码 |
| created_at | datetime | 题目创建日期时间 |
| updated_at | datetime | 题目更新日期时间 |
| input_description | text | 输入格式描述 |
| output_description | text | 输出格式描述 |

## progressing_questions_test_cases

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 测试用例唯一标识符 |
| progressing_questions_id | int | 所属编程题ID |
| input | text | 测试输入数据 |
| output | text | 预期输出数据 |
| is_example | tinyint(1) | 是否为示例测试用例 |

## student_answers

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 学生答案记录唯一标识符 |
| student_id | int | 学生ID |
| homework_id | int | 作业ID |
| question_id | int | 题目ID |
| question_type | enum('progressing','choice','judgment') | 题目类型 |
| answer_text | text | 文字答案内容 |
| choice_answer | varchar(10) | 选择题答案选项 |
| judgment_answer | tinyint(1) | 判断题答案 |
| is_correct | tinyint(1) | 答案是否正确 |
| score | decimal(5,2) | 该题得分 |
| teacher_comment | text | 教师针对该题的评语 |
| status | enum('submitted','graded') | 答案状态 |
| last_attempt_at | datetime | 最后提交时间 |
| graded_at | datetime | 评分时间 |
| created_at | timestamp | 记录创建时间戳 |
| updated_at | timestamp | 记录更新时间戳 |

## student_answers_backup

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 答案备份记录ID |
| student_id | int | 学生ID |
| homework_id | int | 作业ID |
| question_id | int | 题目ID |
| question_type | enum('progressing','choice','judgment') | 题目类型 |
| answer_text | text | 文字答案备份 |
| choice_answer | varchar(10) | 选择答案例备份 |
| judgment_answer | tinyint(1) | 判断答案备份 |
| is_correct | tinyint(1) | 正确性备份 |
| score | decimal(5,2) | 得分备份 |
| teacher_comment | text | 教师评语备份 |
| status | enum('draft','submitted','graded') | 备份状态 |
| submit_count | int | 提交次数统计 |
| first_attempt_at | datetime | 首次尝试时间 |
| last_attempt_at | datetime | 最后尝试时间 |
| graded_at | datetime | 评分时间 |
| created_at | timestamp | 备份记录创建时间戳 |
| updated_at | timestamp | 备份记录更新时间戳 |

## student_classes

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 学生班级关联唯一标识符 |
| student_id | int | 学生ID |
| class_id | int | 班级ID |
| joined_at | timestamp | 学生加入班级时间戳 |

## student_zip_submissions

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | ZIP文件提交唯一标识符 |
| student_id | int | 提交学生ID |
| homework_id | int | 作业ID |
| question_id | int | 题目ID |
| zip_filename | varchar(255) | ZIP文件名 |
| zip_content | longblob | ZIP文件内容二进制数据 |
| file_size | int | 文件大小（字节） |
| language | varchar(20) | 编程语言 |
| extract_status | enum('pending','success','failed') | 文件解压状态 |
| validation_status | enum('pending','valid','invalid') | 文件验证状态 |
| evaluation_status | enum('pending','success','failed','error') | 评估状态 |
| is_correct | tinyint(1) | 是否正确 |
| score | decimal(5,2) | 分数 |
| evaluation_result | json | 评估结果详情 |
| error_message | text | 错误信息 |
| submit_time | datetime | 提交时间 |
| ip_address | varchar(45) | 提交IP地址 |
| user_agent | text | 用户代理信息 |
| created_at | timestamp | 记录创建时间戳 |
| updated_at | timestamp | 记录更新时间戳 |

## students

| 列名 | 类型 | 描述 |
|------|------|------|
| student_id | int | 学生用户唯一标识符 |
| username | varchar(50) | 学生登录用户名 |
| password | varchar(255) | 学生密码哈希值 |
| email | varchar(100) | 学生电子邮件地址 |
| telenum | varchar(20) | 学生联系电话号码 |
| created_at | timestamp | 学生账户创建时间戳 |
| updated_at | timestamp | 学生账户更新时间戳 |
| status | enum('active','inactive') | 学生账户状态 |

## teacher_courses

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 教师课程关联唯一标识符 |
| teacher_id | int | 教师ID |
| course_id | int | 课程ID |
| assigned_at | timestamp | 教师分配至课程的时间戳 |
| created_at | datetime | 关联创建日期时间（重复，疑似错误） |
| updated_at | datetime | 关联更新日期时间（重复，疑似错误） |

## teacher_student_answers

| 列名 | 类型 | 描述 |
|------|------|------|
| answer_id | int | 答案ID |
| student_id | int | 学生ID |
| student_name | varchar(50) | 学生姓名 |
| homework_id | int | 作业ID |
| homework_title | varchar(255) | 作业标题 |
| question_id | int | 题目ID |
| question_title | varchar(255) | 题目标题 |
| question_type | enum('progressing','choice','judgment') | 题目类型 |
| question_type_name | varchar(3) | 题目类型简称（如Prog、Cho、Jud） |
| answer_text | text | 学生答案文本 |
| choice_answer | varchar(10) | 选择答案 |
| judgment_answer | tinyint(1) | 判断答案 |
| is_correct | tinyint(1) | 是否正确 |
| score | decimal(5,2) | 得分 |
| status | enum('submitted','graded') | 状态 |
| teacher_comment | text | 教师评语 |
| submit_time | datetime | 提交时间 |
| graded_at | datetime | 评分时间 |
| deadline | date | 截止日期 |

## teachers

| 列名 | 类型 | 描述 |
|------|------|------|
| teacher_id | int | 教师用户唯一标识符 |
| username | varchar(50) | 教师登录用户名 |
| password | varchar(255) | 教师密码哈希值 |
| email | varchar(100) | 教师电子邮件地址 |
| telenum | varchar(20) | 教师联系电话号码 |
| created_at | timestamp | 教师账户创建时间戳 |
| updated_at | timestamp | 教师账户更新时间戳 |
| status | enum('active','inactive') | 教师账户状态 |

## zip_processing_logs

| 列名 | 类型 | 描述 |
|------|------|------|
| id | int | 处理日志唯一标识符 |
| zip_submission_id | int | 关联的ZIP提交ID |
| log_type | enum('info','warning','error') | 日志类型 |
| message | text | 日志消息内容 |
| log_time | timestamp | 日志记录时间戳 |