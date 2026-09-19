// @ts-expect-error IS_REACT_ACT_ENVIRONMENT is not in globalThis types
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
import { expect, it } from 'vitest';
import React from 'react';
import StatusBar from './StatusBar.js';
import { createMockSettingsService } from '../../services/settings/settings-service.mock.js';
import { renderInAct } from '../../test-helpers/ink-testing.js';

it.sequential('renders a weekly credit reading and its reset date', async () => {
  const settingsService = createMockSettingsService({ 'agent.provider': 'grok', 'agent.model': 'grok-4.6' });
  const { lastFrame } = await renderInAct(
    <StatusBar
      settingsService={settingsService}
      {...({
        grokCreditUsage: {
          creditUsagePercent: 29,
          periodEndMs: Date.parse('2026-08-24T06:13:52Z'),
          productUsage: [],
        },
      } as any)}
    />,
  );

  expect(lastFrame()).toContain('Credits 29% · reset 08/24');
});

it.sequential('does not present missing usage as zero', async () => {
  const settingsService = createMockSettingsService({ 'agent.provider': 'grok' });
  const { lastFrame } = await renderInAct(<StatusBar settingsService={settingsService} {...({ grokCreditUsage: null } as any)} />);

  expect(lastFrame() ?? '').not.toContain('Credits');
});
