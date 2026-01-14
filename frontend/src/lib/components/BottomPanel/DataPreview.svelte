<script lang="ts">
	import { rawData, columns, totalRows, highlightedNodes, selectedNodes, columnConfig } from '$lib/stores/data';
	import { showBottomPanel } from '$lib/stores/ui';

	let scrollContainer: HTMLDivElement;
	let visibleRange = { start: 0, end: 50 };
	const ROW_HEIGHT = 32;
	const BUFFER = 10;

	// Filter columns to display (hide internal ones)
	$: displayColumns = $columns.filter(c => !c.startsWith('__'));

	// Get display value for a cell
	function getCellValue(row: any, col: string): string {
		const val = row[col];
		if (val === null || val === undefined) return '';
		if (typeof val === 'string' && val.length > 100) {
			return val.substring(0, 100) + '...';
		}
		return String(val);
	}

	// Check if row is highlighted or selected
	function getRowClass(index: number): string {
		const classes: string[] = [];
		if ($highlightedNodes.has(index)) classes.push('highlighted');
		if ($selectedNodes.has(index)) classes.push('selected');
		return classes.join(' ');
	}

	// Virtual scrolling
	function handleScroll() {
		if (!scrollContainer) return;

		const scrollTop = scrollContainer.scrollTop;
		const containerHeight = scrollContainer.clientHeight;

		const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER);
		const end = Math.min($rawData.length, Math.ceil((scrollTop + containerHeight) / ROW_HEIGHT) + BUFFER);

		visibleRange = { start, end };
	}

	function togglePanel() {
		showBottomPanel.update(v => !v);
	}
</script>

<div class="data-preview">
	<div class="panel-header">
		<h3>Data Preview</h3>
		<div class="header-actions">
			<span class="muted small">{$totalRows.toLocaleString()} rows</span>
			<button class="minimize-btn" on:click={togglePanel} title="Minimize">−</button>
		</div>
	</div>

	<div class="table-container" bind:this={scrollContainer} on:scroll={handleScroll}>
		{#if $rawData.length === 0}
			<div class="empty-state">
				<p class="muted">No data loaded</p>
			</div>
		{:else}
			<table class="data-table">
				<thead>
					<tr>
						<th class="row-num">#</th>
						{#each displayColumns as col}
							<th class:active={col === $columnConfig.text || col === $columnConfig.label}>
								{col}
							</th>
						{/each}
					</tr>
				</thead>
				<tbody style="height: {$rawData.length * ROW_HEIGHT}px">
					<!-- Virtual rows with absolute positioning -->
					{#each $rawData.slice(visibleRange.start, visibleRange.end) as row, i}
						{@const index = visibleRange.start + i}
						<tr
							class={getRowClass(index)}
							style="position: absolute; top: {index * ROW_HEIGHT}px; width: 100%;"
						>
							<td class="row-num">{index + 1}</td>
							{#each displayColumns as col}
								<td title={getCellValue(row, col)}>{getCellValue(row, col)}</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</div>

<style>
	.data-preview {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-sm) var(--spacing-md);
		border-bottom: 1px solid var(--border-color);
		flex-shrink: 0;
	}

	.panel-header h3 {
		font-size: 0.9rem;
		margin: 0;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
	}

	.minimize-btn {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		cursor: pointer;
		font-size: 1.2rem;
		color: var(--text-secondary);
		border-radius: 4px;
	}

	.minimize-btn:hover {
		background: var(--bg-color);
	}

	.table-container {
		flex: 1;
		overflow: auto;
		position: relative;
	}

	.data-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8rem;
		table-layout: fixed;
	}

	.data-table thead {
		position: sticky;
		top: 0;
		z-index: 10;
		background: #f8fafc;
	}

	.data-table th {
		text-align: left;
		padding: var(--spacing-sm);
		border-bottom: 2px solid var(--border-color);
		font-weight: 600;
		color: var(--berkeley-blue);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 80px;
		max-width: 200px;
	}

	.data-table th.active {
		background: rgba(253, 181, 21, 0.2);
	}

	.data-table tbody {
		position: relative;
	}

	.data-table td {
		padding: var(--spacing-xs) var(--spacing-sm);
		border-bottom: 1px solid #f1f5f9;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 200px;
		height: 32px;
	}

	.data-table tr {
		display: flex;
	}

	.data-table th,
	.data-table td {
		flex: 1;
		min-width: 80px;
	}

	.row-num {
		flex: 0 0 50px !important;
		min-width: 50px !important;
		max-width: 50px !important;
		color: var(--text-secondary);
		font-family: var(--font-mono);
		font-size: 0.75rem;
	}

	.data-table tr.highlighted {
		background: rgba(255, 215, 0, 0.2) !important;
	}

	.data-table tr.selected {
		background: rgba(0, 255, 255, 0.15) !important;
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		padding: var(--spacing-xl);
	}
</style>
