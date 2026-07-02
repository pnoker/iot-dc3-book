<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NCard, NGrid, NGi, NProgress, NSpace, NStatistic, NTag, useMessage } from 'naive-ui'
import { api, type DashboardStatus } from '../api/client'

const status = ref<DashboardStatus | null>(null)
const loading = ref(false)
const error = ref('')
const message = useMessage()

async function load() {
  loading.value = true
  error.value = ''
  try {
    status.value = await api.status()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function runCommand(action: 'run' | 'resume' | 'output') {
  try {
    if (action === 'run') await api.run()
    if (action === 'resume') await api.resume()
    if (action === 'output') await api.regenerateOutput()
    message.success('命令已提交')
    await load()
  } catch (err) {
    message.error(err instanceof Error ? err.message : String(err))
  }
}
</script>

<template>
  <NSpace vertical size="large">
    <div class="page-title">
      <h2>运行总览</h2>
      <p>实时掌握写书进度、当前章节和 RAG 健康情况。</p>
    </div>

    <NCard v-if="error" type="error">{{ error }}</NCard>

    <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen">
      <NGi>
        <NCard title="当前阶段">
          <NStatistic :value="status?.phase ?? (loading ? '加载中' : '未开始')" />
          <NTag :type="status?.complete ? 'success' : 'info'" class="mt-12">
            {{ status?.complete ? '已完成' : '进行中' }}
          </NTag>
        </NCard>
      </NGi>
      <NGi>
        <NCard title="章节进度">
          <NProgress type="circle" :percentage="Math.round((status?.progress ?? 0) * 100)" />
          <p class="muted">{{ status?.chapters_written ?? 0 }} / {{ status?.total_chapters ?? 0 }} 章</p>
        </NCard>
      </NGi>
      <NGi>
        <NCard title="当前章节">
          <NStatistic :value="status?.current_chapter?.title ?? '暂无'" />
          <p class="muted">ID: {{ status?.current_chapter?.id ?? '-' }}</p>
        </NCard>
      </NGi>
      <NGi>
        <NCard title="RAG 健康">
          <NTag :type="status?.rag?.healthy ? 'success' : 'warning'">
            {{ status?.rag?.healthy ? '健康' : '待检查' }}
          </NTag>
          <p class="muted">Chunks: {{ status?.rag?.chunk_count ?? 0 }}</p>
        </NCard>
      </NGi>
    </NGrid>

    <NCard title="下一节点">
      <NSpace>
        <NTag v-for="node in status?.next_nodes ?? []" :key="node" type="info">{{ node }}</NTag>
        <span v-if="!status?.next_nodes?.length" class="muted">暂无待执行节点</span>
      </NSpace>
    </NCard>

    <NCard title="操作控制">
      <NSpace>
        <NButton type="primary" @click="runCommand('run')">启动/续跑</NButton>
        <NButton @click="runCommand('resume')">从 checkpoint 继续</NButton>
        <NButton @click="runCommand('output')">重新生成 output</NButton>
        <NButton @click="load">刷新状态</NButton>
      </NSpace>
    </NCard>
  </NSpace>
</template>
