-- 创建密码重置验证码表
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    user_role ENUM('student', 'teacher', 'admin') NOT NULL,
    contact_type VARCHAR(20) NOT NULL,  -- 'email' 或 'telenum'
    contact_value VARCHAR(100) NOT NULL,
    verification_token VARCHAR(10) NOT NULL,  -- 6位验证码
    token_hash VARCHAR(64) NOT NULL,  -- 验证码的MD5哈希
    expires_at DATETIME NOT NULL,
    status ENUM('active', 'used', 'expired') DEFAULT 'active',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at DATETIME NULL,

    INDEX idx_username_role (username, user_role),
    INDEX idx_token_hash (token_hash),
    INDEX idx_contact (contact_type, contact_value),
    INDEX idx_expires_at (expires_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;