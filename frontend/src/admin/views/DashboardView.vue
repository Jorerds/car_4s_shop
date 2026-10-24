<!-- 工作台：角色相关待办概览（骨架占位） -->
<template>
  <el-card>
    <p>欢迎，{{ userStore.name || '用户' }}（{{ roleName }}）</p>
    <p class="mt-2 text-gray-500">待实现：待确认预约数、今日试驾安排、我的业绩概览</p>
  </el-card>
</template>

<script setup>
// 展示当前登录用户与角色，页面内容随迭代补充
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const roleNames = { sales: '销售顾问', admin: '店管理员' }
const roleName = computed(() => roleNames[userStore.role] || userStore.role)
</script>
