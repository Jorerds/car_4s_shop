<!-- 统计报表：四类报表页签 + 日期范围 + ECharts 图表 + 表格 + Excel/CSV 导出 -->
<template>
  <div>
    <!-- 公共工具栏：日期范围 + 导出 -->
    <div class="mb-4 flex items-center justify-between">
      <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD"
                      start-placeholder="开始日期" end-placeholder="结束日期"
                      :clearable="false" class="w-72" @change="load" />
      <div class="flex gap-2">
        <el-button size="small" :loading="exporting" @click="onExport('excel')">导出 Excel</el-button>
        <el-button size="small" :loading="exporting" @click="onExport('csv')">导出 CSV</el-button>
      </div>
    </div>

    <el-tabs v-model="tab" @tab-change="load">
      <!-- 预约/转化 -->
      <el-tab-pane label="预约/转化" name="booking" lazy>
        <div class="grid grid-cols-3 gap-4">
          <el-card shadow="never"><p class="text-gray-400">预约总量</p><p class="num mt-1 text-2xl font-semibold">{{ booking.total }}</p></el-card>
          <el-card shadow="never"><p class="text-gray-400">到店试驾</p><p class="num mt-1 text-2xl font-semibold">{{ funnelValue(2) }}</p></el-card>
          <el-card shadow="never"><p class="text-gray-400">爽约率</p><p class="num mt-1 text-2xl font-semibold">{{ booking.no_show_rate }}%</p></el-card>
        </div>
        <div class="mt-4 grid grid-cols-2 gap-4">
          <el-card shadow="never"><div ref="trendChartEl" class="h-72" /></el-card>
          <el-card shadow="never"><div ref="funnelChartEl" class="h-72" /></el-card>
        </div>
      </el-tab-pane>

      <!-- 销售业绩 -->
      <el-tab-pane label="销售业绩" name="sales" lazy>
        <div class="grid grid-cols-2 gap-4">
          <el-card shadow="never"><div ref="salesChartEl" class="h-80" /></el-card>
          <el-card shadow="never">
            <el-table :data="salesItems" size="small" border>
              <el-table-column prop="sales_name" label="销售" min-width="90" />
              <el-table-column prop="follow_ups" label="跟进量" width="80" align="center" />
              <el-table-column prop="confirmed" label="确认数" width="80" align="center" />
              <el-table-column prop="completed" label="试驾完成" width="90" align="center" />
              <el-table-column prop="deals" label="成交量" width="80" align="center" />
              <el-table-column label="确认率" width="90" align="center">
                <template #default="{ row }"><span class="num">{{ row.confirm_rate }}%</span></template>
              </el-table-column>
            </el-table>
            <p v-if="!salesItems.length" class="py-8 text-center text-xs text-gray-400">暂无数据</p>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 客户 -->
      <el-tab-pane label="客户" name="customer" lazy>
        <div class="grid grid-cols-2 gap-4">
          <el-card shadow="never"><div ref="customerChartEl" class="h-80" /></el-card>
          <el-card shadow="never"><div ref="customerPieEl" class="h-80" /></el-card>
        </div>
      </el-tab-pane>

      <!-- 车型热度 -->
      <el-tab-pane label="车型热度" name="model" lazy>
        <el-card shadow="never"><div ref="modelChartEl" class="h-80" /></el-card>
        <el-table class="mt-4" :data="modelItems" size="small" border>
          <el-table-column type="index" label="排名" width="70" align="center" />
          <el-table-column prop="model_name" label="车型" min-width="140" />
          <el-table-column prop="views" label="浏览量" width="100" align="center" />
          <el-table-column prop="compares" label="对比次数" width="100" align="center" />
          <el-table-column prop="appointments" label="预约量" width="100" align="center" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
// 四类报表共用一个日期范围；切换页签或改日期即重新加载；导出按当前页签与范围生成
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchBookingReport, fetchSalesReport, fetchCustomerReport,
  fetchModelReport, exportReport
} from '@/api/reports'
import { useChart } from '../composables/useChart'

const SEA = '#17324F'

// 默认近 30 天
function defaultRange() {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 29)
  const fmt = (d) => d.toISOString().slice(0, 10)
  return [fmt(start), fmt(end)]
}

const tab = ref('booking')
const range = ref(defaultRange())
const exporting = ref(false)

const booking = ref({ trend: [], status_counts: [], funnel: [], total: 0, no_show_rate: 0 })
const salesItems = ref([])
const customer = ref({ trend: [], status_dist: [] })
const modelItems = ref([])

const rangeParams = computed(() => ({ start: range.value[0], end: range.value[1] }))
const funnelValue = (i) => booking.value.funnel[i]?.value ?? 0

async function load() {
  // 页签切换后图表容器尺寸变化，触发 resize 自适应
  requestAnimationFrame(() => window.dispatchEvent(new Event("resize")))
  const params = rangeParams.value
  try {
    if (tab.value === 'booking') {
      booking.value = await fetchBookingReport(params)
    } else if (tab.value === 'sales') {
      salesItems.value = (await fetchSalesReport(params)).items
    } else if (tab.value === 'customer') {
      customer.value = await fetchCustomerReport(params)
    } else {
      modelItems.value = (await fetchModelReport(params)).items
    }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

// 导出当前页签报表，新窗口下载文件
async function onExport(format) {
  exporting.value = true
  try {
    const { url } = await exportReport(tab.value, { ...rangeParams.value, format })
    window.open(url, '_blank')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    exporting.value = false
  }
}

// ---- 图表配置 ----

const trendChartEl = ref(null)
const funnelChartEl = ref(null)
const salesChartEl = ref(null)
const customerChartEl = ref(null)
const customerPieEl = ref(null)
const modelChartEl = ref(null)

useChart(trendChartEl, () => ({
  title: { text: '预约量趋势', textStyle: { fontSize: 14 } },
  tooltip: {},
  xAxis: { type: 'category', data: booking.value.trend.map((r) => r.date.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ type: 'line', smooth: true, data: booking.value.trend.map((r) => r.count), areaStyle: {}, itemStyle: { color: SEA } }]
}))

useChart(funnelChartEl, () => ({
  title: { text: '转化漏斗', textStyle: { fontSize: 14 } },
  tooltip: {},
  series: [{
    type: 'funnel', left: '10%', width: '80%',
    data: booking.value.funnel.map((f) => ({ name: f.stage, value: f.value })),
    label: { formatter: '{b}: {c}' },
    itemStyle: { color: SEA }
  }]
}))

useChart(salesChartEl, () => ({
  title: { text: '成交量排行', textStyle: { fontSize: 14 } },
  tooltip: {},
  grid: { left: 90 },
  xAxis: { type: 'value', minInterval: 1 },
  yAxis: { type: 'category', data: salesItems.value.map((r) => r.sales_name).reverse() },
  series: [{ type: 'bar', data: salesItems.value.map((r) => r.deals).reverse(), itemStyle: { color: SEA } }]
}))

useChart(customerChartEl, () => ({
  title: { text: '新增客户趋势', textStyle: { fontSize: 14 } },
  tooltip: {},
  xAxis: { type: 'category', data: customer.value.trend.map((r) => r.date.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ type: 'bar', data: customer.value.trend.map((r) => r.count), itemStyle: { color: SEA } }]
}))

useChart(customerPieEl, () => ({
  title: { text: '客户状态分布', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'item' },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: customer.value.status_dist.map((d) => ({ name: d.label, value: d.count })),
    label: { formatter: '{b}: {c}' }
  }]
}))

useChart(modelChartEl, () => ({
  title: { text: '车型热度（浏览 / 对比 / 预约）', textStyle: { fontSize: 14 } },
  tooltip: {},
  legend: {},
  xAxis: { type: 'category', data: modelItems.value.map((r) => r.model_name) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    { name: '浏览量', type: 'bar', data: modelItems.value.map((r) => r.views), itemStyle: { color: SEA } },
    { name: '对比次数', type: 'bar', data: modelItems.value.map((r) => r.compares), itemStyle: { color: '#7388A0' } },
    { name: '预约量', type: 'bar', data: modelItems.value.map((r) => r.appointments), itemStyle: { color: '#A2B2C4' } }
  ]
}))

onMounted(load)
</script>
