<script lang="ts">
	import { onMount } from "svelte";
	import Sidebar from "$lib/components/Sidebar/Sidebar.svelte";
	import Graph from "$lib/components/MainPanel/Graph.svelte";
	import DataPreview from "$lib/components/BottomPanel/DataPreview.svelte";
	import RightPanel from "$lib/components/RightPanel/RightPanel.svelte";
	import Modal from "$lib/components/shared/Modal.svelte";
	import NodeDetailModal from "$lib/components/shared/NodeDetailModal.svelte";
	import Notifications from "$lib/components/shared/Notifications.svelte";
	import {
		showBottomPanel,
		showRightPanel,
		modalOpen,
		modalContent,
	} from "$lib/stores/ui";
	import {
		hasData,
		hasEmbeddings,
		nodes,
		type Node,
		rawData,
		columns,
		totalRows,
		columnConfig,
		embeddingConfig,
		bounds,
	} from "$lib/stores/data";
	import {
		getAllData,
		getEmbeddingsStatus,
		getEmbeddingsResult,
	} from "$lib/api/client";
	import { setNodes } from "$lib/stores/data";

	// Panel toggle functions
	function toggleRightPanel() {
		showRightPanel.update((v) => !v);
	}

	function toggleBottomPanel() {
		showBottomPanel.update((v) => !v);
	}

	// Node detail modal state
	let showNodeModal = false;
	let selectedNodeForModal: Node | null = null;

	function handleNodeClick(event: CustomEvent<Node>) {
		selectedNodeForModal = event.detail;
		showNodeModal = true;
	}

	let bottomPanelHeight = 220;
	let rightPanelWidth = 380;
	let isDraggingBottom = false;
	let isDraggingRight = false;

	function handleBottomDrag(e: MouseEvent) {
		if (!isDraggingBottom) return;
		const container = document.querySelector(
			".main-content",
		) as HTMLElement;
		if (!container) return;
		const rect = container.getBoundingClientRect();
		const newHeight = rect.bottom - e.clientY;
		bottomPanelHeight = Math.max(100, Math.min(400, newHeight));
	}

	function handleRightDrag(e: MouseEvent) {
		if (!isDraggingRight) return;
		const container = document.querySelector(
			".content-area",
		) as HTMLElement;
		if (!container) return;
		const rect = container.getBoundingClientRect();
		const newWidth = rect.right - e.clientX;
		rightPanelWidth = Math.max(280, Math.min(600, newWidth));
	}

	function stopDrag() {
		isDraggingBottom = false;
		isDraggingRight = false;
	}

	onMount(() => {
		document.addEventListener("mousemove", (e) => {
			handleBottomDrag(e);
			handleRightDrag(e);
		});
		document.addEventListener("mouseup", stopDrag);

		// Restore session data
		(async () => {
			try {
				// 1. Get Data
				const dataRes = await getAllData();
				if (dataRes.data && dataRes.data.total_rows > 0) {
					rawData.set(dataRes.data.rows);
					columns.set(dataRes.data.columns);
					totalRows.set(dataRes.data.total_rows);

					// 2. Check Embedding Status
					const statusRes = await getEmbeddingsStatus();
					if (statusRes.data && statusRes.data.has_embeddings) {
						// Restore config
						if (statusRes.data.config) {
							// Map config back to stores if needed
							// embeddingConfig.set(statusRes.data.config);
						}

						// 3. Get Embeddings
						const resultRes = await getEmbeddingsResult();
						if (resultRes.data) {
							setNodes(
								resultRes.data.coords,
								resultRes.data.clusters,
								dataRes.data.rows, // Using FULL data
								$columnConfig, // Use current config or restored one
							);
							bounds.set(resultRes.data.bounds);
						}
					}
				}
			} catch (e) {
				console.log("No active session to restore");
			}
		})();

		return () => {
			document.removeEventListener("mouseup", stopDrag);
		};
	});
</script>

<div class="app-layout">
	<!-- Sidebar -->
	<aside class="sidebar">
		<Sidebar />
	</aside>

	<!-- Main Content Area -->
	<main class="main-content">
		<!-- Top Row: Graph + Code Editor -->
		<div
			class="content-area"
			style="--right-panel-width: {$showRightPanel
				? rightPanelWidth
				: 0}px"
		>
			<!-- Graph Panel (Main) -->
			<div class="graph-panel">
				<Graph on:nodeclick={handleNodeClick} />

				<!-- Floating Panel Toggle Toolbar -->
				<div class="panel-toggle-toolbar">
					<span class="toolbar-label">View:</span>
					<button
						class="toggle-btn"
						class:active={$showRightPanel}
						on:click={toggleRightPanel}
						title="Toggle Coding Panel"
					>
						Coding
					</button>
					<button
						class="toggle-btn"
						class:active={$showBottomPanel}
						on:click={toggleBottomPanel}
						title="Toggle Data Preview"
					>
						Preview
					</button>
				</div>
			</div>

			<!-- Right Panel: Qualitative Coding + Python Editor -->
			{#if $showRightPanel}
				<div
					class="resize-handle-right"
					on:mousedown={() => (isDraggingRight = true)}
					role="separator"
					aria-orientation="vertical"
					tabindex="0"
				></div>
				<div class="right-panel" style="width: {rightPanelWidth}px">
					<RightPanel />
				</div>
			{/if}
		</div>

		<!-- Bottom Panel: Data Preview -->
		{#if $showBottomPanel && $hasData}
			<div
				class="resize-handle-bottom"
				on:mousedown={() => (isDraggingBottom = true)}
				role="separator"
				aria-orientation="horizontal"
				tabindex="0"
			></div>
			<div class="bottom-panel" style="height: {bottomPanelHeight}px">
				<DataPreview />
			</div>
		{/if}
	</main>
</div>

<!-- Modal -->
{#if $modalOpen}
	<Modal on:close={() => modalOpen.set(false)}>
		{#if $modalContent}
			<svelte:component
				this={$modalContent.component}
				{...$modalContent.props}
			/>
		{/if}
	</Modal>
{/if}

<!-- Node Detail Modal -->
<NodeDetailModal
	node={selectedNodeForModal}
	show={showNodeModal}
	on:close={() => (showNodeModal = false)}
/>

<!-- Notifications -->
<Notifications />

<style>
	.app-layout {
		display: grid;
		grid-template-columns: var(--sidebar-width) 1fr;
		height: 100vh;
		overflow: hidden;
	}

	.sidebar {
		background: var(--panel-bg);
		border-right: 1px solid var(--border-color);
		overflow-y: auto;
		overflow-x: hidden;
	}

	.main-content {
		display: flex;
		flex-direction: column;
		min-height: 0;
		overflow: hidden;
	}

	.content-area {
		flex: 1;
		display: flex;
		min-height: 0;
		overflow: hidden;
	}

	.graph-panel {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		position: relative;
	}

	.right-panel {
		flex-shrink: 0;
		background: var(--panel-bg);
		border-left: 1px solid var(--border-color);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.bottom-panel {
		flex-shrink: 0;
		background: var(--panel-bg);
		border-top: 1px solid var(--border-color);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.resize-handle-right {
		width: 4px;
		cursor: col-resize;
		background: transparent;
		transition: background 0.2s;
	}

	.resize-handle-right:hover,
	.resize-handle-right:active {
		background: var(--berkeley-blue);
	}

	.resize-handle-bottom {
		height: 4px;
		cursor: row-resize;
		background: transparent;
		transition: background 0.2s;
	}

	.resize-handle-bottom:hover,
	.resize-handle-bottom:active {
		background: var(--berkeley-blue);
	}

	/* Floating Panel Toggle Toolbar */
	.panel-toggle-toolbar {
		position: absolute;
		top: 12px;
		right: 12px;
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 10px;
		background: white;
		border-radius: 6px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
		z-index: 10;
	}

	.toolbar-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-secondary);
	}

	.toggle-btn {
		padding: 4px 10px;
		font-size: 0.8rem;
		font-weight: 500;
		border: 1px solid var(--border-color);
		border-radius: 4px;
		background: #fff;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.15s;
	}

	.toggle-btn:hover {
		border-color: var(--berkeley-blue);
		color: var(--berkeley-blue);
	}

	.toggle-btn.active {
		background: var(--berkeley-blue);
		color: #fff;
		border-color: var(--berkeley-blue);
	}

	.toggle-btn.active:hover {
		background: #004280;
	}
</style>
