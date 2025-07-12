"use client";

import { GenerationStatus } from '@/lib/types';
import { CheckCircle, Circle, Clock, AlertCircle, GitBranch, FileText, Route, BookOpen } from 'lucide-react';

type Stage = 'stage1' | 'stage2' | 'stage3' | 'stage4';

interface StagesSidebarProps {
  currentStage: Stage;
  generationStatus: GenerationStatus | null;
  onStageChange: (stage: Stage) => void;
}

interface StageInfo {
  id: Stage;
  title: string;
  description: string;
  icon: React.ReactNode;
  statusKey: keyof GenerationStatus['stage_statuses'];
}

const stages: StageInfo[] = [
  {
    id: 'stage1',
    title: 'Repository Setup',
    description: 'Clone repository and select content',
    icon: <GitBranch className="w-5 h-5" />,
    statusKey: 'CLONE_REPO'
  },
  {
    id: 'stage2',
    title: 'Document Analysis',
    description: 'Analyze and process documents',
    icon: <FileText className="w-5 h-5" />,
    statusKey: 'DOCUMENT_ANALYSIS'
  },
  {
    id: 'stage3',
    title: 'Learning Pathway',
    description: 'Generate learning pathway',
    icon: <Route className="w-5 h-5" />,
    statusKey: 'PATHWAY_BUILDING'
  },
  {
    id: 'stage4',
    title: 'Course Generation',
    description: 'Generate final course content',
    icon: <BookOpen className="w-5 h-5" />,
    statusKey: 'COURSE_GENERATION'
  }
];

export default function StagesSidebar({ currentStage, generationStatus, onStageChange }: StagesSidebarProps) {
  const getStageStatus = (stage: StageInfo) => {
    if (!generationStatus) return 'not_started';
    
    const status = generationStatus.stage_statuses[stage.statusKey];
    return status || 'not_started';
  };

  const getStageIcon = (stage: StageInfo) => {
    const status = getStageStatus(stage);
    const isActive = currentStage === stage.id;
    
    switch (status) {
      case 'completed':
        return (
          <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-green-600" />
          </div>
        );
      case 'in_progress':
        return (
          <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <Clock className="w-5 h-5 text-blue-600 animate-pulse" />
          </div>
        );
      case 'failed':
        return (
          <div className="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-red-600" />
          </div>
        );
      default:
        return (
          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isActive ? 'bg-blue-100' : 'bg-gray-100'
          }`}>
            <Circle className={`w-5 h-5 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
          </div>
        );
    }
  };

  const canNavigateToStage = (stage: StageInfo) => {
    const status = getStageStatus(stage);
    const stageIndex = stages.findIndex(s => s.id === stage.id);
    
    // Can always navigate to Stage 1
    if (stageIndex === 0) return true;
    
    // Can navigate to completed stages
    if (status === 'completed') return true;
    
    // Can navigate to the next stage if previous stage is completed
    if (stageIndex > 0) {
      const previousStage = stages[stageIndex - 1];
      const previousStatus = getStageStatus(previousStage);
      return previousStatus === 'completed';
    }
    
    return false;
  };

  const getStageStatusText = (stage: StageInfo) => {
    const status = getStageStatus(stage);
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'in_progress':
        return 'In Progress';
      case 'failed':
        return 'Failed';
      default:
        return 'Not Started';
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border p-6">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-gray-900 mb-2">Course Generation</h2>
        <p className="text-sm text-gray-600">Follow the stages to generate your course</p>
      </div>

      <div className="space-y-4">
        {stages.map((stage, index) => {
          const isActive = currentStage === stage.id;
          const canNavigate = canNavigateToStage(stage);
          const status = getStageStatus(stage);
          
          return (
            <div key={stage.id} className="relative">
              {/* Connection Line */}
              {index < stages.length - 1 && (
                <div className="absolute left-4 top-12 w-0.5 h-8 bg-gray-200"></div>
              )}
              
              {/* Stage Item */}
              <button
                onClick={() => canNavigate && onStageChange(stage.id)}
                disabled={!canNavigate}
                className={`w-full text-left p-4 rounded-xl border transition-all duration-200 ${
                  isActive
                    ? 'bg-blue-50 border-blue-200 shadow-sm'
                    : canNavigate
                    ? 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                    : 'bg-gray-50 border-gray-200 opacity-60 cursor-not-allowed'
                }`}
              >
                <div className="flex items-start space-x-3">
                  {getStageIcon(stage)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className={`text-sm font-semibold ${
                        isActive ? 'text-blue-900' : 'text-gray-900'
                      }`}>
                        {stage.title}
                      </h3>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        status === 'completed' ? 'bg-green-100 text-green-700' :
                        status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                        status === 'failed' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {getStageStatusText(stage)}
                      </span>
                    </div>
                    <p className={`text-xs ${
                      isActive ? 'text-blue-700' : 'text-gray-600'
                    }`}>
                      {stage.description}
                    </p>
                  </div>
                </div>
              </button>
            </div>
          );
        })}
      </div>

      {/* Overall Status */}
      {generationStatus && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="text-sm text-gray-600 mb-2">Overall Progress</div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ 
                width: `${generationStatus.progress}%` 
              }}
            ></div>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {generationStatus.progress}% complete
          </div>
        </div>
      )}
    </div>
  );
} 