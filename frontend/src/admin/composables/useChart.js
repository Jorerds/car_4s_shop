// ECharts 挂载封装：组件卸载时销毁实例，避免内存泄漏
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'

/**
 * 图表组合式函数
 * @param elRef 容器元素 ref
 * @param getOption 获取 ECharts 配置（数据变化时自动重新渲染）
 */
export function useChart(elRef, getOption) {
  const chart = shallowRef(null)

  function render() {
    if (!elRef.value) return
    if (!chart.value) {
      chart.value = echarts.init(elRef.value)
    }
    chart.value.setOption(getOption(), true)
  }

  function resize() {
    chart.value?.resize()
  }

  onMounted(() => {
    render()
    window.addEventListener('resize', resize)
  })
  // 数据变化自动重绘
  watch(getOption, render, { deep: true })
  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    chart.value?.dispose()
  })

  return { render }
}
