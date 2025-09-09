import React from 'react';
import './QueryInterface.css';

const QueryInterface = ({ query, onQueryChange, onSubmit, loading, onClear, pastQuestions = [], enableWebSearch, onWebSearchToggle }) => {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!loading && query.trim()) {
      onSubmit();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit(e);
    }
  };

  const handlePastQuestionClick = (question) => {
    onQueryChange(question);
  };

  return (
    <div className="query-interface">
      <div className="query-section">
        <h2>Generate Comprehensive Report</h2>
        <form onSubmit={handleSubmit} className="query-form">
          <div className="textarea-container">
            <textarea
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter your research topic for comprehensive report generation... (Ctrl+Enter to submit)"
              className="query-textarea"
              rows={4}
              disabled={loading}
            />
            <div className="textarea-footer">
              <span className="char-count">{query.length} characters</span>
              <span className="shortcut-hint">Ctrl+Enter to submit</span>
            </div>
          </div>
          
          <div className="options-section">
            <label className="websearch-toggle">
              <input
                type="checkbox"
                checked={enableWebSearch}
                onChange={(e) => onWebSearchToggle(e.target.checked)}
                disabled={loading}
              />
              <span className="toggle-text">Enable Web Search</span>
            </label>
          </div>
          
          <div className="button-group">
            <button 
              type="submit" 
              className="submit-btn"
              disabled={loading || !query.trim()}
            >
              {loading ? (
                <>
                  <span className="loading-spinner"></span>
                  Generating Report...
                </>
              ) : (
                'Generate Report'
              )}
            </button>
            
            <button 
              type="button" 
              className="clear-btn"
              onClick={onClear}
              disabled={loading}
            >
              Clear
            </button>
          </div>
        </form>
      </div>

      {/* Past Questions */}
      {pastQuestions.length > 0 && (
        <div className="past-questions-section">
          <h3>Recent Questions</h3>
          <div className="past-questions-grid">
            {pastQuestions.slice(-5).reverse().map((pastQuestion, index) => (
              <div 
                key={index} 
                className="past-question-item"
                onClick={() => handlePastQuestionClick(pastQuestion.question)}
              >
                <div className="past-question-content">
                  <span className="past-question-text">{pastQuestion.question}</span>
                  <span className="past-question-timestamp">
                    {new Date(pastQuestion.timestamp).toLocaleDateString()}
                  </span>
                </div>
                <span className="click-hint">Click to reuse</span>
              </div>
            ))}
          </div>
          {pastQuestions.length > 5 && (
            <div className="past-questions-footer">
              <span className="more-questions-hint">
                Showing last 5 questions ({pastQuestions.length} total)
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default QueryInterface;