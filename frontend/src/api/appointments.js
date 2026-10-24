// 预约试驾相关接口（顾客端）
import client from './client'

// 某日可约时段
export function fetchAvailableSlots(modelId, date) {
  return client.get('/slots', { params: { model_id: modelId, date } })
}

// 提交预约（游客带验证码，登录顾客免码，由后端按 Token 判定）
export function createAppointment(payload) {
  return client.post('/appointments', payload)
}

// 我的预约列表（需登录）
export function fetchMyAppointments() {
  return client.get('/appointments/mine')
}

// 取消预约（需登录）
export function cancelAppointment(id) {
  return client.post(`/appointments/${id}/cancel`)
}
