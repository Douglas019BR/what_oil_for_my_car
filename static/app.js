const makeSelect = document.getElementById('make');
const modelSelect = document.getElementById('model');
const variantSelect = document.getElementById('variant');
const statusEl = document.getElementById('status');
const emptyEl = document.getElementById('empty');
const wrapperEl = document.getElementById('table-wrapper');
const bodyEl = document.getElementById('results-body');
const countEl = document.getElementById('result-count');

let selectedVariant = null;
let recommendationRequestId = 0;

const themeToggle = document.getElementById('theme-toggle');
const THEME_KEY = 'what-oil-theme';
let currentTheme = null;

function readStoredTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

function storeTheme(theme) {
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch {
    return false;
  }
  return true;
}

function preferredTheme() {
  const saved = readStoredTheme();
  if (saved === 'dark' || saved === 'light') return saved;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  currentTheme = theme;
  document.documentElement.dataset.theme = theme;
  themeToggle.textContent = theme === 'dark' ? 'Modo claro' : 'Modo escuro';
  themeToggle.setAttribute('aria-pressed', String(theme === 'dark'));
}

themeToggle.addEventListener('click', () => {
  const next = currentTheme === 'dark' ? 'light' : 'dark';
  storeTheme(next);
  applyTheme(next);
});

applyTheme(preferredTheme());

function setStatus(message) {
  statusEl.textContent = message;
}

function fillSelect(select, items, placeholder) {
  select.innerHTML = '';
  const first = document.createElement('option');
  first.value = '';
  first.textContent = placeholder;
  select.append(first);
  for (const item of items) {
    const option = document.createElement('option');
    option.value = typeof item === 'string' ? item : JSON.stringify(item);
    option.textContent = typeof item === 'string' ? item : item.label;
    select.append(option);
  }
  select.disabled = items.length === 0;
}

function clearResults(message) {
  bodyEl.innerHTML = '';
  wrapperEl.hidden = true;
  emptyEl.hidden = false;
  emptyEl.textContent = message;
  countEl.textContent = '';
}

async function fetchJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Falha ao consultar: ${response.status}`);
  }
  return response.json();
}

async function loadMakes() {
  try {
    setStatus('Carregando marcas...');
    const makes = await fetchJson('/api/makes');
    fillSelect(makeSelect, makes, 'Selecione a marca');
    setStatus('');
  } catch (error) {
    setStatus(error.message);
  }
}

async function loadModels() {
  const make = makeSelect.value;
  selectedVariant = null;
  fillSelect(variantSelect, [], 'Todas as versões');
  clearResults('Selecione um modelo para ver as recomendações.');
  fillSelect(modelSelect, [], 'Selecione o modelo');
  if (!make) {
    return;
  }
  try {
    setStatus('Carregando modelos...');
    const models = await fetchJson(`/api/models?make=${encodeURIComponent(make)}`);
    fillSelect(modelSelect, models, 'Selecione o modelo');
    setStatus('');
  } catch (error) {
    setStatus(error.message);
  }
}

async function loadVariants() {
  const make = makeSelect.value;
  const model = modelSelect.value;
  selectedVariant = null;
  fillSelect(variantSelect, [], 'Todas as versões');
  if (!make || !model) {
    clearResults('Selecione um modelo para ver as recomendações.');
    return;
  }
  try {
    setStatus('Carregando versões...');
    const variants = await fetchJson(
      `/api/variants?make=${encodeURIComponent(make)}&model=${encodeURIComponent(model)}`,
    );
    fillSelect(variantSelect, variants, 'Todas as versões');
    setStatus('');
  } catch (error) {
    setStatus(error.message);
  }
}

function chooseVariant() {
  selectedVariant = variantSelect.value ? JSON.parse(variantSelect.value) : null;
}

function formatCell(value) {
  return value === null || value === undefined || value === '' ? '—' : String(value);
}

async function loadRecommendations() {
  const requestId = ++recommendationRequestId;
  const make = makeSelect.value;
  const model = modelSelect.value;
  if (!make || !model) {
    clearResults('Selecione uma marca e um modelo para ver as recomendações.');
    return;
  }

  const params = new URLSearchParams({ make, model });
  if (selectedVariant) {
    params.set('exact', '1');
    if (selectedVariant.engine) params.set('engine', selectedVariant.engine);
    if (selectedVariant.year_from !== null) params.set('year_from', selectedVariant.year_from);
    if (selectedVariant.year_to !== null) params.set('year_to', selectedVariant.year_to);
  }

  try {
    setStatus('Buscando recomendações...');
    const rows = await fetchJson(`/api/recommendations?${params}`);
    if (requestId !== recommendationRequestId) return;
    bodyEl.innerHTML = '';
    for (const row of rows) {
      const tr = document.createElement('tr');
      const values = [
        row.oil_brand,
        row.oil_name,
        row.sae_viscosity,
        row.oil_type,
        row.capacity_liters === null ? null : `${row.capacity_liters} L`,
        row.notes,
        row.source_pdf,
      ];
      for (const value of values) {
        const td = document.createElement('td');
        td.textContent = formatCell(value);
        tr.append(td);
      }
      bodyEl.append(tr);
    }
    wrapperEl.hidden = false;
    emptyEl.hidden = true;
    countEl.textContent = rows.length
      ? `${rows.length} recomendação(ões) encontrada(s).`
      : 'Nenhuma recomendação encontrada para esta combinação.';
    setStatus('');
  } catch (error) {
    if (requestId !== recommendationRequestId) return;
    clearResults(error.message);
  }
}

makeSelect.addEventListener('change', loadModels);
modelSelect.addEventListener('change', () => {
  loadVariants().then(loadRecommendations);
});
variantSelect.addEventListener('change', () => {
  chooseVariant();
  loadRecommendations();
});

loadMakes();
