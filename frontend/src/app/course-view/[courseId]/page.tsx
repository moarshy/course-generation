"use client";

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Course, Stage3Response, Stage4Response, GenerationStatus } from '@/lib/types';
import { 
  getCourse, 
  getStage3Result, 
  getStage4Result, 
  getCourseContent,
  getGenerationStatus,
  downloadCourse
} from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import ApiInterceptor from '@/components/ApiInterceptor';
import CourseContentRenderer from '@/components/CourseContentRenderer';
import { 
  ArrowLeft, 
  BookOpen, 
  Clock, 
  Target, 
  FileText,
  Download,
  CheckCircle,
  ChevronRight,
  Layers,
  Play,
  User,
  Calendar,
  Globe
} from 'lucide-react';
import Link from 'next/link';
import 'highlight.js/styles/github.css';

interface CourseContent {
  modules: {
    [key: string]: {
      title: string;
      content: string;
      introduction?: string;
      main_content?: string;
      conclusion?: string;
      learning_objectives: string[];
      theme: string;
      sequence_order: number;
      assessment?: string;
      summary?: string;
    };
  };
  course_overview: {
    title: string;
    description: string;
    total_modules: number;
    complexity_level: string;
    estimated_duration: string;
  };
}

export default function CourseViewPage() {
  const params = useParams();
  const courseId = params.courseId as string;
  const { isAuthenticated, isLoading: authLoading, token } = useAuth();
  
  const [course, setCourse] = useState<Course | null>(null);
  const [stage3Data, setStage3Data] = useState<Stage3Response | null>(null);
  const [stage4Data, setStage4Data] = useState<Stage4Response | null>(null);
  const [courseContent, setCourseContent] = useState<CourseContent | null>(null);
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null);
  const [selectedModuleId, setSelectedModuleId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  // Load course data
  useEffect(() => {
    // Only proceed if authentication is ready and user is authenticated
    if (authLoading) return;
    
    if (!isAuthenticated) {
      setError('Authentication required. Please sign in.');
      setLoading(false);
      return;
    }

    // Wait for token to be available
    if (!token) {
      console.log('Waiting for token to be available...');
      return;
    }

    const loadCourseData = async () => {
      try {
        setLoading(true);
        console.log('Loading course data for courseId:', courseId);
        console.log('Using token:', token ? `${token.substring(0, 20)}...` : 'null');
        
        // Ensure token is set before making API calls
        const { setAuthToken } = await import('@/lib/api');
        setAuthToken(token);
        
        console.log('Fetching course and generation status...');
        const [courseData, statusData] = await Promise.all([
          getCourse(courseId).catch((err) => {
            console.error('Error fetching course:', err);
            throw err;
          }),
          getGenerationStatus(courseId).catch((err) => {
            console.error('Error fetching generation status:', err);
            return null;
          })
        ]);
          
        console.log('Course data:', courseData);
        console.log('Status data:', statusData);
          
        setCourse(courseData);
        setGenerationStatus(statusData);
          
        // Check if course generation is complete
        if (statusData?.stage_statuses?.COURSE_GENERATION === 'completed') {
          console.log('Course generation is complete, loading stage results...');
          // Load stage data and content
          const [stage3Result, stage4Result, content] = await Promise.all([
            getStage3Result(courseId).catch((err) => {
              console.error('Error fetching stage 3 result:', err);
              return null;
            }),
            getStage4Result(courseId).catch((err) => {
              console.error('Error fetching stage 4 result:', err);
              return null;
            }),
            getCourseContent(courseId).catch((err) => {
              console.error('Error fetching course content:', err);
              return null;
            })
          ]);
            
          console.log('Stage 3 result:', stage3Result);
          console.log('Stage 4 result:', stage4Result);
          console.log('Course content:', content);
            
          setStage3Data(stage3Result);
          setStage4Data(stage4Result);
          setCourseContent(content);
            
          // Set first module as selected by default
          if (content?.modules) {
            const moduleIds = Object.keys(content.modules);
            if (moduleIds.length > 0) {
              // Sort by sequence order
              const sortedModules = moduleIds.sort((a, b) => {
                const moduleA = content.modules[a];
                const moduleB = content.modules[b];
                return (moduleA.sequence_order || 0) - (moduleB.sequence_order || 0);
              });
              setSelectedModuleId(sortedModules[0]);
            }
          }
        } else {
          setError('Course generation is not complete yet. Please complete the course generation process first.');
        }
      } catch (err: any) {
        console.error('Full error object:', err);
        console.error('Error detail:', err.detail);
        console.error('Error message:', err.message);
        console.error('Error status:', err.status_code);
        setError(`Authentication/API Error: ${err.detail || err.message || 'Failed to load course data'}`);
      } finally {
        setLoading(false);
      }
    };

    if (courseId) {
      loadCourseData();
    }
  }, [courseId, authLoading, isAuthenticated, token]);

  const handleModuleComplete = (moduleId: string) => {
    // This function is no longer needed as completion tracking is removed.
    // Keeping it here for now, but it will not be called.
    console.log(`Module ${moduleId} marked as complete (audit-only).`);
  };

  const handleDownloadCourse = async () => {
    try {
      const response = await downloadCourse(courseId);
      
      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      
      // Get filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'course.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Create download link and click it
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      console.log('Course downloaded successfully');
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const getSortedModules = () => {
    if (!courseContent?.modules) return [];
    
    return Object.entries(courseContent.modules)
      .sort(([, a], [, b]) => (a.sequence_order || 0) - (b.sequence_order || 0))
      .map(([id, module]) => ({ id, ...module }));
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity?.toLowerCase()) {
      case 'beginner':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'intermediate':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'advanced':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading course...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-y-2">
            <Link 
              href={`/course-generation/${courseId}`}
              className="block text-blue-600 hover:text-blue-700"
            >
              → Go to Course Generation
            </Link>
            <Link href="/" className="block text-blue-600 hover:text-blue-700">
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!course || !courseContent) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Course content not found</p>
          <Link href="/" className="text-blue-600 hover:text-blue-700">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const sortedModules = getSortedModules();
  const selectedModule = selectedModuleId ? courseContent.modules[selectedModuleId] : null;
  const currentModuleIndex = sortedModules.findIndex(m => m.id === selectedModuleId);

  return (
    <div className="min-h-screen bg-gray-50">
      <ApiInterceptor />
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link 
                href="/" 
                className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Back to Dashboard</span>
              </Link>
              <div className="border-l border-gray-300 h-6"></div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{course.title}</h1>
                <p className="text-sm text-gray-600">Course Content</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={handleDownloadCourse}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                <span>Download Course</span>
              </button>
              <Link 
                href={`/course-generation/${courseId}`}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <FileText className="w-4 h-4" />
                <span>Edit Course</span>
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-8">
          {/* Sidebar - Course Overview & Module Navigation */}
          <div className="w-80 flex-shrink-0 space-y-6">
            {/* Course Overview */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Course Overview</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total Modules</span>
                  <span className="font-semibold text-gray-900">
                    {courseContent.course_overview?.total_modules || sortedModules.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Complexity</span>
                  <span className={`px-2 py-1 text-xs rounded-full border ${getComplexityColor(courseContent.course_overview?.complexity_level || 'intermediate')}`}>
                    {courseContent.course_overview?.complexity_level || 'intermediate'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Estimated Duration</span>
                  <span className="font-semibold text-gray-900">
                    {courseContent.course_overview?.estimated_duration || '4-6 hours'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Progress</span>
                  <span className="font-semibold text-gray-900">
                    N/A (Audit-only)
                  </span>
                </div>
              </div>
              
              {/* Progress Bar */}
              <div className="mt-4">
                <div className="flex justify-between text-sm text-gray-600 mb-1">
                  <span>Course Progress</span>
                  <span>N/A</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{ width: '0%' }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Module Navigation */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Course Modules</h2>
              <div className="space-y-2">
                {sortedModules.map((module, index) => (
                  <button
                    key={module.id}
                    onClick={() => setSelectedModuleId(module.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      selectedModuleId === module.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                          selectedModuleId === module.id
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {index + 1}
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900 text-sm">{module.title}</h3>
                          <p className="text-xs text-gray-500">{module.theme}</p>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 min-w-0">
            {selectedModule ? (
              <div className="bg-white rounded-xl shadow-sm border">
                {/* Module Header */}
                <div className="p-6 border-b bg-gradient-to-r from-blue-50 to-indigo-50">
                  <div className="flex items-center justify-between mb-4">
                    <h1 className="text-2xl font-bold text-gray-900">{selectedModule.title}</h1>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-600">Module {currentModuleIndex + 1} of {sortedModules.length}</span>
                      {/* Completion button removed */}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4 text-sm text-gray-600 mb-4">
                    <div className="flex items-center space-x-1">
                      <Target className="w-4 h-4" />
                      <span>{selectedModule.theme}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Clock className="w-4 h-4" />
                      <span>30-45 min</span>
                    </div>
                  </div>
                </div>

                {/* Module Content */}
                <div className="p-6">
                  <CourseContentRenderer
                    content={selectedModule.content}
                    introduction={selectedModule.introduction}
                    mainContent={selectedModule.main_content}
                    conclusion={selectedModule.conclusion}
                    title={selectedModule.title}
                    learningObjectives={selectedModule.learning_objectives}
                    assessment={selectedModule.assessment}
                    summary={selectedModule.summary}
                  />
                </div>

                {/* Module Navigation */}
                <div className="p-6 border-t bg-gray-50 flex justify-between items-center">
                  <button
                    onClick={() => {
                      const prevIndex = currentModuleIndex - 1;
                      if (prevIndex >= 0) {
                        setSelectedModuleId(sortedModules[prevIndex].id);
                      }
                    }}
                    disabled={currentModuleIndex === 0}
                    className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Previous Module</span>
                  </button>
                  
                  <div className="text-sm text-gray-600">
                    Module {currentModuleIndex + 1} of {sortedModules.length}
                  </div>
                  
                  <button
                    onClick={() => {
                      const nextIndex = currentModuleIndex + 1;
                      if (nextIndex < sortedModules.length) {
                        setSelectedModuleId(sortedModules[nextIndex].id);
                      }
                    }}
                    disabled={currentModuleIndex === sortedModules.length - 1}
                    className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <span>Next Module</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
                <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Select a Module</h2>
                <p className="text-gray-600">Choose a module from the sidebar to start learning</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 