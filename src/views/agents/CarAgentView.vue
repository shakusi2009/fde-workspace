<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  ArrowRight,
  Connection,
  Cpu,
  Refresh,
  User,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getDriverOptions,
  type DriverOption,
} from '@/services/agentData'
import {
  getVlmModels,
  type VlmModel,
} from '@/services/vlm'

type FlowState =
  | 'idle'
  | 'validating'
  | 'vehicle_running'
  | 'handoff'
  | 'cloud_running'
  | 'returning'
  | 'completed'
  | 'failed'
type LogEntry = {
  time: string
  message: string
  tone?: 'critical'
}

const FLOW_LABELS: Record<FlowState, string> = {
  idle: '等待指令',
  validating: '校验上下文',
  vehicle_running: '车端处理中',
  handoff: 'A2A 传输中',
  cloud_running: '云端处理中',
  returning: '结果回传中',
  completed: '协作完成',
  failed: '执行中断',
}

const drivers = ref<DriverOption[]>([])
const models = ref<VlmModel[]>([])
const selectedDriverId = ref<number>()
const selectedModelId = ref('')
const vehicleInput = ref('')
const vehicleOutput = ref('')
const vehicleLogs = ref<LogEntry[]>([])
const cloudLogs = ref<LogEntry[]>([])
const vehicleLogRef = ref<HTMLElement>()
const cloudLogRef = ref<HTMLElement>()
const state = ref<FlowState>('idle')
const driverLoading = ref(false)
const modelLoading = ref(false)
let runId = 0

const selectedDriver = computed(
  () => drivers.value.find((driver) => driver.id === selectedDriverId.value),
)
const isRunning = computed(() => (
  !['idle', 'completed', 'failed'].includes(state.value)
))
const statusType = computed(() => {
  if (state.value === 'completed') return 'success'
  if (state.value === 'failed') return 'danger'
  if (state.value === 'idle') return 'info'
  return 'primary'
})

function timestamp() {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date())
}

function scrollLogToBottom(element: HTMLElement | undefined) {
  nextTick(() => {
    if (element) element.scrollTop = element.scrollHeight
  })
}

function addVehicleLog(message: string, tone?: LogEntry['tone']) {
  vehicleLogs.value.push({ time: timestamp(), message, tone })
  scrollLogToBottom(vehicleLogRef.value)
}

function addCloudLog(message: string, tone?: LogEntry['tone']) {
  cloudLogs.value.push({ time: timestamp(), message, tone })
  scrollLogToBottom(cloudLogRef.value)
}

function clearConversation() {
  runId += 1
  state.value = 'idle'
  vehicleInput.value = ''
  vehicleOutput.value = ''
  vehicleLogs.value = []
  cloudLogs.value = []
}

function resetSession() {
  clearConversation()
  ElMessage.success('会话已重置')
}

function handleDriverChange() {
  clearConversation()
}

function delay(milliseconds: number, currentRun: number) {
  return new Promise<boolean>((resolve) => {
    window.setTimeout(() => resolve(currentRun === runId), milliseconds)
  })
}

function waitForNextLog(currentRun: number) {
  const seconds = Math.floor(Math.random() * 5) + 1
  return delay(seconds * 1000, currentRun)
}

function validate(input: string) {
  if (!selectedDriver.value) {
    ElMessage.warning('请先选择车主')
    return false
  }
  if (!selectedModelId.value) {
    ElMessage.warning('请选择车端 Agent 模型')
    return false
  }
  if (!input.trim()) {
    ElMessage.warning('请输入 Agent 指令')
    return false
  }
  return true
}

async function sendFromVehicle() {
  if (isRunning.value || !validate(vehicleInput.value)) return
  const driver = selectedDriver.value
  if (!driver) return

  const input = vehicleInput.value.trim()
  const currentRun = ++runId
  state.value = 'vehicle_running'
  vehicleOutput.value = ''
  addVehicleLog(`已接收车主指令：${input}`)

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog(`加载车辆上下文：${driver.vehicle_model} / ${driver.vin}`)

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog('理解车主意图：基于车主习惯进行备车')

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog('A2A 请求已封装并发送云端')

  if (!(await waitForNextLog(currentRun))) return
  state.value = 'handoff'

  if (!(await waitForNextLog(currentRun))) return
  state.value = 'cloud_running'
  addCloudLog(`收到来自 ${driver.name} 车辆的 A2A 请求`, 'critical')

  const cloudMessages = [
    `备车 Agent 正在分析 ${driver.vehicle_model} 的任务上下文`,
    '查询车主当前季节习惯的温度：22度',
    '联网查询当前所在城市 北京 天气',
    '今天气温-1度，有霜冻。需要：除冰除霜、暖风预热',
    '个性化备车指令已完成',
    '备车指令已回传车端',
  ]
  for (const message of cloudMessages) {
    if (!(await waitForNextLog(currentRun))) return
    addCloudLog(message)
  }

  if (!(await waitForNextLog(currentRun))) return
  state.value = 'returning'

  if (!(await waitForNextLog(currentRun))) return
  state.value = 'vehicle_running'
  addVehicleLog(
    '已接收云端协同结果：温度设置22度；打开除冰除霜；打开暖风',
    'critical',
  )
  vehicleOutput.value = '备车协同结果已接收，正在下发车辆执行。'

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog('已下发车端执行', 'critical')
  vehicleOutput.value = '备车指令已下发：温度22度、除冰除霜、暖风预热。'
  state.value = 'completed'
}

async function loadDrivers(keyword = '') {
  driverLoading.value = true
  try {
    const result = await getDriverOptions(keyword.trim())
    const selected = selectedDriver.value
    drivers.value = selected && !result.some((item) => item.id === selected.id)
      ? [selected, ...result]
      : result
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '车主选项加载失败')
  } finally {
    driverLoading.value = false
  }
}

async function loadModels() {
  modelLoading.value = true
  try {
    models.value = await getVlmModels()
    if (models.value.length === 1) {
      selectedModelId.value = models.value[0].model_id
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '模型列表加载失败')
  } finally {
    modelLoading.value = false
  }
}

onMounted(() => {
  loadDrivers()
  loadModels()
})

onBeforeUnmount(() => {
  runId += 1
})
</script>

<template>
  <section class="car-agent-workspace">
    <header class="agent-toolbar">
      <div class="owner-selector">
        <span class="control-label">当前车辆</span>
        <el-select
          v-model="selectedDriverId"
          filterable
          remote
          clearable
          :remote-method="loadDrivers"
          :loading="driverLoading"
          placeholder="搜索姓名或 VIN 码"
          @change="handleDriverChange"
        >
          <el-option
            v-for="driver in drivers"
            :key="driver.id"
            :label="`${driver.name}｜${driver.vin}`"
            :value="driver.id"
          >
            <span>{{ driver.name }}</span>
            <small>{{ driver.vin }}</small>
          </el-option>
        </el-select>
      </div>
      <div class="flow-status">
        <span class="status-light" :class="state"></span>
        <span>{{ FLOW_LABELS[state] }}</span>
        <el-tag :type="statusType" effect="plain" size="small">
          车端 → 云端
        </el-tag>
      </div>
      <el-tooltip content="重置会话" placement="top">
        <el-button :icon="Refresh" circle aria-label="重置会话" @click="resetSession" />
      </el-tooltip>
    </header>

    <div class="agent-grid" :class="`state-${state}`">
      <article class="agent-panel vehicle-panel">
        <header class="panel-heading">
          <div class="agent-icon vehicle-icon"><el-icon><Cpu /></el-icon></div>
          <div>
            <span>ON-VEHICLE AGENT</span>
            <h2>车端 Agent</h2>
          </div>
          <el-tag type="success" effect="plain" size="small">本地节点</el-tag>
        </header>

        <div class="vehicle-profile">
          <div>
            <span>车主</span>
            <strong>{{ selectedDriver?.name || '--' }}</strong>
          </div>
          <div>
            <span>车型</span>
            <strong>{{ selectedDriver?.vehicle_model || '--' }}</strong>
          </div>
          <div class="vin-field">
            <span>VIN</span>
            <strong>{{ selectedDriver?.vin || '--' }}</strong>
          </div>
        </div>

        <div class="field-block">
          <label>推理模型</label>
          <el-select
            v-model="selectedModelId"
            :loading="modelLoading"
            :disabled="isRunning"
            placeholder="选择模型 ID"
          >
            <el-option
              v-for="model in models"
              :key="model.id"
              :label="model.model_id"
              :value="model.model_id"
            />
          </el-select>
          <p v-if="!modelLoading && models.length === 0" class="field-warning">
            暂无可用模型，请先在 VLM 总览中配置。
          </p>
        </div>

        <div class="output-block">
          <div class="block-title">
            <span>AGENT OUTPUT</span>
            <small>{{ vehicleLogs.length }} LOGS</small>
          </div>
          <div class="output-copy">
            {{ vehicleOutput || '等待车端 Agent 输出' }}
          </div>
          <div ref="vehicleLogRef" class="log-stream">
            <div
              v-for="(entry, index) in vehicleLogs"
              :key="`${entry.time}-${index}`"
              :class="{ critical: entry.tone === 'critical' }"
            >
              <time>{{ entry.time }}</time>
              <span>{{ entry.message }}</span>
            </div>
            <p v-if="vehicleLogs.length === 0">暂无运行日志</p>
          </div>
        </div>

        <div class="input-block">
          <el-input
            v-model="vehicleInput"
            type="textarea"
            :rows="3"
            maxlength="300"
            show-word-limit
            resize="none"
            :disabled="isRunning"
            placeholder="输入车端任务，例如：帮我备车"
            @keydown.ctrl.enter.prevent="sendFromVehicle"
          />
          <el-button
            type="primary"
            :icon="ArrowRight"
            :loading="isRunning"
            :disabled="isRunning || models.length === 0"
            @click="sendFromVehicle"
          >
            发送到云端
          </el-button>
        </div>
      </article>

      <div class="a2a-lane">
        <div class="a2a-badge">
          <el-icon><Connection /></el-icon>
          <strong>A2A</strong>
          <span>AGENT LINK</span>
        </div>
        <svg class="desktop-flow" viewBox="0 0 150 520" aria-hidden="true">
          <path class="flow-path forward-path" d="M 0 218 H 150" />
          <path class="flow-path reverse-path" d="M 150 302 H 0" />
          <circle class="flow-marker forward-marker" r="5">
            <animateMotion dur="1s" repeatCount="indefinite" path="M 0 218 H 150" />
          </circle>
          <circle class="flow-marker reverse-marker" r="5">
            <animateMotion dur="1s" repeatCount="indefinite" path="M 150 302 H 0" />
          </circle>
        </svg>
        <svg class="mobile-flow" viewBox="0 0 320 96" aria-hidden="true">
          <path class="flow-path forward-path" d="M 20 10 H 300" />
          <path class="flow-path reverse-path" d="M 300 86 H 20" />
          <circle class="flow-marker forward-marker" r="5">
            <animateMotion dur="1s" repeatCount="indefinite" path="M 20 10 H 300" />
          </circle>
          <circle class="flow-marker reverse-marker" r="5">
            <animateMotion dur="1s" repeatCount="indefinite" path="M 300 86 H 20" />
          </circle>
        </svg>
        <span class="lane-caption">{{ FLOW_LABELS[state] }}</span>
      </div>

      <article class="agent-panel cloud-panel">
        <header class="panel-heading">
          <div class="agent-icon cloud-icon"><el-icon><User /></el-icon></div>
          <div>
            <span>CLOUD STANDBY AGENT</span>
            <h2>备车 Agent</h2>
          </div>
          <el-tag type="warning" effect="plain" size="small">云端节点</el-tag>
        </header>

        <div class="persona">
          <strong>车辆协同与服务编排专家</strong>
          <span>接收车端上下文，生成跨域协同建议，并可主动向目标车辆下发任务。</span>
        </div>

        <div class="output-block cloud-output">
          <div class="block-title">
            <span>AGENT OUTPUT</span>
            <small>{{ cloudLogs.length }} LOGS</small>
          </div>
          <div ref="cloudLogRef" class="log-stream">
            <div
              v-for="(entry, index) in cloudLogs"
              :key="`${entry.time}-${index}`"
              :class="{ critical: entry.tone === 'critical' }"
            >
              <time>{{ entry.time }}</time>
              <span>{{ entry.message }}</span>
            </div>
            <p v-if="cloudLogs.length === 0">暂无运行日志</p>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.car-agent-workspace {
  min-width: 0;
}

.agent-toolbar {
  min-height: 64px;
  margin-bottom: 14px;
  padding: 10px 14px;
  display: grid;
  grid-template-columns: minmax(280px, 460px) 1fr auto;
  align-items: center;
  gap: 18px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
}

.owner-selector {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.owner-selector :deep(.el-select) {
  width: 100%;
}

.control-label,
.block-title,
.panel-heading > div > span {
  color: var(--muted);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.flow-status {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 9px;
  color: #b9c8c6;
  font-size: 12px;
}

.status-light {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--muted);
}

.status-light.validating,
.status-light.vehicle_running,
.status-light.handoff,
.status-light.cloud_running,
.status-light.returning {
  background: var(--cyan);
  box-shadow: 0 0 10px rgba(49, 217, 208, 0.85);
  animation: status-pulse 1s ease-in-out infinite;
}

.status-light.completed {
  background: var(--green);
}

.status-light.failed {
  background: var(--danger);
}

.agent-grid {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(340px, 1fr) 150px minmax(340px, 1fr);
  align-items: stretch;
}

.agent-panel {
  min-width: 0;
  min-height: 620px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: rgba(13, 24, 25, 0.92);
}

.vehicle-panel {
  border-top: 2px solid var(--green);
}

.cloud-panel {
  border-top: 2px solid var(--orange);
}

.panel-heading {
  min-height: 50px;
  display: grid;
  grid-template-columns: 40px 1fr auto;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--line);
}

.panel-heading h2 {
  margin: 4px 0 0;
  color: var(--text);
  font-size: 17px;
  font-weight: 600;
}

.agent-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: 1px solid;
  border-radius: 4px;
  font-size: 20px;
}

.vehicle-icon {
  color: var(--green);
  border-color: rgba(132, 214, 97, 0.35);
  background: rgba(132, 214, 97, 0.07);
}

.cloud-icon {
  color: var(--orange);
  border-color: rgba(240, 160, 75, 0.35);
  background: rgba(240, 160, 75, 0.07);
}

.vehicle-profile {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--line);
}

.vehicle-profile > div {
  min-width: 0;
  padding: 14px 12px;
  border-right: 1px solid var(--line);
}

.vehicle-profile > div:nth-child(2) {
  border-right: 0;
}

.vehicle-profile .vin-field {
  grid-column: 1 / -1;
  border-top: 1px solid var(--line);
  border-right: 0;
}

.vehicle-profile span,
.field-block label,
.persona span {
  display: block;
  margin-bottom: 6px;
  color: var(--muted);
  font-size: 11px;
}

.vehicle-profile strong {
  display: block;
  overflow: hidden;
  color: #dce9e7;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.field-block {
  padding: 14px 0 0;
}

.field-block :deep(.el-select) {
  width: 100%;
}

.field-warning {
  margin: 7px 0 0;
  color: var(--orange);
  font-size: 11px;
}

.persona {
  min-height: 91px;
  padding: 16px 12px;
  border-bottom: 1px solid var(--line);
}

.persona strong {
  display: block;
  margin-bottom: 8px;
  color: #e7dfd3;
  font-size: 13px;
}

.persona span {
  margin: 0;
  line-height: 1.6;
}

.output-block {
  min-height: 250px;
  margin-top: 14px;
  display: grid;
  grid-template-rows: auto minmax(72px, auto) minmax(100px, 1fr);
  border: 1px solid var(--line);
  border-radius: 4px;
  overflow: hidden;
}

.cloud-output {
  min-height: 0;
  margin-top: 14px;
  flex: 1;
  grid-template-rows: auto minmax(0, 1fr);
}

.block-title {
  min-height: 34px;
  padding: 0 11px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.025);
  border-bottom: 1px solid var(--line);
}

.block-title small {
  color: var(--cyan);
  font-size: 9px;
}

.output-copy {
  padding: 12px;
  color: #c6d4d2;
  font-size: 12px;
  line-height: 1.65;
  border-bottom: 1px solid var(--line);
}

.log-stream {
  max-height: 140px;
  padding: 10px 12px;
  overflow: auto;
  background: #091213;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.cloud-output .log-stream {
  max-height: none;
}

.log-stream div {
  display: grid;
  grid-template-columns: 62px minmax(0, 1fr);
  gap: 8px;
  padding: 4px 0;
  color: #a9bab7;
  line-height: 1.45;
}

.log-stream div.critical span {
  color: var(--danger);
}

.log-stream time {
  color: #5e7471;
}

.log-stream p {
  margin: 4px 0;
  color: #526461;
}

.input-block {
  margin-top: auto;
  padding-top: 14px;
  display: grid;
  gap: 10px;
}

.input-block .el-button {
  width: 100%;
  margin: 0;
}

.a2a-lane {
  min-height: 620px;
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.a2a-badge {
  position: relative;
  z-index: 2;
  width: 72px;
  height: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  background: #0a1516;
  box-shadow: 0 0 0 7px rgba(49, 217, 208, 0.035);
}

.a2a-badge .el-icon {
  color: var(--cyan);
}

.a2a-badge strong {
  margin-top: 3px;
  color: #d9e8e6;
  font-size: 12px;
}

.a2a-badge span {
  color: var(--muted);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 7px;
}

.desktop-flow {
  position: absolute;
  inset: 50% auto auto 0;
  width: 150px;
  height: 520px;
  transform: translateY(-50%);
}

.mobile-flow {
  display: none;
}

.flow-path {
  fill: none;
  stroke: rgba(131, 150, 148, 0.5);
  stroke-width: 1.5;
  stroke-dasharray: 6 7;
}

.flow-marker {
  display: none;
  fill: var(--cyan);
  filter: drop-shadow(0 0 4px var(--cyan));
}

.state-handoff .forward-path,
.state-returning .reverse-path {
  stroke: var(--cyan);
  animation: dash-forward 1s linear infinite;
}

.state-handoff .forward-marker,
.state-returning .reverse-marker {
  display: block;
}

.state-returning .reverse-path {
  animation-direction: reverse;
}

.lane-caption {
  position: absolute;
  left: 8px;
  right: 8px;
  top: calc(50% + 50px);
  color: var(--muted);
  font-size: 9px;
  text-align: center;
}

@keyframes dash-forward {
  to { stroke-dashoffset: -26; }
}

@keyframes status-pulse {
  50% { opacity: 0.45; }
}

@media (max-width: 1180px) {
  .agent-toolbar {
    grid-template-columns: minmax(260px, 1fr) auto auto;
  }

  .agent-grid {
    grid-template-columns: minmax(300px, 1fr) 116px minmax(300px, 1fr);
  }

  .desktop-flow {
    width: 116px;
  }
}

@media (max-width: 900px) {
  .agent-toolbar {
    grid-template-columns: 1fr auto;
  }

  .owner-selector {
    grid-column: 1 / -1;
  }

  .flow-status {
    justify-content: flex-start;
  }

  .agent-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .agent-panel {
    min-height: 580px;
  }

  .a2a-lane {
    min-height: 126px;
  }

  .desktop-flow {
    display: none;
  }

  .mobile-flow {
    width: min(100%, 420px);
    display: block;
  }

  .a2a-badge {
    width: 58px;
    height: 58px;
  }

  .lane-caption {
    top: auto;
    bottom: 2px;
  }
}

@media (max-width: 520px) {
  .agent-toolbar {
    gap: 10px;
  }

  .owner-selector {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .flow-status {
    flex-wrap: wrap;
  }

  .agent-panel {
    min-height: 0;
    padding: 14px;
  }

  .panel-heading {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .panel-heading > .el-tag {
    grid-column: 2;
    justify-self: start;
  }

  .agent-icon {
    width: 36px;
    height: 36px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-light,
  .flow-path {
    animation: none !important;
  }

  .flow-marker {
    display: none !important;
  }
}
</style>
