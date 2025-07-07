import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

const CourseViewerPage = () => {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const { getAccessTokenSilently } = useAuth0();
  
  const [courseData, setCourseData] = useState(null);
  const [currentModule, setCurrentModule] = useState(0);
  const [currentFile, setCurrentFile] = useState(0);
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

  useEffect(() => {
    console.log('CourseViewerPage: Loading course data for courseId:', courseId);
    loadCourseData();
  }, [courseId]);

  useEffect(() => {
    if (courseData && courseData.modules.length > 0) {
      loadFileContent();
    }
  }, [currentModule, currentFile, courseData]);

  const loadCourseData = async () => {
    try {
      setLoading(true);
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/course-content`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('CourseViewerPage: Course data loaded successfully:', response.data);
      setCourseData(response.data);
    } catch (error) {
      console.error('CourseViewerPage: Error loading course data:', error);
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading course content...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md mx-auto text-center">
          <div className="text-red-500 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Course</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!courseData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">No course data available</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(-1)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </button>
              <div>
                <h1 className="text-xl font-bold text-gray-900">{courseData.title}</h1>
                <p className="text-sm text-gray-600">
                  Module {currentModule + 1} of {courseData.modules.length}: {courseData.modules[currentModule]?.title}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={downloadCourse}
                className="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600 transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-4-4m4 4l4-4m5-3v8a2 2 0 01-2 2H5a2 2 0 01-2-2v-8" />
                </svg>
                Download Course
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto flex">
        {/* Sidebar Navigation */}
        <div className="w-80 bg-white shadow-sm border-r border-gray-200 min-h-[calc(100vh-4rem)]">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">Course Content</h3>
          </div>
          
          <div className="overflow-y-auto max-h-[calc(100vh-8rem)]">
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
                        className={`w-full px-6 py-3 text-left text-sm hover:bg-gray-50 transition-colors ${
                          currentFile === fileIndex ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600'
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

        {/* Main Content */}
        <div className="flex-1 bg-white">
          <div className="p-8 max-w-4xl mx-auto">
            <div className="prose prose-lg max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  }
                }}
              >
                {fileContent}
              </ReactMarkdown>
            </div>
            
            {/* Navigation Footer */}
            <div className="mt-12 pt-8 border-t border-gray-200 flex justify-between items-center">
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
                className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <span>Previous</span>
              </button>

              <button
                onClick={() => {
                  const currentModuleData = courseData.modules[currentModule];
                  if (currentFile < currentModuleData.files.length - 1) {
                    setCurrentFile(currentFile + 1);
                  } else if (currentModule < courseData.modules.length - 1) {
                    setCurrentModule(currentModule + 1);
                    setCurrentFile(0);
                  }
                }}
                disabled={
                  currentModule === courseData.modules.length - 1 && 
                  currentFile === courseData.modules[currentModule].files.length - 1
                }
                className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span>Next</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CourseViewerPage; 