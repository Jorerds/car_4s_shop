// 展示格式化工具

/** 价格（元）→ 千分位字符串，如 189900 → "189,900" */
export function formatPrice(yuan) {
  return (yuan ?? 0).toLocaleString('zh-CN')
}
