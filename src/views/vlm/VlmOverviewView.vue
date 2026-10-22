<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Connection, DataAnalysis, Refresh, Tickets } from '@element-plus/icons-vue'
import { BarChart, GaugeChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { init, use, type ECharts, type EChartsCoreOption } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import { getVlmOverview, type VlmOverview } from '@/services/vlm'

use([BarChart, GaugeChart, LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const router = useRouter()
const loading = ref(true)
const refreshing = ref(false)
const taskChartRef = ref<HTMLElement>()
const accuracyChartRef = ref<HTMLElement>()
const tokenChartRef = ref<HTMLElement>()
const overview = ref<VlmOverview>({
  task_total: 0,
  overall_accuracy: null,
  token_total: 0,
  task_trend: [],
  token_trend: [],
  data_status: 'pending',
})
const charts: ECharts[] = []
let resizeObserver: ResizeObserver | undefined

const chartText = '#839694'
const gridLine = 'rgba(151, 184, 179, 0.11)'

function taskOption(): EChartsCoreOption {
  return {
    animationDuration: 500,
    grid: { left: 4, right: 4, top: 12, bottom: 2 },
    xAxis: {
      type: 'category',
      data: overview.value.task_trend.map((item) => item.label),
      show: false,
    },
    yAxis: { type: 'value', show: false, minInterval: 1 },
    tooltip: { trigger: 'axis', valueFormatter: (value: unknown) => `${value} 个任务` },
    series: [{
      type: 'bar',
      data: overview.value.task_trend.map((item) => item.value),
      barMaxWidth: 13,
      itemStyle: { color: '#31d9d0', borderRadius: [2, 2, 0, 0] },
      showBackground: true,
      backgroundStyle: { color: 'rgba(49, 217, 208, 0.07)' },
    }],
  }
}

function accuracyOption(): EChartsCoreOption {
  const accuracy = overview.value.overall_accuracy ?? 0
  return {
    series: [{
      type: 'gauge',
      startAngle: 210,
      endAngle: -30,
      min: 0,
      max: 100,
      radius: '91%',
      progress: { show: true, width: 8, itemStyle: { color: '#84d661' } },
      axisLine: { lineStyle: { width: 8, color: [[1, 'rgba(132, 214, 97, 0.1)']] } },
      pointer: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      anchor: { show: false },
      title: { show: false },
      detail: {
        valueAnimation: true,
        color: chartText,
        fontSize: 11,
        offsetCenter: [0, '16%'],
        formatter: overview.value.overall_accuracy === null ? '待计算' : `${accuracy}%`,
      },
      data: [{ value: accuracy }],
    }],
  }
}

function tokenOption(): EChartsCoreOption {
  return {
    grid: { left: 2, right: 2, top: 14, bottom: 2 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: overview.value.token_trend.map((item) => item.label),
      show: false,
    },
    yAxis: { type: 'value', show: false },
    tooltip: { trigger: 'axis', valueFormatter: (value: unknown) => `${Number(value).toLocaleString()} tokens` },
    series: [{
      type: 'line',
      data: overview.value.token_trend.map((item) => item.value),
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: '#f0a04b' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(240, 160, 75, 0.28)' },
            { offset: 1, color: 'rgba(240, 160, 75, 0.01)' },
          ],
        },
      },
    }],
  }
}

function renderCharts() {
  charts.splice(0).forEach((chart) => chart.dispose())
  const configs: Array<[HTMLElement | undefined, EChartsCoreOption]> = [
    [taskChartRef.value, taskOption()],
    [accuracyChartRef.value, accuracyOption()],
    [tokenChartRef.value, tokenOption()],
  ]
  configs.forEach(([element, option]) => {
    if (!element) return
    const chart = init(element)
    chart.setOption(option)
    charts.push(chart)
  })
}

async function load(isRefresh = false) {
  isRefresh ? (refreshing.value = true) : (loading.value = true)
  try {
    overview.value = await getVlmOverview()
    await nextTick()
    renderCharts()
    if (isRefresh) ElMessage.success('汇总信息已刷新')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'VLM 服务暂不可用')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(async () => {
  await load()
  resizeObserver = new ResizeObserver(() => charts.forEach((chart) => chart.resize()))
  ;[taskChartRef.value, accuracyChartRef.value, tokenChartRef.value].forEach((element) => {
    if (element) resizeObserver?.observe(element)
  })
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  charts.forEach((chart) => chart.dispose())
})
</script>

<template>
  <div v-loading="loading" class="vlm-overview">
    <section class="vlm-intro-band">
      <div>
        <span class="section-index">VLM OPERATIONS / OVERVIEW</span>
        <h2>智驾多模态任务中枢</h2>
        <p>聚合打标任务、模型准确率与资源消耗，为后续数据分析预留统一入口。</p>
      </div>
      <div class="vlm-intro-actions">
        <span class="data-state"><i></i>任务统计已接入 · 其余指标待补充</span>
        <el-button :icon="Refresh" :loading="refreshing" @click="load(true)">刷新</el-button>
      </div>
    </section>

    <section class="vlm-kpi-grid">
      <article class="vlm-kpi-card cyan">
        <div class="vlm-kpi-copy">
          <span><el-icon><Tickets /></el-icon>VLM 打标任务总数</span>
          <button type="button" aria-label="查看任务列表" @click="router.push('/vlm/tasks')">
            {{ overview.task_total.toLocaleString() }}
            <el-icon><ArrowRight /></el-icon>
          </button>
          <small>点击数字查看任务列表</small>
        </div>
        <div ref="taskChartRef" class="vlm-mini-chart" aria-label="近七日任务数量图表"></div>
      </article>

      <article class="vlm-kpi-card green">
        <div class="vlm-kpi-copy">
          <span><el-icon><DataAnalysis /></el-icon>整体准确率</span>
          <strong>{{ overview.overall_accuracy === null ? '--' : `${overview.overall_accuracy}%` }}</strong>
          <small>具体计算逻辑待补充</small>
        </div>
        <div ref="accuracyChartRef" class="vlm-mini-chart gauge" aria-label="整体准确率仪表图"></div>
      </article>

      <article class="vlm-kpi-card orange">
        <div class="vlm-kpi-copy">
          <span><el-icon><Connection /></el-icon>大模型消耗</span>
          <strong>{{ overview.token_total.toLocaleString() }}</strong>
          <small>TOKENS / 计算逻辑待补充</small>
        </div>
        <div ref="tokenChartRef" class="vlm-mini-chart" aria-label="近七日 Tokens 消耗图表"></div>
      </article>
    </section>

    <section class="surface vlm-data-contract">
      <div>
        <span>DATA CONTRACT</span>
        <h3>汇总数据接入状态</h3>
      </div>
      <div class="contract-flow">
        <span class="active">任务数据源</span><i></i>
        <span>指标计算</span><i></i>
        <span>VLM 总览</span>
      </div>
      <p>任务总数与近七日趋势已接入 RDS 实时统计；准确率和 Tokens 指标仍等待计算规则确认。</p>
    </section>
  </div>
</template>
