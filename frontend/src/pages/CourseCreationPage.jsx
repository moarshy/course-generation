import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Stage1Content, Stage2Content, Stage3Content, Stage4Content } from '../components/StageContent';
import StageTrail from '../components/StageTrail';

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
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

  const stages = [
    { id: 'repo', title: 'Repository Setup', description: 'Connect your GitHub repository', icon: '📁' },
    { id: 'analysis', title: 'Document Analysis', description: 'AI analyzes your documentation', icon: '🔍' },
    { id: 'pathways', title: 'Learning Pathways', description: 'Review and customize learning paths', icon: '🛤️' },
    { id: 'generation', title: 'Course Generation', description: 'Generate your final course', icon: '🎓' }
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
        console.log('Found existing generation:', response.data);
        setTaskStatus(response.data);
        updateStageProgress(response.data.current_stage, response.data.status);
        
        // Load stage-specific data based on current stage
        if (response.data.current_stage === 'clone_repo' && response.data.status === 'completed') {
          console.log('Loading stage 1 data...');
          await loadStage1Data();
        } else if (response.data.current_stage === 'document_analysis' && response.data.status === 'completed') {
          console.log('Loading stage 2 data...');
          await loadStage2Data();
        } else if (response.data.current_stage === 'pathway_building' && response.data.status === 'completed') {
          console.log('Loading stage 3 data...');
          await loadStage3Data();
        }
        
        // If a stage is running, start polling
        if (response.data.status === 'running') {
          console.log('Starting polling for running stage...');
          pollTaskStatus();
        }
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

  const handleStageChange = (stageId) => {
    if (canAccessStage(stageId)) {
      setCurrentStage(stageId);
    }
  };

  const pollTaskStatus = async () => {
    try {
      console.log('Polling task status...');
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/status`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data) {
        console.log('Poll result:', response.data);
        setTaskStatus(response.data);
        updateStageProgress(response.data.current_stage, response.data.status);
        
        // Load stage data when stages complete
        if (response.data.status === 'completed') {
          const stage = response.data.current_stage;
          console.log(`Stage ${stage} completed, loading data...`);
          
          // Load stage-specific data
          if (stage === 'clone_repo') {
            await loadStage1Data();
          } else if (stage === 'document_analysis') {
            await loadStage2Data();
          } else if (stage === 'pathway_building') {
            await loadStage3Data();
          }
        }
        
        // Handle stage transitions and polling logic
        if (response.data.status === 'running' || response.data.status === 'pending') {
          console.log('Continuing polling...');
          setTimeout(pollTaskStatus, 2000);
        } else if (response.data.status === 'completed') {
          const stage = response.data.current_stage;
          console.log(`Stage ${stage} completed, handling transition...`);
          
          // Handle stage transitions
          if (stage === 'clone_repo') {
            // After repo clone, user needs to configure Stage 2
            setCurrentStage('analysis');
            console.log('Polling stopped, waiting for user input for Stage 2');
          } else if (stage === 'document_analysis') {
            // After document analysis, stay on analysis stage to review results
            setCurrentStage('analysis');
            console.log('Polling stopped, document analysis complete, user can review results');
          } else if (stage === 'pathway_building') {
            // After pathway building, user needs to select pathway
            setCurrentStage('pathways');
            console.log('Polling stopped, waiting for user input for Stage 3');
          } else if (stage === 'course_generation') {
            // Final stage completed
            setCurrentStage('generation');
            console.log('Polling stopped, course generation complete');
          }
        } else if (response.data.status === 'failed') {
          console.log('Generation failed:', response.data.error_message);
          setError(response.data.error_message || 'Generation failed');
        }
      }
    } catch (error) {
      console.error('Error polling task status:', error);
    }
  };

  // Add missing load functions
  const loadStage1Data = async () => {
    try {
      console.log('Loading stage 1 data...');
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage1`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Stage 1 data loaded:', response.data);
      setStageData(prev => ({ ...prev, repo: response.data }));
    } catch (error) {
      console.error('Failed to load stage 1 data:', error);
    }
  };

  const loadStage2Data = async () => {
    try {
      console.log('Loading stage 2 data...');
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage2`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Stage 2 data loaded:', response.data);
      setStageData(prev => ({ ...prev, analysis: response.data }));
    } catch (error) {
      console.error('Failed to load stage 2 data:', error);
    }
  };

  const loadStage3Data = async () => {
    try {
      console.log('Loading stage 3 data...');
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage3`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Stage 3 data loaded:', response.data);
      setStageData(prev => ({ ...prev, pathways: response.data }));
    } catch (error) {
      console.error('Failed to load stage 3 data:', error);
    }
  };

  const renderMainContent = () => {
    if (!course) {
      return (
        <div className="flex items-center justify-center min-h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      );
    }

    switch (currentStage) {
      case 'start':
        return (
          <StartSection 
            course={course}
            onStart={(repoUrl) => handleStartGeneration(repoUrl)}
            isLoading={isLoading}
          />
        );
      case 'repo':
        return (
          <Stage1Content 
            status={getStageStatus('repo')}
            taskStatus={taskStatus}
            stageData={stageData.repo}
            onNext={(data) => handleStageNext('repo', data)}
            isLoading={isLoading}
          />
        );
      case 'analysis':
        return (
          <Stage2Content 
            status={getStageStatus('analysis')}
            taskStatus={taskStatus}
            stageData={stageData.analysis}
            course={course}
            onNext={(data) => handleStageNext('analysis', data)}
            isLoading={isLoading}
          />
        );
      case 'pathways':
        return (
          <Stage3Content 
            status={getStageStatus('pathways')}
            taskStatus={taskStatus}
            stageData={stageData.pathways}
            course={course}
            onNext={(data) => handleStageNext('pathways', data)}
            isLoading={isLoading}
          />
        );
      case 'generation':
        return (
          <Stage4Content 
            status={getStageStatus('generation')}
            taskStatus={taskStatus}
            course={course}
          />
        );
      default:
        return null;
    }
  };

  if (!course) {
    return (
      <div className="bg-gray-50 flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Stage Trail Sidebar */}
      <div className={`${isSidebarCollapsed ? 'w-16' : 'w-80'} transition-all duration-300 bg-white shadow-lg border-r border-gray-200 flex flex-col`}>
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            {!isSidebarCollapsed && (
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => navigate('/dashboard')}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                </button>
                <div>
                  <h1 className="text-lg font-bold text-gray-900 truncate">{course.title}</h1>
                  <p className="text-sm text-gray-600">Course Generation</p>
                </div>
              </div>
            )}
            <button
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <svg className={`w-5 h-5 text-gray-600 transition-transform ${isSidebarCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Stage Trail */}
        <StageTrail
          stages={stages}
          currentStage={currentStage}
          completedStages={completedStages}
          taskStatus={taskStatus}
          stageData={stageData}
          onStageChange={handleStageChange}
          isCollapsed={isSidebarCollapsed}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Main Header */}
        <div className="bg-white shadow-sm border-b border-gray-200">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {stages.find(s => s.id === currentStage)?.title || 'Getting Started'}
                </h2>
                <p className="text-gray-600">
                  {stages.find(s => s.id === currentStage)?.description || 'Let\'s start generating your course'}
                </p>
              </div>
              <div className="flex items-center space-x-3">
                <div className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                  {course.status}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mx-6 mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <svg className="w-5 h-5 text-red-400 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <p className="text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="flex-1 p-6">
          {renderMainContent()}
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
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-8 text-white">
          <h2 className="text-3xl font-bold mb-3">Let's Generate Your Course! 🚀</h2>
          <p className="text-blue-100 text-lg">
            Connect your GitHub repository to start creating an AI-powered course from your documentation.
          </p>
        </div>
        
        <div className="p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
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
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-4 px-6 rounded-lg font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed text-lg"
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
    </div>
  );
};

export default CourseCreationPage; 