# Frontend Migration Plan

## 🎯 Overview
This document outlines the complete migration plan to modernize the frontend to match our new Celery-based backend architecture. 

## ✅ Backend Achievements
- **Complete Celery Task Architecture**: All 4 stages run as async tasks
- **Database-Driven Progress**: Real-time progress in `course_tasks` table  
- **Stage 4 Pipeline Fixed**: Complete course generation working
- **Document Assignments**: Stage 3 now saves/loads document-to-module mappings
- **Unified API Endpoints**: Consistent endpoints with proper progress tracking

## 📋 Migration Phases

### Phase 1: ✅ API Layer Modernization (COMPLETED)
- ✅ Created `courseService.js` - Centralized API service
- ✅ Standardized all API calls to match backend architecture
- ✅ Added proper error handling and timeouts

### Phase 2: ✅ Progress Tracking Hook (COMPLETED)
- ✅ Created `useCourseProgress.js` - Modern progress tracking hook
- ✅ Replaced complex polling logic with clean, reusable solution
- ✅ Added automatic cleanup and error handling

### Phase 3: 🔄 Component Modernization (IN PROGRESS)

#### 3.1 Update CourseCreationPage
**Current Issues:**
- ❌ Complex manual stage progression logic
- ❌ Scattered API calls throughout component
- ❌ Complex retry and error handling
- ❌ Manual polling with setInterval

**Required Changes:**
```javascript
// Replace current logic with:
import { useCourseProgress } from '../hooks/useCourseProgress';
import courseService from '../services/courseService';

const CourseCreationPage = () => {
  const { courseId } = useParams();
  const {
    courseData,
    currentStage,
    stageStatuses,
    startStage,
    getStageResults,
    getStageStatus,
    isPolling,
    error
  } = useCourseProgress(courseId);

  // Simplified stage management
  const handleStageNext = async (stage, inputData) => {
    const result = await startStage(stage, inputData);
    if (!result.success) {
      showError(result.error);
    }
  };

  // Clean component render logic
  const renderStageContent = () => {
    switch (currentStage) {
      case 'repo':
        return <Stage1Component 
          status={getStageStatus('repo')}
          onNext={(data) => handleStageNext('analysis', data)}
        />;
      // ... other stages
    }
  };
};
```

#### 3.2 Modernize Stage Components

**Stage1Component Updates:**
- ✅ Remove manual API calls - use courseService
- ✅ Simplify loading states 
- ✅ Use standardized progress tracking

**Stage2Component Updates:**
- ✅ Add real-time progress for document analysis
- ✅ Use new detailed progress API endpoint
- ✅ Show per-document analysis progress

**Stage3Component Updates:**
- ✅ Leverage new document assignment data
- ✅ Show which documents are assigned to which modules
- ✅ Display pathway generation debate history

**Stage4Component Updates:**
- ✅ Add real-time content generation progress
- ✅ Show module-by-module generation status
- ✅ Display debate system progress

#### 3.3 Remove Legacy Components
- ❌ Delete `CourseGenerationModal.jsx` (duplicate functionality)
- ❌ Clean up `StageContent.jsx` (unused complex logic)
- ❌ Remove manual polling functions

### Phase 4: 🔄 Enhanced User Experience (NEXT)

#### 4.1 Real-Time Progress Components
```javascript
// New progress components to create
<DetailedProgressBar 
  stage="analysis" 
  progress={stageProgress.analysis}
  showFileProgress={true}
/>

<StageDebateHistory 
  stage="pathways"
  history={stageData.debate_history}
/>

<ModuleGenerationProgress
  stage="generation"
  modules={generationProgress.modules}
/>
```

#### 4.2 Document Assignment Visualization
```javascript
// Show document-to-module mappings from Stage 3
<DocumentModuleMapping 
  pathways={stage3Results.pathways}
  documents={stage2Results.analyzed_documents}
/>
```

#### 4.3 Enhanced Error Handling
```javascript
// Unified error system
<ErrorBoundary>
  <StageComponent onError={handleStageError} />
</ErrorBoundary>
```

### Phase 5: 🔄 Performance Optimization (FUTURE)

#### 5.1 Code Splitting
```javascript
// Lazy load stage components
const Stage1Component = lazy(() => import('./Stage1Component'));
const Stage2Component = lazy(() => import('./Stage2Component'));
```

#### 5.2 Caching Strategy
```javascript
// Cache stage results to avoid re-fetching
const useStageCache = (stage) => {
  // Implementation for caching stage data
};
```

## 🔧 Implementation Steps

### Step 1: Update CourseCreationPage (Priority: HIGH)
1. Replace current logic with `useCourseProgress` hook
2. Remove manual polling and API calls
3. Simplify state management
4. Test with existing courses

### Step 2: Modernize Stage Components (Priority: HIGH)
1. Update Stage1Component to use courseService
2. Add real-time progress to Stage2Component
3. Show document assignments in Stage3Component
4. Enhance Stage4Component with detailed progress

### Step 3: Enhanced Progress Tracking (Priority: MEDIUM)
1. Create DetailedProgressBar component
2. Add stage-specific progress displays
3. Show debate system progress
4. Add document-module mapping visualization

### Step 4: Testing & Cleanup (Priority: MEDIUM)
1. Test complete pipeline with new architecture
2. Remove legacy components and functions
3. Update documentation
4. Performance optimization

## 📊 Expected Benefits

### Developer Experience
- ✅ **50% Less Code**: Centralized API service reduces duplication
- ✅ **Cleaner Components**: Single hook replaces complex state management
- ✅ **Better Error Handling**: Standardized error patterns
- ✅ **Easier Testing**: Isolated, testable functions

### User Experience  
- ✅ **Real-Time Progress**: Database-driven progress tracking
- ✅ **Better Feedback**: Stage-specific progress details
- ✅ **Faster Loading**: Optimized API calls and caching
- ✅ **Error Recovery**: Better error messages and retry logic

### System Reliability
- ✅ **No More Polling Loops**: Clean polling with automatic cleanup
- ✅ **Consistent State**: Single source of truth for progress
- ✅ **Robust Error Handling**: Proper error boundaries and recovery
- ✅ **Performance**: Reduced unnecessary API calls

## 🚀 Next Steps

1. **Immediate (Today)**: Update CourseCreationPage with new hook
2. **This Week**: Modernize all stage components
3. **Next Week**: Add enhanced progress tracking
4. **Following Week**: Testing, cleanup, and optimization

## 📝 Notes

- **Backward Compatibility**: Migration preserves existing functionality
- **Incremental**: Can be done step-by-step without breaking changes
- **Testing**: Each phase can be tested independently
- **Rollback**: Original components can be kept as backup during migration

This migration transforms the frontend from a complex, polling-based system to a clean, modern React application that fully leverages our new Celery-based backend architecture. 