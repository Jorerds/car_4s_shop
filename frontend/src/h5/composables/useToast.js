// 轻量 Toast 提示（H5 无组件库，画廊风格用底部浮层）
import { ref } from 'vue'

const message = ref('')
let timer = null

export function useToast() {
  /** 展示提示，2 秒后自动消失 */
  return function toast(text) {
    message.value = text
    clearTimeout(timer)
    timer = setTimeout(() => (message.value = ''), 2000)
  }
}

export const toastMessage = message
