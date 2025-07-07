import React from 'react';
import AlertModal from './AlertModal';
import ConfirmModal from './ConfirmModal';

const ModalProvider = ({ 
  alertModal, 
  onCloseAlert, 
  confirmModal, 
  onCloseConfirm, 
  onConfirm 
}) => {
  return (
    <>
      <AlertModal
        isOpen={alertModal.isOpen}
        onClose={onCloseAlert}
        title={alertModal.title}
        message={alertModal.message}
        type={alertModal.type}
        buttonText={alertModal.buttonText}
      />
      
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        onClose={onCloseConfirm}
        onConfirm={onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        type={confirmModal.type}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        isLoading={confirmModal.isLoading}
      />
    </>
  );
};

export default ModalProvider; 