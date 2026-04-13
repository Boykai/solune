import { describe, expect, it, vi } from 'vitest';
import { createLogger, sanitizeLogContext } from './logger';

describe('logger', () => {
  it('redacts sensitive keys in nested log context', () => {
    expect(
      sanitizeLogContext({
        authorization: 'Bearer secret',
        nested: {
          token: 'abc123',
          cookie: 'session=1',
          safe: 'value',
        },
      })
    ).toEqual({
      authorization: '[REDACTED]',
      nested: {
        token: '[REDACTED]',
        cookie: '[REDACTED]',
        safe: 'value',
      },
    });
  });

  it('only emits debug logs in dev mode', () => {
    const sink = {
      debug: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    };
    const logger = createLogger({ devMode: false, sink });

    logger.debug('sse', 'Debug message', { token: 'secret' });

    expect(sink.debug).not.toHaveBeenCalled();
  });

  it('logs warnings with sanitized context', () => {
    const sink = {
      debug: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    };
    const logger = createLogger({ devMode: true, sink });

    logger.warn('schema', 'Validation failed', { cookie: 'session=1', endpoint: 'apps.list' });

    expect(sink.warn).toHaveBeenCalledWith('[schema] Validation failed', {
      cookie: '[REDACTED]',
      endpoint: 'apps.list',
    });
  });

  it('captures exceptions with structured error metadata', () => {
    const sink = {
      debug: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    };
    const logger = createLogger({ devMode: true, sink });

    logger.captureException(new Error('boom'), { token: 'abc123' });

    expect(sink.error).toHaveBeenCalledWith('[exception] boom', {
      error: expect.objectContaining({ message: 'boom', name: 'Error' }),
      token: '[REDACTED]',
    });
  });
});
