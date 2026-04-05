/**
 * ImportAppDialog — modal for importing a GitHub repository into Solune.
 * Validates URL, uses the shared dialog wrapper, and handles async submission.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
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
    <Dialog open={true} onOpenChange={(open) => { if (!open && !isPending) onClose(); }}>
      <DialogContent hideClose className="max-w-md">
        <DialogHeader>
          <DialogTitle>Import from GitHub</DialogTitle>
          <DialogDescription>
            Import an existing repository into Solune and optionally create a linked GitHub Project.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
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

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!isValidUrl || isPending}
              data-testid="import-submit"
            >
              {isPending ? 'Importing…' : 'Import'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
