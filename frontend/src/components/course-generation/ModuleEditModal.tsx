"use client";

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { DocumentSummary, ModuleSummary, UpdateModuleRequest } from '@/lib/types';
import { getStage2Result, updateModule } from '@/lib/api';
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

const moduleEditSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().min(1, 'Description is required'),
  learning_objectives: z.array(z.string()).optional(),
  theme: z.string().optional(),
  target_complexity: z.string().optional()
});

type ModuleEditFormData = z.infer<typeof moduleEditSchema>;

interface ModuleEditModalProps {
  courseId: string;
  pathwayIndex: number;
  moduleIndex: number;
  module: ModuleSummary;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

export default function ModuleEditModal({
  courseId,
  pathwayIndex,
  moduleIndex,
  module,
  isOpen,
  onClose,
  onSave
}: ModuleEditModalProps) {
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
  } = useForm<ModuleEditFormData>({
    resolver: zodResolver(moduleEditSchema),
    defaultValues: {
      title: module.title,
      description: module.description,
      learning_objectives: module.learning_objectives || [],
      theme: module.theme,
      target_complexity: 'intermediate'
    }
  });

  const learningObjectives = watch('learning_objectives') || [];

  // Load available documents and set initial selections
  useEffect(() => {
    if (isOpen) {
      loadAvailableDocuments();
      setSelectedDocuments(module.documents || []);
      reset({
        title: module.title,
        description: module.description,
        learning_objectives: module.learning_objectives || [],
        theme: module.theme,
        target_complexity: 'intermediate'
      });
    }
  }, [isOpen, module, reset]);

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

  const handleSave = async (data: ModuleEditFormData) => {
    setLoading(true);
    setError(null);

    try {
      const updateRequest: UpdateModuleRequest = {
        pathway_index: pathwayIndex,
        module_index: moduleIndex,
        module_updates: {
          title: data.title,
          description: data.description,
          learning_objectives: data.learning_objectives?.filter(obj => obj.trim() !== '') || [],
          linked_documents: selectedDocuments,
          theme: data.theme,
          target_complexity: data.target_complexity
        }
      };

      await updateModule(courseId, updateRequest);
      onSave();
      onClose();
    } catch (err: any) {
      setError(err.detail || 'Failed to update module');
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
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-500 to-indigo-600 text-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Edit Module</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(handleSave)} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Module Information</h3>
              
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Module Title
                </label>
                <input
                  {...register('title')}
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
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
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  placeholder="Enter module theme"
                />
              </div>
            </div>

            {/* Learning Objectives */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Target className="w-5 h-5 text-green-600 mr-2" />
                  Learning Objectives
                </h3>
                <button
                  type="button"
                  onClick={addLearningObjective}
                  className="flex items-center space-x-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Objective</span>
                </button>
              </div>

              <div className="space-y-2">
                {learningObjectives.map((objective, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="text"
                      value={objective}
                      onChange={(e) => updateLearningObjective(index, e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                      placeholder="Enter learning objective"
                    />
                    <button
                      type="button"
                      onClick={() => removeLearningObjective(index)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Document Selection */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                <FileText className="w-5 h-5 text-blue-600 mr-2" />
                Source Documents
              </h3>

              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search documents..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
              </div>

              {/* Documents List */}
              {loadingDocuments ? (
                <div className="flex justify-center py-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                </div>
              ) : (
                <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
                  {filteredDocuments.length === 0 ? (
                    <p className="text-center text-gray-500 py-4">No documents found</p>
                  ) : (
                    <div className="space-y-1 p-2">
                      {filteredDocuments.map((doc) => (
                        <div
                          key={doc.id}
                          className={`flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors ${
                            selectedDocuments.includes(doc.path) ? 'bg-purple-50 border border-purple-200' : ''
                          }`}
                          onClick={() => handleDocumentToggle(doc.path)}
                        >
                          <div className="flex-shrink-0">
                            {selectedDocuments.includes(doc.path) ? (
                              <CheckCircle className="w-5 h-5 text-purple-600" />
                            ) : (
                              <Circle className="w-5 h-5 text-gray-400" />
                            )}
                          </div>
                          <FileText className="w-4 h-4 text-blue-600 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                            <p className="text-xs text-gray-500 truncate">{getCleanPath(doc.path)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Selected Documents Count */}
              <p className="text-sm text-gray-600">
                {selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''} selected
              </p>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit(handleSave)}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
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
    </div>
  );
} 