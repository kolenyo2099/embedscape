<script lang="ts">
	import {
		memos,
		qualitativeCodes,
		createMemo,
		updateMemo,
		deleteMemo,
		selectedMemoId,
		type Memo
	} from '$lib/stores/coding';
	import { selectedNodes } from '$lib/stores/data';
	import { addNotification } from '$lib/stores/ui';

	let newMemoTitle = '';
	let newMemoContent = '';
	let newMemoType: Memo['memoType'] = 'observational';
	let isCreating = false;
	let editingMemo: Memo | null = null;

	function handleCreateMemo() {
		if (!newMemoTitle.trim()) {
			addNotification('warning', 'Enter a memo title');
			return;
		}

		createMemo(
			newMemoTitle.trim(),
			newMemoContent,
			newMemoType,
			[],
			Array.from($selectedNodes)
		);

		addNotification('success', 'Memo created');
		newMemoTitle = '';
		newMemoContent = '';
		isCreating = false;
	}

	function handleDeleteMemo(memoId: string) {
		if (confirm('Delete this memo?')) {
			deleteMemo(memoId);
			addNotification('info', 'Memo deleted');
		}
	}

	function startEdit(memo: Memo) {
		editingMemo = { ...memo };
	}

	function saveEdit() {
		if (editingMemo) {
			updateMemo(editingMemo.id, {
				title: editingMemo.title,
				content: editingMemo.content,
				memoType: editingMemo.memoType
			});
			editingMemo = null;
			addNotification('success', 'Memo updated');
		}
	}

	function getMemoTypeIcon(type: Memo['memoType']): string {
		switch (type) {
			case 'theoretical': return '💡';
			case 'methodological': return '🔧';
			case 'observational': return '👁️';
			case 'analytical': return '📊';
		}
	}

	function getMemoTypeLabel(type: Memo['memoType']): string {
		switch (type) {
			case 'theoretical': return 'Theoretical';
			case 'methodological': return 'Methodological';
			case 'observational': return 'Observational';
			case 'analytical': return 'Analytical';
		}
	}

	function formatDate(date: Date): string {
		return new Date(date).toLocaleDateString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<div class="memo-panel">
	<div class="memo-header">
		<h4>📝 Research Memos</h4>
		<button class="btn-sm" on:click={() => isCreating = !isCreating}>
			{isCreating ? 'Cancel' : '+ New'}
		</button>
	</div>

	<!-- Create Memo Form -->
	{#if isCreating}
		<div class="create-memo-form">
			<input
				type="text"
				placeholder="Memo title..."
				bind:value={newMemoTitle}
			/>

			<select bind:value={newMemoType}>
				<option value="observational">👁️ Observational</option>
				<option value="theoretical">💡 Theoretical</option>
				<option value="methodological">🔧 Methodological</option>
				<option value="analytical">📊 Analytical</option>
			</select>

			<textarea
				placeholder="Write your memo..."
				bind:value={newMemoContent}
				rows="4"
			></textarea>

			{#if $selectedNodes.size > 0}
				<div class="linked-items muted small">
					Will be linked to {$selectedNodes.size} selected item(s)
				</div>
			{/if}

			<button class="btn btn-primary" on:click={handleCreateMemo}>
				Create Memo
			</button>
		</div>
	{/if}

	<!-- Memos List -->
	<div class="memos-list">
		{#if $memos.length === 0}
			<div class="no-memos muted small">
				No memos yet. Create one to capture your analytical thoughts.
			</div>
		{:else}
			{#each $memos as memo}
				<div
					class="memo-item"
					class:selected={$selectedMemoId === memo.id}
					on:click={() => selectedMemoId.set(memo.id)}
					on:keydown={(e) => e.key === 'Enter' && selectedMemoId.set(memo.id)}
					role="button"
					tabindex="0"
				>
					<div class="memo-item-header">
						<span class="memo-type" title={getMemoTypeLabel(memo.memoType)}>
							{getMemoTypeIcon(memo.memoType)}
						</span>
						<span class="memo-title">{memo.title}</span>
						<div class="memo-actions">
							<button class="action-btn" on:click|stopPropagation={() => startEdit(memo)}>
								✎
							</button>
							<button class="action-btn danger" on:click|stopPropagation={() => handleDeleteMemo(memo.id)}>
								×
							</button>
						</div>
					</div>

					{#if $selectedMemoId === memo.id}
						<div class="memo-content">
							<p>{memo.content || 'No content'}</p>

							{#if memo.linkedNodes.length > 0}
								<div class="memo-links">
									🔗 Linked to {memo.linkedNodes.length} item(s)
								</div>
							{/if}

							<div class="memo-date muted small">
								{formatDate(memo.createdAt)}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		{/if}
	</div>
</div>

<!-- Edit Modal -->
{#if editingMemo}
	<div class="modal-backdrop" on:click|self={() => editingMemo = null} on:keydown={(e) => e.key === 'Escape' && (editingMemo = null)} role="presentation">
		<div class="edit-modal">
			<h3>Edit Memo</h3>

			<label>
				Title
				<input type="text" bind:value={editingMemo.title} />
			</label>

			<label>
				Type
				<select bind:value={editingMemo.memoType}>
					<option value="observational">👁️ Observational</option>
					<option value="theoretical">💡 Theoretical</option>
					<option value="methodological">🔧 Methodological</option>
					<option value="analytical">📊 Analytical</option>
				</select>
			</label>

			<label>
				Content
				<textarea bind:value={editingMemo.content} rows="6"></textarea>
			</label>

			<div class="modal-actions">
				<button class="btn btn-secondary" on:click={() => editingMemo = null}>Cancel</button>
				<button class="btn btn-primary" on:click={saveEdit}>Save</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.memo-panel {
		border-top: 1px solid var(--border-color);
		padding-top: var(--spacing-md);
	}

	.memo-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--spacing-sm);
	}

	.memo-header h4 {
		margin: 0;
		font-size: 0.9rem;
		color: var(--berkeley-blue);
	}

	.btn-sm {
		padding: 4px 8px;
		font-size: 0.75rem;
		background: var(--berkeley-blue);
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}

	.btn-sm:hover {
		background: var(--primary-btn-hover);
	}

	.create-memo-form {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm);
		background: white;
		border-radius: 6px;
		margin-bottom: var(--spacing-sm);
	}

	.memos-list {
		max-height: 200px;
		overflow-y: auto;
	}

	.memo-item {
		padding: var(--spacing-sm);
		background: white;
		border-radius: 4px;
		margin-bottom: 4px;
		cursor: pointer;
		transition: background 0.15s;
	}

	.memo-item:hover {
		background: #f8fafc;
	}

	.memo-item.selected {
		background: #f0f9ff;
		border: 1px solid var(--berkeley-blue);
	}

	.memo-item-header {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
	}

	.memo-type {
		font-size: 0.9rem;
	}

	.memo-title {
		flex: 1;
		font-size: 0.85rem;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.memo-actions {
		display: flex;
		gap: 2px;
		opacity: 0;
	}

	.memo-item:hover .memo-actions {
		opacity: 1;
	}

	.action-btn {
		background: none;
		border: none;
		cursor: pointer;
		padding: 2px 4px;
		font-size: 0.8rem;
		color: var(--text-secondary);
		border-radius: 3px;
	}

	.action-btn:hover {
		background: var(--bg-color);
	}

	.action-btn.danger:hover {
		background: #fee2e2;
		color: #dc2626;
	}

	.memo-content {
		margin-top: var(--spacing-sm);
		padding-top: var(--spacing-sm);
		border-top: 1px solid var(--border-color);
	}

	.memo-content p {
		font-size: 0.85rem;
		line-height: 1.5;
		margin: 0 0 var(--spacing-sm) 0;
		white-space: pre-wrap;
	}

	.memo-links {
		font-size: 0.8rem;
		color: var(--text-secondary);
	}

	.memo-date {
		margin-top: var(--spacing-xs);
	}

	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.edit-modal {
		background: white;
		padding: var(--spacing-lg);
		border-radius: 8px;
		width: 90%;
		max-width: 500px;
	}

	.edit-modal h3 {
		margin: 0 0 var(--spacing-md) 0;
	}

	.edit-modal label {
		display: block;
		margin-bottom: var(--spacing-md);
	}

	.edit-modal input,
	.edit-modal select,
	.edit-modal textarea {
		width: 100%;
		margin-top: var(--spacing-xs);
	}

	.modal-actions {
		display: flex;
		gap: var(--spacing-sm);
		justify-content: flex-end;
		margin-top: var(--spacing-md);
	}

	.muted {
		color: var(--text-secondary);
	}

	.small {
		font-size: 0.85rem;
	}
</style>
