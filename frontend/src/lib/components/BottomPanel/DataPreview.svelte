<script lang="ts">
	import {
		rawData,
		columns,
		totalRows,
		highlightedNodes,
		selectedNodes,
		columnConfig,
		editMode,
		modifiedRows,
		embeddingConfig,
	} from "$lib/stores/data";
	import {
		showBottomPanel,
		addNotification,
		isProcessing,
		processingProgress,
		processingMessage,
		selectionEnabled,
	} from "$lib/stores/ui";
	import {
		updateRow,
		addColumn,
		splitColumn,
		generateSelectiveEmbeddings,
		getAllData,
		createProgressSocket,
	} from "$lib/api/client";
	import SplitColumnModal from "$lib/components/shared/SplitColumnModal.svelte";

	let scrollContainer: HTMLDivElement;
	let visibleRange = { start: 0, end: 50 };
	const ROW_HEIGHT = 32;
	const BUFFER = 10;

	// Edit state
	let editingCell: { row: number; col: string } | null = null;
	let editValue = "";

	// Add column modal
	let showAddColumnModal = false;
	let newColumnName = "";
	let newColumnDefault = "";

	// Split column modal
	let showSplitColumnModal = false;

	// Column resize state
	let columnWidths: Record<string, number> = {};
	let resizingColumn: string | null = null;
	let resizeStartX: number = 0;
	let resizeStartWidth: number = 0;

	// Reactive width getter that forces Svelte to track columnWidths
	$: getWidth = (col: string) => columnWidths[col] ?? 150;

	function startResize(e: MouseEvent, col: string) {
		e.preventDefault();
		e.stopPropagation();
		resizingColumn = col;
		resizeStartX = e.clientX;
		resizeStartWidth = columnWidths[col] ?? 150;

		const onMouseMove = (moveEvent: MouseEvent) => {
			if (!resizingColumn) return;
			const delta = moveEvent.clientX - resizeStartX;
			const newWidth = Math.max(60, resizeStartWidth + delta);
			columnWidths[resizingColumn] = newWidth;
			columnWidths = columnWidths; // Force reactivity
		};

		const onMouseUp = () => {
			resizingColumn = null;
			document.removeEventListener("mousemove", onMouseMove);
			document.removeEventListener("mouseup", onMouseUp);
		};

		document.addEventListener("mousemove", onMouseMove);
		document.addEventListener("mouseup", onMouseUp);
	}

	// Filter columns to display (hide internal ones)
	$: displayColumns = $columns.filter((c) => !c.startsWith("__"));

	// Filter data based on selection state
	// When selection mode is on and there are multiple selected rows, show only those
	// When single selection, show all but scroll to selected row
	// When no selection or selection off, show all rows
	$: filteredData = (() => {
		if ($selectionEnabled && $selectedNodes.size > 1) {
			// Show only selected rows
			return $rawData
				.map((row, idx) => ({ row, originalIndex: idx }))
				.filter(({ originalIndex }) =>
					$selectedNodes.has(originalIndex),
				);
		}
		// Show all rows with their original indices
		return $rawData.map((row, idx) => ({ row, originalIndex: idx }));
	})();

	// Auto-scroll to single selected row
	$: if ($selectionEnabled && $selectedNodes.size === 1 && scrollContainer) {
		const selectedIdx = Array.from($selectedNodes)[0];
		const scrollTop =
			selectedIdx * ROW_HEIGHT -
			scrollContainer.clientHeight / 2 +
			ROW_HEIGHT / 2;
		scrollContainer.scrollTo({
			top: Math.max(0, scrollTop),
			behavior: "smooth",
		});
	}

	// Get display value for a cell
	function getCellValue(row: any, col: string): string {
		const val = row[col];
		if (val === null || val === undefined) return "";
		if (typeof val === "string" && val.length > 100) {
			return val.substring(0, 100) + "...";
		}
		return String(val);
	}

	// Check if row is highlighted or selected
	function getRowClass(index: number): string {
		const classes: string[] = [];
		if ($highlightedNodes.has(index)) classes.push("highlighted");
		if ($selectedNodes.has(index)) classes.push("selected");
		if ($modifiedRows.has(index)) classes.push("modified");
		return classes.join(" ");
	}

	// Virtual scrolling
	function handleScroll() {
		if (!scrollContainer) return;

		const scrollTop = scrollContainer.scrollTop;
		const containerHeight = scrollContainer.clientHeight;

		const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER);
		const end = Math.min(
			$rawData.length,
			Math.ceil((scrollTop + containerHeight) / ROW_HEIGHT) + BUFFER,
		);

		visibleRange = { start, end };
	}

	function togglePanel() {
		showBottomPanel.update((v) => !v);
	}

	function toggleEditMode() {
		editMode.update((v) => !v);
		if (!$editMode) {
			editingCell = null;
		}
	}

	// Cell editing
	function startEdit(rowIndex: number, col: string, currentValue: string) {
		if (!$editMode) return;
		editingCell = { row: rowIndex, col };
		editValue = currentValue;
	}

	async function saveEdit() {
		if (!editingCell) return;

		const { row, col } = editingCell;
		const oldValue = $rawData[row]?.[col];

		if (editValue !== String(oldValue ?? "")) {
			try {
				const result = await updateRow(row, { [col]: editValue });
				if (result.data?.success) {
					// Update local data
					rawData.update((data) => {
						if (data[row]) {
							data[row][col] = editValue;
						}
						return data;
					});
					// Mark as modified
					modifiedRows.update((set) => {
						set.add(row);
						return new Set(set);
					});
				}
			} catch (err) {
				addNotification("error", "Failed to update cell");
			}
		}

		editingCell = null;
		editValue = "";
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === "Enter") {
			saveEdit();
		} else if (e.key === "Escape") {
			editingCell = null;
			editValue = "";
		}
	}

	// Add column
	async function handleAddColumn() {
		if (!newColumnName.trim()) {
			addNotification("error", "Column name is required");
			return;
		}

		try {
			const result = await addColumn(
				newColumnName.trim(),
				newColumnDefault,
			);
			if (result.data?.success) {
				// Refresh data
				const allData = await getAllData();
				if (allData.data) {
					rawData.set(allData.data.rows);
					columns.set(allData.data.columns);
				}
				addNotification("success", `Added column "${newColumnName}"`);
				showAddColumnModal = false;
				newColumnName = "";
				newColumnDefault = "";
			}
		} catch (err) {
			addNotification("error", "Failed to add column");
		}
	}

	// Split column
	async function handleSplitColumn(event: CustomEvent) {
		const { sourceColumn, mode, pattern, newColumnPrefix, keepOriginal } =
			event.detail;

		try {
			const result = await splitColumn(
				sourceColumn,
				mode,
				pattern,
				newColumnPrefix,
				keepOriginal,
			);
			if (result.data?.success) {
				// Refresh data
				const allData = await getAllData();
				if (allData.data) {
					rawData.set(allData.data.rows);
					columns.set(allData.data.columns);
				}
				const newCols = result.data.new_columns;
				addNotification(
					"success",
					`Created ${newCols.length} new column${newCols.length > 1 ? "s" : ""}: ${newCols.join(", ")}`,
				);
				showSplitColumnModal = false;
			} else if (result.error) {
				addNotification("error", result.error);
			}
		} catch (err) {
			addNotification("error", "Failed to split column");
		}
	}

	// Re-embed modified rows
	let socket: WebSocket | null = null;

	async function reembedModified() {
		if ($modifiedRows.size === 0) {
			addNotification("warning", "No modified rows to re-embed");
			return;
		}

		isProcessing.set(true);
		processingProgress.set(0);
		processingMessage.set("Starting...");

		// Connect to WebSocket for progress
		socket = createProgressSocket((data) => {
			if (data.type === "progress") {
				processingProgress.set(data.progress * 100);
				processingMessage.set(data.message);
			} else if (data.type === "complete") {
				processingProgress.set(100);
				processingMessage.set("Complete!");
				setTimeout(async () => {
					isProcessing.set(false);
					modifiedRows.set(new Set());
					// Refresh results
					const { setNodes } = await import("$lib/stores/data");
					const { bounds: boundsStore } = await import(
						"$lib/stores/data"
					);

					const response = await fetch("/api/embeddings/result");
					if (response.ok) {
						const data = await response.json();
						setNodes(
							data.coords,
							data.clusters,
							$rawData,
							$columnConfig,
						);
						boundsStore.set(data.bounds);
						addNotification("success", "Re-embedded modified rows");
					}
				}, 500);
			} else if (data.type === "error") {
				addNotification("error", data.message);
				isProcessing.set(false);
			}
		});

		try {
			await generateSelectiveEmbeddings(
				Array.from($modifiedRows),
				$columnConfig,
				$embeddingConfig,
			);
		} catch (err) {
			addNotification("error", "Re-embedding failed");
			isProcessing.set(false);
			socket?.close();
		}
	}
</script>

<div class="data-wrangling">
	<div class="panel-header">
		<h3>Data Wrangling</h3>
		<div class="header-actions">
			<label class="edit-toggle">
				<input
					type="checkbox"
					checked={$editMode}
					on:change={toggleEditMode}
				/>
				<span>Edit Mode</span>
			</label>
			<button
				class="btn btn-sm"
				on:click={() => (showAddColumnModal = true)}
			>
				+ Column
			</button>
			<button
				class="btn btn-sm"
				on:click={() => (showSplitColumnModal = true)}
				title="Split a column into multiple columns"
			>
				✂ Split
			</button>
			{#if $modifiedRows.size > 0}
				<span class="modified-badge">{$modifiedRows.size} modified</span
				>
				<button
					class="btn btn-sm btn-primary"
					on:click={reembedModified}
				>
					Re-embed
				</button>
			{/if}
			{#if $selectionEnabled && $selectedNodes.size > 1}
				<span class="selection-badge"
					>{$selectedNodes.size} selected</span
				>
			{/if}
			<span class="muted small">{$totalRows.toLocaleString()} rows</span>
			<button class="minimize-btn" on:click={togglePanel} title="Minimize"
				>−</button
			>
		</div>
	</div>

	<div
		class="table-container"
		bind:this={scrollContainer}
		on:scroll={handleScroll}
	>
		{#if $rawData.length === 0}
			<div class="empty-state">
				<p class="muted">No data loaded</p>
			</div>
		{:else}
			<table class="data-table">
				<thead>
					<tr>
						<th
							class="row-num"
							style="width: 50px; min-width: 50px;">#</th
						>
						{#each displayColumns as col}
							<th
								class:active={col === $columnConfig.text ||
									col === $columnConfig.label}
								style="width: {getWidth(
									col,
								)}px; min-width: 60px;"
							>
								<span class="th-content">{col}</span>
								<div
									class="resize-handle"
									on:mousedown={(e) => startResize(e, col)}
									role="separator"
									aria-orientation="vertical"
								></div>
							</th>
						{/each}
					</tr>
				</thead>
				{#if $selectionEnabled && $selectedNodes.size > 1}
					<!-- Filtered mode: show only selected rows without virtual scroll -->
					<tbody>
						{#each filteredData as { row, originalIndex }}
							<tr class={getRowClass(originalIndex)}>
								<td class="row-num" style="width: 50px;"
									>{originalIndex + 1}</td
								>
								{#each displayColumns as col}
									{@const isEditing =
										editingCell?.row === originalIndex &&
										editingCell?.col === col}
									<td
										title={getCellValue(row, col)}
										class:editing={isEditing}
										class:cell-modified={$modifiedRows.has(
											originalIndex,
										)}
										style="width: {getWidth(col)}px;"
										on:dblclick={() =>
											startEdit(
												originalIndex,
												col,
												String(row[col] ?? ""),
											)}
									>
										{#if isEditing}
											<input
												type="text"
												class="cell-input"
												bind:value={editValue}
												on:blur={saveEdit}
												on:keydown={handleKeydown}
												autofocus
											/>
										{:else}
											{getCellValue(row, col)}
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				{:else}
					<!-- Full mode: virtual scrolling -->
					<tbody style="height: {$rawData.length * ROW_HEIGHT}px">
						<!-- Virtual rows with absolute positioning -->
						{#each $rawData.slice(visibleRange.start, visibleRange.end) as row, i}
							{@const index = visibleRange.start + i}
							<tr
								class={getRowClass(index)}
								style="position: absolute; top: {index *
									ROW_HEIGHT}px; width: 100%;"
							>
								<td class="row-num" style="width: 50px;"
									>{index + 1}</td
								>
								{#each displayColumns as col}
									{@const isEditing =
										editingCell?.row === index &&
										editingCell?.col === col}
									<td
										title={getCellValue(row, col)}
										class:editing={isEditing}
										class:cell-modified={$modifiedRows.has(
											index,
										)}
										style="width: {getWidth(col)}px;"
										on:dblclick={() =>
											startEdit(
												index,
												col,
												String(row[col] ?? ""),
											)}
									>
										{#if isEditing}
											<input
												type="text"
												class="cell-input"
												bind:value={editValue}
												on:blur={saveEdit}
												on:keydown={handleKeydown}
												autofocus
											/>
										{:else}
											{getCellValue(row, col)}
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				{/if}
			</table>
		{/if}
	</div>
</div>

<!-- Add Column Modal -->
{#if showAddColumnModal}
	<div
		class="modal-backdrop"
		on:click|self={() => (showAddColumnModal = false)}
	>
		<div class="add-column-modal">
			<h4>Add New Column</h4>
			<div class="field">
				<label for="col-name">Column Name</label>
				<input
					type="text"
					id="col-name"
					bind:value={newColumnName}
					placeholder="e.g., Notes"
				/>
			</div>
			<div class="field">
				<label for="col-default">Default Value (optional)</label>
				<input
					type="text"
					id="col-default"
					bind:value={newColumnDefault}
					placeholder="e.g., empty"
				/>
			</div>
			<div class="modal-actions">
				<button
					class="btn btn-secondary"
					on:click={() => (showAddColumnModal = false)}
				>
					Cancel
				</button>
				<button class="btn btn-primary" on:click={handleAddColumn}>
					Add Column
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Split Column Modal -->
{#if showSplitColumnModal}
	<SplitColumnModal
		on:close={() => (showSplitColumnModal = false)}
		on:apply={handleSplitColumn}
	/>
{/if}

<style>
	.data-wrangling {
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

	.edit-toggle {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.edit-toggle input {
		cursor: pointer;
	}

	.btn-sm {
		font-size: 0.75rem;
		padding: 4px 8px;
	}

	.modified-badge {
		background: var(--warning-color);
		color: #000;
		padding: 2px 8px;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.selection-badge {
		background: rgba(0, 200, 200, 0.2);
		color: var(--berkeley-blue);
		border: 1px solid rgba(0, 200, 200, 0.5);
		padding: 2px 8px;
		border-radius: 12px;
		font-size: 0.75rem;
		font-weight: 600;
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
		position: relative;
	}

	.th-content {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.resize-handle {
		position: absolute;
		right: -2px;
		top: 0;
		bottom: 0;
		width: 8px;
		cursor: col-resize;
		background: transparent;
		transition: background 0.15s;
		z-index: 20;
	}

	.resize-handle:hover {
		background: var(--berkeley-blue);
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

	.data-table td.editing {
		padding: 0;
	}

	.cell-input {
		width: 100%;
		height: 100%;
		border: 2px solid var(--berkeley-blue);
		padding: var(--spacing-xs);
		font-size: inherit;
		font-family: inherit;
	}

	.data-table tr {
		display: flex;
	}

	.data-table th,
	.data-table td {
		flex: 0 0 auto;
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

	.data-table tr.modified {
		background: rgba(253, 181, 21, 0.1) !important;
	}

	.cell-modified {
		border-left: 3px solid var(--warning-color);
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		padding: var(--spacing-xl);
	}

	/* Add Column Modal */
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.add-column-modal {
		background: white;
		padding: var(--spacing-lg);
		border-radius: 8px;
		width: 300px;
		max-width: 90vw;
	}

	.add-column-modal h4 {
		margin: 0 0 var(--spacing-md) 0;
	}

	.field {
		margin-bottom: var(--spacing-md);
	}

	.field label {
		display: block;
		margin-bottom: 4px;
		font-size: 0.85rem;
		font-weight: 500;
	}

	.field input {
		width: 100%;
		padding: var(--spacing-sm);
		border: 1px solid var(--border-color);
		border-radius: 4px;
	}

	.modal-actions {
		display: flex;
		gap: var(--spacing-sm);
		justify-content: flex-end;
	}
</style>
