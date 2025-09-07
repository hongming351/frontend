import pymysql
from pymysql.cursors import DictCursor
from config import Config
import logging
import threading

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseManager, cls).__new__(cls)
                cls._instance.config = config or Config()
                cls._instance.connection_pool = None
                # 初始化连接池
                cls._instance._init_connection_pool()
            return cls._instance
    
    def _init_connection_pool(self):
        """初始化数据库连接池"""
        try:
            from pymysqlpool.pool import Pool
            self.connection_pool = Pool(
                host=self.config.MYSQL_HOST,
                user=self.config.MYSQL_USER,
                password=self.config.MYSQL_PASSWORD,
                database=self.config.MYSQL_DB,
                port=self.config.MYSQL_PORT,
                cursorclass=DictCursor,
                charset='utf8mb4',
                autocommit=True,
                max_size=10,  # 最大连接数
                min_size=2    # 最小连接数
            )
            logger.info("数据库连接池初始化成功")
        except ImportError:
            logger.warning("pymysqlpool未安装，使用单连接模式")
            self.connection_pool = None
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            self.connection_pool = None
    
    def get_connection(self):
        """获取数据库连接"""
        if self.connection_pool:
            try:
                return self.connection_pool.get_connection()
            except Exception as e:
                logger.error(f"从连接池获取连接失败: {e}")
                # 回退到单连接模式
                return self._create_single_connection()
        else:
            return self._create_single_connection()
    
    def _create_single_connection(self):
        """创建单个数据库连接"""
        try:
            connection = pymysql.connect(
                host=self.config.MYSQL_HOST,
                user=self.config.MYSQL_USER,
                password=self.config.MYSQL_PASSWORD,
                database=self.config.MYSQL_DB,
                port=self.config.MYSQL_PORT,
                cursorclass=DictCursor,
                charset='utf8mb4',
                autocommit=True
            )
            return connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def execute_query(self, sql, params=None):
        """执行查询语句"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    result = cursor.fetchall()
                    return result
        except Exception as e:
            logger.error(f"查询执行失败: {e}\nSQL: {sql}\n参数: {params}")
            raise
    
    def execute_update(self, sql, params=None):
        """执行更新语句"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info(f"执行SQL: {sql} 参数: {params}")
                    rows_affected = cursor.execute(sql, params or ())
                    conn.commit()
                    logger.info(f"影响行数: {rows_affected}")
                    return rows_affected
        except Exception as e:
            logger.error(f"更新执行失败: {e}\nSQL: {sql}\n参数: {params}")
            raise

    def execute_insert(self, sql, params=None):
        """执行插入语句并返回最后插入的ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info(f"执行SQL: {sql} 参数: {params}")
                    cursor.execute(sql, params or ())
                    conn.commit()
                    last_id = cursor.lastrowid
                    logger.info(f"插入成功，最后插入ID: {last_id}")
                    return last_id
        except Exception as e:
            logger.error(f"插入执行失败: {e}\nSQL: {sql}\n参数: {params}")
            raise

    def execute_many_update(self, sql, params_list):
        """批量执行更新语句"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info(f"批量执行SQL: {sql} 参数数量: {len(params_list)}")
                    rows_affected = cursor.executemany(sql, params_list)
                    conn.commit()
                    logger.info(f"批量影响行数: {rows_affected}")
                    return rows_affected
        except Exception as e:
            logger.error(f"批量更新执行失败: {e}\nSQL: {sql}\n参数数量: {len(params_list)}")
            raise
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            result = self.execute_query("SELECT 1 as test")
            return {"status": "success", "message": "数据库连接正常", "result": result}
        except Exception as e:
            return {"status": "error", "message": f"数据库连接失败: {str(e)}"}
    

# 全局数据库管理器实例
db = DatabaseManager()

def create_tables():
    """创建数据库表"""
    try:
        # 创建problems表（编程题）
        problems_sql = """
        CREATE TABLE IF NOT EXISTS problems (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            input_description TEXT,
            output_description TEXT,
            difficulty VARCHAR(20) DEFAULT '中等',
            tags VARCHAR(200),
            test_cases JSON,
            solution_idea TEXT,
            reference_code TEXT,
            language VARCHAR(50) DEFAULT 'Python',
            knowledge_points VARCHAR(200),
            created_by INT DEFAULT 1,
            is_ai_generated TINYINT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        # 创建choice_questions表（选择题）
        choice_sql = """
        CREATE TABLE IF NOT EXISTS choice_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            options JSON,
            correct_answer VARCHAR(10),
            solution_idea TEXT,
            difficulty VARCHAR(20) DEFAULT '中等',
            language VARCHAR(50) DEFAULT 'Python',
            knowledge_points VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        # 创建judgment_questions表（判断题）
        judgment_sql = """
        CREATE TABLE IF NOT EXISTS judgment_questions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            correct_answer BOOLEAN,
            solution_idea TEXT,
            difficulty VARCHAR(20) DEFAULT '中等',
            language VARCHAR(50) DEFAULT 'Python',
            knowledge_points VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        # 创建progressing_questions表（编程题）
        progressing_sql = """
        CREATE TABLE IF NOT EXISTS progressing_questions (
            progressing_questions_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            language VARCHAR(50) DEFAULT 'Python',
            description TEXT,
            difficulty VARCHAR(20) DEFAULT '中等',
            knowledge_points VARCHAR(200),
            input_description TEXT,
            output_description TEXT,
            solution_idea TEXT,
            reference_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        # 创建progressing_questions_test_cases表（编程题测试用例）
        test_cases_sql = """
        CREATE TABLE IF NOT EXISTS progressing_questions_test_cases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            progressing_questions_id INT NOT NULL,
            input TEXT,
            output TEXT,
            is_example BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (progressing_questions_id) REFERENCES progressing_questions(progressing_questions_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        # 执行建表语句
        db.execute_update(problems_sql)
        db.execute_update(choice_sql)
        db.execute_update(judgment_sql)
        db.execute_update(progressing_sql)
        db.execute_update(test_cases_sql)

        logger.info("数据库表创建成功")
        return True

    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        return False

def init_database():
    """初始化数据库"""
    try:
        # 测试连接
        result = db.test_connection()
        if result['status'] == 'success':
            # 连接成功后创建表
            if create_tables():
                logger.info("数据库初始化成功")
                return True
            else:
                logger.error("数据库表创建失败")
                return False
        else:
            logger.error(f"数据库初始化失败: {result['message']}")
            return False
    except Exception as e:
        logger.error(f"数据库初始化异常: {e}")
        return False
