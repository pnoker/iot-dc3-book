<script setup lang="ts">
import * as echarts from 'echarts'
import { onMounted, ref } from 'vue'
import { NCard, NGi, NGrid, NSpace } from 'naive-ui'
import { api, type Metrics } from '../api/client'

const metrics = ref<Metrics | null>(null)
const agentChart = ref<HTMLDivElement | null>(null)
const chapterChart = ref<HTMLDivElement | null>(null)

function renderChart(el: HTMLDivElement | null, title: string, data: Record<string, number>) {
  if (!el) return
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: title, textStyle: { color: '#e5e7eb' } },
    tooltip: {},
    xAxis: { type: 'category', data: Object.keys(data), axisLabel: { color: '#cbd5e1' } },
    yAxis: { type: 'value', axisLabel: { color: '#cbd5e1' } },
    series: [{ type: 'bar', data: Object.values(data), itemStyle: { color: '#60a5fa' } }],
    grid: { left: 48, right: 20, bottom: 48, top: 60 },
  })
}

async function load() {
  metrics.value = await api.metrics()
  requestAnimationFrame(() => {
    renderChart(agentChart.value, 'Agent 耗时（秒）', metrics.value?.agent_durations ?? {})
    renderChart(chapterChart.value, '章节耗时（秒）', metrics.value?.chapter_durations ?? {})
  })
}

onMounted(load)
</script>

<template>
  <NSpace vertical size="large">
    <div class="page-title">
      <h2>指标分析</h2>
      <p>从日志聚合每个 Agent 和章节的耗时，用于定位瓶颈。</p>
    </div>
    <NGrid :cols="2" :x-gap="16" responsive="screen">
      <NGi><NCard><div ref="agentChart" class="chart" /></NCard></NGi>
      <NGi><NCard><div ref="chapterChart" class="chart" /></NCard></NGi>
    </NGrid>
  </NSpace>
</template>
