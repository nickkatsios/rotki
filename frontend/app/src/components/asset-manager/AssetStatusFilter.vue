<script setup lang="ts">
import {
  IgnoredAssetHandlingType,
  type IgnoredAssetsHandlingType,
} from '@/types/asset';

interface Model {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}

const props = defineProps<{
  value: Model;
  count: number;
}>();

const emit = defineEmits<{
  (e: 'input', value: Model): void;
}>();

const { t } = useI18n();
const showMenu = ref(false);

function isHandlingType(t: any): t is IgnoredAssetsHandlingType {
  return Object.values(IgnoredAssetHandlingType).includes(t);
}

const handlingSelection = computed({
  get() {
    return props.value.ignoredAssetsHandling;
  },
  set(value: string) {
    if (isHandlingType(value)) {
      emit('input', {
        ...props.value,
        ignoredAssetsHandling: value,
      });
    }
  },
});

const onlyShowOwned = computed({
  get() {
    return props.value.onlyShowOwned;
  },
  set(value: boolean) {
    emit('input', {
      ...props.value,
      onlyShowOwned: value,
    });
  },
});

const onlyShowWhitelisted = computed({
  get() {
    return props.value.onlyShowWhitelisted;
  },
  set(value: boolean) {
    emit('input', {
      ...props.value,
      onlyShowWhitelisted: value,
    });
  },
});
</script>

<template>
  <TableStatusFilter v-model="showMenu">
    <div
      class="p-1 pt-2"
      data-cy="asset-filter-menu"
    >
      <RuiCheckbox
        v-model="onlyShowOwned"
        color="primary"
        data-cy="asset-filter-only-show-owned"
        class="mt-0 px-3"
        :label="t('asset_table.only_show_owned')"
        hide-details
      />
      <RuiCheckbox
        v-model="onlyShowWhitelisted"
        color="primary"
        data-cy="asset-filter-only-show-whitelisted"
        class="mt-0 px-3"
        :label="t('asset_table.only_show_whitelisted')"
        hide-details
      />
      <div class="font-bold uppercase p-2 text-sm">
        {{ t('asset_table.filter_by_ignored_status') }}
      </div>
      <div class="pb-2 px-3">
        <RuiRadioGroup
          v-if="showMenu"
          v-model="handlingSelection"
          color="primary"
          class="mt-0"
          hide-details
          data-cy="asset-filter-ignored"
        >
          <RuiRadio
            internal-value="none"
            data-cy="asset-filter-none"
            :label="t('asset_table.show_all')"
          />
          <RuiRadio
            internal-value="exclude"
            data-cy="asset-filter-exclude"
            :label="t('asset_table.only_show_unignored')"
          />
          <RuiRadio
            internal-value="show_only"
            data-cy="asset-filter-show_only"
            :label="
              t(
                'asset_table.only_show_ignored',
                {
                  length: count,
                },
                1,
              )
            "
          />
        </RuiRadioGroup>
      </div>
    </div>
  </TableStatusFilter>
</template>
