<!-- 车型管理：列表 + 搜索 + 新增/编辑 + 配置参数 + 图片管理 -->
<template>
  <div>
    <!-- 工具栏 -->
    <div class="mb-4 flex items-center justify-between">
      <el-input v-model="keyword" placeholder="搜索名称/品牌/车系" clearable class="w-72"
                @keyup.enter="onSearch" @clear="onSearch" />
      <el-button type="primary" @click="openCreate">新增车型</el-button>
    </div>

    <!-- 车型表格 -->
    <el-table :data="items" v-loading="loading" border>
      <el-table-column label="主图" width="100">
        <template #default="{ row }">
          <img v-if="row.main_image" :src="row.main_image" class="h-12 w-16 bg-gray-100 object-cover" />
          <span v-else class="text-xs text-gray-400">无图</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="车型名称" min-width="120" />
      <el-table-column label="品牌 / 车系" min-width="140">
        <template #default="{ row }">{{ row.brand }} / {{ row.series }}</template>
      </el-table-column>
      <el-table-column label="类型" min-width="120">
        <template #default="{ row }">{{ row.energy_type }} · {{ row.body_type }}</template>
      </el-table-column>
      <el-table-column label="指导价" width="110" align="right">
        <template #default="{ row }"><span class="num">¥{{ formatPrice(row.guide_price) }}</span></template>
      </el-table-column>
      <el-table-column label="状态" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.status === 'on_sale' ? 'success' : 'info'" size="small">
            {{ row.status === 'on_sale' ? '在售' : '停售' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" size="small" @click="openConfigs(row)">配置</el-button>
          <el-button link type="primary" size="small" @click="openImages(row)">图片</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination class="mt-4 justify-end" layout="total, prev, pager, next" :total="total"
                   v-model:current-page="page" :page-size="pageSize" @current-change="load" />

    <!-- 三个功能对话框 -->
    <ModelFormDialog v-model:show="formShow" :model="editing" @saved="load" />
    <ConfigDialog v-model:show="configShow" :model-id="activeId" @saved="load" />
    <ImageDialog v-model:show="imageShow" :model-id="activeId" @saved="load" />
  </div>
</template>

<script setup>
// 列表数据流：搜索/分页触发 load；编辑/配置/图片操作后通过 saved 事件刷新
import { ref, onMounted } from 'vue'
import { adminFetchModels } from '@/api/admin'
import { formatPrice } from '@/utils/format'
import ModelFormDialog from '../components/model/ModelFormDialog.vue'
import ConfigDialog from '../components/model/ConfigDialog.vue'
import ImageDialog from '../components/model/ImageDialog.vue'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const keyword = ref('')
const loading = ref(false)

const formShow = ref(false)
const editing = ref(null)
const configShow = ref(false)
const imageShow = ref(false)
const activeId = ref(null)

async function load() {
  loading.value = true
  try {
    const data = await adminFetchModels({ keyword: keyword.value || undefined, page: page.value, page_size: pageSize })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

function openCreate() {
  editing.value = null
  formShow.value = true
}

function openEdit(row) {
  editing.value = row
  formShow.value = true
}

function openConfigs(row) {
  activeId.value = row.id
  configShow.value = true
}

function openImages(row) {
  activeId.value = row.id
  imageShow.value = true
}

onMounted(load)
</script>
