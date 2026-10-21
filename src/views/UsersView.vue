<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Plus, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { api } from '@/api'
import { useAuthStore } from '@/stores/auth'

type UserRow = {
  id: number
  username: string
  display_name: string
  email: string
  role_id: number
  role_name: string
  status: 'active' | 'disabled'
  created_at: string
}

type RoleOption = { id: number; name: string }

const auth = useAuthStore()
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number>()
const search = ref('')
const statusFilter = ref('')
const users = ref<UserRow[]>([])
const roles = ref<RoleOption[]>([])
const formRef = ref<FormInstance>()
const form = reactive({
  username: '',
  display_name: '',
  email: '',
  password: '',
  role_id: undefined as number | undefined,
  status: 'active' as 'active' | 'disabled',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入登录账号', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入用户姓名', trigger: 'blur' }],
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [{
    validator: (_rule, value, callback) => {
      if (!editingId.value && !value) callback(new Error('请输入初始密码'))
      else if (value && value.length < 8) callback(new Error('密码至少 8 位'))
      else callback()
    },
    trigger: 'blur',
  }],
}

const filteredUsers = computed(() => users.value.filter((user) => {
  const keyword = search.value.trim().toLowerCase()
  const matchesSearch = !keyword
    || user.username.toLowerCase().includes(keyword)
    || user.display_name.toLowerCase().includes(keyword)
    || user.email.toLowerCase().includes(keyword)
  return matchesSearch && (!statusFilter.value || user.status === statusFilter.value)
}))

async function load() {
  loading.value = true
  try {
    const [userRows, roleRows] = await Promise.all([
      api<UserRow[]>('/users'),
      api<RoleOption[]>('/roles'),
    ])
    users.value = userRows
    roles.value = roleRows
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = undefined
  Object.assign(form, {
    username: '',
    display_name: '',
    email: '',
    password: '',
    role_id: undefined,
    status: 'active',
  })
  formRef.value?.clearValidate()
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(user: UserRow) {
  editingId.value = user.id
  Object.assign(form, {
    username: user.username,
    display_name: user.display_name,
    email: user.email,
    password: '',
    role_id: user.role_id,
    status: user.status,
  })
  dialogVisible.value = true
}

async function save() {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    const path = editingId.value ? `/users/${editingId.value}` : '/users'
    await api(path, {
      method: editingId.value ? 'PUT' : 'POST',
      body: JSON.stringify(form),
    })
    ElMessage.success(editingId.value ? '用户信息已更新' : '用户创建成功')
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    saving.value = false
  }
}

async function remove(user: UserRow) {
  await ElMessageBox.confirm(`删除用户“${user.display_name}”后不可恢复，是否继续？`, '删除用户', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  try {
    await api(`/users/${user.id}`, { method: 'DELETE' })
    ElMessage.success('用户已删除')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除失败')
  }
}

onMounted(load)
</script>

<template>
  <section class="surface data-surface">
    <div class="data-toolbar">
      <div class="filter-group">
        <el-input v-model="search" clearable placeholder="搜索账号、姓名或邮箱" :prefix-icon="Search" />
        <el-select v-model="statusFilter" clearable placeholder="全部状态">
          <el-option label="启用" value="active" />
          <el-option label="停用" value="disabled" />
        </el-select>
      </div>
      <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增用户</el-button>
    </div>

    <div class="table-meta">
      <span>USER DIRECTORY</span>
      <strong>{{ filteredUsers.length }} / {{ users.length }}</strong>
    </div>

    <el-table v-loading="loading" :data="filteredUsers" row-key="id" class="tech-table">
      <el-table-column label="用户" min-width="190">
        <template #default="{ row }">
          <div class="identity-cell">
            <span class="initial-avatar">{{ row.display_name.slice(0, 1) }}</span>
            <div><strong>{{ row.display_name }}</strong><small>@{{ row.username }}</small></div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="190">
        <template #default="{ row }"><span class="muted-value">{{ row.email || '未设置' }}</span></template>
      </el-table-column>
      <el-table-column prop="role_name" label="角色" min-width="140" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <span class="status-tag" :class="row.status">{{ row.status === 'active' ? '启用' : '停用' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" min-width="170" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-tooltip content="编辑" placement="top">
            <el-button text circle :icon="Edit" @click="openEdit(row)" />
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button text circle type="danger" :icon="Delete" :disabled="row.id === auth.user?.id" @click="remove(row)" />
          </el-tooltip>
        </template>
      </el-table-column>
      <template #empty><el-empty description="暂无匹配用户" /></template>
    </el-table>
  </section>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑用户' : '新增用户'" width="520px" @closed="resetForm">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <div class="form-grid">
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="form.username" :disabled="Boolean(editingId)" placeholder="例如：zhangsan" />
        </el-form-item>
        <el-form-item label="用户姓名" prop="display_name">
          <el-input v-model="form.display_name" placeholder="请输入姓名" />
        </el-form-item>
      </div>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="name@example.com" />
      </el-form-item>
      <el-form-item :label="editingId ? '重置密码（留空则不修改）' : '初始密码'" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="form.role_id" placeholder="选择角色">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-segmented v-model="form.status" :options="[{ label: '启用', value: 'active' }, { label: '停用', value: 'disabled' }]" />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存用户</el-button>
    </template>
  </el-dialog>
</template>
