# 在线测评系统 (OLJudge)

一个基于 Flask 的在线编程测评系统，支持教师、学生和管理员三种角色，具备AI题目生成功能。

## ✨ 核心功能

- 🔐 多角色用户系统（教师、学生、管理员）
- 🤖 AI题目自动生成（DeepSeek API集成）
- 📚 多课程多班级管理系统
- 💻 在线代码编辑和提交
- 📊 学习进度统计和数据分析
- 📱 响应式设计，支持移动端

## 🛠️ 技术栈

- **后端**: Flask (Python)
- **前端**: HTML5, CSS3, JavaScript
- **数据库**: MySQL (PyMySQL)
- **AI集成**: DeepSeek API
- **样式**: 自定义CSS + Font Awesome图标

## 📁 项目结构

```
frontend/
├── app.py                 # Flask应用工厂和主路由
├── run.py                 # 应用启动脚本（推荐使用）
├── config.py              # 应用配置
├── database.py            # 数据库操作封装
├── requirements.txt       # Python依赖
├── README.md             # 项目说明
├── .gitignore            # Git忽略文件
├── env.example           # 环境变量示例
├── api/                  # API蓝图
│   ├── ai.py             # AI题目生成API
│   ├── classes.py        # 班级管理API
│   ├── courses.py        # 课程管理API
│   ├── problems.py       # 题目管理API
│   ├── students.py       # 学生管理API
│   └── teachers.py       # 教师管理API
├── model/                # 数据模型
│   ├── check_login.py    # 登录验证
│   └── check_regist.py   # 注册验证
├── static/               # 静态文件
│   ├── css/              # 样式文件
│   ├── js/               # JavaScript文件
│   └── images/           # 图片资源
└── templates/            # HTML模板
    ├── login.html        # 登录页面
    ├── register.html     # 注册页面
    ├── admin/            # 管理员页面
    ├── student/          # 学生页面
    └── teacher/          # 教师页面
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `env.example` 为 `.env` 并配置：

```bash
DEEPSEEK_API_KEY=your-deepseek-api-key-here
SECRET_KEY=your-secret-key-here
```

### 3. 配置数据库

在 `config.py` 中配置数据库连接信息：

```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'your-password'
MYSQL_DB = 'oljudge'
```

### 4. 运行应用

```bash
# 使用推荐的启动脚本
python run.py

# 或者直接运行
python app.py
```

### 5. 访问系统

打开浏览器访问 `http://localhost:5000`

## 🎯 用户角色

### 👨‍🏫 教师

- 创建和管理课程、班级
- 使用AI生成编程题目
- 查看学生提交情况和进度
- 管理班级学生

### 👨‍🎓 学生

- 加入课程班级学习
- 练习编程题目并提交代码
- 查看个人学习进度和统计

### 👨‍💼 管理员

- 系统用户管理
- 系统配置和维护
- 数据统计和报表生成

## 🤖 AI功能

系统集成了DeepSeek AI API，教师可以：

- 自动生成各种难度的编程题目
- 支持多种编程语言（Python、C++等）
- 自动解析和保存题目到数据库
- 灵活的提示词系统定制题目内容

## 📝 开发说明

- 使用Flask蓝图进行模块化开发
- 前后端分离的API设计
- 响应式前端设计
- 完善的错误处理和日志记录

## 📄 许可证

MIT License
