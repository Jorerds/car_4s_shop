// 车型对比栏状态：支持 2-3 款，跨页面保持选择，并持久化到 localStorage
import { defineStore } from 'pinia'

const MAX_COMPARE = 3
const STORAGE_KEY = 'compareIds'

// 从本地存储恢复选择，刷新页面后对比栏不丢失
function loadIds() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch {
    return []
  }
}

function saveIds(ids) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
}

export const useCompareStore = defineStore('compare', {
  state: () => ({
    // 已选车型 ID 列表（只存 ID，详情数据进入对比页再拉取）
    modelIds: loadIds()
  }),
  actions: {
    // 加入对比，超过上限返回 false
    add(modelId) {
      if (this.modelIds.includes(modelId)) return true
      if (this.modelIds.length >= MAX_COMPARE) return false
      this.modelIds.push(modelId)
      saveIds(this.modelIds)
      return true
    },
    // 从对比栏移除
    remove(modelId) {
      this.modelIds = this.modelIds.filter((id) => id !== modelId)
      saveIds(this.modelIds)
    },
    // 清空对比栏
    clear() {
      this.modelIds = []
      saveIds([])
    }
  }
})
