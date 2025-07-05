import React, { useState } from 'react';

const Stage3Component = ({ course, taskStatus, stageData, onNext }) => {
  const [selectedPathwayIndex, setSelectedPathwayIndex] = useState(0);
  const [editingPathway, setEditingPathway] = useState(null);
  const [error, setError] = useState('');

  const isCompleted = taskStatus?.status === 'completed';
  const isLoading = taskStatus?.status === 'running';
  const isFailed = taskStatus?.status === 'failed';

  const pathways = stageData?.pathways || [];

  const handleNext = () => {
    if (!isCompleted) {
      setError('Please wait for pathway generation to complete');
      return;
    }

    if (selectedPathwayIndex < 0 || selectedPathwayIndex >= pathways.length) {
      setError('Please select a valid pathway');
      return;
    }

    onNext({
      selected_pathway_index: selectedPathwayIndex,
      complexity_level: pathways[selectedPathwayIndex].complexity
    });
  };

  const handleEditPathway = (pathway) => {
    setEditingPathway({ ...pathway });
  };

  const handleSavePathway = () => {
    // In a real implementation, you would save the modified pathway
    // For now, we'll just close the edit modal
    setEditingPathway(null);
  };

  if (isFailed) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Pathway Generation Failed</h3>
        <p className="text-gray-600">
          {taskStatus?.error_message || 'An error occurred during pathway generation'}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Generating Learning Pathways</h3>
        <p className="text-gray-600 mb-4">
          Creating structured learning paths based on your documents...
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
              <span>Analyzing document relationships</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Grouping related content into modules</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Creating learning objectives</span>
            </li>
            <li className="flex items-start">
              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
              <span>Generating pathway variations</span>
            </li>
          </ul>
        </div>
      </div>
    );
  }

  if (isCompleted && pathways.length > 0) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Learning Pathways Generated</h3>
          <p className="text-gray-600">
            {pathways.length} learning pathway{pathways.length > 1 ? 's' : ''} created based on your documentation
          </p>
        </div>

        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">Select a Learning Pathway</h4>
          <p className="text-sm text-gray-600">
            Choose the pathway that best fits your learning goals. You can modify the selected pathway before generating the final course.
          </p>
        </div>

        <div className="space-y-4">
          {pathways.map((pathway, index) => (
            <div
              key={index}
              className={`border-2 rounded-lg p-4 cursor-pointer transition-all duration-200 ${
                selectedPathwayIndex === index 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => setSelectedPathwayIndex(index)}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center space-x-3">
                  <input
                    type="radio"
                    name="pathway"
                    checked={selectedPathwayIndex === index}
                    onChange={() => setSelectedPathwayIndex(index)}
                    className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                  />
                  <div>
                    <h4 className="font-medium text-gray-900">{pathway.title}</h4>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        pathway.complexity === 'beginner' ? 'bg-green-100 text-green-800' :
                        pathway.complexity === 'intermediate' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {pathway.complexity}
                      </span>
                      <span>{pathway.module_count} modules</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEditPathway(pathway);
                  }}
                  className="text-blue-600 hover:text-blue-800 transition-colors duration-200"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
              </div>

              <p className="text-sm text-gray-600 mb-3">{pathway.description}</p>

              <div className="space-y-2">
                <h5 className="font-medium text-gray-900 text-sm">Modules:</h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {pathway.modules.map((module, moduleIndex) => (
                    <div key={moduleIndex} className="bg-white rounded p-2 text-sm">
                      <div className="font-medium text-gray-900">{module.title}</div>
                      <div className="text-gray-600">{module.theme}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        <div className="flex justify-end space-x-3">
          <button
            onClick={handleNext}
            disabled={!isCompleted || selectedPathwayIndex < 0}
            className="bg-blue-500 text-white px-6 py-2 rounded-md hover:bg-blue-600 transition-colors duration-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Next: Generate Course
          </button>
        </div>

        {/* Edit Pathway Modal */}
        {editingPathway && (
          <PathwayEditModal
            pathway={editingPathway}
            onSave={handleSavePathway}
            onCancel={() => setEditingPathway(null)}
          />
        )}
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
      <h3 className="text-lg font-medium text-gray-900 mb-2">No Learning Pathways Found</h3>
      <p className="text-gray-600">Unable to generate learning pathways. Please try again.</p>
    </div>
  );
};

const PathwayEditModal = ({ pathway, onSave, onCancel }) => {
  const [editedPathway, setEditedPathway] = useState(pathway);

  const handleSave = () => {
    onSave(editedPathway);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Edit Learning Pathway</h3>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600 transition-colors duration-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Title
              </label>
              <input
                type="text"
                value={editedPathway.title}
                onChange={(e) => setEditedPathway({...editedPathway, title: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={editedPathway.description}
                onChange={(e) => setEditedPathway({...editedPathway, description: e.target.value})}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Complexity Level
              </label>
              <select
                value={editedPathway.complexity}
                onChange={(e) => setEditedPathway({...editedPathway, complexity: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Modules
              </label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {editedPathway.modules.map((module, index) => (
                  <div key={index} className="bg-gray-50 rounded p-3">
                    <div className="font-medium text-gray-900">{module.title}</div>
                    <div className="text-sm text-gray-600">{module.theme}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors duration-200"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors duration-200"
            >
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Stage3Component; 