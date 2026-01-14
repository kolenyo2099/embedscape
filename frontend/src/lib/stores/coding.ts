/**
 * Qualitative Coding Stores
 * For sociological/anthropological qualitative analysis
 */
import { writable, derived } from 'svelte/store';

// Types for qualitative coding

export interface QualitativeCode {
	id: string;
	name: string;
	description: string;
	color: string;
	parentId: string | null;  // For hierarchical codes
	level: 1 | 2 | 3;         // 1=Theme, 2=Category, 3=Subcode
	createdAt: Date;
	createdBy?: string;
}

export interface CodeApplication {
	codeId: string;
	nodeId: number;           // Which data point
	appliedAt: Date;
	appliedBy?: string;
	notes?: string;           // Optional annotation
}

export interface Memo {
	id: string;
	title: string;
	content: string;          // Rich text/markdown
	linkedCodes: string[];    // Code IDs this memo relates to
	linkedNodes: number[];    // Data points this memo references
	memoType: 'theoretical' | 'methodological' | 'observational' | 'analytical';
	createdAt: Date;
	updatedAt: Date;
	createdBy?: string;
}

export interface CodeRelation {
	fromCodeId: string;
	toCodeId: string;
	relationType: 'is-a' | 'part-of' | 'causes' | 'contradicts' | 'associates-with' | 'precedes';
	strength?: number;        // 0-1 for weighted relationships
	notes?: string;
}

export interface CodingEvent {
	id: string;
	timestamp: Date;
	action: 'apply' | 'remove' | 'create-code' | 'update-code' | 'delete-code' | 'merge-codes' | 'create-memo';
	codeId?: string;
	nodeIds?: number[];
	coder?: string;
	details?: string;
}

// Stores
export const qualitativeCodes = writable<QualitativeCode[]>([]);
export const codeApplications = writable<CodeApplication[]>([]);
export const memos = writable<Memo[]>([]);
export const codeRelations = writable<CodeRelation[]>([]);
export const codingEvents = writable<CodingEvent[]>([]);

// Currently active code for quick application
export const activeCodeId = writable<string | null>(null);

// Coding panel state
export const codingPanelOpen = writable<boolean>(true);
export const selectedMemoId = writable<string | null>(null);

// Color palette for codes
export const CODE_COLORS = [
	'#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
	'#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
	'#008080', '#e6beff', '#9a6324', '#fffac8', '#800000',
	'#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080'
];

// Derived stores

// Get codes organized by hierarchy
export const codeHierarchy = derived(qualitativeCodes, ($codes) => {
	const rootCodes = $codes.filter(c => c.parentId === null).sort((a, b) => a.name.localeCompare(b.name));

	function getChildren(parentId: string): QualitativeCode[] {
		return $codes
			.filter(c => c.parentId === parentId)
			.sort((a, b) => a.name.localeCompare(b.name));
	}

	function buildTree(codes: QualitativeCode[]): Array<QualitativeCode & { children: any[] }> {
		return codes.map(code => ({
			...code,
			children: buildTree(getChildren(code.id))
		}));
	}

	return buildTree(rootCodes);
});

// Get codes applied to a specific node
export const getCodesForNode = derived(
	[qualitativeCodes, codeApplications],
	([$codes, $applications]) => {
		return (nodeId: number): QualitativeCode[] => {
			const appliedCodeIds = $applications
				.filter(a => a.nodeId === nodeId)
				.map(a => a.codeId);
			return $codes.filter(c => appliedCodeIds.includes(c.id));
		};
	}
);

// Get nodes that have a specific code
export const getNodesForCode = derived(codeApplications, ($applications) => {
	return (codeId: string): number[] => {
		return $applications
			.filter(a => a.codeId === codeId)
			.map(a => a.nodeId);
	};
});

// Code frequency (how many times each code is used)
export const codeFrequency = derived(
	[qualitativeCodes, codeApplications],
	([$codes, $applications]) => {
		const freq = new Map<string, number>();
		$codes.forEach(c => freq.set(c.id, 0));
		$applications.forEach(a => {
			freq.set(a.codeId, (freq.get(a.codeId) || 0) + 1);
		});
		return freq;
	}
);

// Helper functions

export function generateCodeId(): string {
	return `code_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function generateMemoId(): string {
	return `memo_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export function createCode(
	name: string,
	parentId: string | null = null,
	level: 1 | 2 | 3 = 1,
	description: string = '',
	color?: string
): QualitativeCode {
	const code: QualitativeCode = {
		id: generateCodeId(),
		name,
		description,
		color: color || CODE_COLORS[Math.floor(Math.random() * CODE_COLORS.length)],
		parentId,
		level,
		createdAt: new Date()
	};

	qualitativeCodes.update(codes => [...codes, code]);
	logCodingEvent('create-code', code.id);

	return code;
}

export function applyCode(codeId: string, nodeIds: number[], notes?: string) {
	codeApplications.update(apps => {
		const newApps = nodeIds
			.filter(nodeId => !apps.some(a => a.codeId === codeId && a.nodeId === nodeId))
			.map(nodeId => ({
				codeId,
				nodeId,
				appliedAt: new Date(),
				notes
			}));
		return [...apps, ...newApps];
	});
	logCodingEvent('apply', codeId, nodeIds);
}

export function removeCodeFromNodes(codeId: string, nodeIds: number[]) {
	codeApplications.update(apps =>
		apps.filter(a => !(a.codeId === codeId && nodeIds.includes(a.nodeId)))
	);
	logCodingEvent('remove', codeId, nodeIds);
}

export function deleteCode(codeId: string) {
	// Remove all applications of this code
	codeApplications.update(apps => apps.filter(a => a.codeId !== codeId));
	// Remove the code itself
	qualitativeCodes.update(codes => codes.filter(c => c.id !== codeId));
	// Update any child codes to become root codes
	qualitativeCodes.update(codes =>
		codes.map(c => c.parentId === codeId ? { ...c, parentId: null } : c)
	);
	logCodingEvent('delete-code', codeId);
}

export function updateCode(codeId: string, updates: Partial<QualitativeCode>) {
	qualitativeCodes.update(codes =>
		codes.map(c => c.id === codeId ? { ...c, ...updates } : c)
	);
	logCodingEvent('update-code', codeId);
}

export function mergeCodes(sourceCodeId: string, targetCodeId: string) {
	// Move all applications from source to target
	codeApplications.update(apps =>
		apps.map(a => a.codeId === sourceCodeId ? { ...a, codeId: targetCodeId } : a)
	);
	// Delete the source code
	deleteCode(sourceCodeId);
	logCodingEvent('merge-codes', targetCodeId, undefined, `Merged from ${sourceCodeId}`);
}

export function createMemo(
	title: string,
	content: string,
	memoType: Memo['memoType'] = 'observational',
	linkedCodes: string[] = [],
	linkedNodes: number[] = []
): Memo {
	const memo: Memo = {
		id: generateMemoId(),
		title,
		content,
		linkedCodes,
		linkedNodes,
		memoType,
		createdAt: new Date(),
		updatedAt: new Date()
	};

	memos.update(m => [...m, memo]);
	logCodingEvent('create-memo', undefined, linkedNodes, title);

	return memo;
}

export function updateMemo(memoId: string, updates: Partial<Memo>) {
	memos.update(m =>
		m.map(memo => memo.id === memoId ? { ...memo, ...updates, updatedAt: new Date() } : memo)
	);
}

export function deleteMemo(memoId: string) {
	memos.update(m => m.filter(memo => memo.id !== memoId));
}

function logCodingEvent(
	action: CodingEvent['action'],
	codeId?: string,
	nodeIds?: number[],
	details?: string
) {
	codingEvents.update(events => [...events, {
		id: `event_${Date.now()}`,
		timestamp: new Date(),
		action,
		codeId,
		nodeIds,
		details
	}]);
}

// Export/Import functions

export function exportCodingData(): string {
	let codes: QualitativeCode[] = [];
	let applications: CodeApplication[] = [];
	let memosData: Memo[] = [];
	let relations: CodeRelation[] = [];

	qualitativeCodes.subscribe(c => codes = c)();
	codeApplications.subscribe(a => applications = a)();
	memos.subscribe(m => memosData = m)();
	codeRelations.subscribe(r => relations = r)();

	return JSON.stringify({
		version: '1.0',
		exportedAt: new Date().toISOString(),
		codes,
		applications,
		memos: memosData,
		relations
	}, null, 2);
}

export function importCodingData(jsonString: string) {
	try {
		const data = JSON.parse(jsonString);
		if (data.codes) qualitativeCodes.set(data.codes);
		if (data.applications) codeApplications.set(data.applications);
		if (data.memos) memos.set(data.memos);
		if (data.relations) codeRelations.set(data.relations);
		return true;
	} catch (e) {
		console.error('Failed to import coding data:', e);
		return false;
	}
}

export function clearAllCodingData() {
	qualitativeCodes.set([]);
	codeApplications.set([]);
	memos.set([]);
	codeRelations.set([]);
	codingEvents.set([]);
}
