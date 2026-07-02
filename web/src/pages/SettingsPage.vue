<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NCard, NDescriptions, NDescriptionsItem, NSpace, NTag } from 'naive-ui'
import { api, type DashboardStatus, type RagStatus } from '../api/client'

const status = ref<DashboardStatus | null>(null)
const rag = ref<RagStatus | null>(null)

onMounted(async () => {
  status.value = await api.status()
  rag.value = await api.ragStatus()
})
</script>

<template>
  <NSpace vertical size="large">
    <div class="page-title">
      <h2>设置</h2>
      <p>只读展示运行配置和健康状态；敏感 Key 不在前端展示。</p>
    </div>
    <NCard title="运行环境">
      <NDescriptions bordered :column="1">
        <NDescriptionsItem label="Thread">{{ status?.thread_id ?? 'book-1' }}</NDescriptionsItem>
        <NDescriptionsItem label="Checkpoint">{{ status?.has_checkpoint ? '存在' : '暂无' }}</NDescriptionsItem>
        <NDescriptionsItem label="RAG Collection">{{ rag?.collection ?? '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="RAG Persist Dir">{{ rag?.persist_dir ?? '-' }}</NDescriptionsItem>
        <NDescriptionsItem label="RAG 健康">
          <NTag :type="rag?.healthy ? 'success' : 'warning'">{{ rag?.healthy ? '健康' : '待检查' }}</NTag>
        </NDescriptionsItem>
      </NDescriptions>
    </NCard>
  </NSpace>
</template>
