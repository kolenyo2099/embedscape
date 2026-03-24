<script lang="ts">
	import { createEventDispatcher, onDestroy } from "svelte";
	import { columnConfig, type Node } from "$lib/stores/data";
	import { codeApplications, qualitativeCodes } from "$lib/stores/coding";

	export let node: Node | null = null;
	export let show = false;

	const dispatch = createEventDispatcher();

	// Lazy loading state
	let mediaLoaded = false;
	let videoElement: HTMLVideoElement | null = null;
	let imageElement: HTMLImageElement | null = null;

	// Get codes applied to this node
	$: nodeCodes = node
		? $codeApplications
				.filter((a) => a.nodeId === node.id)
				.map((a) => $qualitativeCodes.find((c) => c.id === a.codeId))
				.filter((c) => c !== undefined)
		: [];

	function close() {
		// Cleanup media elements before closing
		cleanupMedia();
		dispatch("close");
	}

	function cleanupMedia() {
		// Pause and clear video if present
		if (videoElement) {
			videoElement.pause();
			videoElement.src = "";
			videoElement.load(); // Release resources
			videoElement = null;
		}

		// Clear image source
		if (imageElement) {
			imageElement.src = "";
			imageElement = null;
		}

		mediaLoaded = false;
	}

	// Cleanup on component destroy
	onDestroy(() => {
		cleanupMedia();
	});

	// Load media when modal is shown
	$: if (show && !mediaLoaded) {
		// Small delay to ensure modal is visible before loading media
		setTimeout(() => {
			mediaLoaded = true;
		}, 50);
	}

	// Reset when modal is hidden
	$: if (!show) {
		cleanupMedia();
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			close();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === "Escape") {
			close();
		}
	}

	// Helper to safely get a field value
	function getFieldValue(fieldName: string): string {
		if (!fieldName || !node?.data) return "";
		const val = node.data[fieldName];
		if (val === null || val === undefined || val === "") return "";
		return String(val);
	}

	// Internal media data (from direct uploads)
	$: internalImage = node?.data?.["__imageData"];
	$: internalVideo = node?.data?.["__videoData"];

	// Get display values - prioritize internal media if available
	$: label =
		node && $columnConfig.label ? getFieldValue($columnConfig.label) : "";
	$: displayLabel = label || `Item ${(node?.id ?? 0) + 1}`;
	$: text = node ? getFieldValue($columnConfig.text) : "";
	$: image = internalImage
		? String(internalImage)
		: node
			? getFieldValue($columnConfig.image)
			: "";
	$: video = internalVideo
		? String(internalVideo)
		: node
			? getFieldValue($columnConfig.video)
			: "";
	$: link = node ? getFieldValue($columnConfig.link) : "";
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show && node}
	<div
		class="modal-backdrop"
		on:click={handleBackdropClick}
		role="dialog"
		aria-modal="true"
	>
		<div class="modal-content">
			<button class="close-btn" on:click={close} aria-label="Close"
				>&times;</button
			>

			<h3 class="modal-title">{displayLabel}</h3>

			<div class="modal-body">
				<!-- Image preview -->
				{#if image && mediaLoaded}
					<div class="preview">
						<img
							bind:this={imageElement}
							src={image}
							alt="Preview"
						/>
						{#if !internalImage}
							<div class="caption small muted">
								Image from column <strong
									>{$columnConfig.image}</strong
								>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Video preview -->
				{#if video && mediaLoaded}
					<div class="preview">
						<video
							bind:this={videoElement}
							src={video}
							controls
							preload="metadata"
						>
							<track kind="captions" />
						</video>
						{#if !internalVideo}
							<div class="caption small muted">
								Video from column <strong
									>{$columnConfig.video}</strong
								>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Text content -->
				{#if text}
					<div class="text-box">
						{text}
					</div>
				{/if}

				<!-- Link -->
				{#if link}
					<p class="link-row">
						<strong>Link:</strong>
						<a href={link} target="_blank" rel="noopener noreferrer"
							>{link}</a
						>
					</p>
				{/if}

				{#if nodeCodes.length > 0}
					<div class="codes-section">
						<strong>Applied Codes:</strong>
						<div class="codes-list">
							{#each nodeCodes as code}
								{#if code}
									<span
										class="code-badge"
										style="background: {code.color}"
									>
										{code.name}
									</span>
								{/if}
							{/each}
						</div>
					</div>
				{/if}

				<!-- Tags (legacy) -->
				{#if node.tags && node.tags.size > 0}
					<div class="tags-section">
						<strong>Tags:</strong>
						<div class="tags-list">
							{#each Array.from(node.tags) as tag}
								<span class="tag-badge">{tag}</span>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Metadata -->
				<p class="meta small muted">
					Cluster <strong>{node.cluster}</strong> &bull; Index
					<strong>{node.id}</strong>
				</p>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: var(--spacing-md);
	}

	.modal-content {
		background: white;
		border-radius: 12px;
		max-width: 600px;
		width: 100%;
		max-height: 80vh;
		overflow-y: auto;
		position: relative;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
	}

	.close-btn {
		position: absolute;
		top: 12px;
		right: 16px;
		background: none;
		border: none;
		font-size: 2rem;
		cursor: pointer;
		color: var(--text-secondary);
		line-height: 1;
		padding: 0;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
	}

	.close-btn:hover {
		background: var(--bg-color);
		color: var(--text-primary);
	}

	.modal-title {
		margin: 0;
		padding: var(--spacing-lg);
		padding-right: 48px;
		border-bottom: 1px solid var(--border-color);
		font-size: 1.25rem;
		color: var(--berkeley-blue);
	}

	.modal-body {
		padding: var(--spacing-lg);
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.preview {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.preview img,
	.preview video {
		max-width: 100%;
		max-height: 300px;
		border-radius: 8px;
		object-fit: contain;
		background: #f0f0f0;
	}

	.caption {
		text-align: center;
	}

	.text-box {
		background: #f8fafc;
		border-left: 4px solid var(--berkeley-blue);
		padding: var(--spacing-md);
		border-radius: 4px;
		white-space: pre-wrap;
		word-break: break-word;
		max-height: 200px;
		overflow-y: auto;
		font-size: 0.95rem;
		line-height: 1.5;
	}

	.link-row {
		margin: 0;
	}

	.link-row a {
		color: var(--berkeley-blue);
		word-break: break-all;
	}

	.codes-section,
	.tags-section {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.codes-list,
	.tags-list {
		display: flex;
		flex-wrap: wrap;
		gap: var(--spacing-xs);
	}

	.code-badge {
		display: inline-block;
		padding: 4px 10px;
		border-radius: 16px;
		font-size: 0.8rem;
		color: white;
		font-weight: 500;
	}

	.tag-badge {
		display: inline-block;
		padding: 4px 10px;
		border-radius: 16px;
		font-size: 0.8rem;
		background: #666;
		color: white;
		font-weight: 500;
	}

	.meta {
		margin: 0;
		padding-top: var(--spacing-sm);
		border-top: 1px solid var(--border-color);
	}

	.small {
		font-size: 0.85rem;
	}

	.muted {
		color: var(--text-secondary);
	}
</style>
