import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    // Deliberately blank rather than a spinner -- this state resolves
    // in well under a second (one local request to /auth/me) and a
    // flashed spinner would just be visual noise for something this
    // brief.
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
