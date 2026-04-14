/**
 * AgentsPage — Agent catalog grid.
 * Composes AgentsPanel (catalog), useAgentConfig (assignments), and board columns.
 */

import { useAuth } from '@/hooks/useAuth';
import { useProjects } from '@/hooks/useProjects';
import { useProjectBoard } from '@/hooks/useProjectBoard';
import { useAgentConfig } from '@/hooks/useAgentConfig';
import { useQuery } from '@tanstack/react-query';
import { pipelinesApi } from '@/services/api';
import { AgentsPanel } from '@/components/agents/AgentsPanel';
import { CompactPageHeader } from '@/components/common/CompactPageHeader';
import { ProjectSelectionEmptyState } from '@/components/common/ProjectSelectionEmptyState';
import { Button } from '@/components/ui/button';
import { countPendingAssignedSubIssues } from '@/utils/agentCardMeta';

export function AgentsPage() {
  const { user } = useAuth();
  const {
    selectedProject,
    projects,
    isLoading: projectsLoading,
    selectProject,
  } = useProjects(user?.selected_project_id);
  const projectId = selectedProject?.project_id ?? null;

  const { boardData } = useProjectBoard({ selectedProjectId: projectId });
  const agentConfig = useAgentConfig(projectId);
  const { data: pipelineList } = useQuery({
    queryKey: ['pipelines', 'list', projectId ?? ''],
    queryFn: () => pipelinesApi.list(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  const columns = boardData?.columns ?? [];
  const repo = boardData?.columns.flatMap((c) => c.items).find((i) => i.repository)?.repository;
  const assignedCount = Object.values(agentConfig.localMappings).reduce(
    (sum, mapped) => sum + mapped.length,
    0
  );
  const agentUsageCounts = Object.values(agentConfig.localMappings).reduce<Record<string, number>>(
    (counts, mapped) => {
      mapped.forEach((assignment) => {
        counts[assignment.slug] = (counts[assignment.slug] ?? 0) + 1;
      });
      return counts;
    },
    {}
  );
  const pipelineConfigCounts = (pipelineList?.pipelines ?? []).reduce<Record<string, number>>(
    (counts, pipeline) => {
      const pipelineAgentSlugs = new Set(
        pipeline.stages.flatMap((stage) => {
          const fromGroups = (stage.groups ?? []).flatMap((g) => g.agents);
          const agents = fromGroups.length > 0 ? fromGroups : stage.agents;
          return agents.map((agent) => agent.agent_slug);
        })
      );
      pipelineAgentSlugs.forEach((slug) => {
        counts[slug] = (counts[slug] ?? 0) + 1;
      });
      return counts;
    },
    {}
  );
  const pendingSubIssueCounts = countPendingAssignedSubIssues(boardData);

  return (
    <div className="celestial-fade-in flex flex-col gap-5 rounded-[1.5rem] border border-border/70 bg-background/42 p-4 backdrop-blur-sm sm:gap-6 sm:rounded-[1.75rem] sm:p-6">
      <CompactPageHeader
        eyebrow="Celestial Catalog"
        title="Shape your agent constellation."
        description="Browse repository agents in a broader catalog, spotlight the most active rituals, and keep every board column tied to the right assistant."
        badge={repo ? `${repo.owner}/${repo.name}` : 'Awaiting repository'}
        stats={[
          { label: 'Board columns', value: String(columns.length) },
          { label: 'Assignments', value: String(assignedCount) },
          { label: 'Mapped states', value: String(Object.keys(agentConfig.localMappings).length) },
          { label: 'Project', value: selectedProject?.name ?? 'Unselected' },
        ]}
        actions={
          <>
            <Button variant="default" size="lg" asChild>
              <a href="#agents-catalog">Curate agent rituals</a>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <a href="#agents-catalog">Review assignments</a>
            </Button>
          </>
        }
      />

      {/* No project selected */}
      {!projectId && (
        <ProjectSelectionEmptyState
          projects={projects}
          isLoading={projectsLoading}
          selectedProjectId={projectId}
          onSelectProject={selectProject}
          description="Choose a GitHub Project to manage its agent catalog, ownership patterns, and column assignments from one place."
        />
      )}

      {projectId && (
        <div className="min-w-0">
          <AgentsPanel
            projectId={projectId}
            owner={repo?.owner}
            repo={repo?.name}
            agentUsageCounts={agentUsageCounts}
            pipelineConfigCounts={pipelineConfigCounts}
            pendingSubIssueCounts={pendingSubIssueCounts}
          />
        </div>
      )}
    </div>
  );
}
