import { z } from 'zod';
import { logger } from '@/lib/logger';

export function validateResponse<T>(schema: z.ZodType<T>, data: unknown, endpoint: string): T {
  if (!import.meta.env.DEV) {
    return data as T;
  }

  try {
    return schema.parse(data);
  } catch (error) {
    logger.warn('schema', `API schema validation failed for ${endpoint}`, { error });
    throw error;
  }
}
