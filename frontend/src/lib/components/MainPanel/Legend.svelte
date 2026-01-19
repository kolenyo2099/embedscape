<script lang="ts">
    import { designConfig, getUniqueValues } from "$lib/stores/design";
    import { nodes } from "$lib/stores/data";

    // Color palette for clusters (must match Graph.svelte)
    const clusterColors: [number, number, number][] = [
        [230, 25, 75], // red
        [60, 180, 75], // green
        [255, 225, 25], // yellow
        [67, 99, 216], // blue
        [245, 130, 49], // orange
        [145, 30, 180], // purple
        [70, 240, 240], // cyan
        [240, 50, 230], // magenta
        [188, 246, 12], // lime
        [250, 190, 190], // pink
    ];

    function rgbToHex(r: number, g: number, b: number): string {
        return (
            "#" + [r, g, b].map((x) => x.toString(16).padStart(2, "0")).join("")
        );
    }

    $: colorColumn = $designConfig.colorColumn;
    $: colorMap = $designConfig.colorMap;
    $: colorValues = colorColumn ? getUniqueValues(colorColumn) : [];
    $: hasLegend = colorColumn && colorValues.length > 0;

    // Get color for a value - handles both custom color maps and cluster colors
    function getColorForValue(value: string): string {
        // Check custom color map first
        if (colorMap[value]) {
            return colorMap[value];
        }

        // For _cluster column, use cluster colors
        if (colorColumn === "_cluster") {
            const clusterIndex = parseInt(value);
            if (!isNaN(clusterIndex)) {
                const color =
                    clusterColors[clusterIndex % clusterColors.length];
                return rgbToHex(color[0], color[1], color[2]);
            }
        }

        return "#888888";
    }
</script>

{#if hasLegend}
    <div class="legend">
        <div class="legend-header">
            <span class="legend-title">Color: {colorColumn}</span>
        </div>
        <div class="legend-items">
            {#each colorValues.slice(0, 10) as value}
                <div class="legend-item">
                    <span
                        class="legend-color"
                        style="background-color: {getColorForValue(
                            String(value),
                        )}"
                    ></span>
                    <span class="legend-label" title={String(value)}>
                        {String(value).length > 15
                            ? String(value).substring(0, 15) + "..."
                            : String(value)}
                    </span>
                </div>
            {/each}
            {#if colorValues.length > 10}
                <div class="legend-item legend-more">
                    +{colorValues.length - 10} more
                </div>
            {/if}
        </div>
    </div>
{/if}

<style>
    .legend {
        position: absolute;
        bottom: var(--spacing-md);
        right: var(--spacing-md);
        background: rgba(255, 255, 255, 0.95);
        border-radius: 6px;
        padding: var(--spacing-sm);
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
        max-width: 180px;
        font-size: 0.8rem;
        z-index: 5;
    }

    .legend-header {
        padding-bottom: var(--spacing-xs);
        border-bottom: 1px solid var(--border-color);
        margin-bottom: var(--spacing-xs);
    }

    .legend-title {
        font-weight: 600;
        color: var(--text-secondary);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .legend-items {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .legend-color {
        width: 12px;
        height: 12px;
        border-radius: 3px;
        flex-shrink: 0;
        border: 1px solid rgba(0, 0, 0, 0.1);
    }

    .legend-label {
        color: var(--text-primary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .legend-more {
        color: var(--text-secondary);
        font-style: italic;
        font-size: 0.75rem;
    }
</style>
