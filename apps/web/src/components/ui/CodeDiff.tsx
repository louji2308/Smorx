'use client';

import { forwardRef, Fragment, type HTMLAttributes } from 'react';
import { cn } from '@/lib/design-tokens';
import { lucideReact } from '@/lib/lucide-imports';

const { Copy, FileCode, Minus, Plus, Search } = lucideReact;

/**
 * CodeDiff - Displays a unified diff with syntax highlighting
 */
export interface CodeDiffProps extends HTMLAttributes<HTMLDivElement> {
  diff: CodeDiffData;
  showLineNumbers?: boolean;
  contextLines?: number;
  maxHeight?: string;
}

export interface CodeDiffData {
  filePath: string;
  oldContent?: string;
  newContent?: string;
  hunks: DiffHunk[];
}

export interface DiffHunk {
  oldStart: number;
  oldLines: number;
  newStart: number;
  newLines: number;
  lines: DiffLine[];
}

export interface DiffLine {
  type: 'context' | 'add' | 'remove';
  content: string;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export const CodeDiff = forwardRef<HTMLDivElement, CodeDiffProps>(
  ({ diff, showLineNumbers = true, contextLines = 3, maxHeight = '500px', className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'surface-card overflow-hidden',
          className
        )}
        {...props}
      >
        {/* File header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-surface-border)] bg-[var(--color-surface)]">
          <div className="flex items-center gap-3">
            <FileCode size={18} className="text-[var(--color-text-muted)]" />
            <div>
              <p className="text-body font-medium truncate max-w-[400px]">{diff.filePath}</p>
              <p className="text-caption text-[var(--color-text-muted)]">{diff.hunks.length} hunk{diff.hunks.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="p-2 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-border)] transition-colors"
              title="Copy diff"
            >
              <Copy size={16} />
            </button>
          </div>
        </div>

        {/* Diff content */}
        <div className="overflow-x-auto" style={{ maxHeight }}>
          {diff.hunks.length === 0 ? (
            <div className="p-8 text-center text-[var(--color-text-muted)]">
              <Search size={32} className="mx-auto mb-4 opacity-50" />
              <p className="text-body">No changes detected</p>
              <p className="text-caption mt-1">The files are identical</p>
            </div>
          ) : (
            <table className="w-full border-collapse font-mono text-code-sm">
              <tbody>
                {diff.hunks.map((hunk, hunkIndex) => (
                  <Fragment key={hunkIndex}>
                    {/* Hunk header */}
                    <tr className="bg-[var(--color-surface)] border-b border-[var(--color-surface-border)]">
                      <td className="px-3 py-1 text-[var(--color-text-muted)]" colSpan={showLineNumbers ? 4 : 2}>
                        <span className="text-caption">
                          @@ -{hunk.oldStart},{hunk.oldLines} +{hunk.newStart},{hunk.newLines} @@
                        </span>
                      </td>
                    </tr>
                    {/* Hunk lines */}
                    {hunk.lines.map((line, lineIndex) => (
                      <tr
                        key={`${hunkIndex}-${lineIndex}`}
                        className={cn(
                          'border-b border-[var(--color-surface-border)]/50 last:border-0',
                          line.type === 'add' && 'bg-[color-mix(in_srgb,_var(--color-trust-certified)_8%,_transparent)]',
                          line.type === 'remove' && 'bg-[color-mix(in_srgb,_var(--color-trust-violated)_8%,_transparent)]'
                        )}
                      >
                        {showLineNumbers && (
                          <>
                            <td className={cn(
                              'w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] select-none',
                              line.type === 'remove' ? 'text-[var(--color-trust-violated)]' : 'opacity-50'
                            )}>
                              {line.oldLineNumber !== undefined ? line.oldLineNumber : ''}
                            </td>
                            <td className={cn(
                              'w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] select-none',
                              line.type === 'add' ? 'text-[var(--color-trust-certified)]' : 'opacity-50'
                            )}>
                              {line.newLineNumber !== undefined ? line.newLineNumber : ''}
                            </td>
                          </>
                        )}
                        <td className={cn(
                          'w-6 px-2 py-0.5 text-center select-none font-medium',
                          line.type === 'add' && 'text-[var(--color-trust-certified)]',
                          line.type === 'remove' && 'text-[var(--color-trust-violated)]',
                          line.type === 'context' && 'text-[var(--color-text-muted)]'
                        )}>
                          {line.type === 'add' && <Plus size={12} />}
                          {line.type === 'remove' && <Minus size={12} />}
                          {line.type === 'context' && <span className="text-[var(--color-text-muted)]">·</span>}
                        </td>
                        <td className="px-3 py-0.5 whitespace-pre-wrap break-all">
                          <span className={cn(
                            line.type === 'add' && 'text-[var(--color-trust-certified)]',
                            line.type === 'remove' && 'text-[var(--color-trust-violated)]',
                            line.type === 'context' && 'text-[var(--color-text-secondary)]'
                          )}>
                            {line.content || ' '}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    );
  }
);

CodeDiff.displayName = 'CodeDiff';

/**
 * Inline diff for single line changes
 */
export interface InlineDiffProps {
  oldLine?: string;
  newLine?: string;
  showLineNumbers?: boolean;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export function InlineDiff({ oldLine, newLine, showLineNumbers = true, oldLineNumber, newLineNumber }: InlineDiffProps) {
  const isAdd = oldLine === undefined;
  const isRemove = newLine === undefined;
  const isChange = oldLine !== undefined && newLine !== undefined && oldLine !== newLine;

  if (isAdd) {
    return (
      <tr className="bg-[color-mix(in_srgb,_var(--color-trust-certified)_8%,_transparent)] border-b border-[var(--color-surface-border)]/50">
        {showLineNumbers && (
          <>
            <td className="w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] opacity-50 select-none"></td>
            <td className="w-10 px-2 py-0.5 text-right text-[var(--color-trust-certified)] select-none font-mono">
              {newLineNumber}
            </td>
          </>
        )}
        <td className="w-6 px-2 py-0.5 text-center text-[var(--color-trust-certified)] select-none font-medium">
          <Plus size={12} />
        </td>
        <td className="px-3 py-0.5 whitespace-pre-wrap break-all text-[var(--color-trust-certified)]">
          {newLine || ' '}
        </td>
      </tr>
    );
  }

  if (isRemove) {
    return (
      <tr className="bg-[color-mix(in_srgb,_var(--color-trust-violated)_8%,_transparent)] border-b border-[var(--color-surface-border)]/50">
        {showLineNumbers && (
          <>
            <td className="w-10 px-2 py-0.5 text-right text-[var(--color-trust-violated)] select-none font-mono">
              {oldLineNumber}
            </td>
            <td className="w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] opacity-50 select-none"></td>
          </>
        )}
        <td className="w-6 px-2 py-0.5 text-center text-[var(--color-trust-violated)] select-none font-medium">
          <Minus size={12} />
        </td>
        <td className="px-3 py-0.5 whitespace-pre-wrap break-all text-[var(--color-trust-violated)]">
          {oldLine || ' '}
        </td>
      </tr>
    );
  }

  if (isChange) {
    return (
      <Fragment>
        <tr className="bg-[color-mix(in_srgb,_var(--color-trust-violated)_8%,_transparent)] border-b border-[var(--color-surface-border)]/50">
          {showLineNumbers && (
            <>
              <td className="w-10 px-2 py-0.5 text-right text-[var(--color-trust-violated)] select-none font-mono">
                {oldLineNumber}
              </td>
              <td className="w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] opacity-50 select-none"></td>
            </>
          )}
          <td className="w-6 px-2 py-0.5 text-center text-[var(--color-trust-violated)] select-none font-medium">
            <Minus size={12} />
          </td>
          <td className="px-3 py-0.5 whitespace-pre-wrap break-all text-[var(--color-trust-violated)]">
            {oldLine || ' '}
          </td>
        </tr>
        <tr className="bg-[color-mix(in_srgb,_var(--color-trust-certified)_8%,_transparent)] border-b border-[var(--color-surface-border)]/50">
          {showLineNumbers && (
            <>
              <td className="w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] opacity-50 select-none"></td>
              <td className="w-10 px-2 py-0.5 text-right text-[var(--color-trust-certified)] select-none font-mono">
                {newLineNumber}
              </td>
            </>
          )}
          <td className="w-6 px-2 py-0.5 text-center text-[var(--color-trust-certified)] select-none font-medium">
            <Plus size={12} />
          </td>
          <td className="px-3 py-0.5 whitespace-pre-wrap break-all text-[var(--color-trust-certified)]">
            {newLine || ' '}
          </td>
        </tr>
      </Fragment>
    );
  }

  // Context line
  return (
    <tr className="border-b border-[var(--color-surface-border)]/50">
      {showLineNumbers && (
        <>
          <td className="w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] opacity-50 select-none font-mono">
            {oldLineNumber}
          </td>
          <td className="w-10 px-2 py-0.5 text-right text-[var(--color-text-muted)] opacity-50 select-none font-mono">
            {newLineNumber}
          </td>
        </>
      )}
      <td className="w-6 px-2 py-0.5 text-center text-[var(--color-text-muted)] select-none">
        <span className="text-[var(--color-text-muted)]">·</span>
      </td>
      <td className="px-3 py-0.5 whitespace-pre-wrap break-all text-[var(--color-text-secondary)]">
        {oldLine || newLine || ' '}
      </td>
    </tr>
  );
}