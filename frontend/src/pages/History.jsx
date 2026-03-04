import { useState, useEffect } from "react";
import axios from "axios";
import { Trash2, CheckCircle2, XCircle } from "lucide-react";

export default function History() {
    const [history, setHistory] = useState({ items: [], total: 0 });
    const [pageSize, setPageSize] = useState(25);
    const [selectedIds, setSelectedIds] = useState(new Set());

    const fetchHistory = async () => {
        try {
            const res = await axios.get("/api/history", { params: { limit: pageSize, offset: 0 } });
            if (res.data) setHistory(res.data);
        } catch (err) {
            console.error("Failed to fetch history");
        }
    };

    useEffect(() => {
        fetchHistory();
    }, [pageSize]);

    const toggleSelect = (id) => {
        const next = new Set(selectedIds);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        setSelectedIds(next);
    };

    const toggleSelectAll = () => {
        if (selectedIds.size === history.items.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(history.items.map(i => i.id)));
        }
    };

    const clearAll = async () => {
        if (!window.confirm("Are you sure you want to permanently clear ALL history?")) return;
        try {
            await axios.delete("/api/history");
            setSelectedIds(new Set());
            fetchHistory();
        } catch (err) {
            alert("Failed to clear history");
        }
    };

    const deleteSelected = async () => {
        if (!window.confirm(`Delete ${selectedIds.size} selected items?`)) return;
        try {
            for (const id of selectedIds) {
                await axios.delete(`/api/history/${id}`).catch(() => { });
            }
            setSelectedIds(new Set());
            fetchHistory();
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div>
            <div className="mb-6 flex flex-col md:flex-row md:items-start justify-between border-b border-white/5 pb-5 gap-4">
                <div>
                    <h1 className="text-[1.7rem] font-extrabold text-slate-200 tracking-[-0.03em] mb-1">History</h1>
                    <p className="text-[0.83rem] text-slate-500 font-medium">Audit log of all past queries. Showing most recent queries first.</p>
                </div>
                <div className="flex items-center gap-3">
                    <select
                        value={pageSize}
                        onChange={e => setPageSize(Number(e.target.value))}
                        className="bg-slate-900 border border-white/10 text-slate-300 text-sm rounded-lg px-3 py-2 outline-none"
                    >
                        <option value={10}>10 Rows</option>
                        <option value={25}>25 Rows</option>
                        <option value={50}>50 Rows</option>
                        <option value={100}>100 Rows</option>
                    </select>
                    <button
                        onClick={clearAll}
                        className="bg-white/5 hover:bg-red-500/10 hover:text-red-400 border border-white/10 text-slate-400 px-4 py-2 rounded-lg text-sm font-semibold transition-colors flex items-center gap-2"
                    >
                        <Trash2 size={16} /> Clear All
                    </button>
                </div>
            </div>

            {selectedIds.size > 0 && (
                <div className="bg-indigo-500/10 border border-indigo-500/20 px-5 py-3 rounded-xl mb-4 flex items-center justify-between">
                    <span className="text-sm font-semibold text-indigo-300">{selectedIds.size} queries selected</span>
                    <button
                        onClick={deleteSelected}
                        className="px-4 py-1.5 bg-red-500 text-white rounded shadow-sm hover:bg-red-600 text-xs font-bold transition-colors"
                    >
                        Delete Selected (Irreversible)
                    </button>
                </div>
            )}

            {history.items.length === 0 ? (
                <div className="bg-white/5 border border-dashed border-white/10 rounded-xl p-10 mt-6 flex flex-col items-center text-slate-400">
                    No queries yet — try the Query Console!
                </div>
            ) : (
                <>
                    <p className="text-[0.7rem] text-slate-500 font-semibold tracking-[0.07em] uppercase mb-4">{history.total} total queries · showing latest {history.items.length}</p>
                    <div className="bg-[#0d121c] border border-white/5 rounded-xl overflow-hidden shadow-xl">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm whitespace-nowrap">
                                <thead className="bg-[#0f1420] text-slate-400 sticky top-0 border-b border-white/5 z-10">
                                    <tr>
                                        <th className="px-4 py-3 w-[40px]">
                                            <input
                                                type="checkbox"
                                                checked={selectedIds.size === history.items.length && history.items.length > 0}
                                                onChange={toggleSelectAll}
                                                className="rounded bg-slate-800 border-white/10 text-indigo-500 focus:ring-0 checked:bg-indigo-500"
                                            />
                                        </th>
                                        <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Time</th>
                                        <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase w-full">Query</th>
                                        <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Status</th>
                                        <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Conf.</th>
                                        <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Latency</th>
                                        <th className="px-4 py-3 font-semibold text-xs tracking-wider uppercase">Rows</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5 text-slate-300">
                                    {history.items.map(item => (
                                        <tr
                                            key={item.id}
                                            className={`hover:bg-white/[0.02] transition-colors cursor-pointer ${selectedIds.has(item.id) ? 'bg-indigo-500/5' : ''}`}
                                            onClick={() => toggleSelect(item.id)}
                                        >
                                            <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedIds.has(item.id)}
                                                    onChange={() => toggleSelect(item.id)}
                                                    className="rounded bg-slate-800 border-white/10 text-indigo-500 focus:ring-0"
                                                />
                                            </td>
                                            <td className="px-4 py-3 font-mono text-[0.75rem] text-slate-500">{item.timestamp.substring(0, 19).replace('T', ' ')}</td>
                                            <td className="px-4 py-3 truncate max-w-[300px]" title={item.nl_query}>{item.nl_query}</td>
                                            <td className="px-4 py-3">
                                                {item.execution_success ?
                                                    <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md w-max text-xs font-semibold"><CheckCircle2 size={14} /> Success</div> :
                                                    <div className="flex items-center gap-1.5 text-red-400 bg-red-500/10 px-2 py-0.5 rounded-md w-max text-xs font-semibold"><XCircle size={14} /> Failed</div>
                                                }
                                            </td>
                                            <td className="px-4 py-3 font-mono text-xs">{item.confidence_score ? `${(item.confidence_score * 100).toFixed(0)}%` : '—'}</td>
                                            <td className="px-4 py-3 font-mono text-xs">{item.latency_ms ? `${item.latency_ms.toFixed(0)} ms` : '—'}</td>
                                            <td className="px-4 py-3 font-mono text-xs text-slate-400">{item.row_count ?? '—'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
