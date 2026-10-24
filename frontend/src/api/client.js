// axios 实例封装：统一 baseURL、Token 注入、响应解包与错误提示
import axios from 'axios'

// 创建实例：超时与后端统一前缀
const client = axios.create({
  baseURL: '/api/v1',
  timeout: 10000
})

// 请求拦截器：注入 JWT（管理端与销售端使用）
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：解包后端统一响应体 {code, message, data}，业务代码直接拿到 data
client.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body.code === 200) {
      return body.data
    }
    return Promise.reject(new Error(body.message || '请求失败'))
  },
  (error) => {
    const message = error.response?.data?.message || '网络异常，请稍后重试'
    return Promise.reject(new Error(message))
  }
)

export default client
