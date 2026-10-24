<!-- 车型列表页：品牌/能源/价格筛选 + 排序 + 卡片列表 + 加入对比（光影画廊风格） -->
<template>
  <div>
    <!-- 筛选区：滚片式筛选，激活项深海蓝实底 -->
    <div class="space-y-2 border-b border-hairline px-4 py-3">
      <div class="no-scrollbar flex gap-2 overflow-x-auto whitespace-nowrap text-[12px]">
        <button
          v-for="b in ['全部', ...brands]" :key="b"
          class="rounded-full border px-3 py-1"
          :class="chipClass(filters.brand === normBrand(b))"
          @click="filters.brand = normBrand(b)"
        >{{ b }}</button>
      </div>
      <div class="no-scrollbar flex gap-2 overflow-x-auto whitespace-nowrap text-[12px]">
        <button
          v-for="e in ['全部', '纯电', '混动', '燃油']" :key="e"
          class="rounded-full border px-3 py-1"
          :class="chipClass(filters.energy_type === normEnergy(e))"
          @click="filters.energy_type = normEnergy(e)"
        >{{ e }}</button>
      </div>
      <div class="flex items-center justify-between text-[12px]">
        <div class="no-scrollbar flex gap-2 overflow-x-auto whitespace-nowrap">
          <button
            v-for="p in PRICE_CHIPS" :key="p.label"
            class="rounded-full border px-3 py-1"
            :class="chipClass(activePriceLabel === p.label)"
            @click="onPriceChip(p)"
          >{{ p.label }}</button>
        </div>
        <div class="flex shrink-0 gap-2 pl-2 text-ink-secondary">
          <button v-for="s in SORTS" :key="s.value"
                  :class="filters.sort === s.value ? 'font-medium text-sea' : ''"
                  @click="filters.sort = s.value">{{ s.label }}</button>
        </div>
      </div>
    </div>

    <!-- 列表状态 -->
    <p v-if="loading" class="py-10 text-center text-[12px] text-ink-faint">加载中…</p>
    <p v-else-if="!items.length" class="py-10 text-center text-[12px] text-ink-faint">暂无符合条件的车型</p>

    <!-- 车型卡片 -->
    <div v-else class="divide-y divide-hairline">
      <div v-for="m in items" :key="m.id" class="flex gap-3 px-4 py-3">
        <router-link :to="`/models/${m.id}`" class="w-32 shrink-0">
          <img v-if="m.main_image" :src="m.main_image" :alt="m.name" class="aspect-[4/3] w-full bg-mist object-cover" />
          <div v-else class="flex aspect-[4/3] w-full items-center justify-center bg-mist text-[11px] text-ink-faint">车型图</div>
        </router-link>
        <div class="flex flex-1 flex-col">
          <router-link :to="`/models/${m.id}`">
            <p class="text-[15px] font-semibold">{{ m.name }}</p>
            <p class="mt-0.5 text-[12px] text-ink-faint">{{ m.energy_type }} · {{ m.body_type }}</p>
          </router-link>
          <div class="mt-auto flex items-end justify-between">
            <p class="num text-[15px] font-medium text-sea">
              <span class="text-[12px]">¥</span>{{ formatPrice(m.guide_price) }}<span class="text-[12px]"> 起</span>
            </p>
            <button
              class="rounded-full border px-3 py-1 text-[12px]"
              :class="compare.modelIds.includes(m.id) ? 'border-sea text-sea' : 'border-hairline text-ink-secondary'"
              @click="onToggleCompare(m)"
            >{{ compare.modelIds.includes(m.id) ? '已加入对比' : '加入对比' }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 筛选状态变化即重新加载；价格区间由三段芯片映射为 min/max 参数
import { reactive, ref, watch, onMounted } from 'vue'
import { useToast } from '../composables/useToast'
import { fetchModels, fetchModelFilters } from '@/api/models'
import { useCompareStore } from '@/stores/compare'
import { formatPrice } from '@/utils/format'

const toast = useToast()
const compare = useCompareStore()

const brands = ref([])
const items = ref([])
const loading = ref(false)

const PRICE_CHIPS = [
  { label: '全部价格', min: null, max: null },
  { label: '15万以下', min: null, max: 150000 },
  { label: '15-25万', min: 150000, max: 250000 },
  { label: '25万以上', min: 250000, max: null }
]
const SORTS = [
  { label: '最新', value: 'newest' },
  { label: '价格 ↑', value: 'price_asc' },
  { label: '价格 ↓', value: 'price_desc' }
]

const filters = reactive({ brand: null, energy_type: null, min_price: null, max_price: null, sort: 'newest' })

// '全部' 选项统一归一为 null
const normBrand = (b) => (b === '全部' ? null : b)
const normEnergy = (e) => (e === '全部' ? null : e)

const activePriceLabel = ref('全部价格')
function onPriceChip(p) {
  filters.min_price = p.min
  filters.max_price = p.max
  activePriceLabel.value = p.label
}

function chipClass(active) {
  return active ? 'border-sea bg-sea text-white' : 'border-hairline text-ink-secondary'
}

async function load() {
  loading.value = true
  try {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v !== null))
    const data = await fetchModels(params)
    items.value = data.items
  } finally {
    loading.value = false
  }
}

function onToggleCompare(model) {
  if (compare.modelIds.includes(model.id)) {
    compare.remove(model.id)
    return
  }
  // 超过 3 款给出提示，与 PRD 2-3 款对比限制一致
  if (!compare.add(model.id)) {
    toast('最多同时对比 3 款车型')
  }
}

watch(filters, load, { deep: true })
onMounted(async () => {
  load()
  const data = await fetchModelFilters()
  brands.value = data.brands
})
</script>
