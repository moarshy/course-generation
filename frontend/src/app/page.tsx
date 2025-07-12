"use client";

import { useState, useEffect } from 'react';
import { Plus, BookOpen, Clock, AlertCircle, CheckCircle, Play } from 'lucide-react';
import { getCourses, createCourse, updateCourse, deleteCourse, healthCheck } from '@/lib/api';
import { Course, CourseCreate, CourseStatus } from '@/lib/types';
import { useAuth } from '@/lib/auth-context';
import Header from '@/components/Header';
import ApiInterceptor from '@/components/ApiInterceptor';
import CreateCourseModal from '@/components/CreateCourseModal';
import EditCourseModal from '@/components/EditCourseModal';
import DeleteConfirmationModal from '@/components/DeleteConfirmationModal';
import CourseCard from '@/components/CourseCard';

export default function Dashboard() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'healthy' | 'unhealthy'>('checking');

  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      loadCourses();
      checkBackendHealth();
    }
  }, [authLoading, isAuthenticated]);

  const checkBackendHealth = async () => {
    try {
      await healthCheck();
      setBackendStatus('healthy');
    } catch (err) {
      setBackendStatus('unhealthy');
      setError('Backend is not responding. Please check if the server is running.');
    }
  };

  const loadCourses = async () => {
    try {
      const coursesData = await getCourses();
      setCourses(coursesData);
      setError(null);
    } catch (err: any) {
      setError(err.detail || 'Failed to load courses');
      console.error('Error loading courses:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCourse = async (courseData: CourseCreate) => {
    try {
      const newCourse = await createCourse(courseData);
      setCourses([newCourse, ...courses]);
      setIsCreateModalOpen(false);
      return newCourse;
    } catch (err: any) {
      console.error('Error creating course:', err);
      throw err;
    }
  };

  const handleEditCourse = async (course: Course, data: Partial<CourseCreate>) => {
    setSelectedCourse(course);
    setIsEditModalOpen(true);
  };

  const handleUpdateCourse = async (updateData: Partial<CourseCreate>) => {
    if (!selectedCourse) return;
    
    try {
      const updatedCourse = await updateCourse(selectedCourse.course_id, updateData);
      setCourses(courses.map(course => 
        course.course_id === selectedCourse.course_id ? updatedCourse : course
      ));
      setIsEditModalOpen(false);
      setSelectedCourse(null);
    } catch (err: any) {
      console.error('Error updating course:', err);
      throw err;
    }
  };

  const handleDeleteCourse = async (course: Course) => {
    setSelectedCourse(course);
    setIsDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!selectedCourse) return;
    
    try {
      await deleteCourse(selectedCourse.course_id);
      setCourses(courses.filter(course => course.course_id !== selectedCourse.course_id));
      setIsDeleteModalOpen(false);
      setSelectedCourse(null);
    } catch (err: any) {
      console.error('Error deleting course:', err);
      throw err;
    }
  };

  const getStatusColor = (status: CourseStatus) => {
    switch (status) {
      case CourseStatus.DRAFT:
        return 'text-gray-600';
      case CourseStatus.STAGE1_RUNNING:
      case CourseStatus.STAGE2_RUNNING:
      case CourseStatus.STAGE3_RUNNING:
      case CourseStatus.STAGE4_RUNNING:
        return 'text-blue-600';
      case CourseStatus.STAGE1_COMPLETE:
      case CourseStatus.STAGE2_COMPLETE:
      case CourseStatus.STAGE3_COMPLETE:
      case CourseStatus.STAGE4_COMPLETE:
        return 'text-green-600';
      case CourseStatus.STAGE1_FAILED:
      case CourseStatus.STAGE2_FAILED:
      case CourseStatus.STAGE3_FAILED:
      case CourseStatus.STAGE4_FAILED:
      case CourseStatus.FAILED:
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: CourseStatus) => {
    switch (status) {
      case CourseStatus.DRAFT:
        return <Clock className="w-4 h-4" />;
      case CourseStatus.STAGE1_RUNNING:
      case CourseStatus.STAGE2_RUNNING:
      case CourseStatus.STAGE3_RUNNING:
      case CourseStatus.STAGE4_RUNNING:
        return <Play className="w-4 h-4" />;
      case CourseStatus.STAGE4_COMPLETE:
        return <CheckCircle className="w-4 h-4" />;
      case CourseStatus.STAGE1_FAILED:
      case CourseStatus.STAGE2_FAILED:
      case CourseStatus.STAGE3_FAILED:
      case CourseStatus.STAGE4_FAILED:
      case CourseStatus.FAILED:
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <BookOpen className="w-4 h-4" />;
    }
  };

  // Loading state
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <ApiInterceptor />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  // Not authenticated - show login prompt
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <ApiInterceptor />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Course Creator</h2>
            <p className="text-gray-600 mb-6">
              Generate educational courses from GitHub repositories using AI.
              <br />
              Please sign in to get started.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Authenticated - show dashboard
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <ApiInterceptor />
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading courses...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <ApiInterceptor />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">My Courses</h1>
              <p className="mt-2 text-gray-600">
                Generate educational courses from GitHub repositories using AI
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {/* Backend Status */}
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  backendStatus === 'healthy' ? 'bg-green-500' :
                  backendStatus === 'unhealthy' ? 'bg-red-500' : 'bg-yellow-500'
                }`}></div>
                <span className="text-sm text-gray-600">
                  {backendStatus === 'healthy' ? 'Backend Connected' :
                   backendStatus === 'unhealthy' ? 'Backend Offline' : 'Checking...'}
                </span>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Course
              </button>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Courses Grid */}
        {courses.length === 0 ? (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No courses yet</h3>
            <p className="text-gray-600 mb-6">
              Create your first course by clicking the "New Course" button above.
            </p>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create First Course
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((course) => (
              <CourseCard
                key={course.course_id}
                course={course}
                onRefresh={loadCourses}
                onEdit={handleEditCourse}
                onDelete={handleDeleteCourse}
                getStatusColor={getStatusColor}
                getStatusIcon={getStatusIcon}
              />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      <CreateCourseModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateCourse}
      />

      <EditCourseModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setSelectedCourse(null);
        }}
        onSubmit={handleUpdateCourse}
        course={selectedCourse}
      />

      <DeleteConfirmationModal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setSelectedCourse(null);
        }}
        onConfirm={handleConfirmDelete}
        course={selectedCourse}
      />
    </div>
  );
}
