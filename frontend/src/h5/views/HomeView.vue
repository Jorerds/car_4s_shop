<!-- 首页：光影画廊风格，接入真实车型接口（主推=列表第一款，在售车型横向滑动） -->
<template>
  <div>
    <!-- 顶栏 -->
    <header class="flex items-center justify-between border-b border-hairline px-4 py-3">
      <h1 class="text-[15px] font-semibold tracking-wide">星辉汽车 · 在线展厅</h1>
      <router-link to="/models" class="text-[12px] text-ink-faint">全部车型 ›</router-link>
    </header>

    <p v-if="loading" class="py-20 text-center text-[12px] text-ink-faint">加载中…</p>
    <p v-else-if="!featured" class="py-20 text-center text-[12px] text-ink-faint">暂无在售车型</p>

    <template v-else>
      <!-- 主推车型 -->
      <section class="px-4 pt-4">
        <img v-if="featured.main_image" :src="featured.main_image" :alt="featured.name"
             class="aspect-[16/9] w-full bg-mist object-cover" />
        <div v-else class="flex aspect-[16/9] w-full items-center justify-center bg-mist text-[12px] text-ink-faint">车辆大图</div>
        <div class="mt-3 flex items-baseline justify-between">
          <h2 class="text-[19px] font-semibold">{{ featured.name }}</h2>
          <p class="num text-sea">
            <span class="text-[13px]">¥</span><span class="text-[20px] font-semibold">{{ formatPrice(featured.guide_price) }}</span><span class="text-[12px]"> 起</span>
          </p>
        </div>
        <p class="mt-1 text-[12px] text-ink-secondary">{{ featured.energy_type }} · {{ featured.body_type }}</p>
        <div class="mt-3 grid grid-cols-2 gap-2">
          <router-link :to="`/models/${featured.id}`" class="border border-sea py-2 text-center text-[13px] text-sea">查看详情</router-link>
          <router-link :to="`/models/${featured.id}/appointment`" class="bg-sea py-2 text-center text-[13px] text-white">预约试驾</router-link>
        </div>
      </section>

      <!-- 在售车型：横向滑动卡片 -->
      <section class="mt-6">
        <div class="flex items-baseline justify-between px-4">
          <h3 class="text-[15px] font-semibold">在售车型</h3>
          <router-link to="/models" class="text-[12px] text-ink-faint">全部 ›</router-link>
        </div>
        <div class="no-scrollbar mt-3 flex gap-3 overflow-x-auto px-4 pb-2">
          <router-link v-for="m in models" :key="m.id" :to="`/models/${m.id}`" class="w-40 shrink-0">
            <img v-if="m.main_image" :src="m.main_image" :alt="m.name" class="aspect-[4/3] w-full bg-mist object-cover" />
            <div v-else class="flex aspect-[4/3] w-full items-center justify-center bg-mist text-[11px] text-ink-faint">车型图</div>
            <p class="mt-2 text-[13px] font-medium">{{ m.name }}</p>
            <p class="mt-0.5 text-[11px] text-ink-faint">{{ m.energy_type }} · {{ m.body_type }}</p>
            <p class="num mt-0.5 text-[13px] text-sea">¥{{ formatPrice(m.guide_price) }} 起</p>
          </router-link>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
// 首页数据来自 C 端列表接口：主推取排序后第一款
import { ref, computed, onMounted } from 'vue'
import { fetchModels } from '@/api/models'
import { formatPrice } from '@/utils/format'

const models = ref([])
const loading = ref(true)

// 主推车型：列表第一项
const featured = computed(() => models.value[0] ?? null)

onMounted(async () => {
  try {
    const data = await fetchModels({ sort: 'newest', page_size: 10 })
    models.value = data.items
  } finally {
    loading.value = false
  }
})
</script>
