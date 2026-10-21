<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Lock, Refresh, User } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { api } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const loading = ref(false)
const captcha = ref({ id: '', code: '----' })
const form = reactive({
  username: '',
  password: '',
  captchaCode: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captchaCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '验证码为 4 位数字', trigger: 'blur' },
  ],
}

async function refreshCaptcha() {
  captcha.value = await api<{ id: string; code: string }>('/auth/captcha')
  form.captchaCode = ''
}

async function submit() {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return
  loading.value = true
  try {
    await auth.login({
      ...form,
      captchaId: captcha.value.id,
    })
    ElMessage.success('身份验证通过')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
    form.password = ''
    await refreshCaptcha()
  } finally {
    loading.value = false
  }
}

onMounted(refreshCaptcha)
</script>

<template>
  <main class="login-page">
    <div class="login-overlay"></div>
    <header class="login-header">
      <div class="topbar-brand">
        <span class="brand-mark"><span></span></span>
        <div>
          <strong>STEPHEN</strong>
          <small>FDE CONTROL SYSTEM</small>
        </div>
      </div>
      <div class="login-system-status"><span></span>SECURE LOCAL ENVIRONMENT</div>
    </header>

    <section class="login-intro">
      <span class="section-index">01 / AUTOMOTIVE AI</span>
      <h1>驱动汽车业务<br /><em>智能化演进</em></h1>
      <p>面向未来的汽车 AI 开发与精细化管理中枢</p>
      <div class="telemetry">
        <div><span>CORE</span><strong>ONLINE</strong></div>
        <div><span>DATABASE</span><strong>LOCAL</strong></div>
        <div><span>SECURITY</span><strong>ACTIVE</strong></div>
      </div>
    </section>

    <section class="login-panel">
      <div class="panel-accent"></div>
      <div class="login-title">
        <span>ACCESS CONTROL</span>
        <h2>登录平台</h2>
        <p>使用授权账号进入开发环境</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" size="large" placeholder="请输入账号" autocomplete="username">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="验证码" prop="captchaCode">
          <div class="captcha-row">
            <el-input v-model="form.captchaCode" size="large" maxlength="4" placeholder="4 位验证码" />
            <button class="captcha-code" type="button" aria-label="刷新验证码" @click="refreshCaptcha">
              <span>{{ captcha.code }}</span>
              <el-icon><Refresh /></el-icon>
            </button>
          </div>
        </el-form-item>
        <el-button class="login-button" type="primary" size="large" :loading="loading" @click="submit">
          验证并进入
        </el-button>
      </el-form>

      <div class="login-footer">
        <span><i></i>TLS CHANNEL READY</span>
        <b>v1.0.0</b>
      </div>
    </section>
  </main>
</template>
