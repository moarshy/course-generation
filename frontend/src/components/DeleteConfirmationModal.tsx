"use client";

import { useState } from 'react';
import { AlertTriangle, X, Trash2 } from 'lucide-react';
import { Course } from '@/lib/types';

interface DeleteConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  course: Course | null;
}

export default function DeleteConfirmationModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  course 
}: DeleteConfirmationModalProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setIsDeleting(true);
    setError(null);
    
    try {
      await onConfirm();
      onClose();
    } catch (err: any) {
      setError(err.detail || 'Failed to delete course');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClose = () => {
    if (!isDeleting) {
      setError(null);
      onClose();
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !isDeleting) {
      handleClose();
    }
  };

  if (!isOpen || !course) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black bg-opacity-60 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="relative w-full max-w-lg mx-auto p-6">
        {/* Modal Content */}
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
          {/* Header with danger styling */}
          <div className="bg-gradient-to-r from-red-50 to-red-100 px-8 py-6 border-b border-red-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                  <Trash2 className="w-5 h-5 text-red-600" />
                </div>
                <h3 className="text-2xl font-bold text-red-900">Delete Course</h3>
              </div>
              <button
                onClick={handleClose}
                disabled={isDeleting}
                className="text-red-400 hover:text-red-600 transition-colors disabled:opacity-50 p-1"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="px-8 py-6">
            {error && (
              <div className="mb-6 bg-red-50 border-l-4 border-red-500 rounded-r-lg p-4">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5 text-red-600" />
                  <p className="text-base font-semibold text-red-800">{error}</p>
                </div>
              </div>
            )}

            <div className="space-y-6">
              {/* Warning Message */}
              <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6">
                <div className="flex items-start space-x-4">
                  <AlertTriangle className="w-8 h-8 text-red-600 flex-shrink-0 mt-1" />
                  <div className="flex-1">
                    <h4 className="text-lg font-bold text-red-900 mb-2">
                      Are you absolutely sure?
                    </h4>
                    <p className="text-base text-red-800 leading-relaxed">
                      This action cannot be undone. This will permanently delete the course and all associated data.
                    </p>
                  </div>
                </div>
              </div>

              {/* Course Details */}
              <div className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                <h5 className="text-lg font-bold text-gray-900 mb-4">Course Details</h5>
                <div className="space-y-3">
                  <div className="flex items-start space-x-3">
                    <span className="text-sm font-semibold text-gray-600 min-w-[80px]">Title:</span>
                    <span className="text-base font-medium text-gray-900 flex-1">{course.title}</span>
                  </div>
                  {course.description && (
                    <div className="flex items-start space-x-3">
                      <span className="text-sm font-semibold text-gray-600 min-w-[80px]">Description:</span>
                      <span className="text-base font-medium text-gray-900 flex-1">{course.description}</span>
                    </div>
                  )}
                  <div className="flex items-start space-x-3">
                    <span className="text-sm font-semibold text-gray-600 min-w-[80px]">Created:</span>
                    <span className="text-base font-medium text-gray-900 flex-1">
                      {new Date(course.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Final Warning */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">⚠️</div>
                  <div>
                    <p className="text-sm font-bold text-yellow-800">
                      This action is irreversible and will permanently delete all course data.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="bg-gray-50 px-8 py-6 border-t border-gray-200">
            <div className="flex justify-end space-x-4">
              <button
                type="button"
                onClick={handleClose}
                disabled={isDeleting}
                className="px-8 py-3 text-base font-bold text-gray-700 bg-white border-2 border-gray-300 rounded-xl hover:bg-gray-50 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={isDeleting}
                className="px-8 py-3 text-base font-bold text-white bg-red-600 border-2 border-red-600 rounded-xl hover:bg-red-700 hover:border-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                {isDeleting ? (
                  <span className="flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Deleting...</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-2">
                    <Trash2 className="w-4 h-4" />
                    <span>Delete Course</span>
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 