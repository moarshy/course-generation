"use client";

import { useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { setAuthToken } from '@/lib/api';

export default function ApiInterceptor() {
  const { token, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated && token) {
        setAuthToken(token);
      } else {
        setAuthToken(null);
      }
    }
  }, [token, isAuthenticated, isLoading]);

  return null; // This component doesn't render anything
} 