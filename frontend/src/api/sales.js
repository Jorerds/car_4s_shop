// 销售端接口（销售顾问/管理员，Token 由拦截器注入）
import client from './client'

// 预约列表：status 支持 pending/confirmed/finished/rejected/cancelled
export function fetchSalesAppointments(status) {
  return client.get('/sales/appointments', { params: { status } })
}

// 某车型可分配试驾车
export function fetchAssignableVehicles(modelId) {
  return client.get('/sales/vehicles', { params: { model_id: modelId } })
}

// 确认预约并分配车辆
export function confirmAppointment(id, vehicleId) {
  return client.post(`/sales/appointments/${id}/confirm`, { vehicle_id: vehicleId })
}

// 拒绝预约
export function rejectAppointment(id, reason) {
  return client.post(`/sales/appointments/${id}/reject`, { reason })
}

// 登记试驾结果：completed（可带评分与文字）或 no_show
export function recordTestDrive(id, payload) {
  return client.post(`/sales/appointments/${id}/record`, payload)
}

// 我的站内通知（顾客）
export function fetchMyNotifications() {
  return client.get('/notifications/mine')
}

// 标记通知已读
export function markNotificationRead(id) {
  return client.post(`/notifications/${id}/read`)
}
