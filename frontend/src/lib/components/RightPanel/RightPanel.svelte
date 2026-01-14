<script lang="ts">
	import CodeEditor from './CodeEditor.svelte';
	import QualitativeCoding from './QualitativeCoding.svelte';
	import { showRightPanel } from '$lib/stores/ui';

	type Tab = 'coding' | 'python';
	let activeTab: Tab = 'coding';
	let isCollapsed = false;
	let showPythonHelp = false;

	function toggleCollapse() {
		isCollapsed = !isCollapsed;
	}

	function closePanel() {
		showRightPanel.set(false);
	}

	function openPythonHelp() {
		showPythonHelp = true;
	}

	function closePythonHelp() {
		showPythonHelp = false;
	}
</script>

<div class="right-panel-container" class:collapsed={isCollapsed}>
	<div class="panel-header">
		<div class="tabs">
			<button
				class="tab"
				class:active={activeTab === 'coding'}
				on:click={() => activeTab = 'coding'}
			>
				Coding
			</button>
			<button
				class="tab"
				class:active={activeTab === 'python'}
				on:click={() => activeTab = 'python'}
			>
				Python
				<span class="help-btn" on:click|stopPropagation={openPythonHelp} title="What can I do here?">?</span>
			</button>
		</div>
		<div class="panel-controls">
			<button class="control-btn" on:click={toggleCollapse} title={isCollapsed ? 'Expand' : 'Collapse'}>
				{isCollapsed ? '◀' : '▶'}
			</button>
			<button class="control-btn" on:click={closePanel} title="Close panel">
				×
			</button>
		</div>
	</div>

	{#if !isCollapsed}
		<div class="panel-content">
			{#if activeTab === 'coding'}
				<QualitativeCoding />
			{:else}
				<CodeEditor />
			{/if}
		</div>
	{/if}
</div>

<!-- Python Help Modal -->
{#if showPythonHelp}
	<div class="help-modal-backdrop" on:click={closePythonHelp} role="dialog" aria-modal="true">
		<div class="help-modal" on:click|stopPropagation>
			<button class="close-btn" on:click={closePythonHelp}>&times;</button>
			<h3>Python Editor</h3>
			<div class="help-content">
				<p>Write Python code to analyze and transform your data. The following variables are available:</p>

				<div class="code-section">
					<h4>Available Variables</h4>
					<ul>
						<li><code>data</code> - List of all data rows (dictionaries)</li>
						<li><code>embeddings</code> - NumPy array of embeddings (N x D)</li>
						<li><code>coords</code> - 2D coordinates for visualization (N x 2)</li>
						<li><code>clusters</code> - Cluster assignments for each point</li>
						<li><code>selected</code> - Set of currently selected node indices</li>
					</ul>
				</div>

				<div class="code-section">
					<h4>Available Functions</h4>
					<ul>
						<li><code>highlight(indices)</code> - Highlight specific nodes on the graph</li>
						<li><code>select(indices)</code> - Select specific nodes</li>
						<li><code>filter(fn)</code> - Filter data by a predicate function</li>
						<li><code>export_csv(filename)</code> - Export selected data to CSV</li>
					</ul>
				</div>

				<div class="code-section">
					<h4>Example</h4>
					<pre><code># Find nodes with high similarity to first node
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

sims = cosine_similarity(embeddings[0:1], embeddings)[0]
top_10 = np.argsort(sims)[-10:]
highlight(top_10.tolist())</code></pre>
				</div>

				<div class="code-section">
					<h4>Libraries Available</h4>
					<p>numpy, pandas, sklearn, scipy</p>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.right-panel-container {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--panel-bg);
	}

	.right-panel-container.collapsed {
		width: 40px !important;
		min-width: 40px !important;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 var(--spacing-sm);
		border-bottom: 1px solid var(--border-color);
		background: #f8fafc;
		min-height: 40px;
		flex-shrink: 0;
	}

	.collapsed .panel-header {
		flex-direction: column;
		padding: var(--spacing-sm);
	}

	.tabs {
		display: flex;
		gap: 0;
	}

	.collapsed .tabs {
		display: none;
	}

	.tab {
		padding: var(--spacing-sm) var(--spacing-md);
		border: none;
		background: transparent;
		cursor: pointer;
		font-size: 0.85rem;
		font-weight: 500;
		color: var(--text-secondary);
		border-bottom: 2px solid transparent;
		transition: all 0.15s;
	}

	.tab:hover {
		color: var(--berkeley-blue);
		background: rgba(0, 50, 98, 0.05);
	}

	.tab.active {
		color: var(--berkeley-blue);
		border-bottom-color: var(--berkeley-blue);
	}

	.panel-controls {
		display: flex;
		gap: var(--spacing-xs);
	}

	.control-btn {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		cursor: pointer;
		color: var(--text-secondary);
		border-radius: 4px;
		font-size: 1rem;
	}

	.control-btn:hover {
		background: var(--bg-color);
		color: var(--text-primary);
	}

	.panel-content {
		flex: 1;
		min-height: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	/* Help button */
	.help-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		margin-left: 4px;
		font-size: 0.7rem;
		font-weight: 600;
		background: var(--berkeley-blue);
		color: white;
		border-radius: 50%;
		cursor: pointer;
		vertical-align: middle;
	}

	.help-btn:hover {
		background: #004280;
	}

	/* Help Modal */
	.help-modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 20px;
	}

	.help-modal {
		background: white;
		border-radius: 12px;
		max-width: 600px;
		width: 100%;
		max-height: 80vh;
		overflow-y: auto;
		position: relative;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
		padding: 24px;
	}

	.help-modal .close-btn {
		position: absolute;
		top: 12px;
		right: 16px;
		background: none;
		border: none;
		font-size: 1.5rem;
		cursor: pointer;
		color: var(--text-secondary);
		line-height: 1;
	}

	.help-modal .close-btn:hover {
		color: var(--text-primary);
	}

	.help-modal h3 {
		margin: 0 0 16px 0;
		color: var(--berkeley-blue);
		font-size: 1.25rem;
	}

	.help-content p {
		margin: 0 0 16px 0;
		color: var(--text-secondary);
	}

	.code-section {
		margin-bottom: 20px;
	}

	.code-section h4 {
		margin: 0 0 8px 0;
		font-size: 0.9rem;
		color: var(--text-primary);
	}

	.code-section ul {
		margin: 0;
		padding-left: 20px;
	}

	.code-section li {
		margin-bottom: 6px;
		font-size: 0.9rem;
	}

	.code-section code {
		background: #f0f4f8;
		padding: 2px 6px;
		border-radius: 3px;
		font-family: var(--font-mono);
		font-size: 0.85em;
	}

	.code-section pre {
		background: #1e1e1e;
		color: #d4d4d4;
		padding: 12px;
		border-radius: 6px;
		overflow-x: auto;
		margin: 0;
	}

	.code-section pre code {
		background: none;
		padding: 0;
		color: inherit;
	}
</style>
