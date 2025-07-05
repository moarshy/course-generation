import React from 'react';
import { formatDistanceToNow } from 'date-fns';

const CourseCard = ({ course, onView, onEdit, onDelete, onGenerate }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'draft': return 'bg-gray-100 text-gray-800';
      case 'generating': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'draft': return 'Draft';
      case 'generating': return 'Generating';
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      default: return 'Unknown';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow duration-200">
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {course.title}
          </h3>
          <p className="text-gray-600 text-sm mb-3">
            {course.description || 'No description provided'}
          </p>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(course.status)}`}>
          {getStatusText(course.status)}
        </span>
      </div>
      
      <div className="flex justify-between items-center text-sm text-gray-500 mb-4">
        <span>
          Created {formatDistanceToNow(new Date(course.created_at), { addSuffix: true })}
        </span>
        <span>
          Updated {formatDistanceToNow(new Date(course.updated_at), { addSuffix: true })}
        </span>
      </div>
      
      <div className="flex gap-2">
        {course.status === 'draft' && (
          <button
            onClick={() => onGenerate && onGenerate(course)}
            className="flex-1 bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600 transition-colors duration-200"
          >
            Generate Course
          </button>
        )}
        {course.status === 'generating' && (
          <button
            onClick={() => onGenerate && onGenerate(course)}
            className="flex-1 bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 transition-colors duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            View Progress
          </button>
        )}
        {course.status === 'completed' && (
          <button
            onClick={() => onView(course.course_id)}
            className="flex-1 bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 transition-colors duration-200"
          >
            View Course
          </button>
        )}
        {course.status === 'failed' && (
          <button
            onClick={() => onGenerate && onGenerate(course)}
            className="flex-1 bg-orange-500 text-white px-4 py-2 rounded-md hover:bg-orange-600 transition-colors duration-200"
          >
            Retry Generation
          </button>
        )}
        <button
          onClick={() => onEdit(course)}
          className="flex-1 bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600 transition-colors duration-200"
        >
          Edit
        </button>
        <button
          onClick={() => onDelete(course.course_id)}
          className="flex-1 bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600 transition-colors duration-200"
        >
          Delete
        </button>
      </div>
    </div>
  );
};

export default CourseCard; 