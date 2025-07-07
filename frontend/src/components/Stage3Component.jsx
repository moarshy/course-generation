import React, { useState, useEffect, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import ModalProvider from './ModalProvider';
import { useModal } from '../hooks/useModal';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Generate stable UUID for modules without proper IDs
const generateStableId = (module, pathwayIndex, moduleIndex) => {
  // Use module_id if available
  if (module.module_id) return module.module_id;
  if (module.id) return module.id;
  
  // Generate a stable ID based on module content rather than position
  // This creates a consistent ID based on module title and content
  const contentHash = (module.title || '').toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
  const timestamp = module.created_at || module.updated_at || Date.now();
  return `module-${pathwayIndex}-${contentHash}-${timestamp}`;
};

const Stage3Component = ({ course, taskStatus, stageData, onNext }) => {
  const { getAccessTokenSilently } = useAuth0();
  const [learningPathways, setLearningPathways] = useState([]);
  const [availableDocuments, setAvailableDocuments] = useState([]);
  const [selectedPathway, setSelectedPathway] = useState(0);
  const [selectedComplexity, setSelectedComplexity] = useState('intermediate');
  const [editingPathway, setEditingPathway] = useState(null);
  const [editingModule, setEditingModule] = useState(null);
  const [creatingModule, setCreatingModule] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  
  // Progress tracking state
  const [progressData, setProgressData] = useState(null);
  
  // Custom modal hook
  const {
    alertModal,
    confirmModal,
    closeAlert,
    closeConfirm,
    showError,
    showDeleteConfirm
  } = useModal();

  // Extract courseId from course object or URL params
  const courseId = course?.id || course?.course_id || course?.project_id || window.location.pathname.split('/').pop();

  // Better loading detection logic - check if Stage 3 specifically is running
  const isCompleted = taskStatus?.stage_statuses?.PATHWAY_BUILDING === 'completed' || 
                      taskStatus?.stage_statuses?.pathway_building === 'completed' ||
                      taskStatus?.completed_stages?.includes('PATHWAY_BUILDING') ||
                      taskStatus?.completed_stages?.includes('pathway_building');
  
  const isLoading = (taskStatus?.stage_statuses?.PATHWAY_BUILDING === 'running' || 
                     taskStatus?.stage_statuses?.pathway_building === 'running' ||
                     (taskStatus?.current_stage === 'PATHWAY_BUILDING' && taskStatus?.status === 'running') ||
                     (taskStatus?.current_stage === 'pathway_building' && taskStatus?.status === 'running'));
  
  const isFailed = taskStatus?.stage_statuses?.PATHWAY_BUILDING === 'failed' || 
                   taskStatus?.stage_statuses?.pathway_building === 'failed';

  // Progress polling function
  const fetchProgress = useCallback(async () => {
    try {
      console.log('Fetching Stage 3 progress for course:', courseId);
      const token = await getAccessTokenSilently();
      const response = await axios.get(`${API_BASE_URL}/course-generation/stage3/progress?course_id=${courseId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      console.log('Stage 3 progress data:', response.data);
      setProgressData(response.data);
    } catch (error) {
      console.error('Error fetching Stage 3 progress:', error);
      // Don't set error state here as it might just be that progress data isn't available yet
    }
  }, [courseId, getAccessTokenSilently]);

  // Poll for progress when task is running
  useEffect(() => {
    console.log('Stage 3 isLoading changed:', isLoading, 'taskStatus:', taskStatus);
    if (isLoading) {
      console.log('Starting Stage 3 progress polling...');
      // Start polling immediately
      fetchProgress();
      
      // Poll every 2 seconds
      const interval = setInterval(fetchProgress, 2000);
      
      return () => {
        console.log('Stopping Stage 3 progress polling');
        clearInterval(interval);
      };
    } else {
      // Clear progress data when not loading
      setProgressData(null);
    }
  }, [isLoading, fetchProgress]);

  // Load learning pathways and available documents when component mounts or when stage completes
  useEffect(() => {
    if (isCompleted) {
      loadLearningPathways();
      loadAvailableDocuments();
    }
  }, [isCompleted]);

  const loadLearningPathways = useCallback(async () => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(`${API_BASE_URL}/course-generation/${courseId}/stage3`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data && response.data.pathways) {
        setLearningPathways(response.data.pathways);
      }
    } catch (error) {
      console.error('Error loading learning pathways:', error);
    }
  }, [courseId, getAccessTokenSilently]);

  const loadAvailableDocuments = async () => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(`${API_BASE_URL}/course-generation/${courseId}/stage2`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data && response.data.analyzed_documents) {
        // Extract document paths for dropdown
        const docPaths = response.data.analyzed_documents.map(doc => doc.path);
        setAvailableDocuments(docPaths);
      }
    } catch (error) {
      console.error('Error loading available documents:', error);
    }
  };

  const refreshLearningPathways = useCallback(async () => {
    setRefreshing(true);
    await loadLearningPathways();
    setRefreshing(false);
  }, [loadLearningPathways]);

  const updatePathway = async (pathwayIndex, updates) => {
    try {
      setSaving(true);
      const token = await getAccessTokenSilently();
      
      await axios.put(`${API_BASE_URL}/course-generation/${courseId}/stage3/pathway`, {
        pathway_index: pathwayIndex,
        pathway_updates: updates
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Refresh pathways after update
      await refreshLearningPathways();
      setEditingPathway(null);
      
    } catch (error) {
      console.error('Error updating pathway:', error);
      showError('Failed to update pathway. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const updateModule = async (pathwayIndex, moduleIndex, updates) => {
    try {
      setSaving(true);
      const token = await getAccessTokenSilently();
      
      await axios.put(`${API_BASE_URL}/course-generation/${courseId}/stage3/module`, {
        pathway_index: pathwayIndex,
        module_index: moduleIndex,
        module_updates: updates
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Refresh pathways after update
      await refreshLearningPathways();
      setEditingModule(null);
      
    } catch (error) {
      console.error('Error updating module:', error);
      showError('Failed to update module. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const createModule = async (pathwayIndex, moduleData) => {
    try {
      setSaving(true);
      const token = await getAccessTokenSilently();
      
      await axios.post(`${API_BASE_URL}/course-generation/${courseId}/stage3/module`, {
        pathway_index: pathwayIndex,
        module_data: moduleData
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Refresh pathways after creation
      await refreshLearningPathways();
      setCreatingModule(false);
      
    } catch (error) {
      console.error('Error creating module:', error);
      showError('Failed to create module. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const deleteModule = (pathwayIndex, moduleIndex) => {
    showDeleteConfirm(
      'Are you sure you want to delete this module?',
      async () => {
        try {
          setSaving(true);
          const token = await getAccessTokenSilently();
          
          await axios.delete(`${API_BASE_URL}/course-generation/${courseId}/stage3/pathway/${pathwayIndex}/module/${moduleIndex}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          
          // Refresh pathways after deletion
          await refreshLearningPathways();
          
        } catch (error) {
          console.error('Error deleting module:', error);
          showError('Failed to delete module. Please try again.');
        } finally {
          setSaving(false);
        }
      },
      'Delete Module'
    );
  };

  const reorderModules = useCallback(async (pathwayIndex, sourceIndex, destinationIndex) => {
    try {
      setSaving(true);
      
      // Optimistically update the local state first
      const updatedPathways = [...learningPathways];
      const pathway = updatedPathways[pathwayIndex];
      const newModules = [...pathway.modules];
      
      // Perform the reorder
      const [movedModule] = newModules.splice(sourceIndex, 1);
      newModules.splice(destinationIndex, 0, movedModule);
      
      // Update local state immediately for smooth UX
      updatedPathways[pathwayIndex] = {
        ...pathway,
        modules: newModules
      };
      setLearningPathways(updatedPathways);
      
      // Create the new order array for the API
      const originalLength = pathway.modules.length;
      const newOrder = Array.from({length: originalLength}, (_, i) => i);
      const [movedIndex] = newOrder.splice(sourceIndex, 1);
      newOrder.splice(destinationIndex, 0, movedIndex);
      
      console.log('Reordering modules:', {
        sourceIndex,
        destinationIndex,
        newOrder
      });
      
      const token = await getAccessTokenSilently();
      
      await axios.put(`${API_BASE_URL}/course-generation/${courseId}/stage3/pathway/${pathwayIndex}/modules/reorder`, {
        module_order: newOrder
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Only refresh from server if needed (commenting out to prevent unnecessary re-renders)
      // await refreshLearningPathways();
      
    } catch (error) {
      console.error('Error reordering modules:', error);
      showError('Failed to reorder modules. Please try again.');
      // Reload to revert changes only on error
      await refreshLearningPathways();
    } finally {
      setSaving(false);
    }
  }, [learningPathways, courseId, getAccessTokenSilently, refreshLearningPathways, setSaving]);

  const handleDragEnd = useCallback((result) => {
    // Add validation
    if (!result.destination) {
      console.log('Drag cancelled - no destination');
      return;
    }
    
    if (!learningPathways || !learningPathways[selectedPathway] || !learningPathways[selectedPathway].modules) {
      console.error('No current pathway or modules available');
      return;
    }
    
    const sourceIndex = result.source.index;
    const destinationIndex = result.destination.index;
    
    if (sourceIndex === destinationIndex) {
      console.log('Drag cancelled - same position');
      return;
    }
    
    const currentModules = learningPathways[selectedPathway].modules;
    
    // Validate indices
    if (sourceIndex < 0 || sourceIndex >= currentModules.length ||
        destinationIndex < 0 || destinationIndex >= currentModules.length) {
      console.error('Invalid drag indices:', { 
        sourceIndex, 
        destinationIndex, 
        moduleCount: currentModules.length 
      });
      return;
    }
    
    reorderModules(selectedPathway, sourceIndex, destinationIndex);
  }, [selectedPathway, reorderModules, learningPathways]);

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Generating Learning Pathways</h3>
        <p className="text-gray-600 mb-4">
          {progressData?.stage_description || 'Creating personalized learning paths for different complexity levels...'}
        </p>
        
        {/* Enhanced Progress Display */}
        <div className="max-w-2xl mx-auto space-y-4">
          {/* Main Progress Bar */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Overall Progress</span>
              <span>{progressData ? Math.round((progressData.generated_pathways / progressData.total_pathways) * 100) : 0}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="bg-blue-500 h-3 rounded-full transition-all duration-300"
                style={{ width: `${progressData ? Math.round((progressData.generated_pathways / progressData.total_pathways) * 100) : 0}%` }}
              />
            </div>
            
            {/* Pathway Progress Details */}
            {progressData && (
              <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-lg font-semibold text-blue-600">
                    {progressData.generated_pathways || 0}
                  </div>
                  <div className="text-gray-600">Generated</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-600">
                    {progressData.total_pathways || 3}
                  </div>
                  <div className="text-gray-600">Total Pathways</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-green-600">
                    {progressData.completed_complexities?.length || 0}
                  </div>
                  <div className="text-gray-600">Completed</div>
                </div>
              </div>
            )}
          </div>

          {/* Current Complexity Being Processed */}
          {progressData?.current_complexity && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse mr-3"></div>
                <div className="flex-1">
                  <div className="font-medium text-blue-900">Currently Processing:</div>
                  <div className="text-sm font-semibold text-blue-700 capitalize">
                    {progressData.current_complexity.toLowerCase()} Level Pathway
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Completed Complexities */}
          {progressData?.completed_complexities && progressData.completed_complexities.length > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="font-medium text-green-900 mb-2">Completed Pathways:</div>
              <div className="space-y-1">
                {progressData.completed_complexities.map((complexity, index) => (
                  <div key={index} className="flex items-center text-sm text-green-700">
                    <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium capitalize">{complexity.toLowerCase()} Level</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Processing Stage Description */}
        <div className="mt-6 text-left max-w-md mx-auto">
          <h4 className="font-medium text-gray-900 mb-3">Pathway Generation Process</h4>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <div className={`w-2 h-2 rounded-full mt-2 mr-3 flex-shrink-0 ${
                progressData?.stage === 'initializing' ? 'bg-blue-500 animate-pulse' : 
                progressData?.completed_complexities?.includes('BEGINNER') ? 'bg-green-500' : 'bg-gray-300'
              }`}></div>
              <span>Generating beginner-friendly learning pathway</span>
            </li>
            <li className="flex items-start">
              <div className={`w-2 h-2 rounded-full mt-2 mr-3 flex-shrink-0 ${
                progressData?.current_complexity === 'INTERMEDIATE' ? 'bg-blue-500 animate-pulse' : 
                progressData?.completed_complexities?.includes('INTERMEDIATE') ? 'bg-green-500' : 'bg-gray-300'
              }`}></div>
              <span>Creating intermediate complexity pathway</span>
            </li>
            <li className="flex items-start">
              <div className={`w-2 h-2 rounded-full mt-2 mr-3 flex-shrink-0 ${
                progressData?.current_complexity === 'ADVANCED' ? 'bg-blue-500 animate-pulse' : 
                progressData?.completed_complexities?.includes('ADVANCED') ? 'bg-green-500' : 
                progressData?.stage === 'completed' ? 'bg-green-500' : 'bg-gray-300'
              }`}></div>
              <span>Building advanced technical pathway</span>
            </li>
          </ul>
        </div>
      </div>
    );
  }

  if (isFailed) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-red-800 mb-2">Pathway Generation Failed</h3>
        <p className="text-red-700 mb-4">
          There was an error generating the learning pathways. Please try again.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!isCompleted) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-800 mb-2">Generating Learning Pathways</h3>
        <p className="text-blue-700">
          Please wait while we generate personalized learning pathways based on your documents...
        </p>
      </div>
    );
  }

  if (learningPathways.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-yellow-800 mb-2">No Learning Pathways Found</h3>
        <p className="text-yellow-700 mb-4">
          No learning pathways were generated. This might be due to insufficient document analysis.
        </p>
        <button
          onClick={refreshLearningPathways}
          className="bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700"
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
    );
  }

  const currentPathway = learningPathways[selectedPathway];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">Learning Pathways</h2>
        <button
          onClick={refreshLearningPathways}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Pathway Selection */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-4">Select a Pathway</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {learningPathways.map((pathway, index) => (
            <div
              key={index}
              className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                selectedPathway === index
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setSelectedPathway(index)}
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold text-gray-900">{pathway.title}</h4>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingPathway(index);
                  }}
                  className="text-blue-600 hover:text-blue-800"
                >
                  Edit
                </button>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>Complexity: {pathway.complexity}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Current Pathway Details */}
      {currentPathway && (
        <div key={`pathway-${selectedPathway}`} className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">{currentPathway.title}</h3>
            <button
              onClick={() => setCreatingModule(true)}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
            >
              Add Module
            </button>
          </div>
          
          <p className="text-gray-700 mb-4">{currentPathway.description}</p>
          
          <div className="mb-6">
            <h4 className="font-semibold mb-2">Modules ({currentPathway.modules.length})</h4>
            
            <DragDropContext onDragEnd={handleDragEnd}>
              <Droppable droppableId={`pathway-${selectedPathway}-modules`}>
                {(provided) => (
                  <div {...provided.droppableProps} ref={provided.innerRef}>
                    {currentPathway.modules.map((module, moduleIndex) => {
                      // Generate a truly stable ID that never depends on position
                      const stableId = generateStableId(module, selectedPathway, moduleIndex);
                      const draggableId = `module-${stableId}`;
                      return (
                        <Draggable 
                          key={draggableId} 
                          draggableId={draggableId} 
                          index={moduleIndex}
                        >
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              className={`bg-gray-50 border rounded-lg p-4 mb-3 ${
                                snapshot.isDragging ? 'shadow-lg' : ''
                              }`}
                            >
                            <div className="flex items-center justify-between mb-2">
                              <h5 className="font-semibold text-gray-900">{module.title}</h5>
                              <div className="flex space-x-2">
                                <button
                                  onClick={() => setEditingModule({ pathwayIndex: selectedPathway, moduleIndex, module })}
                                  className="text-blue-600 hover:text-blue-800"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => deleteModule(selectedPathway, moduleIndex)}
                                  className="text-red-600 hover:text-red-800"
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                            
                            <p className="text-sm text-gray-600 mb-2">{module.description}</p>
                            
                            <div className="text-xs text-gray-500 mb-2">
                              <span className="inline-block bg-gray-200 px-2 py-1 rounded mr-2">
                                {module.theme}
                              </span>
                              <span className="inline-block bg-gray-200 px-2 py-1 rounded">
                                {module.target_complexity}
                              </span>
                            </div>
                            
                            {module.learning_objectives && module.learning_objectives.length > 0 && (
                              <div className="mb-2">
                                <strong className="text-xs text-gray-700">Learning Objectives:</strong>
                                <ul className="text-xs text-gray-600 ml-4">
                                  {module.learning_objectives.map((objective, i) => (
                                    <li key={i} className="list-disc">{objective}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            
                            {module.linked_documents && module.linked_documents.length > 0 && (
                              <div>
                                <strong className="text-xs text-gray-700">Linked Documents:</strong>
                                <div className="text-xs text-gray-600">
                                  {module.linked_documents.join(', ')}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </Draggable>
                    );
                    })}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </DragDropContext>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Target Complexity Level:
              </label>
              <select
                value={selectedComplexity}
                onChange={(e) => setSelectedComplexity(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
            
            <div className="flex justify-between">
              <button
                onClick={() => {
                  // Transform pathway to match GroupedLearningPath structure
                  let transformedPathway = null;
                  if (selectedPathway !== null && learningPathways[selectedPathway]) {
                    const pathway = learningPathways[selectedPathway];
                    
                    // Transform modules to match LearningModule structure
                    const transformedModules = (pathway.modules || []).map((module, index) => ({
                      module_id: module.module_id || module.id || `module-${index}`,
                      title: module.title || '',
                      description: module.description || '',
                      learning_objectives: module.learning_objectives || [],
                      linked_documents: module.linked_documents || [],
                      theme: module.theme || 'General',
                      target_complexity: module.target_complexity || selectedComplexity,
                      content: module.content || null,
                      assessment: module.assessment || null
                    }));
                    
                    transformedPathway = {
                      pathway_id: pathway.id || pathway.pathway_id || `pathway-${selectedPathway}-${Date.now()}`,
                      title: pathway.title,
                      description: pathway.description,
                      target_complexity: selectedComplexity, // Use user-selected complexity
                      modules: transformedModules,
                      welcome_message: pathway.welcome_message || `Welcome to ${pathway.title}`
                    };
                  }
                  
                  const stage4Data = { 
                    selected_complexity: selectedComplexity,
                    custom_pathway: transformedPathway
                  };
                  console.log('Sending Stage 4 data:', stage4Data);
                  onNext(stage4Data);
                }}
                className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
              >
                Generate Course →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pathway Edit Modal */}
      {editingPathway !== null && (
        <PathwayEditModal
          pathway={learningPathways[editingPathway]}
          onSave={(updates) => updatePathway(editingPathway, updates)}
          onCancel={() => setEditingPathway(null)}
          saving={saving}
        />
      )}

      {/* Module Edit Modal */}
      {editingModule && (
        <ModuleEditModal
          module={editingModule.module}
          onSave={(updates) => updateModule(editingModule.pathwayIndex, editingModule.moduleIndex, updates)}
          onCancel={() => setEditingModule(null)}
          saving={saving}
          availableDocuments={availableDocuments}
        />
      )}

      {/* Module Create Modal */}
      {creatingModule && (
        <ModuleCreateModal
          onSave={(moduleData) => createModule(selectedPathway, moduleData)}
          onCancel={() => setCreatingModule(false)}
          saving={saving}
          availableDocuments={availableDocuments}
        />
      )}

      <ModalProvider
        alertModal={alertModal}
        onCloseAlert={closeAlert}
        confirmModal={confirmModal}
        onCloseConfirm={closeConfirm}
        onConfirm={confirmModal.onConfirm}
      />
    </div>
  );
};

// Pathway Edit Modal Component
const PathwayEditModal = ({ pathway, onSave, onCancel, saving }) => {
  const [formData, setFormData] = useState({
    title: pathway.title || '',
    description: pathway.description || '',
    target_complexity: pathway.target_complexity || 'intermediate',
    estimated_duration: pathway.estimated_duration || '',
    prerequisites: pathway.prerequisites || []
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">Edit Pathway</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows="3"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Complexity</label>
            <select
              value={formData.target_complexity}
              onChange={(e) => setFormData({...formData, target_complexity: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Estimated Duration</label>
            <input
              type="text"
              value={formData.estimated_duration}
              onChange={(e) => setFormData({...formData, estimated_duration: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., 2 weeks, 40 hours"
            />
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Module Edit Modal Component
const ModuleEditModal = ({ module, onSave, onCancel, saving, availableDocuments = [] }) => {
  const [formData, setFormData] = useState({
    title: module.title || '',
    description: module.description || '',
    theme: module.theme || '',
    target_complexity: module.target_complexity || 'intermediate',
    learning_objectives: module.learning_objectives || [],
    linked_documents: module.linked_documents || []
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  const handleObjectiveChange = (index, value) => {
    const newObjectives = [...formData.learning_objectives];
    newObjectives[index] = value;
    setFormData({...formData, learning_objectives: newObjectives});
  };

  const addObjective = () => {
    setFormData({...formData, learning_objectives: [...formData.learning_objectives, '']});
  };

  const removeObjective = (index) => {
    const newObjectives = formData.learning_objectives.filter((_, i) => i !== index);
    setFormData({...formData, learning_objectives: newObjectives});
  };

  const handleDocumentChange = (docPath, isSelected) => {
    const newLinkedDocs = isSelected 
      ? [...formData.linked_documents, docPath]
      : formData.linked_documents.filter(doc => doc !== docPath);
    setFormData({...formData, linked_documents: newLinkedDocs});
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">Edit Module</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows="3"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Theme</label>
            <input
              type="text"
              value={formData.theme}
              onChange={(e) => setFormData({...formData, theme: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Complexity</label>
            <select
              value={formData.target_complexity}
              onChange={(e) => setFormData({...formData, target_complexity: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Learning Objectives</label>
            {formData.learning_objectives.map((objective, index) => (
              <div key={index} className="flex items-center space-x-2 mb-2">
                <input
                  type="text"
                  value={objective}
                  onChange={(e) => handleObjectiveChange(index, e.target.value)}
                  className="flex-1 p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter learning objective"
                />
                <button
                  type="button"
                  onClick={() => removeObjective(index)}
                  className="text-red-600 hover:text-red-800"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addObjective}
              className="text-blue-600 hover:text-blue-800"
            >
              Add Objective
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Linked Documents</label>
            <div className="max-h-40 overflow-y-auto border border-gray-300 rounded p-2">
              {availableDocuments.length > 0 ? (
                availableDocuments.map((docPath, index) => (
                  <div key={index} className="flex items-center space-x-2 mb-1">
                    <input
                      type="checkbox"
                      id={`doc-${index}`}
                      checked={formData.linked_documents.includes(docPath)}
                      onChange={(e) => handleDocumentChange(docPath, e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <label htmlFor={`doc-${index}`} className="text-sm text-gray-700 cursor-pointer flex-1">
                      {docPath}
                    </label>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No documents available. Make sure Stage 2 is completed.</p>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Selected: {formData.linked_documents.length} document{formData.linked_documents.length !== 1 ? 's' : ''}
            </p>
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Module Create Modal Component
const ModuleCreateModal = ({ onSave, onCancel, saving, availableDocuments = [] }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    theme: 'General',
    target_complexity: 'intermediate',
    learning_objectives: [''],
    linked_documents: []
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    // Filter out empty objectives
    const filteredObjectives = formData.learning_objectives.filter(obj => obj.trim() !== '');
    onSave({...formData, learning_objectives: filteredObjectives});
  };

  const handleObjectiveChange = (index, value) => {
    const newObjectives = [...formData.learning_objectives];
    newObjectives[index] = value;
    setFormData({...formData, learning_objectives: newObjectives});
  };

  const addObjective = () => {
    setFormData({...formData, learning_objectives: [...formData.learning_objectives, '']});
  };

  const removeObjective = (index) => {
    const newObjectives = formData.learning_objectives.filter((_, i) => i !== index);
    setFormData({...formData, learning_objectives: newObjectives});
  };

  const handleDocumentChange = (docPath, isSelected) => {
    const newLinkedDocs = isSelected 
      ? [...formData.linked_documents, docPath]
      : formData.linked_documents.filter(doc => doc !== docPath);
    setFormData({...formData, linked_documents: newLinkedDocs});
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">Create New Module</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              rows="3"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Theme</label>
            <input
              type="text"
              value={formData.theme}
              onChange={(e) => setFormData({...formData, theme: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Complexity</label>
            <select
              value={formData.target_complexity}
              onChange={(e) => setFormData({...formData, target_complexity: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Learning Objectives</label>
            {formData.learning_objectives.map((objective, index) => (
              <div key={index} className="flex items-center space-x-2 mb-2">
                <input
                  type="text"
                  value={objective}
                  onChange={(e) => handleObjectiveChange(index, e.target.value)}
                  className="flex-1 p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter learning objective"
                />
                <button
                  type="button"
                  onClick={() => removeObjective(index)}
                  className="text-red-600 hover:text-red-800"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addObjective}
              className="text-blue-600 hover:text-blue-800"
            >
              Add Objective
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Linked Documents</label>
            <div className="max-h-40 overflow-y-auto border border-gray-300 rounded p-2">
              {availableDocuments.length > 0 ? (
                availableDocuments.map((docPath, index) => (
                  <div key={index} className="flex items-center space-x-2 mb-1">
                    <input
                      type="checkbox"
                      id={`create-doc-${index}`}
                      checked={formData.linked_documents.includes(docPath)}
                      onChange={(e) => handleDocumentChange(docPath, e.target.checked)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <label htmlFor={`create-doc-${index}`} className="text-sm text-gray-700 cursor-pointer flex-1">
                      {docPath}
                    </label>
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500">No documents available. Make sure Stage 2 is completed.</p>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Selected: {formData.linked_documents.length} document{formData.linked_documents.length !== 1 ? 's' : ''}
            </p>
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Stage3Component; 