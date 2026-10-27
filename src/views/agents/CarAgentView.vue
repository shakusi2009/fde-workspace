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
  getCityWeather,
  getDriverOptions,
  type CityWeather,
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
  tone?: 'critical' | 'bright' | 'success'
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
const flowStageRef = ref<HTMLElement>()
const routeNodeRef = ref<HTMLElement>()
const callNodeRef = ref<HTMLElement>()
const vehiclePanelRef = ref<HTMLElement>()
const cloudPanelRef = ref<HTMLElement>()
const state = ref<FlowState>('idle')
const handoffStep = ref(0)
const driverLoading = ref(false)
const modelLoading = ref(false)
const networkLayout = ref({
  width: 1000,
  height: 720,
  vehicleRoute: 'M 200 136 V 76 H 326',
  routeCall: 'M 480 76 H 520',
  callCloud: 'M 674 76 H 800 V 136',
  cloudVehicle: 'M 560 526 H 440',
})
let runId = 0
let networkResizeObserver: ResizeObserver | undefined
let networkFrame = 0

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
  handoffStep.value = 0
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
  addVehicleLog(`已接收车主指令：${input}`, 'critical')

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog(
    `收集车主信息：${driver.name}｜${driver.vehicle_model}｜${driver.registration_city}`,
  )

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog('理解车主意图：基于车主习惯进行备车')

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog('A2A 请求已封装并发送云端')

  state.value = 'handoff'
  for (const step of [1, 2, 3]) {
    handoffStep.value = step
    if (!(await delay(3000, currentRun))) return
  }
  handoffStep.value = 0
  state.value = 'cloud_running'
  addCloudLog(
    `收到来自 ${driver.name} 车辆的 A2A 请求，车主所在城市：${driver.registration_city}`,
    'critical',
  )

  const contextMessages = [
    `云端 Agent 正在分析 ${driver.name}车主 的任务上下文`,
  ]
  for (const message of contextMessages) {
    if (!(await waitForNextLog(currentRun))) return
    addCloudLog(message)
  }

  if (!(await waitForNextLog(currentRun))) return
  addCloudLog(`联网查询当前所在城市 ${driver.registration_city} 天气`)

  let weather: CityWeather
  try {
    weather = await getCityWeather(driver.registration_city)
  } catch (error) {
    if (currentRun !== runId) return
    const message = error instanceof Error ? error.message : '真实天气查询失败'
    addCloudLog(`真实天气查询失败：${message}`, 'critical')
    state.value = 'failed'
    ElMessage.error(message)
    return
  }
  if (currentRun !== runId) return

  if (!(await waitForNextLog(currentRun))) return
  addCloudLog(weather.weather_log)

  if (!(await waitForNextLog(currentRun))) return
  addCloudLog(weather.recommendation, 'bright')

  if (!(await waitForNextLog(currentRun))) return
  addCloudLog('个性化备车指令已完成')

  if (!(await waitForNextLog(currentRun))) return
  addCloudLog('备车指令已回传车端', 'success')
  state.value = 'returning'

  if (!(await waitForNextLog(currentRun))) return
  state.value = 'vehicle_running'
  const vehicleCommand = `接受到云端指令：${weather.recommendation}`
  addVehicleLog(vehicleCommand, 'success')
  vehicleOutput.value = vehicleCommand

  if (!(await waitForNextLog(currentRun))) return
  addVehicleLog('指令已下发车端，完成', 'success')
  vehicleOutput.value = '指令已下发车端，完成'
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

function updateNetworkLayout() {
  const stage = flowStageRef.value
  const route = routeNodeRef.value
  const call = callNodeRef.value
  const vehicle = vehiclePanelRef.value
  const cloud = cloudPanelRef.value
  if (!stage || !route || !call || !vehicle || !cloud) return

  const stageRect = stage.getBoundingClientRect()
  const routeRect = route.getBoundingClientRect()
  const callRect = call.getBoundingClientRect()
  const vehicleRect = vehicle.getBoundingClientRect()
  const cloudRect = cloud.getBoundingClientRect()
  const point = (x: number, y: number) => ({
    x: Math.round((x - stageRect.left) * 10) / 10,
    y: Math.round((y - stageRect.top) * 10) / 10,
  })

  const vehicleTop = point(
    vehicleRect.left + vehicleRect.width / 2,
    vehicleRect.top,
  )
  const routeLeft = point(routeRect.left, routeRect.top + routeRect.height / 2)
  const routeRight = point(routeRect.right, routeRect.top + routeRect.height / 2)
  const callLeft = point(callRect.left, callRect.top + callRect.height / 2)
  const callRight = point(callRect.right, callRect.top + callRect.height / 2)
  const cloudTop = point(cloudRect.left + cloudRect.width / 2, cloudRect.top)
  const cloudLeft = point(cloudRect.left, cloudRect.top + cloudRect.height / 2)
  const vehicleRight = point(
    vehicleRect.right,
    vehicleRect.top + vehicleRect.height / 2,
  )

  networkLayout.value = {
    width: Math.round(stageRect.width * 10) / 10,
    height: Math.round(stageRect.height * 10) / 10,
    vehicleRoute:
      `M ${vehicleTop.x} ${vehicleTop.y} V ${routeLeft.y} H ${routeLeft.x}`,
    routeCall:
      `M ${routeRight.x} ${routeRight.y} H ${callLeft.x}`,
    callCloud:
      `M ${callRight.x} ${callRight.y} H ${cloudTop.x} V ${cloudTop.y}`,
    cloudVehicle:
      `M ${cloudLeft.x} ${cloudLeft.y} H ${vehicleRight.x}`,
  }
}

function scheduleNetworkLayout() {
  window.cancelAnimationFrame(networkFrame)
  networkFrame = window.requestAnimationFrame(updateNetworkLayout)
}

onMounted(async () => {
  loadDrivers()
  loadModels()
  await nextTick()
  scheduleNetworkLayout()
  networkResizeObserver = new ResizeObserver(scheduleNetworkLayout)
  ;[
    flowStageRef.value,
    routeNodeRef.value,
    callNodeRef.value,
    vehiclePanelRef.value,
    cloudPanelRef.value,
  ].forEach((element) => {
    if (element) networkResizeObserver?.observe(element)
  })
})

onBeforeUnmount(() => {
  runId += 1
  window.cancelAnimationFrame(networkFrame)
  networkResizeObserver?.disconnect()
})
</script>

<template>
  <section class="car-agent-workspace">
    <header class="agent-toolbar">
      <div class="owner-selector">
        <span class="control-label">选择车主</span>
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
            :label="`${driver.name}｜${driver.vin}｜${driver.registration_city}`"
            :value="driver.id"
          >
            <span class="driver-option-copy">
              {{ driver.name }}｜{{ driver.vin }}｜{{ driver.registration_city }}
            </span>
          </el-option>
        </el-select>
      </div>
      <div class="model-selector">
        <span class="control-label">推理模型</span>
        <el-select
          v-model="selectedModelId"
          :loading="modelLoading"
          :disabled="isRunning || models.length === 0"
          :placeholder="models.length ? '选择模型 ID' : '暂无可用模型'"
        >
          <el-option
            v-for="model in models"
            :key="model.id"
            :label="model.model_id"
            :value="model.model_id"
          />
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

    <div
      ref="flowStageRef"
      class="flow-stage"
      :class="[`state-${state}`, `handoff-step-${handoffStep}`]"
    >
      <section class="a2a-center">
        <div class="a2a-center-heading">
          <el-icon><Connection /></el-icon>
          <div>
            <span>A2A ORCHESTRATION CENTER</span>
            <h2>A2A 中心</h2>
          </div>
          <small>{{ FLOW_LABELS[state] }}</small>
        </div>
        <div class="a2a-nodes">
          <div ref="routeNodeRef" class="a2a-node route-node">
            <span>01</span>
            <strong>A2A 路由</strong>
            <small>ROUTING</small>
          </div>
          <div class="node-link" aria-hidden="true"></div>
          <div ref="callNodeRef" class="a2a-node call-node">
            <span>02</span>
            <strong>A2A 调用</strong>
            <small>INVOKE</small>
          </div>
        </div>

        <svg class="mobile-network" viewBox="0 0 360 150" aria-hidden="true">
          <defs>
            <marker
              id="mobile-flow-arrow"
              markerWidth="7"
              markerHeight="7"
              refX="6"
              refY="3.5"
              orient="auto"
            >
              <path d="M 0 0 L 7 3.5 L 0 7 Z" />
            </marker>
          </defs>
          <path class="network-path link-vehicle-route" d="M 30 112 L 110 32" />
          <path class="network-path link-route-call" d="M 134 32 H 226" />
          <path class="network-path link-call-cloud" d="M 250 32 L 330 112" />
          <path class="network-path link-cloud-vehicle" d="M 330 132 H 30" />
          <circle v-if="handoffStep === 1" class="flow-dot" r="4">
            <animateMotion dur="3s" repeatCount="indefinite" path="M 30 112 L 110 32" />
          </circle>
          <circle v-if="handoffStep === 2" class="flow-dot" r="4">
            <animateMotion dur="3s" repeatCount="indefinite" path="M 134 32 H 226" />
          </circle>
          <circle v-if="handoffStep === 3" class="flow-dot" r="4">
            <animateMotion dur="3s" repeatCount="indefinite" path="M 250 32 L 330 112" />
          </circle>
          <circle v-if="state === 'returning'" class="flow-dot" r="4">
            <animateMotion dur="1s" repeatCount="indefinite" path="M 330 132 H 30" />
          </circle>
          <text x="30" y="104">车端</text>
          <text x="110" y="22">路由</text>
          <text x="250" y="22">调用</text>
          <text x="330" y="104">云端</text>
        </svg>
      </section>

      <svg
        class="desktop-network"
        :viewBox="`0 0 ${networkLayout.width} ${networkLayout.height}`"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <marker
            id="desktop-flow-arrow"
            markerWidth="7"
            markerHeight="7"
            refX="6"
            refY="3.5"
            orient="auto"
          >
            <path d="M 0 0 L 7 3.5 L 0 7 Z" />
          </marker>
        </defs>
        <path class="network-path link-vehicle-route" :d="networkLayout.vehicleRoute" />
        <path class="network-path link-route-call" :d="networkLayout.routeCall" />
        <path class="network-path link-call-cloud" :d="networkLayout.callCloud" />
        <path class="network-path link-cloud-vehicle" :d="networkLayout.cloudVehicle" />
        <circle v-if="handoffStep === 1" class="flow-dot" r="5">
          <animateMotion
            dur="3s"
            repeatCount="indefinite"
            :path="networkLayout.vehicleRoute"
          />
        </circle>
        <circle v-if="handoffStep === 2" class="flow-dot" r="5">
          <animateMotion
            dur="3s"
            repeatCount="indefinite"
            :path="networkLayout.routeCall"
          />
        </circle>
        <circle v-if="handoffStep === 3" class="flow-dot" r="5">
          <animateMotion
            dur="3s"
            repeatCount="indefinite"
            :path="networkLayout.callCloud"
          />
        </circle>
        <circle v-if="state === 'returning'" class="flow-dot" r="5">
          <animateMotion
            dur="1s"
            repeatCount="indefinite"
            :path="networkLayout.cloudVehicle"
          />
        </circle>
      </svg>

      <div class="agent-grid">
        <article ref="vehiclePanelRef" class="agent-panel vehicle-panel">
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
          <div class="city-field">
            <span>城市</span>
            <strong>{{ selectedDriver?.registration_city || '--' }}</strong>
          </div>
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
              :class="entry.tone"
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

      <article ref="cloudPanelRef" class="agent-panel cloud-panel">
        <header class="panel-heading">
          <div class="agent-icon cloud-icon"><el-icon><User /></el-icon></div>
          <div>
            <span>CLOUD STANDBY AGENT</span>
            <h2>云端 Agent</h2>
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
              :class="entry.tone"
            >
              <time>{{ entry.time }}</time>
              <span>{{ entry.message }}</span>
            </div>
            <p v-if="cloudLogs.length === 0">暂无运行日志</p>
          </div>
        </div>
      </article>
      </div>
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
  grid-template-columns:
    minmax(380px, 1.35fr)
    minmax(240px, 0.85fr)
    minmax(200px, auto)
    auto;
  align-items: center;
  gap: 18px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
}

.owner-selector,
.model-selector {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.owner-selector :deep(.el-select),
.model-selector :deep(.el-select) {
  width: 100%;
}

.driver-option-copy {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.flow-stage {
  min-width: 0;
  position: relative;
}

.a2a-center {
  min-height: 122px;
  position: relative;
  display: grid;
  grid-template-columns: minmax(210px, 1fr) auto minmax(210px, 1fr);
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  border: 1px solid rgba(49, 217, 208, 0.3);
  border-top: 2px solid var(--cyan);
  border-radius: 6px;
  background:
    linear-gradient(90deg, rgba(49, 217, 208, 0.035), transparent 30% 70%, rgba(49, 217, 208, 0.035)),
    rgba(13, 24, 25, 0.96);
  overflow: hidden;
}

.a2a-center::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(49, 217, 208, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(49, 217, 208, 0.035) 1px, transparent 1px);
  background-size: 22px 22px;
  pointer-events: none;
}

.a2a-center-heading,
.a2a-nodes {
  position: relative;
  z-index: 4;
}

.a2a-center-heading {
  min-width: 0;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  align-items: center;
  gap: 11px;
}

.a2a-center-heading > .el-icon {
  width: 36px;
  height: 36px;
  color: var(--cyan);
  border: 1px solid rgba(49, 217, 208, 0.36);
  border-radius: 4px;
  background: rgba(49, 217, 208, 0.07);
  font-size: 19px;
}

.a2a-center-heading span,
.a2a-center-heading small,
.a2a-node small {
  color: var(--muted);
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
}

.a2a-center-heading h2 {
  margin: 4px 0 0;
  color: var(--text);
  font-size: 17px;
  font-weight: 600;
}

.a2a-center-heading > small {
  grid-column: 2;
  color: var(--cyan);
}

.a2a-nodes {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 64px;
}

.a2a-node {
  width: 142px;
  height: 72px;
  position: relative;
  display: grid;
  place-content: center;
  gap: 3px;
  border: 1px solid var(--line-strong);
  border-radius: 4px;
  background: #0a1516;
  text-align: center;
  box-shadow: 0 0 0 5px rgba(49, 217, 208, 0.025);
}

.a2a-node > span {
  position: absolute;
  left: 8px;
  top: 7px;
  color: #53706c;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 8px;
}

.a2a-node strong {
  color: #d9e8e6;
  font-size: 14px;
  font-weight: 600;
}

.a2a-center > small {
  position: relative;
  z-index: 4;
  justify-self: end;
  color: #81928f;
  font-size: 11px;
  line-height: 1.55;
  text-align: right;
}

.agent-grid {
  min-width: 0;
  margin-top: 14px;
  display: grid;
  grid-template-columns: minmax(340px, 1fr) minmax(340px, 1fr);
  align-items: stretch;
  gap: 120px;
}

.agent-panel {
  min-width: 0;
  min-height: 620px;
  position: relative;
  z-index: 1;
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

.vehicle-profile > div:nth-child(2n) {
  border-right: 0;
}

.vehicle-profile > div:nth-child(n + 3) {
  border-top: 1px solid var(--line);
}

.vehicle-profile span,
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

.log-stream div.bright span {
  color: #f3f7f6;
}

.log-stream div.success span {
  color: var(--green);
}

.log-stream span {
  white-space: pre-wrap;
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

.desktop-network {
  position: absolute;
  z-index: 3;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.mobile-network {
  display: none;
}

.network-path {
  fill: none;
  stroke: rgba(131, 150, 148, 0.5);
  stroke-width: 1.2;
  stroke-linecap: round;
  stroke-dasharray: 3 4;
  vector-effect: non-scaling-stroke;
  marker-end: url("#desktop-flow-arrow");
}

.desktop-network marker path,
.mobile-network marker path {
  fill: rgba(131, 150, 148, 0.8);
}

.flow-dot {
  fill: var(--cyan);
  filter: drop-shadow(0 0 4px rgba(49, 217, 208, 0.9));
}

.handoff-step-1 .link-vehicle-route,
.handoff-step-2 .link-route-call,
.handoff-step-3 .link-call-cloud,
.state-returning .link-cloud-vehicle {
  stroke: var(--cyan);
  stroke-width: 1.6;
  filter: drop-shadow(0 0 4px rgba(49, 217, 208, 0.7));
}

.state-handoff .a2a-node,
.state-cloud_running .call-node,
.state-returning .a2a-node {
  border-color: rgba(49, 217, 208, 0.65);
  box-shadow: 0 0 16px rgba(49, 217, 208, 0.12);
}

@keyframes status-pulse {
  50% { opacity: 0.45; }
}

@media (max-width: 1180px) {
  .agent-toolbar {
    grid-template-columns:
      minmax(240px, 1.25fr)
      minmax(170px, 0.75fr)
      auto
      auto;
  }

  .agent-grid {
    grid-template-columns: minmax(300px, 1fr) minmax(300px, 1fr);
    gap: 96px;
  }

  .a2a-center {
    grid-template-columns: minmax(190px, 0.8fr) auto minmax(100px, 0.55fr);
  }

  .a2a-nodes {
    gap: 54px;
  }
}

@media (max-width: 900px) {
  .agent-toolbar {
    grid-template-columns: 1fr auto;
  }

  .owner-selector {
    grid-column: 1 / -1;
  }

  .model-selector {
    grid-column: 1 / -1;
  }

  .flow-status {
    justify-content: flex-start;
  }

  .a2a-center {
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
  }

  .a2a-center-heading {
    justify-self: stretch;
  }

  .agent-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
  }

  .agent-panel {
    min-height: 580px;
  }

  .desktop-network {
    display: none;
  }

  .mobile-network {
    width: min(100%, 440px);
    height: auto;
    position: relative;
    z-index: 3;
    display: block;
    justify-self: center;
    overflow: visible;
  }

  .mobile-network .network-path {
    marker-end: url("#mobile-flow-arrow");
  }

  .mobile-network text {
    fill: var(--muted);
    font-size: 9px;
    text-anchor: middle;
  }
}

@media (max-width: 520px) {
  .agent-toolbar {
    gap: 10px;
  }

  .owner-selector,
  .model-selector {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .flow-status {
    flex-wrap: wrap;
  }

  .a2a-center {
    padding: 14px;
  }

  .a2a-nodes {
    width: 100%;
    gap: 20px;
  }

  .a2a-node {
    width: min(142px, calc((100vw - 78px) / 2));
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
  .status-light {
    animation: none !important;
  }

  .flow-dot {
    display: none !important;
  }
}
</style>
