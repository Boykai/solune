/**
 * ImportAppDialog — modal for importing a GitHub repository into Solune.
 * Validates URL, shows repo info, and handles import submission.
 */

import { useState } from 'react';
import type { ImportAppRequest } from '@/types/app-template';

const GITHUB_URL_RE = /^https:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+\/?$/;

interface ImportAppDialogProps {
  onImport: (request: ImportAppRequest) => void;
  onClose: () => void;
  isPending?: boolean;
}

export function ImportAppDialog({ onImport, onClose, isPending = false }: ImportAppDialogProps) {
  const [url, setUrl] = useState('');
  const [createProject, setCreateProject] = useState(true);
  const [error, setError] = useState('');

  const isValidUrl = GITHUB_URL_RE.test(url);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidUrl) {
      setError('Please enter a valid GitHub repository URL (https://github.com/owner/repo)');
      return;
    }
    setError('');
    onImport({ url, create_project: createProject });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold">Import from GitHub</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="github-url" className="mb-1 block text-sm font-medium">
              Repository URL
            </label>
            <input
              id="github-url"
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setError('');
              }}
              placeholder="https://github.com/owner/repo"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              data-testid="import-url-input"
            />
            {url && !isValidUrl && (
              <p className="mt-1 text-xs text-red-500">
                Please enter a valid GitHub URL (https://github.com/owner/repo)
              </p>
            )}
            {url && isValidUrl && (
              <p className="mt-1 text-xs text-emerald-500">✓ Valid GitHub URL</p>
            )}
            {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
          </div>

          <div className="flex items-center gap-2">
            <input
              id="create-project"
              type="checkbox"
              checked={createProject}
              onChange={(e) => setCreateProject(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="create-project" className="text-sm">
              Create GitHub Project V2 board
            </label>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isValidUrl || isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
              data-testid="import-submit"
            >
              {isPending ? 'Importing…' : 'Import'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
