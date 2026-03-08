import { useState, useEffect, useRef, useCallback } from "react";
import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, AreaChart, Area, ReferenceLine,
} from "recharts";

/* ═══════════════════════════════════════════════════════════════════════════ */
const API = "http://localhost:8080";

// Try API first, fall back to mock if unavailable
async function apiFetch(path) {
  try {
    const res = await fetch(`${API}${path}`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`${res.status}`);
    return await res.json();
  } catch { return null; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   COUNTY PATHS
   ═══════════════════════════════════════════════════════════════════════════ */
const CP = {
  "San Joaquin": { d:"M27.7,33.9 L20.6,49.9 L21.3,104.1 L27.7,116.9 L44.7,128.1 L51.7,139.3 L66.6,134.5 L65.9,102.6 L62.4,72.2 L56.0,62.7 L44.7,43.5 L37.6,37.1 Z", cx:43.9, cy:85 },
  "Stanislaus": { d:"M42.5,129.7 L44.7,158.4 L51.7,172.8 L66.6,172.8 L85.7,171.2 L85.7,142.4 L77.2,132.9 L65.9,134.5 L51.7,139.3 Z", cx:63.5, cy:150 },
  "Merced": { d:"M44.7,158.4 L51.7,172.8 L66.6,222.2 L85.7,239.8 L109.1,236.6 L128.2,227.0 L128.2,188.7 L109.1,164.8 L85.7,171.2 L66.6,172.8 Z", cx:88, cy:195 },
  "Madera": { d:"M109.1,164.8 L128.2,188.7 L128.2,227.0 L144.4,235.0 L162.1,241.4 L180.5,225.4 L201.0,193.5 L201.0,160.0 L179.8,156.8 L144.4,161.6 Z", cx:158, cy:195 },
  "Fresno": { d:"M66.6,222.2 L85.7,239.8 L109.1,236.6 L128.2,227.0 L144.4,235.0 L162.1,241.4 L180.5,225.4 L201.0,193.5 L247.7,241.4 L247.7,322.8 L216.6,343.5 L169.2,343.5 L145.8,324.4 L118.3,298.8 L85.7,260.5 Z", cx:154, cy:264 },
  "Kings": { d:"M118.3,324.4 L118.3,373.8 L118.3,426.5 L155.0,428.1 L169.2,426.5 L169.2,380.2 L145.8,354.7 L134.5,343.5 Z", cx:141, cy:382 },
  "Tulare": { d:"M162.1,316.4 L169.2,380.2 L169.2,426.5 L188.3,428.1 L216.6,428.1 L252.0,426.5 L252.0,378.6 L240.0,343.5 L216.6,322.8 L180.5,316.4 Z", cx:205, cy:377 },
  "Kern": { d:"M118.3,426.5 L155.0,428.1 L188.3,428.1 L216.6,428.1 L252.0,426.5 L299.4,487.1 L299.4,582.9 L243.5,586.1 L183.3,586.1 L155.0,570.1 L135.2,535.0 L135.2,477.6 L118.3,450.4 Z", cx:192, cy:493 },
};
const NP = {
  "Monterey":"M-2.7,251 L27.7,298.8 L85.7,354.7 L66.6,260.5 L39.7,222.2 L-2.7,219 Z",
  "San Benito":"M27.7,219 L44.7,263.7 L66.6,260.5 L85.7,239.8 L66.6,222.2 L44.7,203.1 Z",
  "Tuolumne":"M85.7,59.5 L109.1,104.1 L144.4,104.1 L188.3,97.8 L188.3,56.3 L128.2,59.5 Z",
  "Mariposa":"M109.1,104.1 L128.2,155.2 L179.8,156.8 L201.0,160.0 L188.3,97.8 L144.4,104.1 Z",
  "Inyo":"M247.7,235 L287.4,266.9 L299.4,362.7 L299.4,426.5 L252.0,426.5 L252.0,378.6 L240.0,343.5 L247.7,241.4 Z",
  "SLO":"M68,428.1 L85.7,487.1 L118.3,522.2 L135.2,535 L135.2,477.6 L118.3,450.4 L118.3,426.5 Z",
};

/* ═══════════════════════════════════════════════════════════════════════════
   MONTHLY DATA
   ═══════════════════════════════════════════════════════════════════════════ */
const MONTHS=["Jul 2025","Aug 2025","Sep 2025","Oct 2025","Nov 2025","Dec 2025","Jan 2026","Feb 2026","Mar 2026","Apr 2026","May 2026","Jun 2026"];
const MKEYS=["2025-07","2025-08","2025-09","2025-10","2025-11","2025-12","2026-01","2026-02","2026-03","2026-04","2026-05","2026-06"];

const META={Fresno:{lat:36.74,lon:-119.79},Kern:{lat:35.34,lon:-118.73},Kings:{lat:36.07,lon:-119.82},Madera:{lat:37.22,lon:-119.76},Merced:{lat:37.19,lon:-120.72},"San Joaquin":{lat:37.93,lon:-121.27},Stanislaus:{lat:37.56,lon:-121.00},Tulare:{lat:36.21,lon:-119.05}};

const MD={"Fresno":[{ac:46.1,pc:46.0,rl:"High"},{ac:69.1,pc:147.2,rl:"Very High"},{ac:80.6,pc:250.5,rl:"Very High"},{ac:86.4,pc:104.7,rl:"Very High"},{ac:74.9,pc:82.1,rl:"Very High"},{ac:51.8,pc:45.5,rl:"High"},{ac:null,pc:24.1,rl:"Moderate"},{ac:null,pc:11.9,rl:"Moderate"},{ac:null,pc:32.3,rl:"High"},{ac:null,pc:28.5,rl:"Moderate"},{ac:null,pc:38.2,rl:"High"},{ac:null,pc:52.8,rl:"High"}],"Kern":[{ac:144.0,pc:20.7,rl:"Moderate"},{ac:216.0,pc:15.4,rl:"Moderate"},{ac:252.0,pc:12.6,rl:"Moderate"},{ac:270.0,pc:10.0,rl:"Moderate"},{ac:234.0,pc:27.3,rl:"Moderate"},{ac:162.0,pc:14.1,rl:"Moderate"},{ac:null,pc:5.8,rl:"Low"},{ac:null,pc:3.6,rl:"Low"},{ac:null,pc:5.8,rl:"Low"},{ac:null,pc:12.4,rl:"Moderate"},{ac:null,pc:28.5,rl:"Moderate"},{ac:null,pc:65.2,rl:"High"}],"Kings":[{ac:9.6,pc:103.8,rl:"Very High"},{ac:14.4,pc:25.4,rl:"Moderate"},{ac:16.8,pc:25.2,rl:"Moderate"},{ac:18.0,pc:32.0,rl:"High"},{ac:15.6,pc:68.2,rl:"High"},{ac:10.8,pc:66.4,rl:"High"},{ac:null,pc:38.1,rl:"High"},{ac:null,pc:25.8,rl:"Moderate"},{ac:null,pc:20.7,rl:"Moderate"},{ac:null,pc:15.4,rl:"Moderate"},{ac:null,pc:22.1,rl:"Moderate"},{ac:null,pc:31.8,rl:"High"}],"Madera":[{ac:4.0,pc:66.7,rl:"High"},{ac:6.0,pc:52.4,rl:"High"},{ac:7.0,pc:95.2,rl:"Very High"},{ac:7.5,pc:112.5,rl:"Very High"},{ac:6.5,pc:76.1,rl:"High"},{ac:4.5,pc:19.7,rl:"Moderate"},{ac:null,pc:12.3,rl:"Moderate"},{ac:null,pc:15.3,rl:"Moderate"},{ac:null,pc:24.6,rl:"Moderate"},{ac:null,pc:18.8,rl:"Moderate"},{ac:null,pc:32.1,rl:"High"},{ac:null,pc:48.5,rl:"High"}],"Merced":[{ac:8.0,pc:26.5,rl:"Moderate"},{ac:12.0,pc:24.1,rl:"Moderate"},{ac:14.0,pc:35.1,rl:"High"},{ac:15.0,pc:49.7,rl:"High"},{ac:13.0,pc:39.5,rl:"High"},{ac:9.0,pc:42.7,rl:"High"},{ac:null,pc:36.3,rl:"High"},{ac:null,pc:32.7,rl:"High"},{ac:null,pc:27.5,rl:"Moderate"},{ac:null,pc:22.4,rl:"Moderate"},{ac:null,pc:28.8,rl:"Moderate"},{ac:null,pc:38.2,rl:"High"}],"San Joaquin":[{ac:21.8,pc:53.6,rl:"High"},{ac:32.6,pc:70.0,rl:"High"},{ac:38.1,pc:136.9,rl:"Very High"},{ac:40.8,pc:44.7,rl:"High"},{ac:35.4,pc:59.1,rl:"High"},{ac:24.5,pc:59.8,rl:"High"},{ac:null,pc:16.8,rl:"Moderate"},{ac:null,pc:22.3,rl:"Moderate"},{ac:null,pc:24.1,rl:"Moderate"},{ac:null,pc:18.5,rl:"Moderate"},{ac:null,pc:25.2,rl:"Moderate"},{ac:null,pc:35.8,rl:"High"}],"Stanislaus":[{ac:7.2,pc:29.0,rl:"Moderate"},{ac:10.8,pc:26.5,rl:"Moderate"},{ac:12.6,pc:41.1,rl:"High"},{ac:13.5,pc:47.2,rl:"High"},{ac:11.7,pc:38.8,rl:"High"},{ac:8.1,pc:40.8,rl:"High"},{ac:null,pc:17.5,rl:"Moderate"},{ac:null,pc:7.3,rl:"Low"},{ac:null,pc:10.1,rl:"Moderate"},{ac:null,pc:8.2,rl:"Low"},{ac:null,pc:14.5,rl:"Moderate"},{ac:null,pc:22.8,rl:"Moderate"}],"Tulare":[{ac:29.7,pc:24.5,rl:"Moderate"},{ac:44.5,pc:60.0,rl:"High"},{ac:51.9,pc:94.6,rl:"Very High"},{ac:55.6,pc:40.4,rl:"High"},{ac:48.2,pc:51.8,rl:"High"},{ac:33.4,pc:28.3,rl:"Moderate"},{ac:null,pc:74.4,rl:"High"},{ac:null,pc:34.7,rl:"High"},{ac:null,pc:75.1,rl:"High"},{ac:null,pc:58.2,rl:"High"},{ac:null,pc:42.8,rl:"High"},{ac:null,pc:68.5,rl:"High"}]};

const ENV={Fresno:{temp:18.2,wind:12.4,pm10:28.3,precip:0,soil:0.12,humid:42},Kern:{temp:21.5,wind:18.7,pm10:45.1,precip:0,soil:0.08,humid:35},Kings:{temp:19.1,wind:14.2,pm10:32.6,precip:0.2,soil:0.11,humid:40},Madera:{temp:17.8,wind:10.1,pm10:22.4,precip:0,soil:0.14,humid:45},Merced:{temp:16.9,wind:11.8,pm10:25.7,precip:0,soil:0.13,humid:44},"San Joaquin":{temp:15.4,wind:9.6,pm10:19.2,precip:0.5,soil:0.16,humid:48},Stanislaus:{temp:16.1,wind:10.3,pm10:21.8,precip:0.3,soil:0.15,humid:46},Tulare:{temp:20.3,wind:16.5,pm10:38.9,precip:0,soil:0.09,humid:37}};
const ENVLY={Fresno:{temp:16.8,pm10:22.1,soil:0.18,wind:10.2},Kern:{temp:19.2,pm10:38.6,soil:0.11,wind:15.4},Kings:{temp:17.5,pm10:28.4,soil:0.15,wind:12.8},Madera:{temp:15.9,pm10:18.2,soil:0.19,wind:8.8},Merced:{temp:15.1,pm10:20.8,soil:0.17,wind:10.4},"San Joaquin":{temp:13.8,pm10:16.5,soil:0.21,wind:8.2},Stanislaus:{temp:14.5,pm10:18.4,soil:0.19,wind:9.1},Tulare:{temp:18.6,pm10:32.4,soil:0.13,wind:14.2}};

const SUMM={Fresno:"Dry soil and low rainfall have left ground cracked. Late-winter pattern, warming temps could spike earlier.",Kern:"Seasonal dip — cooler temps suppress spores. PM10 elevated at 45 µg/m³ from ag operations.",Kings:"Wind and soil moisture near average. Ag activity disturbs topsoil. Watch for summer escalation.",Madera:"Higher soil moisture than south. Model forecasts increase as dry season nears.",Merced:"Favorable — moderate winds, decent soil moisture, lower PM10. Seasonal increase expected.","San Joaquin":"Northernmost — typically lower counts. Wind and dust manageable.",Stanislaus:"Lowest predicted cases among inland counties. Cool temps + moisture provide suppression.",Tulare:"Highest risk. Hot dry + ag activity = ideal spore dispersal. PM10 at 39 µg/m³."};

/* ═══════════════════════════════════════════════════════════════════════════ */
const RC={Low:"#22c55e",Moderate:"#eab308",High:"#ef4444","Very High":"#7f1d1d"};
const r2=n=>Math.round(n*100)/100;

function getBD(e){
  const sN=Math.min(e.soil/0.3,1),tN=Math.min(e.temp/45,1),pN=Math.min(e.precip/50,1),dN=Math.min(e.pm10/80,1),wN=Math.min(e.wind/30,1);
  const Gp=1.9*sN+1.9*tN+1.6*pN,Er=1.6*dN+0.5*wN+1.3*(1-sN)+1.9*tN;
  return{Gp:r2(Gp),Er:r2(Er),risk:r2(Gp*Er),vars:[
    {nm:"Soil Moisture",raw:`${(e.soil*100).toFixed(1)}%`,gp:r2(1.9*sN),er:r2(1.3*(1-sN)),wg:1.9,we:1.3},
    {nm:"Temperature",raw:`${e.temp}°C`,gp:r2(1.9*tN),er:r2(1.9*tN),wg:1.9,we:1.9},
    {nm:"Precipitation",raw:`${e.precip} mm`,gp:r2(1.6*pN),er:null,wg:1.6,we:null},
    {nm:"PM10 (Dust)",raw:`${e.pm10} µg/m³`,gp:null,er:r2(1.6*dN),wg:null,we:1.6},
    {nm:"Wind Speed",raw:`${e.wind} km/h`,gp:null,er:r2(0.5*wN),wg:null,we:0.5}]};
}
function mkIns(e,ly){
  const ins=[];
  const sd=((e.soil-ly.soil)/ly.soil*100).toFixed(0),pd=((e.pm10-ly.pm10)/ly.pm10*100).toFixed(0),td=(e.temp-ly.temp).toFixed(1);
  ins.push(+sd<0?{i:"💧",t:`Soil moisture ${Math.abs(sd)}% lower YoY — drier = more exposed spores.`,s:"w"}:{i:"💧",t:`Soil moisture ${sd}% higher YoY — suppresses spore release.`,s:"g"});
  ins.push(+pd>0?{i:"🌫️",t:`PM10 up ${pd}% YoY (${ly.pm10}→${e.pm10} µg/m³). Higher inhalation risk.`,s:"w"}:{i:"🌫️",t:`PM10 down ${Math.abs(pd)}% YoY — improved air quality.`,s:"g"});
  ins.push(+td>0?{i:"🌡️",t:`${td}°C warmer YoY. Warm+dry accelerates Coccidioides lifecycle.`,s:"w"}:{i:"🌡️",t:`${Math.abs(td)}°C cooler YoY — slows fungal growth.`,s:"g"});
  if(e.wind>15)ins.push({i:"💨",t:`Wind ${e.wind} km/h exceeds 15 km/h dispersal threshold.`,s:"w"});
  if(e.precip===0)ins.push({i:"☀️",t:`Zero precipitation — soil cracking exposes fungal colonies.`,s:"w"});
  return ins;
}

/* ═══════════════════════════════════════════════════════════════════════════
   ZOOM VIEWBOX (full map vs zoomed to county)
   ═══════════════════════════════════════════════════════════════════════════ */
const FULL_VB = "-10 0 330 610";

function getZoomedVB(countyName) {
  const g = CP[countyName];
  if (!g) return FULL_VB;
  // Center on county with some padding
  const zoomW = 160, zoomH = 200;
  const x = g.cx - zoomW / 2;
  const y = g.cy - zoomH / 2;
  return `${x} ${y} ${zoomW} ${zoomH}`;
}

/* ═══════════════════════════════════════════════════════════════════════════
   APP
   ═══════════════════════════════════════════════════════════════════════════ */
export default function App(){
  const [mi,setMi]=useState(0);
  const [sel,setSel]=useState(null);
  const [sh,setSh]=useState(0);
  const [zoomed,setZoomed]=useState(false);
  const [viewBox,setViewBox]=useState(FULL_VB);
  // Pan state
  const [pan,setPan]=useState({x:0,y:0});
  const [dragging,setDragging]=useState(false);
  const dragStart=useRef(null);
  const panStart=useRef(null);
  const [co,setCo]=useState(false);
  const [ms,setMs]=useState([{r:"b",t:"SOS — SporeRisk Emergency. Ask about symptoms, prevention, clinics, or risk."}]);
  const [ci,setCi]=useState("");
  const [cb,setCb]=useState(false);
  const ce=useRef(null);
  const animRef=useRef(null);

  // API state
  const [apiCounties,setApiCounties]=useState(null); // from /counties
  const [apiDetail,setApiDetail]=useState(null); // from /risk/{county}
  const [apiHistory,setApiHistory]=useState(null); // from /history/{county}
  const [apiSummary,setApiSummary]=useState(null); // from /summary/{county}
  const [apiConnected,setApiConnected]=useState(false);

  // Fetch counties from API on mount
  useEffect(()=>{
    (async()=>{
      const data=await apiFetch("/counties");
      if(data?.counties){
        setApiConnected(true);
        const byCounty={};
        data.counties.forEach(c=>{byCounty[c.county]=c;});
        setApiCounties(byCounty);
      }
    })();
  },[]);

  // Fetch detail when county selected
  useEffect(()=>{
    if(!sel)return;
    (async()=>{
      const [riskData,histData,summData]=await Promise.all([
        apiFetch(`/risk/${encodeURIComponent(sel)}`),
        apiFetch(`/history/${encodeURIComponent(sel)}`),
        apiFetch(`/summary/${encodeURIComponent(sel)}`),
      ]);
      if(riskData)setApiDetail(riskData);
      if(histData)setApiHistory(histData);
      if(summData)setApiSummary(summData);
    })();
  },[sel]);

  const isPred=mi>=6;
  const monthLabel=MONTHS[mi];

  // Risk for map display: API data if available, else mock
  const risk=c=>{
    // If API returned county data, use latest risk from API
    if(apiCounties?.[c]){
      const ac=apiCounties[c];
      return {ac:ac.monthly_cases||0,pc:ac.predicted_cases||0,rl:ac.risk_level||"Unknown"};
    }
    // Fallback to mock per-month data
    return MD[c]?.[mi]||{ac:null,pc:0,rl:"Unknown"};
  };

  // Animate viewBox transition
  const animateVB = useCallback((from, to, duration=600) => {
    const fromParts = from.split(" ").map(Number);
    const toParts = to.split(" ").map(Number);
    const start = performance.now();
    
    const step = (now) => {
      const t = Math.min((now - start) / duration, 1);
      // Ease out cubic
      const ease = 1 - Math.pow(1 - t, 3);
      const current = fromParts.map((f, i) => f + (toParts[i] - f) * ease);
      setViewBox(current.map(v => v.toFixed(1)).join(" "));
      if (t < 1) animRef.current = requestAnimationFrame(step);
    };
    if (animRef.current) cancelAnimationFrame(animRef.current);
    animRef.current = requestAnimationFrame(step);
  }, []);

  const tap = (c) => {
    if (sel === c) {
      // Deselect — zoom out
      setSel(null);
      setSh(0);
      setZoomed(false);
      animateVB(viewBox, FULL_VB, 500);
    } else {
      // Select — zoom in
      const prevVB = sel ? viewBox : FULL_VB;
      setSel(c);
      setSh(1);
      setZoomed(true);
      animateVB(prevVB, getZoomedVB(c), 600);
    }
  };

  const closeSheet = () => {
    setSh(0);
    setSel(null);
    setZoomed(false);
    setPan({x:0,y:0});
    animateVB(viewBox, FULL_VB, 500);
  };

  useEffect(() => () => { if(animRef.current) cancelAnimationFrame(animRef.current); }, []);

  // Chat — tries API first, falls back to mock
  const send=async()=>{
    if(!ci.trim()||cb)return;const m=ci.trim();setCi("");setMs(p=>[...p,{r:"u",t:m}]);setCb(true);

    // Try real API
    if(apiConnected){
      try{
        const body={message:m};
        if(sel)body.county=sel;
        const res=await fetch(`${API}/chat`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
        const data=await res.json();
        if(data.reply){setMs(p=>[...p,{r:"b",t:data.reply}]);setCb(false);return;}
      }catch{}
    }

    // Mock fallback
    await new Promise(r=>setTimeout(r,500));const lo=m.toLowerCase();
    let rp="Ask about Valley Fever symptoms, prevention, clinics, or risk.";
    if(lo.includes("symptom"))rp="Symptoms: persistent cough, fever/chills, fatigue, chest pain, rash. See doctor if >1-2 weeks.";
    else if(lo.includes("prevent")||lo.includes("mask"))rp="N95 masks in dusty conditions. Avoid disturbed soil. Close windows in dust storms. HEPA filters indoors.";
    else if(lo.includes("clinic")||lo.includes("hospital"))rp="Community Medical Centers (Fresno), Kern Medical (Bakersfield), Mercy Medical (Merced), Kaiser, county health depts.";
    else if(lo.includes("medic"))rp="Fluconazole/itraconazole (prescription). Mild cases self-resolve. Consult healthcare provider.";
    else if(sel&&lo.includes("risk")){const r=risk(sel);rp=`${sel} in ${monthLabel}: ${r.rl} risk, ~${r.pc} pred. cases. ${SUMM[sel]}`;}
    setMs(p=>[...p,{r:"b",t:rp}]);setCb(false);
  };
  useEffect(()=>{ce.current?.scrollIntoView({behavior:"smooth"});},[ms]);

  // Environment: API data first, mock fallback
  const env = sel ? (apiDetail?.environment?.source !== "unavailable" ? {
    temp: apiDetail?.environment?.temperature_c,
    wind: apiDetail?.environment?.wind_speed_kmh,
    pm10: apiDetail?.environment?.pm10_ugm3,
    precip: apiDetail?.environment?.precipitation_mm,
    soil: (apiDetail?.environment?.pm10_ugm3 || 30) / 250, // approximate soil from pm10 if not available
    humid: 40,
  } : null) || ENV[sel] : null;
  const ely=sel?ENVLY[sel]:null;
  const bd=env?getBD(env):null;
  const ins=env&&ely?mkIns(env,ely):[];

  // Summary: API first, mock fallback
  const summary = sel ? (
    apiSummary?.summary_bullets?.length > 0
      ? apiSummary.summary_bullets.join(" ")
      : apiDetail?.summary?.length > 0
        ? apiDetail.summary.join(" ")
        : SUMM[sel]
  ) : "";

  // Chart: build from API history if available, else mock
  const chart = sel ? (() => {
    if (apiHistory?.records || apiHistory?.history) {
      const records = apiHistory.records || apiHistory.history || [];
      return records.map(h => ({
        d: `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][h.month-1]} ${h.year}`,
        actual: h.monthly_cases > 0 ? h.monthly_cases : undefined,
        predicted: h.predicted_cases,
      }));
    }
    // Mock fallback
    return MKEYS.map((k,i)=>{const d=MD[sel]?.[i];return{d:MONTHS[i],actual:d?.ac!==null?d.ac:undefined,predicted:d?.pc};});
  })() : [];

  // Find cutoff in chart data (last month with actual data)
  const lastActualIdx = chart.reduce((last, c, i) => c.actual !== undefined ? i : last, -1);
  const cutDate = lastActualIdx >= 0 ? chart[lastActualIdx]?.d : "Dec 2025";

  // Decomp
  const decomp=MKEYS.map((k,i)=>{const m=parseInt(k.split("-")[1]);const ph=((m-1)/12)*Math.PI*2;const s=(Math.sin(ph-Math.PI/2)+1)/2;return{d:MONTHS[i],gp:r2(0.3+s*0.9),er:r2(0.4+s*1.2)};});

  // Slider snap to nearest month
  const handleSlider = (e) => {
    const raw = +e.target.value;
    setMi(Math.round(raw / (100/11)));
  };
  const sliderVal = mi * (100/11);

  return(
    <div style={S.app}>
      <header style={S.hdr}>
        <div style={{display:"flex",alignItems:"center",gap:6}}>
          <span style={{fontSize:18}}>🍄</span><span style={S.logo}>SporeRisk</span>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:4}}>
          <div style={S.tag}>
            {isPred?`🔮 ${monthLabel}`:`📊 ${monthLabel}`}
          </div>
          <div style={{width:6,height:6,borderRadius:3,background:apiConnected?"#22c55e":"#f59e0b"}} title={apiConnected?"API connected":"Using mock data"}/>
        </div>
      </header>

      {/* MAP */}
      <div style={{...S.mapW,filter:sh===2?"blur(3px) brightness(0.7)":"none"}}
        onMouseDown={e=>{setDragging(true);dragStart.current={x:e.clientX,y:e.clientY};panStart.current={...pan};}}
        onMouseMove={e=>{if(!dragging||!dragStart.current)return;const dx=(e.clientX-dragStart.current.x)*0.8;const dy=(e.clientY-dragStart.current.y)*0.8;setPan({x:panStart.current.x+dx,y:panStart.current.y+dy});}}
        onMouseUp={()=>setDragging(false)}
        onMouseLeave={()=>setDragging(false)}
        onTouchStart={e=>{const t=e.touches[0];setDragging(true);dragStart.current={x:t.clientX,y:t.clientY};panStart.current={...pan};}}
        onTouchMove={e=>{if(!dragging||!dragStart.current)return;const t=e.touches[0];const dx=(t.clientX-dragStart.current.x)*0.8;const dy=(t.clientY-dragStart.current.y)*0.8;setPan({x:panStart.current.x+dx,y:panStart.current.y+dy});}}
        onTouchEnd={()=>setDragging(false)}
      >
        <svg viewBox={viewBox} style={{...S.svg,transition:"none",transform:`translate(${pan.x}px,${pan.y}px)`,cursor:dragging?"grabbing":"grab"}} preserveAspectRatio="xMidYMid meet">
          <defs>
            <filter id="gl"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
            <pattern id="pstripes" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="5" stroke="#a78bfa" strokeWidth="0.7" opacity="0.2"/>
            </pattern>
          </defs>

          <rect x="-20" y="-10" width="360" height="640" fill="#eef2ee" onClick={()=>{if(sel){closeSheet();}}}/>

          {/* Neighbors */}
          {Object.entries(NP).map(([n,d])=>(
            <path key={n} d={d} fill="#d4dfd4" stroke="#b8c8b8" strokeWidth="0.5" opacity="0.5" onClick={()=>{if(sel){closeSheet();}}}/>
          ))}

          {/* Counties */}
          {Object.entries(CP).map(([name,g])=>{
            const r=risk(name);const c=RC[r.rl]||"#6b7280";const isSel=sel===name;
            const fo=0.35;

            return(
              <g key={name} onClick={()=>tap(name)} style={{cursor:"pointer"}}>
                {isSel&&<path d={g.d} fill="none" stroke={c} strokeWidth={zoomed?2:6} opacity="0.3" filter="url(#gl)">
                  <animate attributeName="opacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite"/>
                </path>}
                <path d={g.d} fill={c}
                  fillOpacity={isSel?0.55:fo} stroke={isSel?"#fff":c}
                  strokeWidth={isSel?(zoomed?1.5:2.5):1} style={{transition:"fill-opacity 0.3s"}}/>

                <text x={g.cx} y={g.cy-(zoomed?4:7)} textAnchor="middle" fontSize={zoomed?4.5:8.5} fontWeight="800"
                  fill="#1e293b" fontFamily="system-ui" style={{pointerEvents:"none"}}>{name}</text>
                <text x={g.cx} y={g.cy+(zoomed?2:4)} textAnchor="middle" fontSize={zoomed?3.5:7.5} fontWeight="700"
                  fill={c} fontFamily="system-ui" style={{pointerEvents:"none"}}>{r.rl}</text>
                <text x={g.cx} y={g.cy+(zoomed?7:14)} textAnchor="middle" fontSize={zoomed?3:6.5}
                  fill="#78716c" fontFamily="system-ui" style={{pointerEvents:"none"}}>
                  {r.ac!==null?`${r.ac} cases`:`~${r.pc} pred`}
                </text>
              </g>
            );
          })}

          {/* Legend (only when not zoomed) */}
          {!zoomed&&<>
            <rect x={5} y={555} width={90} height={52} rx={4} fill="#ffffffaa" stroke="#d1d5db88" strokeWidth="0.5"/>
            {["Low","Moderate","High","Very High"].map((l,i)=>(
              <g key={l}><rect x={10} y={559+i*11} width={7} height={7} rx={1.5} fill={RC[l]}/>
              <text x={21} y={565.5+i*11} fontSize="6.5" fill="#475569" fontFamily="system-ui" fontWeight="500">{l}</text></g>
            ))}
          </>}
        </svg>

        {/* SLIDER — v4 style, continuous look, monthly snapping */}
        <div style={S.slB}>
          <div style={S.slR}>
            <span style={{fontSize:10,fontWeight:mi<6?700:400,color:mi<6?"#1d4ed8":"#94a3b8"}}>📊 Historical</span>
            <span style={{fontSize:9,color:"#64748b",fontWeight:600}}>
              {monthLabel}
            </span>
            <span style={{fontSize:10,fontWeight:mi>=6?700:400,color:mi>=6?"#8b5cf6":"#94a3b8"}}>🔮 Predicted</span>
          </div>
          <input type="range" min="0" max="100" value={sliderVal}
            onChange={handleSlider}
            style={{...S.rng,accentColor:"#6366f1"}}/>
          {/* Month dots */}
          <div style={{display:"flex",justifyContent:"space-between",padding:"2px 1px 0",marginTop:1}}>
            {MONTHS.map((m,i)=>(
              <div key={i} onClick={()=>setMi(i)} style={{cursor:"pointer",display:"flex",flexDirection:"column",alignItems:"center"}}>
                <div style={{width:i===mi?6:3,height:i===mi?6:3,borderRadius:"50%",
                  background:i===mi?"#6366f1":"#cbd5e1",
                  transition:"all 0.2s"}}/>
                {(i%2===0||i===mi)&&<span style={{fontSize:5.5,color:i===mi?"#6366f1":"#94a3b8",marginTop:1,whiteSpace:"nowrap"}}>{m.slice(0,3)}</span>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* BOTTOM SHEET */}
      {sel&&sh>0&&(
        <div style={{...S.sht,height:sh===1?"44vh":"92vh"}}>
          <div style={S.hdl} onClick={()=>{if(sh===1)setSh(2);else closeSheet();}}>
            <div style={S.hb}/><span style={{fontSize:8,color:"#94a3b8",marginTop:2}}>{sh===1?"↑ Full insight":"↓ Close"}</span>
          </div>
          <div style={S.sb}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
              <div>
                <h2 style={{margin:0,fontSize:18,fontWeight:800}}>{sel}, CA</h2>
                <span style={{fontSize:10,color:"#64748b"}}>{monthLabel} · {META[sel]?.lat}°N</span>
              </div>
              <span style={{padding:"4px 10px",borderRadius:12,fontWeight:800,fontSize:12,
                background:risk(sel).rl==="Very High"?"#450a0a":RC[risk(sel).rl]+"22",
                color:risk(sel).rl==="Very High"?"#fca5a5":RC[risk(sel).rl]}}>
                {risk(sel).rl}
              </span>
            </div>

            <div style={{display:"flex",gap:8,marginTop:8}}>
              {risk(sel).ac!==null&&(
                <div style={{flex:1,background:"#eff6ff",borderRadius:8,padding:"8px 10px",border:"1px solid #bfdbfe"}}>
                  <div style={{fontSize:8,color:"#3b82f6",fontWeight:700,textTransform:"uppercase"}}>Recorded</div>
                  <div style={{fontSize:20,fontWeight:800,color:"#1e40af"}}>{risk(sel).ac}</div>
                  <div style={{fontSize:8,color:"#64748b"}}>cases</div>
                </div>
              )}
              <div style={{flex:1,background:"#f5f3ff",borderRadius:8,padding:"8px 10px",border:"1px solid #c4b5fd"}}>
                <div style={{fontSize:8,color:"#7c3aed",fontWeight:700,textTransform:"uppercase"}}>{isPred?"Predicted":"Model Est."}</div>
                <div style={{fontSize:20,fontWeight:800,color:"#5b21b6"}}>{risk(sel).pc}</div>
                <div style={{fontSize:8,color:"#64748b"}}>cases/mo</div>
              </div>
            </div>

            <div style={S.ai}>
              <div style={{display:"flex",gap:4,alignItems:"center",marginBottom:3}}>
                <span>✨</span><span style={{fontSize:9,fontWeight:700,color:"#7c3aed",textTransform:"uppercase",letterSpacing:0.5}}>AI Analysis</span>
              </div>
              <p style={{margin:0,fontSize:12,lineHeight:1.5,color:"#334155"}}>{summary}</p>
            </div>

            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:5,marginTop:8}}>
              <MS l="PM10 Dust" v={`${env?.pm10} µg/m³`} w={env?.pm10>35}/>
              <MS l="Soil Moisture" v={`${(env?.soil*100).toFixed(0)}%`} w={env?.soil<0.12}/>
              <MS l="Wind" v={`${env?.wind} km/h`} w={env?.wind>15}/>
              <MS l="Temperature" v={`${env?.temp}°C`} w={env?.temp>30}/>
            </div>

            {sh===2&&(<>
              {/* ──── SECTION: Cases Chart ──── */}
              <div style={V.sec}>
                <div style={V.secLabel}>Real Data</div>
                <h3 style={V.secH}>{sel} — Recorded vs Predicted Cases</h3>
                <p style={V.secSub}>Solid line shows CDPH-verified reported cases. Dashed line shows model prediction. Red divider marks where recorded data ends and forecast begins.</p>
                <div style={V.chartCard}>
                  <ResponsiveContainer width="100%" height={200}>
                    <ComposedChart data={chart}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e0d8"/>
                      <XAxis dataKey="d" tick={{fontSize:7,fill:"#78716c"}} interval={1} angle={-30} textAnchor="end" height={40}/>
                      <YAxis tick={{fontSize:9,fill:"#78716c"}}/>
                      <Tooltip contentStyle={{fontSize:11,borderRadius:4,border:"1px solid #e2e8f0",boxShadow:"none"}}
                        formatter={(v,n)=>[v!==undefined?v?.toFixed?.(1):"—",n==="Recorded"?"Recorded Cases":"Model Predicted"]}/>
                      <Legend wrapperStyle={{fontSize:9,paddingTop:8}}/>
                      <ReferenceLine x={cutDate} stroke="#ef4444" strokeWidth={2} strokeDasharray="8 4"
                        label={{value:"← Recorded | Forecast →",position:"top",fontSize:7,fill:"#ef4444",fontWeight:700}}/>
                      <Area type="monotone" dataKey="actual" fill="#3b82f620" stroke="#3b82f6" strokeWidth={2.5} name="Recorded" dot={false} isAnimationActive={false}/>
                      <Line type="monotone" dataKey="predicted" stroke="#8b5cf6" strokeWidth={1.5} strokeDasharray="6 3" dot={false} name="Predicted"/>
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* ──── SECTION: G_pot vs E_risk ──── */}
              <div style={V.sec}>
                <div style={V.secLabel}>Algorithm</div>
                <h3 style={V.secH}>Growth Potential vs Exposure Risk</h3>
                <p style={V.secSub}>Stacked decomposition of the two biological phases. Growth phase (G_pot) captures antecedent soil conditions. Exposure phase (E_risk) captures current dispersal conditions.</p>
                <div style={V.chartCard}>
                  <ResponsiveContainer width="100%" height={160}>
                    <AreaChart data={decomp}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e0d8"/>
                      <XAxis dataKey="d" tick={{fontSize:7,fill:"#78716c"}} interval={2}/>
                      <YAxis tick={{fontSize:9,fill:"#78716c"}}/>
                      <Tooltip contentStyle={{fontSize:11,borderRadius:4,border:"1px solid #d6d3cd",boxShadow:"none",background:"#fafaf8"}}/>
                      <Legend wrapperStyle={{fontSize:9,paddingTop:4}}/>
                      <Area type="monotone" dataKey="gp" stackId="1" fill="#92785433" stroke="#927854" strokeWidth={1.5} name="G_pot (Growth)"/>
                      <Area type="monotone" dataKey="er" stackId="1" fill="#6d5c3f33" stroke="#6d5c3f" strokeWidth={1.5} name="E_risk (Exposure)"/>
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* ──── SECTION: Risk Index Breakdown ──── */}
              <div style={V.sec}>
                <div style={V.secLabel}>Algorithm</div>
                <h3 style={V.secH}>Two-Phase Risk Index</h3>
                <p style={V.secSub}>Risk = G_pot × E_risk. Growth without dispersal = zero cases. Dispersal without growth = nothing to disperse. Both must align.</p>

                {/* Equation display */}
                <div style={V.eqCard}>
                  <div style={{display:"flex",alignItems:"center",justifyContent:"center",gap:8,flexWrap:"wrap"}}>
                    <div style={V.eqBox}>
                      <div style={{fontSize:9,color:"#927854",fontWeight:600,letterSpacing:0.5}}>G_POT</div>
                      <div style={{fontSize:22,fontWeight:800,color:"#44403c",fontFamily:"'Georgia',serif"}}>{bd?.Gp}</div>
                      <div style={{fontSize:8,color:"#a8a29e"}}>Growth</div>
                    </div>
                    <span style={{fontSize:16,color:"#d6d3cd",fontWeight:300}}>×</span>
                    <div style={V.eqBox}>
                      <div style={{fontSize:9,color:"#78716c",fontWeight:600,letterSpacing:0.5}}>E_RISK</div>
                      <div style={{fontSize:22,fontWeight:800,color:"#44403c",fontFamily:"'Georgia',serif"}}>{bd?.Er}</div>
                      <div style={{fontSize:8,color:"#a8a29e"}}>Exposure</div>
                    </div>
                    <span style={{fontSize:16,color:"#d6d3cd",fontWeight:300}}>=</span>
                    <div style={{...V.eqBox,background:"#44403c",borderColor:"#44403c"}}>
                      <div style={{fontSize:9,color:"#a8a29e",fontWeight:600,letterSpacing:0.5}}>RISK</div>
                      <div style={{fontSize:22,fontWeight:800,color:"#fafaf8",fontFamily:"'Georgia',serif"}}>{bd?.risk}</div>
                      <div style={{fontSize:8,color:"#a8a29e"}}>Score</div>
                    </div>
                  </div>
                </div>

                {/* Variable table */}
                <div style={V.table}>
                  <div style={V.tHead}>
                    <span style={{flex:2}}>Variable</span>
                    <span style={{flex:1,textAlign:"right"}}>Value</span>
                    <span style={{flex:1,textAlign:"right"}}>G_pot</span>
                    <span style={{flex:1,textAlign:"right"}}>E_risk</span>
                  </div>
                  {bd?.vars.map((v,i)=>(
                    <div key={i} style={{...V.tRow,background:i%2===0?"#fafaf8":"transparent"}}>
                      <span style={{flex:2,fontSize:10.5,fontWeight:600,color:"#44403c"}}>{v.nm}</span>
                      <span style={{flex:1,textAlign:"right",fontSize:10,color:"#78716c"}}>{v.raw}</span>
                      <span style={{flex:1,textAlign:"right",fontSize:10,fontWeight:700,color:v.gp!==null?"#927854":"#d6d3cd"}}>{v.gp!==null?v.gp:"—"}</span>
                      <span style={{flex:1,textAlign:"right",fontSize:10,fontWeight:700,color:v.er!==null?"#78716c":"#d6d3cd"}}>{v.er!==null?v.er:"—"}</span>
                    </div>
                  ))}
                </div>
                <p style={{fontSize:9,color:"#a8a29e",margin:"6px 0 0",lineHeight:1.4}}>
                  Weights derived from Multivariable Negative Binomial Regression (MNBR) adjusted IRRs. Validated against Random Forest feature importances (sm_lag6 = 22.3% #1).
                </p>
              </div>

              {/* ──── SECTION: Year-over-Year Insights ──── */}
              <div style={V.sec}>
                <div style={V.secLabel}>Validation</div>
                <h3 style={V.secH}>Year-over-Year Change</h3>
                <p style={V.secSub}>Comparing current environmental conditions to the same period last year. Changes inform whether risk is trending up or down relative to historical baseline.</p>
                {ins.map((n,i)=>(
                  <div key={i} style={V.insCard}>
                    <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:4}}>
                      <span style={{fontSize:14}}>{n.i}</span>
                      <div style={{width:6,height:6,borderRadius:3,background:n.s==="w"?"#d97706":"#16a34a"}}/>
                      <span style={{fontSize:9,fontWeight:700,color:n.s==="w"?"#d97706":"#16a34a",textTransform:"uppercase",letterSpacing:0.5}}>
                        {n.s==="w"?"Risk Factor":"Protective"}
                      </span>
                    </div>
                    <p style={{margin:0,fontSize:11.5,lineHeight:1.5,color:"#44403c"}}>{n.t}</p>
                  </div>
                ))}
              </div>

              {/* ──── SECTION: Environment ──── */}
              <div style={V.sec}>
                <div style={V.secLabel}>Data Pipeline</div>
                <h3 style={V.secH}>Current Environmental Conditions</h3>
                <p style={V.secSub}>Live data from Open-Meteo (weather), EPA AQS (air quality), and derived soil metrics for {sel} County.</p>
                <div style={V.table}>
                  <div style={V.tHead}>
                    <span style={{flex:1}}></span>
                    <span style={{flex:2}}>Metric</span>
                    <span style={{flex:1.5,textAlign:"right"}}>Value</span>
                    <span style={{flex:1.5,textAlign:"right"}}>Role</span>
                  </div>
                  {[
                    ["🌡️","Temperature",`${env?.temp}°C`,"Both phases"],
                    ["💨","Wind Speed",`${env?.wind} km/h`,"E_risk"],
                    ["🌫️","PM10 (Dust)",`${env?.pm10} µg/m³`,"E_risk"],
                    ["🌧️","Precipitation",`${env?.precip} mm`,"G_pot"],
                    ["💧","Soil Moisture",`${(env?.soil*100).toFixed(1)}%`,"Both phases"],
                    ["💦","Humidity",`${env?.humid}%`,"Context"],
                  ].map(([ic,lb,vl,role],i)=>(
                    <div key={i} style={{...V.tRow,background:i%2===0?"#fafaf8":"transparent"}}>
                      <span style={{flex:1,fontSize:13}}>{ic}</span>
                      <span style={{flex:2,fontSize:10.5,fontWeight:600,color:"#44403c"}}>{lb}</span>
                      <span style={{flex:1.5,textAlign:"right",fontSize:11,fontWeight:700,color:"#44403c",fontFamily:"'Georgia',serif"}}>{vl}</span>
                      <span style={{flex:1.5,textAlign:"right",fontSize:9,color:"#a8a29e"}}>{role}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>)}
          </div>
          <div style={S.sa}>
            <button style={{...S.ab,background:sh===1?"#1a3324":"#64748b"}} onClick={()=>{if(sh===1)setSh(2);else closeSheet();}}>
              {sh===1?"View Full Insight ↑":"Close ↓"}
            </button>
          </div>
        </div>
      )}

      {!co&&<button style={S.sos} onClick={()=>setCo(true)}><span style={{fontSize:11,fontWeight:900,letterSpacing:1}}>SOS</span></button>}

      {co&&(
        <div style={S.chW}>
          <div style={S.chH}><span style={{fontWeight:700,fontSize:13}}>🍄 SporeRisk SOS</span><button style={S.chX} onClick={()=>setCo(false)}>✕</button></div>
          <div style={S.chS}>
            {ms.map((m,i)=><div key={i} style={m.r==="u"?S.uR:S.bR}><div style={m.r==="u"?S.uB:S.bB}>{m.t}</div></div>)}
            {cb&&<div style={S.bR}><div style={S.bB}>Thinking...</div></div>}
            <div ref={ce}/>
          </div>
          <div style={S.chB}>
            <input style={S.chI} placeholder="Ask about Valley Fever..." value={ci} onChange={e=>setCi(e.target.value)} onKeyDown={e=>e.key==="Enter"&&send()}/>
            <button style={S.chSe} onClick={send} disabled={cb}>➤</button>
          </div>
        </div>
      )}
    </div>
  );
}

/* Sub-components */
function MS({l,v,w}){return(
  <div style={{background:"#f8fafc",borderRadius:7,padding:"6px 8px",border:"1px solid #e2e8f0"}}>
    <div style={{fontSize:8,color:"#64748b",textTransform:"uppercase",letterSpacing:0.3,fontWeight:600}}>{l}</div>
    <div style={{fontSize:13,fontWeight:800,color:"#0f172a",marginTop:1}}>{v}</div>
    <div style={{fontSize:8,fontWeight:600,color:w?"#ef4444":"#22c55e"}}>{w?"⚠ Elevated":"✓ Normal"}</div>
  </div>
);}
function SC({l,v,s,c,bg}){return(
  <div style={{flex:1,textAlign:"center",padding:"6px 3px",borderRadius:7,border:`2px solid ${c}`,background:bg||"#fff"}}>
    <div style={{fontSize:8,fontWeight:700,color:bg?"#94a3b8":c}}>{l}</div>
    <div style={{fontSize:15,fontWeight:800,color:bg?"#fff":"#0f172a"}}>{v}</div>
    <div style={{fontSize:7,color:bg?"#94a3b8":"#64748b"}}>{s}</div>
  </div>
);}
function BR({l,v,c,w}){const pct=Math.min(v/2*100,100);return(
  <div style={{display:"flex",alignItems:"center",gap:3,marginBottom:1}}>
    <span style={{fontSize:7,color:c,width:28,fontWeight:600}}>{l}</span>
    <div style={{flex:1,height:4,borderRadius:2,background:"#f1f5f9",overflow:"hidden"}}>
      <div style={{height:"100%",width:`${pct}%`,borderRadius:2,background:c,transition:"width 0.5s"}}/>
    </div>
    <span style={{fontSize:7,color:"#64748b",width:18}}>{v}</span>
    <span style={{fontSize:6,color:"#94a3b8",width:16}}>w:{w}</span>
  </div>
);}

/* Editorial styles matching sporisk.vercel.app */
const V={
  sec:{marginTop:16,paddingTop:14,borderTop:"1px solid #e7e5e4"},
  secLabel:{fontSize:9,fontWeight:700,color:"#a8a29e",textTransform:"uppercase",letterSpacing:1.2,marginBottom:4},
  secH:{fontSize:15,fontWeight:700,color:"#292524",margin:"0 0 4px",fontFamily:"'Georgia','Times New Roman',serif",letterSpacing:-0.3},
  secSub:{fontSize:10.5,color:"#78716c",lineHeight:1.5,margin:"0 0 10px"},
  chartCard:{background:"#fafaf8",border:"1px solid #e7e5e4",borderRadius:6,padding:"10px 6px 4px"},
  eqCard:{background:"#fafaf8",border:"1px solid #e7e5e4",borderRadius:6,padding:"14px 10px",marginBottom:12},
  eqBox:{textAlign:"center",padding:"8px 12px",borderRadius:6,border:"1.5px solid #d6d3cd",background:"#fff",minWidth:60},
  table:{border:"1px solid #e7e5e4",borderRadius:6,overflow:"hidden",marginBottom:8},
  tHead:{display:"flex",padding:"6px 10px",background:"#f5f5f0",borderBottom:"1px solid #e7e5e4",fontSize:9,fontWeight:700,color:"#a8a29e",textTransform:"uppercase",letterSpacing:0.5},
  tRow:{display:"flex",padding:"7px 10px",borderBottom:"1px solid #f5f5f0",alignItems:"center"},
  insCard:{background:"#fafaf8",border:"1px solid #e7e5e4",borderRadius:6,padding:"10px 12px",marginBottom:6},
};

const S={
  app:{fontFamily:"'SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif",maxWidth:430,margin:"0 auto",background:"#f5f5f0",minHeight:"100vh",position:"relative",overflow:"hidden"},
  hdr:{padding:"10px 14px",display:"flex",justifyContent:"space-between",alignItems:"center",position:"sticky",top:0,zIndex:100,background:"linear-gradient(135deg,#1a3324,#0f2218)"},
  logo:{fontSize:16,fontWeight:800,color:"#fff",letterSpacing:-0.3},
  tag:{fontSize:8,fontWeight:700,padding:"3px 8px",borderRadius:8,background:"rgba(127,184,149,0.15)",color:"#7fb895"},
  mapW:{position:"relative",transition:"filter 0.3s"},
  svg:{width:"100%",display:"block"},
  slB:{position:"absolute",bottom:10,left:8,right:8,backdropFilter:"blur(10px)",borderRadius:12,padding:"8px 12px 4px",boxShadow:"0 2px 16px rgba(0,0,0,0.08)",background:"rgba(255,255,255,0.95)",border:"1px solid #e2e8f0"},
  slR:{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4},
  rng:{width:"100%",cursor:"pointer",height:6},
  sht:{position:"fixed",bottom:0,left:0,right:0,maxWidth:430,margin:"0 auto",background:"#fff",borderRadius:"16px 16px 0 0",boxShadow:"0 -4px 30px rgba(0,0,0,0.1)",zIndex:200,display:"flex",flexDirection:"column",transition:"height 0.3s ease-out"},
  hdl:{display:"flex",flexDirection:"column",alignItems:"center",padding:"6px 0 2px",cursor:"pointer"},
  hb:{width:28,height:3.5,borderRadius:2,background:"#d1d5db"},
  sb:{flex:1,overflowY:"auto",padding:"0 12px 65px"},
  sa:{position:"absolute",bottom:0,left:0,right:0,padding:"5px 12px 8px",background:"linear-gradient(transparent,#fff 30%)"},
  ab:{width:"100%",padding:"10px",borderRadius:9,border:"none",color:"#fff",fontSize:12,fontWeight:700,cursor:"pointer",fontFamily:"system-ui"},
  ai:{marginTop:8,padding:10,borderRadius:9,background:"linear-gradient(135deg,#f5f3ff,#ede9fe)",border:"1px solid #e0d8f5"},
  cw:{marginTop:12,paddingTop:8,borderTop:"1px solid #e7e5e4"},
  h3:{fontSize:12,fontWeight:700,color:"#292524",margin:"0 0 5px",fontFamily:"'Georgia',serif"},
  ir:{display:"flex",gap:6,alignItems:"flex-start",padding:"6px 8px",marginBottom:4,borderRadius:6,background:"#fafaf8",border:"1px solid #e7e5e4"},
  sos:{position:"fixed",bottom:12,left:"50%",transform:"translateX(-50%)",width:46,height:46,borderRadius:23,border:"3px solid #fff",background:"linear-gradient(135deg,#dc2626,#991b1b)",color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",cursor:"pointer",boxShadow:"0 4px 20px rgba(220,38,38,0.4)",zIndex:150},
  chW:{position:"fixed",bottom:0,left:0,right:0,maxWidth:430,margin:"0 auto",height:"60vh",background:"#fff",borderRadius:"14px 14px 0 0",boxShadow:"0 -4px 24px rgba(0,0,0,0.12)",display:"flex",flexDirection:"column",zIndex:300},
  chH:{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"9px 12px",background:"linear-gradient(135deg,#dc2626,#991b1b)",color:"#fff"},
  chX:{background:"none",border:"none",color:"#fff",fontSize:16,cursor:"pointer"},
  chS:{flex:1,overflowY:"auto",padding:8},
  uR:{display:"flex",justifyContent:"flex-end",marginBottom:5},
  bR:{display:"flex",justifyContent:"flex-start",marginBottom:5},
  uB:{maxWidth:"78%",padding:"6px 10px",borderRadius:"10px 10px 2px 10px",background:"#dc2626",color:"#fff",fontSize:12,lineHeight:1.4,whiteSpace:"pre-wrap",fontFamily:"system-ui"},
  bB:{maxWidth:"78%",padding:"6px 10px",borderRadius:"10px 10px 10px 2px",background:"#f1f5f9",color:"#1e293b",fontSize:12,lineHeight:1.4,whiteSpace:"pre-wrap",fontFamily:"system-ui"},
  chB:{display:"flex",padding:"5px 8px",borderTop:"1px solid #e2e8f0",gap:5},
  chI:{flex:1,padding:"6px 10px",borderRadius:16,border:"1px solid #d1d5db",fontSize:12,outline:"none",fontFamily:"system-ui",background:"#fff"},
  chSe:{width:30,height:30,borderRadius:15,border:"none",background:"#dc2626",color:"#fff",fontSize:13,cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center"},
};
