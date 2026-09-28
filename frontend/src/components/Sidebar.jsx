import { useState, useRef, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

/**
 * Sidebar — Document upload panel and document list.
 */
export default function Sidebar({ documents, onDocumentsChange, onToast }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadingName, setUploadingName] = useState('');
  const fileInputRef = useRef(null);

  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunk_count, 0);

  const handleUpload = useCallback(async (file) => {
    if (!file) return;

    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'txt', 'md'].includes(ext)) {
      onToast('Unsupported file type. Please upload PDF, TXT, or MD files.', 'error');
      return;
    }

    setIsUploading(true);
    setUploadingName(file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const result = await response.json();
      onToast(`✅ ${result.filename} uploaded (${result.chunks_created} chunks)`, 'success');
      onDocumentsChange(); // Refresh the document list
    } catch (err) {
      onToast(`❌ Failed to upload: ${err.message}`, 'error');
    } finally {
      setIsUploading(false);
      setUploadingName('');
    }
  }, [onDocumentsChange, onToast]);

  const handleDelete = useCallback(async (filename) => {
    try {
      const response = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Delete failed');
      }

      onToast(`🗑️ ${filename} removed`, 'info');
      onDocumentsChange();
    } catch (err) {
      onToast(`❌ Failed to delete: ${err.message}`, 'error');
    }
  }, [onDocumentsChange, onToast]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) handleUpload(file);
    // Reset input so the same file can be selected again
    e.target.value = '';
  };

  const getDocIcon = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    if (ext === 'pdf') return '📕';
    if (ext === 'md') return '📘';
    return '📄';
  };

  return (
    <aside className="sidebar">
      <div className="sidebar__header">
        <h2 className="sidebar__title">📚 Knowledge Base</h2>
        <p className="sidebar__count">
          {documents.length} document{documents.length !== 1 ? 's' : ''} · {totalChunks} chunks
        </p>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone ${isDragging ? 'upload-zone--active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="upload-zone__icon">📤</div>
        <div className="upload-zone__text">
          <strong>Drop files here</strong> or click to browse
        </div>
        <div className="upload-zone__formats">PDF, TXT, MD</div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={handleFileSelect}
        />
      </div>

      {/* Upload Progress */}
      {isUploading && (
        <div className="upload-progress">
          <div className="spinner" />
          Uploading {uploadingName}...
        </div>
      )}

      {/* Document List */}
      <div className="doc-list">
        {documents.map((doc) => (
          <div key={doc.filename} className="doc-item">
            <div className="doc-item__icon">{getDocIcon(doc.filename)}</div>
            <div className="doc-item__info">
              <div className="doc-item__name" title={doc.filename}>
                {doc.filename}
              </div>
              <div className="doc-item__chunks">
                {doc.chunk_count} chunk{doc.chunk_count !== 1 ? 's' : ''}
              </div>
            </div>
            <button
              className="doc-item__delete"
              onClick={() => handleDelete(doc.filename)}
              title="Remove document"
            >
              ✕
            </button>
          </div>
        ))}

        {documents.length === 0 && !isUploading && (
          <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)', padding: 'var(--space-lg)' }}>
            No documents yet. Upload some to get started!
          </p>
        )}
      </div>
    </aside>
  );
}
