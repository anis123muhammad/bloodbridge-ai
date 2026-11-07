
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, type UserRole } from "../lib/auth";

type Props = {
    children: React.ReactNode;
    allowedRole: UserRole;
};

export default function ProtectedRoute({ children, allowedRole }: Props) {
    const router = useRouter();
    const [authorized, setAuthorized] = useState(false);

    useEffect(() => {
        const user = getUser();

        if (!user) {
            router.replace("/login");
            return;
        }

        if (user.role !== allowedRole) {
            router.replace("/unauthorized");
            return;
        }

        setAuthorized(true);
    }, [allowedRole, router]);

    if (!authorized) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
                <p className="text-sm text-slate-400">
                    Redirecting or checking access...
                </p>
            </div>
        );
    }

    return <>{children}</>;
}
