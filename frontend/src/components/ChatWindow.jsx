import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

/**
 * Helper to get document icon based on extension.
 */
function getDocIcon(filename = '') {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return '📕';
  if (ext === 'md') return '📘';
  return '📄';
}

/**
 * Helper for score level and label.
 */
function getScoreBadge(score) {
  const pct = Math.round((score || 0) * 100);
  if (pct >= 80) return { pct, label: 'High Match', className: 'score-badge--high' };
  if (pct >= 60) return { pct, label: 'Relevant', className: 'score-badge--med' };
  return { pct, label: 'Context', className: 'score-badge--low' };
}

/**
 * EvidenceCard — Renders detailed excerpt for an individual source.
 */
function EvidenceCard({ source, index, isSelected }) {
  const [copied, setCopied] = useState(false);
  const badge = getScoreBadge(source.score);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(source.snippet || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore clipboard fallback
    }
  };

  return (
    <div className={`evidence-card ${isSelected ? 'evidence-card--selected' : ''}`}>
      <div className="evidence-card__header">
        <div className="evidence-card__title-group">
          <span className="evidence-card__index">[{index + 1}]</span>
          <span className="evidence-card__icon">{getDocIcon(source.document)}</span>
          <span className="evidence-card__doc">{source.document}</span>
          {source.section && (
            <span className="evidence-card__section">§ {source.section}</span>
          )}
        </div>
        <div className="evidence-card__actions">
          <span className={`score-badge ${badge.className}`}>
            <span className="score-badge__dot" />
            <span className="score-badge__text">{badge.pct}% • {badge.label}</span>
          </span>
          <button
            type="button"
            className="evidence-card__copy-btn"
            onClick={handleCopy}
            title="Copy excerpt text"
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        </div>
      </div>
      <div className="evidence-card__body">
        <blockquote className="evidence-card__quote">
          {source.snippet}
        </blockquote>
      </div>
    </div>
  );
}

/**
 * SourceEvidencePanel — Modern, intuitive source inspection with quick-select pills & expandable drawer.
 */
function SourceEvidencePanel({ sources }) {
  const [isOpen, setIsOpen] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-panel">
      {/* Header bar with toggle */}
      <div className="sources-panel__header" onClick={() => setIsOpen(!isOpen)}>
        <div className="sources-panel__title-group">
          <span className="sources-panel__icon">📚</span>
          <span className="sources-panel__title">
            Grounded on {sources.length} {sources.length === 1 ? 'Source' : 'Sources'}
          </span>
        </div>
        <button
          type="button"
          className="sources-panel__toggle"
          aria-expanded={isOpen}
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(!isOpen);
          }}
        >
          {isOpen ? 'Hide Evidence ▲' : 'Inspect Evidence ▼'}
        </button>
      </div>

      {/* Quick-Access Horizontal Pills */}
      <div className="sources-pills">
        {sources.map((src, i) => {
          const badge = getScoreBadge(src.score);
          const isSelected = selectedIdx === i;
          return (
            <button
              key={i}
              type="button"
              className={`source-pill ${isSelected ? 'source-pill--active' : ''}`}
              onClick={() => {
                setIsOpen(true);
                setSelectedIdx(selectedIdx === i ? null : i);
              }}
              title={`Click to focus citation [${i + 1}]: ${src.document}`}
            >
              <span className="source-pill__num">[{i + 1}]</span>
              <span className="source-pill__icon">{getDocIcon(src.document)}</span>
              <span className="source-pill__name">{src.document}</span>
              <span className={`source-pill__badge ${badge.className}`}>
                {badge.pct}%
              </span>
            </button>
          );
        })}
      </div>

      {/* Expandable Evidence Drawer */}
      {isOpen && (
        <div className="sources-panel__drawer">
          {sources.map((src, i) => (
            <EvidenceCard
              key={i}
              source={src}
              index={i}
              isSelected={selectedIdx === i}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * AgentTraceBadge — Visual step-by-step trace of the LangGraph agent flow.
 */
function AgentTraceBadge({ steps, score }) {
  if (!steps || steps.length === 0) return null;

  const stepInfo = {
    retrieve: { icon: '🔍', label: 'Retrieve' },
    grade_relevance: { icon: '⚖️', label: 'Grade Relevance' },
    generate: { icon: '✨', label: 'Generate' },
    cite_and_format: { icon: '📑', label: 'Cite & Format' },
    no_answer_fallback: { icon: '🛡️', label: 'Relevance Guard' },
  };

  return (
    <div className="agent-trace">
      <div className="agent-trace__tag">
        <span className="agent-trace__pulse" />
        <span>LangGraph Agent</span>
      </div>
      <div className="agent-trace__flow">
        {steps.map((st, i) => {
          const info = stepInfo[st] || { icon: '•', label: st };
          return (
            <span key={i} className="agent-trace__node">
              <span className="agent-trace__node-icon">{info.icon}</span>
              <span className="agent-trace__node-label">{info.label}</span>
              {i < steps.length - 1 && (
                <span className="agent-trace__arrow">→</span>
              )}
            </span>
          );
        })}
      </div>
      {score !== null && score !== undefined && score > 0 && (
        <span className="agent-trace__score">
          Score: {Math.round(score * 100)}%
        </span>
      )}
    </div>
  );
}

/**
 * MessageBubble — Renders formatted markdown for bot with intuitive evidence panel.
 */
function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message message--${isUser ? 'user' : 'bot'}`}>
      <div className="message__avatar">
        {isUser ? '👤' : '🧠'}
      </div>
      <div className="message__content">
        {/* Agent Workflow Execution Trace */}
        {!isUser && message.workflow_steps && message.workflow_steps.length > 0 && (
          <AgentTraceBadge
            steps={message.workflow_steps}
            score={message.relevance_score}
          />
        )}

        <div className={`message__bubble ${isUser ? 'message__bubble--user' : 'message__bubble--bot'}`}>
          {isUser ? (
            <div className="message__text-user">{message.text}</div>
          ) : (
            <div className="message__markdown">
              <ReactMarkdown>{message.text}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Intuitive Grounded Sources & Evidence */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourceEvidencePanel sources={message.sources} />
        )}
      </div>
    </div>
  );
}

/**
 * TypingIndicator — Bouncing dots shown while the bot is generating a response.
 */
function TypingIndicator() {
  return (
    <div className="message message--bot">
      <div className="message__avatar">🧠</div>
      <div className="message__content">
        <div className="message__bubble message__bubble--bot">
          <div className="typing-indicator">
            <div className="typing-indicator__dot" />
            <div className="typing-indicator__dot" />
            <div className="typing-indicator__dot" />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ChatWindow — Main chat area with message history, input, and suggestions.
 */
export default function ChatWindow({ messages, onSendMessage, isLoading }) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const suggestions = [
    "How many casual leaves am I entitled to per year?",
    "What is the password policy?",
    "Can I work from home on Fridays?",
    "What's the travel reimbursement process?",
    "What is the probation period for new employees?",
    "What is the dress code policy?",
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleSuggestionClick = (suggestion) => {
    onSendMessage(suggestion);
  };

  // Auto-scroll on new messages or loading state
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="chat-welcome__icon">🧠</div>
            <h2 className="chat-welcome__title">Knowledge Assistant</h2>
            <p className="chat-welcome__desc">
              Ask me anything about company policies, procedures, and guidelines.
              I'll search through the uploaded documents and provide answers with
              source citations.
            </p>
            <div className="chat-welcome__suggestions">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  className="suggestion-chip"
                  onClick={() => handleSuggestionClick(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}
            {isLoading && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="chat-input-container">
        <form className="chat-input-wrapper" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="Ask a question about company documents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!input.trim() || isLoading}
            title="Send message"
          >
            ➤
          </button>
        </form>
        <div className="chat-input-hint">
          Answers are grounded in uploaded documents with source citations
        </div>
      </div>
    </div>
  );
}
