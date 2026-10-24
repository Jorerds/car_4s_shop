// 管理端路由：登录守卫 + 按角色过滤可见菜单（RBAC 前端体现，后端仍逐接口鉴权）
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { title: '登录' } },
    {
      path: '/',
      component: () => import('../layout/AdminLayout.vue'),
      // 未登录一律重定向到登录页
      beforeEnter: () => {
        if (!useUserStore().isLoggedIn) return { name: 'login' }
      },
      children: [
        { path: '', name: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { title: '工作台' } },
        { path: 'models', name: 'models', component: () => import('../views/ModelManageView.vue'), meta: { title: '车型管理', roles: ['admin'] } },
        { path: 'slots', name: 'slots', component: () => import('../views/SlotManageView.vue'), meta: { title: '试驾时段管理', roles: ['admin'] } },
        { path: 'appointments', name: 'appointments', component: () => import('../views/AppointmentConfirmView.vue'), meta: { title: '预约确认', roles: ['sales', 'admin'] } },
        { path: 'customers', name: 'customers', component: () => import('../views/CustomerView.vue'), meta: { title: '客户跟进', roles: ['sales', 'admin'] } },
        { path: 'users', name: 'users', component: () => import('../views/UserManageView.vue'), meta: { title: '账号管理', roles: ['admin'] } },
        { path: 'reports', name: 'reports', component: () => import('../views/ReportView.vue'), meta: { title: '统计报表', roles: ['admin'] } }
      ]
    }
  ]
})

// 全局守卫：校验路由角色要求，越权访问回工作台
router.beforeEach((to) => {
  const user = useUserStore()
  const requiredRoles = to.meta.roles
  if (requiredRoles && !requiredRoles.includes(user.role)) {
    return { name: 'dashboard' }
  }
  document.title = to.meta.title ? `${to.meta.title} · 门店管理系统` : '门店管理系统'
})

export default router
