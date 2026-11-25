
import ProtectedRoute from "../components/ProtectedRoute";
import RoleNavigation from "../components/RoleNavigation";

export default function HospitalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute allowedRole="hospital">
      <RoleNavigation />
      {children}
    </ProtectedRoute>
  );
}
