// 客户跟进与账号管理接口（销售/管理员，Token 由拦截器注入）
import client from './client'

// 客户列表：scope = mine 我的客户 / pool 公共池
export function fetchCustomers(scope) {
  return client.get('/sales/customers', { params: { scope } })
}

// 认领公共池线索
export function claimCustomer(id) {
  return client.post(`/sales/customers/${id}/claim`)
}

// 客户详情：基本信息 + 预约 + 跟进时间线
export function fetchCustomerDetail(id) {
  return client.get(`/sales/customers/${id}`)
}

// 添加跟进记录
export function addFollowUp(id, payload) {
  return client.post(`/sales/customers/${id}/follow-ups`, payload)
}

// 管理员分配线索给销售
export function assignCustomer(customerId, salesId) {
  return client.put(`/admin/customers/${customerId}/assign`, null, { params: { sales_id: salesId } })
}

// ---- 账号管理（管理员）----

// 账号列表（销售/管理员）
export function fetchUsers() {
  return client.get('/admin/users')
}

// 创建账号
export function createUser(payload) {
  return client.post('/admin/users', payload)
}

// 启用/停用账号
export function setUserStatus(id, status) {
  return client.put(`/admin/users/${id}/status`, null, { params: { status } })
}
