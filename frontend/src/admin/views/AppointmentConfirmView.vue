<!-- 预约确认：状态页签列表 + 确认（选车）/拒绝（原因）/登记试驾结果 -->
<template>
  <div>
    <!-- 状态页签 -->
    <el-tabs v-model="status" @tab-change="load">
      <el-tab-pane label="待确认" name="pending" />
      <el-tab-pane label="已确认" name="confirmed" />
      <el-tab-pane label="已结束" name="finished" />
      <el-tab-pane label="已拒绝" name="rejected" />
    </el-tabs>

    <el-table :data="items" v-loading="loading" border>
      <el-table-column prop="id" label="单号" width="70" />
      <el-table-column label="车型" min-width="110">
        <template #default="{ row }">{{ row.model_name }}</template>
      </el-table-column>
      <el-table-column label="顾客" min-width="150">
        <template #default="{ row }">
          {{ row.customer_name }}<br /><span class="text-xs text-gray-400">{{ row.customer_phone }}</span>
        </template>
      </el-table-column>
      <el-table-column label="试驾时间" min-width="150">
        <template #default="{ row }">
          <span class="num">{{ row.slot_date }} {{ row.time_slot }}</span>
        </template>
      </el-table-column>
      <el-table-column label="车辆" width="110">
        <template #default="{ row }">{{ row.vehicle_plate || '—' }}</template>
      </el-table-column>
      <el-table-column label="备注" min-width="120">
        <template #default="{ row }">{{ row.remark || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <template v-if="row.status === 'pending'">
            <el-button link type="primary" size="small" @click="openConfirm(row)">确认</el-button>
            <el-button link type="danger" size="small" @click="openReject(row)">拒绝</el-button>
          </template>
          <el-button v-else-if="row.status === 'confirmed'" link type="primary" size="small"
                     @click="openRecord(row)">登记结果</el-button>
          <span v-else class="text-xs text-gray-400">
            {{ row.status === 'rejected' ? `已拒绝：${row.reject_reason || ''}` : '已结束' }}
          </span>
        </template>
      </el-table-column>
    </el-table>
    <p v-if="!items.length && !loading" class="py-8 text-center text-xs text-gray-400">暂无数据</p>

    <!-- 确认对话框：分配试驾车 -->
    <el-dialog v-model="confirmDialog" title="确认预约" width="420px">
      <p class="mb-3 text-sm text-gray-600">
        {{ active?.model_name }} · <span class="num">{{ active?.slot_date }} {{ active?.time_slot }}</span>
      </p>
      <el-select v-model="selectedVehicleId" placeholder="选择试驾车" class="w-full">
        <el-option v-for="v in vehicles" :key="v.id" :label="v.plate_no" :value="v.id" />
      </el-select>
      <p v-if="!vehicles.length" class="mt-2 text-xs text-red-500">该车型暂无可用试驾车，请先在试驾时段管理中登记</p>
      <template #footer>
        <el-button @click="confirmDialog = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedVehicleId" :loading="saving" @click="onConfirm">确认并通知</el-button>
      </template>
    </el-dialog>

    <!-- 拒绝对话框 -->
    <el-dialog v-model="rejectDialog" title="拒绝预约" width="420px">
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写拒绝原因（将通知顾客）" />
      <template #footer>
        <el-button @click="rejectDialog = false">取消</el-button>
        <el-button type="danger" :disabled="!rejectReason.trim()" :loading="saving" @click="onReject">拒绝并通知</el-button>
      </template>
    </el-dialog>

    <!-- 登记试驾结果对话框 -->
    <el-dialog v-model="recordDialog" title="登记试驾结果" width="420px">
      <el-form label-width="80px">
        <el-form-item label="结果">
          <el-radio-group v-model="recordForm.result">
            <el-radio value="completed">已完成</el-radio>
            <el-radio value="no_show">爽约</el-radio>
          </el-radio-group>
        </el-form-item>
        <template v-if="recordForm.result === 'completed'">
          <el-form-item label="顾客评分">
            <el-rate v-model="recordForm.feedback_score" />
          </el-form-item>
          <el-form-item label="顾客反馈">
            <el-input v-model="recordForm.feedback_text" type="textarea" :rows="3" placeholder="顾客评价（选填）" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="recordDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onRecord">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 数据流：页签切换加载对应状态；确认/拒绝/登记成功后回到当前页签刷新
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchSalesAppointments, fetchAssignableVehicles, confirmAppointment,
  rejectAppointment, recordTestDrive
} from '@/api/sales'

const status = ref('pending')
const items = ref([])
const loading = ref(false)
const saving = ref(false)

const confirmDialog = ref(false)
const rejectDialog = ref(false)
const recordDialog = ref(false)
const active = ref(null)
const vehicles = ref([])
const selectedVehicleId = ref(null)
const rejectReason = ref('')
const recordForm = reactive({ result: 'completed', feedback_score: null, feedback_text: '' })

async function load() {
  loading.value = true
  try {
    const data = await fetchSalesAppointments(status.value)
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function openConfirm(row) {
  active.value = row
  selectedVehicleId.value = null
  const data = await fetchAssignableVehicles(row.model_id)
  vehicles.value = data.items
  confirmDialog.value = true
}

async function onConfirm() {
  saving.value = true
  try {
    await confirmAppointment(active.value.id, selectedVehicleId.value)
    ElMessage.success('已确认并通知顾客')
    confirmDialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function openReject(row) {
  active.value = row
  rejectReason.value = ''
  rejectDialog.value = true
}

async function onReject() {
  saving.value = true
  try {
    await rejectAppointment(active.value.id, rejectReason.value.trim())
    ElMessage.success('已拒绝并通知顾客')
    rejectDialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function openRecord(row) {
  active.value = row
  recordForm.result = 'completed'
  recordForm.feedback_score = null
  recordForm.feedback_text = ''
  recordDialog.value = true
}

async function onRecord() {
  saving.value = true
  try {
    await recordTestDrive(active.value.id, {
      result: recordForm.result,
      feedback_score: recordForm.result === 'completed' ? recordForm.feedback_score : undefined,
      feedback_text: recordForm.feedback_text || undefined
    })
    ElMessage.success('登记成功')
    recordDialog.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

load()
</script>
