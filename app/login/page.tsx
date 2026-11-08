
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Droplets, Mail, Lock, ArrowRight, HeartPulse } from "lucide-react";
import {
    saveUser, getDashboardPath, API_BASE_URL, type UserRole
} from "../lib/auth";

const API_URL = API_BASE_URL;

export default function LoginPage() {
    const router = useRouter();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState<UserRole>("hospital");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const demoLogin = (demoRole: UserRole) => {
        const demoUsers = {
            admin: { name: "Admin User", email: "admin@bloodbridge.demo" },
            donor: { name: "Ali Ahmed", email: "donor@bloodbridge.demo" },
            hospital: { name: "Civil Hospital", email: "hospital@bloodbridge.demo" },
        };

        saveUser({ ...demoUsers[demoRole], role: demoRole });
        router.push(getDashboardPath(demoRole));
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (!email.trim() || !password) {
            setError("Please enter your email and password.");
            return;
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            setError("Please enter a valid email address.");
            return;
        }

        setLoading(true);

        try {
            if (!API_URL) {
                setError("Backend is not connected. Please use Demo Access.");
                return;
            }

            const response = await fetch(`${API_URL}/api/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password, role }),
            });

            const resData = await response.json();

            if (!response.ok) {
                throw new Error(resData.message || resData.detail || "Login failed.");
            }

            // Support both wrapped { success, data: { access_token, me: { user } } } and raw payload
            const inner = resData.data || resData;
            const token = inner.access_token || inner.token || resData.token;
            const user = inner.me?.user || inner.user || inner;

            if (!user?.role || !["admin", "donor", "hospital"].includes(user.role)) {
                throw new Error("The server returned an invalid user role.");
            }

            if (user.role !== role) {
                throw new Error(`This account is registered as a ${user.role}, not ${role}.`);
            }

            saveUser({
                name: user.name || user.full_name || email,
                email: user.email || email,
                role: user.role,
                token: token,
            });

            router.push(getDashboardPath(user.role));
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to login.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex min-h-screen items-center justify-center bg-[#020617] px-4 py-10 text-white">
            <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-[#0f172a] p-7 shadow-2xl md:p-9">
                <div className="mb-7 text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-500/15 text-rose-400">
                        <Droplets size={30} />
                    </div>
                    <h1 className="text-2xl font-bold">Welcome to BloodBridge</h1>
                    <p className="mt-2 text-sm text-slate-400">
                        Sign in to access your dashboard.
                    </p>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                    <label className="block text-sm font-medium">
                        Email Address
                        <span className="mt-2 flex items-center gap-2 rounded-xl border border-slate-700 bg-[#020617] px-3">
                            <Mail size={17} className="text-slate-400" />
                            <input
                                type="email"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                placeholder="Enter your email"
                                className="w-full bg-transparent py-3 text-white outline-none"
                            />
                        </span>
                    </label>

                    <label className="block text-sm font-medium">
                        Password
                        <span className="mt-2 flex items-center gap-2 rounded-xl border border-slate-700 bg-[#020617] px-3">
                            <Lock size={17} className="text-slate-400" />
                            <input
                                type="password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                className="w-full bg-transparent py-3 text-white outline-none"
                            />
                        </span>
                    </label>

                    <label className="block text-sm font-medium">
                        Login as
                        <select
                            value={role}
                            onChange={e => setRole(e.target.value as UserRole)}
                            className="mt-2 w-full rounded-xl border border-slate-700 bg-[#020617] p-3 text-white outline-none"
                        >
                            <option value="hospital">Hospital</option>
                            <option value="donor">Donor</option>
                            <option value="admin">Admin</option>
                        </select>
                    </label>

                    {error && (
                        <p role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-400">
                            {error}
                        </p>
                    )}

                    <button
                        disabled={loading}
                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#f43f5e] py-3 font-semibold text-white hover:bg-rose-600 disabled:opacity-60"
                    >
                        {loading ? "Signing in..." : "Sign In"}
                        {!loading && <ArrowRight size={18} />}
                    </button>
                </form>

                <div className="my-6 flex items-center gap-3">
                    <div className="h-px flex-1 bg-slate-700" />
                    <span className="text-xs text-slate-500">OR DEMO ACCESS</span>
                    <div className="h-px flex-1 bg-slate-700" />
                </div>

                <div className="grid grid-cols-3 gap-2">
                    {(["hospital", "donor", "admin"] as UserRole[]).map(item => (
                        <button
                            key={item}
                            onClick={() => demoLogin(item)}
                            className="rounded-xl border border-slate-700 px-2 py-3 text-xs font-semibold capitalize text-slate-200 hover:border-rose-500 hover:bg-rose-500/10"
                        >
                            {item}
                        </button>
                    ))}
                </div>

                <p className="mt-6 text-center text-sm text-slate-400">
                    New to BloodBridge?{" "}
                    <Link href="/register" className="font-semibold text-rose-400 hover:underline">
                        Create account
                    </Link>
                </p>
            </div>
        </main>
    );
}
