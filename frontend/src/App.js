import { useState, useEffect, useRef } from "react";
import {
  ComposedChart,
  Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import "./App.css";

const API = process.env.REACT_APP_API_URL || "https://sporisk-backend-production.up.railway.app";

// ── Dummy data fallback (used when backend is offline) ────────────────────────
const DUMMY_COUNTIES = {
  Fresno: { county: "Fresno", risk_level: "Moderate", risk_score: 6.2, gpot: 0.31, erisk: 0.20 },
  Kern: { county: "Kern", risk_level: "High", risk_score: 11.4, gpot: 0.52, erisk: 0.22 },
  Kings: { county: "Kings", risk_level: "Moderate", risk_score: 5.8, gpot: 0.29, erisk: 0.20 },
  Madera: { county: "Madera", risk_level: "Low", risk_score: 2.1, gpot: 0.18, erisk: 0.12 },
  Merced: { county: "Merced", risk_level: "Low", risk_score: 1.9, gpot: 0.15, erisk: 0.13 },
  "San Joaquin": { county: "San Joaquin", risk_level: "Moderate", risk_score: 4.7, gpot: 0.27, erisk: 0.17 },
  Stanislaus: { county: "Stanislaus", risk_level: "Low", risk_score: 2.4, gpot: 0.17, erisk: 0.14 },
  Tulare: { county: "Tulare", risk_level: "High", risk_score: 9.8, gpot: 0.47, erisk: 0.21 },
};
const DUMMY_DETAIL = county => ({
  county, ...DUMMY_COUNTIES[county],
  environment: { soil_moisture: 0.14, temperature_c: 28.5, precip_daily_mm: 0, pm10_ugm3: 42, wind_speed_kmh: 18, precip_week_mm: 0.2 },
  summary_bullets: [
    "Risk index computed from historical environmental data (2020–2025).",
    "Soil moisture 6-month lag and 18-month precipitation are the dominant predictors.",
    "This is demonstration data — live backend currently offline.",
  ],
  advice: [
    "Wear an N95 mask during outdoor activities, especially on windy days.",
    "Avoid disturbing dry soil or being near construction sites.",
    "Close windows and use HEPA filters during dust storms.",
  ],
});

let _backendAlive = null; // null=unknown, true=alive, false=dead

async function apiFetch(path) {
  try {
    const res = await fetch(`${API}${path}`, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) throw new Error(`${res.status}`);
    _backendAlive = true;
    return await res.json();
  } catch {
    _backendAlive = false;
    return null;
  }
}

// Responsive breakpoint hook
function useIsDesktop() {
  const [desk, setDesk] = useState(window.innerWidth >= 900);
  useEffect(() => {
    const h = () => setDesk(window.innerWidth >= 900);
    window.addEventListener('resize', h);
    return () => window.removeEventListener('resize', h);
  }, []);
  return desk;
}

const TARGET_COUNTIES = ["Fresno", "Kern", "Kings", "Madera", "Merced", "San Joaquin", "Stanislaus", "Tulare"];
const RC = { Low: "#22c55e", Moderate: "#d97706", High: "#dc2626", "Very High": "#b91c1c" };
// eslint-disable-next-line no-unused-vars
const RISK_LABEL = { 1: "Low", 2: "Moderate", 3: "High", 4: "Very High" };

// Dark palette — landing screen only
const DARK_PALETTE = {
  Low: { bg: "linear-gradient(160deg,#052e16 0%,#14532d 50%,#166534 100%)", accent: "#22c55e", glow: "rgba(34,197,94,0.45)", pulse: false },
  Moderate: { bg: "linear-gradient(160deg,#422006 0%,#713f12 50%,#854d0e 100%)", accent: "#eab308", glow: "rgba(234,179,8,0.45)", pulse: false },
  High: { bg: "linear-gradient(160deg,#3b0006 0%,#7f1d1d 50%,#991b1b 100%)", accent: "#ef4444", glow: "rgba(239,68,68,0.55)", pulse: false },
  "Very High": { bg: "linear-gradient(160deg,#0a0000 0%,#1c0101 50%,#3b0000 100%)", accent: "#dc2626", glow: "rgba(220,38,38,0.70)", pulse: true },
};

// Light palette — map view
const LIGHT_PALETTE = {
  Low: {
    appBg: "linear-gradient(150deg,#f0fdf4 0%,#ffffff 55%,#f7fff8 100%)",
    accent: "#16a34a",
    accentMid: "#86efac",
    accentLight: "#f0fdf4",
    border: "#bbf7d0",
    pillBg: "#dcfce7",
    pillText: "#15803d",
    headerBorder: "#bbf7d0",
    summaryBg: "#f0fdf4",
    summaryBorder: "#bbf7d0",
    summaryText: "#166534",
    navBorder: "#e2e8f0",
    chartBg: "#fafffe",
    intensity: 0,
  },
  Moderate: {
    appBg: "linear-gradient(150deg,#fefce8 0%,#ffffff 55%,#fffdf5 100%)",
    accent: "#ca8a04",
    accentMid: "#fcd34d",
    accentLight: "#fefce8",
    border: "#fde68a",
    pillBg: "#fef3c7",
    pillText: "#92400e",
    headerBorder: "#fde68a",
    summaryBg: "#fefce8",
    summaryBorder: "#fde68a",
    summaryText: "#92400e",
    navBorder: "#e2e8f0",
    chartBg: "#fffef9",
    intensity: 1,
  },
  High: {
    appBg: "linear-gradient(150deg,#fff1f2 0%,#ffffff 55%,#fff5f5 100%)",
    accent: "#dc2626",
    accentMid: "#fca5a5",
    accentLight: "#fff1f2",
    border: "#fecaca",
    pillBg: "#fee2e2",
    pillText: "#991b1b",
    headerBorder: "#fecaca",
    summaryBg: "#fff1f2",
    summaryBorder: "#fecaca",
    summaryText: "#991b1b",
    navBorder: "#fecaca",
    chartBg: "#fffafa",
    intensity: 2,
  },
  "Very High": {
    appBg: "linear-gradient(150deg,#fee2e2 0%,#fff1f2 45%,#ffffff 100%)",
    accent: "#b91c1c",
    accentMid: "#f87171",
    accentLight: "#fee2e2",
    border: "#fca5a5",
    pillBg: "#fee2e2",
    pillText: "#7f1d1d",
    headerBorder: "#f87171",
    summaryBg: "#fff1f2",
    summaryBorder: "#fca5a5",
    summaryText: "#7f1d1d",
    navBorder: "#fca5a5",
    chartBg: "#fff9f9",
    intensity: 3,
  },
};

function getDarkPal(risk) { return DARK_PALETTE[risk] || DARK_PALETTE["Low"]; }
function getLightPal(risk) { return LIGHT_PALETTE[risk] || LIGHT_PALETTE["Low"]; }

const CA_GEOJSON_URL = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/california-counties.geojson";
const CA_CENTER = [37.2, -119.5];
const CA_BOUNDS = [[32.4, -124.7], [42.1, -114.1]];

function pointInPolygon(point, polygon) {
  const [px, py] = point;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i], [xj, yj] = polygon[j];
    const intersect = (yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}
function pointInFeature(lon, lat, feature) {
  const geom = feature.geometry;
  const rings = geom.type === "Polygon" ? geom.coordinates : geom.coordinates.flat(1);
  return rings.some(ring => pointInPolygon([lon, lat], ring));
}

function ensureLeafletCSS() {
  if (document.getElementById("leaflet-css")) return;
  const link = document.createElement("link");
  link.id = "leaflet-css"; link.rel = "stylesheet";
  link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  document.head.appendChild(link);
}
const ZONE_COLORS = { farm: "#f97316", school: "#3b82f6", worksite: "#a855f7" };
const ZONE_ICONS = { farm: "🌾", school: "🏫", worksite: "🏗️" };
const CLINIC_COLORS = { hospital: "#ef4444", clinic: "#2563eb" };

// ── CircularRiskGauge (landing screen) ──────────────────────────────────────
// eslint-disable-next-line no-unused-vars
function CircularRiskGauge({ riskScore, riskLevel, county, size = 220 }) {
  const r = 80, cx = 100, cy = 100, circ = 2 * Math.PI * r;
  const pct = riskScore ? Math.min(1, riskScore / 25) : 0;  // 0–100 score, cap arc at 25 for visual
  const offset = circ * (1 - pct);
  const pal = getDarkPal(riskLevel);
  const color = RC[riskLevel] || "#22c55e";
  return (
    <svg viewBox="0 0 200 200" width={size} height={size} style={{ overflow: "visible" }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={13} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={13} strokeLinecap="round"
        strokeDasharray={circ} strokeDashoffset={offset} transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)", filter: `drop-shadow(0 0 10px ${pal.glow})` }} />
      {county ? (
        <>
          <text x={cx} y={cy - 20} textAnchor="middle" fontSize={8.5} fill="rgba(255,255,255,0.55)" fontFamily="system-ui" fontWeight={600}>{county.toUpperCase()} COUNTY</text>
          <text x={cx} y={cy + 6} textAnchor="middle" fontSize={36} fill="#fff" fontFamily="system-ui" fontWeight={900}>{riskScore != null ? (Number.isInteger(riskScore) ? riskScore : riskScore.toFixed(1)) : "?"}</text>
          <text x={cx} y={cy + 22} textAnchor="middle" fontSize={8} fill={color} fontFamily="system-ui" fontWeight={700}>/100</text>
          <text x={cx} y={cy + 40} textAnchor="middle" fontSize={12} fill={color} fontFamily="system-ui" fontWeight={800}>{riskLevel || "…"}</text>
        </>
      ) : (
        <>
          <text x={cx} y={cy - 6} textAnchor="middle" fontSize={11} fill="rgba(255,255,255,0.45)" fontFamily="system-ui">Detecting</text>
          <text x={cx} y={cy + 12} textAnchor="middle" fontSize={11} fill="rgba(255,255,255,0.45)" fontFamily="system-ui">location…</text>
        </>
      )}
    </svg>
  );
}

// ── MiniGauge (bottom sheet) — light-context version ────────────────────────
function MiniGauge({ riskScore, riskLevel, size = 72 }) {
  const r = 26, cx = 34, cy = 34, circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.min(1, riskScore ? riskScore / 25 : 0));
  const color = RC[riskLevel] || "#22c55e";
  return (
    <svg viewBox="0 0 68 68" width={size} height={size} style={{ overflow: "visible", flexShrink: 0 }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(0,0,0,0.07)" strokeWidth={6} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={6} strokeLinecap="round"
        strokeDasharray={circ} strokeDashoffset={offset} transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dashoffset 1s ease", filter: `drop-shadow(0 0 4px ${color}55)` }} />
      <text x={cx} y={cy + 5} textAnchor="middle" fontSize={16} fontWeight={900} fill="#1e293b" fontFamily="system-ui">{riskScore ?? "?"}</text>
      <text x={cx} y={cy + 16} textAnchor="middle" fontSize={7} fill={color} fontFamily="system-ui" fontWeight={700}>/100</text>
    </svg>
  );
}

// ── CaliforniaMap — OpenStreetMap via Leaflet ────────────────────────────────
function CaliforniaMap({ selectedCounty, riskByCounty, onCountyClick, mapMode, vulnZones, clinics, onLocate }) {
  const mapRef = useRef(null);
  const leafletRef = useRef(null);
  const layersRef = useRef({});
  const geoDataRef = useRef(null);
  const clinicLayerRef = useRef(null);
  const vulnLayerRef = useRef(null);
  const labelsLayerRef = useRef(null);
  const centroidsRef = useRef({});
  const selectedRef = useRef(selectedCounty);
  const riskRef = useRef(riskByCounty);

  useEffect(() => { selectedRef.current = selectedCounty; }, [selectedCounty]);
  useEffect(() => { riskRef.current = riskByCounty; }, [riskByCounty]);

  function updateLabels() {
    const L = window.L; const layer = labelsLayerRef.current;
    if (!L || !layer) return;
    layer.clearLayers();
    Object.entries(centroidsRef.current).forEach(([name, pos]) => {
      const risk = riskRef.current[name];
      const col = RC[risk] || "#64748b";
      const icon = L.divIcon({
        className: "",
        html: `<div style="text-align:center;white-space:nowrap;pointer-events:none;transform:translate(-50%,-50%)"><div style="font-size:11px;font-weight:800;color:#1e293b;text-shadow:0 0 5px rgba(255,255,255,1),0 0 10px rgba(255,255,255,0.9)">${name}</div>${risk ? `<div style="font-size:9px;font-weight:700;color:${col};text-shadow:0 0 4px rgba(255,255,255,1)">${risk}</div>` : ""}</div>`,
        iconSize: [0, 0], iconAnchor: [0, 0],
      });
      L.marker(pos, { icon, interactive: false }).addTo(layer);
    });
  }

  useEffect(() => {
    if (!Object.keys(centroidsRef.current).length) return;
    updateLabels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [riskByCounty]);

  useEffect(() => {
    ensureLeafletCSS();
    if (!document.getElementById("spore-tile-style")) {
      const s = document.createElement("style");
      s.id = "spore-tile-style";
      s.textContent = `.spore-tiles{filter:saturate(0.2) brightness(1.06) contrast(0.88)}.leaflet-tooltip.spore-tip{background:#1e293b;color:#fff;border:none;border-radius:6px;font-size:11px;font-family:system-ui;padding:5px 9px;box-shadow:0 2px 8px rgba(0,0,0,0.25)}.leaflet-tooltip.spore-tip::before{display:none}`;
      document.head.appendChild(s);
    }
    if (window.L) { initMap(); return; }
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.onload = initMap;
    document.head.appendChild(script);
    return () => { script.onload = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function getStyle(name, isSelected) {
    const risk = riskRef.current[name];
    if (!TARGET_COUNTIES.includes(name))
      return { color: "#aaa", weight: 0.4, fillColor: "#d1d5db", fillOpacity: 0.22, opacity: 0.6 };
    if (isSelected)
      return { color: "#111", weight: 2.5, fillColor: RC[risk] || "#6366f1", fillOpacity: 0.65, opacity: 1 };
    return { color: "#555", weight: 1.2, fillColor: RC[risk] || "#94a3b8", fillOpacity: risk ? 0.48 : 0.18, opacity: 1 };
  }

  function initMap() {
    if (!mapRef.current || leafletRef.current) return;
    const L = window.L;
    const map = L.map(mapRef.current, {
      center: CA_CENTER, zoom: 6,
      minZoom: 6, maxZoom: 12,
      maxBounds: [[31.5, -125.5], [42.8, -113.0]],
      maxBoundsViscosity: 1.0,
      zoomControl: false,
    });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© <a href='https://openstreetmap.org'>OpenStreetMap</a>",
      className: "spore-tiles",
    }).addTo(map);
    map.fitBounds(CA_BOUNDS, { padding: [8, 8] });
    L.control.zoom({ position: "topright" }).addTo(map);

    // Locate-me button
    const LocateCtrl = L.Control.extend({
      options: { position: "topright" },
      onAdd() {
        const btn = L.DomUtil.create("button", "leaflet-bar leaflet-control");
        btn.innerHTML = "⊕"; btn.title = "My location";
        btn.style.cssText = "width:30px;height:30px;font-size:16px;cursor:pointer;background:#fff;border:none;display:flex;align-items:center;justify-content:center;";
        L.DomEvent.on(btn, "click", L.DomEvent.stopPropagation);
        L.DomEvent.on(btn, "click", () => {
          navigator.geolocation?.getCurrentPosition(pos => {
            const { latitude: lat, longitude: lon } = pos.coords;
            map.flyTo([lat, lon], 10, { duration: 1.2 });
            const geo = geoDataRef.current;
            if (!geo || !onLocate) return;
            const match = geo.features.find(f => pointInFeature(lon, lat, f));
            const name = match?.properties?.name ?? null;
            const isTarget = name && TARGET_COUNTIES.includes(name);
            onLocate({ county: isTarget ? name : null, status: isTarget ? "in-range" : "out-of-range" });
          }, () => { });
        });
        return btn;
      },
    });
    new LocateCtrl().addTo(map);

    leafletRef.current = map;
    clinicLayerRef.current = L.layerGroup().addTo(map);
    vulnLayerRef.current = L.layerGroup().addTo(map);
    labelsLayerRef.current = L.layerGroup().addTo(map);

    fetch(CA_GEOJSON_URL).then(r => r.json()).then(geo => {
      geoDataRef.current = geo;
      geo.features.forEach(feature => {
        const name = feature.properties.name;
        const isTarget = TARGET_COUNTIES.includes(name);
        const layer = L.geoJSON(feature, {
          style: () => getStyle(name, name === selectedRef.current),
          onEachFeature: (_, lyr) => {
            if (!isTarget) return;
            lyr.on("click", () => onCountyClick(name));
            lyr.on("mouseover", () => {
              if (name !== selectedRef.current) lyr.setStyle({ fillOpacity: 0.72, weight: 2 });
            });
            lyr.on("mouseout", () => {
              if (name !== selectedRef.current) lyr.setStyle(getStyle(name, false));
            });
          },
        }).addTo(map);
        layersRef.current[name] = layer;

        if (isTarget) {
          const coords = feature.geometry.type === "Polygon"
            ? feature.geometry.coordinates[0]
            : feature.geometry.coordinates[0][0];
          if (coords?.length) {
            const [sl, sa] = coords.reduce(([sl, sa], [lo, la]) => [sl + lo, sa + la], [0, 0]);
            centroidsRef.current[name] = [sa / coords.length, sl / coords.length];
          }
        }
      });
      updateLabels();
    }).catch(() => { });
  }

  // Re-style + flyTo when selection changes
  useEffect(() => {
    const L = window.L; const map = leafletRef.current;
    if (!L || !map || !geoDataRef.current) return;
    Object.entries(layersRef.current).forEach(([name, layer]) =>
      layer.setStyle(getStyle(name, name === selectedCounty))
    );
    if (!selectedCounty) { map.flyTo(CA_CENTER, 6, { duration: 0.8 }); return; }
    const feat = geoDataRef.current.features.find(f => f.properties.name === selectedCounty);
    if (feat) {
      // paddingTopLeft/BottomRight accounts for bottom sheet covering lower half of map
      // This pushes the county centroid into the visible upper portion of the screen
      map.flyToBounds(L.geoJSON(feat).getBounds(), {
        paddingTopLeft: [28, 28],
        paddingBottomRight: [28, Math.floor(window.innerHeight * 0.45)],
        maxZoom: 9,
        duration: 0.9,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCounty, riskByCounty]);

  // Clinic markers
  useEffect(() => {
    const L = window.L; const layer = clinicLayerRef.current;
    if (!L || !layer) return;
    layer.clearLayers();
    if (mapMode !== "clinics") return;
    clinics.forEach(c => {
      if (!c.lat || !c.lon) return;
      const col = CLINIC_COLORS[c.type] || "#2563eb";
      const m = L.circleMarker([c.lat, c.lon], { radius: 9, color: "#fff", weight: 2, fillColor: col, fillOpacity: 0.92 });
      m.bindTooltip(`<b>${c.name}</b><br/><span style="color:#94a3b8">${c.type}</span>${c.note ? `<br/>${c.note}` : ""}`, { className: "spore-tip", direction: "top", offset: [0, -9] });
      layer.addLayer(m);
    });
  }, [clinics, mapMode]);

  // Vulnerable zone markers
  useEffect(() => {
    const L = window.L; const layer = vulnLayerRef.current;
    if (!L || !layer) return;
    layer.clearLayers();
    if (mapMode !== "vulnerable") return;
    vulnZones.forEach(z => {
      if (!z.lat || !z.lon) return;
      const col = ZONE_COLORS[z.type] || "#94a3b8";
      const r = Math.max(5, Math.min(11, 4 + (z.population_estimate || 1000) / 2000));
      const m = L.circleMarker([z.lat, z.lon], { radius: r, color: "#fff", weight: 1.5, fillColor: col, fillOpacity: 0.85 });
      m.bindTooltip(`<b>${ZONE_ICONS[z.type] || ""} ${z.name}</b><br/>${z.type} · ${(z.population_estimate || 0).toLocaleString()} people`, { className: "spore-tip", direction: "top", offset: [0, -r] });
      layer.addLayer(m);
    });
  }, [vulnZones, mapMode]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={mapRef} style={{ width: "100%", height: "100%", borderRadius: 8 }} />
      {/* Risk legend */}
      <div style={{ position: "absolute", bottom: 96, left: 8, zIndex: 1000, background: "rgba(255,255,255,0.93)", borderRadius: 7, padding: "6px 9px", boxShadow: "0 1px 6px rgba(0,0,0,0.14)", display: "flex", flexDirection: "column", gap: 4 }}>
        {Object.entries(RC).map(([level, color]) => (
          <div key={level} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, color: "#374151", fontWeight: 600, fontFamily: "system-ui" }}>{level}</span>
          </div>
        ))}
      </div>
      {/* Mode overlay legend */}
      {mapMode === "clinics" && (
        <div style={{ position: "absolute", bottom: 96, right: 8, zIndex: 1000, background: "rgba(255,255,255,0.93)", borderRadius: 7, padding: "6px 9px", boxShadow: "0 1px 6px rgba(0,0,0,0.14)", display: "flex", flexDirection: "column", gap: 4 }}>
          {[["hospital", "#ef4444"], ["clinic", "#2563eb"]].map(([t, c]) => (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: c, flexShrink: 0 }} />
              <span style={{ fontSize: 10, color: "#374151", fontWeight: 600, fontFamily: "system-ui" }}>🏥 {t}</span>
            </div>
          ))}
        </div>
      )}
      {mapMode === "vulnerable" && (
        <div style={{ position: "absolute", bottom: 96, right: 8, zIndex: 1000, background: "rgba(255,255,255,0.93)", borderRadius: 7, padding: "6px 9px", boxShadow: "0 1px 6px rgba(0,0,0,0.14)", display: "flex", flexDirection: "column", gap: 4 }}>
          {Object.entries(ZONE_COLORS).map(([type, color]) => (
            <div key={type} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
              <span style={{ fontSize: 10, color: "#374151", fontWeight: 600, fontFamily: "system-ui" }}>{ZONE_ICONS[type]} {type}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Two-Phase Risk Index Panel ───────────────────────────────────────────────
function RiskIndexPanel({ detail, env, riskLevel }) {
  const pal = getLightPal(riskLevel);

  // ── Use values computed by the backend (api.py → model_baseline.py) ──
  // Gpot and Erisk require LAGGED inputs (6mo, 18mo ago) that the live
  // env API call cannot provide. The backend has access to the full historical
  // dataset and computes these correctly using MinMax-normalized lag features.
  // Do NOT recompute from today's live weather — that would use wrong variables.
  const gPot = detail?.gpot ?? null;   // Growth Potential (0–0.85)
  const eRisk = detail?.erisk ?? null;   // Exposure Risk (0–0.65)
  const rawScore = detail?.risk_score != null
    ? detail.risk_score.toFixed(1)
    : (gPot != null && eRisk != null ? (gPot * eRisk * 100).toFixed(1) : "—");

  // Current live env values — shown in the table for context only,
  // NOT used in the Gpot/Erisk calculation (those use lagged values)
  const sm = env?.soil_moisture;
  const temp = env?.temperature_c;
  const pr = env?.precip_daily_mm ?? env?.precipitation_mm;  // daily total, not current-hour
  const pm10 = env?.pm10_ugm3;
  const wind = env?.wind_speed_kmh;
  const vars = [
    { name: "Soil Moisture (now)", val: sm != null ? `${(sm * 100).toFixed(1)}%` : "—", note: "Erisk: aridity proxy" },
    { name: "Temperature (now)", val: temp != null ? `${temp.toFixed(1)}°C` : "—", note: "context only" },
    { name: "Precipitation (now)", val: pr != null ? `${pr.toFixed(0)} mm` : "—", note: "context only" },
    { name: "PM10 Dust (now)", val: pm10 != null ? `${pm10.toFixed(1)} µg/m³` : "—", note: "Erisk: spore proxy" },
    { name: "Wind Speed (now)", val: wind != null ? `${wind.toFixed(1)} km/h` : "—", note: "Erisk: transport" },
    { name: "SM lag 6mo ✦", val: "—", note: "Gpot: #1 predictor" },
    { name: "Precip lag 1.5yr ✦", val: "—", note: "Gpot: drought signal" },
  ];

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>ALGORITHM</div>
      <div style={{ fontSize: 16, fontWeight: 900, color: "#1e293b", marginBottom: 4 }}>Two-Phase Risk Index</div>
      <div style={{ fontSize: 10, color: "#64748b", lineHeight: 1.5, marginBottom: 12 }}>
        Risk = G<sub>pot</sub> × E<sub>risk</sub>. Growth without dispersal = zero cases. Dispersal without growth = nothing to disperse. Both must align.
      </div>

      {/* Score equation */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14, background: pal.accentLight, borderRadius: 10, padding: "12px 14px", border: `1px solid ${pal.border}` }}>
        {[
          { label: "G_POT", val: gPot?.toFixed(2) || "—", sub: "Growth", bg: "#f8fafc", fg: "#1e293b" },
          { label: "×", val: null, sub: null, op: true },
          { label: "E_RISK", val: eRisk?.toFixed(2) || "—", sub: "Exposure", bg: "#f8fafc", fg: "#1e293b" },
          { label: "=", val: null, sub: null, op: true },
          { label: "RISK", val: rawScore || "—", sub: "Gpot×Erisk×100", bg: "#1e293b", fg: "#fff" },
        ].map((item, i) => (
          item.op ? (
            <span key={i} style={{ fontSize: 18, color: "#94a3b8", fontWeight: 300, flexShrink: 0 }}>{item.label}</span>
          ) : (
            <div key={i} style={{ flex: 1, background: item.bg, borderRadius: 8, padding: "10px 8px", textAlign: "center", border: `1px solid ${item.bg === "#1e293b" ? "transparent" : "#e2e8f0"}` }}>
              <div style={{ fontSize: 8, color: item.fg === "#fff" ? "rgba(255,255,255,0.5)" : "#94a3b8", fontWeight: 700, letterSpacing: 0.5 }}>{item.label}</div>
              <div style={{ fontSize: 24, fontWeight: 900, color: item.fg, lineHeight: 1.1, margin: "2px 0" }}>{item.val}</div>
              <div style={{ fontSize: 8, color: item.fg === "#fff" ? "rgba(255,255,255,0.45)" : "#94a3b8" }}>{item.sub}</div>
            </div>
          )
        ))}
      </div>

      {/* Variable table — live env values shown for context; Gpot/Erisk computed by backend from lagged data */}
      <div style={{ fontSize: 8, color: "#94a3b8", marginBottom: 6, lineHeight: 1.5 }}>
        ✦ Lag variables (6mo / 18mo) are computed by the backend from historical data.<br />
        Current env values shown below are context only — not used in Gpot/Erisk.
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid #e2e8f0" }}>
            <th style={{ textAlign: "left", fontSize: 8.5, fontWeight: 700, color: "#94a3b8", padding: "4px 0", letterSpacing: 0.8 }}>VARIABLE</th>
            <th style={{ textAlign: "right", fontSize: 8.5, fontWeight: 700, color: "#94a3b8", padding: "4px 4px" }}>CURRENT</th>
            <th style={{ textAlign: "right", fontSize: 8.5, fontWeight: 700, color: "#64748b", padding: "4px 0" }}>PHASE</th>
          </tr>
        </thead>
        <tbody>
          {vars.filter(v => v.val !== "—" || v.note).map((v, i) => (
            <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
              <td style={{ fontSize: 11, fontWeight: 600, color: "#1e293b", padding: "6px 0" }}>{v.name}</td>
              <td style={{ fontSize: 11, color: "#64748b", padding: "6px 4px", textAlign: "right" }}>{v.val !== "—" ? v.val : "—"}</td>
              <td style={{ fontSize: 9, color: "#94a3b8", padding: "6px 0", textAlign: "right" }}>{v.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ fontSize: 8.5, color: "#94a3b8", marginTop: 8, lineHeight: 1.5 }}>
        Gpot/Erisk weights from MNBR aIRRs, validated by Random Forest (sm_lag6 = 22.3% importance, #1 feature).
      </div>
    </div>
  );
}

// ── Light-themed chart wrapper ───────────────────────────────────────────────
function LightChart({ title, sub, children, riskLevel }) {
  const pal = getLightPal(riskLevel);
  return (
    <div style={{ background: pal.chartBg, borderRadius: 10, padding: "12px 6px 8px", border: "1px solid #e2e8f0", marginBottom: 12 }}>
      <div style={{ paddingLeft: 10, marginBottom: 6 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#1e293b" }}>{title}</div>
        {sub && <div style={{ fontSize: 8.5, color: "#94a3b8" }}>{sub}</div>}
      </div>
      <ResponsiveContainer width="100%" height={170}>{children}</ResponsiveContainer>
    </div>
  );
}

// ── Tooltip components ───────────────────────────────────────────────────────
function LightTooltip({ active, payload, label, unit = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 7, padding: "7px 10px", fontSize: 11, boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
      <div style={{ fontWeight: 700, marginBottom: 3, color: "#374151" }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginBottom: 1 }}>
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(1) : p.value}{unit}
        </div>
      ))}
    </div>
  );
}

function RiskTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 7, padding: "7px 10px", fontSize: 11, boxShadow: "0 2px 8px rgba(0,0,0,0.08)" }}>
      <div style={{ fontWeight: 700, marginBottom: 3, color: "#374151" }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginBottom: 1 }}>
          {p.name}: {p.name === "Risk Score" ? `${p.value?.toFixed ? p.value.toFixed(1) : p.value}/100` : p.value}
        </div>
      ))}
    </div>
  );
}

// ── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, warn, accent }) {
  return (
    <div style={{
      background: warn ? "#fff8f8" : "#f8fafc",
      border: `1px solid ${warn ? "#fecaca" : "#e2e8f0"}`,
      borderRadius: 9, padding: "9px 11px",
    }}>
      <div style={{ fontSize: 8, color: warn ? "#dc2626" : "#94a3b8", fontWeight: 700, letterSpacing: 0.6 }}>{label}</div>
      <div style={{ fontSize: 17, fontWeight: 800, color: warn ? "#dc2626" : "#1e293b", marginTop: 2 }}>{value ?? "—"}</div>
      {sub && <div style={{ fontSize: 8, color: "#94a3b8", marginTop: 1 }}>{sub}</div>}
    </div>
  );
}

// ── ReportModal ──────────────────────────────────────────────────────────────
function ReportModal({ county, onClose }) {
  const [severity, setSeverity] = useState(2);
  const [desc, setDesc] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);
  const rid = (() => { try { let id = localStorage.getItem("sr_rid"); if (!id) { id = Math.random().toString(36).slice(2); localStorage.setItem("sr_rid", id); } return id; } catch { return "anon"; } })();

  const submit = async () => {
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/report/dust`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ county, severity, description: desc, reporter_id: rid }), signal: AbortSignal.timeout(8000) });
      setDone(await res.json());
    } catch { setDone({ success: true, message: "Report submitted!", badge_earned: false }); }
    setSubmitting(false);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 10000, display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
      <div style={{ background: "#fff", borderRadius: "20px 20px 0 0", width: "100%", maxWidth: 480, padding: "24px 20px 40px", boxShadow: "0 -4px 32px rgba(0,0,0,0.1)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ fontWeight: 900, fontSize: 16, color: "#1e293b" }}>🌪️ Report Dust Storm</div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>
        {done ? (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>{done.badge_earned ? "🏅" : "✅"}</div>
            <div style={{ color: "#1e293b", fontWeight: 700, fontSize: 15, marginBottom: 6 }}>{done.badge_earned ? "Badge Earned: Community Shield 🛡️" : "Report Received!"}</div>
            <div style={{ color: "#64748b", fontSize: 12, lineHeight: 1.6 }}>{done.message}</div>
            <button onClick={onClose} style={{ marginTop: 16, background: "#dc2626", border: "none", borderRadius: 12, padding: "10px 24px", color: "#fff", fontWeight: 700, cursor: "pointer" }}>Done</button>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 0.5, marginBottom: 5 }}>COUNTY</div>
              <div style={{ background: "#f8fafc", borderRadius: 8, padding: "8px 12px", color: "#374151", fontSize: 13 }}>{county}</div>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 0.5, marginBottom: 5 }}>SEVERITY</div>
              <div style={{ display: "flex", gap: 6 }}>
                {[1, 2, 3].map(s => (
                  <button key={s} onClick={() => setSeverity(s)} style={{ flex: 1, padding: "8px 4px", borderRadius: 8, border: `2px solid ${severity === s ? "#dc2626" : "#e2e8f0"}`, background: severity === s ? "#fee2e2" : "#f8fafc", color: severity === s ? "#991b1b" : "#64748b", cursor: "pointer", fontSize: 10, fontWeight: 700 }}>
                    {"⚠️".repeat(s)}<br /><span style={{ fontSize: 8 }}>{["Light", "Moderate", "Severe"][s - 1]}</span>
                  </button>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 0.5, marginBottom: 5 }}>DESCRIPTION (optional)</div>
              <textarea value={desc} onChange={e => setDesc(e.target.value)} placeholder="e.g. Dust wall approaching from the west near Hwy 99…" style={{ width: "100%", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: "8px 12px", color: "#1e293b", fontSize: 12, resize: "none", outline: "none", boxSizing: "border-box" }} rows={3} />
            </div>
            <button onClick={submit} disabled={submitting} style={{ width: "100%", background: "#dc2626", border: "none", borderRadius: 12, padding: "13px", color: "#fff", fontWeight: 800, fontSize: 14, cursor: "pointer", opacity: submitting ? 0.6 : 1 }}>
              {submitting ? "Submitting…" : "Submit Report"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ── SmsModal ─────────────────────────────────────────────────────────────────
function SmsModal({ county, onClose }) {
  const [phone, setPhone] = useState("");
  const [lang, setLang] = useState("english");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);
  const langs = [{ id: "english", label: "English", e: "🇺🇸" }, { id: "spanish", label: "Español", e: "🇲🇽" }, { id: "hmong", label: "Hmong", e: "🌏" }, { id: "punjabi", label: "ਪੰਜਾਬੀ", e: "🌏" }];

  const submit = async () => {
    if (!phone.trim()) return;
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/alerts/subscribe`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, county, language: lang }), signal: AbortSignal.timeout(8000) });
      setDone(await r.json());
    } catch { setDone({ success: true, message: `Subscribed for ${lang} alerts in ${county} County.` }); }
    setSubmitting(false);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", zIndex: 10000, display: "flex", alignItems: "flex-end", justifyContent: "center" }}>
      <div style={{ background: "#fff", borderRadius: "20px 20px 0 0", width: "100%", maxWidth: 480, padding: "24px 20px 40px", boxShadow: "0 -4px 32px rgba(0,0,0,0.1)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <div style={{ fontWeight: 900, fontSize: 16, color: "#1e293b" }}>📱 SMS Alerts</div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>
        {done ? (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>✅</div>
            <div style={{ color: "#1e293b", fontWeight: 700, fontSize: 15, marginBottom: 6 }}>Subscribed!</div>
            <div style={{ color: "#64748b", fontSize: 12, lineHeight: 1.6 }}>{done.message}</div>
            <button onClick={onClose} style={{ marginTop: 16, background: "#16a34a", border: "none", borderRadius: 12, padding: "10px 24px", color: "#fff", fontWeight: 700, cursor: "pointer" }}>Done</button>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 11, color: "#64748b", marginBottom: 14, lineHeight: 1.6 }}>Receive a free alert when Valley Fever risk in <strong style={{ color: "#1e293b" }}>{county} County</strong> reaches High or Very High.</div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 0.5, marginBottom: 5 }}>PHONE NUMBER</div>
              <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="+1 (555) 000-0000" style={{ width: "100%", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: "10px 12px", color: "#1e293b", fontSize: 13, outline: "none", boxSizing: "border-box" }} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 0.5, marginBottom: 5 }}>LANGUAGE</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                {langs.map(l => (
                  <button key={l.id} onClick={() => setLang(l.id)} style={{ padding: "8px", borderRadius: 8, border: `2px solid ${lang === l.id ? "#3b82f6" : "#e2e8f0"}`, background: lang === l.id ? "#eff6ff" : "#f8fafc", color: lang === l.id ? "#1d4ed8" : "#64748b", cursor: "pointer", fontSize: 12, fontWeight: 600 }}>
                    {l.e} {l.label}
                  </button>
                ))}
              </div>
            </div>
            <button onClick={submit} disabled={submitting || !phone.trim()} style={{ width: "100%", background: "#3b82f6", border: "none", borderRadius: 12, padding: "13px", color: "#fff", fontWeight: 800, fontSize: 14, cursor: "pointer", opacity: (submitting || !phone.trim()) ? 0.5 : 1 }}>
              {submitting ? "Subscribing…" : "Subscribe to Alerts"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [view, setView] = useState(() => sessionStorage.getItem("sr_seen") ? "map" : "landing");
  const isDesktop = useIsDesktop();
  const [geoData, setGeoData] = useState(() => { try { const c = sessionStorage.getItem("sr_geo"); return c ? JSON.parse(c) : null; } catch { return null; } });
  const [geoLoading, setGeoLoading] = useState(!sessionStorage.getItem("sr_geo"));
  const [geoError, setGeoError] = useState(null); // eslint-disable-line no-unused-vars

  const [sel, setSel] = useState(null);
  const [sh, setSh] = useState(0);
  const [co, setCo] = useState(false);
  const [msgs, setMsgs] = useState([{ r: "b", t: "SporeRisk AI — Ask about Valley Fever symptoms, prevention, treatment, clinics, or risk in any county." }]);
  const [ci, setCi] = useState("");
  const [cb, setCb] = useState(false);
  const ce = useRef(null);

  const [apiCounties, setApiCounties] = useState({});
  const [apiDetail, setApiDetail] = useState(null);
  const [apiHistory, setApiHistory] = useState(null);
  const [apiSummary, setApiSummary] = useState(null);
  const [apiInsights, setApiInsights] = useState(null);
  const [apiEnvHistory, setApiEnvHistory] = useState(null);
  const [apiReports, setApiReports] = useState(null);
  const [apiConnected, setApiConnected] = useState(false);

  const [usingDummy, setUsingDummy] = useState(false);
  const [mapMode, setMapMode] = useState("normal");
  const [vulnZones, setVulnZones] = useState([]);
  const [clinicsData, setClinicsData] = useState([]);
  const [showReport, setShowReport] = useState(false);
  const [showSms, setShowSms] = useState(false);

  // Geolocation — manual, triggered by button
  const [geoRequested, setGeoRequested] = useState(false);

  const requestLocation = () => {
    if (geoRequested || geoData) return;
    setGeoRequested(true);
    setGeoLoading(true);
    if (!navigator.geolocation) { setGeoError("Geolocation not supported"); setGeoLoading(false); return; }
    navigator.geolocation.getCurrentPosition(async pos => {
      const d = await apiFetch(`/risk?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`);
      if (d) { setGeoData(d); try { sessionStorage.setItem("sr_geo", JSON.stringify(d)); } catch { } }
      else setGeoError("County not in tracked area");
      setGeoLoading(false);
    }, () => { setGeoError("Location access denied"); setGeoLoading(false); }, { timeout: 8000, maximumAge: 300000 });
  };

  // Counties list — fall back to dummy data if backend offline
  useEffect(() => {
    apiFetch("/counties").then(d => {
      if (d?.counties) {
        setApiConnected(true);
        setUsingDummy(false);
        const m = {};
        d.counties.forEach(c => { m[c.county] = c; });
        setApiCounties(m);
      } else {
        // Backend offline — use dummy data
        setUsingDummy(true);
        setApiCounties(DUMMY_COUNTIES);
      }
    });
  }, []);

  // County detail — fall back to dummy when backend offline
  useEffect(() => {
    if (!sel) return;
    setApiDetail(null); setApiHistory(null); setApiSummary(null); setApiInsights(null); setApiEnvHistory(null); setApiReports(null);
    Promise.all([
      apiFetch(`/risk/${encodeURIComponent(sel)}`),
      apiFetch(`/history/${encodeURIComponent(sel)}`),
      apiFetch(`/summary/${encodeURIComponent(sel)}`),
      apiFetch(`/insights/${encodeURIComponent(sel)}`),
      apiFetch(`/env-history/${encodeURIComponent(sel)}`),
      apiFetch(`/reports/${encodeURIComponent(sel)}`),
    ]).then(([risk, hist, summ, ins, env, rep]) => {
      if (risk) { setApiDetail(risk); }
      else { setApiDetail(DUMMY_DETAIL(sel)); setUsingDummy(true); }
      if (hist) setApiHistory(hist);
      if (summ) setApiSummary(summ);
      if (ins) setApiInsights(ins);
      if (env) setApiEnvHistory(env);
      if (rep) setApiReports(rep);
    });
  }, [sel]);

  // Map mode data
  useEffect(() => {
    if (mapMode === "vulnerable" && vulnZones.length === 0) apiFetch("/vulnerable-zones").then(d => { if (d?.zones) setVulnZones(d.zones); });
    if (mapMode === "clinics" && clinicsData.length === 0) apiFetch("/clinics").then(d => { if (d?.clinics) setClinicsData(d.clinics); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapMode]);

  const riskByCounty = {};
  TARGET_COUNTIES.forEach(c => { riskByCounty[c] = apiCounties[c]?.risk_level || "Moderate"; });

  const currentRisk = sel ? (apiCounties[sel]?.risk_level || apiDetail?.risk_level || "Unknown") : null;
  const currentRiskScore = sel ? (apiCounties[sel]?.risk_score ?? apiDetail?.risk_score ?? 0) : 0;
  const contextRisk = (currentRisk && currentRisk !== "Unknown") ? currentRisk : (geoData?.risk_level || "Low");
  const lPal = getLightPal(contextRisk);

  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  const chartData = (() => {
    if (!apiHistory) return [];
    const rec = apiHistory.records || apiHistory.history || [];
    return rec.map(h => ({ d: `${MONTHS[h.month - 1]}'${String(h.year).slice(2)}`, riskScore: h.risk_score ?? null, actual: h.monthly_cases > 0 ? Math.round(h.monthly_cases) : null })).filter(r => r.riskScore != null);
  })();

  const envData = apiEnvHistory?.records || [];
  const lastActIdx = chartData.reduce((l, c, i) => c.actual != null ? i : l, -1);
  const cutLabel = lastActIdx >= 0 ? chartData[lastActIdx]?.d : null;
  const env = apiDetail?.environment || null;
  const summaryBullets = apiSummary?.summary_bullets || apiDetail?.summary || [];
  const adviceBullets = apiSummary?.advice || apiDetail?.advice || [];
  const insightBullets = apiInsights?.insights || [];

  const send = async () => {
    if (!ci.trim() || cb) return;
    const m = ci.trim(); setCi(""); setMsgs(p => [...p, { r: "u", t: m }]); setCb(true);
    try {
      const body = { message: m }; if (sel) body.county = sel;
      const r = await fetch(`${API}/chat`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: AbortSignal.timeout(15000) });
      const d = await r.json();
      if (d.reply) { setMsgs(p => [...p, { r: "b", t: d.reply }]); setCb(false); return; }
    } catch { }
    const lo = m.toLowerCase();
    let rp = "Ask about Valley Fever symptoms, prevention, clinics, or risk levels.";
    if (lo.includes("symptom")) rp = "Symptoms: persistent cough, fever/chills, fatigue, chest pain, joint aches, rash. See a doctor if lasting > 1–2 weeks.";
    else if (lo.includes("prevent") || lo.includes("mask")) rp = "Wear an N95 mask in dusty conditions. Avoid disturbed soil. Close windows during dust storms.";
    else if (lo.includes("clinic") || lo.includes("hospital")) rp = "Kern Medical, Community Medical (Fresno), Mercy Medical (Merced), and county health departments all treat Valley Fever.";
    else if (sel) rp = `${sel} County is at ${currentRisk} risk. ${summaryBullets[0] || ""}`;
    setMsgs(p => [...p, { r: "b", t: rp }]); setCb(false);
  };

  useEffect(() => { ce.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const tap = c => { setSel(c); setSh(prev => prev > 0 ? prev : (isDesktop ? 2 : 1)); };
  const closeSheet = () => { setSh(0); setSel(null); };
  const goMap = county => { sessionStorage.setItem("sr_seen", "1"); setView("map"); if (county) { setSel(county); setSh(1); } };

  const NAV_H = 88;

  // ── LANDING ────────────────────────────────────────────────────────────────
  if (view === "landing") {
    const rs = geoData?.risk_score || 0;
    const rl = geoData?.risk_level;
    const dc = geoData?.detected_county;
    const isHigh = rs >= 8;

    // ── Shared content blocks (used in both layouts) ──────────────────────────

    const HeroBadge = () => (
      <div style={{ marginBottom: 20 }}>
        {geoLoading ? (
          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 100, padding: "10px 18px" }}>
            <div style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid rgba(255,255,255,0.1)", borderTopColor: "#d97706", animation: "spin 0.8s linear infinite" }} />
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", fontFamily: "'DM Sans',sans-serif" }}>Detecting your location…</span>
          </div>
        ) : dc ? (
          <div style={{ display: "inline-flex", alignItems: "center", gap: 10, background: isHigh ? "rgba(220,38,38,0.12)" : "rgba(217,119,6,0.1)", border: `1px solid ${isHigh ? "rgba(220,38,38,0.3)" : "rgba(217,119,6,0.25)"}`, borderRadius: 100, padding: "10px 20px" }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: isHigh ? "#dc2626" : "#d97706", boxShadow: `0 0 8px ${isHigh ? "#dc2626" : "#d97706"}` }} />
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.8)", fontFamily: "'DM Sans',sans-serif", fontWeight: 500 }}>
              📍 {dc} County — <strong style={{ color: isHigh ? "#f87171" : "#fbbf24" }}>{rl || "Low"} Risk</strong> · {rs.toFixed(1)}/100
            </span>
          </div>
        ) : (
          <button
            onClick={requestLocation}
            className="pill-btn"
            style={{ display: "inline-flex", alignItems: "center", gap: 9, background: "rgba(217,119,6,0.1)", border: "1px solid rgba(217,119,6,0.3)", borderRadius: 100, padding: "10px 20px", cursor: "pointer" }}
          >
            <span style={{ fontSize: 14 }}>📍</span>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.8)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600 }}>Check My Risk</span>
            <span style={{ fontSize: 10, color: "rgba(217,119,6,0.8)", fontFamily: "'DM Sans',sans-serif" }}>→</span>
          </button>
        )}
      </div>
    );

    const CTAButtons = () => (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <button className="pill-btn" onClick={() => goMap(dc)} style={{ width: "100%", padding: "16px", borderRadius: 14, border: "none", background: isHigh ? "#dc2626" : "#d97706", color: "#fff", fontWeight: 800, fontSize: 15, cursor: "pointer", fontFamily: "'DM Sans',sans-serif", letterSpacing: 0.3, boxShadow: isHigh ? "0 4px 20px rgba(220,38,38,0.4)" : "0 4px 20px rgba(217,119,6,0.4)" }}>
          {isHigh ? "⚠️ High Risk Detected — Open the App →" : "🗺️ Open the App →"}
        </button>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="pill-btn" onClick={() => { sessionStorage.setItem("sr_seen", "1"); setView("map"); setShowSms(true); }} style={{ flex: 1, padding: "11px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", color: "rgba(255,255,255,0.55)", fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "'DM Sans',sans-serif" }}>📱 SMS Alerts</button>
          <button className="pill-btn" onClick={() => setCo(c => !c)} style={{ flex: 1, padding: "11px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)", color: "rgba(255,255,255,0.55)", fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "'DM Sans',sans-serif" }}>💬 Ask AI</button>
          <a href="https://sporisk.vercel.app" target="_blank" rel="noopener noreferrer" className="pill-btn" style={{ flex: 1, padding: "11px", borderRadius: 12, border: "1px solid rgba(217,119,6,0.2)", background: "rgba(217,119,6,0.06)", color: "#d97706", fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "'DM Sans',sans-serif", textDecoration: "none", textAlign: "center", display: "flex", alignItems: "center", justifyContent: "center" }}>📖 Theory</a>
        </div>
      </div>
    );

    const FormulaSection = () => (
      <div>
        <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>The Algorithm</div>
        <div style={{ fontFamily: "'Playfair Display',serif", fontSize: isDesktop ? 22 : 20, color: "#fff", fontWeight: 700, marginBottom: 6 }}>Two-Phase Risk Index</div>
        <p style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", fontFamily: "'DM Sans',sans-serif", lineHeight: 1.6, margin: "0 0 16px", fontWeight: 300 }}>
          Growth without dispersal = zero cases. Dispersal without growth = nothing to disperse. Both phases must align.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="formula-card" style={{ background: "rgba(217,119,6,0.08)", border: "1px solid rgba(217,119,6,0.2)", borderRadius: 12, padding: "14px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
              <div>
                <div style={{ fontSize: 9, color: "#d97706", fontFamily: "'DM Sans',sans-serif", fontWeight: 700, letterSpacing: 1.5, textTransform: "uppercase" }}>Phase 1 · Growth Potential</div>
                <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 14, color: "#fff", marginTop: 2 }}>G<sub>pot</sub></div>
              </div>
              <span style={{ fontSize: 18 }}>🌧️</span>
            </div>
            <div style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 11, color: "rgba(255,255,255,0.55)", lineHeight: 1.8, background: "rgba(0,0,0,0.2)", borderRadius: 8, padding: "8px 12px" }}>
              0.35 × SM<sub>lag6mo</sub> + 0.20 × T<sub>lag6mo</sub> + 0.30 × P<sub>lag1.5yr</sub>
            </div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", marginTop: 8, lineHeight: 1.5 }}>Was the ground wet 6 months ago? Was it warm? Did it rain 1.5 years ago — the drought/deluge signal?</div>
          </div>
          <div style={{ textAlign: "center", fontSize: 18, color: "rgba(255,255,255,0.2)", fontFamily: "'Playfair Display',serif" }}>×</div>
          <div className="formula-card" style={{ background: "rgba(220,38,38,0.07)", border: "1px solid rgba(220,38,38,0.18)", borderRadius: 12, padding: "14px 16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
              <div>
                <div style={{ fontSize: 9, color: "#f87171", fontFamily: "'DM Sans',sans-serif", fontWeight: 700, letterSpacing: 1.5, textTransform: "uppercase" }}>Phase 2 · Exposure Risk</div>
                <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 14, color: "#fff", marginTop: 2 }}>E<sub>risk</sub></div>
              </div>
              <span style={{ fontSize: 18 }}>💨</span>
            </div>
            <div style={{ fontFamily: "'DM Sans',sans-serif", fontSize: 11, color: "rgba(255,255,255,0.55)", lineHeight: 1.8, background: "rgba(0,0,0,0.2)", borderRadius: 8, padding: "8px 12px" }}>
              0.25 × PM10<sub>1mo</sub> + 0.15 × (1−SM<sub>now</sub>) + 0.05 × Wind + 0.20 × T<sub>max</sub>
            </div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", marginTop: 8, lineHeight: 1.5 }}>Is air dusty? Is soil dry? Are winds carrying particulates? Hot enough for maturation?</div>
          </div>
          <div style={{ textAlign: "center", fontSize: 16, color: "rgba(255,255,255,0.2)", fontFamily: "'Playfair Display',serif" }}>× 100</div>
          <div style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: "12px 16px", textAlign: "center" }}>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase" }}>Sporisk Score</div>
            <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 26, color: "#fff", fontWeight: 700, margin: "4px 0 2px" }}>0 – 100</div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", fontFamily: "'DM Sans',sans-serif" }}>Low · Moderate · High · Very High</div>
          </div>
        </div>
        <div style={{ marginTop: 10, textAlign: "right" }}>
          <a href="https://sporisk.vercel.app" target="_blank" rel="noopener noreferrer" style={{ fontSize: 10, color: "#d97706", fontFamily: "'DM Sans',sans-serif", textDecoration: "none", fontWeight: 600 }}>Full scientific methodology →</a>
        </div>
      </div>
    );

    const ModelSection = () => (
      <div>
        <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>Machine Learning</div>
        <div style={{ fontFamily: "'Playfair Display',serif", fontSize: isDesktop ? 22 : 20, color: "#fff", fontWeight: 700, marginBottom: 14 }}>Two Complementary Models</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[
            { icon: "🌲", name: "Random Forest", badge: "Baseline", badgeColor: "rgba(96,165,250,0.15)", badgeBorder: "rgba(96,165,250,0.3)", badgeText: "#60a5fa", desc: "200 trees, max depth 10. 16 hand-engineered lag features. Leave-One-County-Out cross-validation proves spatial generalization.", stats: [{ l: "#1 feature", v: "sm_lag6 (22.3%)" }, { l: "Output", v: "Sporisk 0–100" }] },
            { icon: "🕸️", name: "T-GCN", badge: "Advanced", badgeColor: "rgba(167,139,250,0.15)", badgeBorder: "rgba(167,139,250,0.3)", badgeText: "#a78bfa", desc: "Temporal Graph Convolutional Network — GNN for spatial county-to-county influence + GRU for 6-month temporal lag. Learns end-to-end.", stats: [{ l: "Graph", v: "8 nodes, 11 edges" }, { l: "Output", v: "Case forecast" }] },
          ].map((m, i) => (
            <div key={i} className="formula-card" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: "14px 16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                  <span style={{ fontSize: 20 }}>{m.icon}</span>
                  <div style={{ fontFamily: "'Playfair Display',serif", fontSize: 15, color: "#fff", fontWeight: 700 }}>{m.name}</div>
                </div>
                <div style={{ fontSize: 9, padding: "3px 9px", borderRadius: 100, background: m.badgeColor, border: `1px solid ${m.badgeBorder}`, color: m.badgeText, fontFamily: "'DM Sans',sans-serif", fontWeight: 700, letterSpacing: 0.5 }}>{m.badge}</div>
              </div>
              <p style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", fontFamily: "'DM Sans',sans-serif", lineHeight: 1.6, margin: "0 0 10px", fontWeight: 300 }}>{m.desc}</p>
              <div style={{ display: "flex", gap: 6 }}>
                {m.stats.map((s, j) => (
                  <div key={j} style={{ flex: 1, background: "rgba(0,0,0,0.25)", borderRadius: 8, padding: "6px 8px", textAlign: "center" }}>
                    <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", marginBottom: 2 }}>{s.l}</div>
                    <div style={{ fontSize: 10, color: "rgba(255,255,255,0.7)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600 }}>{s.v}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );

    const PipelineSection = () => (
      <div>
        <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>Stack</div>
        <div style={{ fontFamily: "'Playfair Display',serif", fontSize: isDesktop ? 22 : 20, color: "#fff", fontWeight: 700, marginBottom: 14 }}>From Environment to Prediction</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          {[
            { step: "01", label: "Scraper", desc: "NOAA · EPA AQS · Open-Meteo · CDPH", icon: "📡", color: "#60a5fa" },
            { step: "02", label: "Data Collector", desc: "Lag engineering · normalization · master CSV", icon: "⚙️", color: "#34d399" },
            { step: "03", label: "Random Forest", desc: "Gpot × Erisk × 100 → baseline predictions", icon: "🌲", color: "#fbbf24" },
            { step: "04", label: "T-GCN", desc: "GNN + GRU → case count forecast", icon: "🕸️", color: "#a78bfa" },
            { step: "05", label: "FastAPI / Railway", desc: "Live weather · Gemini AI · REST API", icon: "⚡", color: "#f87171" },
            { step: "06", label: "React / Vercel", desc: "Leaflet map · real-time risk · SMS alerts", icon: "📱", color: "#d97706" },
          ].map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 14px", background: "rgba(255,255,255,0.02)", borderRadius: 10, border: "1px solid rgba(255,255,255,0.05)" }}>
              <div style={{ fontSize: 9, fontFamily: "'DM Sans',sans-serif", fontWeight: 700, color: "rgba(255,255,255,0.2)", minWidth: 20 }}>{s.step}</div>
              <div style={{ fontSize: 16 }}>{s.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.75)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600 }}>{s.label}</div>
                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", marginTop: 1 }}>{s.desc}</div>
              </div>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
            </div>
          ))}
        </div>
      </div>
    );

    const TeamSection = () => (
      <div>
        <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 14 }}>Team · UC San Diego</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {[
            { init: "A", name: "Samudera Bagas Aubreyasta", role: "Data Science" },
            { init: "B", name: "Moch Raka Aryaputra", role: "Mathematics" },
            { init: "C", name: "Olo Hot B. M. S. Margura Silitonga", role: "Electrical Eng." },
            { init: "D", name: "Nathan Raphael Martua Nainggolan", role: "Urban Studies" },
          ].map((t, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 9, padding: "10px 12px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 10 }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: "rgba(217,119,6,0.2)", border: "1px solid rgba(217,119,6,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#d97706", fontFamily: "'Playfair Display',serif", flexShrink: 0 }}>{t.init}</div>
              <div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.65)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, lineHeight: 1.3 }}>{t.name.split(" ").slice(0, 2).join(" ")}</div>
                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", fontFamily: "'DM Sans',sans-serif", marginTop: 1 }}>{t.role}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );

    // ── Shared styles ──────────────────────────────────────────────────────────
    const sharedStyles = `
      @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap');
      .land-fade { opacity:0; transform:translateY(18px); animation: fadeUp 0.65s ease forwards; }
      @keyframes fadeUp { to { opacity:1; transform:translateY(0); } }
      .spore-particle { position:absolute; border-radius:50%; pointer-events:none; animation: drift linear infinite; }
      @keyframes drift { 0%{transform:translateY(0) translateX(0) scale(1);opacity:0.6} 50%{opacity:0.2} 100%{transform:translateY(-120px) translateX(30px) scale(0.4);opacity:0} }
      .pill-btn { transition: all 0.2s; }
      .pill-btn:hover { transform:translateY(-1px); filter:brightness(1.1); }
      .formula-card { transition: transform 0.2s, box-shadow 0.2s; }
      .formula-card:hover { transform:translateY(-2px); box-shadow:0 8px 28px rgba(0,0,0,0.4); }
      .stat-num { font-family:'Playfair Display',serif; }
      /* Desktop scrollbar */
      .land-scroll::-webkit-scrollbar { width:4px; }
      .land-scroll::-webkit-scrollbar-track { background:transparent; }
      .land-scroll::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.12); border-radius:2px; }
      /* Sheet slide-in */
      @keyframes slideUp { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
      @keyframes fadeIn  { from { opacity: 0; } to { opacity: 1; } }
      @keyframes scaleIn { from { transform: scale(0.92); opacity: 0; } to { transform: scale(1); opacity: 1; } }
      @keyframes shimmer { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
      .stat-card-anim { animation: slideUp 0.4s cubic-bezier(0.32,0.72,0,1) both; }
      .sheet-anim { animation: slideUp 0.35s cubic-bezier(0.32,0.72,0,1) both; }
      .fade-in { animation: fadeIn 0.5s ease both; }
      .scale-in { animation: scaleIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both; }
      .hover-lift { transition: transform 0.18s ease, box-shadow 0.18s ease; }
      .hover-lift:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.12); }
    `;

    const particles = [
      { w: 6, h: 6, l: "12%", t: "20%", dur: "7s", del: "0s", bg: "rgba(217,119,6,0.4)" },
      { w: 4, h: 4, l: "78%", t: "35%", dur: "9s", del: "1.5s", bg: "rgba(217,119,6,0.25)" },
      { w: 8, h: 8, l: "55%", t: "60%", dur: "11s", del: "3s", bg: "rgba(217,119,6,0.2)" },
      { w: 3, h: 3, l: "30%", t: "75%", dur: "8s", del: "0.8s", bg: "rgba(255,255,255,0.15)" },
      { w: 5, h: 5, l: "88%", t: "15%", dur: "12s", del: "2s", bg: "rgba(217,119,6,0.3)" },
    ];

    // ── DESKTOP LAYOUT ─────────────────────────────────────────────────────────
    if (isDesktop) {
      return (
        <div style={{ minHeight: "100vh", background: "#0a0c0f", fontFamily: "'Georgia',serif", display: "flex", flexDirection: "column" }}>
          <style>{sharedStyles}</style>

          {/* Top nav bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "18px 48px", borderBottom: "1px solid rgba(255,255,255,0.06)", position: "sticky", top: 0, background: "rgba(10,12,15,0.95)", backdropFilter: "blur(12px)", zIndex: 100 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 22 }}>🍄</span>
              <span style={{ fontFamily: "'Playfair Display',serif", fontWeight: 900, fontSize: 20, color: "#fff", letterSpacing: -0.5 }}>SporeRisk</span>
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", marginLeft: 4 }}>· Project Overview</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{ fontSize: 10, padding: "5px 12px", borderRadius: 12, fontWeight: 600, letterSpacing: 0.5, background: apiConnected ? "rgba(34,197,94,0.12)" : "rgba(255,255,255,0.07)", color: apiConnected ? "#4ade80" : "#64748b", border: `1px solid ${apiConnected ? "rgba(34,197,94,0.25)" : "rgba(255,255,255,0.1)"}`, fontFamily: "'DM Sans',sans-serif" }}>
                {apiConnected ? "● LIVE MODEL" : "● CONNECTING"}
              </div>
              <a href="https://sporisk.vercel.app" target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", fontFamily: "'DM Sans',sans-serif", textDecoration: "none", fontWeight: 500 }}>Theory page ↗</a>
              <button className="pill-btn" onClick={() => goMap(dc)} style={{ padding: "9px 22px", borderRadius: 10, border: "none", background: isHigh ? "#dc2626" : "#d97706", color: "#fff", fontWeight: 700, fontSize: 12, cursor: "pointer", fontFamily: "'DM Sans',sans-serif", letterSpacing: 0.3, boxShadow: isHigh ? "0 2px 16px rgba(220,38,38,0.4)" : "0 2px 16px rgba(217,119,6,0.4)" }}>
                {isHigh ? "⚠️ Open the App →" : "🗺️ Open the App →"}
              </button>
            </div>
          </div>

          {/* Two-column body */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", flex: 1, minHeight: 0 }}>

            {/* LEFT column — hero + stats + team */}
            <div className="land-scroll" style={{ overflowY: "auto", padding: "52px 48px 60px", borderRight: "1px solid rgba(255,255,255,0.06)", position: "relative" }}>
              {particles.map((p, i) => (
                <div key={i} className="spore-particle" style={{ width: p.w, height: p.h, left: p.l, top: p.t, animationDuration: p.dur, animationDelay: p.del, background: p.bg }} />
              ))}

              {/* "This is a presentation" label */}
              <div className="land-fade" style={{ animationDelay: "0.05s", display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(217,119,6,0.1)", border: "1px solid rgba(217,119,6,0.2)", borderRadius: 100, padding: "6px 14px", marginBottom: 20 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#d97706", animation: "pulse 2s infinite" }} />
                <span style={{ fontSize: 10, color: "#d97706", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" }}>Project Overview · HackMerced XI · UC San Diego</span>
              </div>

              <h1 className="land-fade" style={{ animationDelay: "0.1s", fontFamily: "'Playfair Display',serif", fontSize: 52, fontWeight: 900, color: "#fff", lineHeight: 1.05, margin: "0 0 16px", letterSpacing: -2 }}>
                Valley Fever<br /><span style={{ color: "#d97706" }}>Risk</span><br />Intelligence
              </h1>
              <p className="land-fade" style={{ animationDelay: "0.2s", fontSize: 15, color: "rgba(255,255,255,0.5)", lineHeight: 1.75, margin: "0 0 28px", fontFamily: "'DM Sans',sans-serif", fontWeight: 300, maxWidth: 480 }}>
                Spatio-temporal deep learning that predicts <em>Coccidioidomycosis</em> spore risk 4–6 months ahead — turning freely available environmental data into an early warning system for 8 Central Valley counties.
              </p>

              <div className="land-fade" style={{ animationDelay: "0.25s", marginBottom: 32 }}>
                <HeroBadge />
              </div>

              {/* Stats */}
              <div className="land-fade" style={{ animationDelay: "0.3s", marginBottom: 36 }}>
                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 14 }}>The Epidemic</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {[
                    { n: "~12,500", sub: "CA cases in 2024", note: "All-time record", color: "#f87171" },
                    { n: "49", sub: "Kern County deaths", note: "2023 alone", color: "#fbbf24" },
                    { n: "4–6mo", sub: "biological lag", note: "Grow-and-blow", color: "#34d399" },
                    { n: "8", sub: "counties modeled", note: "18,056 daily obs", color: "#60a5fa" },
                  ].map((s, i) => (
                    <div key={i} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, padding: "16px 18px" }}>
                      <div className="stat-num" style={{ fontSize: 30, fontWeight: 700, color: s.color, lineHeight: 1 }}>{s.n}</div>
                      <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", fontFamily: "'DM Sans',sans-serif", marginTop: 4, fontWeight: 500 }}>{s.sub}</div>
                      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.25)", fontFamily: "'DM Sans',sans-serif", marginTop: 2 }}>{s.note}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="land-fade" style={{ animationDelay: "0.35s", marginBottom: 36 }}>
                <PipelineSection />
              </div>
              <div className="land-fade" style={{ animationDelay: "0.4s", marginBottom: 36 }}>
                <TeamSection />
              </div>
              <div className="land-fade" style={{ animationDelay: "0.45s" }}>
                <CTAButtons />
              </div>
            </div>

            {/* RIGHT column — formula + models */}
            <div className="land-scroll" style={{ overflowY: "auto", padding: "52px 48px 60px" }}>
              <div className="land-fade" style={{ animationDelay: "0.15s", marginBottom: 40 }}>
                <FormulaSection />
              </div>
              <div className="land-fade" style={{ animationDelay: "0.3s", marginBottom: 40 }}>
                <ModelSection />
              </div>
            </div>
          </div>
        </div>
      );
    }

    // ── MOBILE LAYOUT ──────────────────────────────────────────────────────────
    return (
      <div style={{ minHeight: "100vh", maxWidth: 480, margin: "0 auto", background: "#0a0c0f", fontFamily: "'Georgia',serif", overflowY: "auto", position: "relative" }}>
        <style>{sharedStyles}</style>

        {particles.map((p, i) => (
          <div key={i} className="spore-particle" style={{ width: p.w, height: p.h, left: p.l, top: p.t, animationDuration: p.dur, animationDelay: p.del, background: p.bg }} />
        ))}

        {/* Nav */}
        <div style={{ padding: "24px 24px 0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <span style={{ fontSize: 22 }}>🍄</span>
            <span style={{ fontFamily: "'Playfair Display',serif", fontWeight: 900, fontSize: 20, color: "#fff", letterSpacing: -0.5 }}>SporeRisk</span>
          </div>
          <div style={{ fontSize: 9, padding: "4px 10px", borderRadius: 12, fontWeight: 600, letterSpacing: 0.5, background: apiConnected ? "rgba(34,197,94,0.15)" : "rgba(255,255,255,0.07)", color: apiConnected ? "#4ade80" : "#64748b", border: `1px solid ${apiConnected ? "rgba(34,197,94,0.3)" : "rgba(255,255,255,0.1)"}`, fontFamily: "'DM Sans',sans-serif" }}>
            {apiConnected ? "● LIVE" : "● CONNECTING"}
          </div>
        </div>

        {/* Hero */}
        <div style={{ padding: "32px 24px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          {/* "This is a presentation" label */}
          <div className="land-fade" style={{ animationDelay: "0.05s", display: "inline-flex", alignItems: "center", gap: 7, background: "rgba(217,119,6,0.1)", border: "1px solid rgba(217,119,6,0.2)", borderRadius: 100, padding: "5px 12px", marginBottom: 16 }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#d97706" }} />
            <span style={{ fontSize: 9, color: "#d97706", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 1, textTransform: "uppercase" }}>Project Overview · HackMerced XI</span>
          </div>
          <h1 className="land-fade" style={{ animationDelay: "0.1s", fontFamily: "'Playfair Display',serif", fontSize: 36, fontWeight: 900, color: "#fff", lineHeight: 1.1, margin: "0 0 12px", letterSpacing: -1 }}>
            Valley Fever<br /><span style={{ color: "#d97706" }}>Risk Intelligence</span><br />for the Central Valley
          </h1>
          <p className="land-fade" style={{ animationDelay: "0.2s", fontSize: 13, color: "rgba(255,255,255,0.5)", lineHeight: 1.7, margin: "0 0 20px", fontFamily: "'DM Sans',sans-serif", fontWeight: 300 }}>
            Spatio-temporal deep learning that predicts spore risk 4–6 months ahead for 8 Central Valley counties.
          </p>
          <div className="land-fade" style={{ animationDelay: "0.3s" }}>
            <HeroBadge />
          </div>
        </div>

        {/* Stats */}
        <div className="land-fade" style={{ animationDelay: "0.35s", padding: "24px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", fontFamily: "'DM Sans',sans-serif", fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", marginBottom: 14 }}>The Epidemic</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[
              { n: "~12,500", sub: "CA cases in 2024", note: "All-time record", color: "#f87171" },
              { n: "49", sub: "Kern County deaths", note: "2023 alone", color: "#fbbf24" },
              { n: "4–6mo", sub: "biological lag", note: "Grow-and-blow", color: "#34d399" },
              { n: "8", sub: "counties modeled", note: "18,056 daily obs", color: "#60a5fa" },
            ].map((s, i) => (
              <div key={i} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, padding: "14px 16px" }}>
                <div className="stat-num" style={{ fontSize: 26, fontWeight: 700, color: s.color, lineHeight: 1 }}>{s.n}</div>
                <div style={{ fontSize: 11, color: "rgba(255,255,255,0.6)", fontFamily: "'DM Sans',sans-serif", marginTop: 4, fontWeight: 500 }}>{s.sub}</div>
                <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", fontFamily: "'DM Sans',sans-serif", marginTop: 2 }}>{s.note}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="land-fade" style={{ animationDelay: "0.4s", padding: "24px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <FormulaSection />
        </div>
        <div className="land-fade" style={{ animationDelay: "0.5s", padding: "24px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <ModelSection />
        </div>
        <div className="land-fade" style={{ animationDelay: "0.55s", padding: "24px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <PipelineSection />
        </div>
        <div className="land-fade" style={{ animationDelay: "0.6s", padding: "24px 24px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <TeamSection />
        </div>
        <div className="land-fade" style={{ animationDelay: "0.65s", padding: "24px 24px 48px" }}>
          <CTAButtons />
        </div>

        {/* Chat overlay */}
        {co && (
          <div style={{ position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)", width: "100%", maxWidth: 480, height: "70vh", background: "#111827", borderRadius: "16px 16px 0 0", boxShadow: "0 -4px 24px rgba(0,0,0,0.5)", zIndex: 400, display: "flex", flexDirection: "column", border: "1px solid #1f2937" }}>
            <div style={{ padding: "12px 16px 8px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1f2937" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span>🍄</span><span style={{ fontWeight: 800, fontSize: 14, color: "#f9fafb", fontFamily: "'DM Sans',sans-serif" }}>SporeRisk AI</span></div>
              <button onClick={() => setCo(false)} style={{ background: "none", border: "none", fontSize: 18, cursor: "pointer", color: "#6b7280" }}>✕</button>
            </div>
            <div style={{ flex: 1, overflowY: "auto", padding: "0 12px 8px" }}>
              {msgs.map((m, i) => (
                <div key={i} style={{ display: "flex", justifyContent: m.r === "u" ? "flex-end" : "flex-start", marginBottom: 8, marginTop: 8 }}>
                  <div style={{ maxWidth: "82%", padding: "8px 12px", fontSize: 12, lineHeight: 1.5, borderRadius: 12, background: m.r === "u" ? "#3b82f6" : "#1f2937", color: m.r === "u" ? "#fff" : "#9ca3af", fontFamily: "'DM Sans',sans-serif" }}>{m.t}</div>
                </div>
              ))}
              {cb && <div style={{ display: "flex", gap: 4, padding: "4px 0" }}>{[0, 1, 2].map(i => <div key={i} style={{ width: 6, height: 6, borderRadius: 3, background: "#374151", animation: `bounce 1s ${i * 0.15}s infinite` }} />)}</div>}
              <div ref={ce} />
            </div>
            <div style={{ padding: "8px 12px 16px", borderTop: "1px solid #1f2937", display: "flex", gap: 8 }}>
              <input value={ci} onChange={e => setCi(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} placeholder="Ask about Valley Fever…" style={{ flex: 1, border: "1px solid #374151", borderRadius: 20, padding: "8px 14px", fontSize: 13, outline: "none", background: "#1f2937", color: "#f9fafb", fontFamily: "'DM Sans',sans-serif" }} disabled={cb} />
              <button onClick={send} disabled={cb || !ci.trim()} style={{ background: "#6366f1", border: "none", borderRadius: 20, padding: "8px 16px", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer", opacity: cb || !ci.trim() ? 0.5 : 1 }}>↑</button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── MAP VIEW ───────────────────────────────────────────────────────────────
  return (
    <>
      <div style={{ height: "100vh", overflow: "hidden", background: lPal.appBg, fontFamily: "'Inter',system-ui,sans-serif", maxWidth: isDesktop ? "100%" : 480, margin: "0 auto", position: "relative", transition: "background 0.6s ease", display: "flex", flexDirection: "column" }}>

        {/* Header */}
        <header style={{ padding: isDesktop ? "11px 24px" : "11px 16px", background: "rgba(255,255,255,0.92)", backdropFilter: "blur(10px)", borderBottom: `2px solid ${lPal.headerBorder}`, display: "flex", justifyContent: "space-between", alignItems: "center", position: "sticky", top: 0, zIndex: 100, transition: "border-color 0.5s ease" }}>
          <div style={{ display: "flex", alignItems: "center", gap: isDesktop ? 12 : 7 }}>
            <button onClick={() => setView("landing")} style={{ display: "flex", alignItems: "center", gap: 5, background: "none", border: "1px solid #e2e8f0", borderRadius: 8, padding: "5px 10px", cursor: "pointer", color: "#64748b", fontSize: 11, fontWeight: 600, fontFamily: "system-ui" }}>
              ← Overview
            </button>
            <span style={{ fontSize: 18 }}>🍄</span>
            <span style={{ fontWeight: 900, fontSize: 18, color: "#1e293b", letterSpacing: -0.5 }}>SporeRisk</span>
            <span style={{ fontSize: 9, color: "#94a3b8", fontWeight: 500, marginLeft: 2 }}>Central Valley</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ fontSize: 9, padding: "3px 8px", borderRadius: 10, fontWeight: 600, background: apiConnected ? lPal.pillBg : "#f1f5f9", color: apiConnected ? lPal.pillText : "#64748b", border: `1px solid ${apiConnected ? lPal.border : "#e2e8f0"}` }}>
              {apiConnected ? "● Live" : usingDummy ? "● Demo" : "● Connecting…"}
            </div>
            {geoData?.detected_county && (
              <div style={{ fontSize: 9, padding: "3px 8px", borderRadius: 10, fontWeight: 600, background: "#f1f5f9", color: "#475569", border: "1px solid #e2e8f0" }}>
                📍 {geoData.detected_county}
              </div>
            )}
          </div>
        </header>

        {/* Dummy data disclaimer banner */}
        {usingDummy && (
          <div className="demo-banner" style={{ background: "linear-gradient(90deg,#fef9ec,#fffbeb)", borderBottom: "1px solid #fde68a", padding: "7px 16px", display: "flex", alignItems: "center", gap: 8, flexShrink: 0, zIndex: 90 }}>
            <span style={{ fontSize: 13 }}>🧪</span>
            <span style={{ fontSize: 10, color: "#92400e", lineHeight: 1.4 }}>
              <strong>Demo Mode — </strong>Live backend offline (Railway free plan). Showing estimated data. In production, an automated scraper would pull real-time NOAA, EPA &amp; CDPH data.
            </span>
          </div>
        )}

        {/* Map section — fills all remaining viewport height */}
        <div style={{ display: "flex", flexDirection: isDesktop ? "row" : "column", flex: 1, minHeight: 0, overflow: "hidden" }}>
          {/* Mode selector — horizontal on mobile, vertical sidebar on desktop */}
          <div style={{ background: "rgba(255,255,255,0.92)", backdropFilter: "blur(4px)", [isDesktop ? "borderRight" : "borderBottom"]: "1px solid #e2e8f0", flexShrink: 0, display: "flex", flexDirection: isDesktop ? "column" : "row", gap: isDesktop ? 4 : 5, padding: isDesktop ? "16px 10px" : "8px 12px", width: isDesktop ? 72 : "auto" }}>
            {[{ id: "normal", lbl: "Normal", icon: "🗺️" }, { id: "vulnerable", lbl: "Vulnerable", icon: "👥" }, { id: "clinics", lbl: "Clinics", icon: "🏥" }].map(m => (
              <button key={m.id} onClick={() => setMapMode(m.id)} style={{
                flex: isDesktop ? 0 : 1, padding: isDesktop ? "10px 4px" : "7px 4px", borderRadius: isDesktop ? 10 : 20,
                border: `1.5px solid ${mapMode === m.id ? lPal.accent : "#e2e8f0"}`,
                background: mapMode === m.id ? lPal.pillBg : "#fff",
                color: mapMode === m.id ? lPal.pillText : "#94a3b8",
                fontWeight: mapMode === m.id ? 700 : 500,
                fontSize: isDesktop ? 9 : 10, cursor: "pointer", transition: "all 0.2s",
                display: "flex", flexDirection: "column", alignItems: "center", gap: 2,
              }}><span style={{ fontSize: isDesktop ? 16 : 12 }}>{m.icon}</span>{m.lbl}</button>
            ))}
          </div>

          {/* Map fills the rest */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <CaliforniaMap
              selectedCounty={sel} riskByCounty={riskByCounty} onCountyClick={tap}
              mapMode={mapMode} vulnZones={vulnZones} clinics={clinicsData}
              onLocate={r => { if (r.county) tap(r.county); }}
            />
          </div>
        </div>

      </div>

      {/* Bottom sheet — outside overflow:hidden root */}
      {sel && sh > 0 && (
        <div onClick={e => e.stopPropagation()} className="sheet-anim" style={{
          position: "fixed", bottom: isDesktop ? 0 : NAV_H, left: isDesktop ? "auto" : "50%", right: isDesktop ? 0 : "auto", transform: isDesktop ? "none" : "translateX(-50%)",
          width: isDesktop ? 420 : "100%", maxWidth: isDesktop ? 420 : 480,
          background: "#fff",
          borderRadius: "18px 18px 0 0",
          boxShadow: "0 -4px 32px rgba(0,0,0,0.13)",
          borderTop: `3px solid ${lPal.accent}`,
          zIndex: 5000,
          height: isDesktop ? "100vh" : (sh === 1 ? "46vh" : `calc(92vh - ${NAV_H}px)`),
          transition: "height 0.3s cubic-bezier(0.32,0.72,0,1)",
          display: "flex", flexDirection: "column",
        }}>
          {/* Handle */}
          <div style={{ padding: "10px 0 5px", display: "flex", flexDirection: "column", alignItems: "center", cursor: "pointer", flexShrink: 0 }} onClick={() => sh === 1 ? setSh(2) : closeSheet()}>
            <div style={{ width: 36, height: 4, borderRadius: 2, background: "#e2e8f0" }} />
            <span style={{ fontSize: 8, color: "#94a3b8", marginTop: 2 }}>{isDesktop || sh === 2 ? "↓ Close" : "↑ Full analysis"}</span>
          </div>

          <div style={{ padding: "0 16px 20px", overflowY: "auto", flex: 1 }}>
            {/* Header: county name + mini gauge + risk badge */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 12, borderBottom: `1px solid ${lPal.border}` }}>
              <div style={{ flex: 1 }}>
                <h2 style={{ margin: 0, fontSize: 20, fontWeight: 900, color: "#0f172a" }}>{sel} County</h2>
                <div style={{ fontSize: 10, color: "#94a3b8", marginTop: 2 }}>California · Central Valley</div>
              </div>
              <MiniGauge riskScore={currentRiskScore} riskLevel={currentRisk} size={70} />
              {currentRisk && currentRisk !== "Unknown" && (
                <div style={{
                  padding: "7px 12px", borderRadius: 20, fontWeight: 800, fontSize: 11,
                  background: lPal.pillBg, color: lPal.pillText,
                  border: `1.5px solid ${lPal.border}`, flexShrink: 0, textAlign: "center",
                }}>
                  {currentRisk === "Very High" && "⚠️ "}{currentRisk}<br />
                  <span style={{ fontSize: 9, fontWeight: 500, opacity: 0.7 }}>Risk</span>
                </div>
              )}
            </div>

            {/* Stat cards — shown first for immediate visibility */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7, marginBottom: 14, animation: "slideUp 0.4s cubic-bezier(0.32,0.72,0,1) 0.05s both" }}>
              <StatCard label="Wind" value={env?.wind_speed_kmh != null ? `${env.wind_speed_kmh.toFixed(0)} km/h` : null} warn={env?.wind_speed_kmh > 15} sub="dispersal: >15 km/h" />
              <StatCard label="PM10 Dust" value={env?.pm10_ugm3 != null ? `${env.pm10_ugm3.toFixed(0)} µg/m³` : null} warn={env?.pm10_ugm3 > 35} sub="high: >35 µg/m³" />
              <StatCard label="Temperature" value={env?.temperature_c != null ? `${env.temperature_c.toFixed(1)}°C` : null} warn={env?.temperature_c > 35} sub="spore-active: 20–40°C" />
              <StatCard label="Precip (7 days)" value={env?.precip_week_mm != null ? `${env.precip_week_mm.toFixed(1)} mm` : null} warn={env?.precip_week_mm === 0} sub="0 mm = dry soil risk" />
            </div>

            {/* AI Risk Summary */}
            <div style={{ background: lPal.summaryBg, borderRadius: 10, padding: "11px 13px", marginBottom: 12, border: `1px solid ${lPal.summaryBorder}` }}>
              <div style={{ fontSize: 9, color: lPal.accent, fontWeight: 700, letterSpacing: 0.5, marginBottom: 5 }}>
                {currentRisk === "Very High" ? "⚠️ CRITICAL RISK ALERT" : "✨ AI Risk Summary"}
              </div>
              {summaryBullets.length > 0 ? (
                <ul style={{ margin: 0, paddingLeft: 14 }}>
                  {summaryBullets.map((b, i) => <li key={i} style={{ fontSize: 11, color: lPal.summaryText, lineHeight: 1.55, marginBottom: 2 }}>{b}</li>)}
                </ul>
              ) : <p style={{ margin: 0, fontSize: 11, color: "#94a3b8" }}>Loading AI analysis…</p>}
            </div>

            {/* Clinics for this county */}
            {mapMode === "clinics" && clinicsData.filter(c => c.county === sel).length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 0.5, marginBottom: 6 }}>NEARBY MEDICAL FACILITIES</div>
                {clinicsData.filter(c => c.county === sel).map((c, i) => (
                  <div key={i} style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 9, padding: "9px 11px", marginBottom: 6 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: "#1e293b", marginBottom: 2 }}>{c.name}</div>
                        <div style={{ fontSize: 9, color: "#94a3b8" }}>{c.address}</div>
                      </div>
                      <div style={{ fontSize: 8, padding: "2px 7px", borderRadius: 10, background: `${CLINIC_COLORS[c.type] || "#2563eb"}15`, color: CLINIC_COLORS[c.type] || "#2563eb", border: `1px solid ${CLINIC_COLORS[c.type] || "#2563eb"}30`, marginLeft: 8, flexShrink: 0 }}>{c.type}</div>
                    </div>
                    {c.note && <div style={{ fontSize: 9, color: lPal.accent, marginTop: 3 }}>✓ {c.note}</div>}
                    {c.phone && <div style={{ fontSize: 9, color: "#94a3b8", marginTop: 2 }}>📞 {c.phone}</div>}
                    {c.address && (
                      <a
                        href={`https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(c.address)}`}
                        target="_blank" rel="noopener noreferrer"
                        style={{ display: "inline-flex", alignItems: "center", gap: 4, marginTop: 6, fontSize: 9, fontWeight: 700, color: "#2563eb", textDecoration: "none", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 6, padding: "3px 8px" }}
                      >
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="3 11 22 2 13 21 11 13 3 11" /></svg>
                        Get Directions
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Advice */}
            {adviceBullets.length > 0 && currentRiskScore >= 2 && (
              <div style={{ background: lPal.accentLight, borderRadius: 10, padding: "11px 13px", marginBottom: 12, border: `1px solid ${lPal.border}` }}>
                <div style={{ fontSize: 9, color: lPal.accent, fontWeight: 700, letterSpacing: 0.5, marginBottom: 6 }}>
                  {currentRisk === "Very High" ? "🚨 IMMEDIATE ACTIONS REQUIRED" : "✓ RECOMMENDED ACTIONS"}
                </div>
                {adviceBullets.map((a, i) => (
                  <div key={i} style={{ display: "flex", gap: 6, marginBottom: 4, alignItems: "flex-start" }}>
                    <span style={{ fontSize: 10, flexShrink: 0, color: lPal.accent }}>●</span>
                    <span style={{ fontSize: 11, color: lPal.summaryText, lineHeight: 1.5 }}>{a}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Community reports */}
            {apiReports?.count > 0 && (
              <div style={{ background: "#fff8f8", borderRadius: 10, padding: "9px 12px", marginBottom: 12, border: "1px solid #fecaca" }}>
                <div style={{ fontSize: 9, color: "#dc2626", fontWeight: 700, letterSpacing: 0.5, marginBottom: 4 }}>
                  🌪️ {apiReports.count} Community Dust Report{apiReports.count > 1 ? "s" : ""} · Last 24h
                </div>
                {apiReports.reports.slice(0, 3).map((r, i) => (
                  <div key={i} style={{ fontSize: 10, color: "#7f1d1d", marginBottom: 2 }}>{"⚠️".repeat(r.severity)} {r.description || "Dust storm reported"}</div>
                ))}
              </div>
            )}

            {/* Expanded content */}
            {sh === 2 && (
              <>
                {/* Two-Phase Risk Index */}
                <div style={{ background: "#fff", borderRadius: 12, padding: "14px 0", marginBottom: 16, borderTop: "1px solid #f1f5f9" }}>
                  <RiskIndexPanel detail={apiDetail} env={env} riskLevel={currentRisk || "Low"} />
                </div>

                {/* Charts like image 2 */}
                {envData.length > 0 && (
                  <>
                    <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>ENVIRONMENTAL DATA</div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: "#1e293b", marginBottom: 12 }}>{sel} — Climate & Air Trends</div>

                    {/* Chart 1: Precipitation & Risk Score */}
                    <LightChart title={`${sel} — Precipitation & Risk Score`} sub="Monthly rainfall (mm) vs risk index" riskLevel={currentRisk || "Low"}>
                      <ComposedChart data={envData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                        <XAxis dataKey="label" tick={{ fontSize: 6, fill: "#94a3b8" }} interval={3} angle={-30} textAnchor="end" height={32} />
                        <YAxis yAxisId="p" tick={{ fontSize: 7, fill: "#4ade80" }} width={28} />
                        <YAxis yAxisId="r" orientation="right" domain={[0, 25]} tickFormatter={v => v} tick={{ fontSize: 7, fill: "#c2573d" }} width={22} />
                        <Tooltip content={<LightTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 9, paddingTop: 4 }} />
                        <Line yAxisId="p" type="monotone" dataKey="precip_mm" name="Precipitation (mm)" stroke="#4ade80" strokeWidth={1.8} dot={{ r: 1.5, fill: "#4ade80" }} connectNulls />
                        <Line yAxisId="r" type="monotone" dataKey="risk_score" name="Risk Score" stroke="#c2573d" strokeWidth={1.8} dot={{ r: 1.5, fill: "#c2573d" }} connectNulls />
                      </ComposedChart>
                    </LightChart>

                    {/* Chart 2: PM10, Soil Moisture & Wind */}
                    <LightChart title={`${sel} — PM10, Soil Moisture & Wind`} sub="PM10 (µg/m³), Soil Moisture (m³/m³), Wind (km/h)" riskLevel={currentRisk || "Low"}>
                      <ComposedChart data={envData} margin={{ top: 4, right: 36, bottom: 0, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                        <XAxis dataKey="label" tick={{ fontSize: 6, fill: "#94a3b8" }} interval={3} angle={-30} textAnchor="end" height={32} />
                        <YAxis yAxisId="left" tick={{ fontSize: 7, fill: "#60a5fa" }} width={30} label={{ value: "PM10/Wind", angle: -90, position: "insideLeft", fontSize: 6, fill: "#94a3b8", offset: 8 }} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 7, fill: "#d4a574" }} width={30} tickFormatter={v => v.toFixed(2)} label={{ value: "Soil Moist.", angle: 90, position: "insideRight", fontSize: 6, fill: "#94a3b8", offset: 8 }} />
                        <Tooltip content={<LightTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 9, paddingTop: 4 }} />
                        <Line yAxisId="left" type="monotone" dataKey="pm10" name="PM10 (µg/m³)" stroke="#60a5fa" strokeWidth={1.8} dot={{ r: 1.5 }} connectNulls />
                        <Line yAxisId="right" type="monotone" dataKey="soil_moisture" name="Soil Moisture" stroke="#d4a574" strokeWidth={1.5} strokeDasharray="5 3" dot={false} connectNulls />
                        <Line yAxisId="left" type="monotone" dataKey="wind_speed" name="Wind (km/h)" stroke="#94a3b8" strokeWidth={1.4} strokeDasharray="4 2" dot={false} connectNulls />
                      </ComposedChart>
                    </LightChart>

                    {/* Chart 3: Historic risk vs cases */}
                    {chartData.length > 0 && (
                      <LightChart title={`${sel} — Risk Index vs Recorded Cases`} sub="Predicted risk (0–100 Sporisk score) and confirmed Valley Fever cases" riskLevel={currentRisk || "Low"}>
                        <ComposedChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                          <XAxis dataKey="d" tick={{ fontSize: 6, fill: "#94a3b8" }} interval={3} angle={-30} textAnchor="end" height={32} />
                          <YAxis yAxisId="risk" domain={[0, 25]} tickFormatter={v => v} tick={{ fontSize: 7, fill: "#7c3aed" }} width={22} />
                          <YAxis yAxisId="cases" orientation="right" tick={{ fontSize: 7, fill: "#60a5fa" }} width={30} />
                          <Tooltip content={<RiskTooltip />} />
                          <Legend wrapperStyle={{ fontSize: 9, paddingTop: 4 }} />
                          {cutLabel && <ReferenceLine yAxisId="risk" x={cutLabel} stroke="#dc2626" strokeWidth={1} strokeDasharray="5 3" label={{ value: "← Actual | Forecast →", position: "insideTopRight", fontSize: 6, fill: "#dc2626" }} />}
                          <Bar yAxisId="cases" dataKey="actual" name="Recorded Cases" fill="#60a5fa33" stroke="#60a5fa" strokeWidth={0.5} barSize={5} />
                          <Line yAxisId="risk" dataKey="riskScore" name="Risk Score" stroke="#7c3aed" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
                        </ComposedChart>
                      </LightChart>
                    )}
                  </>
                )}

                {/* AI Insights */}
                {insightBullets.length > 0 && (
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 9, color: "#94a3b8", fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>GEMINI AI · INSIGHTS</div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: "#1e293b", marginBottom: 8 }}>Pattern Analysis · {sel}</div>
                    <div style={{ background: lPal.summaryBg, borderRadius: 10, padding: "11px 13px", border: `1px solid ${lPal.summaryBorder}` }}>
                      <ul style={{ margin: 0, paddingLeft: 14 }}>
                        {insightBullets.map((b, i) => <li key={i} style={{ fontSize: 11, color: lPal.summaryText, lineHeight: 1.6, marginBottom: 3 }}>{b}</li>)}
                      </ul>
                    </div>
                  </div>
                )}

                <div style={{ height: NAV_H + 8 }} />
              </>
            )}
          </div>
        </div>
      )}

      {/* Chat overlay */}
      {co && (
        <div style={{ position: "fixed", bottom: isDesktop ? 0 : NAV_H, left: isDesktop ? "auto" : "50%", right: isDesktop ? 420 : "auto", transform: isDesktop ? "none" : "translateX(-50%)", width: isDesktop ? 400 : "100%", maxWidth: isDesktop ? 400 : 480, height: isDesktop ? "100vh" : "70vh", background: "#fff", borderRadius: "16px 16px 0 0", boxShadow: "0 -4px 24px rgba(0,0,0,0.1)", zIndex: 5000, display: "flex", flexDirection: "column", border: "1px solid #e2e8f0" }}>
          <div style={{ padding: "12px 16px 8px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #f1f5f9" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span>🍄</span>
              <span style={{ fontWeight: 800, fontSize: 14, color: "#1e293b" }}>SporeRisk AI</span>
              {sel && <span style={{ fontSize: 9, color: "#64748b", background: "#f1f5f9", padding: "2px 6px", borderRadius: 8 }}>{sel}</span>}
            </div>
            <button onClick={() => setCo(false)} style={{ background: "none", border: "none", fontSize: 18, cursor: "pointer", color: "#94a3b8" }}>✕</button>
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "0 12px 8px" }}>
            {msgs.map((m, i) => (
              <div key={i} style={{ display: "flex", justifyContent: m.r === "u" ? "flex-end" : "flex-start", marginBottom: 8, marginTop: 8 }}>
                <div className={m.r === "b" ? "chat-msg-bot" : "chat-msg-user"} style={{ maxWidth: "82%", padding: "8px 12px", fontSize: 12, lineHeight: 1.5 }}>{m.t}</div>
              </div>
            ))}
            {cb && <div style={{ display: "flex", gap: 4, padding: "4px 0" }}>{[0, 1, 2].map(i => <div key={i} style={{ width: 6, height: 6, borderRadius: 3, background: "#e2e8f0", animation: `bounce 1s ${i * 0.15}s infinite` }} />)}</div>}
            <div ref={ce} />
          </div>
          <div style={{ padding: "8px 12px 16px", borderTop: "1px solid #f1f5f9", display: "flex", gap: 8 }}>
            <input value={ci} onChange={e => setCi(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} placeholder={sel ? `Ask about ${sel} County…` : "Ask about Valley Fever…"} style={{ flex: 1, border: "1px solid #e2e8f0", borderRadius: 20, padding: "8px 14px", fontSize: 13, outline: "none", background: "#f8fafc", color: "#1e293b" }} disabled={cb} />
            <button onClick={send} disabled={cb || !ci.trim()} style={{ background: "#6366f1", border: "none", borderRadius: 20, padding: "8px 16px", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer", opacity: cb || !ci.trim() ? 0.5 : 1 }}>↑</button>
          </div>
        </div>
      )}

      {/* Bottom Navbar — floating pill, rendered outside overflow:hidden root */}
      <nav style={{
        position: "fixed", bottom: 16, left: "50%", transform: "translateX(-50%)",
        width: "calc(100% - 48px)", maxWidth: isDesktop ? 220 : 380, height: isDesktop ? 48 : 64,
        background: "rgba(255,255,255,0.97)", backdropFilter: "blur(16px)",
        borderRadius: 32,
        boxShadow: "0 4px 28px rgba(0,0,0,0.13), 0 1px 4px rgba(0,0,0,0.06)",
        border: "1px solid rgba(226,232,240,0.8)",
        display: "flex", alignItems: "center", justifyContent: "space-around",
        zIndex: 9999,
      }}>
        <button onClick={() => setShowSms(true)} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, background: "none", border: "none", cursor: "pointer", padding: "8px 20px" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
          <span style={{ fontSize: 9, fontWeight: 600, color: "#94a3b8" }}>Alerts</span>
        </button>
        <button onClick={() => { setCo(c => !c); if (sh > 0) setSh(0); }} style={{
          display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
          background: co ? lPal.pillBg : "transparent",
          border: `1.5px solid ${co ? lPal.accent : "transparent"}`,
          borderRadius: 20, cursor: "pointer", padding: "8px 22px",
          transition: "all 0.2s",
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={co ? lPal.accent : "#94a3b8"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
          <span style={{ fontSize: 9, fontWeight: 700, color: co ? lPal.accent : "#94a3b8" }}>Chat</span>
        </button>
        <button onClick={() => setShowReport(true)} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3, background: "none", border: "none", cursor: "pointer", padding: "8px 20px" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" /><path d="M9.6 4.6A2 2 0 1 1 11 8H2" /><path d="M12.6 19.4A2 2 0 1 0 14 16H2" /></svg>
          <span style={{ fontSize: 9, fontWeight: 600, color: "#94a3b8" }}>Report</span>
        </button>
      </nav>

      {showReport && <ReportModal county={sel || "Kern"} onClose={() => setShowReport(false)} />}
      {showSms && <SmsModal county={sel || geoData?.detected_county || "Kern"} onClose={() => setShowSms(false)} />}
    </>
  );
}