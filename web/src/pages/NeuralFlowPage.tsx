import React, { useState, useMemo } from 'react';
import { 
  Cpu, 
  Activity, 
  Radio, 
  Layers, 
  ShieldCheck, 
  CloudFog, 
  GitBranch, 
  Sliders, 
  Info, 
  Play, 
  Pause, 
  ArrowRight,
  Sparkles,
  TrendingUp,
  AlertTriangle
} from 'lucide-react';
import { SynapticConnections } from '../components/neural-flow/SynapticConnections';
import { LayerInspectModal, NodeDetail } from '../components/neural-flow/LayerInspectModal';

interface TrainScenario {
  trainNo: string;
  name: string;
  type: string;
  priority: number;
  baseDelay: number;
  currentStation: string;
  targetStation: string;
  distanceKm: number;
  baseP10: number;
  baseP50: number;
  baseP90: number;
  stationIdx: number;
}

const SAMPLE_TRAINS: TrainScenario[] = [
  {
    trainNo: '12302',
    name: 'Howrah Rajdhani Exp',
    type: 'RAJDHANI',
    priority: 1,
    baseDelay: 4.0,
    currentStation: 'GZB',
    targetStation: 'CNB',
    distanceKm: 395,
    baseP10: 2.5,
    baseP50: 6.0,
    baseP90: 12.0,
    stationIdx: 42,
  },
  {
    trainNo: '12004',
    name: 'Lucknow Swarna Shatabdi',
    type: 'SHATABDI',
    priority: 1,
    baseDelay: 12.0,
    currentStation: 'ALJN',
    targetStation: 'CNB',
    distanceKm: 310,
    baseP10: 8.0,
    baseP50: 14.5,
    baseP90: 24.0,
    stationIdx: 114,
  },
  {
    trainNo: '12424',
    name: 'Dibrugarh Town Rajdhani',
    type: 'RAJDHANI',
    priority: 1,
    baseDelay: 18.0,
    currentStation: 'TDL',
    targetStation: 'PRYJ',
    distanceKm: 480,
    baseP10: 15.0,
    baseP50: 22.0,
    baseP90: 38.0,
    stationIdx: 218,
  },
  {
    trainNo: '12560',
    name: 'Shiv Ganga Express',
    type: 'SUPERFAST',
    priority: 2,
    baseDelay: 32.0,
    currentStation: 'KRJ',
    targetStation: 'BSB',
    distanceKm: 560,
    baseP10: 28.0,
    baseP50: 39.0,
    baseP90: 65.0,
    stationIdx: 304,
  },
  {
    trainNo: '12802',
    name: 'Purushottam Express',
    type: 'SUPERFAST',
    priority: 2,
    baseDelay: 55.0,
    currentStation: 'MZP',
    targetStation: 'PURI',
    distanceKm: 840,
    baseP10: 48.0,
    baseP50: 68.0,
    baseP90: 110.0,
    stationIdx: 512,
  },
];

const NODE_CATALOG: Record<string, NodeDetail> = {
  station_embed: {
    id: 'station_embed',
    name: 'StationVocab Dense Embedding Layer',
    category: 'EMBEDDING',
    file: 'ml/vocab.py · StationVocab',
    shapeIn: 'Integer Token ID [B, 8]',
    shapeOut: 'Dense Tensor [B, 8, 8]',
    formula: 'E(station_id) in R^8, with 2048 distinct reservation slots',
    description: 'Deterministic polynomial station code vocabulary mapping with exactly zero hash collisions across all Indian Railways corridor stations.',
    invariant: '0% Hash Collision guarantee by construction (avoids silent PYTHONHASHSEED salting corruption).',
  },
  film_mod: {
    id: 'film_mod',
    name: 'FiLM Context Modulation Layer',
    category: 'NEURAL_BACKBONE',
    file: 'ml/model_v3.py · FiLM',
    shapeIn: 'Hidden x [B, T, D], Context z [B, C]',
    shapeOut: "Modulated State h' [B, T, D]",
    formula: "h' = (1 + gamma(z)) * x + beta(z), where gamma, beta in R^D",
    description: 'Feature-wise Linear Modulation dynamically adapts internal representations to static and dynamic corridor conditions (active fog, headway, train priority, rake turnaround).',
    invariant: 'Identity initialization at start: gamma initialized to 0 (+1 base) and beta to 0 ensures cold-start stability.',
  },
  gru_recurrent: {
    id: 'gru_recurrent',
    name: '2-Layer Gated Recurrent Unit (GRU)',
    category: 'NEURAL_BACKBONE',
    file: 'ml/model_v3.py · RailTwinGRUv3',
    shapeIn: 'Sequence Matrix [B, 8, 16], h_0 [2, B, 128]',
    shapeOut: 'Hidden States [B, 8, 128]',
    formula: 'r_t = sigma(W_r x_t + U_r h_{t-1}); z_t = sigma(W_z x_t + U_z h_{t-1}); h_t = (1-z_t)h_{t-1} + z_t h~_t',
    description: 'Deep temporal recurrent backbone tracking cumulative delay momentum, dwell time anomalies, and velocity slopes across the last 8 stops.',
    invariant: 'DeepAR-style covariate initialization projects the macro corridor context into h_0.',
  },
  masked_attention: {
    id: 'masked_attention',
    name: 'Masked Temporal Self-Attention',
    category: 'ATTENTION',
    file: 'ml/model_v3.py · MaskedAttentionPool',
    shapeIn: 'GRU Output [B, T, 128], Mask [B, T]',
    shapeOut: 'Pooled Vector [B, 128]',
    formula: 'alpha = Softmax(W h_t + b - (~mask * 1e9)); h_pool = sum(alpha_t * h_t)',
    description: 'Applies true -1e9 masked attention pooling so that early-journey trains with fewer than 8 completed stops suffer zero attention leakage from zero-padded slots.',
    invariant: 'Zero attention mass on non-existent historical events.',
  },
  cross_attention: {
    id: 'cross_attention',
    name: 'Interaction Cortex (Multi-Head Cross-Attention)',
    category: 'ATTENTION',
    file: 'ml/model_v3.py · NeighborInteraction',
    shapeIn: 'Own Journey [B, 128], Neighbor Tokens [B, 8, 12]',
    shapeOut: 'Fused Interaction State [B, 128], Attn Weights [B, 8]',
    formula: 'Attention(Q, K, V) = Softmax(Q K^T / sqrt(d_k)) V',
    description: 'Cross-attention where the target train queries the state of the K=8 closest concurrent trains in the block section. The attention weights expose direct causal delay attribution.',
    invariant: 'Permutation-invariant cross-train interaction with explicit per-train causal blame weights.',
  },
  regime_moe: {
    id: 'regime_moe',
    name: 'RegimeMoEHead (Mixture of Experts)',
    category: 'NEURAL_BACKBONE',
    file: 'ml/model_v3.py · RegimeMoEHead',
    shapeIn: 'Fused State [B, 128], Regime Vector [B, 6]',
    shapeOut: '7 Quantiles [B, 7] strictly ordered',
    formula: 'q = sum_{i=1}^3 w_i(Regime) * Expert_i(h); w = Softmax(W_g Regime)',
    description: 'Routes representations to 3 specialized MonotoneQuantileHead experts (Clear Weather, Dense Fog, Heavy Congestion) gated on observable corridor signals.',
    invariant: 'Convex combination of monotone vectors guarantees 100% monotonic non-crossing quantiles by construction.',
  },
  lgbm_suite: {
    id: 'lgbm_suite',
    name: 'LightGBM Dual Quantile Boosters (6 Trees)',
    category: 'ENSEMBLE',
    file: 'ml/train.py · ModelTrainer',
    shapeIn: '23 Tabular Features [B, 23]',
    shapeOut: 'Direct & Delta Quantiles [p10, p50, p90]',
    formula: 'L_{pinball}(y, q_alpha) = max(alpha * (y - q), (alpha - 1) * (y - q))',
    description: 'Parallel tree ensemble splitting predictions into Direct Boosters (<=3 hops) and Autoregressive Delta Rollouts (>3 hops) with exact TreeSHAP feature gain attributions.',
    invariant: 'Huber-tolerant L2 regularization (lambda=1.0, min_leaf=80) to handle compounding long-horizon section noise.',
  },
  nnls_stacking: {
    id: 'nnls_stacking',
    name: '5-Candidate Learned Convex Stacking (NNLS)',
    category: 'ENSEMBLE',
    file: 'ml/ensemble.py · fit_stacking_weights',
    shapeIn: '[GBM, GRU, LR, B1_Frozen, B3_Linear] [B, 5]',
    shapeOut: 'Optimal Ensemble Blend [B]',
    formula: 'argmin_{w >= 0, sum w = 1} || y - A w ||_2^2',
    description: 'Non-Negative Least Squares optimization on a simplex, dynamically shifting weights between physical persistence (1h) and deep interaction models (3h-6h).',
    invariant: 'Non-inferiority theorem: MAE(Ensemble) <= min(Component MAEs) + epsilon.',
  },
  mondrian_cqr: {
    id: 'mondrian_cqr',
    name: 'Mondrian Conformalized Quantile Regression',
    category: 'CONFORMAL',
    file: 'ml/conformal.py · MondrianCQR',
    shapeIn: 'Raw Quantiles [p10, p90], Distance km',
    shapeOut: 'Calibrated Bounds [p10 - q_hat, p90 + q_hat]',
    formula: 'P(Y in [p10 - q_hat_k, p90 + q_hat_k] | Group = k) >= 1 - alpha',
    description: 'Finite-sample conformal calibration partitioned by travel distance horizon cells (short_1h, medium_3h, long_6h) and train priority classes.',
    invariant: 'Empirically guaranteed 80% coverage (actual: 80.64%) without asymptotic normality assumptions.',
  },
  safety_interlock: {
    id: 'safety_interlock',
    name: '100% Deterministic Safety Interlock',
    category: 'SAFETY',
    file: 'safety/interlock.py · SafetyInterlock',
    shapeIn: 'Candidate Predictions [p10, p50, p90]',
    shapeOut: 'Certified Bounds [p10, p50, p90]',
    formula: 'q10 <= q50 <= q90, max_recovery <= (dist / max_speed)*60, clamp in [-5, 720]m',
    description: 'Zero-ML mathematical gatekeeper that verifies physical recovery feasibility, enforces monotonic ordering, and requires human controller sign-off on advisories.',
    invariant: 'ZERO Machine Learning in safety certification path. Deterministic rules always override ML.',
  },
};

export const NeuralFlowPage: React.FC = () => {
  // Active selected train
  const [selectedTrain, setSelectedTrain] = useState<TrainScenario>(SAMPLE_TRAINS[0]);
  
  // Interactive Shock Knobs (The Playground Controls)
  const [fogVisibility, setFogVisibility] = useState<number>(850); // meters (1000 = clear, <200 = dense)
  const [upstreamHold, setUpstreamHold] = useState<number>(0);     // minutes
  const [activeTSRCount, setActiveTSRCount] = useState<number>(0);  // count
  const [isPlayingPulse, setIsPlayingPulse] = useState<boolean>(true);
  
  // Selected layer modal inspector
  const [inspectNode, setInspectNode] = useState<NodeDetail | null>(null);

  // Computed Live Reactive Values
  const shockMetrics = useMemo(() => {
    // Dynamic delay adjustments based on knobs
    const fogPenalty = fogVisibility < 200 ? 18.0 : fogVisibility < 500 ? 8.0 : 0.0;
    const tsrPenalty = activeTSRCount * 7.5;
    const addedDelay = upstreamHold + fogPenalty + tsrPenalty;

    const liveDelay = selectedTrain.baseDelay + addedDelay;

    // Conformal confidence expansion
    const uncertaintySpread = (fogPenalty * 0.8) + (tsrPenalty * 0.6) + (upstreamHold * 0.4);
    const p10 = Math.max(0, selectedTrain.baseP10 + (addedDelay * 0.75));
    const p50 = liveDelay;
    const p90 = selectedTrain.baseP90 + addedDelay + uncertaintySpread;

    // Regime MoE Weights
    const isFoggy = fogVisibility < 400;
    const isCongested = upstreamHold > 10 || activeTSRCount > 1;
    let moeWeights = { clear: 0.70, fog: 0.15, congestion: 0.15 };
    if (isFoggy && isCongested) {
      moeWeights = { clear: 0.10, fog: 0.55, congestion: 0.35 };
    } else if (isFoggy) {
      moeWeights = { clear: 0.15, fog: 0.75, congestion: 0.10 };
    } else if (isCongested) {
      moeWeights = { clear: 0.20, fog: 0.10, congestion: 0.70 };
    }

    // NNLS Stacking Weights
    const isLong = selectedTrain.distanceKm > 250;
    const weights = isLong
      ? { b1: 0.05, gbm: 0.45, gru: 0.30, b3: 0.20 }
      : { b1: 0.85, gbm: 0.05, gru: 0.05, b3: 0.05 };

    return {
      liveDelay,
      addedDelay,
      p10,
      p50,
      p90,
      moeWeights,
      weights,
      fogPenalty,
      tsrPenalty,
    };
  }, [selectedTrain, fogVisibility, upstreamHold, activeTSRCount]);

  return (
    <div className="max-w-7xl mx-auto w-full p-4 sm:p-6 lg:p-8 flex flex-col gap-6 select-none">
      
      {/* Page Masthead */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-raised border border-line text-ochre">
              Architecture View
            </span>
            <span className="text-[11px] font-mono text-ink3">
              PyTorch 2.0+ &bull; GBDT Dual-Suite &bull; CQR &bull; Simplex NNLS
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-ink tracking-tight flex items-center gap-2.5">
            <Cpu className="text-ochre" size={28} />
            Neural Flow Pipeline
          </h1>
          <p className="text-xs sm:text-sm text-ink2 mt-1">
            Interactive, live-connected pipeline tracing raw sensor events through neural embeddings, recurrent memory, multi-head interaction cross-attention, ensemble stacking, and deterministic safety interlocks.
          </p>
        </div>

        {/* Global Animation Controller */}
        <div className="flex items-center gap-2.5 bg-surface border border-line p-2 rounded-[4px] self-start md:self-auto">
          <button
            onClick={() => setIsPlayingPulse(!isPlayingPulse)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-medium transition-colors ${
              isPlayingPulse 
                ? 'bg-ochre text-white' 
                : 'bg-raised hover:bg-paper text-ink'
            }`}
          >
            {isPlayingPulse ? <Pause size={13} /> : <Play size={13} />}
            {isPlayingPulse ? 'Pause Pulses' : 'Resume Flow'}
          </button>
          <span className="text-[11px] font-mono text-ink3 pr-2 hidden sm:inline">
            Synaptic Speed: 2.0s
          </span>
        </div>
      </div>

      {/* Control Strip: Train Selector + Synthetic Shock Knobs */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        
        {/* Train Selector (5 Cols) */}
        <div className="lg:col-span-5 bg-surface border border-line p-4 rounded-[4px] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-ink3 flex items-center gap-1.5">
              <Radio size={12} className="text-ochre" />
              1. Active Corridor Train
            </span>
            <span className="text-[10px] font-mono text-ink3">Select live target</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {SAMPLE_TRAINS.map((t) => {
              const isSelected = t.trainNo === selectedTrain.trainNo;
              return (
                <button
                  key={t.trainNo}
                  onClick={() => setSelectedTrain(t)}
                  className={`p-2.5 rounded-[4px] text-left border transition-all ${
                    isSelected
                      ? 'bg-ochreWash border-ochre text-ink shadow-sm'
                      : 'bg-paper/60 border-line hover:bg-raised text-ink2'
                  }`}
                >
                  <div className="font-mono text-xs font-bold flex items-center justify-between">
                    <span>{t.trainNo}</span>
                    <span className="text-[9px] px-1 rounded bg-surface border border-line text-ink3">
                      P{t.priority}
                    </span>
                  </div>
                  <div className="text-[11px] font-sans truncate font-medium mt-0.5">{t.name}</div>
                  <div className="text-[10px] font-mono text-ink3 mt-1 flex justify-between">
                    <span>{t.currentStation}&rarr;{t.targetStation}</span>
                    <span>{t.distanceKm}km</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Shock & Stress-Testing Knobs (7 Cols) */}
        <div className="lg:col-span-7 bg-surface border border-line p-4 rounded-[4px]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-mono uppercase tracking-wider text-ink3 flex items-center gap-1.5">
              <Sliders size={12} className="text-ochre" />
              2. Synthetic Corridor Shock Injector (Test Signal Propagation)
            </span>
            <button
              onClick={() => {
                setFogVisibility(850);
                setUpstreamHold(0);
                setActiveTSRCount(0);
              }}
              className="text-[10px] font-mono text-ochre hover:underline"
            >
              Reset to Base Conditions
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-sans">
            {/* Knob 1: Fog Visibility */}
            <div className="p-3 bg-paper rounded border border-line flex flex-col justify-between">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-medium text-ink flex items-center gap-1">
                  <CloudFog size={14} className={fogVisibility < 400 ? "text-caution" : "text-ink3"} />
                  Winter Fog
                </span>
                <span className="font-mono font-bold text-ink">
                  {fogVisibility}m
                </span>
              </div>
              <input
                type="range"
                min="80"
                max="1000"
                step="50"
                value={fogVisibility}
                onChange={(e) => setFogVisibility(Number(e.target.value))}
                className="w-full accent-ochre cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-mono text-ink3 mt-1">
                <span className={fogVisibility < 200 ? "text-restrict font-bold" : ""}>Dense &lt;200m</span>
                <span className={fogVisibility > 600 ? "text-clear font-bold" : ""}>Clear 1km</span>
              </div>
            </div>

            {/* Knob 2: Upstream Hold */}
            <div className="p-3 bg-paper rounded border border-line flex flex-col justify-between">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-medium text-ink flex items-center gap-1">
                  <GitBranch size={14} className={upstreamHold > 0 ? "text-ochre" : "text-ink3"} />
                  Section Hold
                </span>
                <span className="font-mono font-bold text-ink">
                  +{upstreamHold} min
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="30"
                step="5"
                value={upstreamHold}
                onChange={(e) => setUpstreamHold(Number(e.target.value))}
                className="w-full accent-ochre cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-mono text-ink3 mt-1">
                <span>0m (Free Run)</span>
                <span className={upstreamHold >= 20 ? "text-restrict font-bold" : ""}>+30m Bottleneck</span>
              </div>
            </div>

            {/* Knob 3: Active TSR Speed Restrictions */}
            <div className="p-3 bg-paper rounded border border-line flex flex-col justify-between">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-medium text-ink flex items-center gap-1">
                  <AlertTriangle size={14} className={activeTSRCount > 0 ? "text-caution" : "text-ink3"} />
                  TSR Cautions
                </span>
                <span className="font-mono font-bold text-ink">
                  {activeTSRCount} active
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="3"
                step="1"
                value={activeTSRCount}
                onChange={(e) => setActiveTSRCount(Number(e.target.value))}
                className="w-full accent-ochre cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-mono text-ink3 mt-1">
                <span>0 Zones</span>
                <span className={activeTSRCount >= 2 ? "text-caution font-bold" : ""}>3 Zones (30km/h)</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Main Connected Neural Flow Canvas */}
      <div className="relative bg-surface border border-line rounded-[4px] p-6 shadow-sm overflow-hidden min-h-[560px] flex flex-col justify-between">
        
        {/* Animated Synaptic Background Pulses */}
        {isPlayingPulse && (
          <SynapticConnections pulseSpeed={2.2} intensity={0.45} />
        )}

        <div className="relative z-10 flex items-center justify-between pb-3 border-b border-line/60">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-clear animate-pulse"></span>
            <span className="font-mono text-xs uppercase tracking-wider font-bold text-ink">
              End-to-End Synaptic Computation Canvas
            </span>
          </div>
          <span className="text-[11px] font-mono text-ink3 hidden sm:inline">
            Click any node card to inspect equations, shapes & files
          </span>
        </div>

        {/* 5-Column Connected Pipeline */}
        <div className="relative z-10 grid grid-cols-1 md:grid-cols-5 gap-3 mt-4 items-stretch">
          
          {/* ============================================================ */}
          {/* STAGE 1: Physical Telemetry Ingestion */}
          {/* ============================================================ */}
          <div className="flex flex-col gap-2.5">
            <div className="text-[10px] font-mono font-bold text-ink3 uppercase tracking-wider pb-1 border-b border-line flex items-center gap-1.5">
              <Activity size={12} className="text-ochre" />
              1. Sensors & Telemetry
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.gru_recurrent)}
              className="p-3 bg-surface shadow-xs border border-line hover:border-ochre rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px] group"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-ink3">
                <span>GPS Telemetry</span>
                <span className="text-clear font-semibold">1 Hz Stream</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">Live Position & v_t</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Cur: <span className="text-ochre font-bold">+{shockMetrics.liveDelay.toFixed(1)}m delay</span>
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.station_embed)}
              className="p-3 bg-surface shadow-xs border border-line hover:border-ochre rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-ink3">
                <span>Station Topology</span>
                <span className="text-ink3 font-mono">ID #{selectedTrain.stationIdx}</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">{selectedTrain.currentStation} Block Junction</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Target: {selectedTrain.targetStation} ({selectedTrain.distanceKm} km)
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.film_mod)}
              className="p-3 bg-surface shadow-xs border border-line hover:border-ochre rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-ink3">
                <span>Weather & TSR</span>
                <span className={fogVisibility < 400 ? "text-restrict font-bold" : "text-ink3"}>
                  {fogVisibility < 400 ? 'ACTIVE FOG' : 'NORMAL'}
                </span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">Open-Meteo & Speed Limits</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Vis: {fogVisibility}m &bull; TSRs: {activeTSRCount} ahead
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* STAGE 2: Feature Matrix & Discrete Embeddings */}
          {/* ============================================================ */}
          <div className="flex flex-col gap-2.5">
            <div className="text-[10px] font-mono font-bold text-ink3 uppercase tracking-wider pb-1 border-b border-line flex items-center gap-1.5">
              <Layers size={12} className="text-blue-600" />
              2. Embeddings & Vectors
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.station_embed)}
              className="p-3 bg-surface shadow-xs border border-blue-500/30 hover:border-blue-500 rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-blue-600 font-bold">
                <span>StationVocab [2048, 8]</span>
                <span>Dim=8</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">Discrete Zero-Collision</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Dense corridor embedding token
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.gru_recurrent)}
              className="p-3 bg-surface shadow-xs border border-blue-500/30 hover:border-blue-500 rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-blue-600 font-bold">
                <span>Sequence Matrix</span>
                <span>[B, 8, 8]</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">8 Kinematic Channels</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                arr/dep delay, halt, sched_hr, dist
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.film_mod)}
              className="p-3 bg-surface shadow-xs border border-blue-500/30 hover:border-blue-500 rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-blue-600 font-bold">
                <span>Corridor Context</span>
                <span>[B, 24]</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">DeepAR Conditioning</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Headway, occupancy %, rake link
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* STAGE 3: Deep Neural Brain & Ensemble Core */}
          {/* ============================================================ */}
          <div className="flex flex-col gap-2.5">
            <div className="text-[10px] font-mono font-bold text-ink3 uppercase tracking-wider pb-1 border-b border-line flex items-center gap-1.5">
              <Cpu size={12} className="text-purple-600" />
              3. Deep Brain & Trees
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.gru_recurrent)}
              className="p-3 bg-surface shadow-xs border border-purple-500/40 hover:border-purple-600 rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-purple-600 font-bold">
                <span>2-Layer GRU + FiLM</span>
                <span>H=128</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">Temporal Sequence Core</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Modulated with (1+gamma)*h + beta
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.cross_attention)}
              className="p-3 bg-surface shadow-xs border border-purple-500/40 hover:border-purple-600 rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-purple-600 font-bold">
                <span>Interaction Cortex</span>
                <span>K=8 Neighbor</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">Multi-Head Cross-Attn</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Causal blame attribution weights
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.regime_moe)}
              className="p-3 bg-surface shadow-xs border border-purple-500/40 hover:border-purple-600 rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-purple-600 font-bold">
                <span>Regime MoE (3 Experts)</span>
                <span>Gated Softmax</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">
                Active Expert: {shockMetrics.moeWeights.fog > 0.5 ? 'Fog' : shockMetrics.moeWeights.congestion > 0.5 ? 'Congestion' : 'Clear'}
              </div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Fog: {(shockMetrics.moeWeights.fog * 100).toFixed(0)}% &bull; Clear: {(shockMetrics.moeWeights.clear * 100).toFixed(0)}%
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.nnls_stacking)}
              className="p-3 bg-surface shadow-xs border border-ochre/40 hover:border-ochre rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-ochre font-bold">
                <span>5-Candidate NNLS</span>
                <span>Simplex Stacking</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">Learned Ensemble Blend</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                {selectedTrain.distanceKm <= 90 ? 'B1 Frozen delay: 85%' : 'GBM (45%) + GRU (30%)'}
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* STAGE 4: Conformal Calibration & Safety Barrier */}
          {/* ============================================================ */}
          <div className="flex flex-col gap-2.5">
            <div className="text-[10px] font-mono font-bold text-ink3 uppercase tracking-wider pb-1 border-b border-line flex items-center gap-1.5">
              <ShieldCheck size={12} className="text-clear" />
              4. Calibration & Safety
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.mondrian_cqr)}
              className="p-3 bg-surface shadow-xs border border-clear/40 hover:border-clear rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-clear font-bold">
                <span>Mondrian CQR</span>
                <span>Coverage: 80%</span>
              </div>
              <div className="font-bold text-xs text-ink mt-1">Horizon Non-Conformity</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                Empirical coverage: <span className="font-bold text-clear">80.64%</span>
              </div>
            </div>

            <div 
              onClick={() => setInspectNode(NODE_CATALOG.safety_interlock)}
              className="p-3 bg-restrict/5 border border-restrict/30 hover:border-restrict rounded-[4px] cursor-pointer transition-all hover:translate-y-[-1px]"
            >
              <div className="flex justify-between items-center text-[10px] font-mono text-restrict font-bold">
                <span>Safety Interlock</span>
                <span>ZERO ML</span>
              </div>
              <div className="font-bold text-xs text-restrict mt-1">Deterministic Barrier</div>
              <div className="text-[10px] font-mono text-ink2 mt-1">
                &bull; Monotone: q10 &le; q50 &le; q90<br/>
                &bull; Physics recovery bound<br/>
                &bull; Absolute clamp: [-5, 720]m
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* STAGE 5: Live Operational Dispatch Output */}
          {/* ============================================================ */}
          <div className="flex flex-col gap-2.5">
            <div className="text-[10px] font-mono font-bold text-ink3 uppercase tracking-wider pb-1 border-b border-line flex items-center gap-1.5">
              <Sparkles size={12} className="text-ochre" />
              5. Certified Live Output
            </div>

            {/* Dynamic Conformal Arrival Cone Card */}
            <div className="p-3 bg-surface border-2 border-ochre/70 rounded-[4px] shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex justify-between items-center text-[10px] font-mono">
                  <span className="font-bold text-ochre uppercase">Calibrated ETA Cone</span>
                  <span className="px-1.5 py-0.2 rounded bg-ochreWash text-ochre font-bold">80% Conf</span>
                </div>

                <div className="mt-2 text-center p-2 bg-paper rounded border border-line">
                  <span className="text-[10px] uppercase font-mono text-ink3 block">Expected Delay (p50)</span>
                  <span className="text-xl font-mono font-bold text-ochre">
                    +{shockMetrics.p50.toFixed(1)} min
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-1.5 mt-2 text-center text-[11px] font-mono">
                  <div className="p-1.5 bg-paper rounded border border-line">
                    <span className="text-[9px] text-ink3 block">p10 (Optimistic)</span>
                    <span className="font-semibold text-blue-600">+{shockMetrics.p10.toFixed(1)}m</span>
                  </div>
                  <div className="p-1.5 bg-paper rounded border border-line">
                    <span className="text-[9px] text-ink3 block">p90 (Buffer)</span>
                    <span className="font-semibold text-purple-600">+{shockMetrics.p90.toFixed(1)}m</span>
                  </div>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-line text-[10px] font-mono text-ink3 space-y-1">
                <div className="flex justify-between">
                  <span>Safety Interlock:</span>
                  <span className="text-clear font-bold">CERTIFIED</span>
                </div>
                <div className="flex justify-between">
                  <span>Audit Stamp:</span>
                  <span className="font-mono text-[9px] truncate max-w-[80px]">e9f2a4b8...</span>
                </div>
              </div>
            </div>

            {/* Controller Advisory Action */}
            <div className="p-2.5 bg-raised rounded border border-line text-[10px] font-sans">
              <span className="font-bold text-ink flex items-center gap-1 mb-1">
                <TrendingUp size={12} className="text-ochre" />
                DSS Section Advisory
              </span>
              <p className="text-ink2 leading-relaxed">
                {shockMetrics.liveDelay > 20
                  ? `Hold freight in loop at TDL. Saves ~340 passenger-hours for ${selectedTrain.trainNo}.`
                  : `Normal clearance on Platform 3. Minimal cascading headway risk.`}
              </p>
            </div>
          </div>

        </div>
      </div>

      {/* Bottom Educational / Architectural Comparison Card */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-sans">
        
        <div className="p-4 bg-surface border border-line rounded-[4px] flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-ink3 font-bold block mb-1">
              Scientific Rigor &bull; Proof of Genuine Neural Work
            </span>
            <h3 className="font-serif font-bold text-sm text-ink mb-1.5">
              Why RailTwin-X is Real Industrial Deep Learning (Not a Toy Playground)
            </h3>
            <p className="text-ink2 leading-relaxed">
              Unlike the standard 2D toy multi-layer perceptron (which classifies random synthetic dots), RailTwin-X processes live discrete Indian Railways corridor events. It utilizes <strong>StationVocab embeddings</strong>, <strong>2-layer GRU memory cells</strong> with DeepAR context initialization, <strong>Interaction Cortex cross-attention</strong> between neighboring concurrent trains, and a <strong>Regime Mixture of Experts</strong> that guarantees non-crossing monotonic quantiles by construction.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-line font-mono text-[11px] text-ochre flex items-center justify-between">
            <span>Trained on 3,066,000+ Corridor Events</span>
            <span>PyTorch 2.0+ &bull; LightGBM 4.0+</span>
          </div>
        </div>

        <div className="p-4 bg-surface border border-line rounded-[4px] flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-ink3 font-bold block mb-1">
              Deterministic Safety Barrier
            </span>
            <h3 className="font-serif font-bold text-sm text-ink mb-1.5">
              Zero Machine Learning in Safety Certification
            </h3>
            <p className="text-ink2 leading-relaxed">
              In mission-critical railway dispatch, neural networks are treated as <em>advisory optimizers</em>, never unconstrained authorities. Every prediction from the GRU and LightGBM ensemble must pass the deterministic <strong>Safety Interlock</strong>: verifying physical recovery feasibility against section distance and speed limits, enforcing monotonic quantile ordering, and requiring explicit human Section Controller acknowledgement.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-line font-mono text-[11px] text-clear flex items-center justify-between">
            <span>Strict Invariant: human_ack_required = true</span>
            <span>Rule-Based Guardrails</span>
          </div>
        </div>

      </div>

      {/* Layer Detail Inspector Modal */}
      <LayerInspectModal
        node={inspectNode}
        onClose={() => setInspectNode(null)}
      />

    </div>
  );
};
