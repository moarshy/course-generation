import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';
import EnhancedMarkdownRenderer from './EnhancedMarkdownRenderer';

const CourseViewer = ({ courseId, onClose }) => {
  const { getAccessTokenSilently } = useAuth0();
  const [courseData, setCourseData] = useState(null);
  const [currentModule, setCurrentModule] = useState(0);
  const [currentFile, setCurrentFile] = useState(0);
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

  useEffect(() => {
    console.log('CourseViewer: Component mounted with courseId:', courseId);
    loadCourseData();
  }, [courseId]);

  useEffect(() => {
    if (courseData && courseData.modules.length > 0) {
      loadFileContent();
    }
  }, [currentModule, currentFile, courseData]);

  const loadCourseData = async () => {
    try {
      console.log('CourseViewer: Loading course data for courseId:', courseId);
      setLoading(true);
      const token = await getAccessTokenSilently();
      console.log('CourseViewer: Got auth token, making API request...');
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/course-content`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('CourseViewer: Course data loaded successfully:', response.data);
      setCourseData(response.data);
    } catch (error) {
      console.error('CourseViewer: Error loading course data:', error);
      setError('Failed to load course content');
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async () => {
    if (!courseData) return;
    
    try {
      const token = await getAccessTokenSilently();
      const module = courseData.modules[currentModule];
      const fileName = module.files[currentFile];
      
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/course-content/${module.module_id}/${fileName}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setFileContent(response.data.content);
    } catch (error) {
      console.error('Error loading file content:', error);
      setFileContent('Failed to load content');
    }
  };

  const downloadCourse = async () => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/download`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${courseData.title.replace(/[^a-zA-Z0-9]/g, '_')}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error downloading course:', error);
      alert('Failed to download course materials');
    }
  };

  const getFileDisplayName = (fileName) => {
    const names = {
      '01_intro.md': '📖 Introduction',
      '02_main.md': '📚 Main Content', 
      '03_conclusion.md': '🎯 Conclusion',
      '04_assessments.md': '✅ Assessment',
      '05_summary.md': '📋 Summary'
    };
    return names[fileName] || fileName;
  };

  console.log('CourseViewer: Rendering with state:', { loading, error, courseData: !!courseData, showCourseViewer: true });

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading course content...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-md">
          <div className="text-red-500 mb-4">
            <svg className="w-12 h-12 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Course</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={onClose}
            className="w-full bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-7xl w-full h-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900 truncate">{courseData.title}</h1>
            <p className="text-gray-600 text-sm mt-1">
              Module {currentModule + 1} of {courseData.modules.length}: {courseData.modules[currentModule]?.title}
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={downloadCourse}
              className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-4-4m4 4l4-4m5-3v8a2 2 0 01-2 2H5a2 2 0 01-2-2v-8" />
              </svg>
              Download
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar Navigation */}
          <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900">Course Content</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              {courseData.modules.map((module, moduleIndex) => (
                <div key={module.module_id} className="border-b border-gray-200">
                  <button
                    onClick={() => {
                      setCurrentModule(moduleIndex);
                      setCurrentFile(0);
                    }}
                    className={`w-full p-4 text-left hover:bg-gray-100 transition-colors ${
                      currentModule === moduleIndex ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                    }`}
                  >
                    <div className="font-medium text-gray-900">{module.title}</div>
                    <div className="text-sm text-gray-600 mt-1">{module.files.length} sections</div>
                  </button>
                  
                  {currentModule === moduleIndex && (
                    <div className="bg-white">
                      {module.files.map((file, fileIndex) => (
                        <button
                          key={file}
                          onClick={() => setCurrentFile(fileIndex)}
                          className={`w-full p-3 pl-8 text-left text-sm hover:bg-gray-50 transition-colors border-l-2 ${
                            currentFile === fileIndex ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-transparent'
                          }`}
                        >
                          {getFileDisplayName(file)}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex-1 overflow-y-auto p-8">
              <div className="max-w-4xl mx-auto">
                <EnhancedMarkdownRenderer content={fileContent} />
              </div>
            </div>

            {/* Navigation Footer */}
            <div className="border-t border-gray-200 p-4 bg-gray-50">
              <div className="flex justify-between items-center">
                <button
                  onClick={() => {
                    if (currentFile > 0) {
                      setCurrentFile(currentFile - 1);
                    } else if (currentModule > 0) {
                      setCurrentModule(currentModule - 1);
                      setCurrentFile(courseData.modules[currentModule - 1].files.length - 1);
                    }
                  }}
                  disabled={currentModule === 0 && currentFile === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Previous
                </button>

                <div className="text-sm text-gray-600">
                  Section {currentFile + 1} of {courseData.modules[currentModule].files.length}
                </div>

                <button
                  onClick={() => {
                    if (currentFile < courseData.modules[currentModule].files.length - 1) {
                      setCurrentFile(currentFile + 1);
                    } else if (currentModule < courseData.modules.length - 1) {
                      setCurrentModule(currentModule + 1);
                      setCurrentFile(0);
                    }
                  }}
                  disabled={currentModule === courseData.modules.length - 1 && 
                           currentFile === courseData.modules[currentModule].files.length - 1}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CourseViewer; 