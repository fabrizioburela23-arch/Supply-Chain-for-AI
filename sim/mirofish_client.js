// sim/mirofish_client.js — Cliente para el motor de simulación MiroFish (Khipu Finance)
// MiroFish corre en Docker (puerto 8000) y se accede vía el proxy /api/mirofish/* del
// server.py de Khipu. Ejecuta simulaciones multi-agente (estilo OASIS) sobre escenarios
// de cadena de suministro: construye grafo → genera perfiles de agentes → simula N rondas
// → genera reporte. El LLM puede ser Claude vía LiteLLM (ver docker-compose).

const MIROFISH_BASE = (typeof BASE !== 'undefined' ? BASE : '') + '/api/mirofish';

const MiroFishClient = {
  async _req(path, method = 'GET', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(`${MIROFISH_BASE}${path}`, opts);
    if (!r.ok) throw new Error(`MiroFish ${path}: HTTP ${r.status}`);
    return r.json();
  },

  async buildGraph(seedText, description) {
    const fd = new FormData();
    fd.append('files', new Blob([seedText], { type: 'text/plain' }), 'khipu_scenario.txt');
    fd.append('description', description);
    fd.append('lang', (typeof LANG !== 'undefined' && LANG === 'en') ? 'en' : 'en');
    return fetch(`${MIROFISH_BASE}/graph/build`, { method: 'POST', body: fd }).then(r => r.json());
  },

  async generateProfiles(graphId, goal) {
    return this._req('/simulation/generate-profiles', 'POST', { graph_id: graphId, goal });
  },

  async createSimulation(params) {
    return this._req('/simulation/create', 'POST', params);
  },

  async prepareSimulation(simId) {
    return this._req('/simulation/prepare', 'POST', { simulation_id: simId });
  },

  async startSimulation(simId, rounds = 20) {
    return this._req('/simulation/start', 'POST', { simulation_id: simId, rounds });
  },

  async pollSimulation(simId, onProgress, maxWaitMs = 300000) {
    const t0 = Date.now();
    return new Promise((resolve, reject) => {
      const poll = async () => {
        if (Date.now() - t0 > maxWaitMs) return reject(new Error('Simulation timeout'));
        try {
          const data = await this._req(`/simulation/${simId}`);
          if (onProgress) onProgress(data);
          const status = data.data?.status;
          if (status === 'completed') return resolve(data);
          if (status === 'failed') return reject(new Error(data.data?.error || 'Simulation failed'));
        } catch (e) { /* reintentar */ }
        setTimeout(poll, 4000);
      };
      poll();
    });
  },

  async generateReport(simId, question) {
    return this._req('/report/generate', 'POST', { simulation_id: simId, question });
  },

  async pollReport(reportId, onProgress, maxWaitMs = 180000) {
    const t0 = Date.now();
    return new Promise((resolve, reject) => {
      const poll = async () => {
        if (Date.now() - t0 > maxWaitMs) return reject(new Error('Report timeout'));
        try {
          const data = await this._req(`/report/${reportId}/progress`);
          if (onProgress) onProgress(data);
          if (data.data?.status === 'completed') {
            const report = await this._req(`/report/${reportId}`);
            return resolve(report);
          }
          if (data.data?.status === 'failed') return reject(new Error('Report failed'));
        } catch (e) { /* reintentar */ }
        setTimeout(poll, 3000);
      };
      poll();
    });
  },

  async chatWithReport(reportId, message) {
    return this._req('/report/chat', 'POST', { report_id: reportId, message });
  },

  async checkHealth() {
    try {
      const r = await fetch(`${MIROFISH_BASE}/health`);
      return r.ok;
    } catch { return false; }
  },
};

window.MiroFishClient = MiroFishClient;
