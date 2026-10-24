<!-- 图片管理对话框：上传 / 设主图 / 删除 -->
<template>
  <el-dialog :model-value="show" title="车型图片" width="640px"
             @update:model-value="$emit('update:show', $event)" @open="onOpen">
    <!-- 上传：选择文件后立即上传并刷新列表 -->
    <el-upload :show-file-list="false" accept=".jpg,.jpeg,.png,.webp" :http-request="onUpload">
      <el-button type="primary" plain :loading="uploading">上传图片</el-button>
    </el-upload>

    <div class="mt-4 grid grid-cols-3 gap-3">
      <div v-for="img in images" :key="img.id" class="border border-hairline p-1">
        <img :src="img.url" class="aspect-[4/3] w-full bg-mist object-cover" />
        <div class="mt-1 flex items-center justify-between text-[12px]">
          <el-tag v-if="img.is_main" size="small" type="primary">主图</el-tag>
          <el-button v-else link type="primary" size="small" @click="onSetMain(img)">设为主图</el-button>
          <el-button link type="danger" size="small" @click="onDelete(img)">删除</el-button>
        </div>
      </div>
    </div>
    <p v-if="!images.length" class="py-6 text-center text-[12px] text-gray-400">暂无图片</p>
  </el-dialog>
</template>

<script setup>
// 上传走 /files/upload 再登记到车型；无图时首张自动设为主图
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminFetchModelDetail, adminAddImage, adminDeleteImage, adminSetMainImage, uploadImage } from '@/api/admin'

const props = defineProps({ show: Boolean, modelId: Number })
const emit = defineEmits(['saved'])

const images = ref([])
const uploading = ref(false)

async function onOpen() {
  await load()
}

async function load() {
  const detail = await adminFetchModelDetail(props.modelId)
  images.value = detail.images
}

async function onUpload({ file }) {
  uploading.value = true
  try {
    const { url } = await uploadImage(file)
    // 首张照片自动设为主图
    await adminAddImage(props.modelId, { url, is_main: images.value.length === 0 })
    ElMessage.success('上传成功')
    await load()
    emit('saved')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    uploading.value = false
  }
}

async function onSetMain(img) {
  await adminSetMainImage(props.modelId, img.id)
  ElMessage.success('已设置主图')
  await load()
  emit('saved')
}

async function onDelete(img) {
  await ElMessageBox.confirm('确认删除该图片？', '提示', { type: 'warning' })
  await adminDeleteImage(props.modelId, img.id)
  ElMessage.success('删除成功')
  await load()
  emit('saved')
}
</script>
