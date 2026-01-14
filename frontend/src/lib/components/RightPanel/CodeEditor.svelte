<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { codeContent, codeLanguage, addNotification } from '$lib/stores/ui';
	import { rawData, columns } from '$lib/stores/data';

	let editorContainer: HTMLDivElement;
	let editor: any = null;
	let monaco: any = null;

	const defaultPythonCode = `# Transform your data with Python
# Available variables:
#   - df: pandas DataFrame with your data
#   - np: numpy module

def transform(df):
    """
    Transform the DataFrame and return the result.

    Examples:
    - Filter: df[df['likes'] > 100]
    - New column: df['word_count'] = df['text'].str.split().str.len()
    - Aggregate: df.groupby('cluster').size()
    """
    return df
`;

	const defaultSQLCode = `-- Query your data with SQL
-- Table name: data

SELECT *
FROM data
WHERE likes > 100
ORDER BY likes DESC
LIMIT 10;
`;

	onMount(async () => {
		// Dynamic import Monaco
		try {
			const monacoLoader = await import('@monaco-editor/loader');
			monaco = await monacoLoader.default.init();

			editor = monaco.editor.create(editorContainer, {
				value: $codeContent || defaultPythonCode,
				language: $codeLanguage,
				theme: 'vs-dark',
				minimap: { enabled: false },
				fontSize: 13,
				fontFamily: 'SF Mono, Monaco, Inconsolata, monospace',
				lineNumbers: 'on',
				scrollBeyondLastLine: false,
				automaticLayout: true,
				tabSize: 4,
				wordWrap: 'on',
				padding: { top: 12 }
			});

			// Sync content back to store
			editor.onDidChangeModelContent(() => {
				codeContent.set(editor.getValue());
			});
		} catch (err) {
			console.error('Failed to load Monaco editor:', err);
		}
	});

	onDestroy(() => {
		if (editor) {
			editor.dispose();
		}
	});

	// Update language when changed
	$: if (editor && monaco) {
		monaco.editor.setModelLanguage(editor.getModel(), $codeLanguage);
		if ($codeLanguage === 'python' && !$codeContent.includes('def transform')) {
			editor.setValue(defaultPythonCode);
		} else if ($codeLanguage === 'sql' && !$codeContent.includes('SELECT')) {
			editor.setValue(defaultSQLCode);
		}
	}

	async function runCode() {
		// TODO: Send code to backend for execution
		addNotification('info', 'Code execution coming soon...');
	}

	function formatCode() {
		if (editor) {
			editor.getAction('editor.action.formatDocument')?.run();
		}
	}
</script>

<div class="code-editor">
	<div class="editor-header">
		<div class="header-left">
			<h3>Code Editor</h3>
			<select bind:value={$codeLanguage} class="lang-select">
				<option value="python">Python</option>
				<option value="sql">SQL</option>
			</select>
		</div>
		<div class="header-actions">
			<button class="btn btn-secondary btn-sm" on:click={formatCode}>
				Format
			</button>
			<button class="btn btn-primary btn-sm" on:click={runCode}>
				▶ Run
			</button>
		</div>
	</div>

	<div class="editor-container" bind:this={editorContainer}></div>

	<div class="editor-footer">
		<div class="footer-info">
			<span class="muted small">
				{#if $codeLanguage === 'python'}
					Use <code>df</code> to access your data as a pandas DataFrame
				{:else}
					Query the <code>data</code> table
				{/if}
			</span>
		</div>
	</div>
</div>

<style>
	.code-editor {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
	}

	.editor-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-sm) var(--spacing-md);
		border-bottom: 1px solid var(--border-color);
		background: #1e1e2e;
		flex-shrink: 0;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
	}

	.editor-header h3 {
		font-size: 0.9rem;
		margin: 0;
		color: #cdd6f4;
	}

	.lang-select {
		padding: 4px 8px;
		font-size: 0.8rem;
		background: #313244;
		color: #cdd6f4;
		border: 1px solid #45475a;
		border-radius: 4px;
	}

	.header-actions {
		display: flex;
		gap: var(--spacing-sm);
	}

	.btn-sm {
		padding: 4px 12px;
		font-size: 0.8rem;
	}

	.editor-container {
		flex: 1;
		min-height: 0;
	}

	.editor-footer {
		padding: var(--spacing-sm) var(--spacing-md);
		background: #1e1e2e;
		border-top: 1px solid #313244;
		flex-shrink: 0;
	}

	.footer-info {
		color: #6c7086;
		font-size: 0.8rem;
	}

	.footer-info code {
		background: #313244;
		padding: 2px 6px;
		border-radius: 3px;
		font-family: var(--font-mono);
		color: #cba6f7;
	}
</style>
