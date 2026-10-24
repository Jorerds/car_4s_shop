<!-- 账号管理：销售/管理员账号列表、创建、启用停用（仅管理员） -->
<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <span class="text-gray-500">销售顾问与店管理员的登录账号</span>
      <el-button type="primary" @click="openCreate">新建账号</el-button>
    </div>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="username" label="账号" min-width="160" />
      <!-- 弹性列：无固定宽度，吸收表格剩余空间 -->
      <el-table-column prop="name" label="姓名" min-width="140" />
      <el-table-column label="角色" width="110" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.role === 'admin' ? 'warning' : 'primary'">
            {{ row.role === 'admin' ? '店管理员' : '销售顾问' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建日期" width="120" />
      <el-table-column label="状态" width="120" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.status === 'active'"
                     active-text="启用" inactive-text="停用" inline-prompt
                     :disabled="row.username === 'admin'"
                     @change="(v) => onToggleStatus(row, v)" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建账号对话框 -->
    <el-dialog v-model="dialog" title="新建账号" width="440px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="sales">销售顾问</el-radio>
            <el-radio value="admin">店管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSubmit">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 数据流：列表加载；创建成功清空表单并刷新；停用即时生效（下次登录被拒）
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchUsers, createUser, setUserStatus } from '@/api/customer'

const items = ref([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const formRef = ref()
const form = reactive({ role: 'sales', username: '', name: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [{ required: true, min: 6, message: '密码至少 6 位', trigger: 'blur' }]
}

async function load() {
  loading.value = true
  try {
    const data = await fetchUsers()
    items.value = data.items
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.role = 'sales'
  form.username = ''
  form.name = ''
  form.password = ''
  dialog.value = true
}

async function onSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createUser(form)
    ElMessage.success('创建成功')
    dialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function onToggleStatus(row, active) {
  try {
    await setUserStatus(row.id, active ? 'active' : 'disabled')
    ElMessage.success(active ? '已启用' : '已停用')
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

onMounted(load)
</script>
