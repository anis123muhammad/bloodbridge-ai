
"use client";

import Link from "next/link";

export default function UnauthorizedPage() {
    return (
        <main className="flex min-h-screen items-center justify-center bg-[#020617] px-4 text-white">
            <div className="max-w-md rounded-2xl border border-slate-700 bg-[#0f172a] p-8 text-center">
                <h1 className="text-3xl font-bold text-rose-400">Access Denied</h1>
                <p className="mt-3 text-slate-400">
                    You do not have permission to access this dashboard.
                </p>
                <Link
                    href="/login"
                    className="mt-6 inline-block rounded-xl bg-[#f43f5e] px-6 py-3 font-semibold text-white"
                >
                    Return to Login
                </Link>
            </div>
        </main>
    );
}
