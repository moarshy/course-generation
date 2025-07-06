import React, { useState, useEffect } from 'react';
import Stage2Component from './Stage2Component';
import Stage3Component from './Stage3Component';

// Stage 1: Repository Analysis Content
export const Stage1Content = ({ status, taskStatus, stageData, onNext, isLoading }) => {
  const [selectedFolders, setSelectedFolders] = useState([]);
  const [selectedOverviewDoc, setSelectedOverviewDoc] = useState('');
  
  const isCompleted = status === 'completed';
  const isActive = status === 'active';

  const handleFolderToggle = (folder) => {
    setSelectedFolders(prev => 
      prev.includes(folder) 
        ? prev.filter(f => f !== folder)
        : [...prev, folder]
    );
  };

  const handleNext = () => {
    if (selectedFolders.length === 0) return;
    
    onNext({
      include_folders: selectedFolders,
      overview_doc: selectedOverviewDoc || null
    });
  };

  if (isActive && taskStatus?.status === 'running') {
    return (
      <div className="py-6">
        <div className="flex items-center space-x-3 mb-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
          <span className="text-gray-700 font-medium">Analyzing repository...</span>
        </div>
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-sm text-blue-800 mb-2">Progress: {taskStatus?.progress_percentage || 0}%</div>
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${taskStatus?.progress_percentage || 0}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  if (!isCompleted || !stageData) {
    return (
      <div className="py-6 text-center text-gray-500">
        <div className="w-12 h-12 bg-gray-100 rounded-full mx-auto mb-3 flex items-center justify-center">
          <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p>Waiting for repository analysis...</p>
      </div>
    );
  }

  return (
    <div className="py-6 space-y-6">
      {/* Success Message */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center">
          <svg className="w-5 h-5 text-green-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <div>
            <h4 className="text-green-800 font-medium">Repository analyzed successfully!</h4>
            <p className="text-green-700 text-sm">Found {stageData.available_files?.length || 0} documentation files</p>
          </div>
        </div>
      </div>

      {/* Folder Selection */}
      <div>
        <h4 className="font-medium text-gray-900 mb-3">📁 Select folders to include</h4>
        <p className="text-sm text-gray-600 mb-4">Choose which folders contain documentation for your course.</p>
        
        <div className="bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
          {stageData.available_folders && stageData.available_folders.length > 0 ? (
            <div className="space-y-2">
              {stageData.available_folders.map((folder) => (
                <label key={folder} className="flex items-center space-x-3 p-2 hover:bg-white rounded cursor-pointer transition-colors">
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
            <p className="text-sm text-gray-500">No folders found</p>
          )}
        </div>

        {selectedFolders.length > 0 && (
          <div className="mt-3 p-3 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Selected:</strong> {selectedFolders.join(', ')}
            </p>
          </div>
        )}
      </div>

      {/* Overview Document Selection */}
      {stageData.all_overview_candidates && stageData.all_overview_candidates.length > 0 && (
        <div>
          <h4 className="font-medium text-gray-900 mb-3">📄 Overview document (optional)</h4>
          <p className="text-sm text-gray-600 mb-4">Select a document to provide better context for course generation.</p>
          
          <div className="space-y-2 max-h-48 overflow-y-auto">
            <label className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded cursor-pointer">
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
                <label key={doc} className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded cursor-pointer">
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
        </div>
      )}

      {/* Action Button */}
      <div className="pt-4">
        <button
          onClick={handleNext}
          disabled={selectedFolders.length === 0 || isLoading}
          className="w-full bg-blue-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-600 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Processing...' : 'Analyze Documents →'}
        </button>
      </div>
    </div>
  );
};

// Stage 2: Document Analysis Content
export const Stage2Content = ({ status, taskStatus, stageData, course, onNext, isLoading }) => {
  return (
    <Stage2Component 
      course={course}
      taskStatus={taskStatus}
      stageData={stageData}
      onNext={onNext}
    />
  );
};

// Stage 3: Learning Pathways Content
export const Stage3Content = ({ status, taskStatus, stageData, course, onNext, isLoading }) => {
  return (
    <Stage3Component 
      course={course}
      taskStatus={taskStatus}
      stageData={stageData}
      onNext={onNext}
    />
  );
};

// Stage 4: Course Generation Content
export const Stage4Content = ({ status, taskStatus, course }) => {
  const isCompleted = status === 'completed';
  const isActive = status === 'active';

  if (isActive && taskStatus?.status === 'running') {
    return (
      <div className="py-6">
        <div className="text-center mb-6">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <h4 className="font-medium text-gray-900 mb-2">Generating your course</h4>
          <p className="text-gray-600">Creating comprehensive course content with AI...</p>
        </div>
        
        <div className="bg-blue-50 rounded-lg p-4 mb-6">
          <div className="flex justify-between text-sm text-blue-800 mb-2">
            <span>Progress</span>
            <span>{taskStatus?.progress_percentage || 0}%</span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${taskStatus?.progress_percentage || 0}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="flex items-center space-x-3 text-gray-600">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span>Writing module content</span>
          </div>
          <div className="flex items-center space-x-3 text-gray-600">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span>Creating assessments</span>
          </div>
          <div className="flex items-center space-x-3 text-gray-600">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span>Generating summaries</span>
          </div>
          <div className="flex items-center space-x-3 text-gray-600">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
            <span>Exporting materials</span>
          </div>
        </div>

        <div className="mt-6 text-xs text-gray-500 text-center">
          This may take a few minutes depending on course complexity...
        </div>
      </div>
    );
  }

  if (isCompleted) {
    // Check if course generation actually succeeded with modules
    const moduleCount = taskStatus?.course_summary?.module_count || 0;
    const hasGeneratedContent = moduleCount > 0;
    
    if (hasGeneratedContent) {
      // Show success message only if modules were actually generated
      return (
        <div className="py-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-green-100 rounded-full mx-auto mb-4 flex items-center justify-center animate-bounce">
              <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <h4 className="text-2xl font-bold text-gray-900 mb-2">🎉 Course Generated Successfully!</h4>
            <p className="text-gray-600">Your AI-powered course is ready for use</p>
          </div>

          <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6 mb-6">
            <h5 className="font-bold text-gray-900 mb-4">Course Statistics</h5>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {moduleCount}
                </div>
                <div className="text-sm text-gray-600">Modules</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">100%</div>
                <div className="text-sm text-gray-600">Complete</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-600">AI</div>
                <div className="text-sm text-gray-600">Generated</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <button className="bg-blue-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-600 transition-colors duration-200">
              👁️ View Course
            </button>
            <button className="bg-green-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-green-600 transition-colors duration-200">
              📥 Download Materials
            </button>
          </div>

          <div className="mt-6 bg-yellow-50 rounded-lg p-4">
            <h5 className="font-medium text-gray-900 mb-2">🚀 Next Steps</h5>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Review and customize the generated content</li>
              <li>• Add your own examples and exercises</li>
              <li>• Deploy to your learning platform</li>
            </ul>
          </div>
        </div>
      );
    } else {
      // Show failure message when task is "completed" but no modules were generated
      return (
        <div className="py-6">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-red-100 rounded-full mx-auto mb-4 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <h4 className="text-2xl font-bold text-gray-900 mb-2">❌ Course Generation Failed</h4>
            <p className="text-gray-600">The course generation completed but no modules were created</p>
          </div>

          <div className="bg-red-50 rounded-lg p-6 mb-6">
            <h5 className="font-bold text-gray-900 mb-4">Issue Details</h5>
            <div className="text-sm text-gray-700 space-y-2">
              <p>• No course modules were generated</p>
              <p>• This may be due to insufficient source material or processing errors</p>
              <p>• Error details: {taskStatus?.error_message || 'Unknown error occurred'}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <button 
              onClick={() => window.location.reload()}
              className="bg-blue-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-600 transition-colors duration-200"
            >
              🔄 Try Again
            </button>
            <button 
              onClick={() => window.history.back()}
              className="bg-gray-500 text-white py-3 px-6 rounded-lg font-medium hover:bg-gray-600 transition-colors duration-200"
            >
              ← Go Back
            </button>
          </div>

          <div className="mt-6 bg-yellow-50 rounded-lg p-4">
            <h5 className="font-medium text-gray-900 mb-2">💡 Suggestions</h5>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Ensure your repository contains sufficient documentation</li>
              <li>• Check that the selected folders contain relevant content</li>
              <li>• Try selecting different pathways or complexity levels</li>
            </ul>
          </div>
        </div>
      );
    }
  }

  return (
    <div className="py-6 text-center text-gray-500">
      <div className="w-12 h-12 bg-gray-100 rounded-full mx-auto mb-3 flex items-center justify-center">
        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      </div>
      <p>Waiting for course generation...</p>
    </div>
  );
}; 