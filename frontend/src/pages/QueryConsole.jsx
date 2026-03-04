import { useState, useEffect } from "react";
import axios from "axios";
import { Zap, Loader2, Database, Key, Clock, ListOrdered, CheckCircle2, XCircle } from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
    LineChart, Line, PieChart, Pie, Cell
} from "recharts";

export default function QueryConsole() {
    const [query, setQuery] = useState("");
    const [prompts, setPrompts] = useState([
        "Show top 5 rows",
        "What is the average value in all numeric columns?",
        "Count total records",
        "Show summary statistics"
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState(null);
    const [errorStatus, setErrorStatus] = useState(null);

    useEffect(() => {
        // Fetch dynamic prompts
        axios.get("/api/prompts").then(res => {
            if (res.data?.prompts) setPrompts(res.data.prompts);
        }).catch(err => console.error("Failed to fetch prompts", err));
    }, []);

    const handleRunQuery = async () => {
        if (!query.trim()) return;
        setIsLoading(true);
        setResponse(null);
        setErrorStatus(null);

        try {
            const res = await axios.post("/api/query", { query });
            setResponse(res.data);
            // Save globally or locally so Transparency can see it
            localStorage.setItem("lastQueryResponse", JSON.stringify(res.data));
        } catch (err) {
            if (err.response?.status === 422) {
                setErrorStatus("Query rejected — validation failed or confidence too low.");
            } else {
                setErrorStatus("Cannot reach backend. Is the service running?");
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && e.shiftKey) {
            e.preventDefault();
            handleRunQuery();
        }
    };

    // Automated Visualization selection heuristics matching python plotly logic
    const renderVisualization = (data) => {
        if (!data?.results?.rows || data.results.rows.length <= 1) return null;

        const columns = data.results.columns;
        const firstRow = data.results.rows[0];
        const catCols = [];
        const numCols = [];

        columns.forEach((col, idx) => {
            if (typeof firstRow[idx] === 'number') numCols.push({ name: col, idx });
            else catCols.push({ name: col, idx });
        });

        if (catCols.length === 0 || numCols.length === 0) return null;

        // Convert array of arrays to array of objects for Recharts
        const chartData = data.results.rows.map(row => {
            const obj = {};
            columns.forEach((col, i) => obj[col] = row[i]);
            return obj;
        }).slice(0, 20); // Top 20 for charts

        const cx = catCols[0].name;
        const cy = numCols[0].name;
        const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ede9fe', '#4f46e5'];

        let ChartComp;
        const isDate = cx.toLowerCase().match(/(date|month|year|week|day)/);

        if (data.results.rows.length <= 6 && !isDate) {
            ChartComp = (
                <PieChart>
                    <Pie data={chartData} dataKey={cy} nameKey={cx} cx="50%" cy="50%" outerRadius={80} label>
                        {chartData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                    </Pie>
                    <RechartsTooltip contentStyle={{ backgroundColor: '#0f1420', borderColor: 'rgba(255,255,255,0.1)' }} />
                </PieChart>
            );
        } else if (isDate) {
            ChartComp = (
                <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey={cx} stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <RechartsTooltip contentStyle={{ backgroundColor: '#0f1420', borderColor: 'rgba(255,255,255,0.1)' }} />
                    <Line type="monotone" dataKey={cy} stroke="#6366f1" strokeWidth={3} dot={{ r: 4, fill: '#8b5cf6' }} />
                </LineChart>
            );
        } else {
            // Sort for bar chart mimicking python `df.sort_values(ascending=False).head(20)`
            chartData.sort((a, b) => b[cy] - a[cy]);
            ChartComp = (
                <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis dataKey={cx} stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <RechartsTooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: 'rgba(255,255,255,0.1)', color: '#f1f5f9' }} />
                    <Bar dataKey={cy} fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
            );
        }

        return (
            <div className="mt-8">
                <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-4">Auto Visualization</div>
                <div className="bg-slate-900 border border-white/5 rounded-xl p-4 h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                        {ChartComp}
                    </ResponsiveContainer>
                </div>
            </div>
        );
    };

    return (
        <div>
            <div className="mb-6 flex items-start justify-between border-b border-white/5 pb-5">
                <div>
                    <h1 className="text-[1.7rem] font-extrabold text-slate-200 tracking-[-0.03em] mb-1">Query Console</h1>
                    <p className="text-[0.83rem] text-slate-500 font-medium">Ask any question in plain English against your uploaded datasets</p>
                </div>
                <div className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide whitespace-nowrap">
                    v1.0 • Gemini Powered
                </div>
            </div>

            <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-3">Quick Prompts</div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                {prompts.map((p, i) => (
                    <button
                        key={i}
                        onClick={() => setQuery(p)}
                        className="text-left bg-white/[0.03] hover:bg-white/[0.08] border border-white/5 rounded-lg p-3 py-4 text-xs font-medium text-slate-300 transition-colors shadow-sm"
                    >
                        {p}
                    </button>
                ))}
            </div>

            <div className="flex gap-4 mb-4">
                <textarea
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="e.g., Which department has the highest average salary?"
                    className="flex-1 bg-slate-900/50 border border-slate-700/50 rounded-xl p-4 text-slate-200 text-sm focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 min-h-[100px] resize-none"
                />
                <div className="w-[120px] shrink-0 flex flex-col gap-2">
                    <button
                        onClick={handleRunQuery}
                        disabled={isLoading || !query.trim()}
                        className="w-full h-full bg-gradient-to-br from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
                    >
                        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} />}
                        <span>Run</span>
                    </button>
                    <div className="text-[0.65rem] text-center text-slate-500">Shift+Enter to run</div>
                </div>
            </div>

            {isLoading && (
                <div className="flex items-center gap-3 text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 rounded-lg p-4 mt-8 animate-pulse">
                    <Loader2 size={20} className="animate-spin" />
                    <span className="text-sm font-medium">Reasoning about schema and generating optimized SQL...</span>
                </div>
            )}

            {errorStatus && (
                <div className="flex items-center gap-3 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-4 mt-8">
                    <XCircle size={20} />
                    <span className="text-sm font-medium">{errorStatus}</span>
                </div>
            )}

            {response && (
                <div className="mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {/* KPI Strip */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center relative overflow-hidden group hover:border-indigo-500/30 transition-colors">
                            <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Validation</div>
                            <div className={`text-lg font-bold flex items-center gap-2 ${response.validation_status === 'passed' ? 'text-green-400' : 'text-red-400'}`}>
                                {response.validation_status === 'passed' ? <><CheckCircle2 size={18} /> Passed</> : <><XCircle size={18} /> Failed</>}
                            </div>
                        </div>

                        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center relative hover:border-indigo-500/30 transition-colors">
                            <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Confidence</div>
                            <div className="text-lg font-bold text-slate-200">{(response.confidence_score * 100).toFixed(0)}%</div>
                        </div>

                        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center relative hover:border-indigo-500/30 transition-colors">
                            <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Latency</div>
                            <div className="text-lg font-bold text-slate-200">{response.latency_ms.toFixed(0)} ms</div>
                        </div>

                        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center relative hover:border-indigo-500/30 transition-colors">
                            <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Corrections</div>
                            <div className="text-lg font-bold text-slate-200">{response.correction_attempts}</div>
                        </div>

                        <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex flex-col items-center justify-center relative hover:border-indigo-500/30 transition-colors">
                            <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Rows</div>
                            <div className="text-lg font-bold text-slate-200">{response.results?.row_count ?? '—'}</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* SQL Panel */}
                        <div>
                            <div className="flex items-center justify-between mb-3">
                                <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase">Generated SQL</div>
                            </div>
                            <div className="bg-[#0d121c] border border-white/10 rounded-xl overflow-hidden shadow-inner">
                                <div className="flex gap-2 p-2 border-b border-white/5 bg-white/5">
                                    <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                                    <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                                    <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                                </div>
                                <pre className="p-4 text-xs font-mono text-indigo-200 overflow-x-auto whitespace-pre-wrap">{response.final_sql}</pre>
                            </div>

                            <div className="flex flex-wrap gap-2 mt-4">
                                {response.tables_used?.map(t => (
                                    <span key={t} className="px-3 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold flex items-center gap-2">
                                        <Database size={12} /> {t}
                                    </span>
                                ))}
                            </div>
                        </div>

                        {/* Results Dataframe Panel */}
                        <div>
                            <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-3">
                                Results {response.results?.row_count ? `(${response.results.row_count} rows)` : ''}
                            </div>
                            {response.execution_success && response.results ? (
                                <div className="bg-slate-900/50 border border-white/10 rounded-xl overflow-hidden">
                                    <div className="max-h-[350px] overflow-auto custom-scrollbar">
                                        <table className="w-full text-left text-xs whitespace-nowrap">
                                            <thead className="sticky top-0 bg-slate-800 text-slate-300 z-10 shadow-sm shadow-black/20">
                                                <tr>
                                                    {response.results.columns.map((col, i) => (
                                                        <th key={i} className="px-4 py-3 font-semibold border-b border-white/5">{col}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5 text-slate-400">
                                                {response.results.rows.map((row, r_idx) => (
                                                    <tr key={r_idx} className="hover:bg-white/[0.02]">
                                                        {row.map((cell, c_idx) => (
                                                            <td key={c_idx} className="px-4 py-3 max-w-[200px] truncate" title={String(cell)}>{String(cell)}</td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : (
                                <div className="bg-red-500/5 py-8 border border-red-500/20 rounded-xl flex flex-col items-center justify-center text-red-400">
                                    <XCircle size={32} className="mb-2" />
                                    <p className="font-semibold text-sm">Execution Error</p>
                                    <p className="text-xs text-red-400/70 mt-1 max-w-[80%] text-center">{response.execution_error}</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Dynamic Viz */}
                    {response.execution_success && renderVisualization(response)}
                </div>
            )}
        </div>
    );
}
