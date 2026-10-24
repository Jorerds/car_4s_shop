<!-- 管理端根组件：仅承载路由出口；全局配置 Element Plus 中文语言包 -->
<template>
  <el-config-provider :locale="zhCn">
    <router-view />
  </el-config-provider>
</template>

<script setup>
// 按项目规范统一使用 Element Plus 中文语言包
import zhCn from 'element-plus/es/locale/lang/zh-cn'
</script>
