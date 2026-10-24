<!-- 试驾时段管理：试驾车维护 + 时段批量生成 + 某日时段查看（仅管理员） -->
<template>
  <div>
    <!-- 试驾车管理 -->
    <el-card class="mb-4">
      <div class="mb-3 flex items-center justify-between">
        <span class="font-medium">试驾车</span>
        <el-button type="primary" size="small" @click="vehicleDialog = true">新增试驾车</el-button>
      </div>
      <el-table :data="vehicles" size="small" border>
        <el-table-column prop="plate_no" label="车牌号" width="140" />
        <el-table-column prop="model_name" label="所属车型" min-width="140" />
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.status === 'available'"
                       active-text="可用" inactive-text="停用" inline-prompt
                       @change="(v) => onToggleVehicle(row, v)" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 时段管理 -->
    <el-card>
      <div class="mb-3 flex items-center justify-between">
        <span class="font-medium">试驾时段</span>
        <el-button type="primary" size="small" @click="slotDialog = true">批量生成时段</el-button>
      </div>

      <!-- 查询条件：车型 + 日期 -->
      <div class="mb-3 flex gap-2">
        <el-select v-model="queryModelId" placeholder="选择车型" class="w-56" @change="loadDaySlots">
          <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
        </el-select>
        <el-date-picker v-model="queryDate" type="date" value-format="YYYY-MM-DD"
                        placeholder="选择日期" class="w-40" @change="loadDaySlots" />
      </div>

      <el-table :data="daySlots" size="small" border>
        <el-table-column prop="time_slot" label="时段" width="100" />
        <el-table-column prop="capacity" label="容量" width="80" align="center" />
        <el-table-column prop="booked_count" label="已约" width="80" align="center" />
        <el-table-column label="剩余" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.remaining > 0 ? 'success' : 'danger'" size="small">{{ row.remaining }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <p v-if="!daySlots.length" class="py-4 text-center text-xs text-gray-400">当日暂无时段，请批量生成</p>
    </el-card>

    <!-- 新增试驾车对话框 -->
    <el-dialog v-model="vehicleDialog" title="新增试驾车" width="420px">
      <el-form label-width="80px">
        <el-form-item label="车牌号" required>
          <el-input v-model="vehicleForm.plate_no" placeholder="如 沪A·D0001" />
        </el-form-item>
        <el-form-item label="所属车型" required>
          <el-select v-model="vehicleForm.model_id" placeholder="选择车型" class="w-full">
            <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="vehicleDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onCreateVehicle">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量生成时段对话框 -->
    <el-dialog v-model="slotDialog" title="批量生成时段" width="480px">
      <el-form label-width="90px">
        <el-form-item label="车型" required>
          <el-select v-model="slotForm.model_id" placeholder="选择车型" class="w-full">
            <el-option v-for="m in models" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围" required>
          <el-date-picker v-model="slotForm.range" type="daterange" value-format="YYYY-MM-DD"
                          start-placeholder="开始日期" end-placeholder="结束日期" class="w-full" />
        </el-form-item>
        <el-form-item label="时段" required>
          <el-checkbox-group v-model="slotForm.time_slots">
            <el-checkbox v-for="h in HOURS" :key="h" :value="h" class="!mr-3">{{ h }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="每时段容量">
          <el-input-number v-model="slotForm.capacity" :min="1" :max="20" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="slotDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onGenerate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 数据流：车型列表（下拉用）→ 试驾车表 + 某日时段表；生成后若日期匹配则刷新
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  adminFetchModels, adminFetchVehicles, adminCreateVehicle, adminUpdateVehicle,
  adminBatchSlots, adminFetchDaySlots
} from '@/api/admin'

// 可选整点时段（1 小时粒度）
const HOURS = ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00', '17:00']

const models = ref([])
const vehicles = ref([])
const daySlots = ref([])
const queryModelId = ref(null)
const queryDate = ref(new Date().toISOString().slice(0, 10))
const saving = ref(false)
const vehicleDialog = ref(false)
const slotDialog = ref(false)
const vehicleForm = reactive({ plate_no: '', model_id: null })
const slotForm = reactive({ model_id: null, range: null, time_slots: ['10:00', '11:00', '14:00', '15:00'], capacity: 2 })

async function loadVehicles() {
  const data = await adminFetchVehicles()
  vehicles.value = data.items
}

async function loadDaySlots() {
  if (!queryModelId.value || !queryDate.value) {
    daySlots.value = []
    return
  }
  const data = await adminFetchDaySlots(queryModelId.value, queryDate.value)
  daySlots.value = data.items
}

async function onToggleVehicle(row, available) {
  await adminUpdateVehicle(row.id, available ? 'available' : 'disabled')
  ElMessage.success('已更新')
  await loadVehicles()
}

async function onCreateVehicle() {
  if (!vehicleForm.plate_no || !vehicleForm.model_id) {
    ElMessage.warning('请填写完整信息')
    return
  }
  saving.value = true
  try {
    await adminCreateVehicle(vehicleForm)
    ElMessage.success('创建成功')
    vehicleDialog.value = false
    vehicleForm.plate_no = ''
    await loadVehicles()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

// 日期范围展开为日期列表（含首尾，上限 31 天）
function expandDates(range) {
  const [start, end] = range
  const dates = []
  const current = new Date(start)
  const last = new Date(end)
  while (current <= last && dates.length < 31) {
    dates.push(current.toISOString().slice(0, 10))
    current.setDate(current.getDate() + 1)
  }
  return dates
}

async function onGenerate() {
  if (!slotForm.model_id || !slotForm.range || !slotForm.time_slots.length) {
    ElMessage.warning('请填写完整信息')
    return
  }
  saving.value = true
  try {
    const data = await adminBatchSlots({
      model_id: slotForm.model_id,
      dates: expandDates(slotForm.range),
      time_slots: slotForm.time_slots,
      capacity: slotForm.capacity
    })
    ElMessage.success(`已生成 ${data.created} 个时段（已存在的自动跳过）`)
    slotDialog.value = false
    await loadDaySlots()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  const data = await adminFetchModels({ page_size: 100 })
  models.value = data.items
  queryModelId.value = models.value[0]?.id ?? null
  await loadVehicles()
  await loadDaySlots()
})
</script>
