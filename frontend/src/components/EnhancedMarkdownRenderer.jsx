import React, { useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import mermaid from 'mermaid';

// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'Inter, system-ui, sans-serif',
  fontSize: 14,
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: 'basis'
  },
  sequence: {
    useMaxWidth: true,
    htmlLabels: true
  },
  gantt: {
    useMaxWidth: true,
    htmlLabels: true
  }
});

const MermaidDiagram = ({ chart, id }) => {
  const ref = useRef();

  const renderChart = useCallback(async () => {
    if (ref.current && chart) {
      try {
        // Clear previous content
        ref.current.innerHTML = '';
        
        // Generate unique ID for this diagram
        const diagramId = `mermaid-${id}-${Date.now()}`;
        
        // Render the diagram
        const { svg } = await mermaid.render(diagramId, chart);
        ref.current.innerHTML = svg;
        
        // Add responsive styling
        const svgElement = ref.current.querySelector('svg');
        if (svgElement) {
          svgElement.style.maxWidth = '100%';
          svgElement.style.height = 'auto';
        }
      } catch (error) {
        console.error('Mermaid diagram error:', error);
        ref.current.innerHTML = `<pre class="bg-red-50 border border-red-200 rounded p-4 text-red-800 text-sm">Error rendering diagram: ${error.message}</pre>`;
      }
    }
  }, [chart, id]);

  useEffect(() => {
    renderChart();
  }, [renderChart]);

  return (
    <div className="my-6 p-4 bg-gray-50 border border-gray-200 rounded-lg overflow-x-auto">
      <div ref={ref} className="flex justify-center" />
    </div>
  );
};

const EnhancedMarkdownRenderer = ({ content, className = '' }) => {
  const mermaidCounter = useRef(0);

  const components = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';
      const code = String(children).replace(/\n$/, '');

      // Handle mermaid diagrams
      if (language === 'mermaid') {
        mermaidCounter.current += 1;
        return <MermaidDiagram chart={code} id={mermaidCounter.current} />;
      }

      // Handle regular code blocks
      if (!inline && match) {
        return (
          <div className="my-4">
            <SyntaxHighlighter
              style={vscDarkPlus}
              language={language}
              PreTag="div"
              customStyle={{
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                lineHeight: '1.5'
              }}
              {...props}
            >
              {code}
            </SyntaxHighlighter>
          </div>
        );
      }

      // Handle inline code
      return (
        <code className="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
          {children}
        </code>
      );
    },

    // Enhanced header styling with improved typography
    h1: ({ children }) => (
      <h1 className="text-4xl font-bold text-gray-900 mb-8 mt-8 pb-4 border-b-2 border-gray-200 first:mt-0">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-3xl font-semibold text-gray-900 mb-6 mt-10 pb-2 border-b border-gray-200">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-2xl font-semibold text-gray-900 mb-4 mt-8">
        {children}
      </h3>
    ),
    h4: ({ children }) => (
      <h4 className="text-xl font-semibold text-gray-900 mb-3 mt-6">
        {children}
      </h4>
    ),
    h5: ({ children }) => (
      <h5 className="text-lg font-semibold text-gray-900 mb-2 mt-5">
        {children}
      </h5>
    ),
    h6: ({ children }) => (
      <h6 className="text-base font-semibold text-gray-900 mb-2 mt-4">
        {children}
      </h6>
    ),

    // Enhanced paragraph styling
    p: ({ children }) => (
      <p className="text-gray-700 mb-5 leading-relaxed text-base">
        {children}
      </p>
    ),

    // Enhanced list styling
    ul: ({ children }) => (
      <ul className="list-disc list-outside ml-6 mb-5 space-y-2 text-gray-700">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-outside ml-6 mb-5 space-y-2 text-gray-700">
        {children}
      </ol>
    ),
    li: ({ children }) => (
      <li className="leading-relaxed">
        {children}
      </li>
    ),

    // Enhanced blockquote styling
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-blue-500 bg-blue-50 pl-6 pr-4 py-3 italic text-gray-700 mb-5 rounded-r-lg">
        {children}
      </blockquote>
    ),

    // Enhanced table styling
    table: ({ children }) => (
      <div className="overflow-x-auto mb-6 shadow-sm border border-gray-200 rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-gray-50">
        {children}
      </thead>
    ),
    tbody: ({ children }) => (
      <tbody className="bg-white divide-y divide-gray-200">
        {children}
      </tbody>
    ),
    th: ({ children }) => (
      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-6 py-4 text-sm text-gray-900 border-t border-gray-200">
        {children}
      </td>
    ),

    // Enhanced link styling
    a: ({ children, href, ...props }) => (
      <a
        href={href}
        className="text-blue-600 hover:text-blue-800 underline decoration-blue-600/30 hover:decoration-blue-800 transition-colors"
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
      </a>
    ),

    // Enhanced horizontal rule
    hr: () => (
      <hr className="my-8 border-0 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent" />
    ),

    // Enhanced emphasis
    em: ({ children }) => (
      <em className="italic text-gray-800 font-medium">
        {children}
      </em>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-gray-900">
        {children}
      </strong>
    ),

    // Enhanced image styling
    img: ({ src, alt, ...props }) => (
      <div className="my-6 text-center">
        <img
          src={src}
          alt={alt}
          className="max-w-full h-auto rounded-lg shadow-md mx-auto"
          {...props}
        />
        {alt && (
          <p className="text-sm text-gray-600 mt-2 italic">
            {alt}
          </p>
        )}
      </div>
    )
  };

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default EnhancedMarkdownRenderer; 