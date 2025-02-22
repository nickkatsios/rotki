<script setup lang="ts">
import type { IgnoredAssetsHandlingType } from '@/types/asset';

const props = defineProps<{
  selected: string[];
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}>();

const emit = defineEmits<{
  (e: 'update:selected', selected: string[]): void;
  (
    e: 'update:ignored-assets-handling',
    ignoredAssetsHandling: IgnoredAssetsHandlingType
  ): void;
  (e: 'mass-ignore', ignored: boolean): void;
}>();

const internalValue = computed({
  get() {
    return props.ignoredAssetsHandling;
  },
  set(value: IgnoredAssetsHandlingType) {
    emit('update:ignored-assets-handling', value);
  },
});

function massIgnore(ignored: boolean) {
  emit('mass-ignore', ignored);
}

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-row items-center justify-between flex-wrap gap-2">
    <div class="flex flex-row gap-2">
      <IgnoreButtons
        :disabled="selected.length === 0"
        @ignore="massIgnore($event)"
      />
      <div
        v-if="selected.length > 0"
        class="flex flex-row items-center gap-2"
      >
        <span class="text-body-2 text-rui-text-secondary">
          {{
            t('asset_table.selected', { count: selected.length })
          }}
        </span>
        <RuiButton
          size="sm"
          variant="outlined"
          @click="emit('update:selected', [])"
        >
          {{ t('common.actions.clear_selection') }}
        </RuiButton>
      </div>
    </div>
    <div>
      <VMenu
        offset-y
        left
        :close-on-content-click="false"
      >
        <template #activator="{ on }">
          <RuiButton
            variant="outlined"
            v-on="on"
          >
            <template #append>
              <RuiIcon name="arrow-down-s-line" />
            </template>
            {{ t('common.actions.filter') }}
          </RuiButton>
        </template>
        <div class="p-2">
          <div class="font-bold uppercase p-2 text-sm">
            {{ t('asset_table.filter_by_ignored_status') }}
          </div>
          <div class="pb-2 px-3">
            <RuiRadioGroup
              v-model="internalValue"
              class="mt-0"
              data-cy="asset-filter-ignored"
              hide-details
              color="primary"
            >
              <RuiRadio
                internal-value="none"
                :label="t('asset_table.show_all')"
              />
              <RuiRadio
                internal-value="exclude"
                :label="t('asset_table.only_show_unignored')"
              />
              <RuiRadio
                internal-value="show_only"
                :label="t('asset_table.only_show_ignored', 2)"
              />
            </RuiRadioGroup>
          </div>
        </div>
      </VMenu>
    </div>
  </div>
</template>
