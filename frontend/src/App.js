import React, { useState } from 'react';
import './App.css';
import QueryInterface from './components/QueryInterface';
import SourceSelector from './components/SourceSelector';
import ResponseDisplay from './components/ResponseDisplay';

function App() {
  const [selectedSources, setSelectedSources] = useState({
    brokerResearch: {
      enabled: true,
      subcategories: {
        jefferies_research: true,
        ubs_research: true,
        haitong_research: true,
        nomura_research: true,
        batlivala_karani: true,
        krc_research: true,
        smc_global: true,
        institutional_investor: true,
        financial_research: false
      }
    },
    companyDocs: {
      enabled: true,
      subcategories: {
        presentations: true,
        major_filings: true,
        event_transcripts: true
      }
    }
  });

  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pastQuestions, setPastQuestions] = useState([]);
  const [enableWebSearch, setEnableWebSearch] = useState(false);

  const handleSourceChange = (category, subcategory, enabled) => {
    setSelectedSources(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        subcategories: {
          ...prev[category].subcategories,
          [subcategory]: enabled
        }
      }
    }));
  };

  const handleCategoryToggle = (category, enabled) => {
    setSelectedSources(prev => {
      const subcategories = prev[category]?.subcategories || {};
      const updatedSubcategories = {};
      
      // Set all subcategories to the same value as the main category
      Object.keys(subcategories).forEach(key => {
        updatedSubcategories[key] = enabled;
      });

      return {
        ...prev,
        [category]: {
          ...prev[category],
          enabled: enabled,
          subcategories: updatedSubcategories
        }
      };
    });
  };

  const handleQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a question');
      return;
    }

    // Add current question to past questions
    const questionObj = {
      question: query,
      timestamp: new Date().toISOString(),
      sources: selectedSources
    };
    
    setPastQuestions(prev => [...prev, questionObj]);

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const response = await fetch('http://localhost:8000/api/comprehensive-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topic: query,
          sources: selectedSources,
          enable_web_search: enableWebSearch,
          domain_context: "financial analysis"
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResponse(data);
    } catch (error) {
      console.error('Error querying documents:', error);
      setError('Failed to get response. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  const clearResponse = () => {
    setResponse(null);
    setError(null);
  };

  return (
    <div className="App">
      <div className="container">
        <header className="app-header">
          <h1>BetaSense Report Generator</h1>
          <p className="subtitle">Generate comprehensive financial reports with structured analysis</p>
        </header>

        <div className="main-content">
          <div className="left-panel">
            <SourceSelector 
              selectedSources={selectedSources}
              onSourceChange={handleSourceChange}
              onCategoryToggle={handleCategoryToggle}
            />
          </div>

          <div className="right-panel">
            <QueryInterface 
              query={query}
              onQueryChange={setQuery}
              onSubmit={handleQuery}
              loading={loading}
              onClear={clearResponse}
              pastQuestions={pastQuestions}
              enableWebSearch={enableWebSearch}
              onWebSearchToggle={setEnableWebSearch}
            />
            
            {error && (
              <div className="error-message">
                <p>{error}</p>
              </div>
            )}

            <ResponseDisplay 
              response={response}
              loading={loading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
