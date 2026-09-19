import { describe, it, expect } from 'vitest';
import { resolveWorkspacePath } from './utils.js';
import path from 'path';

describe('resolveWorkspacePath security checks', () => {
  const baseDir = '/workspace/project';

  it('allows paths strictly inside workspace', () => {
    const res = resolveWorkspacePath('src/index.ts', baseDir);
    expect(res).toBe(path.resolve(baseDir, 'src/index.ts'));
  });

  it('rejects parent traversal escaping workspace', () => {
    expect(() => {
      resolveWorkspacePath('../../etc/passwd', baseDir);
    }).toThrow();
  });

  it('rejects sibling directories with matching prefixes', () => {
    expect(() => {
      resolveWorkspacePath('/workspace/project-secret/keys.json', baseDir);
    }).toThrow();
  });
});
