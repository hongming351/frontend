import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""

    # Flask 配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    # Session配置 - 修复跨域session问题
    SESSION_COOKIE_SAMESITE = 'None'  # 允许跨域cookie
    SESSION_COOKIE_SECURE = False     # 开发环境设为False
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1小时过期

    # 数据库配置
    MYSQL_HOST = os.environ.get('DB_HOST', 'localhost')
    MYSQL_USER = os.environ.get('DB_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('DB_PASSWORD', '666666')  # 使用您之前的密码
    MYSQL_DB = os.environ.get('DB_NAME', 'oljudge')
    MYSQL_PORT = int(os.environ.get('DB_PORT', 3306))

    # DeepSeek AI API 配置
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', 'your-deepseek-api-key-here')
    DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

    # GCC编译器路径配置
    GPP_PATH = os.environ.get('GPP_PATH', 'g++')

    # 邮件配置
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.qq.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', 'your_email@qq.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'your_email_password')
    SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', 'your_email@qq.com')

    # 短信配置（支持阿里云SMS）
    SMS_ENABLED = os.environ.get('SMS_ENABLED', 'False').lower() == 'true'
    SMS_PROVIDER = os.environ.get('SMS_PROVIDER', 'aliyun')  # aliyun, tencent, etc.

    # 阿里云SMS配置
    SMS_API_KEY = os.environ.get('ALIYUN_ACCESS_KEY_ID', '')     # AccessKey ID
    SMS_SECRET = os.environ.get('ALIYUN_ACCESS_KEY_SECRET', '')  # AccessKey Secret
    SMS_SIGN_NAME = os.environ.get('ALIYUN_SMTP_SIGN_NAME', '您的应用名称')  # 短信签名
    SMS_TEMPLATE_CODE = os.environ.get('ALIYUN_SMTP_TEMPLATE_CODE', 'SMS_123456789')  # 模板ID

    # 兼容旧配置
    SMS_API_URL = os.environ.get('SMS_API_URL', 'https://dysmsapi.aliyuncs.com/')

    # 应用配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB 最大文件上传
    UPLOAD_FOLDER = 'uploads'

    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

    # 开发环境Session配置 - 使用Lax以支持HTTP
    SESSION_COOKIE_SAMESITE = 'Lax'  # 开发环境使用Lax，支持HTTP

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

    # 生产环境必须设置安全的密钥
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production')

    # 生产环境Session配置
    SESSION_COOKIE_SECURE = True  # 生产环境必须使用HTTPS

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    MYSQL_DB = 'oljudge_test'

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
