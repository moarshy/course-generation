"use client";

import { useParams } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Course, GenerationStatus } from '@/lib/types';
import { getCourse, getGenerationStatus } from '@/lib/api';
import StagesSidebar from '@/components/course-generation/StagesSidebar';
import Stage1Component from '@/components/course-generation/Stage1Component';
import Stage2Component from '@/components/course-generation/Stage2Component';
import Stage3Component from '@/components/course-generation/Stage3Component';
import Stage4Component from '@/components/course-generation/Stage4Component';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

type Stage = 'stage1' | 'stage2' | 'stage3' | 'stage4';

export default function CourseGenerationPage() {
  const params = useParams();
  const courseId = params.courseId as string;
  
  const [course, setCourse] = useState<Course | null>(null);
  const [currentStage, setCurrentStage] = useState<Stage>('stage1');
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load course data and status
  useEffect(() => {
    const loadCourseData = async () => {
      try {
        setLoading(true);
        const [courseData, statusData] = await Promise.all([
          getCourse(courseId),
          getGenerationStatus(courseId).catch(() => null) // Status might not exist yet
        ]);
        
        setCourse(courseData);
        setGenerationStatus(statusData);
        
        // Determine current stage based on status
        if (statusData) {
          if (statusData.stage_statuses.COURSE_GENERATION === 'completed') {
            setCurrentStage('stage4');
          } else if (statusData.stage_statuses.PATHWAY_BUILDING === 'completed') {
            setCurrentStage('stage4');
          } else if (statusData.stage_statuses.DOCUMENT_ANALYSIS === 'completed') {
            setCurrentStage('stage3');
          } else if (statusData.stage_statuses.CLONE_REPO === 'completed') {
            setCurrentStage('stage2');
          } else {
            setCurrentStage('stage1');
          }
        }
      } catch (err: any) {
        setError(err.detail || 'Failed to load course data');
      } finally {
        setLoading(false);
      }
    };

    if (courseId) {
      loadCourseData();
    }
  }, [courseId]);

  const handleStageChange = (stage: Stage) => {
    setCurrentStage(stage);
  };

  const handleStatusUpdate = (status: GenerationStatus) => {
    setGenerationStatus(status);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Loading course generation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️ Error</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <Link href="/" className="text-blue-600 hover:text-blue-700">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!course) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Course not found</p>
          <Link href="/" className="text-blue-600 hover:text-blue-700">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const renderStageContent = () => {
    switch (currentStage) {
      case 'stage1':
        return (
          <Stage1Component
            courseId={courseId}
            course={course}
            onStatusUpdate={handleStatusUpdate}
            onStageComplete={() => handleStageChange('stage2')}
          />
        );
      case 'stage2':
        return (
          <Stage2Component
            courseId={courseId}
            course={course}
            onStatusUpdate={handleStatusUpdate}
            onStageComplete={() => handleStageChange('stage3')}
          />
        );
      case 'stage3':
        return (
          <Stage3Component
            courseId={courseId}
            course={course}
            onStatusUpdate={handleStatusUpdate}
            onStageComplete={() => handleStageChange('stage4')}
          />
        );
      case 'stage4':
        return (
          <Stage4Component
            courseId={courseId}
            course={course}
            onStatusUpdate={handleStatusUpdate}
            onStageComplete={() => {
              // Stage 4 is the final stage - course generation is complete
              console.log('Course generation completed successfully!');
            }}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
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
                <p className="text-sm text-gray-600">Course Generation Workflow</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                Course ID: <span className="font-mono">{courseId}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-8">
          {/* Sidebar */}
          <div className="w-80 flex-shrink-0">
            <StagesSidebar
              currentStage={currentStage}
              generationStatus={generationStatus}
              onStageChange={handleStageChange}
            />
          </div>

          {/* Main Content Area */}
          <div className="flex-1 min-w-0">
            <div className="bg-white rounded-2xl shadow-sm border">
              {renderStageContent()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 