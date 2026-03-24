/**
 * Data stores for application state
 */
import { writable, derived } from 'svelte/store';

// Types
export interface DataRow {
	[key: string]: string | number | boolean;
}

export interface ColumnConfig {
	text: string;
	label: string;
	link: string;
	image: string;
	video: string;
}

export interface EmbeddingConfig {
	mode: 'text' | 'multimodal';
	source: 'text' | 'image' | 'video' | 'both' | 'mixed';
	model: string;
	image_model: string;
	batch_size: number;
	k_clusters: number;
	video_fps: number;
	video_max_frames: number;
}

export interface Node {
	id: number;
	position: [number, number];
	cluster: number;
	data: DataRow;
	tags: Set<string>;
}

export interface SearchMatch {
	index: number;
	similarity: number;
	cluster: number;
	coords: [number, number];
	data: DataRow;
}

export interface Bounds {
	min_x: number;
	min_y: number;
	max_x: number;
	max_y: number;
	center_x: number;
	center_y: number;
	span_x: number;
	span_y: number;
}

// Data stores
export const rawData = writable<DataRow[]>([]);
export const columns = writable<string[]>([]);
export const totalRows = writable<number>(0);

// Data wrangling state
export const editMode = writable<boolean>(false);
export const modifiedRows = writable<Set<number>>(new Set());

// Media upload mode tracking
export const isMediaMode = writable<boolean>(false);
export const mediaType = writable<'image' | 'video' | 'mixed' | null>(null);

// Column configuration - use empty string for "None" to match select element behavior
export const columnConfig = writable<ColumnConfig>({
	text: '',
	label: '',
	link: '',
	image: '',
	video: ''
});

// Embedding configuration
export const embeddingConfig = writable<EmbeddingConfig>({
	mode: 'text',
	source: 'text',
	model: 'all-MiniLM-L6-v2',
	image_model: 'openai/clip-vit-base-patch32',
	batch_size: 32,
	k_clusters: 0,  // 0 = auto-detect optimal clusters
	video_fps: 1.0,
	video_max_frames: 30
});

// Visualization data
export const nodes = writable<Node[]>([]);
export const coords = writable<[number, number][]>([]);
export const clusters = writable<number[]>([]);
export const bounds = writable<Bounds | null>(null);

// Selection and highlighting
export const selectedNodes = writable<Set<number>>(new Set());
export const highlightedNodes = writable<Set<number>>(new Set());
export const hoveredNode = writable<number | null>(null);

// Tags
export const allTags = writable<Map<string, Set<number>>>(new Map());
export const tagColors = writable<Record<string, string>>({});

// Search
export const searchResults = writable<SearchMatch[]>([]);
export const searchQuery = writable<string>('');

// Derived stores
export const hasData = derived(rawData, $data => $data.length > 0);
export const hasEmbeddings = derived(nodes, $nodes => $nodes.length > 0);

export const selectedCount = derived(selectedNodes, $selected => $selected.size);

export const visibleNodes = derived(
	[nodes, allTags],
	([$nodes, $tags]) => {
		// Filter logic can be added here for tag filtering
		return $nodes;
	}
);


// Actions
export async function clearData() {
	rawData.set([]);
	columns.set([]);
	totalRows.set(0);
	nodes.set([]);
	coords.set([]);
	clusters.set([]);
	bounds.set(null);
	selectedNodes.set(new Set());
	highlightedNodes.set(new Set());
	allTags.set(new Map());
	tagColors.set({});
	searchResults.set([]);
	isMediaMode.set(false);
	mediaType.set(null);

	// Clear backend
	try {
		const { clearData: clearBackendData, clearEmbeddings } = await import('$lib/api/client');
		await clearBackendData();
		await clearEmbeddings();
	} catch (e) {
		console.error('Failed to clear backend:', e);
	}
}


export function setNodes(
	coordsData: [number, number][],
	clustersData: number[],
	data: DataRow[],
	colConfig: ColumnConfig
) {
	const newNodes: Node[] = coordsData.map((pos, i) => ({
		id: i,
		position: pos,
		cluster: clustersData[i] || 0,
		data: data[i] || {},
		tags: new Set()
	}));

	nodes.set(newNodes);
	coords.set(coordsData);
	clusters.set(clustersData);
}

export function addTagToNodes(tagName: string, nodeIds: number[]) {
	allTags.update(tags => {
		if (!tags.has(tagName)) {
			tags.set(tagName, new Set());
		}
		nodeIds.forEach(id => tags.get(tagName)!.add(id));
		return new Map(tags);
	});

	nodes.update(nodeList => {
		nodeList.forEach(node => {
			if (nodeIds.includes(node.id)) {
				node.tags.add(tagName);
			}
		});
		return [...nodeList];
	});

	// Generate color if new
	tagColors.update(colors => {
		if (!colors[tagName]) {
			const palette = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
				'#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe'];
			colors[tagName] = palette[Object.keys(colors).length % palette.length];
		}
		return { ...colors };
	});
}

export function removeTagFromNodes(tagName: string, nodeIds: number[]) {
	allTags.update(tags => {
		if (tags.has(tagName)) {
			nodeIds.forEach(id => tags.get(tagName)!.delete(id));
			if (tags.get(tagName)!.size === 0) {
				tags.delete(tagName);
			}
		}
		return new Map(tags);
	});

	nodes.update(nodeList => {
		nodeList.forEach(node => {
			if (nodeIds.includes(node.id)) {
				node.tags.delete(tagName);
			}
		});
		return [...nodeList];
	});
}
