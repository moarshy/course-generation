"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Course, GenerationStatus, Stage3Response, Stage3Input, PathwaySummary, ModuleSummary, ModuleReorderRequest } from '@/lib/types';
import { 
  startStage3, 
  getGenerationStatus, 
  getStage3Result,
  reorderModules
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
  GraduationCap,
  Edit,
  Plus,
  X,
  FileText,
  GripVertical
} from 'lucide-react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import ModuleEditModal from './ModuleEditModal';
import AddModuleModal from './AddModuleModal';
import DeleteModuleModal from './DeleteModuleModal';

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
  const [status, setStatus] = useState<string>('pending');
  const [stage3Data, setStage3Data] = useState<Stage3Response | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [pollingStatus, setPollingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [selectedComplexity, setSelectedComplexity] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [editingModule, setEditingModule] = useState<{
    pathwayIndex: number;
    moduleIndex: number;
    module: ModuleSummary;
  } | null>(null);
  const [addingModule, setAddingModule] = useState<{
    pathwayIndex: number;
    pathwayTitle: string;
  } | null>(null);
  const [deletingModule, setDeletingModule] = useState<{
    pathwayIndex: number;
    pathwayId: string;
    pathwayTitle: string;
    moduleIndex: number;
    module: ModuleSummary;
  } | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset
  } = useForm<Stage3FormData>({
    resolver: zodResolver(stage3Schema),
    defaultValues: {
      complexity_level: 'intermediate',
      additional_instructions: ''
    }
  });

  const watchedComplexity = watch('complexity_level');
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
    
    setIsLoading(true);
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
      setIsLoading(false);
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

  const getCleanPath = (path: string): string => {
    // Remove the cache directory path and show a cleaner version
    return path.replace(/^.*\/\.cache\/[^/]+\//, '');
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

  const handleEditModule = (pathwayIndex: number, moduleIndex: number, module: ModuleSummary) => {
    setEditingModule({
      pathwayIndex,
      moduleIndex,
      module
    });
  };

  const handleAddModule = (pathwayIndex: number, pathwayTitle: string) => {
    setAddingModule({
      pathwayIndex,
      pathwayTitle
    });
  };

  const handleDeleteModule = (pathwayIndex: number, pathwayId: string, pathwayTitle: string, moduleIndex: number, module: ModuleSummary) => {
    setDeletingModule({
      pathwayIndex,
      pathwayId,
      pathwayTitle,
      moduleIndex,
      module
    });
  };

  const handleCloseEditModal = () => {
    setEditingModule(null);
  };

  const handleCloseAddModal = () => {
    setAddingModule(null);
  };

  const handleCloseDeleteModal = () => {
    setDeletingModule(null);
  };

  const handleSaveModule = async () => {
    // Refresh the stage 3 data after saving
    try {
      const updatedStage3Result = await getStage3Result(courseId);
      setStage3Data(updatedStage3Result);
    } catch (error) {
      console.error('Error refreshing stage 3 data:', error);
    }
    setEditingModule(null);
  };

  const handleModuleAdded = async () => {
    // Refresh the stage 3 data after adding
    try {
      const updatedStage3Result = await getStage3Result(courseId);
      setStage3Data(updatedStage3Result);
    } catch (error) {
      console.error('Error refreshing stage 3 data:', error);
    }
    setAddingModule(null);
  };

  const handleModuleDeleted = async () => {
    // Refresh the stage 3 data after deleting
    try {
      const updatedStage3Result = await getStage3Result(courseId);
      setStage3Data(updatedStage3Result);
    } catch (error) {
      console.error('Error refreshing stage 3 data:', error);
    }
    setDeletingModule(null);
  };

  const handleDragEnd = async (result: DropResult) => {
    const { destination, source, draggableId } = result;

    // If dropped outside a droppable area, do nothing
    if (!destination) return;

    // If dropped in the same position, do nothing
    if (destination.index === source.index) return;

    console.log('Drag result:', { source: source.index, destination: destination.index, draggableId });

    try {
      // Extract pathway index from draggableId (format: "pathwayIndex-moduleIndex")
      const [pathwayIndexStr] = draggableId.split('-');
      const pathwayIndex = parseInt(pathwayIndexStr);
      
      const pathway = stage3Data?.pathways[pathwayIndex];
      if (!pathway || !pathway.id) return;

      // Get current modules array
      const currentModules = [...(pathway.modules || [])];
      console.log('Current modules before reorder:', currentModules.map(m => m.title));

      // Perform the reorder locally first (optimistic update)
      const [movedModule] = currentModules.splice(source.index, 1);
      currentModules.splice(destination.index, 0, movedModule);

      console.log('Modules after local reorder:', currentModules.map(m => m.title));

      // Update UI optimistically
      const updatedPathways = [...(stage3Data?.pathways || [])];
      updatedPathways[pathwayIndex] = {
        ...pathway,
        modules: currentModules
      };
      
      setStage3Data({
        ...stage3Data!,
        pathways: updatedPathways
      });

      // Create simple module order array - just the new sequence of original indices
      const moduleOrder = currentModules.map((module, newIndex) => {
        // Find this module's original index in the unmodified pathway
        const originalIndex = pathway.modules?.findIndex(originalModule => originalModule.id === module.id);
        return originalIndex !== undefined && originalIndex !== -1 ? originalIndex : newIndex;
      });

      console.log('Module order being sent to API:', moduleOrder);

      // Call API to persist the change
      const reorderRequest: ModuleReorderRequest = {
        module_order: moduleOrder
      };

      await reorderModules(courseId, pathway.id, reorderRequest);
      console.log('API call successful');
      
      // Refresh data to ensure consistency
      const refreshedData = await getStage3Result(courseId);
      setStage3Data(refreshedData);
      console.log('Data refreshed successfully');

    } catch (error) {
      console.error('Error reordering modules:', error);
      // Revert optimistic update by refreshing from server
      try {
        const refreshedData = await getStage3Result(courseId);
        setStage3Data(refreshedData);
      } catch (refreshError) {
        console.error('Error refreshing after failed reorder:', refreshError);
      }
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
                        watchedComplexity === level
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
                  disabled={isLoading}
                  className="flex items-center space-x-2 px-6 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? (
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
      {hasStarted && !isComplete && (
        <div className="mb-8">
          <div className={`border rounded-xl p-6 ${
            pollingStatus ? 'bg-blue-50 border-blue-200' : 
            'bg-red-50 border-red-200'
          }`}>
            <div className="flex items-center space-x-3">
              {pollingStatus ? (
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
                <p className="text-lg font-semibold text-gray-900 mt-1 capitalize">
                  {stage3Data.pathways?.[0]?.complexity_level || stage3Data.pathways?.[0]?.complexity || 'Unknown'}
                </p>
              </div>
            </div>
          </div>

          {/* Learning Pathways */}
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-6">Generated Learning Pathways</h3>
            <div className="space-y-6">
              <DragDropContext onDragEnd={handleDragEnd}>
                {stage3Data.pathways?.map((pathway, pathwayIndex) => (
                  <div key={pathway.id || pathwayIndex} className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                    {/* Pathway Header */}
                    <div className="bg-gradient-to-r from-purple-600 to-indigo-700 text-white p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center space-x-2">
                            <span className="px-3 py-1 bg-white bg-opacity-90 text-purple-700 rounded-full text-sm font-bold">
                              Pathway {pathway.index + 1}
                            </span>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              pathway.complexity === 'beginner' ? 'bg-green-100 text-green-800' :
                              pathway.complexity === 'intermediate' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {pathway.complexity}
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold">{pathway.modules?.length || 0}</div>
                          <div className="text-xs text-purple-200">modules</div>
                        </div>
                      </div>
                      <div className="mt-3">
                        <h4 className="text-lg font-bold mb-1">{pathway.title}</h4>
                        <p className="text-purple-100 text-sm leading-relaxed">{pathway.description}</p>
                      </div>
                    </div>

                    {/* Modules - Single Column Layout */}
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-4">
                        <h5 className="text-base font-semibold text-gray-900">Learning Modules</h5>
                        <div className="flex items-center space-x-2 text-xs text-green-600">
                          <GripVertical className="w-3 h-3" />
                          <span>Drag to reorder</span>
                        </div>
                      </div>
                      
                      {/* Single Column Module List */}
                      <Droppable droppableId={`modules-${pathwayIndex}`} type="module">
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.droppableProps}
                            className={`space-y-3 ${snapshot.isDraggingOver ? 'border-purple-300' : ''}`}
                          >
                            {pathway.modules?.map((module, moduleIndex) => (
                              <Draggable
                                key={module.id || moduleIndex} 
                                draggableId={`${pathwayIndex}-${moduleIndex}`}
                                index={moduleIndex}
                              >
                                {(provided, snapshot) => (
                                  <div
                                    ref={provided.innerRef}
                                    {...provided.draggableProps}
                                    {...provided.dragHandleProps}
                                    className={`group border border-gray-200 rounded-xl overflow-hidden hover:border-purple-300 hover:shadow-md transition-all duration-200 ${snapshot.isDragging ? 'shadow-lg' : ''}`}
                                  >
                                    {/* Module Header */}
                                    <div className="bg-gradient-to-r from-gray-50 to-purple-50 border-b border-gray-200 p-3">
                                      <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-3">
                                          {/* Drag Handle */}
                                          <div className="flex flex-col space-y-1 opacity-60 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing" title="Drag to reorder">
                                            <GripVertical className="w-4 h-4 text-gray-500 hover:text-purple-600" />
                                          </div>
                                          
                                          {/* Module Number */}
                                          <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                                            <span className="text-xs font-bold text-purple-600">{moduleIndex + 1}</span>
                                          </div>
                                          
                                          {/* Module Info */}
                                          <div className="flex-1">
                                            <div className="flex items-center space-x-2 mb-1">
                                              <h6 className="text-base font-semibold text-gray-900">{module.title}</h6>
                                              {module.theme && (
                                                <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded font-medium">
                                                  {module.theme}
                                                </span>
                                              )}
                                            </div>
                                            <p className="text-sm text-gray-600 leading-relaxed line-clamp-2">{module.description}</p>
                                          </div>
                                        </div>
                                        
                                        {/* Action Buttons */}
                                        <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                          <button 
                                            onClick={() => handleEditModule(pathwayIndex, moduleIndex, module)}
                                            className="relative p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-all duration-200 group/edit" 
                                            title="Edit Module"
                                          >
                                            <Edit className="w-3.5 h-3.5" />
                                          </button>
                                          <button 
                                            onClick={() => handleAddModule(pathwayIndex, pathway.title)}
                                            className="relative p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-all duration-200 group/add" 
                                            title="Add Module After"
                                          >
                                            <Plus className="w-3.5 h-3.5" />
                                          </button>
                                          <button 
                                            onClick={() => handleDeleteModule(pathwayIndex, pathway.id || '', pathway.title, moduleIndex, module)}
                                            className="relative p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-all duration-200 group/delete" 
                                            title="Delete Module"
                                          >
                                            <X className="w-3.5 h-3.5" />
                                          </button>
                                        </div>
                                      </div>
                                    </div>

                                    {/* Module Content */}
                                    <div className="p-3">
                                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                        {/* Learning Objectives */}
                                        {module.learning_objectives && module.learning_objectives.length > 0 && (
                                          <div>
                                            <div className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                                              <Target className="w-4 h-4 text-green-600 mr-2" />
                                              Learning Objectives
                                            </div>
                                            <ul className="space-y-2">
                                              {module.learning_objectives.map((objective, objIndex) => (
                                                <li key={objIndex} className="flex items-start space-x-2">
                                                  <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                                  <span className="text-sm text-gray-700">{objective}</span>
                                                </li>
                                              ))}
                                            </ul>
                                          </div>
                                        )}

                                        {/* Source Documents */}
                                        <div>
                                          <div className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                                            <FileText className="w-4 h-4 text-blue-600 mr-2" />
                                            Source Documents
                                          </div>
                                          <div className="space-y-2">
                                            {module.documents && module.documents.length > 0 ? (
                                              module.documents.map((docPath, docIndex) => (
                                                <div key={docIndex} className="flex items-center space-x-2 text-xs bg-blue-50 border border-blue-200 rounded-lg p-2">
                                                  <FileText className="w-3 h-3 text-blue-600 flex-shrink-0" />
                                                  <span className="font-mono text-blue-800 break-all flex-1">{getCleanPath(docPath)}</span>
                                                </div>
                                              ))
                                            ) : (
                                              <div className="text-sm text-gray-500 italic bg-gray-50 border border-gray-200 rounded-lg p-2">
                                                No source documents assigned
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </div>

                                      {/* Module Stats */}
                                      <div className="mt-4 pt-4 border-t border-gray-100">
                                        <div className="flex items-center justify-between text-xs text-gray-500">
                                          <span>Module {moduleIndex + 1} of {pathway.modules?.length}</span>
                                          <div className="flex items-center space-x-4">
                                            <span>{module.learning_objectives?.length || 0} objectives</span>
                                            <span>{module.documents?.length || 0} documents</span>
                                            {module.estimated_time && <span>{module.estimated_time}</span>}
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </Draggable>
                            ))}
                            {provided.placeholder}
                          </div>
                        )}
                      </Droppable>

                      {/* Add Module Button */}
                      <div className="mt-6 pt-4 border-t border-gray-200">
                        <button 
                          onClick={() => handleAddModule(pathwayIndex, pathway.title)}
                          className="w-full flex items-center justify-center space-x-2 py-4 text-green-600 border-2 border-dashed border-green-300 rounded-xl hover:border-green-400 hover:bg-green-50 transition-colors"
                        >
                          <Plus className="w-5 h-5" />
                          <span className="font-medium">Add New Module</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </DragDropContext>
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

      {/* Module Edit Modal */}
      {editingModule && (
        <ModuleEditModal
          courseId={courseId}
          pathwayIndex={editingModule.pathwayIndex}
          moduleIndex={editingModule.moduleIndex}
          module={editingModule.module}
          isOpen={true}
          onClose={handleCloseEditModal}
          onSave={handleSaveModule}
        />
      )}

      {/* Add Module Modal */}
      {addingModule && (
        <AddModuleModal
          courseId={courseId}
          pathwayIndex={addingModule.pathwayIndex}
          pathwayTitle={addingModule.pathwayTitle}
          isOpen={true}
          onClose={handleCloseAddModal}
          onSave={handleModuleAdded}
        />
      )}

      {/* Delete Module Modal */}
      {deletingModule && (
        <DeleteModuleModal
          courseId={courseId}
          pathwayId={deletingModule.pathwayId}
          pathwayTitle={deletingModule.pathwayTitle}
          module={deletingModule.module}
          isOpen={true}
          onClose={handleCloseDeleteModal}
          onDelete={handleModuleDeleted}
        />
      )}
    </div>
  );
}