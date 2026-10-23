<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  Delete,
  Edit,
  Plus,
  Refresh,
  Search,
  User,
} from '@element-plus/icons-vue'
import {
  ElMessage,
  ElMessageBox,
  type FormInstance,
  type FormRules,
} from 'element-plus'
import {
  createDriver,
  deleteDriver,
  getDrivers,
  updateDriver,
  type Driver,
  type DriverPayload,
} from '@/services/agentData'

const PAGE_SIZE = 10
const activeTab = ref('drivers')
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number>()
const keyword = ref('')
const page = ref(1)
const total = ref(0)
const drivers = ref<Driver[]>([])
const formRef = ref<FormInstance>()
const form = reactive<DriverPayload>({
  name: '',
  phone: '',
  vin: '',
  vehicle_model: '',
  address: '',
  registration_city: '',
  registration_date: '',
})
const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入电话', trigger: 'blur' }],
  vin: [{ required: true, message: '请输入 VIN 码', trigger: 'blur' }],
  vehicle_model: [{ required: true, message: '请输入车型', trigger: 'blur' }],
  registration_city: [
    { required: true, message: '请输入注册城市', trigger: 'blur' },
  ],
  registration_date: [
    { required: true, message: '请选择注册日期', trigger: 'change' },
  ],
}

async function load(showMessage = false) {
  loading.value = true
  try {
    const result = await getDrivers(page.value, keyword.value.trim())
    drivers.value = result.items
    total.value = result.total
    if (showMessage) ElMessage.success('车主列表已刷新')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '车主列表加载失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  editingId.value = undefined
  Object.assign(form, {
    name: '',
    phone: '',
    vin: '',
    vehicle_model: '',
    address: '',
    registration_city: '',
    registration_date: '',
  })
  formRef.value?.clearValidate()
}

function openCreate() {
  resetForm()
  dialogVisible.value = true
}

function openEdit(driver: Driver) {
  editingId.value = driver.id
  Object.assign(form, {
    name: driver.name,
    phone: driver.phone,
    vin: driver.vin,
    vehicle_model: driver.vehicle_model,
    address: driver.address,
    registration_city: driver.registration_city,
    registration_date: driver.registration_date,
  })
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

async function save() {
  if (!formRef.value || !(await formRef.value.validate().catch(() => false))) {
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form,
      vin: form.vin.trim().toUpperCase(),
    }
    if (editingId.value !== undefined) {
      await updateDriver(editingId.value, payload)
      ElMessage.success('车主信息已更新')
    } else {
      await createDriver(payload)
      page.value = 1
      ElMessage.success('车主创建成功')
    }
    dialogVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '车主信息保存失败')
  } finally {
    saving.value = false
  }
}

async function removeDriver(driver: Driver) {
  try {
    await ElMessageBox.confirm(
      `确定删除车主“${driver.name}”吗？删除后不可恢复。`,
      '删除车主',
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
    await deleteDriver(driver.id)
    if (drivers.value.length === 1 && page.value > 1) page.value -= 1
    ElMessage.success('车主已删除')
    await load()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '车主删除失败')
  }
}

function searchDrivers() {
  page.value = 1
  load()
}

function clearSearch() {
  if (keyword.value) return
  page.value = 1
  load()
}

function formatDate(value: string) {
  if (!value) return '--'
  return new Intl.DateTimeFormat('zh-CN').format(
    new Date(`${value.slice(0, 10)}T00:00:00`),
  )
}

onMounted(load)
</script>

<template>
  <section class="surface base-data-surface">
    <el-tabs v-model="activeTab" class="base-data-tabs">
      <el-tab-pane label="车主管理" name="drivers">
        <div class="driver-toolbar">
          <div class="driver-search">
            <el-input
              v-model="keyword"
              clearable
              :prefix-icon="Search"
              placeholder="搜索姓名、电话、VIN、车型或城市"
              @keyup.enter="searchDrivers"
              @clear="clearSearch"
            />
            <el-button :icon="Search" @click="searchDrivers">查询</el-button>
          </div>
          <div class="driver-actions">
            <el-button :icon="Refresh" :loading="loading" @click="load(true)">
              刷新
            </el-button>
            <el-button type="primary" :icon="Plus" @click="openCreate">
              新增车主
            </el-button>
          </div>
        </div>

        <div class="table-meta">
          <span>TSP DRIVER DIRECTORY · 每页 {{ PAGE_SIZE }} 条</span>
          <strong>{{ total }} DRIVERS</strong>
        </div>

        <el-table
          v-loading="loading"
          :data="drivers"
          row-key="id"
          class="tech-table driver-table"
        >
          <el-table-column prop="id" label="序号" width="80" align="center" />
          <el-table-column prop="name" label="姓名" min-width="110" />
          <el-table-column prop="phone" label="电话" min-width="145" />
          <el-table-column prop="vin" label="VIN 码" min-width="190" show-overflow-tooltip />
          <el-table-column prop="vehicle_model" label="车型" min-width="145" show-overflow-tooltip />
          <el-table-column prop="address" label="联系地址" min-width="210" show-overflow-tooltip>
            <template #default="{ row }">{{ row.address || '--' }}</template>
          </el-table-column>
          <el-table-column prop="registration_city" label="注册城市" min-width="110" />
          <el-table-column label="注册日期" min-width="125">
            <template #default="{ row }">{{ formatDate(row.registration_date) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="110" align="center" fixed="right">
            <template #default="{ row }">
              <el-tooltip content="编辑" placement="top">
                <el-button text circle :icon="Edit" @click="openEdit(row)" />
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button
                  text
                  circle
                  type="danger"
                  :icon="Delete"
                  @click="removeDriver(row)"
                />
              </el-tooltip>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无车主数据">
              <el-button type="primary" :icon="Plus" @click="openCreate">
                新增车主
              </el-button>
            </el-empty>
          </template>
        </el-table>

        <div class="driver-pagination">
          <el-pagination
            v-model:current-page="page"
            :page-size="PAGE_SIZE"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="load()"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="数据字典" name="dictionary">
        <div class="dictionary-empty">
          <el-empty description="暂无数据字典">
            <template #image>
              <el-icon :size="52"><User /></el-icon>
            </template>
          </el-empty>
        </div>
      </el-tab-pane>
    </el-tabs>
  </section>

  <el-dialog
    v-model="dialogVisible"
    :title="editingId !== undefined ? '编辑车主' : '新增车主'"
    width="620px"
    class="driver-dialog"
    @closed="resetForm"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <div class="driver-form-grid">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" maxlength="100" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="form.phone" maxlength="32" placeholder="请输入电话" />
        </el-form-item>
      </div>
      <el-form-item label="VIN 码" prop="vin">
        <el-input
          v-model="form.vin"
          maxlength="64"
          placeholder="请输入 VIN 码"
          @blur="form.vin = form.vin.trim().toUpperCase()"
        />
      </el-form-item>
      <div class="driver-form-grid">
        <el-form-item label="车型" prop="vehicle_model">
          <el-input
            v-model="form.vehicle_model"
            maxlength="100"
            placeholder="请输入车型"
          />
        </el-form-item>
        <el-form-item label="注册城市" prop="registration_city">
          <el-input
            v-model="form.registration_city"
            maxlength="100"
            placeholder="请输入注册城市"
          />
        </el-form-item>
      </div>
      <el-form-item label="联系地址" prop="address">
        <el-input
          v-model="form.address"
          maxlength="255"
          placeholder="请输入联系地址"
        />
      </el-form-item>
      <el-form-item label="注册日期" prop="registration_date">
        <el-date-picker
          v-model="form.registration_date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="请选择注册日期"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">
        {{ editingId !== undefined ? '保存修改' : '创建车主' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.base-data-surface {
  min-height: 560px;
  padding: 0 24px 24px;
}

.base-data-tabs :deep(.el-tabs__header) {
  margin: 0 0 22px;
}

.base-data-tabs :deep(.el-tabs__item) {
  height: 54px;
  font-size: 14px;
}

.driver-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.driver-search,
.driver-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.driver-search .el-input {
  width: min(380px, 42vw);
}

.driver-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 20px;
}

.dictionary-empty {
  min-height: 390px;
  display: grid;
  place-items: center;
}

.dictionary-empty :deep(.el-empty__image) {
  color: var(--muted);
}

.driver-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.driver-form-grid .el-form-item {
  min-width: 0;
}

.driver-dialog :deep(.el-date-editor) {
  width: 100%;
}

@media (max-width: 1100px) {
  .driver-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .driver-search,
  .driver-actions {
    width: 100%;
  }

  .driver-search .el-input {
    width: 100%;
  }

  .driver-actions {
    justify-content: flex-end;
  }
}

@media (max-width: 760px) {
  .base-data-surface {
    padding: 0 14px 18px;
  }

  .driver-form-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
}
</style>
