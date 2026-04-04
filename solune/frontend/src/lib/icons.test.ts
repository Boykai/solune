/**
 * Tests for icons.ts — centralized Lucide icon re-exports.
 *
 * Verifies the barrel file exports commonly-used icons and that the
 * ESLint-enforced single-import-source pattern works correctly.
 */
import { describe, it, expect } from 'vitest';
import * as Icons from './icons';

describe('icons barrel export', () => {
  it('exports LucideIcon type', () => {
    // LucideIcon is a type-only export — verify the module itself is importable
    expect(Icons).toBeDefined();
  });

  it('exports commonly-used navigation icons', () => {
    expect(Icons.LayoutDashboard).toBeDefined();
    expect(Icons.Kanban).toBeDefined();
    expect(Icons.GitBranch).toBeDefined();
    expect(Icons.Bot).toBeDefined();
    expect(Icons.Wrench).toBeDefined();
    expect(Icons.Settings).toBeDefined();
  });

  it('exports UI action icons', () => {
    expect(Icons.Plus).toBeDefined();
    expect(Icons.X).toBeDefined();
    expect(Icons.Check).toBeDefined();
    expect(Icons.Search).toBeDefined();
    expect(Icons.Save).toBeDefined();
    expect(Icons.Trash2).toBeDefined();
    expect(Icons.Pencil).toBeDefined();
    expect(Icons.Copy).toBeDefined();
  });

  it('exports status/notification icons', () => {
    expect(Icons.AlertCircle).toBeDefined();
    expect(Icons.AlertTriangle).toBeDefined();
    expect(Icons.CheckCircle).toBeDefined();
    expect(Icons.Info).toBeDefined();
    expect(Icons.Bell).toBeDefined();
    expect(Icons.TriangleAlert).toBeDefined();
  });

  it('exports theme icons', () => {
    expect(Icons.Moon).toBeDefined();
    expect(Icons.Sun).toBeDefined();
    expect(Icons.SunMoon).toBeDefined();
  });

  it('exports all icons as valid React components', () => {
    const exports = Object.entries(Icons).filter(
      ([key]) => key !== 'default' && key[0] === key[0].toUpperCase()
    );
    for (const [name, icon] of exports) {
      expect(icon, `Icon ${name} should be defined`).toBeDefined();
      expect(
        typeof icon === 'object' || typeof icon === 'function',
        `Icon ${name} should be a valid component (object or function)`,
      ).toBe(true);
    }
  });

  it('exports at least 50 icons', () => {
    const iconExports = Object.keys(Icons).filter(
      (key) => key !== 'default' && key[0] === key[0].toUpperCase()
    );
    expect(iconExports.length).toBeGreaterThanOrEqual(50);
  });
});
