
import ProtectedRoute from "../components/ProtectedRoute";
import RoleNavigation from "../components/RoleNavigation";

export default function DonorLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <ProtectedRoute allowedRole="donor">
            <RoleNavigation />
            {children}
        </ProtectedRoute>
    );
}
