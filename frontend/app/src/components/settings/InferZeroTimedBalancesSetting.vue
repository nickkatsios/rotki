<script setup lang="ts">
const emit = defineEmits<{
  (e: 'updated'): void;
}>();

const { t } = useI18n();

const updated = () => emit('updated');

const inferZeroTimedBalances = ref<boolean>(false);
const { inferZeroTimedBalances: enabled } = storeToRefs(
  useGeneralSettingsStore(),
);

function resetState() {
  set(inferZeroTimedBalances, get(enabled));
}

function finished() {
  resetState();
  updated();
}

onMounted(() => {
  resetState();
});
</script>

<template>
  <div>
    <CardTitle>
      {{ t('statistics_graph_settings.infer_zero_timed_balances.title') }}
    </CardTitle>
    <SettingsOption
      #default="{ error, success, update }"
      setting="inferZeroTimedBalances"
      @finished="finished()"
    >
      <VSwitch
        v-model="inferZeroTimedBalances"
        :label="t('statistics_graph_settings.infer_zero_timed_balances.label')"
        persistent-hint
        :success-messages="success"
        :error-messages="error"
        @change="update($event)"
      />
    </SettingsOption>
  </div>
</template>
