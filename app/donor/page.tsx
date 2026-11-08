
"use client";

import { useCallback, useEffect, useState } from "react";
import { getAuthHeaders, API_BASE_URL } from "../lib/auth";
import {
    Droplets,
    LayoutDashboard,
    HeartPulse,
    Users,
    Bot,
    BarChart3,
    ScrollText,
    Moon,
    Sun,
    Bell,
    Activity,
    CheckCircle2,
    Clock,
    MapPin,
    CalendarDays,
    AlertTriangle,
    Check,
    X,
    RefreshCw,
    UserRound,
} from "lucide-react";

/*
  Backend API configuration:
  Set NEXT_PUBLIC_API_URL in .env.local when your backend is ready.

  Expected endpoints:
  GET   /api/donor/me
  PATCH /api/donor/availability
  GET   /api/donor/invitations
  POST  /api/donor/invitations/:id/respond

  Without an API URL, the page uses local demo data.
*/

type Donor = {
    id: string;
    name: string;
    bloodGroup: string;
    age: number;
    city: string;
    phone: string;
    email: string;
    lastDonation: string;
    availability: boolean;
    totalDonations: number;
};

type Invitation = {
    id: string;
    patient: string;
    bloodGroup: string;
    hospital: string;
    location: string;
    urgency: "Critical" | "High" | "Normal";
    date: string;
    units: number;
    status: "Pending" | "Accepted" | "Declined" | "Completed";
};

const API_URL = API_BASE_URL;

const demoDonor: Donor = {
    id: "DNR-2048",
    name: "Ali Ahmed",
    bloodGroup: "O+",
    age: 24,
    city: "Hyderabad, Sindh",
    phone: "+92 300 1234567",
    email: "ali.ahmed@example.com",
    lastDonation: "August 15, 2026",
    availability: true,
    totalDonations: 5,
};

const demoInvitations: Invitation[] = [
    {
        id: "INV-1001",
        patient: "Sara Khan",
        bloodGroup: "O+",
        hospital: "Civil Hospital",
        location: "Hyderabad, Sindh",
        urgency: "Critical",
        date: "November 08, 2026",
        units: 2,
        status: "Pending",
    },
    {
        id: "INV-1002",
        patient: "Ahmed Raza",
        bloodGroup: "O+",
        hospital: "Liaquat University Hospital",
        location: "Jamshoro, Sindh",
        urgency: "High",
        date: "November 07, 2026",
        units: 1,
        status: "Accepted",
    },
    {
        id: "INV-1003",
        patient: "Fatima Noor",
        bloodGroup: "O+",
        hospital: "City Hospital",
        location: "Hyderabad, Sindh",
        urgency: "Normal",
        date: "November 04, 2026",
        units: 1,
        status: "Declined",
    },
    {
        id: "INV-1004",
        patient: "Usman Ali",
        bloodGroup: "O+",
        hospital: "Civil Hospital",
        location: "Hyderabad, Sindh",
        urgency: "High",
        date: "October 28, 2026",
        units: 1,
        status: "Completed",
    },
];

const navigation = [
    { name: "Overview", icon: LayoutDashboard },
    { name: "My Invitations", icon: HeartPulse },
    { name: "My Profile", icon: UserRound },
];

export default function DonorDashboard() {
    const [dark, setDark] = useState(true);
    const [donor, setDonor] = useState<Donor | null>(null);
    const [invitations, setInvitations] = useState<Invitation[]>([]);
    const [activeNav, setActiveNav] = useState("Overview");
    const [loading, setLoading] = useState(true);
    const [updatingAvailability, setUpdatingAvailability] = useState(false);
    const [respondingId, setRespondingId] = useState<string | null>(null);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const demoMode = !API_URL;

    const bg = dark ? "#020617" : "#f1f5f9";
    const card = dark ? "#0f172a" : "#ffffff";
    const text = dark ? "#f8fafc" : "#0f172a";
    const muted = dark ? "#94a3b8" : "#64748b";
    const border = dark ? "#273449" : "#e2e8f0";
    const accent = "#f43f5e";

    const loadDashboard = useCallback(async () => {
        setLoading(true);
        setError("");

        if (demoMode) {
            setDonor(demoDonor);
            setInvitations(demoInvitations);
            setLoading(false);
            return;
        }

        try {
            const authHeaders = getAuthHeaders();
            const [profileResponse, invitationsResponse] = await Promise.all([
                fetch(`${API_URL}/api/donors/me`, { headers: { ...authHeaders } }),
                fetch(`${API_URL}/api/invitations`, { headers: { ...authHeaders } }),
            ]);

            if (!profileResponse.ok || !invitationsResponse.ok) {
                throw new Error("Unable to load donor dashboard data. Please verify your login session.");
            }

            const profileData = await profileResponse.json();
            const invitationData = await invitationsResponse.json();

            const p = profileData.data || profileData.donor || profileData;
            const invList = invitationData.data?.items || invitationData.data || invitationData.invitations || (Array.isArray(invitationData) ? invitationData : []);

            setDonor({
                id: p.id || demoDonor.id,
                name: p.name || demoDonor.name,
                bloodGroup: p.blood_group || p.bloodGroup || demoDonor.bloodGroup,
                age: p.age || demoDonor.age,
                city: p.city || demoDonor.city,
                phone: p.phone || demoDonor.phone,
                email: p.email || demoDonor.email,
                lastDonation: p.last_donation_date || p.lastDonation || demoDonor.lastDonation,
                availability: p.availability === "available" || p.availability === true,
                totalDonations: (p.demo_eligibility?.donation_history?.length) || p.totalDonations || 0,
            });

            setInvitations(
                invList.map((inv: any) => ({
                    id: inv.id,
                    patient: inv.request_title || (inv.blood_group ? `${inv.blood_group} Patient` : "Blood Request"),
                    bloodGroup: inv.blood_group || p.blood_group || "O+",
                    hospital: inv.hospital_name || "Regional Hospital",
                    location: inv.location || p.city || "Nearby",
                    urgency: inv.urgency ? inv.urgency.charAt(0).toUpperCase() + inv.urgency.slice(1) : "Normal",
                    date: inv.deadline ? new Date(inv.deadline).toLocaleDateString() : (inv.sent_at ? new Date(inv.sent_at).toLocaleDateString() : "Active"),
                    units: inv.units_requested || 1,
                    status: inv.status ? inv.status.charAt(0).toUpperCase() + inv.status.slice(1) : "Pending",
                }))
            );
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Something went wrong while loading your dashboard."
            );
        } finally {
            setLoading(false);
        }
    }, [demoMode]);

    useEffect(() => {
        loadDashboard();
    }, [loadDashboard]);

    async function updateAvailability() {
        if (!donor || updatingAvailability) return;

        const newAvailability = !donor.availability;
        setUpdatingAvailability(true);
        setError("");
        setSuccess("");

        try {
            if (!demoMode) {
                const authHeaders = getAuthHeaders();
                const response = await fetch(
                    `${API_URL}/api/donors/${donor.id}/availability`,
                    {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json", ...authHeaders },
                        body: JSON.stringify({ availability: newAvailability ? "available" : "unavailable" }),
                    }
                );

                if (!response.ok) {
                    throw new Error("Could not update your availability.");
                }
            }

            setDonor({ ...donor, availability: newAvailability });
            setSuccess(
                newAvailability
                    ? "Your availability is now ON."
                    : "Your availability is now OFF."
            );
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Availability update failed."
            );
        } finally {
            setUpdatingAvailability(false);
        }
    }

    async function respondToInvitation(
        invitationId: string,
        responseStatus: "Accepted" | "Declined"
    ) {
        setRespondingId(invitationId);
        setError("");
        setSuccess("");

        try {
            if (!demoMode) {
                const authHeaders = getAuthHeaders();
                const response = await fetch(
                    `${API_URL}/api/invitations/${invitationId}/respond`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json", ...authHeaders },
                        body: JSON.stringify({ 
                            response: responseStatus.toLowerCase(),
                            message: `I have ${responseStatus.toLowerCase()} the invitation.`
                        }),
                    }
                );

                if (!response.ok) {
                    throw new Error("Unable to submit your invitation response.");
                }
            }

            setInvitations((previous) =>
                previous.map((invitation) =>
                    invitation.id === invitationId
                        ? { ...invitation, status: responseStatus }
                        : invitation
                )
            );

            setSuccess(
                `Invitation ${responseStatus.toLowerCase()} successfully. The Follow-up Agent has recorded your response.`
            );
            );
        } catch (err) {
            setError(
                err instanceof Error ? err.message : "Could not update invitation."
            );
        } finally {
            setRespondingId(null);
        }
    }

    const pendingCount = invitations.filter(
        (item) => item.status === "Pending"
    ).length;

    const acceptedCount = invitations.filter(
        (item) => item.status === "Accepted"
    ).length;

    const completedCount = invitations.filter(
        (item) => item.status === "Completed"
    ).length;

    function statusStyle(status: Invitation["status"]) {
        const styles = {
            Pending: { background: "#f59e0b20", color: "#fbbf24" },
            Accepted: { background: "#10b98120", color: "#34d399" },
            Declined: { background: "#fb718520", color: "#fb7185" },
            Completed: { background: "#6366f120", color: "#818cf8" },
        };

        return styles[status];
    }

    function urgencyStyle(urgency: Invitation["urgency"]) {
        const styles = {
            Critical: { background: "#fb718520", color: "#fb7185" },
            High: { background: "#f59e0b20", color: "#fbbf24" },
            Normal: { background: "#10b98120", color: "#34d399" },
        };

        return styles[urgency];
    }

    return (
        <main
            className="min-h-screen transition-colors duration-300"
            style={{ background: bg, color: text }}
        >
            {/* SAME DARK NAVBAR AS ADMIN DASHBOARD */}
            <header
                className="sticky top-0 z-30"
                style={{
                    background: "#0f172a",
                    borderBottom: "1px solid #273449",
                }}
            >
                <div className="flex items-center gap-5 px-6 py-6 md:px-8">
                    <div
                        className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-white"
                        style={{ background: accent }}
                    >
                        <Droplets size={32} />
                    </div>

                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-white">
                            BloodBridge
                        </h1>
                        <p className="text-sm text-slate-400">
                            AI management platform
                        </p>
                    </div>

                    <div className="ml-auto flex items-center gap-3">
                        <span className="hidden text-sm text-slate-400 sm:block">
                            Donor Portal
                        </span>
                        <div
                            className="flex h-11 w-11 items-center justify-center rounded-xl font-bold text-white"
                            style={{ background: accent }}
                        >
                            {donor?.name?.charAt(0) ?? "D"}
                        </div>
                    </div>
                </div>

                <nav className="overflow-x-auto px-5 pb-4">
                    <div className="flex w-max items-center gap-2">
                        {navigation.map((item) => {
                            const Icon = item.icon;
                            const selected = activeNav === item.name;

                            return (
                                <button
                                    key={item.name}
                                    onClick={() => setActiveNav(item.name)}
                                    className="flex shrink-0 items-center gap-3 rounded-xl px-5 py-4 text-sm font-semibold transition-all hover:-translate-y-0.5"
                                    style={{
                                        background: selected ? "#293449" : "transparent",
                                        color: selected ? "#ffffff" : "#94a3b8",
                                    }}
                                >
                                    <Icon
                                        size={23}
                                        style={{ color: selected ? accent : "#94a3b8" }}
                                    />
                                    {item.name}
                                </button>
                            );
                        })}
                    </div>
                </nav>
            </header>

            <div className="mx-auto max-w-[1500px] px-5 py-7 md:px-8">
                {/* PAGE HEADING */}
                <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <p className="mb-3 text-sm" style={{ color: muted }}>
                            Donor Portal / {activeNav}
                        </p>
                        <h2 className="text-3xl font-bold">
                            {activeNav === "Overview"
                                ? "Donor dashboard"
                                : activeNav}
                        </h2>
                        <p className="mt-2" style={{ color: muted }}>
                            Manage your donor profile, availability and blood requests.
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setDark(true)}
                            className="flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold"
                            style={{
                                background: dark ? "#293449" : card,
                                borderColor: border,
                                color: text,
                            }}
                        >
                            <Moon size={18} /> Dark
                        </button>

                        <button
                            onClick={() => setDark(false)}
                            className="flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold"
                            style={{
                                background: !dark ? "#e2e8f0" : card,
                                borderColor: border,
                                color: text,
                            }}
                        >
                            <Sun size={18} /> Soft
                        </button>

                        <button
                            onClick={loadDashboard}
                            className="flex h-12 w-12 items-center justify-center rounded-xl border"
                            style={{ background: card, borderColor: border }}
                            title="Refresh dashboard"
                        >
                            <RefreshCw size={19} />
                        </button>
                    </div>
                </div>

                {/* DEMO NOTICE */}
                {demoMode && (
                    <div
                        className="mb-6 flex items-start gap-4 rounded-2xl border p-5"
                        style={{
                            background: dark ? "#03182e" : "#eff6ff",
                            borderColor: dark ? "#075985" : "#bfdbfe",
                        }}
                    >
                        <Activity size={23} className="shrink-0 text-sky-400" />
                        <p
                            className="text-sm leading-6"
                            style={{ color: dark ? "#bae6fd" : "#1e40af" }}
                        >
                            <strong>Demo mode.</strong> You are viewing synthetic donor
                            information and simulated invitations. Connect the backend API
                            to save changes on the server.
                        </p>
                    </div>
                )}

                {/* SUCCESS AND ERROR MESSAGES */}
                {success && (
                    <div className="mb-5 flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-400">
                        <CheckCircle2 size={20} />
                        <p className="text-sm font-medium">{success}</p>
                        <button className="ml-auto" onClick={() => setSuccess("")}>
                            <X size={18} />
                        </button>
                    </div>
                )}

                {error && (
                    <div className="mb-5 flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-400">
                        <AlertTriangle size={20} />
                        <p className="text-sm">{error}</p>
                        <button className="ml-auto" onClick={() => setError("")}>
                            <X size={18} />
                        </button>
                    </div>
                )}

                {/* LOADING */}
                {loading ? (
                    <div
                        className="rounded-3xl border p-12 text-center"
                        style={{ background: card, borderColor: border }}
                    >
                        <RefreshCw
                            size={30}
                            className="mx-auto mb-4 animate-spin"
                            style={{ color: accent }}
                        />
                        <p className="font-semibold">Loading donor dashboard...</p>
                        <p className="mt-2 text-sm" style={{ color: muted }}>
                            Please wait while we load your profile and invitations.
                        </p>
                    </div>
                ) : donor ? (
                    <>
                        {/* SUMMARY CARDS */}
                        <div className="mb-7 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
                            {[
                                {
                                    title: "My blood group",
                                    value: donor.bloodGroup,
                                    detail: "Registered blood type",
                                    icon: Droplets,
                                    color: accent,
                                },
                                {
                                    title: "Pending invitations",
                                    value: pendingCount,
                                    detail: "Require your response",
                                    icon: Bell,
                                    color: "#fbbf24",
                                },
                                {
                                    title: "Accepted invitations",
                                    value: acceptedCount,
                                    detail: "You have accepted",
                                    icon: CheckCircle2,
                                    color: "#2dd4bf",
                                },
                                {
                                    title: "Completed donations",
                                    value: completedCount,
                                    detail: "Completed invitation records",
                                    icon: HeartPulse,
                                    color: "#a78bfa",
                                },
                            ].map((item) => {
                                const Icon = item.icon;

                                return (
                                    <div
                                        key={item.title}
                                        className="rounded-3xl border p-6 transition-all duration-300 hover:-translate-y-1"
                                        style={{ background: card, borderColor: border }}
                                    >
                                        <div className="flex items-center justify-between">
                                            <p className="text-sm font-semibold" style={{ color: muted }}>
                                                {item.title}
                                            </p>
                                            <div
                                                className="rounded-2xl p-3"
                                                style={{
                                                    background: `${item.color}20`,
                                                    color: item.color,
                                                }}
                                            >
                                                <Icon size={25} />
                                            </div>
                                        </div>
                                        <h3 className="mt-6 text-4xl font-bold">{item.value}</h3>
                                        <p className="mt-2 text-sm" style={{ color: muted }}>
                                            {item.detail}
                                        </p>
                                    </div>
                                );
                            })}
                        </div>

                        {/* PROFILE AND AVAILABILITY */}
                        <div className="mb-7 grid grid-cols-1 gap-6 lg:grid-cols-3">
                            <section
                                className="rounded-3xl border p-6 lg:col-span-2"
                                style={{ background: card, borderColor: border }}
                            >
                                <div className="mb-6 flex items-center gap-3">
                                    <UserRound size={24} style={{ color: accent }} />
                                    <div>
                                        <h3 className="text-xl font-bold">My donor profile</h3>
                                        <p className="text-sm" style={{ color: muted }}>
                                            Your registered donor information
                                        </p>
                                    </div>
                                </div>

                                <div className="mb-6 flex flex-wrap items-center gap-5">
                                    <div
                                        className="flex h-20 w-20 items-center justify-center rounded-2xl text-3xl font-bold"
                                        style={{
                                            background: `${accent}20`,
                                            color: accent,
                                        }}
                                    >
                                        {donor.name.charAt(0)}
                                    </div>
                                    <div>
                                        <h4 className="text-2xl font-bold">{donor.name}</h4>
                                        <p className="mt-1 text-sm" style={{ color: muted }}>
                                            Donor ID: {donor.id}
                                        </p>
                                        <span
                                            className="mt-2 inline-block rounded-full px-3 py-1 text-xs font-bold"
                                            style={{ background: `${accent}20`, color: accent }}
                                        >
                                            {donor.bloodGroup} Blood Group
                                        </span>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                                    {[
                                        ["Age", `${donor.age} years`],
                                        ["Location", donor.city],
                                        ["Phone", donor.phone],
                                        ["Email", donor.email],
                                        ["Last donation", donor.lastDonation],
                                        ["Total donations", donor.totalDonations],
                                    ].map(([label, value]) => (
                                        <div
                                            key={label}
                                            className="rounded-xl border p-4"
                                            style={{ borderColor: border }}
                                        >
                                            <p className="mb-2 text-xs" style={{ color: muted }}>
                                                {label}
                                            </p>
                                            <p className="break-words text-sm font-semibold">{value}</p>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* AVAILABILITY CONTROL */}
                            <section
                                className="rounded-3xl border p-6"
                                style={{ background: card, borderColor: border }}
                            >
                                <div className="mb-6 flex items-center gap-3">
                                    <Activity size={24} style={{ color: accent }} />
                                    <h3 className="text-xl font-bold">Availability</h3>
                                </div>

                                <div
                                    className="mb-6 rounded-2xl p-5 text-center"
                                    style={{
                                        background: donor.availability
                                            ? "#10b98115"
                                            : "#64748b20",
                                    }}
                                >
                                    <div
                                        className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full"
                                        style={{
                                            background: donor.availability
                                                ? "#10b98125"
                                                : "#64748b25",
                                            color: donor.availability ? "#34d399" : "#94a3b8",
                                        }}
                                    >
                                        {donor.availability ? (
                                            <CheckCircle2 size={32} />
                                        ) : (
                                            <Clock size={32} />
                                        )}
                                    </div>

                                    <h4 className="text-xl font-bold">
                                        {donor.availability ? "Available" : "Unavailable"}
                                    </h4>
                                    <p className="mt-2 text-sm" style={{ color: muted }}>
                                        {donor.availability
                                            ? "You can receive blood donation invitations."
                                            : "You will not receive new invitations."}
                                    </p>
                                </div>

                                <button
                                    onClick={updateAvailability}
                                    disabled={updatingAvailability}
                                    className="flex w-full items-center justify-center gap-2 rounded-xl px-5 py-4 font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                                    style={{
                                        background: donor.availability ? "#64748b" : accent,
                                    }}
                                >
                                    {updatingAvailability && (
                                        <RefreshCw size={18} className="animate-spin" />
                                    )}
                                    {donor.availability
                                        ? "Set as unavailable"
                                        : "Set as available"}
                                </button>

                                <p className="mt-4 text-center text-xs" style={{ color: muted }}>
                                    You can change your availability at any time.
                                </p>
                            </section>
                        </div>

                        {/* INVITATIONS */}
                        <section
                            className="mb-7 overflow-hidden rounded-3xl border"
                            style={{ background: card, borderColor: border }}
                        >
                            <div className="flex flex-wrap items-center justify-between gap-3 p-6">
                                <div>
                                    <h3 className="text-xl font-bold">Received invitations</h3>
                                    <p className="mt-1 text-sm" style={{ color: muted }}>
                                        Review blood requests and respond to invitations.
                                    </p>
                                </div>
                                <span
                                    className="rounded-full px-4 py-2 text-sm font-semibold"
                                    style={{ background: `${accent}20`, color: accent }}
                                >
                                    {pendingCount} Pending
                                </span>
                            </div>

                            {invitations.length === 0 ? (
                                <div className="p-10 text-center">
                                    <Bell
                                        size={35}
                                        className="mx-auto mb-3"
                                        style={{ color: muted }}
                                    />
                                    <p className="font-semibold">No invitations yet</p>
                                    <p className="mt-2 text-sm" style={{ color: muted }}>
                                        New blood donation requests will appear here.
                                    </p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 gap-4 p-6 xl:grid-cols-2">
                                    {invitations.map((invitation) => (
                                        <div
                                            key={invitation.id}
                                            className="rounded-2xl border p-5"
                                            style={{ borderColor: border }}
                                        >
                                            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                                                <div>
                                                    <p className="text-xs" style={{ color: muted }}>
                                                        Invitation ID
                                                    </p>
                                                    <p className="font-bold">{invitation.id}</p>
                                                </div>

                                                <span
                                                    className="rounded-full px-3 py-1.5 text-xs font-bold"
                                                    style={statusStyle(invitation.status)}
                                                >
                                                    {invitation.status}
                                                </span>
                                            </div>

                                            <div className="mb-4 flex items-center gap-4">
                                                <div
                                                    className="flex h-14 w-14 items-center justify-center rounded-xl text-xl font-bold"
                                                    style={{
                                                        background: `${accent}20`,
                                                        color: accent,
                                                    }}
                                                >
                                                    {invitation.bloodGroup}
                                                </div>
                                                <div>
                                                    <h4 className="text-lg font-bold">
                                                        {invitation.patient}
                                                    </h4>
                                                    <p className="text-sm" style={{ color: muted }}>
                                                        {invitation.units} unit(s) requested
                                                    </p>
                                                </div>
                                            </div>

                                            <div className="mb-4 space-y-3 text-sm">
                                                <div className="flex items-center gap-3">
                                                    <HeartPulse size={17} style={{ color: accent }} />
                                                    <span>{invitation.hospital}</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <MapPin size={17} style={{ color: muted }} />
                                                    <span>{invitation.location}</span>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <CalendarDays size={17} style={{ color: muted }} />
                                                    <span>{invitation.date}</span>
                                                </div>
                                            </div>

                                            <div className="mb-5 flex items-center justify-between gap-3">
                                                <span className="text-sm" style={{ color: muted }}>
                                                    Request urgency
                                                </span>
                                                <span
                                                    className="rounded-full px-3 py-1.5 text-xs font-bold"
                                                    style={urgencyStyle(invitation.urgency)}
                                                >
                                                    {invitation.urgency}
                                                </span>
                                            </div>

                                            {invitation.status === "Pending" ? (
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={() =>
                                                            respondToInvitation(invitation.id, "Accepted")
                                                        }
                                                        disabled={respondingId === invitation.id}
                                                        className="flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold text-white disabled:opacity-50"
                                                        style={{ background: "#059669" }}
                                                    >
                                                        {respondingId === invitation.id ? (
                                                            <RefreshCw size={17} className="animate-spin" />
                                                        ) : (
                                                            <Check size={17} />
                                                        )}
                                                        Accept
                                                    </button>

                                                    <button
                                                        onClick={() =>
                                                            respondToInvitation(invitation.id, "Declined")
                                                        }
                                                        disabled={respondingId === invitation.id}
                                                        className="flex flex-1 items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-bold disabled:opacity-50"
                                                        style={{
                                                            background: `${accent}10`,
                                                            color: accent,
                                                            borderColor: `${accent}40`,
                                                        }}
                                                    >
                                                        <X size={17} />
                                                        Decline
                                                    </button>
                                                </div>
                                            ) : (
                                                <div
                                                    className="rounded-xl px-4 py-3 text-center text-sm font-semibold"
                                                    style={{
                                                        background: statusStyle(invitation.status).background,
                                                        color: statusStyle(invitation.status).color,
                                                    }}
                                                >
                                                    Response: {invitation.status}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>

                        {/* INVITATION HISTORY */}
                        <section
                            className="mb-7 overflow-hidden rounded-3xl border"
                            style={{ background: card, borderColor: border }}
                        >
                            <div className="p-6">
                                <div className="flex items-center gap-3">
                                    <ScrollText size={24} style={{ color: accent }} />
                                    <div>
                                        <h3 className="text-xl font-bold">Invitation history</h3>
                                        <p className="mt-1 text-sm" style={{ color: muted }}>
                                            Track your previous invitation responses.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full min-w-[650px] text-left text-sm">
                                    <thead
                                        style={{
                                            background: dark ? "#1e293b" : "#f1f5f9",
                                            color: muted,
                                        }}
                                    >
                                        <tr>
                                            {[
                                                "Invitation ID",
                                                "Patient",
                                                "Blood group",
                                                "Date",
                                                "Status",
                                            ].map((heading) => (
                                                <th key={heading} className="px-6 py-4 font-semibold">
                                                    {heading}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {invitations.map((invitation) => (
                                            <tr
                                                key={invitation.id}
                                                className="border-t"
                                                style={{ borderColor: border }}
                                            >
                                                <td className="px-6 py-4 font-semibold">
                                                    {invitation.id}
                                                </td>
                                                <td className="px-6 py-4">{invitation.patient}</td>
                                                <td
                                                    className="px-6 py-4 font-bold"
                                                    style={{ color: accent }}
                                                >
                                                    {invitation.bloodGroup}
                                                </td>
                                                <td className="px-6 py-4" style={{ color: muted }}>
                                                    {invitation.date}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span
                                                        className="rounded-full px-3 py-1.5 text-xs font-bold"
                                                        style={statusStyle(invitation.status)}
                                                    >
                                                        {invitation.status}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    </>
                ) : (
                    <div
                        className="rounded-3xl border p-10 text-center"
                        style={{ background: card, borderColor: border }}
                    >
                        <AlertTriangle
                            size={32}
                            className="mx-auto mb-3 text-red-400"
                        />
                        <h3 className="text-xl font-bold">Could not load donor profile</h3>
                        <p className="mt-2 text-sm" style={{ color: muted }}>
                            Check your backend connection and try again.
                        </p>
                        <button
                            onClick={loadDashboard}
                            className="mt-5 rounded-xl px-5 py-3 font-semibold text-white"
                            style={{ background: accent }}
                        >
                            Try again
                        </button>
                    </div>
                )}

                <footer
                    className="border-t py-6 text-center text-sm"
                    style={{ borderColor: border, color: muted }}
                >
                    © 2026 BloodBridge AI · Donor Portal
                </footer>
            </div>
        </main>
    );
}

