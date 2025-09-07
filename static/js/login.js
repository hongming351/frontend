// 登录页面JavaScript逻辑

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.querySelector('.login-form');
    const roleSelect = document.getElementById('role');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const captchaInput = document.getElementById('captcha');
    
    // 表单验证
    function validateForm() {
        let isValid = true;
        
        // 验证身份选择
        if (!roleSelect.value) {
            showError(roleSelect, '请选择身份');
            isValid = false;
        } else {
            removeError(roleSelect);
        }
        
        // 验证用户名
        if (!usernameInput.value.trim()) {
            showError(usernameInput, '请输入用户名');
            isValid = false;
        } else {
            removeError(usernameInput);
        }
        
        // 验证密码
        if (!passwordInput.value) {
            showError(passwordInput, '请输入密码');
            isValid = false;
        } else if (passwordInput.value.length < 6) {
            showError(passwordInput, '密码长度至少6位');
            isValid = false;
        } else {
            removeError(passwordInput);
        }
        
        // 验证验证码
        if (!captchaInput.value.trim()) {
            showError(captchaInput, '请输入验证码');
            isValid = false;
        } else {
            removeError(captchaInput);
        }
        
        return isValid;
    }
    
    // 显示错误信息
    function showError(input, message) {
        removeError(input);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.color = 'var(--danger-color)';
        errorDiv.style.fontSize = '12px';
        errorDiv.style.marginTop = '4px';
        
        input.parentNode.appendChild(errorDiv);
        input.style.borderColor = 'var(--danger-color)';
    }
    
    // 移除错误信息
    function removeError(input) {
        const errorDiv = input.parentNode.querySelector('.error-message');
        if (errorDiv) {
            errorDiv.remove();
        }
        input.style.borderColor = '';
    }
    
    // 表单提交处理
    loginForm.addEventListener('submit', function(e) {
        if (!validateForm()) {
            e.preventDefault();
        } else {
            // 显示加载状态
            const submitBtn = loginForm.querySelector('.login-btn');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = '登录中...';
            submitBtn.disabled = true;
        }
    });
    
    // 实时验证
    roleSelect.addEventListener('change', function() {
        if (this.value) {
            removeError(this);
        }
    });
    
    usernameInput.addEventListener('blur', function() {
        if (!this.value.trim()) {
            showError(this, '请输入用户名');
        } else {
            removeError(this);
        }
    });
    
    passwordInput.addEventListener('blur', function() {
        if (!this.value) {
            showError(this, '请输入密码');
        } else if (this.value.length < 6) {
            showError(this, '密码长度至少6位');
        } else {
            removeError(this);
        }
    });
    
    captchaInput.addEventListener('blur', function() {
        if (!this.value.trim()) {
            showError(this, '请输入验证码');
        } else {
            removeError(this);
        }
    });
    
    // 输入时移除错误提示
    [roleSelect, usernameInput, passwordInput, captchaInput].forEach(input => {
        input.addEventListener('input', function() {
            removeError(this);
        });
    });
    
    // 记住密码功能
    const rememberCheckbox = document.querySelector('input[name="remember"]');
    const savedUsername = localStorage.getItem('savedUsername');
    const savedRole = localStorage.getItem('savedRole');
    
    if (savedUsername && savedRole) {
        usernameInput.value = savedUsername;
        roleSelect.value = savedRole;
        rememberCheckbox.checked = true;
    }
    
    rememberCheckbox.addEventListener('change', function() {
        if (this.checked) {
            localStorage.setItem('savedUsername', usernameInput.value);
            localStorage.setItem('savedRole', roleSelect.value);
        } else {
            localStorage.removeItem('savedUsername');
            localStorage.removeItem('savedRole');
        }
    });
    
    // 自动保存功能
    usernameInput.addEventListener('input', function() {
        if (rememberCheckbox.checked) {
            localStorage.setItem('savedUsername', this.value);
        }
    });
    
    roleSelect.addEventListener('change', function() {
        if (rememberCheckbox.checked) {
            localStorage.setItem('savedRole', this.value);
        }
    });
});
