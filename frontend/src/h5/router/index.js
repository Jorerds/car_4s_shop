// 顾客端 H5 路由：浏览 → 对比 → 预约 → 我的预约 主链路
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/'),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue'), meta: { title: '首页' } },
    { path: '/models', name: 'models', component: () => import('../views/ModelListView.vue'), meta: { title: '车型列表' } },
    { path: '/models/:id', name: 'model-detail', component: () => import('../views/ModelDetailView.vue'), meta: { title: '车型详情' } },
    { path: '/compare', name: 'compare', component: () => import('../views/CompareView.vue'), meta: { title: '车型对比' } },
    { path: '/models/:id/appointment', name: 'appointment', component: () => import('../views/AppointmentView.vue'), meta: { title: '预约试驾' } },
    { path: '/my/appointments', name: 'my-appointments', component: () => import('../views/MyAppointmentsView.vue'), meta: { title: '我的预约' } },
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { title: '登录' } }
  ]
})

// 路由切换后同步页面标题（H5 无菜单栏，标题即导航反馈）
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 在线看车` : '在线看车 · 预约试驾'
})

export default router
