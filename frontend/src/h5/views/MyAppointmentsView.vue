<!-- 我的预约 + 消息通知：登录顾客查看预约状态、取消预约、查看并处理站内通知 -->
<template>
  <div>
    <header class="border-b border-hairline px-4 py-3">
      <h1 class="text-[15px] font-semibold">我的</h1>
    </header>

    <!-- 未登录引导 -->
    <div v-if="!userStore.isLoggedIn" class="px-4 py-16 text-center">
      <p class="text-[13px] text-ink-secondary">登录后查看预约记录和试驾通知</p>
      <router-link :to="{ path: '/login', query: { redirect: '/my/appointments' } }"
                   class="mt-4 inline-block bg-sea px-8 py-2.5 text-[14px] text-white">手机号登录</router-link>
    </div>

    <template v-else>
      <!-- 消息通知 -->
      <section class="border-b border-hairline px-4 py-3">
        <div class="flex items-center justify-between">
          <p class="text-[14px] font-semibold">
            消息通知
            <span v-if="unread" class="num ml-1 rounded-full bg-sea px-1.5 text-[10px] leading-4 text-white">{{ unread }}</span>
          </p>
          <button v-if="notifications.length" class="text-[12px] text-ink-faint" @click="showNotifications = !showNotifications">
            {{ showNotifications ? '收起' : '展开' }}
          </button>
        </div>
        <div v-show="showNotifications">
          <p v-if="!notifications.length" class="mt-2 text-[12px] text-ink-faint">暂无通知</p>
          <div v-for="n in notifications" :key="n.id" class="mt-2 flex items-start gap-2"
               @click="onRead(n)">
            <!-- 未读指示点 -->
            <span class="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full"
                  :class="n.is_read ? 'bg-hairline' : 'bg-sea'" />
            <div class="flex-1">
              <p class="text-[13px]" :class="n.is_read ? 'text-ink-secondary' : 'text-ink'">{{ n.content }}</p>
              <p class="num mt-0.5 text-[11px] text-ink-faint">{{ n.created_at }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 我的预约 -->
      <section class="px-4 py-3">
        <p class="mb-1 text-[14px] font-semibold">我的预约</p>
      </section>
      <p v-if="loading" class="py-10 text-center text-[12px] text-ink-faint">加载中…</p>
      <p v-else-if="!items.length" class="py-10 text-center text-[12px] text-ink-faint">暂无预约记录</p>

      <div v-else class="divide-y divide-hairline">
        <div v-for="a in items" :key="a.id" class="px-4 py-3">
          <div class="flex items-baseline justify-between">
            <p class="text-[15px] font-semibold">{{ a.model_name }}</p>
            <p class="text-[12px]"
               :class="a.status === 'confirmed' ? 'text-sea' : a.status === 'pending' ? 'text-ink-secondary' : 'text-ink-faint'">
              {{ a.status_text }}
            </p>
          </div>
          <p class="num mt-1 text-[13px] text-ink-secondary">{{ a.slot_date }} {{ a.time_slot }}</p>
          <div class="mt-2 flex items-center justify-between">
            <p class="text-[11px] text-ink-faint">提交于 {{ a.created_at }}</p>
            <button v-if="['pending', 'confirmed'].includes(a.status)"
                    class="border border-hairline px-3 py-1 text-[12px] text-ink-secondary"
                    @click="onCancel(a)">取消预约</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
// 进入页面并行加载预约与通知；点击通知标记已读；取消预约刷新列表
import { ref, onMounted } from 'vue'
import { fetchMyAppointments, cancelAppointment } from '@/api/appointments'
import { fetchMyNotifications, markNotificationRead } from '@/api/sales'
import { useUserStore } from '@/stores/user'
import { useToast } from '../composables/useToast'

const userStore = useUserStore()
const toast = useToast()

const items = ref([])
const notifications = ref([])
const unread = ref(0)
const showNotifications = ref(true)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const [apptData, notifData] = await Promise.all([fetchMyAppointments(), fetchMyNotifications()])
    items.value = apptData.items
    notifications.value = notifData.items
    unread.value = notifData.unread
  } catch (error) {
    toast(error.message)
  } finally {
    loading.value = false
  }
}

// 点击通知即标记已读（本地即时反馈 + 服务端落库）
async function onRead(notification) {
  if (notification.is_read) return
  notification.is_read = true
  unread.value = Math.max(0, unread.value - 1)
  try {
    await markNotificationRead(notification.id)
  } catch {
    /* 已读标记失败不影响展示，下次进入会校正 */
  }
}

async function onCancel(appointment) {
  try {
    await cancelAppointment(appointment.id)
    toast('已取消，名额已释放')
    await load()
  } catch (error) {
    toast(error.message)
  }
}

onMounted(() => {
  if (userStore.isLoggedIn) load()
})
</script>
