<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from "svelte";
	import { Deck } from "@deck.gl/core";
	import { ScatterplotLayer, TextLayer } from "@deck.gl/layers";
	import { OrthographicView } from "@deck.gl/core";
	import {
		nodes,
		selectedNodes,
		highlightedNodes,
		hoveredNode,
		bounds,
		columnConfig,
		rawData,
	} from "$lib/stores/data";
	import { viewState, selectionEnabled, selectionTool } from "$lib/stores/ui";
	import {
		codeApplications,
		qualitativeCodes,
		activeCodeId,
	} from "$lib/stores/coding";
	import { designConfig } from "$lib/stores/design";
	import Legend from "./Legend.svelte";
	import type { Node } from "$lib/stores/data";

	const dispatch = createEventDispatcher();

	let container: HTMLDivElement;
	let canvas: HTMLCanvasElement;
	let selectionOverlay: SVGSVGElement;
	let deck: any = null; // Using any to avoid complex deck.gl typing issues

	// Selection drawing state
	let isDrawing = false;
	let selectionStart: { x: number; y: number } | null = null;
	let selectionRect: {
		x: number;
		y: number;
		width: number;
		height: number;
	} | null = null;
	let lassoPoints: { x: number; y: number }[] = [];

	// Color palette for clusters
	const clusterColors: [number, number, number, number][] = [
		[230, 25, 75, 255], // red
		[60, 180, 75, 255], // green
		[255, 225, 25, 255], // yellow
		[67, 99, 216, 255], // blue
		[245, 130, 49, 255], // orange
		[145, 30, 180, 255], // purple
		[70, 240, 240, 255], // cyan
		[240, 50, 230, 255], // magenta
		[188, 246, 12, 255], // lime
		[250, 190, 190, 255], // pink
	];

	const HIGHLIGHT_COLOR: [number, number, number, number] = [
		255, 215, 0, 255,
	]; // Gold
	const SELECTED_COLOR: [number, number, number, number] = [0, 255, 255, 200]; // Cyan

	function hexToRgba(hex: string): [number, number, number, number] {
		const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
		if (result) {
			return [
				parseInt(result[1], 16),
				parseInt(result[2], 16),
				parseInt(result[3], 16),
				255,
			];
		}
		return [128, 128, 128, 255];
	}

	// Get codes applied to a node
	function getNodeCodes(nodeId: number): string[] {
		return $codeApplications
			.filter((a) => a.nodeId === nodeId)
			.map((a) => a.codeId);
	}

	// Get the primary code color for a node (first applied code)
	function getNodeCodeColor(
		nodeId: number,
	): [number, number, number, number] | null {
		const nodeCodeIds = getNodeCodes(nodeId);
		if (nodeCodeIds.length === 0) return null;

		const primaryCode = $qualitativeCodes.find(
			(c) => c.id === nodeCodeIds[0],
		);
		if (!primaryCode) return null;

		return hexToRgba(primaryCode.color);
	}

	function getNodeColor(
		node: Node,
		highlighted: Set<number>,
		selected: Set<number>,
	): [number, number, number, number] {
		if (highlighted.has(node.id)) {
			return HIGHLIGHT_COLOR;
		}
		if (selected.has(node.id)) {
			return SELECTED_COLOR;
		}

		// Use design config for color
		const colorCol = $designConfig.colorColumn;
		if (colorCol && node.data && node.data[colorCol] !== undefined) {
			const value = String(node.data[colorCol]);
			const hex = $designConfig.colorMap[value];
			if (hex) return hexToRgba(hex);
		}

		// Fallback to cluster color
		return clusterColors[node.cluster % clusterColors.length];
	}

	function getNodeOpacity(node: Node): number {
		if ($designConfig.opacityMode === "fixed") {
			return $designConfig.opacityFixed;
		}

		// Opacity by column
		if ($designConfig.opacityColumn && node.data) {
			const val = Number(node.data[$designConfig.opacityColumn]);
			if (!isNaN(val)) {
				const allVals = $rawData
					.map((r) => Number(r[$designConfig.opacityColumn]))
					.filter((v) => !isNaN(v));
				const minVal = Math.min(...allVals);
				const maxVal = Math.max(...allVals);
				const range = maxVal - minVal || 1;
				const normalized = (val - minVal) / range;
				const [opacityMin, opacityMax] = $designConfig.opacityRange;
				return opacityMin + normalized * (opacityMax - opacityMin);
			}
		}
		return 1.0;
	}

	function getNodeRadius(
		node: Node,
		highlighted: Set<number>,
		selected: Set<number>,
	): number {
		let baseRadius = $designConfig.sizeFixed;

		// Size by column
		if (
			$designConfig.sizeMode === "column" &&
			$designConfig.sizeColumn &&
			node.data
		) {
			const val = Number(node.data[$designConfig.sizeColumn]);
			if (!isNaN(val)) {
				// Get min/max from data for normalization
				const allVals = $rawData
					.map((r) => Number(r[$designConfig.sizeColumn]))
					.filter((v) => !isNaN(v));
				const minVal = Math.min(...allVals);
				const maxVal = Math.max(...allVals);
				const range = maxVal - minVal || 1;
				const normalized = (val - minVal) / range;
				const [sizeMin, sizeMax] = $designConfig.sizeRange;
				baseRadius = sizeMin + normalized * (sizeMax - sizeMin);
			}
		}

		if (highlighted.has(node.id)) return baseRadius * 2.5;
		if (selected.has(node.id)) return baseRadius * 1.8;
		return baseRadius;
	}

	function createLayer(
		nodeData: Node[],
		highlighted: Set<number>,
		selected: Set<number>,
	): ScatterplotLayer<Node> {
		return new ScatterplotLayer<Node>({
			id: "scatter-layer",
			data: nodeData,
			pickable: true,
			opacity: 1,
			stroked: true,
			filled: true,
			radiusUnits: "pixels",
			radiusMinPixels: 3,
			radiusMaxPixels: 50,
			lineWidthUnits: "pixels",
			lineWidthMinPixels: 1,
			getPosition: (d: Node) =>
				[...d.position, 0] as [number, number, number],
			getRadius: (d: Node) => getNodeRadius(d, highlighted, selected),
			getFillColor: (d: Node) => {
				const baseColor = getNodeColor(d, highlighted, selected);
				const opacity = getNodeOpacity(d);
				return [
					baseColor[0],
					baseColor[1],
					baseColor[2],
					Math.round(opacity * 255),
				] as [number, number, number, number];
			},
			getLineColor: (d: Node) => {
				if (highlighted.has(d.id)) return [255, 0, 0, 255];
				if (selected.has(d.id)) return [0, 200, 200, 255];
				return [0, 0, 0, 80];
			},
			getLineWidth: (d: Node) => {
				if (highlighted.has(d.id)) return 2;
				if (selected.has(d.id)) return 1.5;
				return 1;
			},
			updateTriggers: {
				getRadius: [
					Array.from(highlighted),
					Array.from(selected),
					$designConfig.sizeMode,
					$designConfig.sizeFixed,
					$designConfig.sizeColumn,
				],
				getFillColor: [
					Array.from(highlighted),
					Array.from(selected),
					$codeApplications.length,
					$designConfig.colorColumn,
					JSON.stringify($designConfig.colorMap),
					$designConfig.opacityMode,
					$designConfig.opacityFixed,
					$designConfig.opacityColumn,
				],
				getLineColor: [Array.from(highlighted), Array.from(selected)],
				getLineWidth: [Array.from(highlighted), Array.from(selected)],
			},
		});
	}

	function createTextLayer(
		nodeData: Node[],
		config: typeof $designConfig,
	): TextLayer<Node> | null {
		if (!config.showLabels || !config.labelColumn) return null;

		return new TextLayer<Node>({
			id: "text-layer",
			data: nodeData,
			pickable: false,
			getPosition: (d: Node) =>
				[...d.position, 0] as [number, number, number],
			getText: (d: Node) => {
				const val = d.data?.[config.labelColumn];
				return val !== undefined && val !== null ? String(val) : "";
			},
			getSize: 12,
			getColor: [30, 30, 30, 220],
			getTextAnchor: "middle",
			getAlignmentBaseline: "top",
			getPixelOffset: [0, 8],
			fontFamily: "Inter, system-ui, sans-serif",
			fontWeight: 500,
			outlineWidth: 2,
			outlineColor: [255, 255, 255, 200],
			updateTriggers: {
				getText: [config.labelColumn],
			},
		});
	}

	// Compute convex hull using Gift Wrapping algorithm
	function computeConvexHull(points: [number, number][]): [number, number][] {
		if (points.length < 3) return points;

		// Find leftmost point
		let leftmost = 0;
		for (let i = 1; i < points.length; i++) {
			if (points[i][0] < points[leftmost][0]) leftmost = i;
		}

		const hull: [number, number][] = [];
		let current = leftmost;
		let iterations = 0;
		const maxIterations = points.length + 10;

		do {
			hull.push(points[current]);
			let next = 0;
			for (let i = 0; i < points.length; i++) {
				if (next === current) {
					next = i;
					continue;
				}
				const cross =
					(points[i][0] - points[current][0]) *
						(points[next][1] - points[current][1]) -
					(points[i][1] - points[current][1]) *
						(points[next][0] - points[current][0]);
				if (cross < 0) next = i;
			}
			current = next;
			iterations++;
		} while (current !== leftmost && iterations < maxIterations);

		return hull;
	}

	function initializeDeck() {
		if (!canvas || !container) return;

		const width = container.clientWidth;
		const height = container.clientHeight;

		deck = new Deck({
			canvas,
			width,
			height,
			views: [
				new OrthographicView({
					id: "main",
					controller: {
						scrollZoom: true,
						dragPan: true,
						dragRotate: false,
						doubleClickZoom: true,
						touchZoom: true,
						touchRotate: false,
						keyboard: true,
					},
				}),
			],
			initialViewState: {
				target: [0, 0, 0],
				zoom: 0,
				minZoom: -10,
				maxZoom: 10,
			} as any,
			onViewStateChange: ({ viewState: newViewState }: any) => {
				viewState.set({
					target: newViewState.target as [number, number, number],
					zoom: newViewState.zoom as number,
				});
				return newViewState;
			},
			layers: [],
			onClick: handleClick,
			onHover: handleHover,
			getTooltip: getTooltip,
			getCursor: ({ isHovering }: { isHovering: boolean }) =>
				isHovering ? "pointer" : "grab",
		});
	}

	function handleClick(info: any, event: any) {
		if (!info.object) return;

		const node = info.object as Node;

		if ($selectionEnabled && $selectionTool === "pointer") {
			// Toggle selection in pointer mode
			selectedNodes.update((s) => {
				const newSet = new Set(s);
				if (newSet.has(node.id)) {
					newSet.delete(node.id);
				} else {
					newSet.add(node.id);
				}
				return newSet;
			});
		} else if (!$selectionEnabled) {
			// Selection off - show modal
			showNodeModal(node);
		}
		// For rectangle/lasso tools, clicks are handled by mouse handlers
	}

	function handleHover(info: any) {
		if (info.object) {
			hoveredNode.set((info.object as Node).id);
		} else {
			hoveredNode.set(null);
		}
	}

	function getTooltip({ object }: { object?: Node }) {
		if (!object) return null;

		const cfg = $columnConfig;
		const label = cfg.label ? object.data[cfg.label] : `Node ${object.id}`;
		const tags =
			object.tags.size > 0 ? Array.from(object.tags).join(", ") : "";

		// Get qualitative codes applied to this node
		const nodeCodeIds = getNodeCodes(object.id);
		const nodeCodes = $qualitativeCodes.filter((c) =>
			nodeCodeIds.includes(c.id),
		);
		const codeNames = nodeCodes.map((c) => c.name).join(", ");

		return {
			html: `
				<div style="font-weight: 600">${label}</div>
				${codeNames ? `<div style="font-size: 0.8em; margin-top: 4px">Codes: ${codeNames}</div>` : ""}
				${tags ? `<div style="font-size: 0.8em; margin-top: 2px">Tags: ${tags}</div>` : ""}
				<div style="font-size: 0.8em; opacity: 0.7">Cluster ${object.cluster}</div>
			`,
			style: {
				backgroundColor: "#1a1a2e",
				color: "#ffffff",
				padding: "8px 12px",
				borderRadius: "4px",
				fontSize: "13px",
			},
		};
	}

	function showNodeModal(node: Node) {
		dispatch("nodeclick", node);
	}

	function fitToData() {
		if (!deck || !$bounds) return;

		const { center_x, center_y, span_x, span_y } = $bounds;

		// Calculate zoom to fit
		const containerWidth = container?.clientWidth || 800;
		const containerHeight = container?.clientHeight || 600;

		let zoom = 0;
		if (span_x > 0 && span_y > 0) {
			const zoomX = Math.log2(containerWidth / (span_x * 1.2));
			const zoomY = Math.log2(containerHeight / (span_y * 1.2));
			zoom = Math.min(zoomX, zoomY);
		}

		deck.setProps({
			initialViewState: {
				target: [center_x, center_y, 0],
				zoom,
				minZoom: -10,
				maxZoom: 10,
				transitionDuration: 500,
			},
		});
	}

	// Convert screen position to world coordinates
	function screenToWorld(screenX: number, screenY: number): [number, number] {
		if (!deck || !container) return [0, 0];

		const rect = container.getBoundingClientRect();
		const x = screenX - rect.left;
		const y = screenY - rect.top;

		// Get the viewport from deck
		const viewport = deck.getViewports()[0];
		if (!viewport) return [0, 0];

		// Unproject screen coordinates to world coordinates
		const worldPos = viewport.unproject([x, y]);
		return [worldPos[0], worldPos[1]];
	}

	// Check if point is inside rectangle
	function pointInRect(
		px: number,
		py: number,
		rect: { x: number; y: number; width: number; height: number },
	): boolean {
		const minX = Math.min(rect.x, rect.x + rect.width);
		const maxX = Math.max(rect.x, rect.x + rect.width);
		const minY = Math.min(rect.y, rect.y + rect.height);
		const maxY = Math.max(rect.y, rect.y + rect.height);
		return px >= minX && px <= maxX && py >= minY && py <= maxY;
	}

	// Check if point is inside polygon using ray casting
	function pointInPolygon(
		px: number,
		py: number,
		polygon: { x: number; y: number }[],
	): boolean {
		if (polygon.length < 3) return false;

		let inside = false;
		for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
			const xi = polygon[i].x,
				yi = polygon[i].y;
			const xj = polygon[j].x,
				yj = polygon[j].y;

			if (
				yi > py !== yj > py &&
				px < ((xj - xi) * (py - yi)) / (yj - yi) + xi
			) {
				inside = !inside;
			}
		}
		return inside;
	}

	// Selection mouse handlers
	function handleSelectionMouseDown(e: MouseEvent) {
		if (!$selectionEnabled || $selectionTool === "pointer") return;
		if (e.button !== 0) return; // Only left click

		isDrawing = true;
		const rect = container.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;

		selectionStart = { x, y };

		if ($selectionTool === "rectangle") {
			selectionRect = { x, y, width: 0, height: 0 };
		} else if ($selectionTool === "lasso") {
			lassoPoints = [{ x, y }];
		}

		e.preventDefault();
		e.stopPropagation();
	}

	function handleSelectionMouseMove(e: MouseEvent) {
		if (!isDrawing || !selectionStart) return;

		const rect = container.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;

		if ($selectionTool === "rectangle" && selectionStart) {
			selectionRect = {
				x: selectionStart.x,
				y: selectionStart.y,
				width: x - selectionStart.x,
				height: y - selectionStart.y,
			};
		} else if ($selectionTool === "lasso") {
			lassoPoints = [...lassoPoints, { x, y }];
		}
	}

	function handleSelectionMouseUp(e: MouseEvent) {
		if (!isDrawing) return;

		// Find nodes within selection
		const selectedIds = new Set<number>();

		if ($selectionTool === "rectangle" && selectionRect) {
			// Convert rectangle corners to world coordinates
			const topLeft = screenToWorld(
				container.getBoundingClientRect().left +
					Math.min(
						selectionRect.x,
						selectionRect.x + selectionRect.width,
					),
				container.getBoundingClientRect().top +
					Math.min(
						selectionRect.y,
						selectionRect.y + selectionRect.height,
					),
			);
			const bottomRight = screenToWorld(
				container.getBoundingClientRect().left +
					Math.max(
						selectionRect.x,
						selectionRect.x + selectionRect.width,
					),
				container.getBoundingClientRect().top +
					Math.max(
						selectionRect.y,
						selectionRect.y + selectionRect.height,
					),
			);

			const worldRect = {
				x: topLeft[0],
				y: bottomRight[1], // Note: Y is inverted
				width: bottomRight[0] - topLeft[0],
				height: topLeft[1] - bottomRight[1],
			};

			// Check each node
			for (const node of $nodes) {
				if (
					pointInRect(node.position[0], node.position[1], worldRect)
				) {
					selectedIds.add(node.id);
				}
			}
		} else if ($selectionTool === "lasso" && lassoPoints.length > 2) {
			// Convert lasso points to world coordinates
			const worldPolygon = lassoPoints.map((p) => {
				const world = screenToWorld(
					container.getBoundingClientRect().left + p.x,
					container.getBoundingClientRect().top + p.y,
				);
				return { x: world[0], y: world[1] };
			});

			// Check each node
			for (const node of $nodes) {
				if (
					pointInPolygon(
						node.position[0],
						node.position[1],
						worldPolygon,
					)
				) {
					selectedIds.add(node.id);
				}
			}
		}

		// Update selection (add to existing if shift is held)
		if (e.shiftKey) {
			selectedNodes.update((s) => {
				const newSet = new Set(s);
				selectedIds.forEach((id) => newSet.add(id));
				return newSet;
			});
		} else {
			selectedNodes.set(selectedIds);
		}

		// Reset drawing state
		isDrawing = false;
		selectionStart = null;
		selectionRect = null;
		lassoPoints = [];
	}

	// Generate SVG path for lasso
	$: lassoPath =
		lassoPoints.length > 1
			? `M ${lassoPoints.map((p) => `${p.x},${p.y}`).join(" L ")}`
			: "";

	// Reactive updates - include codeApplications to update when codes change
	$: if (deck) {
		if ($nodes.length > 0) {
			// Reference codeApplications, qualitativeCodes, and designConfig to trigger reactivity
			const _ = [$codeApplications, $qualitativeCodes, $designConfig];
			const layers: any[] = [];

			// Add scatter layer
			layers.push(createLayer($nodes, $highlightedNodes, $selectedNodes));

			// Add text layer on top
			const textLayer = createTextLayer($nodes, $designConfig);
			if (textLayer) layers.push(textLayer);

			deck.setProps({ layers });
		} else {
			// Clear layers when no nodes
			deck.setProps({ layers: [] });
		}
	}

	$: if (deck && $bounds) {
		fitToData();
	}

	// Track last viewState to detect external changes
	let lastViewStateUpdate = { target: [0, 0, 0], zoom: 0 };

	// Respond to external viewState changes (e.g., from search result clicks)
	$: if (deck && $viewState) {
		const isExternalUpdate =
			$viewState.target[0] !== lastViewStateUpdate.target[0] ||
			$viewState.target[1] !== lastViewStateUpdate.target[1] ||
			$viewState.zoom !== lastViewStateUpdate.zoom;

		if (isExternalUpdate) {
			lastViewStateUpdate = {
				target: [...$viewState.target],
				zoom: $viewState.zoom,
			};
			deck.setProps({
				initialViewState: {
					target: $viewState.target,
					zoom: $viewState.zoom,
					minZoom: -10,
					maxZoom: 10,
					transitionDuration: 500,
				},
			});
		}
	}

	// Handle resize
	function handleResize() {
		if (deck && container) {
			deck.setProps({
				width: container.clientWidth,
				height: container.clientHeight,
			});
		}
	}

	onMount(() => {
		initializeDeck();

		const resizeObserver = new ResizeObserver(handleResize);
		resizeObserver.observe(container);

		return () => {
			resizeObserver.disconnect();
		};
	});

	onDestroy(() => {
		if (deck) {
			deck.finalize();
			deck = null;
		}
	});
</script>

<div
	class="graph-container"
	class:selection-active={$selectionEnabled && $selectionTool !== "pointer"}
	bind:this={container}
	on:mousedown={handleSelectionMouseDown}
	on:mousemove={handleSelectionMouseMove}
	on:mouseup={handleSelectionMouseUp}
	on:mouseleave={handleSelectionMouseUp}
	role="application"
	aria-label="Data visualization"
>
	<canvas bind:this={canvas} class="graph-canvas"></canvas>

	<!-- Selection Overlay -->
	{#if $selectionEnabled && $selectionTool !== "pointer"}
		<svg class="selection-overlay" bind:this={selectionOverlay}>
			{#if selectionRect}
				<rect
					x={selectionRect.width >= 0
						? selectionRect.x
						: selectionRect.x + selectionRect.width}
					y={selectionRect.height >= 0
						? selectionRect.y
						: selectionRect.y + selectionRect.height}
					width={Math.abs(selectionRect.width)}
					height={Math.abs(selectionRect.height)}
					class="selection-rect"
				/>
			{/if}
			{#if lassoPath}
				<path d={lassoPath} class="selection-lasso" />
			{/if}
		</svg>
	{/if}

	{#if $nodes.length === 0}
		<div class="empty-state">
			<div class="empty-icon">📊</div>
			<h3>No visualization yet</h3>
			<p>
				Upload data and process embeddings to see your data visualized
				here.
			</p>
		</div>
	{/if}

	<!-- Toolbar -->
	<div class="graph-toolbar">
		<button class="toolbar-btn" on:click={fitToData} title="Fit to data">
			⊡
		</button>
	</div>

	<!-- Selection Mode Indicator -->
	{#if $selectionEnabled}
		<div class="selection-indicator">
			Selection: {$selectionTool}
			{#if $selectionTool !== "pointer"}
				<span class="hint">(Shift+drag to add)</span>
			{/if}
		</div>
	{/if}

	<!-- Legend -->
	{#if $nodes.length > 0}
		<Legend />
	{/if}
</div>

<style>
	.graph-container {
		flex: 1;
		position: relative;
		background: #f8fafc;
		overflow: hidden;
	}

	.graph-canvas {
		width: 100%;
		height: 100%;
		display: block;
	}

	.empty-state {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--text-secondary);
	}

	.empty-icon {
		font-size: 4rem;
		margin-bottom: var(--spacing-md);
		opacity: 0.5;
	}

	.empty-state h3 {
		margin-bottom: var(--spacing-sm);
		color: var(--text-primary);
	}

	.empty-state p {
		max-width: 300px;
		font-size: 0.9rem;
	}

	.graph-toolbar {
		position: absolute;
		top: var(--spacing-md);
		right: var(--spacing-md);
		display: flex;
		gap: var(--spacing-xs);
		background: white;
		padding: var(--spacing-xs);
		border-radius: 4px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.toolbar-btn {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		cursor: pointer;
		border-radius: 4px;
		font-size: 1.2rem;
		transition: background 0.15s;
	}

	.toolbar-btn:hover {
		background: var(--bg-color);
	}

	/* Selection overlay */
	.selection-overlay {
		position: absolute;
		inset: 0;
		pointer-events: none;
		z-index: 10;
	}

	.selection-rect {
		fill: rgba(67, 99, 216, 0.2);
		stroke: rgba(67, 99, 216, 0.8);
		stroke-width: 2;
		stroke-dasharray: 4 2;
	}

	.selection-lasso {
		fill: none;
		stroke: rgba(67, 99, 216, 0.8);
		stroke-width: 2;
		stroke-dasharray: 4 2;
	}

	.graph-container.selection-active {
		cursor: crosshair;
	}

	.graph-container.selection-active .graph-canvas {
		pointer-events: none;
	}

	.selection-indicator {
		position: absolute;
		bottom: var(--spacing-md);
		left: var(--spacing-md);
		background: rgba(26, 26, 46, 0.9);
		color: white;
		padding: 6px 12px;
		border-radius: 4px;
		font-size: 0.8rem;
		text-transform: capitalize;
	}

	.selection-indicator .hint {
		opacity: 0.7;
		font-size: 0.75rem;
		margin-left: 8px;
	}
</style>
