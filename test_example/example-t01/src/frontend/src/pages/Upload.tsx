import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload as UploadIcon, FileText, AlertCircle, Info, ArrowLeft } from 'lucide-react';
import { uploadDocument } from '../services/document.api';
import { showSuccess } from '../utils/toast';
import { getBrowserId } from '../utils/user';
import './Upload.css';

export const Upload = () => {
    const navigate = useNavigate();
    const [file, setFile] = useState<File | null>(null);
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            if (selectedFile.size > 10 * 1024 * 1024) {
                setErrorMessage('File size exceeds 10MB limit.');
                setStatus('error');
                return;
            }
            setFile(selectedFile);
            setStatus('idle');
            setErrorMessage('');
        }
    };

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const selectedFile = e.dataTransfer.files[0];
            if (selectedFile.size > 10 * 1024 * 1024) {
                setErrorMessage('File size exceeds 10MB limit.');
                setStatus('error');
                return;
            }
            setFile(selectedFile);
            setStatus('idle');
            setErrorMessage('');
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setStatus('uploading');
        setProgress(0);

        try {
            const userId = getBrowserId(); // Get session/browser ID
            await uploadDocument(file, (percent) => setProgress(percent), userId);
            setStatus('success');
            showSuccess('Document uploaded successfully!');

            setTimeout(() => {
                navigate('/documents');
            }, 1500);
        } catch (error: any) {
            setStatus('error');
            const detail = error.response?.data?.detail || 'Upload failed. Please try again.';
            setErrorMessage(detail);
        }
    };

    const resetSelection = () => {
        setFile(null);
        setStatus('idle');
    };

    return (
        <div className="upload-page-container">
            <div className="upload-page-header">
                <div className="upload-header-content">
                    <button onClick={() => navigate('/documents')} className="btn-icon">
                        <ArrowLeft size={24} />
                    </button>
                    <div>
                        <h1 className="upload-page-title">
                            Upload Document
                        </h1>
                        <p className="upload-page-subtitle">
                            Add a new file to your secure workspace
                        </p>
                    </div>
                </div>
            </div>

            <div className="upload-content-container">
                {!file ? (
                    <div
                        className={`drop-zone-premium ${status === 'error' ? 'error' : ''}`}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <input
                            type="file"
                            hidden
                            ref={fileInputRef}
                            onChange={handleFileChange}
                        />
                        <div className="icon-wrapper-premium">
                            <UploadIcon size={36} strokeWidth={2} />
                        </div>
                        <h3 className="upload-text-main">
                            Click to upload or drag and drop
                        </h3>
                        <p className="upload-text-sub">
                            Supports all file types (max. 10MB)
                        </p>
                    </div>
                ) : (
                    <div className="file-card-premium">
                        <div className="file-icon-large">
                            {file!.type.startsWith('image/') ? <FileText size={32} /> : <FileText size={32} />}
                        </div>

                        <h2 className="file-name">
                            {file!.name}
                        </h2>
                        <span className="file-size-badge">
                            {(file!.size / 1024 / 1024).toFixed(2)} MB
                        </span>

                        {status === 'uploading' && (
                            <div className="progress-container">
                                <div className="progress-bar-premium">
                                    <div className="progress-fill-premium" style={{ width: `${progress}%` }}></div>
                                </div>
                                <div className="progress-text-row">
                                    <span>Uploading...</span>
                                    <span>{progress}%</span>
                                </div>
                            </div>
                        )}

                        <div className="modal-actions">
                            <button
                                onClick={resetSelection}
                                className="btn btn-cancel"
                            >
                                Cancel
                            </button>
                            {status !== 'success' && (
                                <button
                                    onClick={handleUpload}
                                    disabled={status === 'uploading'}
                                    className="btn btn-upload"
                                >
                                    {status === 'uploading' ? 'Uploading...' : 'Submit'}
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* Footer Info */}
                {!file && (
                    <div className="upload-footer">
                        <p>
                            <Info size={16} />
                            Secure, private, and encrypted storage for all your business documents.
                        </p>
                    </div>
                )}

                {status === 'error' && errorMessage && (
                    <div className="error-message">
                        <AlertCircle size={20} />
                        {errorMessage}
                    </div>
                )}
            </div>
        </div>
    );
};
