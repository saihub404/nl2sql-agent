import { useState, useEffect } from "react";
import axios from "axios";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { Activity, AlertTriangle } from "lucide-react";

export default function Analytics() {
    const [metrics, setMetrics] = useState(null);
    const [errorStatus, setErrorStatus] = useState(false);

    useEffect(() => {
        axios.get("/api/metrics")
            .then(res => setMetrics(res.data))
            .catch(err => setErrorStatus(true));
    }, []);

    if (errorStatus) {
        return <div className="p-8 text-center text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl mt-10">⚠️ Could not reach backend metrics endpoint.</div>;
    }

    if (!metrics) {
        return <div className="p-8 text-center text-indigo-400 animate-pulse mt-10">Loading analytics...</div>;
    }

    const fb = metrics.failure_breakdown;
    const pieData = [
        { name: "Validation", value: fb.validation_failures },
        { name: "Execution", value: fb.execution_failures },
        { name: "Low Confidence", value: fb.low_confidence_rejections }
    ].filter(d => d.value > 0);
    const PIE_COLORS = ["#6366f1", "#8b5cf6", "#a78bfa"];

    const barData = metrics.confidence_distribution || [];

    return (
        <div>
            <div className="mb-6 flex items-start justify-between border-b border-white/5 pb-5">
                <div>
                    <h1 className="text-[1.7rem] font-extrabold text-slate-200 tracking-[-0.03em] mb-1">Analytics</h1>
                    <p className="text-[0.83rem] text-slate-500 font-medium">Real-time performance and accuracy metrics</p>
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-10">
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 hover:border-indigo-500/30 transition-colors">
                    <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Total Queries</div>
                    <div className="text-2xl font-bold text-slate-200">{metrics.total_queries.toLocaleString()}</div>
                </div>
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 hover:border-indigo-500/30 transition-colors">
                    <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Success Rate</div>
                    <div className="text-2xl font-bold text-emerald-400">{metrics.success_rate_pct}%</div>
                </div>
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 hover:border-indigo-500/30 transition-colors">
                    <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Correction Rate</div>
                    <div className="text-2xl font-bold text-orange-400">{metrics.correction_loop_rate_pct}%</div>
                </div>
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 hover:border-indigo-500/30 transition-colors">
                    <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Avg Latency</div>
                    <div className="text-2xl font-bold text-slate-200">{metrics.avg_latency_ms.toFixed(0)} ms</div>
                </div>
                <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-5 hover:border-indigo-500/30 transition-colors">
                    <div className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500 mb-1">Avg Confidence</div>
                    <div className="text-2xl font-bold text-slate-200">{(metrics.avg_confidence_score * 100).toFixed(0)}%</div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div>
                    <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-4">Failure Breakdown</div>
                    {pieData.length > 0 ? (
                        <div className="bg-white/5 border border-white/10 rounded-xl p-5 h-[320px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={70} outerRadius={100} paddingAngle={2} dataKey="value">
                                        {pieData.map((e, index) => <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />)}
                                    </Pie>
                                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: 'rgba(255,255,255,0.1)', color: '#f1f5f9' }} />
                                    <Legend verticalAlign="middle" align="right" layout="vertical" wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="bg-green-500/5 border border-green-500/15 rounded-xl p-10 h-[320px] flex flex-col items-center justify-center text-center">
                            <Activity size={48} className="text-green-500 mb-4 opacity-80" />
                            <div className="text-xl text-green-400 font-bold tracking-wide">Zero failures recorded</div>
                            <p className="text-sm text-green-500/70 mt-2">100% of queries successfully validated and executed.</p>
                        </div>
                    )}
                </div>

                <div>
                    <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-4">Confidence Distribution</div>
                    {barData.length > 0 ? (
                        <div className="bg-white/5 border border-white/10 rounded-xl p-5 h-[320px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={barData} margin={{ top: 20, right: 20, bottom: 10, left: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                    <XAxis dataKey="bucket" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                                    <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: 'rgba(255,255,255,0.1)', color: '#f1f5f9' }} />
                                    <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="bg-white/5 border border-dashed border-white/10 rounded-xl p-10 h-[320px] flex flex-col items-center justify-center text-center">
                            <AlertTriangle size={48} className="text-slate-600 mb-4 opacity-50" />
                            <p className="text-slate-500 font-medium">Run some queries to populate the confidence distribution.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
