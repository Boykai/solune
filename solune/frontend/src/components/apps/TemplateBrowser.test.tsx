/**
 * Unit tests for the TemplateBrowser component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TemplateBrowser } from './TemplateBrowser';
import type { AppTemplateSummary } from '@/types/app-template';

const MOCK_TEMPLATES: AppTemplateSummary[] = [
  {
    id: 'saas-react-fastapi',
    name: 'SaaS — React + FastAPI',
    description: 'Full-stack SaaS application',
    category: 'saas',
    difficulty: 'L',
    tech_stack: ['react', 'fastapi', 'postgresql'],
    scaffold_type: 'starter',
    iac_target: 'azure',
  },
  {
    id: 'api-fastapi',
    name: 'API — FastAPI',
    description: 'RESTful API service',
    category: 'api',
    difficulty: 'M',
    tech_stack: ['fastapi', 'postgresql'],
    scaffold_type: 'skeleton',
    iac_target: 'docker',
  },
  {
    id: 'cli-python',
    name: 'CLI — Python',
    description: 'Command-line application',
    category: 'cli',
    difficulty: 'S',
    tech_stack: ['python', 'click'],
    scaffold_type: 'skeleton',
    iac_target: 'none',
  },
  {
    id: 'dashboard-react',
    name: 'Dashboard — React',
    description: 'Interactive data dashboard',
    category: 'dashboard',
    difficulty: 'M',
    tech_stack: ['react', 'vite', 'tailwind'],
    scaffold_type: 'starter',
    iac_target: 'docker',
  },
];

describe('TemplateBrowser', () => {
  it('renders all 4 template cards', () => {
    render(<TemplateBrowser templates={MOCK_TEMPLATES} onSelectTemplate={vi.fn()} />);

    expect(screen.getByTestId('template-card-saas-react-fastapi')).toBeInTheDocument();
    expect(screen.getByTestId('template-card-api-fastapi')).toBeInTheDocument();
    expect(screen.getByTestId('template-card-cli-python')).toBeInTheDocument();
    expect(screen.getByTestId('template-card-dashboard-react')).toBeInTheDocument();
  });

  it('displays template names and descriptions', () => {
    render(<TemplateBrowser templates={MOCK_TEMPLATES} onSelectTemplate={vi.fn()} />);

    expect(screen.getByText('SaaS — React + FastAPI')).toBeInTheDocument();
    expect(screen.getByText('Full-stack SaaS application')).toBeInTheDocument();
  });

  it('filters by category when filter button clicked', () => {
    render(<TemplateBrowser templates={MOCK_TEMPLATES} onSelectTemplate={vi.fn()} />);

    // Click the API filter button (find the button specifically)
    const apiButtons = screen.getAllByText('API');
    // The first one is the filter button
    fireEvent.click(apiButtons[0]);

    // Only API template should be visible
    expect(screen.getByTestId('template-card-api-fastapi')).toBeInTheDocument();
    expect(screen.queryByTestId('template-card-saas-react-fastapi')).not.toBeInTheDocument();
    expect(screen.queryByTestId('template-card-cli-python')).not.toBeInTheDocument();
  });

  it('shows all templates when "All" filter is clicked', () => {
    render(<TemplateBrowser templates={MOCK_TEMPLATES} onSelectTemplate={vi.fn()} />);

    // First filter to API
    const apiButtons = screen.getAllByText('API');
    fireEvent.click(apiButtons[0]);
    expect(screen.queryByTestId('template-card-cli-python')).not.toBeInTheDocument();

    // Then click All
    fireEvent.click(screen.getByText('All'));
    expect(screen.getByTestId('template-card-cli-python')).toBeInTheDocument();
  });

  it('calls onSelectTemplate with correct ID when "Use Template" clicked', () => {
    const onSelect = vi.fn();
    render(<TemplateBrowser templates={MOCK_TEMPLATES} onSelectTemplate={onSelect} />);

    fireEvent.click(screen.getByTestId('use-template-cli-python'));
    expect(onSelect).toHaveBeenCalledWith('cli-python');
  });

  it('shows loading skeleton when isLoading is true', () => {
    render(<TemplateBrowser templates={[]} onSelectTemplate={vi.fn()} isLoading />);

    expect(screen.getByTestId('template-loading')).toBeInTheDocument();
  });

  it('renders "Let AI Configure" button when onAIConfigure is provided', () => {
    const onAI = vi.fn();
    render(<TemplateBrowser templates={MOCK_TEMPLATES} onSelectTemplate={vi.fn()} onAIConfigure={onAI} />);

    const aiButton = screen.getByText(/Let AI Configure/);
    expect(aiButton).toBeInTheDocument();

    fireEvent.click(aiButton);
    expect(onAI).toHaveBeenCalled();
  });

  it('displays tech stack tags', () => {
    render(<TemplateBrowser templates={MOCK_TEMPLATES} onSelectTemplate={vi.fn()} />);

    // Use getAllByText since tech stack items appear in multiple templates
    expect(screen.getAllByText('react').length).toBeGreaterThan(0);
    expect(screen.getAllByText('fastapi').length).toBeGreaterThan(0);
    expect(screen.getByText('click')).toBeInTheDocument();
  });
});
