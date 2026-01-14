<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let title = '';

	const dispatch = createEventDispatcher();

	function handleClose() {
		dispatch('close');
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			handleClose();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			handleClose();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-backdrop" on:click={handleBackdropClick} role="dialog" aria-modal="true">
	<div class="modal-content">
		<div class="modal-header">
			{#if title}
				<h2>{title}</h2>
			{/if}
			<button class="close-btn" on:click={handleClose} aria-label="Close">
				&times;
			</button>
		</div>
		<div class="modal-body">
			<slot />
		</div>
	</div>
</div>

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 50, 98, 0.4);
		backdrop-filter: blur(2px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal-content {
		background: white;
		border-radius: 8px;
		max-width: 600px;
		max-height: 85vh;
		width: 90%;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
		border-top: 6px solid var(--berkeley-blue);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-md) var(--spacing-lg);
		border-bottom: 1px solid var(--border-color);
	}

	.modal-header h2 {
		margin: 0;
		font-size: 1.25rem;
	}

	.close-btn {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		cursor: pointer;
		font-size: 1.5rem;
		color: var(--text-secondary);
		border-radius: 4px;
		line-height: 1;
	}

	.close-btn:hover {
		background: var(--bg-color);
		color: var(--text-primary);
	}

	.modal-body {
		padding: var(--spacing-lg);
		overflow-y: auto;
	}
</style>
