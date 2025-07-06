import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const Stage2Component = ({ course, taskStatus, stageData, onNext }) => {
  const { getAccessTokenSilently } = useAuth0();
  const [analyzedDocuments, setAnalyzedDocuments] = useState([]);
  const [editingDocument, setEditingDocument] = useState(null);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Extract courseId from course object or URL params
  const courseId = course?.id || course?.course_id || course?.project_id || window.location.pathname.split('/').pop();

  const isCompleted = taskStatus?.status === 'completed';
  const isLoading = taskStatus?.status === 'running';
  const isFailed = taskStatus?.status === 'failed';

  // Load analyzed documents when stage data is available
  useEffect(() => {
    if (stageData && stageData.analyzed_documents) {
      setAnalyzedDocuments(stageData.analyzed_documents);
    }
  }, [stageData]);

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
    try {
      setRefreshing(true);
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage2`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data && response.data.analyzed_documents) {
        setAnalyzedDocuments(response.data.analyzed_documents);
      }
    } catch (error) {
      console.error('Failed to refresh stage data:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handleEditDocument = (doc) => {
    setEditingDocument({
      ...doc,
      // Parse arrays if they're strings
      key_concepts: Array.isArray(doc.metadata.key_concepts) 
        ? doc.metadata.key_concepts.join(', ')
        : doc.metadata.key_concepts || '',
      learning_objectives: Array.isArray(doc.metadata.learning_objectives)
        ? doc.metadata.learning_objectives.join(', ')
        : doc.metadata.learning_objectives || ''
    });
  };

  const handleSaveDocument = async () => {
    if (!editingDocument) return;

    try {
      setSaving(true);
      const token = await getAccessTokenSilently();
      
      // Prepare update data
      const updateData = {
        document_id: editingDocument.id,
        metadata_updates: {
          doc_type: editingDocument.metadata.doc_type,
          semantic_summary: editingDocument.metadata.semantic_summary,
          key_concepts: editingDocument.key_concepts.split(',').map(s => s.trim()).filter(s => s),
          learning_objectives: editingDocument.learning_objectives.split(',').map(s => s.trim()).filter(s => s)
        }
      };

      await axios.put(
        `${API_BASE_URL}/course-generation/${courseId}/stage2/document`,
        updateData,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Refresh the data to get updated results
      await refreshStageData();
      setEditingDocument(null);
    } catch (error) {
      console.error('Failed to update document:', error);
      alert('Failed to update document. Please try again.');
    } finally {
      setSaving(false);
    }
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
          Processing selected documentation files and extracting key information...
        </p>
        
        <div className="max-w-md mx-auto">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Progress</span>
            <span>{taskStatus?.progress_percentage || 0}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${taskStatus?.progress_percentage || 0}%` }}
            />
          </div>
        </div>

        <div className="mt-6 text-left max-w-md mx-auto">
          <h4 className="font-medium text-gray-900 mb-3">What's happening:</h4>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Extracting content from markdown files</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Analyzing document structure and headings</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Identifying key concepts and topics</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
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
            {analyzedDocuments.map((doc) => (
              <div key={doc.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h5 className="font-medium text-gray-900">{doc.metadata.title}</h5>
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {doc.metadata.doc_type}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-2">{doc.path}</p>
                    
                    <div className="space-y-2">
                      <div>
                        <span className="text-sm font-medium text-gray-700">Summary: </span>
                        <span className="text-sm text-gray-600">{doc.metadata.semantic_summary}</span>
                      </div>
                      
                      {doc.metadata.key_concepts && doc.metadata.key_concepts.length > 0 && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Key Concepts: </span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {doc.metadata.key_concepts.map((concept, idx) => (
                              <span key={idx} className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-gray-100 text-gray-800">
                                {concept}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {doc.metadata.learning_objectives && doc.metadata.learning_objectives.length > 0 && (
                        <div>
                          <span className="text-sm font-medium text-gray-700">Learning Objectives: </span>
                          <ul className="text-sm text-gray-600 mt-1 space-y-1">
                            {doc.metadata.learning_objectives.map((objective, idx) => (
                              <li key={idx} className="flex items-start">
                                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
                                {objective}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleEditDocument(doc)}
                    className="ml-4 px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                  >
                    Edit
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Edit Modal */}
        {editingDocument && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Edit Document Metadata</h3>
                <button
                  onClick={() => setEditingDocument(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Document Type</label>
                  <select
                    value={editingDocument.metadata.doc_type}
                    onChange={(e) => setEditingDocument({
                      ...editingDocument,
                      metadata: { ...editingDocument.metadata, doc_type: e.target.value }
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {documentTypes.map((type) => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Summary</label>
                  <textarea
                    value={editingDocument.metadata.semantic_summary}
                    onChange={(e) => setEditingDocument({
                      ...editingDocument,
                      metadata: { ...editingDocument.metadata, semantic_summary: e.target.value }
                    })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Brief summary of the document's purpose and content"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Key Concepts</label>
                  <input
                    type="text"
                    value={editingDocument.key_concepts}
                    onChange={(e) => setEditingDocument({
                      ...editingDocument,
                      key_concepts: e.target.value
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter key concepts separated by commas"
                  />
                  <p className="text-xs text-gray-500 mt-1">Separate multiple concepts with commas</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Learning Objectives</label>
                  <input
                    type="text"
                    value={editingDocument.learning_objectives}
                    onChange={(e) => setEditingDocument({
                      ...editingDocument,
                      learning_objectives: e.target.value
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter learning objectives separated by commas"
                  />
                  <p className="text-xs text-gray-500 mt-1">Separate multiple objectives with commas</p>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setEditingDocument(null)}
                  className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveDocument}
                  disabled={saving}
                  className="px-4 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 flex items-center space-x-2"
                >
                  {saving && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                  <span>{saving ? 'Saving...' : 'Save Changes'}</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Next Button */}
        <div className="flex justify-end pt-6 border-t border-gray-200">
          <button
            onClick={handleNext}
            className="bg-blue-500 text-white px-6 py-2 rounded-md hover:bg-blue-600 transition-colors duration-200"
          >
            Next: Generate Learning Pathways
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