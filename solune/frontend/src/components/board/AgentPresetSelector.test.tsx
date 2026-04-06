import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders, screen } from '@/test/test-utils';
import { AgentPresetSelector } from './AgentPresetSelector';

vi.mock('react-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-dom')>()),
  createPortal: (children: React.ReactNode) => children,
}));

vi.mock('@/services/api', () => ({
  pipelinesApi: {
    list: vi.fn().mockResolvedValue({ pipelines: [] }),
    get: vi.fn().mockResolvedValue({ stages: [] }),
  },
}));

describe('AgentPresetSelector', () => {
  const defaultProps = {
    columnNames: ['Todo', 'In Progress', 'Done'],
    currentMappings: {} as Record<string, { slug: string }[]>,
    onApplyPreset: vi.fn(),
    projectId: null,
  };

  it('renders without crashing', () => {
    renderWithProviders(<AgentPresetSelector {...defaultProps} />);
    expect(screen.getByText('Clear')).toBeInTheDocument();
  });

  it('renders built-in preset buttons', () => {
    renderWithProviders(<AgentPresetSelector {...defaultProps} />);
    expect(screen.getByText('Clear')).toBeInTheDocument();
    expect(screen.getByText('GitHub Copilot')).toBeInTheDocument();
    expect(screen.getByText('Spec Kit')).toBeInTheDocument();
  });

  it('does not render preset buttons in dropdownOnly mode', () => {
    renderWithProviders(<AgentPresetSelector {...defaultProps} dropdownOnly />);
    expect(screen.queryByText('Clear')).not.toBeInTheDocument();
    expect(screen.queryByText('GitHub Copilot')).not.toBeInTheDocument();
  });
});
