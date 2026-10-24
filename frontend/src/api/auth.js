// 认证相关接口：账号密码登录（销售/管理员）、手机号验证码（顾客端）
import client from './client'

// 账号密码登录，成功返回 {token, user}
export function loginByAccount(username, password) {
  return client.post('/auth/login-by-account', { username, password })
}

// 发送短信验证码（mock 模式响应带 dev_code 便于开发）
export function sendSmsCode(phone) {
  return client.post('/auth/sms-code', { phone })
}

// 顾客手机号 + 验证码登录（自动注册）
export function loginByPhone(phone, code) {
  return client.post('/auth/login-by-phone', { phone, code })
}
