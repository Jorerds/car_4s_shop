// 管理端车型与文件接口（需管理员权限，Token 由拦截器注入）
import client from './client'

// 管理端车型列表：关键字 + 分页
export function adminFetchModels(params) {
  return client.get('/admin/models', { params })
}

// 管理端车型详情：含停售车，完整图片与配置
export function adminFetchModelDetail(id) {
  return client.get(`/admin/models/${id}`)
}

// 创建车型
export function adminCreateModel(data) {
  return client.post('/admin/models', data)
}

// 更新车型（含销售状态）
export function adminUpdateModel(id, data) {
  return client.put(`/admin/models/${id}`, data)
}

// 配置参数整体替换
export function adminReplaceConfigs(id, configs) {
  return client.put(`/admin/models/${id}/configs`, { configs })
}

// 添加图片
export function adminAddImage(id, data) {
  return client.post(`/admin/models/${id}/images`, data)
}

// 删除图片
export function adminDeleteImage(modelId, imageId) {
  return client.delete(`/admin/models/${modelId}/images/${imageId}`)
}

// 设置主图
export function adminSetMainImage(modelId, imageId) {
  return client.put(`/admin/models/${modelId}/images/${imageId}/main`)
}

// 上传图片文件，返回 {url}
export function uploadImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  return client.post('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// ---- 试驾资源 ----

// 试驾车列表
export function adminFetchVehicles() {
  return client.get('/admin/vehicles')
}

// 新增试驾车
export function adminCreateVehicle(data) {
  return client.post('/admin/vehicles', data)
}

// 更新试驾车状态（available/disabled）
export function adminUpdateVehicle(id, status) {
  return client.put(`/admin/vehicles/${id}`, { status })
}

// 批量生成试驾时段
export function adminBatchSlots(data) {
  return client.post('/admin/slots/batch', data)
}

// 某日时段列表（管理端）
export function adminFetchDaySlots(modelId, date) {
  return client.get('/admin/slots', { params: { model_id: modelId, date } })
}
