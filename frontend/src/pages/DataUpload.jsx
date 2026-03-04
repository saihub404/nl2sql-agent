import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { UploadCloud, FileText, Trash2, CheckCircle2, AlertCircle, Loader2, FolderOpen } from "lucide-react";

export default function DataUpload() {
    const [file, setFile] = useState(null);
    const [uploadState, setUploadState] = useState("idle"); // idle, uploading, preview, ingesting, success, error
    const [uploadData, setUploadData] = useState(null);
    const [errorMsg, setErrorMsg] = useState("");
    const [progress, setProgress] = useState({ pct: 0, rows: 0 });
    const [datasets, setDatasets] = useState([]);

    const fileInputRef = useRef(null);

    const fetchDatasets = async () => {
        try {
            const res = await axios.get("/api/datasets");
            if (res.data && res.data.datasets) {
                setDatasets(res.data.datasets);
            }
        } catch (err) {
            console.error("Failed to fetch datasets", err);
        }
    };

    useEffect(() => {
        fetchDatasets();
        const interval = setInterval(fetchDatasets, 10000); // refresh list locally
        return () => clearInterval(interval);
    }, []);

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setUploadState("idle");
            setUploadData(null);
            setErrorMsg("");
        }
    };

    const handleUploadSubmit = async () => {
        if (!file) return;
        setUploadState("uploading");
        setErrorMsg("");

        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await axios.post("/api/upload", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            setUploadData(res.data);
            setUploadState("preview");
            pollProgress(res.data.dataset_id);
        } catch (err) {
            setUploadState("error");
            setErrorMsg(err.response?.data?.detail || "Upload failed due to a network error.");
        }
    };

    const pollProgress = (datasetId) => {
        setUploadState("ingesting");

        const interval = setInterval(async () => {
            try {
                const res = await axios.get(`/api/upload/progress/${datasetId}`);
                const data = res.data;

                setProgress({ pct: data.pct, rows: data.rows_ingested });

                if (data.status === "ready") {
                    clearInterval(interval);
                    setUploadState("success");
                    fetchDatasets();
                    setTimeout(() => {
                        setUploadState("idle");
                        setFile(null);
                        setUploadData(null);
                        if (fileInputRef.current) fileInputRef.current.value = "";
                    }, 4000);
                } else if (data.status === "error") {
                    clearInterval(interval);
                    setUploadState("error");
                    setErrorMsg(data.error_message || "Ingestion failed during processing.");
                }
            } catch (err) {
                clearInterval(interval);
                setUploadState("error");
                setErrorMsg("Lost connection to backend during ingestion monitoring.");
            }
        }, 1000);
    };

    const handleDelete = async (tableName) => {
        if (!window.confirm(`Delete ${tableName}?`)) return;
        try {
            await axios.delete(`/api/datasets/${tableName}`);
            fetchDatasets();
        } catch (err) {
            alert("Delete failed: " + (err.response?.data?.detail || err.message));
        }
    };

    return (
        <div>
            <div className="mb-6">
                <h1 className="text-[1.7rem] font-extrabold text-slate-200 tracking-[-0.03em] mb-1">Data Upload</h1>
                <p className="text-[0.83rem] text-slate-500 font-medium">Upload CSV or Parquet, infer schema, and query instantly</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
                <div className="lg:col-span-2 space-y-4">
                    <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase">Upload Dataset</div>

                    <div className="bg-white/5 border border-white/10 rounded-xl p-6 flex flex-col items-center justify-center min-h-[220px] relative">
                        {uploadState === "idle" || uploadState === "error" ? (
                            <>
                                <UploadCloud size={48} className="text-indigo-400 mb-4 opacity-70" />
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    accept=".csv,.tsv,.parquet"
                                    onChange={handleFileChange}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                />
                                <p className="text-slate-300 font-medium text-sm">Drag and drop file here, or click to browse</p>
                                <p className="text-slate-500 text-xs mt-2">Supports .csv, .tsv, .parquet (Max 2GB)</p>

                                {file && (
                                    <div className="mt-6 w-full flex items-center justify-between bg-indigo-500/10 border border-indigo-500/20 px-4 py-3 rounded-lg z-10">
                                        <div className="flex items-center gap-3">
                                            <FileText size={18} className="text-indigo-400" />
                                            <span className="text-sm font-medium text-indigo-200">{file.name}</span>
                                        </div>
                                        <button
                                            onClick={handleUploadSubmit}
                                            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-md transition-colors"
                                        >
                                            Process & Ingest
                                        </button>
                                    </div>
                                )}
                                {uploadState === "error" && (
                                    <div className="mt-4 w-full flex items-center gap-2 text-red-400 bg-red-500/10 px-3 py-2 rounded-md text-xs font-medium border border-red-500/20">
                                        <AlertCircle size={14} /> {errorMsg}
                                    </div>
                                )}
                            </>
                        ) : uploadState === "uploading" ? (
                            <div className="flex flex-col items-center gap-4 py-8">
                                <Loader2 className="animate-spin text-indigo-400" size={32} />
                                <p className="text-slate-300 text-sm font-medium">Uploading and inferring schema...</p>
                            </div>
                        ) : uploadState === "ingesting" || uploadState === "preview" ? (
                            <div className="w-full space-y-4">
                                <div className="flex justify-between items-end">
                                    <div>
                                        <h3 className="text-slate-200 font-semibold">{uploadData?.table_name || 'Processing...'}</h3>
                                        <p className="text-slate-400 text-xs">{(file?.size / (1024 * 1024)).toFixed(1)} MB • {uploadData?.row_estimate?.toLocaleString() || 0} rows estimated</p>
                                    </div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg border border-white/5 p-4 max-h-[160px] overflow-y-auto">
                                    <table className="w-full text-left text-xs text-slate-300">
                                        <thead className="text-slate-500 sticky top-0 bg-slate-900/95 pb-2">
                                            <tr>
                                                <th className="font-semibold py-1">Original Name</th>
                                                <th className="font-semibold py-1">Postgres Name</th>
                                                <th className="font-semibold py-1">Type</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {uploadData?.inferred_columns?.map(col => (
                                                <tr key={col.name}>
                                                    <td className="py-2">{col.original_name}</td>
                                                    <td className="py-2 font-mono text-indigo-300">{col.name}</td>
                                                    <td className="py-2">{col.pg_type} {col.nullable ? ' (null)' : ''}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                <div className="space-y-1 mt-4">
                                    <div className="flex justify-between text-xs font-medium">
                                        <span className="text-indigo-300">Ingesting rows...</span>
                                        <span className="text-slate-300">{progress.pct.toFixed(1)}%</span>
                                    </div>
                                    <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-indigo-500 transition-all duration-300 ease-out"
                                            style={{ width: `${progress.pct}%` }}
                                        />
                                    </div>
                                    <p className="text-[0.65rem] text-slate-500 text-right">{progress.rows.toLocaleString()} rows ingested</p>
                                </div>
                            </div>
                        ) : uploadState === "success" ? (
                            <div className="flex flex-col items-center gap-3 py-6">
                                <CheckCircle2 className="text-green-500" size={48} />
                                <h3 className="text-green-400 font-semibold text-lg">Ingestion Complete!</h3>
                                <p className="text-slate-400 text-sm">Dataset is marked as ready for querying.</p>
                            </div>
                        ) : null}
                    </div>
                </div>

                <div>
                    <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-4">Guidelines</div>
                    <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-xl p-5 text-sm text-slate-400 space-y-4">
                        <div>
                            <span className="font-semibold text-indigo-300 block mb-1">Supported Formats</span>
                            CSV, TSV, Parquet
                        </div>
                        <div>
                            <span className="font-semibold text-indigo-300 block mb-1">Size Limits</span>
                            Max size: 2 GB<br />
                            Target speed: ~300K rows/s
                        </div>
                        <div>
                            <span className="font-semibold text-green-400/80 block mb-1">Pro Tip</span>
                            Use Parquet for datasets over 1 million rows. It's 5-10x faster to read and uses fraction of the disk size!
                        </div>
                    </div>
                </div>
            </div>

            <div className="text-[0.75rem] text-slate-400 font-semibold tracking-[0.07em] uppercase mb-4">Uploaded Datasets</div>
            {datasets.length === 0 ? (
                <div className="text-center py-12 bg-white/[0.02] border border-dashed border-white/[0.06] rounded-xl text-slate-500">
                    <FolderOpen size={32} className="mx-auto mb-3 opacity-50" />
                    <p className="font-medium">No datasets available</p>
                </div>
            ) : (
                <div className="grid gap-3">
                    {datasets.map(ds => (
                        <div key={ds.table_name} className="flex items-center justify-between p-4 bg-white/[0.02] border border-white/5 rounded-xl hover:bg-white/[0.04] transition-colors">
                            <div>
                                <div className="flex items-center justify-between gap-3 mb-1">
                                    {ds.status === 'ready' ? <CheckCircle2 size={16} className="text-green-500" /> : <Loader2 size={16} className="text-yellow-500 animate-spin" />}
                                    <span className="font-semibold text-slate-200 text-sm">{ds.table_name}</span>
                                </div>
                                <p className="text-xs text-slate-500 pl-7">{ds.original_filename} • {(ds.file_size_mb || 0).toFixed(1)} MB • {ds.row_count ? ds.row_count.toLocaleString() : (ds.rows_ingested || 0).toLocaleString()} rows • {ds.column_count || '?'} cols</p>
                            </div>
                            <div className="flex items-center gap-4">
                                <span className={`px-2 py-1 text-[0.65rem] font-bold rounded-md uppercase tracking-wider ${ds.status === 'ready' ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20'}`}>
                                    {ds.status}
                                </span>
                                <button onClick={() => handleDelete(ds.table_name)} className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-md transition-colors" title="Delete Dataset">
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
