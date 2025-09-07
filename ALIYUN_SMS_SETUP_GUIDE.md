# 阿里云短信服务配置指南

本指南将帮助您在忘记密码功能中集成阿里云短信验证码服务。

## 📋 前置准备

### 1. 注册阿里云账号

访问 [阿里云官网](https://www.aliyun.com/) 注册账号（如果已有账号请跳过）

### 2. 开通短信服务

1. 进入 [短信服务控制台](https://dysms.console.aliyun.com/)
2. 点击"开通短信服务"
3. 完成实名认证（个人认证或企业认证）

### 3. 账户充值

阿里云短信服务按条收费，需要预充值：

- 进入控制台 → 资费说明 → 充值
- 建议先充值10-20元测试使用

## 🔑 获取API密钥

### 方法一：在控制台生成（推荐）

1. 进入 [API密钥管理](https://usercenter.console.aliyun.com/#/manage/ak)
2. 点击"创建AccessKey"
3. 下载或复制AccessKey ID和AccessKey Secret

### 方法二：使用子账户

1. 进入RAM访问控制
2. 创建子用户并分配SMS相关权限
3. 为子用户创建AccessKey

## 📝 申请短信签名和模板

### 申请短信签名

1. 在短信控制台 → 签名管理 → 添加签名
2. 签名类型：选择"验证码"或"通用短信"
3. 签名内容：您的应用名称（英文建议用全大写）
4. 提交审核（需要1-3个工作日）

### 申请短信模板

1. 在短信控制台 → 模板管理 → 添加模板
2. 模板类型：验证码
3. 模板内容：

   ```
   您的验证码为：${code}，有效期${time}分钟，请及时输入。
   ```

4. 变量说明：
   - `${code}`: 验证码数字
   - `${time}`: 有效期分钟数

**重要提示：** 签名和模板审核通过前无法使用！

## ⚙️ 代码配置

### 1. 修改环境变量文件 `.env`

```bash
# 启用短信服务
SMS_ENABLED=true

# 阿里云配置
ALIYUN_ACCESS_KEY_ID=LTAI5t6A7B8C9D0E1F2G3H4I
ALIYUN_ACCESS_KEY_SECRET=J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y0
ALIYUN_SMTP_SIGN_NAME=YOUR_APP_NAME
ALIYUN_SMTP_TEMPLATE_CODE=SMS_123456789
```

### 2. 重启应用

修改配置后需要重启Flask应用：

```bash
# Linux/Mac
export FLASK_APP=app.py
export FLASK_ENV=development
flask run

# Windows PowerShell
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
flask run

# 或使用run.py
python run.py
```

## 🧪 测试配置

### 1. 测试阿里云服务连接

```python
# 运行测试脚本
python sms_aliyun_config.py
```

### 2. 完整的忘记密码测试

```python
# 测试完整流程
python test_password_reset.py
```

### 3. 前端界面测试

1. 启动Web应用
2. 访问忘记密码页面：`http://localhost:5000/forgot-password`
3. 输入邮箱或手机号
4. 点击"发送验证码"
5. 观察浏览器和控制台输出

## 📱 发送流程说明

### 成功发送流程

1. 用户输入手机号码
2. 系统查找用户是否存在
3. 系统生成6位验证码
4. 调用阿里云SMS API
5. 阿里云发送短信到用户手机号
6. 用户收到短信验证码
7. 输入验证码验证

### 失败回退机制

1. 如果阿里云API调用失败
2. 系统自动显示模拟发送结果
3. 控制台输出验证码信息
4. 仍可继续测试和开发

## 🔍 常见问题

### Q: 如何查看发送日志？

A: 在阿里云短信控制台的"发送记录"页面

### Q: 短信发送延迟怎么办？

A: 平均发送时间为2-3秒，高峰期可能稍长

### Q: 如何处理签名驳回？

A: 检查签名要求，重新提交或联系阿里云客服

### Q: AccessKey泄露了怎么办？

A: 立即删除泄露的AccessKey并创建新的

### Q: 测试费用花费多少？

A: 一条验证码短信约0.045元，可以免费试用100条

## 📞 技术支持

如果遇到问题，可以：

1. **检查配置**: 确认AccessKey和签名模板ID正确
2. **查看错误日志**: 控制台输出会显示详细错误信息
3. **阿里云文档**: 参考[阿里云短信服务文档](https://help.aliyun.com/document_detail/55284.html)
4. **技术支持**: 使用阿里云工单系统获取帮助

## 💰 资费说明

- **验证码单条**: 约0.045元
- **行业单条**: 约0.045元
- **营销单条**: 约0.055元

计费规则：以成功下发为准，无论用户是否收到

---

配置完成后，您就可以在正式环境中使用真正的短信验证码服务了！
