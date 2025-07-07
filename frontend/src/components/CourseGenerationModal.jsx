import React, { useState, useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';
import Stage1Component from './Stage1Component';
import Stage2Component from './Stage2Component';
import Stage3Component from './Stage3Component';
import Stage4Component from './Stage4Component';

const CourseGenerationModal = ({ isOpen, onClose, course }) => {
  const { getAccessTokenSilently } = useAuth0();
  const [currentStage, setCurrentStage] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);
  const [stageData, setStageData] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen && course) {
      setCurrentStage(null);
      setTaskStatus(null);
      setStageData({});
      setError(null);
      checkExistingGeneration();
    }
  }, [isOpen, course]);

  const checkExistingGeneration = async () => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${course.course_id}/status`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      if (response.data) {
        setTaskStatus(response.data);
        setCurrentStage(response.data.current_stage);
        
        // Load stage-specific data based on current stage
        if (response.data.current_stage === 'clone_repo' && response.data.status === 'completed') {
          setTimeout(() => loadStage1Data(), 500); // Small delay for initial load
        } else if (response.data.current_stage === 'pathway_building' && response.data.status === 'completed') {
          setTimeout(() => loadStage3Data(), 500); // Small delay for initial load
        }
      }
    } catch (error) {
      console.log('No existing generation found');
    }
  };

  const loadStage1Data = async (retryCount = 0) => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${course.course_id}/stage1`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setStageData(prev => ({ ...prev, stage1: response.data }));
    } catch (error) {
      console.error('Failed to load stage 1 data:', error);
      
      // Handle different HTTP status codes appropriately
      if (error.response?.status === 202) {
        // Stage 1 is still in progress - retry with a longer delay
        const delay = Math.min((retryCount + 1) * 3000, 10000); // 3s, 6s, 9s, max 10s
        console.log(`Stage 1 still in progress, retrying in ${delay}ms (attempt ${retryCount + 1})`);
        setTimeout(() => loadStage1Data(retryCount + 1), delay);
      } else if (error.response?.status === 400) {
        // Stage 1 failed - don't retry, show error
        const errorMessage = error.response?.data?.detail || 'Repository analysis failed';
        setError(errorMessage);
      } else if (retryCount < 3) {
        // Other errors - retry up to 3 times with increasing delays
        const delay = (retryCount + 1) * 2000; // 2s, 4s, 6s
        console.log(`Retrying stage 1 data load in ${delay}ms (attempt ${retryCount + 1}/3)`);
        setTimeout(() => loadStage1Data(retryCount + 1), delay);
      } else {
        // Show error to user only after all retries failed
        const errorMessage = error.response?.data?.detail || 'Failed to load repository analysis data';
        setError(errorMessage);
      }
    }
  };

  const loadStage3Data = async (retryCount = 0) => {
    try {
      const token = await getAccessTokenSilently();
      const response = await axios.get(
        `${API_BASE_URL}/course-generation/${course.course_id}/stage3`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      setStageData(prev => ({ ...prev, stage3: response.data }));
    } catch (error) {
      console.error('Failed to load stage 3 data:', error);
      
      // Retry up to 3 times with increasing delays
      if (retryCount < 3) {
        const delay = (retryCount + 1) * 2000; // 2s, 4s, 6s
        console.log(`Retrying stage 3 data load in ${delay}ms (attempt ${retryCount + 1}/3)`);
        setTimeout(() => loadStage3Data(retryCount + 1), delay);
      } else {
        const errorMessage = error.response?.data?.detail || 'Failed to load learning pathways data';
        setError(errorMessage);
      }
    }
  };

  const startGeneration = async (repoUrl) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getAccessTokenSilently();
      await axios.post(
        `${API_BASE_URL}/course-generation/${course.course_id}/start`,
        { repo_url: repoUrl },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setCurrentStage('clone_repo');
      pollTaskStatus();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to start generation');
    } finally {
      setIsLoading(false);
    }
  };

  const pollTaskStatus = async () => {
    const pollInterval = setInterval(async () => {
      try {
        const token = await getAccessTokenSilently();
        const response = await axios.get(
          `${API_BASE_URL}/course-generation/${course.course_id}/status`,
          {
            headers: { Authorization: `Bearer ${token}` }
          }
        );

        if (response.data) {
          setTaskStatus(response.data);
          
          if (response.data.status === 'completed') {
            if (response.data.current_stage === 'clone_repo') {
              setTimeout(() => loadStage1Data(), 1000); // Small delay to ensure files are written
            } else if (response.data.current_stage === 'pathway_building') {
              setTimeout(() => loadStage3Data(), 1000); // Small delay to ensure files are written
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

    // Clear interval after 5 minutes to prevent infinite polling
    setTimeout(() => clearInterval(pollInterval), 300000);
  };

  const renderStageContent = () => {
    if (!currentStage) {
      return <StartStage onStart={startGeneration} />;
    }

    switch (currentStage) {
      case 'clone_repo':
        return (
          <Stage1Component
            course={course}
            taskStatus={taskStatus}
            stageData={stageData.stage1}
            onNext={(selections) => handleStage2(selections)}
          />
        );
      case 'document_analysis':
        return (
          <Stage2Component
            course={course}
            taskStatus={taskStatus}
            onNext={() => handleStage3()}
          />
        );
      case 'pathway_building':
        return (
          <Stage3Component
            course={course}
            taskStatus={taskStatus}
            stageData={stageData.stage3}
            onNext={(selections) => handleStage4(selections)}
          />
        );
      case 'course_generation':
        return (
          <Stage4Component
            course={course}
            taskStatus={taskStatus}
            stageData={stageData.stage4}
            onNext={() => {
              setCurrentStage('completed');
              onClose();
            }}
          />
        );
      default:
        return <div>Unknown stage</div>;
    }
  };

  const handleStage2 = async (selections) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getAccessTokenSilently();
      await axios.post(
        `${API_BASE_URL}/course-generation/${course.course_id}/stage2`,
        selections,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setCurrentStage('document_analysis');
      pollTaskStatus();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to start document analysis');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStage3 = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getAccessTokenSilently();
      await axios.post(
        `${API_BASE_URL}/course-generation/${course.course_id}/stage3`,
        {},
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setCurrentStage('pathway_building');
      pollTaskStatus();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to start pathway building');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStage4 = async (selections) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = await getAccessTokenSilently();
      await axios.post(
        `${API_BASE_URL}/course-generation/${course.course_id}/stage4`,
        selections,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      
      setCurrentStage('course_generation');
      pollTaskStatus();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to start course generation');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen || !course) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Generate Course: {course.title}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors duration-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Stage {getStageNumber(currentStage)} of 4</span>
              <span>{taskStatus?.progress_percentage || 0}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${taskStatus?.progress_percentage || 0}%` }}
              />
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {/* Stage Content */}
          {renderStageContent()}
        </div>
      </div>
    </div>
  );
};

const getStageNumber = (stage) => {
  switch (stage) {
    case 'clone_repo': return 1;
    case 'document_analysis': return 2;
    case 'pathway_building': return 3;
    case 'course_generation': return 4;
    default: return 0;
  }
};

// Start Stage Component
const StartStage = ({ onStart }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) {
      setError('Repository URL is required');
      return;
    }
    
    // Basic URL validation
    try {
      new URL(repoUrl);
    } catch {
      setError('Please enter a valid URL');
      return;
    }
    
    onStart(repoUrl);
  };

  return (
    <div className="text-center">
      <div className="mb-6">
        <div className="mx-auto w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">Start Course Generation</h3>
        <p className="text-gray-600">Enter the repository URL to begin generating your course</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="repoUrl" className="block text-sm font-medium text-gray-700 mb-2">
            Repository URL
          </label>
          <input
            type="url"
            id="repoUrl"
            value={repoUrl}
            onChange={(e) => {
              setRepoUrl(e.target.value);
              setError('');
            }}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              error ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="https://github.com/username/repository"
          />
          {error && (
            <p className="mt-1 text-sm text-red-600">{error}</p>
          )}
        </div>

        <button
          type="submit"
          className="w-full bg-blue-500 text-white px-6 py-3 rounded-md hover:bg-blue-600 transition-colors duration-200 font-medium"
        >
          Start Generation
        </button>
      </form>
    </div>
  );
};

export default CourseGenerationModal; 