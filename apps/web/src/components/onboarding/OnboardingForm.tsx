'use client';

import { useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { api } from '@/lib/api';
import { lucideReact } from '@/lib/lucide-imports';

const { GitBranch, ArrowRight, AlertCircle } = lucideReact;

export function OnboardingForm() {
  const { setProject, setRepository, setChange, setConstitution, setActiveTab } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    projectName: '',
    repoUrl: '',
    changeTitle: '',
    changeDescription: '',
    changeAuthor: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.projectName || !form.repoUrl || !form.changeTitle) return;

    setLoading(true);
    setError(null);

    try {
      const result = await api.startWorkflow({
        project_name: form.projectName,
        repo_url: form.repoUrl,
        change_title: form.changeTitle,
        change_description: form.changeDescription,
        change_author: form.changeAuthor,
      });

      setProject({
        id: result.project.id,
        name: result.project.name,
        slug: result.project.slug,
        description: result.project.description,
      });

      setRepository({
        id: result.repository.id,
        name: result.repository.name,
        url: result.repository.url,
        defaultBranch: result.repository.default_branch,
      });

      setChange({
        id: result.change.id,
        externalId: result.change.external_id,
        title: result.change.title,
        description: result.change.description,
        status: result.change.status || 'OPEN',
        commitSha: result.change.commit_sha,
      });

      setConstitution({
        id: result.constitution.id,
        title: result.constitution.title,
        version: 1,
        status: 'ACTIVE',
        claimCount: result.intents.length,
        protectedCount: 0,
        locked: false,
      });

      setActiveTab('Discover');
    } catch (err: any) {
      setError(err.message || 'Failed to start workflow');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-smoke)] p-6">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h1 className="text-[2rem] font-bold text-[var(--color-text-primary)] font-display tracking-tight">
            Software Evolution Intelligence
          </h1>
          <p className="text-[0.9rem] text-[var(--color-text-secondary)] mt-2">
            Enter your repository details to begin autonomous analysis
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-[var(--color-surface-border)] p-6 space-y-5">
          <div>
            <label className="block text-[0.75rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
              Project Name
            </label>
            <input
              type="text"
              value={form.projectName}
              onChange={(e) => setForm({ ...form, projectName: e.target.value })}
              placeholder="e.g. Payments API"
              className="w-full px-3 py-2 text-[0.85rem] rounded-lg border border-[var(--color-surface-border)] bg-[var(--color-smoke)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-focus)]"
              required
            />
          </div>

          <div>
            <label className="block text-[0.75rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
              <GitBranch size={12} className="inline mr-1" />
              GitHub Repository URL
            </label>
            <input
              type="url"
              value={form.repoUrl}
              onChange={(e) => setForm({ ...form, repoUrl: e.target.value })}
              placeholder="https://github.com/owner/repo"
              className="w-full px-3 py-2 text-[0.85rem] rounded-lg border border-[var(--color-surface-border)] bg-[var(--color-smoke)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-focus)]"
              required
            />
          </div>

          <div>
            <label className="block text-[0.75rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
              Change Title
            </label>
            <input
              type="text"
              value={form.changeTitle}
              onChange={(e) => setForm({ ...form, changeTitle: e.target.value })}
              placeholder="e.g. Add passkey authentication"
              className="w-full px-3 py-2 text-[0.85rem] rounded-lg border border-[var(--color-surface-border)] bg-[var(--color-smoke)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-focus)]"
              required
            />
          </div>

          <div>
            <label className="block text-[0.75rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
              Change Description (optional)
            </label>
            <textarea
              value={form.changeDescription}
              onChange={(e) => setForm({ ...form, changeDescription: e.target.value })}
              placeholder="Describe what this change does..."
              rows={3}
              className="w-full px-3 py-2 text-[0.85rem] rounded-lg border border-[var(--color-surface-border)] bg-[var(--color-smoke)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-focus)] resize-none"
            />
          </div>

          <div>
            <label className="block text-[0.75rem] font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-1.5">
              Author (optional)
            </label>
            <input
              type="text"
              value={form.changeAuthor}
              onChange={(e) => setForm({ ...form, changeAuthor: e.target.value })}
              placeholder="e.g. loujan"
              className="w-full px-3 py-2 text-[0.85rem] rounded-lg border border-[var(--color-surface-border)] bg-[var(--color-smoke)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent-focus)]"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#fcefee] border border-[#f5d5d3] text-[#d8493c] text-[0.8rem]">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !form.projectName || !form.repoUrl || !form.changeTitle}
            className="btn btn--primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Analyzing repository...
              </>
            ) : (
              <>
                Start Analysis
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
