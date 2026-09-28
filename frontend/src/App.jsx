import { useState, useEffect, useCallback } from 'react';
import ChatWindow from './components/ChatWindow';
import Sidebar from './components/Sidebar';
import './index.css';

const API_BASE = 'http://localhost:8000';

/**
 * Toast notification component.
 */
function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast--${toast.type}`}
          onClick={() => onDismiss(toast.id)}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
}

/**
 * App — Root component that orchestrates the chat and sidebar.
 */
export default function App() {
  const [messages, setMessages] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOllamaOnline, setIsOllamaOnline] = useState(false);
  const [toasts, setToasts] = useState([]);

  // Fetch the document list from the backend
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents);
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    }
  }, []);

  // Check backend health
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        setIsOllamaOnline(data.ollama_connected);
      }
    } catch (err) {
      setIsOllamaOnline(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchDocuments();
    checkHealth();
    // Poll health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchDocuments, checkHealth]);

  // Toast management
  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Send a question to the backend
  const handleSendMessage = useCallback(async (text) => {
    // Add user message
    const userMessage = { role: 'user', text, sources: [] };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: text }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Request failed');
      }

      const data = await res.json();

      const botMessage = {
        role: 'bot',
        text: data.answer,
        sources: data.sources || [],
        is_grounded: data.is_grounded,
        workflow_steps: data.workflow_steps || null,
        relevance_score: data.relevance_score || null,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      const errorMessage = {
        role: 'bot',
        text: `Sorry, an error occurred: ${err.message}. Please make sure the backend server and Ollama are running.`,
        sources: [],
        is_grounded: false,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="app-header__brand">
          <div className="app-header__icon">🧠</div>
          <div>
            <div className="app-header__title">Knowledge Assistant</div>
            <div className="app-header__subtitle">
              RAG-Powered Enterprise Document Q&A
            </div>
          </div>
        </div>
        <div className="app-header__status">
          <span
            className={`status-dot ${isOllamaOnline ? 'status-dot--online' : 'status-dot--offline'}`}
          />
          {isOllamaOnline ? 'Ollama Connected' : 'Ollama Offline'}
        </div>
      </header>

      {/* Main Layout */}
      <main className="app-main">
        <Sidebar
          documents={documents}
          onDocumentsChange={fetchDocuments}
          onToast={addToast}
        />
        <ChatWindow
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
        />
      </main>

      {/* Toast Notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
