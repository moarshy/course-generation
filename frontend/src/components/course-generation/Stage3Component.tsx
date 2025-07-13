"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Course, GenerationStatus, Stage3Response, Stage3Input, PathwaySummary, ModuleSummary } from '@/lib/types';
import { 
  startStage3, 
  getGenerationStatus, 
  getStage3Result
} from '@/lib/api';
import { 
  Route, 
  Play, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  BookOpen,
  Target,
  RefreshCw,
  ChevronRight,
  Users,
  Calendar,
  GraduationCap
} from 'lucide-react';

const stage3Schema = z.object({
  complexity_level: z.string().min(1, 'Complexity level is required'),
  additional_instructions: z.string().optional()
});

type Stage3FormData = z.infer<typeof stage3Schema>;

interface Stage3ComponentProps {
  courseId: string;
  course: Course;
  onStatusUpdate: (status: GenerationStatus) => void;
  onStageComplete: () => void;
}

export default function Stage3Component({ 
  courseId, 
  course, 
  onStatusUpdate, 
  onStageComplete 
}: Stage3ComponentProps) {
  const [stage3Data, setStage3Data] = useState<Stage3Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [selectedComplexity, setSelectedComplexity] = useState('');
  const [isStarting, setIsStarting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch
  } = useForm<Stage3FormData>({
    resolver: zodResolver(stage3Schema),
    defaultValues: {
      complexity_level: 'intermediate',
      additional_instructions: ''
    }
  });

  const complexityLevel = watch('complexity_level');
  const additionalInstructions = watch('additional_instructions');

  // Load existing data on component mount
  useEffect(() => {
    let mounted = true; // Guard against race conditions
    
    const loadExistingData = async () => {
      try {
        const status = await getGenerationStatus(courseId).catch(() => null);
        
        if (!mounted) return; // Component unmounted, don't proceed
        
        if (status?.stage_statuses?.PATHWAY_BUILDING === 'completed') {
          setIsComplete(true);
          setHasStarted(true);
          
          // Load Stage 3 results
          const stage3Result = await getStage3Result(courseId);
          if (mounted) setStage3Data(stage3Result);
        } else if (status?.stage_statuses?.PATHWAY_BUILDING === 'in_progress') {
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
      mounted = false; // Cleanup
    };
  }, [courseId]);



  // Start Stage 3 pathway generation
  const handleStartPathwayGeneration = async (data: Stage3FormData) => {
    if (isStarting) {
      return; // Prevent multiple starts
    }
    
    setLoading(true);
    setIsStarting(true);
    setError(null);
    setHasStarted(true);
    setSelectedComplexity(data.complexity_level);

    try {
      await startStage3(courseId, data);
      
      // Start polling for completion
      setPollingStatus(true);
      pollForStageCompletion();
    } catch (err: any) {
      setError(err.detail || 'Failed to start pathway generation');
      setHasStarted(false);
    } finally {
      setLoading(false);
      setIsStarting(false);
    }
  };

  // Poll for stage completion
  const pollForStageCompletion = async () => {
    const maxAttempts = 120; // 10 minutes with 5-second intervals
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await getGenerationStatus(courseId);
        onStatusUpdate(status);

        if (status.stage_statuses.PATHWAY_BUILDING === 'completed') {
          setIsComplete(true);
          setPollingStatus(false);
          
          // Load Stage 3 results
          const stage3Result = await getStage3Result(courseId);
          setStage3Data(stage3Result);
          
          return;
        }

        if (status.stage_statuses.PATHWAY_BUILDING === 'failed') {
          setError('Pathway generation failed. Please try again.');
          setPollingStatus(false);
          setHasStarted(false);
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          setError('Pathway generation timeout. Please try again.');
          setPollingStatus(false);
          setHasStarted(false);
        }
      } catch (err: any) {
        setError(err.detail || 'Failed to check pathway generation status');
        setPollingStatus(false);
        setHasStarted(false);
      }
    };

    poll();
  };

  const handleProceedToStage4 = () => {
    onStageComplete();
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
        return 'Ideal for newcomers with step-by-step introductions and fundamental concepts';
      case 'intermediate':
        return 'Suitable for those with basic knowledge, covering practical implementations';
      case 'advanced':
        return 'For experienced users focusing on complex topics and advanced techniques';
      default:
        return 'Standard complexity level';
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Stage 3: Learning Pathway Generation</h2>
        <p className="text-gray-600">
          Configure and generate structured learning pathways based on the analyzed documents.
        </p>
      </div>

      {/* Configuration Form */}
      {!isComplete && (
        <div className="mb-8">
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Route className="w-6 h-6 text-purple-600" />
              <h3 className="text-lg font-semibold text-purple-900">Pathway Configuration</h3>
            </div>
            
            <form onSubmit={handleSubmit(handleStartPathwayGeneration)} className="space-y-6">
              {/* Complexity Level */}
              <div>
                <label htmlFor="complexity_level" className="block text-sm font-semibold text-gray-900 mb-3">
                  Target Complexity Level
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {['beginner', 'intermediate', 'advanced'].map((level) => (
                    <label key={level} className="relative">
                      <input
                        {...register('complexity_level')}
                        type="radio"
                        value={level}
                        className="sr-only"
                        disabled={hasStarted}
                      />
                      <div className={`cursor-pointer border-2 rounded-xl p-4 transition-all ${
                        complexityLevel === level
                          ? 'border-purple-500 bg-purple-50'
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
                {errors.complexity_level && (
                  <p className="mt-2 text-sm text-red-600">{errors.complexity_level.message}</p>
                )}
              </div>

              {/* Additional Instructions */}
              <div>
                <label htmlFor="additional_instructions" className="block text-sm font-semibold text-gray-900 mb-2">
                  Additional Instructions (Optional)
                </label>
                <textarea
                  {...register('additional_instructions')}
                  id="additional_instructions"
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
                  placeholder="Specify any particular focus areas, learning objectives, or special requirements for the pathway..."
                  disabled={hasStarted}
                />
                <p className="mt-2 text-sm text-gray-500">
                  Example: "Focus on practical hands-on examples with code implementations" or "Include prerequisites and advanced topics"
                </p>
              </div>

              {!hasStarted && (
                <button
                  type="submit"
                  disabled={loading}
                  className="flex items-center space-x-2 px-6 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      <span>Starting...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5" />
                      <span>Generate Learning Pathway</span>
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
                    <h3 className="text-lg font-semibold text-green-900">Pathway Generation Complete</h3>
                    <p className="text-green-700">
                      Successfully generated learning pathways with complexity level: {selectedComplexity}
                    </p>
                  </div>
                </>
              ) : pollingStatus ? (
                <>
                  <Clock className="w-6 h-6 text-blue-600 animate-pulse" />
                  <div>
                    <h3 className="text-lg font-semibold text-blue-900">Generating Learning Pathways</h3>
                    <p className="text-blue-700">
                      AI is analyzing documents and creating structured learning pathways...
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
      {isComplete && stage3Data && (
        <div className="space-y-8">
          {/* Summary Stats */}
          <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-purple-900 mb-4">Pathway Generation Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <Route className="w-5 h-5 text-purple-600" />
                  <span className="text-sm font-medium text-gray-600">Learning Pathways</span>
                </div>
                <p className="text-2xl font-bold text-gray-900 mt-1">{stage3Data.pathways?.length || 0}</p>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <BookOpen className="w-5 h-5 text-blue-600" />
                  <span className="text-sm font-medium text-gray-600">Total Modules</span>
                </div>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {stage3Data.pathways?.reduce((total, pathway) => total + (pathway.modules?.length || 0), 0) || 0}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <Target className="w-5 h-5 text-green-600" />
                  <span className="text-sm font-medium text-gray-600">Complexity</span>
                </div>
                <p className="text-lg font-semibold text-gray-900 mt-1 capitalize">{selectedComplexity}</p>
              </div>
            </div>
          </div>

          {/* Learning Pathways */}
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-6">Generated Learning Pathways</h3>
            <div className="space-y-6">
              {stage3Data.pathways?.map((pathway, index) => (
                <div key={pathway.id || index} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  {/* Pathway Header */}
                  <div className="bg-gradient-to-r from-purple-500 to-indigo-600 text-white p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="px-2 py-1 bg-white bg-opacity-20 rounded-full text-xs font-medium">
                            Pathway {pathway.index + 1}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium border ${
                            pathway.complexity === 'beginner' ? 'bg-green-100 text-green-800 border-green-200' :
                            pathway.complexity === 'intermediate' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
                            'bg-red-100 text-red-800 border-red-200'
                          }`}>
                            {pathway.complexity}
                          </span>
                        </div>
                        <h4 className="text-xl font-bold mb-2">{pathway.title}</h4>
                        <p className="text-purple-100 leading-relaxed">{pathway.description}</p>
                      </div>
                      <div className="ml-4 text-right">
                        <div className="text-2xl font-bold">{pathway.modules?.length || 0}</div>
                        <div className="text-sm text-purple-200">Modules</div>
                      </div>
                    </div>
                  </div>

                  {/* Modules */}
                  <div className="p-6">
                    <h5 className="text-lg font-semibold text-gray-900 mb-4">Learning Modules</h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {pathway.modules?.map((module, moduleIndex) => (
                        <div 
                          key={module.id || moduleIndex} 
                          className="border border-gray-200 rounded-lg p-4 hover:border-purple-300 transition-colors"
                        >
                          <div className="flex items-start space-x-3">
                            <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                              <span className="text-sm font-semibold text-purple-600">{moduleIndex + 1}</span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <h6 className="text-base font-semibold text-gray-900 mb-1">{module.title}</h6>
                              {module.theme && (
                                <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full mb-2">
                                  {module.theme}
                                </span>
                              )}
                              <p className="text-sm text-gray-600 leading-relaxed">{module.description}</p>
                              {module.learning_objectives && module.learning_objectives.length > 0 && (
                                <div className="mt-2">
                                  <p className="text-xs font-medium text-gray-500 mb-1">Learning Objectives:</p>
                                  <ul className="text-xs text-gray-600 space-y-1">
                                    {module.learning_objectives.slice(0, 2).map((objective, objIndex) => (
                                      <li key={objIndex} className="flex items-start space-x-1">
                                        <ChevronRight className="w-3 h-3 text-gray-400 mt-0.5 flex-shrink-0" />
                                        <span>{objective}</span>
                                      </li>
                                    ))}
                                    {module.learning_objectives.length > 2 && (
                                      <li className="text-gray-400 italic">
                                        +{module.learning_objectives.length - 2} more objectives
                                      </li>
                                    )}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Proceed Button */}
          <div className="flex justify-end pt-6">
            <button
              onClick={handleProceedToStage4}
              className="flex items-center space-x-3 px-8 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-purple-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
            >
              <span>Proceed to Stage 4</span>
              <div className="w-5 h-5 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                <ChevronRight className="w-3 h-3" />
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
} 