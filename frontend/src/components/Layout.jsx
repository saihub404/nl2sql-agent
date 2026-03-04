import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
    return (
        <div className="flex min-h-screen relative overflow-hidden">
            <Sidebar />
            <div className="flex-1 ml-[75px] w-[calc(100%-75px)] min-h-screen transition-all duration-300 overflow-y-auto">
                <main className="px-8 pt-4 pb-12 max-w-[1400px] mx-auto min-h-full">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
