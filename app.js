// External deps loaded in index.html: PapaParse, UMAP, deck.gl (UMD)
const { Deck, ScatterplotLayer, OrthographicView, LinearInterpolator } = window.deck;

// Help modal handlers
const helpBtn = document.getElementById('help-btn');
const helpModal = document.getElementById('help-modal');
const helpClose = document.getElementById('help-close');

helpBtn?.addEventListener('click', () => { helpModal.style.display = 'block'; });
helpClose?.addEventListener('click', () => { helpModal.style.display = 'none'; });
helpModal?.addEventListener('click', (e) => { if (e.target === helpModal) helpModal.style.display = 'none'; });

let csv = [];
let fields = [];
let cfg = { text: null, label: null, link: null, image: null, mode: 'text', source: 'text', k: 5, batch: 16, imageEmbedder: 'Xenova/clip-vit-base-patch32' };

let embeddings = [];
let coords = [];
let clusters = [];
let nodes = [];
let searchVec = null;
let highlightedNodes = new Set();  // Track highlighted nodes for search

// Tagging system
let selectedNodes = new Set();  // Track selected nodes for tagging
let allTags = new Map();  // tag name -> Set of node ids
let colorMode = 'cluster';  // 'cluster' or 'tag'
let selectionMode = 'off';  // 'off', 'single', or 'multi'
let tagColors = {};  // tag name -> color

let deckInstance = null;
let currentViewState = null;  // Track current view state for animations
let worker = null;
let workerReady = false;

const el = (id) => document.getElementById(id);
const fileInput = el('csv-file');
const fileInfo = el('file-info');
const loadSavedBtn = el('load-emb-btn');
const embFile = el('emb-file');
const saveBtn = el('save-emb-btn');
const saveMsg = el('save-msg');

const configPanel = el('config');
const textCol = el('text-col');
const labelCol = el('label-col');
const linkCol = el('link-col');
const imageCol = el('image-col');
const imageEmbedderSel = el('image-embedder');
const modeSel = el('mode');
const sourceSel = el('source');
const kInput = el('k');
const batchInput = el('batch');

const processBtn = el('process');
const cancelBtn = el('cancel');

const progressPanel = el('progress');
const bar = el('bar');
const ptext = el('ptext');

const searchPanel = el('search');
const queryType = el('query-type');
const q = el('q');
const qImg = el('q-img');
const go = el('go');
const clearBtn = el('clear');
const th = el('th');
const thval = el('thval');
const results = el('results');

// Tagging UI elements
const selectionModeEl = el('selection-mode');
const selectedCountEl = el('selected-count');
const clearSelectionBtn = el('clear-selection');
const newTagInput = el('new-tag');
const addTagBtn = el('add-tag-btn');
const removeTagBtn = el('remove-tag-btn');
const currentTagsEl = el('current-tags');
const colorModeEl = el('color-mode');
const tagFilterEl = el('tag-filter');
const allTagsEl = el('all-tags');

// Hardcoded node size - good default for UMAP coordinate space
const DEFAULT_NODE_SIZE = 0.05;

const viz = el('viz');

const colors = ['#e6194b','#3cb44b','#ffe119','#4363d8','#f58231','#911eb4','#46f0f0','#f032e6','#bcf60c','#fabebe','#008080','#e6beff','#9a6324','#fffac8','#800000','#aaffc3','#808000','#ffd8b1','#000075','#808080','#ffffff','#000000'];

const setBar = (pct, text) => { bar.style.width = `${pct}%`; bar.textContent = `${Math.round(pct)}%`; ptext.textContent = text || ''; };
const esc = (s) => { const d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; };
const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? { r: parseInt(result[1], 16), g: parseInt(result[2], 16), b: parseInt(result[3], 16) } : { r: 0, g: 0, b: 0 };
};

fileInput.addEventListener('change', (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  Papa.parse(f, {
    header: true,
    skipEmptyLines: true,
    complete: (res) => {
      csv = res.data;
      fields = res.meta.fields || Object.keys(csv[0] || {});
      fileInfo.innerHTML = `<strong>File:</strong> ${esc(f.name)} · <strong>Rows:</strong> ${csv.length}`;
      [textCol, labelCol, linkCol, imageCol].forEach(sel => { sel.innerHTML = ''; });
      fields.forEach(col => {
        textCol.appendChild(new Option(col, col));
        labelCol.appendChild(new Option(col, col));
        linkCol.appendChild(new Option(col, col));
        imageCol.appendChild(new Option(col, col));
      });
      textCol.prepend(new Option('None', ''));
      labelCol.prepend(new Option('None', ''));
      linkCol.prepend(new Option('None', ''));
      imageCol.prepend(new Option('None', ''));
      updateUI();
      configPanel.style.display = 'block';
    }
  });
});

loadSavedBtn.addEventListener('click', () => embFile.click());
embFile.addEventListener('change', async (e) => {
  const f = e.target.files?.[0]; if (!f) return;
  const txt = await f.text();
  const data = JSON.parse(txt);
  csv = data.csv; fields = Object.keys(csv[0] || {});
  cfg = data.cfg; embeddings = data.embeddings; coords = data.coords; clusters = data.clusters;
  // Ensure we keep the original embedding mode for consistent querying
  if (!cfg._embedMode) { cfg._embedMode = cfg.mode; }
  cfg.imageEmbedder = cfg.imageEmbedder || 'Xenova/clip-vit-base-patch32';
  computeEmbedMetadata(cfg);

  // Restore tags if present
  if (data.tags) {
    allTags = new Map(Object.entries(data.tags.allTags || {}).map(([tag, ids]) => [tag, new Set(ids)]));
    tagColors = data.tags.tagColors || {};
  } else {
    allTags = new Map();
    tagColors = {};
  }

  [textCol, labelCol, linkCol, imageCol].forEach(sel => { sel.innerHTML = ''; });
  fields.forEach(col => {
    textCol.appendChild(new Option(col, col));
    labelCol.appendChild(new Option(col, col));
    linkCol.appendChild(new Option(col, col));
    imageCol.appendChild(new Option(col, col));
  });
  textCol.value = cfg.text || '';
  labelCol.value = cfg.label || '';
  linkCol.value = cfg.link || '';
  imageCol.value = cfg.image || '';
  if (imageEmbedderSel) imageEmbedderSel.value = cfg.imageEmbedder || 'Xenova/clip-vit-base-patch32';
  modeSel.value = cfg.mode || 'text';
  sourceSel.value = cfg.source || 'text';
  kInput.value = cfg.k || 5;
  batchInput.value = cfg.batch || 16;
  updateUI();

  await buildNodesAndViz();

  // Restore node tags after nodes are built
  if (data.tags && data.tags.nodeTags) {
    data.tags.nodeTags.forEach((tagArray, i) => {
      if (nodes[i]) {
        nodes[i].tags = new Set(tagArray || []);
      }
    });
  }

  // Update tag UI
  updateTagUI();

  el('search').style.display = 'block';
  viz.style.display = 'block';
  saveBtn.disabled = false;
  updateQueryAvailability();

  // Ensure worker is ready for searches
  if (!worker) {
    worker = createWorker();
    workerReady = false;
    setupWorkerHandlers();
  }
});

saveBtn.addEventListener('click', () => {
  // Serialize tags data
  const tagsData = {
    allTags: Object.fromEntries(Array.from(allTags.entries()).map(([tag, ids]) => [tag, Array.from(ids)])),
    tagColors: tagColors,
    nodeTags: nodes.map(n => n.tags ? Array.from(n.tags) : [])
  };

  const payload = {
    version: '2.1',
    timestamp: new Date().toISOString(),
    csv,
    cfg,
    embeddings,
    coords,
    clusters,
    tags: tagsData
  };

  const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `embeddings_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
  saveMsg.style.display = 'block';
  saveMsg.textContent = `✅ Saved ${embeddings.length} vectors + tags.`;
  setTimeout(() => saveMsg.style.display = 'none', 2500);
});

const updateUI = () => {
  const hasText = textCol.value && textCol.value !== '';
  const hasImage = imageCol.value && imageCol.value !== '';
  const isJEPASelected = (imageEmbedderSel?.value || '').startsWith('onnx-community/ijepa');

  // Show image embedder selection only when multimodal is relevant
  if (imageEmbedderSel) {
    const row = document.getElementById('image-embedder-row');
    if (row) {
      const shouldShow = hasImage && modeSel.value === 'multimodal';
      row.style.display = shouldShow ? 'block' : 'none';
    }
  }
  
  if (!hasText && !hasImage) {
    modeSel.disabled = true;
    sourceSel.disabled = true;
  } else if (hasText && !hasImage) {
    // Text only
    modeSel.value = 'text';
    modeSel.disabled = true;
    sourceSel.disabled = true;
  } else if (!hasText && hasImage) {
    // Image only
    modeSel.value = 'multimodal';
    modeSel.disabled = true;
    sourceSel.value = 'image';
    sourceSel.disabled = true;
  } else {
    // Both selected
    modeSel.disabled = false;
    const multimodal = modeSel.value === 'multimodal';
    if (multimodal) {
      sourceSel.disabled = false;
      sourceSel.options[0].hidden = false; // text
      sourceSel.options[1].hidden = false; // image
      sourceSel.options[2].hidden = false; // both
      if (isJEPASelected) {
        sourceSel.value = 'image';
        sourceSel.options[0].disabled = true;
        sourceSel.options[2].disabled = true;
        sourceSel.options[1].disabled = false;
      } else {
        sourceSel.options[0].disabled = false;
        sourceSel.options[1].disabled = false;
        sourceSel.options[2].disabled = false;
      }
    } else {
      sourceSel.disabled = false;
      sourceSel.options[0].hidden = false; // text
      sourceSel.options[1].hidden = true; // image
      sourceSel.options[2].hidden = true; // both
      sourceSel.value = 'text';
    }
  }
};

const computeEmbedMetadata = (config) => {
  const isJEPA = (config.imageEmbedder || '').startsWith('onnx-community/ijepa');
  config._embedFamily = config.mode === 'text' ? 'text' : (isJEPA ? 'ijepa' : 'clip');
  config._embedHasImage = config.mode === 'multimodal' && (config.source === 'image' || config.source === 'both');
  config._embedHasText = config.mode === 'text' || (config.mode === 'multimodal' && !isJEPA && (config.source === 'text' || config.source === 'both'));
  return config;
};

const updateQueryAvailability = () => {
  const canImageQuery = !!cfg._embedHasImage;
  const canTextQuery = !!cfg._embedHasText;

  if (queryType?.options?.length >= 2) {
    queryType.options[0].disabled = !canTextQuery;
    queryType.options[1].disabled = !canImageQuery;

    if (queryType.value === 'image' && !canImageQuery) queryType.value = 'text';
    if (queryType.value === 'text' && !canTextQuery) queryType.value = 'image';
  }

  const isImageQuery = queryType.value === 'image';
  q.style.display = isImageQuery ? 'none' : 'block';
  qImg.style.display = isImageQuery ? 'block' : 'none';
};

modeSel.addEventListener('change', updateUI);
textCol.addEventListener('change', updateUI);
imageCol.addEventListener('change', updateUI);
imageEmbedderSel?.addEventListener('change', updateUI);

processBtn.addEventListener('click', async () => {
  cfg.text = textCol.value || null; cfg.label = labelCol.value || null; cfg.link = linkCol.value || null; cfg.image = imageCol.value || null;
  cfg.k = parseInt(kInput.value || '5', 10); cfg.batch = parseInt(batchInput.value || '16', 10);
  cfg.imageEmbedder = imageEmbedderSel?.value || 'Xenova/clip-vit-base-patch32';
  
  if (!cfg.text && !cfg.image) { alert('Please select at least a text column or an image column.'); return; }

  const isJEPA = (cfg.imageEmbedder || '').startsWith('onnx-community/ijepa');
  
  // Auto-detect mode and source based on selected columns
  if (cfg.text && !cfg.image) {
    // Text only
    cfg.mode = 'text';
    cfg.source = 'text';
  } else if (!cfg.text && cfg.image) {
    // Image only
    cfg.mode = 'multimodal';
    cfg.source = 'image';
  } else if (cfg.text && cfg.image) {
    // Both selected - use user's choice
    cfg.mode = modeSel.value;
    cfg.source = sourceSel.value;

    // Validate
    if (cfg.mode === 'text' && cfg.source !== 'text') { cfg.source = 'text'; }
    if (cfg.source === 'image' && !cfg.image) { alert('Select an image URL column or choose another source.'); return; }
    if (isJEPA && cfg.source === 'both') { alert('I-JEPA does not support combining text and image. Choose Image column.'); return; }
  }

  if (isJEPA && cfg.mode !== 'multimodal') { cfg.mode = 'multimodal'; }
  if (isJEPA && !cfg.image) { alert('I-JEPA requires an image URL column.'); return; }

  computeEmbedMetadata(cfg);

  configPanel.style.display = 'none';
  progressPanel.style.display = 'block';
  setBar(2, 'Loading worker & model…');

  if (worker) { worker.terminate(); worker = null; }
  worker = createWorker();
  workerReady = false;
  setupWorkerHandlers();

  // Remember which model family produced the embeddings — used later for queries
  cfg._embedMode = cfg.mode;

  const items = buildItems(csv, cfg);
  worker.postMessage({ type: 'start', cfg, items });
  cancelBtn.disabled = false;
});

cancelBtn.addEventListener('click', () => {
  if (worker) { worker.terminate(); worker = null; }
  progressPanel.style.display = 'none';
  configPanel.style.display = 'block';
});

// Query type selector - show/hide appropriate input
queryType.addEventListener('change', () => {
  const isImageQuery = queryType.value === 'image';
  q.style.display = isImageQuery ? 'none' : 'block';
  qImg.style.display = isImageQuery ? 'block' : 'none';

  if (isImageQuery && !cfg._embedHasImage) {
    alert('Image search only works when embeddings include images.');
    queryType.value = 'text';
    q.style.display = 'block';
    qImg.style.display = 'none';
  }
});

th.addEventListener('input', () => { thval.textContent = Number(th.value).toFixed(2); });

go.addEventListener('click', async () => {
  const isImageQuery = queryType.value === 'image';

  if (isImageQuery) {
    // Handle image file upload
    const file = qImg.files?.[0];
    if (!file) {
      alert('Please select an image file');
      return;
    }

    // Ensure worker exists and is set up
    if (!worker) {
      worker = createWorker();
      workerReady = false;
      setupWorkerHandlers();
    }

    // Read the image file and convert to data URL
    const reader = new FileReader();
    reader.onload = (e) => {
      const imageDataUrl = e.target.result;
      const queryMode = cfg._embedMode || cfg.mode;
      worker.postMessage({ type: 'encodeQuery', image: imageDataUrl, cfg: { ...cfg, mode: queryMode, query: true } });
    };
    reader.readAsDataURL(file);
  } else {
    // Handle text query
    const queryInput = q.value.trim();
    if (!queryInput) {
      alert('Enter a query');
      return;
    }

    // Ensure worker exists and is set up
    if (!worker) {
      worker = createWorker();
      workerReady = false;
      setupWorkerHandlers();
    }

    const queryMode = cfg._embedMode || cfg.mode;
    worker.postMessage({ type: 'encodeQuery', text: queryInput, cfg: { ...cfg, mode: queryMode, query: true } });
  }
});

clearBtn.addEventListener('click', () => {
  q.value = '';
  qImg.value = '';
  results.textContent = '';
  searchVec = null;
  paintMatches(new Set());
});

// ---- Tagging System Event Handlers ----

selectionModeEl?.addEventListener('change', () => {
  selectionMode = selectionModeEl.value;
  if (selectionMode === 'off') {
    selectedNodes.clear();
    updateSelectionUI();
    refreshVisualization();
  }
});

clearSelectionBtn?.addEventListener('click', () => {
  selectedNodes.clear();
  updateSelectionUI();
  refreshVisualization();
});

addTagBtn?.addEventListener('click', () => {
  const tagName = newTagInput.value.trim();
  if (!tagName) {
    alert('Enter a tag name');
    return;
  }
  if (selectedNodes.size === 0) {
    alert('Select nodes first');
    return;
  }

  // Add tag to selected nodes
  if (!allTags.has(tagName)) {
    allTags.set(tagName, new Set());
    // Assign a color to new tag
    const colorIndex = allTags.size - 1;
    tagColors[tagName] = colors[colorIndex % colors.length];
  }

  selectedNodes.forEach(nodeId => {
    allTags.get(tagName).add(nodeId);
    if (!nodes[nodeId].tags) nodes[nodeId].tags = new Set();
    nodes[nodeId].tags.add(tagName);
  });

  newTagInput.value = '';
  updateTagUI();
  refreshVisualization();
});

removeTagBtn?.addEventListener('click', () => {
  const tagName = newTagInput.value.trim();
  if (!tagName) {
    alert('Enter a tag name to remove');
    return;
  }
  if (selectedNodes.size === 0) {
    alert('Select nodes first');
    return;
  }

  if (!allTags.has(tagName)) {
    alert('Tag does not exist');
    return;
  }

  selectedNodes.forEach(nodeId => {
    allTags.get(tagName).delete(nodeId);
    if (nodes[nodeId].tags) {
      nodes[nodeId].tags.delete(tagName);
    }
  });

  // Remove tag entirely if no nodes have it
  if (allTags.get(tagName).size === 0) {
    allTags.delete(tagName);
    delete tagColors[tagName];
  }

  newTagInput.value = '';
  updateTagUI();
  refreshVisualization();
});

colorModeEl?.addEventListener('change', () => {
  colorMode = colorModeEl.value;
  refreshVisualization();
});

tagFilterEl?.addEventListener('change', () => {
  refreshVisualization();
});

function updateSelectionUI() {
  if (selectedCountEl) {
    selectedCountEl.textContent = selectedNodes.size.toString();
  }

  // Show tags common to selected nodes
  if (currentTagsEl && selectedNodes.size > 0) {
    const tagCounts = new Map();
    selectedNodes.forEach(nodeId => {
      const node = nodes[nodeId];
      if (node.tags) {
        node.tags.forEach(tag => {
          tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1);
        });
      }
    });

    currentTagsEl.innerHTML = tagCounts.size === 0
      ? '<div class="muted small">No tags on selected items</div>'
      : '<div class="muted small">Tags on selected items:</div>' +
        Array.from(tagCounts.entries()).map(([tag, count]) =>
          `<span class="tag-badge">${esc(tag)} (${count}/${selectedNodes.size})</span>`
        ).join('');
  } else if (currentTagsEl) {
    currentTagsEl.innerHTML = '<div class="muted small">Select items to view/add tags</div>';
  }
}

function updateTagUI() {
  updateSelectionUI();

  // Update tag filter dropdown
  if (tagFilterEl) {
    const selectedFilters = Array.from(tagFilterEl.selectedOptions).map(o => o.value);
    tagFilterEl.innerHTML = '<option value="all">All items</option>';
    allTags.forEach((nodeIds, tagName) => {
      const opt = document.createElement('option');
      opt.value = tagName;
      opt.textContent = `${tagName} (${nodeIds.size})`;
      if (selectedFilters.includes(tagName)) opt.selected = true;
      tagFilterEl.appendChild(opt);
    });
  }

  // Show all tags
  if (allTagsEl) {
    if (allTags.size === 0) {
      allTagsEl.style.display = 'none';
    } else {
      allTagsEl.style.display = 'block';
      allTagsEl.innerHTML = '<div class="muted small">All tags:</div>' +
        Array.from(allTags.entries()).map(([tag, nodeIds]) =>
          `<span class="tag-badge" style="background:${tagColors[tag]}">${esc(tag)} (${nodeIds.size})</span>`
        ).join('');
    }
  }
}

function refreshVisualization() {
  if (!deckInstance || !deckInstance._createLayer) return;

  // Get filtered node IDs
  const selectedFilters = tagFilterEl ? Array.from(tagFilterEl.selectedOptions).map(o => o.value) : [];
  let filteredNodeIds = null;

  if (selectedFilters.length > 0 && !selectedFilters.includes('all')) {
    filteredNodeIds = new Set();
    selectedFilters.forEach(tagName => {
      if (allTags.has(tagName)) {
        allTags.get(tagName).forEach(nodeId => filteredNodeIds.add(nodeId));
      }
    });
  }

  const newLayer = deckInstance._createLayer(highlightedNodes, selectedNodes, filteredNodeIds);
  deckInstance.setProps({ layers: [newLayer] });
}

function setupWorkerHandlers() {
  if (!worker) return;

  worker.onmessage = async (ev) => {
    const { type, data } = ev.data || {};

    if (type === 'progress') {
      setBar(data.pct, data.msg || '');
    } else if (type === 'batch') {
      embeddings.push(...data.embeddings);
      setBar(data.pct, data.msg);
    } else if (type === 'done') {
      setBar(88, 'Clustering…');
      clusters = kMeans(embeddings, cfg.k);
      setBar(92, 'UMAP (2D)…');
      coords = await umap2D(embeddings);
      setBar(96, 'Preparing visualization…');
      await buildNodesAndViz();
      setBar(100, 'Ready!');
      progressPanel.style.display = 'none';
      el('search').style.display = 'block';
      viz.style.display = 'block';
      saveBtn.disabled = false;
      workerReady = true;
      updateQueryAvailability();
    } else if (type === 'qvec') {
      // Handle semantic search results
      searchVec = data.vec;
      const thr = parseFloat(th.value);
      const sims = embeddings.map((e, i) => ({ i, s: cosSim(searchVec, e) }))
        .filter(o => o.s >= thr)
        .sort((a, b) => b.s - a.s);
      paintMatches(new Set(sims.map(o => o.i)));

      // Render clickable results
      if (sims.length === 0) {
        results.innerHTML = 'No matches — try lowering the threshold.';
      } else {
        results.innerHTML = `Found ${sims.length} matches (top 10):<br><br>`;
        const resultList = document.createElement('div');
        resultList.style.display = 'flex';
        resultList.style.flexDirection = 'column';
        resultList.style.gap = '8px';

        sims.slice(0, 10).forEach(o => {
          const lab = cfg.label ? csv[o.i][cfg.label] : `Row ${o.i + 1}`;
          const resultItem = document.createElement('div');
          resultItem.style.cursor = 'pointer';
          resultItem.style.padding = '6px';
          resultItem.style.borderRadius = '4px';
          resultItem.style.transition = 'background 0.2s';
          resultItem.innerHTML = `<b>${esc(lab)}</b> — sim ${o.s.toFixed(3)}`;

          resultItem.addEventListener('mouseenter', () => {
            resultItem.style.background = '#e8ecff';
          });
          resultItem.addEventListener('mouseleave', () => {
            resultItem.style.background = 'transparent';
          });
          resultItem.addEventListener('click', () => {
            // Highlight only this node
            paintMatches(new Set([o.i]));
            // Update result display to show which one is selected
            resultList.querySelectorAll('div').forEach(el => {
              el.style.fontWeight = 'normal';
              el.style.background = 'transparent';
            });
            resultItem.style.fontWeight = 'bold';
            resultItem.style.background = '#e8ecff';

            // Zoom and center on the selected node
            if (deckInstance && nodes[o.i] && currentViewState) {
              const node = nodes[o.i];
              const [x, y] = node.position;

              // Zoom in quite a bit (higher zoom value = closer)
              const targetZoom = currentViewState.zoom + 3;

              // Update viewState with transition (controlled mode)
              currentViewState = {
                ...currentViewState,
                target: [x, y, 0],
                zoom: targetZoom,
                transitionDuration: 500,
                transitionInterpolator: new LinearInterpolator(['target', 'zoom'])
              };

              // Apply the new viewState with animation
              deckInstance.setProps({ viewState: currentViewState });
            }
          });

          resultList.appendChild(resultItem);
        });

        results.appendChild(resultList);
      }
    } else if (type === 'error') {
      alert('Worker error: ' + data.message);
      progressPanel.style.display = 'none';
      configPanel.style.display = 'block';
    }
  };
}

async function buildNodesAndViz() {
  const g = document.getElementById('graph-container');
  g.innerHTML = '';

  // Create canvas for deck.gl
  const canvas = document.createElement('canvas');
  canvas.id = 'deck-canvas';
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  g.appendChild(canvas);

  // Build nodes array with UMAP coordinates
  nodes = coords.map((xy, i) => ({
    id: i,
    position: [xy[0], xy[1], 0],  // deck.gl uses [x, y, z] format
    cluster: clusters[i],
    text: cfg.text ? csv[i][cfg.text] : '',
    label: cfg.label ? csv[i][cfg.label] : `Row ${i + 1}`,
    link: cfg.link ? csv[i][cfg.link] : null,
    image: cfg.image ? csv[i][cfg.image] : null,
    tags: new Set()  // Initialize empty tag set
  }));

  // Calculate center point for initial view
  const xValues = coords.map(xy => xy[0]);
  const yValues = coords.map(xy => xy[1]);
  const centerX = (Math.min(...xValues) + Math.max(...xValues)) / 2;
  const centerY = (Math.min(...yValues) + Math.max(...yValues)) / 2;
  const xSpan = Math.max(...xValues) - Math.min(...xValues);
  const ySpan = Math.max(...yValues) - Math.min(...yValues);
  const maxSpan = Math.max(xSpan, ySpan);

  // Calculate appropriate zoom level (zoom 0 = 1 unit per pixel)
  const containerWidth = g.clientWidth || 800;
  const initialZoom = maxSpan > 0 ? Math.log2(containerWidth / (maxSpan * 1.5)) : 0;

  // Create the scatter plot layer
  const createLayer = (highlightedIndices = new Set(), selectedIndices = new Set(), filteredIndices = null) => {
    const baseRadius = DEFAULT_NODE_SIZE;
    // Convert Sets to Arrays for updateTriggers
    const highlightedArray = Array.from(highlightedIndices);
    const selectedArray = Array.from(selectedIndices);
    const filterArray = filteredIndices ? Array.from(filteredIndices) : null;

    // Filter data if needed
    const displayData = filteredIndices ? nodes.filter(n => filteredIndices.has(n.id)) : nodes;

    return new ScatterplotLayer({
      id: 'scatter-layer',
      data: displayData,
      pickable: true,
      opacity: 1,
      stroked: true,
      filled: true,
      // Use common (data-space) units so nodes scale with UMAP coordinates
      radiusUnits: 'common',
      radiusScale: 1,
      radiusMinPixels: 3,  // Ensure nodes are always visible even when zoomed out
      radiusMaxPixels: 100,  // Cap maximum size when zoomed in
      lineWidthUnits: 'common',
      lineWidthMinPixels: 1,
      getPosition: d => d.position,
      getRadius: d => {
        if (highlightedIndices.has(d.id)) return baseRadius * 2.5;
        if (selectedIndices.has(d.id)) return baseRadius * 1.8;
        return baseRadius;
      },
      getFillColor: d => {
        // Search results (gold)
        if (highlightedIndices.has(d.id)) {
          return [255, 215, 0, 255];
        }
        // Selected nodes (cyan)
        if (selectedIndices.has(d.id)) {
          return [0, 255, 255, 200];
        }
        // Color by tag mode
        if (colorMode === 'tag' && d.tags && d.tags.size > 0) {
          const firstTag = Array.from(d.tags)[0];
          const tagColor = tagColors[firstTag] || colors[0];
          const rgb = hexToRgb(tagColor);
          return [rgb.r, rgb.g, rgb.b, 255];
        }
        // Default: color by cluster
        const color = colors[d.cluster % colors.length];
        const rgb = hexToRgb(color);
        return [rgb.r, rgb.g, rgb.b, 255];
      },
      getLineColor: d => {
        if (highlightedIndices.has(d.id)) return [255, 0, 0, 255];
        if (selectedIndices.has(d.id)) return [0, 200, 200, 255];
        return [0, 0, 0, 80];
      },
      getLineWidth: d => {
        if (highlightedIndices.has(d.id)) return baseRadius * 0.3;
        if (selectedIndices.has(d.id)) return baseRadius * 0.2;
        return baseRadius * 0.1;
      },
      // Tell deck.gl to recalculate these attributes when state changes
      updateTriggers: {
        getRadius: [highlightedArray, selectedArray, colorMode],
        getFillColor: [highlightedArray, selectedArray, colorMode, filterArray],
        getLineColor: [highlightedArray, selectedArray],
        getLineWidth: [highlightedArray, selectedArray]
      }
    });
  };

  // Store initial view state
  currentViewState = {
    target: [centerX, centerY, 0],
    zoom: initialZoom
  };

  // Create deck.gl instance (controlled mode for programmatic control)
  deckInstance = new Deck({
    canvas: 'deck-canvas',
    width: '100%',
    height: '100%',
    glOptions: { alpha: false }, // make canvas opaque to avoid dark halos on blending
    parameters: { clearColor: [1, 1, 1, 1] }, // clear to white each frame
    views: [new OrthographicView({ controller: true })],
    viewState: currentViewState,
    onViewStateChange: ({ viewState }) => {
      // Update our tracked state and re-render (controlled mode)
      currentViewState = viewState;
      deckInstance.setProps({ viewState: currentViewState });
    },
    layers: [createLayer()],
    onClick: (info, event) => {
      if (info.object) {
        const nodeId = info.object.id;

        // Handle selection mode
        if (selectionMode === 'single') {
          selectedNodes.clear();
          selectedNodes.add(nodeId);
          updateSelectionUI();
          refreshVisualization();
        } else if (selectionMode === 'multi') {
          if (event.srcEvent?.ctrlKey || event.srcEvent?.metaKey) {
            // Toggle selection with Ctrl/Cmd
            if (selectedNodes.has(nodeId)) {
              selectedNodes.delete(nodeId);
            } else {
              selectedNodes.add(nodeId);
            }
            updateSelectionUI();
            refreshVisualization();
          } else {
            // Without Ctrl/Cmd, show modal
            showModal(info.object, nodeId);
          }
        } else {
          // Off mode - just show modal
          showModal(info.object, nodeId);
        }
      }
    },
    getTooltip: ({ object }) => {
      if (object) {
        const tagList = object.tags && object.tags.size > 0
          ? '<br><span style="font-size:0.9em">Tags: ' + Array.from(object.tags).map(t => `<span style="background:#dc2626;padding:2px 4px;border-radius:3px;margin:2px">${esc(t)}</span>`).join(' ') + '</span>'
          : '';
        return {
          html: `<strong>${esc(object.label)}</strong>${tagList}`,
          style: {
            backgroundColor: '#333',
            color: '#fff',
            padding: '8px',
            borderRadius: '4px'
          }
        };
      }
    }
  });

  // Store the layer creator for updates
  deckInstance._createLayer = createLayer;

  // Initialize tag UI
  updateTagUI();
}

function paintMatches(set) {
  if (!deckInstance || !deckInstance._createLayer) return;

  highlightedNodes = set;  // Store for later updates
  refreshVisualization();
}

function showModal(data, idx) {
  let modal = document.getElementById('modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'modal';
    modal.className = 'modal';

    const content = document.createElement('div');
    content.className = 'modal-content';

    const closeBtn = document.createElement('span');
    closeBtn.id = 'close';
    closeBtn.className = 'close';
    closeBtn.innerHTML = '&times;';

    const title = document.createElement('h3');
    title.id = 'mtitle';
    title.textContent = 'Item';

    const body = document.createElement('div');
    body.id = 'mbody';

    content.appendChild(closeBtn);
    content.appendChild(title);
    content.appendChild(body);
    modal.appendChild(content);
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
    closeBtn.addEventListener('click', () => modal.style.display = 'none');
  }

  // Update content
  const titleEl = modal.querySelector('#mtitle');
  const bodyEl = modal.querySelector('#mbody');
  titleEl.textContent = data.label || `Row ${idx + 1}`;

  // Clear body
  bodyEl.innerHTML = '';

  if (data.image) {
    const preview = document.createElement('div');
    preview.className = 'preview';

    const img = document.createElement('img');
    img.src = esc(data.image);
    img.alt = 'preview';

    const cap = document.createElement('div');
    cap.className = 'small muted';
    cap.innerHTML = 'Image from column <b>' + esc(cfg.image) + '</b>';

    preview.appendChild(img);
    preview.appendChild(cap);
    bodyEl.appendChild(preview);

    const spacer = document.createElement('div');
    spacer.className = 'spacer';
    bodyEl.appendChild(spacer);
  }

  if (data.text) {
    const box = document.createElement('div');
    box.className = 'info-box';
    box.style.whiteSpace = 'pre-wrap';
    box.textContent = data.text;
    bodyEl.appendChild(box);
  }

  if (data.link) {
    const p = document.createElement('p');
    const strong = document.createElement('strong');
    strong.textContent = 'Link:';
    const space = document.createTextNode(' ');
    const a = document.createElement('a');
    a.href = data.link;
    a.target = '_blank';
    a.textContent = data.link;
    p.appendChild(strong);
    p.appendChild(space);
    p.appendChild(a);
    bodyEl.appendChild(p);
  }

  const meta = document.createElement('p');
  meta.className = 'small muted';
  meta.innerHTML = 'Cluster <b>' + data.cluster + '</b> • Index <b>' + idx + '</b>';
  bodyEl.appendChild(meta);

  modal.style.display = 'block';
}

// ---- math & ml utils ----
function cosSim(a, b) { let dot = 0, na = 0, nb = 0; for (let i = 0; i < a.length; i++) { dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i]; } na = Math.sqrt(na); nb = Math.sqrt(nb); return (na === 0 || nb === 0) ? 0 : dot / (na * nb); }

function kMeans(data, k, maxIter = 100) {
  const n = data.length, d = data[0].length;
  const idx = [...Array(n).keys()].sort(() => Math.random() - .5);
  const cent = []; for (let i = 0; i < k; i++) cent.push([...data[idx[i]]]);
  let assign = new Array(n).fill(0), changed = true, it = 0;
  while (changed && it < maxIter) {
    changed = false;
    for (let i = 0; i < n; i++) {
      let best = 0, md = Infinity;
      for (let j = 0; j < k; j++) {
        let s = 0;
        for (let p = 0; p < d; p++) { const diff = data[i][p] - cent[j][p]; s += diff * diff; }
        const dist = Math.sqrt(s);
        if (dist < md) { md = dist; best = j; }
      }
      if (assign[i] !== best) { assign[i] = best; changed = true; }
    }
    const sums = Array.from({ length: k }, () => Array(d).fill(0));
    const counts = Array(k).fill(0);
    for (let i = 0; i < n; i++) { const c = assign[i]; counts[c]++; for (let p = 0; p < d; p++) { sums[c][p] += data[i][p]; } }
    for (let j = 0; j < k; j++) { if (counts[j] > 0) { for (let p = 0; p < d; p++) { cent[j][p] = sums[j][p] / counts[j]; } } }
    it++;
  }
  return assign;
}

async function umap2D(vecs) {
  const u = new UMAP.UMAP({ nComponents: 2, nNeighbors: 15, minDist: 0.1, spread: 1.0 });
  return await u.fitAsync(vecs);
}

function buildItems(rows, cfg) {
  const items = [];
  for (let i = 0; i < rows.length; i++) {
    const rec = rows[i];
    const t = cfg.text ? (rec[cfg.text] || '') : '';
    const im = cfg.image ? (rec[cfg.image] || '') : '';
    items.push({ index: i, text: t, image: im });
  }
  return items;
}

// ---- worker ----
function createWorker() {
  const src = [
    "self.onmessage = async (ev) => {",
    "  const { type, cfg, items, text, image } = ev.data || {};",
    "  try {",
    "    if (type === 'start') { await runBatches(cfg, items); }",
    "    else if (type === 'encodeQuery') { const v = await encodeQuery(cfg, text, image); self.postMessage({ type: 'qvec', data: { vec: v } }); }",
    "  } catch (e) { self.postMessage({ type: 'error', data: { message: e.message } }); }",
    "};",
    "",
    "function l2Normalize(vec) { let n = 0; for (let i = 0; i < vec.length; i++) n += vec[i] * vec[i]; n = Math.sqrt(n) || 1; for (let i = 0; i < vec.length; i++) vec[i] /= n; return vec; }",
    "const DUMMY_IMG = \"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7W8uQAAAAASUVORK5CYII=\";",
    "async function encodeImage(imgPipe, url, family) {",
    "  const out = await imgPipe(url);",
    "  if (family === 'ijepa') {",
    "    const pooled = out.mean(1);",
    "    return l2Normalize(Array.from(pooled[0].data));",
    "  }",
    "  const data = out.data ? Array.from(out.data) : Array.from(out[0].data);",
    "  return l2Normalize(data);",
    "}",
    "",
    "async function runBatches(cfg, items) {",
    "  const N = items.length; const B = Math.max(1, Math.min(64, cfg.batch || 16));",
    "  self.postMessage({ type: 'progress', data: { pct: 4, msg: 'Loading transformers.js…' } });",
    "  const t = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.0');",
    "  t.env.allowRemoteModels = true;",
    "  t.env.allowLocalModels = false;",
    "  t.env.useBrowserCache = true;",
    "  let textPipe = null, imgPipe = null;",
    "  if (cfg.mode === 'text') {",
    "    self.postMessage({ type: 'progress', data: { pct: 8, msg: 'Loading all-MiniLM-L6-v2…' } });",
    "    textPipe = await t.pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');",
    "  } else {",
    "    // For multimodal, only load what we need",
    "    const needsText = cfg.source === 'text' || cfg.source === 'both';",
    "    const needsImage = cfg.source === 'image' || cfg.source === 'both';",
    "    const isJEPA = (cfg.imageEmbedder || '').startsWith('onnx-community/ijepa');",
    "    const imgFamily = isJEPA ? 'ijepa' : 'clip';",
    "    if (needsText) {",
    "      self.postMessage({ type: 'progress', data: { pct: 8, msg: 'Loading CLIP (text)…' } });",
    "      textPipe = await t.pipeline('feature-extraction', 'Xenova/clip-vit-base-patch32');",
    "    }",
    "    if (needsImage) {",
    "      self.postMessage({ type: 'progress', data: { pct: 12, msg: 'Loading ' + imgFamily.toUpperCase() + ' (image)…' } });",
    "      imgPipe  = await t.pipeline('image-feature-extraction', cfg.imageEmbedder || 'Xenova/clip-vit-base-patch32', { dtype: 'q8' });",
    "    }",
    "    var IMG_DIM = null;",
    "    if (imgPipe) {",
    "      const probe = await encodeImage(imgPipe, DUMMY_IMG, imgFamily);",
    "      IMG_DIM = probe.length;",
    "    }",
    "    const ZERO_IMG = () => new Array(IMG_DIM || 512).fill(0);",
    "  }",
    "  for (let i = 0; i < N; i += B) {",
    "    const batch = items.slice(i, Math.min(i + B, N));",
    "    const vecs = [];",
    "    if (cfg.mode === 'text') {",
    "      const texts = batch.map(o => o.text || '');",
    "      const v = await textPipe(texts, { pooling: 'mean', normalize: true });",
    "      for (let j = 0; j < texts.length; j++) vecs.push(Array.from(v[j].data));",
    "    } else {",
    "      if (cfg.source === 'text') {",
    "        const texts = batch.map(o => o.text || '');",
    "        const v = await textPipe(texts, { pooling: 'mean', normalize: true });",
    "        for (let j = 0; j < texts.length; j++) vecs.push(Array.from(v[j].data));",
    "      } else if (cfg.source === 'image') {",
    "        for (const o of batch) {",
    "          const u = o.image || '';",
    "          if (u && u.trim() !== '') {",
    "            try {",
    "              const v = await encodeImage(imgPipe, u, imgFamily);",
    "              vecs.push(v);",
    "            } catch (err) {",
    "              console.warn('Failed to load image:', u, err.message);",
    "              vecs.push(ZERO_IMG());",
    "            }",
    "          } else {",
    "            // Empty image URL - return zero vector",
    "            vecs.push(ZERO_IMG());",
    "          }",
    "        }",
    "      } else {",
    "        // Source is 'both' - combine text and image",
    "        if (cfg.imageEmbedder && cfg.imageEmbedder.startsWith('onnx-community/ijepa')) { throw new Error(\"I-JEPA doesn't support text+image fusion. Choose source='image'.\"); }",
    "        for (const o of batch) {",
    "          const hasText = o.text && o.text.trim() !== '';",
    "          const hasImage = o.image && o.image.trim() !== '';",
    "          let outv = null;",
    "          if (hasText && hasImage) {",
    "            const vt = await textPipe(o.text, { pooling: 'mean', normalize: true });",
    "            try {",
    "              const vi = await encodeImage(imgPipe, o.image, imgFamily);",
    "              outv = meanNormalize([Array.from(vt.data), vi]);",
    "            } catch (err) {",
    "              // Image load failed, use text only",
    "              outv = Array.from(vt.data);",
    "            }",
    "          } else if (hasText) {",
    "            const vt = await textPipe(o.text, { pooling: 'mean', normalize: true });",
    "            outv = Array.from(vt.data);",
    "          } else if (hasImage) {",
    "            try {",
    "              const vi = await encodeImage(imgPipe, o.image, imgFamily);",
    "              outv = vi;",
    "            } catch (err) {",
    "              // Image load failed, use zero vector",
    "              outv = ZERO_IMG();",
    "            }",
    "          } else {",
    "            // Empty embeddings shouldn't happen, but handle gracefully",
    "            outv = ZERO_IMG();",
    "          }",
    "          vecs.push(outv);",
    "        }",
    "      }",
    "    }",
    "    const done = Math.min(i + B, N);",
    "    const pct = 12 + (done / N) * 70;",
    "    self.postMessage({ type: 'batch', data: { embeddings: vecs, pct, msg: 'Embedding ' + done + '/' + N } });",
    "  }",
    "  self.postMessage({ type: 'done' });",
    "}",
    "",
    "async function encodeQuery(cfg, text, image) {",
    "  const t = await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.0');",
    "  t.env.allowRemoteModels = true;",
    "  t.env.allowLocalModels = false;",
    "  t.env.useBrowserCache = true;",
    "",
    "  if (image) {",
    "    if (cfg.mode !== 'multimodal') {",
    "      throw new Error('Image search requires image embeddings.');",
    "    }",
    "    const isJEPA = (cfg.imageEmbedder || '').startsWith('onnx-community/ijepa');",
    "    const imgFamily = isJEPA ? 'ijepa' : 'clip';",
    "    const imgPipe = await t.pipeline('image-feature-extraction', cfg.imageEmbedder || 'Xenova/clip-vit-base-patch32', { dtype: 'q8' });",
    "    return await encodeImage(imgPipe, image, imgFamily);",
    "  }",
    "",
    "  if (cfg._embedFamily === 'ijepa') {",
    "    throw new Error('This dataset was embedded with I-JEPA (image-only). Use an image query.');",
    "  }",
    "",
    "  // Handle text queries",
    "  if (cfg.mode === 'text') {",
    "    const pipe = await t.pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');",
    "    const out = await pipe(text, { pooling: 'mean', normalize: true });",
    "    return Array.from(out.data);",
    "  } else {",
    "    // For CLIP text encoding, use tokenizer + text model explicitly",
    "    const tokenizer = await t.AutoTokenizer.from_pretrained('Xenova/clip-vit-base-patch32');",
    "    const text_model = await t.CLIPTextModelWithProjection.from_pretrained('Xenova/clip-vit-base-patch32');",
    "    const inputs = await tokenizer(text);",
    "    const output = await text_model(inputs);",
    "    // Get the text embeddings (already projected)",
    "    const embeddings = output.text_embeds;",
    "    // Normalize the embeddings",
    "    const vec = Array.from(embeddings.data);",
    "    let norm = 0;",
    "    for (let i = 0; i < vec.length; i++) norm += vec[i] * vec[i];",
    "    norm = Math.sqrt(norm) || 1;",
    "    for (let i = 0; i < vec.length; i++) vec[i] /= norm;",
    "    return vec;",
    "  }",
    "}",
    "",
    "function meanNormalize(vecs) {",
    "  const d = vecs[0].length; const out = new Array(d).fill(0);",
    "  for (const v of vecs) { for (let i = 0; i < d; i++) out[i] += v[i]; }",
    "  for (let i = 0; i < d; i++) out[i] /= vecs.length;",
    "  let n = 0; for (let i = 0; i < d; i++) n += out[i] * out[i]; n = Math.sqrt(n) || 1;",
    "  for (let i = 0; i < d; i++) out[i] /= n;",
    "  return out;",
    "}"
  ].join("\n");

  const blob = new Blob([src], { type: 'application/javascript' });
  return new Worker(URL.createObjectURL(blob));
}
