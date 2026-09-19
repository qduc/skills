import { it, expect } from 'vitest';
import { OpenAIChatCompletionsModel } from './openai-chat-completions-model.js';

async function* emptyStream(): AsyncIterable<any> {
  yield { choices: [{ delta: {}, finish_reason: 'stop' }] };
}

// Streaming chat completions omit the usage block unless the request opts in.
// Without it `lastUsage` stayed empty for every chat-completions provider, so
// the status bar could never show context, token counts, or cost.
it('requests streamed usage so the status bar has token counts', async () => {
  const bodies: any[] = [];
  const client = {
    chat: {
      completions: {
        create: async (body: any) => {
          bodies.push(body);
          return emptyStream();
        },
      },
    },
  };
  const model = new OpenAIChatCompletionsModel(client as any, 'fixture-chat');

  for await (const _event of model.stream({ input: [], tools: [] } as any)) {
    // drain
  }

  expect(bodies[0].stream_options).toEqual({ include_usage: true });
});

// The opt-in terminal chunk carries usage with an empty `choices` array.
it('reports usage from the terminal chunk that carries no choice', async () => {
  async function* usageTerminalStream(): AsyncIterable<any> {
    yield { choices: [{ delta: { content: 'done' } }] };
    yield { choices: [{ delta: {}, finish_reason: 'stop' }] };
    yield { choices: [], usage: { prompt_tokens: 1234, completion_tokens: 56 } };
  }

  const client = { chat: { completions: { create: async () => usageTerminalStream() } } };
  const model = new OpenAIChatCompletionsModel(client as any, 'fixture-chat');
  const events: any[] = [];
  for await (const event of model.stream({ input: [], tools: [] } as any)) {
    events.push(event);
  }

  const completion = events.find((event) => event.type === 'completion');
  expect(completion.usage).toMatchObject({ inputTokens: 1234, outputTokens: 56 });
});
