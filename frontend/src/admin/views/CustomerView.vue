<!-- 客户跟进：我的/公共池客户列表、认领与分配、详情抽屉（预约 + 跟进时间线）、添加跟进 -->
<template>
  <div>
    <!-- 范围页签：我的客户 / 公共池（未分配可认领） -->
    <el-tabs v-model="scope" @tab-change="load">
      <el-tab-pane label="我的客户" name="mine" />
      <el-tab-pane label="公共池" name="pool" />
    </el-tabs>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="name" label="姓名" min-width="100" />
      <el-table-column prop="phone" label="手机号" min-width="130" />
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small"
                  :type="row.status === 'deal' ? 'success' : row.status === 'new' ? 'info' : 'primary'">
            {{ row.status_text }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="归属销售" min-width="110">
        <template #default="{ row }">{{ row.sales_name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="建档日期" width="110" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
          <el-button v-if="scope === 'pool'" link type="primary" size="small" @click="onClaim(row)">认领</el-button>
          <el-button v-if="isAdmin" link type="primary" size="small" @click="openAssign(row)">分配</el-button>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!items.length && !loading" class="py-8 text-center text-xs text-gray-400">
      {{ scope === 'mine' ? '暂无客户，去公共池认领线索' : '公共池暂无线索' }}
    </p>

    <!-- 客户详情抽屉：信息 + 预约 + 跟进时间线 + 添加跟进 -->
    <el-drawer v-model="drawer" :title="detail ? `${detail.name}（${detail.phone}）` : ''" size="480px">
      <div v-if="detail" v-loading="detailLoading">
        <div class="mb-4 flex items-center gap-2 text-sm">
          <el-tag size="small" :type="detail.status === 'deal' ? 'success' : 'primary'">{{ detail.status_text }}</el-tag>
          <span class="text-gray-400">归属：{{ detail.sales_name || '未分配' }}</span>
        </div>

        <!-- 预约记录 -->
        <p class="mb-2 font-medium">预约记录</p>
        <div v-if="detail.appointments.length" class="mb-4 space-y-1">
          <div v-for="a in detail.appointments" :key="a.id" class="flex justify-between text-sm">
            <span>{{ a.model_name }} <span class="num text-gray-400">{{ a.slot_date }} {{ a.time_slot }}</span></span>
            <span class="text-gray-400">{{ statusText[a.status] || a.status }}</span>
          </div>
        </div>
        <p v-else class="mb-4 text-xs text-gray-400">暂无预约</p>

        <!-- 跟进时间线 -->
        <p class="mb-2 font-medium">跟进记录</p>
        <el-timeline v-if="detail.follow_ups.length" class="mb-4">
          <el-timeline-item v-for="f in detail.follow_ups" :key="f.id"
                            :timestamp="f.created_at" placement="top">
            <p class="text-sm">
              <el-tag size="small" effect="plain">{{ f.type_text }}</el-tag>
              <span class="ml-2">{{ f.content }}</span>
            </p>
            <p class="mt-1 text-xs text-gray-400">
              {{ f.sales_name }}
              <span v-if="f.next_follow_at"> · 下次跟进 {{ f.next_follow_at }}</span>
            </p>
          </el-timeline-item>
        </el-timeline>
        <p v-else class="mb-4 text-xs text-gray-400">暂无跟进记录</p>

        <!-- 添加跟进 -->
        <p class="mb-2 font-medium">添加跟进</p>
        <el-form label-width="90px" size="small">
          <el-form-item label="跟进类型">
            <el-radio-group v-model="followForm.type">
              <el-radio-button value="phone">电话</el-radio-button>
              <el-radio-button value="visit">到店</el-radio-button>
              <el-radio-button value="test_drive">试驾</el-radio-button>
              <el-radio-button value="deal">成交</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="跟进内容">
            <el-input v-model="followForm.content" type="textarea" :rows="3" placeholder="跟进情况记录" />
          </el-form-item>
          <el-form-item label="下次跟进">
            <el-date-picker v-model="followForm.next_follow_at" type="datetime" value-format="YYYY-MM-DD HH:mm"
                            placeholder="选填" class="w-full" />
          </el-form-item>
          <el-button type="primary" class="w-full" :loading="saving" @click="onAddFollowUp">保存跟进</el-button>
        </el-form>
      </div>
    </el-drawer>

    <!-- 分配对话框（管理员） -->
    <el-dialog v-model="assignDialog" title="分配线索" width="400px">
      <el-select v-model="assignSalesId" placeholder="选择销售" class="w-full">
        <el-option v-for="s in salesOptions" :key="s.id" :label="s.name" :value="s.id" />
      </el-select>
      <template #footer>
        <el-button @click="assignDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!assignSalesId" @click="onAssign">分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 数据流：页签 → 列表；详情抽屉内添加跟进后刷新详情；分配仅管理员可见
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchCustomers, claimCustomer, fetchCustomerDetail,
  addFollowUp, assignCustomer, fetchUsers
} from '@/api/customer'
import { useUserStore } from '@/stores/user'

// 预约状态文案（与后端状态机一致）
const statusText = {
  pending: '待确认', confirmed: '已确认', rejected: '已拒绝',
  cancelled: '已取消', completed: '已完成', no_show: '已爽约'
}

const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')

const scope = ref('mine')
const items = ref([])
const loading = ref(false)
const saving = ref(false)
const drawer = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const followForm = reactive({ type: 'phone', content: '', next_follow_at: null })
const assignDialog = ref(false)
const assignSalesId = ref(null)
const salesOptions = ref([])
const activeId = ref(null)

async function load() {
  loading.value = true
  try {
    const data = await fetchCustomers(scope.value)
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function onClaim(row) {
  await claimCustomer(row.id)
  ElMessage.success('认领成功')
  await load()
}

async function openDetail(row) {
  activeId.value = row.id
  drawer.value = true
  detailLoading.value = true
  followForm.content = ''
  followForm.next_follow_at = null
  try {
    detail.value = await fetchCustomerDetail(row.id)
  } finally {
    detailLoading.value = false
  }
}

async function onAddFollowUp() {
  if (!followForm.content.trim()) {
    ElMessage.warning('请填写跟进内容')
    return
  }
  saving.value = true
  try {
    await addFollowUp(activeId.value, {
      type: followForm.type,
      content: followForm.content.trim(),
      next_follow_at: followForm.next_follow_at || undefined
    })
    ElMessage.success('已保存')
    detail.value = await fetchCustomerDetail(activeId.value)
    followForm.content = ''
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

// 分配：打开时拉取销售名单（账号列表过滤）
async function openAssign(row) {
  activeId.value = row.id
  assignSalesId.value = null
  const data = await fetchUsers()
  salesOptions.value = data.items.filter((u) => u.role === 'sales' && u.status === 'active')
  assignDialog.value = true
}

async function onAssign() {
  await assignCustomer(activeId.value, assignSalesId.value)
  ElMessage.success('分配成功')
  assignDialog.value = false
  await load()
}

onMounted(load)
</script>
