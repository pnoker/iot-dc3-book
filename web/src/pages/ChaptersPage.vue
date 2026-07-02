<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import { computed, onMounted, ref } from 'vue'
import { NButton, NCard, NGi, NGrid, NList, NListItem, NSpace, NTag } from 'naive-ui'
import { api, type ChapterDetail, type ChapterSummary, type ChapterTree } from '../api/client'

const md = new MarkdownIt({ html: false, linkify: true, typographer: true })
const tree = ref<ChapterTree | null>(null)
const selected = ref<ChapterDetail | null>(null)
const error = ref('')

const renderedMarkdown = computed(() => md.render(selected.value?.markdown || ''))

async function load() {
  try {
    tree.value = await api.chapters()
    const first = tree.value.parts.flatMap((part) => part.chapters).find((chapter) => chapter.written)
    if (first) await selectChapter(first)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function selectChapter(chapter: ChapterSummary) {
  selected.value = await api.chapter(chapter.id)
}

onMounted(load)
</script>

<template>
  <NSpace vertical size="large">
    <div class="page-title">
      <h2>章节审阅</h2>
      <p>浏览章节树、预览 Markdown 正文，并查看事实/风格/审校反馈。</p>
    </div>
    <NCard v-if="error" type="error">{{ error }}</NCard>
    <NGrid :cols="12" :x-gap="16">
      <NGi :span="4">
        <NCard :title="tree?.book_title || '章节树'">
          <div v-for="part in tree?.parts ?? []" :key="part.name" class="part-block">
            <h3>{{ part.prefix }} · {{ part.name }}</h3>
            <NList hoverable clickable>
              <NListItem v-for="chapter in part.chapters" :key="chapter.id" @click="selectChapter(chapter)">
                <NSpace justify="space-between" align="center">
                  <span>第{{ chapter.id }}章 {{ chapter.title }}</span>
                  <NTag size="small" :type="chapter.written ? 'success' : 'default'">
                    {{ chapter.written ? '已写' : '未写' }}
                  </NTag>
                </NSpace>
              </NListItem>
            </NList>
          </div>
        </NCard>
      </NGi>
      <NGi :span="5">
        <NCard :title="selected?.title || 'Markdown 预览'">
          <article class="markdown-preview" v-html="renderedMarkdown" />
        </NCard>
      </NGi>
      <NGi :span="3">
        <NCard title="质量面板">
          <template v-if="selected">
            <p><strong>状态：</strong>{{ selected.status }}</p>
            <p><strong>字数：</strong>{{ selected.word_count }}</p>
            <p><strong>修订：</strong>{{ selected.revision_count }} 次</p>
            <NCard size="small" title="事实反馈" class="mt-12">{{ selected.feedback.fact || '暂无' }}</NCard>
            <NCard size="small" title="风格反馈" class="mt-12">{{ selected.feedback.style || '暂无' }}</NCard>
            <NCard size="small" title="审校反馈" class="mt-12">{{ selected.feedback.review || '暂无' }}</NCard>
            <NButton class="mt-12" block disabled>局部修订（下一阶段）</NButton>
          </template>
          <span v-else class="muted">请选择章节</span>
        </NCard>
      </NGi>
    </NGrid>
  </NSpace>
</template>
