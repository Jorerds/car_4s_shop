<!-- 管理端登录页：画廊风格——浅灰底衬 + 发丝线边框卡片（逻辑不变） -->
<template>
  <div class="flex min-h-screen items-center justify-center bg-mist">
    <div class="w-[380px] border border-hairline bg-white px-8 py-10">
      <h1 class="text-[17px] font-semibold tracking-wide">星辉汽车 · 门店管理系统</h1>
      <p class="mt-1 text-[12px] text-ink-faint">销售顾问与店管理员登录</p>

      <el-form ref="formRef" :model="form" :rules="rules" class="mt-8" @submit.prevent="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="账号" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-button type="primary" class="w-full" :loading="loading" native-type="submit">登录</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
// 登录成功按角色跳转工作台；失败弹出后端返回的错误信息
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const form = reactive({ username: '', password: '' })
const formRef = ref()
const loading = ref(false)
const userStore = useUserStore()
const router = useRouter()

// 提交前必填校验：空表单直接拦截并给出中文提示，不发起请求
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function onSubmit() {
  // 先过本地表单校验，失败则不提交
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    router.push({ name: 'dashboard' })
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}
</script>
