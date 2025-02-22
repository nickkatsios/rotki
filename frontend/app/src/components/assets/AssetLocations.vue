<script setup lang="ts">
import { Blockchain } from '@rotki/common/lib/blockchain';
import { CURRENCY_USD } from '@/types/currencies';
import { isBlockchain } from '@/types/blockchain/chains';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type { BigNumber } from '@rotki/common';
import type { GeneralAccount } from '@rotki/common/lib/account';
import type { ComputedRef } from 'vue';
import type { AssetBreakdown } from '@/types/blockchain/accounts';

type AssetLocations = AssetLocation[];

interface AssetLocation extends AssetBreakdown {
  readonly account?: GeneralAccount;
  readonly label: string;
}

const props = defineProps<{ identifier: string }>();

const { t } = useI18n();

const { identifier } = toRefs(props);

const sort = ref<DataTableSortData>({
  column: 'amount',
  direction: 'desc',
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getAccountByAddress } = useAccountBalances();
const { getEth2Account } = useEthAccountsStore();
const { detailsLoading } = storeToRefs(useStatusStore());
const { assetPriceInfo } = useAggregatedBalances();
const { assetBreakdown } = useBalancesBreakdown();

const onlyTags = ref<string[]>([]);

const totalUsdValue = computed<BigNumber>(
  () => get(assetPriceInfo(identifier)).usdValue,
);

function getAccount(item: AssetBreakdown): ComputedRef<GeneralAccount | undefined> {
  return computed(() =>
    item.location === Blockchain.ETH2
      ? get(getEth2Account(item.address))
      : get(getAccountByAddress(item.address, item.location)),
  );
}

const assetLocations = computed<AssetLocations>(() => {
  const breakdowns = get(assetBreakdown(get(identifier)));
  return breakdowns.map((item: AssetBreakdown) => {
    const account = get(getAccount(item));
    return {
      ...item,
      account,
      label: account?.label ?? '',
    };
  });
});

const { addressNameSelector } = useAddressesNamesStore();

const visibleAssetLocations = computed<AssetLocations>(() => {
  const locations = get(assetLocations).map(item => ({
    ...item,
    label:
      (isBlockchain(item.location)
        ? get(addressNameSelector(item.address, item.location))
        : null)
        || item.label
        || item.address,
  }));

  if (get(onlyTags).length === 0)
    return locations;

  return locations.filter((assetLocation) => {
    const tags = assetLocation.tags ?? [];
    return get(onlyTags).every(tag => tags.includes(tag));
  });
});

function getPercentage(usdValue: BigNumber): string {
  const percentage = get(totalUsdValue).isZero()
    ? 0
    : usdValue.div(get(totalUsdValue)).multipliedBy(100);

  return percentage.toFixed(2);
}

const headers = computed<DataTableColumn[]>(() => {
  const visibleItemsLength = get(visibleAssetLocations).length;
  const eth2Length = get(visibleAssetLocations).filter(
    account => account?.location === Blockchain.ETH2,
  ).length;

  const labelAccount = t('common.account');
  const labelValidator = t('asset_locations.header.validator');

  let label: string;
  if (eth2Length === 0)
    label = labelAccount;
  else if (eth2Length === visibleItemsLength)
    label = labelValidator;
  else
    label = `${labelAccount} / ${labelValidator}`;

  return [
    {
      label: t('common.location'),
      key: 'location',
      align: 'center',
      cellClass: 'w-36',
      sortable: true,
    },
    {
      label,
      key: 'label',
      sortable: true,
    },
    {
      label: t('common.amount'),
      key: 'amount',
      align: 'end',
      sortable: true,
    },
    {
      label: t('asset_locations.header.value', {
        symbol: get(currencySymbol) ?? CURRENCY_USD,
      }),
      key: 'usdValue',
      align: 'end',
      sortable: true,
    },
    {
      label: t('asset_locations.header.percentage'),
      key: 'percentage',
      sortable: false,
      align: 'end',
    },
  ];
});
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('asset_locations.title') }}
    </template>
    <div class="flex justify-end">
      <div class="w-full md:w-[30rem]">
        <TagFilter v-model="onlyTags" />
      </div>
    </div>
    <RuiDataTable
      :cols="headers"
      :rows="visibleAssetLocations"
      outlined
      row-attr="location"
      :sort.sync="sort"
      :loading="detailsLoading"
    >
      <template #item.location="{ row }">
        <LocationDisplay
          :identifier="row.location"
          :detail-path="row.detailPath"
          class="py-2"
        />
      </template>
      <template #item.label="{ row }">
        <div class="py-4">
          <LabeledAddressDisplay
            v-if="row.account"
            :account="row.account"
          />
          <TagDisplay
            :tags="row.tags"
            small
          />
        </div>
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.balance.amount" />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          show-currency="symbol"
          :amount="row.balance.amount"
          :price-asset="identifier"
          fiat-currency="USD"
          :value="row.balance.usdValue"
        />
      </template>
      <template #item.percentage="{ row }">
        <PercentageDisplay :value="getPercentage(row.balance.usdValue)" />
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
