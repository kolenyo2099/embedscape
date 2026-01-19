/**
 * API client for backend communication
 */

const API_BASE = '/api';

interface ApiResponse<T> {
	data?: T;
	error?: string;
}

async function request<T>(
	endpoint: string,
	options: RequestInit = {}
): Promise<ApiResponse<T>> {
	try {
		const response = await fetch(`${API_BASE}${endpoint}`, {
			headers: {
				'Content-Type': 'application/json',
				...options.headers
			},
			...options
		});

		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			return { error: errorData.detail || `HTTP ${response.status}` };
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Request failed' };
	}
}

// Data endpoints
export async function uploadFile(file: File) {
	const formData = new FormData();
	formData.append('file', file);

	const response = await fetch(`${API_BASE}/data/upload`, {
		method: 'POST',
		body: formData
	});

	if (!response.ok) {
		const err = await response.json().catch(() => ({}));
		throw new Error(err.detail || 'Upload failed');
	}

	return response.json();
}

export async function uploadMedia(files: File[]) {
	const formData = new FormData();
	files.forEach(file => formData.append('files', file));

	const response = await fetch(`${API_BASE}/data/upload/media`, {
		method: 'POST',
		body: formData
	});

	if (!response.ok) {
		const err = await response.json().catch(() => ({}));
		throw new Error(err.detail || 'Upload failed');
	}

	return response.json();
}

export async function getPreview(limit = 100, offset = 0) {
	return request<{
		rows: Record<string, any>[];
		columns: string[];
		total_rows: number;
	}>(`/data/preview?limit=${limit}&offset=${offset}`);
}

export async function getAllData() {
	return request<{
		rows: Record<string, any>[];
		columns: string[];
		total_rows: number;
	}>('/data/all');
}

export async function getColumns() {
	return request<{
		columns: string[];
		suggested: Record<string, string>;
		total_rows: number;
	}>('/data/columns');
}

export async function clearData() {
	return request('/data/clear', { method: 'DELETE' });
}

export async function clearEmbeddings() {
	return request('/embeddings/clear', { method: 'DELETE' });
}

// Data wrangling endpoints
export async function updateRow(index: number, updates: Record<string, any>) {
	return request<{ success: boolean; index: number; modified_count: number }>(
		`/data/row/${index}`,
		{
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ updates })
		}
	);
}

export async function addColumn(name: string, defaultValue: string = '') {
	return request<{ success: boolean; column: string; total_columns: number }>(
		'/data/column',
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, default_value: defaultValue })
		}
	);
}

export async function splitColumn(
	sourceColumn: string,
	mode: 'delimiter' | 'regex',
	pattern: string,
	newColumnPrefix: string,
	keepOriginal: boolean = true
) {
	return request<{ success: boolean; new_columns: string[]; total_columns: number }>(
		'/data/column/split',
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				source_column: sourceColumn,
				mode,
				pattern,
				new_column_prefix: newColumnPrefix,
				keep_original: keepOriginal
			})
		}
	);
}

export async function getModifiedIndices() {
	return request<{ indices: number[]; count: number }>('/data/modified');
}

export async function clearModified() {
	return request('/data/modified/clear', { method: 'DELETE' });
}

export async function generateSelectiveEmbeddings(
	indices: number[],
	columns: ProcessRequest['columns'],
	config: ProcessRequest['config']
) {
	return request('/embeddings/generate/selective', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ indices, columns, config })
	});
}

// Embedding endpoints
export interface ProcessRequest {
	columns: {
		text: string | null;
		label: string | null;
		link: string | null;
		image: string | null;
		video: string | null;
	};
	config: {
		mode: 'text' | 'multimodal';
		source: 'text' | 'image' | 'video' | 'both';
		model: string;
		image_model: string;
		batch_size: number;
		k_clusters: number;
		video_fps: number;
		video_max_frames: number;
	};
}

export async function generateEmbeddings(processRequest: ProcessRequest) {
	return request<{ status: string; total_items: number }>(
		'/embeddings/generate',
		{ method: 'POST', body: JSON.stringify(processRequest) }
	);
}

export async function getEmbeddingsStatus() {
	return request<{
		processing: boolean;
		has_embeddings: boolean;
		count: number;
		config: any;
	}>('/embeddings/status');
}

export async function getEmbeddingsResult() {
	return request<{
		embeddings: number[][];
		coords: [number, number][];
		clusters: number[];
		bounds: any;
		count: number;
	}>('/embeddings/result');
}

export async function getCoords() {
	return request<{
		coords: [number, number][];
		clusters: number[];
		bounds: any;
	}>('/embeddings/coords');
}

// Search endpoints
export async function searchText(query: string, threshold = 0.7, topK = 100) {
	return request<{
		matches: any[];
		query: string;
		total: number;
	}>('/search/text', {
		method: 'POST',
		body: JSON.stringify({ query, threshold, top_k: topK })
	});
}

export async function searchImage(imageData: string, threshold = 0.7, topK = 100) {
	return request<{
		matches: any[];
		total: number;
	}>('/search/image', {
		method: 'POST',
		body: JSON.stringify({ image_data: imageData, threshold, top_k: topK })
	});
}

export async function findSimilar(index: number, threshold = 0.7, topK = 20) {
	return request<{
		matches: any[];
		source_index: number;
		total: number;
	}>(`/search/similar/${index}?threshold=${threshold}&top_k=${topK}`);
}

// Session endpoints
export async function saveSession() {
	const response = await fetch(`${API_BASE}/sessions/save`, {
		method: 'POST'
	});

	if (!response.ok) {
		throw new Error('Save failed');
	}

	// Download the file
	const blob = await response.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = `embedscape_session_${Date.now()}.json`;
	a.click();
	URL.revokeObjectURL(url);
}

export async function loadSession(file: File) {
	const formData = new FormData();
	formData.append('file', file);

	const response = await fetch(`${API_BASE}/sessions/load`, {
		method: 'POST',
		body: formData
	});

	if (!response.ok) {
		const err = await response.json().catch(() => ({}));
		throw new Error(err.detail || 'Load failed');
	}

	return response.json();
}

export async function getTags() {
	return request<{
		tags: Record<string, number[]>;
		colors: Record<string, string>;
	}>('/sessions/tags');
}

export async function addTag(tagName: string, nodeIds: number[]) {
	return request(`/sessions/tags/add?tag_name=${encodeURIComponent(tagName)}`, {
		method: 'POST',
		body: JSON.stringify(nodeIds)
	});
}

export async function removeTag(tagName: string, nodeIds: number[]) {
	return request(`/sessions/tags/remove?tag_name=${encodeURIComponent(tagName)}`, {
		method: 'POST',
		body: JSON.stringify(nodeIds)
	});
}

// WebSocket connection
export function createProgressSocket(
	onProgress: (data: any) => void,
	onError?: (error: Event) => void
): WebSocket {
	const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
	const ws = new WebSocket(`${protocol}//${window.location.host}/ws/progress`);

	ws.onmessage = (event) => {
		// Ignore pong responses from keepalive
		if (event.data === 'pong') return;

		try {
			const data = JSON.parse(event.data);
			onProgress(data);
		} catch (e) {
			console.error('WebSocket parse error:', e);
		}
	};

	ws.onerror = (error) => {
		console.error('WebSocket error:', error);
		onError?.(error);
	};

	// Keepalive ping
	const pingInterval = setInterval(() => {
		if (ws.readyState === WebSocket.OPEN) {
			ws.send('ping');
		}
	}, 25000);

	ws.onclose = () => {
		clearInterval(pingInterval);
	};

	return ws;
}
