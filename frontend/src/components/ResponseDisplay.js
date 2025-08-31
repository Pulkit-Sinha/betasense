import React from 'react';
import './ResponseDisplay.css';

const ResponseDisplay = ({ response, loading }) => {
  if (loading) {
    return (
      <div className="response-display">
        <div className="loading-container">
          <div className="loading-animation">
            <div className="loading-dots">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
            </div>
            <p>Analyzing documents and generating response...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="response-display">
        <div className="empty-state">
          <div className="empty-icon">📄</div>
          <h3>Ready to Answer Your Questions</h3>
          <p>Select your sources and ask a question to get started. I'll analyze the documents and provide detailed insights.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="response-display">
      <div className="response-header">
        <h2>Analysis Results</h2>
        <div className="response-meta">
          <span className="timestamp">Generated on {new Date().toLocaleString()}</span>
        </div>
      </div>

      <div className="response-content">
        {/* Main Answer */}
        <div className="answer-section">
          <h3>Answer</h3>
          <div className="answer-text">
            {response.answer || "I'll provide a comprehensive answer based on the selected documents once the backend is connected."}
          </div>
        </div>

        {/* Sources Used */}
        {response.sources && response.sources.length > 0 && (
          <div className="sources-section">
            <h3>Sources Referenced</h3>
            <div className="sources-list">
              {response.sources.map((source, index) => (
                <div key={index} className="source-item">
                  <div className="source-header">
                    <span className="source-title">{source.title || `Document ${index + 1}`}</span>
                    <span className="source-type">{source.type || 'Unknown Type'}</span>
                  </div>
                  {source.excerpt && (
                    <div className="source-excerpt">
                      "{source.excerpt}"
                    </div>
                  )}
                  {source.relevance && (
                    <div className="source-relevance">
                      Relevance: {(source.relevance * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Key Insights */}
        {response.insights && response.insights.length > 0 && (
          <div className="insights-section">
            <h3>Key Insights</h3>
            <div className="insights-list">
              {response.insights.map((insight, index) => (
                <div key={index} className="insight-item">
                  <div className="insight-bullet">•</div>
                  <div className="insight-text">{insight}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Confidence Score */}
        {response.confidence && (
          <div className="confidence-section">
            <h3>Confidence Level</h3>
            <div className="confidence-bar">
              <div 
                className="confidence-fill" 
                style={{ width: `${response.confidence * 100}%` }}
              ></div>
            </div>
            <span className="confidence-text">
              {(response.confidence * 100).toFixed(1)}% confidence based on available documents
            </span>
          </div>
        )}
      </div>

      {/* Mock Response for Demo */}
      {!response.answer && (
        <div className="demo-response">
          <div className="answer-section">
            <h3>Demo Answer</h3>
            <div className="answer-text">
              This is a demo response. Based on the selected sources, I would analyze documents from:
              <ul>
                <li>Jefferies Research reports on Jio Financial Services</li>
                <li>UBS sector analysis and fast takes</li>
                <li>Company investor presentations and filings</li>
              </ul>
              The actual response would provide detailed insights from these documents once the backend integration is complete.
            </div>
          </div>

          <div className="sources-section">
            <h3>Example Sources</h3>
            <div className="sources-list">
              <div className="source-item">
                <div className="source-header">
                  <span className="source-title">Jefferies - Key Takeaways from Jio's FY25 Annual Report</span>
                  <span className="source-type">Broker Research</span>
                </div>
                <div className="source-excerpt">
                  "Jio remains focused on driving 5G, growing home broadband and scaling its enterprise offerings..."
                </div>
              </div>
              <div className="source-item">
                <div className="source-header">
                  <span className="source-title">UBS Fast Take - India Telecom Sector</span>
                  <span className="source-type">Broker Research</span>
                </div>
                <div className="source-excerpt">
                  "Jio has removed its Rs249 plan (1GB/day, 28 days). Positive for ARPU, expect Airtel, VIL to follow..."
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResponseDisplay;