<script setup lang="ts">
import { Routes } from '@/router/routes';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { SavedFilterLocation } from '@/types/filtering';
import type {
  AssetMovement,
  AssetMovementEntry,
  AssetMovementRequestPayload,
} from '@/types/history/asset-movements';
import type { Collection } from '@/types/collection';
import type { DataTableHeader } from '@/types/vuetify';
import type { Filters, Matcher } from '@/composables/filters/asset-movement';
import type { Writeable } from '@/types';

const props = withDefaults(
  defineProps<{
    locationOverview?: string;
  }>(),
  {
    locationOverview: '',
  },
);

const { t } = useI18n();

const { locationOverview } = toRefs(props);

const showIgnoredAssets: Ref<boolean> = ref(false);

const mainPage = computed(() => get(locationOverview) === '');

const tableHeaders = computed<DataTableHeader[]>(() => {
  const overview = get(locationOverview);
  const headers: DataTableHeader[] = [
    {
      text: '',
      value: 'ignoredInAccounting',
      sortable: false,
      class: !overview ? 'pa-0' : 'pr-0',
      cellClass: !overview ? 'pa-0' : 'pr-0',
    },
    {
      text: t('common.location'),
      value: 'location',
      width: '120px',
      align: 'center',
    },
    {
      text: t('deposits_withdrawals.headers.action'),
      value: 'category',
      align: overview ? 'start' : 'center',
      class: `text-no-wrap ${overview ? 'pl-0' : ''}`,
      cellClass: overview ? 'pl-0' : '',
    },
    {
      text: t('common.asset'),
      value: 'asset',
      sortable: false,
    },
    {
      text: t('common.amount'),
      value: 'amount',
      align: 'end',
    },
    {
      text: t('deposits_withdrawals.headers.fee'),
      value: 'fee',
      align: 'end',
    },
    {
      text: t('common.datetime'),
      value: 'timestamp',
    },
    { text: '', value: 'data-table-expand', sortable: false },
  ];

  if (overview)
    headers.splice(1, 1);

  return headers;
});

const extraParams = computed(() => ({
  excludeIgnoredAssets: !get(showIgnoredAssets),
}));

const { fetchAssetMovements, refreshAssetMovements } = useAssetMovements();

const {
  options,
  selected,
  expanded,
  isLoading,
  state: assetMovements,
  filters,
  matchers,
  setPage,
  setOptions,
  setFilter,
  fetchData,
} = usePaginationFilters<
  AssetMovement,
  AssetMovementRequestPayload,
  AssetMovementEntry,
  Collection<AssetMovementEntry>,
  Filters,
  Matcher
>(locationOverview, mainPage, useAssetMovementFilters, fetchAssetMovements, {
  onUpdateFilters(query) {
    set(showIgnoredAssets, query.excludeIgnoredAssets === 'false');
  },
  customPageParams: computed<Partial<AssetMovementRequestPayload>>(() => {
    const params: Writeable<Partial<AssetMovementRequestPayload>> = {};
    const location = get(locationOverview);

    if (location)
      params.location = toSnakeCase(location);

    return params;
  }),
  extraParams,
});

useHistoryAutoRefresh(fetchData);

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.MOVEMENTS,
    toData: (item: AssetMovementEntry) => item.identifier,
  },
  selected,
  () => fetchData(),
);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.ASSET_MOVEMENT);

function getItemClass(item: AssetMovementEntry) {
  return item.ignoredInAccounting ? 'darken-row' : '';
}

const pageRoute = Routes.HISTORY_DEPOSITS_WITHDRAWALS;

onMounted(async () => {
  await fetchData();
  await refreshAssetMovements();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <TablePageLayout
    :hide-header="!mainPage"
    :child="!mainPage"
    :title="[t('navigation_menu.history'), t('deposits_withdrawals.title')]"
  >
    <template #buttons>
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="refreshAssetMovements(true)"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('deposits_withdrawals.refresh_tooltip') }}
      </RuiTooltip>
    </template>

    <RuiCard>
      <template
        v-if="!mainPage"
        #header
      >
        <CardTitle>
          <NavigatorLink :to="{ path: pageRoute }">
            {{ t('deposits_withdrawals.title') }}
          </NavigatorLink>
        </CardTitle>
      </template>

      <HistoryTableActions v-if="mainPage">
        <template #filter>
          <TableStatusFilter>
            <div class="py-1 max-w-[16rem]">
              <VSwitch
                v-model="showIgnoredAssets"
                class="mb-4 pt-0 px-4"
                hide-details
                :label="t('transactions.filter.show_ignored_assets')"
              />
            </div>
          </TableStatusFilter>
          <TableFilter
            class="min-w-full sm:min-w-[20rem]"
            :matches="filters"
            :matchers="matchers"
            :location="SavedFilterLocation.HISTORY_DEPOSITS_WITHDRAWALS"
            @update:matches="setFilter($event)"
          />
        </template>
        <IgnoreButtons
          :disabled="selected.length === 0 || loading"
          @ignore="ignore($event)"
        />
        <div
          v-if="selected.length > 0"
          class="flex flex-row items-center gap-2"
        >
          {{ t('deposits_withdrawals.selected', { count: selected.length }) }}
          <RuiButton
            variant="text"
            size="sm"
            @click="selected = []"
          >
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </HistoryTableActions>

      <CollectionHandler
        :collection="assetMovements"
        @set-page="setPage($event)"
      >
        <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
          <DataTable
            v-model="selected"
            :expanded.sync="expanded"
            :headers="tableHeaders"
            :items="data"
            :loading="isLoading"
            :loading-text="t('deposits_withdrawals.loading')"
            :options="options"
            :server-items-length="itemLength"
            class="asset-movements"
            :single-select="false"
            :show-select="mainPage"
            item-key="identifier"
            show-expand
            single-expand
            multi-sort
            :must-sort="false"
            :item-class="getItemClass"
            @update:options="setOptions($event)"
          >
            <template #item.ignoredInAccounting="{ item, isMobile }">
              <IgnoredInAcountingIcon
                v-if="item.ignoredInAccounting"
                :mobile="isMobile"
              />
            </template>
            <template #item.location="{ item }">
              <LocationDisplay :identifier="item.location" />
            </template>
            <template #item.category="{ item }">
              <BadgeDisplay
                :color="
                  item.category.toLowerCase() === 'withdrawal'
                    ? 'grey'
                    : 'green'
                "
              >
                {{ item.category }}
              </BadgeDisplay>
            </template>
            <template #item.asset="{ item }">
              <AssetDetails
                opens-details
                :asset="item.asset"
              />
            </template>
            <template #item.amount="{ item }">
              <AmountDisplay
                class="deposits-withdrawals__movement__amount"
                :value="item.amount"
              />
            </template>
            <template #item.fee="{ item }">
              <AmountDisplay
                class="deposits-withdrawals__trade__fee"
                :asset="item.feeAsset"
                :value="item.fee"
              />
            </template>
            <template #item.timestamp="{ item }">
              <DateDisplay :timestamp="item.timestamp" />
            </template>
            <template #expanded-item="{ headers, item }">
              <DepositWithdrawalDetails
                :span="headers.length"
                :item="item"
              />
            </template>
            <template
              v-if="showUpgradeRow"
              #body.prepend="{ headers }"
            >
              <UpgradeRow
                :limit="limit"
                :total="total"
                :colspan="headers.length"
                :label="t('deposits_withdrawals.label')"
              />
            </template>
          </DataTable>
        </template>
      </CollectionHandler>
    </RuiCard>
  </TablePageLayout>
</template>
