import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Stage1Content, Stage2Content, Stage3Content, Stage4Content } from '../components/StageContent';

const CourseCreationPage = () => {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const { getAccessTokenSilently } = useAuth0();
  
  const [course, setCourse] = useState(null);
  const [currentStage, setCurrentStage] = useState('start');
  const [completedStages, setCompletedStages] = useState(new Set());
  const [taskStatus, setTaskStatus] = useState(null);
  const [stageData, setStageData] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

  const stages = [
    { id: 'repo', title: 'Repository Setup', description: 'Connect your GitHub repository' },
    { id: 'analysis', title: 'Document Analysis', description: 'AI analyzes your documentation' },
    { id: 'pathways', title: 'Learning Pathways', description: 'Review and customize learning paths' },
    { id: 'generation', title: 'Course Generation', description: 'Generate your final course' }
  ];

  useEffect(() => {
    if (courseId) {
      fetchCourse();
      checkExistingGeneration();
    }
  }, [courseId]);

  const fetchCourse = async () => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(`${API_BASE_URL}/projects/${courseId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCourse(response.data);
    } catch (error) {
      console.error('Error fetching course:', error);
      setError('Failed to load course details');
    }
  };

  const checkExistingGeneration = async () => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/status`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      if (response.data) {
        setTaskStatus(response.data);
        updateStageProgress(response.data.current_stage, response.data.status);
      }
    } catch (error) {
      console.log('No existing generation found');
    }
  };

  const updateStageProgress = (stage, status) => {
    const stageMap = {
      'clone_repo': 'repo',
      'document_analysis': 'analysis', 
      'pathway_building': 'pathways',
      'course_generation': 'generation'
    };
    
    const mappedStage = stageMap[stage];
    if (mappedStage) {
      setCurrentStage(mappedStage);
      if (status === 'completed') {
        setCompletedStages(prev => new Set([...prev, mappedStage]));
      }
    }
  };

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

  if (!course) {
    return (
      <div className="bg-gray-50 flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{course.title}</h1>
                <p className="text-gray-600">AI-Powered Course Generation</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                {course.status}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Overview */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-sm border p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Course Generation Progress</h2>
          <div className="flex items-center justify-between mb-4">
            {stages.map((stage, index) => (
              <div key={stage.id} className="flex items-center">
                <div className={`
                  w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium
                  ${getStageStatus(stage.id) === 'completed' 
                    ? 'bg-green-500 text-white' 
                    : getStageStatus(stage.id) === 'active'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-200 text-gray-600'}
                `}>
                  {getStageStatus(stage.id) === 'completed' ? (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </div>
                {index < stages.length - 1 && (
                  <div className={`
                    h-1 w-20 mx-2
                    ${completedStages.has(stage.id) ? 'bg-green-300' : 'bg-gray-200'}
                  `} />
                )}
              </div>
            ))}
          </div>
          <div className="text-sm text-gray-600">
            Step {stages.findIndex(s => s.id === currentStage) + 1} of {stages.length}: {stages.find(s => s.id === currentStage)?.title || 'Getting Started'}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex">
              <svg className="w-5 h-5 text-red-400 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <p className="text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Accordion Stages */}
        <div className="space-y-4">
          {currentStage === 'start' && (
            <StartSection 
              course={course}
              onStart={(repoUrl) => handleStartGeneration(repoUrl)}
              isLoading={isLoading}
            />
          )}
          
          {stages.map((stage) => (
            <StageAccordion
              key={stage.id}
              stage={stage}
              status={getStageStatus(stage.id)}
              canAccess={canAccessStage(stage.id)}
              taskStatus={taskStatus}
              stageData={stageData[stage.id]}
              onNext={(data) => handleStageNext(stage.id, data)}
              course={course}
              isLoading={isLoading}
            />
          ))}
        </div>
      </div>
    </div>
  );

  // Handler functions
  async function handleStartGeneration(repoUrl) {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getAccessTokenSilently();
      await axios.post(
        `${API_BASE_URL}/course-generation/${courseId}/start`,
        { repo_url: repoUrl },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setCurrentStage('repo');
      pollTaskStatus();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to start generation');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleStageNext(stageId, data) {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getAccessTokenSilently();
      const stageEndpoints = {
        'repo': '/stage2',
        'analysis': '/stage3', 
        'pathways': '/stage4'
      };
      
      const endpoint = stageEndpoints[stageId];
      if (endpoint) {
        await axios.post(
          `${API_BASE_URL}/course-generation/${courseId}${endpoint}`,
          data || {},
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        const nextStageMap = {
          'repo': 'analysis',
          'analysis': 'pathways',
          'pathways': 'generation'
        };
        
        setCurrentStage(nextStageMap[stageId]);
        pollTaskStatus();
      }
    } catch (error) {
      setError(error.response?.data?.detail || `Failed to proceed to next stage`);
    } finally {
      setIsLoading(false);
    }
  }

  function pollTaskStatus() {
    const pollInterval = setInterval(async () => {
      try {
        const token = await getAccessTokenSilently();
        const response = await axios.get(
          `${API_BASE_URL}/course-generation/${courseId}/status`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        if (response.data) {
          setTaskStatus(response.data);
          
          if (response.data.status === 'completed') {
            const stage = response.data.current_stage;
            updateStageProgress(stage, 'completed');
            
            // Load stage-specific data
            if (stage === 'clone_repo') {
              await loadStage1Data();
            } else if (stage === 'pathway_building') {
              await loadStage3Data();
            }
            
            clearInterval(pollInterval);
          } else if (response.data.status === 'failed') {
            setError(response.data.error_message || 'Generation failed');
            clearInterval(pollInterval);
          }
        }
      } catch (error) {
        console.error('Error polling status:', error);
        clearInterval(pollInterval);
      }
    }, 2000);

    setTimeout(() => clearInterval(pollInterval), 300000);
  }

  async function loadStage1Data() {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage1`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStageData(prev => ({ ...prev, repo: response.data }));
    } catch (error) {
      console.error('Failed to load stage 1 data:', error);
    }
  }

  async function loadStage3Data() {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage3`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStageData(prev => ({ ...prev, pathways: response.data }));
    } catch (error) {
      console.error('Failed to load stage 3 data:', error);
    }
  }
};

// Start Section Component
const StartSection = ({ course, onStart, isLoading }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) {
      setError('Repository URL is required');
      return;
    }
    
    try {
      new URL(repoUrl);
    } catch {
      setError('Please enter a valid URL');
      return;
    }
    
    onStart(repoUrl);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-6 text-white">
        <h2 className="text-2xl font-bold mb-2">Let's Generate Your Course! 🚀</h2>
        <p className="opacity-90">
          Connect your GitHub repository to start creating an AI-powered course from your documentation.
        </p>
      </div>
      
      <div className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              GitHub Repository URL
            </label>
            <input
              type="url"
              value={repoUrl}
              onChange={(e) => {
                setRepoUrl(e.target.value);
                setError('');
              }}
              className={`w-full px-4 py-3 border-2 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors ${
                error ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="https://github.com/username/repository"
              disabled={isLoading}
            />
            {error && (
              <p className="mt-2 text-sm text-red-600">{error}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || !repoUrl.trim()}
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3 px-6 rounded-lg font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                Starting Generation...
              </div>
            ) : (
              'Start Course Generation'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

// Stage Accordion Component
const StageAccordion = ({ stage, status, canAccess, taskStatus, stageData, onNext, course, isLoading }) => {
  const [isExpanded, setIsExpanded] = useState(status === 'active');

  useEffect(() => {
    if (status === 'active') {
      setIsExpanded(true);
    }
  }, [status]);

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return (
          <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          </div>
        );
      case 'active':
        return (
          <div className="w-6 h-6 bg-blue-500 rounded-full animate-pulse"></div>
        );
      default:
        return (
          <div className="w-6 h-6 bg-gray-300 rounded-full"></div>
        );
    }
  };

  const getStageContent = () => {
    switch (stage.id) {
      case 'repo':
        return (
          <Stage1Content 
            status={status}
            taskStatus={taskStatus}
            stageData={stageData}
            onNext={onNext}
            isLoading={isLoading}
          />
        );
      case 'analysis':
        return (
          <Stage2Content 
            status={status}
            taskStatus={taskStatus}
            onNext={onNext}
          />
        );
      case 'pathways':
        return (
          <Stage3Content 
            status={status}
            taskStatus={taskStatus}
            stageData={stageData}
            onNext={onNext}
            isLoading={isLoading}
          />
        );
      case 'generation':
        return (
          <Stage4Content 
            status={status}
            taskStatus={taskStatus}
            course={course}
          />
        );
      default:
        return null;
    }
  };

  if (!canAccess && status === 'pending') {
    return (
      <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 p-6">
        <div className="flex items-center space-x-3 opacity-50">
          <div className="w-6 h-6 bg-gray-300 rounded-full"></div>
          <div>
            <h3 className="font-medium text-gray-600">{stage.title}</h3>
            <p className="text-sm text-gray-500">{stage.description}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl shadow-sm border-2 transition-all duration-200 ${
      status === 'active' ? 'border-blue-300 shadow-blue-100' : 
      status === 'completed' ? 'border-green-300' : 'border-gray-200'
    }`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-6 text-left focus:outline-none"
        disabled={!canAccess}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getStatusIcon()}
            <div>
              <h3 className="font-semibold text-gray-900">{stage.title}</h3>
              <p className="text-sm text-gray-600">{stage.description}</p>
            </div>
          </div>
          <svg 
            className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${
              isExpanded ? 'rotate-180' : ''
            }`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      
      {isExpanded && (
        <div className="px-6 pb-6 border-t border-gray-100">
          {getStageContent()}
        </div>
      )}
    </div>
  );
};

export default CourseCreationPage; 