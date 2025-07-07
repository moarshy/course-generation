import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';
import { toast } from 'react-toastify';
import CourseViewer from './CourseViewer';

const Stage4Component = ({ course, taskStatus, stageData, onNext }) => {
  console.log('🚀 Stage4Component rendering!', { course, taskStatus });
  
  const { getAccessTokenSilently } = useAuth0();
  const [courseSummary, setCourseSummary] = useState(stageData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showCourseViewer, setShowCourseViewer] = useState(false);
  
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

  const [showCelebration, setShowCelebration] = useState(false);
  const [courseData, setCourseData] = useState(null);

  const isCompleted = taskStatus?.status === 'completed';
  const isLoading = taskStatus?.status === 'running';
  const isFailed = taskStatus?.status === 'failed';

  useEffect(() => {
    if (isCompleted && !showCelebration) {
      setTimeout(() => setShowCelebration(true), 500);
    }
  }, [isCompleted, showCelebration]);

  const handleComplete = () => {
    if (onNext) {
      onNext();
    }
  };

  const handleDownload = async () => {
    console.log('Download button clicked!', { 
      courseId: course?.id, 
      course: course 
    });
    try {
      setLoading(true);
      const token = await getAccessTokenSilently();
      console.log('Got auth token, making download request...');
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${course?.id}/download`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      console.log('Download response received:', response.status);
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${course.name.replace(/[^a-zA-Z0-9]/g, '_')}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Course materials downloaded successfully!');
    } catch (error) {
      console.error('Error downloading course:', error);
      toast.error('Failed to download course materials');
    } finally {
      setLoading(false);
    }
  };

  const handleViewCourse = () => {
    console.log('View Course button clicked!', { 
      courseId: course?.id, 
      course: course,
      showCourseViewer 
    });
    setShowCourseViewer(true);
    console.log('showCourseViewer set to true');
  };

  if (isFailed) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Course Generation Failed</h3>
        <p className="text-gray-600 mb-4">
          {taskStatus?.error_message || 'An error occurred during course generation'}
        </p>
        <button
          onClick={handleComplete}
          className="px-6 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 transition-colors duration-200"
        >
          Close
        </button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Generating Course Content</h3>
        <p className="text-gray-600 mb-4">
          Creating comprehensive course materials from your selected pathway...
        </p>
        
        <div className="max-w-md mx-auto">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progress</span>
            <span>{taskStatus?.progress_percentage || 0}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${taskStatus?.progress_percentage || 0}%` }}
            />
          </div>
        </div>

        <div className="mt-6 text-left max-w-md mx-auto">
          <h4 className="font-medium text-gray-900 mb-3">What's happening:</h4>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Generating module introductions</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Creating comprehensive content</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Developing assessments</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Generating summaries</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Exporting course materials</span>
            </li>
          </ul>
        </div>

        <div className="mt-6 text-xs text-gray-500">
          This process may take several minutes depending on the complexity of your course.
        </div>
      </div>
    );
  }

  if (isCompleted) {
    return (
      <div className="space-y-6">
        {/* Celebration Animation */}
        {showCelebration && (
          <div className="text-center">
            <div className="animate-bounce w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">🎉 Course Generated Successfully!</h3>
            <p className="text-gray-600">
              Your AI-powered course has been created and is ready for use
            </p>
          </div>
        )}

        {/* Course Summary */}
        <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6">
          <h4 className="font-bold text-gray-900 mb-4">Course Summary</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {taskStatus?.course_summary?.module_count || 0}
              </div>
              <div className="text-gray-600">Modules</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">100%</div>
              <div className="text-gray-600">Complete</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">AI</div>
              <div className="text-gray-600">Generated</div>
            </div>
          </div>
        </div>

        {/* Course Details */}
        <div className="bg-white border rounded-lg p-6">
          <h4 className="font-semibold text-gray-900 mb-4">Course Details</h4>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Course Title:</span>
              <span className="font-medium text-gray-900">
                {taskStatus?.course_summary?.title || course.title}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Description:</span>
              <span className="font-medium text-gray-900 max-w-xs text-right">
                {taskStatus?.course_summary?.description || course.description}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Export Path:</span>
              <span className="font-mono text-xs text-gray-700 max-w-xs text-right">
                {taskStatus?.course_summary?.export_path || 'Generated course files'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className="font-medium text-green-600">Ready for Use</span>
            </div>
          </div>
        </div>

        {/* Course Structure Preview */}
        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">Course Structure</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center">
              <div className="w-2 h-2 bg-blue-500 rounded-full mr-3"></div>
              <span>Welcome & Course Introduction</span>
            </div>
            {Array.from({ length: taskStatus?.course_summary?.module_count || 0 }, (_, i) => (
              <div key={i} className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-3"></div>
                <span>Module {i + 1}: Learning Content</span>
              </div>
            ))}
            <div className="flex items-center">
              <div className="w-2 h-2 bg-purple-500 rounded-full mr-3"></div>
              <span>Course Conclusion & Next Steps</span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleViewCourse}
            className="flex-1 bg-blue-500 text-white px-6 py-3 rounded-md hover:bg-blue-600 transition-colors duration-200 font-medium"
          >
            View Course
          </button>
          <button
            onClick={handleDownload}
            className="flex-1 bg-green-500 text-white px-6 py-3 rounded-md hover:bg-green-600 transition-colors duration-200 font-medium"
          >
            Download Materials
          </button>
          <button
            onClick={handleComplete}
            className="flex-1 bg-gray-500 text-white px-6 py-3 rounded-md hover:bg-gray-600 transition-colors duration-200 font-medium"
          >
            Close
          </button>
        </div>

        {/* Next Steps */}
        <div className="bg-yellow-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">Next Steps</h4>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>• Review and customize the generated course content</li>
            <li>• Add additional materials or examples as needed</li>
            <li>• Deploy to your learning management system</li>
            <li>• Gather feedback from learners for future improvements</li>
          </ul>
        </div>

        {/* Course Viewer Modal */}
        {showCourseViewer && course?.id && (
          <CourseViewer
            courseId={course.id}
            onClose={() => setShowCourseViewer(false)}
          />
        )}
      </div>
    );
  }

  return (
    <>
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Waiting for Course Generation</h3>
        <p className="text-gray-600">Course generation hasn't started yet.</p>
      </div>

      {/* Course Viewer Modal */}
      {showCourseViewer && course?.id && (
        <CourseViewer
          courseId={course.id}
          onClose={() => setShowCourseViewer(false)}
        />
      )}
    </>
  );
};

export default Stage4Component; 