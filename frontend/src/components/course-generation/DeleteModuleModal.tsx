"use client";

import { useState } from 'react';
import { ModuleSummary } from '@/lib/types';
import { deleteModule } from '@/lib/api';
import { 
  X, 
  AlertTriangle, 
  Trash2,
  FileText,
  Target
} from 'lucide-react';

interface DeleteModuleModalProps {
  courseId: string;
  pathwayId: string;
  pathwayTitle: string;
  module: ModuleSummary;
  isOpen: boolean;
  onClose: () => void;
  onDelete: () => void;
}

export default function DeleteModuleModal({
  courseId,
  pathwayId,
  pathwayTitle,
  module,
  isOpen,
  onClose,
  onDelete
}: DeleteModuleModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!module.id) {
      setError('Module ID not found');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await deleteModule(courseId, pathwayId, module.id);
      onDelete();
      onClose();
    } catch (err: any) {
      setError(err.detail || 'Failed to delete module');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-500 to-red-600 text-white p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white bg-opacity-20 rounded-lg">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Delete Module</h2>
                <p className="text-red-100 text-sm mt-1">This action cannot be undone</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors flex-shrink-0"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            {/* Warning Message */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-yellow-800">
                    Are you sure you want to delete this module?
                  </h3>
                  <p className="text-sm text-yellow-700 mt-1">
                    This will permanently remove the module and all its associated content from the pathway.
                  </p>
                </div>
              </div>
            </div>

            {/* Module Details */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700">Module:</p>
                  <p className="text-lg font-semibold text-gray-900">{module.title}</p>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700">Pathway:</p>
                  <p className="text-sm text-gray-900">{pathwayTitle}</p>
                </div>

                <div>
                  <p className="text-sm font-medium text-gray-700">Description:</p>
                  <p className="text-sm text-gray-600">{module.description}</p>
                </div>

                {module.learning_objectives && module.learning_objectives.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 flex items-center">
                      <Target className="w-4 h-4 mr-1" />
                      Learning Objectives ({module.learning_objectives.length}):
                    </p>
                    <ul className="text-sm text-gray-600 mt-1 space-y-1">
                      {module.learning_objectives.slice(0, 3).map((objective, index) => (
                        <li key={index} className="flex items-start">
                          <span className="text-gray-400 mr-2">•</span>
                          <span>{objective}</span>
                        </li>
                      ))}
                      {module.learning_objectives.length > 3 && (
                        <li className="text-gray-500 italic">
                          ... and {module.learning_objectives.length - 3} more
                        </li>
                      )}
                    </ul>
                  </div>
                )}

                {module.documents && module.documents.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 flex items-center">
                      <FileText className="w-4 h-4 mr-1" />
                      Linked Documents ({module.documents.length}):
                    </p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {module.documents.slice(0, 3).map((doc, index) => (
                        <span key={index} className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                          {doc.split('/').pop()}
                        </span>
                      ))}
                      {module.documents.length > 3 && (
                        <span className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                          +{module.documents.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 rounded-b-xl">
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Deleting...</span>
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  <span>Delete Module</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 