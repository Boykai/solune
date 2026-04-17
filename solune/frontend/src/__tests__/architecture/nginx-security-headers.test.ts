/**
 * Static validation tests for nginx.conf security headers (SC-006).
 *
 * These tests parse the nginx configuration file and verify that all required
 * security headers are present in every location block that defines add_header
 * directives, since nginx does not inherit server-level headers into locations
 * that define their own.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const NGINX_CONF_PATH = resolve(__dirname, '../../../nginx.conf');
const nginxConf = readFileSync(NGINX_CONF_PATH, 'utf-8');

/** Required security headers that must be present in nginx config. */
const REQUIRED_HEADERS = [
  'Content-Security-Policy',
  'Strict-Transport-Security',
  'Referrer-Policy',
  'Permissions-Policy',
  'X-Frame-Options',
  'X-Content-Type-Options',
];

/** Headers that should NOT be present (deprecated). */
const DEPRECATED_HEADERS = ['X-XSS-Protection'];

describe('nginx.conf security headers (SC-006)', () => {
  it('contains all required security headers', () => {
    for (const header of REQUIRED_HEADERS) {
      expect(nginxConf).toContain(header);
    }
  });

  it('does not contain deprecated X-XSS-Protection header', () => {
    for (const header of DEPRECATED_HEADERS) {
      expect(nginxConf).not.toContain(header);
    }
  });

  it('has server_tokens off to hide nginx version', () => {
    expect(nginxConf).toContain('server_tokens off');
  });

  it('sets X-Frame-Options to DENY (not SAMEORIGIN)', () => {
    // All X-Frame-Options directives should be DENY, not SAMEORIGIN
    const frameOptions = nginxConf.match(/X-Frame-Options\s+"([^"]+)"/g) || [];
    expect(frameOptions.length).toBeGreaterThan(0);
    for (const directive of frameOptions) {
      expect(directive).toContain('DENY');
      expect(directive).not.toContain('SAMEORIGIN');
    }
  });

  it('sets HSTS with max-age >= 1 year', () => {
    const hstsMatches = nginxConf.match(/max-age=(\d+)/g) || [];
    expect(hstsMatches.length).toBeGreaterThan(0);
    for (const match of hstsMatches) {
      const maxAge = parseInt(match.replace('max-age=', ''), 10);
      expect(maxAge).toBeGreaterThanOrEqual(31536000); // 1 year in seconds
    }
  });

  it('includes security headers in /assets/ location block', () => {
    // Extract the /assets/ location block
    const assetsBlock = extractLocationBlock(nginxConf, '/assets/');
    expect(assetsBlock).toBeDefined();
    if (assetsBlock) {
      for (const header of REQUIRED_HEADERS) {
        expect(assetsBlock).toContain(header);
      }
    }
  });

  it('includes security headers in / location block', () => {
    // The root location block must also include all security headers
    const rootBlock = extractLocationBlock(nginxConf, '/ {');
    expect(rootBlock).toBeDefined();
    if (rootBlock) {
      for (const header of REQUIRED_HEADERS) {
        expect(rootBlock).toContain(header);
      }
    }
  });

  it('includes CSP with frame-ancestors none', () => {
    expect(nginxConf).toContain("frame-ancestors 'none'");
  });

  it('includes Referrer-Policy with strict-origin-when-cross-origin', () => {
    expect(nginxConf).toContain('strict-origin-when-cross-origin');
  });

  it('includes Permissions-Policy restricting camera, microphone, geolocation', () => {
    expect(nginxConf).toContain('camera=()');
    expect(nginxConf).toContain('microphone=()');
    expect(nginxConf).toContain('geolocation=()');
  });
});

/**
 * Extract the text content of a location block from nginx config.
 * Simple heuristic: finds 'location <path>' and captures until the matching '}'.
 */
function extractLocationBlock(
  config: string,
  locationPath: string,
): string | undefined {
  const idx = config.indexOf(`location ${locationPath}`);
  if (idx === -1) return undefined;

  let depth = 0;
  let start = -1;
  for (let i = idx; i < config.length; i++) {
    if (config[i] === '{') {
      if (start === -1) start = i;
      depth++;
    } else if (config[i] === '}') {
      depth--;
      if (depth === 0) {
        return config.substring(start, i + 1);
      }
    }
  }
  return undefined;
}
