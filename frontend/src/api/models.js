// 顾客端车型接口
import client from './client'

// 车型列表：筛选 + 排序 + 分页
export function fetchModels(params) {
  return client.get('/models', { params })
}

// 筛选项（在售品牌）
export function fetchModelFilters() {
  return client.get('/models/filters')
}

// 车型详情：图片集 + 六组配置
export function fetchModelDetail(id) {
  return client.get(`/models/${id}`)
}

// 车型对比：2-3 款参数对齐 + 差异标记
export function compareModels(modelIds) {
  return client.post('/models/compare', { model_ids: modelIds })
}

// 浏览埋点：详情页展示时上报
export function recordView(id) {
  return client.post(`/models/${id}/view`)
}
