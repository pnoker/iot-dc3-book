<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NCard, NInput, NSelect, NSpace, NTag } from 'naive-ui'
import { api, type LogEntry } from '../api/client'

const logs = ref<LogEntry[]>([])
const level = ref<string | null>(null)
const agent = ref('')
const levels = [
  { label: '全部', value: '' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' },
]

async function load() {
  const params = new URLSearchParams()
  if (level.value) params.set('level', level.value)
  if (agent.value) params.set('agent', agent.value)
  params.set('limit', '200')
  logs.value = await api.logs(`?${params.toString()}`)
}

onMounted(load)
</script>

<template>
  <NSpace vertical size="large">
    <div class="page-title">
      <h2>实时日志</h2>
      <p>按级别和 Agent 过滤运行日志，日志中的密钥会在后端脱敏。</p>
    </div>
    <NCard>
      <NSpace>
        <NSelect v-model:value="level" :options="levels" placeholder="级别" style="width: 140px" @update:value="load" />
        <NInput v-model:value="agent" placeholder="Agent，例如 WriterAgent" style="width: 260px" @keydown.enter="load" />
        <NButton @click="load">刷新</NButton>
      </NSpace>
    </NCard>
    <NCard>
      <div class="log-list">
        <div v-for="entry in logs" :key="`${entry.timestamp}-${entry.raw}`" class="log-line">
          <span class="log-time">{{ entry.timestamp }}</span>
          <NTag size="small" :type="entry.level === 'ERROR' ? 'error' : entry.level === 'WARNING' ? 'warning' : 'info'">
            {{ entry.level || 'RAW' }}
          </NTag>
          <span class="log-agent">{{ entry.agent }}</span>
          <span>{{ entry.message }}</span>
        </div>
      </div>
    </NCard>
  </NSpace>
</template>
