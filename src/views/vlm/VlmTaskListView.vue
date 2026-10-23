<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Connection,
  CopyDocument,
  Delete,
  Edit,
  Plus,
  Refresh,
  Tickets,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  createVlmTask,
  deleteVlmTask,
  generateTosPrivateSignedUrl,
  getVlmPrompts,
  getVlmTasks,
  updateVlmTask,
  type VlmPrompt,
  type VlmTask,
} from '@/services/vlm'

const router = useRouter()
const loading = ref(false)
const promptLoading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingTaskId = ref<number>()
const tosDialogVisible = ref(false)
const tosGenerating = ref(false)
const formRef = ref<FormInstance>()
const tosFormRef = ref<FormInstance>()
const tasks = ref<VlmTask[]>([])
const prompts = ref<VlmPrompt[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 10
const percentageFormatter = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 })
type TaskStatusTagType = 'success' | 'warning' | 'info' | 'danger'
type TaskType = 'label' | 'dig'
const form = reactive<{
  task_type: TaskType
  prompt_id?: number
  task_input: string
  remarks: string
  task_status: 0 | 1 | 2
}>({
  task_type: 'label',
  prompt_id: undefined,
  task_input: '',
  remarks: '',
  task_status: 0,
})
const rules: FormRules = {
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  prompt_id: [{ required: true, message: '请选择提示词模版', trigger: 'change' }],
  task_input: [{ required: true, message: '请输入任务输入', trigger: 'blur' }],
}
const tosForm = reactive({
  original_url: '',
  signed_url: '',
})
const tosRules: FormRules = {
  original_url: [
    { required: true, message: '请输入 TOS 文件原始地址', trigger: 'blur' },
    { max: 1024, message: '地址不能超过 1024 个字符', trigger: 'blur' },
  ],
}
const TASK_TYPE_LABELS: Record<TaskType, string> = {
  label: '标注',
  dig: '挖掘',
}
const availablePrompts = computed(() => prompts.value.filter(
  prompt => (
    (!prompt.is_closed || prompt.id === form.prompt_id)
    && prompt.vlm_type === TASK_TYPE_LABELS[form.task_type]
  ),
))

const TASK_STATUS_LABELS: Record<number, string> = {
  0: '未开始',
  1: '进行中',
  2: '已完成',
}

async function load(showMessage = false) {
  loading.value = true
  try {
    const result = await getVlmTasks(page.value)
    tasks.value = result.items
    total.value = result.total
    if (showMessage) ElMessage.success('任务列表已刷新')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务列表加载失败')
  } finally {
    loading.value = false
  }
}

async function loadPromptOptions() {
  promptLoading.value = true
  try {
    prompts.value = await getVlmPrompts()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提示词模版加载失败')
  } finally {
    promptLoading.value = false
  }
}

function openCreate() {
  editingTaskId.value = undefined
  form.task_type = 'label'
  form.prompt_id = undefined
  form.task_input = ''
  form.remarks = ''
  form.task_status = 0
  formRef.value?.clearValidate()
  dialogVisible.value = true
  loadPromptOptions()
}

function openEdit(task: VlmTask) {
  editingTaskId.value = task.sequence
  form.task_type = task.task_type === '挖掘' ? 'dig' : 'label'
  form.prompt_id = task.prompt_id ?? undefined
  form.task_input = task.task_input ?? ''
  form.remarks = task.remark
  form.task_status = [0, 1, 2].includes(task.task_status)
    ? task.task_status as 0 | 1 | 2
    : 0
  formRef.value?.clearValidate()
  dialogVisible.value = true
  loadPromptOptions()
}

async function save() {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return
  if (!form.prompt_id) return

  saving.value = true
  try {
    const payload = {
      prompt_id: form.prompt_id,
      task_type: form.task_type,
      task_input: form.task_input,
      remarks: form.remarks,
    }
    if (editingTaskId.value !== undefined) {
      await updateVlmTask(editingTaskId.value, {
        ...payload,
        task_status: form.task_status,
      })
      ElMessage.success('任务更新成功')
    } else {
      await createVlmTask(payload)
      ElMessage.success('任务创建成功')
      page.value = 1
    }
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务创建失败')
  } finally {
    saving.value = false
  }
}

async function removeTask(task: VlmTask) {
  try {
    await ElMessageBox.confirm(
      `确定删除任务 #${task.sequence} 吗？删除后列表和总览将不再统计该任务。`,
      '删除任务',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  try {
    await deleteVlmTask(task.sequence)
    ElMessage.success('任务已删除')
    if (tasks.value.length === 1 && page.value > 1) page.value -= 1
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务删除失败')
  }
}

function changeTaskType() {
  form.prompt_id = undefined
  formRef.value?.clearValidate('prompt_id')
}

function openTosSigner() {
  tosForm.original_url = ''
  tosForm.signed_url = ''
  tosFormRef.value?.clearValidate()
  tosDialogVisible.value = true
}

async function generateTosSign() {
  if (
    !tosFormRef.value
    || !(await tosFormRef.value.validate().catch(() => false))
  ) return

  tosGenerating.value = true
  tosForm.signed_url = ''
  try {
    const result = await generateTosPrivateSignedUrl(tosForm.original_url)
    tosForm.signed_url = result.signed_url
    ElMessage.success('TOS 私有签名生成成功')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'TOS 私有签名生成失败')
  } finally {
    tosGenerating.value = false
  }
}

async function copyTosSignedUrl() {
  if (!tosForm.signed_url) return

  try {
    await navigator.clipboard.writeText(tosForm.signed_url)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = tosForm.signed_url
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const copied = document.execCommand('copy')
    textarea.remove()
    if (!copied) {
      ElMessage.error('复制失败，请手动复制转换结果')
      return
    }
  }

  ElMessage.success('转换结果已复制')
}

function formatDate(value: string | null) {
  if (!value) return '--'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function formatAccuracy(value: number | null) {
  if (value === null) return '--'
  return `${percentageFormatter.format(value * 100)}%`
}

function taskStatusLabel(status: number) {
  return TASK_STATUS_LABELS[status] ?? `未知（${status}）`
}

function taskStatusType(status: number): TaskStatusTagType {
  if (status === 0) return 'info'
  if (status === 1) return 'warning'
  if (status === 2) return 'success'
  return 'danger'
}

onMounted(() => load())
</script>

<template>
  <section class="surface data-surface vlm-task-surface">
    <div class="data-toolbar">
      <div class="vlm-table-title">
        <span>VLM TASK DIRECTORY</span>
        <div><el-icon><Tickets /></el-icon><strong>打标任务</strong></div>
      </div>
      <div class="vlm-task-toolbar-actions">
        <el-button :icon="Refresh" :loading="loading" @click="load(true)">刷新列表</el-button>
        <el-button :icon="Connection" @click="openTosSigner">TOS私有签名</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
      </div>
    </div>

    <div class="table-meta">
      <span>火山引擎 RDS · 每页 {{ PAGE_SIZE }} 条</span>
      <strong>{{ total }} TASKS</strong>
    </div>

    <el-table v-loading="loading" :data="tasks" row-key="sequence" class="tech-table vlm-task-table">
      <el-table-column label="序号" width="86" align="center">
        <template #default="{ row }">
          <button
            type="button"
            class="vlm-task-id-link"
            :aria-label="`查看任务 ${row.sequence} 的任务列表`"
            @click="router.push({ name: 'vlm-task-items', params: { taskId: row.sequence } })"
          >
            {{ row.sequence }}
          </button>
        </template>
      </el-table-column>
      <el-table-column label="提示词模版" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.prompt_title || '--' }}</template>
      </el-table-column>
      <el-table-column prop="task_type" label="任务类型" min-width="180" />
      <el-table-column label="任务状态" min-width="120">
        <template #default="{ row }">
          <el-tag :type="taskStatusType(row.task_status)" effect="plain" size="small">
            {{ taskStatusLabel(row.task_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="任务创建时间" min-width="190">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="任务结束时间" min-width="190">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="Tokens 消耗" min-width="150" align="right">
        <template #default="{ row }">
          <span class="token-value">{{ row.token_usage.toLocaleString() }}</span>
        </template>
      </el-table-column>
      <el-table-column label="准确率" min-width="120" align="right">
        <template #default="{ row }">{{ formatAccuracy(row.accuracy) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="220" show-overflow-tooltip />
      <el-table-column label="操作" width="116" align="center" fixed="right">
        <template #default="{ row }">
          <el-tooltip content="修改" placement="top">
            <el-button text circle :icon="Edit" @click="openEdit(row)" />
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button text circle type="danger" :icon="Delete" @click="removeTask(row)" />
          </el-tooltip>
        </template>
      </el-table-column>
      <template #empty>
        <div class="vlm-empty">
          <el-icon :size="34"><Tickets /></el-icon>
          <strong>暂无 VLM 打标任务</strong>
          <span>当前页没有可展示的任务记录</span>
        </div>
      </template>
    </el-table>

    <div class="vlm-pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="PAGE_SIZE"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load()"
      />
    </div>
  </section>

  <el-dialog
    v-model="dialogVisible"
    :title="editingTaskId !== undefined ? '修改任务' : '新增任务'"
    width="520px"
    class="vlm-task-dialog"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="任务类型" prop="task_type">
        <el-segmented
          v-model="form.task_type"
          :options="[
            { label: '标注', value: 'label' },
            { label: '挖掘', value: 'dig' },
          ]"
          @change="changeTaskType"
        />
      </el-form-item>
      <el-form-item label="提示词模版" prop="prompt_id">
        <el-select
          v-model="form.prompt_id"
          :loading="promptLoading"
          placeholder="请选择提示词模版"
          no-data-text="暂无开启的提示词模版"
        >
          <el-option
            v-for="prompt in availablePrompts"
            :key="prompt.id"
            :label="`[${prompt.vlm_type}] ${prompt.title}`"
            :value="prompt.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-if="editingTaskId !== undefined" label="任务状态">
        <el-segmented
          v-model="form.task_status"
          :options="[
            { label: '未开始', value: 0 },
            { label: '进行中', value: 1 },
            { label: '已完成', value: 2 },
          ]"
        />
      </el-form-item>
      <el-form-item label="任务输入" prop="task_input">
        <el-input
          v-model="form.task_input"
          type="textarea"
          :rows="7"
          resize="none"
          placeholder="请输入任务输入"
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input
          v-model="form.remarks"
          maxlength="32"
          show-word-limit
          placeholder="请输入备注"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">
        {{ editingTaskId !== undefined ? '保存修改' : '创建任务' }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="tosDialogVisible"
    title="TOS私有签名"
    width="640px"
    class="vlm-tos-dialog"
  >
    <el-form ref="tosFormRef" :model="tosForm" :rules="tosRules" label-position="top">
      <el-form-item label="TOS文件原始地址" prop="original_url">
        <el-input
          v-model="tosForm.original_url"
          maxlength="1024"
          show-word-limit
          clearable
          placeholder="https://bucket.tos-cn-beijing.volces.com/path/to/object"
        />
      </el-form-item>

      <div class="vlm-tos-action">
        <small>该功能将公网TOS地址转换为内网预签名URL</small>
        <el-button
          type="primary"
          :icon="Connection"
          :loading="tosGenerating"
          @click="generateTosSign"
        >
          生成
        </el-button>
      </div>

      <el-form-item label="转换结果">
        <el-input
          v-model="tosForm.signed_url"
          type="textarea"
          :rows="6"
          resize="none"
          readonly
          placeholder="生成结果将在此显示"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="tosDialogVisible = false">关闭</el-button>
      <el-button
        type="primary"
        :icon="CopyDocument"
        :disabled="!tosForm.signed_url"
        @click="copyTosSignedUrl"
      >
        复制
      </el-button>
    </template>
  </el-dialog>
</template>
