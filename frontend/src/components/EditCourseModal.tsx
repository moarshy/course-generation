"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { X, BookOpen, Save } from 'lucide-react';
import { Course, CourseCreate } from '@/lib/types';

const courseSchema = z.object({
  title: z.string().min(1, 'Title is required').max(255, 'Title must be less than 255 characters'),
  description: z.string().max(1000, 'Description must be less than 1000 characters').optional(),
});

type CourseFormData = z.infer<typeof courseSchema>;

interface EditCourseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: Partial<CourseCreate>) => Promise<any>;
  course: Course | null;
}

export default function EditCourseModal({ isOpen, onClose, onSubmit, course }: EditCourseModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<CourseFormData>({
    resolver: zodResolver(courseSchema),
  });

  // Reset form when course changes
  useEffect(() => {
    if (course) {
      reset({
        title: course.title,
        description: course.description || '',
      });
    }
  }, [course, reset]);

  const handleFormSubmit = async (data: CourseFormData) => {
    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit(data);
      onClose();
    } catch (err: any) {
      setError(err.detail || 'Failed to update course');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setError(null);
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
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
          {/* Header with gradient */}
          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 px-8 py-6 border-b border-emerald-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0 w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-emerald-900">Edit Course</h3>
                                      <p className="text-sm text-emerald-700 mt-1">Last updated: {(() => {
                      try {
                        const date = new Date(course.updated_at);
                        if (isNaN(date.getTime())) return 'Unknown';
                        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                        return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
                      } catch {
                        return 'Unknown';
                      }
                    })()}</p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="text-emerald-400 hover:text-emerald-600 transition-colors p-1"
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
                  <div className="w-5 h-5 text-red-600">⚠️</div>
                  <p className="text-base font-semibold text-red-800">{error}</p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
              <div>
                <label htmlFor="title" className="block text-base font-bold text-gray-900 mb-3">
                  Course Title
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <input
                  {...register('title')}
                  type="text"
                  id="title"
                  className={`w-full px-4 py-4 text-lg font-medium border-2 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all duration-200 ${
                    errors.title ? 'border-red-400 bg-red-50' : 'border-gray-300 bg-white hover:border-gray-400'
                  }`}
                  placeholder="Enter an engaging course title..."
                />
                {errors.title && (
                  <p className="mt-2 text-sm font-semibold text-red-700 flex items-center space-x-1">
                    <span>⚠️</span>
                    <span>{errors.title.message}</span>
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="description" className="block text-base font-bold text-gray-900 mb-3">
                  Course Description
                  <span className="text-gray-500 text-sm font-normal ml-2">(Optional)</span>
                </label>
                <textarea
                  {...register('description')}
                  id="description"
                  rows={4}
                  className={`w-full px-4 py-4 text-lg font-medium border-2 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all duration-200 resize-none ${
                    errors.description ? 'border-red-400 bg-red-50' : 'border-gray-300 bg-white hover:border-gray-400'
                  }`}
                  placeholder="Describe what students will learn in this course..."
                />
                {errors.description && (
                  <p className="mt-2 text-sm font-semibold text-red-700 flex items-center space-x-1">
                    <span>⚠️</span>
                    <span>{errors.description.message}</span>
                  </p>
                )}
              </div>

              {/* Info box */}
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <div className="flex items-start space-x-3">
                  <div className="text-emerald-600 text-lg">📝</div>
                  <div>
                    <p className="text-sm font-semibold text-emerald-900">
                      Course Updates
                    </p>
                    <p className="text-sm text-emerald-700 mt-1">
                      Changes will be saved immediately. Course generation status and generated content will remain unchanged.
                    </p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end space-x-4 pt-6">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-8 py-3 text-base font-bold text-gray-700 bg-white border-2 border-gray-300 rounded-xl hover:bg-gray-50 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-all duration-200 shadow-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-8 py-3 text-base font-bold text-white bg-emerald-600 border-2 border-emerald-600 rounded-xl hover:bg-emerald-700 hover:border-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  {isSubmitting ? (
                    <span className="flex items-center space-x-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Saving...</span>
                    </span>
                  ) : (
                    <span className="flex items-center space-x-2">
                      <Save className="w-4 h-4" />
                      <span>Save Changes</span>
                    </span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
} 