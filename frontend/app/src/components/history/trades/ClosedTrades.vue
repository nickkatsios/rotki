<script setup lang="ts">
import { Routes } from '@/router/routes';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { SavedFilterLocation } from '@/types/filtering';
import type { Writeable } from '@/types';
import type {
  Trade,
  TradeEntry,
  TradeRequestPayload,
} from '@/types/history/trade';
import type { Collection } from '@/types/collection';
import type { DataTableHeader } from '@/types/vuetify';
import type { Filters, Matcher } from '@/composables/filters/trades';

const props = withDefaults(
  defineProps<{
    locationOverview?: string;
    mainPage?: boolean;
  }>(),
  {
    locationOverview: '',
    mainPage: false,
  },
);

const { t } = useI18n();

const { locationOverview, mainPage } = toRefs(props);

const hideIgnoredTrades: Ref<boolean> = ref(false);
const showIgnoredAssets: Ref<boolean> = ref(false);

const router = useRouter();
const route = useRoute();

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
      text: t('closed_trades.headers.action'),
      value: 'type',
      align: overview ? 'start' : 'center',
      class: `text-no-wrap ${overview ? 'pl-0' : ''}`,
      cellClass: overview ? 'pl-0' : '',
    },
    {
      text: t('common.amount'),
      value: 'amount',
      align: 'end',
    },
    {
      text: t('closed_trades.headers.base'),
      value: 'baseAsset',
      sortable: false,
    },
    {
      text: '',
      value: 'description',
      sortable: false,
      width: '40px',
    },
    {
      text: t('closed_trades.headers.quote'),
      value: 'quoteAsset',
      sortable: false,
    },
    {
      text: t('closed_trades.headers.rate'),
      value: 'rate',
      align: 'end',
    },
    {
      text: t('common.datetime'),
      value: 'timestamp',
    },
    {
      text: t('common.actions_text'),
      value: 'actions',
      align: 'center',
      sortable: false,
      width: '1px',
    },
    { text: '', value: 'data-table-expand', sortable: false },
  ];

  if (overview) {
    headers.splice(9, 1);
    headers.splice(1, 1);
  }

  return headers;
});

const extraParams = computed(() => ({
  includeIgnoredTrades: !get(hideIgnoredTrades),
  excludeIgnoredAssets: !get(showIgnoredAssets),
}));

const assetInfoRetrievalStore = useAssetInfoRetrieval();
const { assetSymbol } = assetInfoRetrievalStore;

const { deleteExternalTrade, fetchTrades, refreshTrades } = useTrades();

const {
  options,
  selected,
  editableItem,
  itemsToDelete: tradesToDelete,
  confirmationMessage,
  expanded,
  isLoading,
  state: trades,
  filters,
  matchers,
  setPage,
  setOptions,
  setFilter,
  fetchData,
} = usePaginationFilters<
  Trade,
  TradeRequestPayload,
  TradeEntry,
  Collection<TradeEntry>,
  Filters,
  Matcher
>(locationOverview, mainPage, useTradeFilters, fetchTrades, {
  onUpdateFilters(query) {
    set(hideIgnoredTrades, query.includeIgnoredTrades === 'false');
    set(showIgnoredAssets, query.excludeIgnoredAssets === 'false');
  },
  customPageParams: computed<Partial<TradeRequestPayload>>(() => {
    const params: Writeable<Partial<TradeRequestPayload>> = {};
    const location = get(locationOverview);

    if (location)
      params.location = toSnakeCase(location);

    return params;
  }),
  extraParams,
});

useHistoryAutoRefresh(fetchData);

const { setOpenDialog, setPostSubmitFunc } = useTradesForm();

setPostSubmitFunc(fetchData);

function newExternalTrade() {
  set(editableItem, null);
  setOpenDialog(true);
}

function editTradeHandler(trade: TradeEntry) {
  set(editableItem, trade);
  setOpenDialog(true);
}

const { floatingPrecision } = storeToRefs(useGeneralSettingsStore());

function promptForDelete(trade: TradeEntry) {
  const prep = (
    trade.tradeType === 'buy'
      ? t('closed_trades.description.with')
      : t('closed_trades.description.for')
  ).toLocaleLowerCase();

  const base = get(assetSymbol(trade.baseAsset));
  const quote = get(assetSymbol(trade.quoteAsset));
  set(
    confirmationMessage,
    t('closed_trades.confirmation.message', {
      pair: `${base} ${prep} ${quote}`,
      action: trade.tradeType,
      amount: trade.amount.toFormat(get(floatingPrecision)),
    }),
  );
  set(tradesToDelete, [trade]);
  showDeleteConfirmation();
}

function massDelete() {
  const selectedVal = get(selected);
  if (selectedVal.length === 1) {
    promptForDelete(selectedVal[0]);
    return;
  }

  set(tradesToDelete, [...selectedVal]);

  set(
    confirmationMessage,
    t('closed_trades.confirmation.multiple_message', {
      length: get(tradesToDelete).length,
    }),
  );

  showDeleteConfirmation();
}

async function deleteTradeHandler() {
  const tradesToDeleteVal = get(tradesToDelete);
  if (tradesToDeleteVal.length === 0)
    return;

  const ids = tradesToDeleteVal.map(trade => trade.tradeId);
  const { success } = await deleteExternalTrade(ids);

  if (!success)
    return;

  set(tradesToDelete, []);
  set(confirmationMessage, '');

  const selectedVal = [...get(selected)];
  set(
    selected,
    selectedVal.filter(trade => !ids.includes(trade.tradeId)),
  );

  await fetchData();
}

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.TRADES,
    toData: (item: TradeEntry) => item.tradeId,
  },
  selected,
  () => fetchData(),
);

const { show } = useConfirmStore();

function showDeleteConfirmation() {
  show(
    {
      title: t('closed_trades.confirmation.title'),
      message: get(confirmationMessage),
    },
    deleteTradeHandler,
  );
}

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.TRADES);

function getItemClass(item: TradeEntry) {
  return item.ignoredInAccounting ? 'darken-row' : '';
}

const pageRoute = Routes.HISTORY_TRADES;

onMounted(async () => {
  const query = get(route).query;

  if (query.add) {
    newExternalTrade();
    await router.replace({ query: {} });
  }
  else {
    await fetchData();
    await refreshTrades();
  }
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchData();
});
</script>

<template>
  <TablePageLayout
    :hide-header="!!locationOverview"
    :child="!mainPage"
    :title="[t('navigation_menu.history'), t('closed_trades.title')]"
  >
    <template #buttons>
      <RuiTooltip>
        <template #activator>
          <RuiButton
            variant="outlined"
            color="primary"
            :loading="loading"
            @click="refreshTrades(true)"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('closed_trades.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        data-cy="closed-trades__add-trade"
        @click="newExternalTrade()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('closed_trades.dialog.add.title') }}
      </RuiButton>
    </template>

    <RuiCard>
      <template
        v-if="!!locationOverview"
        #header
      >
        <CardTitle>
          <NavigatorLink :to="{ path: pageRoute }">
            {{ t('closed_trades.title') }}
          </NavigatorLink>
        </CardTitle>
      </template>

      <HistoryTableActions v-if="!locationOverview">
        <template #filter>
          <TableStatusFilter>
            <div class="py-1 max-w-[16rem]">
              <VSwitch
                v-model="hideIgnoredTrades"
                class="mb-4 pt-0 px-4"
                hide-details
                :label="t('closed_trades.hide_ignored_trades')"
              />
              <RuiDivider />
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
            :location="SavedFilterLocation.HISTORY_TRADES"
            @update:matches="setFilter($event)"
          />
        </template>

        <RuiButton
          variant="outlined"
          color="error"
          :disabled="selected.length === 0"
          @click="massDelete()"
        >
          <RuiIcon name="delete-bin-line" />
        </RuiButton>

        <IgnoreButtons
          :disabled="selected.length === 0 || loading"
          @ignore="ignore($event)"
        />
        <div
          v-if="selected.length > 0"
          class="flex flex-row items-center gap-2"
        >
          {{ t('closed_trades.selected', { count: selected.length }) }}
          <RuiButton
            variant="text"
            @click="selected = []"
          >
            {{ t('common.actions.clear_selection') }}
          </RuiButton>
        </div>
      </HistoryTableActions>

      <CollectionHandler
        :collection="trades"
        @set-page="setPage($event)"
      >
        <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
          <DataTable
            v-model="selected"
            :expanded.sync="expanded"
            :headers="tableHeaders"
            :items="data"
            :loading="isLoading"
            :loading-text="t('trade_history.loading')"
            :options="options"
            :server-items-length="itemLength"
            data-cy="closed-trades"
            :single-select="false"
            :show-select="!locationOverview"
            :item-class="getItemClass"
            item-key="tradeId"
            show-expand
            single-expand
            multi-sort
            :must-sort="false"
            @update:options="setOptions($event)"
          >
            <template #item.ignoredInAccounting="{ item, isMobile }">
              <IgnoredInAcountingIcon
                v-if="item.ignoredInAccounting"
                :mobile="isMobile"
              />
            </template>
            <template #item.location="{ item }">
              <LocationDisplay
                data-cy="trade-location"
                :identifier="item.location"
              />
            </template>
            <template #item.type="{ item }">
              <BadgeDisplay
                :color="
                  item.tradeType.toLowerCase() === 'sell' ? 'red' : 'green'
                "
              >
                {{ item.tradeType }}
              </BadgeDisplay>
            </template>
            <template #item.baseAsset="{ item }">
              <AssetDetails
                data-cy="trade-base"
                opens-details
                hide-name
                :asset="item.baseAsset"
              />
            </template>
            <template #item.quoteAsset="{ item }">
              <AssetDetails
                hide-name
                opens-details
                :asset="item.quoteAsset"
                data-cy="trade-quote"
              />
            </template>
            <template #item.description="{ item }">
              {{
                item.tradeType === 'buy'
                  ? t('closed_trades.description.with')
                  : t('closed_trades.description.for')
              }}
            </template>
            <template #item.rate="{ item }">
              <AmountDisplay
                class="closed-trades__trade__rate"
                :value="item.rate"
              />
            </template>
            <template #item.amount="{ item }">
              <AmountDisplay
                class="closed-trades__trade__amount"
                :value="item.amount"
              />
            </template>
            <template #item.timestamp="{ item }">
              <DateDisplay :timestamp="item.timestamp" />
            </template>
            <template #item.actions="{ item }">
              <RowActions
                v-if="item.location === 'external'"
                :disabled="loading"
                :edit-tooltip="t('closed_trades.edit_tooltip')"
                :delete-tooltip="t('closed_trades.delete_tooltip')"
                @edit-click="editTradeHandler(item)"
                @delete-click="promptForDelete(item)"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <TradeDetails
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
                :label="t('closed_trades.label')"
              />
            </template>
          </DataTable>
        </template>
      </CollectionHandler>
      <ExternalTradeFormDialog
        :loading="loading"
        :editable-item="editableItem"
      />
    </RuiCard>
  </TablePageLayout>
</template>
