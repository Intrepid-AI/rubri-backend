import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardHeader, CardContent, Button } from '../ui';
import '../../styles/markdown-enhanced.css';
import { 
  Download, 
  Share2, 
  Copy, 
  CheckCircle, 
  Clock, 
  Users, 
  Target,
  FileText,
  ArrowRight,
  ExternalLink
} from 'lucide-react';
import type { QuestionGenerationResponse } from '../../types/api';

interface ReportViewerProps {
  result: QuestionGenerationResponse;
  onExport?: (format: 'pdf' | 'link') => void;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  result,
  onExport
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyReport = async () => {
    if (result.formatted_report) {
      await navigator.clipboard.writeText(result.formatted_report);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDuration = (minutes?: number) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header with Metrics */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-foreground mb-2">
                Interview Questions for {result.position_title}
              </h1>
              {result.candidate_name && (
                <p className="text-foreground-muted">
                  Candidate: <span className="font-medium">{result.candidate_name}</span>
                </p>
              )}
              <p className="text-sm text-foreground-subtle mt-1">
                Generated in {result.processing_time.toFixed(1)}s • Input: {result.input_scenario}
              </p>
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyReport}
                disabled={!result.formatted_report}
              >
                {copied ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </>
                )}
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => onExport?.('pdf')}
              >
                <Download className="h-4 w-4 mr-2" />
                Export PDF
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => onExport?.('link')}
              >
                <Share2 className="h-4 w-4 mr-2" />
                Share Link
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-blue-500/20 rounded-lg mx-auto mb-2">
                <Target className="h-6 w-6 text-blue-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {result.skills_identified || 0}
              </p>
              <p className="text-sm text-foreground-muted">Skills Identified</p>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-green-500/20 rounded-lg mx-auto mb-2">
                <FileText className="h-6 w-6 text-green-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {result.questions_generated || 0}
              </p>
              <p className="text-sm text-foreground-muted">Questions Generated</p>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-purple-500/20 rounded-lg mx-auto mb-2">
                <Clock className="h-6 w-6 text-purple-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {formatDuration(result.interview_duration_minutes || undefined)}
              </p>
              <p className="text-sm text-foreground-muted">Est. Duration</p>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center w-12 h-12 bg-orange-500/20 rounded-lg mx-auto mb-2">
                <Users className="h-6 w-6 text-orange-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {result.sections_created || 0}
              </p>
              <p className="text-sm text-foreground-muted">Sections</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Insights */}
      {(result.key_strengths || result.potential_concerns || result.focus_areas) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {result.key_strengths && result.key_strengths.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-green-400">Key Strengths</h3>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.key_strengths.map((strength, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-foreground-muted">{strength}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          
          {result.potential_concerns && result.potential_concerns.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-orange-400">Areas to Explore</h3>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.potential_concerns.map((concern, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <ArrowRight className="h-4 w-4 text-orange-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-foreground-muted">{concern}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          
          {result.focus_areas && result.focus_areas.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-blue-400">Focus Areas</h3>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.focus_areas.map((area, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <Target className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-foreground-muted">{area}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Overall Recommendation */}
      {result.overall_recommendation && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-foreground">Overall Recommendation</h3>
          </CardHeader>
          <CardContent>
            <p className="text-foreground-muted leading-relaxed">
              {result.overall_recommendation}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Main Report */}
      {result.formatted_report && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-foreground">Interview Questions & Guidance</h3>
            <p className="text-sm text-foreground-muted">
              Complete interview plan with questions, expected responses, and evaluation criteria
            </p>
          </CardHeader>
          <CardContent>
            <div className="markdown-enhanced max-w-none" spellCheck={false}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Professional Link Components with enhanced styling
                  a: ({ href, children }) => (
                    <a href={href} className="text-primary-600 hover:text-primary-800 no-underline hover:underline transition-all duration-200" target="_blank" rel="noopener noreferrer" spellCheck={false}>
                      {children}
                      <ExternalLink className="inline h-3 w-3 ml-1" />
                    </a>
                  ),
                  // Enhanced Table Components - Let CSS handle the styling
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-6">
                      <table className="min-w-full">
                        {children}
                      </table>
                    </div>
                  ),
                  // Keep other components minimal to let CSS handle styling
                }}
              >
                {result.formatted_report}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent Performance (for debugging) */}
      {result.agent_performance && import.meta.env.DEV && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-foreground">Agent Performance</h3>
            <p className="text-sm text-foreground-muted">Debug information</p>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-surface-100 p-3 rounded-md overflow-x-auto text-foreground-muted">
              {JSON.stringify(result.agent_performance, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
};