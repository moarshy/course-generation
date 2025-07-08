import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const Stage1Component = ({ course, status, taskStatus, stageData, onNext, currentStage, completedStages }) => {
  const { getAccessTokenSilently } = useAuth0();
  const [selectedFolders, setSelectedFolders] = useState([]);
  const [selectedOverviewDoc, setSelectedOverviewDoc] = useState('');
  const [error, setError] = useState('');
  const [loadingSelections, setLoadingSelections] = useState(false);

  // Extract courseId from course object
  const courseId = course?.id || course?.course_id || course?.project_id;

  // Determine completion based on stage data availability AND backend status
  const isCompleted = (status === 'completed') || (stageData && stageData.available_files);
  const isLoading = status === 'active' && taskStatus?.status === 'running';

  // Load previously saved selections only when Stage 1 is completed
  useEffect(() => {
    const loadSavedSelections = async () => {
      if (!courseId || !isCompleted) {
        return;
      }
      
      try {
        setLoadingSelections(true);
        const token = await getAccessTokenSilently();
        const response = await axios.get(
          `${API_BASE_URL}/course-generation/${courseId}/stage1/selections`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        if (response.data) {
          setSelectedFolders(response.data.include_folders || []);
          setSelectedOverviewDoc(response.data.overview_doc || '');
        }
      } catch (error) {
        // Handle different error responses appropriately
        if (error.response?.status === 202) {
          // Stage 1 is still in progress - this is expected
          console.log('Stage 1 still in progress, selections not available yet');
        } else if (error.response?.status === 404) {
          // No saved selections found - this is OK, user hasn't made selections yet
          console.log('No saved selections found yet');
        } else {
          console.error('Error loading saved selections:', error);
        }
      } finally {
        setLoadingSelections(false);
      }
    };

    loadSavedSelections();
  }, [courseId, getAccessTokenSilently, isCompleted]);

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
        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            ⏳ This process may take a few minutes. Please wait while we analyze your repository structure and identify documentation files.
          </p>
        </div>
      </div>
    );
  }

  // Show loading state if stage is completed but data hasn't loaded yet
  if (isCompleted && !stageData) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Loading Repository Data</h3>
        <p className="text-gray-600">Loading folder structure and document information...</p>
        <div className="mt-6 p-4 bg-yellow-50 rounded-lg">
          <p className="text-sm text-yellow-800 mb-3">
            ⚠️ If this takes more than a minute, try refreshing the data or check the browser console for errors.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="bg-yellow-600 text-white px-4 py-2 rounded-md hover:bg-yellow-700 transition-colors duration-200 text-sm"
          >
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  // Show loading state when loading saved selections
  if (loadingSelections) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Loading Saved Selections</h3>
        <p className="text-gray-600">Loading your previously selected folders and documents...</p>
      </div>
    );
  }

  // Show failure state only if stage actually failed (not just pending/running)
  if (!isCompleted) {
    // Check if the task actually failed vs still running/pending
    const taskFailed = taskStatus?.status === 'failed' || status === 'failed';
    
    if (taskFailed) {
      return (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Repository Analysis Failed</h3>
          <p className="text-gray-600">
            {taskStatus?.error_message || 'Unable to analyze the repository. Please try again.'}
          </p>
        </div>
      );
    } else {
      // Stage is pending - show waiting state instead of failure
      return (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Waiting for Repository Analysis</h3>
          <p className="text-gray-600">Repository analysis will begin shortly. Please wait...</p>
        </div>
      );
    }
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

      {/* Compact Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Folder Selection */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">Select Folders to Include</h4>
          <p className="text-sm text-gray-600 mb-4">
            Choose which folders contain the documentation you want to include in your course.
          </p>
          
          {stageData.available_folders && stageData.available_folders.length > 0 ? (
            <div className="space-y-2 max-h-48 overflow-y-auto">
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

        {/* Right Column - Overview Document Selection */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">Overview Document (Optional)</h4>
          <p className="text-sm text-gray-600 mb-4">
            Select an overview document to provide context for better course generation.
          </p>
          
          {stageData.all_overview_candidates && stageData.all_overview_candidates.length > 0 ? (
            <div className="space-y-2 max-h-48 overflow-y-auto">
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
              
              {stageData.all_overview_candidates.map((doc) => {
                const isSuggested = stageData.suggested_overview_docs?.includes(doc);
                return (
                  <label key={doc} className="flex items-center space-x-3 p-2 hover:bg-gray-100 rounded cursor-pointer">
                    <input
                      type="radio"
                      name="overview_doc"
                      value={doc}
                      checked={selectedOverviewDoc === doc}
                      onChange={(e) => setSelectedOverviewDoc(e.target.value)}
                      className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                    />
                    <span className="text-sm font-mono text-gray-700 flex-1">{doc}</span>
                    {isSuggested && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                        Recommended
                      </span>
                    )}
                  </label>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No overview documents available</p>
          )}
        </div>
      </div>

      {/* Repository Statistics */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-medium text-gray-900">Repository Overview</h4>
          <div className="flex items-center space-x-2">
            <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span className="text-sm font-mono text-gray-600 bg-gray-100 px-2 py-1 rounded">
              {stageData.repo_name}
            </span>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <div className="text-2xl font-semibold text-blue-600 mb-1">
              {stageData.available_files?.length || 0}
            </div>
            <div className="text-sm text-gray-600">Documentation Files</div>
          </div>
          
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="text-2xl font-semibold text-green-600 mb-1">
              {stageData.available_folders?.length || 0}
            </div>
            <div className="text-sm text-gray-600">Folders</div>
          </div>
          
          <div className="text-center p-3 bg-purple-50 rounded-lg">
            <div className="text-2xl font-semibold text-purple-600 mb-1">
              {stageData.all_overview_candidates?.length || 0}
            </div>
            <div className="text-sm text-gray-600">Overview Docs</div>
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
          disabled={!isCompleted || selectedFolders.length === 0 || (completedStages?.has('analysis') || completedStages?.has('pathways') || completedStages?.has('generation'))}
          className="bg-blue-500 text-white px-6 py-2 rounded-md hover:bg-blue-600 transition-colors duration-200 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {(completedStages?.has('analysis') || completedStages?.has('pathways') || completedStages?.has('generation'))
            ? 'Stage Complete' 
            : 'Next: Analyze Documents'
          }
        </button>
      </div>
    </div>
  );
};

export default Stage1Component; 