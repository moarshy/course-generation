"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Course, GenerationStatus, Stage4Response, Stage4Input, Stage3Response } from '@/lib/types';
import { 
  startStage4, 
  getGenerationStatus, 
  getStage4Result,
  getStage3Result,
  getCourseContent
} from '@/lib/api';
import { 
  BookOpen, 
  Play, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  FileText,
  RefreshCw,
  Download,
  Layers,
  Target,
  Zap
} from 'lucide-react';

const stage4Schema = z.object({
  selected_complexity: z.string().min(1, 'Complexity level is required'),
  additional_instructions: z.string().optional()
});

type Stage4FormData = z.infer<typeof stage4Schema>;

interface Stage4ComponentProps {
  courseId: string;
  course: Course;
  onStatusUpdate: (status: GenerationStatus) => void;
  onStageComplete: () => void;
}

export default function Stage4Component({ 
  courseId, 
  course, 
  onStatusUpdate, 
  onStageComplete 
}: Stage4ComponentProps) {
  const [stage4Data, setStage4Data] = useState<Stage4Response | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [selectedComplexity, setSelectedComplexity] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [courseContent, setCourseContent] = useState<any>(null);
  const [stage3Data, setStage3Data] = useState<Stage3Response | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue
  } = useForm<Stage4FormData>({
    resolver: zodResolver(stage4Schema),
    defaultValues: {
      selected_complexity: 'intermediate',
      additional_instructions: ''
    }
  });

  const watchedComplexity = watch('selected_complexity');
  const additionalInstructions = watch('additional_instructions');

  // Load existing data on component mount
  useEffect(() => {
    let mounted = true;
    
    const loadExistingData = async () => {
      try {
        const status = await getGenerationStatus(courseId).catch(() => null);
        
        if (!mounted) return;
        
        // Load Stage 3 data to pre-populate complexity
        try {
          const stage3Result = await getStage3Result(courseId);
          if (mounted && stage3Result) {
            setStage3Data(stage3Result);
            // Get complexity from Stage 3 pathways
            const stage3Complexity = stage3Result.pathways?.[0]?.complexity_level || stage3Result.pathways?.[0]?.complexity || 'intermediate';
            setValue('selected_complexity', stage3Complexity);
          }
        } catch (err) {
          console.log('Stage 3 data not available, using default complexity');
        }
        
        if (status?.stage_statuses?.COURSE_GENERATION === 'completed') {
          setIsComplete(true);
          setHasStarted(true);
          
          // Load Stage 4 results
          const stage4Result = await getStage4Result(courseId);
          if (mounted) {
            setStage4Data(stage4Result);
            // Also load course content
            try {
              const content = await getCourseContent(courseId);
              setCourseContent(content);
            } catch (err) {
              console.log('Course content not available yet');
            }
          }
        } else if (status?.stage_statuses?.COURSE_GENERATION === 'in_progress') {
          setHasStarted(true);
          setPollingStatus(true);
          pollForStageCompletion();
        }
      } catch (err) {
        console.error('Error loading existing data:', err);
      }
    };

    loadExistingData();
    
    return () => {
      mounted = false;
    };
  }, [courseId]);

  // Start Stage 4 course generation
  const handleStartCourseGeneration = async (data: Stage4FormData) => {
    if (isStarting) {
      return; // Prevent multiple starts
    }
    
    setIsLoading(true);
    setIsStarting(true);
    setError(null);
    setHasStarted(true);
    setSelectedComplexity(data.selected_complexity);

    try {
      await startStage4(courseId, data);
      
      // Start polling for completion
      setPollingStatus(true);
      pollForStageCompletion();
    } catch (err: any) {
      setError(err.detail || 'Failed to start course generation');
      setHasStarted(false);
    } finally {
      setIsLoading(false);
      setIsStarting(false);
    }
  };

  // Poll for stage completion
  const pollForStageCompletion = async () => {
    const maxAttempts = 240; // 20 minutes with 5-second intervals
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await getGenerationStatus(courseId);
        onStatusUpdate(status);

        if (status.stage_statuses.COURSE_GENERATION === 'completed') {
          setIsComplete(true);
          setPollingStatus(false);
          
          // Load Stage 4 results
          const stage4Result = await getStage4Result(courseId);
          setStage4Data(stage4Result);
          
          // Load course content
          try {
            const content = await getCourseContent(courseId);
            setCourseContent(content);
          } catch (err) {
            console.log('Course content loading failed, will retry');
          }
          
          return;
        }

        if (status.stage_statuses.COURSE_GENERATION === 'failed') {
          setError('Course generation failed. Please try again.');
          setPollingStatus(false);
          setHasStarted(false);
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          setError('Course generation timeout. Please try again.');
          setPollingStatus(false);
          setHasStarted(false);
        }
      } catch (err: any) {
        setError(err.detail || 'Failed to check course generation status');
        setPollingStatus(false);
        setHasStarted(false);
      }
    };

    poll();
  };

  const getComplexityColor = (complexity: string) => {
    switch (complexity.toLowerCase()) {
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

  const getComplexityDescription = (complexity: string) => {
    switch (complexity.toLowerCase()) {
      case 'beginner':
        return 'Generate accessible content with detailed explanations and step-by-step guidance';
      case 'intermediate':
        return 'Create balanced content with practical examples and moderate complexity';
      case 'advanced':
        return 'Produce comprehensive content with advanced concepts and expert-level details';
      default:
        return 'Standard complexity level';
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Stage 4: Course Content Generation</h2>
        <p className="text-gray-600">
          Generate comprehensive course content with markdown files for each module based on your learning pathways.
        </p>
      </div>

      {/* Configuration Form */}
      {!isComplete && (
        <div className="mb-8">
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <BookOpen className="w-6 h-6 text-indigo-600" />
              <h3 className="text-lg font-semibold text-indigo-900">Content Generation Configuration</h3>
            </div>
            
            {/* Stage 3 Summary */}
            {stage3Data && (
              <div className="bg-white border border-indigo-100 rounded-lg p-4 mb-6">
                <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                  <Layers className="w-4 h-4 text-indigo-600 mr-2" />
                  Learning Pathway Summary
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Pathways:</span>
                    <span className="font-medium ml-1">{stage3Data.pathways?.length || 0}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Total Modules:</span>
                    <span className="font-medium ml-1">
                      {stage3Data.pathways?.reduce((total, pathway) => total + (pathway.modules?.length || 0), 0) || 0}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Stage 3 Complexity:</span>
                    <span className={`px-2 py-1 text-xs rounded-full border ml-1 ${getComplexityColor(stage3Data.pathways?.[0]?.complexity || 'intermediate')}`}>
                      {stage3Data.pathways?.[0]?.complexity || 'intermediate'}
                    </span>
                  </div>
                </div>
              </div>
            )}
            
            <form onSubmit={handleSubmit(handleStartCourseGeneration)} className="space-y-6">
              {/* Complexity Level */}
              <div>
                <label htmlFor="selected_complexity" className="block text-sm font-semibold text-gray-900 mb-3">
                  Content Complexity Level
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {['beginner', 'intermediate', 'advanced'].map((level) => (
                    <label key={level} className="relative">
                      <input
                        {...register('selected_complexity')}
                        type="radio"
                        value={level}
                        className="sr-only"
                        disabled={hasStarted}
                      />
                      <div className={`cursor-pointer border-2 rounded-xl p-4 transition-all ${
                        watchedComplexity === level
                          ? 'border-indigo-500 bg-indigo-50'
                          : 'border-gray-200 hover:border-gray-300'
                      } ${hasStarted ? 'opacity-50 cursor-not-allowed' : ''}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-gray-900 capitalize">{level}</span>
                          <span className={`px-2 py-1 text-xs rounded-full border ${getComplexityColor(level)}`}>
                            {level}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">
                          {getComplexityDescription(level)}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
                {errors.selected_complexity && (
                  <p className="mt-2 text-sm text-red-600">{errors.selected_complexity.message}</p>
                )}
              </div>

              {/* Additional Instructions */}
              <div>
                <label htmlFor="additional_instructions" className="block text-sm font-semibold text-gray-900 mb-2">
                  Additional Content Instructions (Optional)
                </label>
                <textarea
                  {...register('additional_instructions')}
                  id="additional_instructions"
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                  placeholder="Specify any particular content style, format preferences, or special requirements for the course generation..."
                  disabled={hasStarted}
                />
                <p className="mt-2 text-sm text-gray-500">
                  Example: "Include code examples in Python and JavaScript" or "Focus on practical implementation with real-world scenarios"
                </p>
              </div>

              {!hasStarted && (
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex items-center space-x-2 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      <span>Starting...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-5 h-5" />
                      <span>Generate Course Content</span>
                    </>
                  )}
                </button>
              )}
            </form>
          </div>
        </div>
      )}

      {/* Status Display */}
      {hasStarted && (
        <div className="mb-8">
          <div className={`border rounded-xl p-6 ${
            isComplete ? 'bg-green-50 border-green-200' : 
            pollingStatus ? 'bg-blue-50 border-blue-200' : 
            'bg-red-50 border-red-200'
          }`}>
            <div className="flex items-center space-x-3">
              {isComplete ? (
                <>
                  <CheckCircle className="w-6 h-6 text-green-600" />
                  <div>
                    <h3 className="text-lg font-semibold text-green-900">Course Generation Complete!</h3>
                    <p className="text-green-700">
                      Successfully generated course content with complexity level: {selectedComplexity}
                    </p>
                  </div>
                </>
              ) : pollingStatus ? (
                <>
                  <Clock className="w-6 h-6 text-blue-600 animate-pulse" />
                  <div>
                    <h3 className="text-lg font-semibold text-blue-900">Generating Course Content</h3>
                    <p className="text-blue-700">
                      AI is creating comprehensive course materials including markdown content for each module...
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <AlertCircle className="w-6 h-6 text-red-600" />
                  <div>
                    <h3 className="text-lg font-semibold text-red-900">Generation Failed</h3>
                    <p className="text-red-700">Please try again or check your configuration.</p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-8">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <p className="text-sm font-medium text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results Display */}
      {isComplete && stage4Data && (
        <div className="space-y-8">
          {/* Course Summary */}
          <div className="bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 border border-green-200 rounded-2xl p-8 shadow-lg">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-green-900">Course Generation Complete!</h3>
                <p className="text-green-700">Your course content has been successfully generated</p>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white rounded-xl p-6 shadow-sm border border-green-100">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <BookOpen className="w-5 h-5 text-green-600" />
                  </div>
                  <span className="text-sm font-semibold text-gray-600">Course Title</span>
                </div>
                <p className="text-xl font-bold text-gray-900">{stage4Data.course_summary.title}</p>
              </div>
              
              <div className="bg-white rounded-xl p-6 shadow-sm border border-blue-100">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Layers className="w-5 h-5 text-blue-600" />
                  </div>
                  <span className="text-sm font-semibold text-gray-600">Modules Generated</span>
                </div>
                <p className="text-3xl font-bold text-blue-900">{stage4Data.course_summary.module_count}</p>
              </div>
              
              <div className="bg-white rounded-xl p-6 shadow-sm border border-purple-100">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Target className="w-5 h-5 text-purple-600" />
                  </div>
                  <span className="text-sm font-semibold text-gray-600">Complexity</span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`px-3 py-1 text-sm rounded-full border font-medium ${getComplexityColor(selectedComplexity)}`}>
                    {selectedComplexity}
                  </span>
                </div>
              </div>
              
              <div className="bg-white rounded-xl p-6 shadow-sm border border-emerald-100">
                <div className="flex items-center space-x-3 mb-3">
                  <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                  </div>
                  <span className="text-sm font-semibold text-gray-600">Status</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></div>
                  <span className="text-lg font-bold text-emerald-900">Complete</span>
                </div>
              </div>
            </div>
            
            {stage4Data.course_summary.description && (
              <div className="mt-6 p-6 bg-white rounded-xl border border-gray-100 shadow-sm">
                <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                  <FileText className="w-5 h-5 text-gray-600 mr-2" />
                  Course Description
                </h4>
                <p className="text-gray-700 leading-relaxed">{stage4Data.course_summary.description}</p>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-lg">
            <div className="text-center mb-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">What's Next?</h3>
              <p className="text-gray-600">Your course is ready! Choose what you'd like to do next.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Primary Action - View Course */}
              <div className="md:col-span-1">
                <button
                  onClick={() => window.location.href = `/course-view/${courseId}`}
                  className="w-full group relative overflow-hidden bg-gradient-to-r from-green-600 to-emerald-600 text-white font-bold py-6 px-8 rounded-2xl hover:from-green-700 hover:to-emerald-700 transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-green-400 to-emerald-400 opacity-0 group-hover:opacity-20 transition-opacity duration-300"></div>
                  <div className="relative flex flex-col items-center space-y-3">
                    <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                      <BookOpen className="w-6 h-6" />
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold">View Course</div>
                      <div className="text-sm text-green-100">Start learning now</div>
                    </div>
                  </div>
                </button>
              </div>
              
              {/* Secondary Actions */}
              <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                  onClick={() => window.open(stage4Data.course_summary.export_path, '_blank')}
                  className="flex items-center space-x-4 p-6 bg-gray-50 hover:bg-gray-100 rounded-2xl border border-gray-200 transition-all duration-200 hover:shadow-md group"
                  disabled={!stage4Data.course_summary.export_path}
                >
                  <div className="w-12 h-12 bg-gray-100 group-hover:bg-gray-200 rounded-xl flex items-center justify-center transition-colors">
                    <FileText className="w-6 h-6 text-gray-600" />
                  </div>
                  <div className="text-left">
                    <div className="font-semibold text-gray-900">View Course Files</div>
                    <div className="text-sm text-gray-600">Access raw content</div>
                  </div>
                </button>
                
                                 <button
                   onClick={() => {
                     // Handle download functionality
                     console.log('Download course clicked');
                   }}
                   className="flex items-center space-x-4 p-6 bg-blue-50 hover:bg-blue-100 rounded-2xl border border-blue-200 transition-all duration-200 hover:shadow-md group"
                 >
                  <div className="w-12 h-12 bg-blue-100 group-hover:bg-blue-200 rounded-xl flex items-center justify-center transition-colors">
                    <Download className="w-6 h-6 text-blue-600" />
                  </div>
                  <div className="text-left">
                    <div className="font-semibold text-gray-900">Download Course</div>
                    <div className="text-sm text-gray-600">Save to your device</div>
                  </div>
                </button>
              </div>
            </div>
            
            {/* Course Complete Button */}
            <div className="mt-8 text-center">
              <button
                onClick={onStageComplete}
                className="inline-flex items-center space-x-3 px-8 py-4 bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-bold rounded-2xl hover:from-emerald-700 hover:to-teal-700 shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
              >
                <CheckCircle className="w-6 h-6" />
                <span>Mark Course Complete</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 