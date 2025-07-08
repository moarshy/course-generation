import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const Stage2Component = ({ course, taskStatus, stageData, onNext, currentStage, completedStages }) => {
  const { getAccessTokenSilently } = useAuth0();
  const [analyzedDocuments, setAnalyzedDocuments] = useState([]);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [detailedProgress, setDetailedProgress] = useState(null);
  const [editingDocumentId, setEditingDocumentId] = useState(null);
  const [editingData, setEditingData] = useState({});

  // Extract courseId from course object or URL params
  const courseId = course?.id || course?.course_id || course?.project_id || window.location.pathname.split('/').pop();

  // Better loading detection logic
  const isCompleted = taskStatus?.stage_statuses?.DOCUMENT_ANALYSIS === 'completed' || 
                      taskStatus?.stage_statuses?.document_analysis === 'completed' ||
                      taskStatus?.completed_stages?.includes('DOCUMENT_ANALYSIS') ||
                      taskStatus?.completed_stages?.includes('document_analysis');
  
  const isLoading = (taskStatus?.stage_statuses?.DOCUMENT_ANALYSIS === 'running' || 
                     taskStatus?.stage_statuses?.document_analysis === 'running' ||
                     (taskStatus?.current_stage === 'DOCUMENT_ANALYSIS' && taskStatus?.status === 'running') ||
                     (taskStatus?.current_stage === 'document_analysis' && taskStatus?.status === 'running'));
  
  const isFailed = taskStatus?.stage_statuses?.DOCUMENT_ANALYSIS === 'failed' || 
                   taskStatus?.stage_statuses?.document_analysis === 'failed';

  // Load analyzed documents when stage data is available
  useEffect(() => {
    if (stageData && stageData.analyzed_documents) {
      setAnalyzedDocuments(stageData.analyzed_documents);
    }
  }, [stageData]);

  // Load detailed progress when stage 2 is running
  useEffect(() => {
    let progressInterval;
    
    if (isLoading && courseId) {
      // Poll for detailed progress every 2 seconds
      const fetchProgress = async () => {
        try {
          const token = await getAccessTokenSilently();
          const response = await axios.get(
            `${API_BASE_URL}/course-generation/stage2/progress`,
            {
              headers: { Authorization: `Bearer ${token}` },
              params: { course_id: courseId }
            }
          );
          setDetailedProgress(response.data);
        } catch (error) {
          console.error('Error fetching detailed progress:', error);
          // Don't set detailed progress on error to avoid clearing existing data
        }
      };
      
      // Fetch immediately
      fetchProgress();
      
      // Set up polling
      progressInterval = setInterval(fetchProgress, 2000);
    } else {
      // Clear detailed progress when not loading
      setDetailedProgress(null);
    }
    
    return () => {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
    };
  }, [isLoading, courseId, getAccessTokenSilently]);

  // Document type options
  const documentTypes = [
    { value: 'reference', label: 'Reference' },
    { value: 'guide', label: 'Guide' },
    { value: 'api', label: 'API Documentation' },
    { value: 'example', label: 'Example' },
    { value: 'overview', label: 'Overview' },
    { value: 'configuration', label: 'Configuration' },
    { value: 'troubleshooting', label: 'Troubleshooting' },
    { value: 'changelog', label: 'Changelog' }
  ];

  const refreshStageData = async () => {
    setRefreshing(true);
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage2`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.analyzed_documents) {
        setAnalyzedDocuments(response.data.analyzed_documents);
      }
    } catch (error) {
      console.error('Error refreshing stage data:', error);
      alert('Failed to refresh stage data. Please try again.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleEditDocument = (doc) => {
    setEditingDocumentId(doc.id);
    setEditingData({
      ...doc,
      metadata: {
        ...doc.metadata,
        key_concepts: Array.isArray(doc.metadata.key_concepts) 
          ? doc.metadata.key_concepts
          : (doc.metadata.key_concepts ? doc.metadata.key_concepts.split(',').map(concept => concept.trim()).filter(concept => concept) : []),
        learning_objectives: Array.isArray(doc.metadata.learning_objectives)
          ? doc.metadata.learning_objectives
          : (doc.metadata.learning_objectives ? doc.metadata.learning_objectives.split(',').map(obj => obj.trim()).filter(obj => obj) : [])
      }
    });
  };

  const handleCancelEdit = () => {
    setEditingDocumentId(null);
    setEditingData({});
  };

  const handleSaveDocument = async (documentId) => {
    if (!editingData || editingDocumentId !== documentId) return;

    setSaving(true);
    try {
      const token = await getAccessTokenSilently();
      
      // Prepare the request body in the format the backend expects
      const requestBody = {
        document_id: documentId,
        metadata_updates: {
          doc_type: editingData.metadata.doc_type,
          semantic_summary: editingData.metadata.semantic_summary,
          key_concepts: editingData.metadata.key_concepts,
          learning_objectives: editingData.metadata.learning_objectives
        }
      };
      
      await axios.put(
        `${API_BASE_URL}/course-generation/${courseId}/stage2/document`,
        requestBody,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Update local state
      setAnalyzedDocuments(prev => 
        prev.map(doc => 
          doc.id === documentId ? editingData : doc
        )
      );
      
      // Exit editing mode
      setEditingDocumentId(null);
      setEditingData({});
    } catch (error) {
      console.error('Error saving document:', error);
      alert('Failed to save document changes. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // Helper functions for key concepts
  const addKeyConcept = () => {
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        key_concepts: [...editingData.metadata.key_concepts, '']
      }
    });
  };

  const removeKeyConcept = (index) => {
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        key_concepts: editingData.metadata.key_concepts.filter((_, i) => i !== index)
      }
    });
  };

  const updateKeyConcept = (index, value) => {
    const updated = [...editingData.metadata.key_concepts];
    updated[index] = value;
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        key_concepts: updated
      }
    });
  };

  // Helper functions for learning objectives
  const addLearningObjective = () => {
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        learning_objectives: [...editingData.metadata.learning_objectives, '']
      }
    });
  };

  const removeLearningObjective = (index) => {
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        learning_objectives: editingData.metadata.learning_objectives.filter((_, i) => i !== index)
      }
    });
  };

  const updateLearningObjective = (index, value) => {
    const updated = [...editingData.metadata.learning_objectives];
    updated[index] = value;
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        learning_objectives: updated
      }
    });
  };

  const updateDocumentType = (docType) => {
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        doc_type: docType
      }
    });
  };

  const updateSummary = (summary) => {
    setEditingData({
      ...editingData,
      metadata: {
        ...editingData.metadata,
        semantic_summary: summary
      }
    });
  };

  const handleNext = () => {
    if (!isCompleted) return;
    onNext();
  };

  if (isFailed) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Document Analysis Failed</h3>
        <p className="text-gray-600">
          {taskStatus?.error_message || 'An error occurred during document analysis'}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Analyzing Documents</h3>
        <p className="text-gray-600 mb-4">
          {detailedProgress?.stage_description || 'Processing selected documentation files and extracting key information...'}
        </p>
        
        {/* Enhanced Progress Display */}
        <div className="max-w-2xl mx-auto space-y-4">
          {/* Main Progress Bar */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Overall Progress</span>
              <span>{detailedProgress?.percentage || taskStatus?.progress_percentage || 0}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="bg-blue-500 h-3 rounded-full transition-all duration-300"
                style={{ width: `${detailedProgress?.percentage || taskStatus?.progress_percentage || 0}%` }}
              />
            </div>
            
            {/* File Progress Details */}
            {detailedProgress && (
              <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-lg font-semibold text-blue-600">
                    {detailedProgress.processed_files || 0}
                  </div>
                  <div className="text-gray-600">Processed</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-600">
                    {detailedProgress.total_files || 0}
                  </div>
                  <div className="text-gray-600">Total Files</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-red-600">
                    {detailedProgress.failed_files || 0}
                  </div>
                  <div className="text-gray-600">Failed</div>
                </div>
              </div>
            )}
          </div>

          {/* Current File Being Processed */}
          {detailedProgress?.current_file && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse mr-3"></div>
                <div className="flex-1">
                  <div className="font-medium text-blue-900">Currently Processing:</div>
                  <div className="text-sm font-mono text-blue-700 break-all">
                    {detailedProgress.current_file}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Recently Completed Files */}
          {detailedProgress?.completed_files && detailedProgress.completed_files.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="font-medium text-green-900 mb-2">Recently Completed:</div>
              <div className="max-h-24 overflow-y-auto">
                {detailedProgress.completed_files.slice(-5).map((file, index) => (
                  <div key={index} className="flex items-center text-sm text-green-700 mb-1">
                    <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="font-mono truncate">{file}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Failed Files */}
          {detailedProgress?.failed_files_list && detailedProgress.failed_files_list.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="font-medium text-red-900 mb-2">Failed Files:</div>
              <div className="max-h-24 overflow-y-auto">
                {detailedProgress.failed_files_list.map((failedFile, index) => (
                  <div key={index} className="flex items-start text-sm text-red-700 mb-1">
                    <svg className="w-4 h-4 text-red-500 mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <div className="flex-1">
                      <div className="font-mono truncate">{failedFile.file}</div>
                      <div className="text-xs text-red-600">{failedFile.error}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Processing Stage Description */}
        <div className="mt-6 text-left max-w-md mx-auto">
          <h4 className="font-medium text-gray-900 mb-3">Current Stage: {detailedProgress?.stage || 'Processing'}</h4>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <div className={`w-2 h-2 rounded-full mt-2 mr-3 flex-shrink-0 ${
                detailedProgress?.stage === 'raw_processing' ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'
              }`}></div>
              <span>Extracting content from markdown files</span>
            </li>
            <li className="flex items-start">
              <div className={`w-2 h-2 rounded-full mt-2 mr-3 flex-shrink-0 ${
                detailedProgress?.stage === 'llm_analysis' ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'
              }`}></div>
              <span>Analyzing content with AI for key concepts</span>
            </li>
            <li className="flex items-start">
              <div className={`w-2 h-2 rounded-full mt-2 mr-3 flex-shrink-0 ${
                detailedProgress?.stage === 'completed' ? 'bg-green-500' : 'bg-gray-300'
              }`}></div>
              <span>Classifying document types and complexity</span>
            </li>
          </ul>
        </div>
      </div>
    );
  }

  if (isCompleted && analyzedDocuments.length > 0) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">Document Analysis Results</h3>
            <p className="text-gray-600 mt-1">
              Review and edit the analyzed documents before proceeding to pathway generation
            </p>
          </div>
          <button
            onClick={refreshStageData}
            disabled={refreshing}
            className="flex items-center space-x-2 px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            {refreshing ? (
              <div className="w-4 h-4 border-2 border-gray-400 border-t-gray-600 rounded-full animate-spin"></div>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
            <span>Refresh</span>
          </button>
        </div>

        {/* Analysis Statistics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-600">{stageData?.processed_files_count || analyzedDocuments.length}</div>
            <div className="text-sm text-gray-600">Documents Processed</div>
          </div>
          <div className="bg-red-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-600">{stageData?.failed_files_count || 0}</div>
            <div className="text-sm text-gray-600">Failed Files</div>
          </div>
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-600">{stageData?.include_folders?.length || 0}</div>
            <div className="text-sm text-gray-600">Folders Included</div>
          </div>
        </div>

        {/* Documents List */}
        <div className="space-y-4">
          <h4 className="text-lg font-medium text-gray-900">Analyzed Documents</h4>
          
          <div className="grid gap-4">
            {analyzedDocuments.map((doc) => {
              const isEditing = editingDocumentId === doc.id;
              const displayData = isEditing ? editingData : doc;
              
              return (
                <div key={doc.id} className={`border rounded-lg p-4 transition-all ${isEditing ? 'border-blue-300 bg-blue-50' : 'border-gray-200 hover:shadow-md'}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h5 className="font-medium text-gray-900">{displayData.metadata.title}</h5>
                        
                        {/* Document Type */}
                        {isEditing ? (
                          <select
                            value={displayData.metadata.doc_type}
                            onChange={(e) => updateDocumentType(e.target.value)}
                            className="text-xs px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="tutorial">Tutorial</option>
                            <option value="guide">Guide</option>
                            <option value="reference">Reference</option>
                            <option value="explanation">Explanation</option>
                            <option value="api">API</option>
                            <option value="example">Example</option>
                            <option value="troubleshooting">Troubleshooting</option>
                          </select>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {displayData.metadata.doc_type}
                          </span>
                        )}
                      </div>
                      
                      <p className="text-sm text-gray-600 mb-3">{displayData.path}</p>
                      
                      <div className="space-y-3">
                        {/* Summary */}
                        <div>
                          <span className="text-sm font-medium text-gray-700">Summary: </span>
                          {isEditing ? (
                            <textarea
                              value={displayData.metadata.semantic_summary}
                              onChange={(e) => updateSummary(e.target.value)}
                              rows={2}
                              className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                              placeholder="Brief summary of the document's purpose and content"
                            />
                          ) : (
                            <span className="text-sm text-gray-600">{displayData.metadata.semantic_summary}</span>
                          )}
                        </div>
                        
                        {/* Key Concepts */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-gray-700">Key Concepts: </span>
                            {isEditing && (
                              <button
                                type="button"
                                onClick={addKeyConcept}
                                className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-600 bg-green-100 border border-green-300 rounded-md hover:bg-green-200"
                              >
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Add
                              </button>
                            )}
                          </div>
                          
                          {isEditing ? (
                            <div className="space-y-2">
                              {displayData.metadata.key_concepts.map((concept, idx) => (
                                <div key={idx} className="flex items-center space-x-2">
                                  <input
                                    type="text"
                                    value={concept}
                                    onChange={(e) => updateKeyConcept(idx, e.target.value)}
                                    className="flex-1 px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    placeholder={`Key concept ${idx + 1}`}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => removeKeyConcept(idx)}
                                    className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                  </button>
                                </div>
                              ))}
                              {displayData.metadata.key_concepts.length === 0 && (
                                <div className="text-center py-2 text-gray-500 bg-gray-50 rounded border-2 border-dashed border-gray-300">
                                  <p className="text-xs">No key concepts yet.</p>
                                </div>
                              )}
                            </div>
                          ) : (
                            displayData.metadata.key_concepts && displayData.metadata.key_concepts.length > 0 ? (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {displayData.metadata.key_concepts.map((concept, idx) => (
                                  <span key={idx} className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-gray-100 text-gray-800">
                                    {concept}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-sm text-gray-500 italic">No key concepts</span>
                            )
                          )}
                        </div>
                        
                        {/* Learning Objectives */}
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium text-gray-700">Learning Objectives: </span>
                            {isEditing && (
                              <button
                                type="button"
                                onClick={addLearningObjective}
                                className="inline-flex items-center px-2 py-1 text-xs font-medium text-blue-600 bg-blue-100 border border-blue-300 rounded-md hover:bg-blue-200"
                              >
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Add
                              </button>
                            )}
                          </div>
                          
                          {isEditing ? (
                            <div className="space-y-2">
                              {displayData.metadata.learning_objectives.map((objective, idx) => (
                                <div key={idx} className="flex items-center space-x-2">
                                  <input
                                    type="text"
                                    value={objective}
                                    onChange={(e) => updateLearningObjective(idx, e.target.value)}
                                    className="flex-1 px-2 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                                    placeholder={`Learning objective ${idx + 1}`}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => removeLearningObjective(idx)}
                                    className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                  </button>
                                </div>
                              ))}
                              {displayData.metadata.learning_objectives.length === 0 && (
                                <div className="text-center py-2 text-gray-500 bg-gray-50 rounded border-2 border-dashed border-gray-300">
                                  <p className="text-xs">No learning objectives yet.</p>
                                </div>
                              )}
                            </div>
                          ) : (
                            displayData.metadata.learning_objectives && displayData.metadata.learning_objectives.length > 0 ? (
                              <ul className="text-sm text-gray-600 mt-1 space-y-1">
                                {displayData.metadata.learning_objectives.map((objective, idx) => (
                                  <li key={idx} className="flex items-start">
                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
                                    {objective}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-sm text-gray-500 italic">No learning objectives</span>
                            )
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Edit/Save/Cancel buttons */}
                    <div className="ml-4 flex flex-col space-y-2">
                      {isEditing ? (
                        <>
                          <button
                            onClick={() => handleSaveDocument(doc.id)}
                            disabled={saving}
                            className="px-3 py-1 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 flex items-center space-x-1"
                          >
                            {saving ? (
                              <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                            ) : (
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                            <span>Save</span>
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            disabled={saving}
                            className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleEditDocument(doc)}
                          className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                        >
                          Edit
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Next Button */}
        <div className="flex justify-end pt-6 border-t border-gray-200">
          <button
            onClick={handleNext}
            disabled={completedStages?.has('pathways') || completedStages?.has('generation')}
            className="bg-blue-500 text-white px-6 py-2 rounded-md hover:bg-blue-600 transition-colors duration-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {(completedStages?.has('pathways') || completedStages?.has('generation'))
              ? 'Stage Complete' 
              : 'Next: Generate Learning Pathways'
            }
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center py-8">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-2">Waiting for Document Analysis</h3>
      <p className="text-gray-600">Document analysis hasn't started yet.</p>
    </div>
  );
};

export default Stage2Component; 