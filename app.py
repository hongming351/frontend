from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, make_response
import os
from config import config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)

    # 获取配置
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 初始化数据库
    from database import init_database
    if init_database():
        logger.info("数据库初始化完成")
    else:
        logger.error("数据库初始化失败")

    return app

app = create_app()

@app.after_request
def after_request(response):
    # 允许多个origin
    allowed_origins = ['http://localhost:5000', 'http://127.0.0.1:5000']
    origin = request.headers.get('Origin')

    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')

    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-CSRFToken')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# 添加静态文件路由
@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件路由"""
    return send_from_directory('static', filename)

@app.route('/')
def index():
    """首页 - 重定向到登录页面"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        identity = request.form.get('role')  # 前端表单仍使用role字段名
        username = request.form.get('username')
        password = request.form.get('password')
        captcha = request.form.get('captcha')
        
        logger.info(f"登录尝试: 身份={identity}, 用户名={username}")
        print(f"DEBUG: 收到登录请求 - 身份:{identity}, 用户名:{username}, 验证码:{captcha}")
        
        # 验证验证码（这里简化处理，实际应该验证验证码）
        if not captcha:
            print("DEBUG: 验证码为空")
            flash('请输入验证码', 'error')
            return render_template('login.html')
        
        # 实际用户验证
        if identity and username and password:
            from model.check_login import is_existed
            user = is_existed(username, password, identity)
            
            if not user:
                flash('用户名或密码错误', 'error')
                logger.warning(f"用户 {username} 登录失败")
                return render_template('login.html')
            
            # 设置session
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['identity'] = identity  # 使用前端原始角色值
            
            # 确保模板文件存在
            template_path = f"{identity}/dashboard.html"
            if not os.path.exists(os.path.join('templates', template_path)):
                flash('系统配置错误，请联系管理员', 'error')
                logger.error(f"模板文件不存在: {template_path}")
                return render_template('login.html')
            
            logger.info(f"用户 {username} 登录成功，身份：{identity}")
            
            # 根据角色跳转到对应页面
            try:
                if identity == 'teacher':
                    print("DEBUG: 渲染教师页面")
                    return render_template('teacher/dashboard.html', user=user)
                elif identity == 'student':
                    print("DEBUG: 渲染学生页面")
                    return render_template('student/dashboard.html', user=user)
                elif identity == 'admin':
                    print("DEBUG: 渲染管理员页面")
                    return render_template('admin/dashboard.html', user=user)
                else:
                    print(f"DEBUG: 无效身份: {identity}")
                    flash('无效的身份选择', 'error')
                    return render_template('login.html')
            except Exception as e:
                print(f"DEBUG: 渲染页面时出错: {e}")
                logger.error(f"页面渲染失败: {e}")
                flash('页面加载失败', 'error')
                return render_template('login.html')
        else:
            print(f"DEBUG: 登录信息不完整 - 身份:{identity}, 用户名:{username}, 密码:{'已填写' if password else '未填写'}")
            flash('请填写完整的登录信息', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """退出登录"""
    session.clear()
    flash('已成功退出登录', 'success')
    return redirect(url_for('login'))

@app.route('/forgot-password')
def forgot_password():
    """忘记密码页面"""
    return render_template('forgot_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username')
        identity = request.form.get('role')  # 前端表单仍使用role字段名
        email = request.form.get('email')
        telenum = request.form.get('telenum')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证必填字段
        if not all([username, identity, telenum, password, confirm_password]):
            flash('请填写所有必填字段', 'error')
            return render_template('register.html')
            
        # 验证密码匹配
        if password != confirm_password:
            flash('两次输入的密码不匹配', 'error')
            return render_template('register.html')
            
        # 调用实际的用户注册逻辑
        from model.check_regist import add_user
        result = add_user(username, password, identity, telenum, email)
        
        if result['success']:
            flash(result['message'], 'success')
            return redirect(url_for('login'))
        else:
            flash(result['message'], 'error')
            return render_template('register.html')
    
    return render_template('register.html')


@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """获取仪表盘统计数据"""
    try:
        from database import db
        
        # 获取教师数量
        teachers_sql = "SELECT COUNT(*) as count FROM teachers"
        teachers_count = db.execute_query(teachers_sql)[0]['count']
        
        # 获取学生数量
        students_sql = "SELECT COUNT(*) as count FROM students"
        students_count = db.execute_query(students_sql)[0]['count']
        
        # 获取管理员数量
        admins_sql = "SELECT COUNT(*) as count FROM admins"
        admins_count = db.execute_query(admins_sql)[0]['count']
        
        # 计算总用户数
        total_users = teachers_count + students_count + admins_count
        
        return jsonify({
            "success": True,
            "data": {
                "total_users": total_users,
                "teachers_count": teachers_count,
                "students_count": students_count,
                "admins_count": admins_count
            }
        })
    except Exception as e:
        logger.error(f"获取仪表盘统计数据失败: {e}")
        return jsonify({"success": False, "message": "获取统计数据失败"}), 500

@app.route('/api/teacher/profile', methods=['GET'])
def get_teacher_profile():
    """获取当前教师个人资料"""
    try:
        # 检查教师会话
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False, 
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401
        
        from database import db
        teacher_id = session['user_id']
        
        # 获取教师详细信息
        sql = """
            SELECT teacher_id as id, username, email, telenum, status, created_at
            FROM teachers 
            WHERE teacher_id = %s
        """
        teacher = db.execute_query(sql, (teacher_id,))
        
        if teacher:
            return jsonify({"success": True, "data": teacher[0]})
        return jsonify({"success": False, "message": "教师信息不存在"}), 404
    except Exception as e:
        logger.error(f"获取教师个人资料失败: {e}")
        return jsonify({"success": False, "message": "获取个人资料失败"}), 500

@app.route('/api/teacher/profile', methods=['PUT'])
def update_teacher_profile():
    """更新当前教师个人资料"""
    try:
        # 检查教师会话
        if 'identity' not in session or session['identity'] != 'teacher':
            return jsonify({
                "success": False, 
                "message": "需要教师权限",
                "redirect": "/login"
            }), 401
        
        from database import db
        teacher_id = session['user_id']
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无更新数据"}), 400
        
        # 检查教师状态是否为"active"
        check_status_sql = "SELECT status FROM teachers WHERE teacher_id = %s"
        teacher_status = db.execute_query(check_status_sql, (teacher_id,))
        
        if not teacher_status or teacher_status[0]['status'] != 'active':
            return jsonify({"success": False, "message": "只有状态为'active'的教师才能修改个人资料"}), 403
        
        # 构建更新字段
        update_fields = []
        update_values = []
        
        allowed_fields = ['email', 'telenum']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                update_values.append(data[field])
        
        if not update_fields:
            return jsonify({"success": False, "message": "没有有效的更新字段"}), 400
        
        # 添加教师ID到参数列表
        update_values.append(teacher_id)
        
        # 执行更新
        update_sql = f"UPDATE teachers SET {', '.join(update_fields)} WHERE teacher_id = %s"
        affected = db.execute_update(update_sql, update_values)
        
        if affected > 0:
            logger.info(f"教师 {teacher_id} 个人资料更新成功")
            return jsonify({"success": True, "message": "个人资料更新成功"})
        
        return jsonify({"success": False, "message": "个人资料更新失败"}), 400
        
    except Exception as e:
        logger.error(f"更新教师个人资料失败: {e}")
        return jsonify({"success": False, "message": "更新个人资料失败"}), 500

@app.route('/student/profile')
def student_profile():
    """学生个人信息页面"""
    # 检查学生会话
    if 'identity' not in session or session['identity'] != 'student':
        flash('请先登录学生账户', 'error')
        return redirect(url_for('login'))

    # 从数据库获取完整的用户信息
    from database import db
    student_id = session.get('user_id')

    sql = """
        SELECT student_id as id, username, email, telenum, status, created_at
        FROM students
        WHERE student_id = %s
    """
    user_data = db.execute_query(sql, (student_id,))

    if not user_data:
        flash('用户信息不存在', 'error')
        return redirect(url_for('login'))

    user = user_data[0]

    return render_template('student/profile.html', user=user)

@app.route('/student/dashboard')
def student_dashboard():
    """学生仪表盘页面"""
    # 检查学生会话
    if 'identity' not in session or session['identity'] != 'student':
        flash('请先登录学生账户', 'error')
        return redirect(url_for('login'))

    # 获取用户信息
    from database import db
    student_id = session.get('user_id')

    sql = """
        SELECT student_id as id, username, email, telenum, status, created_at
        FROM students
        WHERE student_id = %s
    """
    user_data = db.execute_query(sql, (student_id,))

    if not user_data:
        flash('用户信息不存在', 'error')
        return redirect(url_for('login'))

    user = user_data[0]

    return render_template('student/dashboard.html', user=user)

@app.route('/student/course')
@app.route('/student/course_detail')
def student_course_detail():
    """学生课程详情页面"""
    # 检查学生会话
    if 'identity' not in session or session['identity'] != 'student':
        flash('请先登录学生账户', 'error')
        return redirect(url_for('login'))

    # 获取用户信息
    from database import db
    student_id = session.get('user_id')

    sql = """
        SELECT student_id as id, username, email, telenum, status, created_at
        FROM students
        WHERE student_id = %s
    """
    user_data = db.execute_query(sql, (student_id,))

    if not user_data:
        flash('用户信息不存在', 'error')
        return redirect(url_for('login'))

    user = user_data[0]

    return render_template('student/course_detail.html', user=user)

@app.route('/student/problem/solve')
def student_problem_solve():
    """学生答题页面"""
    # 检查学生会话
    if 'identity' not in session or session['identity'] != 'student':
        flash('请先登录学生账户', 'error')
        return redirect(url_for('login'))

    # 获取用户信息
    from database import db
    student_id = session.get('user_id')

    sql = """
        SELECT student_id as id, username, email, telenum, status, created_at
        FROM students
        WHERE student_id = %s
    """
    user_data = db.execute_query(sql, (student_id,))

    if not user_data:
        flash('用户信息不存在', 'error')
        return redirect(url_for('login'))

    user = user_data[0]

    return render_template('student/problem_solve.html', user=user)

# 注册API蓝图
from api.courses import courses_bp
from api.classes import classes_bp
from api.teachers import teachers_bp
from api.students import students_bp
from api.problems import problems_bp
from api.question_bank import question_bank_bp
from api.ai import ai_bp
from api.ai_problems import ai_problems_bp
from api.password_reset import password_reset_bp

app.register_blueprint(courses_bp)
app.register_blueprint(classes_bp)
app.register_blueprint(teachers_bp)
app.register_blueprint(students_bp)
app.register_blueprint(problems_bp)
app.register_blueprint(question_bank_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(ai_problems_bp)
app.register_blueprint(password_reset_bp)

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])
