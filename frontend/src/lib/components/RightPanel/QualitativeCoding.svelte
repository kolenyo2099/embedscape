<script lang="ts">
	import { selectedNodes, nodes, hoveredNode } from "$lib/stores/data";
	import {
		qualitativeCodes,
		codeApplications,
		codeHierarchy,
		codeFrequency,
		activeCodeId,
		createCode,
		applyCode,
		removeCodeFromNodes,
		deleteCode,
		updateCode,
		CODE_COLORS,
		exportCodingData,
		importCodingData,
		clearAllCodingData,
		type QualitativeCode,
	} from "$lib/stores/coding";
	import {
		addNotification,
		selectionEnabled,
		selectionTool,
		colorMode,
	} from "$lib/stores/ui";
	import CodeTree from "./CodeTree.svelte";
	import MemoPanel from "./MemoPanel.svelte";

	let newCodeName = "";
	let newCodeLevel: 1 | 2 | 3 = 1;
	let selectedParentId: string | null = null;
	let showMemos = false;
	let editingCode: QualitativeCode | null = null;

	// Compute stats
	$: totalApplications = Array.from($codeFrequency.values()).reduce(
		(a, b) => a + b,
		0,
	);

	function clearSelection() {
		selectedNodes.set(new Set());
	}

	function handleExport() {
		const data = exportCodingData();
		const blob = new Blob([data], { type: "application/json" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `coding-export-${new Date().toISOString().split("T")[0]}.json`;
		a.click();
		URL.revokeObjectURL(url);
		addNotification("success", "Coding data exported");
	}

	async function handleImport() {
		const input = document.createElement("input");
		input.type = "file";
		input.accept = ".json";
		input.onchange = async (e) => {
			const file = (e.target as HTMLInputElement).files?.[0];
			if (!file) return;
			try {
				const text = await file.text();
				if (importCodingData(text)) {
					addNotification("success", "Coding data imported");
				} else {
					addNotification("error", "Failed to import coding data");
				}
			} catch {
				addNotification("error", "Failed to read file");
			}
		};
		input.click();
	}

	function handleClearCoding() {
		if (confirm("Clear all coding data? This cannot be undone.")) {
			clearAllCodingData();
			addNotification("info", "All coding data cleared");
		}
	}

	// Get codes applied to currently selected or hovered node
	$: currentNodeId =
		$selectedNodes.size === 1
			? Array.from($selectedNodes)[0]
			: $hoveredNode;

	$: currentNodeCodes =
		currentNodeId !== null
			? $codeApplications
					.filter((a) => a.nodeId === currentNodeId)
					.map((a) =>
						$qualitativeCodes.find((c) => c.id === a.codeId),
					)
					.filter((c): c is QualitativeCode => c !== undefined)
			: [];

	$: currentNode =
		currentNodeId !== null
			? $nodes.find((n) => n.id === currentNodeId)
			: null;

	function handleCreateCode() {
		if (!newCodeName.trim()) {
			addNotification("warning", "Enter a code name");
			return;
		}

		const code = createCode(
			newCodeName.trim(),
			selectedParentId,
			newCodeLevel,
		);

		addNotification("success", `Created code: ${code.name}`);
		newCodeName = "";
		selectedParentId = null;
	}

	function handleApplyCode(codeId: string) {
		if ($selectedNodes.size === 0) {
			addNotification("warning", "Select nodes first");
			return;
		}

		applyCode(codeId, Array.from($selectedNodes));
		addNotification(
			"success",
			`Applied code to ${$selectedNodes.size} items`,
		);
	}

	function handleRemoveCode(codeId: string) {
		if ($selectedNodes.size === 0) {
			addNotification("warning", "Select nodes first");
			return;
		}

		removeCodeFromNodes(codeId, Array.from($selectedNodes));
		addNotification(
			"info",
			`Removed code from ${$selectedNodes.size} items`,
		);
	}

	function handleQuickApply() {
		if ($activeCodeId && $selectedNodes.size > 0) {
			handleApplyCode($activeCodeId);
		}
	}

	function handleDeleteCode(codeId: string) {
		const code = $qualitativeCodes.find((c) => c.id === codeId);
		if (
			code &&
			confirm(
				`Delete code "${code.name}"? This will remove all applications.`,
			)
		) {
			deleteCode(codeId);
			addNotification("info", `Deleted code: ${code.name}`);
		}
	}

	function startEditCode(code: QualitativeCode) {
		editingCode = { ...code };
	}

	function saveEditCode() {
		if (editingCode) {
			updateCode(editingCode.id, {
				name: editingCode.name,
				description: editingCode.description,
				color: editingCode.color,
			});
			editingCode = null;
		}
	}

	function setActiveCode(codeId: string) {
		activeCodeId.set($activeCodeId === codeId ? null : codeId);
	}

	// Get level label
	function getLevelLabel(level: 1 | 2 | 3): string {
		switch (level) {
			case 1:
				return "Theme";
			case 2:
				return "Category";
			case 3:
				return "Subcode";
		}
	}
</script>

<div class="qualitative-coding">
	<!-- Selection & Display Controls -->
	<div class="section controls-section">
		<div class="control-row">
			<div class="control-field">
				<label>Selection Mode</label>
				<button
					class="toggle-btn"
					class:active={$selectionEnabled}
					on:click={() => selectionEnabled.update((v) => !v)}
				>
					{$selectionEnabled ? "On" : "Off"}
				</button>
			</div>
		</div>

		<!-- Selection Tools (shown when selection is enabled) -->
		{#if $selectionEnabled}
			<div class="tool-row">
				<span class="tool-label">Tool:</span>
				<button
					class="tool-btn"
					class:active={$selectionTool === "pointer"}
					on:click={() => selectionTool.set("pointer")}
					title="Pointer - click to select/deselect"
				>
					<span class="tool-icon">👆</span>
					<span class="tool-name">Pointer</span>
				</button>
				<button
					class="tool-btn"
					class:active={$selectionTool === "rectangle"}
					on:click={() => selectionTool.set("rectangle")}
					title="Rectangle - drag to select area"
				>
					<span class="tool-icon">⬜</span>
					<span class="tool-name">Rectangle</span>
				</button>
				<button
					class="tool-btn"
					class:active={$selectionTool === "lasso"}
					on:click={() => selectionTool.set("lasso")}
					title="Lasso - draw to select area"
				>
					<span class="tool-icon">〰️</span>
					<span class="tool-name">Lasso</span>
				</button>
			</div>
		{/if}

		<div class="stats-row">
			<div class="stat">
				<span class="stat-value">{$qualitativeCodes.length}</span>
				<span class="stat-label">codes</span>
			</div>
			<div class="stat">
				<span class="stat-value">{totalApplications}</span>
				<span class="stat-label">applied</span>
			</div>
			<div class="coding-actions">
				<button class="btn-xs" on:click={handleExport} title="Export"
					>Export</button
				>
				<button class="btn-xs" on:click={handleImport} title="Import"
					>Import</button
				>
			</div>
		</div>
	</div>

	<!-- Current Selection Info -->
	<div class="section current-selection">
		<div class="section-header">
			<h4>Selection</h4>
			<span class="badge">{$selectedNodes.size} items</span>
			{#if $selectedNodes.size > 0}
				<button class="clear-btn" on:click={clearSelection}
					>Clear</button
				>
			{/if}
		</div>

		{#if currentNode}
			<div class="current-node-preview">
				<div class="node-label">
					{currentNode.data?.label || `Node ${currentNode.id}`}
				</div>
				{#if currentNodeCodes.length > 0}
					<div class="applied-codes">
						{#each currentNodeCodes as code}
							<span
								class="code-tag"
								style="background: {code.color}"
								title={code.description}
							>
								{code.name}
								<button
									class="remove-tag"
									on:click|stopPropagation={() =>
										handleRemoveCode(code.id)}>×</button
								>
							</span>
						{/each}
					</div>
				{:else}
					<div class="no-codes muted small">No codes applied</div>
				{/if}
			</div>
		{:else if $selectedNodes.size > 1}
			<div class="multi-select-info muted small">
				{$selectedNodes.size} items selected for bulk coding
			</div>
		{:else}
			<div class="no-selection muted small">
				Click on nodes to select them for coding
			</div>
		{/if}
	</div>

	<!-- Quick Apply -->
	{#if $activeCodeId}
		{@const activeCode = $qualitativeCodes.find(
			(c) => c.id === $activeCodeId,
		)}
		{#if activeCode}
			<div class="quick-apply">
				<span
					class="code-tag active"
					style="background: {activeCode.color}"
				>
					{activeCode.name}
				</span>
				<button
					class="btn btn-primary btn-sm"
					on:click={handleQuickApply}
					disabled={$selectedNodes.size === 0}
				>
					Apply to Selection
				</button>
				<button
					class="btn btn-secondary btn-sm"
					on:click={() => activeCodeId.set(null)}
				>
					Clear
				</button>
			</div>
		{/if}
	{/if}

	<!-- Code Tree -->
	<div class="section code-tree-section">
		<div class="section-header">
			<h4>Codes</h4>
			<button
				class="btn-icon"
				on:click={() => (showMemos = !showMemos)}
				title="Toggle Memos"
			>
				📝
			</button>
		</div>

		{#if $codeHierarchy.length === 0}
			<div class="empty-codes muted small">
				No codes yet. Create your first code below.
			</div>
		{:else}
			<div class="code-tree-container">
				<CodeTree
					codes={$codeHierarchy}
					frequency={$codeFrequency}
					activeCodeId={$activeCodeId}
					on:apply={(e) => handleApplyCode(e.detail)}
					on:remove={(e) => handleRemoveCode(e.detail)}
					on:delete={(e) => handleDeleteCode(e.detail)}
					on:edit={(e) => startEditCode(e.detail)}
					on:setActive={(e) => setActiveCode(e.detail)}
					on:setParent={(e) => (selectedParentId = e.detail)}
				/>
			</div>
		{/if}
	</div>

	<!-- Create Code -->
	<div class="section create-code">
		<div class="section-header">
			<h4>Create Code</h4>
		</div>

		<div class="create-form">
			<input
				type="text"
				placeholder="Code name..."
				bind:value={newCodeName}
				on:keypress={(e) => e.key === "Enter" && handleCreateCode()}
			/>

			<div class="create-options">
				<select bind:value={newCodeLevel}>
					<option value={1}>Theme (L1)</option>
					<option value={2}>Category (L2)</option>
					<option value={3}>Subcode (L3)</option>
				</select>

				{#if $qualitativeCodes.length > 0}
					<select bind:value={selectedParentId}>
						<option value={null}>No parent (root)</option>
						{#each $qualitativeCodes as code}
							<option value={code.id}>↳ {code.name}</option>
						{/each}
					</select>
				{/if}
			</div>

			<button class="btn btn-primary" on:click={handleCreateCode}>
				+ Create Code
			</button>
		</div>
	</div>

	<!-- Memos Panel (collapsible) -->
	{#if showMemos}
		<div class="section memos-section">
			<MemoPanel />
		</div>
	{/if}
</div>

<!-- Edit Code Modal -->
{#if editingCode}
	<div
		class="modal-backdrop"
		on:click|self={() => (editingCode = null)}
		on:keydown={(e) => e.key === "Escape" && (editingCode = null)}
		role="presentation"
	>
		<div class="edit-modal">
			<h3>Edit Code</h3>

			<label>
				Name
				<input type="text" bind:value={editingCode.name} />
			</label>

			<label>
				Description
				<textarea bind:value={editingCode.description} rows="3"
				></textarea>
			</label>

			<label>
				Color
				<div class="color-picker">
					{#each CODE_COLORS as color}
						<button
							class="color-swatch"
							class:selected={editingCode.color === color}
							style="background: {color}"
							on:click={() =>
								editingCode && (editingCode.color = color)}
						></button>
					{/each}
				</div>
			</label>

			<div class="modal-actions">
				<button
					class="btn btn-secondary"
					on:click={() => (editingCode = null)}>Cancel</button
				>
				<button class="btn btn-primary" on:click={saveEditCode}
					>Save</button
				>
			</div>
		</div>
	</div>
{/if}

<style>
	.qualitative-coding {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow-y: auto;
		padding: var(--spacing-md);
		gap: var(--spacing-md);
	}

	.section {
		background: #f8fafc;
		border-radius: 6px;
		padding: var(--spacing-md);
	}

	.controls-section {
		padding: var(--spacing-sm);
	}

	.control-row {
		display: flex;
		gap: var(--spacing-sm);
	}

	.control-field {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.control-field label {
		font-size: 0.7rem;
		color: var(--text-secondary);
		text-transform: uppercase;
	}

	.control-field select {
		padding: 4px 6px;
		font-size: 0.8rem;
	}

	.toggle-btn {
		padding: 4px 12px;
		font-size: 0.8rem;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
	}

	.toggle-btn.active {
		background: var(--berkeley-blue);
		color: white;
		border-color: var(--berkeley-blue);
	}

	.tool-row {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: var(--spacing-sm);
		padding-top: var(--spacing-sm);
		border-top: 1px solid var(--border-color);
	}

	.tool-label {
		font-size: 0.7rem;
		color: var(--text-secondary);
		text-transform: uppercase;
	}

	.tool-btn {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 4px 8px;
		font-size: 0.75rem;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
	}

	.tool-btn:hover {
		background: #f0f0f0;
	}

	.tool-btn.active {
		background: var(--california-gold);
		border-color: var(--california-gold);
		color: var(--berkeley-blue);
		font-weight: 500;
	}

	.tool-icon {
		font-size: 0.9rem;
	}

	.tool-name {
		font-size: 0.7rem;
	}

	.stats-row {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
		margin-top: var(--spacing-sm);
		padding-top: var(--spacing-sm);
		border-top: 1px solid var(--border-color);
	}

	.stat {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.stat-value {
		font-size: 1rem;
		font-weight: 600;
		color: var(--berkeley-blue);
	}

	.stat-label {
		font-size: 0.65rem;
		color: var(--text-secondary);
		text-transform: uppercase;
	}

	.coding-actions {
		display: flex;
		gap: 4px;
		margin-left: auto;
	}

	.btn-xs {
		padding: 2px 6px;
		font-size: 0.7rem;
		background: var(--berkeley-blue);
		color: white;
		border: none;
		border-radius: 3px;
		cursor: pointer;
	}

	.btn-xs:hover {
		opacity: 0.9;
	}

	.clear-btn {
		background: none;
		border: none;
		color: var(--danger-color);
		cursor: pointer;
		font-size: 0.75rem;
		text-decoration: underline;
		padding: 0;
	}

	.section-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		margin-bottom: var(--spacing-sm);
	}

	.section-header h4 {
		margin: 0;
		font-size: 0.9rem;
		color: var(--berkeley-blue);
	}

	.badge {
		background: var(--berkeley-blue);
		color: white;
		padding: 2px 8px;
		border-radius: 10px;
		font-size: 0.75rem;
	}

	.btn-icon {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 1rem;
		padding: 4px;
		border-radius: 4px;
	}

	.btn-icon:hover {
		background: rgba(0, 0, 0, 0.1);
	}

	.current-node-preview {
		margin-top: var(--spacing-sm);
	}

	.node-label {
		font-weight: 500;
		margin-bottom: var(--spacing-xs);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.applied-codes {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}

	.code-tag {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: 12px;
		font-size: 0.75rem;
		color: white;
		font-weight: 500;
	}

	.code-tag.active {
		box-shadow: 0 0 0 2px var(--california-gold);
	}

	.remove-tag {
		background: none;
		border: none;
		color: white;
		cursor: pointer;
		padding: 0;
		font-size: 0.9rem;
		line-height: 1;
		opacity: 0.7;
	}

	.remove-tag:hover {
		opacity: 1;
	}

	.quick-apply {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm);
		background: rgba(253, 181, 21, 0.1);
		border-radius: 6px;
		border: 1px solid var(--california-gold);
	}

	.code-tree-section {
		flex: 1;
		min-height: 150px;
		display: flex;
		flex-direction: column;
	}

	.code-tree-container {
		flex: 1;
		overflow-y: auto;
		max-height: 300px;
	}

	.create-form {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.create-options {
		display: flex;
		gap: var(--spacing-sm);
	}

	.create-options select {
		flex: 1;
		font-size: 0.85rem;
	}

	.btn-sm {
		padding: 4px 12px;
		font-size: 0.8rem;
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.edit-modal {
		background: white;
		padding: var(--spacing-lg);
		border-radius: 8px;
		width: 90%;
		max-width: 400px;
	}

	.edit-modal h3 {
		margin: 0 0 var(--spacing-md) 0;
	}

	.edit-modal label {
		display: block;
		margin-bottom: var(--spacing-md);
	}

	.edit-modal input,
	.edit-modal textarea {
		width: 100%;
		margin-top: var(--spacing-xs);
	}

	.color-picker {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: var(--spacing-xs);
	}

	.color-swatch {
		width: 24px;
		height: 24px;
		border-radius: 4px;
		border: 2px solid transparent;
		cursor: pointer;
	}

	.color-swatch.selected {
		border-color: var(--berkeley-blue);
	}

	.modal-actions {
		display: flex;
		gap: var(--spacing-sm);
		justify-content: flex-end;
		margin-top: var(--spacing-md);
	}

	.muted {
		color: var(--text-secondary);
	}

	.small {
		font-size: 0.85rem;
	}
</style>
