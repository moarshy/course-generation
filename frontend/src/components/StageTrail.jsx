import React from 'react';

const StageTrail = ({ 
  stages, 
  currentStage, 
  completedStages, 
  taskStatus, 
  stageData, 
  onStageChange, 
  isCollapsed 
}) => {
  const getStageStatus = (stageId) => {
    if (completedStages.has(stageId)) return 'completed';
    if (currentStage === stageId) return 'active';
    return 'pending';
  };

  const canAccessStage = (stageId) => {
    const stageIndex = stages.findIndex(s => s.id === stageId);
    if (stageIndex === 0) return true;
    
    const prevStage = stages[stageIndex - 1];
    return completedStages.has(prevStage.id);
  };

  const getStageIcon = (stage, status) => {
    if (status === 'completed') {
      return (
        <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </div>
      );
    }
    
    if (status === 'active') {
      return (
        <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center animate-pulse">
          <span className="text-white font-medium text-lg">{stage.icon}</span>
        </div>
      );
    }
    
    return (
      <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
        <span className="text-gray-600 font-medium text-lg">{stage.icon}</span>
      </div>
    );
  };

  const getProgressPercentage = (stageId) => {
    if (taskStatus && taskStatus.current_stage) {
      const stageMap = {
        'clone_repo': 'repo',
        'document_analysis': 'analysis',
        'pathway_building': 'pathways',
        'course_generation': 'generation'
      };
      
      const mappedStage = stageMap[taskStatus.current_stage];
      if (mappedStage === stageId && taskStatus.progress_percentage) {
        return taskStatus.progress_percentage;
      }
    }
    return null;
  };

  const getStageSummary = (stage) => {
    const status = getStageStatus(stage.id);
    const data = stageData[stage.id];
    
    if (status === 'completed' && data) {
      switch (stage.id) {
        case 'repo':
          return `${data.available_files?.length || 0} files found`;
        case 'analysis':
          return `${data.processed_files_count || 0} docs analyzed`;
        case 'pathways':
          return `${data.pathways?.length || 0} pathways generated`;
        case 'generation':
          return 'Course ready';
        default:
          return 'Completed';
      }
    }
    
    if (status === 'active') {
      const progress = getProgressPercentage(stage.id);
      if (progress) {
        return `${progress}% complete`;
      }
      
      // Handle new courses without task status
      if (!taskStatus) {
        switch (stage.id) {
          case 'repo':
            return 'Ready to start';
          case 'analysis':
            return 'Waiting for repository';
          case 'pathways':
            return 'Waiting for analysis';
          case 'generation':
            return 'Waiting for pathways';
          default:
            return 'Ready to start';
        }
      }
      
      return 'In progress...';
    }
    
    return status === 'pending' ? 'Pending' : '';
  };

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Progress Overview */}
      {!isCollapsed && (
        <div className="p-4 border-b border-gray-200">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-gray-900">Progress</h3>
            <span className="text-sm text-gray-500">
              {completedStages.size} of {stages.length}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(completedStages.size / stages.length) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Stage List */}
      <div className="p-4 space-y-3">
        {stages.map((stage, index) => {
          const status = getStageStatus(stage.id);
          const canAccess = canAccessStage(stage.id);
          const progress = getProgressPercentage(stage.id);
          
          return (
            <div key={stage.id} className="relative">
              {/* Connection Line */}
              {index < stages.length - 1 && (
                <div className="absolute left-5 top-10 w-0.5 h-8 bg-gray-200"></div>
              )}
              
              {/* Stage Item */}
              <div
                className={`relative flex items-start space-x-3 p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                  status === 'active' 
                    ? 'bg-blue-50 border-2 border-blue-200' 
                    : status === 'completed'
                    ? 'bg-green-50 border-2 border-green-200'
                    : canAccess
                    ? 'hover:bg-gray-50'
                    : 'opacity-50 cursor-not-allowed'
                }`}
                onClick={() => canAccess && onStageChange(stage.id)}
              >
                {/* Stage Icon */}
                {getStageIcon(stage, status)}
                
                {/* Stage Content */}
                {!isCollapsed && (
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-900 truncate">
                        {stage.title}
                      </h4>
                      {status === 'active' && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 truncate">
                      {stage.description}
                    </p>
                    
                    {/* Progress Bar for Active Stage */}
                    {status === 'active' && progress && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 rounded-full h-1">
                          <div 
                            className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{progress}%</p>
                      </div>
                    )}
                    
                    {/* Stage Summary */}
                    <p className="text-xs text-gray-500 mt-1">
                      {getStageSummary(stage)}
                    </p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      {!isCollapsed && (
        <div className="p-4 border-t border-gray-200 mt-auto">
          <div className="space-y-2">
            <button
              onClick={() => onStageChange('start')}
              className="w-full text-left p-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
            >
              🏠 Back to Start
            </button>
            {taskStatus && (
              <div className="p-2 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-600">
                  Status: <span className="font-medium">{taskStatus.status}</span>
                </p>
                {taskStatus.updated_at && (
                  <p className="text-xs text-gray-500">
                    Updated: {new Date(taskStatus.updated_at).toLocaleTimeString()}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StageTrail; 