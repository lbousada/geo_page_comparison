// Enhanced Screaming Frog Recipe: Semantic Chunking + OpenAI Embeddings
//
// This script breaks webpage content into semantic passages (paragraphs, headings,
// list items, etc.) and embeds each chunk using OpenAI's text-embedding-3-small model.
//
// SETUP REQUIRED:
// 1. Replace 'YOUR_OPENAI_API_KEY_HERE' below with your actual API key.
// 2. The token will be stored in your SEO Spider configuration - be mindful when sharing.
//
// MODEL INFO:
// - Model: text-embedding-3-small (1536 dimensions)
// - Context Length: Up to 8191 tokens
//

// Configuration variables
const OPENAI_API_KEY = '<key>';
const MODEL_NAME = 'text-embedding-3-small';

// Create a client class to handle OpenAI API interaction
class OpenAIClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
  }

  async getEmbeddings(options) {
    const url = 'https://api.openai.com/v1/embeddings';
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input: options.inputs, // OpenAI natively accepts a string or an array of strings
        model: options.model,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`OpenAI API error (${response.status}): ${errorText}`);
    }

    const json = await response.json();
    
    // OpenAI returns data array ordered by input index: [{ embedding: [...] }, ...]
    // Map it to return a direct array of embedding vectors to match original logic
    return json.data.map(item => item.embedding);
  }
}

// Initialize the client
const aiClient = new OpenAIClient(OPENAI_API_KEY);

// Configuration
const CONFIG = {
  minChunkLength: 50,    // Minimum characters per chunk
  maxChunkLength: 1500,  // Maximum characters per chunk (increased safely for OpenAI)
  includeMetadata: true, // Include element type and position info
  batchSize: 16,         // OpenAI handles larger batch sizes comfortably
  retryAttempts: 3,      // Retry failed requests
  retryDelay: 1000,      // Delay between retries (ms)
};

/**
 * Extract semantic passages from the webpage DOM
 * @returns {Array} Array of chunk objects with text and metadata
 */
function extractSemanticChunks() {
  const chunks = [];
  let chunkIndex = 0;

  // Define semantic elements to extract
  const semanticSelectors = [
    'h1, h2, h3, h4, h5, h6', // Headings
    'p', // Paragraphs
    'li', // List items
    'blockquote', // Quotes
    'article', // Articles
    'section', // Sections
    'div[role="main"]', // Main content areas
    'td, th', // Table cells
    'figcaption', // Figure captions
    'summary', // Summary elements
    'dd', // Definition descriptions
  ];

  semanticSelectors.forEach((selector) => {
    const elements = document.querySelectorAll(selector);

    elements.forEach((element, index) => {
      const text = element.textContent?.trim();

      if (text && text.length >= CONFIG.minChunkLength) {
        // Split long chunks while preserving sentence boundaries
        const textChunks = splitLongText(text, CONFIG.maxChunkLength);

        textChunks.forEach((chunkText, subIndex) => {
          const chunk = {
            text: chunkText,
            index: chunkIndex++,
            metadata: CONFIG.includeMetadata
              ? {
                  elementType: element.tagName.toLowerCase(),
                  elementIndex: index,
                  subChunkIndex: subIndex,
                  totalSubChunks: textChunks.length,
                  xpath: getXPath(element),
                  textLength: chunkText.length,
                }
              : null,
          };

          chunks.push(chunk);
        });
      }
    });
  });

  // Fallback: if no semantic elements found, chunk the body text
  if (chunks.length === 0) {
    const bodyText = document.body.textContent?.trim();
    if (bodyText) {
      const textChunks = splitLongText(bodyText, CONFIG.maxChunkLength);
      textChunks.forEach((chunkText, index) => {
        chunks.push({
          text: chunkText,
          index: index,
          metadata: CONFIG.includeMetadata
            ? {
                elementType: 'body',
                elementIndex: 0,
                subChunkIndex: index,
                totalSubChunks: textChunks.length,
                xpath: '/html/body',
                textLength: chunkText.length,
              }
            : null,
        });
      });
    }
  }

  return chunks;
}

/**
 * Split long text into smaller chunks while preserving sentence boundaries
 * @param {string} text - Text to split
 * @param {number} maxLength - Maximum length per chunk
 * @returns {Array} Array of text chunks
 */
function splitLongText(text, maxLength) {
  if (text.length <= maxLength) {
    return [text];
  }

  const chunks = [];
  const sentences = text.split(/(?<=[.!?])\s+/);
  let currentChunk = '';

  for (const sentence of sentences) {
    if ((currentChunk + sentence).length <= maxLength) {
      currentChunk += (currentChunk ? ' ' : '') + sentence;
    } else {
      if (currentChunk) {
        chunks.push(currentChunk);
        currentChunk = sentence;
      } else {
        // Handle very long sentences by splitting on word boundaries
        const words = sentence.split(' ');
        let wordChunk = '';

        for (const word of words) {
          if ((wordChunk + word).length <= maxLength) {
            wordChunk += (wordChunk ? ' ' : '') + word;
          } else {
            if (wordChunk) chunks.push(wordChunk);
            wordChunk = word;
          }
        }
        if (wordChunk) currentChunk = wordChunk;
      }
    }
  }

  if (currentChunk) {
    chunks.push(currentChunk);
  }

  return chunks.filter((chunk) => chunk.length >= CONFIG.minChunkLength);
}

/**
 * Get XPath for an element
 * @param {Element} element - DOM element
 * @returns {string} XPath string
 */
function getXPath(element) {
  if (element.id) {
    return `//*[@id="${element.id}"]`;
  }

  const parts = [];
  while (element && element.nodeType === Node.ELEMENT_NODE) {
    let index = 0;
    let sibling = element.previousSibling;

    while (sibling) {
      if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === element.tagName) {
        index++;
      }
      sibling = sibling.previousSibling;
    }

    const tagName = element.tagName.toLowerCase();
    const pathIndex = index > 0 ? `[${index + 1}]` : '';
    parts.unshift(`${tagName}${pathIndex}`);

    element = element.parentNode;
  }

  return parts.length ? `/${parts.join('/')}` : '';
}

/**
 * Fetch embeddings via the OpenAI client
 */
async function fetchEmbeddings(texts) {
  try {
    return await aiClient.getEmbeddings({
      model: MODEL_NAME,
      inputs: texts
    });
  } catch (error) {
    throw new Error(`OpenAI pipeline error: ${error.message}`);
  }
}

/**
 * Process chunks in batches with retry logic
 * @param {Array} chunks - Array of chunk objects
 * @returns {Promise} Promise resolving to embedded chunks
 */
async function processChunksWithRetry(chunks) {
  const results = [];

  // Process in batches
  for (let i = 0; i < chunks.length; i += CONFIG.batchSize) {
    const batch = chunks.slice(i, i + CONFIG.batchSize);
    const texts = batch.map((chunk) => chunk.text);

    let attempt = 0;
    let embeddings = null;

    while (attempt < CONFIG.retryAttempts && !embeddings) {
      try {
        embeddings = await fetchEmbeddings(texts);

        // Combine chunks with their embeddings
        batch.forEach((chunk, index) => {
          results.push({
            ...chunk,
            embedding: embeddings[index],
            embeddingModel: MODEL_NAME,
            processingTimestamp: new Date().toISOString(),
          });
        });
      } catch (error) {
        attempt++;
        console.warn(`Batch ${Math.floor(i / CONFIG.batchSize) + 1} attempt ${attempt} failed:`, error.message);

        if (attempt < CONFIG.retryAttempts) {
          await new Promise((resolve) => setTimeout(resolve, CONFIG.retryDelay * attempt));
        } else {
          // Add chunks without embeddings as fallback
          batch.forEach((chunk) => {
            results.push({
              ...chunk,
              embedding: null,
              error: error.message,
              embeddingModel: MODEL_NAME,
              processingTimestamp: new Date().toISOString(),
            });
          });
        }
      }
    }
  }

  return results;
}

/**
 * Main processing function
 * @returns {Promise} Promise resolving to processing results
 */
async function processPageEmbeddings() {
  try {
    // Validate configuration
    if (OPENAI_API_KEY === 'YOUR_OPENAI_API_KEY_HERE') {
      throw new Error('Please set your OpenAI API key in the OPENAI_API_KEY variable');
    }

    // Extract semantic chunks
    console.log('Extracting semantic chunks from webpage...');
    const chunks = extractSemanticChunks();
    console.log(`Extracted ${chunks.length} semantic chunks`);

    if (chunks.length === 0) {
      throw new Error('No content chunks found on the page');
    }

    // Process embeddings
    console.log(`Processing embeddings using ${MODEL_NAME}...`);
    const embeddedChunks = await processChunksWithRetry(chunks);

    // Generate summary statistics
    const successfulEmbeddings = embeddedChunks.filter((chunk) => chunk.embedding !== null).length;
    const failedEmbeddings = embeddedChunks.length - successfulEmbeddings;

    const result = {
      success: true,
      model: MODEL_NAME,
      totalChunks: embeddedChunks.length,
      successfulEmbeddings,
      failedEmbeddings,
      processingTimestamp: new Date().toISOString(),
      pageUrl: window.location.href,
      pageTitle: document.title,
      chunks: embeddedChunks,
      summary: {
        avgChunkLength: Math.round(embeddedChunks.reduce((sum, chunk) => sum + chunk.text.length, 0) / embeddedChunks.length),
        elementTypes: [...new Set(embeddedChunks.map((chunk) => chunk.metadata?.elementType).filter(Boolean))],
        embeddingDimensions: embeddedChunks.find((chunk) => chunk.embedding)?.embedding?.length || null,
      },
    };

    console.log(`Processing complete: ${successfulEmbeddings}/${embeddedChunks.length} chunks embedded successfully`);
    return result;
  } catch (error) {
    console.error('Processing failed:', error);
    return {
      success: false,
      error: error.message,
      model: MODEL_NAME,
      processingTimestamp: new Date().toISOString(),
      pageUrl: window.location.href,
      pageTitle: document.title,
    };
  }
}

// Execute the main function and return results to Screaming Frog
return processPageEmbeddings()
  .then((result) => seoSpider.data(JSON.stringify(result, null, 2)))
  .catch((error) => seoSpider.error(`Script execution failed: ${error.message}`));