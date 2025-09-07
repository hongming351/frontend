document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.register-form');
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    const username = document.getElementById('username');
    const email = document.getElementById('email');
    const telenum = document.getElementById('telenum');
    
    // 手机号验证 (11位数字)
    function validatePhoneNumber(phone) {
        return /^1[3-9]\d{9}$/.test(phone);
    }
    
    // 邮箱格式验证 (必须包含@和.)
    function validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
    
    // 密码强度检查
    function checkPasswordStrength(password) {
        let strength = 0;
        let requirements = [];
        
        if (password.length >= 8) {
            strength++;
            requirements.push('长度≥8位');
        }
        if (/[a-z]/.test(password)) {
            strength++;
            requirements.push('包含小写字母');
        }
        if (/[A-Z]/.test(password)) {
            strength++;
            requirements.push('包含大写字母');
        }
        if (/[0-9]/.test(password)) {
            strength++;
            requirements.push('包含数字');
        }
        if (/[^A-Za-z0-9]/.test(password)) {
            strength++;
            requirements.push('包含特殊字符');
        }
        
        return { strength, requirements };
    }
    
    // 实时手机号验证
    telenum.addEventListener('input', function() {
        const existingTip = this.parentNode.querySelector('.field-tip');
        if (existingTip) {
            existingTip.remove();
        }
        
        if (this.value.length > 0) {
            const tip = document.createElement('div');
            if (validatePhoneNumber(this.value)) {
                tip.className = 'field-tip success';
                tip.textContent = '✓ 手机号格式正确';
            } else {
                tip.className = 'field-tip error';
                tip.textContent = '✗ 请输入11位有效手机号';
            }
            this.parentNode.appendChild(tip);
        }
    });
    
    // 实时邮箱验证
    email.addEventListener('input', function() {
        const existingTip = this.parentNode.querySelector('.field-tip');
        if (existingTip) {
            existingTip.remove();
        }
        
        if (this.value.length > 0) {
            const tip = document.createElement('div');
            if (validateEmail(this.value)) {
                tip.className = 'field-tip success';
                tip.textContent = '✓ 邮箱格式正确';
            } else {
                tip.className = 'field-tip error';
                tip.textContent = '✗ 请输入有效的邮箱地址';
            }
            this.parentNode.appendChild(tip);
        }
    });
    
    // 实时密码强度显示
    password.addEventListener('input', function() {
        const { strength, requirements } = checkPasswordStrength(this.value);
        let strengthText = '';
        let strengthClass = '';
        
        if (strength < 2) {
            strengthText = '弱';
            strengthClass = 'weak';
        } else if (strength < 4) {
            strengthText = '中等';
            strengthClass = 'medium';
        } else {
            strengthText = '强';
            strengthClass = 'strong';
        }
        
        // 移除之前的强度提示
        const existingTip = document.querySelector('.password-strength');
        if (existingTip) {
            existingTip.remove();
        }
        
        // 添加新的强度提示
        if (this.value.length > 0) {
            const tip = document.createElement('div');
            tip.className = `password-strength ${strengthClass}`;
            
            let tipContent = `密码强度: ${strengthText}`;
            if (requirements.length > 0) {
                tipContent += ` (${requirements.join(', ')})`;
            }
            tip.textContent = tipContent;
            this.parentNode.appendChild(tip);
        }
    });
    
    // 实时密码确认检查
    confirmPassword.addEventListener('input', function() {
        const existingTip = document.querySelector('.password-confirm-tip');
        if (existingTip) {
            existingTip.remove();
        }
        
        if (this.value.length > 0 && this.value !== password.value) {
            const tip = document.createElement('div');
            tip.className = 'password-confirm-tip error';
            tip.textContent = '两次输入的密码不一致';
            this.parentNode.appendChild(tip);
        }
    });
    
    // 表单提交验证
    form.addEventListener('submit', function(e) {
        let isValid = true;
        
        // 清除之前的错误提示
        const existingTips = document.querySelectorAll('.password-strength, .password-confirm-tip, .field-tip');
        existingTips.forEach(tip => tip.remove());
        
        // 检查用户名长度
        if (username.value.length < 3) {
            showError(username, '用户名至少需要3个字符');
            isValid = false;
        }
        
        // 检查手机号格式
        if (telenum.value && !validatePhoneNumber(telenum.value)) {
            showError(telenum, '请输入11位有效手机号');
            isValid = false;
        }
        
        // 检查邮箱格式（如果填写了邮箱）
        if (email.value && !validateEmail(email.value)) {
            showError(email, '请输入有效的邮箱地址（包含@和.）');
            isValid = false;
        }
        
        // 检查密码长度
        if (password.value.length < 6) {
            showError(password, '密码至少需要6个字符');
            isValid = false;
        }
        
        // 检查密码强度（至少中等强度）
        const { strength } = checkPasswordStrength(password.value);
        if (strength < 2) {
            showError(password, '密码强度太弱，请包含字母和数字');
            isValid = false;
        }
        
        // 检查密码确认
        if (password.value !== confirmPassword.value) {
            showError(confirmPassword, '两次输入的密码不一致');
            isValid = false;
        }
        
        if (!isValid) {
            e.preventDefault();
        }
    });
    
    // 显示错误信息
    function showError(input, message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        input.parentNode.appendChild(errorDiv);
        input.style.borderColor = '#e74c3c';
    }
    
    // 输入框获得焦点时清除错误状态
    const inputs = form.querySelectorAll('input, select');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.style.borderColor = '';
            const errorDiv = this.parentNode.querySelector('.field-error');
            if (errorDiv) {
                errorDiv.remove();
            }
        });
    });
});
