<script lang="ts">
	import {
		searchQuery,
		searchResults,
		highlightedNodes,
		embeddingConfig,
		nodes,
		selectedNodes,
	} from "$lib/stores/data";
	import {
		queryType,
		searchThreshold,
		addNotification,
		viewState,
	} from "$lib/stores/ui";
	import { searchText, searchImage } from "$lib/api/client";

	let imageInput: HTMLInputElement;
	let isSearching = false;

	async function handleSearch() {
		if ($queryType === "text") {
			if (!$searchQuery.trim()) {
				addNotification("warning", "Enter a search query");
				return;
			}

			isSearching = true;
			try {
				const result = await searchText($searchQuery, $searchThreshold);
				if (result.data) {
					searchResults.set(result.data.matches);
					highlightedNodes.set(
						new Set(result.data.matches.map((m) => m.index)),
					);
					addNotification(
						"success",
						`Found ${result.data.total} matches`,
					);
				}
			} catch (err) {
				addNotification("error", "Search failed");
			} finally {
				isSearching = false;
			}
		} else {
			imageInput.click();
		}
	}

	async function handleImageSearch(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;

		// Convert to base64
		const reader = new FileReader();
		reader.onload = async () => {
			isSearching = true;
			try {
				const result = await searchImage(
					reader.result as string,
					$searchThreshold,
				);
				if (result.data) {
					searchResults.set(result.data.matches);
					highlightedNodes.set(
						new Set(result.data.matches.map((m) => m.index)),
					);
					addNotification(
						"success",
						`Found ${result.data.total} matches`,
					);
				}
			} catch (err) {
				addNotification("error", "Image search failed");
			} finally {
				isSearching = false;
			}
		};
		reader.readAsDataURL(file);
	}

	function clearSearch() {
		searchQuery.set("");
		searchResults.set([]);
		highlightedNodes.set(new Set());
	}

	function focusResult(index: number) {
		highlightedNodes.set(new Set([index]));
		selectedNodes.set(new Set([index])); // Also select the node to sync with data table

		// Zoom to the node
		const node = $nodes.find((n) => n.id === index);
		if (node) {
			viewState.set({
				target: [node.position[0], node.position[1], 0],
				zoom: 8, // Max zoom level to focus closely on the node
			});
		}
	}

	$: canImageSearch = $embeddingConfig.mode === "multimodal";
</script>

<div class="panel search-panel">
	<h2>Semantic Search</h2>

	<div class="search-controls">
		<div class="query-type-row">
			<label>
				<input type="radio" bind:group={$queryType} value="text" />
				Text
			</label>
			<label class:disabled={!canImageSearch}>
				<input
					type="radio"
					bind:group={$queryType}
					value="image"
					disabled={!canImageSearch}
				/>
				Image
			</label>
		</div>

		{#if $queryType === "text"}
			<input
				type="text"
				placeholder="e.g. a red dog"
				bind:value={$searchQuery}
				on:keypress={(e) => e.key === "Enter" && handleSearch()}
			/>
		{:else}
			<div class="image-search-hint">
				Click Search to upload an image query
			</div>
		{/if}

		<input
			type="file"
			bind:this={imageInput}
			accept="image/*"
			on:change={handleImageSearch}
			style="display: none"
		/>

		<div class="threshold-row">
			<label
				>Threshold: <span class="tag"
					>{$searchThreshold.toFixed(2)}</span
				></label
			>
			<input
				type="range"
				min="0"
				max="1"
				step="0.01"
				bind:value={$searchThreshold}
			/>
		</div>

		<div class="btn-row">
			<button
				class="btn btn-primary"
				on:click={handleSearch}
				disabled={isSearching}
			>
				{isSearching ? "Searching..." : "Search"}
			</button>
			<button class="btn btn-secondary" on:click={clearSearch}>
				Clear
			</button>
		</div>
	</div>

	{#if $searchResults.length > 0}
		<div class="results">
			<div class="results-header">
				Found {$searchResults.length} matches
			</div>
			<div class="results-list">
				{#each $searchResults.slice(0, 10) as match}
					<button
						class="result-item"
						on:click={() => focusResult(match.index)}
					>
						<span class="result-label"
							>{match.data?.label || `Node ${match.index}`}</span
						>
						<span class="result-sim"
							>{match.similarity.toFixed(3)}</span
						>
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	.search-panel {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.search-controls {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.query-type-row {
		display: flex;
		gap: var(--spacing-md);
	}

	.query-type-row label {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		cursor: pointer;
	}

	.query-type-row label.disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.image-search-hint {
		padding: var(--spacing-sm);
		background: #f8fafc;
		border-radius: 4px;
		text-align: center;
		color: var(--text-secondary);
		font-size: 0.9rem;
	}

	.threshold-row {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.threshold-row input[type="range"] {
		width: 100%;
	}

	.btn-row {
		display: flex;
		gap: var(--spacing-sm);
	}

	.btn-row .btn {
		flex: 1;
	}

	.results {
		border-top: 1px solid var(--border-color);
		padding-top: var(--spacing-md);
	}

	.results-header {
		font-size: 0.9rem;
		color: var(--text-secondary);
		margin-bottom: var(--spacing-sm);
	}

	.results-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
		max-height: 200px;
		overflow-y: auto;
	}

	.result-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-sm);
		background: #f8fafc;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		text-align: left;
		transition: background 0.15s;
	}

	.result-item:hover {
		background: #e8ecff;
	}

	.result-label {
		font-size: 0.9rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 180px;
	}

	.result-sim {
		font-size: 0.8rem;
		color: var(--text-secondary);
		font-family: var(--font-mono);
	}
</style>
