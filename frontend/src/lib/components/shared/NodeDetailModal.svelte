<script lang="ts">
	import { createEventDispatcher } from "svelte";
	import { columnConfig, type Node } from "$lib/stores/data";
	import { codeApplications, qualitativeCodes } from "$lib/stores/coding";

	export let node: Node | null = null;
	export let show = false;

	const dispatch = createEventDispatcher();

	// Get codes applied to this node
	$: nodeCodes = node
		? $codeApplications
				.filter((a) => a.nodeId === node.id)
				.map((a) => $qualitativeCodes.find((c) => c.id === a.codeId))
				.filter((c) => c !== undefined)
		: [];

	function close() {
		dispatch("close");
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
		console.log(
			"getFieldValue called with:",
			fieldName,
			"length:",
			fieldName?.length,
		);
		if (!fieldName || !node?.data) {
			console.log("  -> Returning empty: no fieldName or no node.data");
			return "";
		}
		const val = node.data[fieldName];
		console.log("  -> Looking up node.data[" + fieldName + "]:", val);
		console.log("  -> fieldName in node.data?", fieldName in node.data);
		if (val === null || val === undefined || val === "") {
			console.log("  -> Returning empty: val is null/undefined/empty");
			return "";
		}
		console.log("  -> Returning:", String(val));
		return String(val);
	}

	// Get display values - only show if the column is configured AND has data
	$: label =
		node && $columnConfig.label ? getFieldValue($columnConfig.label) : "";
	$: displayLabel = label || `Item ${(node?.id ?? 0) + 1}`;
	$: text = node ? getFieldValue($columnConfig.text) : "";
	$: image = node ? getFieldValue($columnConfig.image) : "";
	$: video = node ? getFieldValue($columnConfig.video) : "";
	$: link = node ? getFieldValue($columnConfig.link) : "";

	// DEBUG: Log what we're working with
	$: if (node && show) {
		console.log("=== NodeDetailModal Debug ===");
		console.log("columnConfig:", $columnConfig);
		console.log("node.data:", node.data);
		console.log("node.data keys:", Object.keys(node.data || {}));
		console.log("Extracted values:", { text, label, image, video, link });
		console.log("============================");
	}
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
				{#if image}
					<div class="preview">
						<img src={image} alt="Preview" />
						<div class="caption small muted">
							Image from column <strong
								>{$columnConfig.image}</strong
							>
						</div>
					</div>
				{/if}

				<!-- Video preview -->
				{#if video}
					<div class="preview">
						<video src={video} controls>
							<track kind="captions" />
						</video>
						<div class="caption small muted">
							Video from column <strong
								>{$columnConfig.video}</strong
							>
						</div>
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
