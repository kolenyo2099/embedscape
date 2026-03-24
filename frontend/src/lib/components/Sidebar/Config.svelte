<script lang="ts">
	import {
		columns,
		columnConfig,
		embeddingConfig,
		rawData,
		isMediaMode,
		mediaType,
	} from "$lib/stores/data";
	import {
		isProcessing,
		processingProgress,
		processingMessage,
		addNotification,
	} from "$lib/stores/ui";
	import { createProgressSocket } from "$lib/api/client";

	let socket: WebSocket | null = null;

	$: hasText = $columnConfig.text && $columnConfig.text !== "";
	$: hasImage = $columnConfig.image && $columnConfig.image !== "";
	$: hasVideo = $columnConfig.video && $columnConfig.video !== "";

	// Auto-adjust mode based on selections (for non-media mode)
	$: if (!$isMediaMode) {
		if (hasText && !hasImage && !hasVideo) {
			$embeddingConfig.mode = "text";
			$embeddingConfig.source = "text";
		} else if (!hasText && hasImage) {
			$embeddingConfig.mode = "multimodal";
			$embeddingConfig.source = "image";
		} else if (!hasText && hasVideo) {
			$embeddingConfig.mode = "multimodal";
			$embeddingConfig.source = "video";
		}
	}

	// Auto-configure for media mode
	$: if ($isMediaMode) {
		$embeddingConfig.mode = "multimodal";
		if ($mediaType === "video") {
			$embeddingConfig.source = "video";
			$columnConfig.video = "__videoData";
			$columnConfig.image = "";
		} else if ($mediaType === "image") {
			$embeddingConfig.source = "image";
			$columnConfig.image = "__imageData";
			$columnConfig.video = "";
		} else if ($mediaType === "mixed") {
			// Smart mixed mode: detect per-row and embed accordingly
			$embeddingConfig.source = "mixed";
			$columnConfig.image = "__imageData";
			$columnConfig.video = "__videoData";
		}
		// Always use label column for filenames
		$columnConfig.label = "label";
	}

	async function startProcessing() {
		// For media mode, we don't need column validation
		if (
			!$isMediaMode &&
			!$columnConfig.text &&
			!$columnConfig.image &&
			!$columnConfig.video
		) {
			addNotification("error", "Select at least one column to embed");
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
				setTimeout(() => {
					isProcessing.set(false);
					fetchResults();
				}, 500);
			} else if (data.type === "error") {
				addNotification("error", data.message);
				isProcessing.set(false);
			}
		});

		// Start processing
		try {
			// Ensure all numeric fields are sent as numbers (form elements may return strings)
			const configToSend = {
				...$embeddingConfig,
				k_clusters: Number($embeddingConfig.k_clusters),
				batch_size: Number($embeddingConfig.batch_size),
				video_fps: Number($embeddingConfig.video_fps),
				video_max_frames: Number($embeddingConfig.video_max_frames),
			};

			const payload = {
				columns: $columnConfig,
				config: configToSend,
			};

			console.log(
				"Sending to /api/embeddings/generate:",
				JSON.stringify(payload, null, 2),
			);

			const response = await fetch("/api/embeddings/generate", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(payload),
			});

			if (!response.ok) {
				const err = await response.json();
				throw new Error(err.detail || "Processing failed");
			}
		} catch (err) {
			addNotification(
				"error",
				err instanceof Error ? err.message : "Processing failed",
			);
			isProcessing.set(false);
			socket?.close();
		}
	}

	async function fetchResults() {
		try {
			const response = await fetch("/api/embeddings/result");
			if (response.ok) {
				const data = await response.json();
				// Update stores with results
				const { setNodes } = await import("$lib/stores/data");
				const { bounds: boundsStore } = await import(
					"$lib/stores/data"
				);

				// Debug logging
				console.log("FetchResults - rawData count:", $rawData.length);
				console.log("FetchResults - columnConfig:", $columnConfig);
				console.log("FetchResults - first row sample:", $rawData[0]);

				setNodes(data.coords, data.clusters, $rawData, $columnConfig);
				boundsStore.set(data.bounds);

				addNotification(
					"success",
					`Generated ${data.count} embeddings`,
				);
			}
		} catch (err) {
			addNotification("error", "Failed to fetch results");
		}
		socket?.close();
	}
</script>

<div class="panel config-panel">
	<h2>2) Configure</h2>

	{#if $isMediaMode}
		<!-- Simplified Media Mode UI -->
		<div class="media-info">
			<span class="media-badge">
				{#if $mediaType === "image"}
					🖼️ Image Mode
				{:else if $mediaType === "video"}
					🎬 Video Mode
				{:else}
					🎞️ Mixed Media
				{/if}
			</span>
			<small>Filenames will be used as labels</small>
		</div>

		<div class="config-grid">
			<div class="field">
				<label for="image-model">CLIP Model</label>
				<select
					id="image-model"
					bind:value={$embeddingConfig.image_model}
				>
					<option value="openai/clip-vit-base-patch32"
						>CLIP ViT-Base (fast)</option
					>
					<option value="openai/clip-vit-large-patch14"
						>CLIP ViT-Large (better)</option
					>
				</select>
			</div>

			<div class="field">
				<label for="clusters">Clusters</label>
				<select id="clusters" bind:value={$embeddingConfig.k_clusters}>
					<option value={0}>Auto (detect)</option>
					{#each Array.from({ length: 19 }, (_, i) => i + 2) as k}
						<option value={k}>{k} clusters</option>
					{/each}
				</select>
			</div>
		</div>

		{#if $mediaType === "video" || $mediaType === "mixed"}
			<div class="divider"></div>
			<h3>Video Options</h3>
			<div class="config-grid">
				<div class="field">
					<label for="video-fps">Frames per second</label>
					<input
						type="number"
						id="video-fps"
						bind:value={$embeddingConfig.video_fps}
						min="0.1"
						max="30"
						step="0.1"
					/>
					<small class="hint"
						>Frames extracted per second of video</small
					>
				</div>

				<div class="field">
					<label for="video-max-frames">Max frames</label>
					<input
						type="number"
						id="video-max-frames"
						bind:value={$embeddingConfig.video_max_frames}
						min="1"
						max="100"
					/>
					<small class="hint"
						>Limit per video (prevents long processing)</small
					>
				</div>
			</div>
		{/if}
	{:else}
		<!-- Standard Column Selection Mode -->
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
				<select
					id="mode"
					bind:value={$embeddingConfig.mode}
					disabled={!hasText || (!hasImage && !hasVideo)}
				>
					<option value="text">Text only (MiniLM)</option>
					<option value="multimodal">Multimodal (CLIP)</option>
				</select>
			</div>

			{#if $embeddingConfig.mode === "multimodal"}
				<div class="field">
					<label for="source">Embed from</label>
					<select id="source" bind:value={$embeddingConfig.source}>
						<option value="text" disabled={!hasText}>Text</option>
						<option value="image" disabled={!hasImage}>Image</option
						>
						<option value="video" disabled={!hasVideo}>Video</option
						>
						<option value="both" disabled={!hasText || !hasImage}
							>Both</option
						>
					</select>
				</div>
			{/if}

			<div class="field">
				<label for="clusters-std">Clusters</label>
				<select
					id="clusters-std"
					bind:value={$embeddingConfig.k_clusters}
				>
					<option value={0}>Auto (detect)</option>
					{#each Array.from({ length: 19 }, (_, i) => i + 2) as k}
						<option value={k}>{k} clusters</option>
					{/each}
				</select>
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
	{/if}

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

	.media-info {
		background: #f0f9ff;
		border-left: 4px solid var(--berkeley-blue);
		padding: var(--spacing-sm) var(--spacing-md);
		border-radius: 4px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.media-badge {
		font-weight: 600;
		color: var(--berkeley-blue);
	}

	.media-info small {
		color: var(--text-secondary);
		font-size: 0.8rem;
	}

	h3 {
		font-size: 0.9rem;
		margin: 0;
		color: var(--text-secondary);
	}

	.hint {
		color: var(--text-secondary);
		font-size: 0.75rem;
		margin-top: 2px;
	}
</style>
