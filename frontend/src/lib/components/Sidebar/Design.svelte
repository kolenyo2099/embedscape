<script lang="ts">
    import { columns, rawData } from "$lib/stores/data";
    import {
        designConfig,
        getUniqueValues,
        generateColorMap,
        getNumericColumns,
    } from "$lib/stores/design";

    let isCollapsed = false;

    // Get columns for dropdowns
    $: allColumns = $columns.filter((c) => !c.startsWith("__"));
    $: numericColumns = getNumericColumns();

    // Color column unique values
    $: colorValues = $designConfig.colorColumn
        ? getUniqueValues($designConfig.colorColumn)
        : [];

    // Handle color column change - auto-generate colors
    function handleColorColumnChange(e: Event) {
        const col = (e.target as HTMLSelectElement).value;
        designConfig.update((cfg) => ({
            ...cfg,
            colorColumn: col,
            colorMap: col ? generateColorMap(col) : {},
        }));
    }

    // Handle individual color change
    function handleColorChange(value: string, color: string) {
        designConfig.update((cfg) => ({
            ...cfg,
            colorMap: { ...cfg.colorMap, [value]: color },
        }));
    }

    // Handle size mode change
    function handleSizeModeChange(mode: "fixed" | "column") {
        designConfig.update((cfg) => ({ ...cfg, sizeMode: mode }));
    }
</script>

<div class="panel design-panel" class:collapsed={isCollapsed}>
    <button class="panel-header" on:click={() => (isCollapsed = !isCollapsed)}>
        <h2>Design</h2>
        <span class="collapse-icon">{isCollapsed ? "▶" : "▼"}</span>
    </button>

    {#if !isCollapsed}
        <div class="panel-content">
            <!-- Node Size Section -->
            <div class="section">
                <h4>Node Size</h4>
                <div class="size-options">
                    <label class="radio-option">
                        <input
                            type="radio"
                            name="sizeMode"
                            value="fixed"
                            checked={$designConfig.sizeMode === "fixed"}
                            on:change={() => handleSizeModeChange("fixed")}
                        />
                        <span>Fixed</span>
                    </label>
                    {#if $designConfig.sizeMode === "fixed"}
                        <div class="slider-row">
                            <input
                                type="range"
                                min="2"
                                max="20"
                                bind:value={$designConfig.sizeFixed}
                            />
                            <span class="slider-value"
                                >{$designConfig.sizeFixed}</span
                            >
                        </div>
                    {/if}

                    <label class="radio-option">
                        <input
                            type="radio"
                            name="sizeMode"
                            value="column"
                            checked={$designConfig.sizeMode === "column"}
                            on:change={() => handleSizeModeChange("column")}
                        />
                        <span>By Column</span>
                    </label>
                    {#if $designConfig.sizeMode === "column"}
                        <select bind:value={$designConfig.sizeColumn}>
                            <option value="">Select column...</option>
                            {#each numericColumns as col}
                                <option value={col}>{col}</option>
                            {/each}
                        </select>
                        <div class="range-inputs">
                            <label>
                                Min: <input
                                    type="number"
                                    bind:value={$designConfig.sizeRange[0]}
                                    min="1"
                                    max="50"
                                />
                            </label>
                            <label>
                                Max: <input
                                    type="number"
                                    bind:value={$designConfig.sizeRange[1]}
                                    min="1"
                                    max="50"
                                />
                            </label>
                        </div>
                    {/if}
                </div>
            </div>

            <hr class="section-divider" />

            <!-- Node Color Section -->
            <div class="section">
                <h4>Node Color</h4>
                <select
                    on:change={handleColorColumnChange}
                    value={$designConfig.colorColumn}
                >
                    <option value="">No color mapping</option>
                    {#each allColumns as col}
                        <option value={col}>{col}</option>
                    {/each}
                </select>

                {#if colorValues.length > 0}
                    <div class="color-map">
                        {#each colorValues as value}
                            <div class="color-row">
                                <input
                                    type="color"
                                    value={$designConfig.colorMap[value] ||
                                        "#888888"}
                                    on:input={(e) =>
                                        handleColorChange(
                                            value,
                                            e.currentTarget.value,
                                        )}
                                />
                                <span class="color-label" title={value}>
                                    {value.length > 20
                                        ? value.substring(0, 20) + "..."
                                        : value}
                                </span>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>

            <hr class="section-divider" />

            <!-- Labels Section -->
            <div class="section">
                <label class="checkbox-option">
                    <input
                        type="checkbox"
                        bind:checked={$designConfig.showLabels}
                    />
                    <span>Show Labels</span>
                </label>
                {#if $designConfig.showLabels}
                    <select bind:value={$designConfig.labelColumn}>
                        <option value="">Select column...</option>
                        {#each allColumns as col}
                            <option value={col}>{col}</option>
                        {/each}
                    </select>
                {/if}
            </div>

            <hr class="section-divider" />

            <!-- Node Opacity Section -->
            <div class="section">
                <h4>Node Opacity</h4>
                <div class="size-options">
                    <label class="radio-option">
                        <input
                            type="radio"
                            name="opacityMode"
                            value="fixed"
                            checked={$designConfig.opacityMode === "fixed"}
                            on:change={() =>
                                designConfig.update((cfg) => ({
                                    ...cfg,
                                    opacityMode: "fixed",
                                }))}
                        />
                        <span>Fixed</span>
                    </label>
                    {#if $designConfig.opacityMode === "fixed"}
                        <div class="slider-row">
                            <input
                                type="range"
                                min="0.1"
                                max="1"
                                step="0.05"
                                bind:value={$designConfig.opacityFixed}
                            />
                            <span class="slider-value"
                                >{$designConfig.opacityFixed.toFixed(2)}</span
                            >
                        </div>
                    {/if}

                    <label class="radio-option">
                        <input
                            type="radio"
                            name="opacityMode"
                            value="column"
                            checked={$designConfig.opacityMode === "column"}
                            on:change={() =>
                                designConfig.update((cfg) => ({
                                    ...cfg,
                                    opacityMode: "column",
                                }))}
                        />
                        <span>By Column</span>
                    </label>
                    {#if $designConfig.opacityMode === "column"}
                        <select bind:value={$designConfig.opacityColumn}>
                            <option value="">Select column...</option>
                            {#each numericColumns as col}
                                <option value={col}>{col}</option>
                            {/each}
                        </select>
                        <div class="range-inputs">
                            <label>
                                Min: <input
                                    type="number"
                                    bind:value={$designConfig.opacityRange[0]}
                                    min="0"
                                    max="1"
                                    step="0.1"
                                />
                            </label>
                            <label>
                                Max: <input
                                    type="number"
                                    bind:value={$designConfig.opacityRange[1]}
                                    min="0"
                                    max="1"
                                    step="0.1"
                                />
                            </label>
                        </div>
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    .design-panel {
        display: flex;
        flex-direction: column;
    }

    .panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: none;
        border: none;
        width: 100%;
        padding: var(--spacing-sm) 0;
        cursor: pointer;
        text-align: left;
    }

    .panel-header h2 {
        margin: 0;
        font-size: 1rem;
    }

    .collapse-icon {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }

    .panel-content {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-lg);
        padding-top: var(--spacing-sm);
    }

    .section-divider {
        border: none;
        border-top: 1px solid var(--border-color);
        margin: 0;
        opacity: 0.5;
    }

    .section {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-xs);
    }

    .section h4 {
        margin: 0;
        font-size: 0.85rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .size-options {
        display: flex;
        flex-direction: column;
        gap: var(--spacing-xs);
    }

    .radio-option,
    .checkbox-option {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.9rem;
        cursor: pointer;
    }

    .slider-row {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        padding-left: 24px;
    }

    .slider-row input[type="range"] {
        flex: 1;
    }

    .slider-value {
        min-width: 24px;
        text-align: right;
        font-family: var(--font-mono);
        font-size: 0.85rem;
    }

    .range-inputs {
        display: flex;
        gap: var(--spacing-md);
        padding-left: 24px;
    }

    .range-inputs label {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 0.8rem;
    }

    .range-inputs input {
        width: 50px;
        padding: 2px 4px;
    }

    select {
        padding: var(--spacing-xs) var(--spacing-sm);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        font-size: 0.85rem;
    }

    .color-map {
        max-height: 150px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: var(--spacing-xs);
        background: #f8fafc;
        border-radius: 4px;
    }

    .color-row {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
    }

    .color-row input[type="color"] {
        width: 24px;
        height: 24px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        padding: 0;
    }

    .color-label {
        font-size: 0.8rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .collapsed .panel-content {
        display: none;
    }
</style>
