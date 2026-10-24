<!-- 顾客端登录页：手机号 + 短信验证码，登录后回跳来源页或首页 -->
<template>
  <div class="flex min-h-screen flex-col bg-white">
    <header class="flex items-center border-b border-hairline px-2 py-2.5">
      <button class="px-2 text-[15px] text-ink-secondary" @click="$router.back()">‹ 返回</button>
      <span class="ml-2 text-[15px] font-semibold">登录</span>
    </header>

    <div class="px-5 pt-8">
      <h2 class="text-[19px] font-semibold">手机号登录</h2>
      <p class="mt-1 text-[12px] text-ink-faint">登录后可查看预约记录、取消预约、接收试驾通知</p>

      <!-- 手机号输入：下划线式表单，符合画廊风格 -->
      <div class="mt-6 flex items-center border-b border-hairline py-2">
        <span class="text-[15px] text-ink-secondary">+86</span>
        <input v-model="phone" type="tel" maxlength="11" placeholder="请输入手机号"
               class="ml-3 flex-1 bg-transparent text-[15px] outline-none" />
      </div>

      <!-- 验证码输入：获取按钮 60 秒倒计时 -->
      <div class="mt-4 flex items-center border-b border-hairline py-2">
        <input v-model="code" maxlength="6" placeholder="短信验证码"
               class="flex-1 bg-transparent text-[15px] outline-none" />
        <button class="text-[13px] text-sea disabled:text-ink-faint" :disabled="countdown > 0" @click="onSendCode">
          {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
        </button>
      </div>

      <button class="mt-8 w-full bg-sea py-2.5 text-[15px] text-white disabled:bg-ink-faint"
              :disabled="!phone || !code" @click="onLogin">登录</button>
      <p class="mt-4 text-center text-[11px] text-ink-faint">未注册的手机号验证通过后自动创建账号</p>
      <p v-if="devCode" class="mt-2 text-center text-[11px] text-ink-faint">开发模式验证码：{{ devCode }}</p>
    </div>
  </div>
</template>

<script setup>
// 开发模式（mock 短信）下展示 dev_code 便于联调；生产环境无此行
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { sendSmsCode } from '@/api/auth'
import { useUserStore } from '@/stores/user'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const toast = useToast()

const phone = ref('')
const code = ref('')
const devCode = ref('')
const countdown = ref(0)
let timer = null

async function onSendCode() {
  if (!/^1\d{10}$/.test(phone.value)) {
    toast('请输入正确的手机号')
    return
  }
  try {
    const data = await sendSmsCode(phone.value)
    devCode.value = data.dev_code || ''
    // 60 秒重发倒计时
    countdown.value = 60
    clearInterval(timer)
    timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (error) {
    toast(error.message)
  }
}

async function onLogin() {
  try {
    await userStore.loginWithPhone(phone.value, code.value)
    // 回跳来源页（如从"我的预约"被引导登录），否则回首页
    router.replace(route.query.redirect || '/')
  } catch (error) {
    toast(error.message)
  }
}
</script>
