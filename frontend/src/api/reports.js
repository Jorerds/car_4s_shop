// 统计报表接口（仅管理员）
import client from './client'

// 预约/转化报表
export function fetchBookingReport(params) {
  return client.get('/reports/booking', { params })
}

// 销售业绩报表
export function fetchSalesReport(params) {
  return client.get('/reports/sales', { params })
}

// 客户报表
export function fetchCustomerReport(params) {
  return client.get('/reports/customer', { params })
}

// 车型热度报表
export function fetchModelReport(params) {
  return client.get('/reports/model', { params })
}

// 导出报表：format = excel | csv，返回 {url}
export function exportReport(type, params) {
  return client.post(`/reports/${type}/export`, null, { params })
}
