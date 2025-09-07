// 忘记密码功能JavaScript
let currentStep = 1;
let selectedMethod = '';
let contactValue = '';
let countdownInterval;

function goBack() {
    window.history.back();
}

function goToLogin() {
    window.location.href = '/login';
}

// 第一步：选择联系方式
document.addEventListener('DOMContentLoaded', function() {
    // 为验证方式选项添加点击事件
    const methodOptions = document.querySelectorAll('.method-option');
    methodOptions.forEach(option => {
        option.addEventListener('click', function() {
            const method = this.dataset.method;

            // 清除其他选项的选中状态
            methodOptions.forEach(opt => opt.classList.remove('selected'));
            // 设置当前选项为选中状态
            this.classList.add('selected');

            selectedMethod = method;
            document.getElementById('selected-method').value = method;

            // 显示联系方式输入框
            showContactInput(method);
        });
    });

    // 为验证码输入框添加自动跳转功能
    const codeInputs = document.querySelectorAll('.code-input');
    codeInputs.forEach((input, index) => {
        input.addEventListener('input', function() {
            if (this.value.length >= 1 && index < codeInputs.length - 1) {
                codeInputs[index + 1].focus();
            }
        });

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && this.value.length === 0 && index > 0) {
                codeInputs[index - 1].focus();
            }
        });
    });
});

function showContactInput(method) {
    const contactInput = document.getElementById('contact-input');
    const contactLabel = document.getElementById('contact-label');
    const contactValueInput = document.getElementById('contact-value');

    contactInput.style.display = 'block';
    contactValueInput.placeholder = method === 'email' ?
        '请输入邮箱地址' : '请输入手机号码';
    contactValueInput.type = method === 'email' ? 'email' : 'tel';
    contactLabel.textContent = method === 'email' ? '邮箱地址' : '手机号码';
    contactValueInput.value = '';
    contactValueInput.focus();
}

function findUser() {
    const contactValueInput = document.getElementById('contact-value');
    const contactValue = contactValueInput.value.trim();

    if (!contactValue) {
        alert('请输入' + (selectedMethod === 'email' ? '邮箱地址' : '手机号码'));
        return;
    }

    // 简单的格式验证
    if (selectedMethod === 'email') {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(contactValue)) {
            alert('请输入有效的邮箱地址');
            return;
        }
    } else if (selectedMethod === 'telenum') {
        const phoneRegex = /^1[3-9]\d{9}$/;
        if (!phoneRegex.test(contactValue)) {
            alert('请输入有效的手机号码');
            return;
        }
    }

    // 显示加载状态
    const button = document.querySelector('#contact-input button');
    const originalText = button.textContent;
    button.textContent = '查找中...';
    button.disabled = true;

    // 调用API查找用户
    fetch('/api/password-reset/find-user', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact_type: selectedMethod,
            contact_value: contactValue
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 存储用户信息
            document.getElementById('user-username').value = data.data.username;
            document.getElementById('user-role').value = data.data.role;
            window.contactValue = contactValue;

            // 进入下一步
            goToStep2(contactValue, data.data.username);
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('查找用户失败:', error);
        alert('查找用户失败，请稍后重试');
    })
    .finally(() => {
        // 恢复按钮状态
        button.textContent = originalText;
        button.disabled = false;
    });
}

function goToStep2(contactValue, username) {
    // 更新步骤指示器
    document.getElementById('step-indicator-1').classList.remove('active');
    document.getElementById('step-indicator-1').classList.add('completed');
    document.getElementById('step-indicator-2').classList.add('active');

    // 隐藏第一步，显示第二步
    document.getElementById('step1').classList.remove('active');
    document.getElementById('step2').classList.add('active');

    // 更新验证描述
    const verifyDesc = document.getElementById('verify-description');
    verifyDesc.textContent = `正在验证用户 ${username} 的${selectedMethod === 'email' ? '邮箱' : '手机号'}`;

    currentStep = 2;

    // 清空验证码输入
    document.getElementById('verification-code').value = '';

    // 显示验证码发送按钮
    document.getElementById('send-code-btn').style.display = 'block';
}

function sendCode() {
    if (!window.contactValue) {
        alert('联系方式信息丢失，请重新开始');
        return;
    }

    const button = document.getElementById('send-code-btn');
    const originalText = button.textContent;
    button.textContent = '发送中...';
    button.disabled = true;

    // 调用API发送验证码
    fetch('/api/password-reset/send-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact_type: selectedMethod,
            contact_value: window.contactValue
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 显示验证码已发送状态
            showSendStatus(window.contactValue);

            // 开始倒计时
            startCountdown();

            // 对于手机号，在测试环境下显示验证码
            if (selectedMethod === 'telenum' && data.data.verification_token) {
                console.log('测试环境验证码:', data.data.verification_token);
                alert(`测试环境验证码: ${data.data.verification_token}`);
            }
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('发送验证码失败:', error);
        alert('发送验证码失败，请稍后重试');
    })
    .finally(() => {
        button.textContent = originalText;
        button.disabled = false;
    });
}

function showSendStatus(target) {
    document.getElementById('verification-form').style.display = 'none';
    document.getElementById('send-status').style.display = 'block';
    document.getElementById('send-target').textContent = target;
}

function showVerifyForm() {
    document.getElementById('send-status').style.display = 'none';
    document.getElementById('verification-form').style.display = 'block';

    // 切换到6位输入框
    document.getElementById('verification-code').style.display = 'none';
    document.getElementById('code-input-group').style.display = 'block';

    // 清空输入框
    document.querySelectorAll('.code-input').forEach(input => {
        input.value = '';
    });

    // 聚焦第一个输入框
    document.getElementById('code-input-0').focus();
}

function startCountdown() {
    let countdown = 60;
    const timerElement = document.getElementById('countdown-timer');
    const resendBtn = document.getElementById('resend-btn');

    timerElement.textContent = `验证码 ${countdown} 秒后可重新发送`;
    resendBtn.classList.add('disabled');
    resendBtn.style.pointerEvents = 'none';

    countdownInterval = setInterval(() => {
        countdown--;
        timerElement.textContent = `验证码 ${countdown} 秒后可重新发送`;

        if (countdown <= 0) {
            clearInterval(countdownInterval);
            timerElement.style.display = 'none';
            resendBtn.textContent = '重新发送验证码';
            resendBtn.classList.remove('disabled');
            resendBtn.style.pointerEvents = '';
        }
    }, 1000);
}

function resendCode() {
    // 停止当前倒计时
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }

    // 重新发送
    sendCode();
}

function getVerificationCode() {
    // 获取6位验证码
    const inputs = document.querySelectorAll('.code-input');
    let code = '';

    for (let input of inputs) {
        code += input.value;
    }

    return code.length === 6 ? code : '';
}

function verifyCode() {
    const code = getVerificationCode();

    if (!code || code.length !== 6) {
        alert('请输入完整的6位验证码');
        return;
    }

    if (!window.contactValue) {
        alert('联系方式信息丢失，请重新开始');
        return;
    }

    // 显示加载状态
    const button = document.querySelector('#step2 .login-btn');
    const originalText = button.textContent;
    button.textContent = '验证中...';
    button.disabled = true;

    // 调用API验证验证码
    fetch('/api/password-reset/verify-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact_type: selectedMethod,
            contact_value: window.contactValue,
            verification_token: code
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 验证成功，进入第三步
            goToStep3();
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('验证码验证失败:', error);
        alert('验证码验证失败，请稍后重试');
    })
    .finally(() => {
        // 恢复按钮状态
        button.textContent = originalText;
        button.disabled = false;
    });
}

function goToStep3() {
    // 更新步骤指示器
    document.getElementById('step-indicator-2').classList.remove('active');
    document.getElementById('step-indicator-2').classList.add('completed');
    document.getElementById('step-indicator-3').classList.add('active');

    // 隐藏第二步，显示第三步
    document.getElementById('step2').classList.remove('active');
    document.getElementById('step3').classList.add('active');

    // 清空密码输入框
    document.getElementById('new-password').value = '';
    document.getElementById('confirm-password').value = '';

    currentStep = 3;

    // 为密码表单添加验证
    const form = document.getElementById('password-reset-form');
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        resetPassword();
    });
}

function checkPasswordStrength() {
    const password = document.getElementById('new-password').value;
    const strengthElement = document.getElementById('password-strength');

    if (password.length === 0) {
        strengthElement.textContent = '';
        return;
    }

    let strength = 0;
    let tips = [];

    // 检查长度
    if (password.length >= 6) {
        strength += 1;
    } else {
        tips.push('至少6位字符');
    }

    // 检查是否有字母
    if (/[a-zA-Z]/.test(password)) {
        strength += 1;
    } else {
        tips.push('包含字母');
    }

    // 检查是否有数字
    if (/\d/.test(password)) {
        strength += 1;
    } else {
        tips.push('包含数字');
    }

    let strengthText = '';
    let strengthClass = '';

    if (strength < 2) {
        strengthText = '密码强度：弱 - ' + tips.join('，');
        strengthClass = 'strength-weak';
    } else if (strength < 3) {
        strengthText = '密码强度：中等';
        strengthClass = 'strength-medium';
    } else {
        strengthText = '密码强度：强';
        strengthClass = 'strength-strong';
    }

    strengthElement.textContent = strengthText;
    strengthElement.className = 'password-strength ' + strengthClass;
}

function resetPassword() {
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    if (!newPassword || !confirmPassword) {
        alert('请填写完整的新密码');
        return;
    }

    if (newPassword !== confirmPassword) {
        alert('两次输入的密码不一致');
        return;
    }

    if (newPassword.length < 6) {
        alert('密码长度不能少于6位');
        return;
    }

    if (!window.contactValue) {
        alert('会话信息丢失，请重新开始');
        return;
    }

    // 显示加载状态
    const button = document.querySelector('#password-reset-form .login-btn');
    const originalText = button.textContent;
    button.textContent = '重置中...';
    button.disabled = true;

    // 调用API重置密码
    fetch('/api/password-reset/reset-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact_type: selectedMethod,
            contact_value: window.contactValue,
            new_password: newPassword,
            confirm_password: confirmPassword
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 显示成功状态
            document.getElementById('password-reset-form').style.display = 'none';
            document.getElementById('reset-success').style.display = 'block';
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error('密码重置失败:', error);
        alert('密码重置失败，请稍后重试');
    })
    .finally(() => {
        // 恢复按钮状态
        button.textContent = originalText;
        button.disabled = false;
    });
}

// 页面刷新时清理状态
window.addEventListener('beforeunload', function() {
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
});