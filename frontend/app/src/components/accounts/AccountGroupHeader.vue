<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import type { Balance, BigNumber } from '@rotki/common';
import type { ComputedRef } from 'vue';
import type { XpubAccountWithBalance } from '@/types/blockchain/accounts';

const props = withDefaults(
  defineProps<{
    group: string;
    items: XpubAccountWithBalance[];
    expanded: boolean;
    loading?: boolean;
  }>(),
  { loading: false },
);

const emit = defineEmits(['delete-clicked', 'expand-clicked', 'edit-clicked']);

const { t } = useI18n();

const { items } = toRefs(props);
const { name: breakpoint, xs } = useDisplay();
const { shouldShowAmount } = storeToRefs(useSessionSettingsStore());

const xpub: ComputedRef<XpubAccountWithBalance> = computed(() => {
  const account = get(items).find(item => !item.address);
  assert(account);
  return account;
});

const label = computed<string>(() => get(xpub).label);

const xpubTags = computed<string[]>(() => get(xpub).tags);

const displayXpub = computed<string>(() =>
  truncateAddress(get(xpub).xpub, truncationPoints[get(breakpoint)] ?? 4),
);

const sum = computed<BigNumber>(() =>
  bigNumberSum(get(items).map(({ balance: { amount } }) => amount)),
);

const usdSum = computed<BigNumber>(() => balanceUsdValueSum(get(items)));

const balance = computed<Balance>(() => ({
  amount: get(sum),
  usdValue: get(usdSum),
}));

function deleteClicked(_payload: XpubAccountWithBalance) {
  return emit('delete-clicked', _payload);
}

function expandClicked(_payload: XpubAccountWithBalance) {
  return emit('expand-clicked', _payload);
}

function editClicked(_payload: XpubAccountWithBalance) {
  return emit('edit-clicked', _payload);
}
</script>

<template>
  <td
    v-if="!group"
    class="font-medium text-subtitle-2 px-4 py-2"
    colspan="5"
  >
    {{ t('account_group_header.standalone') }}
  </td>
  <Fragment v-else>
    <td
      colspan="2"
      :class="{
        '!p-2': !xs,
      }"
    >
      <div class="pl-9">
        <span class="text-subtitle-2">{{ label }}</span>
      </div>
      <div class="flex items-center gap-1 -my-2">
        <RuiButton
          :disabled="items.length === 0"
          variant="text"
          size="sm"
          icon
          @click="expandClicked({ ...xpub, balance })"
        >
          <RuiIcon
            v-if="expanded"
            name="arrow-up-s-line"
          />
          <RuiIcon
            v-else
            name="arrow-down-s-line"
          />
        </RuiButton>
        <span class="font-medium">
          {{ t('account_group_header.xpub') }}
        </span>
        <span :class="{ blur: !shouldShowAmount }">
          <RuiTooltip
            :popper="{ placement: 'top' }"
            :open-delay="400"
          >
            <template #activator>
              {{ displayXpub }}
            </template>
            {{ xpub.xpub }}
          </RuiTooltip>
        </span>
        <CopyButton
          :value="xpub.xpub"
          :tooltip="t('account_group_header.copy_tooltip')"
        />
        <span
          v-if="xpub.derivationPath"
          :class="{ blur: !shouldShowAmount }"
        >
          <span class="font-medium">
            {{ t('account_group_header.derivation_path') }}:
          </span>
          {{ xpub.derivationPath }}
        </span>
      </div>
      <TagDisplay
        wrapper-class="ml-9"
        :tags="xpubTags"
      />
    </td>
    <td class="text-end px-4">
      <AmountDisplay
        :value="sum"
        :loading="loading"
        :asset="xs ? 'BTC' : undefined"
        :asset-padding="0.1"
      />
    </td>
    <td class="text-end px-4">
      <AmountDisplay
        fiat-currency="USD"
        show-currency="symbol"
        :value="usdSum"
        :loading="loading"
        :asset-padding="0.1"
      />
    </td>
    <td class="text-end">
      <RowActions
        :edit-tooltip="t('account_group_header.edit_tooltip')"
        :delete-tooltip="t('account_group_header.delete_tooltip')"
        @edit-click="editClicked(xpub)"
        @delete-click="deleteClicked(xpub)"
      />
    </td>
  </Fragment>
</template>
