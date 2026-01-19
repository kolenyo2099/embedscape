<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { columns, rawData } from "$lib/stores/data";

    export let sourceColumn: string = "";

    const dispatch = createEventDispatcher();

    // Mode: 'delimiter' or 'regex'
    let mode: "delimiter" | "regex" = "delimiter";

    // Delimiter options
    const presetDelimiters = [
        { label: "Comma", value: "," },
        { label: "Tab", value: "\\t" },
        { label: "Space", value: " " },
        { label: "Semicolon", value: ";" },
        { label: "Pipe", value: "|" },
        { label: "Colon", value: ":" },
    ];
    let selectedDelimiter = ",";
    let customDelimiter = "";
    let useCustomDelimiter = false;

    // Regex options
    let regexPattern = "";
    let regexError = "";

    // Output options
    let newColumnPrefix = "";
    let keepOriginal = true;

    // Preview
    $: previewData = getPreviewData();
    $: effectivePattern = useCustomDelimiter
        ? customDelimiter
        : selectedDelimiter;
    $: displayColumns = $columns.filter((c) => !c.startsWith("__"));

    // Generate default prefix from source column
    $: if (sourceColumn && !newColumnPrefix) {
        newColumnPrefix = sourceColumn;
    }

    function getPreviewData(): { original: string; parts: string[] }[] {
        if (!sourceColumn) return [];

        const sampleRows = $rawData.slice(0, 3);
        return sampleRows.map((row) => {
            const value = String(row[sourceColumn] || "");
            let parts: string[] = [];

            if (mode === "delimiter") {
                const pattern = useCustomDelimiter
                    ? customDelimiter
                    : selectedDelimiter;
                if (pattern === "\\t") {
                    parts = value.split("\t");
                } else if (pattern === "\\n") {
                    parts = value.split("\n");
                } else if (pattern) {
                    parts = value.split(pattern);
                }
            } else {
                // Regex mode
                if (regexPattern) {
                    try {
                        const regex = new RegExp(regexPattern, "g");
                        if (regexPattern.includes("(")) {
                            // Has capture groups
                            const matches = [...value.matchAll(regex)];
                            if (matches.length > 0) {
                                parts = matches[0].slice(1); // Get capture groups
                            }
                        } else {
                            // No capture groups - use split
                            parts = value.split(regex);
                        }
                        regexError = "";
                    } catch (e: any) {
                        regexError = e.message;
                        parts = [];
                    }
                }
            }

            return {
                original:
                    value.length > 50 ? value.substring(0, 50) + "..." : value,
                parts: parts.map((p) => p.trim()),
            };
        });
    }

    function handleClose() {
        dispatch("close");
    }

    function handleBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) {
            handleClose();
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Escape") {
            handleClose();
        }
    }

    function handleApply() {
        const pattern = mode === "delimiter" ? effectivePattern : regexPattern;
        if (!sourceColumn || !pattern || !newColumnPrefix) return;

        dispatch("apply", {
            sourceColumn,
            mode,
            pattern,
            newColumnPrefix,
            keepOriginal,
        });
    }

    $: canApply =
        sourceColumn &&
        newColumnPrefix &&
        ((mode === "delimiter" && effectivePattern) ||
            (mode === "regex" && regexPattern && !regexError));
</script>

<svelte:window on:keydown={handleKeydown} />

<div
    class="modal-backdrop"
    on:click={handleBackdropClick}
    role="dialog"
    aria-modal="true"
>
    <div class="modal-content">
        <div class="modal-header">
            <h2>Split Column</h2>
            <button class="close-btn" on:click={handleClose} aria-label="Close">
                &times;
            </button>
        </div>

        <div class="modal-body">
            <!-- Source Column -->
            <div class="field">
                <label for="source-col">Source Column</label>
                <select id="source-col" bind:value={sourceColumn}>
                    <option value="">Select a column...</option>
                    {#each displayColumns as col}
                        <option value={col}>{col}</option>
                    {/each}
                </select>
            </div>

            <!-- Mode Toggle -->
            <div class="mode-toggle">
                <button
                    class="mode-btn"
                    class:active={mode === "delimiter"}
                    on:click={() => (mode = "delimiter")}
                >
                    Split by Delimiter
                </button>
                <button
                    class="mode-btn"
                    class:active={mode === "regex"}
                    on:click={() => (mode = "regex")}
                >
                    Extract with Regex
                </button>
            </div>

            <!-- Delimiter Mode -->
            {#if mode === "delimiter"}
                <div class="delimiter-section">
                    <label>Delimiter</label>
                    <div class="preset-buttons">
                        {#each presetDelimiters as preset}
                            <button
                                class="preset-btn"
                                class:active={!useCustomDelimiter &&
                                    selectedDelimiter === preset.value}
                                on:click={() => {
                                    useCustomDelimiter = false;
                                    selectedDelimiter = preset.value;
                                }}
                            >
                                {preset.label}
                            </button>
                        {/each}
                        <button
                            class="preset-btn"
                            class:active={useCustomDelimiter}
                            on:click={() => (useCustomDelimiter = true)}
                        >
                            Custom
                        </button>
                    </div>
                    {#if useCustomDelimiter}
                        <input
                            type="text"
                            class="custom-input"
                            placeholder="Enter custom delimiter..."
                            bind:value={customDelimiter}
                        />
                    {/if}
                </div>
            {:else}
                <!-- Regex Mode -->
                <div class="regex-section">
                    <label for="regex-pattern">Regex Pattern</label>
                    <input
                        id="regex-pattern"
                        type="text"
                        placeholder="e.g., (\d+)-(\d+) or \s+"
                        bind:value={regexPattern}
                        class:error={regexError}
                    />
                    {#if regexError}
                        <span class="error-text">{regexError}</span>
                    {/if}
                    <p class="help-text">
                        Use capture groups <code>()</code> to extract specific parts,
                        or provide a pattern to split on.
                    </p>
                </div>
            {/if}

            <!-- Output Options -->
            <div class="output-section">
                <div class="field">
                    <label for="prefix">New Column Prefix</label>
                    <input
                        id="prefix"
                        type="text"
                        placeholder="e.g., part"
                        bind:value={newColumnPrefix}
                    />
                    <p class="help-text">
                        Columns will be named: {newColumnPrefix}_1, {newColumnPrefix}_2,
                        etc.
                    </p>
                </div>

                <label class="checkbox-label">
                    <input type="checkbox" bind:checked={keepOriginal} />
                    <span>Keep original column</span>
                </label>
            </div>

            <!-- Preview -->
            {#if sourceColumn && previewData.length > 0}
                <div class="preview-section">
                    <label>Preview (first 3 rows)</label>
                    <div class="preview-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>Original</th>
                                    <th>→</th>
                                    <th>Split Result</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each previewData as row}
                                    <tr>
                                        <td class="original">{row.original}</td>
                                        <td class="arrow">→</td>
                                        <td class="parts">
                                            {#if row.parts.length > 0}
                                                {#each row.parts as part, i}
                                                    <span class="part"
                                                        >{part ||
                                                            "(empty)"}</span
                                                    >
                                                    {#if i < row.parts.length - 1}
                                                        <span class="separator"
                                                            >,</span
                                                        >
                                                    {/if}
                                                {/each}
                                            {:else}
                                                <span class="no-match"
                                                    >No match</span
                                                >
                                            {/if}
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                </div>
            {/if}
        </div>

        <div class="modal-footer">
            <button class="btn btn-secondary" on:click={handleClose}>
                Cancel
            </button>
            <button
                class="btn btn-primary"
                on:click={handleApply}
                disabled={!canApply}
            >
                Split Column
            </button>
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
        max-width: 550px;
        max-height: 85vh;
        width: 90%;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow:
            0 20px 25px -5px rgba(0, 0, 0, 0.1),
            0 10px 10px -5px rgba(0, 0, 0, 0.04);
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
        display: flex;
        flex-direction: column;
        gap: var(--spacing-md);
    }

    .modal-footer {
        display: flex;
        gap: var(--spacing-sm);
        justify-content: flex-end;
        padding: var(--spacing-md) var(--spacing-lg);
        border-top: 1px solid var(--border-color);
    }

    .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .field label {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--text-primary);
    }

    .field input,
    .field select {
        padding: var(--spacing-sm);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        font-size: 0.9rem;
    }

    .field input:focus,
    .field select:focus {
        outline: none;
        border-color: var(--berkeley-blue);
        box-shadow: 0 0 0 2px rgba(0, 50, 98, 0.1);
    }

    .mode-toggle {
        display: flex;
        gap: 2px;
        background: var(--bg-color);
        padding: 2px;
        border-radius: 6px;
    }

    .mode-btn {
        flex: 1;
        padding: var(--spacing-sm) var(--spacing-md);
        border: none;
        background: transparent;
        cursor: pointer;
        font-size: 0.85rem;
        border-radius: 4px;
        color: var(--text-secondary);
        transition: all 0.15s ease;
    }

    .mode-btn.active {
        background: white;
        color: var(--berkeley-blue);
        font-weight: 500;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .delimiter-section,
    .regex-section,
    .output-section {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-sm);
    }

    .delimiter-section label,
    .regex-section label,
    .output-section label {
        font-size: 0.85rem;
        font-weight: 500;
    }

    .preset-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }

    .preset-btn {
        padding: 6px 12px;
        border: 1px solid var(--border-color);
        background: white;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.8rem;
        transition: all 0.15s ease;
    }

    .preset-btn:hover {
        border-color: var(--berkeley-blue);
    }

    .preset-btn.active {
        background: var(--berkeley-blue);
        color: white;
        border-color: var(--berkeley-blue);
    }

    .custom-input {
        margin-top: var(--spacing-xs);
        padding: var(--spacing-sm);
        border: 1px solid var(--border-color);
        border-radius: 4px;
    }

    .regex-section input.error {
        border-color: #dc3545;
    }

    .error-text {
        color: #dc3545;
        font-size: 0.8rem;
    }

    .help-text {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin: 4px 0 0 0;
    }

    .help-text code {
        background: var(--bg-color);
        padding: 2px 4px;
        border-radius: 3px;
        font-family: var(--font-mono);
    }

    .checkbox-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem;
        cursor: pointer;
    }

    .checkbox-label input {
        cursor: pointer;
    }

    .preview-section {
        margin-top: var(--spacing-sm);
    }

    .preview-section label {
        display: block;
        margin-bottom: var(--spacing-sm);
        font-size: 0.85rem;
        font-weight: 500;
    }

    .preview-table {
        max-height: 150px;
        overflow: auto;
        border: 1px solid var(--border-color);
        border-radius: 4px;
    }

    .preview-table table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8rem;
    }

    .preview-table th,
    .preview-table td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid var(--border-color);
    }

    .preview-table th {
        background: var(--bg-color);
        font-weight: 500;
        position: sticky;
        top: 0;
    }

    .preview-table .original {
        max-width: 150px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        color: var(--text-secondary);
    }

    .preview-table .arrow {
        width: 30px;
        text-align: center;
        color: var(--text-secondary);
    }

    .preview-table .parts {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        align-items: center;
    }

    .part {
        background: rgba(0, 200, 200, 0.1);
        border: 1px solid rgba(0, 200, 200, 0.3);
        padding: 2px 6px;
        border-radius: 3px;
        font-family: var(--font-mono);
        font-size: 0.75rem;
    }

    .separator {
        color: var(--text-secondary);
    }

    .no-match {
        color: var(--text-secondary);
        font-style: italic;
    }

    .btn {
        padding: var(--spacing-sm) var(--spacing-md);
        border-radius: 4px;
        font-size: 0.9rem;
        cursor: pointer;
        border: none;
        transition: all 0.15s ease;
    }

    .btn-secondary {
        background: var(--bg-color);
        color: var(--text-primary);
    }

    .btn-secondary:hover {
        background: var(--border-color);
    }

    .btn-primary {
        background: var(--berkeley-blue);
        color: white;
    }

    .btn-primary:hover:not(:disabled) {
        background: #001e3d;
    }

    .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>
