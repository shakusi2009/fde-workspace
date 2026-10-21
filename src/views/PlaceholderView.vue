<script setup lang="ts">
import { Cpu, DataAnalysis, Plus } from '@element-plus/icons-vue'

defineProps<{
  type: 'vlm' | 'agent'
  title: string
  description: string
}>()
</script>

<template>
  <section class="placeholder-zone">
    <div class="placeholder-visual" :class="type">
      <div class="orbit orbit-one"></div>
      <div class="orbit orbit-two"></div>
      <el-icon :size="44"><DataAnalysis v-if="type === 'vlm'" /><Cpu v-else /></el-icon>
    </div>
    <span class="section-index">{{ type === 'vlm' ? 'VLM / 01' : 'AGENT / 01' }}</span>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <el-button type="primary" disabled><el-icon><Plus /></el-icon>新建项目</el-button>
    <small>模块空间已预留，等待业务能力接入</small>
  </section>
</template>
