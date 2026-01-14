<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { QualitativeCode } from '$lib/stores/coding';

	export let codes: Array<QualitativeCode & { children: any[] }>;
	export let frequency: Map<string, number>;
	export let activeCodeId: string | null;
	export let depth = 0;

	const dispatch = createEventDispatcher();

	let expandedCodes = new Set<string>();

	function toggleExpand(codeId: string) {
		if (expandedCodes.has(codeId)) {
			expandedCodes.delete(codeId);
		} else {
			expandedCodes.add(codeId);
		}
		expandedCodes = expandedCodes; // Trigger reactivity
	}

	function handleApply(codeId: string) {
		dispatch('apply', codeId);
	}

	function handleRemove(codeId: string) {
		dispatch('remove', codeId);
	}

	function handleDelete(codeId: string) {
		dispatch('delete', codeId);
	}

	function handleEdit(code: QualitativeCode) {
		dispatch('edit', code);
	}

	function handleSetActive(codeId: string) {
		dispatch('setActive', codeId);
	}

	function handleSetParent(codeId: string) {
		dispatch('setParent', codeId);
	}

	function getLevelBadge(level: 1 | 2 | 3): string {
		switch (level) {
			case 1: return 'T';
			case 2: return 'C';
			case 3: return 'S';
		}
	}
</script>

<ul class="code-tree" style="--depth: {depth}">
	{#each codes as code}
		<li class="code-item" class:active={code.id === activeCodeId}>
			<div class="code-row">
				<!-- Expand/collapse toggle -->
				{#if code.children.length > 0}
					<button class="expand-toggle" on:click={() => toggleExpand(code.id)}>
						{expandedCodes.has(code.id) ? '▼' : '▶'}
					</button>
				{:else}
					<span class="expand-spacer"></span>
				{/if}

				<!-- Code color indicator -->
				<span class="code-color" style="background: {code.color}"></span>

				<!-- Code name -->
				<button
					class="code-name"
					on:click={() => handleSetActive(code.id)}
					on:dblclick={() => handleApply(code.id)}
					title="Click to set active, double-click to apply"
					type="button"
				>
					{code.name}
				</button>

				<!-- Level badge -->
				<span class="level-badge" title="Level {code.level}">
					{getLevelBadge(code.level)}
				</span>

				<!-- Frequency -->
				<span class="frequency" title="Used {frequency.get(code.id) || 0} times">
					({frequency.get(code.id) || 0})
				</span>

				<!-- Actions -->
				<div class="code-actions">
					<button
						class="action-btn"
						on:click={() => handleApply(code.id)}
						title="Apply to selection"
					>
						+
					</button>
					<button
						class="action-btn"
						on:click={() => handleSetParent(code.id)}
						title="Add child code"
					>
						↳
					</button>
					<button
						class="action-btn"
						on:click={() => handleEdit(code)}
						title="Edit code"
					>
						✎
					</button>
					<button
						class="action-btn danger"
						on:click={() => handleDelete(code.id)}
						title="Delete code"
					>
						×
					</button>
				</div>
			</div>

			<!-- Children -->
			{#if code.children.length > 0 && expandedCodes.has(code.id)}
				<svelte:self
					codes={code.children}
					{frequency}
					{activeCodeId}
					depth={depth + 1}
					on:apply
					on:remove
					on:delete
					on:edit
					on:setActive
					on:setParent
				/>
			{/if}
		</li>
	{/each}
</ul>

<style>
	.code-tree {
		list-style: none;
		margin: 0;
		padding: 0;
		padding-left: calc(var(--depth) * 16px);
	}

	.code-item {
		margin: 2px 0;
	}

	.code-item.active > .code-row {
		background: rgba(253, 181, 21, 0.2);
		border-radius: 4px;
	}

	.code-row {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 4px 6px;
		border-radius: 4px;
		transition: background 0.15s;
	}

	.code-row:hover {
		background: rgba(0, 50, 98, 0.05);
	}

	.expand-toggle {
		background: none;
		border: none;
		cursor: pointer;
		padding: 0;
		width: 16px;
		font-size: 0.7rem;
		color: var(--text-secondary);
	}

	.expand-spacer {
		width: 16px;
	}

	.code-color {
		width: 12px;
		height: 12px;
		border-radius: 3px;
		flex-shrink: 0;
	}

	.code-name {
		flex: 1;
		font-size: 0.85rem;
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		background: none;
		border: none;
		text-align: left;
		padding: 0;
		font-family: inherit;
		color: inherit;
	}

	.code-name:hover {
		text-decoration: underline;
	}

	.level-badge {
		font-size: 0.65rem;
		font-weight: bold;
		padding: 1px 4px;
		border-radius: 3px;
		background: var(--bg-color);
		color: var(--text-secondary);
	}

	.frequency {
		font-size: 0.75rem;
		color: var(--text-secondary);
		min-width: 24px;
	}

	.code-actions {
		display: flex;
		gap: 2px;
		opacity: 0;
		transition: opacity 0.15s;
	}

	.code-row:hover .code-actions {
		opacity: 1;
	}

	.action-btn {
		background: none;
		border: none;
		cursor: pointer;
		padding: 2px 4px;
		font-size: 0.8rem;
		color: var(--text-secondary);
		border-radius: 3px;
	}

	.action-btn:hover {
		background: var(--bg-color);
		color: var(--text-primary);
	}

	.action-btn.danger:hover {
		background: #fee2e2;
		color: #dc2626;
	}
</style>
