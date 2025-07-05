import React, { useState, useEffect } from 'react';

const Stage1Component = ({ course, taskStatus, stageData, onNext }) => {
  const [selectedFolders, setSelectedFolders] = useState([]);
  const [selectedOverviewDoc, setSelectedOverviewDoc] = useState('');
  const [error, setError] = useState('');

  const isCompleted = taskStatus?.status === 'completed';
  const isLoading = taskStatus?.status === 'running';

  const handleFolderToggle = (folder) => {
    setSelectedFolders(prev => 
      prev.includes(folder) 
        ? prev.filter(f => f !== folder)
        : [...prev, folder]
    );
  };

  const handleNext = () => {
    if (!isCompleted) {
      setError('Please wait for repository analysis to complete');
      return;
    }

    if (selectedFolders.length === 0) {
      setError('Please select at least one folder to include');
      return;
    }

    onNext({
      include_folders: selectedFolders,
      overview_doc: selectedOverviewDoc || null
    });
  };

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Analyzing Repository</h3>
        <p className="text-gray-600">Cloning repository and discovering documentation files...</p>
        <div className="mt-4 text-sm text-gray-500">
          Progress: {taskStatus?.progress_percentage || 0}%
        </div>
      </div>
    );
  }

  if (!isCompleted || !stageData) {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Repository Analysis Failed</h3>
        <p className="text-gray-600">Unable to analyze the repository. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">Repository Analysis Complete</h3>
        <p className="text-gray-600">
          Found {stageData.available_files?.length || 0} documentation files in {stageData.repo_name}
        </p>
      </div>

      {/* Folder Selection */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">Select Folders to Include</h4>
        <p className="text-sm text-gray-600 mb-4">
          Choose which folders contain the documentation you want to include in your course.
        </p>
        
        {stageData.available_folders && stageData.available_folders.length > 0 ? (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {stageData.available_folders.map((folder) => (
              <label key={folder} className="flex items-center space-x-3 p-2 hover:bg-gray-100 rounded cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedFolders.includes(folder)}
                  onChange={() => handleFolderToggle(folder)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm font-mono text-gray-700">{folder}</span>
              </label>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No folders found in repository</p>
        )}
        
        {selectedFolders.length > 0 && (
          <div className="mt-3 p-2 bg-blue-50 rounded">
            <p className="text-sm text-blue-800">
              Selected: {selectedFolders.join(', ')}
            </p>
          </div>
        )}
      </div>

      {/* Overview Document Selection */}
      {stageData.suggested_overview_docs && stageData.suggested_overview_docs.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">Overview Document (Optional)</h4>
          <p className="text-sm text-gray-600 mb-4">
            Select an overview document to provide context for better course generation.
          </p>
          
          <div className="space-y-2">
            <label className="flex items-center space-x-3 p-2 hover:bg-gray-100 rounded cursor-pointer">
              <input
                type="radio"
                name="overview_doc"
                value=""
                checked={selectedOverviewDoc === ''}
                onChange={(e) => setSelectedOverviewDoc(e.target.value)}
                className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">None</span>
            </label>
            
            {stageData.suggested_overview_docs.map((doc) => (
              <label key={doc} className="flex items-center space-x-3 p-2 hover:bg-gray-100 rounded cursor-pointer">
                <input
                  type="radio"
                  name="overview_doc"
                  value={doc}
                  checked={selectedOverviewDoc === doc}
                  onChange={(e) => setSelectedOverviewDoc(e.target.value)}
                  className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                />
                <span className="text-sm font-mono text-gray-700">{doc}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Repository Statistics */}
      <div className="bg-blue-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-2">Repository Statistics</h4>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Repository:</span>
            <span className="ml-2 font-mono text-gray-900">{stageData.repo_name}</span>
          </div>
          <div>
            <span className="text-gray-600">Total Files:</span>
            <span className="ml-2 font-medium text-gray-900">{stageData.available_files?.length || 0}</span>
          </div>
          <div>
            <span className="text-gray-600">Folders:</span>
            <span className="ml-2 font-medium text-gray-900">{stageData.available_folders?.length || 0}</span>
          </div>
          <div>
            <span className="text-gray-600">Overview Docs:</span>
            <span className="ml-2 font-medium text-gray-900">{stageData.suggested_overview_docs?.length || 0}</span>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end space-x-3">
        <button
          onClick={handleNext}
          disabled={!isCompleted || selectedFolders.length === 0}
          className="bg-blue-500 text-white px-6 py-2 rounded-md hover:bg-blue-600 transition-colors duration-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Next: Analyze Documents
        </button>
      </div>
    </div>
  );
};

export default Stage1Component; 