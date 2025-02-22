<script setup lang="ts">
import { CURRENCY_USD } from '@/types/currencies';
import { isNft } from '@/utils/nft';
import { toSentenceCase } from '@/utils/text';
import { BalanceType } from '@/types/balances';
import type { BigNumber } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { DataTableHeader } from '@/types/vuetify';
import type {
  BalanceSnapshot,
  BalanceSnapshotPayload,
  Snapshot,
} from '@/types/snapshots';

const props = defineProps<{
  value: Snapshot;
  timestamp: number;
}>();

const emit = defineEmits<{
  (e: 'update:step', step: number): void;
  (e: 'input', value: Snapshot): void;
}>();

const { t } = useI18n();

type IndexedBalanceSnapshot = BalanceSnapshot & { index: number };

const css = useCssModule();

const { value, timestamp } = toRefs(props);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const showDeleteConfirmation = ref<boolean>(false);
const indexToEdit = ref<number | null>(null);
const indexToDelete = ref<number | null>(null);
const locationToDelete = ref<string>('');
const form = ref<(BalanceSnapshotPayload & { location: string }) | null>(null);

const { exchangeRate } = useBalancePricesStore();
const fiatExchangeRate = computed<BigNumber>(
  () => get(exchangeRate(get(currencySymbol))) ?? One,
);

const data: ComputedRef<IndexedBalanceSnapshot[]> = computed(() =>
  get(value).balancesSnapshot.map((item, index) => ({
    ...item,
    index,
  })),
);

const assetSearch: Ref<string> = ref('');
const filteredData: ComputedRef<IndexedBalanceSnapshot[]> = computed(() => {
  const allData = get(data);
  const search = get(assetSearch);
  if (!search)
    return allData;

  return allData.filter(({ assetIdentifier }) => assetIdentifier === search);
});

const total = computed<BigNumber>(() => {
  const totalEntry = get(value).locationDataSnapshot.find(
    item => item.location === 'total',
  );

  if (!totalEntry)
    return Zero;

  return totalEntry.usdValue;
});

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.category'),
    value: 'category',
    cellClass: 'py-2',
    width: 150,
  },
  {
    text: t('common.asset'),
    value: 'assetIdentifier',
  },
  {
    text: t('common.amount'),
    value: 'amount',
    align: 'end',
    sort: (a: BigNumber, b: BigNumber) => sortDesc(a, b),
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }).toString(),
    value: 'usdValue',
    align: 'end',
    sort: (a: BigNumber, b: BigNumber) => sortDesc(a, b),
  },
  {
    text: '',
    value: 'action',
    cellClass: 'py-2',
    width: 100,
    sortable: false,
  },
]);

function input(value: Snapshot) {
  emit('input', value);
}

function updateStep(step: number) {
  emit('update:step', step);
}

const conflictedBalanceSnapshot: Ref<BalanceSnapshot | null> = ref(null);

function checkAssetExist(asset: string) {
  const assetFound = get(value).balancesSnapshot.find(
    item => item.assetIdentifier === asset,
  );
  set(conflictedBalanceSnapshot, assetFound || null);
}

function closeConvertToEditDialog() {
  set(conflictedBalanceSnapshot, null);
}

function cancelConvertToEdit() {
  set(form, {
    ...get(form),
    assetIdentifier: '',
  });

  closeConvertToEditDialog();
}

function convertToEdit() {
  assert(conflictedBalanceSnapshot);
  const item = get(data).find(
    ({ assetIdentifier }) =>
      assetIdentifier === get(conflictedBalanceSnapshot)?.assetIdentifier,
  );

  if (item)
    editClick(item);

  closeConvertToEditDialog();
}

function editClick(item: IndexedBalanceSnapshot) {
  set(indexToEdit, item.index);

  const convertedFiatValue
    = get(currencySymbol) === CURRENCY_USD
      ? item.usdValue.toFixed()
      : item.usdValue.multipliedBy(get(fiatExchangeRate)).toFixed();

  set(form, {
    ...item,
    amount: item.amount.toFixed(),
    usdValue: convertedFiatValue,
    location: '',
  });

  setOpenDialog(true);
}

const existingLocations = computed<string[]>(() =>
  get(value)
    .locationDataSnapshot.filter(item => item.location !== 'total')
    .map(item => item.location),
);

function deleteClick(item: IndexedBalanceSnapshot) {
  set(indexToDelete, item.index);
  set(showDeleteConfirmation, true);
  set(locationToDelete, '');
}

function add() {
  set(indexToEdit, null);
  set(form, {
    timestamp: get(timestamp),
    category: BalanceType.ASSET,
    assetIdentifier: '',
    amount: '',
    usdValue: '',
    location: '',
  });
  setOpenDialog(true);
}

const previewLocationBalance = computed<Record<string, BigNumber> | null>(
  () => {
    const formVal = get(form);

    if (!formVal || !formVal.amount || !formVal.usdValue || !formVal.location)
      return null;

    const index = get(indexToEdit);
    const val = get(value);

    const locationData = val.locationDataSnapshot.find(
      item => item.location === formVal.location,
    );

    const usdValueInBigNumber = bigNumberify(formVal.usdValue);
    const convertedUsdValue
      = get(currencySymbol) === CURRENCY_USD
        ? usdValueInBigNumber
        : usdValueInBigNumber.dividedBy(get(fiatExchangeRate));

    if (!locationData) {
      return {
        before: Zero,
        after: convertedUsdValue,
      };
    }

    const isCurrentLiability = formVal.category === 'liability';
    const currentFactor = bigNumberify(isCurrentLiability ? -1 : 1);
    let usdValueDiff = convertedUsdValue.multipliedBy(currentFactor);

    const balancesSnapshot = val.balancesSnapshot;

    if (index !== null) {
      const isPrevLiability = balancesSnapshot[index].category === 'liability';
      const prevFactor = bigNumberify(isPrevLiability ? -1 : 1);
      usdValueDiff = usdValueDiff.minus(
        balancesSnapshot[index].usdValue.multipliedBy(prevFactor),
      );
    }

    return {
      before: locationData.usdValue,
      after: locationData.usdValue.plus(usdValueDiff),
    };
  },
);

const previewDeleteLocationBalance = computed<Record<string, BigNumber> | null>(
  () => {
    const index = get(indexToDelete);
    const location = get(locationToDelete);

    if (index === null || !location)
      return null;

    const val = get(value);
    const locationData = val.locationDataSnapshot.find(
      item => item.location === location,
    );
    const balanceData = val.balancesSnapshot[index];

    if (!locationData || !balanceData)
      return null;

    const isCurrentLiability = balanceData.category === 'liability';
    const currentFactor = bigNumberify(isCurrentLiability ? 1 : -1);
    const usdValueDiff = balanceData.usdValue.multipliedBy(currentFactor);

    return {
      before: locationData.usdValue,
      after: locationData.usdValue.plus(usdValueDiff),
    };
  },
);

function updateData(balancesSnapshot: BalanceSnapshot[], location = '', calculatedBalance: Record<string, BigNumber> | null = null) {
  const val = get(value);
  const locationDataSnapshot = [...val.locationDataSnapshot];

  if (location) {
    const locationDataIndex = locationDataSnapshot.findIndex(
      item => item.location === location,
    );
    if (locationDataIndex > -1) {
      locationDataSnapshot[locationDataIndex].usdValue
        = calculatedBalance!.after;
    }
    else {
      locationDataSnapshot.push({
        timestamp: get(timestamp),
        location,
        usdValue: calculatedBalance!.after,
      });
    }
  }

  const assetsValue = balancesSnapshot.map((item: BalanceSnapshot) => {
    if (item.category === 'asset')
      return item.usdValue;

    return item.usdValue.negated();
  });

  const total = bigNumberSum(assetsValue);

  const totalDataIndex = locationDataSnapshot.findIndex(
    item => item.location === 'total',
  );

  locationDataSnapshot[totalDataIndex].usdValue = total;

  input({
    balancesSnapshot,
    locationDataSnapshot,
  });
}

const {
  openDialog,
  setOpenDialog,
  closeDialog,
  submitting,
  setSubmitFunc,
  trySubmit,
} = useEditBalancesSnapshotForm();

async function save() {
  const formVal = get(form);

  if (!formVal)
    return;

  const index = get(indexToEdit);
  const val = get(value);
  const timestampVal = get(timestamp);

  const usdValueInBigNumber = bigNumberify(formVal.usdValue);
  const convertedUsdValue
    = get(currencySymbol) === CURRENCY_USD
      ? usdValueInBigNumber
      : usdValueInBigNumber.dividedBy(get(fiatExchangeRate));

  const balancesSnapshot = [...val.balancesSnapshot];
  const payload = {
    timestamp: timestampVal,
    category: formVal.category,
    assetIdentifier: formVal.assetIdentifier,
    amount: bigNumberify(formVal.amount),
    usdValue: convertedUsdValue,
  };

  if (index !== null)
    balancesSnapshot[index] = payload;
  else
    balancesSnapshot.unshift(payload);

  updateData(balancesSnapshot, formVal.location, get(previewLocationBalance));
  clearEditDialog();
}

setSubmitFunc(save);

function clearEditDialog() {
  closeDialog();
  set(indexToEdit, null);
  set(form, null);
}

function updateForm(newForm: BalanceSnapshotPayload & { location: string }) {
  set(form, newForm);
}

function clearDeleteDialog() {
  set(indexToDelete, null);
  set(showDeleteConfirmation, false);
  set(locationToDelete, '');
}

function confirmDelete() {
  const index = get(indexToDelete);
  const val = get(value);
  const location = get(locationToDelete);

  if (index === null)
    return;

  const balancesSnapshot = [...val.balancesSnapshot];
  balancesSnapshot.splice(index, 1);

  updateData(balancesSnapshot, location, get(previewDeleteLocationBalance));
  clearDeleteDialog();
}

const tableRef = ref<any>(null);

const tableContainer = computed(() => get(tableRef)?.$el);
</script>

<template>
  <div>
    <div class="grid md:grid-cols-2 pa-4 border-b border-default">
      <AssetSelect
        v-model="assetSearch"
        outlined
        hide-details
        clearable
        :label="t('dashboard.snapshot.search_asset')"
      />
    </div>
    <DataTable
      ref="tableRef"
      class="table-inside-dialog"
      :class="css['table-inside-dialog']"
      :headers="tableHeaders"
      :items="filteredData"
      :container="tableContainer"
      :mobile-breakpoint="0"
      flat
      disable-floating-header
    >
      <template #item.category="{ item }">
        <div>
          <span>{{ toSentenceCase(item.category) }}</span>
          <span v-if="isNft(item.assetIdentifier)">
            ({{ t('dashboard.snapshot.edit.dialog.balances.nft') }})
          </span>
        </div>
      </template>

      <template #item.assetIdentifier="{ item }">
        <AssetDetails
          v-if="!isNft(item.assetIdentifier)"
          class="[&_.avatar]:ml-1.5 [&_.avatar]:mr-2"
          :asset="item.assetIdentifier"
          :opens-details="false"
          :enable-association="false"
        />
        <NftDetails
          v-else
          :identifier="item.assetIdentifier"
          :class="css.asset"
        />
      </template>

      <template #item.amount="{ item }">
        <AmountDisplay :value="item.amount" />
      </template>

      <template #item.usdValue="{ item }">
        <AmountDisplay
          :value="item.usdValue"
          fiat-currency="USD"
        />
      </template>

      <template #item.action="{ item }">
        <RowActions
          :edit-tooltip="t('dashboard.snapshot.edit.dialog.actions.edit_item')"
          :delete-tooltip="
            t('dashboard.snapshot.edit.dialog.actions.delete_item')
          "
          @edit-click="editClick(item)"
          @delete-click="deleteClick(item)"
        />
      </template>
    </DataTable>
    <div
      class="border-t-2 border-rui-grey-300 dark:border-rui-grey-800 relative z-[2] flex items-center justify-between gap-4 p-2"
    >
      <div>
        <div class="text-caption">
          {{ t('common.total') }}:
        </div>
        <div class="font-bold text-h6 -mt-1">
          <AmountDisplay
            :value="total"
            fiat-currency="USD"
          />
        </div>
      </div>

      <div class="flex gap-2">
        <RuiButton
          variant="text"
          color="primary"
          @click="add()"
        >
          <template #prepend>
            <RuiIcon name="add-circle-line" />
          </template>
          {{ t('dashboard.snapshot.edit.dialog.actions.add_new_entry') }}
        </RuiButton>
        <RuiButton
          color="primary"
          @click="updateStep(2)"
        >
          {{ t('common.actions.next') }}
          <template #append>
            <RuiIcon name="arrow-right-line" />
          </template>
        </RuiButton>
      </div>
    </div>

    <BigDialog
      :display="openDialog"
      :title="
        indexToEdit !== null
          ? t('dashboard.snapshot.edit.dialog.balances.edit_title')
          : t('dashboard.snapshot.edit.dialog.balances.add_title')
      "
      :primary-action="t('common.actions.save')"
      :loading="submitting"
      @confirm="trySubmit()"
      @cancel="clearEditDialog()"
    >
      <EditBalancesSnapshotForm
        v-if="form"
        :edit="!!indexToEdit"
        :form="form"
        :preview-location-balance="previewLocationBalance"
        :locations="indexToEdit !== null ? existingLocations : []"
        @update:form="updateForm($event)"
        @update:asset="checkAssetExist($event)"
      />

      <ConfirmSnapshotConflictReplacementDialog
        :snapshot="conflictedBalanceSnapshot"
        @cancel="cancelConvertToEdit()"
        @confirm="convertToEdit()"
      />
    </BigDialog>

    <ConfirmDialog
      :display="showDeleteConfirmation"
      :title="t('dashboard.snapshot.edit.dialog.balances.delete_title')"
      :message="
        t('dashboard.snapshot.edit.dialog.balances.delete_confirmation')
      "
      max-width="700"
      @cancel="clearDeleteDialog()"
      @confirm="confirmDelete()"
    >
      <div class="mt-4">
        <EditBalancesSnapshotLocationSelector
          v-model="locationToDelete"
          :locations="existingLocations"
          :preview-location-balance="previewDeleteLocationBalance"
        />
      </div>
    </ConfirmDialog>
  </div>
</template>

<style module lang="scss">
.table-inside-dialog {
  max-height: calc(100vh - 420px);
}
</style>
