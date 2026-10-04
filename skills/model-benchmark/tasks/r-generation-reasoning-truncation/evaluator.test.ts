import { expect, it } from 'vitest';
import { GenerationGuard, GenerationGuardError } from './generation-guard.js';

it('retains only the prefix that fits for verbose reasoning without aborting', () => {
  const guard = new GenerationGuard({ maxReasoningCharacters: 5, maxOutputCharacters: 5 });

  expect(guard.observeReasoning('123')).toBe('123');
  expect(guard.observeReasoning('456')).toBe('45');
  expect(guard.observeReasoning('789')).toBe('');
  expect(guard.reasoningCharacters).toBe(5);
});

it('leaves capacity for later visible text after verbose reasoning', () => {
  const guard = new GenerationGuard({
    maxReasoningCharacters: 5,
    maxOutputCharacters: 5,
    maxTextCharacters: 5,
  });

  expect(guard.observeReasoning('123456')).toBe('12345');
  expect(() => guard.observeText('hello')).not.toThrow();
  expect(guard.outputCharacters).toBe(5);
});

it('still rejects visible text that exceeds its own cap', () => {
  const guard = new GenerationGuard({ maxTextCharacters: 5 });

  expect(() => guard.observeText('123456')).toThrow(GenerationGuardError);
});
