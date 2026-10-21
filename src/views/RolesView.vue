<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Delete, Edit, Lock, Plus, Search, User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { api } from '@/api'

type RoleRow = {
  id: number
  name: string
  description: string
  permissions: string[]
  is_system: boolean
  user_count: number
}

const permissionOptions = [
  { value: 'account_center', label: '账号中心', description: '用户、角色及访问权限管理' },
  { value: 'agent_center', label: '智能体中心', description: '智能体开发模块访问权限' },
]

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number>()
const search = ref('')
const roles = ref<RoleRow[]>([])
const formRef = ref<FormInstance>()
const form = reactive({
  name: '',
  description: '',
  permissions: [] as string[],
  is_system: false,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
}

const filteredRoles = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  return !keyword
    ? roles.value
    : roles.value.filter((role) =>
      role.name.toLowerCase().includes(keyword) || role.description.toLowerCase().includes(keyword),
    )
})

async function load() {
  loading.value = true
  try {
    roles.value = await api<RoleRow[]>('/roles')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = undefined
  Object.assign(form, { name: '', description: '', permissions: [], is_system: false })
  formRef.value?.clearValidate()
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(role: RoleRow) {
  editingId.value = role.id
  Object.assign(form, {
    name: role.name,
    description: role.description,
    permissions: [...role.permissions],
    is_system: role.is_system,
  })
  dialogVisible.value = true
}

async function save() {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    await api(editingId.value ? `/roles/${editingId.value}` : '/roles', {
      method: editingId.value ? 'PUT' : 'POST',
      body: JSON.stringify(form),
    })
    ElMessage.success(editingId.value ? '角色信息已更新' : '角色创建成功')
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '操作失败')
  } finally {
    saving.value = false
  }
}

async function remove(role: RoleRow) {
  await ElMessageBox.confirm(`确定删除角色“${role.name}”吗？`, '删除角色', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  try {
    await api(`/roles/${role.id}`, { method: 'DELETE' })
    ElMessage.success('角色已删除')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除失败')
  }
}

function permissionLabel(permission: string) {
  return permissionOptions.find((item) => item.value === permission)?.label ?? permission
}

onMounted(load)
</script>

<template>
  <section class="surface data-surface">
    <div class="data-toolbar">
      <el-input v-model="search" clearable placeholder="搜索角色" :prefix-icon="Search" class="role-search" />
      <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增角色</el-button>
    </div>

    <div class="table-meta">
      <span>ACCESS ROLE MATRIX</span>
      <strong>{{ filteredRoles.length }} ROLES</strong>
    </div>

    <div v-loading="loading" class="role-grid">
      <article v-for="role in filteredRoles" :key="role.id" class="role-card">
        <div class="role-card-top">
          <div class="role-icon" :class="{ system: role.is_system }"><el-icon><Lock /></el-icon></div>
          <div class="role-actions">
            <el-tooltip content="编辑" placement="top">
              <el-button text circle :icon="Edit" @click="openEdit(role)" />
            </el-tooltip>
            <el-tooltip :content="role.is_system ? '系统角色不可删除' : '删除'" placement="top">
              <el-button text circle type="danger" :icon="Delete" :disabled="role.is_system" @click="remove(role)" />
            </el-tooltip>
          </div>
        </div>
        <div class="role-title">
          <h3>{{ role.name }}</h3>
          <span v-if="role.is_system">SYSTEM</span>
        </div>
        <p>{{ role.description || '暂无角色描述' }}</p>
        <div class="permission-list">
          <span v-for="permission in role.permissions" :key="permission">{{ permissionLabel(permission) }}</span>
          <small v-if="!role.permissions.length">无模块权限</small>
        </div>
        <footer>
          <span><el-icon><User /></el-icon>{{ role.user_count }} 位用户</span>
          <b>ROLE-{{ String(role.id).padStart(3, '0') }}</b>
        </footer>
      </article>
      <el-empty v-if="!loading && !filteredRoles.length" description="暂无匹配角色" />
    </div>
  </section>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑角色' : '新增角色'" width="560px" @closed="resetForm">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="角色名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入角色名称" />
      </el-form-item>
      <el-form-item label="角色描述">
        <el-input v-model="form.description" type="textarea" :rows="3" resize="none" placeholder="说明该角色的职责范围" />
      </el-form-item>
      <el-form-item label="模块访问权限">
        <el-checkbox-group v-model="form.permissions" class="permission-options">
          <label v-for="item in permissionOptions" :key="item.value" class="permission-option">
            <el-checkbox :value="item.value" :disabled="form.is_system" />
            <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
          </label>
        </el-checkbox-group>
        <p v-if="form.is_system" class="system-role-note">系统角色始终拥有全部模块权限。</p>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存角色</el-button>
    </template>
  </el-dialog>
</template>
