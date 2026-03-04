import { useState, useEffect } from "react";
import { SearchCode, RefreshCcw, DatabaseZap, Clock } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function Transparency() {
    const [data, setData] = useState(null);

    useEffect(() => {
        // Read from localStorage that QueryConsole saves to
        const lastData = localStorage.getItem("lastQueryResponse");
        if (lastData) {
            try {
                setData(JSON.parse(lastData));
            } catch (e) {
                console.error("Failed to parse last query", e);
            }
        }
    }, []);

    if (!data) {
        return (
            <div>
                <div className="mb-6 flex items-start justify-between border-b border-white/5 pb-5">
                    <div>
                        <h1 className="text-[1.7rem] font-extrabold text-slate-200 tracking-[-0.03em] mb-1">Transparency</h1>
                        <p className="text-[0.83rem] text-slate-500 font-medium">Inspect LLM reasoning, schema selection, and correction steps</p>
                    </div>
                </div>
                <div className="text-center py-20 bg-white/[0.02] border border-dashed border-white/[0.06] rounded-xl text-slate-500 flex flex-col items-center mt-10">
                    <SearchCode size={48} className="mb-4 opacity-50 text-indigo-400" />
                    <p className="font-semibold text-lg text-slate-300">No query recorded yet</p>
                    <p className="text-sm mt-2">Run a query in the Query Console first to see transparency data here.</p>
                </div>
            </div>
        );
    }

    // Parse Raw LLM Output safely
    let rawJson = "{}";
    try {
        rawJson = JSON.stringify(JSON.parse(data.raw_llm_output || "{}"), null, 2);
    } catch (e) {
        rawJson = data.raw_llm_output || "N/A";
    }

    // Transform similarity scores to array for Recharts
    const scoresObj = data.similarity_scores || {};
    const similarityChartData = Object.keys(scoresObj)
        .map(key => ({ table: key, score: scoresObj[key] * 100 }))
        .sort((a, b) => b.score - a.score);

    return (
        <div>
            <div className="mb-6 flex items-start justify-between border-b border-white/5 pb-5">
                <div>
                    <h1 className="text-[1.7rem] font-extrabold text-slate-200 tracking-[-0.03em] mb-1">Transparency</h1>
                    <p className="text-[0.83rem] text-slate-500 font-medium">Inspect LLM reasoning, schema selection, and correction steps</p>
                </div>
                <div className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                    Confidence: {(data.confidence_score * 100).toFixed(0)}%
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                {/* Left Column */}
                <div className="space-y-8">
                    <div>
                        <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-3">Raw LLM JSON Output</div>
                        <div className="bg-[#0d121c] border border-white/10 rounded-xl overflow-hidden shadow-inner max-h-[300px] overflow-y-auto custom-scrollbar">
                            <pre className="p-4 text-[0.7rem] font-mono text-emerald-300">{rawJson}</pre>
                        </div>
                    </div>

                    <div>
                        <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-3">Initial SQL Candidate</div>
                        <div className="bg-[#0d121c] border border-white/10 rounded-xl overflow-hidden shadow-inner">
                            <pre className="p-4 text-xs font-mono text-indigo-300 whitespace-pre-wrap">{data.generated_sql}</pre>
                        </div>
                    </div>

                    {data.generated_sql !== data.final_sql && (
                        <div className="border border-orange-500/30 rounded-xl overflow-hidden shadow-inner shadow-orange-500/10 relative">
                            <div className="absolute top-0 right-0 py-1 px-3 bg-orange-500/20 text-orange-400 text-[0.65rem] font-bold rounded-bl-lg">CORRECTED</div>
                            <div className="px-4 py-3 bg-orange-500/5 text-[0.75rem] text-orange-500/80 font-semibold tracking-[0.07em] uppercase flex items-center gap-2">
                                <RefreshCcw size={14} /> Refined SQL output
                            </div>
                            <div className="bg-[#0d121c]">
                                <pre className="p-4 pt-2 text-xs font-mono text-orange-300 whitespace-pre-wrap">{data.final_sql}</pre>
                            </div>
                        </div>
                    )}
                </div>

                {/* Right Column */}
                <div className="space-y-8">
                    <div>
                        <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-4">Pipeline Stats</div>
                        <div className="bg-white/5 border border-white/10 rounded-xl divide-y divide-white/5">
                            <div className="flex justify-between items-center px-5 py-4">
                                <span className="text-slate-400 text-sm font-medium">Original Query</span>
                                <span className="text-slate-200 text-sm font-medium text-right max-w-[50%]">{data.nl_query}</span>
                            </div>
                            <div className="flex justify-between items-center px-5 py-4">
                                <span className="text-slate-400 text-sm font-medium">Confidence Score</span>
                                <span className="text-indigo-400 text-sm font-bold bg-indigo-500/10 px-2 py-1 rounded">{(data.confidence_score * 100).toFixed(1)}%</span>
                            </div>
                            <div className="flex justify-between items-center px-5 py-4">
                                <span className="text-slate-400 text-sm font-medium">Correction Passes</span>
                                <span className="text-slate-200 text-sm font-medium">{data.correction_attempts}</span>
                            </div>
                            <div className="flex justify-between items-center px-5 py-4">
                                <span className="text-slate-400 text-sm font-medium flex items-center gap-2"><DatabaseZap size={16} /> Tables Queried</span>
                                <span className="text-slate-200 text-sm font-medium">{data.tables_used?.join(", ") || "None"}</span>
                            </div>
                            <div className="flex justify-between items-center px-5 py-4">
                                <span className="text-slate-400 text-sm font-medium flex items-center gap-2"><Clock size={16} /> End-to-End Latency</span>
                                <span className="text-slate-200 text-sm font-medium">{data.latency_ms.toFixed(1)} ms</span>
                            </div>
                        </div>
                    </div>

                    <div>
                        <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-4">FAISS Schema Similarity Matches</div>
                        <div className="bg-white/5 border border-white/10 rounded-xl p-5 h-[280px]">
                            {similarityChartData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart layout="vertical" data={similarityChartData} margin={{ top: 0, right: 20, bottom: 0, left: 20 }}>
                                        <XAxis type="number" domain={[0, 100]} hide />
                                        <YAxis dataKey="table" type="category" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                        <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: 'rgba(255,255,255,0.1)', color: '#f1f5f9' }} />
                                        <Bar dataKey="score" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={20} />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="h-full flex items-center justify-center text-slate-500 text-sm">No schema matches returned</div>
                            )}
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
