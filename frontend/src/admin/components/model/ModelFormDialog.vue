<!-- 车型表单对话框：新增 / 编辑车型（编辑时可调整销售状态） -->
<template>
  <el-dialog :model-value="show" :title="isEdit ? '编辑车型' : '新增车型'" width="480px"
             @update:model-value="$emit('update:show', $event)" @open="onOpen">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="车型名称" prop="name"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="品牌" prop="brand"><el-input v-model="form.brand" /></el-form-item>
      <el-form-item label="车系" prop="series"><el-input v-model="form.series" /></el-form-item>
      <el-form-item label="指导价" prop="guide_price">
        <el-input-number v-model="form.guide_price" :min="1" :step="1000" class="w-full" controls-position="right" />
      </el-form-item>
      <el-form-item label="车身类型" prop="body_type"><el-input v-model="form.body_type" placeholder="轿车 / SUV / MPV 等" /></el-form-item>
      <el-form-item label="能源类型" prop="energy_type"><el-input v-model="form.energy_type" placeholder="燃油 / 纯电 / 混动 等" /></el-form-item>
      <el-form-item v-if="isEdit" label="销售状态">
        <el-switch v-model="onSale" active-text="在售" inactive-text="停售" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:show', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
// 新增/编辑共用：传入 model 为编辑态；保存成功后通知父组件刷新列表
import { reactive, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { adminCreateModel, adminUpdateModel } from '@/api/admin'

const props = defineProps({ show: Boolean, model: Object })
const emit = defineEmits(['update:show', 'saved'])

const formRef = ref()
const saving = ref(false)
const form = reactive({ name: '', brand: '', series: '', guide_price: 100000, body_type: '', energy_type: '' })
const onSale = ref(true)

const isEdit = computed(() => Boolean(props.model))

// 必填校验：与后端字段限制保持一致
const rules = {
  name: [{ required: true, message: '请输入车型名称', trigger: 'blur' }],
  brand: [{ required: true, message: '请输入品牌', trigger: 'blur' }],
  series: [{ required: true, message: '请输入车系', trigger: 'blur' }],
  guide_price: [{ required: true, message: '请输入指导价', trigger: 'blur' }],
  body_type: [{ required: true, message: '请输入车身类型', trigger: 'blur' }],
  energy_type: [{ required: true, message: '请输入能源类型', trigger: 'blur' }]
}

function onOpen() {
  // 打开时回填：编辑态用传入车型，新增态重置
  const m = props.model
  form.name = m?.name ?? ''
  form.brand = m?.brand ?? ''
  form.series = m?.series ?? ''
  form.guide_price = m?.guide_price ?? 100000
  form.body_type = m?.body_type ?? ''
  form.energy_type = m?.energy_type ?? ''
  onSale.value = m?.status !== 'off_sale'
}

async function onSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value) {
      await adminUpdateModel(props.model.id, { ...form, status: onSale.value ? 'on_sale' : 'off_sale' })
    } else {
      await adminCreateModel(form)
    }
    ElMessage.success('保存成功')
    emit('update:show', false)
    emit('saved')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}
</script>
