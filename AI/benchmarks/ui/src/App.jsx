import React, { useState, useEffect, useMemo } from 'react';
import _ from 'lodash';
import { 
  BarChart, 
  LayoutDashboard, 
  Cpu, 
  Monitor, 
  Layers, 
  Server,
  Activity,
  ArrowUpDown
} from 'lucide-react';

const STATS_MAP = {
  'tokens_per_second': 'Tokens/s',
  'ttft_s': 'TTFT (s)',
  'total_duration_s': 'Total Duration (s)'
};

const App = () => {
  const [data, setData] = useState(null);
  const [view, setView] = useState('hosts'); // 'hosts', 'models', 'aggregation'
  const [selectedHost, setSelectedHost] = useState('all');
  const [selectedModel, setSelectedModel] = useState('all');
  const [groupBy, setGroupBy] = useState('gpu');

  useEffect(() => {
    fetch('/benchmark_results.json')
      .then(res => res.json())
      .then(json => setData(json))
      .catch(err => console.error("Failed to load benchmarks:", err));
  }, []);

  const flattenedData = useMemo(() => {
    if (!data) return [];
    const runs = [];
    const hosts = Object.keys(data).filter(k => k !== '_prompts');

    hosts.forEach(hostId => {
      const host = data[hostId];
      const results = host.results || {};
      
      Object.entries(results).forEach(([modelId, contexts]) => {
        Object.entries(contexts).forEach(([ctxSize, benchmarkTypes]) => {
          if (modelId === '_model_stats') return;
          
          Object.entries(benchmarkTypes).forEach(([benchType, measurements]) => {
            if (benchType === '_model_stats' || !Array.isArray(measurements)) return;

            const stats = benchmarkTypes._model_stats || {};

            measurements.forEach(m => {
              runs.push({
                hostId,
                modelId,
                benchType,
                os: host.hardware.os,
                cpu: host.hardware.cpu,
                gpu: host.hardware.gpus?.[0]?.name || 'CPU',
                gpuType: host.hardware.gpus?.[0]?.type || 'N/A',
                family: stats.details?.family || 'unknown',
                paramSize: stats.details?.parameter_size || 'unknown',
                quant: stats.details?.quantization_level || 'unknown',
                ...m
              });
            });
          });
        });
      });
    });
    return runs;
  }, [data]);

  const aggregate = (runs, field) => {
    const groups = _.groupBy(runs, field);
    return Object.entries(groups).map(([key, groupRuns]) => {
      const metrics = ['tokens_per_second', 'ttft_s', 'total_duration_s'];
      const stats = {};
      
      metrics.forEach(m => {
        const values = groupRuns.map(r => r[m]).filter(v => v != null);
        if (values.length === 0) return;
        
        const mean = _.mean(values);
        const sorted = [...values].sort((a, b) => a - b);
        const median = sorted[Math.floor(sorted.length / 2)];
        const stdDev = Math.sqrt(_.sum(values.map(v => Math.pow(v - mean, 2))) / values.length);
        const cv = mean !== 0 ? (stdDev / mean) * 100 : 0;

        stats[m] = { mean, median, cv, count: values.length };
      });

      return { key, stats, raw: groupRuns[0] };
    }).sort((a, b) => (b.stats.tokens_per_second?.mean || 0) - (a.stats.tokens_per_second?.mean || 0));
  };

  if (!data) return <div className="p-8 text-center">Loading benchmark data...</div>;

  const hosts = Object.keys(data).filter(k => k !== '_prompts');
  const models = _.uniq(flattenedData.map(r => r.modelId));
  const gpus = _.uniq(flattenedData.map(r => r.gpu));

  const filteredRuns = flattenedData.filter(r => {
    if (view === 'hosts' && selectedHost !== 'all' && r.hostId !== selectedHost) return false;
    if (view === 'models' && selectedModel !== 'all' && r.modelId !== selectedModel) return false;
    return true;
  });

  const displayAggregates = aggregate(filteredRuns, 
    view === 'hosts' ? 'modelId' : 
    view === 'models' ? 'gpu' : 
    groupBy
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2">
              <BarChart className="text-blue-600 w-8 h-8" />
              <h1 className="text-xl font-bold tracking-tight">Gemini LLM Benchmarks</h1>
            </div>
            <nav className="flex space-x-4">
              <button 
                onClick={() => setView('hosts')}
                className={`px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2 ${view === 'hosts' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}
              >
                <Server size={18} /> Hosts
              </button>
              <button 
                onClick={() => setView('models')}
                className={`px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2 ${view === 'models' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}
              >
                <Layers size={18} /> Models
              </button>
              <button 
                onClick={() => setView('aggregation')}
                className={`px-3 py-2 rounded-md text-sm font-medium flex items-center gap-2 ${view === 'aggregation' ? 'bg-blue-50 text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}
              >
                <Activity size={18} /> Global
              </button>
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Controls */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 mb-8 flex flex-wrap gap-4 items-center">
          {view === 'hosts' && (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Select Host:</label>
              <select 
                value={selectedHost} 
                onChange={(e) => setSelectedHost(e.target.value)}
                className="rounded border-gray-300 text-sm focus:ring-blue-500"
              >
                <option value="all">All Hosts</option>
                {hosts.map(h => <option key={h} value={h}>{h}</option>)}
              </select>
            </div>
          )}

          {view === 'models' && (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Select Model:</label>
              <select 
                value={selectedModel} 
                onChange={(e) => setSelectedModel(e.target.value)}
                className="rounded border-gray-300 text-sm focus:ring-blue-500"
              >
                <option value="all">All Models</option>
                {models.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          )}

          {view === 'aggregation' && (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Aggregate By:</label>
              <select 
                value={groupBy} 
                onChange={(e) => setGroupBy(e.target.value)}
                className="rounded border-gray-300 text-sm focus:ring-blue-500"
              >
                <option value="gpu">GPU Name</option>
                <option value="family">Model Family</option>
                <option value="os">Platform (OS)</option>
                <option value="modelId">Specific Model</option>
              </select>
            </div>
          )}
        </div>

        {/* Results Grid */}
        <div className="grid grid-cols-1 gap-6">
          {displayAggregates.map((agg) => (
            <div key={agg.key} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 flex justify-between items-center">
                <div>
                  <h3 className="text-lg font-bold text-gray-900">{agg.key}</h3>
                  <div className="flex gap-4 mt-1">
                    {view === 'hosts' && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                        {agg.raw.family} • {agg.raw.paramSize} • {agg.raw.quant}
                      </span>
                    )}
                    {view === 'models' && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded bg-green-100 text-green-800">
                         {agg.raw.gpuType} • {agg.raw.os}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-black text-blue-600">
                    {agg.stats.tokens_per_second?.mean.toFixed(2)}
                    <span className="text-xs font-normal text-gray-500 ml-1">t/s</span>
                  </div>
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">Average Speed</div>
                </div>
              </div>

              <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8">
                {/* Visual Bar */}
                <div className="md:col-span-3">
                  <div className="w-full bg-gray-100 rounded-full h-4 overflow-hidden">
                    <div 
                      className="bg-blue-500 h-full transition-all duration-500"
                      style={{ width: `${Math.min(100, (agg.stats.tokens_per_second?.mean / 200) * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Metrics Table */}
                {Object.entries(agg.stats).map(([metric, values]) => (
                  <div key={metric} className="bg-gray-50 p-4 rounded-lg border border-gray-100">
                    <div className="text-xs font-bold text-gray-500 uppercase mb-3 flex items-center gap-2">
                      <ArrowUpDown size={14} /> {STATS_MAP[metric]}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-sm text-gray-500">Mean</div>
                        <div className="text-lg font-semibold">{values.mean.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Median</div>
                        <div className="text-lg font-semibold">{values.median.toFixed(2)}</div>
                      </div>
                      <div className="col-span-2 pt-2 border-t border-gray-200 flex justify-between items-center">
                        <span className="text-xs text-gray-500">Coeff. of Variation</span>
                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${values.cv > 15 ? 'bg-orange-100 text-orange-700' : 'bg-green-100 text-green-700'}`}>
                          {values.cv.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {displayAggregates.length === 0 && (
            <div className="text-center py-20 text-gray-500 italic bg-white rounded-xl border-2 border-dashed border-gray-200">
              No benchmark data found for this selection.
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;