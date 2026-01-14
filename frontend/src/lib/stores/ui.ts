/**
 * UI state stores
 */
import { writable, derived } from 'svelte/store';

// Processing state
export const isProcessing = writable<boolean>(false);
export const processingStage = writable<string>('');
export const processingProgress = writable<number>(0);
export const processingMessage = writable<string>('');

// Panel visibility
export const showSidebar = writable<boolean>(true);
export const showBottomPanel = writable<boolean>(true);
export const showRightPanel = writable<boolean>(true);

// Modal state
export const modalOpen = writable<boolean>(false);
export const modalContent = writable<any>(null);

// Selection mode (simple on/off toggle)
export const selectionEnabled = writable<boolean>(false);

// Selection tool
export type SelectionTool = 'pointer' | 'rectangle' | 'lasso';
export const selectionTool = writable<SelectionTool>('pointer');

// Color mode for visualization
export type ColorMode = 'cluster' | 'tag';
export const colorMode = writable<ColorMode>('cluster');

// View state for deck.gl
export interface ViewState {
	target: [number, number, number];
	zoom: number;
	minZoom?: number;
	maxZoom?: number;
}

export const viewState = writable<ViewState>({
	target: [0, 0, 0],
	zoom: 0
});

// Search UI
export type QueryType = 'text' | 'image';
export const queryType = writable<QueryType>('text');
export const searchThreshold = writable<number>(0.7);

// Notifications
export interface Notification {
	id: string;
	type: 'info' | 'success' | 'warning' | 'error';
	message: string;
	duration?: number;
}

export const notifications = writable<Notification[]>([]);

export function addNotification(type: Notification['type'], message: string, duration = 3000) {
	const id = crypto.randomUUID();
	notifications.update(n => [...n, { id, type, message, duration }]);

	if (duration > 0) {
		setTimeout(() => {
			notifications.update(n => n.filter(notif => notif.id !== id));
		}, duration);
	}

	return id;
}

export function removeNotification(id: string) {
	notifications.update(n => n.filter(notif => notif.id !== id));
}

// Code editor state
export const codeContent = writable<string>(`# Transform your data with Python
# Available: df (pandas DataFrame with your data)

def transform(df):
    # Example: filter rows where likes > 100
    # return df[df['likes'] > 100]

    # Example: add a new column
    # df['word_count'] = df['text'].str.split().str.len()

    return df
`);

export const codeLanguage = writable<'python' | 'sql'>('python');

// Derived
export const isReady = derived(
	[isProcessing],
	([$isProcessing]) => !$isProcessing
);
