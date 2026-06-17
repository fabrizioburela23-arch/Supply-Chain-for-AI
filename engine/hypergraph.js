// engine/hypergraph.js — Hipergrafos temporales agénticos para Khipu Finance
// Una hiper-arista conecta MÚLTIPLES nodos a la vez (un evento que afecta a N empresas)
// y tiene fecha + severidad. Se renderiza como una esfera translúcida que envuelve
// al cluster afectado en el grafo 3D, con un timeline reproducible.
//
// Depende de: KhipuGraph3D (graph3d.js), NODE_BY_ID, getCatColorHex, DataLayer, Keys

class TemporalHypergraph {
  constructor(graph3d) {
    this.graph3d = graph3d;
    this.hyperedges = [];
    this.timeline = [];
    this.visualObjects = [];   // { sphere, line, he }
    this.currentPosition = 1.0; // 0=oldest, 1=present
  }

  addHyperedge(he) {
    this.hyperedges.push(he);
    this.timeline.push({ t: new Date(he.timestamp).getTime(), id: he.id });
    this.timeline.sort((a, b) => a.t - b.t);
    if (this.graph3d?.active) this._render3D(he);
    this._updateTimelineUI();
    this.save();
  }

  _render3D(he) {
    const affectedMeshes = (he.nodes_affected || [])
      .map(id => this.graph3d.nodeMeshes.get(id))
      .filter(Boolean);
    if (affectedMeshes.length < 2) return;

    const centroid = new THREE.Vector3();
    affectedMeshes.forEach(m => centroid.add(m.position));
    centroid.divideScalar(affectedMeshes.length);

    let maxR = 0;
    affectedMeshes.forEach(m => maxR = Math.max(maxR, centroid.distanceTo(m.position)));
    maxR += 25;

    const color = this._heColor(he.type);
    const severity = Math.min(10, Math.max(1, he.severity || 5));
    const opacity = 0.04 + severity * 0.006;

    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(maxR, 24, 16),
      new THREE.MeshBasicMaterial({
        color: new THREE.Color(color),
        transparent: true, opacity, wireframe: false,
        side: THREE.DoubleSide,
      })
    );
    sphere.position.copy(centroid);
    sphere.userData = { hyperedge: he, type: 'he_sphere' };
    this.graph3d.scene.add(sphere);

    affectedMeshes.forEach(m => {
      const geo = new THREE.BufferGeometry().setFromPoints([centroid, m.position]);
      const mat = new THREE.LineBasicMaterial({
        color: new THREE.Color(color), transparent: true, opacity: 0.5,
      });
      const line = new THREE.Line(geo, mat);
      this.graph3d.scene.add(line);
      this.visualObjects.push({ sphere, line, he });
    });

    this._flashNodes(he.nodes_affected, color);
  }

  _flashNodes(nodeIds, color) {
    (nodeIds || []).forEach(id => {
      const mesh = this.graph3d?.nodeMeshes?.get(id);
      if (!mesh) return;
      const origEmissive = mesh.material.emissiveIntensity;
      mesh.material.emissive.setStyle(color);
      mesh.material.emissiveIntensity = 1.5;
      setTimeout(() => {
        const n = NODE_BY_ID[id];
        if (n) mesh.material.emissive.set(getCatColorHex(n.cat));
        mesh.material.emissiveIntensity = origEmissive;
      }, 1200);
    });
  }

  _heColor(type) {
    const MAP = {
      geopolitical_shock: '#FF4444', supply_shock: '#F2C744',
      regulation: '#FF8800', market_event: '#52B1FF',
      earnings: '#3DE0C8', news_event: '#A78BFF',
      simulation: '#C58BFF', space_launch: '#FF6B35',
    };
    return MAP[type] || '#FFFFFF';
  }

  async fromNewsItem(newsItem, affectedNodeIds) {
    const severity = await this._estimateSeverity(newsItem.headline);
    const he = {
      id: 'he_' + Date.now(),
      type: 'news_event',
      timestamp: new Date((newsItem.datetime || Date.now() / 1000) * 1000).toISOString(),
      title: (newsItem.headline || '').slice(0, 100),
      description: newsItem.summary || newsItem.headline,
      severity,
      nodes_affected: (affectedNodeIds || []).slice(0, 20),
      node_impacts: {},
      duration_days: 7,
      news_source_urls: [newsItem.url],
    };
    this.addHyperedge(he);
    return he;
  }

  async _estimateSeverity(headline) {
    if (typeof Keys === 'undefined' || !Keys.has('claude')) return 5;
    try {
      const txt = await DataLayer.aiComplete(
        'You are a financial impact analyst. Rate news headline severity for the semiconductor/AI/space supply chain (1-10). Reply ONLY with a number.',
        `Severity 1-10: "${headline}"`, 8
      );
      return Math.min(10, Math.max(1, parseInt(String(txt).trim()) || 5));
    } catch { return 5; }
  }

  setTimelinePosition(pos) {
    this.currentPosition = pos;
    if (this.timeline.length === 0) return;
    const minT = this.timeline[0].t;
    const maxT = this.timeline[this.timeline.length - 1].t;
    const cutoffT = minT + pos * (maxT - minT);

    const yearLabel = document.getElementById('hg-year-label') || document.getElementById('timeline-year');
    if (yearLabel) {
      const d = new Date(cutoffT);
      yearLabel.textContent = pos >= 0.99 ? 'HOY' : d.getFullYear() + '/' + (d.getMonth() + 1);
    }

    this.hyperedges.forEach(he => {
      const heT = new Date(he.timestamp).getTime();
      const visible = heT <= cutoffT;
      const objs = this.visualObjects.filter(o => o.he.id === he.id);
      objs.forEach(o => {
        if (o.sphere) o.sphere.material.opacity = visible ? (0.04 + (he.severity || 5) * 0.006) : 0;
        if (o.line) o.line.material.opacity = visible ? 0.5 : 0;
      });
    });

    if (this.graph3d) {
      const yearAtPos = new Date(cutoffT).getFullYear();
      this.graph3d.nodeMeshes.forEach((mesh, id) => {
        const n = NODE_BY_ID[id];
        const fy = n?.founded || 2000;
        mesh.material.opacity = fy <= yearAtPos ? 0.9 : 0.05;
      });
    }
  }

  playTimeline(speedMs = 80) {
    let pos = 0;
    const step = () => {
      if (pos >= 1.0) return;
      pos += 0.005;
      this.setTimelinePosition(Math.min(1, pos));
      const slider = document.getElementById('hg-year') || document.getElementById('timeline-slider');
      if (slider) {
        if (slider.id === 'hg-year') {
          slider.value = 2015 + Math.round(pos * 15);
        } else {
          slider.value = Math.round(pos * 100);
        }
      }
      setTimeout(step, speedMs);
    };
    step();
  }

  _updateTimelineUI() {
    const ctrl = document.getElementById('hypergraph-timeline') || document.getElementById('timeline-ctrl');
    if (ctrl && this.hyperedges.length > 0) ctrl.style.display = 'flex';
  }

  // Precargar hiper-aristas históricas del sector (demo)
  seedHistoricalEvents() {
    const SEED = [
      { id: 'he_huawei_2019', type: 'regulation', timestamp: '2019-05-16T00:00:00Z',
        title: 'Huawei Entity List', severity: 9,
        nodes_affected: ['TSMC', 'Qualcomm', 'ARM', 'HiSilicon'].filter(id => NODE_BY_ID[id]) },
      { id: 'he_covid_2020', type: 'supply_shock', timestamp: '2020-03-15T00:00:00Z',
        title: 'COVID Semiconductor Shortage', severity: 8,
        nodes_affected: ['TSMC', 'Nvidia', 'AMD', 'Intel'].filter(id => NODE_BY_ID[id]) },
      { id: 'he_asml_2024', type: 'regulation', timestamp: '2024-01-01T00:00:00Z',
        title: 'ASML DUV Export Ban to China', severity: 8,
        nodes_affected: ['ASML', 'TSMC', 'SMIC', 'AMAT', 'KLAC'].filter(id => NODE_BY_ID[id]) },
      { id: 'he_hbm_2024', type: 'supply_shock', timestamp: '2024-06-01T00:00:00Z',
        title: 'HBM Shortage — AI Boom', severity: 7,
        nodes_affected: ['SKHynix', 'Micron', 'Samsung', 'Nvidia'].filter(id => NODE_BY_ID[id]) },
      { id: 'he_starlink_2025', type: 'space_launch', timestamp: '2025-01-01T00:00:00Z',
        title: 'Starlink Direct-to-Cell Launch', severity: 6,
        nodes_affected: ['SpaceX', 'T_Mobile', 'AST_SpaceMobile'].filter(id => NODE_BY_ID[id]) },
    ];
    SEED.forEach(he => { if (he.nodes_affected.length >= 2) this.addHyperedge(he); });
  }

  save() {
    try {
      localStorage.setItem('khipu_hyperedges', JSON.stringify(this.hyperedges.slice(-100)));
    } catch {}
  }

  load() {
    try {
      const saved = JSON.parse(localStorage.getItem('khipu_hyperedges') || '[]');
      saved.forEach(he => this.addHyperedge(he));
    } catch {}
  }
}

window.TemporalHypergraph = TemporalHypergraph;
