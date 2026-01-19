import { writable, derived, get } from 'svelte/store';
import { columns, rawData } from './data';

export interface DesignConfig {
    // Size configuration
    sizeMode: 'fixed' | 'column';
    sizeFixed: number;
    sizeColumn: string;
    sizeRange: [number, number];

    // Color configuration
    colorColumn: string;
    colorMap: Record<string, string>; // value -> hex color

    // Opacity configuration
    opacityMode: 'fixed' | 'column';
    opacityFixed: number;
    opacityColumn: string;
    opacityRange: [number, number];

    // Labels
    showLabels: boolean;
    labelColumn: string;

    // Cluster outlines
    showClusterOutlines: boolean;
}

const defaultDesignConfig: DesignConfig = {
    sizeMode: 'fixed',
    sizeFixed: 6,
    sizeColumn: '',
    sizeRange: [3, 20],
    colorColumn: '_cluster',
    colorMap: {},
    opacityMode: 'fixed',
    opacityFixed: 1.0,
    opacityColumn: '',
    opacityRange: [0.2, 1.0],
    showLabels: false,
    labelColumn: '',
    showClusterOutlines: false
};

export const designConfig = writable<DesignConfig>(defaultDesignConfig);

// Default color palette for auto-assignment
const defaultPalette = [
    '#E53935', // red
    '#43A047', // green
    '#1E88E5', // blue
    '#FB8C00', // orange
    '#8E24AA', // purple
    '#00ACC1', // cyan
    '#FFB300', // amber
    '#5E35B1', // deep purple
    '#00897B', // teal
    '#D81B60', // pink
];

// Get unique values from a column
export function getUniqueValues(column: string): string[] {
    const data = get(rawData);
    if (!data || !column) return [];

    const values = new Set<string>();
    for (const row of data) {
        const val = row[column];
        if (val !== null && val !== undefined && val !== '') {
            values.add(String(val));
        }
    }
    return Array.from(values).sort();
}

// Auto-generate color map for a column
export function generateColorMap(column: string): Record<string, string> {
    const values = getUniqueValues(column);
    const colorMap: Record<string, string> = {};

    values.forEach((val, i) => {
        colorMap[val] = defaultPalette[i % defaultPalette.length];
    });

    return colorMap;
}

// Get numeric columns for size mapping
export function getNumericColumns(): string[] {
    const data = get(rawData);
    const cols = get(columns);
    if (!data || data.length === 0) return [];

    return cols.filter(col => {
        // Check first few rows to determine if column is numeric
        for (let i = 0; i < Math.min(5, data.length); i++) {
            const val = data[i][col];
            if (val !== null && val !== undefined && val !== '') {
                const num = Number(val);
                if (isNaN(num)) return false;
            }
        }
        return true;
    });
}

// Reset design config to defaults
export function resetDesignConfig() {
    designConfig.set(defaultDesignConfig);
}
