// @ts-expect-error IS_REACT_ACT_ENVIRONMENT is not in globalThis types
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
import { expect, it } from 'vitest';
import React from 'react';
import SettingsSelectionMenu from './SettingsSelectionMenu.js';
import { SETTINGS_CATEGORIES } from '../../hooks/settings-completion-config.js';
import { renderInAct } from '../../test-helpers/ink-testing.js';

it.sequential('never renders a stored credential in the settings picker', async () => {
  const secret = 'sk-live-terminal-should-not-show-this';
  const { lastFrame } = await renderInAct(
    <SettingsSelectionMenu
      items={[{ key: 'agent.openai.apiKey', currentValue: secret, description: 'Credential' }]}
      selectedIndex={0}
      query=""
      activeCategoryId="models"
      categories={SETTINGS_CATEGORIES}
    />,
  );

  const output = lastFrame() ?? '';
  expect(output).not.toContain(secret);
  expect(output).toContain('********');
});
