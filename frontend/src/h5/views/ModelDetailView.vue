<!-- 车型详情页：图册 + 基础信息 + 工程图纸式六组配置 + 底部预约入口 -->
<template>
  <!-- 底部留白 = 标签栏(56px) + CTA 区高度，避免遮挡配置表末尾 -->
  <div v-if="detail" class="pb-32">
    <!-- 返回栏 -->
    <header class="flex items-center border-b border-hairline px-2 py-2.5">
      <button class="px-2 text-[15px] text-ink-secondary" @click="$router.back()">‹ 返回</button>
    </header>

    <!-- 图册：横向滑动 -->
    <div class="no-scrollbar flex snap-x snap-mandatory overflow-x-auto">
      <img v-for="url in detail.images" :key="url" :src="url" :alt="detail.name"
           class="aspect-[16/9] w-full shrink-0 snap-center bg-mist object-cover" />
      <div v-if="!detail.images.length" class="flex aspect-[16/9] w-full items-center justify-center bg-mist text-[12px] text-ink-faint">
        车辆大图
      </div>
    </div>

    <!-- 基础信息 -->
    <section class="px-4 pt-3">
      <div class="flex items-baseline justify-between">
        <h1 class="text-[19px] font-semibold">{{ detail.name }}</h1>
        <p class="num text-sea">
          <span class="text-[13px]">¥</span><span class="text-[20px] font-semibold">{{ formatPrice(detail.guide_price) }}</span><span class="text-[12px]"> 起</span>
        </p>
      </div>
      <p class="mt-1 text-[12px] text-ink-secondary">
        {{ detail.brand }} {{ detail.series }} · {{ detail.energy_type }} · {{ detail.body_type }}
      </p>
    </section>

    <!-- 配置参数：工程图纸式分栏，六组固定顺序 -->
    <section v-for="group in GROUPS" :key="group" class="mt-5 px-4">
      <template v-if="detail.configs[group]?.length">
        <p class="label-tech">── {{ group }} ──</p>
        <div class="mt-1 divide-y divide-hairline border-y border-hairline">
          <div v-for="item in detail.configs[group]" :key="item.param_name"
               class="flex justify-between py-2 text-[13px]">
            <span class="text-ink-secondary">{{ item.param_name }}</span>
            <span class="num font-medium">{{ item.param_value }}</span>
          </div>
        </div>
      </template>
    </section>

    <!-- 底部固定 CTA：加入对比 + 预约试驾，悬浮于标签栏上方 -->
    <div class="fixed bottom-14 left-1/2 w-full max-w-md -translate-x-1/2 border-t border-hairline bg-white p-3">
      <div class="grid grid-cols-2 gap-2">
        <button class="border py-2.5 text-[14px]"
                :class="compare.modelIds.includes(detail.id) ? 'border-sea text-sea' : 'border-hairline text-ink-secondary'"
                @click="onToggleCompare">{{ compare.modelIds.includes(detail.id) ? '已加入对比' : '加入对比' }}</button>
        <router-link :to="`/models/${detail.id}/appointment`"
                     class="bg-sea py-2.5 text-center text-[14px] text-white">预约试驾</router-link>
      </div>
    </div>
  </div>
  <p v-else class="py-20 text-center text-[12px] text-ink-faint">{{ errorText }}</p>
</template>

<script setup>
// 六组配置展示顺序固定，与后端 CONFIG_GROUPS 一致
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { fetchModelDetail, recordView } from '@/api/models'
import { useCompareStore } from '@/stores/compare'
import { useToast } from '../composables/useToast'
import { formatPrice } from '@/utils/format'

const GROUPS = ['动力', '底盘', '车身', '安全', '舒适', '科技']

const route = useRoute()
const compare = useCompareStore()
const toast = useToast()
const detail = ref(null)
const errorText = ref('加载中…')

onMounted(async () => {
  try {
    detail.value = await fetchModelDetail(route.params.id)
    // 浏览埋点：不计入页面加载失败的情况
    recordView(route.params.id).catch(() => {})
  } catch {
    errorText.value = '车型不存在或已停售'
  }
})

// 加入/移出对比栏，超限提示（与对比页 2-3 款限制一致）
function onToggleCompare() {
  const id = detail.value.id
  if (compare.modelIds.includes(id)) {
    compare.remove(id)
    return
  }
  if (!compare.add(id)) {
    toast('最多同时对比 3 款车型')
  }
}
</script>
