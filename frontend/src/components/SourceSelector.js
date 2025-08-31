import React from 'react';
import './SourceSelector.css';

const SourceSelector = ({ selectedSources, onSourceChange, onCategoryToggle }) => {
  const brokerResearchSources = {
    jefferies_research: 'Jefferies Research',
    ubs_research: 'UBS Research',
    haitong_research: 'Haitong International',
    nomura_research: 'Nomura Research',
    batlivala_karani: 'Batlivala & Karani',
    krc_research: 'KRC Research',
    smc_global: 'SMC Global',
    institutional_investor: 'Institutional Investor Advisory',
    financial_research: 'Financial Research'
  };

  const companyDocsSources = {
    presentations: 'Investor Presentations',
    major_filings: 'Major Filings & Disclosures',
    event_transcripts: 'Event Transcripts'
  };

  const handleCategoryChange = (category, enabled) => {
    onCategoryToggle(category, enabled);
  };

  const handleSubcategoryChange = (category, subcategory, enabled) => {
    onSourceChange(category, subcategory, enabled);
  };

  const getSelectedCount = (category) => {
    const subcategories = selectedSources[category]?.subcategories || {};
    return Object.values(subcategories).filter(Boolean).length;
  };

  const getTotalCount = (category) => {
    const subcategories = selectedSources[category]?.subcategories || {};
    return Object.keys(subcategories).length;
  };

  return (
    <div className="source-selector">
      <h2>Select Sources</h2>
      
      {/* Broker Research Section */}
      <div className="source-category">
        <div className="category-header">
          <label className="category-toggle">
            <input
              type="checkbox"
              checked={selectedSources.brokerResearch?.enabled || false}
              onChange={(e) => handleCategoryChange('brokerResearch', e.target.checked)}
            />
            <span className="category-title">
              Broker Research 
              <span className="count">({getSelectedCount('brokerResearch')}/{getTotalCount('brokerResearch')})</span>
            </span>
          </label>
        </div>
        
        {selectedSources.brokerResearch?.enabled && (
          <div className="subcategories">
            {Object.entries(brokerResearchSources).map(([key, label]) => (
              <label key={key} className="subcategory-item">
                <input
                  type="checkbox"
                  checked={selectedSources.brokerResearch?.subcategories?.[key] || false}
                  onChange={(e) => handleSubcategoryChange('brokerResearch', key, e.target.checked)}
                />
                <span className="subcategory-label">{label}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Company Documents Section */}
      <div className="source-category">
        <div className="category-header">
          <label className="category-toggle">
            <input
              type="checkbox"
              checked={selectedSources.companyDocs?.enabled || false}
              onChange={(e) => handleCategoryChange('companyDocs', e.target.checked)}
            />
            <span className="category-title">
              Company Documents 
              <span className="count">({getSelectedCount('companyDocs')}/{getTotalCount('companyDocs')})</span>
            </span>
          </label>
        </div>
        
        {selectedSources.companyDocs?.enabled && (
          <div className="subcategories">
            {Object.entries(companyDocsSources).map(([key, label]) => (
              <label key={key} className="subcategory-item">
                <input
                  type="checkbox"
                  checked={selectedSources.companyDocs?.subcategories?.[key] || false}
                  onChange={(e) => handleSubcategoryChange('companyDocs', key, e.target.checked)}
                />
                <span className="subcategory-label">{label}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Selection Summary */}
      <div className="selection-summary">
        <h3>Selection Summary</h3>
        <div className="summary-stats">
          <div className="stat">
            <span className="stat-label">Broker Research:</span>
            <span className="stat-value">
              {getSelectedCount('brokerResearch')} sources selected
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Company Docs:</span>
            <span className="stat-value">
              {getSelectedCount('companyDocs')} categories selected
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SourceSelector;