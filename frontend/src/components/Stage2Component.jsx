import React from 'react';

const Stage2Component = ({ course, taskStatus, onNext }) => {
  const isCompleted = taskStatus?.status === 'completed';
  const isLoading = taskStatus?.status === 'running';
  const isFailed = taskStatus?.status === 'failed';

  const handleNext = () => {
    if (!isCompleted) {
      return;
    }
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

  if (isCompleted) {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Document Analysis Complete</h3>
          <p className="text-gray-600">
            Successfully analyzed all selected documentation files
          </p>
        </div>

        <div className="bg-green-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-3">Analysis Results</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Documents processed:</span>
              <span className="font-medium text-gray-900">
                {taskStatus?.progress_percentage === 100 ? 'All documents' : 'Processing...'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Status:</span>
              <span className="font-medium text-green-600">Ready for next stage</span>
            </div>
          </div>
        </div>

        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">Next Steps</h4>
          <p className="text-sm text-gray-600">
            The documents have been successfully analyzed and are ready for learning pathway generation. 
            The AI will now group related content into structured learning modules.
          </p>
        </div>

        <div className="flex justify-end space-x-3">
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