<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Avatar,
  Cpu,
  DataAnalysis,
  Document,
  Expand,
  Files,
  Fold,
  Grid,
  List,
  Lock,
  MagicStick,
  SwitchButton,
  User,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)
const mobileNav = ref(false)

const activeMenu = computed(() => (
  route.path.startsWith('/vlm/tasks/') ? '/vlm/tasks' : route.path
))
const initials = computed(() => auth.user?.display_name.slice(0, 1).toUpperCase() ?? 'S')

async function logout() {
  await ElMessageBox.confirm('确定退出 Stephen 开发平台吗？', '退出登录', {
    confirmButtonText: '退出',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <button class="icon-button nav-toggle" type="button" aria-label="切换导航" @click="collapsed = !collapsed">
        <el-icon :size="19"><Expand v-if="collapsed" /><Fold v-else /></el-icon>
      </button>
      <button class="icon-button mobile-toggle" type="button" aria-label="打开导航" @click="mobileNav = true">
        <el-icon :size="19"><Expand /></el-icon>
      </button>

      <div class="topbar-brand" @click="router.push('/')">
        <span class="brand-mark"><span></span></span>
        <div>
          <strong>STEPHEN</strong>
          <small>FDE CONTROL SYSTEM</small>
        </div>
      </div>

      <div class="topbar-status">
        <span class="status-dot"></span>
        <span>系统运行正常</span>
      </div>

      <div class="topbar-user">
        <div class="user-copy">
          <strong>{{ auth.user?.display_name }}</strong>
          <span>{{ auth.user?.role_name }}</span>
        </div>
        <el-avatar :size="34">{{ initials }}</el-avatar>
        <el-tooltip content="退出登录" placement="bottom">
          <button class="icon-button" type="button" aria-label="退出登录" @click="logout">
            <el-icon><SwitchButton /></el-icon>
          </button>
        </el-tooltip>
      </div>
    </header>

    <aside class="sidebar" :class="{ collapsed }">
      <el-scrollbar>
        <el-menu
          :default-active="activeMenu"
          :collapse="collapsed"
          :collapse-transition="false"
          router
          class="nav-menu"
        >
          <el-menu-item index="/">
            <el-icon><Grid /></el-icon>
            <template #title>工作台</template>
          </el-menu-item>

          <el-sub-menu v-if="auth.can('account_center')" index="account">
            <template #title>
              <el-icon><Lock /></el-icon>
              <span>账号中心</span>
            </template>
            <el-menu-item index="/account/users">
              <el-icon><User /></el-icon>
              <template #title>用户管理</template>
            </el-menu-item>
            <el-menu-item index="/account/roles">
              <el-icon><Avatar /></el-icon>
              <template #title>角色管理</template>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="vlm">
            <template #title>
              <el-icon><DataAnalysis /></el-icon>
              <span>智驾 VLM 业务</span>
            </template>
            <el-menu-item index="/vlm/overview">
              <el-icon><DataAnalysis /></el-icon>
              <template #title>VLM 总览</template>
            </el-menu-item>
            <el-menu-item index="/vlm/tasks">
              <el-icon><List /></el-icon>
              <template #title>打标任务</template>
            </el-menu-item>
            <el-menu-item index="/vlm/prompts">
              <el-icon><Document /></el-icon>
              <template #title>提示词管理</template>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu v-if="auth.can('agent_center')" index="agents">
            <template #title>
              <el-icon><MagicStick /></el-icon>
              <span>车联AI业务</span>
            </template>
            <el-menu-item index="/agents">
              <el-icon><Cpu /></el-icon>
              <template #title>车端Agent</template>
            </el-menu-item>
            <el-menu-item index="/agents/base-data">
              <el-icon><Files /></el-icon>
              <template #title>基础数据管理</template>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-scrollbar>

      <div v-if="!collapsed" class="sidebar-footer">
        <span>LOCAL CORE</span>
        <strong>SQLite / ONLINE</strong>
      </div>
    </aside>

    <main class="main-content">
      <div class="page-heading">
        <div>
          <span class="page-eyebrow">STEPHEN DEVELOPMENT PLATFORM</span>
          <h1>{{ route.meta.title }}</h1>
        </div>
        <span class="page-code">FDE-{{ String(route.name ?? 'CORE').toUpperCase() }}</span>
      </div>
      <router-view />
    </main>

    <el-drawer v-model="mobileNav" direction="ltr" size="270px" :with-header="false" class="mobile-drawer">
      <div class="drawer-brand">
        <span class="brand-mark"><span></span></span>
        <strong>STEPHEN</strong>
      </div>
      <el-menu :default-active="activeMenu" router @select="mobileNav = false">
        <el-menu-item index="/"><el-icon><Grid /></el-icon><span>工作台</span></el-menu-item>
        <el-menu-item v-if="auth.can('account_center')" index="/account/users">
          <el-icon><User /></el-icon><span>用户管理</span>
        </el-menu-item>
        <el-menu-item v-if="auth.can('account_center')" index="/account/roles">
          <el-icon><Avatar /></el-icon><span>角色管理</span>
        </el-menu-item>
        <el-menu-item index="/vlm/overview"><el-icon><DataAnalysis /></el-icon><span>VLM 总览</span></el-menu-item>
        <el-menu-item index="/vlm/tasks"><el-icon><List /></el-icon><span>打标任务</span></el-menu-item>
        <el-menu-item index="/vlm/prompts"><el-icon><Document /></el-icon><span>提示词管理</span></el-menu-item>
        <el-sub-menu v-if="auth.can('agent_center')" index="mobile-agents">
          <template #title><el-icon><MagicStick /></el-icon><span>车联AI业务</span></template>
          <el-menu-item index="/agents"><el-icon><Cpu /></el-icon><span>车端Agent</span></el-menu-item>
          <el-menu-item index="/agents/base-data">
            <el-icon><Files /></el-icon><span>基础数据管理</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-drawer>
  </div>
</template>
