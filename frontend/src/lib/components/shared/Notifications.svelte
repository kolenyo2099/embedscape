<script lang="ts">
	import { notifications, removeNotification } from '$lib/stores/ui';
	import { fly } from 'svelte/transition';
</script>

<div class="notifications-container">
	{#each $notifications as notification (notification.id)}
		<div
			class="notification {notification.type}"
			transition:fly={{ x: 300, duration: 300 }}
		>
			<span class="notification-icon">
				{#if notification.type === 'success'}✓
				{:else if notification.type === 'error'}✗
				{:else if notification.type === 'warning'}⚠
				{:else}ℹ
				{/if}
			</span>
			<span class="notification-message">{notification.message}</span>
			<button
				class="notification-close"
				on:click={() => removeNotification(notification.id)}
				aria-label="Dismiss"
			>
				&times;
			</button>
		</div>
	{/each}
</div>

<style>
	.notifications-container {
		position: fixed;
		top: var(--spacing-md);
		right: var(--spacing-md);
		z-index: 9999;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
		max-width: 400px;
	}

	.notification {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		border-radius: 6px;
		background: white;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		font-size: 0.9rem;
	}

	.notification.success {
		border-left: 4px solid var(--success-color);
	}

	.notification.error {
		border-left: 4px solid var(--danger-color);
	}

	.notification.warning {
		border-left: 4px solid var(--california-gold);
	}

	.notification.info {
		border-left: 4px solid var(--berkeley-blue);
	}

	.notification-icon {
		font-size: 1rem;
		font-weight: bold;
	}

	.notification.success .notification-icon { color: var(--success-color); }
	.notification.error .notification-icon { color: var(--danger-color); }
	.notification.warning .notification-icon { color: var(--california-gold); }
	.notification.info .notification-icon { color: var(--berkeley-blue); }

	.notification-message {
		flex: 1;
		color: var(--text-primary);
	}

	.notification-close {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		cursor: pointer;
		color: var(--text-secondary);
		font-size: 1.2rem;
		border-radius: 4px;
	}

	.notification-close:hover {
		background: var(--bg-color);
	}
</style>
