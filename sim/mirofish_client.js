// sim/mirofish_client.js — Cliente para el motor de simulación MiroFish (Khipu Finance)
// Compatible con la API real de MiroFish (github.com/666ghj/MiroFish)
// El proxy server.py mapea /api/mirofish/<path> → MIROFISH_URL/api/<path>

const MIROFISH_BASE = (typeof BASE !== 'undefined' ? BASE : '') + '/api/mirofish';

const MiroFishClient = {

  async _req(path, method = 'GET', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(`${MIROFISH_BASE}${path}`, opts);
    if (!r.ok) throw new Error(`MiroFish ${path}: HTTP ${r.status}`);
    return r.json();
  },

  // Poll a task/status endpoint until status === 'completed' | 'failed'
  async _poll(getStatus, onProgress, maxWaitMs = 300000, intervalMs = 3000) {
    const t0 = Date.now();
    return new Promise((resolve, reject) => {
      const tick = async () => {
        if (Date.now() - t0 > maxWaitMs) return reject(new Error('Timeout esperando MiroFish'));
        try {
          const data = await getStatus();
          if (onProgress) onProgress(data);
          const st = data?.data?.status || data?.status;
          if (st === 'completed') return resolve(data);
          if (st === 'failed') return reject(new Error(data?.data?.error || 'MiroFish task failed'));
        } catch (_) { /* reintentar */ }
        setTimeout(tick, intervalMs);
      };
      tick();
    });
  },

  // ── Graph ────────────────────────────────────────────────────────────────────

  async buildGraph(seedText, description) {
    // MiroFish /graph/build is async: POST → {task_id}, then poll /graph/task/<id>
    const fd = new FormData();
    fd.append('files', new Blob([seedText], { type: 'text/plain' }), 'khipu_scenario.txt');
    fd.append('description', description || '');
    fd.append('lang', 'en');
    const r = await fetch(`${MIROFISH_BASE}/graph/build`, { method: 'POST', body: fd });
    if (!r.ok) throw new Error(`MiroFish /graph/build: HTTP ${r.status}`);
    const init = await r.json();
    const taskId = init?.data?.task_id || init?.task_id;
    if (!taskId) throw new Error('MiroFish no devolvió task_id en /graph/build');

    // Poll until graph is built
    const result = await this._poll(
      () => this._req(`/graph/task/${taskId}`),
      null, 180000, 3000,
    );
    const graphId = result?.data?.graph_id || result?.graph_id;
    if (!graphId) throw new Error('MiroFish no devolvió graph_id tras completar el build');
    return { graph_id: graphId, data: { graph_id: graphId } };
  },

  // ── Simulation ───────────────────────────────────────────────────────────────

  async createSimulation(params) {
    return this._req('/simulation/create', 'POST', params);
  },

  async prepareSimulation(simId) {
    // /simulation/prepare is async → poll /simulation/prepare/status
    await this._req('/simulation/prepare', 'POST', { simulation_id: simId });
    await this._poll(
      () => this._req('/simulation/prepare/status', 'POST', { simulation_id: simId }),
      null, 120000, 2500,
    );
  },

  async startSimulation(simId, rounds = 20) {
    return this._req('/simulation/start', 'POST', { simulation_id: simId, rounds });
  },

  async pollSimulation(simId, onProgress, maxWaitMs = 300000) {
    return this._poll(
      () => this._req(`/simulation/${simId}`),
      onProgress, maxWaitMs, 4000,
    );
  },

  // ── Report ───────────────────────────────────────────────────────────────────

  async generateReport(simId, question) {
    return this._req('/report/generate', 'POST', { simulation_id: simId, question });
  },

  async pollReport(reportId, onProgress, maxWaitMs = 180000) {
    await this._poll(
      () => this._req(`/report/${reportId}/progress`),
      onProgress, maxWaitMs, 3000,
    );
    return this._req(`/report/${reportId}`);
  },

  async chatWithReport(reportId, message) {
    return this._req('/report/chat', 'POST', { report_id: reportId, message });
  },

  // ── Health ───────────────────────────────────────────────────────────────────

  async checkHealth() {
    try {
      const r = await fetch(`${MIROFISH_BASE}/health`, { signal: AbortSignal.timeout(5000) });
      return r.ok;
    } catch { return false; }
  },
};

window.MiroFishClient = MiroFishClient;
