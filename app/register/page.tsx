
"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Droplets } from "lucide-react";
import { getDashboardPath, saveUser, type UserRole } from "../lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export default function RegisterPage() {
    const router = useRouter();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState<UserRole>("donor");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (!name.trim() || !email.trim() || !password) {
            setError("Please complete all fields.");
            return;
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            setError("Enter a valid email address.");
            return;
        }

        if (password.length < 8) {
            setError("Password must contain at least 8 characters.");
            return;
        }

        if (!API_URL) {
            setError("Registration requires the backend. Use Demo Access on the login screen.");
            return;
        }

        setLoading(true);

        try {
            const response = await fetch(`${API_URL}/api/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password, role }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || data.detail || "Registration failed.");
            }

            const user = data.user || data;

            if (!["admin", "donor", "hospital"].includes(user.role)) {
                throw new Error("Registration returned an invalid role.");
            }

            saveUser({
                name: user.name || user.full_name || name,
                email: user.email || email,
                role: user.role,
                token: data.token || data.access_token,
            });

            router.push(getDashboardPath(user.role));
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to register.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="flex min-h-screen items-center justify-center bg-[#020617] px-4 py-10 text-white">
            <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-[#0f172a] p-8">
                <div className="mb-6 text-center">
                    <div className="mx-auto mb-3 inline-flex rounded-2xl bg-rose-500/15 p-3 text-rose-400">
                        <Droplets size={30} />
                    </div>
                    <h1 className="text-2xl font-bold">Create Account</h1>
                    <p className="mt-2 text-sm text-slate-400">Join BloodBridge AI</p>
                </div>

                <form onSubmit={handleRegister} className="space-y-4">
                    <label className="block text-sm">
                        Full Name
                        <input
                            value={name}
                            onChange={e => setName(e.target.value)}
                            className="mt-2 w-full rounded-xl border border-slate-700 bg-[#020617] p-3 outline-none focus:border-rose-500"
                            placeholder="Your full name"
                        />
                    </label>

                    <label className="block text-sm">
                        Email
                        <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            className="mt-2 w-full rounded-xl border border-slate-700 bg-[#020617] p-3 outline-none focus:border-rose-500"
                            placeholder="name@example.com"
                        />
                    </label>

                    <label className="block text-sm">
                        Password
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            className="mt-2 w-full rounded-xl border border-slate-700 bg-[#020617] p-3 outline-none focus:border-rose-500"
                            placeholder="At least 8 characters"
                        />
                    </label>

                    <label className="block text-sm">
                        Account Role
                        <select
                            value={role}
                            onChange={e => setRole(e.target.value as UserRole)}
                            className="mt-2 w-full rounded-xl border border-slate-700 bg-[#020617] p-3 outline-none"
                        >
                            <option value="donor">Donor</option>
                            <option value="hospital">Hospital</option>
                            <option value="admin">Admin</option>
                        </select>
                    </label>

                    {error && (
                        <p role="alert" className="rounded-lg bg-rose-500/10 p-3 text-sm text-rose-400">
                            {error}
                        </p>
                    )}

                    <button
                        disabled={loading}
                        className="w-full rounded-xl bg-[#f43f5e] py-3 font-semibold text-white hover:bg-rose-600 disabled:opacity-60"
                    >
                        {loading ? "Creating account..." : "Register"}
                    </button>
                </form>

                <p className="mt-6 text-center text-sm text-slate-400">
                    Already registered?{" "}
                    <Link href="/login" className="font-semibold text-rose-400">
                        Sign in
                    </Link>
                </p>
            </div>
        </main>
    );
}
