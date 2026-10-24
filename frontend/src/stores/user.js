// 用户状态：登录态与角色信息，Token 持久化到 localStorage（管理端与顾客端共用）
import { defineStore } from 'pinia'
import { loginByAccount, loginByPhone } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    // 角色：customer/sales/admin，空串表示未登录
    role: localStorage.getItem('role') || '',
    name: localStorage.getItem('name') || '',
    phone: localStorage.getItem('phone') || ''
  }),
  getters: {
    // 是否已登录
    isLoggedIn: (state) => Boolean(state.token),
    // 是否为登录顾客（C 端能力：我的预约、免验证码预约）
    isCustomer: (state) => state.role === 'customer'
  },
  actions: {
    // 写入登录态（两端登录共用）
    _setSession(data, phone = '') {
      this.token = data.token
      this.role = data.user.role
      this.name = data.user.name || ''
      this.phone = phone
      localStorage.setItem('token', this.token)
      localStorage.setItem('role', this.role)
      localStorage.setItem('name', this.name)
      localStorage.setItem('phone', this.phone)
    },
    // 账号密码登录（销售/管理员入口）
    async login(username, password) {
      const data = await loginByAccount(username, password)
      this._setSession(data)
    },
    // 顾客手机号登录
    async loginWithPhone(phone, code) {
      const data = await loginByPhone(phone, code)
      this._setSession(data, phone)
    },
    // 退出登录：清空内存与持久化状态
    logout() {
      this.token = ''
      this.role = ''
      this.name = ''
      this.phone = ''
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('name')
      localStorage.removeItem('phone')
    }
  }
})
