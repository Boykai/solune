import { describe, it, expect } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { PipelineIndicator } from './PipelineIndicator';

describe('PipelineIndicator', () => {
  it('returns null when no pipeline and no invalid mentions', () => {
    const { container } = render(
      <PipelineIndicator
        activePipelineName={null}
        hasMultipleMentions={false}
        hasInvalidMentions={false}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows "Pipeline not found" when only invalid mentions', () => {
    render(
      <PipelineIndicator
        activePipelineName={null}
        hasMultipleMentions={false}
        hasInvalidMentions={true}
      />
    );
    expect(screen.getByText('Pipeline not found')).toBeInTheDocument();
  });

  it('shows active pipeline name', () => {
    render(
      <PipelineIndicator
        activePipelineName="my-pipeline"
        hasMultipleMentions={false}
        hasInvalidMentions={false}
      />
    );
    expect(screen.getByText(/my-pipeline/)).toBeInTheDocument();
    expect(screen.getByText(/Using pipeline:/)).toBeInTheDocument();
  });

  it('shows info icon when multiple mentions exist', () => {
    const { container } = render(
      <PipelineIndicator
        activePipelineName="my-pipeline"
        hasMultipleMentions={true}
        hasInvalidMentions={false}
      />
    );
    // Should have a title about multiple pipelines
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper?.getAttribute('title')).toContain('Multiple pipelines');
  });

  it('does not set title when only single mention', () => {
    const { container } = render(
      <PipelineIndicator
        activePipelineName="my-pipeline"
        hasMultipleMentions={false}
        hasInvalidMentions={false}
      />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper?.getAttribute('title')).toBeNull();
  });
});
