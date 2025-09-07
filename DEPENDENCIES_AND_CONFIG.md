# 项目依赖和环境配置指南

## 📋 项目概述

这是一个基于 Flask 的在线编程测评系统 (OLJudge)，支持教师、学生和管理员三种角色，支持 AI 题目生成功能。项目使用 Python Flask 框架构建，具有多角色用户系统、在线编程题提交、学习进度统计等功能。

## 🛠️ Python 依赖

安装所有必需的 Python 包：

```bash
pip install -r requirements.txt
```

**核心依赖列表**：

| 包名 | 版本 | 用途 |
|------|------|------|
| Flask | 2.3.3 | Web 框架 |
| PyMySQL | 1.1.0 | MySQL 数据库连接 |
| Werkzeug | 2.3.7 | WSGI 工具包 |
| pymysqlpool | 0.3.4 | MySQL 连接池 |
| requests | 2.31.0 | HTTP 请求库 |
| python-dotenv | 1.0.0 | 环境变量管理 |

## 🗄️ 数据库配置

### MySQL 数据库要求

- **版本要求**: MySQL 5.7 或更高版本
- **字符集**: UTF-8
- **默认数据库名**: `oljudge`

### 数据库配置选项

```env
# .env 文件中配置
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=oljudge
DB_PORT=3306
```

### 数据库初始化

项目根目录包含数据库脚本，请先运行以下文件初始化数据库：

- `create_password_reset_table.sql` - 密码重置相关表
- `fix_table_enums.py` - 修复表枚举类型
- `create_password_reset_db.py` - 创建数据库

## ⚙️ 环境配置

### 必需的环境文件

1. **复制示例文件**：

```bash
cp .env.example .env
cp env.example .env
```

2. **编辑 `.env` 文件** 并填入实际值：

```env
# Flask 应用配置
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# DeepSeek AI API 配置
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# GCC 编译器路径（Windows）
GPP_PATH=D:\mingw64\bin\g++.exe

# 邮件服务配置（可选）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your_email@qq.com
SMTP_PASSWORD=your_email_password

# 阿里云短信服务（可选）
SMS_ENABLED=true
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_SMTP_SIGN_NAME=Your_App_Name
ALIYUN_SMTP_TEMPLATE_CODE=SMS_123456789
```

## 🤖 AI 功能配置

### DeepSeek API 配置

1. 获取 API Key：
   - 访问 [DeepSeek API](https://platform.deepseek.com/)
   - 注册账号并创建 API Key

2. 配置环境变量：

```env
DEEPSEEK_API_KEY=your_actual_api_key
```

功能特点：

- 支持多种编程语言题目生成
- AI 自动解析和保存题目
- 灵活的提示词定制

## 📱 短信服务配置（可选）

### 阿里云短信服务

**前置要求**：

- 阿里云账号及实名认证
- 开通短信服务
- 账户充值（建议 10-20 元测试）

**配置步骤**：

1. 创建 AccessKey：
   - 访问 [阿里云 API 密钥管理](https://usercenter.console.aliyun.com/#/manage/ak)
   - 生成 AccessKey ID 和 Secret

2. 申请签名和模板：
   - 短信签名：您的应用名称
   - 模板内容：`您的验证码为：${code}，有效期${time}分钟，请及时输入。`

3. 配置环境变量（见上方示例）

**费用说明**：

- 验证码单条：约 0.045 元
- 可免费试用 100 条

## 📧 邮件服务配置（可选）

### SMTP 配置示例

```env
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your_qq_email@qq.com
SMTP_PASSWORD=your_email_authorization_code
SMTP_FROM_EMAIL=your_qq_email@qq.com
```

注意：QQ 邮箱需要申请应用专属密码。

## 🔧 系统要求

### 硬件要求

- RAM：至少 2GB
- 磁盘空间：500MB 以上

### 软件要求

- **Python**: 3.7+
- **操作系统**:
  - Linux (推荐)
  - macOS
  - Windows (需配置 GCC)
- **GCC 编译器**: 用于 C++ 代码执行
  - Linux/Mac: 通常预装
  - Windows: 安装 MinGW64 或 MSVC

### Windows 额外配置

如果在 Windows 上运行 C++ 代码，需要安装 GCC：

1. 下载 MinGW64：<https://sourceforge.net/projects/mingw-w64/>
2. 配置环境变量 `GPP_PATH` 指向 `g++.exe` 路径
3. 或者配置系统 PATH 环境变量

## 🚀 快速启动

### 标准启动方式

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（编辑 .env 文件）

# 3. 初始化数据库
python create_password_reset_db.py
python fix_table_enums.py

# 4. 启动应用
python run.py
```

### 开发模式启动

```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

### 访问应用

启动后访问：`http://localhost:5000`

## 🧪 测试配置

### 基本功能测试

```bash
# 测试基本应用运行
python test_simple.py

# 测试密码重置功能
python test_password_reset.py

# 测试阿里云短信服务
python sms_aliyun_config.py

# 测试数据库连接
python test_validate.py
```

### 手动测试步骤

1. 启动应用
2. 访问注册页面测试用户注册
3. 测试登录功能
4. 如果配置了短信服务，测试忘记密码功能

## 🔍 常见问题

### 数据库连接错误

- 检查 MySQL 服务是否运行
- 确认用户名、密码、数据库名正确
- 检查网络连接（如果是远程数据库）

### AI 功能不工作

- 确认 DeepSeek API Key 有效
- 检查网络连接
- 查看控制台错误日志

### 短信发送失败

- 确认阿里云配置正确
- 检查签名和模板是否审核通过
- 查看阿里云控制台的发送记录

### C++ 编译错误（Windows）

- 确认 GCC/MinGW64 已正确安装
- 检查 `GPP_PATH` 环境变量
- 确保系统 PATH 包含编译器路径

## 📚 相关文档

- [README.md](./README.md) - 项目主要文档
- [ALIYUN_SMS_SETUP_GUIDE.md](./ALIYUN_SMS_SETUP_GUIDE.md) - 阿里云短信详细配置
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - 实现总结
- [database_design_student_submission.md](./database_design_student_submission.md) - 数据库设计文档

## 📞 技术支持

遇到配置问题时请：

1. 检查控制台输出的错误信息
2. 确认所有环境变量配置正确
3. 查看相关配置文件注释说明
4. 参考项目的 testing 脚本验证配置

---

配置完成后，即可开始使用在线编程测评系统。
