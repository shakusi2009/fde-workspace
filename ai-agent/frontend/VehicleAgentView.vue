<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  Connection,
  Cpu,
  Promotion,
  UserFilled,
  Van,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getVehicleAgentDrivers,
  getVehicleAgentModels,
  sendVehicleAgentMessage,
  type VehicleAgentDriver,
  type VehicleAgentModel,
} from './api'

type ConversationMessage = {
  id: number
  role: 'user' | 'agent'
  content: string
  reasoningSummary?: string[]
  internetUsed?: boolean
  sources?: string[]
}

const drivers = ref<VehicleAgentDriver[]>([])
const models = ref<VehicleAgentModel[]>([])
const selectedDriverId = ref<number>()
const selectedModelId = ref('')
const sessionId = ref(crypto.randomUUID())
const prompt = ref('')
const messages = ref<ConversationMessage[]>([])
const driverLoading = ref(false)
const modelLoading = ref(false)
const submitting = ref(false)
const conversationRef = ref<HTMLElement>()
let messageId = 0

const selectedDriver = computed(
  () => drivers.value.find((driver) => driver.id === selectedDriverId.value),
)
const canSubmit = computed(() => (
  Boolean(
    prompt.value.trim()
    && selectedDriver.value
    && selectedModelId.value
    && !submitting.value,
  )
))

async function loadDrivers(keyword = '') {
  driverLoading.value = true
  try {
    const result = await getVehicleAgentDrivers(keyword.trim())
    const selected = selectedDriver.value
    drivers.value = selected && !result.some((driver) => driver.id === selected.id)
      ? [selected, ...result]
      : result
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '车主列表加载失败')
  } finally {
    driverLoading.value = false
  }
}

async function loadModels() {
  modelLoading.value = true
  try {
    models.value = await getVehicleAgentModels()
    if (models.value.length === 1) {
      selectedModelId.value = models.value[0].model_id
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '模型列表加载失败')
  } finally {
    modelLoading.value = false
  }
}

function scrollConversation() {
  nextTick(() => {
    if (conversationRef.value) {
      conversationRef.value.scrollTop = conversationRef.value.scrollHeight
    }
  })
}

async function submitPrompt() {
  const driver = selectedDriver.value
  const content = prompt.value.trim()
  if (!driver) {
    ElMessage.warning('请先选择车主')
    return
  }
  if (!selectedModelId.value) {
    ElMessage.warning('请先选择模型')
    return
  }
  if (!content || submitting.value) return

  messages.value.push({
    id: ++messageId,
    role: 'user',
    content,
  })
  prompt.value = ''
  submitting.value = true
  scrollConversation()

  try {
    const result = await sendVehicleAgentMessage(
      sessionId.value,
      selectedModelId.value,
      driver,
      content,
    )
    messages.value.push({
      id: ++messageId,
      role: 'agent',
      content: result.answer,
      reasoningSummary: result.reasoning_summary,
      internetUsed: result.internet_used,
      sources: result.sources,
    })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '车端 Agent 暂不可用')
  } finally {
    submitting.value = false
    scrollConversation()
  }
}

watch(
  [selectedModelId, selectedDriverId],
  ([modelId, driverId], [previousModelId, previousDriverId]) => {
    if (
      modelId === previousModelId
      && driverId === previousDriverId
    ) return

    sessionId.value = crypto.randomUUID()
    messages.value = []
  },
)

onMounted(() => {
  loadDrivers()
  loadModels()
})
</script>

<template>
  <section class="vehicle-agent-workspace">
    <div class="agent-stage">
      <div class="workspace-grid">
        <aside class="control-column">
          <div class="selector-row">
            <div class="selector-control model-selector">
              <span>推理模型</span>
              <el-select
                v-model="selectedModelId"
                filterable
                :loading="modelLoading"
                placeholder="选择模型"
                aria-label="推理模型"
              >
                <el-option
                  v-for="model in models"
                  :key="model.id"
                  :label="model.model_id"
                  :value="model.model_id"
                />
              </el-select>
            </div>

            <div class="selector-control driver-selector">
              <span>选择车主</span>
              <el-select
                v-model="selectedDriverId"
                filterable
                remote
                clearable
                :remote-method="loadDrivers"
                :loading="driverLoading"
                placeholder="搜索姓名或 VIN"
                aria-label="选择车主"
              >
                <el-option
                  v-for="driver in drivers"
                  :key="driver.id"
                  :label="`${driver.name}｜${driver.vin}｜${driver.registration_city}`"
                  :value="driver.id"
                />
              </el-select>
            </div>
          </div>

          <div class="driver-profile">
            <div class="profile-heading">
              <el-icon><UserFilled /></el-icon>
              <span>VEHICLE CONTEXT</span>
            </div>
            <dl>
              <div>
                <dt>车主</dt>
                <dd>{{ selectedDriver?.name || '--' }}</dd>
              </div>
              <div>
                <dt>车型</dt>
                <dd>{{ selectedDriver?.vehicle_model || '--' }}</dd>
              </div>
              <div>
                <dt>VIN</dt>
                <dd>{{ selectedDriver?.vin || '--' }}</dd>
              </div>
              <div>
                <dt>城市</dt>
                <dd>{{ selectedDriver?.registration_city || '--' }}</dd>
              </div>
            </dl>
          </div>
        </aside>

        <main class="conversation-panel">
          <div ref="conversationRef" class="conversation-stream">
            <div
              v-for="message in messages"
              :key="message.id"
              class="message-row"
              :class="message.role"
            >
              <span v-if="message.role === 'agent'" class="message-avatar">
                <el-icon><Van /></el-icon>
              </span>
              <p v-if="message.role === 'user'">{{ message.content }}</p>
              <div v-else class="agent-message">
                <div class="reasoning-summary">
                  <div class="reasoning-heading">
                    <span>
                      <el-icon><Cpu /></el-icon>
                      思考过程（摘要）
                    </span>
                    <span
                      v-if="message.internetUsed"
                      class="internet-status"
                    >
                      <el-icon><Connection /></el-icon>
                      已联网
                    </span>
                  </div>
                  <ol>
                    <li
                      v-for="step in message.reasoningSummary"
                      :key="step"
                    >
                      {{ step }}
                    </li>
                  </ol>
                  <div
                    v-if="message.sources?.length"
                    class="source-line"
                  >
                    数据来源：{{ message.sources.join('、') }}
                  </div>
                </div>
                <p>{{ message.content }}</p>
              </div>
            </div>
          </div>

          <div class="prompt-composer" :class="{ active: prompt.trim() }">
            <el-input
              v-model="prompt"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              maxlength="1000"
              resize="none"
              placeholder="请输入问题，帮您解答"
              :disabled="submitting"
              @keydown.ctrl.enter.prevent="submitPrompt"
            />
            <el-tooltip content="提交问题" placement="top">
              <el-button
                v-if="prompt.trim()"
                type="primary"
                circle
                :icon="Promotion"
                :loading="submitting"
                :disabled="!canSubmit"
                aria-label="提交问题"
                @click="submitPrompt"
              />
            </el-tooltip>
          </div>
        </main>
      </div>
    </div>
  </section>
</template>

<style scoped>
.vehicle-agent-workspace {
  min-height: calc(100vh - 148px);
  color: #d7e2df;
}

.agent-stage {
  min-height: 640px;
  padding: 22px 20px 20px;
  overflow: hidden;
  border: 1px solid #1d3735;
  background:
    linear-gradient(rgba(32, 72, 68, 0.09) 1px, transparent 1px),
    linear-gradient(90deg, rgba(32, 72, 68, 0.09) 1px, transparent 1px),
    #081210;
  background-size: 32px 32px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
  gap: 24px;
}

.control-column {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 18px;
}

.selector-row {
  display: grid;
  gap: 14px;
}

.selector-control {
  display: grid;
  gap: 7px;
}

.selector-control > span {
  color: #718783;
  font-size: 12px;
  white-space: nowrap;
}

.profile-heading span {
  color: #6f8581;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.driver-profile {
  border: 1px solid rgba(57, 82, 79, 0.78);
  background: rgba(8, 24, 21, 0.68);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.profile-heading {
  min-height: 46px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  gap: 9px;
  color: #84d661;
  border-bottom: 1px solid #1d3735;
}

.driver-profile dl {
  margin: 0;
}

.driver-profile dl div {
  min-height: 60px;
  padding: 11px 14px;
  display: grid;
  gap: 5px;
  border-bottom: 1px solid rgba(29, 55, 53, 0.72);
}

.driver-profile dl div:last-child {
  border-bottom: 0;
}

.driver-profile dt {
  color: #607671;
  font-size: 11px;
}

.driver-profile dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  color: #dce7e4;
  font-size: 13px;
}

.conversation-panel {
  min-height: 594px;
  padding: 18px;
  display: grid;
  grid-template-rows: minmax(360px, 1fr) auto;
  gap: 18px;
  border: 1px solid rgba(49, 217, 208, 0.24);
  background: rgba(9, 25, 23, 0.52);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025);
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
}

.conversation-stream {
  min-height: 360px;
  max-height: 470px;
  padding: 18px;
  overflow-y: auto;
  border: 1px solid rgba(132, 214, 97, 0.2);
  background:
    linear-gradient(145deg, rgba(132, 214, 97, 0.075), rgba(12, 31, 27, 0.32));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.message-row {
  margin-bottom: 22px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row p {
  max-width: min(78%, 760px);
  margin: 0;
  padding: 13px 16px;
  color: #dce7e4;
  line-height: 1.7;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.agent-message {
  width: min(78%, 760px);
  border: 1px solid rgba(132, 214, 97, 0.2);
  background: rgba(132, 214, 97, 0.07);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.reasoning-summary {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(132, 214, 97, 0.16);
  background: rgba(4, 18, 16, 0.24);
}

.reasoning-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #91a6a1;
  font-size: 11px;
}

.reasoning-heading > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.internet-status {
  color: #31d9d0;
  white-space: nowrap;
}

.reasoning-summary ol {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #819993;
  font-size: 11px;
  line-height: 1.7;
}

.source-line {
  margin-top: 8px;
  color: #607b75;
  font-size: 10px;
  overflow-wrap: anywhere;
}

.message-row.user p {
  color: #eaf2f0;
  border: 1px solid rgba(49, 217, 208, 0.26);
  background: rgba(49, 217, 208, 0.1);
  box-shadow: 0 8px 24px rgba(1, 14, 12, 0.18);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.message-row.agent p {
  width: 100%;
  max-width: none;
  color: #c5d5d1;
}

.message-avatar {
  flex: 0 0 auto;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  color: #84d661;
  border: 1px solid rgba(132, 214, 97, 0.38);
}

.prompt-composer {
  position: relative;
  width: 100%;
  padding: 6px;
  border: 1px solid rgba(49, 217, 208, 0.3);
  background:
    linear-gradient(145deg, rgba(49, 217, 208, 0.08), rgba(7, 20, 18, 0.54));
  box-shadow: 0 12px 30px rgba(1, 12, 10, 0.2);
  backdrop-filter: blur(16px) saturate(125%);
  -webkit-backdrop-filter: blur(16px) saturate(125%);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.prompt-composer.active {
  border-color: rgba(49, 217, 208, 0.62);
  box-shadow: 0 0 18px rgba(49, 217, 208, 0.08);
}

.prompt-composer :deep(.el-textarea__inner) {
  min-height: 68px !important;
  padding: 13px 54px 13px 14px;
  color: #dce7e4;
  border: 0;
  box-shadow: none;
  background: transparent;
}

.prompt-composer .el-button {
  position: absolute;
  right: 14px;
  bottom: 14px;
  width: 34px;
  height: 34px;
}

@media (max-width: 900px) {
  .agent-stage {
    min-height: 700px;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .driver-profile dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .driver-profile dl div:nth-child(odd) {
    border-right: 1px solid rgba(29, 55, 53, 0.72);
  }

  .conversation-panel {
    min-height: 500px;
  }
}

@media (max-width: 560px) {
  .vehicle-agent-workspace {
    min-height: auto;
  }

  .agent-stage {
    min-height: 760px;
    padding: 14px 12px;
  }

  .driver-profile dl {
    grid-template-columns: 1fr;
  }

  .driver-profile dl div:nth-child(odd) {
    border-right: 0;
  }

  .conversation-panel {
    min-height: 470px;
    padding: 12px;
  }

  .conversation-stream {
    min-height: 300px;
    padding: 12px;
  }

  .message-row p {
    max-width: 88%;
  }

  .agent-message {
    width: 88%;
  }
}
</style>
