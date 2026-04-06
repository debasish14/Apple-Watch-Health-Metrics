import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';

const UploadZone = ({ onUploadSuccess }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleUpload(files[0]);
        }
    };

    const handleFileSelect = (e) => {
        if (e.target.files.length > 0) {
            handleUpload(e.target.files[0]);
        }
    };

    const handleUpload = async (file) => {
        setUploading(true);
        setError(null);
        setSuccess(false);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();
            setSuccess(true);
            if (onUploadSuccess) onUploadSuccess(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div
            className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors cursor-pointer ${isDragging ? 'border-primary bg-primary/10' : 'border-border hover:border-primary/50'
                }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('fileInput').click()}
        >
            <input
                type="file"
                id="fileInput"
                className="hidden"
                accept=".xml"
                onChange={handleFileSelect}
            />

            <div className="flex flex-col items-center gap-4">
                {uploading ? (
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                ) : success ? (
                    <CheckCircle className="h-12 w-12 text-green-500" />
                ) : error ? (
                    <AlertCircle className="h-12 w-12 text-destructive" />
                ) : (
                    <Upload className="h-12 w-12 text-muted-foreground" />
                )}

                <div className="space-y-1">
                    <h3 className="font-semibold text-lg">
                        {uploading ? 'Processing...' : success ? 'Upload Complete!' : error ? 'Upload Failed' : 'Upload Health Data'}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        {error ? error : "Drag & drop your export.xml here, or click to select"}
                    </p>
                </div>
            </div>
        </div>
    );
};

export default UploadZone;
