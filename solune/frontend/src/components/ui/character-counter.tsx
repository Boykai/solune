import { cn } from '@/lib/utils';

interface CharacterCounterProps {
  current: number;
  max: number;
  className?: string;
}

export function CharacterCounter({ current, max, className }: CharacterCounterProps) {
  const warn = current > max * 0.8;
  const over = current > max;
  return (
    <span
      className={cn(
        'text-xs text-muted-foreground',
        warn && !over && 'text-amber-500',
        over && 'text-destructive',
        className,
      )}
    >
      {current.toLocaleString()} / {max.toLocaleString()} chars
    </span>
  );
}
