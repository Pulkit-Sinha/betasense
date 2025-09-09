import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import './ResponseDisplay.css';

const ResponseDisplay = ({ response, loading }) => {
  // Function to parse and create citation links
  const createCitationLink = (citationText) => {
    // Extract filename from citation like "[Source: filename.pdf]"
    const match = citationText.match(/\[Source:\s*([^\]]+)\]/);
    if (match) {
      const filename = match[1].trim();
      // Convert filename to URL path (handle spaces and special characters)  
      const urlPath = encodeURIComponent(filename);
      const pdfUrl = `http://localhost:8000/api/pdf/${urlPath}`;
      
      // Extract a clean display name from filename
      const displayName = filename.replace(/\.pdf$/i, '')
        .replace(/^\d{8}\s*-\s*/, '') // Remove date prefix
        .replace(/\s*-\s*\d+\s*pages?$/i, ''); // Remove page count suffix
      
      return (
        <a 
          href={pdfUrl} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="citation-link"
          title={`Open ${filename} in new tab`}
          onClick={(e) => {
            // Optional: Add analytics tracking
            console.log('Citation clicked:', filename);
          }}
        >
          📄 {displayName}
        </a>
      );
    }
    return citationText;
  };

  // Function to create citation link markup that ReactMarkdown can render
  const createCitationMarkup = (citationText) => {
    const match = citationText.match(/\[Source:\s*([^\]]+)\]/);
    if (match) {
      const filename = match[1].trim();
      const urlPath = encodeURIComponent(filename);
      const pdfUrl = `http://localhost:8000/api/pdf/${urlPath}`;
      
      // Extract a clean display name from filename
      const displayName = filename.replace(/\.pdf$/i, '')
        .replace(/^\d{8}\s*-\s*/, '') // Remove date prefix
        .replace(/\s*-\s*\d+\s*pages?$/i, ''); // Remove page count suffix
      
      // Return HTML markup that ReactMarkdown can process
      return `<a href="${pdfUrl}" target="_blank" rel="noopener noreferrer" class="citation-link" title="Open ${filename} in new tab">📄 ${displayName}</a>`;
    }
    return citationText;
  };

  // Function to preprocess markdown content and convert citations to HTML links
  const preprocessContentForCitations = (content) => {
    if (typeof content !== 'string') return content;
    
    // Replace all citations with HTML link markup
    const citationRegex = /\[Source:[^\]]+\]/g;
    return content.replace(citationRegex, (match) => {
      return createCitationMarkup(match);
    });
  };

  // Custom markdown components (citations now handled at preprocessing level)
  const markdownComponents = {
    h1: ({children}) => <h1 className="markdown-h1">{children}</h1>,
    h2: ({children}) => <h2 className="markdown-h2">{children}</h2>,
    h3: ({children}) => <h3 className="markdown-h3">{children}</h3>,
    h4: ({children}) => <h4 className="markdown-h4">{children}</h4>,
    p: ({children}) => <p className="markdown-p">{children}</p>,
    ul: ({children}) => <ul className="markdown-ul">{children}</ul>,
    ol: ({children}) => <ol className="markdown-ol">{children}</ol>,
    li: ({children}) => <li className="markdown-li">{children}</li>,
    strong: ({children}) => <strong className="markdown-strong">{children}</strong>,
    em: ({children}) => <em className="markdown-em">{children}</em>,
    blockquote: ({children}) => <blockquote className="markdown-blockquote">{children}</blockquote>,
    code: ({children}) => <code className="markdown-code">{children}</code>,
  };
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
            <p>Generating comprehensive report...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="response-display">
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <h3>Ready to Generate Reports</h3>
          <p>Select your sources and enter a research topic to generate a comprehensive structured report with detailed analysis.</p>
        </div>
      </div>
    );
  }

  // Check if this is a comprehensive report response
  const isComprehensiveReport = response.report && response.report.structure;
  
  if (isComprehensiveReport) {
    return (
      <div className="response-display">
        <div className="response-header">
          <h2>📊 Comprehensive Report</h2>
          <div className="response-meta">
            <span className="timestamp">Generated on {new Date().toLocaleString()}</span>
            <span className="report-stats">
              {response.report.metadata?.total_sections || 0} sections • 
              {response.report.metadata?.estimated_pages || 0} pages • 
              {response.report.metadata?.sources_count || 0} sources
            </span>
          </div>
        </div>

        <div className="response-content">
          {/* Report Title */}
          <div className="report-title-section">
            <h1>{response.report.structure.title}</h1>
          </div>

          {/* Report Sections */}
          {response.report.structure.sections.map((section, index) => (
            <div key={index} className="report-section">
              <div className="section-header">
                <h2>{section.title}</h2>
                <span className="section-meta">
                  ~{section.estimated_pages} pages • {section.key_topics?.length || 0} key topics
                </span>
              </div>
              
              <div className="section-content">
                {response.report.sections && response.report.sections[section.title] ? (
                  <div className="section-text">
                    <ReactMarkdown 
                      components={markdownComponents}
                      // Allow HTML so we can render citation links
                      remarkPlugins={[]}
                      rehypePlugins={[rehypeRaw]}
                    >
                      {preprocessContentForCitations(response.report.sections[section.title])}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div className="section-placeholder">
                    <p><strong>Section Description:</strong> {section.description}</p>
                    <div className="key-topics">
                      <strong>Key Topics:</strong>
                      <ul>
                        {section.key_topics?.map((topic, tIndex) => (
                          <li key={tIndex}>{topic}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Sources Used */}
          {response.report.sources_used && response.report.sources_used.length > 0 && (
            <div className="sources-section">
              <h3>📚 Sources Referenced</h3>
              <div className="sources-list">
                {response.report.sources_used.slice(0, 10).map((source, index) => (
                  <div key={index} className="source-item">
                    <div className="source-header">
                      <span className="source-title">{source.file || `Source ${index + 1}`}</span>
                      <span className="source-type">{source.search_type || 'Document'}</span>
                    </div>
                    <div className="source-score">
                      Score: {source.score?.toFixed(3) || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
              {response.report.sources_used.length > 10 && (
                <p className="sources-more">
                  ... and {response.report.sources_used.length - 10} more sources
                </p>
              )}
            </div>
          )}

          {/* Web Results if available */}
          {response.report.web_results && response.report.web_results.length > 0 && (
            <div className="web-sources-section">
              <h3>🌐 Web Sources</h3>
              <div className="sources-list">
                {response.report.web_results.slice(0, 5).map((source, index) => (
                  <div key={index} className="source-item">
                    <div className="source-header">
                      <span className="source-title">{source.title || 'Web Source'}</span>
                      <a href={source.url} target="_blank" rel="noopener noreferrer" className="source-link">
                        🔗
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Fallback for old response format
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
            <ReactMarkdown 
              components={markdownComponents}
              remarkPlugins={[]}
              rehypePlugins={[rehypeRaw]}
            >
              {preprocessContentForCitations(response.answer || "I'll provide a comprehensive answer based on the selected documents once the backend is connected.")}
            </ReactMarkdown>
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