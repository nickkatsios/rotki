<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';

const isDevelopment = checkIfDevelopment();

const { smAndUp } = useDisplay();

const { darkModeEnabled } = useDarkMode();
const { showPinned, showNotesSidebar, showNotificationBar, showHelpBar }
  = storeToRefs(useAreaVisibilityStore());
</script>

<template>
  <Fragment>
    <div class="flex overflow-hidden grow">
      <SyncIndicator />
      <GlobalSearch v-if="smAndUp" />
      <BackButton />
    </div>
    <div class="flex overflow-hidden h-full items-center">
      <GetPremiumButton />
      <RouterLink
        v-if="isDevelopment && smAndUp"
        to="/playground"
      >
        <RuiButton
          variant="text"
          icon
        >
          <RuiIcon name="code-box-line" />
        </RuiButton>
      </RouterLink>
      <AppUpdateIndicator />
      <UserNotesIndicator
        :visible.sync="showNotesSidebar"
      />
      <PinnedIndicator
        :visible.sync="showPinned"
      />
      <ThemeControl
        v-if="smAndUp"
        :dark-mode-enabled="darkModeEnabled"
      />
      <NotificationIndicator
        :visible="showNotificationBar"
        class="app__app-bar__button"
        @click="showNotificationBar = !showNotificationBar"
      />
      <CurrencyDropdown class="app__app-bar__button" />
      <PrivacyModeDropdown
        v-if="smAndUp"
        class="app__app-bar__button"
      />
      <UserDropdown class="app__app-bar__button" />
      <HelpIndicator
        v-if="smAndUp"
        :visible.sync="showHelpBar"
      />
    </div>
  </Fragment>
</template>

<style module lang="scss">
.language {
  width: 110px;
}
</style>
