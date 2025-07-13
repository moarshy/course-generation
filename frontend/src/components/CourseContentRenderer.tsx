"use client";

import React, { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import mermaid from 'mermaid';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FileText, Target, CheckCircle2, AlertCircle, Eye, Code, BookOpen, Lightbulb, Copy, Check, ChevronDown, ChevronRight, HelpCircle, Brain } from 'lucide-react';

interface CourseContentRendererProps {
  content: string;
  introduction?: string;
  mainContent?: string;
  conclusion?: string;
  title?: string;
  learningObjectives?: string[];
  assessment?: string;
  summary?: string;
}

// Mermaid will be initialized in the component

// Language normalization for better syntax highlighting
const normalizeLanguage = (lang: string): string => {
  const languageMap: { [key: string]: string } = {
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python',
    'sh': 'bash',
    'shell': 'bash',
    'yml': 'yaml',
    'md': 'markdown',
    'jsx': 'javascript',
    'tsx': 'typescript',
    'json5': 'json',
    'jsonc': 'json',
  };
  
  const normalized = lang.toLowerCase().trim();
  return languageMap[normalized] || normalized;
};

// Helper function to extract text content from React children
const extractTextContent = (node: any): string => {
  if (typeof node === 'string') {
    return node;
  }
  if (Array.isArray(node)) {
    return node.map(extractTextContent).join('');
  }
  if (node && typeof node === 'object') {
    if (node.props && node.props.children) {
      return extractTextContent(node.props.children);
    }
  }
  return String(node || '');
};

const CodeBlock: React.FC<{ 
  code: string; 
  language: string; 
  showLineNumbers?: boolean;
}> = ({ code, language, showLineNumbers = true }) => {
  const [copied, setCopied] = React.useState(false);

  // Ensure code is always a string and clean it up
  const safeCode = String(code);
  const cleanCode = safeCode.replace(/\n$/, '');
  const normalizedLanguage = normalizeLanguage(language);
  const displayLanguage = language || 'text';

  // Calculate code statistics
  const lines = cleanCode.split('\n').length;
  const chars = cleanCode.length;
  const words = cleanCode.trim().split(/\s+/).length;

  // Get language icon/color
  const getLanguageInfo = (lang: string) => {
    const langMap: { [key: string]: { color: string; icon: string } } = {
      'javascript': { color: 'text-yellow-600', icon: '{}' },
      'typescript': { color: 'text-blue-600', icon: 'TS' },
      'python': { color: 'text-green-600', icon: 'Py' },
      'java': { color: 'text-red-600', icon: 'J' },
      'bash': { color: 'text-gray-600', icon: '$' },
      'json': { color: 'text-orange-600', icon: '{}' },
      'sql': { color: 'text-blue-500', icon: 'SQL' },
      'css': { color: 'text-blue-400', icon: 'CSS' },
      'html': { color: 'text-orange-500', icon: 'HTML' },
      'markdown': { color: 'text-gray-700', icon: 'MD' },
      'yaml': { color: 'text-purple-600', icon: 'YML' },
      'xml': { color: 'text-green-500', icon: 'XML' },
      'text': { color: 'text-gray-500', icon: 'TXT' }
    };
    return langMap[lang.toLowerCase()] || { color: 'text-gray-600', icon: 'CODE' };
  };

  const langInfo = getLanguageInfo(normalizedLanguage);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(safeCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  return (
    <div className="relative my-6 rounded-lg overflow-hidden border border-gray-200 shadow-sm bg-white">
      {/* Header bar */}
      <div className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <div className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold ${langInfo.color} bg-white border`}>
                {langInfo.icon}
              </div>
              <span className="text-sm font-semibold text-gray-700 capitalize">{displayLanguage}</span>
              {language !== normalizedLanguage && (
                <span className="text-xs text-gray-500 px-2 py-1 bg-gray-200 rounded">
                  maps to {normalizedLanguage}
                </span>
              )}
            </div>
            <div className="flex items-center space-x-3 text-xs text-gray-500">
              <span>{lines} lines</span>
              <span>{chars} chars</span>
              <span>{words} words</span>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <label className="flex items-center space-x-1 text-xs text-gray-600">
              <input
                type="checkbox"
                checked={showLineNumbers}
                onChange={() => {}} // Controlled by parent
                className="w-3 h-3 rounded"
              />
              <span>Lines</span>
            </label>
            <button
              onClick={handleCopy}
              className="flex items-center space-x-1 px-3 py-1.5 text-xs bg-white hover:bg-gray-50 border border-gray-300 rounded-md transition-colors shadow-sm"
              title="Copy code"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-green-600" />
                  <span className="text-green-600 font-medium">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 text-gray-600" />
                  <span className="text-gray-600">Copy</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
      
      {/* Code content */}
      <div className="relative">
        <SyntaxHighlighter
          language={normalizedLanguage}
          style={oneLight}
          showLineNumbers={showLineNumbers}
          wrapLines={true}
          wrapLongLines={true}
          customStyle={{
            margin: 0,
            padding: '1.5rem',
            background: '#fafafa',
            fontSize: '14px',
            lineHeight: '1.6',
            borderRadius: 0,
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          }}
          lineNumberStyle={{
            color: '#9ca3af',
            paddingRight: '1em',
            borderRight: '1px solid #e5e7eb',
            marginRight: '1em',
            userSelect: 'none',
            fontSize: '12px'
          }}
          codeTagProps={{
            style: {
              fontSize: '14px',
              fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
            }
          }}
        >
          {cleanCode}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};

const MermaidDiagram: React.FC<{ chart: string }> = ({ chart }) => {
  const [svg, setSvg] = React.useState<string>('');
  const [error, setError] = React.useState<string>('');
  const [isLoading, setIsLoading] = React.useState(true);

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        setIsLoading(true);
        setError('');
        
        // Initialize mermaid
        mermaid.initialize({ 
          startOnLoad: false,
          theme: 'neutral',
          securityLevel: 'loose'
        });
        
        const id = `mermaid-${Date.now()}`;
        const { svg: renderedSvg } = await mermaid.render(id, chart);
        setSvg(renderedSvg);
      } catch (err) {
        setError('Failed to render diagram');
        console.error('Mermaid render error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    if (chart) {
      renderDiagram();
    }
  }, [chart]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 my-6">
        <div className="flex items-center space-x-2 mb-2">
          <AlertCircle className="w-4 h-4 text-red-600" />
          <p className="text-red-600 text-sm font-medium">Diagram Rendering Error</p>
        </div>
        <p className="text-red-600 text-sm mb-2">{error}</p>
        <details className="text-xs text-red-500">
          <summary className="cursor-pointer hover:text-red-700">View source</summary>
          <pre className="mt-2 overflow-x-auto bg-red-100 p-2 rounded border">{chart}</pre>
        </details>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 my-6">
        <div className="flex items-center space-x-2 mb-2">
          <Code className="w-4 h-4 text-blue-600 animate-pulse" />
          <span className="text-sm font-medium text-blue-600">Rendering Diagram...</span>
        </div>
        <div className="animate-pulse bg-gray-200 h-32 rounded"></div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm my-6 overflow-hidden">
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
        <div className="flex items-center space-x-2">
          <Code className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-blue-600">Mermaid Diagram</span>
        </div>
      </div>
      <div className="p-6 overflow-x-auto">
        <div 
          className="flex justify-center"
          dangerouslySetInnerHTML={{ __html: svg }} 
        />
      </div>
    </div>
  );
};

interface QuestionAnswer {
  id: string;
  question: string;
  answer: string;
}

const AssessmentRenderer: React.FC<{ content: string }> = ({ content }) => {
  const [expandedQuestions, setExpandedQuestions] = React.useState<Set<string>>(new Set());

  const parseQuestionsAndAnswers = (text: string): QuestionAnswer[] => {
    const questions: QuestionAnswer[] = [];
    
    // Split by numbered questions (1., 2., etc.)
    const sections = text.split(/\n\s*\d+\./);
    
    sections.forEach((section, index) => {
      if (!section.trim() || index === 0) return;
      
      // Look for question mark to identify question
      const questionIndex = section.indexOf('?');
      if (questionIndex !== -1) {
        const questionText = section.substring(0, questionIndex + 1).trim();
        const remainingText = section.substring(questionIndex + 1).trim();
        
        // Clean up answer text
        let answerText = remainingText
          .replace(/^\*\*Answer\*\*:?\s*/i, '')
          .replace(/^Answer:?\s*/i, '')
          .replace(/^A:?\s*/i, '')
          .trim();
        
        if (questionText && answerText) {
          questions.push({
            id: `q${index}`,
            question: questionText,
            answer: answerText
          });
        }
      } else {
        // Try to split by answer indicators
        const answerSplit = section.split(/\n\s*(?:\*\*Answer\*\*|Answer:|A:)/i);
        if (answerSplit.length >= 2) {
          const questionText = answerSplit[0].trim();
          const answerText = answerSplit[1].trim();
          
          if (questionText && answerText) {
            questions.push({
              id: `q${index}`,
              question: questionText,
              answer: answerText
            });
          }
        }
      }
    });
    
    return questions;
  };

  const questionsAndAnswers = parseQuestionsAndAnswers(content);

  const toggleQuestion = (questionId: string) => {
    setExpandedQuestions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(questionId)) {
        newSet.delete(questionId);
      } else {
        newSet.add(questionId);
      }
      return newSet;
    });
  };

  if (questionsAndAnswers.length === 0) {
    // Fallback to simple markdown if parsing fails
    return (
      <div className="prose max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Brain className="w-5 h-5 text-purple-600" />
          <span className="text-sm font-medium text-purple-800">
            {questionsAndAnswers.length} Questions
          </span>
        </div>
        <button
          onClick={() => {
            if (expandedQuestions.size === questionsAndAnswers.length) {
              setExpandedQuestions(new Set());
            } else {
              setExpandedQuestions(new Set(questionsAndAnswers.map(qa => qa.id)));
            }
          }}
          className="text-xs text-purple-600 hover:text-purple-800 font-medium"
        >
          {expandedQuestions.size === questionsAndAnswers.length ? 'Collapse All' : 'Expand All'}
        </button>
      </div>

      {questionsAndAnswers.map((qa, index) => {
        const isExpanded = expandedQuestions.has(qa.id);
        
        return (
          <div key={qa.id} className="border border-purple-200 rounded-lg overflow-hidden bg-white shadow-sm">
            <button
              onClick={() => toggleQuestion(qa.id)}
              className="w-full px-4 py-3 text-left hover:bg-purple-50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 flex items-center justify-center mt-0.5">
                    <span className="text-xs font-bold text-purple-700">{index + 1}</span>
                  </div>
                  <div className="flex items-start space-x-2 flex-1">
                    <HelpCircle className="w-4 h-4 text-purple-600 mt-0.5 flex-shrink-0" />
                    <p className="text-purple-900 font-medium leading-relaxed">{qa.question}</p>
                  </div>
                </div>
                <div className="flex-shrink-0 ml-2">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-purple-600" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-purple-600" />
                  )}
                </div>
              </div>
            </button>
            
            {isExpanded && (
              <div className="px-4 pb-4 border-t border-purple-100 bg-purple-25">
                <div className="pl-9 pt-3">
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ children }) => (
                          <p className="text-purple-800 mb-2 leading-relaxed">
                            {children}
                          </p>
                        ),
                        ul: ({ children }) => (
                          <ul className="list-disc pl-4 text-purple-800 space-y-1 mb-3">
                            {children}
                          </ul>
                        ),
                        li: ({ children }) => (
                          <li className="text-purple-800">
                            {children}
                          </li>
                        ),
                        code: ({ children, className }) => {
                          const match = /language-(\w+)/.exec(className || '');
                          const language = match ? match[1] : '';
                          
                          if (language) {
                            const code = extractTextContent(children).replace(/\n$/, '');
                            return <CodeBlock code={code} language={language} />;
                          }
                          
                          return (
                            <code className="bg-purple-100 px-2 py-1 rounded text-sm font-mono text-purple-900 border border-purple-200">
                              {extractTextContent(children)}
                            </code>
                          );
                        },
                      }}
                    >
                      {qa.answer}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

const MarkdownRenderer: React.FC<{ content: string }> = ({ content }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        h1: ({ children }) => (
          <h1 className="text-2xl font-bold text-gray-900 mb-4 mt-8 border-b pb-2">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-xl font-semibold text-gray-900 mb-3 mt-6">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-lg font-medium text-gray-900 mb-2 mt-5">
            {children}
          </h3>
        ),
        p: ({ children }) => (
          <p className="text-gray-700 mb-4 leading-relaxed">
            {children}
          </p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc pl-6 text-gray-700 mb-4 space-y-2">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal pl-6 text-gray-700 mb-4 space-y-2">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="text-gray-700 leading-relaxed">
            {children}
          </li>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 my-4 bg-blue-50 py-2 rounded-r">
            {children}
          </blockquote>
        ),
        code: ({ children, className, ...props }) => {
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : '';
          
          // Handle mermaid diagrams
          if (language === 'mermaid') {
            const code = String(children).replace(/\n$/, '');
            return <MermaidDiagram chart={code} />;
          }
          
          // Handle code blocks with language
          if (language) {
            const code = extractTextContent(children).replace(/\n$/, '');
            return <CodeBlock code={code} language={language} />;
          }
          
          // Inline code (no language specified)
          return (
            <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800 border border-gray-200">
              {extractTextContent(children)}
            </code>
          );
        },
        pre: ({ children }) => {
          // Handle pre tags that might contain code without language
          try {
            const childElement = React.Children.only(children) as React.ReactElement;
            
            // If it's a code element, try to extract language from className
            if (childElement && childElement.type === 'code' && childElement.props) {
              const props = childElement.props as any;
              const className = props.className || '';
              const languageMatch = className.match(/language-(\w+)/);
              
              if (languageMatch) {
                const language = languageMatch[1];
                const code = String(props.children).replace(/\n$/, '');
                
                if (language === 'mermaid') {
                  return <MermaidDiagram chart={code} />;
                }
                
                return <CodeBlock code={code} language={language} />;
              }
            }
          } catch (e) {
            // If there's an error parsing children, fall through to default
          }
          
          // Fallback for plain pre blocks
          return (
            <div className="bg-gray-50 rounded-lg p-4 overflow-x-auto my-6 border border-gray-200">
              <pre className="text-sm text-gray-800 font-mono whitespace-pre-wrap">
                {children}
              </pre>
            </div>
          );
        },
        table: ({ children }) => (
          <div className="overflow-x-auto my-4 border rounded-lg">
            <table className="min-w-full border-collapse">
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border-b border-gray-200 bg-gray-50 px-4 py-2 text-left font-semibold text-gray-900">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border-b border-gray-200 px-4 py-2 text-gray-700">
            {children}
          </td>
        ),
        img: ({ src, alt }) => (
          <img 
            src={src} 
            alt={alt} 
            className="max-w-full h-auto rounded-lg border my-4"
          />
        ),
        a: ({ href, children }) => (
          <a 
            href={href} 
            className="text-blue-600 hover:text-blue-800 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
};

const CourseContentRenderer: React.FC<CourseContentRendererProps> = ({ 
  content, 
  introduction,
  mainContent,
  conclusion,
  title, 
  learningObjectives,
  assessment,
  summary 
}) => {
  // Use separate sections if available, otherwise fall back to combined content
  const hasSeperatedSections = !!(introduction || mainContent || conclusion);
  const displayContent = hasSeperatedSections ? '' : content;
  
  // Calculate content statistics for audit purposes
  const totalContent = [introduction, mainContent, conclusion, assessment, summary].filter(Boolean).join('\n\n');
  const analyzeContent = totalContent || content;
  
  const contentStats = {
    wordCount: analyzeContent.split(/\s+/).length,
    paragraphCount: analyzeContent.split('\n\n').length,
    codeBlocks: (analyzeContent.match(/```[\s\S]*?```/g) || []).length,
    mermaidDiagrams: (analyzeContent.match(/```mermaid[\s\S]*?```/g) || []).length,
    headingCount: (analyzeContent.match(/^#{1,6}\s+/gm) || []).length
  };

  return (
    <div className="space-y-6">
      {/* Audit Header */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-2">
          <Eye className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-blue-900">Content Audit</h3>
          {hasSeperatedSections && (
            <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">
              Structured Sections
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="font-medium text-blue-800">Word Count:</span>
            <span className="text-blue-700 ml-2">{contentStats.wordCount}</span>
          </div>
          <div>
            <span className="font-medium text-blue-800">Paragraphs:</span>
            <span className="text-blue-700 ml-2">{contentStats.paragraphCount}</span>
          </div>
          <div>
            <span className="font-medium text-blue-800">Headings:</span>
            <span className="text-blue-700 ml-2">{contentStats.headingCount}</span>
          </div>
          <div>
            <span className="font-medium text-blue-800">Code Blocks:</span>
            <span className="text-blue-700 ml-2">{contentStats.codeBlocks}</span>
          </div>
          <div>
            <span className="font-medium text-blue-800">Diagrams:</span>
            <span className="text-blue-700 ml-2">{contentStats.mermaidDiagrams}</span>
          </div>
        </div>
      </div>

      {/* Learning Objectives */}
      {learningObjectives && learningObjectives.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <Target className="w-5 h-5 text-green-600" />
            <h3 className="text-lg font-semibold text-green-900">Learning Objectives</h3>
            <span className="text-sm text-green-700 bg-green-100 px-2 py-1 rounded">
              {learningObjectives.length} objectives
            </span>
          </div>
          <ul className="space-y-2">
            {learningObjectives.map((objective, index) => (
              <li key={index} className="flex items-start space-x-2">
                <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-green-800 leading-relaxed">{objective}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Introduction Section */}
      {introduction && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <BookOpen className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-blue-900">Introduction</h3>
          </div>
          <div className="prose prose-lg max-w-none">
            <MarkdownRenderer content={introduction} />
          </div>
        </div>
      )}

      {/* Main Content Section */}
      {mainContent && (
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <FileText className="w-5 h-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Main Content</h3>
          </div>
          <div className="prose prose-lg max-w-none">
            <MarkdownRenderer content={mainContent} />
          </div>
        </div>
      )}

      {/* Conclusion Section */}
      {conclusion && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Lightbulb className="w-5 h-5 text-yellow-600" />
            <h3 className="text-lg font-semibold text-yellow-900">Conclusion</h3>
          </div>
          <div className="prose prose-lg max-w-none">
            <MarkdownRenderer content={conclusion} />
          </div>
        </div>
      )}

      {/* Fallback: Combined Content */}
      {!hasSeperatedSections && displayContent && (
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <FileText className="w-5 h-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Module Content</h3>
          </div>
          <div className="prose prose-lg max-w-none">
            <MarkdownRenderer content={displayContent} />
          </div>
        </div>
      )}

      {/* Assessment Section */}
      {assessment && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <CheckCircle2 className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-purple-900">Assessment</h3>
          </div>
          <AssessmentRenderer content={assessment} />
        </div>
      )}

      {/* Summary Section */}
      {summary && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <div className="flex items-center space-x-2 mb-3">
            <FileText className="w-5 h-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Summary</h3>
          </div>
          <div className="prose max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => (
                  <p className="text-gray-700 mb-2 leading-relaxed">
                    {children}
                  </p>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc pl-6 text-gray-700 space-y-1">
                    {children}
                  </ul>
                ),
                li: ({ children }) => (
                  <li className="text-gray-700">
                    {children}
                  </li>
                ),
              }}
            >
              {summary}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
};

export default CourseContentRenderer; 