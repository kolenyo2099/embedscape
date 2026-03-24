<script lang="ts">
	import {
		isProcessing,
		processingProgress,
		processingMessage,
	} from "$lib/stores/ui";
	import { fade, fly } from "svelte/transition";

	function cancelProcessing() {
		// TODO: implement cancel via API, for now just hide UI
		isProcessing.set(false);
	}
</script>

<div class="progress-toast" in:fly={{ y: 20, duration: 300 }} out:fade>
	<div class="toast-header">
		<span class="processing-label">Processing...</span>
		<button class="cancel-btn" on:click={cancelProcessing}>Cancel</button>
	</div>

	<div class="progress-message" title={$processingMessage}>
		{$processingMessage || "Initializing..."}
	</div>

	<div class="progress-bar">
		<div
			class="progress-bar-fill"
			style="width: {$processingProgress}%"
		></div>
	</div>

	<div class="progress-stats">
		<span class="progress-percent">{Math.round($processingProgress)}%</span>
	</div>
</div>

<style>
	.progress-toast {
		position: fixed;
		bottom: 30px;
		right: 30px;
		width: 320px;
		background: white;
		padding: 16px;
		border-radius: 8px;
		box-shadow:
			0 10px 25px -5px rgba(0, 0, 0, 0.1),
			0 8px 10px -6px rgba(0, 0, 0, 0.1);
		z-index: 1000;
		border-left: 4px solid var(--berkeley-blue);
		display: flex;
		flex-direction: column;
		gap: 8px;
		font-family: var(--font-sans);
	}

	.toast-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.processing-label {
		font-weight: 600;
		color: var(--berkeley-blue);
		font-size: 0.9rem;
	}

	.cancel-btn {
		background: none;
		border: none;
		color: var(--text-secondary);
		font-size: 0.8rem;
		cursor: pointer;
		padding: 2px 6px;
		border-radius: 4px;
		transition: all 0.2s;
	}

	.cancel-btn:hover {
		background: #f1f5f9;
		color: #ef4444;
	}

	.progress-message {
		font-size: 0.85rem;
		color: var(--text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		line-height: 1.4;
	}

	.progress-bar {
		height: 6px;
		background: #e2e8f0;
		border-radius: 3px;
		overflow: hidden;
		width: 100%;
	}

	.progress-bar-fill {
		height: 100%;
		background: linear-gradient(
			90deg,
			var(--berkeley-blue),
			var(--founders-rock)
		);
		transition: width 0.3s ease;
	}

	.progress-stats {
		display: flex;
		justify-content: flex-end;
		font-size: 0.75rem;
		color: var(--text-secondary);
	}
</style>
