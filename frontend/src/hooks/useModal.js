import { useState } from 'react';

export const useModal = () => {
  const [alertModal, setAlertModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    type: 'info',
    buttonText: 'OK'
  });

  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    type: 'default',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    onConfirm: () => {},
    isLoading: false
  });

  const showAlert = ({
    title = 'Alert',
    message = 'Something happened.',
    type = 'info',
    buttonText = 'OK'
  }) => {
    setAlertModal({
      isOpen: true,
      title,
      message,
      type,
      buttonText
    });
  };

  const showConfirm = ({
    title = 'Confirm Action',
    message = 'Are you sure you want to proceed?',
    type = 'default',
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    onConfirm = () => {}
  }) => {
    setConfirmModal({
      isOpen: true,
      title,
      message,
      type,
      confirmText,
      cancelText,
      onConfirm,
      isLoading: false
    });
  };

  const closeAlert = () => {
    setAlertModal(prev => ({ ...prev, isOpen: false }));
  };

  const closeConfirm = () => {
    setConfirmModal(prev => ({ ...prev, isOpen: false }));
  };

  const setConfirmLoading = (isLoading) => {
    setConfirmModal(prev => ({ ...prev, isLoading }));
  };

  // Convenience methods for common use cases
  const showError = (message, title = 'Error') => {
    showAlert({ title, message, type: 'error' });
  };

  const showSuccess = (message, title = 'Success') => {
    showAlert({ title, message, type: 'success' });
  };

  const showWarning = (message, title = 'Warning') => {
    showAlert({ title, message, type: 'warning' });
  };

  const showInfo = (message, title = 'Info') => {
    showAlert({ title, message, type: 'info' });
  };

  const showDeleteConfirm = (message, onConfirm, title = 'Delete Confirmation') => {
    showConfirm({
      title,
      message,
      type: 'danger',
      confirmText: 'Delete',
      cancelText: 'Cancel',
      onConfirm
    });
  };

  return {
    // Alert modal state and controls
    alertModal,
    showAlert,
    closeAlert,
    
    // Confirm modal state and controls
    confirmModal,
    showConfirm,
    closeConfirm,
    setConfirmLoading,
    
    // Convenience methods
    showError,
    showSuccess,
    showWarning,
    showInfo,
    showDeleteConfirm
  };
}; 