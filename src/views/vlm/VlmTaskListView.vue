<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Refresh, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getVlmTasks, type VlmTask } from '@/services/vlm'

const loading = ref(false)
const tasks = ref<VlmTask[]>([])
const total = ref(0)
const page = ref(1)
const PAGE_SIZE = 10
const percentageFormatter = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 })
type TaskStatusTagType = 'success' | 'warning' | 'info' | 'danger'

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
      <el-button :icon="Refresh" :loading="loading" @click="load(true)">刷新列表</el-button>
    </div>

    <div class="table-meta">
      <span>火山引擎 RDS · 每页 {{ PAGE_SIZE }} 条</span>
      <strong>{{ total }} TASKS</strong>
    </div>

    <el-table v-loading="loading" :data="tasks" row-key="sequence" class="tech-table vlm-task-table">
      <el-table-column prop="sequence" label="序号" width="86" align="center" />
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
</template>
