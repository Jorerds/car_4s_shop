<!-- 配置参数编辑对话框：六组分组维护，保存时整体替换 -->
<template>
  <el-dialog :model-value="show" title="配置参数" width="640px"
             @update:model-value="$emit('update:show', $event)" @open="onOpen">
    <div v-for="group in GROUPS" :key="group" class="mb-4">
      <p class="mb-2 text-[13px] font-medium">{{ group }}</p>
      <div v-for="(row, idx) in grouped[group]" :key="idx" class="mb-2 flex gap-2">
        <el-input v-model="row.param_name" placeholder="参数名" class="w-2/5" />
        <el-input v-model="row.param_value" placeholder="参数值" />
        <el-button link type="danger" @click="grouped[group].splice(idx, 1)">删除</el-button>
      </div>
      <el-button link type="primary" size="small" @click="grouped[group].push({ param_name: '', param_value: '' })">
        + 添加参数
      </el-button>
    </div>
    <template #footer>
      <el-button @click="$emit('update:show', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
// 六组固定顺序；行内编辑，保存前校验参数名/值非空后整体提交
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminFetchModelDetail, adminReplaceConfigs } from '@/api/admin'

const GROUPS = ['动力', '底盘', '车身', '安全', '舒适', '科技']

const props = defineProps({ show: Boolean, modelId: Number })
const emit = defineEmits(['update:show', 'saved'])

const grouped = reactive(Object.fromEntries(GROUPS.map((g) => [g, []])))
const saving = ref(false)

async function onOpen() {
  // 每次打开拉取最新配置（含停售车，走管理端详情接口）
  const detail = await adminFetchModelDetail(props.modelId)
  for (const g of GROUPS) {
    grouped[g] = (detail.configs[g] ?? []).map((i) => ({ ...i }))
  }
}

async function onSave() {
  // 扁平化六组数据，过滤未填完整的行
  const configs = GROUPS.flatMap((g) =>
    grouped[g]
      .filter((r) => r.param_name.trim() && r.param_value.trim())
      .map((r) => ({ group_name: g, param_name: r.param_name.trim(), param_value: r.param_value.trim() }))
  )
  saving.value = true
  try {
    await adminReplaceConfigs(props.modelId, configs)
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
