import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Stage1Content, Stage2Content, Stage3Content, Stage4Content } from '../components/StageContent';
import Stage1Component from '../components/Stage1Component';
import StageTrail from '../components/StageTrail';
import ToastContainer from '../components/ToastContainer';
import { useToast } from '../hooks/useToast';

const CourseCreationPage = () => {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const { getAccessTokenSilently } = useAuth0();
  
  const [course, setCourse] = useState(null);
  const [currentStage, setCurrentStage] = useState('repo');
  const [completedStages, setCompletedStages] = useState(new Set());
  const [taskStatus, setTaskStatus] = useState(null);
  const [stageData, setStageData] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  // Toast notifications
  const { toasts, removeToast, showSuccess, showError, showInfo } = useToast();

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
        updateStageProgress(response.data);
        
        // Load stage-specific data based on completed stages
        const stageStatuses = response.data.stage_statuses || {};
        const completedStages = response.data.completed_stages || [];
        
        // Helper function to check if stage is completed
        const isStageCompleted = (stageKey) => {
          return stageStatuses[stageKey] === 'completed' || 
                 stageStatuses[stageKey.toLowerCase()] === 'completed' ||
                 completedStages.includes(stageKey.toLowerCase()) ||
                 completedStages.includes(stageKey);
        };
        
        if (isStageCompleted('CLONE_REPO') && !stageData.repo) {
          console.log('Loading stage 1 data...');
          setTimeout(() => loadStage1Data(), 500); // Small delay for initial load
        }
        if (isStageCompleted('DOCUMENT_ANALYSIS') && !stageData.analysis) {
          console.log('Loading stage 2 data...');
          setTimeout(() => loadStage2Data(), 500); // Small delay for initial load
        }
        if (isStageCompleted('PATHWAY_BUILDING') && !stageData.pathways) {
          console.log('Loading stage 3 data...');
          setTimeout(() => loadStage3Data(), 500); // Small delay for initial load
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

  const updateStageProgress = (taskStatusData) => {
    // Handle case where taskStatusData is null/undefined (new courses)
    if (!taskStatusData) {
      setCurrentStage('repo');
      setCompletedStages(new Set());
      return;
    }
    
    const stageMap = {
      'CLONE_REPO': 'repo',
      'clone_repo': 'repo',
      'DOCUMENT_ANALYSIS': 'analysis',
      'document_analysis': 'analysis',
      'PATHWAY_BUILDING': 'pathways',
      'pathway_building': 'pathways',
      'COURSE_GENERATION': 'generation',
      'course_generation': 'generation'
    };
    
    // Use new detailed stage statuses if available, fallback to old structure
    if (taskStatusData.stage_statuses) {
      const newCompletedStages = new Set();
      let activeStage = null;
      
      // Process each stage status
      Object.entries(taskStatusData.stage_statuses).forEach(([stage, status]) => {
        const mappedStage = stageMap[stage];
        console.log(`Processing stage: ${stage} -> ${mappedStage} (status: ${status})`);
        if (mappedStage) {
          if (status === 'completed') {
            console.log(`Marking ${mappedStage} as completed`);
            newCompletedStages.add(mappedStage);
          } else if (status === 'running' || status === 'failed') {
            console.log(`Setting ${mappedStage} as active stage`);
            activeStage = mappedStage;
          }
        }
      });
      
      // Also check the completed_stages array for backward compatibility
      if (taskStatusData.completed_stages) {
        taskStatusData.completed_stages.forEach(stage => {
          const mappedStage = stageMap[stage];
          if (mappedStage) {
            newCompletedStages.add(mappedStage);
          }
        });
      }
      
      setCompletedStages(newCompletedStages);
      
              // Handle stage progression logic
        if (activeStage) {
          // There's an active backend task, switch to that stage
          setCurrentStage(activeStage);
        } else {
          // No active backend task
          // Don't automatically advance stages when tasks complete
          // Let the user control progression by clicking "Next"
          // Only set initial stage if none is set
          if (!currentStage) {
            setCurrentStage('repo');
          }
          // Otherwise, keep the current stage unchanged
        }
    } else {
      // Fallback to old logic for backward compatibility
      const mappedStage = stageMap[taskStatusData.current_stage];
      if (mappedStage) {
        setCurrentStage(mappedStage);
        if (taskStatusData.status === 'completed') {
          setCompletedStages(prev => new Set([...prev, mappedStage]));
        }
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
        updateStageProgress(response.data);
        
        // Load stage data when stages complete
        const stageStatuses = response.data.stage_statuses || {};
        const completedStages = response.data.completed_stages || [];
        
        // Helper function to check if stage is completed
        const isStageCompleted = (stageKey) => {
          return stageStatuses[stageKey] === 'completed' || 
                 stageStatuses[stageKey.toLowerCase()] === 'completed' ||
                 completedStages.includes(stageKey.toLowerCase()) ||
                 completedStages.includes(stageKey);
        };
        
        // Load data for newly completed stages (with small delay to ensure files are written)
        if (isStageCompleted('CLONE_REPO') && !stageData.repo) {
          console.log('Stage 1 completed, loading data...');
          setTimeout(async () => {
            await loadStage1Data();
            showSuccess('✅ Repository analysis completed! Ready to select folders.');
          }, 1000); // 1 second delay
        } else if (isStageCompleted('CLONE_REPO') && stageData.repo) {
          console.log('Stage 1 completed, data already loaded:', stageData.repo);
        }
        if (isStageCompleted('DOCUMENT_ANALYSIS') && !stageData.analysis) {
          console.log('Stage 2 completed, loading data...');
          setTimeout(async () => {
            await loadStage2Data();
            showSuccess('✅ Document analysis completed! Review the results.');
          }, 1000); // 1 second delay
        }
        if (isStageCompleted('PATHWAY_BUILDING') && !stageData.pathways) {
          console.log('Stage 3 completed, loading data...');
          setTimeout(async () => {
            await loadStage3Data();
            showSuccess('✅ Learning pathways generated! Select your preferred pathway.');
          }, 1000); // 1 second delay
        }
        
        // Handle stage transitions and polling logic
        const currentStageStatus = response.data.status;
        console.log('Current stage status:', currentStageStatus, 'Stage statuses:', stageStatuses);
        
        if (currentStageStatus === 'running' || currentStageStatus === 'pending') {
          console.log('Task is running, continuing polling...');
          setTimeout(pollTaskStatus, 2000);
        } else if (currentStageStatus === 'completed') {
          // Check if any individual stage is still running
          const hasRunningStage = Object.values(stageStatuses).includes('running');
          if (hasRunningStage) {
            console.log('A stage is still running, continuing polling...');
            setTimeout(pollTaskStatus, 2000);
          } else {
            console.log('All stages completed');
            // Check if we need to load final stage data
            if (isStageCompleted('COURSE_GENERATION') && !stageData.generation) {
              console.log('Stage 4 completed, loading data...');
              await loadStage4Data();
            }
          }
        } else if (currentStageStatus === 'failed') {
          console.log('Generation failed:', response.data.error_message);
          const errorMessage = response.data.error_message || 'Generation failed';
          setError(errorMessage);
          showError(`❌ ${errorMessage}`);
        }
      }
    } catch (error) {
      console.error('Error polling task status:', error);
    }
  };

  // Add missing load functions
  const loadStage1Data = async (retryCount = 0) => {
    try {
      console.log(`Loading stage 1 data (attempt ${retryCount + 1})...`);
      const token = await getAccessTokenSilently();
      
      // Add timeout to the request
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage1`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          timeout: 30000 // 30 second timeout
        }
      );
      console.log('Stage 1 data loaded successfully:', response.data);
      setStageData(prev => ({ ...prev, repo: response.data }));
    } catch (error) {
      console.error(`Failed to load stage 1 data (attempt ${retryCount + 1}):`, error);
      console.error('Error details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        message: error.message
      });
      
      // Handle different HTTP status codes appropriately
      if (error.response?.status === 202) {
        // Stage 1 is still in progress - retry with a longer delay (max 10 attempts)
        if (retryCount < 10) {
          const delay = Math.min((retryCount + 1) * 3000, 10000); // 3s, 6s, 9s, max 10s
          console.log(`Stage 1 still in progress, retrying in ${delay}ms (attempt ${retryCount + 1}/10)`);
          setTimeout(() => loadStage1Data(retryCount + 1), delay);
        } else {
          console.error('Maximum retries reached for stage 1 data loading');
          showError(`❌ Stage 1 is taking too long. Please check the task status or try refreshing the page.`);
        }
      } else if (error.response?.status === 400) {
        // Stage 1 failed - don't retry, show error
        const errorMessage = error.response?.data?.detail || 'Repository analysis failed';
        showError(`❌ ${errorMessage}`);
      } else if (retryCount < 3) {
        // Other errors - retry up to 3 times with increasing delays
        const delay = (retryCount + 1) * 2000; // 2s, 4s, 6s
        console.log(`Retrying stage 1 data load in ${delay}ms (attempt ${retryCount + 1}/3)`);
        setTimeout(() => loadStage1Data(retryCount + 1), delay);
      } else {
        // Show error to user only after all retries failed
        const errorMessage = error.response?.data?.detail || 'Failed to load repository analysis data';
        showError(`❌ ${errorMessage}`);
      }
    }
  };

  const loadStage2Data = async (retryCount = 0) => {
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
      
      // Retry up to 3 times with increasing delays
      if (retryCount < 3) {
        const delay = (retryCount + 1) * 2000; // 2s, 4s, 6s
        console.log(`Retrying stage 2 data load in ${delay}ms (attempt ${retryCount + 1}/3)`);
        setTimeout(() => loadStage2Data(retryCount + 1), delay);
      } else {
        const errorMessage = error.response?.data?.detail || 'Failed to load document analysis data';
        showError(`❌ ${errorMessage}`);
      }
    }
  };

  const loadStage3Data = async (retryCount = 0) => {
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
      
      // Retry up to 3 times with increasing delays
      if (retryCount < 3) {
        const delay = (retryCount + 1) * 2000; // 2s, 4s, 6s
        console.log(`Retrying stage 3 data load in ${delay}ms (attempt ${retryCount + 1}/3)`);
        setTimeout(() => loadStage3Data(retryCount + 1), delay);
      } else {
        const errorMessage = error.response?.data?.detail || 'Failed to load learning pathways data';
        showError(`❌ ${errorMessage}`);
      }
    }
  };

  const loadStage4Data = async (retryCount = 0) => {
    try {
      console.log('Loading stage 4 data...');
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${courseId}/stage4`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Stage 4 data loaded:', response.data);
      setStageData(prev => ({ ...prev, generation: response.data }));
    } catch (error) {
      console.error('Failed to load stage 4 data:', error);
      
      // Retry up to 3 times with increasing delays
      if (retryCount < 3) {
        const delay = (retryCount + 1) * 2000; // 2s, 4s, 6s
        console.log(`Retrying stage 4 data load in ${delay}ms (attempt ${retryCount + 1}/3)`);
        setTimeout(() => loadStage4Data(retryCount + 1), delay);
      } else {
        const errorMessage = error.response?.data?.detail || 'Failed to load course generation data';
        showError(`❌ ${errorMessage}`);
      }
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

    // Show start section if no task has been started yet
    if (currentStage === 'repo' && !taskStatus) {
      return (
        <StartSection 
          course={course}
          onStart={(repoUrl) => handleStartGeneration(repoUrl)}
          isLoading={isLoading}
        />
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
          <Stage1Component 
            course={course}
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
    <>
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
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
                  {currentStage === 'repo' && !taskStatus ? 'Getting Started' : (stages.find(s => s.id === currentStage)?.title || 'Getting Started')}
                </h2>
                <p className="text-gray-600">
                  {currentStage === 'repo' && !taskStatus ? 'Let\'s start generating your course' : (stages.find(s => s.id === currentStage)?.description || 'Let\'s start generating your course')}
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
    </>
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
      showInfo('🚀 Started repository analysis! This may take a few minutes.');
      pollTaskStatus();
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Failed to start generation';
      setError(errorMessage);
      showError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleStageNext(stageId, data) {
    setIsLoading(true);
    setError(null);
    
    const stageNames = {
      'repo': 'Document Analysis',
      'analysis': 'Learning Pathways',
      'pathways': 'Course Generation'
    };
    
    try {
      const token = await getAccessTokenSilently();
      
      // Special handling for Stage 1 (repo) - save selections first
      if (stageId === 'repo') {
        // First, save the Stage 1 selections
        await axios.post(
          `${API_BASE_URL}/course-generation/${courseId}/stage1/selections`,
          data || {},
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        // Then start Stage 2 with the same data
        await axios.post(
          `${API_BASE_URL}/course-generation/${courseId}/stage2`,
          data || {},
          { headers: { Authorization: `Bearer ${token}` } }
        );
      } else {
        // For other stages, use the normal flow
        const stageEndpoints = {
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
        }
      }
      
      const nextStageMap = {
        'repo': 'analysis',
        'analysis': 'pathways',
        'pathways': 'generation'
      };
      
      setCurrentStage(nextStageMap[stageId]);
      showInfo(`🔄 Starting ${stageNames[stageId]}...`);
      pollTaskStatus();
      
    } catch (error) {
      console.error('Stage transition error:', error.response?.data);
      let errorMessage = `Failed to proceed to next stage`;
      
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          // Handle validation errors array
          errorMessage = error.response.data.detail.map(err => 
            typeof err === 'string' ? err : err.msg || JSON.stringify(err)
          ).join(', ');
        } else {
          // Handle validation error object
          errorMessage = error.response.data.detail.msg || JSON.stringify(error.response.data.detail);
        }
      }
      
      setError(errorMessage);
      showError(errorMessage);
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