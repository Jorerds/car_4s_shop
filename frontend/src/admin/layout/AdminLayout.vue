<!-- 管理端布局：侧边栏菜单（按角色渲染）+ 主内容区 -->
<template>
  <el-container class="min-h-screen">
    <el-aside width="220px" class="bg-sea-deep text-white">
      <div class="p-4 text-[15px] font-semibold tracking-wide">门店管理系统</div>
      <el-menu :default-active="$route.path" router background-color="#0F2438" text-color="#A2B2C4" active-text-color="#FFFFFF">
        <el-menu-item v-for="item in visibleMenus" :key="item.path" :index="item.path">
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="flex items-center justify-between border-b">
        <span>{{ $route.meta.title }}</span>
        <el-button size="small" @click="onLogout">退出登录</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
// 菜单按角色过滤：roles 包含当前用户角色才显示
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

// 全量菜单定义，与路由 meta.roles 保持一致
const menus = [
  { path: '/', title: '工作台', roles: ['sales', 'admin'] },
  { path: '/appointments', title: '预约确认', roles: ['sales', 'admin'] },
  { path: '/customers', title: '客户跟进', roles: ['sales', 'admin'] },
  { path: '/models', title: '车型管理', roles: ['admin'] },
  { path: '/slots', title: '试驾时段管理', roles: ['admin'] },
  { path: '/users', title: '账号管理', roles: ['admin'] },
  { path: '/reports', title: '统计报表', roles: ['admin'] }
]

const visibleMenus = computed(() => menus.filter((m) => m.roles.includes(userStore.role)))

// 退出登录后回到登录页
function onLogout() {
  userStore.logout()
  router.push({ name: 'login' })
}
</script>
