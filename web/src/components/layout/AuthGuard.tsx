import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getCurrentSession } from '@/mock/auth';

interface AuthGuardProps {
  children: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const session = getCurrentSession();
  const location = useLocation();

  if (!session) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }

  return <>{children}</>;
};
