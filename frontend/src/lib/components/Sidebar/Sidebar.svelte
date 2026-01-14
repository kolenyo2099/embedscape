<script lang="ts">
	import Upload from './Upload.svelte';
	import Config from './Config.svelte';
	import Progress from './Progress.svelte';
	import Search from './Search.svelte';
	import { hasData, hasEmbeddings } from '$lib/stores/data';
	import { isProcessing } from '$lib/stores/ui';
</script>

<div class="sidebar-content">
	<header class="sidebar-header">
		<h1>EmbedScape</h1>
		<p class="tagline">Semantic visualization</p>
	</header>

	<div class="sidebar-panels">
		<!-- Upload Panel -->
		<Upload />

		<!-- Config Panel (shown after data loaded) -->
		{#if $hasData && !$isProcessing && !$hasEmbeddings}
			<Config />
		{/if}

		<!-- Progress Panel (shown during processing) -->
		{#if $isProcessing}
			<Progress />
		{/if}

		<!-- Search Panel (shown after embeddings) -->
		{#if $hasEmbeddings}
			<Search />
		{/if}
	</div>

	<footer class="sidebar-footer">
		<p class="muted small">All processing runs locally in your browser.</p>
	</footer>
</div>

<style>
	.sidebar-content {
		display: flex;
		flex-direction: column;
		height: 100%;
		padding: var(--spacing-md);
	}

	.sidebar-header {
		text-align: center;
		padding-bottom: var(--spacing-md);
		margin-bottom: var(--spacing-md);
		border-bottom: 2px solid var(--california-gold);
	}

	.sidebar-header h1 {
		font-size: 1.5rem;
		margin-bottom: 4px;
	}

	.tagline {
		font-family: var(--font-serif);
		font-style: italic;
		color: var(--text-secondary);
		font-size: 0.9rem;
	}

	.sidebar-panels {
		flex: 1;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.sidebar-footer {
		padding-top: var(--spacing-md);
		margin-top: var(--spacing-md);
		border-top: 1px solid var(--border-color);
		text-align: center;
	}
</style>
