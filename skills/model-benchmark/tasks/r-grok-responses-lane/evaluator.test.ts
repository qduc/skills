import { expect, it } from 'vitest';
import { createResponseEventNormalizationState, normalizeResponseEvent } from './openai-responses-model.js';

it('keeps foreign Responses-native items on their own vendor lane', () => {
  const completion: any = (normalizeResponseEvent as any)(
    {
      type: 'response.completed',
      response: { id: 'resp-1', status: 'completed', output: [{ type: 'compaction', id: 'compact-1' }] },
    },
    createResponseEventNormalizationState(),
    'grok',
  );

  expect(completion.output).toEqual([
    expect.objectContaining({ type: 'provider_opaque', provider: 'grok' }),
  ]);
});

it('namespaces encrypted reasoning under the producing vendor', () => {
  const completion: any = (normalizeResponseEvent as any)(
    {
      type: 'response.completed',
      response: {
        id: 'resp-2',
        output: [
          { type: 'reasoning', id: 'reason-1', summary: [], encrypted_content: 'vendor-ciphertext' },
        ],
      },
    },
    createResponseEventNormalizationState(),
    'grok',
  );

  expect(completion.output[0].providerMetadata).toEqual({ grok: { encrypted_content: 'vendor-ciphertext' } });
  expect(completion.output[0].providerMetadata.openai).toBeUndefined();
});

it('leaves the existing Responses vendor as the default', () => {
  const completion: any = normalizeResponseEvent(
    { type: 'response.completed', response: { id: 'resp-3', output: [{ type: 'compaction', id: 'compact-2' }] } },
    createResponseEventNormalizationState(),
  );

  expect(completion.output[0]).toMatchObject({ type: 'provider_opaque', provider: 'openai' });
});
