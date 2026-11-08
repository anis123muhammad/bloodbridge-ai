
export type UserRole = "admin" | "donor" | "hospital";

export type AuthUser = {
    name: string;
    email: string;
    role: UserRole;
    token?: string;
};

const STORAGE_KEY = "bloodbridge_user";

export function getUser(): AuthUser | null {
    if (typeof window === "undefined") return null;

    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) as AuthUser : null;
    } catch {
        return null;
    }
}

export function saveUser(user: AuthUser) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

export function getToken(): string | null {
    const user = getUser();
    return user?.token || null;
}

export function getAuthHeaders(): Record<string, string> {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
}

export function logout() {
    localStorage.removeItem(STORAGE_KEY);
}

export function getDashboardPath(role: UserRole) {
    if (role === "hospital") return "/hospital";
    if (role === "donor") return "/donor";
    return "/admin";
}
