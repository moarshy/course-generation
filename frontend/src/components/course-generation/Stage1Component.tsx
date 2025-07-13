"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Course, GenerationStatus, Stage1Response, Stage1Input } from '@/lib/types';
import { 
  startCourseGeneration, 
  getGenerationStatus, 
  getStage1Result, 
  saveStage1Selections, 
  getStage1Selections 
} from '@/lib/api';
import { 
  Github, 
  Play, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Folder, 
  File,
  Save,
  RefreshCw
} from 'lucide-react';

const repoUrlSchema = z.object({
  repo_url: z.string().url('Please enter a valid GitHub repository URL')
});

type RepoUrlFormData = z.infer<typeof repoUrlSchema>;

interface Stage1ComponentProps {
  courseId: string;
  course: Course;
  onStatusUpdate: (status: GenerationStatus) => void;
  onStageComplete: () => void;
}

export default function Stage1Component({ 
  courseId, 
  course, 
  onStatusUpdate, 
  onStageComplete 
}: Stage1ComponentProps) {
  const [stage1Data, setStage1Data] = useState<Stage1Response | null>(null);
  const [selections, setSelections] = useState<Stage1Input>({ include_folders: [] });
  const [loading, setLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [isStage2Complete, setIsStage2Complete] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch
  } = useForm<RepoUrlFormData>({
    resolver: zodResolver(repoUrlSchema),
    defaultValues: {
      repo_url: course.repo_url || ''
    }
  });

  const repoUrl = watch('repo_url');

  // Load existing data on component mount
  useEffect(() => {
    const loadExistingData = async () => {
      try {
        // Check if Stage 1 is already completed
        const status = await getGenerationStatus(courseId).catch(() => null);
        if (status?.stage_statuses?.CLONE_REPO === 'completed') {
          setIsComplete(true);
          setHasStarted(true);
          
          // Check if Stage 2 is also complete
          if (status?.stage_statuses?.DOCUMENT_ANALYSIS === 'completed') {
            setIsStage2Complete(true);
          }
          
          // Load Stage 1 results
          const [stage1Result, stage1Selections] = await Promise.all([
            getStage1Result(courseId),
            getStage1Selections(courseId).catch(() => ({ include_folders: [] } as Stage1Input))
          ]);
          
          console.log('Stage 1 result:', stage1Result);
          console.log('Stage 1 selections from API:', stage1Selections);
          
          setStage1Data(stage1Result);
          // Map API response field names to frontend expected field names
          const restoredSelections = {
            include_folders: (stage1Selections as any)?.selected_folders || stage1Selections?.include_folders || [],
            overview_doc: (stage1Selections as any)?.overview_document || stage1Selections?.overview_doc
          };
          console.log('Restored selections:', restoredSelections);
          setSelections(restoredSelections);
        }
      } catch (err) {
        console.error('Error loading existing data:', err);
      }
    };

    loadExistingData();
  }, [courseId]);

  // Start the generation process
  const handleStartGeneration = async (data: RepoUrlFormData) => {
    setLoading(true);
    setError(null);
    setHasStarted(true);

    try {
      await startCourseGeneration(courseId, { repo_url: data.repo_url });
      
      // Start polling for completion
      setPollingStatus(true);
      pollForStageCompletion();
    } catch (err: any) {
      setError(err.detail || 'Failed to start course generation');
      setHasStarted(false);
    } finally {
      setLoading(false);
    }
  };

  // Poll for stage completion
  const pollForStageCompletion = async () => {
    const maxAttempts = 60; // 5 minutes with 5-second intervals
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await getGenerationStatus(courseId);
        onStatusUpdate(status);

        // Check if Stage 2 is complete
        if (status.stage_statuses.DOCUMENT_ANALYSIS === 'completed') {
          setIsStage2Complete(true);
        }

        if (status.stage_statuses.CLONE_REPO === 'completed') {
          setIsComplete(true);
          setPollingStatus(false);
          
          // Load Stage 1 results
          const stage1Result = await getStage1Result(courseId);
          setStage1Data(stage1Result);
          
          return;
        }

        if (status.stage_statuses.CLONE_REPO === 'failed') {
          setError('Repository cloning failed. Please check the repository URL and try again.');
          setPollingStatus(false);
          setHasStarted(false);
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          setError('Generation timeout. Please try again.');
          setPollingStatus(false);
          setHasStarted(false);
        }
      } catch (err: any) {
        setError(err.detail || 'Failed to check generation status');
        setPollingStatus(false);
        setHasStarted(false);
      }
    };

    poll();
  };

  // Handle folder selection
  const handleFolderToggle = (folder: string) => {
    setSelections(prev => ({
      ...prev,
      include_folders: (prev.include_folders || []).includes(folder)
        ? (prev.include_folders || []).filter(f => f !== folder)
        : [...(prev.include_folders || []), folder]
    }));
  };

  // Handle overview document selection
  const handleOverviewDocChange = (doc: string) => {
    setSelections(prev => ({
      ...prev,
      overview_doc: doc === prev.overview_doc ? undefined : doc
    }));
  };

  // Save selections and proceed
  const handleSaveSelections = async () => {
    setLoading(true);
    setError(null);

    try {
      await saveStage1Selections(courseId, selections);
      onStageComplete();
    } catch (err: any) {
      setError(err.detail || 'Failed to save selections');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Stage 1: Repository Setup</h2>
        <p className="text-gray-600">
          Start by providing a GitHub repository URL to analyze and generate course content from.
        </p>
      </div>

      {/* Step 1: Repository URL */}
      <div className="mb-8">
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Github className="w-6 h-6 text-blue-600" />
            <h3 className="text-lg font-semibold text-blue-900">GitHub Repository</h3>
          </div>
          
          <form onSubmit={handleSubmit(handleStartGeneration)} className="space-y-4">
            <div>
              <label htmlFor="repo_url" className="block text-sm font-semibold text-gray-900 mb-2">
                Repository URL
              </label>
                             <input
                 {...register('repo_url')}
                 type="url"
                 id="repo_url"
                 className="w-full px-4 py-3 text-lg font-semibold text-gray-900 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white placeholder-gray-500"
                 placeholder="https://github.com/username/repository"
                 disabled={hasStarted}
               />
              {errors.repo_url && (
                <p className="mt-2 text-sm text-red-600">{errors.repo_url.message}</p>
              )}
            </div>

            {!hasStarted && (
              <button
                type="submit"
                disabled={loading || !repoUrl}
                className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>Starting...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5" />
                    <span>Start Generation</span>
                  </>
                )}
              </button>
            )}
          </form>
        </div>
      </div>

      {/* Status Display */}
      {hasStarted && (
        <div className="mb-8">
          {isComplete ? (
            /* Success State */
            <div className="bg-green-50 border border-green-200 rounded-xl p-6">
              <div className="flex items-center space-x-3 mb-2">
                <CheckCircle className="w-6 h-6 text-green-600" />
                <h3 className="text-lg font-semibold text-green-900">Repository Analysis Complete!</h3>
              </div>
              <p className="text-sm text-green-700">
                Repository has been successfully cloned and analyzed.
              </p>
            </div>
          ) : pollingStatus ? (
            /* Loading State with Enhanced UI */
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-8">
              <div className="text-center mb-6">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-4">
                  <Github className="w-8 h-8 text-blue-600 animate-pulse" />
                </div>
                <h3 className="text-xl font-bold text-blue-900 mb-2">Analyzing Repository</h3>
                <p className="text-sm text-blue-700">
                  We're cloning and analyzing your repository to prepare it for course generation
                </p>
              </div>

              {/* Progress Steps */}
              <div className="space-y-4 mb-6">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-900">Cloning repository from GitHub</p>
                    <p className="text-xs text-blue-600">Downloading source code and files...</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-200 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-800">Scanning file structure</p>
                    <p className="text-xs text-blue-600">Identifying folders and documents...</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-blue-700">Preparing analysis results</p>
                    <p className="text-xs text-blue-500">Organizing content for selection...</p>
                  </div>
                </div>
              </div>

              {/* Animated Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between text-xs text-blue-600 mb-2">
                  <span>Progress</span>
                  <span>Typically takes 30-60 seconds</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2">
                  <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                </div>
              </div>

              {/* Tips while waiting */}
              <div className="bg-white bg-opacity-60 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 text-blue-600">💡</div>
                  <div>
                    <p className="text-sm font-medium text-blue-900 mb-1">While you wait...</p>
                    <p className="text-xs text-blue-700">
                      Our AI will analyze your repository structure and suggest the most relevant folders and files for course generation. 
                      You'll be able to customize these selections in the next step.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Error State */
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <div className="flex items-center space-x-3 mb-2">
                <AlertCircle className="w-6 h-6 text-red-600" />
                <h3 className="text-lg font-semibold text-red-900">Analysis Failed</h3>
              </div>
              <p className="text-sm text-red-700 mb-4">{error}</p>
              <button
                onClick={() => {
                  setHasStarted(false);
                  setError(null);
                }}
                className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Folder and File Selection */}
      {isComplete && stage1Data && (
        <div className="mb-8">
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Select Content to Include
            </h3>
            <p className="text-sm text-gray-600 mb-6">
              Choose which folders and files to include in your course generation.
            </p>

            {/* Repository Info */}
            <div className="mb-6 p-4 bg-white rounded-lg border">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="font-semibold text-gray-900">Repository</div>
                  <div className="text-gray-600">{stage1Data.repo_name}</div>
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Folders</div>
                  <div className="text-gray-600">{stage1Data.available_folders.length}</div>
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Files</div>
                  <div className="text-gray-600">{stage1Data.total_files}</div>
                </div>
                <div>
                  <div className="font-semibold text-gray-900">Selected</div>
                  <div className="text-gray-600">{selections.include_folders?.length || 0} folders</div>
                </div>
              </div>
            </div>

            {/* Folder Selection */}
            <div className="mb-6">
              <h4 className="text-base font-semibold text-gray-900 mb-3">Available Folders</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {stage1Data.available_folders.map((folder) => (
                  <label
                    key={folder}
                    className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selections.include_folders?.includes(folder) || false}
                      onChange={() => handleFolderToggle(folder)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <Folder className="w-5 h-5 text-blue-600" />
                    <span className="text-sm font-medium text-gray-900">{folder}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Overview Document Selection */}
            {stage1Data.available_files.length > 0 && (
              <div className="mb-6">
                <h4 className="text-base font-semibold text-gray-900 mb-3">
                  Overview Document (Optional)
                </h4>
                <p className="text-sm text-gray-600 mb-3">
                  Select a document to serve as the main overview for your course.
                </p>
                <div className="space-y-2">
                  {stage1Data.available_files.map((doc) => (
                    <label
                      key={doc}
                      className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="overview_doc"
                        checked={selections.overview_doc === doc}
                        onChange={() => handleOverviewDocChange(doc)}
                        className="w-4 h-4 text-blue-600 focus:ring-blue-500"
                      />
                      <File className="w-5 h-5 text-green-600" />
                      <span className="text-sm font-medium text-gray-900">{doc}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Save Selections Button */}
            <div className="flex flex-col items-end">
              <button
                onClick={handleSaveSelections}
                disabled={loading || (selections.include_folders?.length || 0) === 0 || isStage2Complete}
                className="flex items-center space-x-2 px-6 py-3 bg-green-600 text-white font-semibold rounded-xl hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-5 h-5" />
                    <span>Save Selections & Continue</span>
                  </>
                )}
              </button>
              
              {/* Status message */}
              <div className="mt-2 text-sm">
                {isStage2Complete ? (
                  <span className="text-green-600">✓ Stage 2 already completed</span>
                ) : (selections.include_folders?.length || 0) === 0 ? (
                  <span className="text-amber-600">⚠️ Please select at least one folder</span>
                ) : (
                  <span className="text-blue-600">Ready to continue to Stage 2</span>
                )}
              </div>
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
    </div>
  );
} 