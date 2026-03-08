import { useState, useEffect, useRef, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

// ─── CONFIG ────────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8080"; // Change to your deployed URL

// ─── RISK COLORS ───────────────────────────────────────────────────────────
const RISK_COLORS = {
  Low: "#22c55e",
  Moderate: "#f59e0b",
  High: "#ef4444",
  "Very High": "#991b1b",
  Unknown: "#6b7280",
};

const RISK_BG = {
  Low: "rgba(34,197,94,0.15)",
  Moderate: "rgba(245,158,11,0.15)",
  High: "rgba(239,68,68,0.15)",
  "Very High": "rgba(153,27,27,0.2)",
  Unknown: "rgba(107,114,128,0.1)",
};

// ─── COUNTY MAP POSITIONS (approximate Central Valley layout) ──────────────
// SVG viewBox coordinates placing counties geographically
const COUNTY_MAP = {
  "San Joaquin": { x: 130, y: 30, w: 80, h: 55 },
  Stanislaus: { x: 120, y: 90, w: 90, h: 50 },
  Merced: { x: 100, y: 145, w: 100, h: 55 },
  Madera: { x: 110, y: 205, w: 90, h: 50 },
  Fresno: { x: 90, y: 260, w: 120, h: 70 },
  Kings: { x: 80, y: 335, w: 90, h: 50 },
  Tulare: { x: 110, y: 390, w: 110, h: 60 },
  Kern: { x: 80, y: 455, w: 140, h: 75 },
};

// ─── MAIN APP ──────────────────────────────────────────────────────────────
export default function SporeRiskApp() {
  const [tab, setTab] = useState("dashboard");
  const [counties, setCounties] = useState([]);
  const [selectedCounty, setSelectedCounty] = useState(null);
  const [countyDetail, setCountyDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    { role: "bot", text: "Hi! I'm SporeRisk's health assistant. Ask me about Valley Fever risk, symptoms, prevention, or nearby healthcare." },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const chatEndRef = useRef(null);

  // ─── FETCH ALL COUNTIES ON MOUNT ─────────────────────────────────────────
  useEffect(() => {
    fetchCounties();
  }, []);

  const fetchCounties = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/counties`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setCounties(data.counties || []);
    } catch (e) {
      setError(`Can't reach API at ${API_BASE} — is the backend running? (${e.message})`);
    } finally {
      setLoading(false);
    }
  };

  // ─── FETCH COUNTY DETAIL ─────────────────────────────────────────────────
  const selectCounty = useCallback(async (name) => {
    setSelectedCounty(name);
    setTab("detail");
    setCountyDetail(null);
    setHistory([]);
    setForecast(null);

    try {
      const [riskRes, histRes, forecastRes] = await Promise.all([
        fetch(`${API_BASE}/risk/${encodeURIComponent(name)}`),
        fetch(`${API_BASE}/history/${encodeURIComponent(name)}`),
        fetch(`${API_BASE}/forecast/${encodeURIComponent(name)}`),
      ]);
      const riskData = await riskRes.json();
      const histData = await histRes.json();
      const forecastData = await forecastRes.json();

      setCountyDetail(riskData);
      setHistory(histData.records || histData.history || []);
      setForecast(forecastData);
    } catch (e) {
      setError(`Failed to load ${name} data: ${e.message}`);
    }
  }, []);

  // ─── CHAT ────────────────────────────────────────────────────────────────
  const sendChat = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const msg = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", text: msg }]);
    setChatLoading(true);

    try {
      const body = { message: msg };
      if (selectedCounty) body.county = selectedCounty;

      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: data.reply || data.detail || "No response", sources: data.sources },
      ]);
    } catch (e) {
      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: `Error: ${e.message}. Is the backend running?` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // ─── RENDER ──────────────────────────────────────────────────────────────
  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 22 }}>🍄</span>
            <span style={styles.logo}>SporeRisk</span>
          </div>
          <span style={styles.tagline}>Valley Fever Early Warning</span>
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        {tab === "dashboard" && (
          <DashboardTab
            counties={counties}
            loading={loading}
            error={error}
            onSelect={selectCounty}
            onRetry={fetchCounties}
          />
        )}
        {tab === "detail" && (
          <DetailTab
            county={selectedCounty}
            detail={countyDetail}
            history={history}
            forecast={forecast}
            onBack={() => setTab("dashboard")}
          />
        )}
        {tab === "about" && <AboutTab />}
      </main>

      {/* Floating Chat Bubble */}
      {!chatOpen && (
        <button style={styles.chatBubble} onClick={() => setChatOpen(true)} aria-label="Open chat">
          💬
        </button>
      )}

      {/* Chat Overlay */}
      {chatOpen && (
        <div style={styles.chatOverlay}>
          <div style={styles.chatHeader}>
            <span style={{ fontWeight: 700 }}>🍄 SporeRisk Assistant</span>
            <button style={styles.chatClose} onClick={() => setChatOpen(false)}>✕</button>
          </div>
          <div style={styles.chatBody}>
            {chatMessages.map((m, i) => (
              <div key={i} style={m.role === "user" ? styles.chatUser : styles.chatBot}>
                <div style={m.role === "user" ? styles.chatUserBubble : styles.chatBotBubble}>
                  {m.text}
                  {m.sources && m.sources.length > 0 && (
                    <div style={styles.chatSources}>
                      {m.sources.map((s, j) => (
                        <span key={j} style={styles.sourceTag}>{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div style={styles.chatBot}>
                <div style={styles.chatBotBubble}>Thinking...</div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
          <div style={styles.chatInputRow}>
            <input
              style={styles.chatInputField}
              placeholder="Ask about Valley Fever..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendChat()}
            />
            <button style={styles.chatSend} onClick={sendChat} disabled={chatLoading}>
              ➤
            </button>
          </div>
        </div>
      )}

      {/* Bottom Tab Bar */}
      <nav style={styles.tabBar}>
        {[
          { id: "dashboard", icon: "🗺️", label: "Dashboard" },
          { id: "detail", icon: "📊", label: "Detail" },
          { id: "about", icon: "ℹ️", label: "About" },
        ].map((t) => (
          <button
            key={t.id}
            style={{
              ...styles.tabBtn,
              color: tab === t.id ? "#1d4ed8" : "#6b7280",
              borderTop: tab === t.id ? "2px solid #1d4ed8" : "2px solid transparent",
            }}
            onClick={() => {
              if (t.id === "detail" && !selectedCounty) return;
              setTab(t.id);
            }}
          >
            <span style={{ fontSize: 18 }}>{t.icon}</span>
            <span style={{ fontSize: 11, marginTop: 2 }}>{t.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// DASHBOARD TAB
// ═══════════════════════════════════════════════════════════════════════════
function DashboardTab({ counties, loading, error, onSelect, onRetry }) {
  const riskByCounty = {};
  counties.forEach((c) => {
    riskByCounty[c.county] = c;
  });

  return (
    <div style={{ padding: 16 }}>
      <h2 style={styles.sectionTitle}>Central Valley Risk Map</h2>
      <p style={styles.subtitle}>Tap a county to view details</p>

      {error && (
        <div style={styles.errorBox}>
          <p>{error}</p>
          <button style={styles.retryBtn} onClick={onRetry}>Retry</button>
        </div>
      )}

      {loading && !error && <p style={styles.loadingText}>Loading county data...</p>}

      {/* SVG MAP */}
      {!loading && !error && (
        <div style={styles.mapContainer}>
          <svg viewBox="0 0 300 560" style={{ width: "100%", maxWidth: 340, margin: "0 auto", display: "block" }}>
            {/* Background */}
            <rect x="0" y="0" width="300" height="560" rx="12" fill="#f0f4f8" />
            <text x="150" y="20" textAnchor="middle" fontSize="10" fill="#94a3b8" fontFamily="sans-serif">
              California's Central Valley
            </text>

            {Object.entries(COUNTY_MAP).map(([name, pos]) => {
              const data = riskByCounty[name];
              const risk = data?.risk_level || "Unknown";
              const color = RISK_COLORS[risk];
              const bg = RISK_BG[risk];
              const cases = data?.predicted_cases;

              return (
                <g key={name} onClick={() => onSelect(name)} style={{ cursor: "pointer" }}>
                  <rect
                    x={pos.x}
                    y={pos.y}
                    width={pos.w}
                    height={pos.h}
                    rx={6}
                    fill={bg}
                    stroke={color}
                    strokeWidth={2}
                  />
                  <text
                    x={pos.x + pos.w / 2}
                    y={pos.y + pos.h / 2 - 6}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight="700"
                    fill="#1e293b"
                    fontFamily="sans-serif"
                  >
                    {name}
                  </text>
                  <text
                    x={pos.x + pos.w / 2}
                    y={pos.y + pos.h / 2 + 8}
                    textAnchor="middle"
                    fontSize="9"
                    fontWeight="600"
                    fill={color}
                    fontFamily="sans-serif"
                  >
                    {risk}
                  </text>
                  {cases != null && (
                    <text
                      x={pos.x + pos.w / 2}
                      y={pos.y + pos.h / 2 + 20}
                      textAnchor="middle"
                      fontSize="8"
                      fill="#64748b"
                      fontFamily="sans-serif"
                    >
                      ~{cases} cases/mo
                    </text>
                  )}
                </g>
              );
            })}

            {/* Legend */}
            {[
              { label: "Low", color: RISK_COLORS.Low, y: 0 },
              { label: "Moderate", color: RISK_COLORS.Moderate, y: 16 },
              { label: "High", color: RISK_COLORS.High, y: 32 },
              { label: "Very High", color: RISK_COLORS["Very High"], y: 48 },
            ].map((l) => (
              <g key={l.label}>
                <rect x={10} y={538 - 60 + l.y} width={10} height={10} rx={2} fill={l.color} />
                <text x={24} y={538 - 60 + l.y + 9} fontSize="8" fill="#475569" fontFamily="sans-serif">
                  {l.label}
                </text>
              </g>
            ))}
          </svg>
        </div>
      )}

      {/* County Cards */}
      {!loading && !error && counties.length > 0 && (
        <div style={styles.cardGrid}>
          {counties.map((c) => (
            <button key={c.county} style={styles.countyCard} onClick={() => onSelect(c.county)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={styles.cardCounty}>{c.county}</span>
                <span
                  style={{
                    ...styles.riskBadge,
                    backgroundColor: RISK_BG[c.risk_level],
                    color: RISK_COLORS[c.risk_level],
                  }}
                >
                  {c.risk_level}
                </span>
              </div>
              <div style={styles.cardMeta}>
                ~{c.predicted_cases} predicted cases/month
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// DETAIL TAB
// ═══════════════════════════════════════════════════════════════════════════
function DetailTab({ county, detail, history, forecast, onBack }) {
  if (!county) {
    return (
      <div style={{ padding: 16, textAlign: "center", marginTop: 40 }}>
        <p style={{ color: "#64748b" }}>Select a county from the Dashboard first</p>
      </div>
    );
  }

  const risk = detail?.risk;
  const env = detail?.environment;
  const summary = detail?.summary;
  const riskLevel = risk?.risk_level || "Unknown";

  // Build chart data from history
  const chartData = (history || []).map((h) => ({
    label: `${h.year}-${String(h.month).padStart(2, "0")}`,
    actual: h.monthly_cases,
    predicted: h.predicted_cases,
  }));

  // Forecast chart (baseline)
  const forecastChart = (forecast?.baseline_forecast || []).map((f) => ({
    label: `${f.year}-${String(f.month).padStart(2, "0")}`,
    predicted: f.predicted_cases,
    risk: f.risk_level,
  }));

  return (
    <div style={{ padding: 16 }}>
      <button style={styles.backBtn} onClick={onBack}>← Back to Map</button>

      <h2 style={styles.sectionTitle}>{county} County</h2>

      {/* Risk Card */}
      {risk && (
        <div
          style={{
            ...styles.riskCard,
            borderLeft: `4px solid ${RISK_COLORS[riskLevel]}`,
            background: RISK_BG[riskLevel],
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={styles.riskLabel}>Current Risk Level</div>
              <div style={{ fontSize: 28, fontWeight: 800, color: RISK_COLORS[riskLevel] }}>
                {riskLevel}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={styles.riskLabel}>Predicted Cases</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#1e293b" }}>
                {risk.predicted_cases}
              </div>
              <div style={{ fontSize: 11, color: "#64748b" }}>per month</div>
            </div>
          </div>
        </div>
      )}

      {/* Environment Stats */}
      {env && env.source !== "unavailable" && (
        <div style={styles.envGrid}>
          <EnvStat label="Temp" value={env.temperature_c != null ? `${env.temperature_c}°C` : "—"} />
          <EnvStat label="Wind" value={env.wind_speed_kmh != null ? `${env.wind_speed_kmh} km/h` : "—"} />
          <EnvStat label="PM10" value={env.pm10_ugm3 != null ? `${env.pm10_ugm3} µg/m³` : "—"} />
          <EnvStat label="Rain" value={env.precipitation_mm != null ? `${env.precipitation_mm} mm` : "—"} />
        </div>
      )}

      {/* AI Summary Bullets */}
      {summary && summary.length > 0 && (
        <div style={styles.summaryBox}>
          <div style={styles.summaryTitle}>Risk Analysis</div>
          {summary.map((s, i) => (
            <div key={i} style={styles.bulletItem}>
              <span style={styles.bulletDot}>•</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
      )}

      {/* History Chart */}
      {chartData.length > 0 && (
        <div style={styles.chartBox}>
          <div style={styles.chartTitle}>Historical Cases</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 9 }}
                interval={Math.max(0, Math.floor(chartData.length / 6) - 1)}
              />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="actual" stroke="#3b82f6" name="Actual" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="predicted" stroke="#f59e0b" name="Predicted" dot={false} strokeWidth={2} strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Forecast Chart */}
      {forecastChart.length > 0 && (
        <div style={styles.chartBox}>
          <div style={styles.chartTitle}>Forecast (Random Forest)</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={forecastChart}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" tick={{ fontSize: 9 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="predicted" stroke="#8b5cf6" name="Forecast" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* T-GCN Forecast */}
      {forecast?.tgcn_forecast?.length > 0 && (
        <div style={styles.chartBox}>
          <div style={styles.chartTitle}>T-GCN Model (Actual vs Predicted)</div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={forecast.tgcn_forecast}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="test_sample" tick={{ fontSize: 10 }} label={{ value: "Test Sample", position: "insideBottom", offset: -5, fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="actual_cases" stroke="#3b82f6" name="Actual" strokeWidth={2} />
              <Line type="monotone" dataKey="predicted_cases" stroke="#ef4444" name="T-GCN Predicted" strokeWidth={2} strokeDasharray="4 4" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {!detail && (
        <div style={styles.loadingText}>Loading {county} data...</div>
      )}
    </div>
  );
}

function EnvStat({ label, value }) {
  return (
    <div style={styles.envItem}>
      <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", marginTop: 2 }}>{value}</div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ABOUT TAB
// ═══════════════════════════════════════════════════════════════════════════
function AboutTab() {
  return (
    <div style={{ padding: 16 }}>
      <h2 style={styles.sectionTitle}>About SporeRisk</h2>

      <div style={styles.aboutSection}>
        <h3 style={styles.aboutH3}>What is Valley Fever?</h3>
        <p style={styles.aboutP}>
          Valley Fever (Coccidioidomycosis) is a fungal lung infection caused by <em>Coccidioides</em> spores
          found in soil across California's Central Valley. When disturbed by wind, construction, or farming,
          these spores become airborne and can be inhaled. Most infections are mild, but severe cases can be
          life-threatening — especially for immunocompromised individuals, outdoor workers, and communities
          in high-exposure areas.
        </p>
      </div>

      <div style={styles.aboutSection}>
        <h3 style={styles.aboutH3}>How SporeRisk Works</h3>
        <p style={styles.aboutP}>
          SporeRisk combines environmental data (temperature, wind, dust/PM10, precipitation) with
          historical case data from CDPH to predict Valley Fever risk across 8 Central Valley counties.
        </p>
        <div style={styles.techStack}>
          <TechItem label="Random Forest" desc="200-tree ensemble with 16 lag features for monthly case prediction" />
          <TechItem label="T-GCN" desc="Temporal Graph Convolutional Network modeling spatial spread between counties" />
          <TechItem label="Real-time Data" desc="Open-Meteo weather, EPA air quality, CDPH case reports" />
          <TechItem label="AI Assistant" desc="Gemini-powered chatbot with Google Search for local healthcare resources" />
        </div>
      </div>

      <div style={styles.aboutSection}>
        <h3 style={styles.aboutH3}>Risk Index</h3>
        <p style={styles.aboutP}>
          Our risk index combines Growth Potential (soil moisture, temperature, precipitation lag)
          and Exposure Risk (dust levels, wind, soil dryness, temperature) into a composite score:
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
          {Object.entries(RISK_COLORS).filter(([k]) => k !== "Unknown").map(([level, color]) => (
            <span key={level} style={{ padding: "4px 12px", borderRadius: 12, fontSize: 12, fontWeight: 600, backgroundColor: RISK_BG[level], color }}>
              {level}
            </span>
          ))}
        </div>
      </div>

      <div style={styles.aboutSection}>
        <h3 style={styles.aboutH3}>Our Mission</h3>
        <p style={styles.aboutP}>
          Built at UC Merced for HackMerced IX, SporeRisk is aligned with CITRIS (Center for Information
          Technology Research in the Interest of Society) core values: leveraging technology to address
          society's most pressing challenges. We believe every Central Valley community deserves equitable
          access to health intelligence — especially the farmworkers, outdoor laborers, and underserved
          populations disproportionately affected by Valley Fever.
        </p>
      </div>

      <div style={{ textAlign: "center", marginTop: 24, padding: 16, borderTop: "1px solid #e2e8f0" }}>
        <div style={{ fontSize: 12, color: "#64748b" }}>
          SporeRisk — HackMerced IX @ UC Merced
        </div>
        <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
          CITRIS · Valley Fever Early Warning System
        </div>
      </div>
    </div>
  );
}

function TechItem({ label, desc }) {
  return (
    <div style={styles.techItem}>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#1e293b" }}>{label}</div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{desc}</div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════════════════════════════════════
const styles = {
  app: {
    fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    maxWidth: 430,
    margin: "0 auto",
    background: "#ffffff",
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    position: "relative",
    color: "#1e293b",
  },
  header: {
    background: "linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%)",
    padding: "14px 16px",
    position: "sticky",
    top: 0,
    zIndex: 100,
  },
  headerInner: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  logo: {
    fontSize: 18,
    fontWeight: 800,
    color: "#ffffff",
    letterSpacing: -0.5,
  },
  tagline: {
    fontSize: 11,
    color: "#94b8d8",
    fontWeight: 500,
  },
  main: {
    flex: 1,
    paddingBottom: 72,
    overflowY: "auto",
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 800,
    color: "#0f172a",
    margin: "0 0 4px 0",
  },
  subtitle: {
    fontSize: 13,
    color: "#64748b",
    margin: "0 0 16px 0",
  },

  // Error
  errorBox: {
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: 10,
    padding: 16,
    marginBottom: 16,
    fontSize: 13,
    color: "#991b1b",
  },
  retryBtn: {
    marginTop: 8,
    padding: "6px 16px",
    borderRadius: 6,
    border: "none",
    background: "#1d4ed8",
    color: "#fff",
    fontSize: 12,
    fontWeight: 600,
    cursor: "pointer",
  },
  loadingText: {
    textAlign: "center",
    padding: 40,
    color: "#64748b",
    fontSize: 14,
  },

  // Map
  mapContainer: {
    marginBottom: 20,
    borderRadius: 12,
    overflow: "hidden",
    border: "1px solid #e2e8f0",
  },

  // County cards
  cardGrid: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  countyCard: {
    width: "100%",
    textAlign: "left",
    padding: "12px 14px",
    borderRadius: 10,
    border: "1px solid #e2e8f0",
    background: "#fff",
    cursor: "pointer",
    transition: "box-shadow 0.15s",
    outline: "none",
    fontFamily: "inherit",
  },
  cardCounty: {
    fontSize: 15,
    fontWeight: 700,
    color: "#0f172a",
  },
  riskBadge: {
    fontSize: 11,
    fontWeight: 700,
    padding: "3px 10px",
    borderRadius: 10,
  },
  cardMeta: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 4,
  },

  // Detail
  backBtn: {
    background: "none",
    border: "none",
    color: "#1d4ed8",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    padding: "4px 0",
    marginBottom: 8,
    fontFamily: "inherit",
  },
  riskCard: {
    borderRadius: 12,
    padding: 16,
    marginTop: 12,
    marginBottom: 16,
  },
  riskLabel: {
    fontSize: 11,
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    fontWeight: 600,
  },
  envGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr 1fr",
    gap: 8,
    marginBottom: 16,
  },
  envItem: {
    background: "#f8fafc",
    borderRadius: 8,
    padding: "10px 8px",
    textAlign: "center",
    border: "1px solid #e2e8f0",
  },
  summaryBox: {
    background: "#f8fafc",
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
    border: "1px solid #e2e8f0",
  },
  summaryTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: 8,
  },
  bulletItem: {
    display: "flex",
    gap: 8,
    fontSize: 13,
    color: "#334155",
    marginBottom: 6,
    lineHeight: 1.4,
  },
  bulletDot: {
    color: "#1d4ed8",
    fontWeight: 700,
    flexShrink: 0,
  },
  chartBox: {
    marginBottom: 20,
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    padding: "12px 8px 4px",
    background: "#fff",
  },
  chartTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: "#0f172a",
    marginBottom: 8,
    paddingLeft: 8,
  },

  // About
  aboutSection: {
    marginBottom: 20,
  },
  aboutH3: {
    fontSize: 15,
    fontWeight: 700,
    color: "#0f172a",
    margin: "0 0 6px 0",
  },
  aboutP: {
    fontSize: 13,
    color: "#475569",
    lineHeight: 1.6,
    margin: 0,
  },
  techStack: {
    marginTop: 10,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  techItem: {
    background: "#f8fafc",
    borderRadius: 8,
    padding: 10,
    border: "1px solid #e2e8f0",
  },

  // Chat
  chatBubble: {
    position: "fixed",
    bottom: 80,
    right: 16,
    width: 52,
    height: 52,
    borderRadius: 26,
    background: "linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 100%)",
    border: "none",
    fontSize: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
    zIndex: 200,
  },
  chatOverlay: {
    position: "fixed",
    bottom: 72,
    right: 8,
    left: 8,
    maxWidth: 414,
    margin: "0 auto",
    height: "60vh",
    background: "#fff",
    borderRadius: "16px 16px 0 0",
    boxShadow: "0 -4px 24px rgba(0,0,0,0.15)",
    display: "flex",
    flexDirection: "column",
    zIndex: 300,
    overflow: "hidden",
  },
  chatHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 16px",
    background: "linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%)",
    color: "#fff",
    fontSize: 14,
  },
  chatClose: {
    background: "none",
    border: "none",
    color: "#fff",
    fontSize: 18,
    cursor: "pointer",
    padding: "2px 6px",
  },
  chatBody: {
    flex: 1,
    overflowY: "auto",
    padding: 12,
  },
  chatUser: {
    display: "flex",
    justifyContent: "flex-end",
    marginBottom: 8,
  },
  chatBot: {
    display: "flex",
    justifyContent: "flex-start",
    marginBottom: 8,
  },
  chatUserBubble: {
    maxWidth: "80%",
    padding: "8px 12px",
    borderRadius: "12px 12px 2px 12px",
    background: "#1d4ed8",
    color: "#fff",
    fontSize: 13,
    lineHeight: 1.4,
    whiteSpace: "pre-wrap",
  },
  chatBotBubble: {
    maxWidth: "80%",
    padding: "8px 12px",
    borderRadius: "12px 12px 12px 2px",
    background: "#f1f5f9",
    color: "#1e293b",
    fontSize: 13,
    lineHeight: 1.4,
    whiteSpace: "pre-wrap",
  },
  chatSources: {
    marginTop: 6,
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
  },
  sourceTag: {
    fontSize: 9,
    padding: "2px 6px",
    borderRadius: 4,
    background: "#e2e8f0",
    color: "#64748b",
  },
  chatInputRow: {
    display: "flex",
    padding: "8px 12px",
    borderTop: "1px solid #e2e8f0",
    gap: 8,
  },
  chatInputField: {
    flex: 1,
    padding: "8px 12px",
    borderRadius: 20,
    border: "1px solid #d1d5db",
    fontSize: 13,
    outline: "none",
    fontFamily: "inherit",
  },
  chatSend: {
    width: 36,
    height: 36,
    borderRadius: 18,
    border: "none",
    background: "#1d4ed8",
    color: "#fff",
    fontSize: 16,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },

  // Tab bar
  tabBar: {
    position: "fixed",
    bottom: 0,
    left: 0,
    right: 0,
    maxWidth: 430,
    margin: "0 auto",
    display: "flex",
    justifyContent: "space-around",
    background: "#fff",
    borderTop: "1px solid #e2e8f0",
    padding: "6px 0 10px",
    zIndex: 100,
  },
  tabBtn: {
    flex: 1,
    background: "none",
    border: "none",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    cursor: "pointer",
    padding: "4px 0",
    fontFamily: "inherit",
    fontWeight: 600,
  },
};