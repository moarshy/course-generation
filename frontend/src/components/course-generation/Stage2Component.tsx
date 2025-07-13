"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Course, GenerationStatus, Stage2Response, Stage2Input, DocumentSummary } from '@/lib/types';
import { 
  startStage2, 
  getGenerationStatus, 
  getStage2Result,
  updateStage2Document
} from '@/lib/api';
import { 
  FileText, 
  Play, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Edit,
  Save,
  RefreshCw,
  Search,
  FolderOpen,
  X,
  Plus
} from 'lucide-react';

const stage2Schema = z.object({
  complexity_level: z.string().min(1, 'Complexity level is required'),
  additional_info: z.string().optional()
});

type Stage2FormData = z.infer<typeof stage2Schema>;

interface Stage2ComponentProps {
  courseId: string;
  course: Course;
  onStatusUpdate: (status: GenerationStatus) => void;
  onStageComplete: () => void;
}

export default function Stage2Component({ 
  courseId, 
  course, 
  onStatusUpdate, 
  onStageComplete 
}: Stage2ComponentProps) {
  const [stage2Data, setStage2Data] = useState<Stage2Response | null>(null);
  const [loading, setLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [editingDoc, setEditingDoc] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState<string>('');
  const [editedKeyConcepts, setEditedKeyConcepts] = useState<string[]>([]);
  const [editedLearningObjectives, setEditedLearningObjectives] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedComplexity, setSelectedComplexity] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isStarting, setIsStarting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch
  } = useForm<Stage2FormData>({
    resolver: zodResolver(stage2Schema),
    defaultValues: {
      complexity_level: 'beginner',
      additional_info: ''
    }
  });

  const complexityLevel = watch('complexity_level');
  const additionalInfo = watch('additional_info');

  // Load existing data on component mount
  useEffect(() => {
    let mounted = true; // Guard against race conditions
    
    const loadExistingData = async () => {
      try {
        const status = await getGenerationStatus(courseId).catch(() => null);
        
        if (!mounted) return; // Component unmounted, don't proceed
        
        if (status?.stage_statuses?.DOCUMENT_ANALYSIS === 'completed') {
          setIsComplete(true);
          setHasStarted(true);
          
          // Load Stage 2 results
          const stage2Result = await getStage2Result(courseId);
          if (mounted) setStage2Data(stage2Result);
        } else if (status?.stage_statuses?.DOCUMENT_ANALYSIS === 'in_progress') {
          setHasStarted(true);
          setPollingStatus(true);
          pollForStageCompletion();
        } else if (status?.stage_statuses?.CLONE_REPO === 'completed' && 
                   status?.stage_statuses?.DOCUMENT_ANALYSIS === 'pending') {
          // Stage 1 is complete and Stage 2 is pending, auto-start Stage 2 with default values
          autoStartStage2();
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

  // Auto-start Stage 2 with default values
  const autoStartStage2 = async () => {
    if (isStarting) {
      return; // Prevent multiple starts
    }
    
    // Double-check status before starting
    try {
      const status = await getGenerationStatus(courseId);
      if (status?.stage_statuses?.DOCUMENT_ANALYSIS === 'in_progress' || 
          status?.stage_statuses?.DOCUMENT_ANALYSIS === 'completed') {
        return;
      }
    } catch (err) {
      // Status check failed, continue with auto-start
    }
    
    const defaultData: Stage2FormData = {
      complexity_level: 'beginner',
      additional_info: ''
    };
    
    setIsStarting(true);
    setHasStarted(true);
    setSelectedComplexity(defaultData.complexity_level);
    
    try {
      await startStage2(courseId, defaultData);
      
      // Start polling for completion
      setPollingStatus(true);
      pollForStageCompletion();
    } catch (err: any) {
      setError(err.detail || 'Failed to start document analysis');
      setHasStarted(false);
    } finally {
      setIsStarting(false);
    }
  };

  // Start Stage 2 analysis
  const handleStartAnalysis = async (data: Stage2FormData) => {
    if (isStarting) {
      return; // Prevent multiple starts
    }
    
    setLoading(true);
    setIsStarting(true);
    setError(null);
    setHasStarted(true);
    setSelectedComplexity(data.complexity_level);

    try {
      await startStage2(courseId, data);
      
      // Start polling for completion
      setPollingStatus(true);
      pollForStageCompletion();
    } catch (err: any) {
      setError(err.detail || 'Failed to start document analysis');
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

        if (status.stage_statuses.DOCUMENT_ANALYSIS === 'completed') {
          setIsComplete(true);
          setPollingStatus(false);
          
          // Load Stage 2 results
          const stage2Result = await getStage2Result(courseId);
          setStage2Data(stage2Result);
          
          return;
        }

        if (status.stage_statuses.DOCUMENT_ANALYSIS === 'failed') {
          setError('Document analysis failed. Please try again.');
          setPollingStatus(false);
          setHasStarted(false);
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          setError('Analysis timeout. Please try again.');
          setPollingStatus(false);
          setHasStarted(false);
        }
      } catch (err: any) {
        setError(err.detail || 'Failed to check analysis status');
        setPollingStatus(false);
        setHasStarted(false);
      }
    };

    poll();
  };

  // Handle document editing
  const handleEditDocument = (docId: string, content: string, keyConcepts: string[] = [], learningObjectives: string[] = []) => {
    // Prevent editing if analysis is still in progress
    if (pollingStatus) {
      setError('Cannot edit documents while analysis is in progress. Please wait for completion.');
      return;
    }
    
    setEditingDoc(docId);
    setEditedContent(content);
    setEditedKeyConcepts(keyConcepts);
    setEditedLearningObjectives(learningObjectives);
  };

  const handleSaveEdit = async () => {
    if (editingDoc && stage2Data) {
      setLoading(true);
      setError(null);
      
      try {
        // Prepare the updated document data
        const updatedDoc = {
          content: editedContent,
          metadata: {
            ...stage2Data.analyzed_documents.find(doc => doc.id === editingDoc)?.metadata,
            key_concepts: editedKeyConcepts,
            learning_objectives: editedLearningObjectives
          }
        };

        // Save to backend
        await updateStage2Document(courseId, editingDoc, updatedDoc);

        // Update the local state
        const updatedDocs = stage2Data.analyzed_documents.map(doc => 
          doc.id === editingDoc ? { 
            ...doc, 
            content: editedContent,
            metadata: {
              ...doc.metadata,
              key_concepts: editedKeyConcepts,
              learning_objectives: editedLearningObjectives
            }
          } : doc
        );
        
        setStage2Data({
          ...stage2Data,
          analyzed_documents: updatedDocs
        });
        
        setEditingDoc(null);
        setEditedContent('');
        setEditedKeyConcepts([]);
        setEditedLearningObjectives([]);
        
        // Show success message
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      } catch (err: any) {
        setError(err.detail || 'Failed to save document changes');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingDoc(null);
    setEditedContent('');
    setEditedKeyConcepts([]);
    setEditedLearningObjectives([]);
  };

  // Filter documents based on search query
  const filteredDocuments = stage2Data?.analyzed_documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.content.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const handleProceedToStage3 = () => {
    onStageComplete();
  };

  // Helper functions to extract data from document metadata
  const getKeyConcepts = (doc: DocumentSummary): string[] => {
    return doc.metadata?.key_concepts || [];
  };

  const getLearningObjectives = (doc: DocumentSummary): string[] => {
    return doc.metadata?.learning_objectives || [];
  };

  const getCleanPath = (path: string): string => {
    // Remove the cache directory path and show a cleaner version
    return path.replace(/^.*\/\.cache\/[^/]+\//, '');
  };

  const addKeyConcept = () => {
    setEditedKeyConcepts([...editedKeyConcepts, '']);
  };

  const removeKeyConcept = (index: number) => {
    setEditedKeyConcepts(editedKeyConcepts.filter((_, i) => i !== index));
  };

  const addLearningObjective = () => {
    setEditedLearningObjectives([...editedLearningObjectives, '']);
  };

  const removeLearningObjective = (index: number) => {
    setEditedLearningObjectives(editedLearningObjectives.filter((_, i) => i !== index));
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Stage 2: Document Analysis</h2>
        <p className="text-gray-600">
          Configure the analysis parameters and process the selected documents to extract course content.
        </p>
      </div>

      {/* Stage 2 will auto-start when Stage 1 is complete */}

      {/* Status Display */}
      {hasStarted && !isComplete && (
        <div className="mb-8">
          {pollingStatus ? (
            /* Compact Loading State */
            <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-4">
              <div className="flex items-center space-x-3 mb-4">
                <div className="flex-shrink-0 w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
                  <FileText className="w-5 h-5 text-emerald-600 animate-pulse" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-emerald-900">Analyzing Documents</h3>
                  <p className="text-sm text-emerald-700">Processing and extracting key information...</p>
                </div>
              </div>

              {/* Simple Progress Bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-emerald-600 mb-2">
                  <span>Analysis in progress...</span>
                  <span>2-5 minutes</span>
                </div>
                <div className="w-full bg-emerald-200 rounded-full h-2">
                  <div className="bg-emerald-600 h-2 rounded-full animate-pulse" style={{ width: '75%' }}></div>
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

      {/* Analysis Results */}
      {isComplete && stage2Data && (
        <div className="mb-8">
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            {/* Compact Results Header */}
            <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border-b border-emerald-100 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="flex items-center justify-center w-10 h-10 bg-emerald-100 rounded-full">
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-emerald-900">Analysis Complete!</h3>
                    <p className="text-sm text-emerald-700">
                      Successfully processed {stage2Data.analyzed_documents.length} documents
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-emerald-600">{stage2Data.processed_files_count}</div>
                    <div className="text-xs text-emerald-500 font-medium">Processed</div>
                  </div>
                  {stage2Data.failed_files_count > 0 && (
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-500">{stage2Data.failed_files_count}</div>
                      <div className="text-xs text-red-400 font-medium">Failed</div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="p-4">
              {/* Compact Search Bar */}
              <div className="mb-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="Search documents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-gray-50 focus:bg-white transition-colors"
                  />
                </div>
                {searchQuery && (
                  <p className="mt-2 text-xs text-gray-500">
                    Found {filteredDocuments.length} of {stage2Data.analyzed_documents.length} documents
                  </p>
                )}
              </div>

              {/* Compact Documents Grid */}
              <div className="grid gap-4 mb-6">
                {filteredDocuments.map((doc) => (
                  <div key={doc.id} className="border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow">
                    {/* Document Header */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200 p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-lg">
                            <FileText className="w-4 h-4 text-blue-600" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-semibold text-gray-900 text-base">{doc.filename}</h4>
                            <p className="text-xs text-gray-500 mt-1 font-mono break-all">{getCleanPath(doc.path)}</p>
                          </div>
                        </div>
                        <button
                          onClick={() => handleEditDocument(doc.id, doc.content, getKeyConcepts(doc), getLearningObjectives(doc))}
                          disabled={pollingStatus}
                          className={`flex items-center space-x-2 px-4 py-2 text-sm rounded-lg transition-colors font-medium ${
                            pollingStatus 
                              ? 'text-gray-400 cursor-not-allowed' 
                              : 'text-blue-600 hover:bg-blue-100'
                          }`}
                        >
                          <Edit className="w-4 h-4" />
                          <span>Edit</span>
                        </button>
                      </div>
                    </div>
                    
                    {/* Document Content */}
                    {editingDoc === doc.id ? (
                      <div className="p-5">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                          {/* Key Concepts Editing */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              Key Concepts
                            </label>
                            <div className="space-y-2">
                              {editedKeyConcepts.map((concept, index) => (
                                <div key={index} className="flex items-center space-x-2">
                                  <input
                                    type="text"
                                    value={concept}
                                    onChange={(e) => {
                                      const newConcepts = [...editedKeyConcepts];
                                      newConcepts[index] = e.target.value;
                                      setEditedKeyConcepts(newConcepts);
                                    }}
                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                                    placeholder="Enter key concept..."
                                  />
                                  <button
                                    onClick={() => removeKeyConcept(index)}
                                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                  >
                                    <X className="w-4 h-4" />
                                  </button>
                                </div>
                              ))}
                                                             <button
                                 onClick={addKeyConcept}
                                 className="flex items-center space-x-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                               >
                                <Plus className="w-4 h-4" />
                                <span>Add Key Concept</span>
                              </button>
                            </div>
                          </div>

                          {/* Learning Objectives Editing */}
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              Learning Objectives
                            </label>
                            <div className="space-y-2">
                              {editedLearningObjectives.map((objective, index) => (
                                <div key={index} className="flex items-center space-x-2">
                                  <input
                                    type="text"
                                    value={objective}
                                    onChange={(e) => {
                                      const newObjectives = [...editedLearningObjectives];
                                      newObjectives[index] = e.target.value;
                                      setEditedLearningObjectives(newObjectives);
                                    }}
                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-sm"
                                    placeholder="Enter learning objective..."
                                  />
                                  <button
                                    onClick={() => removeLearningObjective(index)}
                                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                  >
                                    <X className="w-4 h-4" />
                                  </button>
                                </div>
                              ))}
                                                             <button
                                 onClick={addLearningObjective}
                                 className="flex items-center space-x-2 px-3 py-2 text-sm text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                               >
                                <Plus className="w-4 h-4" />
                                <span>Add Learning Objective</span>
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Content Editing */}
                        <div className="mb-6">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Document Content
                          </label>
                          <textarea
                            value={editedContent}
                            onChange={(e) => setEditedContent(e.target.value)}
                            className="w-full h-80 px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 resize-none font-mono text-sm bg-gray-50"
                            placeholder="Edit document content..."
                          />
                        </div>

                        {/* Action Buttons */}
                        <div className="flex justify-end space-x-3">
                          <button
                            onClick={handleCancelEdit}
                            className="px-5 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors font-medium"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSaveEdit}
                            disabled={loading}
                            className="flex items-center space-x-2 px-5 py-2 text-sm bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                          >
                            {loading ? (
                              <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                <span>Saving...</span>
                              </>
                            ) : (
                              <>
                                <Save className="w-4 h-4" />
                                <span>Save Changes</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="p-5">
                        {/* Key Concepts Section */}
                        {getKeyConcepts(doc).length > 0 && (
                          <div className="mb-4">
                            <h5 className="text-sm font-medium text-gray-700 mb-2">Key Concepts</h5>
                            <div className="flex flex-wrap gap-2">
                              {getKeyConcepts(doc).map((concept, index) => (
                                <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
                                  {concept}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Learning Objectives Section */}
                        {getLearningObjectives(doc).length > 0 && (
                          <div className="mb-4">
                            <h5 className="text-sm font-medium text-gray-700 mb-2">Learning Objectives</h5>
                            <ul className="space-y-1">
                              {getLearningObjectives(doc).map((objective, index) => (
                                <li key={index} className="text-sm text-gray-600 flex items-start">
                                  <span className="text-green-600 mr-2">•</span>
                                  {objective}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Content Preview */}
                        <div className="bg-gray-50 rounded-xl p-4 border">
                          <div className="flex items-center justify-between mb-3">
                            <h5 className="text-sm font-medium text-gray-700">Content Preview</h5>
                            <div className="text-xs text-gray-500">
                              {doc.content.length} characters
                            </div>
                          </div>
                          <div className="max-h-40 overflow-y-auto">
                            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">
                              {doc.content.length > 800 ? 
                                `${doc.content.substring(0, 800)}...` : 
                                doc.content
                              }
                            </pre>
                          </div>
                          {doc.content.length > 800 && (
                            <div className="mt-3 text-center">
                              <button
                                onClick={() => handleEditDocument(doc.id, doc.content, getKeyConcepts(doc), getLearningObjectives(doc))}
                                disabled={pollingStatus}
                                className={`text-sm font-medium ${
                                  pollingStatus 
                                    ? 'text-gray-400 cursor-not-allowed' 
                                    : 'text-blue-600 hover:text-blue-700'
                                }`}
                              >
                                View Full Content
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* No Results State */}
              {filteredDocuments.length === 0 && searchQuery && (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Search className="w-8 h-8 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No documents found</h3>
                  <p className="text-gray-500">Try adjusting your search terms or clear the search to see all documents.</p>
                </div>
              )}

              {/* Enhanced Proceed Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleProceedToStage3}
                  className="flex items-center space-x-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
                >
                  <span>Proceed to Stage 3</span>
                  <div className="w-5 h-5 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                    <RefreshCw className="w-3 h-3" />
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Success Display */}
      {saveSuccess && (
        <div className="mb-8">
          <div className="bg-green-50 border border-green-200 rounded-xl p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <p className="text-sm font-medium text-green-800">Document changes saved successfully!</p>
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