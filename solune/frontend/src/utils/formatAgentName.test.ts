import { describe, it, expect } from 'vitest';
import { formatAgentName } from './formatAgentName';

describe('formatAgentName', () => {
  it('returns empty string for empty slug', () => {
    expect(formatAgentName('')).toBe('');
  });

  it('title-cases a simple slug', () => {
    expect(formatAgentName('linter')).toBe('Linter');
  });

  it('formats dot-separated segments', () => {
    expect(formatAgentName('speckit.tasks')).toBe('Spec Kit - Tasks');
  });

  it('formats hyphen-separated words', () => {
    expect(formatAgentName('quality-assurance')).toBe('Quality Assurance');
  });

  it('formats underscore-separated words', () => {
    expect(formatAgentName('quality_assurance')).toBe('Quality Assurance');
  });

  it('uppercases version-like segments', () => {
    expect(formatAgentName('api.v2')).toBe('Api - V2');
  });

  it('prefers displayName over slug', () => {
    expect(formatAgentName('linter', 'Custom Linter')).toBe('Custom Linter');
  });

  it('formats raw-slug displayName as slug', () => {
    expect(formatAgentName('linter', 'quality-assurance')).toBe('Quality Assurance');
  });

  it('returns displayName verbatim if it has spaces/caps', () => {
    expect(formatAgentName('x', 'My Agent')).toBe('My Agent');
  });

  it('falls back to slug when displayName is null', () => {
    expect(formatAgentName('tester', null)).toBe('Tester');
  });

  it('falls back to slug when displayName is empty string', () => {
    expect(formatAgentName('tester', '')).toBe('Tester');
  });

  it('handles specKitStyle suffix option', () => {
    expect(formatAgentName('speckit.tasks', undefined, { specKitStyle: 'suffix' })).toBe(
      'Tasks (Spec Kit)',
    );
  });

  it('returns "Spec Kit" for bare speckit slug with suffix style', () => {
    expect(formatAgentName('speckit', undefined, { specKitStyle: 'suffix' })).toBe('Spec Kit');
  });

  it('formats unknown speckit subcommand with suffix style', () => {
    expect(formatAgentName('speckit.unknown', undefined, { specKitStyle: 'suffix' })).toBe(
      'Unknown (Spec Kit)',
    );
  });

  it('filters empty dot segments', () => {
    expect(formatAgentName('a..b')).toBe('A - B');
  });
});
