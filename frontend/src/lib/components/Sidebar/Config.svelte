<script lang="ts">
	import { columns, columnConfig, embeddingConfig, rawData } from '$lib/stores/data';
	import { isProcessing, processingProgress, processingMessage, addNotification } from '$lib/stores/ui';
	import { createProgressSocket } from '$lib/api/client';

	let socket: WebSocket | null = null;

	$: hasText = $columnConfig.text && $columnConfig.text !== '';
	$: hasImage = $columnConfig.image && $columnConfig.image !== '';
	$: hasVideo = $columnConfig.video && $columnConfig.video !== '';

	// Auto-adjust mode based on selections
	$: {
		if (hasText && !hasImage && !hasVideo) {
			$embeddingConfig.mode = 'text';
			$embeddingConfig.source = 'text';
		} else if (!hasText && hasImage) {
			$embeddingConfig.mode = 'multimodal';
			$embeddingConfig.source = 'image';
		} else if (!hasText && hasVideo) {
			$embeddingConfig.mode = 'multimodal';
			$embeddingConfig.source = 'video';
		}
	}

	async function startProcessing() {
		if (!$columnConfig.text && !$columnConfig.image && !$columnConfig.video) {
			addNotification('error', 'Select at least one column to embed');
			return;
		}

		isProcessing.set(true);
		processingProgress.set(0);
		processingMessage.set('Starting...');

		// Connect to WebSocket for progress
		socket = createProgressSocket((data) => {
			if (data.type === 'progress') {
				processingProgress.set(data.progress * 100);
				processingMessage.set(data.message);
			} else if (data.type === 'complete') {
				processingProgress.set(100);
				processingMessage.set('Complete!');
				setTimeout(() => {
					isProcessing.set(false);
					fetchResults();
				}, 500);
			} else if (data.type === 'error') {
				addNotification('error', data.message);
				isProcessing.set(false);
			}
		});

		// Start processing
		try {
			const response = await fetch('/api/embeddings/generate', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					columns: $columnConfig,
					config: $embeddingConfig
				})
			});

			if (!response.ok) {
				const err = await response.json();
				throw new Error(err.detail || 'Processing failed');
			}
		} catch (err) {
			addNotification('error', err instanceof Error ? err.message : 'Processing failed');
			isProcessing.set(false);
			socket?.close();
		}
	}

	async function fetchResults() {
		try {
			const response = await fetch('/api/embeddings/result');
			if (response.ok) {
				const data = await response.json();
				// Update stores with results
				const { setNodes } = await import('$lib/stores/data');
				const { bounds: boundsStore } = await import('$lib/stores/data');

				setNodes(data.coords, data.clusters, $rawData, $columnConfig);
				boundsStore.set(data.bounds);

				addNotification('success', `Generated ${data.count} embeddings`);
			}
		} catch (err) {
			addNotification('error', 'Failed to fetch results');
		}
		socket?.close();
	}
</script>

<div class="panel config-panel">
	<h2>2) Configure</h2>

	<div class="config-grid">
		<div class="field">
			<label for="text-col">Text column</label>
			<select id="text-col" bind:value={$columnConfig.text}>
				<option value="">None</option>
				{#each $columns as col}
					<option value={col}>{col}</option>
				{/each}
			</select>
		</div>

		<div class="field">
			<label for="label-col">Label column</label>
			<select id="label-col" bind:value={$columnConfig.label}>
				<option value="">None</option>
				{#each $columns as col}
					<option value={col}>{col}</option>
				{/each}
			</select>
		</div>

		<div class="field">
			<label for="link-col">Link column</label>
			<select id="link-col" bind:value={$columnConfig.link}>
				<option value="">None</option>
				{#each $columns as col}
					<option value={col}>{col}</option>
				{/each}
			</select>
		</div>

		<div class="field">
			<label for="image-col">Image URL column</label>
			<select id="image-col" bind:value={$columnConfig.image}>
				<option value="">None</option>
				{#each $columns as col}
					<option value={col}>{col}</option>
				{/each}
			</select>
		</div>

		<div class="field">
			<label for="video-col">Video URL column</label>
			<select id="video-col" bind:value={$columnConfig.video}>
				<option value="">None</option>
				{#each $columns as col}
					<option value={col}>{col}</option>
				{/each}
			</select>
		</div>
	</div>

	<div class="divider"></div>

	<div class="config-grid">
		<div class="field">
			<label for="mode">Embedding mode</label>
			<select id="mode" bind:value={$embeddingConfig.mode} disabled={!hasText || (!hasImage && !hasVideo)}>
				<option value="text">Text only (MiniLM)</option>
				<option value="multimodal">Multimodal (CLIP)</option>
			</select>
		</div>

		{#if $embeddingConfig.mode === 'multimodal'}
			<div class="field">
				<label for="source">Embed from</label>
				<select id="source" bind:value={$embeddingConfig.source}>
					<option value="text" disabled={!hasText}>Text</option>
					<option value="image" disabled={!hasImage}>Image</option>
					<option value="video" disabled={!hasVideo}>Video</option>
					<option value="both" disabled={!hasText || !hasImage}>Both</option>
				</select>
			</div>
		{/if}

		<div class="field">
			<label for="clusters">Clusters (k)</label>
			<input
				type="number"
				id="clusters"
				bind:value={$embeddingConfig.k_clusters}
				min="2"
				max="20"
			/>
		</div>

		<div class="field">
			<label for="batch">Batch size</label>
			<input
				type="number"
				id="batch"
				bind:value={$embeddingConfig.batch_size}
				min="1"
				max="64"
			/>
		</div>
	</div>

	<button class="btn btn-primary process-btn" on:click={startProcessing}>
		⚙️ Process Embeddings
	</button>
</div>

<style>
	.config-panel {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.config-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--spacing-sm);
	}

	.field {
		display: flex;
		flex-direction: column;
	}

	.divider {
		height: 1px;
		background: var(--border-color);
		margin: var(--spacing-xs) 0;
	}

	.process-btn {
		width: 100%;
		margin-top: var(--spacing-sm);
	}
</style>
