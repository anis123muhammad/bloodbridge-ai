
"use client";

import { useState } from "react";
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
  Send,
} from "lucide-react";

const navItems = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Blood Requests", icon: HeartPulse },
  { name: "Donors", icon: Users },
  { name: "Agent Activity", icon: Bot },
  { name: "Analytics", icon: BarChart3 },
  { name: "Audit Logs", icon: ScrollText },
];

const stats = [
  {
    title: "Total requests",
    value: "120",
    change: "+12.5%",
    icon: HeartPulse,
    color: "#fb7185",
    points: "0,40 15,35 30,38 45,25 60,30 75,15 100,5",
  },
  {
    title: "Available donors",
    value: "348",
    change: "+8.2%",
    icon: Users,
    color: "#2dd4bf",
    points: "0,42 15,32 30,37 45,22 60,27 75,13 100,4",
  },
  {
    title: "Invitations sent",
    value: "86",
    change: "+15.3%",
    icon: Send,
    color: "#a78bfa",
    points: "0,40 15,34 30,38 45,20 60,28 75,12 100,5",
  },
  {
    title: "Successful matches",
    value: "64",
    change: "+10.1%",
    icon: CheckCircle2,
    color: "#fbbf24",
    points: "0,42 15,35 30,30 45,33 60,20 75,14 100,4",
  },
];

const bloodGroups = [
  { name: "A+", value: 35, color: "#f43f5e" },
  { name: "A-", value: 12, color: "#fb7185" },
  { name: "B+", value: 28, color: "#14b8a6" },
  { name: "B-", value: 10, color: "#2dd4bf" },
  { name: "O+", value: 45, color: "#818cf8" },
  { name: "O-", value: 18, color: "#a78bfa" },
  { name: "AB+", value: 20, color: "#f59e0b" },
  { name: "AB-", value: 8, color: "#fbbf24" },
];

const weekly = [
  { day: "Mon", value: 45 },
  { day: "Tue", value: 65 },
  { day: "Wed", value: 38 },
  { day: "Thu", value: 80 },
  { day: "Fri", value: 55 },
  { day: "Sat", value: 95 },
  { day: "Sun", value: 70 },
];

const requests = [
  ["BB-1001", "Ali Ahmed", "O+", "City Hospital", "Pending"],
  ["BB-1002", "Sara Khan", "A+", "Civil Hospital", "Matched"],
  ["BB-1003", "Ahmed Raza", "B+", "Liaquat Hospital", "Processing"],
  ["BB-1004", "Fatima Noor", "AB+", "City Hospital", "Completed"],
];

const activities = [
  ["Donor matching agent completed", "Matched 3 potential donors for BB-1002", "2 minutes ago"],
  ["New blood request received", "Request BB-1005 requires O-negative blood", "15 minutes ago"],
  ["Notification agent executed", "Invitation sent to 12 eligible donors", "35 minutes ago"],
  ["Request validation completed", "Request BB-1004 passed validation", "1 hour ago"],
];

const auditLogs = [
  ["New request created", "Admin", "10:45 AM"],
  ["Donor invitation sent", "Matching Agent", "10:30 AM"],
  ["Request status updated", "Admin", "09:55 AM"],
  ["Donor profile verified", "Verification Agent", "09:20 AM"],
];


export default function Home() {
  const [dark, setDark] = useState(true);
  const accent = "#f43f5e";
  const [active, setActive] = useState("Overview");
  const [filter, setFilter] = useState("All");

  const bg = dark ? "#020617" : "#f1f5f9";
  const card = dark ? "#0f172a" : "#ffffff";
  const text = dark ? "#f8fafc" : "#0f172a";
  const muted = dark ? "#94a3b8" : "#64748b";
  const border = dark ? "#273449" : "#e2e8f0";

  return (
    <main
      className="min-h-screen"
      style={{ background: bg, color: text }}
    >
      {/* BRAND HEADER */}
      <header
        className="sticky top-0 z-30"
        style={{
          background: "#0f172a",
          borderBottom: "1px solid #273449",
        }}
      >
        <div className="flex items-center gap-5 px-6 py-7 md:px-8">
          <div
            className="flex h-[60px] w-[60px] shrink-0 items-center justify-center rounded-2xl text-white"
            style={{ background: accent }}
          >
            <Droplets size={32} />
          </div>

          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              BloodBridge
            </h1>

            <p className="text-base text-slate-400">
              AI management platform
            </p>
          </div>
        </div>

        {/* HORIZONTAL NAVIGATION */}
        <nav className="overflow-x-auto px-5 pb-4">
          <div className="flex w-max min-w-full items-center gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const selected = active === item.name;

              return (
                <button
                  key={item.name}
                  onClick={() => setActive(item.name)}
                  className="flex shrink-0 items-center gap-3 rounded-xl px-5 py-4 text-base font-semibold transition-all hover:-translate-y-0.5"
                  style={{
                    background: selected ? "#293449" : "transparent",
                    color: selected ? "#ffffff" : "#94a3b8",
                  }}
                >
                  <Icon
                    size={25}
                    style={{ color: selected ? accent : muted }}
                  />
                  {item.name}
                </button>
              );
            })}
          </div>
        </nav>
      </header>

      {/* DASHBOARD CONTENT */}
      <div className="mx-auto max-w-[1600px] px-6 py-7 md:px-8">

        {/* TITLE */}
        <div className="mb-6">
          <p className="mb-3 text-lg" style={{ color: muted }}>
            Admin / {active}
          </p>

          <h2 className="text-3xl font-bold tracking-tight">
            {active === "Overview" ? "Dashboard overview" : active}
          </h2>

          <p className="mt-2 text-lg" style={{ color: muted }}>
            Monitor requests, donor matching and agent runs in one place.
          </p>
        </div>

        {/* THEME CONTROLS */}
        <div className="mb-9 flex flex-wrap items-center gap-4">

          <div
            className="flex rounded-2xl border p-1"
            style={{ background: card, borderColor: border }}
          >
            <button
              onClick={() => setDark(true)}
              className="flex items-center gap-2 rounded-xl px-4 py-3 font-semibold"
              style={{
                background: dark ? "#293449" : "transparent",
                color: text,
              }}
            >
              <Moon size={20} /> Dark
            </button>

            <button
              onClick={() => setDark(false)}
              className="flex items-center gap-2 rounded-xl px-4 py-3 font-semibold"
              style={{
                background: !dark ? "#e2e8f0" : "transparent",
                color: dark ? muted : "#0f172a",
              }}
            >
              <Sun size={20} /> Soft
            </button>
          </div>

          {/* ACCENT COLORS */}


          {/* NOTIFICATION */}
          <button
            className="relative flex h-14 w-14 items-center justify-center rounded-2xl border"
            style={{ background: card, borderColor: border }}
          >
            <Bell size={25} style={{ color: muted }} />
            <span
              className="absolute right-3 top-3 h-3 w-3 rounded-full"
              style={{ background: accent }}
            />
          </button>

          {/* ADMIN */}
          <div
            className="flex items-center gap-4 rounded-2xl border px-3 py-2"
            style={{ background: card, borderColor: border }}
          >
            <div
              className="flex h-14 w-14 items-center justify-center rounded-xl text-xl font-bold"
              style={{ background: `${accent}25`, color: "#fda4af" }}
            >
              A
            </div>
            <div>
              <p className="text-lg font-semibold">Administrator</p>
              <p style={{ color: muted }}>Super admin</p>
            </div>
          </div>
        </div>

        {/* DEMO MODE */}
        <div
          className="mb-9 flex items-start gap-5 rounded-2xl border p-6"
          style={{
            background: dark ? "#03182e" : "#eff6ff",
            borderColor: dark ? "#075985" : "#bfdbfe",
          }}
        >
          <Activity size={25} style={{ color: "#7dd3fc" }} />
          <p
            className="text-lg font-medium leading-7"
            style={{ color: dark ? "#bae6fd" : "#1e40af" }}
          >
            <strong>Demo mode.</strong> You’re looking at sample data.
            Connect the backend API to show live platform information.
          </p>
        </div>

        {/* STATISTICS CARDS */}
        <div className="mb-8 grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((item) => {
            const Icon = item.icon;

            return (
              <div
                key={item.title}
                className="rounded-3xl border p-7 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
                style={{ background: card, borderColor: border }}
              >
                <div className="flex items-center justify-between">
                  <p className="text-lg font-semibold" style={{ color: muted }}>
                    {item.title}
                  </p>

                  <div
                    className="rounded-2xl p-4"
                    style={{
                      background: `${item.color}20`,
                      color: item.color,
                    }}
                  >
                    <Icon size={28} />
                  </div>
                </div>

                <div className="mt-8 flex items-end justify-between">
                  <div>
                    <h3 className="text-5xl font-bold">{item.value}</h3>
                    <p className="mt-3 text-sm" style={{ color: "#2dd4bf" }}>
                      {item.change}{" "}
                      <span style={{ color: muted }}>vs last week</span>
                    </p>
                  </div>

                  <svg width="100" height="50" viewBox="0 0 100 50">
                    <polyline
                      points={item.points}
                      fill="none"
                      stroke={item.color}
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </div>
            );
          })}
        </div>

        {/* BLOOD GROUPS AND DONORS */}
        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">

          <section
            className="rounded-3xl border p-6"
            style={{ background: card, borderColor: border }}
          >
            <h3 className="text-xl font-bold">Requests by blood group</h3>
            <p className="mb-7 mt-2" style={{ color: muted }}>
              Distribution of blood requests
            </p>

            <div className="grid grid-cols-2 gap-6">
              {bloodGroups.map((item) => (
                <div key={item.name}>
                  <div className="mb-2 flex justify-between">
                    <span className="font-semibold">{item.name}</span>
                    <span style={{ color: muted }}>{item.value}</span>
                  </div>
                  <div
                    className="h-2.5 overflow-hidden rounded-full"
                    style={{ background: dark ? "#293449" : "#e2e8f0" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(item.value / 50) * 100}%`,
                        background: item.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section
            className="rounded-3xl border p-6"
            style={{ background: card, borderColor: border }}
          >
            <h3 className="text-xl font-bold">Donor availability</h3>
            <p className="mb-7 mt-2" style={{ color: muted }}>
              Current donor status distribution
            </p>

            <div className="flex flex-wrap items-center justify-center gap-10">
              <div
                className="flex h-48 w-48 items-center justify-center rounded-full"
                style={{
                  background: "conic-gradient(#2dd4bf 0% 68%, #fb7185 68% 88%, #64748b 88% 100%)",
                }}
              >
                <div
                  className="flex h-32 w-32 flex-col items-center justify-center rounded-full"
                  style={{ background: card }}
                >
                  <strong className="text-3xl">348</strong>
                  <span className="text-xs" style={{ color: muted }}>
                    Total donors
                  </span>
                </div>
              </div>

              <div className="space-y-5">
                {[
                  ["Available", "237", "#2dd4bf"],
                  ["Unavailable", "70", "#fb7185"],
                  ["Inactive", "41", "#64748b"],
                ].map(([name, value, color]) => (
                  <div key={name} className="flex items-center gap-3">
                    <span className="h-3 w-3 rounded-full" style={{ background: color }} />
                    <div>
                      <p className="text-sm" style={{ color: muted }}>{name}</p>
                      <strong>{value}</strong>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>

        {/* WEEKLY DEMAND AND INVITATIONS */}
        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section
            className="rounded-3xl border p-6"
            style={{ background: card, borderColor: border }}
          >
            <h3 className="text-xl font-bold">Weekly blood demand</h3>
            <p className="mb-8 mt-2" style={{ color: muted }}>
              Number of requests received this week
            </p>

            <div className="flex h-52 items-end justify-around gap-3">
              {weekly.map((item) => (
                <div key={item.day} className="flex h-full flex-1 flex-col items-center justify-end gap-3">
                  <span className="text-xs" style={{ color: muted }}>{item.value}</span>
                  <div
                    className="w-full max-w-12 rounded-t-lg"
                    style={{ height: `${item.value}%`, background: accent }}
                  />
                  <span className="text-xs" style={{ color: muted }}>{item.day}</span>
                </div>
              ))}
            </div>
          </section>

          <section
            className="rounded-3xl border p-6"
            style={{ background: card, borderColor: border }}
          >
            <h3 className="text-xl font-bold">Invitation statistics</h3>
            <p className="mb-8 mt-2" style={{ color: muted }}>
              Donor invitation performance
            </p>

            {[
              ["Sent", 86, 100, "#818cf8"],
              ["Accepted", 58, 67, "#2dd4bf"],
              ["Declined", 18, 21, "#fb7185"],
              ["Pending", 10, 12, "#fbbf24"],
            ].map(([name, value, percent, color]) => (
              <div key={name} className="mb-5">
                <div className="mb-2 flex justify-between text-sm">
                  <span>{name}</span>
                  <span style={{ color: muted }}>{value}</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full" style={{ background: dark ? "#293449" : "#e2e8f0" }}>
                  <div className="h-full rounded-full" style={{ width: `${percent}%`, background: color }} />
                </div>
              </div>
            ))}
          </section>
        </div>

        {/* BLOOD REQUEST TABLE */}
        <section
          className="mb-8 overflow-hidden rounded-3xl border"
          style={{ background: card, borderColor: border }}
        >
          <div className="flex flex-wrap items-center justify-between gap-4 p-6">
            <div>
              <h3 className="text-xl font-bold">Recent blood requests</h3>
              <p className="mt-2 text-sm" style={{ color: muted }}>
                Monitor and manage incoming requests
              </p>
            </div>

            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="rounded-xl border px-4 py-3"
              style={{ background: bg, color: text, borderColor: border }}
            >
              <option value="All">All statuses</option>
              <option value="Pending">Pending</option>
              <option value="Matched">Matched</option>
              <option value="Processing">Processing</option>
              <option value="Completed">Completed</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead style={{ background: dark ? "#1e293b" : "#f1f5f9", color: muted }}>
                <tr>
                  {["Request ID", "Patient", "Blood group", "Hospital", "Status"].map((heading) => (
                    <th key={heading} className="px-6 py-4">{heading}</th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {requests
                  .filter((request) => filter === "All" || request[4] === filter)
                  .map((request) => (
                    <tr key={request[0]} className="border-t" style={{ borderColor: border }}>
                      {request.map((value, index) => (
                        <td
                          key={index}
                          className="px-6 py-5"
                          style={{ color: index === 2 ? accent : text }}
                        >
                          {value}
                        </td>
                      ))}
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* AGENT ACTIVITY AND AUDIT LOGS */}
        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section
            className="rounded-3xl border p-6"
            style={{ background: card, borderColor: border }}
          >
            <div className="mb-7 flex items-center gap-3">
              <Bot size={25} style={{ color: accent }} />
              <div>
                <h3 className="text-xl font-bold">Agent activity</h3>
                <p className="text-sm" style={{ color: muted }}>Latest AI agent runs</p>
              </div>
            </div>

            <div className="space-y-6">
              {activities.map(([title, detail, time]) => (
                <div key={title} className="flex gap-4">
                  <CheckCircle2 size={23} className="shrink-0 text-emerald-400" />
                  <div>
                    <p className="font-semibold">{title}</p>
                    <p className="mt-1 text-sm" style={{ color: muted }}>{detail}</p>
                    <p className="mt-2 text-xs" style={{ color: muted }}>{time}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section
            className="rounded-3xl border p-6"
            style={{ background: card, borderColor: border }}
          >
            <div className="mb-7 flex items-center gap-3">
              <ScrollText size={25} style={{ color: accent }} />
              <div>
                <h3 className="text-xl font-bold">Audit logs</h3>
                <p className="text-sm" style={{ color: muted }}>Recent platform events</p>
              </div>
            </div>

            <div className="space-y-5">
              {auditLogs.map(([action, user, time]) => (
                <div
                  key={action}
                  className="flex justify-between gap-3 border-b pb-4"
                  style={{ borderColor: border }}
                >
                  <div>
                    <p className="font-semibold">{action}</p>
                    <p className="mt-1 text-sm" style={{ color: muted }}>{user}</p>
                  </div>
                  <span className="text-xs" style={{ color: muted }}>{time}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <footer
          className="border-t py-6 text-center text-sm"
          style={{ borderColor: border, color: muted }}
        >
          © 2026 BloodBridge AI · Admin Management Platform
        </footer>
      </div>
    </main>
  );
}
