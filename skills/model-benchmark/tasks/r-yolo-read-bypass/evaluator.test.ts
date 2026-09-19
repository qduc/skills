import { it, expect } from 'vitest';
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs/promises';
import { createReadFileToolDefinition } from './read-file.js';
import { createCreateFileToolDefinition } from './create-file.js';

// YOLO (shell.autoApproveMode 'always') approved every shell command but never
// consulted the read tools' workspace-boundary checks, so reading a file
// outside the workspace still prompted. This evaluator asserts the yolo read
// bypass through the public factory API, plus the invariant that writes never
// consult autoApproveMode.
const yoloSettings = {
  get: (key: string) => {
    if (key === 'shell.autoApproveMode') return 'always';
    if (key === 'sandbox.enabled') return false;
    return undefined;
  },
};

async function withTempDir(fn: (dir: string) => Promise<void>): Promise<void> {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'term2-yolo-eval-'));
  try {
    await fn(dir);
  } finally {
    await fs.rm(dir, { recursive: true, force: true });
  }
}

it('yolo mode bypasses the workspace boundary for reads', async () => {
  const tool = createReadFileToolDefinition({ settingsService: yoloSettings } as any);
  const result = await tool.needsApproval({ path: '/etc/passwd' });
  expect(result).toBe(false);
});

it('yolo mode does NOT bypass outside-workspace writes', async () => {
  await withTempDir(async (dir) => {
    const tool = createCreateFileToolDefinition({
      settingsService: yoloSettings,
      executionContext: { getCwd: () => dir },
    } as any);
    const result = await tool.needsApproval({ path: '../outside-file.txt', content: 'x', overwrite: true });
    expect(result).toBe(true);
  });
});
