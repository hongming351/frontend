"""
在线测评系统启动脚本
"""

import os
import sys
from app import create_app

def main():
    """主函数"""
    # 设置环境变量
    os.environ.setdefault('FLASK_ENV', 'development')
    
    # 创建应用实例
    app = create_app()
    
    # 启动应用
    try:
        print("🚀 正在启动在线测评系统...")
        print(f"📁 工作目录: {os.getcwd()}")
        print(f"🌍 环境: {os.environ.get('FLASK_ENV', 'development')}")
        print(f"🔧 调试模式: {app.config['DEBUG']}")
        print("✅ 应用启动成功！")
        print("🌐 访问地址: http://localhost:5000")
        print("⏹️  按 Ctrl+C 停止应用")
        print("-" * 50)
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=app.config['DEBUG']
        )
        
    except KeyboardInterrupt:
        print("\n⏹️  应用已停止")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()