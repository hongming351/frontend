# 学生作业提交功能数据库设计

## 需求分析

需要支持以下功能：

1. 学生答题记录（支持三种题型：编程题、选择题、判断题）
2. 作业提交状态跟踪
3. 支持编程题多次提交和运行
4. 自动评分和人工评分
5. 作业完成度统计

## 数据库表设计

### 1. student_answers（学生答案表）

存储学生的答题记录，支持三种题型。

```sql
CREATE TABLE student_answers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    homework_id INT NOT NULL,
    question_id INT NOT NULL,
    question_type ENUM('progressing', 'choice', 'judgment') NOT NULL,

    -- 答案内容（根据题型存储不同格式）
    answer_text TEXT,                    -- 编程题代码答案
    choice_answer VARCHAR(10),           -- 选择题答案（A、B、C、D等）
    judgment_answer TINYINT(1),          -- 判断题答案（0-错误，1-正确）

    -- 评分信息
    is_correct TINYINT(1) DEFAULT NULL,  -- 是否正确（自动判分题型）
    score DECIMAL(5,2) DEFAULT NULL,     -- 得分
    teacher_comment TEXT,                -- 教师评语

    -- 状态信息
    status ENUM('draft', 'submitted', 'graded') DEFAULT 'draft',
    submit_count INT DEFAULT 0,          -- 提交次数（主要用于编程题）

    -- 时间信息
    first_attempt_at DATETIME,           -- 首次作答时间
    last_attempt_at DATETIME,            -- 最后作答时间
    graded_at DATETIME,                  -- 评分时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    UNIQUE KEY unique_answer (student_id, homework_id, question_id),
    INDEX idx_student_homework (student_id, homework_id),
    INDEX idx_question (question_id),
    INDEX idx_status (status),

    -- 外键约束
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (homework_id) REFERENCES homework_assignments(id) ON DELETE CASCADE
);
```

### 2. homework_submissions（作业提交表）

记录作业的整体提交状态。

```sql
CREATE TABLE homework_submissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    homework_id INT NOT NULL,

    -- 提交状态
    submit_status ENUM('draft', 'submitted', 'graded', 'returned') DEFAULT 'draft',
    submitted_at DATETIME,               -- 首次提交时间
    graded_at DATETIME,                  -- 评分完成时间

    -- 评分信息
    total_score DECIMAL(6,2) DEFAULT 0,  -- 作业总分
    auto_score DECIMAL(6,2) DEFAULT 0,   -- 自动评分部分得分
    manual_score DECIMAL(6,2) DEFAULT 0, -- 人工评分部分得分

    -- 完成统计
    total_questions INT DEFAULT 0,       -- 作业总题数
    answered_questions INT DEFAULT 0,    -- 已答题数
    correct_questions INT DEFAULT 0,     -- 正确题数

    -- 教师反馈
    teacher_comment TEXT,
    graded_by INT,                      -- 评分教师ID

    -- 时间信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- 索引
    UNIQUE KEY unique_submission (student_id, homework_id),
    INDEX idx_student (student_id),
    INDEX idx_homework (homework_id),
    INDEX idx_status (submit_status),
    INDEX idx_graded_by (graded_by),

    -- 外键约束
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (homework_id) REFERENCES homework_assignments(id) ON DELETE CASCADE,
    FOREIGN KEY (graded_by) REFERENCES teachers(teacher_id) ON DELETE SET NULL
);
```

### 3. programming_submissions（编程题提交历史表）

专门记录编程题的多次提交历史，用于分析学生解题过程。

```sql
CREATE TABLE programming_submissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    homework_id INT NOT NULL,
    question_id INT NOT NULL,

    -- 提交信息
    submission_code TEXT NOT NULL,       -- 提交的代码
    language VARCHAR(20) DEFAULT 'Python', -- 编程语言
    submit_time DATETIME NOT NULL,       -- 提交时间

    -- 运行结果
    run_status ENUM('pending', 'running', 'success', 'failed', 'timeout', 'error') DEFAULT 'pending',
    execution_time INT,                  -- 执行时间（毫秒）
    memory_usage INT,                    -- 内存使用（KB）

    -- 测试结果
    test_results JSON,                   -- 测试用例执行结果（JSON格式）
    passed_tests INT DEFAULT 0,          -- 通过的测试数
    total_tests INT DEFAULT 0,           -- 总测试数
    score DECIMAL(5,2) DEFAULT 0,        -- 本次提交得分

    -- 错误信息
    compile_error TEXT,                  -- 编译错误信息
    runtime_error TEXT,                  -- 运行时错误信息

    -- 其他信息
    ip_address VARCHAR(45),              -- 提交IP地址
    user_agent TEXT,                     -- 用户代理信息

    -- 时间信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 索引
    INDEX idx_student_question (student_id, question_id),
    INDEX idx_homework (homework_id),
    INDEX idx_submit_time (submit_time),
    INDEX idx_run_status (run_status),

    -- 外键约束
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (homework_id) REFERENCES homework_assignments(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES progressing_questions(progressing_questions_id) ON DELETE CASCADE
);
```

## 设计说明

### 1. student_answers表设计要点

- **灵活的答案存储**：使用三个字段分别存储不同题型的答案，避免了复杂的JSON存储和解析
- **状态管理**：通过status字段支持草稿、提交、已评分三种状态
- **自动评分支持**：is_correct字段用于客观题的自动评分
- **多次提交支持**：submit_count记录提交次数，主要用于编程题

### 2. homework_submissions表设计要点

- **整体状态跟踪**：记录作业的完整生命周期
- **评分分离**：区分自动评分和人工评分，便于统计分析
- **完成度统计**：提供作业完成情况的详细统计信息

### 3. programming_submissions表设计要点

- **历史记录**：保留每次编程题提交的完整记录
- **运行状态跟踪**：详细记录代码运行状态和结果
- **测试结果存储**：JSON格式存储详细的测试用例执行结果
- **性能监控**：记录执行时间和内存使用情况

## 业务流程

### 1. 学生答题流程

1. 学生开始答题 → 创建或更新student_answers记录（status='draft'）
2. 学生提交答案 → 更新status为'submitted'，记录提交时间
3. 系统自动评分（客观题）→ 更新is_correct和score字段
4. 教师人工评分（主观题）→ 更新score和teacher_comment

### 2. 作业提交流程

1. 学生完成所有题目后提交作业 → 创建homework_submissions记录
2. 系统计算总分和完成统计
3. 教师可以对需要人工评分的题目进行评分
4. 教师提交最终评分后，更新作业状态为'graded'

### 3. 编程题特殊流程

1. 学生可以多次提交代码
2. 每次提交都会记录到programming_submissions表
3. 系统自动运行测试用例并评分
4. 学生可以看到每次提交的结果和历史记录

## 扩展性考虑

1. **支持更多题型**：通过扩展question_type枚举和添加相应字段
2. **评分规则灵活性**：可以通过配置表来定义不同题型的评分规则
3. **批量操作**：支持教师批量评分和学生批量提交
4. **数据分析**：丰富的提交历史数据支持学习分析和统计

这个设计考虑了当前的需求，同时为未来扩展留出了空间。
