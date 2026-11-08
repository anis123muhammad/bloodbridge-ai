
"use client";

import { useCallback, useEffect, useState } from "react";
import { getAuthHeaders } from "../lib/auth";
import {
    Droplets, LayoutDashboard, FilePlus2, ClipboardList,
    Users, Bell, Moon, Sun, RefreshCw, MapPin,
    CalendarDays, Clock, CheckCircle2, AlertTriangle,
    Check, X, HeartPulse, Activity, ShieldCheck
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

type RequestStatus = "Pending" | "Matching" | "Matched" | "Completed" | "Cancelled";

type DonorMatch = {
    id: string;
    name: string;
    bloodGroup: string;
    location: string;
    distance: string;
    explanation: string;
    score: number;
    status: "Proposed" | "Approved" | "Rejected";
};

type BloodRequest = {
    id: string;
    bloodGroup: string;
    units: number;
    location: string;
    urgency: string;
    deadline: string;
    status: RequestStatus;
    createdAt: string;
    matches: DonorMatch[];
    timeline: { label: string; time: string; done: boolean }[];
};

const demoRequests: BloodRequest[] = [
    {
        id: "REQ-2026-001",
        bloodGroup: "O+",
        units: 3,
        location: "Civil Hospital, Hyderabad",
        urgency: "Critical",
        deadline: "2026-11-09T10:00",
        status: "Matching",
        createdAt: "Nov 8, 2026",
        matches: [
            {
                id: "DNR-101",
                name: "Ali Ahmed",
                bloodGroup: "O+",
                location: "Latifabad, Hyderabad",
                distance: "2.4 km",
                explanation: "Exact blood group match, nearby location, and donor is available.",
                score: 96,
                status: "Proposed"
            },
            {
                id: "DNR-102",
                name: "Sara Khan",
                bloodGroup: "O+",
                location: "Qasimabad, Hyderabad",
                distance: "4.1 km",
                explanation: "Exact blood group match and availability confirmed in demo data.",
                score: 91,
                status: "Proposed"
            }
        ],
        timeline: [
            { label: "Blood request submitted", time: "Today, 09:00 AM", done: true },
            { label: "Donor matching started", time: "Today, 09:02 AM", done: true },
            { label: "Waiting for hospital approval", time: "In progress", done: false },
            { label: "Invitations sent to donors", time: "Pending approval", done: false }
        ]
    },
    {
        id: "REQ-2026-002",
        bloodGroup: "B+",
        units: 2,
        location: "Liaquat University Hospital, Jamshoro",
        urgency: "High",
        deadline: "2026-11-10T14:00",
        status: "Matched",
        createdAt: "Nov 7, 2026",
        matches: [
            {
                id: "DNR-103",
                name: "Ahmed Raza",
                bloodGroup: "B+",
                location: "Jamshoro",
                distance: "3.0 km",
                explanation: "Compatible blood group and donor is close to the hospital.",
                score: 89,
                status: "Approved"
            }
        ],
        timeline: [
            { label: "Blood request submitted", time: "Nov 7, 10:00 AM", done: true },
            { label: "Donor matching completed", time: "Nov 7, 10:04 AM", done: true },
            { label: "Donor invitation approved", time: "Nov 7, 10:10 AM", done: true },
            { label: "Awaiting donation", time: "In progress", done: false }
        ]
    }
];

const initialForm = {
    bloodGroup: "O+",
    units: "2",
    location: "Civil Hospital, Hyderabad",
    urgency: "High",
    deadline: ""
};

const urgencyColor = (urgency: string) => {
    if (urgency === "Critical") return "bg-rose-500/10 text-rose-500";
    if (urgency === "High") return "bg-orange-500/10 text-orange-500";
    return "bg-blue-500/10 text-blue-500";
};

export default function HospitalDashboard() {
    const [soft, setSoft] = useState(false);
    const [requests, setRequests] = useState<BloodRequest[]>(demoRequests);
    const [form, setForm] = useState(initialForm);
    const [loading, setLoading] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");
    const [selected, setSelected] = useState<string | null>("REQ-2026-001");
    const [activeNav, setActiveNav] = useState("Overview");

    const bg = soft ? "#f1f5f9" : "#020617";
    const card = soft ? "#ffffff" : "#0f172a";
    const text = soft ? "#0f172a" : "#f8fafc";
    const muted = soft ? "#64748b" : "#94a3b8";
    const border = soft ? "#e2e8f0" : "#273449";
    const red = "#f43f5e";

    const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
        const authHeaders = getAuthHeaders();
        const response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...authHeaders,
                ...options?.headers
            }
        });

        if (!response.ok) {
            const errBody = await response.json().catch(() => ({}));
            const msg = errBody.message || (errBody.errors && errBody.errors[0]?.message) || `Request failed (${response.status})`;
            throw new Error(msg);
        }

        const json = await response.json();
        return json.data !== undefined ? json.data : json;
    }, []);

    const mapBackendRequest = (r: any): BloodRequest => ({
        id: r.id,
        bloodGroup: r.blood_group || r.bloodGroup || "O+",
        units: r.units_requested || r.units || 1,
        location: r.location || "City",
        urgency: r.urgency ? r.urgency.charAt(0).toUpperCase() + r.urgency.slice(1) : "Normal",
        deadline: r.deadline || "",
        status: r.status === "awaiting_approval" ? "Matching" : (r.status === "inviting_donors" ? "Matched" : (r.status === "fulfilled" ? "Completed" : "Pending")),
        createdAt: r.created_at ? new Date(r.created_at).toLocaleDateString() : (r.createdAt || ""),
        matches: (r.matches || []).map((m: any) => ({
            id: m.id || m.donor_id,
            name: m.donor_name || m.name || "Donor",
            bloodGroup: m.blood_group || m.bloodGroup || r.blood_group,
            location: m.city || m.location || "Nearby",
            distance: m.distance_km != null ? `${m.distance_km} km` : (m.distance || "2.5 km"),
            explanation: Array.isArray(m.match_reasons) ? m.match_reasons.join(". ") : (m.explanation || "Eligible donor match"),
            score: m.match_score || m.score || 85,
            status: m.status === "approved" ? "Approved" : (m.status === "rejected" ? "Rejected" : "Proposed")
        })),
        timeline: (r.timeline || []).map((t: any) => ({
            label: t.title || t.label || "Action",
            time: t.at ? new Date(t.at).toLocaleTimeString() : (t.time || ""),
            done: t.status === "completed" || t.done === true
        }))
    });

    const loadRequests = useCallback(async () => {
        if (!API_URL) return;

        setLoading(true);
        setError("");

        try {
            const data = await apiFetch("/api/requests");
            const rawList = Array.isArray(data) ? data : (data.items || data.requests || []);
            const mapped = rawList.map(mapBackendRequest);
            setRequests(mapped);
            if (mapped.length > 0 && (!selected || !mapped.find((m: BloodRequest) => m.id === selected))) {
                setSelected(mapped[0].id);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Could not load requests.");
        } finally {
            setLoading(false);
        }
    }, [apiFetch, selected]);

    useEffect(() => {
        loadRequests();
    }, [loadRequests]);

    const submitRequest = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setError("");
        setSuccess("");
        setSubmitting(true);

        const deadlineIso = form.deadline 
            ? new Date(form.deadline).toISOString() 
            : new Date(Date.now() + 24 * 3600 * 1000).toISOString();

        const payload = {
            title: `Blood Request for ${form.bloodGroup}`,
            blood_group: form.bloodGroup,
            units_requested: Number(form.units),
            location: form.location,
            urgency: form.urgency.toLowerCase(),
            deadline: deadlineIso,
            auto_run_workflow: true
        };

        try {
            if (API_URL) {
                await apiFetch("/api/requests", {
                    method: "POST",
                    body: JSON.stringify(payload)
                });
                await loadRequests();
                setSuccess("Blood request submitted and AI matching workflow initiated.");
            } else {
                const newRequest: BloodRequest = {
                    id: `REQ-${Date.now()}`,
                    bloodGroup: form.bloodGroup,
                    units: Number(form.units),
                    location: form.location,
                    urgency: form.urgency,
                    deadline: form.deadline,
                    status: "Pending",
                    createdAt: new Date().toLocaleString(),
                    matches: [],
                    timeline: [
                        {
                            label: "Blood request submitted",
                            time: new Date().toLocaleString(),
                            done: true
                        },
                        {
                            label: "Donor matching started",
                            time: "Waiting",
                            done: false
                        }
                    ]
                };

                setRequests(previous => [newRequest, ...previous]);
                setSelected(newRequest.id);
                setSuccess("Demo request submitted successfully.");
            }

            setForm(initialForm);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to submit request.");
        } finally {
            setSubmitting(false);
        }
    };

    const approveMatch = async (
        requestId: string,
        matchId: string,
        approved: boolean
    ) => {
        setError("");
        setSuccess("");

        try {
            if (API_URL) {
                await apiFetch(`/api/requests/${requestId}/approve-matches`, {
                    method: "POST",
                    body: JSON.stringify({
                        approve_ids: approved ? [matchId] : [],
                        reject_ids: approved ? [] : [matchId]
                    })
                });
                await loadRequests();
            } else {
                setRequests(previous =>
                    previous.map(request =>
                        request.id === requestId
                            ? {
                                ...request,
                                matches: request.matches.map(match =>
                                    match.id === matchId
                                        ? { ...match, status: approved ? "Approved" : "Rejected" }
                                        : match
                                )
                            }
                            : request
                    )
                );
            }

            setSuccess(
                approved
                    ? "Donor match approved. Coordination Agent created simulated invitation."
                    : "Donor match rejected."
            );
        } catch (err) {
            setError(err instanceof Error ? err.message : "Approval action failed.");
        }
    };

    const selectedRequest = requests.find(request => request.id === selected);

    const totalUnits = requests.reduce((sum, request) => sum + request.units, 0);
    const pendingCount = requests.filter(r => r.status === "Pending").length;
    const matchingCount = requests.filter(r => r.status === "Matching").length;
    const completedCount = requests.filter(r => r.status === "Completed").length;

    const panelStyle = {
        background: card,
        border: `1px solid ${border}`,
        borderRadius: "16px"
    };

    return (
        <div style={{ background: bg, color: text, minHeight: "100vh" }}>
            {/* NAVBAR */}
            <header
                className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-4 px-5 py-4 md:px-8"
                style={{ background: "#0f172a", borderBottom: "1px solid #273449" }}
            >
                <div className="flex items-center gap-3">
                    <div className="rounded-xl p-2" style={{ background: "#f43f5e20", color: red }}>
                        <Droplets size={25} />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-white">BloodBridge</h1>
                        <p className="text-xs text-slate-400">Hospital Portal</p>
                    </div>
                </div>

                <nav className="flex flex-wrap items-center gap-2">
                    {[
                        { name: "Overview", icon: LayoutDashboard },
                        { name: "New Request", icon: FilePlus2 },
                        { name: "Requests", icon: ClipboardList }
                    ].map(item => (
                        <button
                            key={item.name}
                            onClick={() => {
                                setActiveNav(item.name);
                                if (item.name === "New Request") {
                                    document.getElementById("request-form")?.scrollIntoView({ behavior: "smooth" });
                                }
                                if (item.name === "Requests") {
                                    document.getElementById("requests-list")?.scrollIntoView({ behavior: "smooth" });
                                }
                                if (item.name === "Overview") {
                                    window.scrollTo({ top: 0, behavior: "smooth" });
                                }
                            }}
                            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
                            style={{
                                background: activeNav === item.name ? "#293449" : "transparent",
                                color: activeNav === item.name ? "#fff" : "#94a3b8"
                            }}
                        >
                            <item.icon size={16} />
                            <span className="hidden sm:inline">{item.name}</span>
                        </button>
                    ))}
                </nav>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setSoft(!soft)}
                        className="rounded-lg p-2 text-slate-300 hover:bg-slate-700"
                        title="Toggle Dark and Soft mode"
                    >
                        {soft ? <Moon size={18} /> : <Sun size={18} />}
                    </button>
                    <button
                        onClick={loadRequests}
                        className="rounded-lg p-2 text-slate-300 hover:bg-slate-700"
                        title="Refresh requests"
                    >
                        <RefreshCw size={18} />
                    </button>
                    <div className="rounded-full p-2" style={{ background: "#f43f5e25", color: "#fb7185" }}>
                        <HeartPulse size={20} />
                    </div>
                </div>
            </header>

            <main className="mx-auto max-w-7xl space-y-6 px-4 py-7 md:px-8">
                {/* PAGE HEADING */}
                <section className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="mb-1 text-sm font-medium" style={{ color: red }}>
                            HOSPITAL MANAGEMENT
                        </p>
                        <h2 className="text-2xl font-bold md:text-3xl">Hospital Dashboard</h2>
                        <p className="mt-1 text-sm" style={{ color: muted }}>
                            Create blood requests and review suggested donor matches.
                        </p>
                    </div>
                    <div className="rounded-xl px-4 py-3 text-sm" style={panelStyle}>
                        <p style={{ color: muted }}>Hospital account</p>
                        <p className="font-semibold">Civil Hospital, Hyderabad</p>
                    </div>
                </section>

                {!API_URL && (
                    <div className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-600">
                        <AlertTriangle size={19} className="mt-0.5 shrink-0" />
                        <div>
                            <strong>Demo mode:</strong> Synthetic data is being used. Requests and approvals
                            update only this page until your backend API is connected.
                        </div>
                    </div>
                )}

                {error && (
                    <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-500">
                        <AlertTriangle size={18} /> {error}
                    </div>
                )}

                {success && (
                    <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-500">
                        <CheckCircle2 size={18} /> {success}
                    </div>
                )}

                {/* STAT CARDS */}
                <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    {[
                        { label: "Total Requests", value: requests.length, icon: ClipboardList },
                        { label: "Units Requested", value: totalUnits, icon: Droplets },
                        { label: "Pending Requests", value: pendingCount, icon: Clock },
                        { label: "Matching Requests", value: matchingCount, icon: Activity }
                    ].map((stat, index) => (
                        <div key={stat.label} className="rounded-2xl p-5" style={panelStyle}>
                            <div className="flex items-center justify-between">
                                <p className="text-sm" style={{ color: muted }}>{stat.label}</p>
                                <div
                                    className="rounded-xl p-2"
                                    style={{
                                        color: red,
                                        background: "#f43f5e18"
                                    }}
                                >
                                    <stat.icon size={20} />
                                </div>
                            </div>
                            <h3 className="mt-3 text-3xl font-bold">{stat.value}</h3>
                            <p className="mt-1 text-xs" style={{ color: muted }}>
                                {index === 3 ? `${completedCount} completed requests` : "Hospital request overview"}
                            </p>
                        </div>
                    ))}
                </section>

                {/* REQUEST FORM */}
                <section id="request-form" className="rounded-2xl p-5 md:p-6" style={panelStyle}>
                    <div className="mb-5 flex items-center gap-3">
                        <div className="rounded-xl p-2" style={{ background: "#f43f5e18", color: red }}>
                            <FilePlus2 size={21} />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold">Create Blood Request</h3>
                            <p className="text-sm" style={{ color: muted }}>
                                Enter the blood requirements for a patient.
                            </p>
                        </div>
                    </div>

                    <form onSubmit={submitRequest} className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        <label className="space-y-2 text-sm font-medium">
                            Blood Group
                            <select
                                required
                                value={form.bloodGroup}
                                onChange={e => setForm({ ...form, bloodGroup: e.target.value })}
                                className="w-full rounded-xl border p-3 outline-none"
                                style={{ background: bg, color: text, borderColor: border }}
                            >
                                {["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"].map(group => (
                                    <option key={group}>{group}</option>
                                ))}
                            </select>
                        </label>

                        <label className="space-y-2 text-sm font-medium">
                            Units Required
                            <input
                                type="number"
                                min="1"
                                max="20"
                                required
                                value={form.units}
                                onChange={e => setForm({ ...form, units: e.target.value })}
                                className="w-full rounded-xl border p-3 outline-none"
                                style={{ background: bg, color: text, borderColor: border }}
                                placeholder="Enter units"
                            />
                        </label>

                        <label className="space-y-2 text-sm font-medium">
                            Hospital Location
                            <input
                                required
                                value={form.location}
                                onChange={e => setForm({ ...form, location: e.target.value })}
                                className="w-full rounded-xl border p-3 outline-none"
                                style={{ background: bg, color: text, borderColor: border }}
                                placeholder="Enter hospital location"
                            />
                        </label>

                        <label className="space-y-2 text-sm font-medium">
                            Urgency
                            <select
                                value={form.urgency}
                                onChange={e => setForm({ ...form, urgency: e.target.value })}
                                className="w-full rounded-xl border p-3 outline-none"
                                style={{ background: bg, color: text, borderColor: border }}
                            >
                                <option>Normal</option>
                                <option>High</option>
                                <option>Critical</option>
                            </select>
                        </label>

                        <label className="space-y-2 text-sm font-medium md:col-span-2">
                            Required Deadline
                            <input
                                type="datetime-local"
                                required
                                value={form.deadline}
                                onChange={e => setForm({ ...form, deadline: e.target.value })}
                                className="w-full rounded-xl border p-3 outline-none"
                                style={{ background: bg, color: text, borderColor: border }}
                            />
                        </label>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="flex items-center justify-center gap-2 rounded-xl px-5 py-3 font-semibold text-white transition hover:opacity-90 disabled:opacity-50 md:col-span-2"
                            style={{ background: red }}
                        >
                            <Droplets size={18} />
                            {submitting ? "Submitting..." : "Submit Blood Request"}
                        </button>
                    </form>
                </section>

                {/* REQUEST LIST */}
                <section id="requests-list" className="rounded-2xl p-5 md:p-6" style={panelStyle}>
                    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h3 className="text-lg font-bold">Submitted Blood Requests</h3>
                            <p className="text-sm" style={{ color: muted }}>
                                Select a request to inspect matches and its timeline.
                            </p>
                        </div>
                        <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: "#f43f5e18", color: red }}>
                            {requests.length} requests
                        </span>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center gap-2 py-10" style={{ color: muted }}>
                            <RefreshCw className="animate-spin" size={20} /> Loading requests...
                        </div>
                    ) : requests.length === 0 ? (
                        <p className="py-8 text-center text-sm" style={{ color: muted }}>
                            No blood requests found. Create your first request above.
                        </p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[700px] text-left text-sm">
                                <thead>
                                    <tr style={{ color: muted, borderBottom: `1px solid ${border}` }}>
                                        <th className="p-3">Request ID</th>
                                        <th className="p-3">Blood Group</th>
                                        <th className="p-3">Units</th>
                                        <th className="p-3">Urgency</th>
                                        <th className="p-3">Status</th>
                                        <th className="p-3">Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {requests.map(request => (
                                        <tr key={request.id} style={{ borderBottom: `1px solid ${border}` }}>
                                            <td className="p-3 font-semibold">{request.id}</td>
                                            <td className="p-3 font-bold" style={{ color: red }}>{request.bloodGroup}</td>
                                            <td className="p-3">{request.units}</td>
                                            <td className="p-3">
                                                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${urgencyColor(request.urgency)}`}>
                                                    {request.urgency}
                                                </span>
                                            </td>
                                            <td className="p-3">{request.status}</td>
                                            <td className="p-3">
                                                <button
                                                    onClick={() => setSelected(request.id)}
                                                    className="rounded-lg px-3 py-2 text-xs font-semibold text-white"
                                                    style={{ background: red }}
                                                >
                                                    View Details
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

                {/* SELECTED REQUEST DETAILS */}
                {selectedRequest && (
                    <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                        <div className="space-y-5 xl:col-span-2">
                            <div className="rounded-2xl p-5 md:p-6" style={panelStyle}>
                                <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <p className="text-xs font-semibold" style={{ color: red }}>REQUEST DETAILS</p>
                                        <h3 className="mt-1 text-xl font-bold">{selectedRequest.id}</h3>
                                    </div>
                                    <span className="rounded-full px-3 py-1 text-xs font-semibold" style={{ background: "#f43f5e18", color: red }}>
                                        {selectedRequest.status}
                                    </span>
                                </div>

                                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                                    {[
                                        { label: "Blood Group", value: selectedRequest.bloodGroup, icon: Droplets },
                                        { label: "Units", value: selectedRequest.units, icon: Activity },
                                        { label: "Urgency", value: selectedRequest.urgency, icon: AlertTriangle },
                                        { label: "Deadline", value: selectedRequest.deadline ? new Date(selectedRequest.deadline).toLocaleString() : "Not set", icon: CalendarDays }
                                    ].map(item => (
                                        <div key={item.label} className="rounded-xl p-3" style={{ background: bg }}>
                                            <item.icon size={18} style={{ color: red }} />
                                            <p className="mt-2 text-xs" style={{ color: muted }}>{item.label}</p>
                                            <p className="mt-1 break-words text-sm font-semibold">{item.value}</p>
                                        </div>
                                    ))}
                                </div>

                                <div className="mt-4 flex items-start gap-2 text-sm" style={{ color: muted }}>
                                    <MapPin size={17} className="mt-0.5 shrink-0" />
                                    {selectedRequest.location}
                                </div>
                            </div>

                            {/* MATCH SUGGESTIONS */}
                            <div className="rounded-2xl p-5 md:p-6" style={panelStyle}>
                                <div className="mb-5 flex items-center justify-between gap-3">
                                    <div>
                                        <h3 className="text-lg font-bold">Suggested Donor Matches</h3>
                                        <p className="text-sm" style={{ color: muted }}>
                                            Review each suggestion before approving an invitation.
                                        </p>
                                    </div>
                                    <Users size={22} style={{ color: red }} />
                                </div>

                                {selectedRequest.matches.length === 0 ? (
                                    <p className="py-6 text-center text-sm" style={{ color: muted }}>
                                        No donor matches are available for this request yet.
                                    </p>
                                ) : (
                                    <div className="space-y-4">
                                        {selectedRequest.matches.map(match => (
                                            <div key={match.id} className="rounded-xl border p-4" style={{ borderColor: border }}>
                                                <div className="flex flex-wrap items-start justify-between gap-3">
                                                    <div>
                                                        <h4 className="font-bold">{match.name}</h4>
                                                        <p className="mt-1 text-xs" style={{ color: muted }}>{match.id}</p>
                                                    </div>
                                                    <span className="rounded-full px-3 py-1 text-xs font-bold" style={{ background: "#f43f5e18", color: red }}>
                                                        {match.score}% match
                                                    </span>
                                                </div>

                                                <div className="mt-3 flex flex-wrap gap-3 text-sm" style={{ color: muted }}>
                                                    <span className="font-semibold" style={{ color: red }}>{match.bloodGroup}</span>
                                                    <span className="flex items-center gap-1"><MapPin size={14} />{match.location}</span>
                                                    <span>{match.distance} away</span>
                                                </div>

                                                <div className="mt-3 rounded-lg p-3 text-sm" style={{ background: bg }}>
                                                    <p className="mb-1 flex items-center gap-2 font-semibold">
                                                        <ShieldCheck size={16} style={{ color: red }} /> Match explanation
                                                    </p>
                                                    <p style={{ color: muted }}>{match.explanation}</p>
                                                </div>

                                                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                                                    <span className="text-xs font-semibold" style={{ color: muted }}>
                                                        Approval: {match.status}
                                                    </span>

                                                    {match.status === "Proposed" ? (
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => approveMatch(selectedRequest.id, match.id, true)}
                                                                className="flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold text-white"
                                                                style={{ background: "#16a34a" }}
                                                            >
                                                                <Check size={15} /> Approve invitation
                                                            </button>
                                                            <button
                                                                onClick={() => approveMatch(selectedRequest.id, match.id, false)}
                                                                className="flex items-center gap-1 rounded-lg border px-3 py-2 text-xs font-semibold"
                                                                style={{ borderColor: border, color: text }}
                                                            >
                                                                <X size={15} /> Reject
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <span className="text-xs font-semibold" style={{ color: match.status === "Approved" ? "#16a34a" : "#ef4444" }}>
                                                            {match.status === "Approved" ? "Approved for invitation" : "Match rejected"}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* TIMELINE */}
                        <aside className="rounded-2xl p-5 md:p-6" style={panelStyle}>
                            <div className="mb-5 flex items-center gap-2">
                                <Clock size={20} style={{ color: red }} />
                                <h3 className="text-lg font-bold">Request Timeline</h3>
                            </div>

                            <div className="space-y-5">
                                {selectedRequest.timeline.map((event, index) => (
                                    <div key={index} className="flex gap-3">
                                        <div className="flex flex-col items-center">
                                            <div
                                                className="rounded-full p-2"
                                                style={{
                                                    background: event.done ? "#16a34a20" : bg,
                                                    color: event.done ? "#16a34a" : muted
                                                }}
                                            >
                                                {event.done ? <CheckCircle2 size={17} /> : <Clock size={17} />}
                                            </div>
                                            {index !== selectedRequest.timeline.length - 1 && (
                                                <div className="mt-1 h-8 w-px" style={{ background: border }} />
                                            )}
                                        </div>
                                        <div className="pb-2">
                                            <p className="text-sm font-semibold">{event.label}</p>
                                            <p className="mt-1 text-xs" style={{ color: muted }}>{event.time}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="mt-6 rounded-xl p-4" style={{ background: bg }}>
                                <p className="text-xs font-semibold" style={{ color: muted }}>REQUEST PROGRESS</p>
                                <div className="mt-3 h-2 overflow-hidden rounded-full" style={{ background: border }}>
                                    <div
                                        className="h-full rounded-full"
                                        style={{
                                            width: `${(selectedRequest.timeline.filter(event => event.done).length / selectedRequest.timeline.length) * 100}%`,
                                            background: red
                                        }}
                                    />
                                </div>
                                <p className="mt-2 text-xs" style={{ color: muted }}>
                                    {selectedRequest.timeline.filter(event => event.done).length} of {selectedRequest.timeline.length} steps completed
                                </p>
                            </div>
                        </aside>
                    </section>
                )}

                <footer className="pb-5 text-center text-xs" style={{ color: muted }}>
                    BloodBridge AI · Hospital Request Management · Synthetic Demo Data
                </footer>
            </main>
        </div>
    );
}
