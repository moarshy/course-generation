"use client";

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Calendar, ExternalLink, Play, Trash2, MoreVertical, Edit, Eye } from 'lucide-react';
import { Course, CourseStatus, CourseCreate } from '@/lib/types';

interface CourseCardProps {
  course: Course;
  onRefresh: () => void;
  onEdit: (course: Course, data: Partial<CourseCreate>) => Promise<void>;
  onDelete: (course: Course) => Promise<void>;
  getStatusColor: (status: CourseStatus) => string;
  getStatusIcon: (status: CourseStatus) => React.ReactNode;
}

export default function CourseCard({ 
  course, 
  onRefresh, 
  onEdit, 
  onDelete, 
  getStatusColor, 
  getStatusIcon 
}: CourseCardProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const router = useRouter();
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMenuOpen]);

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        return 'Invalid date';
      }
      
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
      ];
      
      const year = date.getFullYear();
      const month = months[date.getMonth()];
      const day = date.getDate();
      
      return `${month} ${day}, ${year}`;
    } catch (error) {
      return 'Invalid date';
    }
  };

  const getStatusText = (status: CourseStatus) => {
    switch (status) {
      case CourseStatus.DRAFT:
        return 'Draft';
      case CourseStatus.STAGE1_RUNNING:
        return 'Cloning Repository';
      case CourseStatus.STAGE1_COMPLETE:
        return 'Repository Ready';
      case CourseStatus.STAGE2_RUNNING:
        return 'Analyzing Documents';
      case CourseStatus.STAGE2_COMPLETE:
        return 'Analysis Complete';
      case CourseStatus.STAGE3_RUNNING:
        return 'Building Pathway';
      case CourseStatus.STAGE3_COMPLETE:
        return 'Pathway Ready';
      case CourseStatus.STAGE4_RUNNING:
        return 'Generating Course';
      case CourseStatus.STAGE4_COMPLETE:
        return 'Course Complete';
      case CourseStatus.STAGE1_FAILED:
        return 'Repository Failed';
      case CourseStatus.STAGE2_FAILED:
        return 'Analysis Failed';
      case CourseStatus.STAGE3_FAILED:
        return 'Pathway Failed';
      case CourseStatus.STAGE4_FAILED:
        return 'Generation Failed';
      case CourseStatus.FAILED:
        return 'Failed';
      default:
        return 'Unknown';
    }
  };

  const canStartGeneration = (status: CourseStatus) => {
    return status === CourseStatus.DRAFT;
  };

  const canContinue = (status: CourseStatus) => {
    return [
      CourseStatus.STAGE1_COMPLETE,
      CourseStatus.STAGE2_COMPLETE,
      CourseStatus.STAGE3_COMPLETE,
      CourseStatus.STAGE4_COMPLETE,
    ].includes(status);
  };

  const isProcessing = (status: CourseStatus) => {
    return [
      CourseStatus.STAGE1_RUNNING,
      CourseStatus.STAGE2_RUNNING,
      CourseStatus.STAGE3_RUNNING,
      CourseStatus.STAGE4_RUNNING,
    ].includes(status);
  };

  const isComplete = (status: CourseStatus) => {
    return status === CourseStatus.STAGE4_COMPLETE;
  };

  const handleCardClick = () => {
    if (canContinue(course.status) || isProcessing(course.status)) {
      router.push(`/course-generation/${course.course_id}`);
    }
  };

  const handleStartGeneration = (e: React.MouseEvent) => {
    e.stopPropagation();
    router.push(`/course-generation/${course.course_id}`);
  };

  const handleOpenRepo = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (course.repo_url) {
      window.open(course.repo_url, '_blank');
    }
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsMenuOpen(false);
    // The parent component will handle showing the edit modal
    // We'll trigger this via a callback
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsMenuOpen(false);
    // The parent component will handle showing the delete modal
    // We'll trigger this via a callback
  };

  const handleViewCourse = (e: React.MouseEvent) => {
    e.stopPropagation();
    router.push(`/course-view/${course.course_id}`);
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-md border hover:shadow-lg transition-shadow duration-200 overflow-hidden ${
        canContinue(course.status) || isProcessing(course.status) ? 'cursor-pointer' : ''
      }`}
      onClick={handleCardClick}
    >
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{course.title}</h3>
            {course.description && (
              <p className="text-gray-600 text-sm line-clamp-2">{course.description}</p>
            )}
          </div>
          <div className="relative" ref={menuRef}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsMenuOpen(!isMenuOpen);
              }}
              className="text-gray-400 hover:text-gray-600 p-1"
            >
              <MoreVertical className="w-5 h-5" />
            </button>
            {isMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border">
                <div className="py-1">
                  {course.repo_url && (
                    <button
                      onClick={handleOpenRepo}
                      className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                    >
                      <ExternalLink className="w-4 h-4 mr-2" />
                      Open Repository
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsMenuOpen(false);
                      onEdit(course, { title: course.title, description: course.description || '' });
                    }}
                    className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                  >
                    <Edit className="w-4 h-4 mr-2" />
                    Edit Course
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsMenuOpen(false);
                      onDelete(course);
                    }}
                    className="flex items-center px-4 py-2 text-sm text-red-600 hover:bg-gray-100 w-full text-left"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete Course
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center justify-between mb-4">
          <div className={`flex items-center space-x-2 ${getStatusColor(course.status)}`}>
            {getStatusIcon(course.status)}
            <span className="text-sm font-medium">{getStatusText(course.status)}</span>
          </div>
          {isProcessing(course.status) && (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-xs text-gray-500">Processing...</span>
            </div>
          )}
        </div>

        {/* Repository URL */}
        {course.repo_url && (
          <div className="mb-4">
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <ExternalLink className="w-4 h-4" />
              <span className="truncate">{course.repo_url}</span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-1 text-xs text-gray-500">
            <Calendar className="w-4 h-4" />
            <span>Created {formatDate(course.created_at)}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            {canStartGeneration(course.status) && (
              <button
                onClick={handleStartGeneration}
                className="inline-flex items-center px-3 py-1 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                <Play className="w-4 h-4 mr-1" />
                Start Generation
              </button>
            )}
            
            {isComplete(course.status) && (
              <button
                onClick={handleViewCourse}
                className="inline-flex items-center px-3 py-1 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
              >
                <Eye className="w-4 h-4 mr-1" />
                View Course
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 