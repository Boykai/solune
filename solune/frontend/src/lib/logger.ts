type LogContext = Record<string, unknown>;

type LoggerSink = Pick<Console, 'debug' | 'warn' | 'error'>;

interface LoggerOptions {
  devMode?: boolean;
  sink?: LoggerSink;
}

const REDACTED_VALUE = '[REDACTED]';
const SENSITIVE_KEY_PATTERN = /authorization|token|cookie|password|secret/i;

function serializeError(error: unknown): Record<string, unknown> {
  if (error instanceof Error) {
    return {
      message: error.message,
      name: error.name,
      stack: error.stack,
    };
  }

  return { value: error };
}

function sanitizeValue(value: unknown, seen: WeakSet<object>): unknown {
  if (value instanceof Error) {
    return serializeError(value);
  }

  if (Array.isArray(value)) {
    return value.map((item) => sanitizeValue(item, seen));
  }

  if (value && typeof value === 'object') {
    if (seen.has(value)) {
      return '[Circular]';
    }

    seen.add(value);
    const sanitizedEntries = Object.entries(value as Record<string, unknown>).map(([key, entryValue]) => [
      key,
      SENSITIVE_KEY_PATTERN.test(key) ? REDACTED_VALUE : sanitizeValue(entryValue, seen),
    ]);
    seen.delete(value);
    return Object.fromEntries(sanitizedEntries);
  }

  return value;
}

export function sanitizeLogContext(context?: LogContext): LogContext | undefined {
  if (!context) {
    return undefined;
  }

  return sanitizeValue(context, new WeakSet()) as LogContext;
}

export function createLogger(options: LoggerOptions = {}) {
  const sink = options.sink ?? console;
  const devMode = options.devMode ?? import.meta.env.DEV;

  const emit = (level: keyof LoggerSink, tag: string, message: string, context?: LogContext) => {
    const payload = sanitizeLogContext(context);
    const args: unknown[] = [`[${tag}] ${message}`];

    if (payload && Object.keys(payload).length > 0) {
      args.push(payload);
    }

    sink[level](...args);
  };

  return {
    debug(tag: string, message: string, context?: LogContext): void {
      if (!devMode) {
        return;
      }

      emit('debug', tag, message, context);
    },
    warn(tag: string, message: string, context?: LogContext): void {
      emit('warn', tag, message, context);
    },
    error(tag: string, message: string, context?: LogContext): void {
      emit('error', tag, message, context);
    },
    captureException(error: unknown, context?: LogContext): void {
      emit('error', 'exception', error instanceof Error ? error.message : 'Captured exception', {
        ...context,
        error: serializeError(error),
      });
    },
  };
}

export const logger = createLogger();
