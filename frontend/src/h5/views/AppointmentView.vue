<!-- 预约试驾页：车型摘要 → 选日期/时段（含余量）→ 联系信息（游客需验证码）→ 提交成功 -->
<template>
  <div class="flex min-h-screen flex-col bg-white">
    <header class="flex items-center border-b border-hairline px-2 py-2.5">
      <button class="px-2 text-[15px] text-ink-secondary" @click="$router.back()">‹ 返回</button>
      <span class="ml-2 text-[15px] font-semibold">预约试驾</span>
    </header>

    <p v-if="loading" class="py-20 text-center text-[12px] text-ink-faint">加载中…</p>

    <!-- 成功态 -->
    <div v-else-if="success" class="px-5 py-16 text-center">
      <p class="text-[18px] font-semibold">预约提交成功</p>
      <p class="mt-2 text-[13px] text-ink-secondary">销售顾问确认后将短信通知您，请保持手机畅通</p>
      <router-link to="/my/appointments" class="mt-6 inline-block bg-sea px-8 py-2.5 text-[14px] text-white">查看我的预约</router-link>
    </div>

    <template v-else-if="detail">
      <!-- 车型摘要 -->
      <section class="flex items-center gap-3 border-b border-hairline px-4 py-3">
        <img v-if="detail.images[0]" :src="detail.images[0]" :alt="detail.name" class="h-16 w-24 bg-mist object-cover" />
        <div v-else class="flex h-16 w-24 items-center justify-center bg-mist text-[11px] text-ink-faint">车型图</div>
        <div>
          <p class="text-[15px] font-semibold">{{ detail.name }}</p>
          <p class="num mt-0.5 text-[13px] text-sea">¥{{ formatPrice(detail.guide_price) }} 起</p>
        </div>
      </section>

      <!-- 日期选择：未来 7 天横向滚动 -->
      <section class="px-4 pt-3">
        <p class="label-tech">选择日期</p>
        <div class="no-scrollbar mt-2 flex gap-2 overflow-x-auto">
          <button v-for="d in days" :key="d.date"
                  class="shrink-0 border px-3 py-2 text-center"
                  :class="selectedDate === d.date ? 'border-sea bg-sea text-white' : 'border-hairline'"
                  @click="onSelectDate(d.date)">
            <p class="text-[12px]">{{ d.weekday }}</p>
            <p class="num mt-0.5 text-[13px]">{{ d.label }}</p>
          </button>
        </div>
      </section>

      <!-- 时段选择：显示余量 -->
      <section class="mt-4 px-4">
        <p class="label-tech">选择时段</p>
        <p v-if="slotsLoading" class="mt-2 text-[12px] text-ink-faint">加载时段…</p>
        <p v-else-if="!slots.length" class="mt-2 text-[12px] text-ink-faint">当日已约满，请换一天</p>
        <div v-else class="mt-2 grid grid-cols-3 gap-2">
          <button v-for="s in slots" :key="s.id"
                  class="border py-2 text-center"
                  :class="selectedSlotId === s.id ? 'border-sea bg-sea text-white' : 'border-hairline'"
                  @click="selectedSlotId = s.id">
            <p class="num text-[14px]">{{ s.time_slot }}</p>
            <p class="mt-0.5 text-[11px]" :class="selectedSlotId === s.id ? 'text-white/80' : 'text-ink-faint'">余 {{ s.remaining }}</p>
          </button>
        </div>
      </section>

      <!-- 联系信息 -->
      <section class="mt-5 px-4">
        <p class="label-tech">联系信息</p>
        <div class="mt-2 flex items-center border-b border-hairline py-2">
          <input v-model="form.customer_name" maxlength="20" placeholder="姓名"
                 class="flex-1 bg-transparent text-[15px] outline-none" />
        </div>
        <div class="mt-3 flex items-center border-b border-hairline py-2">
          <input v-model="form.phone" type="tel" maxlength="11" placeholder="手机号"
                 class="flex-1 bg-transparent text-[15px] outline-none" :disabled="isLoggedIn" />
        </div>
        <!-- 游客需短信验证码；登录顾客免验证码 -->
        <div v-if="!isLoggedIn" class="mt-3 flex items-center border-b border-hairline py-2">
          <input v-model="form.code" maxlength="6" placeholder="短信验证码"
                 class="flex-1 bg-transparent text-[15px] outline-none" />
          <button class="text-[13px] text-sea disabled:text-ink-faint" :disabled="countdown > 0" @click="onSendCode">
            {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
          </button>
        </div>
        <div class="mt-3 flex items-center border-b border-hairline py-2">
          <input v-model="form.remark" maxlength="200" placeholder="备注（选填，如期望配置、问题等）"
                 class="flex-1 bg-transparent text-[15px] outline-none" />
        </div>
      </section>

      <!-- 提交 -->
      <div class="mt-auto p-4">
        <button class="w-full bg-sea py-2.5 text-[15px] text-white disabled:bg-ink-faint"
                :disabled="!canSubmit" @click="onSubmit">提交预约</button>
        <p class="mt-2 text-center text-[11px] text-ink-faint">提交即占用名额；试驾开始前 2 小时内不可取消</p>
      </div>
    </template>

    <p v-else class="py-20 text-center text-[12px] text-ink-faint">车型不存在或已停售</p>
  </div>
</template>

<script setup>
// 流程：加载车型 → 默认选明天 → 拉可约时段 → 填信息提交
// 登录顾客（store 判定）自动带出手机号、免验证码；游客需短信验证码
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { fetchModelDetail } from '@/api/models'
import { fetchAvailableSlots, createAppointment } from '@/api/appointments'
import { sendSmsCode } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { useToast } from '../composables/useToast'
import { formatPrice } from '@/utils/format'

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const route = useRoute()
const userStore = useUserStore()
const toast = useToast()

const detail = ref(null)
const loading = ref(true)
const success = ref(false)
const days = ref([])
const selectedDate = ref('')
const slots = ref([])
const slotsLoading = ref(false)
const selectedSlotId = ref(null)
const form = reactive({ customer_name: '', phone: '', code: '', remark: '' })
const countdown = ref(0)
let timer = null

// 未来 7 天日期选项（今天置灰不排：避免预约已过时段的复杂度）
function buildDays() {
  const result = []
  for (let i = 1; i <= 7; i++) {
    const d = new Date()
    d.setDate(d.getDate() + i)
    result.push({
      date: d.toISOString().slice(0, 10),
      weekday: WEEKDAYS[d.getDay()],
      label: `${d.getMonth() + 1}/${d.getDate()}`,
    })
  }
  return result
}

const isLoggedIn = computed(() => userStore.isCustomer)

const canSubmit = computed(() =>
  Boolean(selectedSlotId.value && form.customer_name && form.phone)
  && (isLoggedIn.value || form.code)
)

function onSelectDate(date) {
  selectedDate.value = date
  selectedSlotId.value = null
  loadSlots()
}

async function loadSlots() {
  slotsLoading.value = true
  try {
    const data = await fetchAvailableSlots(route.params.id, selectedDate.value)
    slots.value = data.items
  } catch {
    slots.value = []
  } finally {
    slotsLoading.value = false
  }
}

async function onSendCode() {
  if (!/^1\d{10}$/.test(form.phone)) {
    toast('请输入正确的手机号')
    return
  }
  try {
    await sendSmsCode(form.phone)
    countdown.value = 60
    clearInterval(timer)
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
    toast('验证码已发送（开发模式见后端日志）')
  } catch (error) {
    toast(error.message)
  }
}

async function onSubmit() {
  try {
    await createAppointment({
      model_id: Number(route.params.id),
      slot_id: selectedSlotId.value,
      customer_name: form.customer_name,
      phone: form.phone,
      code: form.code || undefined,
      remark: form.remark || undefined
    })
    success.value = true
    window.scrollTo(0, 0)
  } catch (error) {
    toast(error.message)
  }
}

onMounted(async () => {
  try {
    detail.value = await fetchModelDetail(route.params.id)
    days.value = buildDays()
    selectedDate.value = days.value[0].date
    await loadSlots()
    // 登录顾客带出联系信息
    if (isLoggedIn.value) {
      form.phone = userStore.phone
      form.customer_name = userStore.name
    }
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
})
</script>
