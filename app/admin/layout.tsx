
import ProtectedRoute from "../components/ProtectedRoute";
import RoleNavigation from "../components/RoleNavigation";

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <ProtectedRoute allowedRole="admin">
            <RoleNavigation />
            {children}
        </ProtectedRoute>
    );
}
