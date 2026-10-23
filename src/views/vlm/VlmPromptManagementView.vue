<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Clock, Delete, Document, Edit, Plus, Refresh, User } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  createVlmPrompt,
  deleteVlmPrompt,
  getVlmPrompts,
  updateVlmPrompt,
  type VlmPrompt,
  type VlmPromptPayload,
} from '@/services/vlm'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number>()
const formRef = ref<FormInstance>()
const prompts = ref<VlmPrompt[]>([])
const form = reactive<VlmPromptPayload>({
  title: '',
  vlm_type: 'label',
  content: '',
  is_closed: false,
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  vlm_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  content: [{ required: true, message: '请输入 Prompt 内容', trigger: 'blur' }],
}

async function load(showMessage = false) {
  loading.value = true
  try {
    prompts.value = await getVlmPrompts()
    if (showMessage) ElMessage.success('提示词列表已刷新')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提示词列表加载失败')
  } finally {
    loading.value = false
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function resetForm() {
  editingId.value = undefined
  Object.assign(form, {
    title: '',
    vlm_type: 'label',
    content: '',
    is_closed: false,
  })
  formRef.value?.clearValidate()
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(prompt: VlmPrompt) {
  editingId.value = prompt.id
  Object.assign(form, {
    title: prompt.title,
    vlm_type: prompt.vlm_type === '挖掘' ? 'dig' : 'label',
    content: prompt.content,
    is_closed: prompt.is_closed,
  })
  dialogVisible.value = true
}

async function save() {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    if (editingId.value) {
      await updateVlmPrompt(editingId.value, form)
      ElMessage.success('提示词更新成功')
    } else {
      await createVlmPrompt(form)
      ElMessage.success('提示词创建成功')
    }
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提示词保存失败')
  } finally {
    saving.value = false
  }
}

async function remove(prompt: VlmPrompt) {
  try {
    await ElMessageBox.confirm(`确定删除提示词“${prompt.title}”吗？`, '删除提示词', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }

  try {
    await deleteVlmPrompt(prompt.id)
    ElMessage.success('提示词已删除')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提示词删除失败')
  }
}

onMounted(() => load())
</script>

<template>
  <div class="vlm-prompt-view">
    <section class="data-toolbar vlm-prompt-toolbar">
      <div class="vlm-table-title">
        <span>PROMPT REGISTRY / {{ prompts.length }} RECORDS</span>
        <div><el-icon><Document /></el-icon><strong>VLM 提示词库</strong></div>
      </div>
      <div class="vlm-prompt-toolbar-actions">
        <el-button :icon="Refresh" :loading="loading" @click="load(true)">刷新列表</el-button>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
      </div>
    </section>

    <section v-loading="loading" class="vlm-prompt-content">
      <div v-if="prompts.length" class="vlm-prompt-grid">
        <article
          v-for="prompt in prompts"
          :key="prompt.id"
          class="vlm-prompt-card"
          :class="prompt.is_closed ? 'closed' : 'open'"
        >
          <header>
            <div class="vlm-prompt-title">
              <span class="vlm-prompt-icon"><el-icon><Document /></el-icon></span>
              <div>
                <small>{{ prompt.vlm_type }}</small>
                <h3>{{ prompt.title }}</h3>
              </div>
            </div>
            <div class="vlm-prompt-card-controls">
              <span class="vlm-prompt-status">
                <i></i>{{ prompt.is_closed ? '关闭' : '开启' }}
              </span>
              <div class="vlm-prompt-actions">
                <el-tooltip content="编辑" placement="top">
                  <el-button text circle :icon="Edit" @click="openEdit(prompt)" />
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button text circle type="danger" :icon="Delete" @click="remove(prompt)" />
                </el-tooltip>
              </div>
            </div>
          </header>

          <pre class="vlm-prompt-text">{{ prompt.content }}</pre>

          <footer>
            <span><el-icon><Clock /></el-icon>{{ formatDate(prompt.update_date) }}</span>
            <span><el-icon><User /></el-icon>{{ prompt.create_by }}</span>
          </footer>
        </article>
      </div>

      <div v-else-if="!loading" class="vlm-prompt-empty">
        <el-icon :size="38"><Document /></el-icon>
        <strong>暂无提示词记录</strong>
        <span>vlm_prompt 表中暂时没有可展示的数据</span>
      </div>
    </section>
  </div>

  <el-dialog
    v-model="dialogVisible"
    :title="editingId ? '编辑提示词' : '新增提示词'"
    width="640px"
    class="vlm-prompt-dialog"
    @closed="resetForm"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" maxlength="255" show-word-limit placeholder="请输入提示词标题" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="类型" prop="vlm_type">
          <el-select v-model="form.vlm_type">
            <el-option label="标注" value="label" />
            <el-option label="挖掘" value="dig" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-segmented
            v-model="form.is_closed"
            :options="[
              { label: '开启', value: false },
              { label: '关闭', value: true },
            ]"
          />
        </el-form-item>
      </div>
      <el-form-item label="Prompt 内容" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="10"
          resize="none"
          placeholder="请输入完整的 Prompt 内容"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">
        {{ editingId ? '保存修改' : '创建提示词' }}
      </el-button>
    </template>
  </el-dialog>
</template>
