import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { Terminal, Lightbulb, PieChart, RotateCcw, CloudUpload, ChevronDown, ChevronRight, Table2 } from "lucide-react";

export default function Sidebar() {
    const [health, setHealth] = useState({ db_connected: false, faiss_ready: false, schema_loaded: 0 });
    const [isHovered, setIsHovered] = useState(false);
    const [showColumns, setShowColumns] = useState(false);
    const [schemaMap, setSchemaMap] = useState({});
    const location = useLocation();

    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const res = await axios.get("/health");
                setHealth(res.data);
            } catch (err) {
                console.error("Health check failed", err);
            }
        };
        fetchHealth();
        const interval = setInterval(fetchHealth, 10000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const fetchSchema = async () => {
            try {
                const res = await axios.get("/api/schema");
                if (res.data) setSchemaMap(res.data);
            } catch (err) {
                console.error("Failed to fetch schema for sidebar");
            }
        };
        fetchSchema();
        const interval = setInterval(fetchSchema, 15000);
        return () => clearInterval(interval);
    }, []);

    const navItems = [
        { name: "Query Console", path: "/", icon: <Terminal size={20} /> },
        { name: "Transparency", path: "/transparency", icon: <Lightbulb size={20} /> },
        { name: "Analytics", path: "/analytics", icon: <PieChart size={20} /> },
        { name: "History", path: "/history", icon: <RotateCcw size={20} /> },
        { name: "Data Upload", path: "/upload", icon: <CloudUpload size={20} /> },
    ];

    const sidebarWidth = isHovered ? "w-[336px]" : "w-[75px]";

    return (
        <div
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className={`fixed top-0 left-0 h-screen ${sidebarWidth} transition-all duration-300 ease-in-out z-50 overflow-hidden bg-gradient-to-b from-[#0f1420] to-[#0b0f1a] border-r border-[#6378ff1f] flex flex-col`}
        >
            {/* Logo */}
            <div className="flex-none p-[1.4rem_1.2rem_1rem] w-[336px] flex items-center gap-4">
                <div className="w-9 h-9 rounded-[10px] bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-[0_4px_12px_rgba(99,102,241,0.35)] shrink-0 text-white">
                    ⚡
                </div>
                <div className={`transition-opacity duration-300 ${isHovered ? "opacity-100 delay-100" : "opacity-0 invisible"}`}>
                    <div className="font-extrabold text-[1.05rem] text-slate-200 tracking-[-0.01em] leading-tight">
                        NL2SQL
                    </div>
                    <div className="text-[0.7rem] text-slate-500 font-semibold tracking-[0.05em] leading-tight">
                        INTELLIGENCE
                    </div>
                </div>
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 w-[336px] px-3 mt-6 flex flex-col min-h-0">
                <div className="flex-1">
                    {navItems.map((item) => {
                        const isActive = location.pathname === item.path;
                        return (
                            <Link
                                key={item.name}
                                to={item.path}
                                className={`flex items-center gap-4 px-[16px] py-[10px] mb-1 rounded-[10px] transition-all duration-200 font-medium text-[0.88rem] ${isActive
                                    ? "bg-[#6378ff26] text-indigo-400"
                                    : "text-slate-400 hover:bg-[#6378ff14] hover:text-indigo-200"
                                    }`}
                            >
                                <div className="shrink-0">{item.icon}</div>
                                <span className={`transition-opacity duration-300 whitespace-nowrap ${isHovered ? "opacity-100 delay-100" : "opacity-0"}`}>
                                    {item.name}
                                </span>
                            </Link>
                        );
                    })}
                </div>

                {/* Show Columns Expander */}
                <div className={`transition-opacity duration-300 mt-2 ${isHovered ? "opacity-100" : "opacity-0"}`}>
                    <button
                        onClick={() => setShowColumns((v) => !v)}
                        className="w-full flex items-center justify-between px-4 py-2.5 rounded-[10px] text-slate-400 hover:bg-[#6378ff14] hover:text-indigo-200 transition-colors"
                    >
                        <div className="flex items-center gap-3 text-[0.88rem] font-medium">
                            <Table2 size={18} className="shrink-0" />
                            <span>Show Columns</span>
                        </div>
                        {showColumns ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>

                    {showColumns && (
                        <div className="ml-3 mt-1 max-h-[280px] overflow-y-auto custom-scrollbar pr-1">
                            {Object.keys(schemaMap).length === 0 ? (
                                <p className="text-[0.75rem] text-slate-600 px-4 py-2 italic">No tables indexed yet</p>
                            ) : (
                                Object.entries(schemaMap).map(([tableName, columns]) => (
                                    <div key={tableName} className="mb-3">
                                        <div className="flex items-center gap-2 px-4 py-1">
                                            <div className="w-1.5 h-1.5 rounded-full bg-indigo-400/80 shrink-0"></div>
                                            <span className="text-[0.8rem] font-bold text-indigo-300 truncate">{tableName}</span>
                                        </div>
                                        <div className="ml-8 space-y-0.5">
                                            {columns.map((col, i) => (
                                                <div key={i} className="flex items-center justify-between pr-2">
                                                    <span className="text-[0.72rem] text-slate-400 font-mono truncate">{col.name}</span>
                                                    <span className="text-[0.65rem] text-slate-600 font-semibold ml-2 shrink-0">{col.type}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </nav>

            {/* System Status Box */}
            <div className={`flex-none w-[336px] p-[1.2rem_1.4rem] bg-[#0f1420f0] border-t border-white/5 backdrop-blur-md transition-opacity duration-300 ${isHovered ? "opacity-100" : "opacity-0"}`}>
                <div className="text-[0.75rem] text-slate-500 font-semibold tracking-[0.1em] mb-2 uppercase">
                    SYSTEM
                </div>
                <div className="flex flex-col gap-[5px]">
                    <div className="flex justify-between items-center">
                        <span className="text-[0.82rem] text-slate-400 font-medium">Engine</span>
                        <span className={`px-3 py-[3px] rounded-full text-[0.73rem] font-semibold tracking-[0.03em] border ${health.db_connected ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"}`}>
                            {health.db_connected ? "● PASSED" : "● FAILED"}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-[0.82rem] text-slate-400 font-medium">Vector DB</span>
                        <span className={`px-3 py-[3px] rounded-full text-[0.73rem] font-semibold tracking-[0.03em] border ${health.faiss_ready ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"}`}>
                            {health.faiss_ready ? "● PASSED" : "● FAILED"}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-[0.82rem] text-slate-400 font-medium">Schema</span>
                        <span className="px-3 py-[3px] rounded-full text-[0.73rem] font-semibold tracking-[0.03em] border bg-blue-500/10 text-blue-500 border-blue-500/20">
                            📋 {health.schema_loaded} tables indexed
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
