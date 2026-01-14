<script lang="ts">
	import { isProcessing, processingProgress, processingMessage } from '$lib/stores/ui';

	function cancelProcessing() {
		// TODO: implement cancel via API
		isProcessing.set(false);
	}
</script>

<div class="panel progress-panel">
	<h2>Processing...</h2>

	<div class="progress-bar">
		<div class="progress-bar-fill" style="width: {$processingProgress}%"></div>
	</div>

	<div class="progress-info">
		<span class="progress-percent">{Math.round($processingProgress)}%</span>
		<span class="progress-message">{$processingMessage}</span>
	</div>

	<button class="btn btn-secondary" on:click={cancelProcessing}>
		Cancel
	</button>
</div>

<style>
	.progress-panel {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.progress-bar {
		height: 12px;
		background: #e2e8f0;
		border-radius: 6px;
		overflow: hidden;
	}

	.progress-bar-fill {
		height: 100%;
		background: linear-gradient(90deg, var(--berkeley-blue), var(--founders-rock));
		transition: width 0.3s ease;
	}

	.progress-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.9rem;
	}

	.progress-percent {
		font-weight: 600;
		color: var(--berkeley-blue);
	}

	.progress-message {
		color: var(--text-secondary);
	}
</style>
