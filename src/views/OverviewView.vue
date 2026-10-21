<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Cpu, DataAnalysis, Lock, User } from '@element-plus/icons-vue'
import { api } from '@/api'
import { useAuthStore } from '@/stores/auth'

type Overview = {
  users: { total: number; active: number }
  roles: { total: number }
  services: { online: number; total: number }
}

const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const overview = ref<Overview>({
  users: { total: 0, active: 0 },
  roles: { total: 0 },
  services: { online: 0, total: 0 },
})

const dateText = computed(() =>
  new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date()),
)

onMounted(async () => {
  try {
    overview.value = await api<Overview>('/overview')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div v-loading="loading" class="overview">
    <section class="command-banner">
      <div>
        <span>{{ dateText }}</span>
        <h2>你好，{{ auth.user?.display_name }}</h2>
        <p>汽车 AI 开发环境已就绪，所有本地核心服务运行正常。</p>
      </div>
      <div class="system-score">
        <div class="score-ring"><strong>100</strong><span>%</span></div>
        <div><span>SYSTEM HEALTH</span><strong>运行状态优良</strong></div>
      </div>
    </section>

    <section class="metrics-grid">
      <article class="metric-cell">
        <div class="metric-icon cyan"><el-icon><User /></el-icon></div>
        <div><span>用户总数</span><strong>{{ overview.users.total }}</strong><small>{{ overview.users.active }} 个账号启用</small></div>
      </article>
      <article class="metric-cell">
        <div class="metric-icon green"><el-icon><Lock /></el-icon></div>
        <div><span>角色模型</span><strong>{{ overview.roles.total }}</strong><small>细粒度模块权限</small></div>
      </article>
      <article class="metric-cell">
        <div class="metric-icon orange"><el-icon><Cpu /></el-icon></div>
        <div><span>核心服务</span><strong>{{ overview.services.online }}/{{ overview.services.total }}</strong><small>全部在线</small></div>
      </article>
    </section>

    <div class="overview-grid">
      <section class="surface module-list">
        <div class="surface-heading">
          <div><span>MODULE MATRIX</span><h3>业务模块</h3></div>
          <small>04 UNITS</small>
        </div>
        <button v-if="auth.can('account_center')" type="button" @click="router.push('/account/users')">
          <span class="module-number">01</span>
          <el-icon><User /></el-icon>
          <span><strong>账号中心</strong><small>用户与权限体系</small></span>
          <el-icon class="module-arrow"><ArrowRight /></el-icon>
        </button>
        <button type="button" @click="router.push('/vlm')">
          <span class="module-number">02</span>
          <el-icon><DataAnalysis /></el-icon>
          <span><strong>智驾 VLM 业务</strong><small>多模态业务空间</small></span>
          <el-icon class="module-arrow"><ArrowRight /></el-icon>
        </button>
        <button v-if="auth.can('agent_center')" type="button" @click="router.push('/agents')">
          <span class="module-number">03</span>
          <el-icon><Cpu /></el-icon>
          <span><strong>智能体开发</strong><small>业务智能体工作区</small></span>
          <el-icon class="module-arrow"><ArrowRight /></el-icon>
        </button>
      </section>

      <section class="surface activity-panel">
        <div class="surface-heading">
          <div><span>REALTIME STATUS</span><h3>环境状态</h3></div>
          <span class="live-badge">LIVE</span>
        </div>
        <div class="status-line">
          <div><i class="online"></i><span><strong>API Service</strong><small>localhost:3001</small></span></div>
          <b>12 ms</b>
        </div>
        <div class="status-line">
          <div><i class="online"></i><span><strong>SQLite Core</strong><small>local persistent storage</small></span></div>
          <b>READY</b>
        </div>
        <div class="status-line">
          <div><i class="standby"></i><span><strong>VLM Pipeline</strong><small>waiting for configuration</small></span></div>
          <b>STANDBY</b>
        </div>
        <div class="signal-chart" aria-hidden="true">
          <span v-for="height in [28, 45, 38, 70, 52, 88, 64, 74, 42, 61, 82, 56]" :key="height" :style="{ height: `${height}%` }"></span>
        </div>
      </section>
    </div>
  </div>
</template>
