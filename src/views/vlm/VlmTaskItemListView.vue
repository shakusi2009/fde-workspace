<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Refresh, Tickets, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  executeVlmTask,
  getVlmModels,
  getVlmTaskExecutionContext,
  getVlmTaskItems,
  type VlmModel,
  type VlmTaskExecutionContext,
  type VlmTaskItem,
} from '@/services/vlm'

type ItemStatusTagType = 'success' | 'info' | 'danger'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const executionDialogVisible = ref(false)
const contextLoading = ref(false)
const executing = ref(false)
const executionFormRef = ref<FormInstance>()
const executionContext = ref<VlmTaskExecutionContext>()
const models = ref<VlmModel[]>([])
const executionResult = ref('')
const executionForm = reactive({ model_id: '' })
const executionRules: FormRules = {
  model_id: [{ required: true, message: '请选择模型 ID', trigger: 'change' }],
}
const items = ref<VlmTaskItem[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 10
const taskId = computed(() => Number(route.params.taskId))

function statusLabel(status: number | null) {
  if (status === 0) return '成功'
  if (status === 1) return '失败'
  return '待执行'
}

function statusType(status: number | null): ItemStatusTagType {
  if (status === 0) return 'success'
  if (status === 1) return 'danger'
  return 'info'
}

function formatTokens(value: number | null) {
  return value === null ? '--' : value.toLocaleString()
}

async function openExecution() {
  executionDialogVisible.value = true
  contextLoading.value = true
  executionContext.value = undefined
  models.value = []
  executionForm.model_id = ''
  executionResult.value = ''
  executionFormRef.value?.clearValidate()
  try {
    const [context, modelList] = await Promise.all([
      getVlmTaskExecutionContext(taskId.value),
      getVlmModels(),
    ])
    executionContext.value = context
    models.value = modelList
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '执行上下文加载失败')
  } finally {
    contextLoading.value = false
  }
}

async function executeTask() {
  if (
    !executionContext.value
    || !executionFormRef.value
    || !(await executionFormRef.value.validate().catch(() => false))
  ) return

  executing.value = true
  executionResult.value = ''
  try {
    const result = await executeVlmTask(taskId.value, executionForm.model_id)
    executionResult.value = result.output_text ?? ''
    page.value = 1
    await load()
    if (result.task_status === 0) {
      ElMessage.success('Agent 执行成功')
    } else {
      ElMessage.error('Agent 执行失败，结果已记录')
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Agent 执行失败')
  } finally {
    executing.value = false
  }
}

async function load(showMessage = false) {
  if (!Number.isInteger(taskId.value) || taskId.value <= 0) {
    ElMessage.error('任务 ID 无效')
    await router.replace('/vlm/tasks')
    return
  }

  loading.value = true
  try {
    const result = await getVlmTaskItems(taskId.value, page.value)
    items.value = result.items
    total.value = result.total
    if (showMessage) ElMessage.success('任务列表已刷新')
  } catch (error) {
    items.value = []
    total.value = 0
    ElMessage.error(error instanceof Error ? error.message : '任务列表加载失败')
  } finally {
    loading.value = false
  }
}

watch(taskId, () => {
  page.value = 1
  load()
})

onMounted(() => load())
</script>

<template>
  <section class="surface data-surface vlm-task-item-surface">
    <div class="data-toolbar">
      <div class="vlm-table-title">
        <span>TASK ITEM DIRECTORY / TASK #{{ taskId }}</span>
        <div><el-icon><Tickets /></el-icon><strong>任务执行明细</strong></div>
      </div>
      <div class="vlm-task-item-actions">
        <el-button :icon="ArrowLeft" @click="router.push('/vlm/tasks')">返回打标任务</el-button>
        <el-button type="primary" :icon="VideoPlay" @click="openExecution">新增执行</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="load(true)">刷新列表</el-button>
      </div>
    </div>

    <div class="table-meta">
      <span>vlm_tasks_item · 主任务 #{{ taskId }} · 每页 {{ PAGE_SIZE }} 条</span>
      <strong>{{ total }} ITEMS</strong>
    </div>

    <el-table
      v-loading="loading"
      :data="items"
      row-key="id"
      class="tech-table vlm-task-item-table"
    >
      <el-table-column prop="id" label="明细 ID" width="92" align="center" />
      <el-table-column prop="task_id" label="主任务 ID" width="104" align="center" />
      <el-table-column prop="model_id" label="模型 ID" min-width="180" show-overflow-tooltip />
      <el-table-column prop="task_input" label="推理输入" min-width="280" show-overflow-tooltip />
      <el-table-column label="总 Tokens" min-width="130" align="right">
        <template #default="{ row }">{{ formatTokens(row.total_tokens) }}</template>
      </el-table-column>
      <el-table-column label="输入 Tokens" min-width="130" align="right">
        <template #default="{ row }">{{ formatTokens(row.input_tokens) }}</template>
      </el-table-column>
      <el-table-column label="输出 Tokens" min-width="130" align="right">
        <template #default="{ row }">{{ formatTokens(row.output_tokens) }}</template>
      </el-table-column>
      <el-table-column label="缓存 Tokens" min-width="130" align="right">
        <template #default="{ row }">{{ formatTokens(row.cached_tokens) }}</template>
      </el-table-column>
      <el-table-column label="执行状态" width="108" align="center">
        <template #default="{ row }">
          <el-tag :type="statusType(row.task_status)" effect="plain" size="small">
            {{ statusLabel(row.task_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="output_text" label="输出日志" min-width="320" show-overflow-tooltip>
        <template #default="{ row }">{{ row.output_text || '--' }}</template>
      </el-table-column>
      <template #empty>
        <div class="vlm-empty">
          <el-icon :size="34"><Tickets /></el-icon>
          <strong>暂无任务明细</strong>
          <span>当前主任务尚未写入 vlm_tasks_item 记录</span>
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
    v-model="executionDialogVisible"
    title="新增执行"
    width="720px"
    class="vlm-execution-dialog"
    :close-on-click-modal="!executing"
    :close-on-press-escape="!executing"
  >
    <div v-loading="contextLoading">
      <el-form
        ref="executionFormRef"
        :model="executionForm"
        :rules="executionRules"
        label-position="top"
      >
        <el-form-item
          :label="executionContext
            ? `提示词模版 · ${executionContext.prompt_title}`
            : '提示词模版'"
        >
          <el-input
            :model-value="executionContext?.prompt_content ?? ''"
            type="textarea"
            :rows="8"
            resize="none"
            readonly
            placeholder="正在读取主任务提示词模版"
          />
        </el-form-item>

        <el-form-item label="任务输入">
          <el-input
            :model-value="executionContext?.task_input ?? ''"
            type="textarea"
            :rows="4"
            resize="none"
            readonly
            placeholder="正在读取主任务输入"
          />
        </el-form-item>

        <el-form-item label="模型 ID" prop="model_id">
          <el-select
            v-model="executionForm.model_id"
            filterable
            placeholder="请选择模型管理中的模型"
            no-data-text="模型管理中暂无可用模型"
          >
            <el-option
              v-for="model in models"
              :key="model.id"
              :label="model.model_id"
              :value="model.model_id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="任务执行结果">
          <el-input
            v-model="executionResult"
            type="textarea"
            :rows="10"
            resize="none"
            readonly
            placeholder="Agent 执行结果将在此显示"
          />
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button :disabled="executing" @click="executionDialogVisible = false">关闭</el-button>
      <el-button
        type="primary"
        :icon="VideoPlay"
        :loading="executing"
        :disabled="contextLoading || !executionContext || !models.length"
        @click="executeTask"
      >
        执行
      </el-button>
    </template>
  </el-dialog>
</template>
