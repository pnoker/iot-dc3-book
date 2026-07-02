<script setup lang="ts">
import { computed, ref } from 'vue'
import { NConfigProvider, NGlobalStyle, NLayout, NLayoutContent, NLayoutSider, NMenu, NMessageProvider, darkTheme } from 'naive-ui'
import OverviewPage from './pages/OverviewPage.vue'
import ChaptersPage from './pages/ChaptersPage.vue'
import LogsPage from './pages/LogsPage.vue'
import MetricsPage from './pages/MetricsPage.vue'
import SettingsPage from './pages/SettingsPage.vue'

const activePage = ref('overview')
const menuOptions = [
  { label: '总览', key: 'overview' },
  { label: '章节审阅', key: 'chapters' },
  { label: '实时日志', key: 'logs' },
  { label: '指标分析', key: 'metrics' },
  { label: '设置', key: 'settings' },
]

const currentComponent = computed(() => {
  return {
    overview: OverviewPage,
    chapters: ChaptersPage,
    logs: LogsPage,
    metrics: MetricsPage,
    settings: SettingsPage,
  }[activePage.value] ?? OverviewPage
})
</script>

<template>
  <NConfigProvider :theme="darkTheme">
    <NMessageProvider>
      <NGlobalStyle />
      <NLayout has-sider class="app-shell">
        <NLayoutSider bordered collapse-mode="width" :width="240">
          <div class="brand">
            <div class="brand-mark">📚</div>
            <div>
              <h1>mi-book-writer</h1>
              <p>多 Agent 写书控制台</p>
            </div>
          </div>
          <NMenu v-model:value="activePage" :options="menuOptions" />
        </NLayoutSider>
        <NLayoutContent class="content">
          <component :is="currentComponent" />
        </NLayoutContent>
      </NLayout>
    </NMessageProvider>
  </NConfigProvider>
</template>
