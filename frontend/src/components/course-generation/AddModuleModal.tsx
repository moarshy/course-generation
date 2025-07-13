"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { DocumentSummary, ModuleCreate, CreateModuleRequest } from '@/lib/types';
import { getStage2Result, addModule } from '@/lib/api';
import { 
  X, 
  Save, 
  FileText, 
  Target, 
  Plus, 
  Trash2,
  Search,
  CheckCircle,
  Circle
} from 'lucide-react';

const moduleCreateSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().min(1, 'Description is required'),
  learning_objectives: z.array(z.string()).optional(),
  theme: z.string().optional(),
  target_complexity: z.string().optional()
});

type ModuleCreateFormData = z.infer<typeof moduleCreateSchema>;

interface AddModuleModalProps {
  courseId: string;
  pathwayIndex: number;
  pathwayTitle: string;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

export default function AddModuleModal({
  courseId,
  pathwayIndex,
  pathwayTitle,
  isOpen,
  onClose,
  onSave
}: AddModuleModalProps) {
  const [availableDocuments, setAvailableDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loadingDocuments, setLoadingDocuments] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    reset
  } = useForm<ModuleCreateFormData>({
    resolver: zodResolver(moduleCreateSchema),
    defaultValues: {
      title: '',
      description: '',
      learning_objectives: [],
      theme: '',
      target_complexity: 'intermediate'
    }
  });

  const learningObjectives = watch('learning_objectives') || [];

  // Load available documents when modal opens
  useEffect(() => {
    if (isOpen) {
      loadAvailableDocuments();
      // Reset form when modal opens
      reset({
        title: '',
        description: '',
        learning_objectives: [],
        theme: '',
        target_complexity: 'intermediate'
      });
      setSelectedDocuments([]);
    }
  }, [isOpen, reset]);

  const loadAvailableDocuments = async () => {
    setLoadingDocuments(true);
    try {
      const stage2Data = await getStage2Result(courseId);
      setAvailableDocuments(stage2Data.analyzed_documents || []);
    } catch (err: any) {
      setError('Failed to load available documents');
      console.error('Error loading documents:', err);
    } finally {
      setLoadingDocuments(false);
    }
  };

  const handleDocumentToggle = (documentPath: string) => {
    setSelectedDocuments(prev => 
      prev.includes(documentPath)
        ? prev.filter(path => path !== documentPath)
        : [...prev, documentPath]
    );
  };

  const addLearningObjective = () => {
    const currentObjectives = learningObjectives;
    setValue('learning_objectives', [...currentObjectives, '']);
  };

  const removeLearningObjective = (index: number) => {
    const currentObjectives = learningObjectives;
    setValue('learning_objectives', currentObjectives.filter((_, i) => i !== index));
  };

  const updateLearningObjective = (index: number, value: string) => {
    const currentObjectives = learningObjectives;
    const updated = [...currentObjectives];
    updated[index] = value;
    setValue('learning_objectives', updated);
  };

  const handleSave = async (data: ModuleCreateFormData) => {
    setLoading(true);
    setError(null);

    try {
      const moduleData: ModuleCreate = {
        title: data.title,
        description: data.description,
        learning_objectives: data.learning_objectives?.filter(obj => obj.trim() !== '') || [],
        linked_documents: selectedDocuments,
        theme: data.theme,
        target_complexity: data.target_complexity
      };

      const createRequest: CreateModuleRequest = {
        pathway_index: pathwayIndex,
        module_data: moduleData
      };

      await addModule(courseId, createRequest);
      onSave();
      onClose();
    } catch (err: any) {
      setError(err.detail || 'Failed to create module');
    } finally {
      setLoading(false);
    }
  };

  const getCleanPath = (path: string): string => {
    return path.replace(/^.*\/\.cache\/[^/]+\//, '');
  };

  const filteredDocuments = availableDocuments.filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    doc.path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-2xl lg:max-w-4xl max-h-[95vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-500 to-emerald-600 text-white p-4 sm:p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg sm:text-xl font-bold">Add New Module</h2>
              <p className="text-green-100 text-sm mt-1">Add a new module to "{pathwayTitle}"</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors flex-shrink-0"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit(handleSave)} className="flex flex-col max-h-[calc(95vh-100px)]">
          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            )}

            <div className="space-y-8">
              {/* Basic Information */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2">
                  Module Information
                </h3>
                
                <div className="grid grid-cols-1 gap-4">
                  {/* Title */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Module Title
                    </label>
                    <input
                      {...register('title')}
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors"
                      placeholder="Enter module title"
                    />
                    {errors.title && (
                      <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
                    )}
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description
                    </label>
                    <textarea
                      {...register('description')}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 resize-none transition-colors"
                      placeholder="Enter module description"
                    />
                    {errors.description && (
                      <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
                    )}
                  </div>

                  {/* Theme */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Theme
                    </label>
                    <input
                      {...register('theme')}
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors"
                      placeholder="Enter module theme (e.g., Introduction, Advanced Topics)"
                    />
                  </div>
                </div>
              </div>

              {/* Learning Objectives */}
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-gray-200 pb-2">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <Target className="w-5 h-5 text-green-600 mr-2" />
                    Learning Objectives
                  </h3>
                  <button
                    type="button"
                    onClick={addLearningObjective}
                    className="flex items-center space-x-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add</span>
                  </button>
                </div>

                <div className="space-y-3">
                  {learningObjectives.length === 0 ? (
                    <p className="text-gray-500 text-sm italic text-center py-4 bg-gray-50 rounded-lg">
                      No learning objectives yet. Click "Add" to create one.
                    </p>
                  ) : (
                    learningObjectives.map((objective, index) => (
                      <div key={index} className="flex items-start space-x-3 bg-gray-50 p-3 rounded-lg">
                        <div className="flex-shrink-0 w-6 h-6 bg-green-100 rounded-full flex items-center justify-center mt-1">
                          <span className="text-xs font-medium text-green-700">{index + 1}</span>
                        </div>
                        <input
                          type="text"
                          value={objective}
                          onChange={(e) => updateLearningObjective(index, e.target.value)}
                          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors"
                          placeholder="Enter learning objective"
                        />
                        <button
                          type="button"
                          onClick={() => removeLearningObjective(index)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
                          title="Remove objective"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Document Selection */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center border-b border-gray-200 pb-2">
                  <FileText className="w-5 h-5 text-blue-600 mr-2" />
                  Source Documents
                </h3>

                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search documents by name or path..."
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors"
                  />
                </div>

                {/* Documents List */}
                {loadingDocuments ? (
                  <div className="flex justify-center items-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                    <span className="ml-3 text-gray-600">Loading documents...</span>
                  </div>
                ) : (
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
                      <p className="text-sm font-medium text-gray-700">
                        {filteredDocuments.length} document{filteredDocuments.length !== 1 ? 's' : ''} available
                        {selectedDocuments.length > 0 && (
                          <span className="ml-2 text-green-600">
                            ({selectedDocuments.length} selected)
                          </span>
                        )}
                      </p>
                    </div>
                    
                    {filteredDocuments.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                        <p>No documents found</p>
                        {searchQuery && (
                          <p className="text-sm mt-1">Try adjusting your search terms</p>
                        )}
                      </div>
                    ) : (
                      <div className="max-h-64 overflow-y-auto">
                        <div className="divide-y divide-gray-100">
                          {filteredDocuments.map((doc) => (
                            <div
                              key={doc.id}
                              className={`flex items-center space-x-3 p-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                                selectedDocuments.includes(doc.path) ? 'bg-green-50 border-l-4 border-green-500' : ''
                              }`}
                              onClick={() => handleDocumentToggle(doc.path)}
                            >
                              <div className="flex-shrink-0">
                                {selectedDocuments.includes(doc.path) ? (
                                  <CheckCircle className="w-5 h-5 text-green-600" />
                                ) : (
                                  <Circle className="w-5 h-5 text-gray-400" />
                                )}
                              </div>
                              <FileText className="w-4 h-4 text-blue-600 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                                <p className="text-xs text-gray-500 truncate">{getCleanPath(doc.path)}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-4 sm:px-6 py-4 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row justify-end space-y-2 sm:space-y-0 sm:space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="w-full sm:w-auto px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Creating...</span>
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    <span>Create Module</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
} 