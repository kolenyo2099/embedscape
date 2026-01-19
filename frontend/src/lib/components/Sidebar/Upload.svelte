<script lang="ts">
	import {
		rawData,
		columns,
		totalRows,
		clearData,
		hasEmbeddings,
	} from "$lib/stores/data";
	import { addNotification } from "$lib/stores/ui";
	import {
		uploadFile,
		uploadMedia,
		getAllData,
		loadSession,
		saveSession,
		clearEmbeddings,
	} from "$lib/api/client";

	let fileInput: HTMLInputElement;
	let sessionInput: HTMLInputElement;
	let mediaInput: HTMLInputElement;
	let isDragging = false;
	let isUploading = false;
	let isSaving = false;

	async function handleFileUpload(file: File) {
		if (!file) return;

		isUploading = true;
		try {
			// Clear old embeddings first
			await clearEmbeddings();

			const result = await uploadFile(file);
			// Fetch all data
			const allData = await getAllData();
			if (allData.data) {
				rawData.set(allData.data.rows);
				columns.set(allData.data.columns);
				totalRows.set(allData.data.total_rows);
			}

			addNotification(
				"success",
				`Loaded ${result.rows} rows from ${file.name}`,
			);
		} catch (err) {
			addNotification(
				"error",
				err instanceof Error ? err.message : "Upload failed",
			);
		} finally {
			isUploading = false;
		}
	}

	async function handleMediaUpload(files: FileList) {
		if (!files.length) return;

		isUploading = true;
		try {
			// Clear old embeddings first
			await clearEmbeddings();

			const result = await uploadMedia(Array.from(files));
			const allData = await getAllData();
			if (allData.data) {
				rawData.set(allData.data.rows);
				columns.set(allData.data.columns);
				totalRows.set(allData.data.total_rows);
			}
			addNotification("success", `Loaded ${result.count} media files`);
		} catch (err) {
			addNotification(
				"error",
				err instanceof Error ? err.message : "Upload failed",
			);
		} finally {
			isUploading = false;
		}
	}

	async function handleSessionLoad(file: File) {
		if (!file) return;

		isUploading = true;
		try {
			// Clear old embeddings first
			await clearEmbeddings();

			const result = await loadSession(file);
			const allData = await getAllData();
			if (allData.data) {
				rawData.set(allData.data.rows);
				columns.set(allData.data.columns);
				totalRows.set(allData.data.total_rows);
			}
			addNotification(
				"success",
				`Loaded session with ${result.rows} rows`,
			);
		} catch (err) {
			addNotification(
				"error",
				err instanceof Error ? err.message : "Load failed",
			);
		} finally {
			isUploading = false;
		}
	}

	async function handleSaveSession() {
		if (!$hasEmbeddings) {
			addNotification(
				"warning",
				"Process embeddings first before saving",
			);
			return;
		}
		isSaving = true;
		try {
			await saveSession();
			addNotification("success", "Session saved");
		} catch (err) {
			addNotification(
				"error",
				"Save failed - make sure embeddings are processed",
			);
		} finally {
			isSaving = false;
		}
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;

		const files = e.dataTransfer?.files;
		if (!files?.length) return;

		const file = files[0];
		if (file.name.endsWith(".json")) {
			handleSessionLoad(file);
		} else if (
			file.name.endsWith(".csv") ||
			file.name.endsWith(".ndjson") ||
			file.name.endsWith(".jsonl")
		) {
			handleFileUpload(file);
		} else if (
			file.type.startsWith("image/") ||
			file.type.startsWith("video/")
		) {
			handleMediaUpload(files);
		}
	}
</script>

<div class="panel upload-panel">
	<h2>Data</h2>

	{#if $totalRows === 0}
		<!-- Drop zone - only shown when no data loaded -->
		<div
			class="drop-zone"
			class:dragging={isDragging}
			on:dragover|preventDefault={() => (isDragging = true)}
			on:dragleave={() => (isDragging = false)}
			on:drop={handleDrop}
			on:click={() => fileInput.click()}
			role="button"
			tabindex="0"
		>
			{#if isUploading}
				<p>Uploading...</p>
			{:else}
				<p>📁 Drop file here or click to browse</p>
				<small>CSV, NDJSON, images, or videos</small>
			{/if}
		</div>
	{/if}

	<input
		type="file"
		bind:this={fileInput}
		accept=".csv,.ndjson,.jsonl"
		on:change={(e) =>
			e.currentTarget.files?.[0] &&
			handleFileUpload(e.currentTarget.files[0])}
		style="display: none"
	/>

	<input
		type="file"
		bind:this={mediaInput}
		accept="image/*,video/*"
		multiple
		on:change={(e) =>
			e.currentTarget.files && handleMediaUpload(e.currentTarget.files)}
		style="display: none"
	/>

	<input
		type="file"
		bind:this={sessionInput}
		accept=".json"
		on:change={(e) =>
			e.currentTarget.files?.[0] &&
			handleSessionLoad(e.currentTarget.files[0])}
		style="display: none"
	/>

	{#if $totalRows > 0}
		<!-- Compact view when data is loaded -->
		<div class="info-box">
			<strong>{$totalRows.toLocaleString()}</strong> rows loaded
			<button class="clear-btn" on:click={clearData}>Clear</button>
		</div>
	{/if}

	<!-- Session buttons -->
	<div class="btn-row">
		<button class="btn btn-secondary" on:click={() => sessionInput.click()}>
			Load Session
		</button>
		<button
			class="btn btn-primary"
			on:click={handleSaveSession}
			disabled={$totalRows === 0 || !$hasEmbeddings || isSaving}
			title={!$hasEmbeddings
				? "Process embeddings first"
				: "Save current session"}
		>
			{isSaving ? "Saving..." : "Save Session"}
		</button>
	</div>
</div>

<style>
	.upload-panel {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.drop-zone {
		border: 2px dashed var(--border-color);
		border-radius: 6px;
		padding: var(--spacing-lg);
		text-align: center;
		cursor: pointer;
		transition: all 0.2s;
		background: #f8fafc;
	}

	.drop-zone:hover,
	.drop-zone.dragging {
		border-color: var(--berkeley-blue);
		background: #f0f9ff;
	}

	.drop-zone p {
		margin-bottom: 4px;
		font-weight: 500;
		color: var(--berkeley-blue);
	}

	.drop-zone small {
		color: var(--text-secondary);
		font-size: 0.8rem;
	}

	.btn-row {
		display: flex;
		gap: var(--spacing-sm);
	}

	.btn-row .btn {
		flex: 1;
		font-size: 0.8rem;
		padding: var(--spacing-sm);
	}

	.info-box {
		background: #f0f9ff;
		border-left: 4px solid var(--berkeley-blue);
		padding: var(--spacing-sm) var(--spacing-md);
		border-radius: 4px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 0.9rem;
	}

	.clear-btn {
		background: none;
		border: none;
		color: var(--danger-color);
		cursor: pointer;
		font-size: 0.8rem;
		text-decoration: underline;
	}
</style>
