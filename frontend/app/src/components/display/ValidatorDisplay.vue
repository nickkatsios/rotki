<script setup lang="ts">
import { truncateAddress } from '@/utils/truncate';
import type { Eth2ValidatorEntry } from '@rotki/common/lib/staking/eth2';

const props = withDefaults(
  defineProps<{
    validator: Eth2ValidatorEntry;
    horizontal?: boolean;
  }>(),
  {
    horizontal: false,
  },
);

const { horizontal } = toRefs(props);
const length = computed(() => (get(horizontal) ? 4 : 10));

const { t } = useI18n();

const { scrambleIdentifier, scrambleHex, shouldShowAmount } = useScramble();
</script>

<template>
  <div
    :class="{
      flex: horizontal,
      blur: !shouldShowAmount,
    }"
  >
    <div class="font-medium text-truncate">
      {{ truncateAddress(scrambleHex(validator.publicKey), length) }}
    </div>
    <div>
      <span
        v-if="horizontal"
        class="px-1"
      >
        -
      </span>
      <span
        v-else
        class="text-caption"
      >
        {{ t('common.validator_index') }}:
      </span>
      {{ scrambleIdentifier(validator.validatorIndex) }}
    </div>
  </div>
</template>
