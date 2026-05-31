<template>
  <el-dialog
    v-model="visible"
    title="LLM 配置"
    width="680px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <div v-for="(group, gi) in configStore.groups" :key="gi" class="config-group">
      <h4 class="group-title">{{ group.title }}</h4>
      <p v-if="group.subtitle" class="group-subtitle">{{ group.subtitle }}</p>
      <div class="group-fields">
        <div v-for="field in group.fields" :key="field.key" v-show="isFieldVisible(field)" class="field-row">
          <template v-if="field.type === 'select'">
            <label class="field-label">{{ field.label }}</label>
            <el-select
              v-model="localValues[field.key]"
              size="small"
              style="width:100%"
            >
              <el-option
                v-for="opt in field.options"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </template>
          <template v-else>
            <label class="field-label">{{ field.label }}</label>
            <el-input
              v-model="localValues[field.key]"
              :type="field.type === 'password' ? (showPasswords[field.key] ? 'text' : 'password') : 'text'"
              size="small"
            >
              <template v-if="field.type === 'password'" #suffix>
                <el-icon
                  class="password-toggle"
                  @click="showPasswords[field.key] = !showPasswords[field.key]"
                >
                  <View v-if="!showPasswords[field.key]" />
                  <Hide v-else />
                </el-icon>
              </template>
            </el-input>
          </template>
        </div>
      </div>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="refreshConfig" :loading="refreshing">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button type="primary" @click="saveConfig" :loading="saving">
          <el-icon><Check /></el-icon> 保存
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, reactive, watch, onBeforeUnmount } from 'vue'
import { View, Hide, Refresh, Check } from '@element-plus/icons-vue'
import { useConfigStore } from '@/stores/config'
import type { ConfigFieldDef } from '@/stores/config'

const configStore = useConfigStore()

const visible = computed({
  get: () => configStore.modalOpen,
  set: (v) => {
    if (!v) {
      configStore.closeModal()
    } else {
      configStore.openModal()
    }
  },
})

const localValues = reactive<Record<string, any>>({})
const showPasswords = reactive<Record<string, boolean>>({})
const refreshing = ref(false)
const saving = ref(false)
const autoRefreshTimer = ref<ReturnType<typeof setInterval> | null>(null)

function isFieldVisible(field: ConfigFieldDef): boolean {
  if (!field.condition) return true
  return localValues[field.condition.key] === field.condition.value
}

watch(localValues, () => {
  configStore.dirty = true
}, { deep: true })

watch(visible, async (open) => {
  if (open) {
    await configStore.refreshFromServer()
    Object.assign(localValues, configStore.values)
    configStore.dirty = false
    autoRefreshTimer.value = setInterval(async () => {
      if (!configStore.dirty) {
        await configStore.refreshFromServer()
        Object.assign(localValues, configStore.values)
        configStore.dirty = false
      }
    }, 10000)
  } else {
    if (autoRefreshTimer.value) {
      clearInterval(autoRefreshTimer.value)
      autoRefreshTimer.value = null
    }
  }
})

onBeforeUnmount(() => {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value)
  }
})

async function refreshConfig() {
  refreshing.value = true
  await configStore.refreshFromServer()
  Object.assign(localValues, configStore.values)
  configStore.dirty = false
  refreshing.value = false
}

async function saveConfig() {
  saving.value = true
  const updates: Record<string, any> = {}
  for (const key of Object.keys(localValues)) {
    if (localValues[key] !== configStore.values[key]) {
      updates[key] = localValues[key]
    }
  }
  if (Object.keys(updates).length > 0) {
    await configStore.saveUpdates(updates)
    configStore.dirty = false
  }
  saving.value = false
}
</script>

<style scoped>
.config-group {
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}
.config-group:last-child { border-bottom: none; }
.group-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 2px;
  letter-spacing: 0.5px;
}
.group-subtitle {
  font-size: 12px;
  color: #909399;
  margin: 0 0 10px;
}
.group-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.field-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field-label {
  font-size: 12px;
  color: #606266;
}
.password-toggle {
  cursor: pointer;
  color: #909399;
}
.password-toggle:hover { color: #409eff; }
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
