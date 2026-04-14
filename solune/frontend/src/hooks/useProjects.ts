/**
 * Projects hook for listing and selecting GitHub Projects.
 */

import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { projectsApi } from '@/services/api';
import type { ApiError } from '@/services/api';
import { STALE_TIME_PROJECTS } from '@/constants';
import type { Project, ProjectListResponse } from '@/types';
import type { CreateProjectRequest, CreateProjectResponse } from '@/types/apps';

interface UseProjectsReturn {
  projects: Project[];
  isLoading: boolean;
  error: Error | null;
  selectedProject: Project | null;
  selectProject: (projectId: string) => Promise<void>;
  refreshProjects: () => void;
}

export function useProjects(selectedProjectId?: string | null): UseProjectsReturn {
  const queryClient = useQueryClient();

  // Fetch projects list
  const {
    data: projectsData,
    isLoading,
    error,
    refetch: refreshProjects,
  } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
    staleTime: STALE_TIME_PROJECTS,
    retry: false,
  });

  // Select project mutation
  const selectMutation = useMutation({
    mutationFn: projectsApi.select,
    onSuccess: (user) => {
      // Update auth with the returned user (includes selected_project_id)
      queryClient.setQueryData(['auth', 'me'], user);
      // Also invalidate projects to refresh task data
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project selected');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Failed to select project', { duration: Infinity });
    },
  });

  const selectProject = useCallback(
    async (projectId: string) => {
      await selectMutation.mutateAsync(projectId);
    },
    [selectMutation]
  );

  // Find currently selected project from list
  const selectedProject =
    projectsData?.projects.find((p) => p.project_id === selectedProjectId) ?? null;

  return {
    projects: projectsData?.projects ?? [],
    isLoading,
    error: error as Error | null,
    selectedProject,
    selectProject,
    refreshProjects,
  };
}

/** Create a standalone GitHub Project V2. */
export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation<CreateProjectResponse, ApiError, CreateProjectRequest, {
    snapshot: ProjectListResponse;
    queryKey: readonly string[];
  } | undefined>({
    mutationFn: (data) => projectsApi.create(data),
    onMutate: async (data: CreateProjectRequest) => {
      const queryKey = ['projects'] as const;
      await queryClient.cancelQueries({ queryKey });
      const snapshot = queryClient.getQueryData<ProjectListResponse>(queryKey);
      if (!snapshot) return;

      const now = new Date().toISOString();
      const placeholder = {
        project_id: `temp-${Date.now()}`,
        owner_id: '',
        owner_login: data.owner,
        name: data.title,
        type: 'organization' as const,
        url: '',
        description: '',
        status_columns: [],
        item_count: 0,
        cached_at: now,
        _optimistic: true,
      } satisfies Project & { _optimistic: boolean };

      queryClient.setQueryData<ProjectListResponse>(queryKey, {
        ...snapshot,
        projects: [placeholder, ...snapshot.projects],
      });
      return { snapshot, queryKey };
    },
    onSuccess: () => {
      toast.success('Project created');
    },
    onError: (error, _variables, context) => {
      if (context?.snapshot && context.queryKey) {
        queryClient.setQueryData(context.queryKey, context.snapshot);
      }
      toast.error(error instanceof Error ? error.message : 'Failed to create project', { duration: Infinity });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
