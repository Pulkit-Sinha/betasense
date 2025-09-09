// Test citation processing logic
const testText = "Core Subsidiaries: Reliance Industrial Investments and Holdings Limited, Jio Credit Limited, Jio Insurance Broking Limited, Jio Payment Solutions Limited, Jio Leasing Services Limited, and Jio Finance Platform and Service Limited [Source: 20250717 - INTRM - 543940_IN - Independent Auditors Review Report - 11 pages.pdf]";

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

console.log('Original text:');
console.log(testText);
console.log('\nProcessed text:');
console.log(preprocessContentForCitations(testText));