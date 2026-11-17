<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
} from 'vue'
import {
  DataAnalysis,
  Link,
  Refresh,
  Trophy,
} from '@element-plus/icons-vue'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
} from 'echarts/components'
import {
  init,
  use,
  type ECharts,
  type EChartsCoreOption,
} from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import {
  getFilteredVehicleSalesRanking,
  getSalesFilterOptions,
  getSalesPeriods,
  type SalesFilterOptions,
  type SalesPeriod,
  type VehicleSalesRanking,
} from './api'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const periods = ref<SalesPeriod[]>([])
const selectedYear = ref<number>()
const selectedMonth = ref<number>()
const vehicleType = ref('all')
const level = ref('')
const energyType = ref('')
const manufacturer = ref('')
const brandId = ref<number>()
const ranking = ref<VehicleSalesRanking>()
const filterOptions = ref<SalesFilterOptions>({
  vehicle_types: [],
  energy_types: [],
  manufacturers: [],
  brands: [],
})
const loading = ref(false)
const periodsLoading = ref(false)
const filtersLoading = ref(false)
const chartRef = ref<HTMLElement>()
let chart: ECharts | undefined
let resizeObserver: ResizeObserver | undefined

const years = computed(() => (
  [...new Set(periods.value.map((item) => item.year))]
    .sort((left, right) => right - left)
))
const months = computed(() => (
  periods.value
    .filter((item) => item.year === selectedYear.value)
    .sort((left, right) => right.month - left.month)
))
const topThree = computed(() => ranking.value?.items.slice(0, 3) ?? [])
const totalSales = computed(() => (
  ranking.value?.items.reduce((sum, item) => sum + item.sales, 0) ?? 0
))
const levelOptions = computed(() => {
  if (vehicleType.value === 'sedan') {
    return [
      { value: '', label: '全部轿车' },
      { value: 'micro', label: '微型车' },
      { value: 'small', label: '小型车' },
      { value: 'compact', label: '紧凑型车' },
      { value: 'medium', label: '中型车' },
      { value: 'medium-large', label: '中大型车' },
      { value: 'large', label: '大型车' },
    ]
  }
  if (vehicleType.value === 'suv') {
    return [
      { value: '', label: '全部 SUV' },
      { value: 'micro', label: '微型 SUV' },
      { value: 'small', label: '小型 SUV' },
      { value: 'compact', label: '紧凑型 SUV' },
      { value: 'medium', label: '中型 SUV' },
      { value: 'medium-large', label: '中大型 SUV' },
      { value: 'large', label: '大型 SUV' },
    ]
  }
  return []
})
const activeTypeLabel = computed(() => (
  filterOptions.value.vehicle_types.find(
    (item) => item.value === vehicleType.value,
  )?.label ?? '全部'
))

function chartOption(): EChartsCoreOption {
  const items = ranking.value?.items ?? []
  const maxSales = Math.max(...items.map((item) => item.sales), 0)
  return {
    animationDuration: 500,
    grid: {
      left: 142,
      right: 78,
      top: 12,
      bottom: 20,
      containLabel: false,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
        shadowStyle: { color: 'rgba(49, 217, 208, 0.05)' },
      },
      backgroundColor: '#0d1b19',
      borderColor: '#29413d',
      textStyle: { color: '#dce7e4' },
      formatter: (params: unknown) => {
        const rows = params as Array<{ dataIndex: number }>
        const item = items[rows[0]?.dataIndex ?? 0]
        if (!item) return ''
        const movement = item.previous_rank
          ? `上月第 ${item.previous_rank} 名`
          : '上月暂无排名'
        return [
          `<strong>#${item.rank} ${item.series_name}</strong>`,
          `${item.manufacturer || item.brand_name}`,
          `月销量 ${item.sales.toLocaleString()} 辆`,
          movement,
        ].join('<br/>')
      },
    },
    xAxis: {
      type: 'value',
      max: maxSales ? Math.ceil(maxSales / 5000) * 5000 : undefined,
      axisLabel: {
        color: '#6f8581',
        formatter: (value: number) => `${Math.round(value / 1000)}k`,
      },
      splitLine: {
        lineStyle: { color: 'rgba(151, 184, 179, 0.1)' },
      },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: items.map((item) => item.series_name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#b8c8c4',
        width: 124,
        overflow: 'truncate',
        formatter: (value: string, index: number) => (
          `{rank|${items[index]?.rank ?? ''}}  {name|${value}}`
        ),
        rich: {
          rank: { color: '#31d9d0', width: 22, align: 'right' },
          name: { color: '#b8c8c4', width: 92 },
        },
      },
    },
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: items.map((item, index) => ({
        value: item.sales,
        itemStyle: {
          color: index === 0
            ? '#84d661'
            : index === 1
              ? '#31d9d0'
              : index === 2
                ? '#f0a04b'
                : '#355d58',
          borderRadius: [0, 3, 3, 0],
        },
      })),
      label: {
        show: true,
        position: 'right',
        color: '#9eb0ac',
        formatter: (params: { value?: unknown }) => (
          Number(params.value ?? 0).toLocaleString()
        ),
      },
    }],
  }
}

async function renderChart() {
  await nextTick()
  if (!chartRef.value) return
  chart?.dispose()
  chart = init(chartRef.value)
  chart.setOption(chartOption())
}

async function loadRanking() {
  if (!selectedYear.value || !selectedMonth.value) return
  loading.value = true
  try {
    ranking.value = await getFilteredVehicleSalesRanking(
      selectedYear.value,
      selectedMonth.value,
      {
        vehicleType: vehicleType.value,
        level: level.value,
        energyType: energyType.value,
        manufacturer: manufacturer.value,
        brandId: brandId.value,
      },
    )
    await renderChart()
  } catch (error) {
    ranking.value = undefined
    chart?.clear()
    ElMessage.error(
      error instanceof Error ? error.message : '公开销量数据加载失败',
    )
  } finally {
    loading.value = false
  }
}

async function loadFilterOptions() {
  if (!selectedYear.value || !selectedMonth.value) return
  filtersLoading.value = true
  try {
    filterOptions.value = await getSalesFilterOptions(
      selectedYear.value,
      selectedMonth.value,
    )
    if (
      brandId.value
      && !filterOptions.value.brands.some(
        (item) => item.id === brandId.value,
      )
    ) {
      brandId.value = undefined
    }
  } catch (error) {
    ElMessage.error(
      error instanceof Error ? error.message : '销量筛选项加载失败',
    )
  } finally {
    filtersLoading.value = false
  }
}

async function loadPeriods() {
  periodsLoading.value = true
  try {
    const result = await getSalesPeriods()
    periods.value = result.periods
    const latest = periods.value[0]
    if (latest) {
      selectedYear.value = latest.year
      selectedMonth.value = latest.month
      await loadFilterOptions()
      await loadRanking()
    }
  } catch (error) {
    ElMessage.error(
      error instanceof Error ? error.message : '可用销量月份加载失败',
    )
  } finally {
    periodsLoading.value = false
  }
}

async function handleYearChange() {
  selectedMonth.value = months.value[0]?.month
  await handlePeriodChange()
}

async function handlePeriodChange() {
  await loadFilterOptions()
  await loadRanking()
}

function handleVehicleTypeChange(value: string) {
  vehicleType.value = value
  level.value = ''
  energyType.value = ''
  loadRanking()
}

onMounted(() => {
  resizeObserver = new ResizeObserver(() => chart?.resize())
  if (chartRef.value) resizeObserver.observe(chartRef.value)
  loadPeriods()
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
})
</script>

<template>
  <section class="insight-workspace">
    <div class="filter-surface">
      <div class="vehicle-type-tabs" aria-label="车型大类">
        <button
          v-for="item in filterOptions.vehicle_types"
          :key="item.value"
          type="button"
          :class="{ active: vehicleType === item.value }"
          @click="handleVehicleTypeChange(item.value)"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="insight-toolbar">
        <div class="filter-group">
          <label v-if="levelOptions.length">
            <span>车型级别</span>
            <el-select
              v-model="level"
              aria-label="车型级别"
              @change="loadRanking"
            >
              <el-option
                v-for="item in levelOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </label>
          <label v-if="vehicleType === 'new-energy'">
            <span>能源类型</span>
            <el-select
              v-model="energyType"
              aria-label="能源类型"
              @change="loadRanking"
            >
              <el-option
                v-for="item in filterOptions.energy_types"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </label>
          <label>
            <span>厂商属性</span>
            <el-select
              v-model="manufacturer"
              aria-label="厂商属性"
              @change="loadRanking"
            >
              <el-option
                v-for="item in filterOptions.manufacturers"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </label>
          <label>
            <span>品牌</span>
            <el-select
              v-model="brandId"
              filterable
              clearable
              :loading="filtersLoading"
              placeholder="全部品牌"
              aria-label="品牌"
              @change="loadRanking"
            >
              <el-option
                v-for="item in filterOptions.brands"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
          </label>
        <label>
          <span>年份</span>
          <el-select
            v-model="selectedYear"
            :loading="periodsLoading"
            aria-label="销量年份"
            @change="handleYearChange"
          >
            <el-option
              v-for="year in years"
              :key="year"
              :label="`${year} 年`"
              :value="year"
            />
          </el-select>
        </label>
        <label>
          <span>月份</span>
          <el-select
            v-model="selectedMonth"
            :loading="periodsLoading"
            aria-label="销量月份"
            @change="handlePeriodChange"
          >
            <el-option
              v-for="item in months"
              :key="item.period"
              :label="`${item.month} 月`"
              :value="item.month"
            />
          </el-select>
        </label>
        </div>

        <el-tooltip content="刷新公开数据" placement="top">
          <el-button
            circle
            :icon="Refresh"
            :loading="loading"
            aria-label="刷新公开数据"
            @click="loadRanking"
          />
        </el-tooltip>
      </div>
    </div>

    <div v-if="ranking" class="source-strip">
      <span>
        <el-icon><DataAnalysis /></el-icon>
        {{ ranking.year }} 年 {{ ranking.month }} 月
        {{ activeTypeLabel }}车系零售量
      </span>
      <span>{{ ranking.source_note }}</span>
      <a :href="ranking.source_url" target="_blank" rel="noreferrer">
        {{ ranking.source_name }}公开数据
        <el-icon><Link /></el-icon>
      </a>
    </div>

    <div v-loading="loading" class="insight-content">
      <div v-if="topThree.length" class="leader-strip">
        <article
          v-for="item in topThree"
          :key="item.series_id"
          class="leader-item"
        >
          <span class="leader-rank">
            <el-icon><Trophy /></el-icon>
            TOP {{ item.rank }}
          </span>
          <strong>{{ item.series_name }}</strong>
          <small>{{ item.manufacturer || item.brand_name }}</small>
          <b>{{ item.sales.toLocaleString() }} <em>辆</em></b>
        </article>
        <div class="sample-total">
          <span>TOP {{ ranking?.items.length || 0 }} 合计</span>
          <strong>{{ totalSales.toLocaleString() }} 辆</strong>
        </div>
      </div>

      <div class="ranking-panel">
        <header>
          <div>
            <span>MODEL SALES RANKING</span>
            <h2>车型月销量排名</h2>
          </div>
          <small>单位：辆</small>
        </header>
        <div
          v-if="ranking?.items.length"
          ref="chartRef"
          class="ranking-chart"
          role="img"
          :aria-label="`${ranking.period} 车型销量排名图`"
        ></div>
        <el-empty
          v-else-if="!loading"
          description="该月份暂无公开销量数据"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.insight-workspace {
  min-height: calc(100vh - 148px);
  color: #dce7e4;
}

.filter-surface {
  border: 1px solid #263d39;
  background: #0a1715;
}

.vehicle-type-tabs {
  min-height: 58px;
  padding: 9px 12px;
  display: flex;
  align-items: stretch;
  gap: 8px;
  overflow-x: auto;
  border-bottom: 1px solid #263d39;
}

.vehicle-type-tabs button {
  flex: 0 0 126px;
  min-height: 38px;
  border: 1px solid #304843;
  color: #9db0ab;
  background: #101f1d;
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}

.vehicle-type-tabs button:hover {
  border-color: #31d9d0;
  color: #dce7e4;
}

.vehicle-type-tabs button.active {
  border-color: #31d9d0;
  color: #071310;
  background: #31d9d0;
}

.insight-toolbar {
  min-height: 78px;
  padding: 11px 12px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.filter-group {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 10px;
}

.filter-group label {
  width: 138px;
  display: grid;
  gap: 6px;
}

.filter-group label > span {
  color: #718783;
  font-size: 11px;
}

.source-strip {
  min-height: 42px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  gap: 22px;
  border: 1px solid #263d39;
  border-top: 0;
  color: #7f9691;
  background: #0c1b18;
  font-size: 11px;
}

.source-strip span,
.source-strip a {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.source-strip span:first-child {
  color: #bfd0cc;
}

.source-strip a {
  margin-left: auto;
  color: #31d9d0;
  text-decoration: none;
}

.insight-content {
  min-height: 640px;
  padding-top: 16px;
}

.leader-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) minmax(180px, 0.8fr);
  gap: 12px;
}

.leader-item,
.sample-total {
  min-height: 112px;
  padding: 14px;
  border: 1px solid #263d39;
  background: #0b1917;
}

.leader-item {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: start;
  gap: 4px 12px;
}

.leader-rank {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #84d661;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 10px;
}

.leader-item strong {
  grid-column: 1;
  overflow-wrap: anywhere;
  font-size: 15px;
}

.leader-item small {
  grid-column: 1;
  color: #708681;
  font-size: 11px;
}

.leader-item b {
  grid-column: 2;
  grid-row: 1 / span 3;
  align-self: center;
  color: #dce7e4;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 18px;
}

.leader-item em {
  color: #708681;
  font-size: 10px;
  font-style: normal;
}

.sample-total {
  display: grid;
  align-content: center;
  gap: 8px;
  border-color: rgba(240, 160, 75, 0.38);
}

.sample-total span {
  color: #8f9d99;
  font-size: 11px;
}

.sample-total strong {
  color: #f0a04b;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 17px;
}

.ranking-panel {
  margin-top: 16px;
  border: 1px solid #263d39;
  background:
    linear-gradient(rgba(32, 72, 68, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(32, 72, 68, 0.08) 1px, transparent 1px),
    #091512;
  background-size: 32px 32px;
}

.ranking-panel header {
  min-height: 64px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #263d39;
}

.ranking-panel header span {
  color: #59726c;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 9px;
}

.ranking-panel h2 {
  margin: 3px 0 0;
  font-size: 14px;
}

.ranking-panel header small {
  color: #708681;
  font-size: 10px;
}

.ranking-chart {
  width: 100%;
  height: 720px;
}

@media (max-width: 900px) {
  .leader-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .vehicle-type-tabs button {
    flex-basis: 104px;
  }

  .insight-toolbar {
    align-items: flex-end;
  }

  .filter-group {
    min-width: 0;
    flex: 1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-group label {
    width: auto;
    min-width: 0;
  }

  .source-strip {
    padding: 10px 12px;
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .source-strip a {
    margin-left: 0;
  }

  .leader-strip {
    grid-template-columns: 1fr;
  }

  .ranking-chart {
    height: 660px;
  }
}
</style>
