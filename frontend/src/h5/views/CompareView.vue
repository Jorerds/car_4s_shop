<!-- 车型对比页：2-3 款参数横向对齐，差异项高亮，支持移除与预约入口 -->
<template>
  <div>
    <header class="flex items-center justify-between border-b border-hairline px-4 py-3">
      <h1 class="text-[15px] font-semibold">车型对比</h1>
      <button v-if="compare.modelIds.length" class="text-[12px] text-ink-faint" @click="onClear">清空</button>
    </header>

    <!-- 空状态引导 -->
    <div v-if="compare.modelIds.length < 2" class="px-4 py-16 text-center">
      <p class="text-[13px] text-ink-secondary">请选择 2-3 款车型进行对比</p>
      <router-link to="/models" class="mt-4 inline-block bg-sea px-6 py-2 text-[13px] text-white">去选车型</router-link>
    </div>

    <p v-else-if="loading" class="py-20 text-center text-[12px] text-ink-faint">加载中…</p>

    <!-- 对比表：首列固定，横向滑动 -->
    <div v-else-if="data" class="no-scrollbar overflow-x-auto">
      <table class="w-full border-collapse text-[13px]" :style="{ minWidth: `${140 + data.models.length * 150}px` }">
        <!-- 表头：车型卡片 -->
        <thead>
          <tr>
            <th class="sticky left-0 z-10 w-[140px] bg-white p-3 text-left align-bottom"></th>
            <th v-for="m in data.models" :key="m.id" class="p-3 align-bottom">
              <img v-if="m.main_image" :src="m.main_image" :alt="m.name" class="aspect-[4/3] w-full bg-mist object-cover" />
              <div v-else class="flex aspect-[4/3] w-full items-center justify-center bg-mist text-[11px] text-ink-faint">车型图</div>
              <p class="mt-2 text-left text-[14px] font-semibold">{{ m.name }}</p>
              <p class="num mt-0.5 text-left text-[13px] text-sea">¥{{ formatPrice(m.guide_price) }} 起</p>
              <p class="mt-0.5 text-left text-[11px] text-ink-faint">{{ m.energy_type }} · {{ m.body_type }}</p>
              <div class="mt-2 flex gap-1">
                <router-link :to="`/models/${m.id}/appointment`" class="flex-1 bg-sea py-1.5 text-center text-[12px] text-white">预约试驾</router-link>
                <button class="border border-hairline px-2 py-1.5 text-[12px] text-ink-secondary" @click="onRemove(m.id)">移除</button>
              </div>
            </th>
          </tr>
        </thead>
        <!-- 参数体：六组分组，差异项数值高亮 -->
        <tbody v-for="group in GROUPS" :key="group">
          <tr v-if="rowsOf(group).length">
            <td colspan="100%" class="sticky left-0 bg-mist px-3 py-1.5 text-[11px] tracking-[0.15em] text-ink-faint">
              ── {{ group }} ──
            </td>
          </tr>
          <tr v-for="row in rowsOf(group)" :key="row.param_name" class="border-t border-hairline">
            <td class="sticky left-0 z-10 bg-white px-3 py-2 text-ink-secondary">{{ row.param_name }}</td>
            <td v-for="(value, i) in row.values" :key="i"
                class="num px-3 py-2 font-medium"
                :class="row.is_diff ? 'text-sea' : 'text-ink'">
              {{ value ?? '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
// 进入页面即按对比栏 ID 拉取对齐数据；少于 2 款给引导；车型下架后端返回 404，提示并清空
import { ref, computed, watch } from 'vue'
import { compareModels } from '@/api/models'
import { useCompareStore } from '@/stores/compare'
import { useToast } from '../composables/useToast'
import { formatPrice } from '@/utils/format'

const GROUPS = ['动力', '底盘', '车身', '安全', '舒适', '科技']

const compare = useCompareStore()
const toast = useToast()

const data = ref(null)
const loading = ref(false)

const rowsOf = (group) => data.value.rows.filter((r) => r.group === group)

async function load() {
  if (compare.modelIds.length < 2) {
    data.value = null
    return
  }
  loading.value = true
  try {
    data.value = await compareModels(compare.modelIds)
  } catch {
    toast('部分车型已停售，请重新选择')
    compare.clear()
  } finally {
    loading.value = false
  }
}

function onRemove(id) {
  compare.remove(id)
  // 剩余不足 2 款时清空对比结果
  if (compare.modelIds.length < 2) data.value = null
}

function onClear() {
  compare.clear()
  data.value = null
}

// 对比栏变化（从其他页面增删）自动重载
watch(() => [...compare.modelIds], load)
load()
</script>
