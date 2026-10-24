<!-- 顾客端 H5 应用外壳：居中限宽容器 + 图纸式底部标签栏 + 对比浮条 + Toast -->
<template>
  <div class="mx-auto flex min-h-screen w-full max-w-md flex-col bg-white">
    <main class="flex-1 pb-14">
      <router-view />
    </main>

    <!-- 底部标签栏：发丝线分隔，激活项以顶部指示线标记；对比 tab 带数量角标（登录页隐藏） -->
    <nav v-if="showTabBar" class="fixed bottom-0 left-1/2 w-full max-w-md -translate-x-1/2 border-t border-hairline bg-white">
      <div class="grid grid-cols-4">
        <router-link
          v-for="tab in tabs"
          :key="tab.to"
          :to="tab.to"
          class="relative py-2.5 text-center text-[12px]"
          :class="isActive(tab.to) ? 'font-medium text-sea' : 'text-ink-faint'"
        >
          <!-- 激活指示线 -->
          <span v-if="isActive(tab.to)" class="absolute inset-x-6 top-0 border-t-2 border-sea" />
          {{ tab.label }}
          <!-- 对比数量角标：替代原浮条，不占内容区 -->
          <span
            v-if="tab.to === '/compare' && compare.modelIds.length"
            class="num absolute right-[20%] top-0.5 min-w-[16px] rounded-full bg-sea px-1 text-[10px] leading-4 text-white"
          >{{ compare.modelIds.length }}</span>
        </router-link>
      </div>
    </nav>

    <!-- 全局 Toast -->
    <transition name="fade">
      <div v-if="toastMessage" class="fixed left-1/2 top-1/2 z-20 -translate-x-1/2 -translate-y-1/2 rounded bg-ink/80 px-4 py-2 text-[13px] text-white">
        {{ toastMessage }}
      </div>
    </transition>
  </div>
</template>

<script setup>
// 标签栏定义；激活判断：首页要求精确匹配，其余按前缀匹配
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCompareStore } from '@/stores/compare'
import { toastMessage } from './composables/useToast'

const route = useRoute()
const compare = useCompareStore()

const tabs = [
  { to: '/', label: '首页' },
  { to: '/models', label: '车型' },
  { to: '/compare', label: '对比' },
  { to: '/my/appointments', label: '我的' }
]

// 登录页为独立任务流，不展示标签栏与对比浮条
const showTabBar = computed(() => route.path !== '/login')

function isActive(to) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
