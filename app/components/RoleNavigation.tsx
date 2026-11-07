
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    Droplets, LayoutDashboard, ClipboardList, Users,
    HeartPulse, LogOut, ShieldCheck, Hospital
} from "lucide-react";
import { getUser, logout, getDashboardPath } from "../lib/auth";

export default function RoleNavigation() {
    const router = useRouter();
    const user = getUser();

    if (!user) return null;

    const menus = {
        admin: [
            { label: "Overview", href: "/admin", icon: LayoutDashboard },
        ],
        donor: [
            { label: "Overview", href: "/donor", icon: LayoutDashboard },
        ],
        hospital: [
            { label: "Overview", href: "/hospital", icon: LayoutDashboard },
        ],
    };

    const roleIcon = {
        admin: ShieldCheck,
        donor: HeartPulse,
        hospital: Hospital,
    };

    const Icon = roleIcon[user.role];

    const handleLogout = () => {
        logout();
        router.replace("/login");
    };

    return (
        <header className="sticky top-0 z-40 border-b border-slate-700 bg-[#0f172a] px-5 py-4 text-white md:px-8">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
                <Link href={getDashboardPath(user.role)} className="flex items-center gap-3">
                    <span className="rounded-xl bg-rose-500/15 p-2 text-rose-400">
                        <Droplets size={24} />
                    </span>
                    <span>
                        <span className="block font-bold">BloodBridge</span>
                        <span className="block text-xs text-slate-400">AI Platform</span>
                    </span>
                </Link>

                <nav className="flex flex-wrap items-center gap-2">
                    {menus[user.role].map(item => {
                        const ItemIcon = item.icon;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className="flex items-center gap-2 rounded-lg bg-[#293449] px-3 py-2 text-sm text-white"
                            >
                                <ItemIcon size={16} />
                                {item.label}
                            </Link>
                        );
                    })}
                </nav>

                <div className="flex items-center gap-3">
                    <div className="hidden text-right sm:block">
                        <p className="text-sm font-semibold">{user.name}</p>
                        <p className="text-xs capitalize text-slate-400">{user.role}</p>
                    </div>
                    <span className="rounded-full bg-rose-500/15 p-2 text-rose-400">
                        <Icon size={19} />
                    </span>
                    <button
                        onClick={handleLogout}
                        className="flex items-center gap-2 rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"
                    >
                        <LogOut size={16} />
                        Logout
                    </button>
                </div>
            </div>
        </header>
    );
}
