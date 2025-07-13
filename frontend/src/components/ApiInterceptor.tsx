"use client";

import { useEffect } from 'react';
import { useAuth } from '@/lib/auth-context';
import { setAuthToken } from '@/lib/api';

export default function ApiInterceptor() {
  const { token, isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    console.log('ApiInterceptor useEffect:', { 
      isLoading, 
      isAuthenticated, 
      hasToken: !!token,
      tokenPreview: token ? `${token.substring(0, 20)}...` : 'null'
    });
    
    if (!isLoading) {
      if (isAuthenticated && token) {
        console.log('ApiInterceptor: Setting auth token');
        setAuthToken(token);
      } else {
        console.log('ApiInterceptor: Clearing auth token');
        setAuthToken(null);
      }
    }
  }, [token, isAuthenticated, isLoading]);

  return null; // This component doesn't render anything
} 